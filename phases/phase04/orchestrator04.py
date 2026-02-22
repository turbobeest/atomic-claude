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
PROJECT_ROOT = ATOMIC_ROOT.parent
OUTPUT_DIR = Path(os.getenv('ATOMIC_OUTPUT_DIR', PROJECT_ROOT / '.outputs' / '4-specification'))
UAT_MODE = os.getenv('ATOMIC_UAT_MODE', 'false').lower() == 'true'


def run_phase(resume_at: str = None) -> bool:
    """
    Execute Phase 4: Specification

    Args:
        resume_at: Optional task ID to resume from (e.g., "403")

    Returns:
        bool: True if phase completed successfully
    """
    if resume_at:
        phase_header("Phase 4: Specification (resuming)")
    else:
        phase_header("Phase 4: Specification")

    state = StateManager()
    phase_id = "4-specification"

    # Initialize knowledge graph (None if disabled/unavailable)
    graph = get_graph(phase_id=phase_id)
    if graph:
        graph.ensure_schema()

    # Register active phase in task-state.json so dashboard always knows
    state.set_current_phase(phase_id)

    # Task list in execution order
    tasks = [
        ("401", "Entry initialization", task_401_entry_initialization),
        ("402", "Agent selection", task_402_agent_selection),
        ("403", "OpenSpec generation", task_403_openspec_generation),
        ("404", "TDD subtask injection", task_404_tdd_subtask_injection),
        ("405", "Phase audit", task_405_phase_audit),
        ("406", "Closeout", task_406_closeout),
    ]

    # Expected artifacts per task (relative to OUTPUT_DIR)
    task_artifacts = {
        "401": ["initialization.json"],
        "402": ["selected-agents.json"],
        "403": ["openspec-generation.json"],
        "404": ["tdd-injection.json"],
        "405": [],  # audit — writes to audits dir, not OUTPUT_DIR
        "406": ["closeout.json"],
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
    phase_complete("Phase 4: Specification")

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

def task_401_entry_initialization(mem=None, graph=None) -> bool:
    """Task 401: Entry initialization"""
    return task_401(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem, graph=graph)


def task_402_agent_selection(mem=None, graph=None) -> bool:
    """Task 402: Agent selection"""
    return task_402(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem, graph=graph)


def task_403_openspec_generation(mem=None, graph=None) -> bool:
    """Task 403: OpenSpec generation"""
    return task_403(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem, graph=graph)


def task_404_tdd_subtask_injection(mem=None, graph=None) -> bool:
    """Task 404: TDD subtask injection"""
    return task_404(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem, graph=graph)


def task_405_phase_audit(mem=None, graph=None) -> bool:
    """Task 405: Phase audit"""
    return task_405(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem, graph=graph)


def task_406_closeout(mem=None, graph=None) -> bool:
    """Task 406: Closeout"""
    return task_406(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem, graph=graph)


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
