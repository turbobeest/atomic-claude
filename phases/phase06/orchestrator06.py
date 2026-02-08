#!/usr/bin/env python3
"""
Phase 6 Orchestrator (orchestrator06.py)

Orchestrator for Phase 6: Code Review - Comprehensive code review and refinement.

Tasks:
  601 - Entry initialization
  602 - Agent selection
  603 - Comprehensive review
  604 - Refinement
  605 - Phase audit
  606 - Closeout
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
from phases.phase_06_code_review.tasks import (
    task_601,
    task_602,
    task_603,
    task_604,
    task_605,
    task_606,
)

# Environment variables
ATOMIC_ROOT = Path(os.getenv('ATOMIC_ROOT', Path.cwd()))
OUTPUT_DIR = Path(os.getenv('ATOMIC_OUTPUT_DIR', Path('.outputs/6-code-review')))
UAT_MODE = os.getenv('ATOMIC_UAT_MODE', 'false').lower() == 'true'


def run_phase(resume_at: str = None) -> bool:
    """
    Execute Phase 6: Code Review

    Args:
        resume_at: Optional task ID to resume from (e.g., "603")

    Returns:
        bool: True if phase completed successfully
    """
    phase_header("Phase 6: Code Review")

    state = StateManager()
    phase_id = "6-code-review"

    # Task list in execution order
    tasks = [
        ("601", "Entry initialization", task_601_wrapper),
        ("602", "Agent selection", task_602_wrapper),
        ("603", "Comprehensive review", task_603_wrapper),
        ("604", "Refinement", task_604_wrapper),
        ("605", "Phase audit", task_605_wrapper),
        ("606", "Closeout", task_606_wrapper),
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

    phase_complete("Phase 6: Code Review")

    # Create closeout file
    create_closeout(phase_id, tasks)

    return True


# Task wrapper functions (call Python task modules)

def task_601_wrapper() -> bool:
    """Task 601: Entry initialization"""
    return task_601(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_602_wrapper() -> bool:
    """Task 602: Agent selection"""
    return task_602(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_603_wrapper() -> bool:
    """Task 603: Comprehensive review"""
    return task_603(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_604_wrapper() -> bool:
    """Task 604: Refinement"""
    return task_604(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_605_wrapper() -> bool:
    """Task 605: Phase audit"""
    return task_605(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_606_wrapper() -> bool:
    """Task 606: Closeout"""
    return task_606(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def create_closeout(phase_id: str, tasks: list):
    """
    Create phase closeout file.

    Args:
        phase_id: Phase identifier (e.g., "6-code-review")
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
            "review_report": "Comprehensive code review complete",
            "refinements": "Code refinements applied",
            "agent_roster": "Selected review agents"
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
