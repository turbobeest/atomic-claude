"""Tests for task executor."""

import pytest
import time
from core.task.executor import TaskExecutor, TaskTimeoutError
from core.task.types import TaskDefinition, TaskState, TaskResult
from core.task.dependencies import TaskDependencyGraph


class TestTaskExecutor:
    """Tests for TaskExecutor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.executor = TaskExecutor()

    def test_execute_simple_task(self):
        """Test executing a simple task."""
        def simple_task():
            return True

        task = TaskDefinition(
            task_id="001",
            phase_id="0-setup",
            name="Simple Task",
            function=simple_task
        )

        result = self.executor.execute_task(task)
        assert result.success
        assert result.state == TaskState.COMPLETED

    def test_execute_failing_task(self):
        """Test executing a task that fails."""
        def failing_task():
            return False

        task = TaskDefinition(
            task_id="001",
            phase_id="0-setup",
            name="Failing Task",
            function=failing_task,
            retryable=False  # Don't retry for this test
        )

        result = self.executor.execute_task(task)
        assert result.failed
        assert result.state == TaskState.FAILED

    def test_execute_task_with_exception(self):
        """Test executing a task that raises an exception."""
        def error_task():
            raise ValueError("Test error")

        task = TaskDefinition(
            task_id="001",
            phase_id="0-setup",
            name="Error Task",
            function=error_task,
            retryable=False
        )

        result = self.executor.execute_task(task)
        assert result.failed
        assert "Test error" in result.error

    def test_execute_task_with_timeout(self):
        """Test task timeout enforcement."""
        def slow_task():
            time.sleep(5)
            return True

        task = TaskDefinition(
            task_id="001",
            phase_id="0-setup",
            name="Slow Task",
            function=slow_task,
            timeout=1,  # 1 second timeout
            retryable=False
        )

        result = self.executor.execute_task(task)
        assert result.failed
        assert "timeout" in result.error.lower() or result.exit_code == 124

    def test_execute_task_with_integer_return(self):
        """Test task with integer return (exit code)."""
        def task_with_exit_code():
            return 0

        task = TaskDefinition(
            task_id="001",
            phase_id="0-setup",
            name="Exit Code Task",
            function=task_with_exit_code
        )

        result = self.executor.execute_task(task)
        assert result.success
        assert result.exit_code == 0

    def test_execute_task_with_result_return(self):
        """Test task that returns TaskResult."""
        def task_with_result():
            return TaskResult(
                task_id="001",
                phase_id="0-setup",
                state=TaskState.COMPLETED,
                exit_code=0,
                output="Custom output"
            )

        task = TaskDefinition(
            task_id="001",
            phase_id="0-setup",
            name="Result Task",
            function=task_with_result
        )

        result = self.executor.execute_task(task)
        assert result.success
        assert result.output == "Custom output"

    def test_retry_task(self):
        """Test task retry logic."""
        call_count = [0]

        def flaky_task():
            call_count[0] += 1
            if call_count[0] < 2:
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
        assert result.success
        assert result.retry_count > 0
        assert call_count[0] == 2

    def test_retry_max_exceeded(self):
        """Test retry stops at max retries."""
        def always_fails():
            return False

        task = TaskDefinition(
            task_id="001",
            phase_id="0-setup",
            name="Always Fails",
            function=always_fails,
            retryable=True,
            max_retries=2
        )

        result = self.executor.execute_task(task)
        assert result.failed
        assert result.retry_count == 2

    def test_execute_phase_sequential(self):
        """Test executing phase tasks sequentially."""
        execution_order = []

        def task_func(task_num):
            def func():
                execution_order.append(task_num)
                return True
            return func

        tasks = [
            TaskDefinition(
                task_id=f"00{i}",
                phase_id="0-setup",
                name=f"Task {i}",
                function=task_func(i)
            )
            for i in range(1, 4)
        ]

        results = self.executor.execute_phase("0-setup", tasks)

        assert len(results) == 3
        assert all(r.success for r in results)
        assert execution_order == [1, 2, 3]

    def test_execute_phase_with_dependencies(self):
        """Test executing phase with task dependencies."""
        execution_order = []

        def task_func(task_num):
            def func():
                execution_order.append(task_num)
                return True
            return func

        # Task 3 depends on tasks 1 and 2
        tasks = [
            TaskDefinition(
                task_id="001",
                phase_id="0-setup",
                name="Task 1",
                function=task_func(1)
            ),
            TaskDefinition(
                task_id="002",
                phase_id="0-setup",
                name="Task 2",
                function=task_func(2)
            ),
            TaskDefinition(
                task_id="003",
                phase_id="0-setup",
                name="Task 3",
                function=task_func(3)
            ),
        ]

        # Add dependencies
        self.executor.dependency_graph.add_task(tasks[0])
        self.executor.dependency_graph.add_task(tasks[1])
        self.executor.dependency_graph.add_task(tasks[2])
        self.executor.dependency_graph.add_dependency("003", "001")
        self.executor.dependency_graph.add_dependency("003", "002")

        results = self.executor.execute_phase("0-setup", tasks)

        assert len(results) == 3
        assert all(r.success for r in results)
        # Task 3 should execute after tasks 1 and 2
        assert execution_order.index(3) > execution_order.index(1)
        assert execution_order.index(3) > execution_order.index(2)

    def test_execute_phase_stops_on_critical_failure(self):
        """Test phase execution stops on critical (non-retryable) failure."""
        execution_order = []

        def success_task():
            execution_order.append("success")
            return True

        def critical_fail_task():
            execution_order.append("fail")
            return False

        tasks = [
            TaskDefinition(
                task_id="001",
                phase_id="0-setup",
                name="Task 1",
                function=success_task
            ),
            TaskDefinition(
                task_id="002",
                phase_id="0-setup",
                name="Task 2",
                function=critical_fail_task,
                retryable=False  # Critical failure
            ),
            TaskDefinition(
                task_id="003",
                phase_id="0-setup",
                name="Task 3",
                function=success_task
            ),
        ]

        results = self.executor.execute_phase("0-setup", tasks)

        # Should stop after task 2 fails
        assert len(results) == 2
        assert results[0].success
        assert results[1].failed
        assert execution_order == ["success", "fail"]

    def test_get_progress(self):
        """Test getting execution progress."""
        tasks = [
            TaskDefinition(
                task_id=f"00{i}",
                phase_id="0-setup",
                name=f"Task {i}",
                function=lambda: True
            )
            for i in range(1, 4)
        ]

        # Start phase execution (just check progress tracking)
        self.executor._current_phase = "0-setup"
        self.executor._total_tasks = 3
        self.executor._completed_count = 1
        self.executor._completed_tasks.add("001")
        self.executor._phase_start_time = time.time()

        progress = self.executor.get_progress()

        assert progress["phase_id"] == "0-setup"
        assert progress["total_tasks"] == 3
        assert progress["completed_tasks"] == 1
        assert progress["completion_percentage"] > 0

    def test_reset_executor(self):
        """Test resetting executor state."""
        self.executor._completed_tasks.add("001")
        self.executor._failed_tasks.add("002")
        self.executor._current_phase = "0-setup"

        self.executor.reset()

        assert len(self.executor._completed_tasks) == 0
        assert len(self.executor._failed_tasks) == 0
        assert self.executor._current_phase is None

    def test_task_duration_tracking(self):
        """Test task execution duration is tracked."""
        def timed_task():
            time.sleep(0.1)
            return True

        task = TaskDefinition(
            task_id="001",
            phase_id="0-setup",
            name="Timed Task",
            function=timed_task
        )

        result = self.executor.execute_task(task)
        assert result.duration is not None
        assert result.duration >= 0.1

    def test_task_timestamps(self):
        """Test task start and completion timestamps."""
        def simple_task():
            return True

        task = TaskDefinition(
            task_id="001",
            phase_id="0-setup",
            name="Simple Task",
            function=simple_task
        )

        result = self.executor.execute_task(task)
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.completed_at >= result.started_at

    def test_validation_failure_prevents_execution(self):
        """Test validation failure prevents task execution."""
        # Task with no executable should fail validation
        task = TaskDefinition(
            task_id="001",
            phase_id="0-setup",
            name="Invalid Task"
        )

        result = self.executor.execute_task(task)
        assert result.failed
        assert "validation" in result.error.lower()
