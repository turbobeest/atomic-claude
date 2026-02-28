"""Consensus Engine — multi-agent voting with LLM invocation.

Collects votes from agents by invoking the LLM, parses structured
responses, tallies via the appropriate voting strategy, and records
the outcome to the knowledge graph.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from orchestration.consensus.models import (
    ConsensusResult,
    ConsensusStatus,
    Proposal,
    Vote,
    VotingStrategy,
)
from orchestration.consensus.prompts import format_vote_prompt, parse_vote_response
from orchestration.consensus.voting import get_tallier
from orchestration.consensus.graph_integration import record_consensus_decision

logger = logging.getLogger(__name__)

# Default voting strategies by gravity
_DEFAULT_STRATEGY = {
    "light": None,           # Skipped
    "standard": VotingStrategy.MAJORITY,
    "intensive": VotingStrategy.WEIGHTED,
}


class ConsensusEngine:
    """Orchestrates multi-agent consensus via LLM voting."""

    def request_consensus(
        self,
        proposal: Proposal,
        agents: List[Tuple],
        gravity: Optional[str] = None,
        graph: Any = None,
        task_id: str = "",
        shared_context: str = "",
    ) -> ConsensusResult:
        """Run a consensus round.

        Args:
            proposal: The question and options to vote on.
            agents: List of (AgentEntry, ResolvedModel) tuples.
            gravity: Gravity level. LIGHT → SKIPPED (zero LLM calls).
            graph: Optional GraphManager for persisting results.
            task_id: Current task ID for graph linking.
            shared_context: Additional context shared with all agents.

        Returns:
            ConsensusResult with voting outcome.
        """
        # Gravity gate: LIGHT → skip consensus entirely
        if gravity == "light":
            logger.info("Consensus skipped for LIGHT gravity")
            return ConsensusResult(
                proposal_id=proposal.id,
                status=ConsensusStatus.SKIPPED,
            )

        if not agents:
            return ConsensusResult(
                proposal_id=proposal.id,
                status=ConsensusStatus.NO_CONSENSUS,
            )

        # Override strategy based on gravity if proposal uses default
        strategy = proposal.voting_strategy
        if gravity and gravity in _DEFAULT_STRATEGY:
            gravity_strategy = _DEFAULT_STRATEGY[gravity]
            if gravity_strategy:
                strategy = gravity_strategy

        # Collect votes
        votes = self._collect_votes(proposal, agents, shared_context)

        if not votes:
            return ConsensusResult(
                proposal_id=proposal.id,
                status=ConsensusStatus.NO_CONSENSUS,
            )

        # Tally
        tallier = get_tallier(strategy.value)
        result = tallier.tally(proposal.id, votes)

        # Record to graph
        if graph is not None and task_id:
            record_consensus_decision(result, task_id, graph)

        return result

    def _collect_votes(
        self,
        proposal: Proposal,
        agents: List[Tuple],
        shared_context: str = "",
    ) -> List[Vote]:
        """Collect votes from all agents via LLM invocation.

        Uses haiku model for token efficiency.
        """
        votes = []

        for agent_entry in agents:
            agent = agent_entry[0] if isinstance(agent_entry, (list, tuple)) else agent_entry
            name = getattr(agent, "name", str(agent))
            role = getattr(agent, "role", "advisor")
            score = getattr(agent, "composite_score", 50.0)

            vote = self._invoke_vote(
                name, role, score, proposal, shared_context,
            )
            if vote:
                votes.append(vote)

        return votes

    def _invoke_vote(
        self,
        agent_name: str,
        agent_role: str,
        agent_score: float,
        proposal: Proposal,
        shared_context: str,
    ) -> Optional[Vote]:
        """Invoke LLM to get a single agent's vote."""
        try:
            from core.llm.invoke import invoke_llm

            prompt = format_vote_prompt(
                agent_name=agent_name,
                agent_role=agent_role,
                question=proposal.question,
                context=proposal.context,
                options=proposal.options,
                shared_context=shared_context,
            )

            response = invoke_llm(prompt=prompt, model="haiku")
            if not response:
                return None

            parsed = parse_vote_response(response)

            # Validate vote references a real option
            valid_ids = {opt.id for opt in proposal.options}
            if parsed["vote"] not in valid_ids:
                logger.debug(
                    "Agent %s voted for invalid option '%s'",
                    agent_name, parsed["vote"],
                )
                return None

            return Vote(
                agent_name=agent_name,
                agent_role=agent_role,
                agent_score=agent_score,
                chosen_option_id=parsed["vote"],
                confidence=max(0.0, min(1.0, parsed["confidence"])),
                reasoning=parsed["reasoning"],
                dissent=parsed["dissent"],
            )

        except Exception as e:
            logger.debug("Vote collection from %s failed: %s", agent_name, e)
            return None
