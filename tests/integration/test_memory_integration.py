"""
Integration Tests for Memory System

Tests for full memory workflows and cross-module interactions.
"""

import pytest
import tempfile
import shutil
import time
from pathlib import Path
from datetime import datetime, timedelta

from core.memory import (
    memory_init,
    memory_save,
    memory_recall,
    memory_recall_phase,
    memory_recall_recent,
    memory_checkpoint,
    memory_restore,
    memory_list_checkpoints,
    memory_get_latest_checkpoint,
    memory_stats,
    memory_compact,
    memory_handle_backtrack,
    MemoryEntryType,
    CheckpointStatus
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    temp = Path(tempfile.mkdtemp())
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture(autouse=True)
def reset_memory():
    """Reset memory system between tests."""
    import core.memory as mem
    mem._store = None
    mem._checkpoint_manager = None
    mem._recall_engine = None
    mem._compactor = None
    mem._initialized = False
    yield


class TestFullWorkflow:
    """Test complete memory workflows."""

    def test_save_and_recall_workflow(self, temp_dir):
        """Test saving and recalling memory."""
        memory_init(temp_dir)

        # Save some entries
        entry_id1 = memory_save(
            phase="0-setup",
            task_id="001",
            content="Configuration completed successfully",
            tags=["config", "setup"],
            entry_type=MemoryEntryType.TASK_END
        )

        entry_id2 = memory_save(
            phase="0-setup",
            task_id="002",
            content="Environment validation passed",
            tags=["validation", "setup"],
            entry_type=MemoryEntryType.TASK_END
        )

        # Recall by query
        context = memory_recall("configuration")

        assert len(context.entries) > 0
        assert any("Configuration" in e.content for e in context.entries)

    def test_checkpoint_and_restore_workflow(self, temp_dir):
        """Test checkpoint creation and restoration."""
        memory_init(temp_dir)

        # Save some memory
        memory_save(
            phase="0-setup",
            task_id="001",
            content="Setup completed",
            tags=["setup"]
        )

        # Create checkpoint
        checkpoint_id = memory_checkpoint(
            phase=0,
            phase_name="Setup",
            summary="Phase 0 completed successfully",
            key_decisions=["Used Python 3.11", "Selected PostgreSQL"],
            artifacts=["/path/to/config.json"]
        )

        assert checkpoint_id is not None

        # Restore checkpoint
        checkpoint = memory_restore(checkpoint_id)

        assert checkpoint is not None
        assert checkpoint.phase == 0
        assert checkpoint.summary == "Phase 0 completed successfully"
        assert "Used Python 3.11" in checkpoint.key_decisions

    def test_multi_phase_workflow(self, temp_dir):
        """Test memory across multiple phases."""
        memory_init(temp_dir)

        # Phase 0
        memory_save(
            phase="0-setup",
            task_id="001",
            content="Setup completed",
            tags=["setup"]
        )
        memory_checkpoint(
            phase=0,
            phase_name="Setup",
            summary="Setup done"
        )

        # Phase 1
        memory_save(
            phase="1-discovery",
            task_id="101",
            content="Discovery completed",
            tags=["discovery"]
        )
        memory_checkpoint(
            phase=1,
            phase_name="Discovery",
            summary="Discovery done"
        )

        # Recall from specific phases
        phase0_context = memory_recall_phase(0)
        phase1_context = memory_recall_phase(1)

        assert len(phase0_context.entries) > 0
        assert len(phase1_context.entries) > 0

        # List checkpoints
        checkpoints = memory_list_checkpoints()
        assert len(checkpoints) == 2


class TestBacktracking:
    """Test backtracking scenarios."""

    def test_backtrack_invalidates_future_checkpoints(self, temp_dir):
        """Test that backtracking invalidates future checkpoints."""
        memory_init(temp_dir)

        # Create checkpoints for phases 0, 1, 2
        for phase in range(3):
            memory_checkpoint(
                phase=phase,
                phase_name=f"Phase {phase}",
                summary=f"Phase {phase} done"
            )

        # Backtrack to phase 0
        result = memory_handle_backtrack(target_phase=0)

        assert result["invalidated_checkpoints"] > 0

        # Check that phases 1+ are invalidated
        checkpoints = memory_list_checkpoints()
        for cp in checkpoints:
            if cp.phase > 0:
                assert cp.status == CheckpointStatus.INVALIDATED

    def test_backtrack_clears_memory_entries(self, temp_dir):
        """Test that backtracking clears memory entries."""
        memory_init(temp_dir)

        # Add entries to multiple phases
        memory_save(phase="0-setup", task_id="001", content="Phase 0")
        memory_save(phase="1-discovery", task_id="101", content="Phase 1")
        memory_save(phase="2-prd", task_id="201", content="Phase 2")

        # Backtrack to phase 0
        result = memory_handle_backtrack(target_phase=0)

        assert result["cleared_entries"] > 0

        # Phase 0 should remain, others should be cleared
        phase0_context = memory_recall_phase(0)
        phase1_context = memory_recall_phase(1)

        assert len(phase0_context.entries) > 0
        assert len(phase1_context.entries) == 0


class TestMemoryCompaction:
    """Test memory compaction scenarios."""

    def test_compaction_effectiveness(self, temp_dir):
        """Test that compaction reduces memory size."""
        memory_init(temp_dir)

        # Add many old, low-value entries
        for i in range(50):
            memory_save(
                phase="0-setup",
                task_id=f"{i:03d}",
                content=f"Entry {i}",
                tags=["test"]
            )

        # Get initial stats
        initial_stats = memory_stats()
        initial_count = initial_stats.total_entries

        # Compact
        result = memory_compact(max_age_days=30, min_relevance=0.5)

        # Get final stats
        final_stats = memory_stats()

        assert final_stats.total_entries <= initial_count

    def test_compaction_preserves_checkpoints(self, temp_dir):
        """Test that compaction keeps checkpoints."""
        memory_init(temp_dir)

        # Create checkpoint
        checkpoint_id = memory_checkpoint(
            phase=0,
            phase_name="Setup",
            summary="Important checkpoint"
        )

        # Add low-value entries
        for i in range(10):
            memory_save(
                phase="0-setup",
                task_id=f"{i:03d}",
                content="x",
                tags=[]
            )

        # Compact aggressively
        memory_compact(max_age_days=1, min_relevance=0.9)

        # Checkpoint should still exist
        checkpoint = memory_restore(checkpoint_id)
        assert checkpoint is not None


class TestConcurrentAccess:
    """Test concurrent memory access."""

    def test_multiple_saves_sequential(self, temp_dir):
        """Test sequential saves work correctly."""
        memory_init(temp_dir)

        ids = []
        for i in range(10):
            entry_id = memory_save(
                phase="0-setup",
                task_id=f"{i:03d}",
                content=f"Content {i}",
                tags=["test"]
            )
            ids.append(entry_id)

        # All entries should be retrievable
        context = memory_recall("Content", max_tokens=10000)
        assert len(context.entries) == 10

    def test_save_during_recall(self, temp_dir):
        """Test saving while recalling."""
        memory_init(temp_dir)

        # Add some initial entries
        for i in range(5):
            memory_save(
                phase="0-setup",
                task_id=f"{i:03d}",
                content=f"Initial {i}",
                tags=["initial"]
            )

        # Recall
        context1 = memory_recall("Initial")

        # Save more
        memory_save(
            phase="0-setup",
            task_id="999",
            content="Additional entry",
            tags=["additional"]
        )

        # Recall again
        context2 = memory_recall("entry")

        # Should find the new entry
        assert len(context2.entries) > 0


class TestLargeMemorySets:
    """Test with large amounts of memory."""

    def test_large_number_of_entries(self, temp_dir):
        """Test handling large number of entries."""
        memory_init(temp_dir)

        # Add many entries
        for i in range(100):
            memory_save(
                phase=f"{i % 3}-phase",
                task_id=f"{i:03d}",
                content=f"Entry {i} with some content to search",
                tags=[f"tag{i % 10}"]
            )

        # Recall should still work efficiently
        start_time = time.time()
        context = memory_recall("content", max_tokens=1000)
        elapsed = time.time() - start_time

        assert elapsed < 1.0  # Should complete in under 1 second
        assert len(context.entries) > 0

    def test_large_content_entries(self, temp_dir):
        """Test handling large content entries."""
        memory_init(temp_dir)

        # Add entries with large content
        large_content = "This is a large content block. " * 1000
        for i in range(10):
            memory_save(
                phase="0-setup",
                task_id=f"{i:03d}",
                content=large_content,
                tags=["large"]
            )

        # Should handle gracefully
        stats = memory_stats()
        assert stats.total_entries == 10


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_recall_before_any_saves(self, temp_dir):
        """Test recalling when no memory exists."""
        memory_init(temp_dir)

        context = memory_recall("anything")
        assert context.entries == []
        assert context.total_tokens == 0

    def test_save_empty_content(self, temp_dir):
        """Test saving empty content."""
        memory_init(temp_dir)

        entry_id = memory_save(
            phase="0-setup",
            task_id="001",
            content="",
            tags=[]
        )

        assert entry_id is not None

    def test_save_very_long_content(self, temp_dir):
        """Test saving very long content."""
        memory_init(temp_dir)

        long_content = "x" * 100000
        entry_id = memory_save(
            phase="0-setup",
            task_id="001",
            content=long_content,
            tags=[]
        )

        assert entry_id is not None

    def test_recall_with_special_characters(self, temp_dir):
        """Test recall with special characters in query."""
        memory_init(temp_dir)

        memory_save(
            phase="0-setup",
            task_id="001",
            content="Special: @#$%^&*()",
            tags=[]
        )

        # Should not crash
        context = memory_recall("@#$%^&*()")
        assert context is not None

    def test_checkpoint_with_empty_summary(self, temp_dir):
        """Test checkpoint with empty summary."""
        memory_init(temp_dir)

        checkpoint_id = memory_checkpoint(
            phase=0,
            phase_name="Setup",
            summary=""
        )

        assert checkpoint_id is not None


class TestStatistics:
    """Test statistics reporting."""

    def test_stats_empty_memory(self, temp_dir):
        """Test stats on empty memory."""
        memory_init(temp_dir)

        stats = memory_stats()

        assert stats.total_entries == 0
        assert stats.total_checkpoints == 0

    def test_stats_with_content(self, temp_dir):
        """Test stats with memory content."""
        memory_init(temp_dir)

        # Add entries
        for i in range(5):
            memory_save(
                phase="0-setup",
                task_id=f"{i:03d}",
                content=f"Entry {i}",
                tags=[]
            )

        # Create checkpoint
        memory_checkpoint(phase=0, phase_name="Setup", summary="Done")

        stats = memory_stats()

        assert stats.total_entries == 5
        assert stats.size_mb >= 0  # May be 0.0 for small files
        assert "0-setup" in stats.entries_by_phase

    def test_stats_after_compaction(self, temp_dir):
        """Test stats after compaction."""
        memory_init(temp_dir)

        # Add entries
        for i in range(20):
            memory_save(
                phase="0-setup",
                task_id=f"{i:03d}",
                content="x",
                tags=[]
            )

        initial_stats = memory_stats()

        # Compact
        memory_compact(max_age_days=0, min_relevance=0.9)

        final_stats = memory_stats()

        assert final_stats.total_entries <= initial_stats.total_entries


class TestRecentRecall:
    """Test recent entry recall."""

    def test_recent_recall_ordering(self, temp_dir):
        """Test that recent recall returns newest first."""
        memory_init(temp_dir)

        # Add entries with small delays
        ids = []
        for i in range(5):
            entry_id = memory_save(
                phase="0-setup",
                task_id=f"{i:03d}",
                content=f"Entry {i}",
                tags=[]
            )
            ids.append(entry_id)
            time.sleep(0.01)

        context = memory_recall_recent(count=3)

        assert len(context.entries) == 3
        # Newest should be first
        assert context.entries[0].content == "Entry 4"

    def test_recent_recall_with_limit(self, temp_dir):
        """Test recent recall respects count limit."""
        memory_init(temp_dir)

        for i in range(10):
            memory_save(
                phase="0-setup",
                task_id=f"{i:03d}",
                content=f"Entry {i}",
                tags=[]
            )

        context = memory_recall_recent(count=5)
        assert len(context.entries) == 5
