"""
Task 503: Agent Selection

Select agents for TDD execution: test-writer, code-implementer, refactorer, security-scanner.
"""

import sys
import json
import csv
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, print_magenta, prompt_user
)
from core.utils.file_ops import ensure_dir, write_file, read_file


def find_agent_repo(atomic_root: Path) -> Optional[Path]:
    """Find the agent repository location."""
    # Check embedded repo first (monorepo deployment)
    embedded_repo = atomic_root / "repos" / "agents"
    if (embedded_repo / "agent-inventory.csv").exists():
        return embedded_repo

    # Check atomic_root/agents
    local_agents = atomic_root / "agents"
    if (local_agents / "agent-inventory.csv").exists():
        return local_agents

    # Check environment variable
    import os
    env_repo = os.environ.get('ATOMIC_AGENT_REPO')
    if env_repo:
        repo_path = Path(env_repo)
        if (repo_path / "agent-inventory.csv").exists():
            return repo_path

    return None


def get_csv_model(agent_name: str, csv_path: Path) -> str:
    """Get model tier for agent. CSV has no model column — return default.

    Model assignment is handled by pipeline config, not agent inventory.
    """
    return "opus"


def analyze_project_patterns(specs_dir: Path) -> Dict[str, bool]:
    """Analyze project characteristics from specs."""
    patterns = {
        "has_api": False,
        "has_db": False,
        "has_frontend": False,
        "has_cli": False,
        "has_async": False
    }

    if not specs_dir.exists():
        return patterns

    for spec_file in specs_dir.glob("*.json"):
        try:
            content = read_file(spec_file)
            content_lower = content.lower()

            if any(keyword in content_lower for keyword in ["api", "endpoint", "rest", "graphql"]):
                patterns["has_api"] = True
            if any(keyword in content_lower for keyword in ["database", "sql", "query", "orm"]):
                patterns["has_db"] = True
            if any(keyword in content_lower for keyword in ["component", "render", "dom", "react", "vue"]):
                patterns["has_frontend"] = True
            if any(keyword in content_lower for keyword in ["command", "cli", "argparse", "argv"]):
                patterns["has_cli"] = True
            if any(keyword in content_lower for keyword in ["async", "await", "concurrent", "parallel"]):
                patterns["has_async"] = True
        except:
            continue

    return patterns


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None) -> bool:
    """
    Execute Task 503: Agent Selection.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    project_root = atomic_root.parent
    agents_file = output_dir / "selected-agents.json"
    tasks_file = project_root / ".taskmaster" / "tasks" / "tasks.json"
    specs_dir = project_root / ".claude" / "specs"

    # UAT Mode Bypass
    if uat_mode:
        print()
        print(print_yellow("⚡ UAT Mode: Auto-selecting default implementation agents"))
        print()

        ensure_dir(agents_file.parent)

        agents_data = {
            "tdd_agents": {
                "red": {"name": "test-first-developer", "model": "haiku", "phase": "RED"},
                "green": {"name": "implementation-engineer", "model": "sonnet", "phase": "GREEN"},
                "refactor": {"name": "code-optimization-specialist", "model": "haiku", "phase": "REFACTOR"},
                "verify": {"name": "security-scanner", "model": "haiku", "phase": "VERIFY"}
            },
            "specialists": ["backend-engineer", "api-developer"],
            "source": "uat-defaults",
            "mode": "uat",
            "selected_at": datetime.now().isoformat()
        }
        write_file(agents_file, json.dumps(agents_data, indent=2))

        print(print_green("✓ Agent Selection complete (UAT mode)"))
        return True

    ensure_dir(agents_file.parent)

    print()
    print(print_dim("  Selecting specialized agents for each TDD phase from agent-inventory.csv."))
    print()

    # Load Available Agents from CSV
    print(print_dim("─" * 120))
    print()
    print(print_bold("AVAILABLE IMPLEMENTATION AGENTS") + " (from agent-inventory.csv)")
    print()

    agent_repo = find_agent_repo(atomic_root)
    csv_path = agent_repo / "agent-inventory.csv" if agent_repo else None

    if csv_path and csv_path.exists():
        print(print_dim("  Agents in 06-09-implementation category:"))
        print()

        try:
            with open(csv_path, newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('category', '') == "06-09-implementation":
                        name = row.get('name', '')
                        tier = row.get('tier', '')
                        role = row.get('role', '')
                        print(f"    {name:<28} [{tier:<6} {role}]")
        except Exception as e:
            print(print_yellow(f"  ! Error reading agent inventory: {e}"))

        print()
    else:
        print(print_yellow("  ! Agent inventory not found - using defaults"))
        print()

    # Project Analysis
    print(print_dim("─" * 120))
    print()
    print(print_bold("PROJECT ANALYSIS"))
    print()

    patterns = analyze_project_patterns(specs_dir)

    print(print_dim("  Detected project patterns:"))
    print()
    if patterns["has_api"]:
        print(print_green("    ✓ API endpoints"))
    if patterns["has_db"]:
        print(print_green("    ✓ Database operations"))
    if patterns["has_frontend"]:
        print(print_green("    ✓ Frontend components"))
    if patterns["has_cli"]:
        print(print_green("    ✓ CLI interface"))
    if patterns["has_async"]:
        print(print_green("    ✓ Async/concurrent code"))
    print()

    # TDD Agent Roles
    print(print_dim("─" * 120))
    print()
    print(print_bold("TDD AGENT ROLES"))
    print()

    print(print_dim("  Four agents are needed for the TDD cycle (using agents from inventory):"))
    print()

    # RED phase agent
    print(print_red("  " + "─" * 118))
    print(print_bold("  RED: Test Strategist"))
    print()
    print("    Writes failing tests based on OpenSpec test strategy.")
    print("    Must understand testing frameworks, mocking, fixtures.")
    print()
    print(print_cyan("    Recommended:") + " test-strategist (expert, opus)")
    print(print_red("  " + "─" * 118))
    print()

    # GREEN phase agent
    print(print_green("  " + "─" * 118))
    print(print_bold("  GREEN: TDD Implementation"))
    print()
    print("    Writes minimal implementation to make tests pass.")
    print("    Focus on correctness, not optimization.")
    print()
    print(print_cyan("    Recommended:") + " tdd-implementation-agent (phd, opus)")
    print(print_green("  " + "─" * 118))
    print()

    # REFACTOR phase agent
    print(print_cyan("  " + "─" * 118))
    print(print_bold("  REFACTOR: Code Review Gate"))
    print()
    print("    Improves code quality while maintaining test passage.")
    print("    Runs linters, formatters, type checkers.")
    print()
    print(print_cyan("    Recommended:") + " code-review-gate (expert, opus)")
    print(print_cyan("  " + "─" * 118))
    print()

    # VERIFY phase agent
    print(print_magenta("  " + "─" * 118))
    print(print_bold("  VERIFY: Plan Guardian"))
    print()
    print("    Verifies implementation against PRD and spec drift.")
    print("    Computes alignment scores and triggers gates.")
    print()
    print(print_cyan("    Recommended:") + " plan-guardian (phd, opus)")
    print(print_magenta("  " + "─" * 118))
    print()

    # Agent Selection
    print(print_dim("─" * 120))
    print()
    print(print_bold("SELECT AGENTS"))
    print()

    # RED agent
    print(print_red("  RED: Test Strategy"))
    print(print_green("    [1]") + " test-strategist (recommended - from inventory)")
    print(print_dim("    [2]") + " specification-agent")
    print()

    red_choice = prompt_user("    Selection (default: 1): ").strip()
    red_choice = red_choice if red_choice else "1"
    red_agent = "test-strategist" if red_choice != "2" else "specification-agent"
    red_model = get_csv_model(red_agent, csv_path) if csv_path else "opus"
    print()

    # GREEN agent
    print(print_green("  GREEN: TDD Implementation"))
    print(print_green("    [1]") + " tdd-implementation-agent (recommended - from inventory)")
    print(print_dim("    [2]") + " specification-agent")
    print()

    green_choice = prompt_user("    Selection (default: 1): ").strip()
    green_choice = green_choice if green_choice else "1"
    green_agent = "tdd-implementation-agent" if green_choice != "2" else "specification-agent"
    green_model = get_csv_model(green_agent, csv_path) if csv_path else "opus"
    print()

    # REFACTOR agent
    print(print_cyan("  REFACTOR: Code Review"))
    print(print_green("    [1]") + " code-review-gate (recommended - from inventory)")
    print(print_dim("    [2]") + " plan-guardian")
    print()

    refactor_choice = prompt_user("    Selection (default: 1): ").strip()
    refactor_choice = refactor_choice if refactor_choice else "1"
    refactor_agent = "code-review-gate" if refactor_choice != "2" else "plan-guardian"
    refactor_model = get_csv_model(refactor_agent, csv_path) if csv_path else "opus"
    print()

    # VERIFY agent
    print(print_magenta("  VERIFY: Drift Monitor"))
    print(print_green("    [1]") + " plan-guardian (recommended - from inventory)")
    print(print_dim("    [2]") + " code-review-gate")
    print()

    verify_choice = prompt_user("    Selection (default: 1): ").strip()
    verify_choice = verify_choice if verify_choice else "1"
    verify_agent = "plan-guardian" if verify_choice != "2" else "code-review-gate"
    verify_model = get_csv_model(verify_agent, csv_path) if csv_path else "opus"
    print()

    # Optional: Expert Agents
    print(print_dim("─" * 120))
    print()
    print(print_bold("OPTIONAL: EXPERT AGENTS"))
    print()

    print(print_dim("  Based on project patterns, consider adding expert agents from inventory:"))
    print()

    if patterns["has_api"]:
        print(print_cyan("    [api]") + "      api-tester - API testing specialist")
    if patterns["has_db"]:
        print(print_cyan("    [db]") + "       database-optimizer - Database operations")
    if patterns["has_frontend"]:
        print(print_cyan("    [ui]") + "       frontend-developer - UI components")
    if patterns["has_async"]:
        print(print_cyan("    [async]") + "    debugger - Async debugging")

    print()
    print(print_dim("  Enter comma-separated list of specialists (or Enter to skip):"))
    specialist_input = prompt_user("    Specialists: ").strip()

    specialists = []
    if specialist_input:
        specialist_keys = [s.strip() for s in specialist_input.split(',')]
        for key in specialist_keys:
            mapping = {
                "api": "api-tester",
                "db": "database-optimizer",
                "ui": "frontend-developer",
                "async": "debugger"
            }
            specialists.append(mapping.get(key, key))

        print()
        print(print_green(f"  ✓ Added {len(specialists)} specialist(s): {', '.join(specialists)}"))
    print()

    # Selection Summary
    print(print_dim("─" * 120))
    print()
    print(print_bold("AGENT SELECTION SUMMARY") + " (from agent-inventory.csv)")
    print()

    print(print_red("    RED:") + f"       {red_agent} ({red_model})")
    print(print_green("    GREEN:") + f"     {green_agent} ({green_model})")
    print(print_cyan("    REFACTOR:") + f"  {refactor_agent} ({refactor_model})")
    print(print_magenta("    VERIFY:") + f"    {verify_agent} ({verify_model})")
    if specialists:
        print(print_dim("    Specialists:") + f" {', '.join(specialists)}")
    print()

    # Save agent selection
    agents_data = {
        "tdd_agents": {
            "red": {"name": red_agent, "model": red_model, "phase": "RED"},
            "green": {"name": green_agent, "model": green_model, "phase": "GREEN"},
            "refactor": {"name": refactor_agent, "model": refactor_model, "phase": "REFACTOR"},
            "verify": {"name": verify_agent, "model": verify_model, "phase": "VERIFY"}
        },
        "specialists": specialists,
        "source": "agent-inventory.csv",
        "selected_at": datetime.now().isoformat()
    }
    write_file(agents_file, json.dumps(agents_data, indent=2))

    print(print_green("✓ Agent Selection complete"))
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 503: Agent Selection")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
