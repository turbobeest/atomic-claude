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

import logging
import sys
import os
from pathlib import Path

# Ensure atomic-claude2 root is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)

from orchestration.phase_runner import run_phase_tasks

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


# Task wrapper functions (call Python task modules)

def task_901_wrapper(mem=None, **kwargs) -> bool:
    """Task 901: Entry initialization"""
    return task_901(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_902_wrapper(mem=None, **kwargs) -> bool:
    """Task 902: Release setup"""
    return task_902(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_903_wrapper(mem=None, **kwargs) -> bool:
    """Task 903: Agent selection"""
    return task_903(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_904_wrapper(mem=None, **kwargs) -> bool:
    """Task 904: Release execution"""
    return task_904(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_905_wrapper(mem=None, **kwargs) -> bool:
    """Task 905: Release confirmation"""
    return task_905(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def task_906_wrapper(mem=None, **kwargs) -> bool:
    """Task 906: Closeout"""
    return task_906(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)


def run_phase(resume_at: str = None) -> bool:
    """
    Execute Phase 9: Release

    Args:
        resume_at: Optional task ID to resume from (e.g., "904")

    Returns:
        bool: True if phase completed successfully
    """
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
        "903": ["release-agents.json", "agents-decision.json"],
        "904": ["execution-decision.json"],
        "905": ["confirmation-decision.json"],
        "906": [],
    }

    return run_phase_tasks(
        phase_num=9,
        phase_name="Release",
        phase_id="9-release",
        tasks=tasks,
        task_artifacts=task_artifacts,
        atomic_root=ATOMIC_ROOT,
        output_dir=OUTPUT_DIR,
        uat_mode=UAT_MODE,
        resume_at=resume_at,
    )


if __name__ == "__main__":
    import sys

    resume_at = None
    if len(sys.argv) > 1:
        resume_at = sys.argv[1]

    success = run_phase(resume_at)
    sys.exit(0 if success else 1)
