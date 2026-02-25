"""
Task 302: Agent Selection

Analyze PRD and select agents for task decomposition.

This task:
  1. Analyzes the PRD to understand project characteristics
  2. Provides contextual guidance on agent selection
  3. Recommends additional agents based on project specifics
  4. Allows customization of agent composition

Core agents (always included):
  - task-decomposer (opus) - Break PRD into tasks
  - dependency-mapper (sonnet) - Map task dependencies, build DAG
  - work-packager (sonnet) - Group tasks for parallel execution

Validation agents (always included):
  - task-validator (sonnet) - Validate task quality
  - coverage-checker (haiku) - Verify PRD coverage
"""

import sys
import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.config import Config
from core.state import StateManager
from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user, clear_input_buffer
)
from core.utils.file_ops import ensure_dir, read_file, write_file


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None, graph=None) -> bool:
    """
    Execute Task 302: Agent Selection.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing
        graph: Optional GraphManager instance for knowledge graph operations

    Returns:
        True if task completed successfully, False otherwise
    """
    agents_file = output_dir / "selected-agents.json"
    project_root = atomic_root.parent
    prd_file = project_root / "docs" / "prd" / "PRD.md"
    analysis_file = output_dir / "prd-analysis.json"

    # UAT Mode: Auto-select core agents
    if uat_mode:
        print()
        print(print_yellow("⚡ UAT Mode: Using core agents only"))
        print()

        agents_data = {
            "selected": ["task-decomposer", "dependency-mapper", "work-packager",
                        "task-validator", "coverage-checker"],
            "additional": [],
            "selection_method": "uat_defaults"
        }
        write_file(agents_file, json.dumps(agents_data, indent=2))
        print(print_green("✓ Agent selection complete (UAT mode)"))
        return True

    print()
    print(print_dim("Analyzing your PRD to recommend the best agent composition."))
    print()

    # PRD Analysis
    print(print_dim("─" * 100))
    print()
    print(print_bold("PRD ANALYSIS"))
    print()

    # Analyze PRD characteristics
    analysis = _analyze_prd(prd_file)

    print(print_dim("Scanned PRD for project characteristics..."))
    print()
    print(print_bold("Project Profile:"))
    print()
    print(f"  Features:     {analysis['feature_count']} defined")
    print(f"  NFRs:         {analysis['nfr_count']} defined")
    print()
    print(print_bold("Detected Patterns:"))
    print()

    patterns = analysis['patterns']
    if patterns['api']:
        print(print_green("  ✓ API/Endpoints"))
    if patterns['auth']:
        print(print_green("  ✓ Authentication/Authorization"))
    if patterns['database']:
        print(print_green("  ✓ Database/Data Layer"))
    if patterns['ui']:
        print(print_green("  ✓ User Interface"))
    if patterns['testing']:
        print(print_green("  ✓ Testing Emphasis"))
    if patterns['security']:
        print(print_green("  ✓ Security Requirements"))
    if patterns['integration']:
        print(print_green("  ✓ External Integrations"))
    if patterns['performance']:
        print(print_green("  ✓ Performance Requirements"))

    if not any(patterns.values()):
        print(print_dim("  (No specific patterns detected - using core agents)"))
    print()

    # Save analysis
    ensure_dir(analysis_file.parent)
    write_file(analysis_file, json.dumps(analysis, indent=2))

    # Core Agents
    _show_core_agents()

    # Recommended Additions
    recommendations = _get_recommendations(analysis)
    _show_recommendations(recommendations)

    # Selection
    print(print_dim("─" * 100))
    print()
    print(print_bold("SELECTION"))
    print()

    decomposition_agents = ["task-decomposer", "dependency-mapper", "work-packager"]
    validation_agents = ["task-validator", "coverage-checker"]
    additional_agents: List[str] = []

    if recommendations:
        print(print_green("  approve     ") + f"Use core agents + recommendations ({len(recommendations)} suggested)")
        print(print_cyan("  core        ") + "Use core agents only")
        print(print_yellow("  custom      ") + "Customize agent selection")
        print()

        agent_choice = ""
        while agent_choice not in ["approve", "core", "custom"]:
            clear_input_buffer()
            agent_choice = prompt_user("Choice (default: approve): ").strip().lower()
            if not agent_choice:
                agent_choice = "approve"
            if agent_choice not in ["approve", "core", "custom"]:
                print(print_red("Invalid choice. Enter: approve, core, or custom"))

        if agent_choice == "approve":
            additional_agents = [rec[0] for rec in recommendations]
        elif agent_choice == "custom":
            additional_agents = _custom_selection(recommendations)
    else:
        print(print_green("  approve     ") + "Use core agents")
        print(print_yellow("  custom      ") + "Add custom agents")
        print()

        agent_choice = ""
        while agent_choice not in ["approve", "custom"]:
            clear_input_buffer()
            agent_choice = prompt_user("Choice (default: approve): ").strip().lower()
            if not agent_choice:
                agent_choice = "approve"
            if agent_choice not in ["approve", "custom"]:
                print(print_red("Invalid choice. Enter: approve or custom"))

        if agent_choice == "custom":
            additional_agents = _custom_selection_from_all()

    print()

    # Summary
    _show_final_roster(decomposition_agents, validation_agents, additional_agents)

    # Save Selection
    selection_data = {
        "phase": 3,
        "phase_name": "Tasking",
        "decomposition_agents": decomposition_agents,
        "validation_agents": validation_agents,
        "additional_agents": additional_agents,
        "agent_pipeline": {
            "sequential": decomposition_agents,
            "parallel": validation_agents
        },
        "prd_analysis": analysis,
        "selected_at": datetime.utcnow().isoformat() + "Z"
    }

    ensure_dir(agents_file.parent)
    write_file(agents_file, json.dumps(selection_data, indent=2))

    print(print_green("✓ Agent selection complete"))
    return True


def _analyze_prd(prd_file: Path) -> Dict[str, Any]:
    """Analyze PRD to detect project characteristics."""
    analysis = {
        "feature_count": 0,
        "nfr_count": 0,
        "patterns": {
            "api": False,
            "auth": False,
            "database": False,
            "ui": False,
            "testing": False,
            "security": False,
            "integration": False,
            "performance": False
        },
        "analyzed_at": datetime.utcnow().isoformat() + "Z"
    }

    if not prd_file.exists():
        return analysis

    content = read_file(prd_file).lower()

    # Count features and NFRs
    analysis["feature_count"] = len(re.findall(r'^## feature f\d+', content, re.MULTILINE | re.IGNORECASE))
    analysis["nfr_count"] = len(re.findall(r'^## nfr-\d+', content, re.MULTILINE | re.IGNORECASE))

    # Detect patterns
    patterns = analysis["patterns"]
    patterns["api"] = bool(re.search(r'api|endpoint|rest|graphql|grpc|webhook', content))
    patterns["auth"] = bool(re.search(r'auth|authentication|authorization|oauth|jwt|token|login|rbac|permission', content))
    patterns["database"] = bool(re.search(r'database|sql|postgres|mysql|mongo|redis|schema|migration|orm', content))
    patterns["ui"] = bool(re.search(r'ui|interface|component|frontend|react|vue|angular|css|responsive', content))
    patterns["testing"] = bool(re.search(r'test coverage|unit test|integration test|e2e|tdd|pytest|vitest|jest', content))
    patterns["security"] = bool(re.search(r'security|encryption|audit|compliance|vulnerability|sast|sca|owasp', content))
    patterns["integration"] = bool(re.search(r'integration|third-party|external api|webhook|event|message queue|kafka|rabbitmq', content))
    patterns["performance"] = bool(re.search(r'latency|throughput|performance|p99|p95|scalability|load|benchmark', content))

    return analysis


def _show_core_agents() -> None:
    """Display core agents that are always included."""
    print(print_dim("─" * 100))
    print()
    print(print_bold("CORE AGENTS ") + print_dim("(always included)"))
    print()
    print("These agents form the backbone of task decomposition. They transform your")
    print("PRD into a structured task graph following the DAG (Directed Acyclic Graph)")
    print("pattern, enabling parallel execution in git worktrees.")
    print()
    print(print_green("  task-decomposer") + " (opus)")
    print(print_dim("    Parses PRD Section 4 (Features) and Section 10 (Task Decomposition)."))
    print(print_dim("    Generates atomic tasks with acceptance criteria from EARS requirements."))
    print(print_dim("    Maps RFC 2119 keywords (SHALL/SHOULD/MAY) to task priorities."))
    print()
    print(print_green("  dependency-mapper") + " (sonnet)")
    print(print_dim("    Builds the DAG from PRD dependency tables and task relationships."))
    print(print_dim("    Detects cycles, validates ordering, identifies critical path."))
    print(print_dim("    Enables parallel worktree execution for independent tasks."))
    print()
    print(print_green("  work-packager") + " (sonnet)")
    print(print_dim("    Groups tasks into parallel execution packages based on DAG analysis."))
    print(print_dim("    Assigns tasks to worktrees, respects dependency constraints."))
    print()
    print(print_green("  task-validator") + " (sonnet)")
    print(print_dim("    Validates task clarity, completeness, and actionability."))
    print(print_dim("    Ensures acceptance criteria are testable."))
    print()
    print(print_green("  coverage-checker") + " (haiku)")
    print(print_dim("    Verifies all PRD features have corresponding tasks."))
    print(print_dim("    Maps tasks back to requirements for traceability."))
    print()


def _get_recommendations(analysis: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Get agent recommendations based on PRD analysis."""
    recommendations = []
    patterns = analysis["patterns"]
    feature_count = analysis["feature_count"]

    if patterns["api"]:
        recommendations.append((
            "api-task-specialist",
            "Your PRD includes API/endpoint definitions. This agent ensures API tasks include proper request/response validation, error handling, and versioning considerations."
        ))

    if patterns["auth"] or patterns["security"]:
        recommendations.append((
            "security-task-analyst",
            "Your PRD includes authentication or security requirements. This agent adds security-focused subtasks and ensures OWASP considerations are addressed."
        ))

    if patterns["testing"] or feature_count > 5:
        recommendations.append((
            "test-strategy-planner",
            "Your PRD emphasizes testing or has many features. This agent pre-plans test approaches and ensures TDD phases (RED/GREEN/REFACTOR/VERIFY) are well-scoped."
        ))

    if patterns["database"]:
        recommendations.append((
            "data-task-architect",
            "Your PRD includes database/data layer requirements. This agent ensures tasks properly sequence schema changes, migrations, and data access patterns."
        ))

    if patterns["integration"]:
        recommendations.append((
            "integration-task-specialist",
            "Your PRD includes external integrations. This agent ensures integration tasks include proper error handling, retry logic, and fallback strategies."
        ))

    return recommendations


def _show_recommendations(recommendations: List[Tuple[str, str]]) -> None:
    """Display recommended agents."""
    print(print_dim("─" * 100))
    print()
    print(print_bold("RECOMMENDED ADDITIONS ") + print_dim("(based on your PRD)"))
    print()

    if not recommendations:
        print(print_dim("No specific additions recommended - core agents are sufficient for this project."))
        print()
    else:
        for agent_name, reason in recommendations:
            print(print_yellow(f"  {agent_name}") + " (sonnet)")
            print(print_dim(f"    {reason}"))
            print()


def _custom_selection(recommendations: List[Tuple[str, str]]) -> List[str]:
    """Handle custom agent selection from recommendations."""
    print()
    print(print_dim("Select additional agents (space-separated numbers, or 'none'):"))
    for i, (agent_name, _) in enumerate(recommendations, 1):
        print(f"  {i}. {agent_name}")
    print()

    custom_selection = prompt_user("> ").strip()
    additional = []

    if custom_selection and custom_selection != "none":
        for num_str in custom_selection.split():
            try:
                idx = int(num_str) - 1
                if 0 <= idx < len(recommendations):
                    additional.append(recommendations[idx][0])
            except ValueError as e:
                logger.debug("Invalid agent selection number %r: %s", num_str, e)

    return additional


def _custom_selection_from_all() -> List[str]:
    """Handle custom agent selection from all available agents."""
    print()
    print(print_dim("Available additional agents:"))
    print("  1. api-task-specialist")
    print("  2. security-task-analyst")
    print("  3. test-strategy-planner")
    print("  4. data-task-architect")
    print("  5. integration-task-specialist")
    print()

    custom_selection = prompt_user("Select (space-separated numbers): ").strip()
    additional = []

    agent_map = {
        "1": "api-task-specialist",
        "2": "security-task-analyst",
        "3": "test-strategy-planner",
        "4": "data-task-architect",
        "5": "integration-task-specialist"
    }

    for num in custom_selection.split():
        if num in agent_map:
            additional.append(agent_map[num])

    return additional


def _show_final_roster(
    decomposition: List[str],
    validation: List[str],
    additional: List[str]
) -> None:
    """Display final agent roster."""
    print(print_dim("─" * 100))
    print()
    print(print_bold("FINAL AGENT ROSTER"))
    print()
    print(print_dim("Decomposition Pipeline (sequential):"))
    for agent in decomposition:
        print(f"  • {agent}")
    print()
    print(print_dim("Validation (parallel):"))
    for agent in validation:
        print(f"  • {agent}")
    if additional:
        print()
        print(print_dim("Additional Specialists:"))
        for agent in additional:
            print(f"  • {agent}")
    print()


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 302: Agent Selection")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
