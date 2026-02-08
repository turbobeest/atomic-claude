#!/usr/bin/env python3
"""
Phase 5 Orchestrator (orchestrator05.py)

Orchestrator for Phase 5: Implementation - TDD execution and code generation.

Tasks:
  501 - Entry initialization
  502 - TDD setup
  503 - Agent selection
  504 - TDD execution
  505 - Validation
  506 - Phase audit
  507 - Closeout
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Ensure atomic-claude2 root is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.state import StateManager
from core.ui import phase_header, phase_complete
from orchestration.pre_task_validation import validate_directory_pristine

# Import Python task modules
from phases.phase_05_implementation.tasks import (
    task_501_entry_initialization,
    task_502_tdd_setup,
    task_503_agent_selection,
    task_504_tdd_execution,
    task_505_validation,
    task_506_phase_audit,
    task_507_closeout,
)

# Environment variables
ATOMIC_ROOT = Path(os.getenv('ATOMIC_ROOT', Path.cwd()))
OUTPUT_DIR = Path(os.getenv('ATOMIC_OUTPUT_DIR', Path('.outputs/5-implementation')))
UAT_MODE = os.getenv('ATOMIC_UAT_MODE', 'false').lower() == 'true'


def run_phase(resume_at: str = None) -> bool:
    """
    Execute Phase 5: Implementation

    Args:
        resume_at: Optional task ID to resume from (e.g., "503")

    Returns:
        bool: True if phase completed successfully
    """
    phase_header("Phase 5: Implementation")

    state = StateManager()
    phase_id = "5-implementation"

    # Task list in execution order
    tasks = [
        ("501", "Entry initialization", task_501_wrapper),
        ("502", "TDD setup", task_502_wrapper),
        ("503", "Agent selection", task_503_wrapper),
        ("504", "TDD execution", task_504_wrapper),
        ("505", "Validation", task_505_wrapper),
        ("506", "Phase audit", task_506_wrapper),
        ("507", "Closeout", task_507_wrapper),
    ]

    # Determine starting point
    start_index = 0
    if resume_at:
        for i, (task_id, _, _) in enumerate(tasks):
            if task_id == resume_at:
                start_index = i
                break

    # Execute tasks
    for task_id, task_name, task_func in tasks[start_index:]:
        # Skip if already completed
        if state.is_task_complete(phase_id, task_id):
            print(f"✓ Task {task_id} already complete, skipping")
            continue

        # PRE-TASK VALIDATION: Ensure directory is pristine (BLOCKER)
        if not validate_directory_pristine(phase_id, task_id):
            print(f"\n🛑 Cannot proceed to Task {task_id} - fix violations first")
            return False

        # Run task
        print(f"\n⚡ Running Task {task_id}: {task_name}")

        try:
            success = task_func()
            if not success:
                state.mark_task_failed(phase_id, task_id, task_name)
                print(f"\n❌ Task {task_id} failed")
                return False

            state.mark_task_complete(phase_id, task_id, task_name)

        except Exception as e:
            state.mark_task_failed(phase_id, task_id, task_name, str(e))
            print(f"\n❌ Task {task_id} error: {e}")
            return False

    phase_complete("Phase 5: Implementation")

    # Create closeout file
    create_closeout(phase_id, tasks)

    return True


# Task wrapper functions (call Python task modules)

def task_501_wrapper() -> bool:
    """Task 501: Entry initialization"""
    return task_501_entry_initialization.execute(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_502_wrapper() -> bool:
    """Task 502: TDD setup"""
    return task_502_tdd_setup.execute(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_503_wrapper() -> bool:
    """Task 503: Agent selection"""
    return task_503_agent_selection.execute(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_504_wrapper() -> bool:
    """Task 504: TDD execution"""
    return task_504_tdd_execution.execute(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_505_wrapper() -> bool:
    """Task 505: Validation"""
    return task_505_validation.execute(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_506_wrapper() -> bool:
    """Task 506: Phase audit"""
    return task_506_phase_audit.execute(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_507_wrapper() -> bool:
    """Task 507: Closeout"""
    return task_507_closeout.execute(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def create_closeout(phase_id: str, tasks: list):
    """
    Create phase closeout file.

    Args:
        phase_id: Phase identifier (e.g., "5-implementation")
        tasks: List of (task_id, task_name, task_func) tuples
    """
    from pathlib import Path
    import json
    from datetime import datetime

    # Get atomic-claude2 root
    atomic_root = Path(__file__).parent.parent.parent

    # Closeout file path
    closeout_dir = atomic_root / ".outputs" / phase_id
    closeout_dir.mkdir(parents=True, exist_ok=True)
    closeout_file = closeout_dir / "closeout.json"

    # Build closeout data
    closeout = {
        "phase": phase_id,
        "status": "complete",
        "completed_at": datetime.now().isoformat(),
        "tasks_completed": len(tasks),
        "tasks": [
            {
                "id": task_id,
                "name": task_name,
                "status": "completed"
            }
            for task_id, task_name, _ in tasks
        ],
        "outputs": {
            "implementation": "TDD-driven code implementation complete",
            "test_results": "All tests passing",
            "agent_roster": "Selected implementation agents"
        }
    }

    # Write closeout file
    with open(closeout_file, "w") as f:
        json.dump(closeout, f, indent=2)

    print(f"\n✓ Closeout file created: {closeout_file}")


if __name__ == "__main__":
    import sys

    resume_at = None
    if len(sys.argv) > 1:
        resume_at = sys.argv[1]

    success = run_phase(resume_at)
    sys.exit(0 if success else 1)
