"""
Task 703: Agent Selection

Present and select integration testing agents for Phase 7.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_dim, print_blue, print_magenta, prompt_user, clear_input_buffer
)
from core.utils.file_ops import write_json


def _select_agent_for_role(
    role_name: str, color_fn, options: list, default_idx: int = 0
) -> str:
    """Select an agent for a given role interactively.

    Args:
        role_name: Display name for the role
        color_fn: Color function for display
        options: List of "name:model" strings
        default_idx: Index of the default option (0-based)

    Returns:
        Selected "name:model" string
    """
    print(color_fn(f"{role_name}:"))
    for i, opt in enumerate(options):
        prefix = print_green(f"  [{i + 1}] ") if i == default_idx else print_dim(f"  [{i + 1}] ")
        label = f"{opt} - Recommended" if i == default_idx else opt
        print(prefix + label)
    print(print_yellow("  [c] ") + "Custom agent")
    print()

    choice = prompt_user(f"Select (default: {default_idx + 1}): ").strip() or str(default_idx + 1)

    if choice.lower() == "c":
        custom_name = prompt_user("Custom agent name: ").strip()
        custom_model = prompt_user("Custom agent model (default: sonnet): ").strip() or "sonnet"
        return f"{custom_name}:{custom_model}"

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(options):
            return options[idx]
    except ValueError:
        pass

    return options[default_idx]


def _display_agent_roles() -> None:
    """Display available integration agent roles."""
    # E2E Test Runner
    print(print_cyan("-" * 118))
    print(print_bold("E2E TEST RUNNER"))
    print()
    print("  Executes end-to-end test suites across all user flows.")
    print("  Validates complete system behavior from input to output.")
    print(print_green("  Recommended: ") + "e2e-test-runner-phd (sonnet)")
    print(print_cyan("-" * 118))
    print()

    # Acceptance Validator
    print(print_magenta("-" * 118))
    print(print_bold("ACCEPTANCE VALIDATOR"))
    print()
    print("  Validates each acceptance criterion from PRD.")
    print("  Maps requirements to test evidence.")
    print(print_green("  Recommended: ") + "acceptance-validator-phd (sonnet)")
    print(print_magenta("-" * 118))
    print()

    # Performance Tester
    print(print_yellow("-" * 118))
    print(print_bold("PERFORMANCE TESTER"))
    print()
    print("  Benchmarks system against NFR targets.")
    print("  Measures response times, memory, throughput.")
    print(print_green("  Recommended: ") + "performance-tester-phd (haiku)")
    print(print_yellow("-" * 118))
    print()

    # Integration Reporter
    print(print_blue("-" * 118))
    print(print_bold("INTEGRATION REPORTER"))
    print()
    print("  Generates comprehensive integration report.")
    print("  Consolidates results from all testing agents.")
    print(print_green("  Recommended: ") + "integration-reporter-phd (haiku)")
    print(print_blue("-" * 118))
    print()


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None) -> bool:
    """
    Execute Task 703: Agent Selection.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    agents_file = output_dir / "integration-agents.json"

    print()
    print(print_dim("Select agents for integration testing."))
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # INTEGRATION WORKFLOW
    # ─────────────────────────────────────────────────────────────────────────

    print()
    print(print_bold("  - INTEGRATION WORKFLOW"))
    print()

    print("  E2E Test Runner ────────┐")
    print(print_dim("      (test flows)        │"))
    print("                          ├→  Acceptance Validator  →  Integration Reporter")
    print("  Performance Tester ─────┘      " + print_dim("(all criteria)") + "          " + print_dim("(consolidate)"))
    print(print_dim("      (benchmark NFRs)"))
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # AVAILABLE AGENTS
    # ─────────────────────────────────────────────────────────────────────────

    print()
    print(print_bold("  - AVAILABLE AGENTS"))
    print()

    _display_agent_roles()

    # ─────────────────────────────────────────────────────────────────────────
    # AGENT SELECTION
    # ─────────────────────────────────────────────────────────────────────────

    print()
    print(print_bold("  - AGENT SELECTION"))
    print()

    # PLACEHOLDER agent IDs -- validate against agent-manifest.json when available
    if uat_mode:
        # UAT mode: use defaults
        selected_agents = [
            "e2e-test-runner-phd:sonnet",
            "acceptance-validator-phd:sonnet",
            "performance-tester-phd:haiku",
            "integration-reporter-phd:haiku"
        ]
        print(print_yellow("UAT Mode: Using default agents"))
        print()
    else:
        print(print_dim("Select agents for each role:"))
        print()

        clear_input_buffer()
        selected_agents = []

        selected_agents.append(_select_agent_for_role(
            "E2E Test Runner", print_cyan,
            ["e2e-test-runner-phd:sonnet", "e2e-test-runner:haiku"],
            default_idx=0,
        ))
        print()

        selected_agents.append(_select_agent_for_role(
            "Acceptance Validator", print_magenta,
            ["acceptance-validator-phd:sonnet", "acceptance-validator:haiku"],
            default_idx=0,
        ))
        print()

        selected_agents.append(_select_agent_for_role(
            "Performance Tester", print_yellow,
            ["performance-tester-phd:haiku", "performance-tester-deep:sonnet"],
            default_idx=0,
        ))
        print()

        selected_agents.append(_select_agent_for_role(
            "Integration Reporter", print_blue,
            ["integration-reporter-phd:haiku", "integration-reporter-detailed:sonnet"],
            default_idx=0,
        ))
        print()

    # ─────────────────────────────────────────────────────────────────────────
    # SELECTION SUMMARY
    # ─────────────────────────────────────────────────────────────────────────

    print()
    print(print_bold("  - SELECTION SUMMARY"))
    print()

    print(print_dim("─" * 118))
    print(print_bold("SELECTED AGENTS"))
    print()
    for agent in selected_agents:
        parts = agent.split(":", 1)
        name = parts[0]
        model = parts[1] if len(parts) > 1 else "sonnet"
        print(print_green("  ✓ ") + f"{name} ({model})")
    print(print_dim("─" * 118))
    print()

    # Save agent selection
    agents_data = {
        "phase": 7,
        "agents": selected_agents,
        "selected_at": datetime.now(timezone.utc).isoformat()
    }

    write_json(agents_file, agents_data)

    print(print_green("✓ Agent Selection complete"))
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 703: Agent Selection")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
