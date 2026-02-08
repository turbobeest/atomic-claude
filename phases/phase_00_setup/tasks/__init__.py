"""
Phase 00 Setup - Task Modules

Task implementations for Setup Phase (Phase 0).
"""

from .task_001_mode_selection import execute as task_001
from .task_002_config_collection import execute as task_002
from .task_003_config_review import execute as task_003
from .task_004_api_keys import execute as task_004
from .task_005_material_scan import execute as task_005
from .task_006_reference_materials import execute as task_006
from .task_007_environment_setup import execute as task_007
from .task_008_repository_setup import execute as task_008
from .task_009_environment_check import execute as task_009

__all__ = [
    'task_001',
    'task_002',
    'task_003',
    'task_004',
    'task_005',
    'task_006',
    'task_007',
    'task_008',
    'task_009',
]
