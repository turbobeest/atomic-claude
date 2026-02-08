"""
Phase 02 PRD - Task Modules

This package contains all task execution modules for Phase 02 (PRD).

Tasks:
  201 - Entry Validation
  202 - PRD Setup
  203 - PRD Interview (Optional)
  204 - Agent Selection
  205 - PRD Authoring
  206 - PRD Validation
  206b - PRD Revision (helper)
  207 - PRD Approval
  208 - Phase Audit
  209 - Phase Closeout
"""

# Import execute functions from task modules
from .task_201_entry_validation import execute as task_201
from .task_202_prd_setup import execute as task_202
from .task_203_prd_interview import execute as task_203
from .task_204_agent_selection import execute as task_204
from .task_205_prd_authoring import execute as task_205
from .task_206_prd_validation import execute as task_206
# task_206b is a helper module called by task_206, not a standalone task
from .task_207_prd_approval import execute as task_207
from .task_208_phase_audit import execute as task_208
from .task_209_closeout import execute as task_209

__all__ = [
    'task_201',
    'task_202',
    'task_203',
    'task_204',
    'task_205',
    'task_206',
    'task_207',
    'task_208',
    'task_209',
]
