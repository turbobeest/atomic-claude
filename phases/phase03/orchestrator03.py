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

# Ensure atomic-claude root is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)

from orchestration.phase_runner import run_phase_tasks
from core.graph import get_graph

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
    phase_id = "3-tasking"

    # Initialize knowledge graph (raises GraphUnavailableError on failure)
    graph = get_graph(phase_id=phase_id)
    graph.ensure_schema()

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

    return run_phase_tasks(
        phase_num=3,
        phase_name="Tasking",
        phase_id=phase_id,
        tasks=tasks,
        task_artifacts=task_artifacts,
        atomic_root=ATOMIC_ROOT,
        output_dir=OUTPUT_DIR,
        uat_mode=UAT_MODE,
        resume_at=resume_at,
        graph=graph,
    )


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


if __name__ == "__main__":
    success = run_phase()
    sys.exit(0 if success else 1)
