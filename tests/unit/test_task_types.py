"""Tests for task type definitions."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from core.task.types import (
    TaskDefinition,
    TaskState,
    TaskResult,
    TaskDependency,
    DependencyType,
    StateTransition,
    ValidationResult
)


class TestTaskState:
    """Tests for TaskState enum."""

    def test_task_state_values(self):
        """Test TaskState enum values."""
        assert TaskState.PENDING.value == "pending"
        assert TaskState.RUNNING.value == "running"
        assert TaskState.COMPLETED.value == "completed"
        assert TaskState.FAILED.value == "failed"
        assert TaskState.SKIPPED.value == "skipped"


class TestTaskDependency:
    """Tests for TaskDependency model."""

    def test_create_required_dependency(self):
        """Test creating a required dependency."""
        dep = TaskDependency(task_id="001", type=DependencyType.REQUIRED)
        assert dep.task_id == "001"
        assert dep.type == DependencyType.REQUIRED

    def test_create_optional_dependency(self):
        """Test creating an optional dependency."""
        dep = TaskDependency(task_id="002", type=DependencyType.OPTIONAL)
        assert dep.task_id == "002"
        assert dep.type == DependencyType.OPTIONAL

    def test_default_dependency_type(self):
        """Test default dependency type is REQUIRED."""
        dep = TaskDependency(task_id="003")
        assert dep.type == DependencyType.REQUIRED


class TestTaskDefinition:
    """Tests for TaskDefinition model."""

    def test_create_minimal_task(self):
        """Test creating a task with minimal fields."""
        task = TaskDefinition(
            task_id="001",
            phase_id="0-setup",
            name="Test Task"
        )
        assert task.task_id == "001"
        assert task.phase_id == "0-setup"
        assert task.name == "Test Task"
        assert task.timeout == 600
        assert task.dependencies == []
        assert task.retryable is True
        assert task.max_retries == 3

    def test_create_full_task(self):
        """Test creating a task with all fields."""
        deps = [TaskDependency(task_id="001")]
        task = TaskDefinition(
            task_id="002",
            phase_id="0-setup",
            name="Test Task",
            description="A test task",
            timeout=300,
            dependencies=deps,
            script_path="/path/to/script.sh",
            retryable=False,
            max_retries=5,
            metadata={"key": "value"}
        )
        assert task.task_id == "002"
        assert task.description == "A test task"
        assert task.timeout == 300
        assert len(task.dependencies) == 1
        assert task.script_path == "/path/to/script.sh"
        assert task.retryable is False
        assert task.max_retries == 5
        assert task.metadata == {"key": "value"}

    def test_task_id_validation(self):
        """Test task ID validation."""
        # Valid numeric ID
        task = TaskDefinition(task_id="123", phase_id="0-setup", name="Test")
        assert task.task_id == "123"

        # Invalid non-numeric ID
        with pytest.raises(ValidationError):
            TaskDefinition(task_id="abc", phase_id="0-setup", name="Test")

        # Empty ID
        with pytest.raises(ValidationError):
            TaskDefinition(task_id="", phase_id="0-setup", name="Test")

    def test_timeout_validation(self):
        """Test timeout validation."""
        # Valid timeout
        task = TaskDefinition(task_id="001", phase_id="0-setup", name="Test", timeout=60)
        assert task.timeout == 60

        # Too short
        with pytest.raises(ValidationError):
            TaskDefinition(task_id="001", phase_id="0-setup", name="Test", timeout=0)

        # Too long
        with pytest.raises(ValidationError):
            TaskDefinition(task_id="001", phase_id="0-setup", name="Test", timeout=10000)

    def test_max_retries_validation(self):
        """Test max_retries validation."""
        # Valid retries
        task = TaskDefinition(
            task_id="001",
            phase_id="0-setup",
            name="Test",
            max_retries=5
        )
        assert task.max_retries == 5

        # Negative retries
        with pytest.raises(ValidationError):
            TaskDefinition(
                task_id="001",
                phase_id="0-setup",
                name="Test",
                max_retries=-1
            )

        # Too many retries
        with pytest.raises(ValidationError):
            TaskDefinition(
                task_id="001",
                phase_id="0-setup",
                name="Test",
                max_retries=20
            )


class TestStateTransition:
    """Tests for StateTransition model."""

    def test_create_transition(self):
        """Test creating a state transition."""
        transition = StateTransition(
            from_state=TaskState.PENDING,
            to_state=TaskState.RUNNING,
            reason="Task started"
        )
        assert transition.from_state == TaskState.PENDING
        assert transition.to_state == TaskState.RUNNING
        assert transition.reason == "Task started"
        assert isinstance(transition.timestamp, datetime)


class TestTaskResult:
    """Tests for TaskResult model."""

    def test_create_minimal_result(self):
        """Test creating a result with minimal fields."""
        result = TaskResult(
            task_id="001",
            phase_id="0-setup",
            state=TaskState.COMPLETED
        )
        assert result.task_id == "001"
        assert result.phase_id == "0-setup"
        assert result.state == TaskState.COMPLETED

    def test_create_full_result(self):
        """Test creating a result with all fields."""
        now = datetime.now()
        result = TaskResult(
            task_id="001",
            phase_id="0-setup",
            state=TaskState.COMPLETED,
            exit_code=0,
            output="Task output",
            error=None,
            duration=5.5,
            started_at=now,
            completed_at=now,
            artifacts=["file1.txt", "file2.json"],
            retry_count=1,
            metadata={"key": "value"}
        )
        assert result.exit_code == 0
        assert result.output == "Task output"
        assert result.duration == 5.5
        assert len(result.artifacts) == 2
        assert result.retry_count == 1

    def test_success_property(self):
        """Test success property."""
        # Successful result
        result = TaskResult(
            task_id="001",
            phase_id="0-setup",
            state=TaskState.COMPLETED,
            exit_code=0
        )
        assert result.success is True

        # Failed result
        result = TaskResult(
            task_id="001",
            phase_id="0-setup",
            state=TaskState.FAILED,
            exit_code=1
        )
        assert result.success is False

    def test_failed_property(self):
        """Test failed property."""
        result = TaskResult(
            task_id="001",
            phase_id="0-setup",
            state=TaskState.FAILED
        )
        assert result.failed is True

        result = TaskResult(
            task_id="001",
            phase_id="0-setup",
            state=TaskState.COMPLETED
        )
        assert result.failed is False

    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = TaskResult(
            task_id="001",
            phase_id="0-setup",
            state=TaskState.COMPLETED,
            exit_code=0
        )
        result_dict = result.to_dict()
        assert result_dict["task_id"] == "001"
        assert result_dict["phase_id"] == "0-setup"
        assert result_dict["state"] == "completed"
        assert result_dict["exit_code"] == 0


class TestValidationResult:
    """Tests for ValidationResult model."""

    def test_create_valid_result(self):
        """Test creating a valid validation result."""
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_add_error(self):
        """Test adding validation errors."""
        result = ValidationResult(valid=True)
        result.add_error("Error 1")
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0] == "Error 1"

    def test_add_warning(self):
        """Test adding validation warnings."""
        result = ValidationResult(valid=True)
        result.add_warning("Warning 1")
        assert result.valid is True
        assert len(result.warnings) == 1
        assert result.warnings[0] == "Warning 1"

    def test_has_errors_property(self):
        """Test has_errors property."""
        result = ValidationResult(valid=True)
        assert result.has_errors is False

        result.add_error("Error")
        assert result.has_errors is True

    def test_has_warnings_property(self):
        """Test has_warnings property."""
        result = ValidationResult(valid=True)
        assert result.has_warnings is False

        result.add_warning("Warning")
        assert result.has_warnings is True
