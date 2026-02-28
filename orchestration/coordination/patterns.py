"""Coordination Patterns — catalog of multi-agent coordination strategies.

Each pattern defines when it's applicable, agent count bounds, gravity
compatibility, and estimated token overhead. The PatternSelector (selector.py)
scores these against task context to pick the best fit.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, Set


class CoordinationPattern(str, Enum):
    """Available coordination patterns."""

    SEQUENTIAL = "sequential"               # Current behavior (default)
    PARALLEL_FAN_OUT = "parallel_fan_out"    # Same task, multiple agents, merge
    REVIEW_LOOP = "review_loop"             # Produce → review → iterate
    PIPELINE_CHAIN = "pipeline_chain"       # Output chains between agents
    ESCALATION = "escalation"               # Cheap agent first, escalate if needed
    DEBATE = "debate"                       # Two propose, third judges
    SAGA = "saga"                           # Multi-step with compensating rollback


@dataclass(frozen=True)
class PatternSpec:
    """Specification for a coordination pattern."""

    name: CoordinationPattern
    description: str
    when_to_use: str
    min_agents: int
    max_agents: int
    compatible_gravity: FrozenSet[str]
    requires_feature_flags: tuple = ()      # Frozen for hashability
    task_categories: FrozenSet[str] = frozenset()  # Empty = all categories
    supports_rollback: bool = False
    estimated_overhead_factor: float = 1.0  # Token cost multiplier


PATTERN_CATALOG: Dict[CoordinationPattern, PatternSpec] = {
    CoordinationPattern.SEQUENTIAL: PatternSpec(
        name=CoordinationPattern.SEQUENTIAL,
        description="Execute task with a single agent (current default behavior)",
        when_to_use="Always valid; baseline for comparison",
        min_agents=1,
        max_agents=1,
        compatible_gravity=frozenset({"light", "standard", "intensive"}),
        supports_rollback=False,
        estimated_overhead_factor=1.0,
    ),
    CoordinationPattern.PARALLEL_FAN_OUT: PatternSpec(
        name=CoordinationPattern.PARALLEL_FAN_OUT,
        description="Run same task with multiple agents in parallel, synthesize results",
        when_to_use="When diverse perspectives improve quality (design, analysis)",
        min_agents=2,
        max_agents=5,
        compatible_gravity=frozenset({"standard", "intensive"}),
        requires_feature_flags=("coordination.fan_out",),
        supports_rollback=False,
        estimated_overhead_factor=2.5,
    ),
    CoordinationPattern.REVIEW_LOOP: PatternSpec(
        name=CoordinationPattern.REVIEW_LOOP,
        description="Produce artifact then have reviewer agent evaluate, iterate up to 3x",
        when_to_use="Code review, spec validation, quality gates",
        min_agents=2,
        max_agents=3,
        compatible_gravity=frozenset({"standard", "intensive"}),
        requires_feature_flags=("coordination.review_loop",),
        task_categories=frozenset({"code_review", "spec_validation", "testing"}),
        supports_rollback=False,
        estimated_overhead_factor=2.0,
    ),
    CoordinationPattern.PIPELINE_CHAIN: PatternSpec(
        name=CoordinationPattern.PIPELINE_CHAIN,
        description="Sequential agent chain where each gets prior agent's output",
        when_to_use="Multi-stage transformations (analyze→design→implement)",
        min_agents=2,
        max_agents=4,
        compatible_gravity=frozenset({"standard", "intensive"}),
        requires_feature_flags=("coordination.pipeline_chain",),
        supports_rollback=False,
        estimated_overhead_factor=1.8,
    ),
    CoordinationPattern.ESCALATION: PatternSpec(
        name=CoordinationPattern.ESCALATION,
        description="Start with cheap model, escalate to expensive if quality insufficient",
        when_to_use="Cost optimization for variable-difficulty tasks",
        min_agents=1,
        max_agents=1,
        compatible_gravity=frozenset({"standard", "intensive"}),
        requires_feature_flags=("coordination.escalation",),
        supports_rollback=False,
        estimated_overhead_factor=1.3,
    ),
    CoordinationPattern.DEBATE: PatternSpec(
        name=CoordinationPattern.DEBATE,
        description="Two agents propose solutions, third judges which is better",
        when_to_use="Architectural decisions, design tradeoffs",
        min_agents=3,
        max_agents=3,
        compatible_gravity=frozenset({"intensive",}),
        requires_feature_flags=("coordination.debate",),
        task_categories=frozenset({"architecture", "design", "security"}),
        supports_rollback=False,
        estimated_overhead_factor=3.0,
    ),
    CoordinationPattern.SAGA: PatternSpec(
        name=CoordinationPattern.SAGA,
        description="Multi-step execution with compensating rollback on failure",
        when_to_use="Complex multi-step tasks where partial failure is costly",
        min_agents=1,
        max_agents=5,
        compatible_gravity=frozenset({"intensive",}),
        requires_feature_flags=("coordination.saga",),
        supports_rollback=True,
        estimated_overhead_factor=1.5,
    ),
}
