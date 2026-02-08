"""
Phase 03 Tasking - Task Modules

This package contains all task execution modules for Phase 3: Tasking.

Tasks:
  301 - Entry & Initialization
  302 - Agent Selection
  303 - Task Decomposition
  304 - Dependency Analysis
  305 - Phase Audit
  306 - Phase Closeout
"""

from pathlib import Path

# Task module imports
from .task_301_entry_initialization import execute as task_301
from .task_302_agent_selection import execute as task_302
from .task_303_task_decomposition import execute as task_303
from .task_304_dependency_analysis import execute as task_304
from .task_305_phase_audit import execute as task_305
from .task_306_closeout import execute as task_306

__all__ = [
    'task_301',
    'task_302',
    'task_303',
    'task_304',
    'task_305',
    'task_306',
]
