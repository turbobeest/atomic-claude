"""Unit tests for core/graph/writer.py — mock-based, no Docker."""
import pytest
from unittest.mock import MagicMock, patch, call
from core.graph.writer import GraphWriter
from core.graph.exceptions import SchemaValidationError


class MockQueryResult:
    def __init__(self, rows=None):
        self.result_set = rows or []


@pytest.fixture
def mock_conn():
    conn = MagicMock()
    conn.query.return_value = MockQueryResult()
    return conn


@pytest.fixture
def writer(mock_conn):
    return GraphWriter(mock_conn)


class TestAddNode:

    def test_add_source_node(self, writer, mock_conn):
        writer.add_node("Source", {"id": "S-1", "type": "corpus", "title": "README"})
        mock_conn.query.assert_called_once()
        cypher = mock_conn.query.call_args[0][0]
        assert "CREATE" in cypher
        assert ":Source" in cypher

    def test_add_finding_with_defaults(self, writer, mock_conn):
        writer.add_node("Finding", {
            "id": "F-1", "category": "vision", "title": "T", "content": "C"
        })
        mock_conn.query.assert_called_once()
        params = mock_conn.query.call_args[0][1]
        # Should have defaults applied (confidence, phase)
        param_values = list(params.values())
        assert 0.8 in param_values  # default confidence
        assert "1-discovery" in param_values  # default phase

    def test_add_node_validation_error(self, writer):
        with pytest.raises(SchemaValidationError):
            writer.add_node("Source", {"id": "S-1"})  # missing type and title

    def test_add_node_invalid_enum_value(self, writer):
        with pytest.raises(SchemaValidationError):
            writer.add_node("Source", {"id": "S-1", "type": "bogus", "title": "T"})


class TestUpdateNode:

    def test_update_returns_true_on_match(self, writer, mock_conn):
        mock_conn.query.return_value = MockQueryResult([[MagicMock()]])
        result = writer.update_node("Task", 1, {"status": "done"})
        assert result is True

    def test_update_returns_false_on_no_match(self, writer, mock_conn):
        mock_conn.query.return_value = MockQueryResult([])
        result = writer.update_node("Task", 999, {"status": "done"})
        assert result is False

    def test_update_empty_updates(self, writer, mock_conn):
        result = writer.update_node("Task", 1, {})
        assert result is False
        mock_conn.query.assert_not_called()


class TestAddEdge:

    def test_add_valid_edge(self, writer, mock_conn):
        writer.add_edge("IMPLEMENTS", "Task", 1, "Requirement", "REQ-1")
        mock_conn.query.assert_called_once()
        cypher = mock_conn.query.call_args[0][0]
        assert "IMPLEMENTS" in cypher
        assert ":Task" in cypher
        assert ":Requirement" in cypher

    def test_add_edge_with_properties(self, writer, mock_conn):
        writer.add_edge("CONTAINS", "Feature", "F-1", "Requirement", "R-1", {"order": 1})
        cypher = mock_conn.query.call_args[0][0]
        assert "order" in cypher

    def test_add_invalid_edge(self, writer):
        with pytest.raises(SchemaValidationError):
            writer.add_edge("IMPLEMENTS", "Source", "S-1", "Requirement", "R-1")


class TestDeleteNode:

    def test_delete_existing(self, writer, mock_conn):
        mock_conn.query.return_value = MockQueryResult([[1]])
        result = writer.delete_node("Task", 1)
        assert result is True

    def test_delete_nonexistent(self, writer, mock_conn):
        mock_conn.query.return_value = MockQueryResult([[0]])
        result = writer.delete_node("Task", 999)
        assert result is False


class TestBulkWrite:

    def test_bulk_multiple_ops(self, writer, mock_conn):
        ops = [
            {"op": "add_node", "label": "Source", "properties": {"id": "S-1", "type": "corpus", "title": "T"}},
            {"op": "add_node", "label": "Finding", "properties": {"id": "F-1", "category": "vision", "title": "T", "content": "C"}},
        ]
        count = writer.bulk_write(ops)
        assert count == 2
        assert mock_conn.query.call_count == 2

    def test_bulk_continues_on_error(self, writer, mock_conn):
        """Bulk write should continue even if one op fails."""
        mock_conn.query.side_effect = [Exception("fail"), MockQueryResult()]
        ops = [
            {"op": "add_node", "label": "Source", "properties": {"id": "S-1", "type": "corpus", "title": "T"}},
            {"op": "add_node", "label": "Source", "properties": {"id": "S-2", "type": "corpus", "title": "T2"}},
        ]
        count = writer.bulk_write(ops)
        assert count == 1  # second succeeded
