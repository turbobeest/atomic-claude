"""Unit tests for GraphManager memory operations and dual-write integration."""
import pytest
from datetime import datetime
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


# ============================================================================
# GraphManager.save_memory()
# ============================================================================

class TestSaveMemory:

    def test_save_memory_creates_node(self, manager, mock_conn):
        manager.save_memory(
            entry_id="mem-001",
            phase="1-discovery",
            content="Found 3 source documents",
            entry_type="task_end",
            task_id="101",
            tags=["finding", "phase-1"],
        )
        mock_conn.query.assert_called_once()
        cypher = mock_conn.query.call_args[0][0]
        assert "CREATE" in cypher
        assert ":Memory" in cypher

    def test_save_memory_stores_tags_as_csv(self, manager, mock_conn):
        manager.save_memory(
            entry_id="mem-002",
            phase="0-setup",
            content="Config set",
            tags=["config", "setup"],
        )
        params = mock_conn.query.call_args[0][1]
        param_values = list(params.values())
        assert "config,setup" in param_values

    def test_save_memory_empty_tags(self, manager, mock_conn):
        manager.save_memory(
            entry_id="mem-003",
            phase="0-setup",
            content="No tags",
        )
        params = mock_conn.query.call_args[0][1]
        param_values = list(params.values())
        assert "" in param_values  # tags_csv should be empty string

    def test_save_memory_defaults(self, manager, mock_conn):
        manager.save_memory(
            entry_id="mem-004",
            phase="2-prd",
            content="Default test",
        )
        params = mock_conn.query.call_args[0][1]
        param_values = list(params.values())
        assert "task_end" in param_values  # default entry_type
        assert 0.8 in param_values  # default relevance_score


# ============================================================================
# GraphManager.recall_memory()
# ============================================================================

class TestRecallMemory:

    def _mock_memory_nodes(self, memories):
        """Create mock FalkorDB node results."""
        rows = []
        for m in memories:
            node = MagicMock()
            node.properties = m
            rows.append([node])
        return rows

    def test_recall_memory_uses_fulltext(self, manager, mock_conn):
        memories = [
            {"id": "mem-001", "phase": "1-discovery", "task_id": "101",
             "entry_type": "task_end", "content": "Found 3 documents",
             "tags_csv": "finding", "relevance_score": 0.9,
             "created_at": "2026-02-22T10:00:00"},
        ]
        mock_conn.query.return_value = MockQueryResult(
            self._mock_memory_nodes(memories)
        )

        results = manager.recall_memory("documents")
        assert len(results) == 1
        assert results[0].get("content") == "Found 3 documents"

    def test_recall_with_phase_filter(self, manager, mock_conn):
        memories = [
            {"id": "m1", "phase": "1-discovery", "task_id": "",
             "entry_type": "task_end", "content": "Phase 1 result",
             "tags_csv": "", "relevance_score": 0.8,
             "created_at": "2026-02-22T10:00:00"},
            {"id": "m2", "phase": "2-prd", "task_id": "",
             "entry_type": "task_end", "content": "Phase 2 result",
             "tags_csv": "", "relevance_score": 0.8,
             "created_at": "2026-02-22T11:00:00"},
        ]
        mock_conn.query.return_value = MockQueryResult(
            self._mock_memory_nodes(memories)
        )

        results = manager.recall_memory("result", phase="1-discovery")
        assert all(r.get("phase") == "1-discovery" for r in results)

    def test_recall_falls_back_to_property_query(self, manager, mock_conn):
        """When fulltext returns nothing, falls back to get_nodes."""
        # First call (fulltext) returns empty, second (get_nodes) returns data
        memories = [
            {"id": "m1", "phase": "1-discovery", "task_id": "",
             "entry_type": "task_end", "content": "Result",
             "tags_csv": "", "relevance_score": 0.8,
             "created_at": "2026-02-22T10:00:00"},
        ]
        mock_conn.query.side_effect = [
            MockQueryResult([]),  # fulltext empty
            MockQueryResult(self._mock_memory_nodes(memories)),  # get_nodes
        ]

        results = manager.recall_memory("result")
        assert len(results) == 1


# ============================================================================
# GraphManager.save_checkpoint()
# ============================================================================

class TestSaveCheckpoint:

    def test_save_checkpoint_creates_node(self, manager, mock_conn):
        manager.save_checkpoint(
            checkpoint_id="phase1-20260222-120000",
            phase=1,
            phase_name="discovery",
            summary="Phase 1 complete with 12 findings",
            key_decisions=["Use FalkorDB", "Claude Code provider"],
            artifacts=[".outputs/1-discovery/findings.json"],
        )
        mock_conn.query.assert_called_once()
        cypher = mock_conn.query.call_args[0][0]
        assert "CREATE" in cypher
        assert ":PhaseCheckpoint" in cypher

    def test_save_checkpoint_stores_lists_as_csv(self, manager, mock_conn):
        manager.save_checkpoint(
            checkpoint_id="cp-1",
            phase=0,
            phase_name="setup",
            summary="Done",
            key_decisions=["decision-1", "decision-2"],
        )
        params = mock_conn.query.call_args[0][1]
        param_values = list(params.values())
        assert "decision-1,decision-2" in param_values


# ============================================================================
# GraphManager.invalidate_checkpoints_after()
# ============================================================================

class TestInvalidateCheckpoints:

    def test_invalidate_returns_count(self, manager, mock_conn):
        mock_conn.query.return_value = MockQueryResult([[3]])
        count = manager.invalidate_checkpoints_after(2)
        assert count == 3
        cypher = mock_conn.query.call_args[0][0]
        assert "SET c.status = 'invalidated'" in cypher

    def test_invalidate_zero_when_none_match(self, manager, mock_conn):
        mock_conn.query.return_value = MockQueryResult([[0]])
        count = manager.invalidate_checkpoints_after(9)
        assert count == 0


# ============================================================================
# GraphManager.clear_memory_after_phase()
# ============================================================================

class TestClearMemoryAfterPhase:

    def _mock_memory_nodes(self, memories):
        rows = []
        for m in memories:
            node = MagicMock()
            node.properties = m
            rows.append([node])
        return rows

    def test_clear_deletes_later_phases(self, manager, mock_conn):
        memories = [
            {"id": "m1", "phase": "1-discovery"},
            {"id": "m2", "phase": "2-prd"},
            {"id": "m3", "phase": "3-design"},
        ]
        # First call: get_nodes returns all memories
        mock_conn.query.side_effect = [
            MockQueryResult(self._mock_memory_nodes(memories)),
            MockQueryResult(),  # delete m2
            MockQueryResult(),  # delete m3
        ]

        count = manager.clear_memory_after_phase(1)
        assert count == 2  # phases 2 and 3 cleared

    def test_clear_nothing_when_all_before(self, manager, mock_conn):
        memories = [
            {"id": "m1", "phase": "0-setup"},
            {"id": "m2", "phase": "1-discovery"},
        ]
        mock_conn.query.return_value = MockQueryResult(
            self._mock_memory_nodes(memories)
        )

        count = manager.clear_memory_after_phase(5)
        assert count == 0


# ============================================================================
# Dual-write integration (MemoryStore + graph)
# ============================================================================

class TestDualWrite:

    def test_store_append_writes_to_graph(self, tmp_path, manager):
        """MemoryStore.append() should call graph.save_memory()."""
        from core.memory.store import MemoryStore
        from core.memory.types import MemoryEntry, MemoryEntryType

        store = MemoryStore(tmp_path, graph=manager)
        store.initialize()

        entry = MemoryEntry(
            id="test-001",
            entry_type=MemoryEntryType.TASK_END,
            phase="1-discovery",
            task_id="101",
            content="Test finding",
            tags=["test"],
            relevance_score=0.9,
        )

        # Patch save_memory to track calls
        manager.save_memory = MagicMock()
        store.append(entry)

        manager.save_memory.assert_called_once()
        call_kwargs = manager.save_memory.call_args
        assert call_kwargs[1]["entry_id"] == "test-001" or call_kwargs[0][0] == "test-001"

    def test_store_append_survives_graph_failure(self, tmp_path):
        """Graph failure should not prevent file-based save."""
        from core.memory.store import MemoryStore
        from core.memory.types import MemoryEntry, MemoryEntryType

        broken_graph = MagicMock()
        broken_graph.save_memory.side_effect = Exception("Connection refused")

        store = MemoryStore(tmp_path, graph=broken_graph)
        store.initialize()

        entry = MemoryEntry(
            id="test-002",
            entry_type=MemoryEntryType.TASK_END,
            phase="0-setup",
            content="Should still save to file",
        )

        # Should not raise
        store.append(entry)

        # File should still have the entry
        assert len(store._entries) == 1
        assert store._entries[0].id == "test-002"


# ============================================================================
# Recall with graph (MemoryRecall + graph)
# ============================================================================

class TestRecallWithGraph:

    def test_recall_prefers_graph(self, tmp_path, manager, mock_conn):
        """MemoryRecall should use graph fulltext search when available."""
        from core.memory.store import MemoryStore
        from core.memory.recall import MemoryRecall

        store = MemoryStore(tmp_path)
        store.initialize()

        recall = MemoryRecall(store, graph=manager)

        # Mock recall_memory to return results
        manager.recall_memory = MagicMock(return_value=[
            {"id": "m1", "phase": "1-discovery", "task_id": "101",
             "entry_type": "task_end", "content": "Found documents",
             "tags_csv": "finding", "relevance_score": 0.9,
             "created_at": "2026-02-22T10:00:00"},
        ])

        context = recall.recall("documents")
        manager.recall_memory.assert_called_once()
        assert len(context.entries) == 1
        assert "documents" in context.entries[0].content

    def test_recall_falls_back_on_graph_failure(self, tmp_path):
        """If graph recall fails, falls back to file-based."""
        from core.memory.store import MemoryStore
        from core.memory.recall import MemoryRecall
        from core.memory.types import MemoryEntry, MemoryEntryType

        store = MemoryStore(tmp_path)
        store.initialize()

        # Add an entry to the file store
        entry = MemoryEntry(
            id="file-001",
            entry_type=MemoryEntryType.TASK_END,
            phase="1-discovery",
            content="File-based finding about documents",
            tags=["documents"],
            relevance_score=0.9,
        )
        store.append(entry)

        broken_graph = MagicMock()
        broken_graph.recall_memory.side_effect = Exception("Graph down")

        recall = MemoryRecall(store, graph=broken_graph)
        context = recall.recall("documents")

        # Should still return the file-based entry
        assert len(context.entries) >= 1
