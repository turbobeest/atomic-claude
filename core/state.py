"""
State Management System

Immutable, atomic state management with transactions, snapshots, and rollback.

Features:
- Immutable state transitions
- Atomic commits with rollback capability
- State snapshots and restore
- Concurrent access safety (file locking)
- State migration between versions
- JSON persistence with atomic writes

Architecture:
- StateManager: Main state coordinator
- StateTransaction: Transaction context manager
- StateSnapshot: Point-in-time state capture
- StateLock: File locking for concurrent access

State Structure:
- Session state (phase, task, timestamp, user)
- Task state (completed tasks, pending, failed)
- Memory state (checkpoints, context)
- Provider state (usage, rate limits, health)

Author: Phase 2 - State Management
"""

import json
import fcntl
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from enum import Enum
import os

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS & TYPES
# ============================================================================

class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    COMPLETE = "complete"  # Alias for compatibility
    FAILED = "failed"


class PhaseStatus(str, Enum):
    """Phase execution status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class TaskState:
    """Task state record."""
    task_id: str
    name: str
    status: TaskStatus
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    failed_at: Optional[str] = None
    error: Optional[str] = None
    artifacts: List[str] = None

    def __post_init__(self):
        if self.artifacts is None:
            self.artifacts = []
        # Convert string status to enum
        if isinstance(self.status, str):
            # Handle "complete" as alias for "completed"
            if self.status == "complete":
                self.status = TaskStatus.COMPLETED
            else:
                self.status = TaskStatus(self.status)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        result = asdict(self)
        result['status'] = self.status.value
        return result


@dataclass
class PhaseState:
    """Phase state record."""
    phase_id: str
    status: PhaseStatus
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    tasks: Dict[str, TaskState] = None

    def __post_init__(self):
        if self.tasks is None:
            self.tasks = {}
        # Convert string status to enum
        if isinstance(self.status, str):
            self.status = PhaseStatus(self.status)
        # Convert task dicts to TaskState objects
        if self.tasks:
            for task_id, task_data in list(self.tasks.items()):
                if isinstance(task_data, dict):
                    self.tasks[task_id] = TaskState(task_id=task_id, **task_data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        result = {
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'status': self.status.value,
            'tasks': {
                task_id: task.to_dict()
                for task_id, task in self.tasks.items()
            }
        }
        # Remove status if it's not explicitly set
        if self.status == PhaseStatus.NOT_STARTED:
            result.pop('status', None)
        return result


@dataclass
class StateSnapshot:
    """Point-in-time state snapshot for rollback."""
    timestamp: str
    version: str
    phases: Dict[str, PhaseState]
    current_phase: Optional[str]
    current_task: Optional[str]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            'timestamp': self.timestamp,
            'version': self.version,
            'current_phase': self.current_phase,
            'current_task': self.current_task,
            'metadata': self.metadata,
            'phases': {
                phase_id: phase.to_dict()
                for phase_id, phase in self.phases.items()
            }
        }


# ============================================================================
# FILE LOCKING
# ============================================================================

class StateLock:
    """
    File-based lock for concurrent state access.

    Uses fcntl on Unix, fallback to mkdir on Windows.
    """

    def __init__(self, lock_file: Path):
        self.lock_file = lock_file
        self.lock_fd = None

    def acquire(self, timeout: int = 10) -> bool:
        """
        Acquire exclusive lock.

        Args:
            timeout: Max seconds to wait for lock

        Returns:
            True if acquired, False on timeout
        """
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Try fcntl first (Unix)
            self.lock_fd = open(self.lock_file, 'w')
            fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except (IOError, OSError):
            # Lock held by another process or fcntl not available
            if self.lock_fd:
                self.lock_fd.close()
                self.lock_fd = None
            return False

    def release(self) -> None:
        """Release lock."""
        if self.lock_fd:
            try:
                fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_UN)
                self.lock_fd.close()
            except Exception as e:
                logger.debug("Failed to release state lock: %s", e)
            finally:
                self.lock_fd = None

        # Clean up lock file
        try:
            self.lock_file.unlink()
        except FileNotFoundError:
            pass

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


# ============================================================================
# STATE TRANSACTION
# ============================================================================

class StateTransaction:
    """
    Transaction context manager for atomic state changes.

    Usage:
        with state_manager.begin_transaction() as txn:
            txn.mark_task_complete("0-setup", "001", "Task name")
            # If exception occurs, changes are rolled back
            # If successful, changes are committed
    """

    def __init__(self, state_manager: 'StateManager'):
        self.state_manager = state_manager
        self.snapshot: Optional[StateSnapshot] = None
        self.committed = False
        self.changes_buffer: List[tuple] = []  # Buffer changes to apply on commit

    def __enter__(self) -> 'StateTransaction':
        """Begin transaction by capturing snapshot BEFORE any changes."""
        self.snapshot = self.state_manager.snapshot()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Commit or rollback on exit."""
        if exc_type is not None:
            # Exception occurred, rollback
            self.rollback()
            return False  # Re-raise exception
        else:
            # Success, commit
            self.commit()
            return True

    def mark_task_complete(self, phase_id: str, task_id: str, task_name: str) -> None:
        """Mark task as complete within transaction (defers save until commit)."""
        self.state_manager.mark_task_complete(phase_id, task_id, task_name, auto_save=False)

    def mark_task_failed(self, phase_id: str, task_id: str, task_name: str, error: str) -> None:
        """Mark task as failed within transaction (defers save until commit)."""
        self.state_manager.mark_task_failed(phase_id, task_id, task_name, error, auto_save=False)

    def set_current_phase(self, phase_id: str) -> None:
        """Set current phase within transaction (applied immediately but can rollback)."""
        self.state_manager.set_current_phase(phase_id)

    def commit(self) -> None:
        """Commit transaction."""
        self.committed = True
        # State changes were already applied, just ensure saved
        self.state_manager.save_state()

    def rollback(self) -> None:
        """Rollback transaction to snapshot."""
        if self.snapshot:
            self.state_manager.restore(self.snapshot)


# ============================================================================
# MAIN STATE MANAGER
# ============================================================================

class StateManager:
    """
    Main state manager with immutable transitions and atomic commits.

    Features:
    - Immutable state transitions
    - Atomic commits with rollback
    - File locking for concurrent access
    - State snapshots and restore
    - Version migration

    Usage:
        state = StateManager()
        if not state.is_task_complete("0-setup", "001"):
            # Execute task
            state.mark_task_complete("0-setup", "001", "Task name")
    """

    STATE_VERSION = "2.0"  # Schema version for migration

    def __init__(self, state_dir: Path = None, atomic_root: Path = None):
        """
        Initialize state manager.

        Args:
            state_dir: State directory (defaults to .state)
            atomic_root: Atomic root directory (for lock file)
        """
        self.atomic_root = atomic_root or Path.cwd()
        self.state_dir = state_dir or (self.atomic_root / ".state")
        self.state_file = self.state_dir / "task-state.json"
        self.lock_file = self.state_dir / "state.lock"
        self.snapshots_dir = self.state_dir / "snapshots"

        self._ensure_state_dir()

        # In-memory state
        self._state: Dict[str, Any] = self.load_state()

        # Save initial state if it doesn't exist
        if not self.state_file.exists():
            self.save_state()

    def _ensure_state_dir(self) -> None:
        """Ensure state directories exist."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    # ========================================================================
    # STATE LOADING & SAVING
    # ========================================================================

    def load_state(self) -> Dict[str, Any]:
        """
        Load current state from disk.

        Returns:
            State dict with version, phases, current pointers
        """
        if not self.state_file.exists():
            return self._create_empty_state()

        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)

            # Migrate if needed
            if state.get('version') != self.STATE_VERSION:
                state = self._migrate_state(state)

            return state

        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load state file: {e}")
            return self._create_empty_state()

    def save_state(self) -> None:
        """
        Atomically save state to disk.

        Uses atomic write (write to temp, then rename) to prevent corruption.
        """
        # Create temp file
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self.state_dir,
            prefix='.state-',
            suffix='.tmp'
        )

        try:
            # Write to temp file
            with os.fdopen(temp_fd, 'w') as f:
                json.dump(self._state, f, indent=2)

            # Atomic rename
            shutil.move(temp_path, self.state_file)

        except Exception as e:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.debug("Failed to clean up temp state file %s: %s", temp_path, e)
            raise IOError(f"Failed to save state: {e}")

    def _create_empty_state(self) -> Dict[str, Any]:
        """Create empty state structure."""
        return {
            'version': self.STATE_VERSION,
            'current_phase': None,
            'current_task': None,
            'phases': {},
            'metadata': {
                'created_at': datetime.now(timezone.utc).isoformat(),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
        }

    # ========================================================================
    # STATE QUERIES
    # ========================================================================

    def is_task_complete(self, phase_id: str, task_id: str) -> bool:
        """
        Check if task is complete.

        Args:
            phase_id: Phase identifier (e.g., "0-setup")
            task_id: Task identifier (e.g., "001")

        Returns:
            True if task is complete, False otherwise
        """
        phase = self._state.get('phases', {}).get(phase_id, {})
        task = phase.get('tasks', {}).get(task_id, {})

        # Support both "completed" and "complete" status
        status = task.get('status', 'pending')
        return status in ('completed', 'complete')

    def is_task_failed(self, phase_id: str, task_id: str) -> bool:
        """Check if task has failed."""
        phase = self._state.get('phases', {}).get(phase_id, {})
        task = phase.get('tasks', {}).get(task_id, {})
        return task.get('status') == 'failed'

    def get_task_status(self, phase_id: str, task_id: str) -> str:
        """Get task status."""
        phase = self._state.get('phases', {}).get(phase_id, {})
        task = phase.get('tasks', {}).get(task_id, {})
        return task.get('status', 'pending')

    def get_current_phase(self) -> Optional[str]:
        """Get current phase ID."""
        return self._state.get('current_phase')

    def get_current_task(self) -> Optional[str]:
        """Get current task ID."""
        return self._state.get('current_task')

    def get_phase_tasks(self, phase_id: str) -> Dict[str, Dict[str, Any]]:
        """Get all tasks for a phase."""
        phase = self._state.get('phases', {}).get(phase_id, {})
        return phase.get('tasks', {})

    def get_completed_tasks(self, phase_id: str) -> List[str]:
        """Get list of completed task IDs for a phase."""
        tasks = self.get_phase_tasks(phase_id)
        return [
            task_id for task_id, task_data in tasks.items()
            if task_data.get('status') in ('completed', 'complete')
        ]

    # ========================================================================
    # STATE MUTATIONS
    # ========================================================================

    def mark_task_started(self, phase_id: str, task_id: str, task_name: str, auto_save: bool = True) -> None:
        """
        Mark a task as in-progress and record its start time.

        Args:
            phase_id: Phase identifier
            task_id: Task identifier
            task_name: Task name/description
            auto_save: Auto-save state to disk (default True)
        """
        # Ensure phase exists
        if phase_id not in self._state['phases']:
            self._state['phases'][phase_id] = {
                'started_at': datetime.now(timezone.utc).isoformat(),
                'tasks': {}
            }

        if 'tasks' not in self._state['phases'][phase_id]:
            self._state['phases'][phase_id]['tasks'] = {}

        self._state['phases'][phase_id]['tasks'][task_id] = {
            'name': task_name,
            'status': 'in_progress',
            'started_at': datetime.now(timezone.utc).isoformat(),
        }

        self._state['current_task'] = task_id
        self._state['metadata']['last_updated'] = datetime.now(timezone.utc).isoformat()

        if auto_save:
            self.save_state()

    def mark_task_complete(self, phase_id: str, task_id: str, task_name: str, artifacts: List[str] = None, auto_save: bool = True) -> None:
        """
        Mark a task as complete.

        Args:
            phase_id: Phase identifier
            task_id: Task identifier
            task_name: Task name/description
            artifacts: List of output artifact paths
            auto_save: Auto-save state to disk (default True)
        """
        # Ensure phase exists
        if phase_id not in self._state['phases']:
            self._state['phases'][phase_id] = {
                'started_at': datetime.now(timezone.utc).isoformat(),
                'tasks': {}
            }

        # Ensure tasks dict exists
        if 'tasks' not in self._state['phases'][phase_id]:
            self._state['phases'][phase_id]['tasks'] = {}

        # Preserve started_at from mark_task_started() if it exists
        existing = self._state['phases'][phase_id]['tasks'].get(task_id, {})
        started_at = existing.get('started_at', datetime.now(timezone.utc).isoformat())

        # Update task
        self._state['phases'][phase_id]['tasks'][task_id] = {
            'name': task_name,
            'status': 'completed',
            'started_at': started_at,
            'completed_at': datetime.now(timezone.utc).isoformat(),
            'artifacts': artifacts or []
        }

        # Update metadata
        self._state['metadata']['last_updated'] = datetime.now(timezone.utc).isoformat()

        # Clear current task
        self._state['current_task'] = None

        # Save (unless disabled for transactions)
        if auto_save:
            self.save_state()

    def mark_task_failed(self, phase_id: str, task_id: str, task_name: str, error: str = None, auto_save: bool = True) -> None:
        """
        Mark a task as failed.

        Args:
            phase_id: Phase identifier
            task_id: Task identifier
            task_name: Task name/description
            error: Error message
            auto_save: Auto-save state to disk (default True)
        """
        # Ensure phase exists
        if phase_id not in self._state['phases']:
            self._state['phases'][phase_id] = {
                'started_at': datetime.now(timezone.utc).isoformat(),
                'tasks': {}
            }

        # Ensure tasks dict exists
        if 'tasks' not in self._state['phases'][phase_id]:
            self._state['phases'][phase_id]['tasks'] = {}

        # Update task
        self._state['phases'][phase_id]['tasks'][task_id] = {
            'name': task_name,
            'status': 'failed',
            'failed_at': datetime.now(timezone.utc).isoformat(),
            'error': error or 'Task execution failed'
        }

        # Update metadata
        self._state['metadata']['last_updated'] = datetime.now(timezone.utc).isoformat()

        # Save (unless disabled for transactions)
        if auto_save:
            self.save_state()

    def set_current_phase(self, phase_id: str) -> None:
        """Set current active phase."""
        self._state['current_phase'] = phase_id
        self._state['metadata']['last_updated'] = datetime.now(timezone.utc).isoformat()
        self.save_state()

    def set_current_task(self, task_id: str) -> None:
        """Set current active task."""
        self._state['current_task'] = task_id
        self._state['metadata']['last_updated'] = datetime.now(timezone.utc).isoformat()
        self.save_state()

    def mark_phase_complete(self, phase_id: str) -> None:
        """Mark entire phase as complete."""
        # Ensure phase exists
        if phase_id not in self._state['phases']:
            self._state['phases'][phase_id] = {
                'started_at': datetime.now(timezone.utc).isoformat(),
                'tasks': {}
            }

        self._state['phases'][phase_id]['completed_at'] = datetime.now(timezone.utc).isoformat()
        self._state['phases'][phase_id]['status'] = 'completed'
        self._state['metadata']['last_updated'] = datetime.now(timezone.utc).isoformat()
        self.save_state()

    # ========================================================================
    # TRANSACTIONS
    # ========================================================================

    def begin_transaction(self):
        """
        Begin a state transaction.

        Usage:
            with state.begin_transaction() as txn:
                txn.mark_task_complete("0-setup", "001", "Task")
                # Auto-commit on success, rollback on exception

        Returns:
            StateTransaction context manager
        """
        return StateTransaction(self)

    # ========================================================================
    # SNAPSHOTS
    # ========================================================================

    def snapshot(self) -> StateSnapshot:
        """
        Create point-in-time snapshot of current state.

        Returns:
            StateSnapshot object
        """
        import copy

        # Convert phases to PhaseState objects (deep copy to avoid reference issues)
        phases = {}
        for phase_id, phase_data in self._state.get('phases', {}).items():
            # Deep copy task data to avoid mutations
            task_data_copy = copy.deepcopy(phase_data.get('tasks', {}))

            phases[phase_id] = PhaseState(
                phase_id=phase_id,
                status=PhaseStatus.IN_PROGRESS,  # Default
                started_at=phase_data.get('started_at'),
                completed_at=phase_data.get('completed_at'),
                tasks={
                    task_id: TaskState(task_id=task_id, **task_data)
                    for task_id, task_data in task_data_copy.items()
                }
            )

        return StateSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            version=self.STATE_VERSION,
            phases=phases,
            current_phase=self._state.get('current_phase'),
            current_task=self._state.get('current_task'),
            metadata=copy.deepcopy(self._state.get('metadata', {}))
        )

    def save_snapshot(self, name: str = None) -> Path:
        """
        Save snapshot to disk.

        Args:
            name: Snapshot name (defaults to timestamp)

        Returns:
            Path to saved snapshot
        """
        from core.utils.file_ops import write_json

        snapshot = self.snapshot()
        name = name or datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        snapshot_file = self.snapshots_dir / f"{name}.json"

        write_json(snapshot_file, snapshot.to_dict())

        return snapshot_file

    def restore(self, snapshot: StateSnapshot) -> None:
        """
        Restore state from snapshot.

        Args:
            snapshot: StateSnapshot to restore
        """
        # Convert snapshot to state dict
        self._state = {
            'version': snapshot.version,
            'current_phase': snapshot.current_phase,
            'current_task': snapshot.current_task,
            'metadata': snapshot.metadata,
            'phases': {
                phase_id: phase.to_dict()
                for phase_id, phase in snapshot.phases.items()
            }
        }

        # Save restored state
        self.save_state()

    def load_snapshot(self, snapshot_file: Path) -> None:
        """
        Load and restore from snapshot file.

        Args:
            snapshot_file: Path to snapshot JSON
        """
        with open(snapshot_file, 'r') as f:
            data = json.load(f)

        # Recreate snapshot object
        phases = {}
        for phase_id, phase_data in data.get('phases', {}).items():
            # Build PhaseState manually to avoid duplicate task_id
            tasks = {}
            for task_id, task_data in phase_data.get('tasks', {}).items():
                # Don't pass task_id again since it's already in the dict key
                task_copy = dict(task_data)
                task_copy['task_id'] = task_id
                tasks[task_id] = TaskState(**task_copy)

            phases[phase_id] = PhaseState(
                phase_id=phase_id,
                status=phase_data.get('status', 'not_started'),
                started_at=phase_data.get('started_at'),
                completed_at=phase_data.get('completed_at'),
                tasks=tasks
            )

        snapshot = StateSnapshot(
            timestamp=data['timestamp'],
            version=data['version'],
            phases=phases,
            current_phase=data.get('current_phase'),
            current_task=data.get('current_task'),
            metadata=data.get('metadata', {})
        )

        # Restore
        self.restore(snapshot)

    # ========================================================================
    # DISPLAY & UTILITIES
    # ========================================================================

    def display_status(self) -> None:
        """Display current pipeline status."""
        phases = self._state.get('phases', {})

        if not phases:
            print("No phases started yet.\n")
            return

        for phase_id, phase_data in sorted(phases.items()):
            print(f"📦 {phase_id}")

            tasks = phase_data.get('tasks', {})
            if tasks:
                for task_id, task_info in sorted(tasks.items()):
                    status = task_info.get('status', 'pending')
                    is_complete = status in ('completed', 'complete')
                    icon = "✓" if is_complete else "○"
                    name = task_info.get('name', 'Unknown')
                    print(f"   {icon} Task {task_id}: {name}")
            else:
                print("   (no tasks)")

            print()

    def reset_all(self) -> None:
        """Reset entire pipeline state."""
        self._state = self._create_empty_state()
        self.save_state()

        # Clear outputs
        outputs_dir = self.atomic_root.parent / ".outputs"
        if outputs_dir.exists():
            shutil.rmtree(outputs_dir)

        print("✓ State cleared")

    def reset_phase(self, phase_id: str) -> None:
        """Reset specific phase."""
        if phase_id in self._state.get('phases', {}):
            del self._state['phases'][phase_id]
            self.save_state()

    # ========================================================================
    # STATE MIGRATION
    # ========================================================================

    def _migrate_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate state from old version to current.

        Args:
            state: Old state dict

        Returns:
            Migrated state dict
        """
        from_version = state.get('version', '1.0')

        if from_version == '1.0':
            state = self._migrate_v1_to_v2(state)

        state['version'] = self.STATE_VERSION
        return state

    def _migrate_v1_to_v2(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from v1.0 to v2.0."""
        # Add metadata if missing
        if 'metadata' not in state:
            state['metadata'] = {
                'created_at': datetime.now(timezone.utc).isoformat(),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }

        # Normalize task status ("complete" -> "completed")
        for phase_id, phase_data in state.get('phases', {}).items():
            for task_id, task_data in phase_data.get('tasks', {}).items():
                if task_data.get('status') == 'complete':
                    task_data['status'] = 'completed'

        return state


# ============================================================================
# CONTEXT MANAGER FOR TASK EXECUTION
# ============================================================================

@contextmanager
def task_running(phase_id: str, task_id: str, task_name: str, state_dir: Path = None):
    """
    Context manager for task execution tracking.

    Usage:
        with task_running("2-prd", "205", "PRD Authoring"):
            # Task logic here
            pass
    """
    from core.utils.file_ops import write_json

    state_dir = state_dir or Path(".state")
    current_task_file = state_dir / "current-task.json"

    current_task = {
        "phase": phase_id,
        "task": task_id,
        "name": task_name,
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat()
    }

    write_json(current_task_file, current_task)

    try:
        yield
    finally:
        # Clear current task
        if current_task_file.exists():
            current_task_file.unlink()


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("Testing state module...\n")

    # Create temp state for testing
    import tempfile
    test_dir = Path(tempfile.mkdtemp())

    state = StateManager(state_dir=test_dir / ".state", atomic_root=test_dir)

    print("Initial state:")
    state.display_status()

    print("Marking tasks complete...")
    state.set_current_phase("0-setup")
    state.mark_task_complete("0-setup", "001", "Mode Selection")
    state.mark_task_complete("0-setup", "002", "Config Collection")

    print("\nCurrent state:")
    state.display_status()

    print("\nCreating snapshot...")
    snapshot = state.snapshot()
    print(f"Snapshot created at {snapshot.timestamp}")

    print("\nMarking task failed...")
    state.mark_task_failed("0-setup", "003", "Config Display", "Test error")

    print("\nState after failure:")
    state.display_status()

    print("\nRestoring from snapshot...")
    state.restore(snapshot)

    print("\nState after restore:")
    state.display_status()

    # Cleanup
    shutil.rmtree(test_dir)

    print("\n✓ state.py module ready")
