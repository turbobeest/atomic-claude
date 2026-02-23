"""
Unit Tests for Checkpoint Manager

Tests for checkpoint creation, restoration, and management.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from core.memory.store import MemoryStore
from core.memory.checkpoint import CheckpointManager
from core.memory.types import CheckpointStatus


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
def manager(temp_dir, store):
    """Create checkpoint manager."""
    return CheckpointManager(temp_dir, store)


class TestCheckpointCreation:
    """Test checkpoint creation."""

    def test_create_checkpoint_returns_id(self, manager):
        """Test that create returns checkpoint ID."""
        checkpoint_id = manager.create_checkpoint(
            phase=0,
            phase_name="Setup",
            summary="Test checkpoint"
        )

        assert checkpoint_id is not None
        assert checkpoint_id.startswith("phase0-")

    def test_create_checkpoint_saves_file(self, manager, temp_dir):
        """Test that checkpoint file is created."""
        checkpoint_id = manager.create_checkpoint(
            phase=0,
            phase_name="Setup",
            summary="Test checkpoint"
        )

        checkpoint_file = temp_dir / "memory-checkpoints" / f"{checkpoint_id}.json"
        assert checkpoint_file.exists()

    def test_create_checkpoint_with_decisions(self, manager):
        """Test creating checkpoint with key decisions."""
        decisions = ["Decision 1", "Decision 2"]
        checkpoint_id = manager.create_checkpoint(
            phase=0,
            phase_name="Setup",
            summary="Test",
            key_decisions=decisions
        )

        checkpoint = manager.restore_checkpoint(checkpoint_id)
        assert checkpoint is not None
        assert checkpoint.key_decisions == decisions

    def test_create_checkpoint_with_artifacts(self, manager):
        """Test creating checkpoint with artifacts."""
        artifacts = ["/path/to/file1.txt", "/path/to/file2.json"]
        checkpoint_id = manager.create_checkpoint(
            phase=0,
            phase_name="Setup",
            summary="Test",
            artifacts=artifacts
        )

        checkpoint = manager.restore_checkpoint(checkpoint_id)
        assert checkpoint is not None
        assert checkpoint.artifacts == artifacts

    def test_create_checkpoint_with_state_snapshot(self, manager):
        """Test creating checkpoint with state snapshot."""
        state = {"task_count": 10, "completed": 5}
        checkpoint_id = manager.create_checkpoint(
            phase=0,
            phase_name="Setup",
            summary="Test",
            state_snapshot=state
        )

        checkpoint = manager.restore_checkpoint(checkpoint_id)
        assert checkpoint is not None
        assert checkpoint.state_snapshot == state

    def test_create_checkpoint_updates_head(self, manager, temp_dir):
        """Test that creating checkpoint updates head file."""
        checkpoint_id = manager.create_checkpoint(
            phase=0,
            phase_name="Setup",
            summary="Test"
        )

        import json
        with open(temp_dir / "memory-head.json", 'r') as f:
            head = json.load(f)

        assert head["head_phase"] == 0
        assert head["head_checkpoint"] == checkpoint_id

    def test_create_multiple_checkpoints(self, manager):
        """Test creating multiple checkpoints."""
        ids = []
        for i in range(3):
            checkpoint_id = manager.create_checkpoint(
                phase=i,
                phase_name=f"Phase {i}",
                summary=f"Summary {i}"
            )
            ids.append(checkpoint_id)

        # All should be restorable
        for checkpoint_id in ids:
            checkpoint = manager.restore_checkpoint(checkpoint_id)
            assert checkpoint is not None


class TestCheckpointRestoration:
    """Test checkpoint restoration."""

    def test_restore_existing_checkpoint(self, manager):
        """Test restoring existing checkpoint."""
        checkpoint_id = manager.create_checkpoint(
            phase=0,
            phase_name="Setup",
            summary="Test checkpoint"
        )

        checkpoint = manager.restore_checkpoint(checkpoint_id)
        assert checkpoint is not None
        assert checkpoint.checkpoint_id == checkpoint_id
        assert checkpoint.phase == 0
        assert checkpoint.phase_name == "Setup"
        assert checkpoint.summary == "Test checkpoint"

    def test_restore_nonexistent_checkpoint(self, manager):
        """Test restoring non-existent checkpoint returns None."""
        checkpoint = manager.restore_checkpoint("nonexistent")
        assert checkpoint is None

    def test_restore_preserves_data(self, manager):
        """Test that all data is preserved on restore."""
        decisions = ["Decision 1"]
        artifacts = ["/path/to/file"]
        state = {"key": "value"}

        checkpoint_id = manager.create_checkpoint(
            phase=1,
            phase_name="Discovery",
            summary="Test",
            key_decisions=decisions,
            artifacts=artifacts,
            state_snapshot=state
        )

        checkpoint = manager.restore_checkpoint(checkpoint_id)
        assert checkpoint.key_decisions == decisions
        assert checkpoint.artifacts == artifacts
        assert checkpoint.state_snapshot == state


class TestListCheckpoints:
    """Test listing checkpoints."""

    def test_list_empty_checkpoints(self, manager):
        """Test listing when no checkpoints exist."""
        checkpoints = manager.list_checkpoints()
        assert checkpoints == []

    def test_list_all_checkpoints(self, manager):
        """Test listing all checkpoints."""
        for i in range(3):
            manager.create_checkpoint(
                phase=i,
                phase_name=f"Phase {i}",
                summary=f"Summary {i}"
            )

        checkpoints = manager.list_checkpoints()
        assert len(checkpoints) == 3

    def test_list_checkpoints_by_phase(self, manager):
        """Test filtering checkpoints by phase."""
        manager.create_checkpoint(phase=0, phase_name="Setup", summary="Test")
        manager.create_checkpoint(phase=1, phase_name="Discovery", summary="Test")
        manager.create_checkpoint(phase=0, phase_name="Setup", summary="Test 2")

        checkpoints = manager.list_checkpoints(phase=0)
        assert len(checkpoints) == 2
        assert all(c.phase == 0 for c in checkpoints)

    def test_list_checkpoints_by_status(self, manager):
        """Test filtering checkpoints by status."""
        checkpoint_id = manager.create_checkpoint(
            phase=0,
            phase_name="Setup",
            summary="Test"
        )

        # Initially valid
        checkpoints = manager.list_checkpoints(status=CheckpointStatus.VALID)
        assert len(checkpoints) == 1

        # Invalidate all after phase -1 (phase 0 > -1 is True, so it gets invalidated)
        manager.invalidate_after_phase(-1)

        # No valid checkpoints remain
        checkpoints = manager.list_checkpoints(status=CheckpointStatus.VALID)
        assert len(checkpoints) == 0

        # Should find it with INVALIDATED filter
        checkpoints = manager.list_checkpoints(status=CheckpointStatus.INVALIDATED)
        assert len(checkpoints) == 1

    def test_list_checkpoints_sorted_by_date(self, manager):
        """Test that checkpoints are sorted newest first."""
        import time

        ids = []
        for i in range(3):
            checkpoint_id = manager.create_checkpoint(
                phase=i,
                phase_name=f"Phase {i}",
                summary=f"Summary {i}"
            )
            ids.append(checkpoint_id)
            time.sleep(0.01)  # Small delay to ensure different timestamps

        checkpoints = manager.list_checkpoints()
        assert len(checkpoints) == 3

        # Should be sorted newest first
        for i in range(len(checkpoints) - 1):
            assert checkpoints[i].created_at >= checkpoints[i + 1].created_at


class TestLatestCheckpoint:
    """Test getting latest checkpoint."""

    def test_get_latest_checkpoint_empty(self, manager):
        """Test getting latest when no checkpoints exist."""
        latest = manager.get_latest_checkpoint()
        assert latest is None

    def test_get_latest_checkpoint(self, manager):
        """Test getting most recent checkpoint."""
        import time

        ids = []
        for i in range(3):
            checkpoint_id = manager.create_checkpoint(
                phase=i,
                phase_name=f"Phase {i}",
                summary=f"Summary {i}"
            )
            ids.append(checkpoint_id)
            time.sleep(0.01)

        latest = manager.get_latest_checkpoint()
        assert latest is not None
        assert latest.checkpoint_id == ids[-1]

    def test_get_latest_checkpoint_by_phase(self, manager):
        """Test getting latest checkpoint for specific phase."""
        import time

        manager.create_checkpoint(phase=0, phase_name="Setup", summary="First")
        time.sleep(0.01)
        id2 = manager.create_checkpoint(phase=0, phase_name="Setup", summary="Second")
        time.sleep(0.01)
        manager.create_checkpoint(phase=1, phase_name="Discovery", summary="Third")

        latest = manager.get_latest_checkpoint(phase=0)
        assert latest is not None
        assert latest.checkpoint_id == id2


class TestPruneCheckpoints:
    """Test checkpoint pruning."""

    def test_prune_keeps_recent_checkpoints(self, manager):
        """Test that pruning keeps most recent N checkpoints."""
        for i in range(10):
            manager.create_checkpoint(
                phase=0,
                phase_name="Setup",
                summary=f"Checkpoint {i}"
            )

        removed = manager.prune_checkpoints(keep_count=5)
        assert removed == 5

        remaining = manager.list_checkpoints()
        assert len(remaining) == 5

    def test_prune_with_fewer_checkpoints(self, manager):
        """Test pruning when fewer checkpoints than keep_count."""
        for i in range(3):
            manager.create_checkpoint(
                phase=0,
                phase_name="Setup",
                summary=f"Checkpoint {i}"
            )

        removed = manager.prune_checkpoints(keep_count=5)
        assert removed == 0

        remaining = manager.list_checkpoints()
        assert len(remaining) == 3


class TestDeleteCheckpoint:
    """Test deleting checkpoints."""

    def test_delete_existing_checkpoint(self, manager):
        """Test deleting existing checkpoint."""
        checkpoint_id = manager.create_checkpoint(
            phase=0,
            phase_name="Setup",
            summary="Test"
        )

        deleted = manager.delete_checkpoint(checkpoint_id)
        assert deleted is True

        # Should not be restorable
        checkpoint = manager.restore_checkpoint(checkpoint_id)
        assert checkpoint is None

    def test_delete_nonexistent_checkpoint(self, manager):
        """Test deleting non-existent checkpoint."""
        deleted = manager.delete_checkpoint("nonexistent")
        assert deleted is False


class TestInvalidateAfterPhase:
    """Test invalidating checkpoints after a phase."""

    def test_invalidate_after_phase(self, manager):
        """Test invalidating checkpoints after target phase."""
        manager.create_checkpoint(phase=0, phase_name="Setup", summary="Phase 0")
        manager.create_checkpoint(phase=1, phase_name="Discovery", summary="Phase 1")
        manager.create_checkpoint(phase=2, phase_name="PRD", summary="Phase 2")

        invalidated = manager.invalidate_after_phase(0)
        assert invalidated == 2

        # Check statuses
        checkpoints = manager.list_checkpoints()
        for checkpoint in checkpoints:
            if checkpoint.phase > 0:
                assert checkpoint.status == CheckpointStatus.INVALIDATED
            else:
                assert checkpoint.status == CheckpointStatus.VALID

    def test_invalidate_no_checkpoints_after(self, manager):
        """Test invalidating when no checkpoints after target."""
        manager.create_checkpoint(phase=0, phase_name="Setup", summary="Phase 0")

        invalidated = manager.invalidate_after_phase(5)
        assert invalidated == 0
