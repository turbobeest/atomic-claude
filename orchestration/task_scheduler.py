"""
Task Scheduler

Manages parallel task execution with resource management, priority scheduling,
and dynamic rescheduling on failure.
"""

import asyncio
import time
from asyncio import Queue, Task
from collections import defaultdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Callable, Any
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from core.task.types import TaskDefinition, TaskResult, TaskState
from core.task.executor import TaskExecutor
from core.task.dependencies import TaskDependencyGraph


class SchedulingStrategy(str, Enum):
    """Task scheduling strategy."""
    FIFO = "fifo"  # First in, first out
    PRIORITY = "priority"  # Priority-based
    DEPENDENCY = "dependency"  # Dependency-aware (topological)


@dataclass
class TaskSchedule:
    """Scheduled task metadata."""
    task_def: TaskDefinition
    priority: int = 0
    scheduled_at: datetime = field(default_factory=datetime.now)
    attempts: int = 0
    last_failure: Optional[str] = None


@dataclass
class ResourceLimits:
    """Resource limits for task execution."""
    max_concurrent_tasks: int = 4
    max_llm_calls_per_minute: int = 60
    max_memory_mb: Optional[int] = None
    max_cpu_percent: Optional[int] = None


class TokenBucket:
    """
    Token bucket rate limiter.

    Implements token bucket algorithm for rate limiting LLM calls.
    """

    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.

        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> bool:
        """
        Acquire tokens from bucket.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens acquired, False if not enough tokens
        """
        async with self._lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    async def wait_for_tokens(self, tokens: int = 1, timeout: Optional[float] = None):
        """
        Wait until tokens are available.

        Args:
            tokens: Number of tokens needed
            timeout: Maximum wait time in seconds

        Raises:
            TimeoutError: If timeout exceeded
        """
        start_time = time.time()

        while True:
            if await self.acquire(tokens):
                return

            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError("Token bucket wait timeout")

            # Wait before retrying
            await asyncio.sleep(0.1)

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        new_tokens = elapsed * self.refill_rate

        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now

    def get_available_tokens(self) -> float:
        """Get number of available tokens."""
        self._refill()
        return self.tokens


class TaskScheduler:
    """
    Task scheduler with parallel execution, resource management, and priority scheduling.

    Features:
    - Parallel execution based on dependency graph
    - Resource limits (concurrent tasks, LLM rate limiting)
    - Priority-based scheduling
    - Dynamic rescheduling on failure
    - Progress tracking
    - Graceful shutdown
    """

    def __init__(
        self,
        executor: TaskExecutor,
        dependency_graph: Optional[TaskDependencyGraph] = None,
        resource_limits: Optional[ResourceLimits] = None,
        strategy: SchedulingStrategy = SchedulingStrategy.DEPENDENCY
    ):
        """
        Initialize task scheduler.

        Args:
            executor: TaskExecutor instance
            dependency_graph: TaskDependencyGraph instance
            resource_limits: Resource limits configuration
            strategy: Scheduling strategy
        """
        self.executor = executor
        self.dependency_graph = dependency_graph or TaskDependencyGraph()
        self.resource_limits = resource_limits or ResourceLimits()
        self.strategy = strategy

        # Task queues
        self._ready_queue: Queue[TaskSchedule] = Queue()
        self._running_tasks: Dict[str, Task] = {}
        self._completed_tasks: Set[str] = set()
        self._failed_tasks: Dict[str, str] = {}  # task_id -> error
        self._scheduled_tasks: Dict[str, TaskSchedule] = {}

        # Resource management
        self._rate_limiter = TokenBucket(
            capacity=resource_limits.max_llm_calls_per_minute,
            refill_rate=resource_limits.max_llm_calls_per_minute / 60.0
        )
        self._semaphore = asyncio.Semaphore(resource_limits.max_concurrent_tasks)

        # Progress tracking
        self._total_tasks = 0
        self._start_time: Optional[float] = None
        self._task_results: List[TaskResult] = []

        # Control flags
        self._running = False
        self._shutdown_requested = False

        # Callbacks
        self._on_task_complete: Optional[Callable[[TaskResult], None]] = None
        self._on_task_failed: Optional[Callable[[TaskResult], None]] = None

    def schedule_tasks(
        self,
        tasks: List[TaskDefinition],
        priorities: Optional[Dict[str, int]] = None
    ):
        """
        Schedule tasks for execution.

        Args:
            tasks: List of task definitions
            priorities: Optional priority map (task_id -> priority)
        """
        priorities = priorities or {}

        for task in tasks:
            # Add to dependency graph
            if not self.dependency_graph.has_task(task.task_id):
                self.dependency_graph.add_task(task)

            # Create schedule
            priority = priorities.get(task.task_id, 0)
            schedule = TaskSchedule(
                task_def=task,
                priority=priority
            )
            self._scheduled_tasks[task.task_id] = schedule

        self._total_tasks = len(tasks)

    async def run(self) -> List[TaskResult]:
        """
        Run all scheduled tasks.

        Returns:
            List of TaskResult objects
        """
        if self._running:
            raise RuntimeError("Scheduler is already running")

        self._running = True
        self._start_time = time.time()
        self._shutdown_requested = False

        try:
            # Create worker pool
            workers = [
                asyncio.create_task(self._worker(i))
                for i in range(self.resource_limits.max_concurrent_tasks)
            ]

            # Create task feeder
            feeder = asyncio.create_task(self._task_feeder())

            # Wait for all workers to complete
            await asyncio.gather(*workers)

            # Cancel feeder if still running
            if not feeder.done():
                feeder.cancel()

            return self._task_results

        finally:
            self._running = False

    async def _task_feeder(self):
        """
        Feed tasks to the ready queue based on dependency resolution.

        This coroutine runs continuously, checking for tasks that are ready
        to execute and adding them to the ready queue.
        """
        while not self._shutdown_requested:
            # Find tasks that are ready to run
            ready_tasks = self._get_ready_tasks()

            # Add to ready queue (sorted by priority)
            for schedule in sorted(ready_tasks, key=lambda s: -s.priority):
                await self._ready_queue.put(schedule)

            # Check if we're done
            if self._is_complete():
                # Signal workers to stop by adding None sentinels
                for _ in range(self.resource_limits.max_concurrent_tasks):
                    await self._ready_queue.put(None)
                break

            # Wait before checking again
            await asyncio.sleep(0.1)

    async def _worker(self, worker_id: int):
        """
        Worker coroutine that executes tasks from the ready queue.

        Args:
            worker_id: Worker identifier
        """
        while not self._shutdown_requested:
            # Get next task from queue
            schedule = await self._ready_queue.get()

            # Check for sentinel (shutdown signal)
            if schedule is None:
                self._ready_queue.task_done()
                break

            # Acquire resources
            async with self._semaphore:
                # Rate limit LLM calls (assume each task makes ~1 call)
                await self._rate_limiter.wait_for_tokens(1, timeout=30.0)

                # Execute task
                result = await self._execute_task_async(schedule)

                # Handle result
                await self._handle_task_result(schedule, result)

            self._ready_queue.task_done()

    async def _execute_task_async(self, schedule: TaskSchedule) -> TaskResult:
        """
        Execute task asynchronously.

        Args:
            schedule: Task schedule

        Returns:
            TaskResult
        """
        task_def = schedule.task_def
        task_id = task_def.task_id

        # Mark as running
        self._running_tasks[task_id] = asyncio.current_task()

        try:
            # Execute in thread pool (TaskExecutor uses synchronous code)
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as pool:
                result = await loop.run_in_executor(
                    pool,
                    self.executor.execute_task,
                    task_def
                )

            return result

        finally:
            # Remove from running
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]

    async def _handle_task_result(self, schedule: TaskSchedule, result: TaskResult):
        """
        Handle task execution result.

        Args:
            schedule: Task schedule
            result: Task result
        """
        task_id = result.task_id

        if result.success:
            # Task completed successfully
            self._completed_tasks.add(task_id)
            self._task_results.append(result)

            # Callback
            if self._on_task_complete:
                self._on_task_complete(result)

        else:
            # Task failed
            schedule.attempts += 1
            schedule.last_failure = result.error

            # Check if we should retry
            if schedule.attempts < schedule.task_def.max_retries:
                # Reschedule with exponential backoff
                backoff = 2 ** schedule.attempts
                await asyncio.sleep(backoff)

                # Re-add to queue
                await self._ready_queue.put(schedule)
            else:
                # Mark as failed
                self._failed_tasks[task_id] = result.error or "Unknown error"
                self._task_results.append(result)

                # Callback
                if self._on_task_failed:
                    self._on_task_failed(result)

    def _get_ready_tasks(self) -> List[TaskSchedule]:
        """
        Get tasks that are ready to execute.

        Returns:
            List of TaskSchedule objects
        """
        ready = []

        for task_id, schedule in self._scheduled_tasks.items():
            # Skip if already completed, failed, or running
            if (task_id in self._completed_tasks or
                task_id in self._failed_tasks or
                task_id in self._running_tasks):
                continue

            # Check if dependencies are satisfied
            if self.dependency_graph.is_ready(task_id, self._completed_tasks):
                ready.append(schedule)

        return ready

    def _is_complete(self) -> bool:
        """
        Check if all tasks are complete (either succeeded or failed).

        Returns:
            True if all tasks are complete
        """
        total_processed = len(self._completed_tasks) + len(self._failed_tasks)
        return total_processed >= self._total_tasks

    def get_progress(self) -> Dict[str, Any]:
        """
        Get current execution progress.

        Returns:
            Dictionary with progress information
        """
        elapsed = 0.0
        if self._start_time:
            elapsed = time.time() - self._start_time

        completed_count = len(self._completed_tasks)
        failed_count = len(self._failed_tasks)
        running_count = len(self._running_tasks)

        completion_pct = 0.0
        if self._total_tasks > 0:
            completion_pct = (completed_count / self._total_tasks) * 100

        # Estimate remaining time
        estimated_remaining = 0.0
        if completed_count > 0 and completion_pct < 100:
            avg_time_per_task = elapsed / completed_count
            remaining_tasks = self._total_tasks - completed_count - failed_count
            estimated_remaining = avg_time_per_task * remaining_tasks

        return {
            "total_tasks": self._total_tasks,
            "completed_tasks": completed_count,
            "failed_tasks": failed_count,
            "running_tasks": running_count,
            "pending_tasks": self._total_tasks - completed_count - failed_count - running_count,
            "completion_percentage": completion_pct,
            "elapsed_time": elapsed,
            "estimated_remaining": estimated_remaining,
            "available_tokens": self._rate_limiter.get_available_tokens()
        }

    async def shutdown(self, graceful: bool = True):
        """
        Shutdown the scheduler.

        Args:
            graceful: If True, wait for running tasks to complete
        """
        self._shutdown_requested = True

        if graceful:
            # Wait for running tasks to complete
            if self._running_tasks:
                await asyncio.gather(*self._running_tasks.values(), return_exceptions=True)
        else:
            # Cancel running tasks
            for task in self._running_tasks.values():
                task.cancel()

    def set_on_task_complete(self, callback: Callable[[TaskResult], None]):
        """
        Set callback for task completion.

        Args:
            callback: Function to call when task completes
        """
        self._on_task_complete = callback

    def set_on_task_failed(self, callback: Callable[[TaskResult], None]):
        """
        Set callback for task failure.

        Args:
            callback: Function to call when task fails
        """
        self._on_task_failed = callback

    def get_task_status(self, task_id: str) -> Optional[str]:
        """
        Get status of a specific task.

        Args:
            task_id: Task identifier

        Returns:
            Status string or None if task not found
        """
        if task_id in self._completed_tasks:
            return "completed"
        elif task_id in self._failed_tasks:
            return f"failed: {self._failed_tasks[task_id]}"
        elif task_id in self._running_tasks:
            return "running"
        elif task_id in self._scheduled_tasks:
            return "pending"
        else:
            return None

    def get_failed_tasks(self) -> Dict[str, str]:
        """
        Get failed tasks with error messages.

        Returns:
            Dictionary mapping task_id to error message
        """
        return self._failed_tasks.copy()

    def get_completed_tasks(self) -> Set[str]:
        """
        Get completed task IDs.

        Returns:
            Set of completed task IDs
        """
        return self._completed_tasks.copy()

    def reset(self):
        """Reset scheduler state."""
        self._ready_queue = Queue()
        self._running_tasks.clear()
        self._completed_tasks.clear()
        self._failed_tasks.clear()
        self._scheduled_tasks.clear()
        self._task_results.clear()
        self._total_tasks = 0
        self._start_time = None
        self._running = False
        self._shutdown_requested = False
