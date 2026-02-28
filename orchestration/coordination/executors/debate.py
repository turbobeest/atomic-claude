"""Debate Executor — two propose, third judges.

Two agents independently propose solutions. A third agent evaluates both
proposals and selects the stronger one, optionally merging the best ideas.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Tuple

from orchestration.coordination.executors.base import (
    BasePatternExecutor,
    ExecutionContext,
    ExecutionResult,
)

logger = logging.getLogger(__name__)

JUDGE_PROMPT = (
    "You are judging two competing proposals for the following task.\n"
    "Task: {task_name}\n\n"
    "=== Proposal A ({agent_a}) ===\n{proposal_a}\n\n"
    "=== Proposal B ({agent_b}) ===\n{proposal_b}\n\n"
    "Select the better proposal and explain why. If both have strengths, "
    "synthesize them. Start your response with WINNER: A or WINNER: B "
    "or WINNER: MERGED."
)


class DebateExecutor(BasePatternExecutor):
    """Two agents propose solutions, third judges."""

    def execute(self, ctx: ExecutionContext) -> ExecutionResult:
        if not ctx.roster or len(ctx.roster) < 3:
            from orchestration.coordination.executors.sequential import SequentialExecutor
            return SequentialExecutor().execute(ctx)

        # First run the actual task function
        import inspect
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
                    error="Task returned False",
                    pattern_used="debate",
                )
        except Exception as e:
            return ExecutionResult(
                success=False, error=str(e), pattern_used="debate",
            )

        # Get two proposals in parallel
        agent_a = ctx.roster[0]
        agent_b = ctx.roster[1]
        judge_agent = ctx.roster[2]

        proposals = {}

        def get_proposal(agent_entry, label):
            agent = agent_entry[0] if isinstance(agent_entry, (list, tuple)) else agent_entry
            name = getattr(agent, "name", str(agent))
            desc = getattr(agent, "description", "")
            return label, name, self._get_proposal(name, desc, ctx)

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(get_proposal, agent_a, "A"),
                pool.submit(get_proposal, agent_b, "B"),
            ]
            for future in as_completed(futures, timeout=120):
                try:
                    label, name, proposal = future.result()
                    proposals[label] = (name, proposal)
                except Exception as e:
                    logger.debug("Debate proposal failed: %s", e)

        if len(proposals) < 2:
            return ExecutionResult(
                success=True,
                pattern_used="debate",
                metadata={"debate_status": "insufficient_proposals"},
            )

        # Judge
        name_a, proposal_a = proposals["A"]
        name_b, proposal_b = proposals["B"]
        judgment = self._judge(ctx, name_a, proposal_a, name_b, proposal_b, judge_agent)

        if judgment:
            ctx.mem.finding(f"Debate result: {judgment[:500]}")

        return ExecutionResult(
            success=True,
            output=judgment,
            pattern_used="debate",
            iterations=3,
            metadata={
                "debaters": [name_a, name_b],
                "debate_status": "judged",
            },
        )

    def _get_proposal(self, name: str, desc: str, ctx: ExecutionContext) -> Optional[str]:
        """Get a proposal from an agent."""
        try:
            from core.llm.invoke import invoke_llm

            task_context = ctx.mem.build_content() if ctx.mem.has_entries() else ""
            prompt = (
                f"You are {name}. {desc}\n\n"
                f"Task: {ctx.task_name}\n"
                f"Context:\n{task_context[:2000]}\n\n"
                f"Propose your solution with rationale."
            )
            return invoke_llm(prompt=prompt, model="sonnet")
        except Exception as e:
            logger.debug("Debate proposal from %s failed: %s", name, e)
            return None

    def _judge(
        self, ctx: ExecutionContext,
        name_a: str, proposal_a: str,
        name_b: str, proposal_b: str,
        judge_entry,
    ) -> Optional[str]:
        """Have the judge evaluate both proposals."""
        try:
            from core.llm.invoke import invoke_llm

            prompt = JUDGE_PROMPT.format(
                task_name=ctx.task_name,
                agent_a=name_a,
                proposal_a=proposal_a[:2000] if proposal_a else "(no proposal)",
                agent_b=name_b,
                proposal_b=proposal_b[:2000] if proposal_b else "(no proposal)",
            )
            return invoke_llm(prompt=prompt, model="sonnet")
        except Exception as e:
            logger.debug("Debate judging failed: %s", e)
            return None
