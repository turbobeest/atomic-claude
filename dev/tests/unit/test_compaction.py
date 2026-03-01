"""
Unit Tests for Memory Compaction

Tests for memory optimization and compaction.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone

from core.memory.store import MemoryStore
from core.memory.compaction import MemoryCompactor
from core.memory.types import MemoryEntry, MemoryEntryType


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    temp = Path(tempfile.mkdtemp())
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def store(temp_dir):
    """Create memory store."""
    store = MemoryStore(temp_dir)
    store.initialize()
    return store


@pytest.fixture
def compactor(store):
    """Create compactor."""
    return MemoryCompactor(store)


def create_entry(
    entry_id,
    content,
    timestamp=None,
    relevance=0.5,
    entry_type=MemoryEntryType.TASK_END
):
    """Helper to create test entry."""
    return MemoryEntry(
        id=entry_id,
        timestamp=timestamp or datetime.now(timezone.utc),
        entry_type=entry_type,
        phase="0-setup",
        content=content,
        tags=[],
        relevance_score=relevance
    )


class TestBasicCompaction:
    """Test basic compaction functionality."""

    def test_compact_returns_stats(self, compactor):
        """Test that compact returns statistics."""
        result = compactor.compact()

        assert "initial_size_mb" in result
        assert "final_size_mb" in result
        assert "total_removed" in result

    def test_compact_removes_old_entries(self, store, compactor):
        """Test that old entries are removed."""
        # Add old entry
        old_entry = create_entry(
            "test-1",
            "Old content",
            timestamp=datetime.now(timezone.utc) - timedelta(days=100),
            relevance=0.1
        )
        store.append(old_entry)

        # Add recent entry
        recent_entry = create_entry("test-2", "Recent content")
        store.append(recent_entry)

        result = compactor.compact(max_age_days=90, min_relevance=0.2)

        assert result["total_removed"] >= 1
        assert store.get("test-1") is None
        assert store.get("test-2") is not None

    def test_compact_keeps_important_entries(self, store, compactor):
        """Test that important entries are kept."""
        # Old but important
        important_entry = create_entry(
            "test-1",
            "Important content",
            timestamp=datetime.now(timezone.utc) - timedelta(days=100),
            relevance=0.9
        )
        store.append(important_entry)

        result = compactor.compact(max_age_days=90, min_relevance=0.2)

        assert store.get("test-1") is not None

    def test_compact_keeps_checkpoints(self, store, compactor):
        """Test that checkpoints are always kept."""
        checkpoint = create_entry(
            "test-1",
            "Checkpoint",
            timestamp=datetime.now(timezone.utc) - timedelta(days=100),
            relevance=0.1,
            entry_type=MemoryEntryType.CHECKPOINT
        )
        store.append(checkpoint)

        result = compactor.compact(max_age_days=90, min_relevance=0.2)

        assert store.get("test-1") is not None


class TestFindRedundant:
    """Test redundancy detection."""

    def test_find_redundant_empty_store(self, compactor):
        """Test finding redundant in empty store."""
        redundant = compactor.find_redundant()
        assert redundant == set()

    def test_find_redundant_identical_entries(self, store, compactor):
        """Test that identical entries are found."""
        # Add two nearly identical entries
        entry1 = create_entry("test-1", "This is test content")
        entry1.timestamp = datetime.now(timezone.utc) - timedelta(hours=1)

        entry2 = create_entry("test-2", "This is test content")
        entry2.timestamp = datetime.now(timezone.utc)

        store.append(entry1)
        store.append(entry2)

        redundant = compactor.find_redundant(similarity_threshold=0.9)

        # Should find one redundant (the older one)
        assert len(redundant) >= 1
        if "test-1" in redundant:
            assert "test-2" not in redundant

    def test_find_redundant_different_entries(self, store, compactor):
        """Test that different entries are not flagged."""
        entry1 = create_entry("test-1", "Content about setup")
        entry2 = create_entry("test-2", "Content about testing")

        store.append(entry1)
        store.append(entry2)

        redundant = compactor.find_redundant(similarity_threshold=0.8)

        # Should not flag as redundant
        assert len(redundant) == 0

    def test_find_redundant_similar_entries(self, store, compactor):
        """Test that similar entries are found."""
        entry1 = create_entry("test-1", "Configuration setup for the project")
        entry1.timestamp = datetime.now(timezone.utc) - timedelta(hours=1)

        entry2 = create_entry("test-2", "Configuration setup for project")
        entry2.timestamp = datetime.now(timezone.utc)

        store.append(entry1)
        store.append(entry2)

        redundant = compactor.find_redundant(similarity_threshold=0.7)

        # Should find similarity
        assert len(redundant) >= 1


class TestMergeEntries:
    """Test entry merging."""

    def test_merge_entries_combines_content(self, store, compactor):
        """Test that merging combines content."""
        entry1 = create_entry("test-1", "Part one")
        entry2 = create_entry("test-2", "Part two")

        store.append(entry1)
        store.append(entry2)

        merged_id = compactor.merge_entries(["test-1", "test-2"])

        merged = store.get(merged_id)
        assert merged is not None
        assert "Part one" in merged.content
        assert "Part two" in merged.content

    def test_merge_entries_combines_tags(self, store, compactor):
        """Test that merging combines tags."""
        entry1 = create_entry("test-1", "Content")
        entry1.tags = ["tag1", "tag2"]

        entry2 = create_entry("test-2", "Content")
        entry2.tags = ["tag2", "tag3"]

        store.append(entry1)
        store.append(entry2)

        merged_id = compactor.merge_entries(["test-1", "test-2"])

        merged = store.get(merged_id)
        assert "tag1" in merged.tags
        assert "tag2" in merged.tags
        assert "tag3" in merged.tags

    def test_merge_entries_with_empty_list(self, compactor):
        """Test merging empty list raises error."""
        with pytest.raises(ValueError):
            compactor.merge_entries([])

    def test_merge_entries_with_nonexistent(self, compactor):
        """Test merging non-existent entries raises error."""
        with pytest.raises(ValueError):
            compactor.merge_entries(["nonexistent"])


class TestPrioritize:
    """Test entry prioritization."""

    def test_prioritize_returns_scored_list(self, store, compactor):
        """Test that prioritize returns scored list."""
        store.append(create_entry("test-1", "Content"))

        priorities = compactor.prioritize()

        assert len(priorities) > 0
        assert isinstance(priorities[0], tuple)
        assert len(priorities[0]) == 2  # (entry_id, score)

    def test_prioritize_checkpoints_score_higher(self, store, compactor):
        """Test that checkpoints score higher."""
        checkpoint = create_entry(
            "test-1",
            "Checkpoint",
            entry_type=MemoryEntryType.CHECKPOINT
        )
        regular = create_entry(
            "test-2",
            "Regular entry",
            entry_type=MemoryEntryType.TASK_END
        )

        store.append(checkpoint)
        store.append(regular)

        priorities = compactor.prioritize()

        # Find scores
        checkpoint_score = next(s for eid, s in priorities if eid == "test-1")
        regular_score = next(s for eid, s in priorities if eid == "test-2")

        assert checkpoint_score > regular_score

    def test_prioritize_recent_scores_higher(self, store, compactor):
        """Test that recent entries score higher."""
        old_entry = create_entry(
            "test-1",
            "Old content",
            timestamp=datetime.now(timezone.utc) - timedelta(days=100)
        )
        recent_entry = create_entry(
            "test-2",
            "Recent content",
            timestamp=datetime.now(timezone.utc)
        )

        store.append(old_entry)
        store.append(recent_entry)

        priorities = compactor.prioritize()

        old_score = next(s for eid, s in priorities if eid == "test-1")
        recent_score = next(s for eid, s in priorities if eid == "test-2")

        assert recent_score > old_score

    def test_prioritize_sorted_descending(self, store, compactor):
        """Test that priorities are sorted descending."""
        for i in range(5):
            store.append(create_entry(f"test-{i}", f"Content {i}"))

        priorities = compactor.prioritize()

        # Should be sorted by score (descending)
        for i in range(len(priorities) - 1):
            assert priorities[i][1] >= priorities[i + 1][1]


class TestRemoveLowValue:
    """Test removing low-value entries."""

    def test_remove_low_value_entries(self, store, compactor):
        """Test that low-value entries are removed."""
        # Low value entry
        low_value = create_entry(
            "test-1",
            "x",  # Short content
            timestamp=datetime.now(timezone.utc) - timedelta(days=100),
            relevance=0.1,
            entry_type=MemoryEntryType.TASK_START
        )

        # High value entry
        high_value = create_entry(
            "test-2",
            "Important detailed content",
            timestamp=datetime.now(timezone.utc),
            relevance=0.9,
            entry_type=MemoryEntryType.CHECKPOINT
        )

        store.append(low_value)
        store.append(high_value)

        removed = compactor.remove_low_value(threshold=0.3)

        assert removed >= 1
        assert store.get("test-2") is not None

    def test_remove_low_value_keeps_checkpoints(self, store, compactor):
        """Test that checkpoints are kept even if low value."""
        checkpoint = create_entry(
            "test-1",
            "Checkpoint",
            timestamp=datetime.now(timezone.utc) - timedelta(days=100),
            relevance=0.1,
            entry_type=MemoryEntryType.CHECKPOINT
        )

        store.append(checkpoint)

        removed = compactor.remove_low_value(threshold=0.5)

        # Checkpoint should be kept
        assert store.get("test-1") is not None


class TestCalculateSimilarity:
    """Test similarity calculation."""

    def test_calculate_similarity_identical(self, compactor):
        """Test similarity of identical entries."""
        entry1 = create_entry("test-1", "This is test content")
        entry2 = create_entry("test-2", "This is test content")

        similarity = compactor._calculate_similarity(entry1, entry2)
        assert similarity == 1.0

    def test_calculate_similarity_different(self, compactor):
        """Test similarity of different entries."""
        entry1 = create_entry("test-1", "About configuration")
        entry2 = create_entry("test-2", "About testing")

        similarity = compactor._calculate_similarity(entry1, entry2)
        assert 0.0 <= similarity < 0.5

    def test_calculate_similarity_partial(self, compactor):
        """Test similarity of partially matching entries."""
        entry1 = create_entry("test-1", "Configuration setup for project")
        entry2 = create_entry("test-2", "Configuration setup for testing")

        similarity = compactor._calculate_similarity(entry1, entry2)
        assert 0.5 <= similarity <= 1.0

    def test_calculate_similarity_empty(self, compactor):
        """Test similarity of empty entries."""
        entry1 = create_entry("test-1", "")
        entry2 = create_entry("test-2", "")

        similarity = compactor._calculate_similarity(entry1, entry2)
        assert similarity == 1.0  # Both empty


class TestCalculateImportance:
    """Test importance calculation."""

    def test_calculate_importance_checkpoint(self, compactor):
        """Test that checkpoints have high importance."""
        checkpoint = create_entry(
            "test-1",
            "Checkpoint",
            entry_type=MemoryEntryType.CHECKPOINT
        )

        importance = compactor._calculate_importance(checkpoint)
        assert importance > 0.7

    def test_calculate_importance_recent(self, compactor):
        """Test that recent entries have higher importance."""
        recent = create_entry(
            "test-1",
            "Recent content",
            timestamp=datetime.now(timezone.utc)
        )

        old = create_entry(
            "test-2",
            "Old content",
            timestamp=datetime.now(timezone.utc) - timedelta(days=100)
        )

        recent_importance = compactor._calculate_importance(recent)
        old_importance = compactor._calculate_importance(old)

        assert recent_importance > old_importance

    def test_calculate_importance_long_content(self, compactor):
        """Test that longer content has higher importance."""
        short = create_entry("test-1", "Short")
        long = create_entry("test-2", "Long content " * 100)

        short_importance = compactor._calculate_importance(short)
        long_importance = compactor._calculate_importance(long)

        assert long_importance > short_importance
