"""Voting Strategies — talliers for multi-agent consensus.

Three strategies: MajorityTallier (>50%), WeightedTallier (by agent
composite_score * confidence), UnanimousTallier (all must agree).
"""

from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

from orchestration.consensus.models import (
    ConsensusResult,
    ConsensusStatus,
    Vote,
)


class VotingTallier(ABC):
    """Abstract base for vote tallying strategies."""

    @abstractmethod
    def tally(self, proposal_id: str, votes: List[Vote]) -> ConsensusResult:
        """Tally votes and produce a result."""
        ...


class MajorityTallier(VotingTallier):
    """>50% of votes wins."""

    def tally(self, proposal_id: str, votes: List[Vote]) -> ConsensusResult:
        if not votes:
            return ConsensusResult(
                proposal_id=proposal_id,
                status=ConsensusStatus.NO_CONSENSUS,
            )

        counts: Dict[str, int] = Counter(v.chosen_option_id for v in votes)
        total = len(votes)
        breakdown = dict(counts)

        # Find majority winner
        winner = None
        for option_id, count in counts.most_common():
            if count / total > 0.5:
                winner = option_id
                break

        # Collect dissenting opinions
        dissents = [v.dissent for v in votes if v.dissent]

        if winner:
            avg_confidence = sum(
                v.confidence for v in votes if v.chosen_option_id == winner
            ) / counts[winner]
            return ConsensusResult(
                proposal_id=proposal_id,
                status=ConsensusStatus.APPROVED,
                winning_option=winner,
                vote_breakdown=breakdown,
                confidence=avg_confidence,
                votes=votes,
                dissenting_opinions=dissents,
            )

        return ConsensusResult(
            proposal_id=proposal_id,
            status=ConsensusStatus.NO_CONSENSUS,
            vote_breakdown=breakdown,
            votes=votes,
            dissenting_opinions=dissents,
        )


class WeightedTallier(VotingTallier):
    """Votes weighted by agent composite_score * confidence."""

    def tally(self, proposal_id: str, votes: List[Vote]) -> ConsensusResult:
        if not votes:
            return ConsensusResult(
                proposal_id=proposal_id,
                status=ConsensusStatus.NO_CONSENSUS,
            )

        counts: Dict[str, int] = Counter(v.chosen_option_id for v in votes)
        weighted: Dict[str, float] = defaultdict(float)

        for vote in votes:
            weight = (vote.agent_score / 100.0) * vote.confidence
            weighted[vote.chosen_option_id] += weight

        total_weight = sum(weighted.values())
        breakdown = dict(counts)
        weighted_scores = {k: round(v, 4) for k, v in weighted.items()}

        # Winner needs >50% of total weight
        winner = None
        winner_confidence = 0.0
        for option_id, weight in sorted(weighted.items(), key=lambda x: -x[1]):
            if total_weight > 0 and weight / total_weight > 0.5:
                winner = option_id
                winner_confidence = weight / total_weight
                break

        dissents = [v.dissent for v in votes if v.dissent]

        if winner:
            return ConsensusResult(
                proposal_id=proposal_id,
                status=ConsensusStatus.APPROVED,
                winning_option=winner,
                vote_breakdown=breakdown,
                weighted_scores=weighted_scores,
                confidence=winner_confidence,
                votes=votes,
                dissenting_opinions=dissents,
            )

        return ConsensusResult(
            proposal_id=proposal_id,
            status=ConsensusStatus.NO_CONSENSUS,
            vote_breakdown=breakdown,
            weighted_scores=weighted_scores,
            votes=votes,
            dissenting_opinions=dissents,
        )


class UnanimousTallier(VotingTallier):
    """All agents must agree on the same option."""

    def tally(self, proposal_id: str, votes: List[Vote]) -> ConsensusResult:
        if not votes:
            return ConsensusResult(
                proposal_id=proposal_id,
                status=ConsensusStatus.NO_CONSENSUS,
            )

        options = {v.chosen_option_id for v in votes}
        counts = Counter(v.chosen_option_id for v in votes)
        breakdown = dict(counts)
        dissents = [v.dissent for v in votes if v.dissent]

        if len(options) == 1:
            winner = options.pop()
            avg_confidence = sum(v.confidence for v in votes) / len(votes)
            return ConsensusResult(
                proposal_id=proposal_id,
                status=ConsensusStatus.APPROVED,
                winning_option=winner,
                vote_breakdown=breakdown,
                confidence=avg_confidence,
                votes=votes,
                dissenting_opinions=dissents,
            )

        return ConsensusResult(
            proposal_id=proposal_id,
            status=ConsensusStatus.NO_CONSENSUS,
            vote_breakdown=breakdown,
            votes=votes,
            dissenting_opinions=dissents,
        )


def get_tallier(strategy: str) -> VotingTallier:
    """Get the appropriate tallier for a voting strategy.

    Args:
        strategy: One of "majority", "weighted", "unanimous".

    Returns:
        VotingTallier instance.
    """
    talliers = {
        "majority": MajorityTallier,
        "weighted": WeightedTallier,
        "unanimous": UnanimousTallier,
    }
    cls = talliers.get(strategy, MajorityTallier)
    return cls()
