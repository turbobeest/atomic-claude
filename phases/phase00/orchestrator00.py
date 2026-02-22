#!/usr/bin/env python3
"""
Phase 0 Orchestrator (orchestrator00.py)

Orchestrator for Phase 0: Setup - Initial configuration and environment setup.

Tasks:
  001 - Environment bootstrap (OS, tools, npm deps, dashboard launch)
  002 - Provider detection (credentials, Ollama hosts, health checks)
  003 - Setup wizard (project identity, type, pipeline config, LLM preferences)
  004 - Material scan & reference organization
  005 - Repository & system setup (agents/audits/skills, git, system capabilities)
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


# Import Phase 00 task modules
from phases.phase_00_setup.tasks import (
    task_001,
    task_002,
    task_003,
    task_004,
    task_005,
)

# Get paths from environment
ATOMIC_ROOT = Path(os.getenv('ATOMIC_ROOT', Path.cwd()))
PROJECT_ROOT = ATOMIC_ROOT.parent
OUTPUT_DIR = Path(os.getenv('ATOMIC_OUTPUT_DIR', PROJECT_ROOT / '.outputs' / '0-setup'))
UAT_MODE = os.getenv('ATOMIC_UAT_MODE', 'false').lower() == 'true'


def run_phase(resume_at: str = None) -> bool:
    """
    Execute Phase 0: Setup

    Args:
        resume_at: Optional task ID to resume from (e.g., "003")

    Returns:
        bool: True if phase completed successfully
    """
    if resume_at:
        phase_header("Phase 0: Setup (resuming)")
    else:
        phase_header("Phase 0: Setup")

        print("  This phase walks you through project setup in 5 steps:")
        print()
        print("    1. Environment bootstrap — OS, tools, npm deps, dashboard launch")
        print("    2. Provider detection    — credentials, Ollama hosts, health checks")
        print("    3. Setup wizard          — project identity, type, pipeline, LLM preferences")
        print("    4. Material scan         — scan, collect references, and organize")
        print("    5. Repository & system   — agents/audits/skills, git, system capabilities")
        print()
        print("  You can quit at any prompt with 'q' and resume later.")
        print()

    state = StateManager()
    phase_id = "0-setup"

    # Register active phase in task-state.json so dashboard always knows
    state.set_current_phase(phase_id)

    # Task list in execution order with expected output artifacts
    tasks = [
        ("001", "Environment bootstrap", task_001_environment_bootstrap),
        ("002", "Provider detection", task_002_provider_detection),
        ("003", "Setup wizard", task_003_setup_wizard),
        ("004", "Material scan", task_004_material_scan),
        ("005", "Repository & system setup", task_005_repository_setup),
    ]

    # Expected artifacts per task (relative to OUTPUT_DIR)
    task_artifacts = {
        "001": ["project-config.json"],
        "002": ["secrets.json", "provider-inventory.json", "project-config.json"],
        "003": ["project-config.json", "extracted-config.json"],
        "004": ["material-manifest.json", "project-config.json"],
        "005": ["env-validation.json", "project-config.json"],
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
                print(f"\n❌ Task {task_id} failed")
                state.mark_task_failed(phase_id, task_id, task_name)
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
            print(f"\n❌ Task {task_id} error: {e}")
            state.mark_task_failed(phase_id, task_id, task_name, str(e))
            log_error(phase_id, task_id, str(e), traceback.format_exc())
            clear_current_task()
            get_resolver().clear_task_overrides()
            return False

    # Phase complete — NOW clear current-task.json
    clear_current_task()
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

def task_001_environment_bootstrap(mem=None) -> bool:
    """Execute task 001: Environment bootstrap."""
    return task_001(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_002_provider_detection(mem=None) -> bool:
    """Execute task 002: Provider detection."""
    return task_002(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_003_setup_wizard(mem=None) -> bool:
    """Execute task 003: Setup wizard."""
    return task_003(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_004_material_scan(mem=None) -> bool:
    """Execute task 004: Material scan & reference organization."""
    return task_004(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_005_repository_setup(mem=None) -> bool:
    """Execute task 005: Repository & system setup."""
    return task_005(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def create_closeout(phase_id: str, tasks: list):
    """Create closeout.json file for phase completion."""
    atomic_root = Path(os.environ.get("ATOMIC_ROOT", Path.cwd()))
    outputs_dir = atomic_root.parent / ".outputs" / phase_id
    outputs_dir.mkdir(parents=True, exist_ok=True)

    closeout = {
        "phase": phase_id,
        "phase_num": 0,
        "status": "complete",
        "completed_at": datetime.now().isoformat(),
        "tasks_completed": [task_id for task_id, _, _ in tasks],
        "summary": "Phase 0 (Setup) completed successfully. Configuration collected and environment prepared."
    }

    closeout_path = outputs_dir / "closeout.json"
    with open(closeout_path, "w") as f:
        json.dump(closeout, f, indent=2)

    print(f"\n✅ Closeout file created: {closeout_path}")


if __name__ == "__main__":
    success = run_phase()
    sys.exit(0 if success else 1)
