"""
Task Validator

Validates task execution preconditions including dependencies, resources, and configuration.
"""

import os
import shutil
from pathlib import Path
from typing import Set, Optional

from .types import TaskDefinition, ValidationResult, TaskState
from .dependencies import TaskDependencyGraph


class TaskValidator:
    """
    Validates task execution preconditions.

    Features:
    - Pre-execution validation
    - Resource availability checks
    - Dependency validation
    - Configuration validation
    - Input validation
    """

    def __init__(
        self,
        dependency_graph: Optional[TaskDependencyGraph] = None,
        state_manager=None,
        config=None
    ):
        """
        Initialize task validator.

        Args:
            dependency_graph: Task dependency graph (optional)
            state_manager: StateManager instance (optional)
            config: Config instance (optional)
        """
        self.dependency_graph = dependency_graph
        self.state_manager = state_manager
        self.config = config

    def validate_task(
        self,
        task_def: TaskDefinition,
        completed_tasks: Optional[Set[str]] = None
    ) -> ValidationResult:
        """
        Validate task can be executed.

        Args:
            task_def: Task definition
            completed_tasks: Set of completed task IDs

        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult(valid=True)
        completed_tasks = completed_tasks or set()

        # Validate task definition
        self._validate_definition(task_def, result)

        # Validate dependencies
        if self.dependency_graph:
            self._validate_dependencies(task_def, completed_tasks, result)

        # Validate resources
        self._validate_resources(result)

        # Validate state
        if self.state_manager:
            self._validate_state(result)

        # Validate task script or function exists
        self._validate_executable(task_def, result)

        return result

    def validate_resources(self) -> bool:
        """
        Check resource availability.

        Returns:
            True if resources are available
        """
        result = ValidationResult(valid=True)
        self._validate_resources(result)
        return result.valid

    def validate_state(self) -> bool:
        """
        Check state system is ready.

        Returns:
            True if state is valid
        """
        result = ValidationResult(valid=True)
        if self.state_manager:
            self._validate_state(result)
        return result.valid

    def validate_dependencies(
        self,
        task_id: str,
        completed_tasks: Set[str]
    ) -> bool:
        """
        Check if all dependencies are satisfied.

        Args:
            task_id: Task identifier
            completed_tasks: Set of completed task IDs

        Returns:
            True if dependencies are satisfied
        """
        if not self.dependency_graph:
            return True

        return self.dependency_graph.is_ready(task_id, completed_tasks)

    def _validate_definition(
        self,
        task_def: TaskDefinition,
        result: ValidationResult
    ):
        """Validate task definition is complete."""
        if not task_def.task_id:
            result.add_error("Task ID is required")

        if not task_def.phase_id:
            result.add_error("Phase ID is required")

        if not task_def.name:
            result.add_error("Task name is required")

        if task_def.timeout < 1:
            result.add_error(f"Invalid timeout: {task_def.timeout}")

        if task_def.max_retries < 0:
            result.add_error(f"Invalid max_retries: {task_def.max_retries}")

    def _validate_dependencies(
        self,
        task_def: TaskDefinition,
        completed_tasks: Set[str],
        result: ValidationResult
    ):
        """Validate task dependencies are satisfied."""
        if not self.dependency_graph:
            return

        dependencies = self.dependency_graph.get_dependencies(task_def.task_id)

        for dep_task in dependencies:
            if dep_task.task_id not in completed_tasks:
                # Check if dependency is required
                dep_def = next(
                    (d for d in task_def.dependencies if d.task_id == dep_task.task_id),
                    None
                )

                if dep_def and dep_def.type.value == "required":
                    result.add_error(
                        f"Required dependency not completed: {dep_task.task_id} ({dep_task.name})"
                    )
                else:
                    result.add_warning(
                        f"Optional dependency not completed: {dep_task.task_id} ({dep_task.name})"
                    )

    def _validate_resources(self, result: ValidationResult):
        """Validate system resources are available."""
        # Check disk space (require at least 100MB free)
        try:
            stat = shutil.disk_usage(Path.cwd())
            free_mb = stat.free / (1024 * 1024)

            if free_mb < 100:
                result.add_error(f"Low disk space: {free_mb:.0f}MB available (need 100MB)")
            elif free_mb < 500:
                result.add_warning(f"Low disk space: {free_mb:.0f}MB available")

        except Exception as e:
            result.add_warning(f"Could not check disk space: {e}")

        # Check memory availability (basic check)
        try:
            # This is a simple check - could be enhanced with psutil
            pass
        except Exception:
            pass

        # Check network connectivity for LLM tasks (basic check)
        # This would need enhancement for production use
        pass

    def _validate_state(self, result: ValidationResult):
        """Validate state system is accessible."""
        if not self.state_manager:
            result.add_warning("StateManager not available")
            return

        try:
            # Try to load state
            state = self.state_manager.load_state()
            if state is None:
                result.add_warning("Could not load state")
        except Exception as e:
            result.add_error(f"State system error: {e}")

    def _validate_executable(
        self,
        task_def: TaskDefinition,
        result: ValidationResult
    ):
        """Validate task script or function exists."""
        if task_def.script_path:
            # Validate bash script exists
            script_path = Path(task_def.script_path)
            if not script_path.exists():
                result.add_error(f"Task script not found: {task_def.script_path}")
            elif not script_path.is_file():
                result.add_error(f"Task script is not a file: {task_def.script_path}")
            elif not os.access(script_path, os.X_OK):
                result.add_warning(f"Task script is not executable: {task_def.script_path}")

        elif task_def.function:
            # Validate Python function is callable
            if not callable(task_def.function):
                result.add_error(f"Task function is not callable: {task_def.function}")

        else:
            result.add_error("Task must have either script_path or function")

    def validate_phase_preconditions(
        self,
        phase_id: str,
        previous_phase_id: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate preconditions for starting a phase.

        Args:
            phase_id: Phase identifier
            previous_phase_id: Previous phase that should be completed

        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True)

        # Check if previous phase is complete
        if previous_phase_id and self.state_manager:
            state = self.state_manager.load_state()
            prev_phase = state.get("phases", {}).get(previous_phase_id, {})

            if not prev_phase.get("completed"):
                result.add_error(f"Previous phase not completed: {previous_phase_id}")

            # Check for closeout file
            closeout_path = Path(f".outputs/{previous_phase_id}/closeout.json")
            if not closeout_path.exists():
                result.add_error(
                    f"Previous phase closeout not found: {closeout_path}"
                )

        # Check phase output directory
        phase_output_dir = Path(f".outputs/{phase_id}")
        if not phase_output_dir.exists():
            try:
                phase_output_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                result.add_error(f"Could not create phase output directory: {e}")

        # Validate configuration
        if self.config:
            try:
                # Basic config validation
                if not self.config.get("project.name"):
                    result.add_warning("Project name not configured")
            except Exception as e:
                result.add_warning(f"Config validation error: {e}")

        return result

    def validate_retry(
        self,
        task_def: TaskDefinition,
        current_retry_count: int
    ) -> ValidationResult:
        """
        Validate if task can be retried.

        Args:
            task_def: Task definition
            current_retry_count: Current number of retries

        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True)

        if not task_def.retryable:
            result.add_error("Task is not retryable")
            return result

        if current_retry_count >= task_def.max_retries:
            result.add_error(
                f"Max retries exceeded: {current_retry_count}/{task_def.max_retries}"
            )

        return result
