"""
Task 703: Agent Selection

Present and select integration testing agents for Phase 7.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, print_blue, print_magenta, prompt_user, clear_input_buffer
)
from core.utils.file_ops import write_json


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
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
    print_dim("Select agents for integration testing.")
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # INTEGRATION WORKFLOW
    # ─────────────────────────────────────────────────────────────────────────

    print()
    print_bold("  - INTEGRATION WORKFLOW")
    print()

    print("  E2E Test Runner ────────┐")
    print_dim("      (test flows)        │")
    print("                          ├→  Acceptance Validator  →  Integration Reporter")
    print("  Performance Tester ─────┘      " + print_dim("(all criteria)") + "          " + print_dim("(consolidate)"))
    print_dim("      (benchmark NFRs)")
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # AVAILABLE AGENTS
    # ─────────────────────────────────────────────────────────────────────────

    print()
    print_bold("  - AVAILABLE AGENTS")
    print()

    # E2E Test Runner
    print_cyan("─" * 118)
    print_bold("E2E TEST RUNNER")
    print()
    print("  Executes end-to-end test suites across all user flows.")
    print("  Validates complete system behavior from input to output.")
    print_green("  Recommended: ") + "e2e-test-runner-phd (sonnet)"
    print_cyan("─" * 118)
    print()

    # Acceptance Validator
    print_magenta("─" * 118)
    print_bold("ACCEPTANCE VALIDATOR")
    print()
    print("  Validates each acceptance criterion from PRD.")
    print("  Maps requirements to test evidence.")
    print_green("  Recommended: ") + "acceptance-validator-phd (sonnet)"
    print_magenta("─" * 118)
    print()

    # Performance Tester
    print_yellow("─" * 118)
    print_bold("PERFORMANCE TESTER")
    print()
    print("  Benchmarks system against NFR targets.")
    print("  Measures response times, memory, throughput.")
    print_green("  Recommended: ") + "performance-tester-phd (haiku)"
    print_yellow("─" * 118)
    print()

    # Integration Reporter
    print_blue("─" * 118)
    print_bold("INTEGRATION REPORTER")
    print()
    print("  Generates comprehensive integration report.")
    print("  Consolidates results from all testing agents.")
    print_green("  Recommended: ") + "integration-reporter-phd (haiku)"
    print_blue("─" * 118)
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # AGENT SELECTION
    # ─────────────────────────────────────────────────────────────────────────

    print()
    print_bold("  - AGENT SELECTION")
    print()

    if uat_mode:
        # UAT mode: use defaults
        selected_agents = [
            "e2e-test-runner-phd:sonnet",
            "acceptance-validator-phd:sonnet",
            "performance-tester-phd:haiku",
            "integration-reporter-phd:haiku"
        ]
        print_yellow("UAT Mode: Using default agents")
        print()
    else:
        print_dim("Select agents for each role:")
        print()

        clear_input_buffer()
        selected_agents = []

        # E2E Test Runner selection
        print_cyan("E2E Test Runner:")
        print_green("  [1] ") + "e2e-test-runner-phd (sonnet) - Recommended"
        print_dim("  [2] ") + "e2e-test-runner (haiku) - Fast, standard"
        print_yellow("  [c] ") + "Custom agent"
        print()
        e2e_choice = prompt_user("Select (default: 1): ").strip() or "1"

        if e2e_choice.lower() == "c":
            custom_name = prompt_user("Custom agent name: ").strip()
            custom_model = prompt_user("Custom agent model (default: sonnet): ").strip() or "sonnet"
            selected_agents.append(f"{custom_name}:{custom_model}")
        elif e2e_choice == "2":
            selected_agents.append("e2e-test-runner:haiku")
        else:
            selected_agents.append("e2e-test-runner-phd:sonnet")
        print()

        # Acceptance Validator selection
        print_magenta("Acceptance Validator:")
        print_green("  [1] ") + "acceptance-validator-phd (sonnet) - Recommended"
        print_dim("  [2] ") + "acceptance-validator (haiku) - Fast, standard"
        print_yellow("  [c] ") + "Custom agent"
        print()
        accept_choice = prompt_user("Select (default: 1): ").strip() or "1"

        if accept_choice.lower() == "c":
            custom_name = prompt_user("Custom agent name: ").strip()
            custom_model = prompt_user("Custom agent model (default: sonnet): ").strip() or "sonnet"
            selected_agents.append(f"{custom_name}:{custom_model}")
        elif accept_choice == "2":
            selected_agents.append("acceptance-validator:haiku")
        else:
            selected_agents.append("acceptance-validator-phd:sonnet")
        print()

        # Performance Tester selection
        print_yellow("Performance Tester:")
        print_green("  [1] ") + "performance-tester-phd (haiku) - Recommended"
        print_dim("  [2] ") + "performance-tester-deep (sonnet) - Thorough"
        print_yellow("  [c] ") + "Custom agent"
        print()
        perf_choice = prompt_user("Select (default: 1): ").strip() or "1"

        if perf_choice.lower() == "c":
            custom_name = prompt_user("Custom agent name: ").strip()
            custom_model = prompt_user("Custom agent model (default: haiku): ").strip() or "haiku"
            selected_agents.append(f"{custom_name}:{custom_model}")
        elif perf_choice == "2":
            selected_agents.append("performance-tester-deep:sonnet")
        else:
            selected_agents.append("performance-tester-phd:haiku")
        print()

        # Integration Reporter selection
        print_blue("Integration Reporter:")
        print_green("  [1] ") + "integration-reporter-phd (haiku) - Recommended"
        print_dim("  [2] ") + "integration-reporter-detailed (sonnet) - Comprehensive"
        print_yellow("  [c] ") + "Custom agent"
        print()
        report_choice = prompt_user("Select (default: 1): ").strip() or "1"

        if report_choice.lower() == "c":
            custom_name = prompt_user("Custom agent name: ").strip()
            custom_model = prompt_user("Custom agent model (default: haiku): ").strip() or "haiku"
            selected_agents.append(f"{custom_name}:{custom_model}")
        elif report_choice == "2":
            selected_agents.append("integration-reporter-detailed:sonnet")
        else:
            selected_agents.append("integration-reporter-phd:haiku")
        print()

    # ─────────────────────────────────────────────────────────────────────────
    # SELECTION SUMMARY
    # ─────────────────────────────────────────────────────────────────────────

    print()
    print_bold("  - SELECTION SUMMARY")
    print()

    print_dim("─" * 118)
    print_bold("SELECTED AGENTS")
    print()
    for agent in selected_agents:
        name, model = agent.split(":", 1)
        print_green("  ✓ ") + f"{name} ({model})"
    print_dim("─" * 118)
    print()

    # Save agent selection
    agents_data = {
        "phase": 7,
        "agents": selected_agents,
        "selected_at": datetime.now().isoformat()
    }

    write_json(agents_file, agents_data)

    print_green("✓ Agent Selection complete")
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
