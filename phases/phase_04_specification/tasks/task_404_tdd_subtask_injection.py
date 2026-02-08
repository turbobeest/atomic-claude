"""
Task 404: TDD Subtask Injection

Write RED/GREEN/REFACTOR/VERIFY subtasks into tasks.json.
"""

import json
import sys
import shutil
from pathlib import Path
from typing import Dict, List
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user, clear_input_buffer
)
from core.utils.file_ops import ensure_dir, read_file, write_file


TDD_CYCLE_BANNER = """┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   RED  ────────►  GREEN  ────────►  REFACTOR  ────────►  VERIFY   │
│                                                                 │
│  Write tests    Implement      Clean up        Security       │
│  (must FAIL)    (tests PASS)   (still PASS)    scan           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘"""


def create_tdd_subtasks(task_id: int, task_title: str) -> List[Dict]:
    """Create the 4 TDD subtasks for a given task."""
    return [
        {
            "id": 1,
            "title": f"RED: Write failing tests for T{task_id}",
            "phase": "RED",
            "status": "pending",
            "dependencies": [],
            "acceptance_criteria": "Tests exist and FAIL when run",
            "description": "Write unit tests and/or integration tests based on the OpenSpec. Tests must fail initially (no implementation yet)."
        },
        {
            "id": 2,
            "title": f"GREEN: Implement T{task_id} to pass tests",
            "phase": "GREEN",
            "status": "pending",
            "dependencies": [1],
            "acceptance_criteria": "All tests PASS",
            "description": "Write the minimal implementation code to make all tests pass. Focus on correctness, not optimization."
        },
        {
            "id": 3,
            "title": f"REFACTOR: Clean up T{task_id} code",
            "phase": "REFACTOR",
            "status": "pending",
            "dependencies": [2],
            "acceptance_criteria": "Linting passes, tests still PASS",
            "description": "Refactor the code for clarity, maintainability, and style compliance. Run linters (ruff, black, eslint). Ensure tests still pass."
        },
        {
            "id": 4,
            "title": f"VERIFY: Security scan T{task_id}",
            "phase": "VERIFY",
            "status": "pending",
            "dependencies": [3],
            "acceptance_criteria": "No critical or high security issues",
            "description": "Run security scanners (bandit, safety, npm audit). Address any critical or high severity issues."
        }
    ]


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 404: TDD Subtask Injection.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, skip injection for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    tasks_file = atomic_root / ".taskmaster" / "tasks" / "tasks.json"
    backup_file = atomic_root / ".taskmaster" / "tasks" / "tasks.json.pre-tdd-backup"
    injection_report = output_dir / "tdd-injection.json"

    # UAT Mode: Skip TDD injection
    if uat_mode:
        print()
        print_yellow("⚡ UAT Mode: Skipping TDD subtask injection")
        print()
        ensure_dir(output_dir)
        write_file(injection_report, json.dumps({
            "subtasks_injected": 0,
            "mode": "uat"
        }, indent=2))
        print_green("✓ TDD subtask injection complete (UAT mode)")
        return True

    ensure_dir(injection_report.parent)

    print()
    print_dim("  Injecting TDD subtasks (RED/GREEN/REFACTOR/VERIFY) into tasks.json.")
    print()

    # TDD Cycle Education
    print_dim("─" * 109)
    print()
    print_bold("THE TDD CYCLE")
    print()
    print_dim("  Each task will receive 4 subtasks forming a dependency chain:")
    print()
    print(TDD_CYCLE_BANNER)
    print()
    print_bold("Subtask Details:")
    print()
    print_red("    1. RED - Write Failing Tests")
    print_dim("       Acceptance: Tests exist AND fail")
    print_dim("       Tools: pytest, jest, etc.")
    print()
    print_green("    2. GREEN - Minimal Implementation")
    print_dim("       Acceptance: All tests pass")
    print_dim("       Focus: Simplest code that works")
    print()
    print_cyan("    3. REFACTOR - Code Cleanup")
    print_dim("       Acceptance: Linting passes, tests still pass")
    print_dim("       Tools: ruff, black, mypy, eslint")
    print()
    print("\033[35m    4. VERIFY - Security Scan\033[0m")  # Magenta
    print_dim("       Acceptance: No critical/high issues")
    print_dim("       Tools: bandit, safety, npm audit")
    print()

    prompt_user("  Press Enter to continue...")
    print()

    # Pre-injection Backup
    print_dim("─" * 109)
    print()
    print_bold("PRE-INJECTION BACKUP")
    print()

    if not tasks_file.exists():
        print_red("✗ tasks.json not found")
        return False

    shutil.copy(tasks_file, backup_file)
    print_green("  ✓ Backed up tasks.json → tasks.json.pre-tdd-backup")
    print()

    # Injection Mode
    print_dim("─" * 109)
    print()
    print_bold("INJECTION MODE")
    print()

    tasks_data = json.loads(read_file(tasks_file))
    tasks = tasks_data.get("tasks", [])
    total_tasks = len(tasks)

    tasks_with_subtasks = len([t for t in tasks if len(t.get("subtasks", [])) > 0])

    print_dim("  Current state:")
    print(f"    Tasks with subtasks: {tasks_with_subtasks} / {total_tasks}")
    print()

    inject_mode = "inject"

    if tasks_with_subtasks > 0:
        print_yellow("  ! Some tasks already have subtasks.")
        print()
        print_cyan("Options:")
        print()
        print_green("  [skip]       Skip tasks that already have subtasks")
        print_yellow("  [replace]   Replace existing subtasks")
        print_red("  [abort]     Abort and review manually")
        print()

        clear_input_buffer()
        inject_mode = prompt_user("  Choice (default: skip): ").strip().lower() or "skip"

        if inject_mode == "abort":
            print_red("✗ Aborted by user")
            return False

    print()

    # Subtask Injection
    print_dim("─" * 109)
    print()
    print_bold("INJECTING TDD SUBTASKS")
    print()

    injected = 0
    skipped = 0

    for task in tasks:
        task_id = task.get("id", 0)
        task_title = task.get("title", "")
        existing_subtasks = len(task.get("subtasks", []))

        # Skip if has subtasks and mode is skip
        if inject_mode == "skip" and existing_subtasks > 0:
            print_dim(f"  [{task_id}] Skipping (has subtasks): {task_title[:50]}")
            skipped += 1
            continue

        print_cyan(f"  [{task_id}] Injecting: {task_title[:60]}")

        # Create TDD subtasks
        task["subtasks"] = create_tdd_subtasks(task_id, task_title)

        print_green(f"       ✓ Injected 4 TDD subtasks")
        injected += 1

    # Write updated tasks back
    write_file(tasks_file, json.dumps(tasks_data, indent=2))

    print()

    # Injection Summary
    print_dim("─" * 109)
    print()
    print_bold("INJECTION SUMMARY")
    print()

    print_green(f"    Tasks injected: {injected}")
    print_yellow(f"    Tasks skipped:  {skipped}")
    print()

    total_subtasks = injected * 4
    print_bold(f"    Total subtasks created: {total_subtasks}")
    print()

    # Verify injection
    tasks_data = json.loads(read_file(tasks_file))
    tasks = tasks_data.get("tasks", [])
    final_with_subtasks = len([t for t in tasks if len(t.get("subtasks", [])) >= 4])

    print_dim("  Verification:")
    print(f"    Tasks with TDD subtasks: {final_with_subtasks} / {total_tasks}")
    print()

    # Sample Output
    print_dim("─" * 109)
    print()
    print_bold("SAMPLE TASK STRUCTURE")
    print()

    if tasks:
        sample_task = tasks[0]
        sample_output = {
            "id": sample_task.get("id"),
            "title": sample_task.get("title"),
            "subtasks": [
                {
                    "id": st.get("id"),
                    "title": st.get("title"),
                    "phase": st.get("phase"),
                    "dependencies": st.get("dependencies")
                }
                for st in sample_task.get("subtasks", [])
            ]
        }
        print(json.dumps(sample_output, indent=2))
    print()

    # Save injection report
    injection_data = {
        "injection_mode": inject_mode,
        "tasks_injected": injected,
        "tasks_skipped": skipped,
        "total_subtasks_created": total_subtasks,
        "tasks_with_tdd_subtasks": final_with_subtasks,
        "total_tasks": total_tasks,
        "backup_file": "tasks.json.pre-tdd-backup",
        "completed_at": datetime.now().isoformat()
    }

    write_file(injection_report, json.dumps(injection_data, indent=2))

    print_green("✓ TDD Subtask Injection complete")

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 404: TDD Subtask Injection")
    parser.add_argument('--atomic-root', type=Path, required=True,
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip injection)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
