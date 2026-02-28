"""Consensus Models — data structures for multi-agent voting.

Defines proposals, votes, and consensus results used by the
ConsensusEngine and voting strategies.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class VotingStrategy(str, Enum):
    """How votes are tallied."""

    MAJORITY = "majority"       # >50% of votes
    WEIGHTED = "weighted"       # By agent composite_score * confidence
    UNANIMOUS = "unanimous"     # All agents must agree


class ConsensusStatus(str, Enum):
    """Outcome of a consensus round."""

    APPROVED = "approved"
    REJECTED = "rejected"
    NO_CONSENSUS = "no_consensus"
    SKIPPED = "skipped"          # Gravity gate bypassed consensus


@dataclass
class ProposalOption:
    """A single option in a proposal."""

    id: str
    title: str
    description: str


@dataclass
class Proposal:
    """A question posed to agents for consensus."""

    id: str
    question: str
    context: str
    options: List[ProposalOption]
    voting_strategy: VotingStrategy = VotingStrategy.MAJORITY
    required_confidence: float = 0.6


@dataclass
class Vote:
    """A single agent's vote on a proposal."""

    agent_name: str
    agent_role: str
    agent_score: float          # 0-100 composite score from manifest
    chosen_option_id: str
    confidence: float           # 0.0-1.0
    reasoning: str
    dissent: Optional[str] = None


@dataclass
class ConsensusResult:
    """Outcome of a consensus round."""

    proposal_id: str
    status: ConsensusStatus
    winning_option: Optional[str] = None
    vote_breakdown: Dict[str, int] = field(default_factory=dict)
    weighted_scores: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    votes: List[Vote] = field(default_factory=list)
    dissenting_opinions: List[str] = field(default_factory=list)
