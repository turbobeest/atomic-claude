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

import logging
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

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
from core.graph import get_graph


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
PROJECT_ROOT = ATOMIC_ROOT.parent
OUTPUT_DIR = Path(os.getenv('ATOMIC_OUTPUT_DIR', PROJECT_ROOT / '.outputs' / '3-tasking'))
UAT_MODE = os.getenv('ATOMIC_UAT_MODE', 'false').lower() == 'true'


def run_phase(resume_at: str = None) -> bool:
    """
    Execute Phase 3: Tasking

    Args:
        resume_at: Optional task ID to resume from (e.g., "304")

    Returns:
        bool: True if phase completed successfully
    """
    if resume_at:
        phase_header("Phase 3: Tasking (resuming)")
    else:
        phase_header("Phase 3: Tasking")

    state = StateManager()
    phase_id = "3-tasking"

    # Initialize knowledge graph (raises GraphUnavailableError on failure)
    graph = get_graph(phase_id=phase_id)
    graph.ensure_schema()

    # Register active phase in task-state.json so dashboard always knows
    state.set_current_phase(phase_id)

    # Task list in execution order
    tasks = [
        ("301", "Entry initialization", task_301_entry_initialization),
        ("302", "Agent selection", task_302_agent_selection),
        ("303", "Task decomposition", task_303_task_decomposition),
        ("304", "Dependency analysis", task_304_dependency_analysis),
        ("305", "Phase audit", task_305_phase_audit),
        ("306", "Closeout", task_306_closeout),
    ]

    # Expected artifacts per task (relative to OUTPUT_DIR)
    task_artifacts = {
        "301": ["entry-validation.json"],
        "302": ["selected-agents.json", "prd-analysis.json"],
        "303": ["raw-tasks.json", "prompts/task-decomposition.md"],
        "304": ["dependency-analysis.json"],
        "305": [],  # audit — writes to audits dir, not OUTPUT_DIR
        "306": [],  # closeout — writes to project .claude/closeout/
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
            success = task_func(mem, graph=graph)
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
    phase_complete("Phase 3: Tasking")

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


# Task wrapper functions (call Python modules)

def task_301_entry_initialization(mem=None, graph=None) -> bool:
    """Task 301: Entry initialization"""
    return task_301(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem, graph=graph)


def task_302_agent_selection(mem=None, graph=None) -> bool:
    """Task 302: Agent selection"""
    return task_302(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem, graph=graph)


def task_303_task_decomposition(mem=None, graph=None) -> bool:
    """Task 303: Task decomposition"""
    return task_303(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem, graph=graph)


def task_304_dependency_analysis(mem=None, graph=None) -> bool:
    """Task 304: Dependency analysis"""
    return task_304(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem, graph=graph)


def task_305_phase_audit(mem=None, graph=None) -> bool:
    """Task 305: Phase audit"""
    return task_305(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem, graph=graph)


def task_306_closeout(mem=None, graph=None) -> bool:
    """Task 306: Closeout"""
    return task_306(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem, graph=graph)


def create_closeout(phase_id: str, tasks: list):
    """
    Create phase closeout file.

    Args:
        phase_id: Phase identifier (e.g., "3-tasking")
        tasks: List of (task_id, task_name, task_func) tuples
    """
    atomic_root = Path(os.environ.get("ATOMIC_ROOT", Path.cwd()))
    output_dir = atomic_root.parent / ".outputs" / phase_id
    output_dir.mkdir(parents=True, exist_ok=True)

    closeout_file = output_dir / "closeout.json"

    # Extract phase number from phase_id (e.g., "3-tasking" -> 3)
    phase_num = int(phase_id.split("-")[0])

    # Get list of completed task IDs
    completed_tasks = [task_id for task_id, _, _ in tasks]

    closeout_data = {
        "phase": phase_id,
        "phase_num": phase_num,
        "completed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z"),
        "status": "complete",
        "tasks_completed": completed_tasks,
        "summary": f"Phase {phase_num} ({phase_id.split('-', 1)[1].title()}) completed successfully."
    }

    write_json(closeout_file, closeout_data)

    print(f"\n✅ Phase {phase_num} closeout: {closeout_file}")


if __name__ == "__main__":
    success = run_phase()
    sys.exit(0 if success else 1)
