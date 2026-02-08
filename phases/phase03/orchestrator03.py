#!/usr/bin/env python3
"""
Phase 3 Orchestrator (orchestrator03.py)

Orchestrator for Phase 3: Tasking - Task decomposition and dependency analysis.

Tasks:
  301 - Entry initialization
  302 - Agent selection
  303 - Task decomposition
  304 - Dependency analysis
  305 - Phase audit
  306 - Closeout
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

# Import Phase 03 task modules
from phases.phase_03_tasking.tasks import (
    task_301,
    task_302,
    task_303,
    task_304,
    task_305,
    task_306,
)

# Get paths from environment
ATOMIC_ROOT = Path(os.getenv('ATOMIC_ROOT', Path.cwd()))
OUTPUT_DIR = Path(os.getenv('ATOMIC_OUTPUT_DIR', ATOMIC_ROOT / '.outputs' / '3-tasking'))
UAT_MODE = os.getenv('ATOMIC_UAT_MODE', 'false').lower() == 'true'


def run_phase(resume_at: str = None) -> bool:
    """
    Execute Phase 3: Tasking

    Args:
        resume_at: Optional task ID to resume from (e.g., "304")

    Returns:
        bool: True if phase completed successfully
    """
    phase_header("Phase 3: Tasking")

    state = StateManager()
    phase_id = "3-tasking"

    # Task list in execution order
    tasks = [
        ("301", "Entry initialization", task_301_entry_initialization),
        ("302", "Agent selection", task_302_agent_selection),
        ("303", "Task decomposition", task_303_task_decomposition),
        ("304", "Dependency analysis", task_304_dependency_analysis),
        ("305", "Phase audit", task_305_phase_audit),
        ("306", "Closeout", task_306_closeout),
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

    phase_complete("Phase 3: Tasking")

    # Create closeout file
    create_closeout(phase_id, tasks)

    return True


# Task wrapper functions (call Python modules)

def task_301_entry_initialization() -> bool:
    """Task 301: Entry initialization"""
    return task_301(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_302_agent_selection() -> bool:
    """Task 302: Agent selection"""
    return task_302(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_303_task_decomposition() -> bool:
    """Task 303: Task decomposition"""
    return task_303(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_304_dependency_analysis() -> bool:
    """Task 304: Dependency analysis"""
    return task_304(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_305_phase_audit() -> bool:
    """Task 305: Phase audit"""
    return task_305(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_306_closeout() -> bool:
    """Task 306: Closeout"""
    return task_306(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def create_closeout(phase_id: str, tasks: list):
    """
    Create phase closeout file.

    Args:
        phase_id: Phase identifier (e.g., "3-tasking")
        tasks: List of (task_id, task_name, task_func) tuples
    """
    import os

    atomic_root = Path(os.environ.get("ATOMIC_ROOT", Path.cwd()))
    output_dir = atomic_root / ".outputs" / phase_id
    output_dir.mkdir(parents=True, exist_ok=True)

    closeout_file = output_dir / "closeout.json"

    # Extract phase number from phase_id (e.g., "3-tasking" -> 3)
    phase_num = int(phase_id.split("-")[0])

    # Get list of completed task IDs
    completed_tasks = [task_id for task_id, _, _ in tasks]

    closeout_data = {
        "phase": phase_id,
        "phase_num": phase_num,
        "completed_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "tasks_completed": completed_tasks,
        "summary": f"Phase {phase_num} ({phase_id.split('-', 1)[1].title()}) completed successfully."
    }

    with open(closeout_file, "w") as f:
        json.dump(closeout_data, f, indent=2)

    print(f"\n✅ Phase {phase_num} closeout: {closeout_file}")


if __name__ == "__main__":
    success = run_phase()
    sys.exit(0 if success else 1)
