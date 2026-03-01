#!/usr/bin/env python3
"""
Phase 1 Orchestrator (orchestrator01.py)

Orchestrator for Phase 1: Discovery - Requirements gathering and agent selection.

Tasks:
  101 - Entry validation & corpus analysis
  102 - Import requirements
  103 - Agent selection
  104 - Opening dialogue
  105 - Discovery work
  106 - Approach selection
  107 - Discovery diagrams
  108 - Phase audit
  109 - Closeout
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

# Import Phase 01 task modules
from phases.phase_01_discovery.tasks import (
    task_101,
    task_102,
    task_103,
    task_104,
    task_105,
    task_106,
    task_107,
    task_108,
    task_109,
)

# Get paths from environment
ATOMIC_ROOT = Path(os.getenv('ATOMIC_ROOT', Path.cwd()))
OUTPUT_DIR = Path(os.getenv('ATOMIC_OUTPUT_DIR', ATOMIC_ROOT.parent / '.outputs' / '1-discovery'))


def run_phase(resume_at: str = None) -> bool:
    """
    Execute Phase 1: Discovery

    Args:
        resume_at: Optional task ID to resume from (e.g., "104")

    Returns:
        bool: True if phase completed successfully
    """
    phase_id = "1-discovery"

    # Initialize knowledge graph (optional — graceful degradation if unavailable)
    graph = None
    try:
        graph = get_graph(phase_id=phase_id)
        if graph:
            graph.ensure_schema()
    except Exception as e:
        logger.warning("Knowledge graph unavailable for Phase 1: %s", e)
        graph = None

    # Task list in execution order
    tasks = [
        ("101", "Entry validation & corpus analysis", task_101_entry_validation),
        ("102", "Import requirements", task_102_import_requirements),
        ("103", "Agent selection", task_103_agent_selection),
        ("104", "Opening dialogue", task_104_opening_dialogue),
        ("105", "Discovery work", task_105_discovery_work),
        ("106", "Approach selection", task_106_approach_selection),
        ("107", "Discovery diagrams", task_107_discovery_diagrams),
        ("108", "Phase audit", task_108_phase_audit),
        ("109", "Closeout", task_109_closeout),
    ]

    # Expected artifacts per task (relative to OUTPUT_DIR)
    task_artifacts = {
        "101": ["corpus-analysis.md", "corpus.json", "CORPUS-INDEX.md"],
        "102": ["needs-index.json"],
        "103": ["selected-agents.json", "agent-roster.json", "agent-selection-log.md"],
        "104": ["dialogue.json", "conversation-log.md"],
        "105": ["approaches.json", "consensus.json", "deliberation-log.md", "ingested-context.md"],
        "106": ["selected-approach.json", "selected-approach.md"],
        "107": [],  # Diagrams write to docs/diagrams/, not OUTPUT_DIR
        "108": [],  # Audit writes to .outputs/audits/, not OUTPUT_DIR
        "109": [],  # Closeout writes to .claude/closeout/, not OUTPUT_DIR
    }

    return run_phase_tasks(
        phase_num=1,
        phase_name="Discovery",
        phase_id=phase_id,
        tasks=tasks,
        task_artifacts=task_artifacts,
        atomic_root=ATOMIC_ROOT,
        output_dir=OUTPUT_DIR,
        resume_at=resume_at,
        graph=graph,
    )


# Task wrapper functions (call Python modules)

def task_101_entry_validation(mem=None, graph=None) -> bool:
    """Task 101: Entry validation & corpus analysis"""
    return task_101(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)


def task_102_import_requirements(mem=None, graph=None) -> bool:
    """Task 102: Import requirements"""
    return task_102(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)


def task_103_agent_selection(mem=None, graph=None) -> bool:
    """Task 103: Agent selection"""
    return task_103(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)


def task_104_opening_dialogue(mem=None, graph=None) -> bool:
    """Task 104: Opening dialogue"""
    return task_104(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)


def task_105_discovery_work(mem=None, graph=None) -> bool:
    """Task 105: Discovery work"""
    return task_105(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)


def task_106_approach_selection(mem=None, graph=None) -> bool:
    """Task 106: Approach selection"""
    return task_106(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)


def task_107_discovery_diagrams(mem=None, graph=None) -> bool:
    """Task 107: Discovery diagrams"""
    return task_107(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)


def task_108_phase_audit(mem=None, graph=None) -> bool:
    """Task 108: Phase audit"""
    return task_108(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)


def task_109_closeout(mem=None, graph=None) -> bool:
    """Task 109: Closeout"""
    return task_109(ATOMIC_ROOT, OUTPUT_DIR, mem=mem, graph=graph)


if __name__ == "__main__":
    success = run_phase()
    sys.exit(0 if success else 1)
