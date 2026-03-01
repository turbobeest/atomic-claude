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

import logging
import sys
import os
from pathlib import Path

# Ensure atomic-claude root is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)

from orchestration.phase_runner import run_phase_tasks

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
OUTPUT_DIR = Path(os.getenv('ATOMIC_OUTPUT_DIR', ATOMIC_ROOT.parent / '.outputs' / '0-setup'))


def _print_setup_description():
    """Print phase description after header (first run only)."""
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


def run_phase(resume_at: str = None) -> bool:
    """
    Execute Phase 0: Setup

    Args:
        resume_at: Optional task ID to resume from (e.g., "003")

    Returns:
        bool: True if phase completed successfully
    """
    # Task list in execution order
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

    return run_phase_tasks(
        phase_num=0,
        phase_name="Setup",
        phase_id="0-setup",
        tasks=tasks,
        task_artifacts=task_artifacts,
        atomic_root=ATOMIC_ROOT,
        output_dir=OUTPUT_DIR,
        resume_at=resume_at,
        pre_header_fn=_print_setup_description,
    )


# Task wrapper functions (call Python modules)

def task_001_environment_bootstrap(mem=None) -> bool:
    """Execute task 001: Environment bootstrap."""
    return task_001(ATOMIC_ROOT, OUTPUT_DIR, mem=mem)
task_001_environment_bootstrap.uses_llm = False


def task_002_provider_detection(mem=None) -> bool:
    """Execute task 002: Provider detection."""
    return task_002(ATOMIC_ROOT, OUTPUT_DIR, mem=mem)
task_002_provider_detection.uses_llm = False


def task_003_setup_wizard(mem=None) -> bool:
    """Execute task 003: Setup wizard."""
    return task_003(ATOMIC_ROOT, OUTPUT_DIR, mem=mem)

task_003_setup_wizard.model_tier = "haiku"


def task_004_material_scan(mem=None) -> bool:
    """Execute task 004: Material scan & reference organization."""
    return task_004(ATOMIC_ROOT, OUTPUT_DIR, mem=mem)
task_004_material_scan.uses_llm = False


def task_005_repository_setup(mem=None) -> bool:
    """Execute task 005: Repository & system setup."""
    return task_005(ATOMIC_ROOT, OUTPUT_DIR, mem=mem)
task_005_repository_setup.uses_llm = False


if __name__ == "__main__":
    success = run_phase()
    sys.exit(0 if success else 1)
