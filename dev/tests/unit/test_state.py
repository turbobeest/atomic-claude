"""
Unit Tests for State Management System

Comprehensive tests for core/state.py covering:
- State loading/saving
- Task state tracking
- Phase state tracking
- Transactions (commit/rollback)
- Snapshots and restore
- Concurrent access (file locking)
- State migration
- Atomic writes

Requirements: 25+ tests with 95%+ coverage
"""

import pytest
import json
import os
import time
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

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
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_state_dir(tmp_path):
    """Create temporary state directory."""
    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    return state_dir


@pytest.fixture
def state_manager(temp_state_dir):
    """Create StateManager instance."""
    return StateManager(state_dir=temp_state_dir, atomic_root=temp_state_dir.parent)


@pytest.fixture
def populated_state(state_manager):
    """Create populated state for testing."""
    state_manager.set_current_phase("0-setup")
    state_manager.mark_task_complete("0-setup", "001", "Mode Selection")
    state_manager.mark_task_complete("0-setup", "002", "Config Collection")
    state_manager.mark_task_failed("0-setup", "003", "Config Display", "Test error")
    return state_manager


# ============================================================================
# STATE MANAGER INITIALIZATION
# ============================================================================

class TestStateManagerInit:
    """Test StateManager initialization."""

    def test_init_creates_directories(self, temp_state_dir):
        """Test initialization creates required directories."""
        state_manager = StateManager(state_dir=temp_state_dir)

        assert state_manager.state_dir.exists()
        assert state_manager.snapshots_dir.exists()

    def test_init_creates_empty_state(self, temp_state_dir):
        """Test initialization creates empty state file."""
        state_manager = StateManager(state_dir=temp_state_dir)

        assert state_manager.state_file.exists()

        with open(state_manager.state_file) as f:
            state = json.load(f)

        assert state['version'] == StateManager.STATE_VERSION
        assert state['phases'] == {}
        assert state['current_phase'] is None

    def test_init_loads_existing_state(self, temp_state_dir):
        """Test initialization loads existing state file."""
        # Create existing state
        state_file = temp_state_dir / "task-state.json"
        state_data = {
            'version': '2.0',
            'current_phase': '0-setup',
            'phases': {
                '0-setup': {
                    'started_at': '2024-01-01T00:00:00',
                    'tasks': {
                        '001': {'name': 'Task', 'status': 'completed'}
                    }
                }
            },
            'metadata': {'created_at': '2024-01-01T00:00:00'}
        }

        with open(state_file, 'w') as f:
            json.dump(state_data, f)

        # Load
        state_manager = StateManager(state_dir=temp_state_dir)

        assert state_manager.get_current_phase() == '0-setup'
        assert state_manager.is_task_complete('0-setup', '001')


# ============================================================================
# STATE LOADING & SAVING
# ============================================================================

class TestStateLoadingSaving:
    """Test state loading and saving."""

    def test_save_state_atomic(self, state_manager):
        """Test state saving is atomic (temp + rename)."""
        state_manager.set_current_phase("0-setup")
        state_manager.save_state()

        assert state_manager.state_file.exists()

        # Verify no temp files left
        temp_files = list(state_manager.state_dir.glob(".state-*.tmp"))
        assert len(temp_files) == 0

    def test_save_state_valid_json(self, state_manager):
        """Test saved state is valid JSON."""
        state_manager.set_current_phase("0-setup")
        state_manager.mark_task_complete("0-setup", "001", "Task")
        state_manager.save_state()

        with open(state_manager.state_file) as f:
            state = json.load(f)  # Should not raise

        assert isinstance(state, dict)

    def test_load_state_invalid_json(self, temp_state_dir):
        """Test loading with invalid JSON falls back to empty state."""
        state_file = temp_state_dir / "task-state.json"
        state_file.write_text("{invalid json")

        state_manager = StateManager(state_dir=temp_state_dir)

        # Should create empty state
        assert state_manager.get_current_phase() is None
        assert len(state_manager._state['phases']) == 0

    def test_load_state_migration(self, temp_state_dir):
        """Test state migration from v1.0 to v2.0."""
        # Create v1.0 state
        state_file = temp_state_dir / "task-state.json"
        v1_state = {
            'version': '1.0',
            'current_phase': '0-setup',
            'phases': {
                '0-setup': {
                    'tasks': {
                        '001': {'name': 'Task', 'status': 'complete'}  # Old format
                    }
                }
            }
        }

        with open(state_file, 'w') as f:
            json.dump(v1_state, f)

        # Load and migrate
        state_manager = StateManager(state_dir=temp_state_dir)

        # Should be migrated to v2.0
        assert state_manager._state['version'] == '2.0'

        # Status should be normalized
        task = state_manager._state['phases']['0-setup']['tasks']['001']
        assert task['status'] == 'completed'  # Normalized from 'complete'

        # Metadata should be added
        assert 'metadata' in state_manager._state


# ============================================================================
# STATE QUERIES
# ============================================================================

class TestStateQueries:
    """Test state query methods."""

    def test_is_task_complete(self, populated_state):
        """Test checking if task is complete."""
        assert populated_state.is_task_complete('0-setup', '001') is True
        assert populated_state.is_task_complete('0-setup', '002') is True
        assert populated_state.is_task_complete('0-setup', '003') is False  # Failed
        assert populated_state.is_task_complete('0-setup', '999') is False  # Not started

    def test_is_task_failed(self, populated_state):
        """Test checking if task failed."""
        assert populated_state.is_task_failed('0-setup', '003') is True
        assert populated_state.is_task_failed('0-setup', '001') is False

    def test_get_task_status(self, populated_state):
        """Test getting task status."""
        assert populated_state.get_task_status('0-setup', '001') == 'completed'
        assert populated_state.get_task_status('0-setup', '003') == 'failed'
        assert populated_state.get_task_status('0-setup', '999') == 'pending'

    def test_get_current_phase(self, populated_state):
        """Test getting current phase."""
        assert populated_state.get_current_phase() == '0-setup'

    def test_get_current_task(self, state_manager):
        """Test getting current task."""
        state_manager.set_current_task('001')
        assert state_manager.get_current_task() == '001'

    def test_get_phase_tasks(self, populated_state):
        """Test getting all phase tasks."""
        tasks = populated_state.get_phase_tasks('0-setup')

        assert len(tasks) == 3
        assert '001' in tasks
        assert '002' in tasks
        assert '003' in tasks

    def test_get_completed_tasks(self, populated_state):
        """Test getting completed tasks list."""
        completed = populated_state.get_completed_tasks('0-setup')

        assert len(completed) == 2
        assert '001' in completed
        assert '002' in completed
        assert '003' not in completed  # Failed, not completed


# ============================================================================
# STATE MUTATIONS
# ============================================================================

class TestStateMutations:
    """Test state mutation methods."""

    def test_mark_task_complete(self, state_manager):
        """Test marking task as complete."""
        state_manager.set_current_phase('0-setup')
        state_manager.mark_task_complete('0-setup', '001', 'Test Task')

        assert state_manager.is_task_complete('0-setup', '001')

        task = state_manager.get_phase_tasks('0-setup')['001']
        assert task['name'] == 'Test Task'
        assert task['status'] == 'completed'
        assert 'completed_at' in task

    def test_mark_task_complete_with_artifacts(self, state_manager):
        """Test marking task complete with artifacts."""
        artifacts = ['output1.json', 'output2.md']
        state_manager.mark_task_complete('0-setup', '001', 'Task', artifacts=artifacts)

        task = state_manager.get_phase_tasks('0-setup')['001']
        assert task['artifacts'] == artifacts

    def test_mark_task_failed(self, state_manager):
        """Test marking task as failed."""
        state_manager.mark_task_failed('0-setup', '001', 'Task', 'Error message')

        assert state_manager.is_task_failed('0-setup', '001')

        task = state_manager.get_phase_tasks('0-setup')['001']
        assert task['status'] == 'failed'
        assert task['error'] == 'Error message'
        assert 'failed_at' in task

    def test_set_current_phase(self, state_manager):
        """Test setting current phase."""
        state_manager.set_current_phase('1-discovery')
        assert state_manager.get_current_phase() == '1-discovery'

    def test_set_current_task(self, state_manager):
        """Test setting current task."""
        state_manager.set_current_task('001')
        assert state_manager.get_current_task() == '001'

    def test_mark_phase_complete(self, state_manager):
        """Test marking phase as complete."""
        state_manager.set_current_phase('0-setup')
        state_manager.mark_phase_complete('0-setup')

        phase = state_manager._state['phases']['0-setup']
        assert phase['status'] == 'completed'
        assert 'completed_at' in phase

    def test_reset_all(self, populated_state):
        """Test resetting all state."""
        populated_state.reset_all()

        assert populated_state.get_current_phase() is None
        assert len(populated_state._state['phases']) == 0

    def test_reset_phase(self, populated_state):
        """Test resetting specific phase."""
        populated_state.reset_phase('0-setup')

        assert '0-setup' not in populated_state._state['phases']


# ============================================================================
# TRANSACTIONS
# ============================================================================

class TestTransactions:
    """Test transaction support."""

    def test_transaction_commit(self, state_manager):
        """Test successful transaction commit."""
        with state_manager.begin_transaction() as txn:
            txn.mark_task_complete('0-setup', '001', 'Task')

        # Changes should be persisted
        assert state_manager.is_task_complete('0-setup', '001')

    def test_transaction_rollback(self, state_manager):
        """Test transaction rollback on exception."""
        # Create initial state
        state_manager.mark_task_complete('0-setup', '001', 'Task 1')

        # Capture the initial state
        initial_completed = state_manager.get_completed_tasks('0-setup')
        assert '001' in initial_completed

        try:
            with state_manager.begin_transaction() as txn:
                txn.mark_task_complete('0-setup', '002', 'Task 2')
                # Verify task 2 is marked (changes are immediate within transaction)
                assert state_manager.is_task_complete('0-setup', '002')
                raise Exception("Simulated error")
        except Exception:
            pass

        # After rollback, should restore to pre-transaction state
        # Task 1 should still be complete
        assert state_manager.is_task_complete('0-setup', '001')

        # Task 2 should be rolled back
        assert state_manager.is_task_complete('0-setup', '002') is False

    def test_transaction_set_phase(self, state_manager):
        """Test setting phase within transaction."""
        with state_manager.begin_transaction() as txn:
            txn.set_current_phase('0-setup')

        assert state_manager.get_current_phase() == '0-setup'

    def test_transaction_mark_failed(self, state_manager):
        """Test marking task failed within transaction."""
        with state_manager.begin_transaction() as txn:
            txn.mark_task_failed('0-setup', '001', 'Task', 'Error')

        assert state_manager.is_task_failed('0-setup', '001')


# ============================================================================
# SNAPSHOTS
# ============================================================================

class TestSnapshots:
    """Test snapshot and restore functionality."""

    def test_create_snapshot(self, populated_state):
        """Test creating state snapshot."""
        snapshot = populated_state.snapshot()

        assert isinstance(snapshot, StateSnapshot)
        assert snapshot.version == StateManager.STATE_VERSION
        assert snapshot.current_phase == '0-setup'
        assert len(snapshot.phases) > 0

    def test_restore_snapshot(self, populated_state):
        """Test restoring from snapshot."""
        # Create snapshot
        snapshot = populated_state.snapshot()

        # Make changes
        populated_state.mark_task_complete('0-setup', '004', 'New Task')

        # Restore
        populated_state.restore(snapshot)

        # Task 004 should be gone
        assert populated_state.is_task_complete('0-setup', '004') is False

        # Original tasks should be restored
        assert populated_state.is_task_complete('0-setup', '001') is True

    def test_save_snapshot(self, populated_state):
        """Test saving snapshot to disk."""
        snapshot_file = populated_state.save_snapshot('test_snapshot')

        assert snapshot_file.exists()
        assert snapshot_file.name == 'test_snapshot.json'

        with open(snapshot_file) as f:
            data = json.load(f)

        assert data['version'] == StateManager.STATE_VERSION

    def test_load_snapshot(self, populated_state):
        """Test loading snapshot from disk."""
        # Save snapshot
        snapshot_file = populated_state.save_snapshot('test')

        # Make changes
        populated_state.mark_task_complete('0-setup', '004', 'New')

        # Load snapshot
        populated_state.load_snapshot(snapshot_file)

        # Should be restored
        assert populated_state.is_task_complete('0-setup', '004') is False


# ============================================================================
# FILE LOCKING
# ============================================================================

class TestFileLocking:
    """Test concurrent access via file locking."""

    def test_lock_acquire_release(self, temp_state_dir):
        """Test basic lock acquire/release."""
        lock_file = temp_state_dir / "test.lock"
        lock = StateLock(lock_file)

        assert lock.acquire() is True
        lock.release()

        assert not lock_file.exists()

    def test_lock_context_manager(self, temp_state_dir):
        """Test lock as context manager."""
        lock_file = temp_state_dir / "test.lock"

        with StateLock(lock_file) as lock:
            assert lock_file.exists()

        assert not lock_file.exists()

    def test_lock_prevents_concurrent_access(self, temp_state_dir):
        """Test lock prevents concurrent access."""
        lock_file = temp_state_dir / "test.lock"
        lock1 = StateLock(lock_file)

        assert lock1.acquire() is True

        # Second lock should fail
        lock2 = StateLock(lock_file)
        assert lock2.acquire() is False

        lock1.release()

        # Now should succeed
        assert lock2.acquire() is True
        lock2.release()


# ============================================================================
# TASK RUNNING CONTEXT
# ============================================================================

class TestTaskRunningContext:
    """Test task_running context manager."""

    def test_task_running_creates_file(self, temp_state_dir):
        """Test task_running creates current-task.json."""
        current_task_file = temp_state_dir / "current-task.json"

        with task_running('0-setup', '001', 'Test Task', state_dir=temp_state_dir):
            assert current_task_file.exists()

            with open(current_task_file) as f:
                data = json.load(f)

            assert data['phase'] == '0-setup'
            assert data['task'] == '001'
            assert data['name'] == 'Test Task'
            assert data['status'] == 'running'

        # File should be cleaned up
        assert not current_task_file.exists()

    def test_task_running_cleanup_on_exception(self, temp_state_dir):
        """Test task_running cleans up even on exception."""
        current_task_file = temp_state_dir / "current-task.json"

        try:
            with task_running('0-setup', '001', 'Task', state_dir=temp_state_dir):
                raise Exception("Test error")
        except Exception:
            pass

        # File should still be cleaned up
        assert not current_task_file.exists()


# ============================================================================
# DATA CLASSES
# ============================================================================

class TestDataClasses:
    """Test data classes."""

    def test_task_state_creation(self):
        """Test TaskState creation."""
        task = TaskState(
            task_id='001',
            name='Test Task',
            status=TaskStatus.COMPLETED
        )

        assert task.task_id == '001'
        assert task.name == 'Test Task'
        assert task.status == TaskStatus.COMPLETED

    def test_task_state_to_dict(self):
        """Test TaskState serialization."""
        task = TaskState(
            task_id='001',
            name='Test',
            status=TaskStatus.COMPLETED,
            artifacts=['file.txt']
        )

        task_dict = task.to_dict()

        assert task_dict['status'] == 'completed'
        assert task_dict['artifacts'] == ['file.txt']

    def test_phase_state_creation(self):
        """Test PhaseState creation."""
        phase = PhaseState(
            phase_id='0-setup',
            status=PhaseStatus.IN_PROGRESS,
            tasks={}
        )

        assert phase.phase_id == '0-setup'
        assert phase.status == PhaseStatus.IN_PROGRESS

    def test_snapshot_to_dict(self):
        """Test StateSnapshot serialization."""
        phases = {
            '0-setup': PhaseState(
                phase_id='0-setup',
                status=PhaseStatus.IN_PROGRESS,
                tasks={}
            )
        }

        snapshot = StateSnapshot(
            timestamp=datetime.now().isoformat(),
            version='2.0',
            phases=phases,
            current_phase='0-setup',
            current_task=None,
            metadata={}
        )

        snapshot_dict = snapshot.to_dict()

        assert snapshot_dict['version'] == '2.0'
        assert '0-setup' in snapshot_dict['phases']


# ============================================================================
# DISPLAY & UTILITIES
# ============================================================================

class TestDisplayUtilities:
    """Test display and utility methods."""

    def test_display_status_empty(self, state_manager, capsys):
        """Test display_status with empty state."""
        state_manager.display_status()

        captured = capsys.readouterr()
        assert "No phases started yet" in captured.out

    def test_display_status_populated(self, populated_state, capsys):
        """Test display_status with populated state."""
        populated_state.display_status()

        captured = capsys.readouterr()
        assert "0-setup" in captured.out
        assert "Mode Selection" in captured.out


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Test performance requirements."""

    def test_state_operations_performance(self, state_manager):
        """Test state operations complete in < 5ms."""
        import time

        operations = [
            lambda: state_manager.is_task_complete('0-setup', '001'),
            lambda: state_manager.get_current_phase(),
            lambda: state_manager.get_phase_tasks('0-setup'),
        ]

        for op in operations:
            start = time.time()
            for _ in range(100):
                op()
            duration_ms = (time.time() - start) * 1000 / 100

            assert duration_ms < 5, f"Operation took {duration_ms:.2f}ms (target: <5ms)"

    def test_save_state_performance(self, populated_state):
        """Test state saving completes quickly."""
        import time

        start = time.time()
        for _ in range(10):
            populated_state.save_state()
        duration_ms = (time.time() - start) * 1000 / 10

        # Should save in < 10ms
        assert duration_ms < 10, f"Save took {duration_ms:.2f}ms (target: <10ms)"


# ============================================================================
# CONCURRENT ACCESS TESTS
# ============================================================================

class TestConcurrentAccess:
    """Test concurrent access scenarios."""

    def test_multiple_threads_access(self, state_manager):
        """Test multiple threads can access state safely."""
        def mark_task(task_id):
            state_manager.mark_task_complete('0-setup', task_id, f'Task {task_id}')

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(mark_task, f'{i:03d}') for i in range(1, 11)]
            for future in futures:
                future.result()

        # All tasks should be marked
        completed = state_manager.get_completed_tasks('0-setup')
        assert len(completed) == 10


# ============================================================================
# EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_mark_task_complete_creates_phase(self, state_manager):
        """Test marking task complete creates phase if missing."""
        state_manager.mark_task_complete('new-phase', '001', 'Task')

        assert 'new-phase' in state_manager._state['phases']
        assert state_manager.is_task_complete('new-phase', '001')

    def test_query_nonexistent_phase(self, state_manager):
        """Test querying nonexistent phase returns defaults."""
        assert state_manager.is_task_complete('nonexistent', '001') is False
        assert state_manager.get_phase_tasks('nonexistent') == {}

    def test_status_normalization(self):
        """Test status normalization (complete -> completed)."""
        task = TaskState(task_id='001', name='Task', status='complete')
        assert task.status == TaskStatus.COMPLETED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
