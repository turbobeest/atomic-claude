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

import logging
import sys
import os
from pathlib import Path

# Ensure atomic-claude root is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)

from orchestration.phase_runner import run_phase_tasks
from core.graph import get_graph

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
OUTPUT_DIR = Path(os.getenv('ATOMIC_OUTPUT_DIR', ATOMIC_ROOT.parent / '.outputs' / '4-specification'))


def run_phase(resume_at: str = None) -> bool:
    """
    Execute Phase 4: Specification

    Args:
        resume_at: Optional task ID to resume from (e.g., "403")

    Returns:
        bool: True if phase completed successfully
    """
    phase_id = "4-specification"

    # Initialize knowledge graph (raises GraphUnavailableError on failure)
    graph = get_graph(phase_id=phase_id)
    graph.ensure_schema()

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

    return run_phase_tasks(
        phase_num=4,
        phase_name="Specification",
        phase_id=phase_id,
        tasks=tasks,
        task_artifacts=task_artifacts,
        atomic_root=ATOMIC_ROOT,
        output_dir=OUTPUT_DIR,
        resume_at=resume_at,
        graph=graph,
    )


# Task wrapper functions (call Python modules)

def task_401_entry_initialization(mem=None, graph=None) -> bool:
    """Task 401: Entry initialization"""
    return task_401(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)

task_401_entry_initialization.uses_llm = False


def task_402_agent_selection(mem=None, graph=None) -> bool:
    """Task 402: Agent selection"""
    return task_402(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)

task_402_agent_selection.uses_llm = False


def task_403_openspec_generation(mem=None, graph=None) -> bool:
    """Task 403: OpenSpec generation"""
    return task_403(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)

task_403_openspec_generation.model_tier = "opus"


def task_404_tdd_subtask_injection(mem=None, graph=None) -> bool:
    """Task 404: TDD subtask injection"""
    return task_404(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)

task_404_tdd_subtask_injection.model_tier = "opus"


def task_405_phase_audit(mem=None, graph=None) -> bool:
    """Task 405: Phase audit"""
    return task_405(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)


def task_406_closeout(mem=None, graph=None) -> bool:
    """Task 406: Closeout"""
    return task_406(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)


if __name__ == "__main__":
    resume_at = None
    if len(sys.argv) > 1:
        resume_at = sys.argv[1]

    success = run_phase(resume_at)
    sys.exit(0 if success else 1)
