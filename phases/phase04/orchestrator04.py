#!/usr/bin/env python3
"""
Phase 4 Orchestrator (orchestrator04.py)

Orchestrator for Phase 4: Specification - OpenSpec generation and TDD subtask injection.

Tasks:
  401 - Entry initialization
  402 - Agent selection
  403 - OpenSpec generation
  404 - TDD subtask injection
  405 - Phase audit
  406 - Closeout
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

# Import Phase 04 task modules
from phases.phase_04_specification.tasks import (
    task_401,
    task_402,
    task_403,
    task_404,
    task_405,
    task_406,
)

# Get paths from environment
ATOMIC_ROOT = Path(os.getenv('ATOMIC_ROOT', Path.cwd()))
OUTPUT_DIR = Path(os.getenv('ATOMIC_OUTPUT_DIR', ATOMIC_ROOT / '.outputs' / '4-specification'))
UAT_MODE = os.getenv('ATOMIC_UAT_MODE', 'false').lower() == 'true'


def run_phase(resume_at: str = None) -> bool:
    """
    Execute Phase 4: Specification

    Args:
        resume_at: Optional task ID to resume from (e.g., "403")

    Returns:
        bool: True if phase completed successfully
    """
    phase_header("Phase 4: Specification")

    state = StateManager()
    phase_id = "4-specification"

    # Task list in execution order
    tasks = [
        ("401", "Entry initialization", task_401_entry_initialization),
        ("402", "Agent selection", task_402_agent_selection),
        ("403", "OpenSpec generation", task_403_openspec_generation),
        ("404", "TDD subtask injection", task_404_tdd_subtask_injection),
        ("405", "Phase audit", task_405_phase_audit),
        ("406", "Closeout", task_406_closeout),
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

    phase_complete("Phase 4: Specification")

    # Create closeout file
    create_closeout(phase_id, tasks)

    return True


# Task wrapper functions (call Python modules)

def task_401_entry_initialization() -> bool:
    """Task 401: Entry initialization"""
    return task_401(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_402_agent_selection() -> bool:
    """Task 402: Agent selection"""
    return task_402(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_403_openspec_generation() -> bool:
    """Task 403: OpenSpec generation"""
    return task_403(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_404_tdd_subtask_injection() -> bool:
    """Task 404: TDD subtask injection"""
    return task_404(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_405_phase_audit() -> bool:
    """Task 405: Phase audit"""
    return task_405(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_406_closeout() -> bool:
    """Task 406: Closeout"""
    return task_406(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def create_closeout(phase_id: str, tasks: list):
    """
    Create phase closeout file.

    Args:
        phase_id: Phase identifier (e.g., "4-specification")
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
            "openspec_files": "Generated OpenSpec test specifications",
            "tdd_subtasks": "TDD subtasks injected into TaskMaster",
            "agent_roster": "Selected specification agents"
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
