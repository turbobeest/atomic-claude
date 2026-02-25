"""
Task 803: Agent Selection

Present and select deployment preparation agents.
"""

import sys
from pathlib import Path
from typing import List
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, print_magenta, print_blue, prompt_user
)
from core.utils.file_ops import write_json


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None) -> bool:
    """
    Execute Task 803: Agent Selection.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    agents_file = output_dir / "deployment-agents.json"

    print(print_bold("Agent Selection"))
    print()

    # UAT Mode Bypass
    if uat_mode:
        print(print_dim("  UAT Mode: Creating minimal valid output"))
        agents_data = {
            "agents": [
                "release-packager-phd:sonnet",
                "changelog-writer-phd:sonnet",
                "documentation-generator-phd:opus",
                "installation-guide-writer-phd:sonnet"
            ],
            "count": 4
        }
        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(agents_file, agents_data)
        print(print_green("✓ UAT bypass complete"))
        return True

    print()
    print(print_dim("  Select agents for deployment preparation."))
    print()

    # DEPLOYMENT PREP WORKFLOW
    print()
    print(print_bold("  - DEPLOYMENT PREP WORKFLOW"))
    print()

    print("    Release Packager ────────┐")
    print(print_dim("        (build artifacts)    │"))
    print("    Changelog Writer ────────┤")
    print(print_dim("        (version notes)      ├→  Deployment Approval"))
    print("    Documentation Gen ───────┤       (human gate)")
    print(print_dim("        (user guides)        │"))
    print("    Install Guide Writer ────┘")
    print(print_dim("        (setup instructions)"))
    print()

    # AVAILABLE AGENTS
    print()
    print(print_bold("  - AVAILABLE AGENTS"))
    print()

    _display_agent_options()

    # AGENT SELECTION
    print()
    print(print_bold("  - AGENT SELECTION"))
    print()

    print(print_dim("  Select agents for each role:"))
    print()

    selected_agents = []

    # Release Packager
    selected_agents.append(_select_agent(
        "Release Packager",
        [
            ("1", "release-packager-phd:sonnet", "Recommended"),
            ("2", "release-packager:haiku", "Fast, standard")
        ],
        print_cyan
    ))

    # Changelog Writer
    selected_agents.append(_select_agent(
        "Changelog Writer",
        [
            ("1", "changelog-writer-phd:sonnet", "Recommended"),
            ("2", "changelog-writer:haiku", "Fast, standard")
        ],
        print_magenta
    ))

    # Documentation Generator
    selected_agents.append(_select_agent(
        "Documentation Generator",
        [
            ("1", "documentation-generator-phd:opus", "Recommended"),
            ("2", "documentation-generator:sonnet", "Standard")
        ],
        print_yellow
    ))

    # Installation Guide Writer
    selected_agents.append(_select_agent(
        "Installation Guide Writer",
        [
            ("1", "installation-guide-writer-phd:sonnet", "Recommended"),
            ("2", "installation-guide-writer:haiku", "Fast, standard")
        ],
        print_blue
    ))

    # SELECTION SUMMARY
    print()
    print(print_bold("  - SELECTION SUMMARY"))
    print()

    print("  " + "─" * 110)
    print(print_bold("  SELECTED AGENTS"))
    print()
    # PLACEHOLDER: Agent IDs should be validated against agent-manifest.json
    for agent in selected_agents:
        parts = agent.rsplit(":", 1)
        agent_name = parts[0]
        model = parts[1] if len(parts) > 1 else "sonnet"
        print(f"    ✓ {agent_name} ({model})")
    print("  " + "─" * 110)
    print()

    # Save agent selection
    agents_data = {
        "phase": 8,
        "agents": selected_agents,
        "selected_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(agents_file, agents_data)

    print(print_green("✓ Agent Selection complete"))

    return True


def _display_agent_options():
    """Display available agent options."""
    # Release Packager
    print(print_cyan("  " + "─" * 110))
    print(print_bold("  RELEASE PACKAGER"))
    print()
    print("    Prepares release package (setup.py, pyproject.toml, etc.).")
    print("    Builds distribution artifacts for selected channels.")
    print("    Recommended: release-packager-phd (sonnet)")
    print(print_cyan("  " + "─" * 110))
    print()

    # Changelog Writer
    print(print_magenta("  " + "─" * 110))
    print(print_bold("  CHANGELOG WRITER"))
    print()
    print("    Generates changelog from commits and PRD.")
    print("    Follows Keep a Changelog format.")
    print("    Recommended: changelog-writer-phd (sonnet)")
    print(print_magenta("  " + "─" * 110))
    print()

    # Documentation Generator
    print(print_yellow("  " + "─" * 110))
    print(print_bold("  DOCUMENTATION GENERATOR"))
    print()
    print("    Generates comprehensive user documentation.")
    print("    Creates API references and usage guides.")
    print("    Recommended: documentation-generator-phd (opus)")
    print(print_yellow("  " + "─" * 110))
    print()

    # Installation Guide Writer
    print(print_blue("  " + "─" * 110))
    print(print_bold("  INSTALLATION GUIDE WRITER"))
    print()
    print("    Creates installation and quick-start guide.")
    print("    Platform-specific instructions and troubleshooting.")
    print("    Recommended: installation-guide-writer-phd (sonnet)")
    print(print_blue("  " + "─" * 110))
    print()


def _select_agent(role_name: str, options: List[tuple], color_func) -> str:
    """Select an agent for a specific role."""
    print(color_func(f"  {role_name}:"))
    print()

    for choice, agent, desc in options:
        print(f"    [{choice}] {agent} - {desc}")
    print("    [c] Custom agent")
    print()

    selection = prompt_user("  Select (default: 1): ") or "1"

    if selection.lower() == "c":
        custom_name = prompt_user("  Custom agent name: ")
        custom_model = prompt_user("  Custom agent model (default: sonnet): ") or "sonnet"
        print()
        return f"{custom_name}:{custom_model}"

    # Find matching option
    for choice, agent, _ in options:
        if selection == choice:
            print()
            return agent

    # Default to first option
    print()
    return options[0][1]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 803: Agent Selection")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
