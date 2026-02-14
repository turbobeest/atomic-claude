#!/usr/bin/env python3
"""
Phase 8 Orchestrator (orchestrator08.py)

Orchestrator for Phase 8: Deployment Prep - Deployment preparation and artifact generation.

Tasks:
  801 - Entry initialization
  802 - Deployment setup
  803 - Agent selection
  804 - Artifact generation
  805 - Phase audit
  806 - Deployment approval
  807 - Closeout
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Ensure atomic-claude2 root is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import traceback

from core.state import StateManager
from core.ui import phase_header, phase_complete
from core.memory import memory_save, MemoryEntryType
from orchestration.pre_task_validation import validate_directory_pristine
from orchestration.dashboard_sync import write_current_task, clear_current_task, log_error
from orchestration.task_display import display_task_roster, resolve_agent_roster
from core.llm.resolver import resolve_model, get_resolver

# Import Python task modules
from phases.phase_08_deployment_prep.tasks import (
    task_801,
    task_802,
    task_803,
    task_804,
    task_805,
    task_806,
    task_807,
)

# Environment variables
ATOMIC_ROOT = Path(os.getenv('ATOMIC_ROOT', Path.cwd()))
OUTPUT_DIR = Path(os.getenv('ATOMIC_OUTPUT_DIR', Path('.outputs/8-deployment-prep')))
UAT_MODE = os.getenv('ATOMIC_UAT_MODE', 'false').lower() == 'true'


def run_phase(resume_at: str = None) -> bool:
    """
    Execute Phase 8: Deployment Prep

    Args:
        resume_at: Optional task ID to resume from (e.g., "804")

    Returns:
        bool: True if phase completed successfully
    """
    phase_header("Phase 8: Deployment Prep")

    state = StateManager()
    phase_id = "8-deployment-prep"

    # Task list in execution order
    tasks = [
        ("801", "Entry initialization", task_801_wrapper),
        ("802", "Deployment setup", task_802_wrapper),
        ("803", "Agent selection", task_803_wrapper),
        ("804", "Artifact generation", task_804_wrapper),
        ("805", "Phase audit", task_805_wrapper),
        ("806", "Deployment approval", task_806_wrapper),
        ("807", "Closeout", task_807_wrapper),
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
        roster = resolve_agent_roster(phase_id, task_id, OUTPUT_DIR)
        roster = display_task_roster(task_id, task_name, roster, uat_mode=UAT_MODE)
        write_current_task(phase_id, task_id, task_name, resolved=roster[0][1],
                           agent_roster=roster)

        try:
            success = task_func()
            if not success:
                state.mark_task_failed(phase_id, task_id, task_name)
                print(f"\n❌ Task {task_id} failed")
                clear_current_task()
                get_resolver().clear_task_overrides()
                return False

            state.mark_task_complete(phase_id, task_id, task_name)
            clear_current_task()
            get_resolver().clear_task_overrides()

            # Save task completion to memory
            try:
                memory_save(
                    phase=phase_id,
                    task_id=task_id,
                    content=f"Task {task_id} ({task_name}) completed",
                    tags=["task-complete", phase_id, f"task-{task_id}"],
                    entry_type=MemoryEntryType.TASK_END,
                )
            except Exception:
                pass  # Memory save failure is non-blocking

        except Exception as e:
            state.mark_task_failed(phase_id, task_id, task_name, str(e))
            log_error(phase_id, task_id, str(e), traceback.format_exc())
            print(f"\n❌ Task {task_id} error: {e}")
            clear_current_task()
            get_resolver().clear_task_overrides()
            return False

    phase_complete("Phase 8: Deployment Prep")

    # Save phase completion to memory
    try:
        memory_save(
            phase=phase_id,
            task_id=None,
            content=f"Phase {phase_id} completed. Tasks: {', '.join(t[0] for t in tasks)}",
            tags=["phase-complete", phase_id],
            entry_type=MemoryEntryType.PHASE_CLOSEOUT,
        )
    except Exception:
        pass

    # Create closeout file
    create_closeout(phase_id, tasks)

    return True


# Task wrapper functions (call Python task modules)

def task_801_wrapper() -> bool:
    """Task 801: Entry initialization"""
    return task_801(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_802_wrapper() -> bool:
    """Task 802: Deployment setup"""
    return task_802(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_803_wrapper() -> bool:
    """Task 803: Agent selection"""
    return task_803(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_804_wrapper() -> bool:
    """Task 804: Artifact generation"""
    return task_804(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_805_wrapper() -> bool:
    """Task 805: Phase audit"""
    return task_805(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_806_wrapper() -> bool:
    """Task 806: Deployment approval"""
    return task_806(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_807_wrapper() -> bool:
    """Task 807: Closeout"""
    return task_807(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def create_closeout(phase_id: str, tasks: list):
    """
    Create phase closeout file.

    Args:
        phase_id: Phase identifier (e.g., "8-deployment-prep")
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
            "deployment_artifacts": "Deployment artifacts generated",
            "deployment_plan": "Deployment plan created",
            "agent_roster": "Selected deployment agents"
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
