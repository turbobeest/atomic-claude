#!/usr/bin/env python3
"""
Phase 2 Orchestrator (orchestrator02.py)

Orchestrator for Phase 2: PRD - Product Requirements Document authoring and validation.

Tasks:
  201 - Entry validation
  202 - PRD setup
  203 - PRD interview
  204 - Agent selection
  205 - PRD authoring
  206 - PRD validation
  206b - PRD revision (conditional - only if 206 fails)
  207 - PRD approval
  208 - Phase audit
  209 - Closeout
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


# Import Phase 02 task modules
from phases.phase_02_prd.tasks import (
    task_201,
    task_202,
    task_203,
    task_204,
    task_205,
    task_206,
    # task_206b is a helper called by task_206, not imported here
    task_207,
    task_208,
    task_209,
)

# Get paths from environment
ATOMIC_ROOT = Path(os.getenv('ATOMIC_ROOT', Path.cwd()))
PROJECT_ROOT = ATOMIC_ROOT.parent
OUTPUT_DIR = Path(os.getenv('ATOMIC_OUTPUT_DIR', PROJECT_ROOT / '.outputs' / '2-prd'))
UAT_MODE = os.getenv('ATOMIC_UAT_MODE', 'false').lower() == 'true'


def run_phase(resume_at: str = None) -> bool:
    """
    Execute Phase 2: PRD

    Args:
        resume_at: Optional task ID to resume from (e.g., "204")

    Returns:
        bool: True if phase completed successfully
    """
    if resume_at:
        phase_header("Phase 2: PRD (resuming)")
    else:
        phase_header("Phase 2: PRD")

    state = StateManager()
    phase_id = "2-prd"

    # Initialize knowledge graph (None if disabled/unavailable)
    graph = get_graph(phase_id=phase_id)
    if graph:
        graph.ensure_schema()

    # Register active phase in task-state.json so dashboard always knows
    state.set_current_phase(phase_id)

    # Expected artifacts per task (relative to OUTPUT_DIR)
    task_artifacts = {
        "201": ["phase1-context.json"],
        "202": ["prd-setup.json"],
        "203": ["prd-interview.json"],
        "204": ["selected-agents.json"],
        "205": [],  # PRD written to docs/prd/PRD.md (outside OUTPUT_DIR)
        "206": ["prd-validation.json"],
        "207": ["prd-approved.json"],
        "208": [],  # Audit written to .claude/audit/ (outside OUTPUT_DIR)
        "209": [],  # Closeout written to .claude/closeout/ (outside OUTPUT_DIR)
    }

    # Task list in execution order
    tasks = [
        ("201", "Entry validation", task_201_entry_validation),
        ("202", "PRD setup", task_202_prd_setup),
        ("203", "PRD interview", task_203_prd_interview),
        ("204", "Agent selection", task_204_agent_selection),
        ("205", "PRD authoring", task_205_prd_authoring),
        ("206", "PRD validation", task_206_prd_validation),
        # 206b is a helper called by 206 when validation fails, not a standalone task
        ("207", "PRD approval", task_207_prd_approval),
        ("208", "Phase audit", task_208_phase_audit),
        ("209", "Closeout", task_209_closeout),
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

        # Skip 206b unless 206 failed
        if task_id == "206b":
            # Check if Task 206 passed - if so, skip 206b
            if state.is_task_complete(phase_id, "206"):
                print(f"✓ Task 206 passed validation, skipping 206b")
                continue
            # If 206 is NOT complete, it means it failed, so run 206b

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
                # Special handling for Task 206: Don't fail the phase, proceed to 206b
                if task_id == "206":
                    print(f"\n⚠️  Task 206 validation failed - will proceed to Task 206b for revision")
                    clear_current_task()
                    get_resolver().clear_task_overrides()
                    continue

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
    phase_complete("Phase 2: PRD")

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

def task_201_entry_validation(mem=None, graph=None) -> bool:
    """Task 201: Entry validation"""
    return task_201(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem, graph=graph)


def task_202_prd_setup(mem=None, graph=None) -> bool:
    """Task 202: PRD setup"""
    return task_202(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem, graph=graph)


def task_203_prd_interview(mem=None, graph=None) -> bool:
    """Task 203: PRD interview"""
    return task_203(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem, graph=graph)


def task_204_agent_selection(mem=None, graph=None) -> bool:
    """Task 204: Agent selection"""
    return task_204(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem, graph=graph)


def task_205_prd_authoring(mem=None, graph=None) -> bool:
    """Task 205: PRD authoring"""
    return task_205(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem, graph=graph)


def task_206_prd_validation(mem=None, graph=None) -> bool:
    """Task 206: PRD validation"""
    return task_206(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem, graph=graph)


# task_206b is a helper module called internally by task_206 when validation fails
# It doesn't need a wrapper function here


def task_207_prd_approval(mem=None, graph=None) -> bool:
    """Task 207: PRD approval"""
    return task_207(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem, graph=graph)


def task_208_phase_audit(mem=None, graph=None) -> bool:
    """Task 208: Phase audit"""
    return task_208(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem, graph=graph)


def task_209_closeout(mem=None, graph=None) -> bool:
    """Task 209: Closeout"""
    return task_209(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem, graph=graph)


def create_closeout(phase_id: str, tasks: list):
    """
    Create phase closeout file.

    Args:
        phase_id: Phase identifier (e.g., "2-prd")
        tasks: List of (task_id, task_name, task_func) tuples
    """
    import os

    atomic_root = Path(os.environ.get("ATOMIC_ROOT", Path.cwd()))
    output_dir = atomic_root.parent / ".outputs" / phase_id
    output_dir.mkdir(parents=True, exist_ok=True)

    closeout_file = output_dir / "closeout.json"

    # Extract phase number from phase_id (e.g., "2-prd" -> 2)
    phase_num = int(phase_id.split("-")[0])

    # Get list of completed task IDs
    completed_tasks = [task_id for task_id, _, _ in tasks]

    closeout_data = {
        "phase": phase_id,
        "phase_num": phase_num,
        "completed_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "status": "complete",
        "tasks_completed": completed_tasks,
        "summary": f"Phase {phase_num} ({phase_id.split('-', 1)[1].upper()}) completed successfully."
    }

    with open(closeout_file, "w") as f:
        json.dump(closeout_data, f, indent=2)

    print(f"\n✅ Phase {phase_num} closeout: {closeout_file}")


if __name__ == "__main__":
    success = run_phase()
    sys.exit(0 if success else 1)
