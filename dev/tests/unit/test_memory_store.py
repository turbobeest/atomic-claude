"""
Unit Tests for Memory Store

Tests for persistent storage layer.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from core.memory.store import MemoryStore
from core.memory.types import MemoryEntry, MemoryEntryType


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    temp = Path(tempfile.mkdtemp())
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def store(temp_dir):
    """Create memory store instance."""
    store = MemoryStore(temp_dir)
    store.initialize()
    return store


def create_test_entry(
    entry_id="test-1",
    phase="0-setup",
    content="Test content",
    entry_type=MemoryEntryType.TASK_END
):
    """Helper to create test entry."""
    return MemoryEntry(
        id=entry_id,
        timestamp=datetime.now(),
        entry_type=entry_type,
        phase=phase,
        content=content,
        tags=["test"],
        relevance_score=0.5
    )


class TestStoreInitialization:
    """Test store initialization."""

    def test_initialize_creates_directories(self, temp_dir):
        """Test that initialize creates required directories."""
        store = MemoryStore(temp_dir)
        store.initialize()

        assert (temp_dir / "memory").exists()
        assert (temp_dir / "memory.json").exists()
        assert (temp_dir / "memory-head.json").exists()

    def test_initialize_creates_empty_memory_file(self, temp_dir):
        """Test that initialize creates empty memory.json."""
        store = MemoryStore(temp_dir)
        store.initialize()

        import json
        with open(temp_dir / "memory.json", 'r') as f:
            data = json.load(f)

        assert "entries" in data
        assert data["entries"] == []

    def test_initialize_idempotent(self, store):
        """Test that initialize can be called multiple times."""
        store.initialize()  # Call again
        store.initialize()  # And again

        # Should not raise errors


class TestAppend:
    """Test appending entries."""

    def test_append_adds_entry(self, store):
        """Test that append adds entry to store."""
        entry = create_test_entry()
        store.append(entry)

        retrieved = store.get(entry.id)
        assert retrieved is not None
        assert retrieved.id == entry.id
        assert retrieved.content == entry.content

    def test_append_persists_to_disk(self, store, temp_dir):
        """Test that append persists to disk."""
        entry = create_test_entry()
        store.append(entry)

        # Create new store instance
        new_store = MemoryStore(temp_dir)
        new_store.initialize()

        retrieved = new_store.get(entry.id)
        assert retrieved is not None
        assert retrieved.id == entry.id

    def test_append_updates_index(self, store):
        """Test that append updates the index."""
        entry = create_test_entry()
        store.append(entry)

        assert entry.id in store._index
        assert store._index[entry.id] == 0

    def test_append_multiple_entries(self, store):
        """Test appending multiple entries."""
        entries = [
            create_test_entry(f"test-{i}", content=f"Content {i}")
            for i in range(5)
        ]

        for entry in entries:
            store.append(entry)

        for i, entry in enumerate(entries):
            retrieved = store.get(entry.id)
            assert retrieved is not None
            assert retrieved.content == f"Content {i}"


class TestGet:
    """Test retrieving entries."""

    def test_get_existing_entry(self, store):
        """Test retrieving existing entry."""
        entry = create_test_entry()
        store.append(entry)

        retrieved = store.get(entry.id)
        assert retrieved is not None
        assert retrieved.id == entry.id

    def test_get_nonexistent_entry(self, store):
        """Test retrieving non-existent entry returns None."""
        retrieved = store.get("nonexistent")
        assert retrieved is None

    def test_get_empty_store(self, store):
        """Test get on empty store."""
        retrieved = store.get("test-1")
        assert retrieved is None


class TestQuery:
    """Test querying entries."""

    def test_query_all_entries(self, store):
        """Test querying all entries."""
        entries = [create_test_entry(f"test-{i}") for i in range(3)]
        for entry in entries:
            store.append(entry)

        results = store.query()
        assert len(results) == 3

    def test_query_by_phase(self, store):
        """Test filtering by phase."""
        store.append(create_test_entry("test-1", phase="0-setup"))
        store.append(create_test_entry("test-2", phase="1-discovery"))
        store.append(create_test_entry("test-3", phase="0-setup"))

        results = store.query(phase="0-setup")
        assert len(results) == 2
        assert all(e.phase == "0-setup" for e in results)

    def test_query_by_task_id(self, store):
        """Test filtering by task ID."""
        entry1 = create_test_entry("test-1")
        entry1.task_id = "001"
        entry2 = create_test_entry("test-2")
        entry2.task_id = "002"

        store.append(entry1)
        store.append(entry2)

        results = store.query(task_id="001")
        assert len(results) == 1
        assert results[0].task_id == "001"

    def test_query_by_entry_type(self, store):
        """Test filtering by entry type."""
        store.append(create_test_entry("test-1", entry_type=MemoryEntryType.TASK_START))
        store.append(create_test_entry("test-2", entry_type=MemoryEntryType.TASK_END))

        results = store.query(entry_type=MemoryEntryType.TASK_START)
        assert len(results) == 1
        assert results[0].entry_type == MemoryEntryType.TASK_START

    def test_query_by_tags(self, store):
        """Test filtering by tags."""
        entry1 = create_test_entry("test-1")
        entry1.tags = ["config", "setup"]
        entry2 = create_test_entry("test-2")
        entry2.tags = ["discovery"]

        store.append(entry1)
        store.append(entry2)

        results = store.query(tags=["config"])
        assert len(results) == 1
        assert "config" in results[0].tags

    def test_query_with_limit(self, store):
        """Test limit parameter."""
        for i in range(10):
            store.append(create_test_entry(f"test-{i}"))

        results = store.query(limit=5)
        assert len(results) == 5

    def test_query_with_min_relevance(self, store):
        """Test minimum relevance filter."""
        entry1 = create_test_entry("test-1")
        entry1.relevance_score = 0.8
        entry2 = create_test_entry("test-2")
        entry2.relevance_score = 0.2

        store.append(entry1)
        store.append(entry2)

        results = store.query(min_relevance=0.5)
        assert len(results) == 1
        assert results[0].relevance_score >= 0.5

    def test_query_sorts_by_timestamp(self, store):
        """Test that results are sorted by timestamp (newest first)."""
        # Add entries with different timestamps
        for i in range(3):
            entry = create_test_entry(f"test-{i}")
            entry.timestamp = datetime.now() - timedelta(hours=i)
            store.append(entry)

        results = store.query()
        assert len(results) == 3

        # Should be sorted newest first
        for i in range(len(results) - 1):
            assert results[i].timestamp >= results[i + 1].timestamp


class TestCompact:
    """Test memory compaction."""

    def test_compact_removes_old_entries(self, store):
        """Test that compact removes old entries."""
        # Add old entry
        old_entry = create_test_entry("test-1")
        old_entry.timestamp = datetime.now() - timedelta(days=100)
        old_entry.relevance_score = 0.1

        # Add recent entry
        recent_entry = create_test_entry("test-2")
        recent_entry.timestamp = datetime.now()

        store.append(old_entry)
        store.append(recent_entry)

        removed = store.compact(max_age_days=90, min_relevance=0.2)
        assert removed == 1

        # Old entry should be removed
        assert store.get("test-1") is None
        assert store.get("test-2") is not None

    def test_compact_keeps_high_relevance_old_entries(self, store):
        """Test that high relevance entries are kept even if old."""
        old_entry = create_test_entry("test-1")
        old_entry.timestamp = datetime.now() - timedelta(days=100)
        old_entry.relevance_score = 0.9

        store.append(old_entry)

        removed = store.compact(max_age_days=90, min_relevance=0.2)
        assert removed == 0

        # Should still be there
        assert store.get("test-1") is not None

    def test_compact_keeps_checkpoints(self, store):
        """Test that checkpoints are always kept."""
        checkpoint = create_test_entry(
            "test-1",
            entry_type=MemoryEntryType.CHECKPOINT
        )
        checkpoint.timestamp = datetime.now() - timedelta(days=100)
        checkpoint.relevance_score = 0.1

        store.append(checkpoint)

        removed = store.compact(max_age_days=90, min_relevance=0.2)
        assert removed == 0

        # Checkpoint should still be there
        assert store.get("test-1") is not None


class TestStats:
    """Test statistics generation."""

    def test_get_stats_empty_store(self, store):
        """Test stats on empty store."""
        stats = store.get_stats()

        assert stats.total_entries == 0
        assert stats.size_bytes >= 0
        assert stats.oldest_entry is None
        assert stats.newest_entry is None

    def test_get_stats_with_entries(self, store):
        """Test stats with entries."""
        for i in range(5):
            entry = create_test_entry(f"test-{i}", phase=f"{i}-phase")
            store.append(entry)

        stats = store.get_stats()

        assert stats.total_entries == 5
        assert stats.size_bytes > 0
        assert stats.size_mb >= 0  # May round to 0.0 for small files
        assert stats.oldest_entry is not None
        assert stats.newest_entry is not None

    def test_stats_entries_by_phase(self, store):
        """Test phase breakdown in stats."""
        store.append(create_test_entry("test-1", phase="0-setup"))
        store.append(create_test_entry("test-2", phase="0-setup"))
        store.append(create_test_entry("test-3", phase="1-discovery"))

        stats = store.get_stats()

        assert stats.entries_by_phase["0-setup"] == 2
        assert stats.entries_by_phase["1-discovery"] == 1

    def test_stats_entries_by_type(self, store):
        """Test type breakdown in stats."""
        store.append(create_test_entry("test-1", entry_type=MemoryEntryType.TASK_START))
        store.append(create_test_entry("test-2", entry_type=MemoryEntryType.TASK_END))
        store.append(create_test_entry("test-3", entry_type=MemoryEntryType.TASK_END))

        stats = store.get_stats()

        assert stats.entries_by_type["task_start"] == 1
        assert stats.entries_by_type["task_end"] == 2


class TestExportImport:
    """Test export and import functionality."""

    def test_export_creates_file(self, store, temp_dir):
        """Test that export creates file."""
        store.append(create_test_entry("test-1"))

        export_path = temp_dir / "export.json"
        store.export(export_path)

        assert export_path.exists()

    def test_import_adds_entries(self, store, temp_dir):
        """Test that import adds entries."""
        # Create and export
        store.append(create_test_entry("test-1"))
        export_path = temp_dir / "export.json"
        store.export(export_path)

        # Create new store and import
        new_store = MemoryStore(temp_dir / "new")
        new_store.initialize()
        imported = new_store.import_data(export_path)

        assert imported == 1
        assert new_store.get("test-1") is not None

    def test_import_skips_duplicates(self, store, temp_dir):
        """Test that import skips duplicate entries."""
        store.append(create_test_entry("test-1"))
        export_path = temp_dir / "export.json"
        store.export(export_path)

        # Import again (should skip)
        imported = store.import_data(export_path)
        assert imported == 0


class TestClearPhase:
    """Test clearing phase data."""

    def test_clear_phase_removes_entries(self, store):
        """Test that clear_phase removes entries."""
        store.append(create_test_entry("test-1", phase="0-setup"))
        store.append(create_test_entry("test-2", phase="1-discovery"))
        store.append(create_test_entry("test-3", phase="2-prd"))

        removed = store.clear_phase(1)
        assert removed == 2

        # Phase 0 should remain
        assert store.get("test-1") is not None
        # Phases 1+ should be removed
        assert store.get("test-2") is None
        assert store.get("test-3") is None
