"""
Task 204: Agent Selection

Selects agents for PRD authoring and validation.

Core agents:
  - requirements-engineer (opus) - Synthesize requirements
  - prd-writer (opus) - Author PRD document
  - prd-validator (sonnet) - Validate completeness
"""

import logging
import sys
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_dim, print_magenta, prompt_user, clear_input_buffer
)
from core.utils.file_ops import write_file


# Core PRD agents (always included)
CORE_AGENTS = [
    "requirements-engineer",
    "prd-writer",
    "prd-validator"
]

# Additional suggested agents
ADDITIONAL_AGENTS = {
    "1": {
        "name": "security-requirements-analyst",
        "description": "For projects with security requirements"
    },
    "2": {
        "name": "api-requirements-engineer",
        "description": "For API-heavy projects"
    },
    "3": {
        "name": "ux-requirements-analyst",
        "description": "For user-facing applications"
    }
}


def execute(atomic_root: Path, output_dir: Path, mem=None, graph=None) -> bool:
    """
    Execute Task 204: Agent Selection.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        graph: Optional GraphManager instance for knowledge graph operations

    Returns:
        True if task completed successfully, False otherwise
    """
    agents_file = output_dir / "selected-agents.json"

    print()
    print(print_dim("  ┌─────────────────────────────────────────────────────────┐"))
    print(print_dim("  │ Select agents for PRD authoring and validation.        │"))
    print(print_dim("  │                                                         │"))
    print(print_dim("  │ Tip: Custom agents can be created in the agent repo's  │"))
    print(print_dim("  │ custom/ directory for project-specific needs.          │"))
    print(print_dim("  └─────────────────────────────────────────────────────────┘"))
    print()

    # Display core agents
    display_core_agents()

    print()

    # Display suggested additional agents
    display_additional_agents()

    print()

    # Agent selection
    selected_agents, additional = select_agents()

    print()

    # Save selection
    save_agent_selection(agents_file, selected_agents, additional)

    print(print_green("✓ Agent selection complete"))
    return True


def display_core_agents() -> None:
    """Display core PRD agents."""
    print(print_cyan("╔═══════════════════════════════════════════════════════════╗"))
    print(print_cyan("║ " + print_bold("CORE PRD AGENTS") + "                                           ║"))
    print(print_cyan("╚═══════════════════════════════════════════════════════════╝"))
    print()

    print("  " + print_bold("Authoring Agents:"))
    print("    " + print_green("requirements-engineer") + " (opus)")
    print("      " + print_dim("Synthesizes requirements into structured format"))
    print("      " + print_dim("Uses RFC 2119 + EARS syntax"))
    print()
    print("    " + print_green("prd-writer") + " (opus)")
    print("      " + print_dim("Authors formal PRD using 15-section template"))
    print()
    print("  " + print_bold("Validation Agents:"))
    print("    " + print_green("prd-validator") + " (sonnet)")
    print("      " + print_dim("Validates completeness, clarity, consistency"))
    print("      " + print_dim("Generates Gherkin scenarios"))


def display_additional_agents() -> None:
    """Display suggested additional agents."""
    print(print_cyan("╔═══════════════════════════════════════════════════════════╗"))
    print(print_cyan("║ " + print_bold("SUGGESTED ADDITIONAL AGENTS") + "                               ║"))
    print(print_cyan("╚═══════════════════════════════════════════════════════════╝"))
    print()

    print(print_dim("  Based on your project, consider adding:"))
    print()

    for num, agent_info in ADDITIONAL_AGENTS.items():
        print("    " + print_yellow(agent_info["name"]) + " (sonnet)")
        print("      " + print_dim(agent_info["description"]))
        print()


def select_agents() -> tuple:
    """
    Select agents for PRD phase.

    Returns:
        Tuple of (selected_agents_list, additional_agents_list)
    """
    print(print_dim("━" * 60))
    print()
    print(print_cyan("  How would you like to proceed?"))
    print()
    print("    " + print_green("[approve]") + "   Use core agents only (recommended)")
    print("    " + print_yellow("[add]") + "       Add suggested agents")
    print("    " + print_cyan("[custom]") + "    Specify custom agent selection")
    print("    " + print_magenta("[list]") + "      Browse available agents")
    print()

    clear_input_buffer()
    agent_choice = prompt_user("  Choice (default: approve): ").strip().lower() or "approve"

    selected_agents = list(CORE_AGENTS)
    additional_agents = []

    if agent_choice == "add":
        print()
        print(print_dim("  Select additional agents (space-separated numbers):"))
        print("    1. security-requirements-analyst")
        print("    2. api-requirements-engineer")
        print("    3. ux-requirements-analyst")
        print()
        add_selection = prompt_user("  > ").strip()

        for num in add_selection.split():
            if num in ADDITIONAL_AGENTS:
                agent_name = ADDITIONAL_AGENTS[num]["name"]
                additional_agents.append(agent_name)
                selected_agents.append(agent_name)

    elif agent_choice == "custom":
        print()
        print(print_dim("  Enter agent names (one per line, empty to finish):"))
        selected_agents = []
        while True:
            agent_name = prompt_user("    > ").strip()
            if not agent_name:
                break
            selected_agents.append(agent_name)

        # Ensure at least core agents
        if not selected_agents:
            selected_agents = list(CORE_AGENTS)

    elif agent_choice == "list":
        list_available_agents()
        print()
        prompt_user("  Press Enter to continue with core agents...")

    # Remove duplicates while preserving order
    seen = set()
    selected_agents = [x for x in selected_agents if not (x in seen or seen.add(x))]

    print()
    print("  " + print_green("✓") + " Selected agents:")
    for agent in selected_agents:
        print(f"    • {agent}")

    return selected_agents, additional_agents


def list_available_agents() -> None:
    """List available agents from repository."""
    print()
    print(print_cyan("╔═══════════════════════════════════════════════════════════╗"))
    print(print_cyan("║ " + print_bold("AVAILABLE AGENTS") + "                                          ║"))
    print(print_cyan("╚═══════════════════════════════════════════════════════════╝"))
    print()

    # Try to find agent repository
    # NOTE: Uses Path.cwd() because this function has no access to atomic_root.
    # The execute() caller could pass it, but for a display-only helper the
    # current heuristic is acceptable.
    agent_repo = Path.cwd() / "agents"
    if not agent_repo.exists():
        agent_repo = Path.cwd().parent / "agents"
    if not agent_repo.exists():
        agent_repo = Path.cwd() / ".." / "atomic-claude" / "agents"

    # Common agent list shown in both branches
    builtin_agents = [
        "requirements-engineer",
        "prd-writer",
        "prd-validator",
        "security-requirements-analyst",
        "api-requirements-engineer",
    ]

    print(print_dim("  Using built-in agents (external repository not configured)"))
    print()
    print("  " + print_bold("PRD-related built-in agents:"))
    for agent_name in builtin_agents:
        print(f"    • {agent_name}")

    if agent_repo.exists():
        print()
        # List pipeline agents if directory exists
        pipeline_dir = agent_repo / "pipeline-agents"
        if pipeline_dir.exists():
            print("  " + print_bold("Pipeline Agents:"))
            try:
                agent_files = list(pipeline_dir.glob("*.md"))
                for agent_file in sorted(agent_files)[:20]:
                    print(f"    • {agent_file.stem}")
            except Exception as e:
                print(print_yellow(f"    ⚠ Error reading pipeline agents: {e}"))
            print()


def save_agent_selection(
    agents_file: Path,
    selected_agents: List[str],
    additional_agents: List[str]
) -> None:
    """
    Save agent selection.

    Args:
        agents_file: Path to agents file
        selected_agents: List of selected agent names
        additional_agents: List of additional agent names
    """
    agents_data = {
        "phase": 2,
        "phase_name": "PRD",
        "selected": selected_agents,
        "core": CORE_AGENTS,
        "additional": additional_agents,
        "selected_at": datetime.now(timezone.utc).isoformat()
    }

    write_file(agents_file, json.dumps(agents_data, indent=2))
    print()
    print(print_dim(f"  Agent selection saved: {agents_file}"))


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 204: Agent Selection")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir)
    sys.exit(0 if success else 1)
