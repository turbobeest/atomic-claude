"""Pattern Executors — execution engines for coordination patterns.

Each executor implements BasePatternExecutor for a specific
CoordinationPattern. The top-level ``execute_with_pattern()`` dispatches
to the correct executor and falls back to SEQUENTIAL on error.
"""

import logging
from typing import Optional

from orchestration.coordination.patterns import CoordinationPattern
from orchestration.coordination.executors.base import (
    BasePatternExecutor,
    ExecutionContext,
    ExecutionResult,
)
from orchestration.coordination.executors.sequential import SequentialExecutor
from orchestration.coordination.executors.review_loop import ReviewLoopExecutor
from orchestration.coordination.executors.fan_out import FanOutExecutor
from orchestration.coordination.executors.pipeline_chain import PipelineChainExecutor
from orchestration.coordination.executors.escalation import EscalationExecutor
from orchestration.coordination.executors.debate import DebateExecutor
from orchestration.coordination.executors.saga import SagaExecutor

logger = logging.getLogger(__name__)

_EXECUTORS = {
    CoordinationPattern.SEQUENTIAL: SequentialExecutor,
    CoordinationPattern.REVIEW_LOOP: ReviewLoopExecutor,
    CoordinationPattern.PARALLEL_FAN_OUT: FanOutExecutor,
    CoordinationPattern.PIPELINE_CHAIN: PipelineChainExecutor,
    CoordinationPattern.ESCALATION: EscalationExecutor,
    CoordinationPattern.DEBATE: DebateExecutor,
    CoordinationPattern.SAGA: SagaExecutor,
}


def execute_with_pattern(
    pattern: CoordinationPattern,
    ctx: ExecutionContext,
) -> ExecutionResult:
    """Execute a task using the specified coordination pattern.

    Falls back to SEQUENTIAL on any executor error to preserve pipeline
    stability.

    Args:
        pattern: Which coordination pattern to use.
        ctx: Execution context with task function, memory, roster, etc.

    Returns:
        ExecutionResult with success flag and optional output.
    """
    executor_cls = _EXECUTORS.get(pattern, SequentialExecutor)

    try:
        executor = executor_cls()
        return executor.execute(ctx)
    except Exception as e:
        logger.warning(
            "Pattern %s executor failed, falling back to SEQUENTIAL: %s",
            pattern.value, e,
        )
        try:
            return SequentialExecutor().execute(ctx)
        except Exception as fallback_err:
            logger.error("SEQUENTIAL fallback also failed: %s", fallback_err)
            return ExecutionResult(success=False, error=str(fallback_err))


__all__ = [
    "BasePatternExecutor",
    "ExecutionContext",
    "ExecutionResult",
    "execute_with_pattern",
]
