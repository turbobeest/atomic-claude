"""Pipeline Chain Executor — sequential agent chain.

Each agent receives the previous agent's output, enabling multi-stage
transformations (e.g., analyze → design → implement).
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


class PipelineChainExecutor(BasePatternExecutor):
    """Sequential agent chain where each gets prior agent's output."""

    def execute(self, ctx: ExecutionContext) -> ExecutionResult:
        if not ctx.roster or len(ctx.roster) < 2:
            from orchestration.coordination.executors.sequential import SequentialExecutor
            return SequentialExecutor().execute(ctx)

        # First, run the actual task function for side effects
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
                    pattern_used="pipeline_chain",
                )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e),
                pattern_used="pipeline_chain",
            )

        # Chain agents: each refines the previous output
        chain_output = ctx.mem.build_content() if ctx.mem.has_entries() else ctx.task_name
        agents_used = []

        for i, agent_entry in enumerate(ctx.roster[:4]):
            agent = agent_entry[0] if isinstance(agent_entry, (list, tuple)) else agent_entry
            name = getattr(agent, "name", str(agent))
            desc = getattr(agent, "description", "")
            agents_used.append(name)

            refined = self._chain_step(name, desc, ctx.task_name, chain_output, i)
            if refined:
                chain_output = refined
                ctx.mem.finding(f"Pipeline stage {i+1} ({name}): processed")

        return ExecutionResult(
            success=True,
            output=chain_output,
            pattern_used="pipeline_chain",
            iterations=len(agents_used),
            metadata={"agents_chained": agents_used},
        )

    def _chain_step(
        self, agent_name: str, agent_desc: str,
        task_name: str, prior_output: str, step: int,
    ) -> Optional[str]:
        """Run one step of the pipeline chain."""
        try:
            from core.llm.invoke import invoke_llm

            prompt = (
                f"You are {agent_name}. {agent_desc}\n\n"
                f"Task: {task_name}\n"
                f"Previous stage output:\n{prior_output[:3000]}\n\n"
                f"Refine and improve this output from your expert perspective."
            )
            return invoke_llm(prompt=prompt, model="haiku")
        except Exception as e:
            logger.debug("Pipeline chain step %d failed: %s", step, e)
            return None
