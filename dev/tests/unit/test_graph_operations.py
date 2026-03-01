"""Unit tests for core/graph/operations.py — mock-based."""
import pytest
from unittest.mock import MagicMock, patch
from core.graph.operations import GraphOperations


class MockQueryResult:
    def __init__(self, rows=None):
        self.result_set = rows or []


@pytest.fixture
def mock_reader():
    reader = MagicMock()
    reader.conn = MagicMock()
    return reader


@pytest.fixture
def mock_writer():
    return MagicMock()


@pytest.fixture
def ops(mock_reader, mock_writer):
    return GraphOperations(mock_reader, mock_writer)


class TestAnalyzeComplexity:

    def test_basic_scoring(self, ops, mock_reader, mock_writer):
        mock_reader.get_task_topology.return_value = [
            {"id": 1, "title": "Setup", "category": "infrastructure",
             "req_count": 2, "dep_count": 0, "transitive_deps": 0, "conflict_count": 0},
            {"id": 2, "title": "Auth", "category": "feature",
             "req_count": 5, "dep_count": 2, "transitive_deps": 3, "conflict_count": 1},
        ]
        result = ops.analyze_complexity()
        assert len(result["tasks"]) == 2
        # Task 1: 1 + 2*0.8 + 0 + 0 + 0 = 2.6 -> 3
        assert result["tasks"][0]["score"] == 3
        # Task 2: 1 + 5*0.8 + 2*0.5 + 3*0.3 + 1*1.5 = 1+4+1+0.9+1.5 = 8.4 -> 8
        assert result["tasks"][1]["score"] == 8

    def test_complexity_capped_at_10(self, ops, mock_reader, mock_writer):
        mock_reader.get_task_topology.return_value = [
            {"id": 1, "title": "Monster", "category": "feature",
             "req_count": 20, "dep_count": 10, "transitive_deps": 10, "conflict_count": 5},
        ]
        result = ops.analyze_complexity()
        assert result["tasks"][0]["score"] == 10


class TestValidateDependencies:

    def test_valid_graph(self, ops, mock_reader):
        mock_reader.detect_cycles.return_value = []
        mock_reader.find_orphan_tasks.return_value = []
        result = ops.validate_dependencies()
        assert result["valid"] is True
        assert result["cycles"] == []
        assert result["orphans"] == []

    def test_cycle_detected(self, ops, mock_reader):
        mock_reader.detect_cycles.return_value = [[1, 2, 3, 1]]
        mock_reader.find_orphan_tasks.return_value = []
        result = ops.validate_dependencies()
        assert result["valid"] is False
        assert len(result["cycles"]) == 1


class TestAddNewTask:

    def test_add_task(self, ops, mock_reader, mock_writer):
        mock_reader.conn.query.return_value = MockQueryResult([[10]])
        new_id = ops.add_new_task("New Task", "Description", depends_on=[5])
        assert new_id == 11
        mock_writer.add_node.assert_called_once()
        mock_writer.add_edge.assert_called_once()


class TestResearchSaveTo:

    def test_creates_finding_and_edge(self, ops, mock_writer):
        finding_id = ops.research_save_to(5, "Research content here")
        assert finding_id.startswith("R-5-")
        mock_writer.add_node.assert_called_once()
        mock_writer.add_edge.assert_called_once()
        # Verify edge type
        edge_call = mock_writer.add_edge.call_args
        assert edge_call[0][0] == "INFORMED_BY"
