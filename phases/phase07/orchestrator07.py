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

import logging
import sys
import os
from pathlib import Path
from datetime import datetime

# Ensure atomic-claude2 root is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import traceback

logger = logging.getLogger(__name__)

from core.state import StateManager
from core.ui import phase_header, phase_complete
from core.memory import memory_save, MemoryEntryType
from orchestration.pre_task_validation import validate_directory_pristine
from orchestration.dashboard_sync import write_current_task, clear_current_task, log_error, ensure_dashboard
from orchestration.memory_enrichment import summarize_task_artifacts, enrich_memory_with_llm
from orchestration.task_memory import TaskMemory
from orchestration.task_display import display_task_roster, resolve_agent_roster, is_infrastructure_task
from core.llm.resolver import resolve_model, get_resolver
from core.utils.file_ops import write_json


def _make_flush_fn(phase_id: str, task_id: str):
    """Create a callback for mid-task memory checkpoints."""
    def flush(content, tags, entry_type):
        memory_save(
            phase=phase_id,
            task_id=task_id,
            content=content,
            tags=tags,
            entry_type=MemoryEntryType.TASK_PROGRESS,
        )
    return flush


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
PROJECT_ROOT = ATOMIC_ROOT.parent
OUTPUT_DIR = Path(os.getenv('ATOMIC_OUTPUT_DIR', PROJECT_ROOT / '.outputs' / '7-integration'))
UAT_MODE = os.getenv('ATOMIC_UAT_MODE', 'false').lower() == 'true'


def run_phase(resume_at: str = None) -> bool:
    """
    Execute Phase 7: Integration

    Args:
        resume_at: Optional task ID to resume from (e.g., "704")

    Returns:
        bool: True if phase completed successfully
    """
    if resume_at:
        phase_header("Phase 7: Integration (resuming)")
    else:
        phase_header("Phase 7: Integration")

    state = StateManager()
    phase_id = "7-integration"

    # Register active phase in task-state.json so dashboard always knows
    state.set_current_phase(phase_id)

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

    # Expected artifacts per task (relative to OUTPUT_DIR)
    task_artifacts = {
        "701": [],
        "702": [],
        "703": ["integration-agents.json"],
        "704": ["integration-test-results.json"],
        "705": [],
        "706": [],
        "707": [],
    }

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
        ensure_dashboard(ATOMIC_ROOT)
        if is_infrastructure_task(task_name):
            print(f"\n  {task_name}\n")
            write_current_task(phase_id, task_id, task_name)
        else:
            roster = resolve_agent_roster(phase_id, task_id, OUTPUT_DIR)
            roster = display_task_roster(task_id, task_name, roster, uat_mode=UAT_MODE)
            write_current_task(phase_id, task_id, task_name, resolved=roster[0][1],
                               agent_roster=roster)

        state.mark_task_started(phase_id, task_id, task_name)
        mem = TaskMemory(phase_id, task_id, task_name,
                         flush_fn=_make_flush_fn(phase_id, task_id))
        try:
            success = task_func(mem)
            if not success:
                state.mark_task_failed(phase_id, task_id, task_name)
                print(f"\n❌ Task {task_id} failed")
                clear_current_task()
                get_resolver().clear_task_overrides()
                return False

            # Collect actual artifacts (files that exist)
            artifacts = [
                str(OUTPUT_DIR / f) for f in task_artifacts.get(task_id, [])
                if (OUTPUT_DIR / f).exists()
            ]
            state.mark_task_complete(phase_id, task_id, task_name, artifacts=artifacts)
            # Don't clear current-task.json here — the next write_current_task()
            # overwrites it, keeping the dashboard session alive between tasks.
            get_resolver().clear_task_overrides()

            # Save task completion to memory (with enriched artifact summaries)
            try:
                if mem.has_entries():
                    memory_content = mem.build_content()
                    memory_metadata = mem.build_metadata()
                else:
                    # Try LLM enrichment first (haiku), fall back to file-based summary
                    memory_content = enrich_memory_with_llm(
                        artifacts, task_id, task_name, output_dir=OUTPUT_DIR
                    )
                    if not memory_content:
                        memory_content = summarize_task_artifacts(
                            artifacts, task_id, task_name, output_dir=OUTPUT_DIR
                        )
                    memory_metadata = {}
                memory_save(
                    phase=phase_id,
                    task_id=task_id,
                    content=memory_content,
                    tags=["task-complete", phase_id, f"task-{task_id}"],
                    entry_type=MemoryEntryType.TASK_END,
                    metadata=memory_metadata,
                )
            except Exception as e:
                logger.warning("Memory save failed for task %s: %s", task_id, e)

        except Exception as e:
            state.mark_task_failed(phase_id, task_id, task_name, str(e))
            log_error(phase_id, task_id, str(e), traceback.format_exc())
            print(f"\n❌ Task {task_id} error: {e}")
            clear_current_task()
            get_resolver().clear_task_overrides()
            return False

    # Phase complete — NOW clear current-task.json
    clear_current_task()
    phase_complete("Phase 7: Integration")

    # Save phase completion to memory
    try:
        memory_save(
            phase=phase_id,
            task_id=None,
            content=f"Phase {phase_id} completed. Tasks: {', '.join(t[0] for t in tasks)}",
            tags=["phase-complete", phase_id],
            entry_type=MemoryEntryType.PHASE_CLOSEOUT,
        )
    except Exception as e:
        logger.warning("Phase closeout memory save failed: %s", e)

    # Create closeout file
    try:
        create_closeout(phase_id, tasks)
    except Exception as e:
        logger.warning("Closeout file creation failed: %s", e)

    return True


# Task wrapper functions (call Python task modules)

def task_701_wrapper(mem=None) -> bool:
    """Task 701: Entry initialization"""
    return task_701(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_702_wrapper(mem=None) -> bool:
    """Task 702: Integration setup"""
    return task_702(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_703_wrapper(mem=None) -> bool:
    """Task 703: Agent selection"""
    return task_703(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_704_wrapper(mem=None) -> bool:
    """Task 704: Testing execution"""
    return task_704(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_705_wrapper(mem=None) -> bool:
    """Task 705: Integration approval"""
    return task_705(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_706_wrapper(mem=None) -> bool:
    """Task 706: Phase audit"""
    return task_706(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_707_wrapper(mem=None) -> bool:
    """Task 707: Closeout"""
    return task_707(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def create_closeout(phase_id: str, tasks: list):
    """
    Create phase closeout file.

    Args:
        phase_id: Phase identifier (e.g., "7-integration")
        tasks: List of (task_id, task_name, task_func) tuples
    """
    # Get atomic-claude2 root
    atomic_root = Path(__file__).parent.parent.parent

    # Closeout file path
    closeout_dir = atomic_root.parent / ".outputs" / phase_id
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

    write_json(closeout_file, closeout)

    print(f"\n✓ Closeout file created: {closeout_file}")


if __name__ == "__main__":
    import sys

    resume_at = None
    if len(sys.argv) > 1:
        resume_at = sys.argv[1]

    success = run_phase(resume_at)
    sys.exit(0 if success else 1)
