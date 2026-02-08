"""Tests for task state machine."""

import pytest
from core.task.state import TaskStateMachine
from core.task.types import TaskState


class TestTaskStateMachine:
    """Tests for TaskStateMachine."""

    def setup_method(self):
        """Set up test fixtures."""
        self.state_machine = TaskStateMachine()

    def test_initial_state(self):
        """Test tasks start in PENDING state."""
        state = self.state_machine.get_state("001")
        assert state == TaskState.PENDING

    def test_valid_transition_pending_to_running(self):
        """Test valid transition from PENDING to RUNNING."""
        success = self.state_machine.transition(
            "001",
            TaskState.RUNNING,
            persist=False
        )
        assert success is True
        assert self.state_machine.get_state("001") == TaskState.RUNNING

    def test_valid_transition_running_to_completed(self):
        """Test valid transition from RUNNING to COMPLETED."""
        self.state_machine.transition("001", TaskState.RUNNING, persist=False)
        success = self.state_machine.transition(
            "001",
            TaskState.COMPLETED,
            persist=False
        )
        assert success is True
        assert self.state_machine.get_state("001") == TaskState.COMPLETED

    def test_valid_transition_running_to_failed(self):
        """Test valid transition from RUNNING to FAILED."""
        self.state_machine.transition("001", TaskState.RUNNING, persist=False)
        success = self.state_machine.transition(
            "001",
            TaskState.FAILED,
            persist=False
        )
        assert success is True
        assert self.state_machine.get_state("001") == TaskState.FAILED

    def test_invalid_transition(self):
        """Test invalid transition raises ValueError."""
        with pytest.raises(ValueError):
            self.state_machine.transition(
                "001",
                TaskState.COMPLETED,  # Can't go directly from PENDING to COMPLETED
                persist=False
            )

    def test_transition_history(self):
        """Test state transition history is recorded."""
        self.state_machine.transition("001", TaskState.RUNNING, persist=False)
        self.state_machine.transition("001", TaskState.COMPLETED, persist=False)

        history = self.state_machine.get_history("001")
        assert len(history) == 2
        assert history[0].from_state == TaskState.PENDING
        assert history[0].to_state == TaskState.RUNNING
        assert history[1].from_state == TaskState.RUNNING
        assert history[1].to_state == TaskState.COMPLETED

    def test_transition_with_reason(self):
        """Test transition with reason is recorded."""
        self.state_machine.transition(
            "001",
            TaskState.RUNNING,
            reason="Task started by user",
            persist=False
        )

        history = self.state_machine.get_history("001")
        assert len(history) == 1
        assert history[0].reason == "Task started by user"

    def test_reset_task(self):
        """Test resetting task to PENDING state."""
        self.state_machine.transition("001", TaskState.RUNNING, persist=False)
        self.state_machine.reset_task("001", persist=False)
        assert self.state_machine.get_state("001") == TaskState.PENDING

    def test_reset_all(self):
        """Test resetting all tasks."""
        self.state_machine.transition("001", TaskState.RUNNING, persist=False)
        self.state_machine.transition("002", TaskState.COMPLETED, persist=False)

        self.state_machine.reset_all()

        assert self.state_machine.get_state("001") == TaskState.PENDING
        assert self.state_machine.get_state("002") == TaskState.PENDING

    def test_mark_running(self):
        """Test mark_running convenience method."""
        self.state_machine.mark_running("001", persist=False)
        assert self.state_machine.get_state("001") == TaskState.RUNNING

    def test_mark_completed(self):
        """Test mark_completed convenience method."""
        self.state_machine.mark_running("001", persist=False)
        self.state_machine.mark_completed("001", persist=False)
        assert self.state_machine.get_state("001") == TaskState.COMPLETED

    def test_mark_failed(self):
        """Test mark_failed convenience method."""
        self.state_machine.mark_running("001", persist=False)
        self.state_machine.mark_failed("001", "Task error", persist=False)
        assert self.state_machine.get_state("001") == TaskState.FAILED

    def test_mark_skipped(self):
        """Test mark_skipped convenience method."""
        self.state_machine.mark_skipped("001", persist=False)
        assert self.state_machine.get_state("001") == TaskState.SKIPPED

    def test_get_tasks_by_state(self):
        """Test getting tasks by state."""
        self.state_machine.mark_running("001", persist=False)
        self.state_machine.mark_running("002", persist=False)
        self.state_machine.mark_completed("002", persist=False)

        running = self.state_machine.get_running_tasks()
        assert "001" in running
        assert "002" not in running

        completed = self.state_machine.get_completed_tasks()
        assert "002" in completed
        assert "001" not in completed

    def test_get_pending_tasks(self):
        """Test getting pending tasks."""
        pending = self.state_machine.get_pending_tasks()
        assert len(pending) == 0  # No tasks added yet

        self.state_machine.mark_running("001", persist=False)
        # Task 002 never touched, should be pending
        pending = self.state_machine.get_pending_tasks()
        # Note: get_pending_tasks only returns tasks that have been set
        # Tasks that were never touched won't appear

    def test_export_state(self):
        """Test exporting state."""
        self.state_machine.mark_running("001", persist=False)
        self.state_machine.mark_completed("001", persist=False)
        self.state_machine.mark_failed("002", persist=False)

        exported = self.state_machine.export_state()
        assert exported["001"] == "completed"
        assert exported["002"] == "failed"

    def test_import_state(self):
        """Test importing state."""
        state_data = {
            "001": "completed",
            "002": "running",
            "003": "failed"
        }

        self.state_machine.import_state(state_data)

        assert self.state_machine.get_state("001") == TaskState.COMPLETED
        assert self.state_machine.get_state("002") == TaskState.RUNNING
        assert self.state_machine.get_state("003") == TaskState.FAILED

    def test_import_state_ignores_invalid(self):
        """Test importing state ignores invalid values."""
        state_data = {
            "001": "completed",
            "002": "invalid_state",
            "003": "running"
        }

        self.state_machine.import_state(state_data)

        assert self.state_machine.get_state("001") == TaskState.COMPLETED
        assert self.state_machine.get_state("002") == TaskState.PENDING  # Ignored
        assert self.state_machine.get_state("003") == TaskState.RUNNING

    def test_same_state_transition(self):
        """Test transitioning to same state is allowed."""
        self.state_machine.mark_running("001", persist=False)
        success = self.state_machine.transition("001", TaskState.RUNNING, persist=False)
        assert success is True
        assert self.state_machine.get_state("001") == TaskState.RUNNING

    def test_concurrent_state_updates(self):
        """Test multiple tasks can have state updated independently."""
        self.state_machine.mark_running("001", persist=False)
        self.state_machine.mark_running("002", persist=False)
        self.state_machine.mark_completed("001", persist=False)

        assert self.state_machine.get_state("001") == TaskState.COMPLETED
        assert self.state_machine.get_state("002") == TaskState.RUNNING
