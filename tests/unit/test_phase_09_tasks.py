"""
Unit Tests for Phase 9: Release Task Modules

Comprehensive tests for phase_09_release task modules covering:
- Task 901: Entry initialization
- Task 902: Release setup
- Task 903: Agent selection
- Task 904: Release execution
- Task 905: Release confirmation
- Task 906: Closeout

Target: 6+ tests per task × 6 tasks = 36+ unit tests
Requirements: Mock LLM calls, file operations, and test all code paths
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# Import task modules
from phases.phase_09_release.tasks import (
    task_901_entry_initialization,
    task_902_release_setup,
    task_903_agent_selection,
    task_904_release_execution,
    task_905_release_confirmation,
    task_906_closeout,
)

# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_dirs(tmp_path):
    """Create temporary directories for testing."""
    atomic_root = tmp_path / "atomic_root"
    output_dir = tmp_path / "output"
    atomic_root.mkdir()
    output_dir.mkdir()

    # Create .outputs and .claude directories
    outputs_dir = atomic_root / ".outputs"
    claude_dir = atomic_root / ".claude"
    outputs_dir.mkdir()
    claude_dir.mkdir()

    return {
        "atomic_root": atomic_root,
        "output_dir": output_dir,
        "outputs_dir": outputs_dir,
        "claude_dir": claude_dir
    }

@pytest.fixture
def phase8_closeout(temp_dirs):
    """Create Phase 8 closeout file."""
    closeout_dir = temp_dirs["outputs_dir"] / "8-deployment-prep"
    closeout_dir.mkdir(parents=True, exist_ok=True)
    closeout_file = closeout_dir / "closeout.json"

    closeout_data = {
        "phase": "8-deployment-prep",
        "status": "complete",
        "tasks_completed": 7,
        "outputs": {
            "deployment_artifacts": "Generated",
            "deployment_plan": "Complete"
        }
    }

    closeout_file.write_text(json.dumps(closeout_data, indent=2))
    return closeout_file

@pytest.fixture
def deployment_artifacts(temp_dirs):
    """Create deployment artifacts file."""
    artifacts_dir = temp_dirs["claude_dir"] / "deployment"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    artifacts_file = artifacts_dir / "deployment-artifacts.json"

    artifacts_data = {
        "status": "ready",
        "artifacts": ["build.tar.gz", "manifest.json"],
        "version": "1.0.0"
    }

    artifacts_file.write_text(json.dumps(artifacts_data, indent=2))
    return artifacts_file

# ============================================================================
# TASK 901: ENTRY INITIALIZATION TESTS
# ============================================================================

class TestTask901EntryInitialization:
    """Test Task 901: Entry & Initialization."""

    def test_901_missing_phase8_closeout(self, temp_dirs):
        """Test failure when Phase 8 closeout is missing."""
        result = task_901_entry_initialization.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        assert result is False

    def test_901_phase8_incomplete_status(self, temp_dirs, phase8_closeout):
        """Test failure when Phase 8 status is not complete."""
        closeout_data = json.loads(phase8_closeout.read_text())
        closeout_data["status"] = "in_progress"
        phase8_closeout.write_text(json.dumps(closeout_data, indent=2))

        result = task_901_entry_initialization.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        assert result is False

    def test_901_successful_validation(self, temp_dirs, phase8_closeout, deployment_artifacts):
        """Test successful prerequisite validation."""
        result = task_901_entry_initialization.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        assert result is True

    def test_901_invalid_closeout_json(self, temp_dirs):
        """Test handling of invalid closeout JSON."""
        closeout_dir = temp_dirs["outputs_dir"] / "8-deployment-prep"
        closeout_dir.mkdir(parents=True, exist_ok=True)
        closeout_file = closeout_dir / "closeout.json"
        closeout_file.write_text("invalid json {")

        result = task_901_entry_initialization.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        assert result is False

    def test_901_legacy_closeout_format(self, temp_dirs):
        """Test finding legacy format closeout file."""
        # Create legacy closeout location
        legacy_dir = temp_dirs["claude_dir"] / "closeout"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        legacy_file = legacy_dir / "phase-08-closeout.json"

        closeout_data = {
            "phase": "8-deployment-prep",
            "status": "complete",
            "tasks_completed": 7
        }
        legacy_file.write_text(json.dumps(closeout_data, indent=2))

        result = task_901_entry_initialization.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        assert result is True

    def test_901_prerequisite_display(self, temp_dirs, phase8_closeout):
        """Test prerequisite checks are displayed."""
        with patch('builtins.print') as mock_print:
            result = task_901_entry_initialization.execute(
                temp_dirs["atomic_root"],
                temp_dirs["output_dir"],
            )

            # Verify output was printed
            assert mock_print.called

# ============================================================================
# TASK 902: RELEASE SETUP TESTS
# ============================================================================

class TestTask902ReleaseSetup:
    """Test Task 902: Release Setup."""

    def test_902_setup_configuration(self, temp_dirs):
        """Test release setup creates proper configuration."""
        result = task_902_release_setup.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        setup_file = temp_dirs["output_dir"] / "release-setup.json"
        setup_data = json.loads(setup_file.read_text())

        assert "release_channels" in setup_data
        assert "release_version" in setup_data
        assert "release_type" in setup_data

    def test_902_release_channel_detection(self, temp_dirs):
        """Test detection of release channels."""
        result = task_902_release_setup.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        setup_file = temp_dirs["output_dir"] / "release-setup.json"
        setup_data = json.loads(setup_file.read_text())

        assert isinstance(setup_data["release_channels"], list)
        # Common channels: stable, beta, canary
        assert len(setup_data["release_channels"]) > 0

    def test_902_version_detection(self, temp_dirs):
        """Test release version is determined."""
        result = task_902_release_setup.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        setup_file = temp_dirs["output_dir"] / "release-setup.json"
        setup_data = json.loads(setup_file.read_text())

        assert setup_data["release_version"] is not None
        # Verify semver format (basic check)
        assert isinstance(setup_data["release_version"], str)

    def test_902_release_type_selection(self, temp_dirs):
        """Test release type is selected."""
        result = task_902_release_setup.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        setup_file = temp_dirs["output_dir"] / "release-setup.json"
        setup_data = json.loads(setup_file.read_text())

        assert setup_data["release_type"] in ["major", "minor", "patch", "hotfix"]

    def test_902_timestamp_recorded(self, temp_dirs):
        """Test setup timestamp is recorded."""
        result = task_902_release_setup.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        setup_file = temp_dirs["output_dir"] / "release-setup.json"
        setup_data = json.loads(setup_file.read_text())

        assert "setup_at" in setup_data
        datetime.fromisoformat(setup_data["setup_at"])

# ============================================================================
# TASK 903: AGENT SELECTION TESTS
# ============================================================================

class TestTask903AgentSelection:
    """Test Task 903: Agent Selection."""

    def test_903_agent_roles_structure(self, temp_dirs):
        """Test agent selection creates proper role structure."""
        result = task_903_agent_selection.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        agents_file = temp_dirs["output_dir"] / "release-agents.json"
        agent_data = json.loads(agents_file.read_text())

        assert "release_agents" in agent_data

    def test_903_release_specific_roles(self, temp_dirs):
        """Test release-specific agent roles."""
        result = task_903_agent_selection.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        agents_file = temp_dirs["output_dir"] / "release-agents.json"
        agent_data = json.loads(agents_file.read_text())

        required_roles = ["release_manager", "distribution_specialist", "release_validator"]
        for role in required_roles:
            assert role in agent_data["release_agents"]

    def test_903_model_assignments(self, temp_dirs):
        """Test model assignments for agents."""
        result = task_903_agent_selection.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        agents_file = temp_dirs["output_dir"] / "release-agents.json"
        agent_data = json.loads(agents_file.read_text())

        for role, agent_info in agent_data["release_agents"].items():
            assert "model" in agent_info
            assert agent_info["model"] in ["opus", "sonnet", "haiku"]

    def test_903_timestamp_included(self, temp_dirs):
        """Test selection timestamp is recorded."""
        result = task_903_agent_selection.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        agents_file = temp_dirs["output_dir"] / "release-agents.json"
        agent_data = json.loads(agents_file.read_text())

        assert "selected_at" in agent_data
        datetime.fromisoformat(agent_data["selected_at"])

    def test_903_interactive_selection(self, temp_dirs):
        """Test interactive agent selection mode."""
        with patch('phases.phase_09_release.tasks.task_903_agent_selection._select_agents') as mock_select:
            mock_select.return_value = {
                "release_manager": "release-coordinator",
                "distribution_specialist": "package-manager",
                "release_validator": "qa-final"
            }

            result = task_903_agent_selection.execute(
                temp_dirs["atomic_root"],
                temp_dirs["output_dir"],
            )

            assert result is True

# ============================================================================
# TASK 904: RELEASE EXECUTION TESTS
# ============================================================================

class TestTask904ReleaseExecution:
    """Test Task 904: Release Execution."""

    def test_904_release_steps_execution(self, temp_dirs):
        """Test release execution steps are tracked."""
        result = task_904_release_execution.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        execution_file = temp_dirs["output_dir"] / "release-execution.json"
        execution_data = json.loads(execution_file.read_text())

        assert "steps" in execution_data
        assert "steps_completed" in execution_data
        assert "steps_total" in execution_data

    def test_904_distribution_tracking(self, temp_dirs):
        """Test distribution to channels is tracked."""
        result = task_904_release_execution.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        execution_file = temp_dirs["output_dir"] / "release-execution.json"
        execution_data = json.loads(execution_file.read_text())

        assert "distribution" in execution_data
        assert "channels_published" in execution_data["distribution"]

    def test_904_missing_release_setup(self, temp_dirs):
        """Test handling when release setup is missing."""
        with patch('phases.phase_09_release.tasks.task_904_release_execution.read_json') as mock_read:
            mock_read.side_effect = FileNotFoundError("Setup not found")

            result = task_904_release_execution.execute(
                temp_dirs["atomic_root"],
                temp_dirs["output_dir"],
            )

            assert result is False

    def test_904_release_failure_handling(self, temp_dirs):
        """Test handling of release execution failures."""
        with patch('phases.phase_09_release.tasks.task_904_release_execution.execute_release') as mock_release:
            mock_release.return_value = {
                "success": False,
                "error": "Distribution failed"
            }

            result = task_904_release_execution.execute(
                temp_dirs["atomic_root"],
                temp_dirs["output_dir"],
            )

            # Should handle release failures
            assert result is False

    def test_904_timestamp_recorded(self, temp_dirs):
        """Test execution timestamp is recorded."""
        result = task_904_release_execution.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        execution_file = temp_dirs["output_dir"] / "release-execution.json"
        execution_data = json.loads(execution_file.read_text())

        assert "executed_at" in execution_data
        datetime.fromisoformat(execution_data["executed_at"])

# ============================================================================
# TASK 905: RELEASE CONFIRMATION TESTS
# ============================================================================

class TestTask905ReleaseConfirmation:
    """Test Task 905: Release Confirmation."""

    def test_905_confirmation_criteria_validation(self, temp_dirs):
        """Test confirmation validates all criteria."""
        result = task_905_release_confirmation.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        confirmation_file = temp_dirs["output_dir"] / "release-confirmation.json"
        confirmation_data = json.loads(confirmation_file.read_text())

        assert "criteria" in confirmation_data
        assert "release_successful" in confirmation_data["criteria"]
        assert "distribution_complete" in confirmation_data["criteria"]

    def test_905_missing_release_execution(self, temp_dirs):
        """Test handling when release execution is missing."""
        with patch('phases.phase_09_release.tasks.task_905_release_confirmation.read_json') as mock_read:
            mock_read.side_effect = FileNotFoundError("Execution not found")

            result = task_905_release_confirmation.execute(
                temp_dirs["atomic_root"],
                temp_dirs["output_dir"],
            )

            assert result is False

    def test_905_failed_release_detection(self, temp_dirs):
        """Test detection of failed release."""
        # Create failed release execution
        execution_file = temp_dirs["output_dir"] / "release-execution.json"
        execution_file.write_text(json.dumps({
            "success": False,
            "steps_completed": 3,
            "steps_total": 5
        }))

        result = task_905_release_confirmation.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        # Should fail confirmation
        assert result is False

    def test_905_confirmation_timestamp(self, temp_dirs):
        """Test confirmation timestamp is recorded."""
        result = task_905_release_confirmation.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        confirmation_file = temp_dirs["output_dir"] / "release-confirmation.json"
        confirmation_data = json.loads(confirmation_file.read_text())

        assert "confirmed_at" in confirmation_data
        datetime.fromisoformat(confirmation_data["confirmed_at"])

    def test_905_release_metadata_included(self, temp_dirs):
        """Test release metadata is included in confirmation."""
        result = task_905_release_confirmation.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        confirmation_file = temp_dirs["output_dir"] / "release-confirmation.json"
        confirmation_data = json.loads(confirmation_file.read_text())

        assert "release_version" in confirmation_data
        assert "release_channels" in confirmation_data

# ============================================================================
# TASK 906: CLOSEOUT TESTS
# ============================================================================

class TestTask906Closeout:
    """Test Task 906: Closeout."""

    def test_906_closeout_structure(self, temp_dirs):
        """Test closeout has required structure."""
        result = task_906_closeout.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        closeout_file = temp_dirs["output_dir"] / "closeout.json"
        closeout_data = json.loads(closeout_file.read_text())

        required_keys = ["phase", "phase_num", "completed_at", "tasks_completed", "summary"]
        for key in required_keys:
            assert key in closeout_data

    def test_906_phase_status_complete(self, temp_dirs):
        """Test closeout marks phase as complete."""
        result = task_906_closeout.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        closeout_file = temp_dirs["output_dir"] / "closeout.json"
        closeout_data = json.loads(closeout_file.read_text())

        assert closeout_data["phase"] == "9-release"
        assert closeout_data["phase_num"] == 9

    def test_906_release_summary(self, temp_dirs):
        """Test closeout includes release summary."""
        result = task_906_closeout.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        closeout_file = temp_dirs["output_dir"] / "closeout.json"
        closeout_data = json.loads(closeout_file.read_text())

        assert "summary" in closeout_data
        assert "completed successfully" in closeout_data["summary"].lower()

    def test_906_timestamp_format(self, temp_dirs):
        """Test closeout timestamp is valid ISO format."""
        result = task_906_closeout.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        closeout_file = temp_dirs["output_dir"] / "closeout.json"
        closeout_data = json.loads(closeout_file.read_text())

        datetime.fromisoformat(closeout_data["completed_at"])

    def test_906_tasks_list_included(self, temp_dirs):
        """Test closeout includes completed tasks list."""
        result = task_906_closeout.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        closeout_file = temp_dirs["output_dir"] / "closeout.json"
        closeout_data = json.loads(closeout_file.read_text())

        assert "tasks_completed" in closeout_data
        assert isinstance(closeout_data["tasks_completed"], list)
        # Phase 9 has 6 tasks (901-906)
        assert len(closeout_data["tasks_completed"]) == 6

    def test_906_final_phase_marker(self, temp_dirs):
        """Test closeout marks this as final phase."""
        result = task_906_closeout.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        closeout_file = temp_dirs["output_dir"] / "closeout.json"
        closeout_data = json.loads(closeout_file.read_text())

        # Phase 9 is the final phase
        assert closeout_data["phase_num"] == 9
        assert "release" in closeout_data["summary"].lower()

# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestPhase09Integration:
    """Integration tests for Phase 9 task flow."""

    def test_phase09_release_pipeline(self, temp_dirs, phase8_closeout):
        """Test release pipeline from setup to confirmation."""
        # Setup
        task_902_release_setup.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        setup_file = temp_dirs["output_dir"] / "release-setup.json"
        assert setup_file.exists()

        # Agent selection
        task_903_agent_selection.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        agents_file = temp_dirs["output_dir"] / "release-agents.json"
        assert agents_file.exists()

        # Release execution
        task_904_release_execution.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        execution_file = temp_dirs["output_dir"] / "release-execution.json"
        assert execution_file.exists()

        # Confirmation uses execution results
        task_905_release_confirmation.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        confirmation_file = temp_dirs["output_dir"] / "release-confirmation.json"
        assert confirmation_file.exists()

    def test_phase09_final_closeout_validation(self, temp_dirs, phase8_closeout):
        """Test final closeout validates entire pipeline."""
        # Execute all tasks
        task_901_entry_initialization.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )
        task_902_release_setup.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )
        task_903_agent_selection.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )
        task_904_release_execution.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )
        task_905_release_confirmation.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        # Final closeout
        result = task_906_closeout.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        assert result is True

        # Verify closeout is complete
        closeout_file = temp_dirs["output_dir"] / "closeout.json"
        closeout_data = json.loads(closeout_file.read_text())

        assert closeout_data["phase_num"] == 9
        assert len(closeout_data["tasks_completed"]) == 6
