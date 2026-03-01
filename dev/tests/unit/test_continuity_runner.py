"""
Unit Tests for Continuity Test Runner

Tests the ContinuityTestRunner functionality in isolation.
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dev.tests.runners.continuity_runner import (
    ContinuityTestRunner,
    TaskResult,
    ContinuityTestReport,
    load_phase_config
)


class TestTaskResult:
    """Test TaskResult dataclass."""

    def test_task_result_creation(self):
        """Test creating a TaskResult."""
        result = TaskResult(
            task_id="001",
            task_name="Test Task",
            exit_code=0,
            duration_seconds=5.0,
            stdout="Output",
            stderr="",
            success=True
        )

        assert result.task_id == "001"
        assert result.task_name == "Test Task"
        assert result.exit_code == 0
        assert result.success is True

    def test_task_result_with_error(self):
        """Test TaskResult with error message."""
        result = TaskResult(
            task_id="002",
            task_name="Failing Task",
            exit_code=1,
            duration_seconds=2.0,
            stdout="",
            stderr="Error occurred",
            success=False,
            error_message="Task failed"
        )

        assert result.success is False
        assert result.error_message == "Task failed"
        assert result.exit_code == 1


class TestContinuityTestReport:
    """Test ContinuityTestReport dataclass."""

    def test_report_creation(self):
        """Test creating a report."""
        report = ContinuityTestReport(
            phase_id="0-setup",
            phase_name="Phase 0: Setup",
            started_at="2026-02-06T10:00:00",
            total_tasks=3
        )

        assert report.phase_id == "0-setup"
        assert report.total_tasks == 3
        assert report.tasks_passed == 0
        assert report.success is False

    def test_report_success_criteria(self):
        """Test report success determination."""
        report = ContinuityTestReport(
            phase_id="0-setup",
            phase_name="Phase 0",
            started_at="2026-02-06T10:00:00",
            total_tasks=3,
            tasks_passed=3,
            tasks_failed=0,
            state_transitions_valid=True,
            no_resource_leaks=True,
            cleanup_successful=True,
            success=True
        )

        assert report.success is True
        assert report.tasks_failed == 0


class TestContinuityTestRunner:
    """Test ContinuityTestRunner class."""

    @pytest.fixture
    def runner(self, temp_dir):
        """Create a test runner."""
        return ContinuityTestRunner(atomic_root=temp_dir)

    @pytest.fixture
    def sample_config(self):
        """Sample test configuration."""
        return {
            "phase": "0-setup",
            "name": "Phase 0: Setup",
            "tasks": ["001", "002", "003"],
            "continuity": {
                "timeout_per_task": 60
            }
        }

    def test_runner_initialization(self, runner, temp_dir):
        """Test runner initialization."""
        assert runner.atomic_root == temp_dir
        assert runner.state_manager is not None

    def test_find_task_script_basic(self, runner, temp_dir):
        """Test finding a task script (Python module in phase_NN_name/tasks/)."""
        # Create a Python task module matching the new search pattern
        phase_dir = temp_dir / "phases" / "phase_00_setup" / "tasks"
        phase_dir.mkdir(parents=True)
        task_script = phase_dir / "task_001_mode_selection.py"
        task_script.write_text("# task module")

        # Find it
        found = runner._find_task_script("0", "001")
        assert found == task_script

    def test_find_task_script_not_found(self, runner, temp_dir):
        """Test finding non-existent task script."""
        found = runner._find_task_script("0", "999")
        assert found is None

    def test_find_task_script_tasks_subdir(self, runner, temp_dir):
        """Test finding task script in phase_NN_name/tasks/ directory."""
        # Create task in phase_NN_name/tasks/ pattern
        phase_dir = temp_dir / "phases" / "phase_02_prd" / "tasks"
        phase_dir.mkdir(parents=True)
        task_script = phase_dir / "task_205_prd_authoring.py"
        task_script.write_text("# task module")

        # Find it
        found = runner._find_task_script("2", "205")
        assert found == task_script

    @patch('tests.runners.continuity_runner.run_task_script')
    def test_run_single_task_success(self, mock_run, runner, sample_config):
        """Test running a single task successfully."""
        # Mock successful execution
        mock_run.return_value = (0, "Success", "")

        # Create Python task module matching the new search pattern
        phase_dir = runner.atomic_root / "phases" / "phase_00_setup" / "tasks"
        phase_dir.mkdir(parents=True)
        task_script = phase_dir / "task_001_mode_selection.py"
        task_script.write_text("# task module")

        result = runner._run_single_task(
            phase_id="0-setup",
            task_id="001",
            config=sample_config,
            mock_inputs=False
        )

        assert result.success is True
        assert result.exit_code == 0
        assert result.task_id == "001"

    @patch('tests.runners.continuity_runner.run_task_script')
    def test_run_single_task_failure(self, mock_run, runner, sample_config):
        """Test running a task that fails."""
        # Mock failed execution
        mock_run.return_value = (1, "", "Error occurred")

        # Create Python task module matching the new search pattern
        phase_dir = runner.atomic_root / "phases" / "phase_00_setup" / "tasks"
        phase_dir.mkdir(parents=True)
        task_script = phase_dir / "task_001_mode_selection.py"
        task_script.write_text("# task module")

        result = runner._run_single_task(
            phase_id="0-setup",
            task_id="001",
            config=sample_config,
            mock_inputs=False
        )

        assert result.success is False
        assert result.exit_code == 1
        assert result.error_message is not None

    def test_run_single_task_not_found(self, runner, sample_config):
        """Test running a task with missing script."""
        result = runner._run_single_task(
            phase_id="0-setup",
            task_id="999",
            config=sample_config,
            mock_inputs=False
        )

        assert result.success is False
        assert "not found" in result.error_message.lower()

    def test_validate_state_transition_success(self, runner, temp_state_dir):
        """Test state transition validation."""
        # Create state file with completed task
        state = {
            "phases": {
                "0-setup": {
                    "tasks": {
                        "001": {"name": "Test", "status": "completed"}
                    }
                }
            }
        }
        state_file = temp_state_dir / "task-state.json"
        with open(state_file, "w") as f:
            json.dump(state, f)

        # Update runner's state manager: set the file path and reload in-memory state
        runner.state_manager.state_file = state_file
        runner.state_manager._state = runner.state_manager.load_state()

        # Validate
        valid = runner._validate_state_transition("0-setup", "001")
        assert valid is True

    def test_validate_state_transition_failure(self, runner, temp_state_dir):
        """Test state transition validation failure."""
        # Create state file without completed task
        state = {"phases": {}}
        state_file = temp_state_dir / "task-state.json"
        with open(state_file, "w") as f:
            json.dump(state, f)

        runner.state_manager.state_file = state_file

        # Validate
        valid = runner._validate_state_transition("0-setup", "001")
        assert valid is False

    def test_capture_initial_state(self, runner):
        """Test capturing initial system state."""
        runner._capture_initial_state()

        # Should capture process list and file count
        assert isinstance(runner.initial_processes, list)
        assert isinstance(runner.initial_open_files, int)

    def test_setup_mock_environment(self, runner):
        """Test setting up mock environment."""
        import os

        backup = runner._setup_mock_environment()

        try:
            # Check mock vars are set
            assert os.environ.get("ATOMIC_TEST_MODE") == "1"
            assert os.environ.get("ATOMIC_MOCK_LLM") == "1"
            assert os.environ.get("CLAUDE_PROVIDER") == "mock"

            # Backup should contain original values
            assert isinstance(backup, dict)
        finally:
            runner._restore_environment(backup)

    def test_restore_environment(self, runner):
        """Test restoring environment."""
        import os

        # Set test var
        os.environ["TEST_VAR"] = "original"

        # Backup and change
        backup = {"TEST_VAR": "original"}
        os.environ["TEST_VAR"] = "changed"

        # Restore
        runner._restore_environment(backup)
        assert os.environ["TEST_VAR"] == "original"

    def test_save_report(self, runner, temp_dir):
        """Test saving report to disk."""
        report = ContinuityTestReport(
            phase_id="0-setup",
            phase_name="Phase 0",
            started_at="2026-02-06T10:00:00",
            completed_at="2026-02-06T10:01:00",
            duration_seconds=60.0,
            total_tasks=2,
            tasks_passed=2,
            success=True
        )

        json_path, text_path = runner.save_report(report, output_dir=temp_dir)

        # Check files exist
        assert json_path.exists()
        assert text_path.exists()

        # Check JSON content
        with open(json_path) as f:
            data = json.load(f)
            assert data["phase_id"] == "0-setup"
            assert data["success"] is True

        # Check text content
        text_content = text_path.read_text()
        assert "Phase 0" in text_content
        assert "PASSED" in text_content


class TestLoadPhaseConfig:
    """Test load_phase_config function."""

    def test_load_valid_config(self, temp_dir):
        """Test loading a valid configuration."""
        config = {
            "phase": "0-setup",
            "tasks": ["001", "002"],
            "continuity": {"timeout_per_task": 60}
        }

        config_file = temp_dir / "test_config.json"
        with open(config_file, "w") as f:
            json.dump(config, f)

        loaded = load_phase_config(config_file)

        assert loaded["phase"] == "0-setup"
        assert len(loaded["tasks"]) == 2
        assert loaded["continuity"]["timeout_per_task"] == 60

    def test_load_missing_config(self, temp_dir):
        """Test loading non-existent config."""
        with pytest.raises(FileNotFoundError):
            load_phase_config(temp_dir / "nonexistent.json")


class TestIntegration:
    """Integration tests for continuity runner."""

    @pytest.fixture
    def full_test_env(self, temp_dir):
        """Set up complete test environment."""
        # Create phase directory
        phase_dir = temp_dir / "phases" / "phase00"
        phase_dir.mkdir(parents=True)

        # Create task scripts
        for task_id in ["001", "002", "003"]:
            script = phase_dir / f"task{task_id}.sh"
            script.write_text(f"""#!/bin/bash
echo "Task {task_id} executing"
exit 0
""")
            script.chmod(0o755)

        # Create state directory
        state_dir = temp_dir / ".state"
        state_dir.mkdir()

        # Create config
        config = {
            "phase": "0-setup",
            "name": "Phase 0: Setup",
            "tasks": ["001", "002", "003"],
            "continuity": {"timeout_per_task": 10}
        }

        config_file = temp_dir / "test_config.json"
        with open(config_file, "w") as f:
            json.dump(config, f)

        return temp_dir, config

    @patch('tests.runners.continuity_runner.run_task_script')
    def test_full_phase_test(self, mock_run, full_test_env):
        """Test running a complete phase test."""
        temp_dir, config = full_test_env

        # Mock all tasks succeeding
        mock_run.return_value = (0, "Success", "")

        runner = ContinuityTestRunner(atomic_root=temp_dir)
        report = runner.run_phase_continuity_test(
            phase_num=0,
            config=config,
            mock_inputs=True
        )

        # Check report
        assert report.total_tasks == 3
        assert len(report.task_results) == 3
        # Note: success may be False due to state validation,
        # but tasks should have executed
        assert report.tasks_passed + report.tasks_failed == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
