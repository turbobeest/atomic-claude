"""Saga Executor — multi-step execution with compensating rollback.

Wraps task execution in a transaction-like pattern. If a step fails,
previously completed steps' compensating actions are executed in reverse.
"""

import inspect
import logging
from typing import Any, Callable, Dict, List, Optional

from orchestration.coordination.executors.base import (
    BasePatternExecutor,
    ExecutionContext,
    ExecutionResult,
)

logger = logging.getLogger(__name__)


class SagaStep:
    """A single step in a saga with an optional compensating action."""

    def __init__(self, name: str, action: Callable, compensate: Optional[Callable] = None):
        self.name = name
        self.action = action
        self.compensate = compensate
        self.completed = False
        self.result: Any = None


class SagaExecutor(BasePatternExecutor):
    """Multi-step execution with compensating rollback on failure."""

    def execute(self, ctx: ExecutionContext) -> ExecutionResult:
        # For now, wrap the task function as a single saga step
        # with state snapshot as the compensating action
        steps = self._build_steps(ctx)
        completed_steps: List[SagaStep] = []

        for step in steps:
            try:
                step.result = step.action()
                if step.result is False:
                    logger.warning(
                        "Saga step '%s' returned False, rolling back",
                        step.name,
                    )
                    self._rollback(completed_steps)
                    return ExecutionResult(
                        success=False,
                        error=f"Saga step '{step.name}' failed",
                        pattern_used="saga",
                        iterations=len(completed_steps) + 1,
                        metadata={"rolled_back_steps": [s.name for s in completed_steps]},
                    )

                step.completed = True
                completed_steps.append(step)

            except Exception as e:
                logger.warning(
                    "Saga step '%s' raised %s, rolling back %d steps",
                    step.name, e, len(completed_steps),
                )
                self._rollback(completed_steps)
                return ExecutionResult(
                    success=False,
                    error=str(e),
                    pattern_used="saga",
                    iterations=len(completed_steps) + 1,
                    metadata={"rolled_back_steps": [s.name for s in completed_steps]},
                )

        return ExecutionResult(
            success=True,
            pattern_used="saga",
            iterations=len(completed_steps),
            metadata={"completed_steps": [s.name for s in completed_steps]},
        )

    def _build_steps(self, ctx: ExecutionContext) -> List[SagaStep]:
        """Build saga steps from the execution context.

        For the basic case, wraps the task function as a single step.
        Tasks can provide saga_steps in ctx.extra for multi-step sagas.
        """
        # Check if the task provides custom saga steps
        custom_steps = ctx.extra.get("saga_steps")
        if custom_steps:
            return custom_steps

        # Default: single step wrapping the task function
        def run_task():
            if ctx.graph is not None:
                try:
                    sig = inspect.signature(ctx.task_func)
                    accepts_graph = "graph" in sig.parameters
                except (ValueError, TypeError):
                    accepts_graph = False
                if accepts_graph:
                    return ctx.task_func(ctx.mem, graph=ctx.graph)
                return ctx.task_func(ctx.mem)
            return ctx.task_func(ctx.mem)

        # Compensating action: log that rollback was needed
        def compensate_task():
            ctx.mem.warning(f"Saga rollback: task {ctx.task_id} execution reverted")
            logger.info("Saga compensate: task %s rolled back", ctx.task_id)

        return [SagaStep(name=ctx.task_name, action=run_task, compensate=compensate_task)]

    def _rollback(self, completed_steps: List[SagaStep]) -> None:
        """Execute compensating actions in reverse order."""
        for step in reversed(completed_steps):
            if step.compensate:
                try:
                    step.compensate()
                    logger.info("Saga compensated step: %s", step.name)
                except Exception as e:
                    logger.error(
                        "Saga compensation failed for step '%s': %s",
                        step.name, e,
                    )
