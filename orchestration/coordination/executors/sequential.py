"""Sequential Executor — wraps existing single-agent task execution.

This is the identity executor: it calls task_func(mem) exactly as the
current phase_runner does, preserving backward compatibility.
"""

import inspect
import logging

from orchestration.coordination.executors.base import (
    BasePatternExecutor,
    ExecutionContext,
    ExecutionResult,
)

logger = logging.getLogger(__name__)


class SequentialExecutor(BasePatternExecutor):
    """Execute task with single agent (current default behavior)."""

    def execute(self, ctx: ExecutionContext) -> ExecutionResult:
        try:
            # Pass graph if the function accepts it
            if ctx.graph is not None:
                try:
                    sig = inspect.signature(ctx.task_func)
                    accepts_graph = "graph" in sig.parameters
                except (ValueError, TypeError):
                    accepts_graph = False
                if accepts_graph:
                    result = ctx.task_func(ctx.mem, graph=ctx.graph)
                else:
                    result = ctx.task_func(ctx.mem)
            else:
                result = ctx.task_func(ctx.mem)

            # Treat None as success; only explicit False is failure
            success = result is not False

            return ExecutionResult(
                success=success,
                pattern_used="sequential",
            )
        except Exception as e:
            logger.error("Sequential execution failed: %s", e)
            return ExecutionResult(
                success=False,
                error=str(e),
                pattern_used="sequential",
            )
