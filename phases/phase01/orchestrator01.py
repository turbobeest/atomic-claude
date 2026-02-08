#!/usr/bin/env python3
"""
Phase 1 Orchestrator (orchestrator01.py)

Orchestrator for Phase 1: Discovery - Requirements gathering and agent selection.

Tasks:
  101 - Entry validation
  102 - Corpus collection
  103 - Import requirements
  104 - Agent selection
  105 - Opening dialogue
  106 - Discovery work
  107 - Approach selection
  108 - Discovery diagrams
  109 - Phase audit
  110 - Closeout
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

# Import Phase 01 task modules
from phases.phase_01_discovery.tasks import (
    task_101,
    task_102,
    task_103,
    task_104,
    task_105,
    task_106,
    task_107,
    task_108,
    task_109,
    task_110,
)

# Get paths from environment
ATOMIC_ROOT = Path(os.getenv('ATOMIC_ROOT', Path.cwd()))
OUTPUT_DIR = Path(os.getenv('ATOMIC_OUTPUT_DIR', ATOMIC_ROOT / '.outputs' / '1-discovery'))
UAT_MODE = os.getenv('ATOMIC_UAT_MODE', 'false').lower() == 'true'


def run_phase(resume_at: str = None) -> bool:
    """
    Execute Phase 1: Discovery

    Args:
        resume_at: Optional task ID to resume from (e.g., "104")

    Returns:
        bool: True if phase completed successfully
    """
    phase_header("Phase 1: Discovery")

    state = StateManager()
    phase_id = "1-discovery"

    # Task list in execution order
    tasks = [
        ("101", "Entry validation", task_101_entry_validation),
        ("102", "Corpus collection", task_102_corpus_collection),
        ("103", "Import requirements", task_103_import_requirements),
        ("104", "Agent selection", task_104_agent_selection),
        ("105", "Opening dialogue", task_105_opening_dialogue),
        ("106", "Discovery work", task_106_discovery_work),
        ("107", "Approach selection", task_107_approach_selection),
        ("108", "Discovery diagrams", task_108_discovery_diagrams),
        ("109", "Phase audit", task_109_phase_audit),
        ("110", "Closeout", task_110_closeout),
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

    phase_complete("Phase 1: Discovery")

    # Create closeout file
    create_closeout(phase_id, tasks)

    return True


# Task wrapper functions (call Python modules)

def task_101_entry_validation() -> bool:
    """Task 101: Entry validation"""
    return task_101(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_102_corpus_collection() -> bool:
    """Task 102: Corpus collection"""
    return task_102(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_103_import_requirements() -> bool:
    """Task 103: Import requirements"""
    return task_103(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_104_agent_selection() -> bool:
    """Task 104: Agent selection"""
    return task_104(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_105_opening_dialogue() -> bool:
    """Task 105: Opening dialogue"""
    return task_105(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_106_discovery_work() -> bool:
    """Task 106: Discovery work"""
    return task_106(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_107_approach_selection() -> bool:
    """Task 107: Approach selection"""
    return task_107(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_108_discovery_diagrams() -> bool:
    """Task 108: Discovery diagrams"""
    return task_108(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_109_phase_audit() -> bool:
    """Task 109: Phase audit"""
    return task_109(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_110_closeout() -> bool:
    """Task 110: Closeout"""
    return task_110(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def create_closeout(phase_id: str, tasks: list):
    """
    Create phase closeout file.

    Args:
        phase_id: Phase identifier (e.g., "1-discovery")
        tasks: List of (task_id, task_name, task_func) tuples
    """
    import os

    atomic_root = Path(os.environ.get("ATOMIC_ROOT", Path.cwd()))
    output_dir = atomic_root / ".outputs" / phase_id
    output_dir.mkdir(parents=True, exist_ok=True)

    closeout_file = output_dir / "closeout.json"

    # Extract phase number from phase_id (e.g., "1-discovery" -> 1)
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
