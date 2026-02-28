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

# Ensure atomic-claude root is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)

from orchestration.phase_runner import run_phase_tasks
from core.graph import get_graph

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


# Task wrapper functions (call Python task modules)

def task_701_wrapper(mem=None, **kwargs) -> bool:
    """Task 701: Entry initialization"""
    return task_701(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_702_wrapper(mem=None, **kwargs) -> bool:
    """Task 702: Integration setup"""
    return task_702(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_703_wrapper(mem=None, **kwargs) -> bool:
    """Task 703: Agent selection"""
    return task_703(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_704_wrapper(mem=None, **kwargs) -> bool:
    """Task 704: Testing execution"""
    return task_704(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_705_wrapper(mem=None, **kwargs) -> bool:
    """Task 705: Integration approval"""
    return task_705(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_706_wrapper(mem=None, **kwargs) -> bool:
    """Task 706: Phase audit"""
    return task_706(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem, graph=kwargs.get("graph"))


def task_707_wrapper(mem=None, **kwargs) -> bool:
    """Task 707: Closeout"""
    return task_707(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def run_phase(resume_at: str = None) -> bool:
    """
    Execute Phase 7: Integration

    Args:
        resume_at: Optional task ID to resume from (e.g., "704")

    Returns:
        bool: True if phase completed successfully
    """
    phase_id = "7-integration"

    # Initialize knowledge graph (raises GraphUnavailableError on failure)
    graph = get_graph(phase_id=phase_id)
    graph.ensure_schema()

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
        "702": ["integration-setup.json"],
        "703": ["integration-agents.json"],
        "704": ["integration-test-results.json"],
        "705": [],
        "706": [],
        "707": [],
    }

    return run_phase_tasks(
        phase_num=7,
        phase_name="Integration",
        phase_id=phase_id,
        tasks=tasks,
        task_artifacts=task_artifacts,
        atomic_root=ATOMIC_ROOT,
        output_dir=OUTPUT_DIR,
        uat_mode=UAT_MODE,
        resume_at=resume_at,
        graph=graph,
    )


if __name__ == "__main__":
    import sys

    resume_at = None
    if len(sys.argv) > 1:
        resume_at = sys.argv[1]

    success = run_phase(resume_at)
    sys.exit(0 if success else 1)
