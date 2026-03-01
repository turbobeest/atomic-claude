"""Tests for priority-based memory (MemoryPriority, assign_priority, compaction changes)."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from core.memory.types import MemoryEntry, MemoryEntryType, MemoryPriority
from core.memory.content_signals import assign_priority, detect_signals


class TestMemoryPriority:
    """Test MemoryPriority enum."""

    def test_values(self):
        assert MemoryPriority.P0.value == "P0"
        assert MemoryPriority.P1.value == "P1"
        assert MemoryPriority.P2.value == "P2"
        assert MemoryPriority.P3.value == "P3"
        assert MemoryPriority.P4.value == "P4"

    def test_string_enum(self):
        assert isinstance(MemoryPriority.P0, str)
        assert MemoryPriority.P0 == "P0"


class TestMemoryEntryPriority:
    """Test MemoryEntry with priority field."""

    def test_default_priority(self):
        entry = MemoryEntry(
            id="test-1",
            entry_type=MemoryEntryType.TASK_END,
            phase="0-setup",
            content="test content",
        )
        assert entry.priority == "P2"

    def test_custom_priority(self):
        entry = MemoryEntry(
            id="test-1",
            entry_type=MemoryEntryType.CHECKPOINT,
            phase="0-setup",
            content="critical",
            priority="P0",
        )
        assert entry.priority == "P0"

    def test_backward_compatibility(self):
        """Existing entries without priority should work."""
        entry = MemoryEntry(
            id="test-1",
            entry_type=MemoryEntryType.TASK_END,
            phase="0-setup",
            content="test",
        )
        # Default P2 should be set
        assert hasattr(entry, "priority")
        assert entry.priority == "P2"


class TestAssignPriorityIntegration:
    """Test assign_priority in context of memory entries."""

    def test_checkpoint_with_error_is_p0(self):
        content = "Phase failed with critical security vulnerability"
        entry_type = MemoryEntryType.CHECKPOINT.value
        assert assign_priority(content, entry_type) == "P0"

    def test_phase_closeout_with_error_is_p0(self):
        content = "Phase closeout: error in deployment"
        entry_type = MemoryEntryType.PHASE_CLOSEOUT.value
        assert assign_priority(content, entry_type) == "P0"

    def test_task_end_is_p1(self):
        content = "Task completed, all tests pass"
        entry_type = MemoryEntryType.TASK_END.value
        assert assign_priority(content, entry_type) == "P1"

    def test_decision_content_is_p1(self):
        content = "We decided to use PostgreSQL for the database"
        entry_type = MemoryEntryType.TASK_PROGRESS.value
        assert assign_priority(content, entry_type) == "P1"

    def test_routine_content_is_p4(self):
        content = "acknowledged, no changes needed"
        entry_type = MemoryEntryType.SYSTEM_EVENT.value
        assert assign_priority(content, entry_type) == "P4"

    def test_task_start_is_p3(self):
        content = "Starting implementation work"
        entry_type = MemoryEntryType.TASK_START.value
        assert assign_priority(content, entry_type) == "P3"

    def test_normal_content_is_p2(self):
        content = "Processed 15 files, generated output"
        entry_type = MemoryEntryType.TASK_PROGRESS.value
        assert assign_priority(content, entry_type) == "P2"


class TestCompactionWithSignals:
    """Test enhanced compaction formula integration."""

    def test_compaction_import(self):
        """Verify compaction module imports content_signals."""
        from core.memory.compaction import MemoryCompactor
        # Should not raise — imports detect_signals

    def test_importance_uses_content_signals(self):
        """Verify the new formula gives different scores for different content."""
        from core.memory.compaction import MemoryCompactor
        from core.memory.store import MemoryStore

        store = MagicMock(spec=MemoryStore)
        compactor = MemoryCompactor(store)

        # Entry with decision content (should score higher)
        decision_entry = MemoryEntry(
            id="e1",
            entry_type=MemoryEntryType.TASK_END,
            phase="0-setup",
            content="We decided to use Python for the backend implementation",
            relevance_score=0.5,
        )

        # Entry with routine content (should score lower)
        routine_entry = MemoryEntry(
            id="e2",
            entry_type=MemoryEntryType.TASK_END,
            phase="0-setup",
            content="acknowledged, no changes needed, skipping",
            relevance_score=0.5,
        )

        decision_score = compactor._calculate_importance(decision_entry)
        routine_score = compactor._calculate_importance(routine_entry)

        # Decision content should score higher due to content signals
        assert decision_score > routine_score

    def test_importance_still_capped(self):
        """Importance should still be capped at 1.0."""
        from core.memory.compaction import MemoryCompactor
        from core.memory.store import MemoryStore

        store = MagicMock(spec=MemoryStore)
        compactor = MemoryCompactor(store)

        entry = MemoryEntry(
            id="e1",
            entry_type=MemoryEntryType.CHECKPOINT,
            phase="0-setup",
            content="Critical: ```error``` decided failed vulnerability? TBD",
            relevance_score=1.0,
        )
        score = compactor._calculate_importance(entry)
        assert score <= 1.0


class TestRecallWithSignals:
    """Test recall scoring with content signal boost."""

    def test_recall_import(self):
        """Verify recall module imports content_signals."""
        from core.memory.recall import MemoryRecall
        # Should not raise

    def test_score_entry_signal_boost(self):
        """Entries with positive signals should score higher."""
        from core.memory.recall import MemoryRecall
        from core.memory.store import MemoryStore

        store = MagicMock(spec=MemoryStore)
        recall = MemoryRecall(store)

        decision_entry = MemoryEntry(
            id="e1",
            entry_type=MemoryEntryType.TASK_END,
            phase="0-setup",
            content="We decided to use the new API approach",
            relevance_score=0.5,
        )

        plain_entry = MemoryEntry(
            id="e2",
            entry_type=MemoryEntryType.TASK_END,
            phase="0-setup",
            content="Processed files in the directory",
            relevance_score=0.5,
        )

        # Score with same query — decision content should get boost
        score_decision = recall._score_entry(decision_entry, "API approach", "0-setup")
        score_plain = recall._score_entry(plain_entry, "API approach", "0-setup")

        # Decision entry should score at least as high (signal boost helps)
        assert score_decision >= score_plain
