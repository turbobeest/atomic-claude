"""
Test Runners Module

Provides phase-end test runners for validating atomic-claude phases.

Available Runners:
- ContinuityTestRunner: Validates seamless task-to-task execution
- UATRunner: User experience validation (TUI/UX sniff test) - TBD
- FunctionalTestRunner: 90%+ test coverage validation - TBD
"""

from .continuity_runner import (
    ContinuityTestRunner,
    ContinuityTestReport,
    TaskResult,
    load_phase_config
)

__all__ = [
    "ContinuityTestRunner",
    "ContinuityTestReport",
    "TaskResult",
    "load_phase_config",
]
