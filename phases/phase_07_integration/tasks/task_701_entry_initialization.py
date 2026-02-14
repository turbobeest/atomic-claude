"""
Task 701: Entry & Initialization

Validate prerequisites and present phase objectives for Phase 7 (Integration).

Prerequisites checked:
  - Phase 6 closeout exists and is complete
  - Review artifacts present
  - Project configuration exists
  - Testing artifacts present (optional)
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user
)
from core.utils.file_ops import read_json


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 701: Entry & Initialization.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    closeout_file = atomic_root / ".outputs" / "6-code-review" / "closeout.json"
    config_file = atomic_root / ".outputs" / "0-setup" / "project-config.json"

    print()
    print(print_dim("━" * 118))
    print(print_cyan("  PHASE 07 - INTEGRATION"))
    print(print_dim("━" * 118))
    print()

    print(print_bold("Entry & Initialization"))
    print()
    print(print_dim("  Validating prerequisites for Integration phase."))
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # PREREQUISITE VALIDATION
    # ─────────────────────────────────────────────────────────────────────────

    print()
    print(print_bold("  - PREREQUISITE VALIDATION"))
    print()

    all_valid = True

    # Check Phase 6 closeout
    if closeout_file.exists():
        closeout_data = read_json(closeout_file)
        phase_6_status = closeout_data.get("status", "unknown")
        if phase_6_status == "complete":
            print(print_green("  [CRIT] ✓ Phase 6 (Code Review) complete"))
        else:
            print(print_red(f"  [CRIT] ✗ Phase 6 not complete (status: {phase_6_status})"))
            all_valid = False
    else:
        print(print_red("  [CRIT] ✗ Phase 6 closeout not found"))
        all_valid = False

    # Check for review artifacts
    review_dir = atomic_root / ".claude" / "reviews"
    if review_dir.exists():
        print(print_green("  [BLCK] ✓ Review artifacts present"))
    else:
        print(print_yellow("  [BLCK] ! Review artifacts not found"))

    # Check project config
    if config_file.exists():
        print(print_green("  [PASS] ✓ Project configuration found"))
    else:
        print(print_yellow("  [PASS] ! Project configuration not found"))

    # Check for test artifacts from implementation
    testing_dir = atomic_root / ".claude" / "testing"
    if testing_dir.exists():
        print(print_green("  [PASS] ✓ Testing artifacts present"))
    else:
        print(print_yellow("  [PASS] ! Testing artifacts not found"))

    print()

    if not all_valid:
        print(print_yellow("⚠  Prerequisites not met - cannot proceed"))
        return False

    # ─────────────────────────────────────────────────────────────────────────
    # PHASE OBJECTIVES
    # ─────────────────────────────────────────────────────────────────────────

    print()
    print(print_bold("  - PHASE OBJECTIVES"))
    print()

    print(print_dim("  In this phase, we will:"))
    print()
    print(print_cyan("    1.") + " Integrate all components end-to-end")
    print(print_cyan("    2.") + " Run full E2E test suite")
    print(print_cyan("    3.") + " Validate all acceptance criteria from PRD")
    print(print_cyan("    4.") + " Performance testing against NFRs")
    print(print_cyan("    5.") + " Generate comprehensive integration report")
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # INTEGRATION PROCESS
    # ─────────────────────────────────────────────────────────────────────────

    print()
    print(print_bold("  - INTEGRATION PROCESS"))
    print()

    print(print_dim("  Integration follows a validation-first approach:"))
    print()
    print("    E2E Testing  →  Acceptance  →  Performance  →  Approval")
    print(print_dim("       (flows)       (criteria)    (benchmarks)     (gate)"))
    print()

    if not uat_mode:
        prompt_user("  Press Enter to continue...")
    print()

    print(print_green("✓ Entry & Initialization complete"))
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 701: Entry & Initialization")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
