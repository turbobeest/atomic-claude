"""Unit tests for core/graph/reader.py — mock-based, no Docker."""
import pytest
from unittest.mock import MagicMock
from core.graph.reader import GraphReader


class MockNode:
    def __init__(self, props):
        self.properties = props


class MockQueryResult:
    def __init__(self, rows=None):
        self.result_set = rows or []


@pytest.fixture
def mock_conn():
    conn = MagicMock()
    conn.query.return_value = MockQueryResult()
    return conn


@pytest.fixture
def reader(mock_conn):
    return GraphReader(mock_conn)


class TestGetNode:

    def test_found(self, reader, mock_conn):
        node = MockNode({"id": "F-1", "title": "Test"})
        mock_conn.query.return_value = MockQueryResult([[node]])
        result = reader.get_node("Finding", "F-1")
        assert result == {"id": "F-1", "title": "Test"}

    def test_not_found(self, reader, mock_conn):
        mock_conn.query.return_value = MockQueryResult([])
        result = reader.get_node("Finding", "F-999")
        assert result is None

    def test_spec_uses_task_id(self, reader, mock_conn):
        mock_conn.query.return_value = MockQueryResult([])
        reader.get_node("Spec", 5)
        cypher = mock_conn.query.call_args[0][0]
        assert "task_id" in cypher


class TestGetNodes:

    def test_with_filters(self, reader, mock_conn):
        reader.get_nodes("Task", filters={"status": "pending"})
        cypher = mock_conn.query.call_args[0][0]
        assert "WHERE" in cypher
        assert "status" in cypher

    def test_with_limit(self, reader, mock_conn):
        reader.get_nodes("Finding", limit=5)
        cypher = mock_conn.query.call_args[0][0]
        assert "LIMIT 5" in cypher

    def test_with_order(self, reader, mock_conn):
        reader.get_nodes("Task", order_by="id")
        cypher = mock_conn.query.call_args[0][0]
        assert "ORDER BY" in cypher


class TestGetNeighbors:

    def test_outgoing(self, reader, mock_conn):
        reader.get_neighbors("Task", 1, rel_type="IMPLEMENTS", direction="out")
        cypher = mock_conn.query.call_args[0][0]
        assert ":IMPLEMENTS" in cypher
        assert "->" in cypher

    def test_incoming(self, reader, mock_conn):
        reader.get_neighbors("Task", 1, direction="in")
        cypher = mock_conn.query.call_args[0][0]
        assert "<-" in cypher


class TestTopologicalOrder:

    def test_simple_chain(self, reader, mock_conn):
        """Tasks 1 -> 2 -> 3 should produce [1, 2, 3]."""
        mock_conn.query.return_value = MockQueryResult([
            [1, [None]],   # Task 1 depends on nothing (None from OPTIONAL MATCH)
            [2, [1]],      # Task 2 depends on Task 1
            [3, [2]],      # Task 3 depends on Task 2
        ])
        order = reader.get_topological_order()
        assert order == [1, 2, 3]

    def test_independent_tasks(self, reader, mock_conn):
        mock_conn.query.return_value = MockQueryResult([
            [1, [None]],
            [2, [None]],
            [3, [None]],
        ])
        order = reader.get_topological_order()
        assert set(order) == {1, 2, 3}


class TestNodeToDict:

    def test_with_properties(self):
        node = MockNode({"id": 1, "title": "Test"})
        assert GraphReader._node_to_dict(node) == {"id": 1, "title": "Test"}

    def test_with_none(self):
        assert GraphReader._node_to_dict(None) == {}

    def test_with_dict(self):
        assert GraphReader._node_to_dict({"a": 1}) == {"a": 1}
