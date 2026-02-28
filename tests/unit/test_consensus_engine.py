"""Tests for orchestration.consensus."""

import pytest
from unittest.mock import MagicMock, patch

from orchestration.consensus.models import (
    ConsensusResult,
    ConsensusStatus,
    Proposal,
    ProposalOption,
    Vote,
    VotingStrategy,
)
from orchestration.consensus.voting import (
    MajorityTallier,
    WeightedTallier,
    UnanimousTallier,
    get_tallier,
)
from orchestration.consensus.prompts import parse_vote_response, format_vote_prompt
from orchestration.consensus.engine import ConsensusEngine


def _make_vote(option_id, confidence=0.8, score=80.0, name="agent", dissent=None):
    return Vote(
        agent_name=name,
        agent_role="advisor",
        agent_score=score,
        chosen_option_id=option_id,
        confidence=confidence,
        reasoning="test",
        dissent=dissent,
    )


class TestMajorityTallier:
    """Test >50% majority voting."""

    def test_clear_majority(self):
        votes = [_make_vote("A"), _make_vote("A"), _make_vote("B")]
        result = MajorityTallier().tally("prop-1", votes)
        assert result.status == ConsensusStatus.APPROVED
        assert result.winning_option == "A"
        assert result.vote_breakdown == {"A": 2, "B": 1}

    def test_no_majority(self):
        votes = [_make_vote("A"), _make_vote("B"), _make_vote("C")]
        result = MajorityTallier().tally("prop-1", votes)
        assert result.status == ConsensusStatus.NO_CONSENSUS

    def test_empty_votes(self):
        result = MajorityTallier().tally("prop-1", [])
        assert result.status == ConsensusStatus.NO_CONSENSUS

    def test_unanimous_is_majority(self):
        votes = [_make_vote("A"), _make_vote("A"), _make_vote("A")]
        result = MajorityTallier().tally("prop-1", votes)
        assert result.status == ConsensusStatus.APPROVED
        assert result.winning_option == "A"

    def test_confidence_averaged(self):
        votes = [
            _make_vote("A", confidence=0.9),
            _make_vote("A", confidence=0.7),
            _make_vote("B", confidence=0.5),
        ]
        result = MajorityTallier().tally("prop-1", votes)
        assert result.confidence == pytest.approx(0.8)

    def test_dissenting_opinions_collected(self):
        votes = [
            _make_vote("A"),
            _make_vote("A"),
            _make_vote("B", dissent="I disagree because..."),
        ]
        result = MajorityTallier().tally("prop-1", votes)
        assert len(result.dissenting_opinions) == 1


class TestWeightedTallier:
    """Test agent-score-weighted voting."""

    def test_high_score_agent_wins(self):
        votes = [
            _make_vote("A", score=90, confidence=0.9),  # weight: 0.9 * 0.9 = 0.81
            _make_vote("B", score=30, confidence=0.5),  # weight: 0.3 * 0.5 = 0.15
        ]
        result = WeightedTallier().tally("prop-1", votes)
        assert result.status == ConsensusStatus.APPROVED
        assert result.winning_option == "A"

    def test_many_low_score_can_win(self):
        votes = [
            _make_vote("A", score=90, confidence=0.9),  # 0.81
            _make_vote("B", score=60, confidence=0.8),  # 0.48
            _make_vote("B", score=60, confidence=0.8),  # 0.48 → total 0.96
        ]
        result = WeightedTallier().tally("prop-1", votes)
        assert result.status == ConsensusStatus.APPROVED
        assert result.winning_option == "B"

    def test_empty_votes(self):
        result = WeightedTallier().tally("prop-1", [])
        assert result.status == ConsensusStatus.NO_CONSENSUS

    def test_weighted_scores_in_result(self):
        votes = [_make_vote("A", score=80, confidence=0.7)]
        result = WeightedTallier().tally("prop-1", votes)
        assert "A" in result.weighted_scores


class TestUnanimousTallier:
    """Test unanimous agreement requirement."""

    def test_all_agree(self):
        votes = [_make_vote("A"), _make_vote("A"), _make_vote("A")]
        result = UnanimousTallier().tally("prop-1", votes)
        assert result.status == ConsensusStatus.APPROVED
        assert result.winning_option == "A"

    def test_one_dissent(self):
        votes = [_make_vote("A"), _make_vote("A"), _make_vote("B")]
        result = UnanimousTallier().tally("prop-1", votes)
        assert result.status == ConsensusStatus.NO_CONSENSUS

    def test_empty_votes(self):
        result = UnanimousTallier().tally("prop-1", [])
        assert result.status == ConsensusStatus.NO_CONSENSUS


class TestGetTallier:
    """Test tallier factory."""

    def test_majority(self):
        assert isinstance(get_tallier("majority"), MajorityTallier)

    def test_weighted(self):
        assert isinstance(get_tallier("weighted"), WeightedTallier)

    def test_unanimous(self):
        assert isinstance(get_tallier("unanimous"), UnanimousTallier)

    def test_unknown_defaults_to_majority(self):
        assert isinstance(get_tallier("unknown"), MajorityTallier)


class TestParseVoteResponse:
    """Test structured vote response parsing."""

    def test_full_response(self):
        response = (
            "VOTE: option-1\n"
            "CONFIDENCE: 0.85\n"
            "REASONING: This is the best option\n"
            "DISSENT: NONE"
        )
        parsed = parse_vote_response(response)
        assert parsed["vote"] == "option-1"
        assert parsed["confidence"] == 0.85
        assert parsed["reasoning"] == "This is the best option"
        assert parsed["dissent"] is None

    def test_with_dissent(self):
        response = (
            "VOTE: option-2\n"
            "CONFIDENCE: 0.6\n"
            "REASONING: Acceptable but not ideal\n"
            "DISSENT: I preferred option-1 for performance"
        )
        parsed = parse_vote_response(response)
        assert parsed["dissent"] == "I preferred option-1 for performance"

    def test_partial_response(self):
        response = "VOTE: option-1"
        parsed = parse_vote_response(response)
        assert parsed["vote"] == "option-1"
        assert parsed["confidence"] == 0.5  # Default

    def test_empty_response(self):
        parsed = parse_vote_response("")
        assert parsed["vote"] == ""


class TestConsensusEngine:
    """Test ConsensusEngine orchestration."""

    def test_light_gravity_skips(self):
        engine = ConsensusEngine()
        proposal = Proposal(
            id="p1", question="test?", context="ctx",
            options=[ProposalOption("a", "A", "desc")],
        )
        result = engine.request_consensus(proposal, [], gravity="light")
        assert result.status == ConsensusStatus.SKIPPED

    def test_no_agents_no_consensus(self):
        engine = ConsensusEngine()
        proposal = Proposal(
            id="p1", question="test?", context="ctx",
            options=[ProposalOption("a", "A", "desc")],
        )
        result = engine.request_consensus(proposal, [], gravity="standard")
        assert result.status == ConsensusStatus.NO_CONSENSUS

    @patch("orchestration.consensus.engine.ConsensusEngine._collect_votes")
    def test_majority_with_votes(self, mock_collect):
        mock_collect.return_value = [
            _make_vote("opt-1", name="agent-1"),
            _make_vote("opt-1", name="agent-2"),
            _make_vote("opt-2", name="agent-3"),
        ]
        engine = ConsensusEngine()
        proposal = Proposal(
            id="p1", question="test?", context="ctx",
            options=[
                ProposalOption("opt-1", "Option 1", "desc"),
                ProposalOption("opt-2", "Option 2", "desc"),
            ],
            voting_strategy=VotingStrategy.MAJORITY,
        )
        result = engine.request_consensus(
            proposal, [("a1",), ("a2",), ("a3",)], gravity="standard",
        )
        assert result.status == ConsensusStatus.APPROVED
        assert result.winning_option == "opt-1"

    @patch("orchestration.consensus.engine.ConsensusEngine._collect_votes")
    def test_graph_recording(self, mock_collect):
        mock_collect.return_value = [
            _make_vote("opt-1", name="agent-1"),
            _make_vote("opt-1", name="agent-2"),
        ]
        graph = MagicMock()
        engine = ConsensusEngine()
        proposal = Proposal(
            id="p1", question="test?", context="ctx",
            options=[ProposalOption("opt-1", "Option 1", "desc")],
        )
        result = engine.request_consensus(
            proposal, [("a1",), ("a2",)],
            gravity="standard", graph=graph, task_id="task-001",
        )
        # Should have written to graph
        graph.writer.create_node.assert_called()
