"""
Phase 09 Release Tasks

All tasks for the Release phase (Phase 9).
"""

from .task_901_entry_initialization import execute as task_901
from .task_902_release_setup import execute as task_902
from .task_903_agent_selection import execute as task_903
from .task_904_release_execution import execute as task_904
from .task_905_release_confirmation import execute as task_905
from .task_906_closeout import execute as task_906

__all__ = [
    'task_901',
    'task_902',
    'task_903',
    'task_904',
    'task_905',
    'task_906',
]
