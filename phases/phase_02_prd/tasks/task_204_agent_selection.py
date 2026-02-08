"""
Task 204: Agent Selection

Selects agents for PRD authoring and validation.

Core agents:
  - requirements-engineer (opus) - Synthesize requirements
  - prd-writer (opus) - Author PRD document
  - prd-validator (sonnet) - Validate completeness
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.config import Config
from core.state import StateManager
from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, print_magenta, print_blue, prompt_user, clear_input_buffer
)
from core.utils.file_ops import ensure_dir, read_file, write_file


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


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 204: Agent Selection.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    config_file = output_dir.parent / "0-setup" / "project-config.json"
    agents_file = output_dir / "selected-agents.json"

    print()
    print_dim("  ┌─────────────────────────────────────────────────────────┐")
    print_dim("  │ Select agents for PRD authoring and validation.        │")
    print_dim("  │                                                         │")
    print_dim("  │ Tip: Custom agents can be created in the agent repo's  │")
    print_dim("  │ custom/ directory for project-specific needs.          │")
    print_dim("  └─────────────────────────────────────────────────────────┘")
    print()

    # Display core agents
    display_core_agents()

    print()

    # Display suggested additional agents
    display_additional_agents()

    print()

    # Agent selection
    selected_agents, additional = select_agents(uat_mode)

    print()

    # Save selection
    save_agent_selection(agents_file, selected_agents, additional)

    print_green("✓ Agent selection complete")
    return True


def display_core_agents() -> None:
    """Display core PRD agents."""
    print_cyan("╔═══════════════════════════════════════════════════════════╗")
    print_cyan("║ " + print_bold("CORE PRD AGENTS") + "                                           ║")
    print_cyan("╚═══════════════════════════════════════════════════════════╝")
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
    print_cyan("╔═══════════════════════════════════════════════════════════╗")
    print_cyan("║ " + print_bold("SUGGESTED ADDITIONAL AGENTS") + "                               ║")
    print_cyan("╚═══════════════════════════════════════════════════════════╝")
    print()

    print_dim("  Based on your project, consider adding:")
    print()

    for num, agent_info in ADDITIONAL_AGENTS.items():
        print("    " + print_yellow(agent_info["name"]) + " (sonnet)")
        print("      " + print_dim(agent_info["description"]))
        print()


def select_agents(uat_mode: bool) -> tuple:
    """
    Select agents for PRD phase.

    Args:
        uat_mode: If True, use defaults

    Returns:
        Tuple of (selected_agents_list, additional_agents_list)
    """
    print_dim("━" * 60)
    print()
    print_cyan("  How would you like to proceed?")
    print()
    print("    " + print_green("[approve]") + "   Use core agents only (recommended)")
    print("    " + print_yellow("[add]") + "       Add suggested agents")
    print("    " + print_cyan("[custom]") + "    Specify custom agent selection")
    print("    " + print_magenta("[list]") + "      Browse available agents")
    print()

    if uat_mode:
        agent_choice = "approve"
        print_dim(f"  UAT mode: Using '{agent_choice}'")
    else:
        clear_input_buffer()
        agent_choice = prompt_user("  Choice (default: approve): ").strip().lower() or "approve"

    selected_agents = list(CORE_AGENTS)
    additional_agents = []

    if agent_choice == "add":
        if uat_mode:
            # Don't add any in UAT mode
            pass
        else:
            print()
            print_dim("  Select additional agents (space-separated numbers):")
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
        if uat_mode:
            # Use core agents in UAT mode
            pass
        else:
            print()
            print_dim("  Enter agent names (one per line, empty to finish):")
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
        if not uat_mode:
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
    print_cyan("╔═══════════════════════════════════════════════════════════╗")
    print_cyan("║ " + print_bold("AVAILABLE AGENTS") + "                                          ║")
    print_cyan("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Try to find agent repository
    agent_repo = Path.cwd() / "agents"
    if not agent_repo.exists():
        agent_repo = Path.cwd().parent / "agents"
    if not agent_repo.exists():
        agent_repo = Path.cwd() / ".." / "atomic-claude" / "agents"

    if agent_repo.exists():
        print_dim("  Using built-in agents (external repository not configured)")
        print()
        print("  " + print_bold("PRD-related built-in agents:"))
        print("    • requirements-engineer")
        print("    • prd-writer")
        print("    • prd-validator")
        print("    • security-requirements-analyst")
        print("    • api-requirements-engineer")
        print()

        # List pipeline agents if directory exists
        pipeline_dir = agent_repo / "pipeline-agents"
        if pipeline_dir.exists():
            print("  " + print_bold("Pipeline Agents:"))
            try:
                agent_files = list(pipeline_dir.glob("*.md"))
                for agent_file in sorted(agent_files)[:20]:
                    agent_name = agent_file.stem
                    print(f"    • {agent_name}")
            except Exception as e:
                print_yellow(f"    ⚠ Error reading pipeline agents: {e}")
            print()
    else:
        print_dim("  Using built-in agents (external repository not configured)")
        print()
        print("  " + print_bold("PRD-related built-in agents:"))
        print("    • requirements-engineer")
        print("    • prd-writer")
        print("    • prd-validator")
        print("    • security-requirements-analyst")
        print("    • api-requirements-engineer")


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
        "selected_at": datetime.now().isoformat()
    }

    write_file(agents_file, json.dumps(agents_data, indent=2))
    print()
    print_dim(f"  Agent selection saved: {agents_file}")


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 204: Agent Selection")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
