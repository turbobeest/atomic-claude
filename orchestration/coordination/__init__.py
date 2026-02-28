"""Coordination — multi-agent task coordination patterns.

Provides pattern selection and execution for tasks that benefit from
parallel agents, review loops, escalation chains, or debate workflows.
"""

from orchestration.coordination.patterns import CoordinationPattern, PatternSpec, PATTERN_CATALOG

__all__ = [
    "CoordinationPattern",
    "PatternSpec",
    "PATTERN_CATALOG",
]
