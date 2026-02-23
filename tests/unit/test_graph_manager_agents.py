"""Unit tests for GraphManager agent operations — mock-based, no Docker."""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.graph.manager import GraphManager


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
    return GraphManager(mock_conn, phase_id="1-discovery")


class TestAddAgent:

    def test_add_agent_creates_node(self, manager, mock_conn):
        manager.add_agent("python-pro", tier="expert",
                          category="backend-ecosystems", role="executor")
        mock_conn.query.assert_called_once()
        cypher = mock_conn.query.call_args[0][0]
        assert "CREATE" in cypher
        assert ":Agent" in cypher

    def test_add_agent_with_extra_kwargs(self, manager, mock_conn):
        manager.add_agent("python-pro", tier="expert",
                          category="backend-ecosystems", role="executor",
                          description="Python specialist",
                          composite_score=9.2)
        params = mock_conn.query.call_args[0][1]
        param_values = list(params.values())
        assert "Python specialist" in param_values
        assert 9.2 in param_values


class TestLoadAgentsFromManifest:

    def _write_manifest(self, tmp_path, agents):
        manifest = {"version": "3.0.0", "agents": agents}
        path = tmp_path / "agent-manifest.json"
        path.write_text(json.dumps(manifest))
        return path

    def test_load_from_manifest(self, manager, mock_conn, tmp_path):
        agents = [
            {"name": "python-pro", "tier": "expert",
             "category": "backend-ecosystems", "role": "executor",
             "description": "Python specialist", "composite_score": 9.0},
            {"name": "go-architect", "tier": "expert",
             "category": "backend-ecosystems", "role": "architect",
             "description": "Go architect", "composite_score": 8.5},
        ]
        path = self._write_manifest(tmp_path, agents)

        # count_nodes returns 0 → not loaded yet
        mock_conn.query.return_value = MockQueryResult([[0]])

        loaded = manager.load_agents_from_manifest(path)
        assert loaded == 2

    def test_idempotent_skip_when_loaded(self, manager, mock_conn, tmp_path):
        agents = [
            {"name": "python-pro", "tier": "expert",
             "category": "backend-ecosystems", "role": "executor"},
        ]
        path = self._write_manifest(tmp_path, agents)

        # count_nodes returns 1 → already loaded
        mock_conn.query.return_value = MockQueryResult([[1]])

        loaded = manager.load_agents_from_manifest(path)
        assert loaded == 0

    def test_missing_manifest_returns_zero(self, manager):
        loaded = manager.load_agents_from_manifest(Path("/nonexistent/manifest.json"))
        assert loaded == 0

    def test_empty_agents_list(self, manager, tmp_path):
        path = self._write_manifest(tmp_path, [])
        loaded = manager.load_agents_from_manifest(path)
        assert loaded == 0


class TestQueryAgentCatalog:

    def _mock_agent_nodes(self, agents):
        """Create mock FalkorDB node results."""
        rows = []
        for a in agents:
            node = MagicMock()
            node.properties = a
            rows.append([node])
        return rows

    def test_catalog_groups_by_category(self, manager, mock_conn):
        agents = [
            {"id": "python-pro", "name": "python-pro", "tier": "expert",
             "category": "backend-ecosystems", "role": "executor",
             "description": "Python specialist for backend services"},
            {"id": "react-guru", "name": "react-guru", "tier": "expert",
             "category": "frontend-ecosystems", "role": "executor",
             "description": "React frontend expert"},
        ]
        mock_conn.query.return_value = MockQueryResult(
            self._mock_agent_nodes(agents)
        )

        catalog = manager.query_agent_catalog(tier="expert")
        assert "### backend-ecosystems" in catalog
        assert "### frontend-ecosystems" in catalog
        assert "python-pro" in catalog
        assert "react-guru" in catalog

    def test_catalog_with_category_filter(self, manager, mock_conn):
        agents = [
            {"id": "python-pro", "name": "python-pro", "tier": "expert",
             "category": "backend-ecosystems", "role": "executor",
             "description": "Python specialist"},
            {"id": "react-guru", "name": "react-guru", "tier": "expert",
             "category": "frontend-ecosystems", "role": "executor",
             "description": "React expert"},
        ]
        mock_conn.query.return_value = MockQueryResult(
            self._mock_agent_nodes(agents)
        )

        catalog = manager.query_agent_catalog(categories=["backend-ecosystems"])
        assert "python-pro" in catalog
        assert "react-guru" not in catalog

    def test_empty_catalog(self, manager, mock_conn):
        mock_conn.query.return_value = MockQueryResult([])
        catalog = manager.query_agent_catalog()
        assert catalog == ""

    def test_long_descriptions_truncated(self, manager, mock_conn):
        long_desc = "A" * 200
        agents = [
            {"id": "verbose-agent", "name": "verbose-agent", "tier": "expert",
             "category": "test", "role": "executor",
             "description": long_desc},
        ]
        mock_conn.query.return_value = MockQueryResult(
            self._mock_agent_nodes(agents)
        )

        catalog = manager.query_agent_catalog()
        assert "..." in catalog
        # Should be truncated to ~120 chars
        assert long_desc not in catalog
