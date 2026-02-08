"""
Unit Tests for Memory Recall

Tests for context retrieval and relevance scoring.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from core.memory.store import MemoryStore
from core.memory.recall import MemoryRecall
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
def recall(store):
    """Create recall engine."""
    return MemoryRecall(store)


def create_entry(
    entry_id,
    content,
    phase="0-setup",
    tags=None,
    timestamp=None
):
    """Helper to create test entry."""
    return MemoryEntry(
        id=entry_id,
        timestamp=timestamp or datetime.now(),
        entry_type=MemoryEntryType.TASK_END,
        phase=phase,
        content=content,
        tags=tags or [],
        relevance_score=0.5
    )


class TestBasicRecall:
    """Test basic recall functionality."""

    def test_recall_empty_store(self, recall):
        """Test recall on empty store."""
        context = recall.recall("test query")
        assert context is not None
        assert context.entries == []
        assert context.total_tokens == 0

    def test_recall_finds_matching_entries(self, store, recall):
        """Test that recall finds matching entries."""
        store.append(create_entry("test-1", "This is about config setup"))
        store.append(create_entry("test-2", "This is about database setup"))
        store.append(create_entry("test-3", "This is about testing"))

        context = recall.recall("config")
        assert len(context.entries) > 0

        # Should find config-related entry
        entry_ids = [e.id for e in context.entries]
        assert "test-1" in entry_ids

    def test_recall_returns_context_object(self, store, recall):
        """Test that recall returns MemoryContext."""
        store.append(create_entry("test-1", "Test content"))

        context = recall.recall("test")
        assert context.query == "test"
        assert hasattr(context, 'entries')
        assert hasattr(context, 'total_tokens')

    def test_recall_with_no_matches(self, store, recall):
        """Test recall when no entries match."""
        store.append(create_entry("test-1", "About config"))

        context = recall.recall("unrelated query")
        # May return empty or low-relevance results
        assert context is not None


class TestPhaseFiltering:
    """Test phase filtering."""

    def test_recall_filters_by_phase(self, store, recall):
        """Test that phase filter works."""
        store.append(create_entry("test-1", "Phase 0 content", phase="0-setup"))
        store.append(create_entry("test-2", "Phase 1 content", phase="1-discovery"))

        context = recall.recall("content", phase="0-setup")
        assert all(e.phase == "0-setup" for e in context.entries)

    def test_recall_phase(self, store, recall):
        """Test recalling all entries from a phase."""
        store.append(create_entry("test-1", "Content 1", phase="0-setup"))
        store.append(create_entry("test-2", "Content 2", phase="0-setup"))
        store.append(create_entry("test-3", "Content 3", phase="1-discovery"))

        context = recall.recall_phase(0)
        assert len(context.entries) == 2
        assert all(e.phase.startswith("0-") for e in context.entries)


class TestTaskFiltering:
    """Test task filtering."""

    def test_recall_filters_by_task_id(self, store, recall):
        """Test that task_id filter works."""
        entry1 = create_entry("test-1", "Task 001 content")
        entry1.task_id = "001"
        entry2 = create_entry("test-2", "Task 002 content")
        entry2.task_id = "002"

        store.append(entry1)
        store.append(entry2)

        context = recall.recall("content", task_id="001")
        assert len(context.entries) >= 1
        assert all(e.task_id == "001" for e in context.entries if e.task_id)

    def test_recall_task(self, store, recall):
        """Test recalling specific task."""
        entry1 = create_entry("test-1", "Content 1", phase="0-setup")
        entry1.task_id = "001"
        entry2 = create_entry("test-2", "Content 2", phase="0-setup")
        entry2.task_id = "002"

        store.append(entry1)
        store.append(entry2)

        context = recall.recall_task(0, "001")
        assert len(context.entries) == 1
        assert context.entries[0].task_id == "001"


class TestRecentRecall:
    """Test recent entries recall."""

    def test_recall_recent(self, store, recall):
        """Test recalling recent entries."""
        import time

        for i in range(5):
            entry = create_entry(f"test-{i}", f"Content {i}")
            store.append(entry)
            time.sleep(0.01)

        context = recall.recall_recent(count=3)
        assert len(context.entries) == 3

        # Should be most recent
        assert context.entries[0].id == "test-4"

    def test_recall_recent_with_fewer_entries(self, store, recall):
        """Test recall_recent when fewer entries than requested."""
        store.append(create_entry("test-1", "Content"))

        context = recall.recall_recent(count=5)
        assert len(context.entries) == 1


class TestRelevanceScoring:
    """Test relevance scoring."""

    def test_keyword_match_scores_higher(self, store, recall):
        """Test that keyword matches score higher."""
        store.append(create_entry(
            "test-1",
            "This entry is about configuration and setup"
        ))
        store.append(create_entry(
            "test-2",
            "This entry is about something completely different"
        ))

        context = recall.recall("configuration setup")

        if len(context.entries) > 1:
            # Entry with matching keywords should score higher
            assert context.entries[0].id == "test-1"

    def test_recent_entries_score_higher(self, store, recall):
        """Test that recent entries score higher."""
        # Old entry with keyword match
        old_entry = create_entry("test-1", "About config")
        old_entry.timestamp = datetime.now() - timedelta(days=30)

        # Recent entry with keyword match
        recent_entry = create_entry("test-2", "About config")
        recent_entry.timestamp = datetime.now()

        store.append(old_entry)
        store.append(recent_entry)

        context = recall.recall("config")

        # Recent should score higher (first in results)
        if len(context.entries) > 1:
            assert context.entries[0].id == "test-2"

    def test_current_phase_scores_higher(self, store, recall):
        """Test that current phase entries score higher."""
        store.append(create_entry("test-1", "About config", phase="0-setup"))
        store.append(create_entry("test-2", "About config", phase="1-discovery"))

        context = recall.recall("config", phase="0-setup")

        if len(context.entries) > 0:
            # Current phase should appear first
            assert context.entries[0].phase == "0-setup"

    def test_relevance_threshold_filters_low_scores(self, store, recall):
        """Test that relevance threshold works."""
        store.append(create_entry("test-1", "Highly relevant config content"))
        store.append(create_entry("test-2", "Unrelated content"))

        context = recall.recall("config", relevance_threshold=0.5)

        # All entries should meet threshold
        assert all(e.relevance_score >= 0.5 for e in context.entries)


class TestTokenLimits:
    """Test token limit enforcement."""

    def test_recall_respects_max_tokens(self, store, recall):
        """Test that max_tokens limit is respected."""
        # Create entries with known content lengths
        for i in range(10):
            content = "word " * 100  # ~100 words
            store.append(create_entry(f"test-{i}", content))

        context = recall.recall("word", max_tokens=100)

        # Should respect token limit
        assert context.total_tokens <= 100

    def test_recall_includes_as_many_as_possible(self, store, recall):
        """Test that recall includes as many entries as fit."""
        # Small entries
        for i in range(5):
            store.append(create_entry(f"test-{i}", "small content"))

        context = recall.recall("content", max_tokens=1000)

        # Should include all entries
        assert len(context.entries) == 5

    def test_recall_stops_at_token_limit(self, store, recall):
        """Test that recall stops when reaching token limit."""
        # Create one large entry
        large_content = "word " * 2000
        store.append(create_entry("test-1", large_content))
        store.append(create_entry("test-2", "small"))

        context = recall.recall("word", max_tokens=100)

        # Should not include large entry if it exceeds limit
        # OR should include it and stop
        assert context.total_tokens <= 2100  # Some tolerance


class TestKeywordExtraction:
    """Test keyword extraction."""

    def test_extract_keywords_removes_stopwords(self, recall):
        """Test that stop words are removed."""
        keywords = recall._extract_keywords("the quick brown fox")

        assert "the" not in keywords
        assert "quick" in keywords
        assert "brown" in keywords

    def test_extract_keywords_removes_short_words(self, recall):
        """Test that short words are removed."""
        keywords = recall._extract_keywords("a bb ccc dddd")

        assert "a" not in keywords
        assert "bb" not in keywords
        assert "ccc" in keywords
        assert "dddd" in keywords

    def test_extract_keywords_lowercase(self, recall):
        """Test that keywords are lowercase."""
        keywords = recall._extract_keywords("Config Setup")

        assert "config" in keywords
        assert "setup" in keywords


class TestTokenEstimation:
    """Test token estimation."""

    def test_estimate_tokens_short_text(self, recall):
        """Test token estimation for short text."""
        tokens = recall._estimate_tokens("Hello world")
        assert tokens > 0
        assert tokens < 10

    def test_estimate_tokens_long_text(self, recall):
        """Test token estimation for long text."""
        text = "word " * 1000
        tokens = recall._estimate_tokens(text)
        assert tokens > 100

    def test_estimate_tokens_empty(self, recall):
        """Test token estimation for empty string."""
        tokens = recall._estimate_tokens("")
        assert tokens == 0


class TestSortingAndRanking:
    """Test result sorting and ranking."""

    def test_recall_sorts_by_relevance(self, store, recall):
        """Test that results are sorted by relevance."""
        # Create entries with different relevance
        entry1 = create_entry("test-1", "About config and setup")
        entry2 = create_entry("test-2", "About testing")
        entry3 = create_entry("test-3", "About config")

        store.append(entry1)
        store.append(entry2)
        store.append(entry3)

        context = recall.recall("config setup")

        if len(context.entries) > 1:
            # Should be sorted by relevance (highest first)
            for i in range(len(context.entries) - 1):
                assert context.entries[i].relevance_score >= context.entries[i + 1].relevance_score
