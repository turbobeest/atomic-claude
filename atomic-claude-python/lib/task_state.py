#!/usr/bin/env python3
"""
ATOMIC CLAUDE - Task State Management

Provides persistent task-level state tracking for resumable workflows.

Features:
  - Track completed tasks per phase
  - Resume from any task
  - Reset/redo from specific task
  - Survive session boundaries
  - Thread-safe file locking

State file: .claude/task-state.json
"""

import json
import os
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# Try to import file locking library
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False


# ============================================================================
# TYPE DEFINITIONS
# ============================================================================

class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class Task:
    """Represents a single task within a phase."""
    name: str
    status: TaskStatus = TaskStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    failed_at: Optional[str] = None
    error: Optional[str] = None
    artifacts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with enum values as strings."""
        result = asdict(self)
        result['status'] = self.status.value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create Task from dictionary."""
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = TaskStatus(data['status'])
        return cls(**data)


@dataclass
class Phase:
    """Represents a phase containing multiple tasks."""
    started_at: str
    tasks: Dict[str, Task] = field(default_factory=dict)
    completed: bool = False
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'started_at': self.started_at,
            'tasks': {k: v.to_dict() for k, v in self.tasks.items()},
            'completed': self.completed,
            'completed_at': self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Phase':
        """Create Phase from dictionary."""
        tasks = {k: Task.from_dict(v) for k, v in data.get('tasks', {}).items()}
        return cls(
            started_at=data['started_at'],
            tasks=tasks,
            completed=data.get('completed', False),
            completed_at=data.get('completed_at'),
        )


@dataclass
class TaskState:
    """Root state object for entire pipeline."""
    version: str = "1.0"
    current_phase: Optional[str] = None
    current_task: Optional[str] = None
    phases: Dict[str, Phase] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'version': self.version,
            'current_phase': self.current_phase,
            'current_task': self.current_task,
            'phases': {k: v.to_dict() for k, v in self.phases.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskState':
        """Create TaskState from dictionary."""
        phases = {k: Phase.from_dict(v) for k, v in data.get('phases', {}).items()}
        return cls(
            version=data.get('version', '1.0'),
            current_phase=data.get('current_phase'),
            current_task=data.get('current_task'),
            phases=phases,
        )


# ============================================================================
# FILE LOCKING
# ============================================================================

class FileLock:
    """Context manager for file locking with fallback mechanisms."""

    def __init__(self, lock_path: Path, timeout: int = 10):
        """
        Initialize file lock.

        Args:
            lock_path: Path to lock file
            timeout: Maximum seconds to wait for lock
        """
        self.lock_path = lock_path
        self.timeout = timeout
        self.lock_fd: Optional[int] = None
        self.lock_dir: Optional[Path] = None

    def __enter__(self):
        """Acquire lock."""
        if HAS_FCNTL:
            self._acquire_fcntl_lock()
        else:
            self._acquire_mkdir_lock()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release lock."""
        if HAS_FCNTL:
            self._release_fcntl_lock()
        else:
            self._release_mkdir_lock()

    def _acquire_fcntl_lock(self):
        """Acquire lock using fcntl (Unix systems)."""
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_fd = os.open(str(self.lock_path), os.O_CREAT | os.O_WRONLY)

        start_time = time.time()
        while True:
            try:
                fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return
            except BlockingIOError:
                if time.time() - start_time >= self.timeout:
                    os.close(self.lock_fd)
                    raise TimeoutError(f"Failed to acquire lock after {self.timeout}s")
                time.sleep(0.1)

    def _release_fcntl_lock(self):
        """Release lock using fcntl."""
        if self.lock_fd is not None:
            try:
                fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
                os.close(self.lock_fd)
            except Exception:
                pass
            finally:
                self.lock_fd = None

    def _acquire_mkdir_lock(self):
        """Acquire lock using mkdir (atomic on all POSIX systems)."""
        self.lock_dir = self.lock_path.parent / f"{self.lock_path.name}.d"

        start_time = time.time()
        while True:
            try:
                self.lock_dir.mkdir(parents=True)
                # Store PID for stale lock detection
                pid_file = self.lock_dir / "pid"
                pid_file.write_text(str(os.getpid()))
                return
            except FileExistsError:
                # Check for stale locks
                if time.time() - start_time >= self.timeout:
                    # Try stale lock cleanup
                    pid_file = self.lock_dir / "pid"
                    if pid_file.exists():
                        try:
                            lock_pid = int(pid_file.read_text().strip())
                            # Check if process still exists
                            os.kill(lock_pid, 0)  # Doesn't kill, just checks
                        except (ProcessLookupError, ValueError, OSError):
                            # Lock holder is dead, remove stale lock
                            try:
                                import shutil
                                shutil.rmtree(self.lock_dir)
                                continue
                            except Exception:
                                pass

                    raise TimeoutError(f"Failed to acquire lock after {self.timeout}s")
                time.sleep(0.1)

    def _release_mkdir_lock(self):
        """Release lock using mkdir."""
        if self.lock_dir is not None:
            try:
                import shutil
                shutil.rmtree(self.lock_dir, ignore_errors=True)
            except Exception:
                pass
            finally:
                self.lock_dir = None


# ============================================================================
# STATE MANAGER
# ============================================================================

class TaskStateManager:
    """Manages task state with atomic file operations and locking."""

    def __init__(self, atomic_root: Optional[str] = None):
        """
        Initialize task state manager.

        Args:
            atomic_root: Root directory for atomic-claude (defaults to ATOMIC_ROOT env var)
        """
        if atomic_root is None:
            atomic_root = os.environ.get('ATOMIC_ROOT', os.getcwd())

        self.atomic_root = Path(atomic_root)
        self.state_file = self.atomic_root / ".claude" / "task-state.json"
        self.lock_file = Path(f"{self.state_file}.lock")

        # Runtime flags (set via parse_args)
        self.resume_at: Optional[str] = None
        self.force_redo: bool = False

    # ========================================================================
    # FILE OPERATIONS
    # ========================================================================

    def _load_state(self) -> TaskState:
        """
        Load state from file.

        Returns:
            TaskState object
        """
        if not self.state_file.exists():
            return TaskState()

        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
            return TaskState.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"ERROR: Failed to load state file: {e}", file=sys.stderr)
            return TaskState()

    def _save_state(self, state: TaskState):
        """
        Save state to file atomically.

        Args:
            state: TaskState object to save
        """
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file first
        with tempfile.NamedTemporaryFile(
            mode='w',
            dir=self.state_file.parent,
            delete=False,
            prefix='.task-state-',
            suffix='.json'
        ) as tmp:
            json.dump(state.to_dict(), tmp, indent=2)
            tmp_path = tmp.name

        # Atomic move
        try:
            os.replace(tmp_path, self.state_file)
        except Exception as e:
            os.unlink(tmp_path)
            raise IOError(f"Failed to save state file: {e}")

    def _update_state(self, update_fn):
        """
        Update state with locking.

        Args:
            update_fn: Function that takes TaskState and modifies it
        """
        with FileLock(self.lock_file):
            state = self._load_state()
            update_fn(state)
            self._save_state(state)

    # ========================================================================
    # INITIALIZATION
    # ========================================================================

    def task_state_init(self, phase_id: str):
        """
        Initialize task state for a phase.

        Args:
            phase_id: Phase identifier (e.g., "1-discovery")
        """
        def update(state: TaskState):
            state.current_phase = phase_id

            # Initialize phase if it doesn't exist
            if phase_id not in state.phases:
                state.phases[phase_id] = Phase(
                    started_at=datetime.utcnow().isoformat() + 'Z'
                )

        self._update_state(update)

        # Recover stuck tasks
        self.task_state_recover_stuck()

    # ========================================================================
    # TASK STATE QUERIES
    # ========================================================================

    def task_state_is_complete(self, task_id: str) -> bool:
        """
        Check if a task is complete.

        Args:
            task_id: Task identifier (e.g., "101")

        Returns:
            True if task is complete, False otherwise
        """
        state = self._load_state()

        if not state.current_phase:
            return False

        phase = state.phases.get(state.current_phase)
        if not phase:
            return False

        task = phase.tasks.get(task_id)
        if not task:
            return False

        return task.status == TaskStatus.COMPLETE

    def task_state_should_skip(self, task_id: str) -> bool:
        """
        Check if task should be skipped.

        Args:
            task_id: Task identifier (e.g., "101")

        Returns:
            True if should skip, False if should run
        """
        # Check for forced redo flag
        if self.force_redo:
            return False

        # Check for resume target
        if self.resume_at:
            if task_id == self.resume_at:
                # Reached resume point, clear it and run
                self.resume_at = None
                return False
            # Haven't reached resume point yet, skip
            return True

        # Normal case: skip if complete
        return self.task_state_is_complete(task_id)

    def task_state_get_last_complete(self) -> Optional[str]:
        """
        Get the last completed task for current phase.

        Returns:
            Task ID or None
        """
        state = self._load_state()

        if not state.current_phase:
            return None

        phase = state.phases.get(state.current_phase)
        if not phase:
            return None

        # Find last completed task
        completed = [
            (task_id, task)
            for task_id, task in phase.tasks.items()
            if task.status == TaskStatus.COMPLETE and task.completed_at
        ]

        if not completed:
            return None

        # Sort by completion time
        completed.sort(key=lambda x: x[1].completed_at or '')
        return completed[-1][0]

    def task_state_get_resume_point(self) -> Optional[str]:
        """
        Get the next task to run (current task).

        Returns:
            Task ID or None
        """
        state = self._load_state()
        return state.current_task

    # ========================================================================
    # TASK STATE UPDATES
    # ========================================================================

    def task_state_start(self, task_id: str, task_name: str):
        """
        Mark a task as in-progress.

        Args:
            task_id: Task identifier
            task_name: Human-readable task name
        """
        def update(state: TaskState):
            if not state.current_phase:
                raise ValueError("No current phase set")

            phase = state.phases.get(state.current_phase)
            if not phase:
                raise ValueError(f"Phase {state.current_phase} not found")

            state.current_task = task_id

            # Don't overwrite if already in progress (idempotent)
            if task_id in phase.tasks and phase.tasks[task_id].status == TaskStatus.IN_PROGRESS:
                phase.tasks[task_id].name = task_name
            else:
                phase.tasks[task_id] = Task(
                    name=task_name,
                    status=TaskStatus.IN_PROGRESS,
                    started_at=datetime.utcnow().isoformat() + 'Z'
                )

        self._update_state(update)

    def task_state_complete(self, task_id: str, task_name: str, artifacts: Optional[List[str]] = None):
        """
        Mark a task as complete.

        Args:
            task_id: Task identifier
            task_name: Human-readable task name
            artifacts: List of artifact file paths
        """
        if artifacts is None:
            artifacts = []

        def update(state: TaskState):
            if not state.current_phase:
                raise ValueError("No current phase set")

            phase = state.phases.get(state.current_phase)
            if not phase:
                raise ValueError(f"Phase {state.current_phase} not found")

            state.current_task = None

            if task_id not in phase.tasks:
                phase.tasks[task_id] = Task(name=task_name)

            task = phase.tasks[task_id]
            task.status = TaskStatus.COMPLETE
            task.completed_at = datetime.utcnow().isoformat() + 'Z'
            task.artifacts = artifacts

        self._update_state(update)

    def task_state_fail(self, task_id: str, error_msg: str):
        """
        Mark a task as failed.

        Args:
            task_id: Task identifier
            error_msg: Error message
        """
        def update(state: TaskState):
            if not state.current_phase:
                raise ValueError("No current phase set")

            phase = state.phases.get(state.current_phase)
            if not phase:
                raise ValueError(f"Phase {state.current_phase} not found")

            if task_id not in phase.tasks:
                raise ValueError(f"Task {task_id} not found")

            task = phase.tasks[task_id]
            task.status = TaskStatus.FAILED
            task.error = error_msg
            task.failed_at = datetime.utcnow().isoformat() + 'Z'

        self._update_state(update)

    # ========================================================================
    # TASK NAVIGATION
    # ========================================================================

    def task_state_reset_from(self, from_task: str):
        """
        Reset task state from a specific task (inclusive).
        All tasks from this point forward are marked pending.

        Args:
            from_task: Task ID to reset from
        """
        def update(state: TaskState):
            if not state.current_phase:
                raise ValueError("No current phase set")

            phase = state.phases.get(state.current_phase)
            if not phase:
                raise ValueError(f"Phase {state.current_phase} not found")

            state.current_task = from_task

            # Reset all tasks >= from_task
            for task_id, task in phase.tasks.items():
                if task_id >= from_task:
                    task.status = TaskStatus.PENDING
                    task.completed_at = None
                    task.failed_at = None
                    task.error = None

        self._update_state(update)
        print(f"Reset to task {from_task} - all subsequent tasks marked pending")

    def task_state_clear_phase(self):
        """Clear all task state for current phase (start fresh)."""
        def update(state: TaskState):
            if not state.current_phase:
                raise ValueError("No current phase set")

            phase = state.phases.get(state.current_phase)
            if not phase:
                raise ValueError(f"Phase {state.current_phase} not found")

            state.current_task = None
            phase.tasks = {}
            phase.completed = False
            phase.completed_at = None

        self._update_state(update)

        state = self._load_state()
        print(f"Cleared all task state for phase {state.current_phase}")

    def task_state_phase_complete(self):
        """Mark entire phase as complete."""
        def update(state: TaskState):
            if not state.current_phase:
                raise ValueError("No current phase set")

            phase = state.phases.get(state.current_phase)
            if not phase:
                raise ValueError(f"Phase {state.current_phase} not found")

            state.current_task = None
            phase.completed = True
            phase.completed_at = datetime.utcnow().isoformat() + 'Z'

        self._update_state(update)

    # ========================================================================
    # CROSS-PHASE REVERSIBILITY
    # ========================================================================

    def task_state_pipeline_reset(self, input_task: str):
        """
        Reset pipeline from any task across any phase.
        Clears all progress from that task forward, including all subsequent phases.

        Args:
            input_task: Task ID (e.g., "204" for phase 2, task 204)
        """
        # Parse input
        if len(input_task) == 3:
            target_phase = input_task[0]
            target_task = input_task
        elif len(input_task) == 4:
            target_phase = input_task[:2]
            target_task = input_task
        else:
            print("Invalid task ID format. Use 3-digit (e.g., 204) or 4-digit (e.g., 1104)")
            return

        # ANSI color codes
        YELLOW = '\033[33m'
        RED = '\033[31m'
        GREEN = '\033[32m'
        BOLD = '\033[1m'
        CYAN = '\033[36m'
        NC = '\033[0m'

        print()
        print(f"{YELLOW}╔═══════════════════════════════════════════════════════════╗{NC}")
        print(f"{YELLOW}║{NC} {BOLD}PIPELINE RESET{NC}                                            {YELLOW}║{NC}")
        print(f"{YELLOW}╠═══════════════════════════════════════════════════════════╣{NC}")
        print(f"{YELLOW}║{NC} Resetting from: Task {target_task} (Phase {target_phase})                       {YELLOW}║{NC}")
        print(f"{YELLOW}║{NC}                                                           {YELLOW}║{NC}")
        print(f"{YELLOW}║{NC} This will:                                                {YELLOW}║{NC}")
        print(f"{YELLOW}║{NC}   • Reset Phase {target_phase} from task {target_task}                          {YELLOW}║{NC}")
        print(f"{YELLOW}║{NC}   • Clear ALL phases after Phase {target_phase}                       {YELLOW}║{NC}")
        print(f"{YELLOW}║{NC}                                                           {YELLOW}║{NC}")
        print(f"{YELLOW}╚═══════════════════════════════════════════════════════════╝{NC}")
        print()

        phases_cleared = 0
        tasks_reset = 0

        def update(state: TaskState):
            nonlocal phases_cleared, tasks_reset

            # Get all phases sorted
            all_phases = sorted(
                state.phases.keys(),
                key=lambda x: int(x.split('-')[0])
            )

            started_clearing = False
            target_phase_id = None

            for phase_entry in all_phases:
                phase_num = phase_entry.split('-')[0]

                if phase_num == target_phase:
                    # This is the target phase - reset from specific task
                    print(f"  {YELLOW}→{NC} Phase {phase_num}: Resetting from task {target_task}")

                    phase = state.phases[phase_entry]
                    for task_id, task in phase.tasks.items():
                        if task_id >= target_task:
                            task.status = TaskStatus.PENDING
                            task.completed_at = None
                            task.failed_at = None
                            task.error = None
                            tasks_reset += 1

                    phase.completed = False
                    phase.completed_at = None
                    started_clearing = True
                    target_phase_id = phase_entry

                elif started_clearing or int(phase_num) > int(target_phase):
                    # This phase comes after target - clear entirely
                    print(f"  {RED}✗{NC} Phase {phase_num}: Clearing all tasks")

                    phase = state.phases[phase_entry]
                    phase.tasks = {}
                    phase.completed = False
                    phase.completed_at = None
                    phases_cleared += 1
                    started_clearing = True

                else:
                    # This phase is before target - keep it
                    print(f"  {GREEN}✓{NC} Phase {phase_num}: Preserved")

            # Update current phase to target
            if target_phase_id:
                state.current_phase = target_phase_id
                state.current_task = target_task

        self._update_state(update)

        print()
        print(f"  {BOLD}Summary:{NC}")
        print(f"    Tasks reset in Phase {target_phase}: {tasks_reset}")
        print(f"    Phases cleared: {phases_cleared}")
        print()
        print(f"  {CYAN}To continue from task {target_task}:{NC}")
        print(f"    ./phases/{target_phase}-*/run.sh")
        print()

    def task_state_pipeline_status(self):
        """Show full pipeline state across all phases."""
        state = self._load_state()

        # ANSI color codes
        CYAN = '\033[36m'
        YELLOW = '\033[33m'
        GREEN = '\033[32m'
        RED = '\033[31m'
        BLUE = '\033[34m'
        DIM = '\033[2m'
        BOLD = '\033[1m'
        NC = '\033[0m'

        print()
        print(f"{CYAN}╔═══════════════════════════════════════════════════════════╗{NC}")
        print(f"{CYAN}║{NC} {BOLD}PIPELINE STATE{NC}                                            {CYAN}║{NC}")
        print(f"{CYAN}╚═══════════════════════════════════════════════════════════╝{NC}")
        print()

        # Get all phases sorted
        all_phases = sorted(
            state.phases.keys(),
            key=lambda x: int(x.split('-')[0])
        )

        if not all_phases:
            print("  No phases tracked yet.")
            print()
            return

        for phase_entry in all_phases:
            phase_num = phase_entry.split('-')[0]
            phase_name = '-'.join(phase_entry.split('-')[1:])
            phase = state.phases[phase_entry]

            # Count tasks
            total_tasks = len(phase.tasks)
            complete_tasks = sum(1 for t in phase.tasks.values() if t.status == TaskStatus.COMPLETE)
            pending_tasks = sum(1 for t in phase.tasks.values() if t.status == TaskStatus.PENDING)
            failed_tasks = sum(1 for t in phase.tasks.values() if t.status == TaskStatus.FAILED)

            # Determine status icon and color
            if phase.completed:
                status_icon = "✓"
                status_color = GREEN
            elif phase_entry == state.current_phase:
                status_icon = "→"
                status_color = YELLOW
            elif total_tasks == 0:
                status_icon = "○"
                status_color = DIM
            else:
                status_icon = "◐"
                status_color = BLUE

            print(f"  {status_color}{status_icon}{NC} Phase {phase_num:2} {phase_name:20} ", end='')

            if total_tasks > 0:
                print(f"[{GREEN}{complete_tasks}{NC}/{total_tasks} tasks]")

                # Show individual tasks if phase is current or has issues
                if phase_entry == state.current_phase or failed_tasks > 0:
                    for task_id in sorted(phase.tasks.keys()):
                        task = phase.tasks[task_id]
                        status_str = task.status.value

                        if task.status == TaskStatus.COMPLETE:
                            print(f"    {GREEN}✓{NC} {task_id}: {status_str}")
                        elif task.status == TaskStatus.IN_PROGRESS:
                            print(f"    {YELLOW}→{NC} {task_id}: {status_str}")
                        elif task.status == TaskStatus.FAILED:
                            print(f"    {RED}✗{NC} {task_id}: {status_str}")
                        else:
                            print(f"    {DIM}○{NC} {task_id}: {status_str}")
            else:
                print(f"{DIM}[not started]{NC}")

        print()

    # ========================================================================
    # STATUS DISPLAY
    # ========================================================================

    def task_state_show(self):
        """Show task state for current phase."""
        state = self._load_state()

        # ANSI color codes
        CYAN = '\033[36m'
        YELLOW = '\033[33m'
        GREEN = '\033[32m'
        RED = '\033[31m'
        DIM = '\033[2m'
        NC = '\033[0m'

        if not state.current_phase:
            print("No active phase")
            return

        phase = state.phases.get(state.current_phase)
        if not phase:
            print(f"Phase {state.current_phase} not found")
            return

        print()
        print(f"{CYAN}Task State: Phase {state.current_phase}{NC}")
        print(f"{DIM}─────────────────────────────────────────────{NC}")

        for task_id in sorted(phase.tasks.keys()):
            task = phase.tasks[task_id]
            status_str = task.status.value
            name = task.name or "unnamed"

            if task.status == TaskStatus.COMPLETE:
                print(f"  {GREEN}✓{NC} {task_id}: {status_str} - {name}")
            elif task.status == TaskStatus.IN_PROGRESS:
                print(f"  {YELLOW}→{NC} {task_id}: {status_str} - {name}")
            elif task.status == TaskStatus.FAILED:
                print(f"  {RED}✗{NC} {task_id}: {status_str} - {name}")
            else:
                print(f"  {DIM}○{NC} {task_id}: {status_str} - {name}")

        print()

    # ========================================================================
    # STUCK TASK RECOVERY
    # ========================================================================

    def task_state_recover_stuck(self):
        """
        Detect and reset tasks stuck in "in_progress" state.
        Called automatically during task_state_init to recover from interrupted sessions.
        """
        state = self._load_state()

        if not state.current_phase:
            return

        phase = state.phases.get(state.current_phase)
        if not phase:
            return

        # Find tasks stuck in in_progress
        stuck_tasks = [
            (task_id, task)
            for task_id, task in phase.tasks.items()
            if task.status == TaskStatus.IN_PROGRESS
        ]

        if stuck_tasks:
            YELLOW = '\033[33m'
            NC = '\033[0m'

            print(f"  {YELLOW}!{NC} Recovering stuck tasks from previous interrupted session:", file=sys.stderr)

            def update(state: TaskState):
                phase = state.phases[state.current_phase]
                for task_id, task in stuck_tasks:
                    task_name = task.name or "unknown"
                    print(f"    {YELLOW}→{NC} Task {task_id} ({task_name}): in_progress → pending", file=sys.stderr)
                    task.status = TaskStatus.PENDING
                    task.completed_at = None
                    task.failed_at = None
                    task.error = None

            self._update_state(update)
            print("", file=sys.stderr)

    # ========================================================================
    # CLI INTERFACE
    # ========================================================================

    def task_state_parse_args(self, args: List[str]) -> List[str]:
        """
        Parse command-line arguments for task state flags.

        Args:
            args: Command-line arguments

        Returns:
            Remaining arguments after parsing task state flags
        """
        self.resume_at = None
        self.force_redo = False

        remaining = []
        i = 0

        while i < len(args):
            arg = args[i]

            if arg == '--resume-at' and i + 1 < len(args):
                self.resume_at = args[i + 1]
                i += 2
            elif arg.startswith('--resume-at='):
                self.resume_at = arg.split('=', 1)[1]
                i += 1
            elif arg == '--redo':
                self.force_redo = True
                i += 1
            elif arg == '--reset-from' and i + 1 < len(args):
                self.task_state_reset_from(args[i + 1])
                i += 2
            elif arg.startswith('--reset-from='):
                self.task_state_reset_from(arg.split('=', 1)[1])
                i += 1
            elif arg == '--pipeline-reset' and i + 1 < len(args):
                self.task_state_pipeline_reset(args[i + 1])
                sys.exit(0)
            elif arg.startswith('--pipeline-reset='):
                self.task_state_pipeline_reset(arg.split('=', 1)[1])
                sys.exit(0)
            elif arg == '--pipeline-status':
                self.task_state_pipeline_status()
                sys.exit(0)
            elif arg == '--clear':
                self.task_state_clear_phase()
                i += 1
            elif arg == '--status':
                self.task_state_show()
                sys.exit(0)
            elif arg in ['-h', '--help', '--skip-intro']:
                # Known flags handled elsewhere — pass through
                remaining.append(arg)
                i += 1
            elif arg.startswith('--'):
                print(f"Warning: Unknown flag '{arg}' ignored", file=sys.stderr)
                print("  Supported: --resume-at=N, --redo, --reset-from=N, --clear, --status, --pipeline-status, --pipeline-reset=N", file=sys.stderr)
                i += 1
            else:
                remaining.append(arg)
                i += 1

        return remaining


# ============================================================================
# CONVENIENCE FUNCTIONS (for compatibility with bash API)
# ============================================================================

# Global instance (initialized on first use)
_manager: Optional[TaskStateManager] = None


def _get_manager() -> TaskStateManager:
    """Get or create global TaskStateManager instance."""
    global _manager
    if _manager is None:
        _manager = TaskStateManager()
    return _manager


def task_state_init(phase_id: str):
    """Initialize task state for a phase."""
    _get_manager().task_state_init(phase_id)


def task_state_is_complete(task_id: str) -> bool:
    """Check if a task is complete."""
    return _get_manager().task_state_is_complete(task_id)


def task_state_should_skip(task_id: str) -> bool:
    """Check if task should be skipped."""
    return _get_manager().task_state_should_skip(task_id)


def task_state_get_last_complete() -> Optional[str]:
    """Get the last completed task for current phase."""
    return _get_manager().task_state_get_last_complete()


def task_state_get_resume_point() -> Optional[str]:
    """Get the next task to run."""
    return _get_manager().task_state_get_resume_point()


def task_state_start(task_id: str, task_name: str):
    """Mark a task as in-progress."""
    _get_manager().task_state_start(task_id, task_name)


def task_state_complete(task_id: str, task_name: str, artifacts: Optional[List[str]] = None):
    """Mark a task as complete."""
    _get_manager().task_state_complete(task_id, task_name, artifacts)


def task_state_fail(task_id: str, error_msg: str):
    """Mark a task as failed."""
    _get_manager().task_state_fail(task_id, error_msg)


def task_state_reset_from(from_task: str):
    """Reset task state from a specific task."""
    _get_manager().task_state_reset_from(from_task)


def task_state_clear_phase():
    """Clear all task state for current phase."""
    _get_manager().task_state_clear_phase()


def task_state_phase_complete():
    """Mark entire phase as complete."""
    _get_manager().task_state_phase_complete()


def task_state_pipeline_reset(input_task: str):
    """Reset pipeline from any task across any phase."""
    _get_manager().task_state_pipeline_reset(input_task)


def task_state_pipeline_status():
    """Show full pipeline state across all phases."""
    _get_manager().task_state_pipeline_status()


def task_state_show():
    """Show task state for current phase."""
    _get_manager().task_state_show()


def task_state_recover_stuck():
    """Detect and reset tasks stuck in in_progress state."""
    _get_manager().task_state_recover_stuck()


def task_state_parse_args(args: List[str]) -> List[str]:
    """Parse command-line arguments for task state flags."""
    return _get_manager().task_state_parse_args(args)


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

def main():
    """CLI entry point for testing."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: task_state.py <command> [args...]")
        print("Commands: init, status, pipeline-status, complete, fail, reset-from, clear, pipeline-reset")
        sys.exit(1)

    manager = TaskStateManager()
    command = sys.argv[1]

    if command == 'init':
        if len(sys.argv) < 3:
            print("Usage: task_state.py init <phase_id>")
            sys.exit(1)
        manager.task_state_init(sys.argv[2])

    elif command == 'status':
        manager.task_state_show()

    elif command == 'pipeline-status':
        manager.task_state_pipeline_status()

    elif command == 'complete':
        if len(sys.argv) < 4:
            print("Usage: task_state.py complete <task_id> <task_name> [artifacts...]")
            sys.exit(1)
        manager.task_state_complete(sys.argv[2], sys.argv[3], sys.argv[4:] if len(sys.argv) > 4 else None)

    elif command == 'fail':
        if len(sys.argv) < 4:
            print("Usage: task_state.py fail <task_id> <error_msg>")
            sys.exit(1)
        manager.task_state_fail(sys.argv[2], sys.argv[3])

    elif command == 'reset-from':
        if len(sys.argv) < 3:
            print("Usage: task_state.py reset-from <task_id>")
            sys.exit(1)
        manager.task_state_reset_from(sys.argv[2])

    elif command == 'clear':
        manager.task_state_clear_phase()

    elif command == 'pipeline-reset':
        if len(sys.argv) < 3:
            print("Usage: task_state.py pipeline-reset <task_id>")
            sys.exit(1)
        manager.task_state_pipeline_reset(sys.argv[2])

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
