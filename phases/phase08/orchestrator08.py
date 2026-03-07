#!/usr/bin/env python3
"""
Phase 8 Orchestrator (orchestrator08.py)

Orchestrator for Phase 8: Deployment Prep - Deployment preparation and artifact generation.

Tasks:
  801 - Entry initialization
  802 - Deployment setup
  803 - Agent selection
  804 - Artifact generation
  805 - Phase audit
  806 - Deployment approval
  807 - Closeout
"""

import logging
import sys
import os
from pathlib import Path

# Ensure atomic-claude root is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)

from orchestration.phase_runner import run_phase_tasks

try:
    from core.graph import get_graph
except ImportError:
    get_graph = None

# Import Python task modules
from phases.phase_08_deployment_prep.tasks import (
    task_801,
    task_802,
    task_803,
    task_804,
    task_805,
    task_806,
    task_807,
)

# Environment variables
ATOMIC_ROOT = Path(os.getenv('ATOMIC_ROOT', Path(__file__).resolve().parent.parent.parent))
OUTPUT_DIR = Path(os.getenv('ATOMIC_OUTPUT_DIR', ATOMIC_ROOT.parent / '.outputs' / '8-deployment-prep'))


# Task wrapper functions (call Python task modules)

def task_801_wrapper(mem=None, graph=None) -> bool:
    """Task 801: Entry initialization"""
    return task_801(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)

task_801_wrapper.uses_llm = False


def task_802_wrapper(mem=None, graph=None) -> bool:
    """Task 802: Deployment setup"""
    return task_802(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)

task_802_wrapper.uses_llm = False


def task_803_wrapper(mem=None, graph=None) -> bool:
    """Task 803: Agent selection"""
    return task_803(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)

task_803_wrapper.uses_llm = False


def task_804_wrapper(mem=None, graph=None) -> bool:
    """Task 804: Artifact generation"""
    return task_804(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)

task_804_wrapper.model_tier = "sonnet"


def task_805_wrapper(mem=None, graph=None) -> bool:
    """Task 805: Phase audit"""
    return task_805(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)


def task_806_wrapper(mem=None, graph=None) -> bool:
    """Task 806: Deployment approval"""
    return task_806(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)

task_806_wrapper.uses_llm = False


def task_807_wrapper(mem=None, graph=None) -> bool:
    """Task 807: Closeout"""
    return task_807(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)


def run_phase(resume_at: str = None) -> bool:
    """
    Execute Phase 8: Deployment Prep

    Args:
        resume_at: Optional task ID to resume from (e.g., "804")

    Returns:
        bool: True if phase completed successfully
    """
    # Task list in execution order
    tasks = [
        ("801", "Entry initialization", task_801_wrapper),
        ("802", "Deployment setup", task_802_wrapper),
        ("803", "Agent selection", task_803_wrapper),
        ("804", "Artifact generation", task_804_wrapper),
        ("805", "Phase audit", task_805_wrapper),
        ("806", "Deployment approval", task_806_wrapper),
        ("807", "Closeout", task_807_wrapper),
    ]

    # Expected artifacts per task (relative to OUTPUT_DIR)
    task_artifacts = {
        "801": [],
        "802": [],
        "803": ["deployment-agents.json"],
        "804": [],
        "805": [],
        "806": [],
        "807": [],
    }

    # Initialize knowledge graph (REQUIRED — graph drives context and decisions)
    graph = None
    if get_graph is not None:
        try:
            graph = get_graph(phase_id="8-deployment-prep")
            graph.ensure_schema()
        except Exception as e:
            logger.error("Graph unavailable for phase 8: %s", e)
            print("  ⚠ FalkorDB knowledge graph is not available!")
            print("    The graph is required for effective context assembly and token efficiency.")
            print("    Run: docker compose up -d falkordb")
            print()
            graph = None

    return run_phase_tasks(
        phase_num=8,
        phase_name="Deployment Prep",
        phase_id="8-deployment-prep",
        tasks=tasks,
        task_artifacts=task_artifacts,
        atomic_root=ATOMIC_ROOT,
        output_dir=OUTPUT_DIR,
        resume_at=resume_at,
        graph=graph,
    )


if __name__ == "__main__":
    resume_at = None
    if len(sys.argv) > 1:
        resume_at = sys.argv[1]

    success = run_phase(resume_at)
    sys.exit(0 if success else 1)
