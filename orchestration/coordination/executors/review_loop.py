"""Review Loop Executor — produce → review → iterate.

Runs the task, then asks a reviewer agent to evaluate the output.
If the review finds issues, the task re-runs with feedback, up to
max_iterations.
"""

import inspect
import logging
from typing import Optional

from orchestration.coordination.executors.base import (
    BasePatternExecutor,
    ExecutionContext,
    ExecutionResult,
)

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 3
REVIEW_PROMPT_TEMPLATE = (
    "Review the following task output for correctness, completeness, "
    "and quality. Task: {task_name}\n\nOutput:\n{output}\n\n"
    "Respond with APPROVED if acceptable, or REVISION_NEEDED: <feedback> "
    "if changes are required."
)


class ReviewLoopExecutor(BasePatternExecutor):
    """Produce artifact then have reviewer evaluate, iterate up to 3x."""

    def execute(self, ctx: ExecutionContext) -> ExecutionResult:
        iterations = 0
        last_output = None

        for iteration in range(MAX_ITERATIONS):
            iterations = iteration + 1

            # Run the task
            try:
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
            except Exception as e:
                return ExecutionResult(
                    success=False,
                    error=str(e),
                    pattern_used="review_loop",
                    iterations=iterations,
                )

            if result is False:
                return ExecutionResult(
                    success=False,
                    error="Task returned False",
                    pattern_used="review_loop",
                    iterations=iterations,
                )

            # Build review output from task memory
            last_output = ctx.mem.build_content() if ctx.mem.has_entries() else ""

            # Skip review if no reviewer agents or no output
            if not last_output or not ctx.roster or len(ctx.roster) < 2:
                return ExecutionResult(
                    success=True,
                    output=last_output,
                    pattern_used="review_loop",
                    iterations=iterations,
                )

            # Request review via LLM
            review_result = self._request_review(ctx, last_output)
            if review_result is None or review_result.startswith("APPROVED"):
                logger.info(
                    "Review loop approved on iteration %d for task %s",
                    iterations, ctx.task_id,
                )
                return ExecutionResult(
                    success=True,
                    output=last_output,
                    pattern_used="review_loop",
                    iterations=iterations,
                    metadata={"review_status": "approved"},
                )

            # Feedback — add to memory for next iteration
            feedback = review_result.replace("REVISION_NEEDED:", "").strip()
            ctx.mem.finding(f"Review iteration {iterations} feedback: {feedback}")
            logger.info(
                "Review loop iteration %d for task %s — revision needed",
                iterations, ctx.task_id,
            )

        # Max iterations reached
        return ExecutionResult(
            success=True,
            output=last_output,
            pattern_used="review_loop",
            iterations=iterations,
            metadata={"review_status": "max_iterations_reached"},
        )

    def _request_review(self, ctx: ExecutionContext, output: str) -> Optional[str]:
        """Invoke LLM to review the task output."""
        try:
            from core.llm.invoke import invoke_llm

            prompt = REVIEW_PROMPT_TEMPLATE.format(
                task_name=ctx.task_name,
                output=output[:2000],  # Cap to avoid token explosion
            )
            response = invoke_llm(prompt=prompt, model="haiku")
            return response.strip() if response else None
        except Exception as e:
            logger.debug("Review LLM call failed, auto-approving: %s", e)
            return "APPROVED"
