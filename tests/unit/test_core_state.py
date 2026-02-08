"""
Unit Tests for Core State Management

Tests StateManager, StateTransaction, StateSnapshot, and related classes.

Author: Phase 6 - Testing & Validation
"""

import pytest
import json
import shutil
from pathlib import Path
from datetime import datetime

from core.state import (
    StateManager,
    StateTransaction,
    StateSnapshot,
    StateLock,
    TaskStatus,
    PhaseStatus,
    TaskState,
    PhaseState,
    task_running
)


# ============================================================================
# STATEMANAGER TESTS
# ============================================================================

@pytest.mark.unit
class TestStateManager:
    """Test StateManager class."""

    def test_init_creates_directories(self, temp_dir):
        """Test StateManager creates required directories."""
        state_dir = temp_dir / ".state"
        state = StateManager(state_dir=state_dir, atomic_root=temp_dir)

        assert state_dir.exists()
        assert (state_dir / "snapshots").exists()

    def test_init_creates_state_file(self, temp_dir):
        """Test StateManager creates state file."""
        state_dir = temp_dir / ".state"
        state = StateManager(state_dir=state_dir, atomic_root=temp_dir)

        state_file = state_dir / "task-state.json"
        assert state_file.exists()

    def test_load_empty_state(self, temp_dir):
        """Test loading empty state."""
        state = StateManager(state_dir=temp_dir / ".state", atomic_root=temp_dir)

        assert state._state["version"] == "2.0"
        assert state._state["phases"] == {}
        assert state._state["current_phase"] is None

    def test_save_state_atomic(self, temp_dir):
        """Test state saving is atomic."""
        state = StateManager(state_dir=temp_dir / ".state", atomic_root=temp_dir)

        # Mark task complete
        state.mark_task_complete("0-setup", "001", "Test Task")

        # Verify file exists
        assert state.state_file.exists()

        # Verify content
        with open(state.state_file) as f:
            data = json.load(f)

        assert "0-setup" in data["phases"]
        assert "001" in data["phases"]["0-setup"]["tasks"]

    def test_mark_task_complete(self, temp_dir):
        """Test marking task as complete."""
        state = StateManager(state_dir=temp_dir / ".state", atomic_root=temp_dir)

        phase_id = "0-setup"
        task_id = "001"
        task_name = "Test Task"

        assert not state.is_task_complete(phase_id, task_id)

        state.mark_task_complete(phase_id, task_id, task_name)

        assert state.is_task_complete(phase_id, task_id)

    def test_mark_task_failed(self, temp_dir):
        """Test marking task as failed."""
        state = StateManager(state_dir=temp_dir / ".state", atomic_root=temp_dir)

        phase_id = "0-setup"
        task_id = "001"
        task_name = "Test Task"
        error = "Test error"

        state.mark_task_failed(phase_id, task_id, task_name, error)

        assert state.is_task_failed(phase_id, task_id)
        assert not state.is_task_complete(phase_id, task_id)

    def test_get_task_status(self, temp_dir):
        """Test getting task status."""
        state = StateManager(state_dir=temp_dir / ".state", atomic_root=temp_dir)

        phase_id = "0-setup"

        # Default status
        assert state.get_task_status(phase_id, "001") == "pending"

        # Complete status
        state.mark_task_complete(phase_id, "002", "Task 2")
        assert state.get_task_status(phase_id, "002") == "completed"

        # Failed status
        state.mark_task_failed(phase_id, "003", "Task 3", "Error")
        assert state.get_task_status(phase_id, "003") == "failed"

    def test_get_current_phase(self, temp_dir):
        """Test getting current phase."""
        state = StateManager(state_dir=temp_dir / ".state", atomic_root=temp_dir)

        assert state.get_current_phase() is None

        state.set_current_phase("0-setup")
        assert state.get_current_phase() == "0-setup"

    def test_get_phase_tasks(self, temp_dir):
        """Test getting all tasks for a phase."""
        state = StateManager(state_dir=temp_dir / ".state", atomic_root=temp_dir)

        phase_id = "0-setup"

        # Empty phase
        assert state.get_phase_tasks(phase_id) == {}

        # Add tasks
        state.mark_task_complete(phase_id, "001", "Task 1")
        state.mark_task_complete(phase_id, "002", "Task 2")

        tasks = state.get_phase_tasks(phase_id)
        assert len(tasks) == 2
        assert "001" in tasks
        assert "002" in tasks

    def test_get_completed_tasks(self, temp_dir):
        """Test getting completed tasks for a phase."""
        state = StateManager(state_dir=temp_dir / ".state", atomic_root=temp_dir)

        phase_id = "0-setup"

        # Mark some tasks complete, some failed
        state.mark_task_complete(phase_id, "001", "Task 1")
        state.mark_task_complete(phase_id, "002", "Task 2")
        state.mark_task_failed(phase_id, "003", "Task 3", "Error")

        completed = state.get_completed_tasks(phase_id)
        assert len(completed) == 2
        assert "001" in completed
        assert "002" in completed
        assert "003" not in completed

    def test_mark_phase_complete(self, temp_dir):
        """Test marking entire phase as complete."""
        state = StateManager(state_dir=temp_dir / ".state", atomic_root=temp_dir)

        phase_id = "0-setup"
        state.mark_phase_complete(phase_id)

        phase_data = state._state["phases"][phase_id]
        assert phase_data["status"] == "completed"
        assert "completed_at" in phase_data

    def test_reset_phase(self, temp_dir):
        """Test resetting a specific phase."""
        state = StateManager(state_dir=temp_dir / ".state", atomic_root=temp_dir)

        phase_id = "0-setup"
        state.mark_task_complete(phase_id, "001", "Task 1")
        assert phase_id in state._state["phases"]

        state.reset_phase(phase_id)
        assert phase_id not in state._state["phases"]

    def test_reset_all(self, temp_dir):
        """Test resetting entire pipeline."""
        state = StateManager(state_dir=temp_dir / ".state", atomic_root=temp_dir)

        # Create some state
        state.mark_task_complete("0-setup", "001", "Task 1")
        state.mark_task_complete("1-discovery", "101", "Task 2")

        state.reset_all()

        assert state._state["phases"] == {}
        assert state._state["current_phase"] is None

    def test_state_persistence(self, temp_dir):
        """Test state persists across instances."""
        state_dir = temp_dir / ".state"

        # First instance
        state1 = StateManager(state_dir=state_dir, atomic_root=temp_dir)
        state1.mark_task_complete("0-setup", "001", "Task 1")

        # Second instance (load from disk)
        state2 = StateManager(state_dir=state_dir, atomic_root=temp_dir)

        assert state2.is_task_complete("0-setup", "001")

    def test_task_with_artifacts(self, temp_dir):
        """Test marking task complete with artifacts."""
        state = StateManager(state_dir=temp_dir / ".state", atomic_root=temp_dir)

        phase_id = "0-setup"
        task_id = "001"
        artifacts = [
            ".outputs/0-setup/config.json",
            ".outputs/0-setup/report.md"
        ]

        state.mark_task_complete(phase_id, task_id, "Task 1", artifacts=artifacts)

        tasks = state.get_phase_tasks(phase_id)
        task_data = tasks[task_id]
        assert task_data["artifacts"] == artifacts


# ============================================================================
# STATE TRANSACTION TESTS
# ============================================================================

@pytest.mark.unit
class TestStateTransaction:
    """Test StateTransaction class."""

    def test_transaction_commit_on_success(self, temp_dir):
        """Test transaction commits on successful completion."""
        state = StateManager(state_dir=temp_dir / ".state", atomic_root=temp_dir)

        with state.begin_transaction() as txn:
            txn.mark_task_complete("0-setup", "001", "Task 1")

        # Changes should be committed
        assert state.is_task_complete("0-setup", "001")

    def test_transaction_rollback_on_error(self, temp_dir):
        """Test transaction rolls back on exception."""
        state = StateManager(state_dir=temp_dir / ".state", atomic_root=temp_dir)

        # Initial state
        state.mark_task_complete("0-setup", "001", "Task 1")

        # Transaction with error
        try:
            with state.begin_transaction() as txn:
                txn.mark_task_complete("0-setup", "002", "Task 2")
                raise ValueError("Test error")
        except ValueError:
            pass

        # Task 1 should still be complete
        assert state.is_task_complete("0-setup", "001")

        # Task 2 should be rolled back
        assert not state.is_task_complete("0-setup", "002")

    def test_nested_transaction_changes(self, temp_dir):
        """Test multiple changes within transaction."""
        state = StateManager(state_dir=temp_dir / ".state", atomic_root=temp_dir)

        with state.begin_transaction() as txn:
            txn.mark_task_complete("0-setup", "001", "Task 1")
            txn.mark_task_complete("0-setup", "002", "Task 2")
            txn.mark_task_complete("0-setup", "003", "Task 3")

        # All changes should be committed
        assert state.is_task_complete("0-setup", "001")
        assert state.is_task_complete("0-setup", "002")
        assert state.is_task_complete("0-setup", "003")

    def test_transaction_set_current_phase(self, temp_dir):
        """Test setting current phase in transaction."""
        state = StateManager(state_dir=temp_dir / ".state", atomic_root=temp_dir)

        with state.begin_transaction() as txn:
            txn.set_current_phase("1-discovery")

        assert state.get_current_phase() == "1-discovery"


# ============================================================================
# STATE SNAPSHOT TESTS
# ============================================================================

@pytest.mark.unit
class TestStateSnapshot:
    """Test StateSnapshot class."""

    def test_create_snapshot(self, temp_dir):
        """Test creating state snapshot."""
        state = StateManager(state_dir=temp_dir / ".state", atomic_root=temp_dir)

        # Create some state
        state.mark_task_complete("0-setup", "001", "Task 1")
        state.mark_task_complete("0-setup", "002", "Task 2")

        # Create snapshot
        snapshot = state.snapshot()

        assert snapshot.version == "2.0"
        assert len(snapshot.phases) == 1
        assert "0-setup" in snapshot.phases

    def test_restore_snapshot(self, temp_dir):
        """Test restoring from snapshot."""
        state = StateManager(state_dir=temp_dir / ".state", atomic_root=temp_dir)

        # Create initial state
        state.mark_task_complete("0-setup", "001", "Task 1")
        state.mark_task_complete("0-setup", "002", "Task 2")

        # Snapshot
        snapshot = state.snapshot()

        # Make changes
        state.mark_task_complete("0-setup", "003", "Task 3")
        assert state.is_task_complete("0-setup", "003")

        # Restore
        state.restore(snapshot)

        # Verify restoration
        assert state.is_task_complete("0-setup", "001")
        assert state.is_task_complete("0-setup", "002")
        assert not state.is_task_complete("0-setup", "003")

    def test_save_snapshot_to_disk(self, temp_dir):
        """Test saving snapshot to disk."""
        state = StateManager(state_dir=temp_dir / ".state", atomic_root=temp_dir)

        state.mark_task_complete("0-setup", "001", "Task 1")

        snapshot_file = state.save_snapshot("test_snapshot")

        assert snapshot_file.exists()
        assert snapshot_file.name == "test_snapshot.json"

    def test_load_snapshot_from_disk(self, temp_dir):
        """Test loading snapshot from disk."""
        state = StateManager(state_dir=temp_dir / ".state", atomic_root=temp_dir)

        # Create and save snapshot
        state.mark_task_complete("0-setup", "001", "Task 1")
        snapshot_file = state.save_snapshot("test")

        # Make changes
        state.mark_task_complete("0-setup", "002", "Task 2")

        # Load snapshot
        state.load_snapshot(snapshot_file)

        # Verify restoration
        assert state.is_task_complete("0-setup", "001")
        assert not state.is_task_complete("0-setup", "002")

    def test_snapshot_to_dict(self, temp_dir):
        """Test converting snapshot to dict."""
        state = StateManager(state_dir=temp_dir / ".state", atomic_root=temp_dir)

        state.mark_task_complete("0-setup", "001", "Task 1")
        snapshot = state.snapshot()

        data = snapshot.to_dict()

        assert isinstance(data, dict)
        assert "version" in data
        assert "phases" in data
        assert "timestamp" in data


# ============================================================================
# STATE LOCK TESTS
# ============================================================================

@pytest.mark.unit
class TestStateLock:
    """Test StateLock class."""

    def test_acquire_lock(self, temp_dir):
        """Test acquiring file lock."""
        lock_file = temp_dir / "test.lock"
        lock = StateLock(lock_file)

        acquired = lock.acquire()
        assert acquired is True

        lock.release()

    def test_release_lock(self, temp_dir):
        """Test releasing file lock."""
        lock_file = temp_dir / "test.lock"
        lock = StateLock(lock_file)

        lock.acquire()
        lock.release()

        # Lock file should be cleaned up
        assert not lock_file.exists()

    def test_lock_context_manager(self, temp_dir):
        """Test using lock as context manager."""
        lock_file = temp_dir / "test.lock"

        with StateLock(lock_file) as lock:
            # Lock should be acquired
            pass

        # Lock should be released
        assert not lock_file.exists()


# ============================================================================
# TASK STATE TESTS
# ============================================================================

@pytest.mark.unit
class TestTaskState:
    """Test TaskState dataclass."""

    def test_create_task_state(self):
        """Test creating TaskState instance."""
        task = TaskState(
            task_id="001",
            name="Test Task",
            status=TaskStatus.COMPLETED
        )

        assert task.task_id == "001"
        assert task.name == "Test Task"
        assert task.status == TaskStatus.COMPLETED

    def test_task_state_to_dict(self):
        """Test converting TaskState to dict."""
        task = TaskState(
            task_id="001",
            name="Test Task",
            status=TaskStatus.COMPLETED
        )

        data = task.to_dict()

        assert isinstance(data, dict)
        assert data["task_id"] == "001"
        assert data["status"] == "completed"

    def test_task_state_with_artifacts(self):
        """Test TaskState with artifacts."""
        artifacts = ["file1.txt", "file2.txt"]
        task = TaskState(
            task_id="001",
            name="Test Task",
            status=TaskStatus.COMPLETED,
            artifacts=artifacts
        )

        assert task.artifacts == artifacts

    def test_task_state_status_conversion(self):
        """Test TaskState converts string status to enum."""
        task = TaskState(
            task_id="001",
            name="Test Task",
            status="completed"  # String
        )

        assert task.status == TaskStatus.COMPLETED
        assert isinstance(task.status, TaskStatus)

    def test_task_state_complete_alias(self):
        """Test TaskState handles 'complete' alias."""
        task = TaskState(
            task_id="001",
            name="Test Task",
            status="complete"  # Alias
        )

        assert task.status == TaskStatus.COMPLETED


# ============================================================================
# PHASE STATE TESTS
# ============================================================================

@pytest.mark.unit
class TestPhaseState:
    """Test PhaseState dataclass."""

    def test_create_phase_state(self):
        """Test creating PhaseState instance."""
        phase = PhaseState(
            phase_id="0-setup",
            status=PhaseStatus.COMPLETED
        )

        assert phase.phase_id == "0-setup"
        assert phase.status == PhaseStatus.COMPLETED

    def test_phase_state_with_tasks(self):
        """Test PhaseState with tasks."""
        tasks = {
            "001": TaskState(
                task_id="001",
                name="Task 1",
                status=TaskStatus.COMPLETED
            )
        }

        phase = PhaseState(
            phase_id="0-setup",
            status=PhaseStatus.COMPLETED,
            tasks=tasks
        )

        assert len(phase.tasks) == 1
        assert "001" in phase.tasks

    def test_phase_state_to_dict(self):
        """Test converting PhaseState to dict."""
        phase = PhaseState(
            phase_id="0-setup",
            status=PhaseStatus.COMPLETED
        )

        data = phase.to_dict()

        assert isinstance(data, dict)
        assert "status" in data
        assert "tasks" in data


# ============================================================================
# TASK RUNNING CONTEXT MANAGER TESTS
# ============================================================================

@pytest.mark.unit
class TestTaskRunning:
    """Test task_running context manager."""

    def test_task_running_creates_file(self, temp_dir):
        """Test task_running creates current-task.json."""
        state_dir = temp_dir / ".state"
        state_dir.mkdir(parents=True, exist_ok=True)

        with task_running("0-setup", "001", "Test Task", state_dir=state_dir):
            # File should exist during execution
            current_file = state_dir / "current-task.json"
            assert current_file.exists()

            # Verify content
            with open(current_file) as f:
                data = json.load(f)

            assert data["phase"] == "0-setup"
            assert data["task"] == "001"
            assert data["name"] == "Test Task"

    def test_task_running_cleanup(self, temp_dir):
        """Test task_running cleans up after completion."""
        state_dir = temp_dir / ".state"
        state_dir.mkdir(parents=True, exist_ok=True)

        with task_running("0-setup", "001", "Test Task", state_dir=state_dir):
            pass

        # File should be cleaned up
        current_file = state_dir / "current-task.json"
        assert not current_file.exists()

    def test_task_running_cleanup_on_error(self, temp_dir):
        """Test task_running cleans up even on error."""
        state_dir = temp_dir / ".state"
        state_dir.mkdir(parents=True, exist_ok=True)

        try:
            with task_running("0-setup", "001", "Test Task", state_dir=state_dir):
                raise ValueError("Test error")
        except ValueError:
            pass

        # File should still be cleaned up
        current_file = state_dir / "current-task.json"
        assert not current_file.exists()


# ============================================================================
# STATE VERSION MIGRATION TESTS
# ============================================================================

@pytest.mark.unit
class TestStateMigration:
    """Test state version migration."""

    def test_migrate_v1_to_v2(self, temp_dir):
        """Test migrating state from v1.0 to v2.0."""
        state = StateManager(state_dir=temp_dir / ".state", atomic_root=temp_dir)

        # Create v1.0 state
        old_state = {
            "version": "1.0",
            "phases": {
                "0-setup": {
                    "tasks": {
                        "001": {"name": "Task 1", "status": "complete"}  # Old alias
                    }
                }
            }
        }

        # Migrate
        migrated = state._migrate_state(old_state)

        # Verify migration
        assert migrated["version"] == "2.0"
        assert "metadata" in migrated
        # Status should be normalized to "completed"
        assert migrated["phases"]["0-setup"]["tasks"]["001"]["status"] == "completed"

    def test_load_old_state_auto_migrates(self, temp_dir):
        """Test loading old state automatically migrates."""
        state_dir = temp_dir / ".state"
        state_file = state_dir / "task-state.json"
        state_dir.mkdir(parents=True, exist_ok=True)

        # Write old version state
        old_state = {
            "version": "1.0",
            "phases": {}
        }

        with open(state_file, 'w') as f:
            json.dump(old_state, f)

        # Load state (should auto-migrate)
        state = StateManager(state_dir=state_dir, atomic_root=temp_dir)

        # Verify migrated
        assert state._state["version"] == "2.0"
        assert "metadata" in state._state


# ============================================================================
# EDGE CASES
# ============================================================================

@pytest.mark.unit
class TestStateEdgeCases:
    """Test edge cases in state management."""

    def test_mark_same_task_twice(self, temp_dir):
        """Test marking same task complete twice (idempotent)."""
        state = StateManager(state_dir=temp_dir / ".state", atomic_root=temp_dir)

        phase_id = "0-setup"
        task_id = "001"

        state.mark_task_complete(phase_id, task_id, "Task 1")
        state.mark_task_complete(phase_id, task_id, "Task 1")

        # Should have only one task record
        tasks = state.get_phase_tasks(phase_id)
        assert len(tasks) == 1

    def test_get_nonexistent_phase(self, temp_dir):
        """Test getting tasks for nonexistent phase."""
        state = StateManager(state_dir=temp_dir / ".state", atomic_root=temp_dir)

        tasks = state.get_phase_tasks("nonexistent-phase")
        assert tasks == {}

    def test_get_nonexistent_task_status(self, temp_dir):
        """Test getting status of nonexistent task."""
        state = StateManager(state_dir=temp_dir / ".state", atomic_root=temp_dir)

        status = state.get_task_status("0-setup", "999")
        assert status == "pending"

    def test_empty_artifacts_list(self, temp_dir):
        """Test marking task complete with empty artifacts list."""
        state = StateManager(state_dir=temp_dir / ".state", atomic_root=temp_dir)

        state.mark_task_complete("0-setup", "001", "Task 1", artifacts=[])

        tasks = state.get_phase_tasks("0-setup")
        assert tasks["001"]["artifacts"] == []
