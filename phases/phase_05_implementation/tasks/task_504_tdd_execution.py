"""
Task 504: TDD Execution

Execute RED/GREEN/REFACTOR/VERIFY cycles for each task.

NOTE: This is a simplified Python implementation. The full bash script (1388 lines)
contains extensive parallel execution, LLM agent loading, and TDD phase helpers.
For production use, this module should call the bash script via subprocess_runner
or be fully implemented with all TDD phase logic.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.subprocess_runner import run_task_script_streaming
from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim
)
from core.utils.file_ops import ensure_dir, write_file


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 504: TDD Execution.

    This is a simplified Python wrapper. For full functionality, it delegates
    to the bash implementation which contains:
    - Parallel/sequential/guided execution modes
    - LLM agent loading and invocation
    - RED/GREEN/REFACTOR/VERIFY phase helpers
    - Error context accumulation
    - Git worktree management

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    testing_dir = atomic_root / ".claude" / "testing"
    progress_file = output_dir / "tdd-progress.json"
    src_dir = atomic_root / "src"

    # UAT Mode Bypass
    if uat_mode:
        print()
        print(print_yellow("⚡ UAT Mode: Creating stub implementation files (no actual TDD cycles)"))
        print()

        ensure_dir(testing_dir)
        ensure_dir(src_dir)

        # Create minimal TDD progress file
        progress_data = {
            "tasks_completed": 3,
            "tasks_total": 3,
            "subtasks_completed": 12,
            "subtasks_total": 12,
            "red_cycles": 3,
            "green_cycles": 3,
            "refactor_cycles": 3,
            "verify_cycles": 3,
            "mode": "uat",
            "completed_at": datetime.now().isoformat()
        }
        write_file(progress_file, json.dumps(progress_data, indent=2))

        # Create stub test and implementation files for 3 tasks
        for task_id in range(1, 4):
            task_dir = src_dir / f"task-{task_id}"
            ensure_dir(task_dir)
            ensure_dir(testing_dir / f"task-{task_id}")

            impl_file = task_dir / "implementation.py"
            write_file(impl_file, "# Stub Implementation (UAT Mode)\ndef stub_function(): pass\n")

            test_file = testing_dir / f"task-{task_id}" / "test_stub.py"
            write_file(test_file, "# Stub Test (UAT Mode)\ndef test_stub(): assert True\n")

            # Create minimal TDD record
            tdd_record = {
                "task_id": task_id,
                "red": {"status": "complete"},
                "green": {"status": "complete"},
                "refactor": {"status": "complete"},
                "verify": {"status": "complete"},
                "mode": "uat"
            }
            write_file(testing_dir / f"tdd-t{task_id}.json", json.dumps(tdd_record, indent=2))

        print(print_green("✓ Created stub files for 3 tasks"))
        print()

        print(print_green("✓ TDD Execution complete (UAT mode)"))
        return True

    # For non-UAT mode, delegate to bash script for full TDD execution
    print()
    print(print_yellow("⚠ TDD Execution requires bash implementation for full functionality"))
    print(print_dim("  This includes:"))
    print(print_dim("  - Parallel/sequential execution with git worktrees"))
    print(print_dim("  - LLM agent loading and prompting"))
    print(print_dim("  - RED/GREEN/REFACTOR/VERIFY phase execution"))
    print(print_dim("  - Error context accumulation and retry logic"))
    print()
    print(print_cyan("  Delegating to bash script..."))
    print()

    # Execute the bash script
    bash_script = Path(__file__).parent.parent / "tasks" / "504-tdd-execution.sh"
    if bash_script.exists():
        exit_code = run_task_script_streaming(
            bash_script,
            "5-implementation",
            "504",
            timeout=3600  # 1 hour timeout for TDD execution
        )
        return exit_code == 0
    else:
        print(print_red(f"✗ Bash script not found: {bash_script}"))
        print(print_yellow("  Creating minimal progress file as fallback..."))

        # Create minimal progress as fallback
        progress_data = {
            "tasks_completed": 0,
            "tasks_total": 0,
            "mode": "fallback",
            "note": "Full TDD execution requires bash implementation",
            "completed_at": datetime.now().isoformat()
        }
        write_file(progress_file, json.dumps(progress_data, indent=2))

        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 504: TDD Execution")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
