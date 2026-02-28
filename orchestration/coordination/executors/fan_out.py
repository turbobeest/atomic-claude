"""Fan-Out Executor — parallel multi-agent execution with synthesis.

Runs the same prompt against multiple agents in parallel using
ThreadPoolExecutor, then synthesizes the results into a unified output.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

from orchestration.coordination.executors.base import (
    BasePatternExecutor,
    ExecutionContext,
    ExecutionResult,
)

logger = logging.getLogger(__name__)

SYNTHESIS_PROMPT = (
    "You are synthesizing multiple expert responses into a single coherent answer.\n"
    "Task: {task_name}\n\n"
    "Expert responses:\n{responses}\n\n"
    "Provide a unified synthesis that incorporates the best insights from all responses."
)


class FanOutExecutor(BasePatternExecutor):
    """Run same task with multiple agents in parallel, synthesize results."""

    def execute(self, ctx: ExecutionContext) -> ExecutionResult:
        if not ctx.roster or len(ctx.roster) < 2:
            # Not enough agents — fall through to sequential
            from orchestration.coordination.executors.sequential import SequentialExecutor
            return SequentialExecutor().execute(ctx)

        agent_responses: List[str] = []
        errors: List[str] = []

        def invoke_agent(agent_entry):
            """Invoke LLM for a single agent."""
            try:
                from core.llm.invoke import invoke_llm

                agent = agent_entry[0] if isinstance(agent_entry, (list, tuple)) else agent_entry
                name = getattr(agent, "name", str(agent))
                desc = getattr(agent, "description", "")

                prompt = (
                    f"You are {name}. {desc}\n\n"
                    f"Task: {ctx.task_name}\n"
                    f"Provide your expert analysis and recommendations."
                )
                response = invoke_llm(prompt=prompt, model="haiku")
                return name, response
            except Exception as e:
                return name, None

        # Fan out to agents (cap at 5)
        agents_to_use = ctx.roster[:5]

        with ThreadPoolExecutor(max_workers=min(len(agents_to_use), 3)) as pool:
            futures = {pool.submit(invoke_agent, agent): agent for agent in agents_to_use}

            for future in as_completed(futures, timeout=120):
                try:
                    name, response = future.result()
                    if response:
                        agent_responses.append(f"[{name}]\n{response}")
                    else:
                        errors.append(f"{name}: no response")
                except Exception as e:
                    errors.append(str(e))

        if not agent_responses:
            return ExecutionResult(
                success=False,
                error="No agent responses received",
                pattern_used="parallel_fan_out",
            )

        # Also run the actual task function for side effects (artifacts, etc.)
        import inspect
        try:
            if ctx.graph is not None:
                try:
                    sig = inspect.signature(ctx.task_func)
                    accepts_graph = "graph" in sig.parameters
                except (ValueError, TypeError):
                    accepts_graph = False
                if accepts_graph:
                    ctx.task_func(ctx.mem, graph=ctx.graph)
                else:
                    ctx.task_func(ctx.mem)
            else:
                ctx.task_func(ctx.mem)
        except Exception:
            pass

        # Synthesize responses
        synthesis = self._synthesize(ctx, agent_responses)

        if synthesis:
            ctx.mem.finding(f"Fan-out synthesis ({len(agent_responses)} agents): {synthesis[:500]}")

        return ExecutionResult(
            success=True,
            output=synthesis,
            pattern_used="parallel_fan_out",
            metadata={
                "agent_count": len(agent_responses),
                "errors": errors,
            },
        )

    def _synthesize(self, ctx: ExecutionContext, responses: List[str]) -> Optional[str]:
        """Synthesize multiple agent responses."""
        try:
            from core.llm.invoke import invoke_llm

            combined = "\n\n---\n\n".join(responses)
            prompt = SYNTHESIS_PROMPT.format(
                task_name=ctx.task_name,
                responses=combined[:4000],
            )
            return invoke_llm(prompt=prompt, model="sonnet")
        except Exception as e:
            logger.debug("Synthesis failed, returning concatenated: %s", e)
            return "\n\n---\n\n".join(responses)
