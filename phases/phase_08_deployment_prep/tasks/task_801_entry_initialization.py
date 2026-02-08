"""
Task 801: Entry & Initialization

Validate prerequisites and present phase objectives.
"""

import sys
import json
from pathlib import Path
from typing import Optional

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user
)
from core.utils.file_ops import read_json


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 801: Entry & Initialization.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    closeout_file = _find_closeout(atomic_root, "7-integration")
    integration_dir = atomic_root / ".claude" / "integration"
    config_file = atomic_root / ".outputs" / "0-setup" / "project-config.json"

    print()
    print_dim("━" * 110)
    print_cyan("  PHASE 08 - DEPLOYMENT PREP")
    print_dim("━" * 110)
    print()

    print_bold("Entry & Initialization")
    print()

    # UAT Mode Bypass
    if uat_mode:
        print_dim("  UAT Mode: Skipping interactive validation")
        print_green("✓ UAT bypass complete")
        return True

    print_dim("  Validating prerequisites for Deployment Prep phase.")
    print()

    # PREREQUISITE VALIDATION
    print()
    print_bold("  - PREREQUISITE VALIDATION")
    print()

    all_valid = True

    # Check Phase 7 closeout
    if closeout_file and closeout_file.exists():
        try:
            closeout_data = read_json(closeout_file)
            phase_7_status = closeout_data.get("status", "unknown")
            if phase_7_status == "complete":
                print_green(f"  [CRIT] ✓ Phase 7 (Integration) complete")
            else:
                print_red(f"  [CRIT] ✗ Phase 7 not complete (status: {phase_7_status})")
                all_valid = False
        except Exception as e:
            print_red(f"  [CRIT] ✗ Phase 7 closeout invalid: {e}")
            all_valid = False
    else:
        print_red("  [CRIT] ✗ Phase 7 closeout not found")
        all_valid = False

    # Check integration report
    integration_report = integration_dir / "integration-report.json"
    if integration_report.exists():
        print_green("  [BLCK] ✓ Integration report present")
    else:
        print_yellow("  [BLCK] ! Integration report not found")

    # Check project config
    if config_file.exists():
        print_green("  [PASS] ✓ Project configuration found")
    else:
        print_yellow("  [PASS] ! Project configuration not found")

    print()

    if not all_valid:
        print_yellow("⚠  Prerequisites not met - cannot proceed")
        return False

    # PHASE OBJECTIVES
    print()
    print_bold("  - PHASE OBJECTIVES")
    print()

    print_dim("  In this phase, we will:")
    print()
    print_cyan("    1. ") + "Prepare deployment artifacts"
    print_cyan("    2. ") + "Generate release documentation"
    print_cyan("    3. ") + "Create installation guides"
    print_cyan("    4. ") + "Prepare changelog"
    print_cyan("    5. ") + "Ready for Release phase"
    print()

    # DEPLOYMENT PREP PROCESS
    print()
    print_bold("  - DEPLOYMENT PREP PROCESS")
    print()

    print_dim("  Preparation follows a parallel workflow:")
    print()
    print("    Packaging  →  Changelog  →  Documentation  →  Approval")
    print_dim("      (build)      (version)       (guides)        (gate)")
    print()

    if not uat_mode:
        prompt_user("  Press Enter to continue...")
        print()

    print_green("✓ Entry & Initialization complete")
    return True


def _find_closeout(atomic_root: Path, phase_name: str) -> Optional[Path]:
    """Find closeout file for a phase."""
    closeout_dir = atomic_root / ".outputs" / phase_name
    if closeout_dir.exists():
        closeout_file = closeout_dir / "closeout.json"
        if closeout_file.exists():
            return closeout_file
    return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 801: Entry & Initialization")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
