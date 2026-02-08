"""
Unit Tests for Task Scheduler

Tests for parallel execution, resource management, priority scheduling,
rate limiting, and failure handling.
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Configure pytest to use asyncio
pytest_plugins = ('pytest_asyncio',)

from orchestration.task_scheduler import (
    TaskScheduler,
    TaskSchedule,
    ResourceLimits,
    SchedulingStrategy,
    TokenBucket
)
from core.task.types import (
    TaskDefinition,
    TaskResult,
    TaskState,
    TaskDependency,
    DependencyType
)
from core.task.executor import TaskExecutor
from core.task.dependencies import TaskDependencyGraph


@pytest.fixture
def dependency_graph():
    """Create empty dependency graph."""
    return TaskDependencyGraph()


@pytest.fixture
def mock_executor():
    """Create mock task executor."""
    executor = Mock(spec=TaskExecutor)
    executor.dependency_graph = TaskDependencyGraph()
    return executor


@pytest.fixture
def resource_limits():
    """Create resource limits."""
    return ResourceLimits(
        max_concurrent_tasks=2,
        max_llm_calls_per_minute=10
    )


@pytest.fixture
def scheduler(mock_executor, dependency_graph, resource_limits):
    """Create task scheduler."""
    return TaskScheduler(
        executor=mock_executor,
        dependency_graph=dependency_graph,
        resource_limits=resource_limits,
        strategy=SchedulingStrategy.DEPENDENCY
    )


class TestTokenBucket:
    """Test token bucket rate limiter."""

    @pytest.mark.asyncio
    async def test_token_bucket_initialization(self):
        """Test token bucket initializes with full capacity."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert abs(bucket.get_available_tokens() - 10.0) < 0.1

    @pytest.mark.asyncio
    async def test_token_bucket_acquire(self):
        """Test acquiring tokens from bucket."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)

        # Acquire tokens successfully
        assert await bucket.acquire(5) is True
        assert abs(bucket.get_available_tokens() - 5.0) < 0.1

        # Try to acquire more than available
        assert await bucket.acquire(10) is False
        assert abs(bucket.get_available_tokens() - 5.0) < 0.1

    @pytest.mark.asyncio
    async def test_token_bucket_refill(self):
        """Test token bucket refills over time."""
        bucket = TokenBucket(capacity=10, refill_rate=10.0)  # 10 tokens/sec

        # Drain bucket
        await bucket.acquire(10)
        assert abs(bucket.get_available_tokens() - 0.0) < 0.1

        # Wait for refill (0.5 seconds = 5 tokens)
        await asyncio.sleep(0.5)
        tokens = bucket.get_available_tokens()
        assert 3.5 <= tokens <= 6.5  # Allow some timing variance

    @pytest.mark.asyncio
    async def test_token_bucket_wait_for_tokens(self):
        """Test waiting for tokens to become available."""
        bucket = TokenBucket(capacity=10, refill_rate=10.0)

        # Drain bucket
        await bucket.acquire(10)

        # Wait for tokens (should succeed within 1 second)
        start = time.time()
        await bucket.wait_for_tokens(5, timeout=2.0)
        elapsed = time.time() - start

        assert 0.4 <= elapsed <= 0.7  # Should take ~0.5 seconds

    @pytest.mark.asyncio
    async def test_token_bucket_wait_timeout(self):
        """Test token bucket wait timeout."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)  # Slow refill

        # Drain bucket
        await bucket.acquire(10)

        # Try to wait for many tokens with short timeout
        with pytest.raises(TimeoutError):
            await bucket.wait_for_tokens(50, timeout=0.1)


class TestTaskScheduler:
    """Test task scheduler."""

    def test_scheduler_initialization(self, scheduler):
        """Test scheduler initializes correctly."""
        assert scheduler._total_tasks == 0
        assert len(scheduler._completed_tasks) == 0
        assert len(scheduler._failed_tasks) == 0
        assert scheduler._running is False

    def test_schedule_tasks(self, scheduler):
        """Test scheduling tasks."""
        tasks = [
            TaskDefinition(task_id="001", phase_id="0-test", name="Task 1"),
            TaskDefinition(task_id="002", phase_id="0-test", name="Task 2"),
            TaskDefinition(task_id="003", phase_id="0-test", name="Task 3"),
        ]

        scheduler.schedule_tasks(tasks)

        assert scheduler._total_tasks == 3
        assert len(scheduler._scheduled_tasks) == 3
        assert "001" in scheduler._scheduled_tasks
        assert "002" in scheduler._scheduled_tasks
        assert "003" in scheduler._scheduled_tasks

    def test_schedule_tasks_with_priorities(self, scheduler):
        """Test scheduling tasks with priorities."""
        tasks = [
            TaskDefinition(task_id="001", phase_id="0-test", name="Task 1"),
            TaskDefinition(task_id="002", phase_id="0-test", name="Task 2"),
        ]

        priorities = {"001": 10, "002": 5}
        scheduler.schedule_tasks(tasks, priorities)

        assert scheduler._scheduled_tasks["001"].priority == 10
        assert scheduler._scheduled_tasks["002"].priority == 5

    @pytest.mark.asyncio
    async def test_parallel_execution(self, scheduler, mock_executor):
        """Test parallel execution of independent tasks."""
        # Create tasks with no dependencies
        tasks = [
            TaskDefinition(task_id="001", phase_id="0-test", name="Task 1"),
            TaskDefinition(task_id="002", phase_id="0-test", name="Task 2"),
        ]

        # Mock executor to return success
        def execute_task(task_def):
            time.sleep(0.1)  # Simulate work
            return TaskResult(
                task_id=task_def.task_id,
                phase_id=task_def.phase_id,
                state=TaskState.COMPLETED,
                exit_code=0
            )

        mock_executor.execute_task = execute_task

        # Schedule and run
        scheduler.schedule_tasks(tasks)
        start = time.time()
        results = await scheduler.run()
        elapsed = time.time() - start

        # Should complete in parallel (< 0.15s instead of 0.2s sequential)
        assert elapsed < 0.15
        assert len(results) == 2
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_dependency_ordering(self, scheduler, mock_executor):
        """Test tasks execute in dependency order."""
        # Create tasks with dependencies: 003 depends on 002, 002 depends on 001
        task1 = TaskDefinition(task_id="001", phase_id="0-test", name="Task 1")
        task2 = TaskDefinition(
            task_id="002",
            phase_id="0-test",
            name="Task 2",
            dependencies=[TaskDependency(task_id="001")]
        )
        task3 = TaskDefinition(
            task_id="003",
            phase_id="0-test",
            name="Task 3",
            dependencies=[TaskDependency(task_id="002")]
        )

        tasks = [task3, task1, task2]  # Intentionally out of order

        # Track execution order
        execution_order = []

        def execute_task(task_def):
            execution_order.append(task_def.task_id)
            return TaskResult(
                task_id=task_def.task_id,
                phase_id=task_def.phase_id,
                state=TaskState.COMPLETED,
                exit_code=0
            )

        mock_executor.execute_task = execute_task

        # Schedule and run
        scheduler.schedule_tasks(tasks)
        results = await scheduler.run()

        # Verify execution order
        assert execution_order == ["001", "002", "003"]
        assert len(results) == 3
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_rate_limiting(self, scheduler, mock_executor):
        """Test rate limiting works correctly."""
        # Create many tasks
        tasks = [
            TaskDefinition(task_id=f"{i:03d}", phase_id="0-test", name=f"Task {i}")
            for i in range(1, 6)
        ]

        call_times = []

        def execute_task(task_def):
            call_times.append(time.time())
            return TaskResult(
                task_id=task_def.task_id,
                phase_id=task_def.phase_id,
                state=TaskState.COMPLETED,
                exit_code=0
            )

        mock_executor.execute_task = execute_task

        # Schedule with low rate limit
        scheduler._rate_limiter = TokenBucket(capacity=2, refill_rate=10.0)
        scheduler.schedule_tasks(tasks)
        await scheduler.run()

        # Verify rate limiting: first 2 tasks immediate, rest spaced out
        assert len(call_times) == 5

        # First 2 should be nearly simultaneous
        assert (call_times[1] - call_times[0]) < 0.1

    @pytest.mark.asyncio
    async def test_retry_on_failure(self, scheduler, mock_executor):
        """Test tasks are retried on failure."""
        task = TaskDefinition(
            task_id="001",
            phase_id="0-test",
            name="Task 1",
            retryable=True,
            max_retries=2
        )

        attempt_count = 0

        def execute_task(task_def):
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count < 2:
                # Fail first attempt
                return TaskResult(
                    task_id=task_def.task_id,
                    phase_id=task_def.phase_id,
                    state=TaskState.FAILED,
                    exit_code=1,
                    error="Simulated failure"
                )
            else:
                # Succeed on second attempt
                return TaskResult(
                    task_id=task_def.task_id,
                    phase_id=task_def.phase_id,
                    state=TaskState.COMPLETED,
                    exit_code=0
                )

        mock_executor.execute_task = execute_task

        scheduler.schedule_tasks([task])
        results = await scheduler.run()

        assert attempt_count == 2
        assert len(results) == 1
        assert results[0].success

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, scheduler, mock_executor):
        """Test task marked as failed after max retries."""
        task = TaskDefinition(
            task_id="001",
            phase_id="0-test",
            name="Task 1",
            retryable=True,
            max_retries=2
        )

        def execute_task(task_def):
            # Always fail
            return TaskResult(
                task_id=task_def.task_id,
                phase_id=task_def.phase_id,
                state=TaskState.FAILED,
                exit_code=1,
                error="Persistent failure"
            )

        mock_executor.execute_task = execute_task

        scheduler.schedule_tasks([task])
        results = await scheduler.run()

        assert len(results) == 1
        assert results[0].failed
        assert "001" in scheduler._failed_tasks

    @pytest.mark.asyncio
    async def test_progress_tracking(self, scheduler, mock_executor):
        """Test progress tracking during execution."""
        tasks = [
            TaskDefinition(task_id=f"{i:03d}", phase_id="0-test", name=f"Task {i}")
            for i in range(1, 4)
        ]

        def execute_task(task_def):
            time.sleep(0.1)
            return TaskResult(
                task_id=task_def.task_id,
                phase_id=task_def.phase_id,
                state=TaskState.COMPLETED,
                exit_code=0
            )

        mock_executor.execute_task = execute_task

        scheduler.schedule_tasks(tasks)

        # Start execution in background
        async def run_and_check():
            task = asyncio.create_task(scheduler.run())

            # Check progress during execution
            await asyncio.sleep(0.05)
            progress = scheduler.get_progress()

            assert progress["total_tasks"] == 3
            assert progress["completion_percentage"] >= 0
            assert progress["elapsed_time"] > 0

            await task

        await run_and_check()

    @pytest.mark.asyncio
    async def test_task_callbacks(self, scheduler, mock_executor):
        """Test task completion and failure callbacks."""
        completed_tasks = []
        failed_tasks = []

        def on_complete(result):
            completed_tasks.append(result.task_id)

        def on_failed(result):
            failed_tasks.append(result.task_id)

        scheduler.set_on_task_complete(on_complete)
        scheduler.set_on_task_failed(on_failed)

        tasks = [
            TaskDefinition(task_id="001", phase_id="0-test", name="Success"),
            TaskDefinition(task_id="002", phase_id="0-test", name="Failure", max_retries=0),
        ]

        def execute_task(task_def):
            if task_def.task_id == "001":
                return TaskResult(
                    task_id=task_def.task_id,
                    phase_id=task_def.phase_id,
                    state=TaskState.COMPLETED,
                    exit_code=0
                )
            else:
                return TaskResult(
                    task_id=task_def.task_id,
                    phase_id=task_def.phase_id,
                    state=TaskState.FAILED,
                    exit_code=1
                )

        mock_executor.execute_task = execute_task

        scheduler.schedule_tasks(tasks)
        await scheduler.run()

        assert "001" in completed_tasks
        assert "002" in failed_tasks

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, scheduler, mock_executor):
        """Test graceful shutdown waits for running tasks."""
        task = TaskDefinition(task_id="001", phase_id="0-test", name="Long task")

        def execute_task(task_def):
            time.sleep(0.5)  # Simulate long-running task
            return TaskResult(
                task_id=task_def.task_id,
                phase_id=task_def.phase_id,
                state=TaskState.COMPLETED,
                exit_code=0
            )

        mock_executor.execute_task = execute_task

        scheduler.schedule_tasks([task])

        # Start execution
        run_task = asyncio.create_task(scheduler.run())

        # Wait a bit then shutdown
        await asyncio.sleep(0.1)
        await scheduler.shutdown(graceful=True)

        # Task should complete
        await run_task
        assert "001" in scheduler._completed_tasks

    @pytest.mark.asyncio
    async def test_get_task_status(self, scheduler, mock_executor):
        """Test getting task status."""
        task = TaskDefinition(task_id="001", phase_id="0-test", name="Task 1")

        def execute_task(task_def):
            return TaskResult(
                task_id=task_def.task_id,
                phase_id=task_def.phase_id,
                state=TaskState.COMPLETED,
                exit_code=0
            )

        mock_executor.execute_task = execute_task

        # Before scheduling
        assert scheduler.get_task_status("001") is None

        # After scheduling
        scheduler.schedule_tasks([task])
        assert scheduler.get_task_status("001") == "pending"

        # After execution
        await scheduler.run()
        assert scheduler.get_task_status("001") == "completed"

    @pytest.mark.asyncio
    async def test_get_failed_tasks(self, scheduler, mock_executor):
        """Test getting failed tasks."""
        task = TaskDefinition(
            task_id="001",
            phase_id="0-test",
            name="Failing task",
            max_retries=0
        )

        def execute_task(task_def):
            return TaskResult(
                task_id=task_def.task_id,
                phase_id=task_def.phase_id,
                state=TaskState.FAILED,
                exit_code=1,
                error="Test failure"
            )

        mock_executor.execute_task = execute_task

        scheduler.schedule_tasks([task])
        await scheduler.run()

        failed = scheduler.get_failed_tasks()
        assert "001" in failed
        assert "Test failure" in failed["001"]

    @pytest.mark.asyncio
    async def test_reset_scheduler(self, scheduler, mock_executor):
        """Test resetting scheduler state."""
        task = TaskDefinition(task_id="001", phase_id="0-test", name="Task 1")

        def execute_task(task_def):
            return TaskResult(
                task_id=task_def.task_id,
                phase_id=task_def.phase_id,
                state=TaskState.COMPLETED,
                exit_code=0
            )

        mock_executor.execute_task = execute_task

        # Run tasks
        scheduler.schedule_tasks([task])
        await scheduler.run()

        assert scheduler._total_tasks == 1
        assert len(scheduler._completed_tasks) == 1

        # Reset
        scheduler.reset()

        assert scheduler._total_tasks == 0
        assert len(scheduler._completed_tasks) == 0
        assert len(scheduler._scheduled_tasks) == 0

    @pytest.mark.asyncio
    async def test_resource_limits_enforced(self, scheduler, mock_executor):
        """Test that concurrent task limits are enforced."""
        tasks = [
            TaskDefinition(task_id=f"{i:03d}", phase_id="0-test", name=f"Task {i}")
            for i in range(1, 6)
        ]

        concurrent_count = 0
        max_concurrent = 0
        lock = asyncio.Lock()

        def execute_task(task_def):
            nonlocal concurrent_count, max_concurrent

            # Track concurrent execution
            async def track():
                nonlocal concurrent_count, max_concurrent
                async with lock:
                    concurrent_count += 1
                    max_concurrent = max(max_concurrent, concurrent_count)

                await asyncio.sleep(0.1)

                async with lock:
                    concurrent_count -= 1

            asyncio.create_task(track())

            time.sleep(0.1)
            return TaskResult(
                task_id=task_def.task_id,
                phase_id=task_def.phase_id,
                state=TaskState.COMPLETED,
                exit_code=0
            )

        mock_executor.execute_task = execute_task

        scheduler.schedule_tasks(tasks)
        await scheduler.run()

        # Max concurrent should not exceed resource limit
        await asyncio.sleep(0.2)  # Wait for tracking to complete
        assert max_concurrent <= scheduler.resource_limits.max_concurrent_tasks


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
