"""
Task 401: Entry & Initialization

Verifies Phase 3 artifacts exist and initializes specification directory.
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user, clear_input_buffer
)
from core.utils.file_ops import ensure_dir, read_file, write_file


PHASE_BANNER = r"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PHASE 04 - SPECIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
       _______  _____  _______ __   _ _______ _____  _______  _______
       |     | |_____] |______ | \  | |______ |_____] |______ |
       |_____| |       |______ |  \_| ______| |       |______ |_____

 _______ _____  _______ _______ _____  _______ _____  _______ _______ _____  _____  __   _
 |______ |_____] |______ |         |   |______   |   |       |_____|   |   |     | | \  |
 ______| |       |______ |_____  __|__ |       __|__ |_____  |     |   |   |_____| |  \_|

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Verifying Phase 3 artifacts and preparing for OpenSpec generation.
"""


def execute(atomic_root: Path, output_dir: Path, mem=None, graph=None) -> bool:
    """
    Execute Task 401: Entry & Initialization.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        graph: Optional GraphManager instance for knowledge graph operations

    Returns:
        True if task completed successfully, False otherwise
    """
    project_root = atomic_root.parent
    tasks_file = project_root / ".taskmaster" / "tasks" / "tasks.json"
    packages_file = project_root / ".taskmaster" / "reports" / "work-packages.json"
    # OpenSpec files: use .openspec/ (current), create if needed
    specs_dir = project_root / ".openspec"
    init_file = output_dir / "initialization.json"

    # Display phase banner
    print(PHASE_BANNER)

    # Phase 3 Verification
    print(print_dim("─" * 109))
    print()
    print(print_bold("PHASE 3 VERIFICATION"))
    print()

    verification_passed = True

    # Check Phase 3 closeout
    phase3_closeout = project_root / ".claude" / "closeout" / "phase-03-closeout.json"
    if phase3_closeout.exists():
        try:
            closeout_data = json.loads(read_file(phase3_closeout))
            status = closeout_data.get("status", "unknown")
            if status == "complete" or "tasks_completed" in closeout_data:
                print(print_green("  ✓ Phase 3 closeout verified"))
            else:
                print(print_yellow(f"  ! Phase 3 closeout status: {status}"))
        except Exception as e:
            print(print_yellow(f"  ! Could not parse Phase 3 closeout: {e}"))
    else:
        print(print_yellow("  ! Phase 3 closeout not found (continuing anyway)"))

    # Check tasks.json
    if tasks_file.exists():
        try:
            tasks_data = json.loads(read_file(tasks_file))
            task_count = len(tasks_data.get("tasks", []))
            if task_count > 0:
                print(print_green(f"  ✓ tasks.json found ({task_count} tasks)"))
            else:
                print(print_red("  ✗ tasks.json is empty"))
                verification_passed = False
        except Exception as e:
            print(print_red(f"  ✗ tasks.json is invalid: {e}"))
            verification_passed = False
    else:
        print(print_red("  ✗ tasks.json not found"))
        verification_passed = False

    # Check work packages
    if packages_file.exists():
        try:
            packages_data = json.loads(read_file(packages_file))
            pkg_count = len(packages_data.get("packages", []))
            print(print_green(f"  ✓ work-packages.json found ({pkg_count} packages)"))
        except Exception as e:
            logger.debug("Could not parse work-packages.json: %s", e)
            print(print_yellow("  ! work-packages.json found but invalid (optional)"))
    else:
        print(print_yellow("  ! work-packages.json not found (optional)"))

    print()

    if not verification_passed:
        print(print_red("  Phase 3 artifacts missing. Cannot proceed."))
        print()
        print(print_dim("  Run Phase 3 (Tasking) first to generate tasks.json"))
        print()
        return False

    # Task Summary
    print(print_dim("─" * 109))
    print()
    print(print_bold("TASK SUMMARY"))
    print()

    tasks_data = json.loads(read_file(tasks_file))
    tasks = tasks_data.get("tasks", [])

    high_priority = len([t for t in tasks if t.get("priority") == "high"])
    medium_priority = len([t for t in tasks if t.get("priority") == "medium"])
    low_priority = len([t for t in tasks if t.get("priority") == "low"])

    print(f"    Total tasks:     {task_count}")
    print(f"    High priority:   {high_priority}")
    print(f"    Medium priority: {medium_priority}")
    print(f"    Low priority:    {low_priority}")
    print()

    # Show first few tasks
    print(print_dim("  First 5 tasks:"))
    for i, task in enumerate(tasks[:5]):
        task_id = task.get("id", i+1)
        task_title = task.get("title", "Untitled")
        print(f"    [{task_id}] {task_title}")
    if len(tasks) > 5:
        print(print_dim(f"    ... and {len(tasks) - 5} more"))
    print()

    # Initialize Spec Directory
    print(print_dim("─" * 109))
    print()
    print(print_bold("INITIALIZE SPEC DIRECTORY"))
    print()

    ensure_dir(specs_dir)

    # Check for existing specs
    existing_specs = list(specs_dir.glob("spec-*.json"))
    existing_count = len(existing_specs)

    if existing_count > 0:
        print(print_yellow(f"  ! Found {existing_count} existing spec files"))
        print()
        print(print_cyan("Options:"))
        print()
        print(print_green("  [keep]     Keep existing specs, generate missing"))
        print(print_yellow("  [replace]  Replace all specs"))
        print(print_red("  [abort]    Abort and review manually"))
        print()

        clear_input_buffer()
        spec_choice = prompt_user("  Choice (default: keep): ").strip().lower() or "keep"

        if spec_choice == "replace":
            for spec_file in existing_specs:
                spec_file.unlink()
            print(print_green("  ✓ Cleared existing specs"))
        elif spec_choice == "abort":
            print(print_red("✗ Aborted by user"))
            return False
        else:
            print(print_green("  ✓ Keeping existing specs"))
    else:
        print(print_green("  ✓ Spec directory initialized: .openspec/"))
    print()

    # OpenSpec Introduction
    print(print_dim("─" * 109))
    print()
    print(print_bold("WHAT IS OPENSPEC?"))
    print()
    print(print_dim("  OpenSpec expands each task into a detailed specification containing:"))
    print()
    print(print_cyan("    1. Test Strategy     - Unit tests, integration tests, Gherkin scenarios"))
    print(print_cyan("    2. Interface Contracts - Inputs, outputs, error conditions"))
    print(print_cyan("    3. Edge Cases        - Boundary conditions, error handling"))
    print(print_cyan("    4. Security Requirements - Auth, validation, data protection"))
    print()
    print(print_dim("  Then it creates 4 TDD subtasks for each task:"))
    print()
    print(print_red("    RED       → Write failing tests (tests exist and FAIL)"))
    print(print_green("    GREEN     → Minimal implementation (tests PASS)"))
    print(print_cyan("    REFACTOR  → Clean up code (linting passes, tests still pass)"))
    print("\033[35m    VERIFY    → Security scan (no critical issues)\033[0m")  # Magenta
    print()
    print(print_dim("  Each subtask depends on the previous: RED→GREEN→REFACTOR→VERIFY"))
    print()

    prompt_user("  Press Enter to continue...")

    # Save initialization state
    ensure_dir(init_file.parent)

    init_data = {
        "phase3_verified": True,
        "task_count": task_count,
        "priority_breakdown": {
            "high": high_priority,
            "medium": medium_priority,
            "low": low_priority
        },
        "existing_specs": existing_count,
        "initialized_at": datetime.now(timezone.utc).isoformat()
    }

    write_file(init_file, json.dumps(init_data, indent=2))

    print(print_green("✓ Entry & Initialization complete"))

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 401: Entry & Initialization")
    parser.add_argument('--atomic-root', type=Path, required=True,
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir)
    sys.exit(0 if success else 1)
