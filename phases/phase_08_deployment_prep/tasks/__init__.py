"""
Phase 8 Deployment Prep - Task modules.
"""

from .task_801_entry_initialization import execute as task_801
from .task_802_deployment_setup import execute as task_802
from .task_803_agent_selection import execute as task_803
from .task_804_artifact_generation import execute as task_804
from .task_805_phase_audit import execute as task_805
from .task_806_deployment_approval import execute as task_806
from .task_807_closeout import execute as task_807

__all__ = [
    'task_801',
    'task_802',
    'task_803',
    'task_804',
    'task_805',
    'task_806',
    'task_807',
]
