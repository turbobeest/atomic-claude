"""Escalation Executor — start cheap, escalate if quality insufficient.

Runs with haiku first, checks quality, escalates to sonnet then opus
if the result doesn't meet a quality threshold.
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

_MODEL_CHAIN = ["haiku", "sonnet", "opus"]

QUALITY_CHECK_PROMPT = (
    "Rate the quality of this task output on a scale of 1-10.\n"
    "Task: {task_name}\nOutput:\n{output}\n\n"
    "Respond with just a number 1-10."
)

QUALITY_THRESHOLD = 6


class EscalationExecutor(BasePatternExecutor):
    """Start with cheap model, escalate to expensive if quality insufficient."""

    def execute(self, ctx: ExecutionContext) -> ExecutionResult:
        # Run the actual task function first (this produces artifacts)
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

            if result is False:
                return ExecutionResult(
                    success=False,
                    error="Task function returned False",
                    pattern_used="escalation",
                )
        except Exception as e:
            return ExecutionResult(
                success=False, error=str(e), pattern_used="escalation",
            )

        output = ctx.mem.build_content() if ctx.mem.has_entries() else ""
        if not output:
            return ExecutionResult(
                success=True, pattern_used="escalation",
                metadata={"escalation_tier": "none"},
            )

        # Check quality and escalate if needed
        for tier in _MODEL_CHAIN:
            quality = self._check_quality(ctx.task_name, output, tier)
            if quality is not None and quality >= QUALITY_THRESHOLD:
                ctx.mem.finding(f"Escalation: quality {quality}/10 at tier {tier}")
                return ExecutionResult(
                    success=True,
                    output=output,
                    pattern_used="escalation",
                    metadata={"escalation_tier": tier, "quality_score": quality},
                )

            # Escalate: re-run analysis with higher tier
            enhanced = self._enhance_with_tier(ctx, tier)
            if enhanced:
                output = enhanced

        return ExecutionResult(
            success=True,
            output=output,
            pattern_used="escalation",
            metadata={"escalation_tier": _MODEL_CHAIN[-1]},
        )

    def _check_quality(self, task_name: str, output: str, tier: str) -> Optional[int]:
        """Check output quality using a fast model."""
        try:
            from core.llm.invoke import invoke_llm

            prompt = QUALITY_CHECK_PROMPT.format(
                task_name=task_name, output=output[:1500],
            )
            response = invoke_llm(prompt=prompt, model="haiku")
            # Extract number from response
            for word in response.strip().split():
                try:
                    return int(word)
                except ValueError:
                    continue
            return None
        except Exception:
            return None

    def _enhance_with_tier(self, ctx: ExecutionContext, tier: str) -> Optional[str]:
        """Re-analyze task output with a higher-tier model."""
        try:
            from core.llm.invoke import invoke_llm

            output = ctx.mem.build_content() if ctx.mem.has_entries() else ""
            prompt = (
                f"Task: {ctx.task_name}\n"
                f"Previous analysis:\n{output[:2000]}\n\n"
                f"Provide an improved, more thorough analysis."
            )
            return invoke_llm(prompt=prompt, model=tier)
        except Exception as e:
            logger.debug("Enhancement at tier %s failed: %s", tier, e)
            return None
