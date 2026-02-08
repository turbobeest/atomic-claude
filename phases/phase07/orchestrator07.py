#!/usr/bin/env python3
"""
Phase 7 Orchestrator (orchestrator07.py)

Orchestrator for Phase 7: Integration - Integration testing and approval.

Tasks:
  701 - Entry initialization
  702 - Integration setup
  703 - Agent selection
  704 - Testing execution
  705 - Integration approval
  706 - Phase audit
  707 - Closeout
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
from phases.phase_07_integration.tasks import (
    task_701,
    task_702,
    task_703,
    task_704,
    task_705,
    task_706,
    task_707,
)

# Environment variables
ATOMIC_ROOT = Path(os.getenv('ATOMIC_ROOT', Path.cwd()))
OUTPUT_DIR = Path(os.getenv('ATOMIC_OUTPUT_DIR', Path('.outputs/7-integration')))
UAT_MODE = os.getenv('ATOMIC_UAT_MODE', 'false').lower() == 'true'


def run_phase(resume_at: str = None) -> bool:
    """
    Execute Phase 7: Integration

    Args:
        resume_at: Optional task ID to resume from (e.g., "704")

    Returns:
        bool: True if phase completed successfully
    """
    phase_header("Phase 7: Integration")

    state = StateManager()
    phase_id = "7-integration"

    # Task list in execution order
    tasks = [
        ("701", "Entry initialization", task_701_wrapper),
        ("702", "Integration setup", task_702_wrapper),
        ("703", "Agent selection", task_703_wrapper),
        ("704", "Testing execution", task_704_wrapper),
        ("705", "Integration approval", task_705_wrapper),
        ("706", "Phase audit", task_706_wrapper),
        ("707", "Closeout", task_707_wrapper),
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

    phase_complete("Phase 7: Integration")

    # Create closeout file
    create_closeout(phase_id, tasks)

    return True


# Task wrapper functions (call Python task modules)

def task_701_wrapper() -> bool:
    """Task 701: Entry initialization"""
    return task_701(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_702_wrapper() -> bool:
    """Task 702: Integration setup"""
    return task_702(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_703_wrapper() -> bool:
    """Task 703: Agent selection"""
    return task_703(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_704_wrapper() -> bool:
    """Task 704: Testing execution"""
    return task_704(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_705_wrapper() -> bool:
    """Task 705: Integration approval"""
    return task_705(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_706_wrapper() -> bool:
    """Task 706: Phase audit"""
    return task_706(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_707_wrapper() -> bool:
    """Task 707: Closeout"""
    return task_707(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def create_closeout(phase_id: str, tasks: list):
    """
    Create phase closeout file.

    Args:
        phase_id: Phase identifier (e.g., "7-integration")
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
            "integration_tests": "Integration tests complete",
            "test_results": "All integration tests passing",
            "agent_roster": "Selected integration agents"
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
