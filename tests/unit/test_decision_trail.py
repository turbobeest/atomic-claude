"""Tests for core.graph.decision_trail."""

import pytest
from unittest.mock import MagicMock, patch

from core.graph.decision_trail import DecisionTrail, TrailEntry


class TestDecisionTrail:
    """Test DecisionTrail in-memory behavior."""

    def test_record_creates_entry(self):
        trail = DecisionTrail(phase_id="0-setup", task_id="001")
        decision_id = trail.record("Use Python", "Better ecosystem")
        assert decision_id.startswith("decision-")
        assert trail.has_entries()
        entries = trail.get_entries()
        assert len(entries) == 1
        assert entries[0].title == "Use Python"
        assert entries[0].rationale == "Better ecosystem"

    def test_default_confidence(self):
        trail = DecisionTrail(phase_id="0-setup", task_id="001")
        trail.record("Choice", "Because")
        assert trail.get_entries()[0].confidence == 0.7

    def test_custom_confidence(self):
        trail = DecisionTrail(phase_id="0-setup", task_id="001")
        trail.record("Choice", "Because", confidence=0.95)
        assert trail.get_entries()[0].confidence == 0.95

    def test_confidence_clamped_high(self):
        trail = DecisionTrail(phase_id="0-setup", task_id="001")
        trail.record("Choice", "Because", confidence=1.5)
        assert trail.get_entries()[0].confidence == 1.0

    def test_confidence_clamped_low(self):
        trail = DecisionTrail(phase_id="0-setup", task_id="001")
        trail.record("Choice", "Because", confidence=-0.5)
        assert trail.get_entries()[0].confidence == 0.0

    def test_alternatives(self):
        trail = DecisionTrail(phase_id="0-setup", task_id="001")
        alts = [
            {"title": "Java", "reason_rejected": "Too verbose"},
            {"title": "Go", "reason_rejected": "Less ecosystem"},
        ]
        trail.record("Use Python", "Better ecosystem", alternatives=alts)
        entry = trail.get_entries()[0]
        assert len(entry.alternatives) == 2
        assert entry.alternatives[0]["title"] == "Java"

    def test_multiple_entries(self):
        trail = DecisionTrail(phase_id="0-setup", task_id="001")
        trail.record("Decision 1", "Reason 1")
        trail.record("Decision 2", "Reason 2")
        trail.record("Decision 3", "Reason 3")
        assert len(trail.get_entries()) == 3

    def test_has_entries_empty(self):
        trail = DecisionTrail(phase_id="0-setup", task_id="001")
        assert not trail.has_entries()

    def test_status_field(self):
        trail = DecisionTrail(phase_id="0-setup", task_id="001")
        trail.record("Choice", "Because", status="rejected")
        assert trail.get_entries()[0].status == "rejected"


class TestDecisionTrailGraphWrite:
    """Test graph persistence (mocked)."""

    def test_writes_decision_node(self):
        graph = MagicMock()
        trail = DecisionTrail(phase_id="0-setup", task_id="001", graph=graph)
        trail.record("Use Python", "Better ecosystem", confidence=0.9)

        graph.writer.create_node.assert_called_once()
        call_args = graph.writer.create_node.call_args
        assert call_args[0][0] == "Decision"
        props = call_args[0][1]
        assert props["title"] == "Use Python"
        assert props["confidence"] == 0.9

    def test_creates_informed_by_relationship(self):
        graph = MagicMock()
        trail = DecisionTrail(phase_id="0-setup", task_id="001", graph=graph)
        decision_id = trail.record("Choice", "Reason")

        graph.writer.create_relationship.assert_called_once()
        call_args = graph.writer.create_relationship.call_args
        assert call_args[0][0] == "Task"
        assert call_args[0][1] == "001"
        assert call_args[0][2] == "INFORMED_BY"
        assert call_args[0][3] == "Decision"

    def test_graph_failure_graceful(self):
        graph = MagicMock()
        graph.writer.create_node.side_effect = RuntimeError("Graph down")
        trail = DecisionTrail(phase_id="0-setup", task_id="001", graph=graph)
        # Should not raise
        decision_id = trail.record("Choice", "Reason")
        assert decision_id.startswith("decision-")
        assert trail.has_entries()


class TestDecisionTrailGetTrail:
    """Test static get_trail() query."""

    def test_returns_empty_without_graph(self):
        result = DecisionTrail.get_trail("001", graph=None)
        assert result == []

    def test_returns_empty_on_graph_error(self):
        graph = MagicMock()
        graph.reader.get_nodes.side_effect = RuntimeError("Query failed")
        result = DecisionTrail.get_trail("001", graph=graph)
        assert result == []


class TestTaskMemoryTrailProperty:
    """Test TaskMemory.trail lazy creation."""

    def test_trail_property_creates_trail(self):
        from orchestration.task_memory import TaskMemory
        mem = TaskMemory("0-setup", "001", "Test Task")
        trail = mem.trail
        assert isinstance(trail, DecisionTrail)

    def test_trail_property_is_cached(self):
        from orchestration.task_memory import TaskMemory
        mem = TaskMemory("0-setup", "001", "Test Task")
        trail1 = mem.trail
        trail2 = mem.trail
        assert trail1 is trail2

    def test_trail_with_graph(self):
        from orchestration.task_memory import TaskMemory
        graph = MagicMock()
        mem = TaskMemory("0-setup", "001", "Test Task")
        mem.set_graph(graph)
        trail = mem.trail
        assert trail._graph is graph
