"""Integration tests for task execution engine."""

import pytest
import time
from pathlib import Path

from core.task import (
    TaskExecutor,
    TaskDefinition,
    TaskState,
    TaskDependencyGraph,
    TaskStateMachine
)
from core.state import StateManager


class TestTaskIntegration:
    """Integration tests for task execution."""

    def setup_method(self):
        """Set up test fixtures."""
        # Use temporary state directory
        self.test_state_dir = Path(".test_state")
        self.test_state_dir.mkdir(exist_ok=True)

        self.state_manager = StateManager(self.test_state_dir)
        self.executor = TaskExecutor(state_manager=self.state_manager)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if self.test_state_dir.exists():
            shutil.rmtree(self.test_state_dir)

    def test_full_task_lifecycle(self):
        """Test complete task lifecycle from pending to completed."""
        def test_task():
            return True

        task = TaskDefinition(
            task_id="001",
            phase_id="0-setup",
            name="Test Task",
            function=test_task
        )

        # Execute task
        result = self.executor.execute_task(task)

        # Verify result
        assert result.success
        assert result.state == TaskState.COMPLETED
        assert result.exit_code == 0

        # Verify state was persisted
        assert self.state_manager.is_task_complete("0-setup", "001")

    def test_phase_execution_with_state_persistence(self):
        """Test phase execution with state persistence."""
        tasks = []
        for i in range(1, 4):
            task = TaskDefinition(
                task_id=f"00{i}",
                phase_id="0-setup",
                name=f"Task {i}",
                function=lambda: True
            )
            tasks.append(task)

        # Execute phase
        results = self.executor.execute_phase("0-setup", tasks)

        # Verify all tasks completed
        assert len(results) == 3
        assert all(r.success for r in results)

        # Verify state persistence
        for task in tasks:
            assert self.state_manager.is_task_complete("0-setup", task.task_id)

    def test_resume_from_failure(self):
        """Test resuming phase execution after failure."""
        call_log = []

        def task1():
            call_log.append("task1")
            return True

        def task2():
            call_log.append("task2")
            return False

        def task3():
            call_log.append("task3")
            return True

        tasks = [
            TaskDefinition(
                task_id="001",
                phase_id="0-setup",
                name="Task 1",
                function=task1
            ),
            TaskDefinition(
                task_id="002",
                phase_id="0-setup",
                name="Task 2",
                function=task2,
                retryable=False
            ),
            TaskDefinition(
                task_id="003",
                phase_id="0-setup",
                name="Task 3",
                function=task3
            ),
        ]

        # First execution - task 2 fails
        results1 = self.executor.execute_phase("0-setup", tasks)
        assert len(results1) == 2  # Stops at failure
        assert results1[1].failed

        # Reset executor for second run
        self.executor.reset()

        # Second execution - should skip completed task 1
        results2 = self.executor.execute_phase("0-setup", tasks)

        # Task 1 should be skipped (already complete)
        # Task 2 will fail again
        assert len([r for r in results2 if r.state == TaskState.SKIPPED]) >= 1

    def test_dependency_resolution(self):
        """Test task dependency resolution in execution."""
        execution_order = []

        def make_task(num):
            def task():
                execution_order.append(num)
                return True
            return task

        # Create tasks with dependencies
        task1 = TaskDefinition(
            task_id="001",
            phase_id="0-setup",
            name="Task 1",
            function=make_task(1)
        )

        task2 = TaskDefinition(
            task_id="002",
            phase_id="0-setup",
            name="Task 2",
            function=make_task(2)
        )

        task3 = TaskDefinition(
            task_id="003",
            phase_id="0-setup",
            name="Task 3",
            function=make_task(3)
        )

        # Set up dependencies: 3 depends on 1 and 2
        self.executor.dependency_graph.add_task(task1)
        self.executor.dependency_graph.add_task(task2)
        self.executor.dependency_graph.add_task(task3)
        self.executor.dependency_graph.add_dependency("003", "001")
        self.executor.dependency_graph.add_dependency("003", "002")

        # Execute phase
        results = self.executor.execute_phase("0-setup", [task1, task2, task3])

        # Verify all completed
        assert all(r.success for r in results)

        # Verify execution order: task 3 ran after 1 and 2
        assert execution_order.index(3) > execution_order.index(1)
        assert execution_order.index(3) > execution_order.index(2)

    def test_retry_with_backoff(self):
        """Test retry logic with exponential backoff."""
        attempts = []
        start_time = time.time()

        def flaky_task():
            attempts.append(time.time())
            if len(attempts) < 2:
                return False
            return True

        task = TaskDefinition(
            task_id="001",
            phase_id="0-setup",
            name="Flaky Task",
            function=flaky_task,
            retryable=True,
            max_retries=3
        )

        result = self.executor.execute_task(task)

        # Should succeed after retry
        assert result.success
        assert len(attempts) == 2

        # Verify backoff delay (should be ~2 seconds)
        if len(attempts) >= 2:
            delay = attempts[1] - attempts[0]
            assert delay >= 2.0  # First retry has 2^1 = 2 second backoff

    def test_parallel_task_identification(self):
        """Test identification of tasks that can run in parallel."""
        # Create task graph with parallel opportunities
        task1 = TaskDefinition(task_id="001", phase_id="0-setup", name="Task 1", function=lambda: True)
        task2 = TaskDefinition(task_id="002", phase_id="0-setup", name="Task 2", function=lambda: True)
        task3 = TaskDefinition(task_id="003", phase_id="0-setup", name="Task 3", function=lambda: True)
        task4 = TaskDefinition(task_id="004", phase_id="0-setup", name="Task 4", function=lambda: True)

        # Set up dependencies:
        # Task 1 (root)
        # ├─> Task 2 (parallel with 3)
        # └─> Task 3 (parallel with 2)
        #     └─> Task 4
        self.executor.dependency_graph.add_task(task1)
        self.executor.dependency_graph.add_task(task2)
        self.executor.dependency_graph.add_task(task3)
        self.executor.dependency_graph.add_task(task4)
        self.executor.dependency_graph.add_dependency("002", "001")
        self.executor.dependency_graph.add_dependency("003", "001")
        self.executor.dependency_graph.add_dependency("004", "003")

        # Get parallel tasks
        levels = self.executor.dependency_graph.get_parallel_tasks()

        # Should have 3 levels
        assert len(levels) == 3

        # Level 0: task 1
        assert len(levels[0]) == 1
        assert levels[0][0].task_id == "001"

        # Level 1: tasks 2 and 3 (can run in parallel)
        assert len(levels[1]) == 2
        level1_ids = {t.task_id for t in levels[1]}
        assert level1_ids == {"002", "003"}

        # Level 2: task 4
        assert len(levels[2]) == 1
        assert levels[2][0].task_id == "004"

    def test_progress_tracking(self):
        """Test progress tracking during phase execution."""
        tasks = [
            TaskDefinition(
                task_id=f"00{i}",
                phase_id="0-setup",
                name=f"Task {i}",
                function=lambda: (time.sleep(0.1), True)[1]
            )
            for i in range(1, 6)
        ]

        # Start execution in background (simulated)
        self.executor._current_phase = "0-setup"
        self.executor._total_tasks = len(tasks)
        self.executor._phase_start_time = time.time()

        # Simulate partial completion
        for i in range(3):
            self.executor._completed_tasks.add(f"00{i+1}")
            self.executor._completed_count += 1

        progress = self.executor.get_progress("0-setup")

        assert progress["phase_id"] == "0-setup"
        assert progress["total_tasks"] == 5
        assert progress["completed_tasks"] == 3
        assert progress["completion_percentage"] == 60.0
        assert progress["elapsed_time"] > 0

    def test_failure_recovery(self):
        """Test recovering from task failures."""
        def failing_task():
            raise Exception("Simulated failure")

        task = TaskDefinition(
            task_id="001",
            phase_id="0-setup",
            name="Failing Task",
            function=failing_task,
            retryable=False
        )

        result = self.executor.execute_task(task)

        # Verify failure was captured
        assert result.failed
        assert result.error is not None
        assert "Simulated failure" in result.error

        # Verify state was marked as failed
        state = self.state_manager.load_state()
        task_state = state.get("phases", {}).get("0-setup", {}).get("tasks", {}).get("001", {})
        assert task_state.get("status") == "failed"

    def test_state_persistence_across_sessions(self):
        """Test state persists across executor sessions."""
        # First session
        task = TaskDefinition(
            task_id="001",
            phase_id="0-setup",
            name="Task 1",
            function=lambda: True
        )

        result1 = self.executor.execute_task(task)
        assert result1.success

        # Create new executor (simulating new session)
        executor2 = TaskExecutor(state_manager=self.state_manager)

        # Task should still be marked complete
        assert self.state_manager.is_task_complete("0-setup", "001")

    def test_concurrent_task_state_management(self):
        """Test managing state for multiple concurrent tasks."""
        tasks = [
            TaskDefinition(
                task_id=f"00{i}",
                phase_id="0-setup",
                name=f"Task {i}",
                function=lambda: True
            )
            for i in range(1, 4)
        ]

        # Mark multiple tasks as running simultaneously
        for task in tasks:
            self.executor.state_machine.mark_running(task.task_id, persist=False)

        # Verify all are running
        running = self.executor.state_machine.get_running_tasks()
        assert len(running) == 3

        # Complete them one by one
        for task in tasks:
            self.executor.state_machine.mark_completed(task.task_id, persist=False)

        # Verify all completed
        completed = self.executor.state_machine.get_completed_tasks()
        assert len(completed) == 3
