"""Consensus — multi-agent voting and decision-making.

Provides voting strategies (majority, weighted, unanimous) and a
ConsensusEngine that collects agent votes via LLM invocation.
"""

from orchestration.consensus.models import (
    ConsensusResult,
    ConsensusStatus,
    Proposal,
    ProposalOption,
    Vote,
    VotingStrategy,
)

__all__ = [
    "ConsensusResult",
    "ConsensusStatus",
    "Proposal",
    "ProposalOption",
    "Vote",
    "VotingStrategy",
]
