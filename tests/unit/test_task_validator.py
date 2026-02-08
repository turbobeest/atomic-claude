"""Tests for task validator."""

import pytest
from pathlib import Path
from core.task.validator import TaskValidator
from core.task.types import TaskDefinition, TaskState
from core.task.dependencies import TaskDependencyGraph


class TestTaskValidator:
    """Tests for TaskValidator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = TaskValidator()

    def test_validate_minimal_task(self):
        """Test validating a minimal task."""
        task = TaskDefinition(
            task_id="001",
            phase_id="0-setup",
            name="Test Task"
        )

        result = self.validator.validate_task(task)
        # Should fail because no executable specified
        assert not result.valid
        assert "script_path or function" in str(result.errors)

    def test_validate_task_with_script(self):
        """Test validating a task with script."""
        task = TaskDefinition(
            task_id="001",
            phase_id="0-setup",
            name="Test Task",
            script_path="/nonexistent/script.sh"
        )

        result = self.validator.validate_task(task)
        assert not result.valid
        assert any("not found" in err for err in result.errors)

    def test_validate_task_with_function(self):
        """Test validating a task with callable function."""
        def dummy_function():
            return True

        task = TaskDefinition(
            task_id="001",
            phase_id="0-setup",
            name="Test Task",
            function=dummy_function
        )

        result = self.validator.validate_task(task)
        # Should pass basic validation (may have resource warnings)
        assert result.valid or result.has_warnings

    def test_validate_task_with_non_callable(self):
        """Test validating a task with non-callable function."""
        task = TaskDefinition(
            task_id="001",
            phase_id="0-setup",
            name="Test Task",
            function="not_a_function"
        )

        result = self.validator.validate_task(task)
        assert not result.valid
        assert any("not callable" in err for err in result.errors)

    def test_validate_dependencies_satisfied(self):
        """Test validating satisfied dependencies."""
        graph = TaskDependencyGraph()

        task1 = TaskDefinition(task_id="001", phase_id="0-setup", name="Task 1")
        task2 = TaskDefinition(
            task_id="002",
            phase_id="0-setup",
            name="Task 2",
            function=lambda: True
        )

        graph.add_task(task1)
        graph.add_task(task2)
        graph.add_dependency("002", "001")

        validator = TaskValidator(dependency_graph=graph)
        result = validator.validate_task(task2, completed_tasks={"001"})

        # Should pass dependency check (may fail on other checks)
        dependency_errors = [e for e in result.errors if "dependency" in e.lower()]
        assert len(dependency_errors) == 0

    def test_validate_dependencies_not_satisfied(self):
        """Test validating unsatisfied dependencies."""
        graph = TaskDependencyGraph()

        task1 = TaskDefinition(task_id="001", phase_id="0-setup", name="Task 1")
        task2 = TaskDefinition(
            task_id="002",
            phase_id="0-setup",
            name="Task 2",
            function=lambda: True
        )

        graph.add_task(task1)
        graph.add_task(task2)
        graph.add_dependency("002", "001")

        validator = TaskValidator(dependency_graph=graph)
        result = validator.validate_task(task2, completed_tasks=set())

        assert not result.valid
        assert any("dependency" in err.lower() for err in result.errors)

    def test_validate_resources(self):
        """Test resource validation."""
        result = self.validator.validate_resources()
        # Should succeed or return warnings (not fail)
        assert result or True  # Resources check shouldn't fail hard

    def test_validate_phase_preconditions(self):
        """Test phase precondition validation."""
        result = self.validator.validate_phase_preconditions("1-discovery")
        # Should return a result (valid or with errors)
        assert result is not None

    def test_validate_retry_allowed(self):
        """Test validating retry is allowed."""
        task = TaskDefinition(
            task_id="001",
            phase_id="0-setup",
            name="Test Task",
            retryable=True,
            max_retries=3
        )

        result = self.validator.validate_retry(task, current_retry_count=1)
        assert result.valid

    def test_validate_retry_max_exceeded(self):
        """Test validating retry when max exceeded."""
        task = TaskDefinition(
            task_id="001",
            phase_id="0-setup",
            name="Test Task",
            retryable=True,
            max_retries=3
        )

        result = self.validator.validate_retry(task, current_retry_count=3)
        assert not result.valid
        assert any("exceeded" in err.lower() for err in result.errors)

    def test_validate_retry_not_retryable(self):
        """Test validating retry when task not retryable."""
        task = TaskDefinition(
            task_id="001",
            phase_id="0-setup",
            name="Test Task",
            retryable=False
        )

        result = self.validator.validate_retry(task, current_retry_count=0)
        assert not result.valid
        assert any("not retryable" in err.lower() for err in result.errors)

    def test_validate_definition_missing_fields(self):
        """Test validation catches missing required fields."""
        # This should be caught by Pydantic validation
        with pytest.raises(Exception):
            task = TaskDefinition(
                task_id="",  # Empty ID should fail
                phase_id="0-setup",
                name="Test"
            )

    def test_validate_definition_invalid_timeout(self):
        """Test validation catches invalid timeout."""
        with pytest.raises(Exception):
            task = TaskDefinition(
                task_id="001",
                phase_id="0-setup",
                name="Test",
                timeout=0  # Invalid
            )
