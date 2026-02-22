#!/usr/bin/env python3
"""
Phase 5 Orchestrator (orchestrator05.py)

Orchestrator for Phase 5: Implementation - TDD execution and code generation.

Tasks:
  501 - Entry initialization
  502 - TDD setup
  503 - Agent selection
  504 - TDD execution
  505 - Validation
  506 - Phase audit
  507 - Closeout
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
from phases.phase_05_implementation.tasks import (
    task_501_entry_initialization,
    task_502_tdd_setup,
    task_503_agent_selection,
    task_504_tdd_execution,
    task_505_validation,
    task_506_phase_audit,
    task_507_closeout,
)

# Environment variables
ATOMIC_ROOT = Path(os.getenv('ATOMIC_ROOT', Path.cwd()))
PROJECT_ROOT = ATOMIC_ROOT.parent
OUTPUT_DIR = Path(os.getenv('ATOMIC_OUTPUT_DIR', PROJECT_ROOT / '.outputs' / '5-implementation'))
UAT_MODE = os.getenv('ATOMIC_UAT_MODE', 'false').lower() == 'true'


def run_phase(resume_at: str = None) -> bool:
    """
    Execute Phase 5: Implementation

    Args:
        resume_at: Optional task ID to resume from (e.g., "503")

    Returns:
        bool: True if phase completed successfully
    """
    if resume_at:
        phase_header("Phase 5: Implementation (resuming)")
    else:
        phase_header("Phase 5: Implementation")

    state = StateManager()
    phase_id = "5-implementation"

    # Register active phase in task-state.json so dashboard always knows
    state.set_current_phase(phase_id)

    # Task list in execution order
    tasks = [
        ("501", "Entry initialization", task_501_wrapper),
        ("502", "TDD setup", task_502_wrapper),
        ("503", "Agent selection", task_503_wrapper),
        ("504", "TDD execution", task_504_wrapper),
        ("505", "Validation", task_505_wrapper),
        ("506", "Phase audit", task_506_wrapper),
        ("507", "Closeout", task_507_wrapper),
    ]

    # Expected artifacts per task (relative to OUTPUT_DIR)
    task_artifacts = {
        "501": ["initialization.json"],
        "502": ["tdd-setup.json"],
        "503": ["selected-agents.json"],
        "504": ["tdd-progress.json"],
        "505": [],  # validation — writes to .claude/testing/, not OUTPUT_DIR
        "506": [],  # audit — writes to audits dir, not OUTPUT_DIR
        "507": [],  # closeout — writes to .claude/closeout/
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
    phase_complete("Phase 5: Implementation")

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

def task_501_wrapper(mem=None) -> bool:
    """Task 501: Entry initialization"""
    return task_501_entry_initialization.execute(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_502_wrapper(mem=None) -> bool:
    """Task 502: TDD setup"""
    return task_502_tdd_setup.execute(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_503_wrapper(mem=None) -> bool:
    """Task 503: Agent selection"""
    return task_503_agent_selection.execute(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_504_wrapper(mem=None) -> bool:
    """Task 504: TDD execution"""
    return task_504_tdd_execution.execute(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_505_wrapper(mem=None) -> bool:
    """Task 505: Validation"""
    return task_505_validation.execute(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_506_wrapper(mem=None) -> bool:
    """Task 506: Phase audit"""
    return task_506_phase_audit.execute(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_507_wrapper(mem=None) -> bool:
    """Task 507: Closeout"""
    return task_507_closeout.execute(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def create_closeout(phase_id: str, tasks: list):
    """
    Create phase closeout file.

    Args:
        phase_id: Phase identifier (e.g., "5-implementation")
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
            "implementation": "TDD-driven code implementation complete",
            "test_results": "All tests passing",
            "agent_roster": "Selected implementation agents"
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
