"""
Phase 01 Discovery - Task Modules

Task implementations for Discovery Phase (Phase 1).
"""

from .task_101_entry_validation import execute as task_101
from .task_102_import_requirements import execute as task_102
from .task_103_agent_selection import execute as task_103
from .task_104_opening_dialogue import execute as task_104
from .task_105_discovery_work import execute as task_105
from .task_106_approach_selection import execute as task_106
from .task_107_discovery_diagrams import execute as task_107
from .task_108_phase_audit import execute as task_108
from .task_109_closeout import execute as task_109

__all__ = [
    'task_101',
    'task_102',
    'task_103',
    'task_104',
    'task_105',
    'task_106',
    'task_107',
    'task_108',
    'task_109',
]
