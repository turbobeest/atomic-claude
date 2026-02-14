#!/usr/bin/env python3
"""
Phase 0 Orchestrator (orchestrator00.py)

Orchestrator for Phase 0: Setup - Initial configuration and environment setup.

Tasks:
  001 - Mode selection (document/guided/quick)
  002 - Config collection
  003 - Config review
  004 - API keys
  005 - Material scan
  006 - Reference materials
  007 - Environment setup
  008 - Repository setup
  009 - Environment check
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

# Import Phase 00 task modules
from phases.phase_00_setup.tasks import (
    task_001,
    task_002,
    task_003,
    task_004,
    task_005,
    task_006,
    task_007,
    task_008,
    task_009,
)

# Get paths from environment
ATOMIC_ROOT = Path(os.getenv('ATOMIC_ROOT', Path.cwd()))
OUTPUT_DIR = Path(os.getenv('ATOMIC_OUTPUT_DIR', ATOMIC_ROOT / '.outputs' / '0-setup'))
UAT_MODE = os.getenv('ATOMIC_UAT_MODE', 'false').lower() == 'true'


def run_phase(resume_at: str = None) -> bool:
    """
    Execute Phase 0: Setup

    Args:
        resume_at: Optional task ID to resume from (e.g., "004")

    Returns:
        bool: True if phase completed successfully
    """
    phase_header("Phase 0: Setup")

    print("  This phase walks you through project setup in 9 steps:")
    print()
    print("    1. Setup wizard     — project identity, type, and pipeline config")
    print("    2. Config validation — verify and resolve configuration")
    print("    3. Config review    — final review and approval")
    print("    4. API keys         — validate LLM provider credentials")
    print("    5. Material scan    — index existing project files")
    print("    6. Reference docs   — identify key reference materials")
    print("    7. Environment      — prepare working directories")
    print("    8. Repository       — configure git and branching")
    print("    9. Environment check — verify everything is ready")
    print()
    print("  You can quit at any prompt with 'q' and resume later.")
    print()

    state = StateManager()
    phase_id = "0-setup"

    # Task list in execution order (all 9 tasks)
    tasks = [
        ("001", "Mode selection", task_001_mode_selection),
        ("002", "Config collection", task_002_config_collection),
        ("003", "Config review", task_003_config_review),
        ("004", "API keys", task_004_api_keys),
        ("005", "Material scan", task_005_material_scan),
        ("006", "Reference materials", task_006_reference_materials),
        ("007", "Environment setup", task_007_environment_setup),
        ("008", "Repository setup", task_008_repository_setup),
        ("009", "Environment check", task_009_environment_check),
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
                print(f"\n❌ Task {task_id} failed")
                state.mark_task_failed(phase_id, task_id, task_name)
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
            print(f"\n❌ Task {task_id} error: {e}")
            state.mark_task_failed(phase_id, task_id, task_name, str(e))
            log_error(phase_id, task_id, str(e), traceback.format_exc())
            clear_current_task()
            get_resolver().clear_task_overrides()
            return False

    phase_complete("Phase 0: Setup")

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


# Task wrapper functions (call Python modules)

def task_001_mode_selection() -> bool:
    """Execute task 001: Mode selection."""
    return task_001(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_002_config_collection() -> bool:
    """Execute task 002: Config collection."""
    return task_002(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_003_config_review() -> bool:
    """Execute task 003: Config review."""
    return task_003(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_004_api_keys() -> bool:
    """Execute task 004: API keys."""
    return task_004(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_005_material_scan() -> bool:
    """Execute task 005: Material scan."""
    return task_005(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_006_reference_materials() -> bool:
    """Execute task 006: Reference materials."""
    return task_006(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_007_environment_setup() -> bool:
    """Execute task 007: Environment setup."""
    return task_007(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_008_repository_setup() -> bool:
    """Execute task 008: Repository setup."""
    return task_008(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def task_009_environment_check() -> bool:
    """Execute task 009: Environment check."""
    return task_009(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE)


def create_closeout(phase_id: str, tasks: list):
    """Create closeout.json file for phase completion."""
    outputs_dir = Path(".outputs") / phase_id
    outputs_dir.mkdir(parents=True, exist_ok=True)

    closeout = {
        "phase": phase_id,
        "phase_num": 0,
        "completed_at": datetime.now().isoformat(),
        "tasks_completed": [task_id for task_id, _, _ in tasks],
        "summary": "Phase 0 (Setup) completed successfully. Configuration collected, API keys validated, and environment prepared."
    }

    closeout_path = outputs_dir / "closeout.json"
    with open(closeout_path, "w") as f:
        json.dump(closeout, f, indent=2)

    print(f"\n✅ Closeout file created: {closeout_path}")


if __name__ == "__main__":
    success = run_phase()
    sys.exit(0 if success else 1)
