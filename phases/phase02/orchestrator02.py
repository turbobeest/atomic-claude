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
  207 - PRD approval
  208 - Phase audit
  209 - Closeout
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
OUTPUT_DIR = Path(os.getenv('ATOMIC_OUTPUT_DIR', ATOMIC_ROOT.parent / '.outputs' / '2-prd'))


def run_phase(resume_at: str = None) -> bool:
    """
    Execute Phase 2: PRD

    Args:
        resume_at: Optional task ID to resume from (e.g., "204")

    Returns:
        bool: True if phase completed successfully
    """
    phase_id = "2-prd"

    # Initialize knowledge graph (raises GraphUnavailableError on failure)
    graph = get_graph(phase_id=phase_id)
    graph.ensure_schema()

    # Task list in execution order
    tasks = [
        ("201", "Entry validation", task_201_entry_validation),
        ("202", "PRD setup", task_202_prd_setup),
        ("203", "PRD interview", task_203_prd_interview),
        ("204", "Agent selection", task_204_agent_selection),
        ("205", "PRD authoring", task_205_prd_authoring),
        ("206", "PRD validation", task_206_prd_validation),
        ("207", "PRD approval", task_207_prd_approval),
        ("208", "Phase audit", task_208_phase_audit),
        ("209", "Closeout", task_209_closeout),
    ]

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

    return run_phase_tasks(
        phase_num=2,
        phase_name="PRD",
        phase_id=phase_id,
        tasks=tasks,
        task_artifacts=task_artifacts,
        atomic_root=ATOMIC_ROOT,
        output_dir=OUTPUT_DIR,
        resume_at=resume_at,
        graph=graph,
    )


# Task wrapper functions (call Python modules)

def task_201_entry_validation(mem=None, graph=None) -> bool:
    """Task 201: Entry validation"""
    return task_201(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)

task_201_entry_validation.uses_llm = False


def task_202_prd_setup(mem=None, graph=None) -> bool:
    """Task 202: PRD setup"""
    return task_202(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)

task_202_prd_setup.uses_llm = False


def task_203_prd_interview(mem=None, graph=None) -> bool:
    """Task 203: PRD interview"""
    return task_203(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)

task_203_prd_interview.uses_llm = False


def task_204_agent_selection(mem=None, graph=None) -> bool:
    """Task 204: Agent selection"""
    return task_204(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)

task_204_agent_selection.uses_llm = False


def task_205_prd_authoring(mem=None, graph=None) -> bool:
    """Task 205: PRD authoring"""
    return task_205(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)

task_205_prd_authoring.model_tier = "opus"


def task_206_prd_validation(mem=None, graph=None) -> bool:
    """Task 206: PRD validation"""
    return task_206(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)

task_206_prd_validation.model_tier = "sonnet"


# task_206b is a helper module called internally by task_206 when validation fails
# It doesn't need a wrapper function here


def task_207_prd_approval(mem=None, graph=None) -> bool:
    """Task 207: PRD approval"""
    return task_207(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)

task_207_prd_approval.model_tier = "opus"


def task_208_phase_audit(mem=None, graph=None) -> bool:
    """Task 208: Phase audit"""
    return task_208(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)


def task_209_closeout(mem=None, graph=None) -> bool:
    """Task 209: Closeout"""
    return task_209(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)


if __name__ == "__main__":
    success = run_phase()
    sys.exit(0 if success else 1)
