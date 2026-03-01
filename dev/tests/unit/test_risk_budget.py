"""Tests for graph-derived risk budget computation."""

import random
import pytest
from unittest.mock import MagicMock
from core.llm.risk import (
    compute_blast_radius,
    has_downstream_validation,
    get_traceability_depth,
    compute_risk_budget,
)


@pytest.fixture
def mock_graph():
    """Create a mock GraphManager with a mock reader."""
    graph = MagicMock()
    graph.reader = MagicMock()
    # Default: no neighbors, no node
    graph.reader.get_neighbors.return_value = []
    graph.reader.get_node.return_value = None
    return graph


class TestBlastRadius:

    @pytest.mark.unit
    def test_blast_radius_leaf_node(self, mock_graph):
        """Task with zero dependents -> blast_radius = 0.0."""
        # get_neighbors for TASK_DEPENDS_ON inbound returns empty
        # get_neighbors for IMPLEMENTS returns empty
        result = compute_blast_radius("task-99", mock_graph)
        assert result == pytest.approx(0.0)

    @pytest.mark.unit
    def test_blast_radius_high_dependents(self, mock_graph):
        """Task with 5+ direct dependents -> blast_radius approaching 1.0."""
        def side_effect(label, node_id, rel_type=None, direction="out"):
            if rel_type == "TASK_DEPENDS_ON" and direction == "in":
                if node_id == "task-1":
                    return [{"id": f"dep-{i}"} for i in range(5)]
                # Don't recurse further
                return []
            if rel_type == "IMPLEMENTS":
                return []
            return []
        mock_graph.reader.get_neighbors.side_effect = side_effect

        result = compute_blast_radius("task-1", mock_graph)
        # 5 direct * 0.3 = 1.5, capped at 1.0
        assert result == pytest.approx(1.0)

    @pytest.mark.unit
    def test_blast_radius_with_conflicts(self, mock_graph):
        """CONFLICTS_WITH edges add to blast score."""
        def side_effect(label, node_id, rel_type=None, direction="out"):
            if rel_type == "TASK_DEPENDS_ON" and direction == "in":
                return []  # No dependents
            if rel_type == "IMPLEMENTS" and direction == "out":
                return [{"id": "req-1"}]
            if rel_type == "CONFLICTS_WITH" and direction == "both":
                return [{"id": "req-2"}]  # Has a conflict
            return []
        mock_graph.reader.get_neighbors.side_effect = side_effect

        result = compute_blast_radius("task-1", mock_graph)
        # 0 dependents * 0.3 + 0 transitive * 0.1 + 1.0 conflict = 1.0
        assert result == pytest.approx(1.0)


class TestDownstreamValidation:

    @pytest.mark.unit
    def test_validation_coverage_phase5(self, mock_graph):
        """Phase 5 task returns has_downstream_validation=True."""
        mock_graph.reader.get_neighbors.return_value = []  # No REVIEW_OF
        mock_graph.reader.get_node.return_value = {"id": "task-504", "phase": "5-impl"}

        result = has_downstream_validation("task-504", mock_graph)
        assert result is True

    @pytest.mark.unit
    def test_validation_coverage_no_review(self, mock_graph):
        """Phase 2 task with no reviewer returns False."""
        mock_graph.reader.get_neighbors.return_value = []
        mock_graph.reader.get_node.return_value = {"id": "task-204", "phase": "2-prd"}

        result = has_downstream_validation("task-204", mock_graph)
        assert result is False


class TestTraceabilityDepth:

    @pytest.mark.unit
    def test_traceability_depth_shallow(self, mock_graph):
        """Task with one requirement, no further upstream = depth 1."""
        def side_effect(label, node_id, rel_type=None, direction="out"):
            if label == "Task" and rel_type == "IMPLEMENTS":
                return [{"id": "req-1"}]
            if label == "Requirement" and rel_type == "DERIVED_FROM":
                return []  # No further upstream
            return []
        mock_graph.reader.get_neighbors.side_effect = side_effect

        result = get_traceability_depth("task-1", mock_graph)
        assert result == 1

    @pytest.mark.unit
    def test_traceability_depth_deep(self, mock_graph):
        """Task -> Requirement -> 3 upstream sources = depth 4."""
        def side_effect(label, node_id, rel_type=None, direction="out"):
            if label == "Task" and rel_type == "IMPLEMENTS":
                return [{"id": "req-1"}]
            if label == "Requirement" and rel_type == "DERIVED_FROM":
                return [{"id": "src-1"}, {"id": "src-2"}, {"id": "src-3"}]
            return []
        mock_graph.reader.get_neighbors.side_effect = side_effect

        result = get_traceability_depth("task-1", mock_graph)
        # 1 (implements) + 3 (derived_from sources) = 4
        assert result == 4


class TestCombinedBudget:

    @pytest.mark.unit
    def test_combined_budget_high_blast(self, mock_graph):
        """High blast + no validation -> budget near 0.0."""
        # 4 direct dependents -> blast = min(4*0.3, 1.0) = 1.0
        def side_effect(label, node_id, rel_type=None, direction="out"):
            if rel_type == "TASK_DEPENDS_ON" and direction == "in":
                if node_id == "task-1":
                    return [{"id": f"d{i}"} for i in range(4)]
                return []
            if rel_type == "REVIEW_OF" and direction == "in":
                return []
            if rel_type == "IMPLEMENTS":
                return []
            if rel_type == "DERIVED_FROM":
                return []
            return []
        mock_graph.reader.get_neighbors.side_effect = side_effect
        mock_graph.reader.get_node.return_value = {"id": "task-1", "phase": "3-tasking"}

        result = compute_risk_budget("task-1", mock_graph)
        assert result <= 0.1  # Near zero

    @pytest.mark.unit
    def test_combined_budget_low_blast_validated(self, mock_graph):
        """Low blast + validated -> budget near 0.85-1.0."""
        def side_effect(label, node_id, rel_type=None, direction="out"):
            if rel_type == "TASK_DEPENDS_ON" and direction == "in":
                return []  # Leaf node
            if rel_type == "REVIEW_OF" and direction == "in":
                return []
            if rel_type == "IMPLEMENTS":
                return []
            if rel_type == "DERIVED_FROM":
                return []
            return []
        mock_graph.reader.get_neighbors.side_effect = side_effect
        mock_graph.reader.get_node.return_value = {"id": "task-leaf", "phase": "5-impl"}

        result = compute_risk_budget("task-leaf", mock_graph)
        # blast=0 -> budget=1.0, validated(phase5)=True -> 1.0*1.3 capped=1.0, depth=0
        assert result >= 0.85

    @pytest.mark.unit
    def test_combined_budget_graph_unavailable(self):
        """Graph exception -> budget stays 0.0 (conservative fallback)."""
        result = compute_risk_budget("task-1", graph=None)
        assert result == 0.0

    @pytest.mark.unit
    def test_budget_never_exceeds_bounds(self, mock_graph):
        """Random inputs always produce 0.0 <= budget <= 1.0."""
        for _ in range(20):
            n_deps = random.randint(0, 10)
            phase_num = random.choice(["2-prd", "3-tasking", "5-impl", "7-integration"])
            n_sources = random.randint(0, 8)

            def make_side_effect(nd, ns):
                def side_effect(label, node_id, rel_type=None, direction="out"):
                    if rel_type == "TASK_DEPENDS_ON" and direction == "in":
                        if node_id == "fuzz":
                            return [{"id": f"d{i}"} for i in range(nd)]
                        return []
                    if rel_type == "IMPLEMENTS":
                        return [{"id": "req-1"}] if ns > 0 else []
                    if rel_type == "DERIVED_FROM":
                        return [{"id": f"s{i}"} for i in range(ns)]
                    if rel_type == "REVIEW_OF" and direction == "in":
                        return []
                    if rel_type == "CONFLICTS_WITH":
                        return []
                    return []
                return side_effect

            mock_graph.reader.get_neighbors.side_effect = make_side_effect(n_deps, n_sources)
            mock_graph.reader.get_node.return_value = {"id": "fuzz", "phase": phase_num}

            result = compute_risk_budget("fuzz", mock_graph)
            assert 0.0 <= result <= 1.0, f"Out of bounds: {result}"
