"""
Task Executor

Main task execution engine with retry logic, timeout enforcement, and progress reporting.
"""

import time
import signal
from pathlib import Path
from typing import List, Set, Optional, Dict, Any, Callable
from datetime import datetime
from contextlib import contextmanager

from .types import (
    TaskDefinition,
    TaskResult,
    TaskState,
    ValidationResult
)
from .state import TaskStateMachine
from .dependencies import TaskDependencyGraph
from .validator import TaskValidator


class TaskTimeoutError(Exception):
    """Raised when task execution exceeds timeout."""
    pass


class TaskExecutor:
    """
    Main task execution engine.

    Features:
    - Execute tasks with retry logic
    - Exponential backoff on failures
    - Timeout enforcement
    - Progress reporting
    - Error capture and logging
    - State integration
    """

    def __init__(
        self,
        state_manager=None,
        config=None,
        dependency_graph: Optional[TaskDependencyGraph] = None
    ):
        """
        Initialize task executor.

        Args:
            state_manager: StateManager instance
            config: Config instance
            dependency_graph: TaskDependencyGraph instance
        """
        self.state_manager = state_manager
        self.config = config
        self.dependency_graph = dependency_graph or TaskDependencyGraph()
        self.state_machine = TaskStateMachine(state_manager)
        self.validator = TaskValidator(self.dependency_graph, state_manager, config)

        # Track completed tasks in current session
        self._completed_tasks: Set[str] = set()
        self._failed_tasks: Set[str] = set()

        # Progress tracking
        self._current_phase: Optional[str] = None
        self._phase_start_time: Optional[float] = None
        self._total_tasks: int = 0
        self._completed_count: int = 0

    def execute_task(
        self,
        task_def: TaskDefinition,
        **kwargs
    ) -> TaskResult:
        """
        Execute a single task.

        Args:
            task_def: Task definition
            **kwargs: Additional arguments to pass to task function

        Returns:
            TaskResult with execution results
        """
        task_id = task_def.task_id
        phase_id = task_def.phase_id

        # Validate task can run
        validation = self.validator.validate_task(
            task_def,
            self._completed_tasks
        )

        if not validation.valid:
            return TaskResult(
                task_id=task_id,
                phase_id=phase_id,
                state=TaskState.FAILED,
                error=f"Validation failed: {', '.join(validation.errors)}",
                exit_code=1
            )

        # Start task
        result = TaskResult(
            task_id=task_id,
            phase_id=phase_id,
            state=TaskState.RUNNING,
            started_at=datetime.now()
        )

        try:
            # Transition to RUNNING
            self.state_machine.mark_running(task_id)

            # Execute with timeout
            result = self._execute_with_timeout(task_def, result, kwargs)

            # Check result
            if result.success:
                self.state_machine.mark_completed(task_id)
                self._completed_tasks.add(task_id)

                # Mark in StateManager
                if self.state_manager:
                    self.state_manager.mark_task_complete(
                        phase_id,
                        task_id,
                        task_def.name
                    )

            else:
                # Task failed - check if we should retry
                if task_def.retryable and result.retry_count < task_def.max_retries:
                    # Retry the task
                    return self.retry_task(task_def, result.retry_count, **kwargs)
                else:
                    # Mark as failed
                    self.state_machine.mark_failed(task_id, result.error)
                    self._failed_tasks.add(task_id)

                    if self.state_manager:
                        self.state_manager.mark_task_failed(
                            phase_id,
                            task_id,
                            task_def.name,
                            result.error
                        )

        except TaskTimeoutError as e:
            result.state = TaskState.FAILED
            result.error = str(e)
            result.exit_code = 124  # Standard timeout exit code

            # Check if we should retry on timeout
            if task_def.retryable and result.retry_count < task_def.max_retries:
                return self.retry_task(task_def, result.retry_count, **kwargs)
            else:
                self.state_machine.mark_failed(task_id, str(e))
                self._failed_tasks.add(task_id)

        except Exception as e:
            result.state = TaskState.FAILED
            result.error = f"Unexpected error: {e}"
            result.exit_code = 1

            self.state_machine.mark_failed(task_id, str(e))
            self._failed_tasks.add(task_id)

        finally:
            result.completed_at = datetime.now()
            if result.started_at:
                duration = (result.completed_at - result.started_at).total_seconds()
                result.duration = duration

        return result

    def retry_task(
        self,
        task_def: TaskDefinition,
        current_retry: int = 0,
        **kwargs
    ) -> TaskResult:
        """
        Retry a failed task with exponential backoff.

        Args:
            task_def: Task definition
            current_retry: Current retry count
            **kwargs: Additional arguments

        Returns:
            TaskResult
        """
        # Validate retry is allowed
        validation = self.validator.validate_retry(task_def, current_retry)
        if not validation.valid:
            return TaskResult(
                task_id=task_def.task_id,
                phase_id=task_def.phase_id,
                state=TaskState.FAILED,
                error=f"Retry validation failed: {', '.join(validation.errors)}",
                exit_code=1,
                retry_count=current_retry
            )

        # Calculate backoff delay: 2^retry_count seconds
        backoff_delay = 2 ** (current_retry + 1)
        time.sleep(backoff_delay)

        # Reset task state for retry
        self.state_machine.reset_task(task_def.task_id, persist=False)

        # Execute again with incremented retry count
        result = self.execute_task(task_def, **kwargs)
        result.retry_count = current_retry + 1

        return result

    def execute_phase(
        self,
        phase_id: str,
        phase_tasks: List[TaskDefinition],
        parallel: bool = False
    ) -> List[TaskResult]:
        """
        Execute all tasks in a phase.

        Args:
            phase_id: Phase identifier
            phase_tasks: List of tasks to execute
            parallel: Whether to execute tasks in parallel (not yet implemented)

        Returns:
            List of TaskResult objects
        """
        self._current_phase = phase_id
        self._phase_start_time = time.time()
        self._total_tasks = len(phase_tasks)
        self._completed_count = 0

        results: List[TaskResult] = []

        # Build dependency graph
        for task in phase_tasks:
            if not self.dependency_graph.has_task(task.task_id):
                self.dependency_graph.add_task(task)

        # Get execution order
        try:
            execution_levels = self.dependency_graph.get_execution_order()
        except Exception as e:
            # If we can't get execution order, fall back to sequential
            print(f"Warning: Could not determine execution order: {e}")
            execution_levels = [[task] for task in phase_tasks]

        # Execute tasks level by level
        for level_tasks in execution_levels:
            # For now, execute sequentially within each level
            # TODO: Implement parallel execution
            for task in level_tasks:
                # Skip if already completed (from previous run)
                if self.state_manager and self.state_manager.is_task_complete(
                    phase_id, task.task_id
                ):
                    # Create a result for the skipped task
                    result = TaskResult(
                        task_id=task.task_id,
                        phase_id=phase_id,
                        state=TaskState.SKIPPED,
                        exit_code=0
                    )
                    results.append(result)
                    self._completed_count += 1
                    continue

                # Execute task
                result = self.execute_task(task)
                results.append(result)
                self._completed_count += 1

                # Stop on critical failure
                if result.failed and not task.retryable:
                    print(f"Critical failure in task {task.task_id}, stopping phase")
                    break

        return results

    def get_progress(self, phase_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get execution progress for a phase.

        Args:
            phase_id: Phase identifier (uses current phase if not specified)

        Returns:
            Dictionary with progress information
        """
        phase_id = phase_id or self._current_phase

        if not phase_id:
            return {
                "phase_id": None,
                "total_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "completion_percentage": 0,
                "elapsed_time": 0,
                "estimated_remaining": 0
            }

        elapsed = 0
        if self._phase_start_time:
            elapsed = time.time() - self._phase_start_time

        # Calculate completion percentage
        completion_pct = 0
        if self._total_tasks > 0:
            completion_pct = (self._completed_count / self._total_tasks) * 100

        # Estimate remaining time
        estimated_remaining = 0
        if self._completed_count > 0 and completion_pct < 100:
            avg_time_per_task = elapsed / self._completed_count
            remaining_tasks = self._total_tasks - self._completed_count
            estimated_remaining = avg_time_per_task * remaining_tasks

        return {
            "phase_id": phase_id,
            "total_tasks": self._total_tasks,
            "completed_tasks": len(self._completed_tasks),
            "failed_tasks": len(self._failed_tasks),
            "completion_percentage": completion_pct,
            "elapsed_time": elapsed,
            "estimated_remaining": estimated_remaining
        }

    def _execute_with_timeout(
        self,
        task_def: TaskDefinition,
        result: TaskResult,
        kwargs: Dict[str, Any]
    ) -> TaskResult:
        """
        Execute task with timeout enforcement.

        Args:
            task_def: Task definition
            result: TaskResult to populate
            kwargs: Additional arguments

        Returns:
            Updated TaskResult
        """
        # Set up timeout handler
        def timeout_handler(signum, frame):
            raise TaskTimeoutError(
                f"Task {task_def.task_id} exceeded timeout of {task_def.timeout}s"
            )

        # Execute task based on type
        if task_def.script_path:
            # Execute bash script
            result = self._execute_bash_script(task_def, result)

        elif task_def.function:
            # Execute Python function with timeout
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(task_def.timeout)

            try:
                result = self._execute_python_function(task_def, result, kwargs)
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)

        return result

    def _execute_bash_script(
        self,
        task_def: TaskDefinition,
        result: TaskResult
    ) -> TaskResult:
        """
        Execute bash task script.

        Args:
            task_def: Task definition
            result: TaskResult to populate

        Returns:
            Updated TaskResult
        """
        # Import here to avoid circular dependency
        from core.subprocess_runner import run_task_script

        try:
            exit_code = run_task_script(
                Path(task_def.script_path),
                task_def.phase_id,
                task_def.task_id,
                timeout=task_def.timeout
            )

            result.exit_code = exit_code
            result.state = TaskState.COMPLETED if exit_code == 0 else TaskState.FAILED

            if exit_code != 0:
                result.error = f"Script exited with code {exit_code}"

        except Exception as e:
            result.state = TaskState.FAILED
            result.error = str(e)
            result.exit_code = 1

        return result

    def _execute_python_function(
        self,
        task_def: TaskDefinition,
        result: TaskResult,
        kwargs: Dict[str, Any]
    ) -> TaskResult:
        """
        Execute Python task function.

        Args:
            task_def: Task definition
            result: TaskResult to populate
            kwargs: Additional arguments

        Returns:
            Updated TaskResult
        """
        try:
            # Call the function
            function_result = task_def.function(**kwargs)

            # Interpret result
            if isinstance(function_result, bool):
                # Boolean return: True = success, False = failure
                result.state = TaskState.COMPLETED if function_result else TaskState.FAILED
                result.exit_code = 0 if function_result else 1

            elif isinstance(function_result, int):
                # Integer return: 0 = success, non-zero = failure
                result.exit_code = function_result
                result.state = TaskState.COMPLETED if function_result == 0 else TaskState.FAILED

            elif isinstance(function_result, TaskResult):
                # TaskResult return: use directly
                result = function_result

            else:
                # Other return: assume success
                result.state = TaskState.COMPLETED
                result.exit_code = 0
                result.output = str(function_result)

        except Exception as e:
            result.state = TaskState.FAILED
            result.error = f"Function raised exception: {e}"
            result.exit_code = 1

        return result

    def reset(self):
        """Reset executor state."""
        self._completed_tasks.clear()
        self._failed_tasks.clear()
        self._current_phase = None
        self._phase_start_time = None
        self._total_tasks = 0
        self._completed_count = 0
        self.state_machine.reset_all()
