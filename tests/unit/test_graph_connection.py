"""Unit tests for core/graph/connection.py — mock-based, no Docker."""
import pytest
from unittest.mock import patch, MagicMock
from core.graph.connection import GraphConnection


class TestGraphConnectionGet:

    def setup_method(self):
        GraphConnection.reset()

    def teardown_method(self):
        GraphConnection.reset()

    @patch.dict("os.environ", {"ATOMIC_GRAPH_ENABLED": "false"})
    def test_returns_none_when_disabled(self):
        result = GraphConnection.get()
        assert result is None

    @patch.dict("os.environ", {"ATOMIC_GRAPH_ENABLED": "true"})
    @patch("core.graph.connection.HAS_FALKORDB", False)
    def test_returns_none_without_package(self):
        result = GraphConnection.get()
        assert result is None

    @patch.dict("os.environ", {"ATOMIC_GRAPH_ENABLED": "true"})
    @patch("core.graph.connection.HAS_FALKORDB", True)
    @patch("core.graph.connection.FalkorDB")
    def test_successful_connection(self, mock_falkor_cls):
        mock_client = MagicMock()
        mock_client.connection.ping.return_value = True
        mock_falkor_cls.return_value = mock_client

        result = GraphConnection.get()
        assert result is not None
        assert result.connected is True

    @patch.dict("os.environ", {"ATOMIC_GRAPH_ENABLED": "true"})
    @patch("core.graph.connection.HAS_FALKORDB", True)
    @patch("core.graph.connection.FalkorDB")
    def test_connection_failure_returns_none(self, mock_falkor_cls):
        mock_falkor_cls.side_effect = Exception("Connection refused")

        result = GraphConnection.get()
        assert result is None

    @patch.dict("os.environ", {
        "ATOMIC_GRAPH_ENABLED": "true",
        "ATOMIC_GRAPH_HOST": "myhost",
        "ATOMIC_GRAPH_PORT": "7777",
        "ATOMIC_GRAPH_NAME": "my-graph",
    })
    @patch("core.graph.connection.HAS_FALKORDB", True)
    @patch("core.graph.connection.FalkorDB")
    def test_reads_env_vars(self, mock_falkor_cls):
        mock_client = MagicMock()
        mock_client.connection.ping.return_value = True
        mock_falkor_cls.return_value = mock_client

        result = GraphConnection.get()
        mock_falkor_cls.assert_called_with(host="myhost", port=7777)
        assert result.graph_name == "my-graph"


class TestGraphConnectionSingleton:

    def setup_method(self):
        GraphConnection.reset()

    def teardown_method(self):
        GraphConnection.reset()

    @patch.dict("os.environ", {"ATOMIC_GRAPH_ENABLED": "true"})
    @patch("core.graph.connection.HAS_FALKORDB", True)
    @patch("core.graph.connection.FalkorDB")
    def test_returns_same_instance(self, mock_falkor_cls):
        mock_client = MagicMock()
        mock_client.connection.ping.return_value = True
        mock_falkor_cls.return_value = mock_client

        conn1 = GraphConnection.get()
        conn2 = GraphConnection.get()
        assert conn1 is conn2

    def test_reset_clears_instance(self):
        GraphConnection._instance = MagicMock()
        GraphConnection.reset()
        assert GraphConnection._instance is None
