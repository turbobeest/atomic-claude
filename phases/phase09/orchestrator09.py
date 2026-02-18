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

import traceback

from core.state import StateManager
from core.ui import phase_header, phase_complete
from core.memory import memory_save, MemoryEntryType
from orchestration.pre_task_validation import validate_directory_pristine
from orchestration.dashboard_sync import write_current_task, clear_current_task, log_error, ensure_dashboard
from orchestration.memory_enrichment import summarize_task_artifacts, enrich_memory_with_llm
from orchestration.task_memory import TaskMemory
from orchestration.task_display import display_task_roster, resolve_agent_roster, is_infrastructure_task
from core.llm.resolver import resolve_model, get_resolver


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
PROJECT_ROOT = ATOMIC_ROOT.parent
OUTPUT_DIR = Path(os.getenv('ATOMIC_OUTPUT_DIR', PROJECT_ROOT / '.outputs' / '9-release'))
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

    # Register active phase in task-state.json so dashboard always knows
    state.set_current_phase(phase_id)

    # Task list in execution order
    tasks = [
        ("901", "Entry initialization", task_901_wrapper),
        ("902", "Release setup", task_902_wrapper),
        ("903", "Agent selection", task_903_wrapper),
        ("904", "Release execution", task_904_wrapper),
        ("905", "Release confirmation", task_905_wrapper),
        ("906", "Closeout", task_906_wrapper),
    ]

    # Expected artifacts per task (relative to OUTPUT_DIR)
    task_artifacts = {
        "901": ["entry-decision.json"],
        "902": ["setup-decision.json"],
        "903": ["release-agents.json", "selected-agents.json", "agents-decision.json"],
        "904": ["execution-decision.json"],
        "905": ["confirmation-decision.json"],
        "906": [],
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
            except Exception:
                pass  # Memory save failure is non-blocking

        except Exception as e:
            state.mark_task_failed(phase_id, task_id, task_name, str(e))
            log_error(phase_id, task_id, str(e), traceback.format_exc())
            print(f"\n❌ Task {task_id} error: {e}")
            clear_current_task()
            get_resolver().clear_task_overrides()
            return False

    # Phase complete — NOW clear current-task.json
    clear_current_task()
    phase_complete("Phase 9: Release")

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

def task_901_wrapper(mem=None) -> bool:
    """Task 901: Entry initialization"""
    return task_901(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_902_wrapper(mem=None) -> bool:
    """Task 902: Release setup"""
    return task_902(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_903_wrapper(mem=None) -> bool:
    """Task 903: Agent selection"""
    return task_903(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_904_wrapper(mem=None) -> bool:
    """Task 904: Release execution"""
    return task_904(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_905_wrapper(mem=None) -> bool:
    """Task 905: Release confirmation"""
    return task_905(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_906_wrapper(mem=None) -> bool:
    """Task 906: Closeout"""
    return task_906(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def create_closeout(phase_id: str, tasks: list):
    """Create closeout.json file for phase completion."""
    atomic_root = Path(os.environ.get("ATOMIC_ROOT", Path.cwd()))
    outputs_dir = atomic_root.parent / ".outputs" / phase_id
    outputs_dir.mkdir(parents=True, exist_ok=True)

    closeout = {
        "phase": phase_id,
        "phase_num": 9,
        "status": "complete",
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
