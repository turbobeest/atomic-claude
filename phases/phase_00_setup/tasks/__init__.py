"""
Phase 00 Setup - Task Modules

Task implementations for Setup Phase (Phase 0).
"""

from .task_001_environment_bootstrap import execute as task_001
from .task_002_provider_detection import execute as task_002
from .task_003_setup_wizard import execute as task_003
from .task_004_material_scan import execute as task_004
from .task_005_repository_setup import execute as task_005

__all__ = [
    'task_001',
    'task_002',
    'task_003',
    'task_004',
    'task_005',
]
