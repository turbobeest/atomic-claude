#!/usr/bin/env python3
"""
Phase 6 Orchestrator (orchestrator06.py)

Orchestrator for Phase 6: Code Review - Comprehensive code review and refinement.

Tasks:
  601 - Entry initialization
  602 - Agent selection
  603 - Comprehensive review
  604 - Refinement
  605 - Phase audit
  606 - Closeout
"""

import logging
import sys
import os
from pathlib import Path

# Ensure atomic-claude2 root is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)

from orchestration.phase_runner import run_phase_tasks
from core.graph import get_graph

# Import Python task modules
from phases.phase_06_code_review.tasks import (
    task_601,
    task_602,
    task_603,
    task_604,
    task_605,
    task_606,
)

# Environment variables
ATOMIC_ROOT = Path(os.getenv('ATOMIC_ROOT', Path.cwd()))
PROJECT_ROOT = ATOMIC_ROOT.parent
OUTPUT_DIR = Path(os.getenv('ATOMIC_OUTPUT_DIR', PROJECT_ROOT / '.outputs' / '6-code-review'))
UAT_MODE = os.getenv('ATOMIC_UAT_MODE', 'false').lower() == 'true'


# Task wrapper functions (call Python task modules)

def task_601_wrapper(mem=None, **kwargs) -> bool:
    """Task 601: Entry initialization"""
    return task_601(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_602_wrapper(mem=None, **kwargs) -> bool:
    """Task 602: Agent selection"""
    return task_602(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_603_wrapper(mem=None, **kwargs) -> bool:
    """Task 603: Comprehensive review"""
    return task_603(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_604_wrapper(mem=None, **kwargs) -> bool:
    """Task 604: Refinement"""
    return task_604(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_605_wrapper(mem=None, **kwargs) -> bool:
    """Task 605: Phase audit"""
    return task_605(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_606_wrapper(mem=None, **kwargs) -> bool:
    """Task 606: Closeout"""
    return task_606(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def run_phase(resume_at: str = None) -> bool:
    """
    Execute Phase 6: Code Review

    Args:
        resume_at: Optional task ID to resume from (e.g., "603")

    Returns:
        bool: True if phase completed successfully
    """
    phase_id = "6-code-review"

    # Initialize knowledge graph (raises GraphUnavailableError on failure)
    graph = get_graph(phase_id=phase_id)
    graph.ensure_schema()

    # Task list in execution order
    tasks = [
        ("601", "Entry initialization", task_601_wrapper),
        ("602", "Agent selection", task_602_wrapper),
        ("603", "Comprehensive review", task_603_wrapper),
        ("604", "Refinement", task_604_wrapper),
        ("605", "Phase audit", task_605_wrapper),
        ("606", "Closeout", task_606_wrapper),
    ]

    # Expected artifacts per task (relative to OUTPUT_DIR)
    task_artifacts = {
        "601": ["entry-context.json"],
        "602": ["review-agents.json"],
        "603": ["review-report.md", "prompts/code-sample.txt", "prompts/test-sample.txt",
                "prompts/review-code.json", "prompts/review-arch.json",
                "prompts/review-perf.json", "prompts/review-doc.json"],
        "604": ["refinement-report.md"],
        "605": [],
        "606": [],
    }

    return run_phase_tasks(
        phase_num=6,
        phase_name="Code Review",
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
