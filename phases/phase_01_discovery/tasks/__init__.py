"""
Phase 01 Discovery - Task Modules

Task implementations for Discovery Phase (Phase 1).
"""

from .task_101_entry_validation import execute as task_101
from .task_102_corpus_collection import execute as task_102
from .task_103_import_requirements import execute as task_103
from .task_104_agent_selection import execute as task_104
from .task_105_opening_dialogue import execute as task_105
from .task_106_discovery_work import execute as task_106
from .task_107_approach_selection import execute as task_107
from .task_108_discovery_diagrams import execute as task_108
from .task_109_phase_audit import execute as task_109
from .task_110_closeout import execute as task_110

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
    'task_110',
]
