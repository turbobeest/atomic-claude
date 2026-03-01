"""Tests for Phase 5 graph integration -- task loading and status updates."""

import pytest
from unittest.mock import MagicMock, patch

from core.graph.manager import GraphManager


# Reuse the mock pattern from test_graph_memory.py
class MockQueryResult:
    def __init__(self, rows=None):
        self.result_set = rows or []


@pytest.fixture
def mock_conn():
    conn = MagicMock()
    conn.query.return_value = MockQueryResult()
    return conn


@pytest.fixture
def manager(mock_conn):
    return GraphManager(mock_conn, phase_id="5-implementation")


def _make_node(props):
    """Create a mock FalkorDB node with .properties dict."""
    node = MagicMock()
    node.properties = props
    return node


# ============================================================================
# GraphManager.update_task_status()
# ============================================================================

@pytest.mark.unit
class TestUpdateTaskStatus:
    """Tests for GraphManager.update_task_status()."""

    def test_valid_status_updates(self, manager, mock_conn):
        """update_task_status fires correct Cypher SET for each valid status."""
        for status in ("pending", "in_progress", "done", "blocked"):
            mock_conn.query.return_value = MockQueryResult([[_make_node({"id": 1})]])
            result = manager.update_task_status(1, status)
            assert result is True
            cypher = mock_conn.query.call_args[0][0]
            assert "SET" in cypher
            assert status in str(mock_conn.query.call_args)

    def test_invalid_status_raises_valueerror(self, manager):
        """update_task_status rejects invalid status strings."""
        with pytest.raises(ValueError, match="Invalid task status"):
            manager.update_task_status(1, "invalid_status")

    def test_nonexistent_task_returns_false(self, manager, mock_conn):
        """update_task_status returns False if task node doesn't exist."""
        mock_conn.query.return_value = MockQueryResult([])
        result = manager.update_task_status(999, "done")
        assert result is False


# ============================================================================
# load_tasks_from_graph()
# ============================================================================

@pytest.mark.unit
class TestLoadTasksFromGraph:
    """Tests for load_tasks_from_graph()."""

    def test_returns_dag_compatible_dicts(self, manager, mock_conn):
        """Tasks returned have id, title, description, dependencies fields."""
        from phases.phase_05_implementation.tasks.task_504_tdd_execution import load_tasks_from_graph

        # Mock get_nodes to return task nodes
        task_nodes = [
            {"id": 1, "title": "Setup DB", "description": "Init database", "status": "pending"},
            {"id": 2, "title": "Add API", "description": "REST endpoints", "status": "pending"},
        ]

        # Mock get_neighbors: task 2 depends on task 1, both have specs
        def mock_get_neighbors(label, node_id, rel_type=None, direction="out"):
            if rel_type == "TASK_DEPENDS_ON":
                if node_id == 2:
                    return [{"id": 1}]
                return []
            if rel_type == "HAS_SPEC":
                return [{"id": f"spec-{node_id}", "task_id": str(node_id)}] * 4  # >= 4 for filter
            return []

        manager.reader.get_nodes = MagicMock(return_value=task_nodes)
        manager.reader.get_neighbors = MagicMock(side_effect=mock_get_neighbors)

        tasks = load_tasks_from_graph(manager)

        assert len(tasks) == 2
        for t in tasks:
            assert "id" in t
            assert "title" in t
            assert "description" in t
            assert "dependencies" in t

        # Check task 2 has dependency on task 1
        task2 = next(t for t in tasks if t["id"] == "2")
        assert "1" in task2["dependencies"]

    def test_fallback_on_empty_graph(self, manager):
        """Returns empty list when graph has no Task nodes."""
        manager.reader.get_nodes = MagicMock(return_value=[])

        from phases.phase_05_implementation.tasks.task_504_tdd_execution import load_tasks_from_graph
        tasks = load_tasks_from_graph(manager)
        assert tasks == []

    def test_fallback_on_exception(self, manager):
        """Returns empty list on graph error (graceful degradation)."""
        manager.reader.get_nodes = MagicMock(side_effect=Exception("connection lost"))

        from phases.phase_05_implementation.tasks.task_504_tdd_execution import load_tasks_from_graph
        tasks = load_tasks_from_graph(manager)
        assert tasks == []


# ============================================================================
# load_specs_from_graph()
# ============================================================================

@pytest.mark.unit
class TestLoadSpecsFromGraph:
    """Tests for load_specs_from_graph()."""

    def test_returns_spec_dict_keyed_by_task_id(self, manager):
        """Specs returned as dict keyed by task_id string."""
        from phases.phase_05_implementation.tasks.task_504_tdd_execution import load_specs_from_graph

        spec_nodes = [
            {"id": "spec-1", "task_id": "1", "test_strategy": "unit tests first"},
            {"id": "spec-2", "task_id": "2", "interfaces": "REST API"},
        ]
        manager.reader.get_nodes = MagicMock(return_value=spec_nodes)

        specs = load_specs_from_graph(manager)

        assert "1" in specs
        assert "2" in specs
        assert specs["1"]["task_id"] == "1"
        assert specs["2"]["task_id"] == "2"

    def test_spec_preserves_extra_properties(self, manager):
        """Extra properties from Spec nodes are passed through."""
        from phases.phase_05_implementation.tasks.task_504_tdd_execution import load_specs_from_graph

        spec_nodes = [
            {"id": "spec-1", "task_id": "1", "test_strategy": "integration",
             "interfaces": "gRPC", "acceptance_criteria": "100% coverage"},
        ]
        manager.reader.get_nodes = MagicMock(return_value=spec_nodes)

        specs = load_specs_from_graph(manager)

        assert specs["1"]["test_strategy"] == "integration"
        assert specs["1"]["interfaces"] == "gRPC"
        assert specs["1"]["acceptance_criteria"] == "100% coverage"

    def test_fallback_on_empty_graph(self, manager):
        """Returns empty dict when graph has no Spec nodes."""
        manager.reader.get_nodes = MagicMock(return_value=[])

        from phases.phase_05_implementation.tasks.task_504_tdd_execution import load_specs_from_graph
        specs = load_specs_from_graph(manager)
        assert specs == {}

    def test_fallback_on_exception(self, manager):
        """Returns empty dict on graph error."""
        manager.reader.get_nodes = MagicMock(side_effect=Exception("query failed"))

        from phases.phase_05_implementation.tasks.task_504_tdd_execution import load_specs_from_graph
        specs = load_specs_from_graph(manager)
        assert specs == {}

    def test_skips_nodes_without_task_id(self, manager):
        """Spec nodes missing task_id are silently skipped."""
        from phases.phase_05_implementation.tasks.task_504_tdd_execution import load_specs_from_graph

        spec_nodes = [
            {"id": "spec-orphan", "task_id": ""},
            {"id": "spec-1", "task_id": "1", "test_strategy": "unit"},
        ]
        manager.reader.get_nodes = MagicMock(return_value=spec_nodes)

        specs = load_specs_from_graph(manager)

        assert len(specs) == 1
        assert "1" in specs
