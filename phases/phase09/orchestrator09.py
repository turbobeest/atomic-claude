#!/usr/bin/env python3
"""
Phase 9 Orchestrator (orchestrator09.py)

Orchestrator for Phase 9: Release - Final release and deployment.

Tasks:
  901 - Entry initialization
  902 - Release setup
  903 - Agent selection
  904 - Release execution
  905 - Release confirmation
  906 - Closeout
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
from phases.phase_09_release.tasks import (
    task_901,
    task_902,
    task_903,
    task_904,
    task_905,
    task_906,
)

# Environment variables
ATOMIC_ROOT = Path(os.getenv('ATOMIC_ROOT', Path.cwd()))
OUTPUT_DIR = Path(os.getenv('ATOMIC_OUTPUT_DIR', Path('.outputs/9-release')))
UAT_MODE = os.getenv('ATOMIC_UAT_MODE', 'false').lower() == 'true'


def run_phase(resume_at: str = None) -> bool:
    """
    Execute Phase 9: Release

    Args:
        resume_at: Optional task ID to resume from (e.g., "904")

    Returns:
        bool: True if phase completed successfully
    """
    phase_header("Phase 9: Release")

    state = StateManager()
    phase_id = "9-release"

    # Task list in execution order
    tasks = [
        ("901", "Entry initialization", task_901_wrapper),
        ("902", "Release setup", task_902_wrapper),
        ("903", "Agent selection", task_903_wrapper),
        ("904", "Release execution", task_904_wrapper),
        ("905", "Release confirmation", task_905_wrapper),
        ("906", "Closeout", task_906_wrapper),
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

    phase_complete("Phase 9: Release")

    # Create closeout file
    create_closeout(phase_id, tasks)

    return True


# Task wrapper functions (call Python task modules)

def task_901_wrapper() -> bool:
    """Task 901: Entry initialization"""
    return task_901(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_902_wrapper() -> bool:
    """Task 902: Release setup"""
    return task_902(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_903_wrapper() -> bool:
    """Task 903: Agent selection"""
    return task_903(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_904_wrapper() -> bool:
    """Task 904: Release execution"""
    return task_904(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_905_wrapper() -> bool:
    """Task 905: Release confirmation"""
    return task_905(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_906_wrapper() -> bool:
    """Task 906: Closeout"""
    return task_906(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def create_closeout(phase_id: str, tasks: list):
    """Create closeout.json file for phase completion."""
    outputs_dir = Path(".outputs") / phase_id
    outputs_dir.mkdir(parents=True, exist_ok=True)

    closeout = {
        "phase": phase_id,
        "phase_num": 9,
        "completed_at": datetime.now().isoformat(),
        "tasks_completed": [task_id for task_id, _, _ in tasks],
        "summary": "Phase 9 (Release) completed successfully. Project released to distribution channels."
    }

    closeout_path = outputs_dir / "closeout.json"
    with open(closeout_path, "w") as f:
        json.dump(closeout, f, indent=2)

    print(f"\n✅ Closeout file created: {closeout_path}")


if __name__ == "__main__":
    import sys

    resume_at = None
    if len(sys.argv) > 1:
        resume_at = sys.argv[1]

    success = run_phase(resume_at)
    sys.exit(0 if success else 1)
