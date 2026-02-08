"""Phase 04 Specification - Task Modules"""

from .task_401_entry_initialization import execute as task_401
from .task_402_agent_selection import execute as task_402
from .task_403_openspec_generation import execute as task_403
from .task_404_tdd_subtask_injection import execute as task_404
from .task_405_phase_audit import execute as task_405
from .task_406_closeout import execute as task_406

__all__ = [
    'task_401',
    'task_402',
    'task_403',
    'task_404',
    'task_405',
    'task_406',
]
