"""Tests for orchestration.coordination.patterns and selector."""

import pytest
from unittest.mock import MagicMock

from orchestration.coordination.patterns import (
    CoordinationPattern,
    PatternSpec,
    PATTERN_CATALOG,
)
from orchestration.coordination.selector import (
    PatternSelection,
    PatternSelector,
    select_pattern,
)


class TestPatternCatalog:
    """Test pattern catalog completeness and integrity."""

    def test_all_patterns_in_catalog(self):
        for pattern in CoordinationPattern:
            assert pattern in PATTERN_CATALOG

    def test_sequential_is_universal(self):
        spec = PATTERN_CATALOG[CoordinationPattern.SEQUENTIAL]
        assert "light" in spec.compatible_gravity
        assert "standard" in spec.compatible_gravity
        assert "intensive" in spec.compatible_gravity
        assert spec.min_agents == 1
        assert spec.max_agents == 1
        assert spec.estimated_overhead_factor == 1.0

    def test_debate_requires_intensive(self):
        spec = PATTERN_CATALOG[CoordinationPattern.DEBATE]
        assert "intensive" in spec.compatible_gravity
        assert "light" not in spec.compatible_gravity
        assert spec.min_agents == 3

    def test_saga_supports_rollback(self):
        spec = PATTERN_CATALOG[CoordinationPattern.SAGA]
        assert spec.supports_rollback is True

    def test_overhead_factors_positive(self):
        for spec in PATTERN_CATALOG.values():
            assert spec.estimated_overhead_factor >= 1.0


class TestPatternSelector:
    """Test pattern scoring heuristics."""

    def test_sequential_default_for_light(self):
        selection = select_pattern(gravity="light", task_id="001", task_name="Test")
        assert selection.pattern == CoordinationPattern.SEQUENTIAL
        assert selection.score == 1.0

    def test_sequential_when_no_flags(self):
        """Without feature flags, only SEQUENTIAL qualifies."""
        selection = select_pattern(
            gravity="standard",
            roster=[("agent1", "model1"), ("agent2", "model2")],
            task_id="001",
            task_name="Test",
            enabled_flags=None,
        )
        assert selection.pattern == CoordinationPattern.SEQUENTIAL

    def test_feature_flag_gating(self):
        """Patterns require their feature flags."""
        # Without flag: sequential
        selection = select_pattern(
            gravity="standard",
            roster=[("a1", "m1"), ("a2", "m2")],
            task_id="001",
            task_name="Review code",
            enabled_flags=set(),
        )
        assert selection.pattern == CoordinationPattern.SEQUENTIAL

        # With flag: may select review_loop
        selection = select_pattern(
            gravity="standard",
            roster=[("a1", "m1"), ("a2", "m2")],
            task_id="001",
            task_name="Review code",
            phase_id="6-code-review",
            enabled_flags={"coordination.review_loop"},
        )
        # Should score higher than sequential due to phase bonus
        assert selection.all_scores.get("review_loop", 0) > 0

    def test_phase_bonus_review_loop(self):
        """Phase 6 gives review_loop a +3.0 bonus."""
        selector = PatternSelector(enabled_flags={"coordination.review_loop"})
        selection = selector.select(
            gravity="standard",
            roster=[("a1", "m1"), ("a2", "m2")],
            task_id="001",
            task_name="Code review",
            phase_id="6-code-review",
        )
        review_score = selection.all_scores.get("review_loop", 0)
        assert review_score > 1.0  # Must beat sequential's 1.0

    def test_phase_bonus_saga(self):
        """Phase 8 gives saga a +3.0 bonus."""
        selector = PatternSelector(enabled_flags={"coordination.saga"})
        selection = selector.select(
            gravity="intensive",
            roster=[("a1", "m1")],
            task_id="001",
            task_name="Deploy",
            phase_id="8-deployment",
        )
        saga_score = selection.all_scores.get("saga", 0)
        assert saga_score > 1.0

    def test_phase_bonus_debate(self):
        """Phase 2-3 gives debate a +2.0 bonus."""
        selector = PatternSelector(enabled_flags={"coordination.debate"})
        selection = selector.select(
            gravity="intensive",
            roster=[("a1", "m1"), ("a2", "m2"), ("a3", "m3")],
            task_id="001",
            task_name="Architecture decision",
            phase_id="2-prd",
        )
        debate_score = selection.all_scores.get("debate", 0)
        assert debate_score > 1.0

    def test_agent_count_gates(self):
        """Patterns gated by min/max agent count."""
        selector = PatternSelector(enabled_flags={"coordination.debate"})
        # Only 1 agent — debate needs 3
        selection = selector.select(
            gravity="intensive",
            roster=[("a1", "m1")],
            task_id="001",
            task_name="Test",
        )
        assert selection.all_scores.get("debate", 0) < 0

    def test_intensive_gravity_bonus(self):
        """INTENSIVE gravity adds +2.0 to qualified patterns."""
        selector = PatternSelector(enabled_flags={"coordination.escalation"})
        selection = selector.select(
            gravity="intensive",
            roster=[("a1", "m1")],
            task_id="001",
            task_name="Complex task",
        )
        esc_score = selection.all_scores.get("escalation", 0)
        # Should have intensive bonus
        assert esc_score > 1.0

    def test_all_scores_populated(self):
        selection = select_pattern(gravity="standard", task_id="001", task_name="Test")
        assert len(selection.all_scores) == len(CoordinationPattern)

    def test_selection_has_reason(self):
        selection = select_pattern(gravity="standard", task_id="001", task_name="Test")
        assert isinstance(selection.reason, str)
        assert len(selection.reason) > 0


class TestPatternSpec:
    """Test PatternSpec frozen behavior."""

    def test_frozen(self):
        spec = PATTERN_CATALOG[CoordinationPattern.SEQUENTIAL]
        with pytest.raises(AttributeError):
            spec.min_agents = 5
