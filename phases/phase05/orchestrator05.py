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

import logging
import sys
import os
from pathlib import Path

# Ensure atomic-claude2 root is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)

from orchestration.phase_runner import run_phase_tasks

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


def run_phase(resume_at: str = None) -> bool:
    """
    Execute Phase 5: Implementation

    Args:
        resume_at: Optional task ID to resume from (e.g., "503")

    Returns:
        bool: True if phase completed successfully
    """
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

    return run_phase_tasks(
        phase_num=5,
        phase_name="Implementation",
        phase_id="5-implementation",
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
