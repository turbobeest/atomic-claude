"""
Task 501: Entry & Initialization

Verify Phase 4 artifacts exist and prepare for TDD implementation.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, print_magenta, prompt_user
)
from core.utils.file_ops import ensure_dir, write_file


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 501: Entry & Initialization.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    phase4_closeout = atomic_root / ".outputs" / "4-specification" / "closeout.json"
    tasks_file = atomic_root / ".taskmaster" / "tasks" / "tasks.json"
    specs_dir = atomic_root / ".claude" / "specs"
    testing_dir = atomic_root / ".claude" / "testing"
    init_file = output_dir / "initialization.json"

    # Phase 5 Welcome Banner
    print()
    print_dim("━" * 120)
    print_cyan("  PHASE 05 - IMPLEMENTATION")
    print_dim("━" * 120)
    print_cyan("""
                                _______ ______  ______
                                   |    |     \ |     \\
                                   |    |_____/ |_____/

      _____ _______  _____         _______ _______ _______ __   _ _______ _______ _______ _____  _____  __   _
        |   |  |  | |_____] |      |______ |  |  | |______ | \  |    |    |_____|    |      |   |     | | \  |
      __|__ |  |  | |       |_____ |______ |  |  | |______ |  \_|    |    |     |    |    __|__ |_____| |  \_|
""")
    print_dim("━" * 120)
    print()
    print_dim("  Executing RED/GREEN/REFACTOR/VERIFY cycles for all tasks.")
    print()

    # UAT Mode Bypass
    if uat_mode:
        print()
        print_yellow("⚡ UAT Mode: Skipping Phase 4 verification, creating minimal initialization")
        print()

        ensure_dir(init_file.parent)

        init_data = {
            "phase4_verified": True,
            "tasks_with_tdd": 3,
            "total_subtasks": 12,
            "spec_count": 3,
            "mode": "uat",
            "initialized_at": datetime.now().isoformat()
        }
        write_file(init_file, json.dumps(init_data, indent=2))

        print_green("✓ Entry & Initialization complete (UAT mode)")
        return True

    # Phase 4 Verification
    print_dim("─" * 120)
    print()
    print_bold("PHASE 4 VERIFICATION")
    print()

    verification_passed = True

    # Check Phase 4 closeout
    if phase4_closeout.exists():
        with open(phase4_closeout) as f:
            closeout_data = json.load(f)
        phase4_status = closeout_data.get("status", "unknown")
        if phase4_status == "complete":
            print_green(f"✓ Phase 4 closeout verified")
        else:
            print_yellow(f"! Phase 4 closeout status: {phase4_status}")
    else:
        print_yellow("! Phase 4 closeout not found (continuing anyway)")

    # Check tasks.json has TDD subtasks
    tasks_with_tdd = 0
    total_tasks = 0
    if tasks_file.exists():
        with open(tasks_file) as f:
            tasks_data = json.load(f)
        tasks = tasks_data.get("tasks", [])
        total_tasks = len(tasks)
        tasks_with_tdd = sum(1 for task in tasks if len(task.get("subtasks", [])) >= 4)

        if tasks_with_tdd > 0:
            print_green(f"✓ TDD subtasks found ({tasks_with_tdd} / {total_tasks} tasks)")
        else:
            print_red("✗ No TDD subtasks found")
            verification_passed = False
    else:
        print_red("✗ tasks.json not found")
        verification_passed = False

    # Check OpenSpec files
    spec_count = 0
    if specs_dir.exists():
        spec_files = list(specs_dir.glob("spec-*.json"))
        spec_count = len(spec_files)
        if spec_count > 0:
            print_green(f"✓ OpenSpec files found ({spec_count} specs)")
        else:
            print_red("✗ No OpenSpec files found")
            verification_passed = False
    else:
        print_red("✗ Specs directory not found")
        verification_passed = False

    print()

    if not verification_passed:
        print_red("Phase 4 artifacts missing. Cannot proceed.")
        print()
        print_dim("Run Phase 4 (Specification) first to generate OpenSpecs and TDD subtasks.")
        print()
        return False

    # TDD Summary
    print_dim("─" * 120)
    print()
    print_bold("TDD SUMMARY")
    print()

    # Calculate total subtasks
    total_subtasks = 0
    if tasks_file.exists():
        with open(tasks_file) as f:
            tasks_data = json.load(f)
        for task in tasks_data.get("tasks", []):
            total_subtasks += len(task.get("subtasks", []))

    print(f"    Tasks with TDD:      {tasks_with_tdd}")
    print(f"    Total subtasks:      {total_subtasks}")
    print(f"    TDD cycles to run:   {tasks_with_tdd}")
    print()

    # Show TDD cycle structure
    print_dim("  Each task will go through:")
    print()
    print_red("    RED       → Write failing tests")
    print_green("    GREEN     → Minimal implementation")
    print_cyan("    REFACTOR  → Clean up code")
    print_magenta("    VERIFY    → Security scan")
    print()

    # Initialize Testing Directory
    print_dim("─" * 120)
    print()
    print_bold("INITIALIZE TESTING DIRECTORY")
    print()

    ensure_dir(testing_dir)
    print_green("✓ Testing directory initialized: .claude/testing/")
    print()

    # TDD Introduction
    print_dim("─" * 120)
    print()
    print_bold("TDD METHODOLOGY")
    print()
    print_dim("  Test-Driven Development ensures code quality through:")
    print()
    print("    ─────────────────────────────────────────────────────────────────")
    print()
    print_red("    RED  ────────►  ") + print_green("GREEN  ────────►  ") + print_cyan("REFACTOR  ────────►  ") + print_magenta("VERIFY")
    print()
    print("    Write tests    Implement      Clean up        Security")
    print("    (must FAIL)    (tests PASS)   (still PASS)    scan")
    print()
    print("    ─────────────────────────────────────────────────────────────────")
    print()
    print_bold("  Key Principles:")
    print()
    print("    1. Never write implementation code without a failing test")
    print("    2. Write only enough code to pass the test")
    print("    3. Refactor while keeping tests green")
    print("    4. Security scan before marking complete")
    print()

    prompt_user("  Press Enter to continue...")

    # Save initialization state
    ensure_dir(init_file.parent)

    init_data = {
        "phase4_verified": True,
        "tasks_with_tdd": tasks_with_tdd,
        "total_subtasks": total_subtasks,
        "spec_count": spec_count,
        "initialized_at": datetime.now().isoformat()
    }
    write_file(init_file, json.dumps(init_data, indent=2))

    print_green("✓ Entry & Initialization complete")
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 501: Entry & Initialization")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
