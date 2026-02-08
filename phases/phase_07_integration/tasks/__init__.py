"""
Phase 7 Integration Tasks

All task modules for Phase 7 (Integration).
"""

from pathlib import Path

# Task module imports
from .task_701_entry_initialization import execute as task_701
from .task_702_integration_setup import execute as task_702
from .task_703_agent_selection import execute as task_703
from .task_704_testing_execution import execute as task_704
from .task_705_integration_approval import execute as task_705
from .task_706_phase_audit import execute as task_706
from .task_707_closeout import execute as task_707

__all__ = [
    'task_701',
    'task_702',
    'task_703',
    'task_704',
    'task_705',
    'task_706',
    'task_707',
]
