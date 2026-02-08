"""
Task State Machine

Manages task state transitions with validation and history tracking.
"""

from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

from .types import TaskState, StateTransition


class TaskStateMachine:
    """
    Manages task state transitions.

    Features:
    - Validates state transitions
    - Tracks state history
    - Integrates with StateManager for persistence
    - Supports concurrent task state management
    """

    # Valid state transitions (from_state -> [to_states])
    VALID_TRANSITIONS = {
        TaskState.PENDING: [TaskState.RUNNING, TaskState.SKIPPED],
        TaskState.RUNNING: [TaskState.COMPLETED, TaskState.FAILED, TaskState.PENDING],
        TaskState.COMPLETED: [TaskState.PENDING],  # Allow reset
        TaskState.FAILED: [TaskState.PENDING, TaskState.RUNNING],  # Allow retry
        TaskState.SKIPPED: [TaskState.PENDING],  # Allow undo skip
    }

    def __init__(self, state_manager=None):
        """
        Initialize task state machine.

        Args:
            state_manager: StateManager instance for persistence (optional)
        """
        self.state_manager = state_manager
        self._states: Dict[str, TaskState] = {}
        self._history: Dict[str, List[StateTransition]] = {}

    def get_state(self, task_id: str) -> TaskState:
        """
        Get current state of a task.

        Args:
            task_id: Task identifier

        Returns:
            Current TaskState (defaults to PENDING if not set)
        """
        return self._states.get(task_id, TaskState.PENDING)

    def is_valid_transition(self, from_state: TaskState, to_state: TaskState) -> bool:
        """
        Check if a state transition is valid.

        Args:
            from_state: Current state
            to_state: Target state

        Returns:
            True if transition is valid
        """
        valid_to_states = self.VALID_TRANSITIONS.get(from_state, [])
        return to_state in valid_to_states

    def transition(
        self,
        task_id: str,
        to_state: TaskState,
        reason: Optional[str] = None,
        persist: bool = True
    ) -> bool:
        """
        Transition task to a new state.

        Args:
            task_id: Task identifier
            to_state: Target state
            reason: Reason for transition (optional)
            persist: Whether to persist to StateManager

        Returns:
            True if transition succeeded, False otherwise

        Raises:
            ValueError: If transition is invalid
        """
        from_state = self.get_state(task_id)

        # Check if transition is valid
        if from_state == to_state:
            # No-op, but record it
            return True

        if not self.is_valid_transition(from_state, to_state):
            raise ValueError(
                f"Invalid state transition for task {task_id}: "
                f"{from_state} -> {to_state}"
            )

        # Record transition in history
        transition = StateTransition(
            from_state=from_state,
            to_state=to_state,
            timestamp=datetime.now(),
            reason=reason
        )

        if task_id not in self._history:
            self._history[task_id] = []
        self._history[task_id].append(transition)

        # Update state
        self._states[task_id] = to_state

        # Persist to StateManager if available
        if persist and self.state_manager:
            self._persist_state(task_id, to_state)

        return True

    def get_history(self, task_id: str) -> List[StateTransition]:
        """
        Get state transition history for a task.

        Args:
            task_id: Task identifier

        Returns:
            List of StateTransition records
        """
        return self._history.get(task_id, [])

    def reset_task(self, task_id: str, persist: bool = True) -> bool:
        """
        Reset task to PENDING state.

        Args:
            task_id: Task identifier
            persist: Whether to persist to StateManager

        Returns:
            True if reset succeeded
        """
        current_state = self.get_state(task_id)
        return self.transition(
            task_id,
            TaskState.PENDING,
            reason="Task reset",
            persist=persist
        )

    def reset_all(self):
        """Reset all tasks to PENDING state."""
        for task_id in list(self._states.keys()):
            self.reset_task(task_id, persist=False)

    def mark_running(self, task_id: str, persist: bool = True) -> bool:
        """
        Mark task as running.

        Args:
            task_id: Task identifier
            persist: Whether to persist to StateManager

        Returns:
            True if transition succeeded
        """
        return self.transition(
            task_id,
            TaskState.RUNNING,
            reason="Task started",
            persist=persist
        )

    def mark_completed(self, task_id: str, persist: bool = True) -> bool:
        """
        Mark task as completed.

        Args:
            task_id: Task identifier
            persist: Whether to persist to StateManager

        Returns:
            True if transition succeeded
        """
        return self.transition(
            task_id,
            TaskState.COMPLETED,
            reason="Task completed successfully",
            persist=persist
        )

    def mark_failed(
        self,
        task_id: str,
        reason: Optional[str] = None,
        persist: bool = True
    ) -> bool:
        """
        Mark task as failed.

        Args:
            task_id: Task identifier
            reason: Failure reason
            persist: Whether to persist to StateManager

        Returns:
            True if transition succeeded
        """
        return self.transition(
            task_id,
            TaskState.FAILED,
            reason=reason or "Task failed",
            persist=persist
        )

    def mark_skipped(self, task_id: str, persist: bool = True) -> bool:
        """
        Mark task as skipped.

        Args:
            task_id: Task identifier
            persist: Whether to persist to StateManager

        Returns:
            True if transition succeeded
        """
        return self.transition(
            task_id,
            TaskState.SKIPPED,
            reason="Task skipped",
            persist=persist
        )

    def get_tasks_by_state(self, state: TaskState) -> List[str]:
        """
        Get all tasks in a specific state.

        Args:
            state: Target state

        Returns:
            List of task IDs
        """
        return [
            task_id
            for task_id, task_state in self._states.items()
            if task_state == state
        ]

    def get_pending_tasks(self) -> List[str]:
        """Get all pending tasks."""
        return self.get_tasks_by_state(TaskState.PENDING)

    def get_running_tasks(self) -> List[str]:
        """Get all running tasks."""
        return self.get_tasks_by_state(TaskState.RUNNING)

    def get_completed_tasks(self) -> List[str]:
        """Get all completed tasks."""
        return self.get_tasks_by_state(TaskState.COMPLETED)

    def get_failed_tasks(self) -> List[str]:
        """Get all failed tasks."""
        return self.get_tasks_by_state(TaskState.FAILED)

    def _persist_state(self, task_id: str, state: TaskState):
        """
        Persist state to StateManager.

        Args:
            task_id: Task identifier
            state: New state
        """
        if not self.state_manager:
            return

        # Note: This is a simplified persistence model
        # The actual StateManager integration would happen in the executor
        # where we have access to phase_id, task_name, etc.
        pass

    def export_state(self) -> Dict[str, str]:
        """
        Export current state for all tasks.

        Returns:
            Dictionary mapping task_id to state
        """
        return {
            task_id: state.value
            for task_id, state in self._states.items()
        }

    def import_state(self, state_data: Dict[str, str]):
        """
        Import state from external source.

        Args:
            state_data: Dictionary mapping task_id to state string
        """
        for task_id, state_str in state_data.items():
            try:
                state = TaskState(state_str)
                self._states[task_id] = state
            except ValueError:
                # Skip invalid states
                pass
