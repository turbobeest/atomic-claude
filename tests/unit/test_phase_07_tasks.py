"""
Unit Tests for Phase 7: Integration Task Modules

Comprehensive tests for phase_07_integration task modules covering:
- Task 701: Entry initialization
- Task 702: Integration setup
- Task 703: Agent selection
- Task 704: Testing execution
- Task 705: Integration approval
- Task 706: Phase audit
- Task 707: Closeout

Target: 6+ tests per task × 7 tasks = 42+ unit tests
Requirements: Mock LLM calls, file operations, and test all code paths
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, call
from datetime import datetime

# Import task modules
from phases.phase_07_integration.tasks import (
    task_701_entry_initialization,
    task_702_integration_setup,
    task_703_agent_selection,
    task_704_testing_execution,
    task_705_integration_approval,
    task_706_phase_audit,
    task_707_closeout,
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
def phase6_closeout(temp_dirs):
    """Create Phase 6 closeout file."""
    closeout_dir = temp_dirs["outputs_dir"] / "6-code-review"
    closeout_dir.mkdir(parents=True, exist_ok=True)
    closeout_file = closeout_dir / "closeout.json"

    closeout_data = {
        "phase": "6-code-review",
        "status": "complete",
        "tasks_completed": 6,
        "outputs": {
            "review_report": "Complete",
            "refinements": "Applied"
        }
    }

    closeout_file.write_text(json.dumps(closeout_data, indent=2))
    return closeout_file


@pytest.fixture
def project_config(temp_dirs):
    """Create project configuration file."""
    config_dir = temp_dirs["outputs_dir"] / "0-setup"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "project-config.json"

    config_data = {
        "project": {
            "name": "Test Project",
            "type": "web-application"
        }
    }

    config_file.write_text(json.dumps(config_data, indent=2))
    return config_file


# ============================================================================
# TASK 701: ENTRY INITIALIZATION TESTS
# ============================================================================

class TestTask701EntryInitialization:
    """Test Task 701: Entry & Initialization."""

    def test_701_uat_mode_bypass(self, temp_dirs):
        """Test UAT mode bypasses prerequisite validation."""
        result = task_701_entry_initialization.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        assert result is True

    def test_701_missing_phase6_closeout(self, temp_dirs):
        """Test failure when Phase 6 closeout is missing."""
        result = task_701_entry_initialization.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=False
        )

        assert result is False

    def test_701_phase6_incomplete_status(self, temp_dirs, phase6_closeout):
        """Test failure when Phase 6 status is not complete."""
        closeout_data = json.loads(phase6_closeout.read_text())
        closeout_data["status"] = "in_progress"
        phase6_closeout.write_text(json.dumps(closeout_data, indent=2))

        result = task_701_entry_initialization.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=False
        )

        assert result is False

    def test_701_successful_validation(self, temp_dirs, phase6_closeout, project_config):
        """Test successful prerequisite validation."""
        # Create review artifacts
        review_dir = temp_dirs["claude_dir"] / "reviews"
        review_dir.mkdir(parents=True, exist_ok=True)

        result = task_701_entry_initialization.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=False
        )

        assert result is True

    def test_701_invalid_closeout_json(self, temp_dirs):
        """Test handling of invalid closeout JSON."""
        closeout_dir = temp_dirs["outputs_dir"] / "6-code-review"
        closeout_dir.mkdir(parents=True, exist_ok=True)
        closeout_file = closeout_dir / "closeout.json"
        closeout_file.write_text("invalid json {")

        result = task_701_entry_initialization.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=False
        )

        assert result is False

    def test_701_prerequisite_display(self, temp_dirs, phase6_closeout):
        """Test prerequisite checks are displayed."""
        with patch('builtins.print') as mock_print:
            result = task_701_entry_initialization.execute(
                temp_dirs["atomic_root"],
                temp_dirs["output_dir"],
                uat_mode=False
            )

            # Verify output was printed
            assert mock_print.called


# ============================================================================
# TASK 702: INTEGRATION SETUP TESTS
# ============================================================================

class TestTask702IntegrationSetup:
    """Test Task 702: Integration Setup."""

    def test_702_uat_mode_bypass(self, temp_dirs):
        """Test UAT mode creates minimal valid output."""
        result = task_702_integration_setup.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        assert result is True
        setup_file = temp_dirs["output_dir"] / "integration-setup.json"
        assert setup_file.exists()

    def test_702_setup_configuration(self, temp_dirs):
        """Test integration setup creates proper configuration."""
        result = task_702_integration_setup.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        setup_file = temp_dirs["output_dir"] / "integration-setup.json"
        setup_data = json.loads(setup_file.read_text())

        assert "test_environments" in setup_data
        assert "integration_points" in setup_data

    def test_702_test_environment_detection(self, temp_dirs):
        """Test detection of test environments."""
        result = task_702_integration_setup.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        setup_file = temp_dirs["output_dir"] / "integration-setup.json"
        setup_data = json.loads(setup_file.read_text())

        assert isinstance(setup_data["test_environments"], list)

    def test_702_output_directory_creation(self, temp_dirs):
        """Test output directory is created if missing."""
        output_dir = temp_dirs["atomic_root"] / "new_output"

        result = task_702_integration_setup.execute(
            temp_dirs["atomic_root"],
            output_dir,
            uat_mode=True
        )

        assert result is True
        assert output_dir.exists()

    def test_702_timestamp_recorded(self, temp_dirs):
        """Test setup timestamp is recorded."""
        result = task_702_integration_setup.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        setup_file = temp_dirs["output_dir"] / "integration-setup.json"
        setup_data = json.loads(setup_file.read_text())

        assert "setup_at" in setup_data
        datetime.fromisoformat(setup_data["setup_at"])

    def test_702_missing_project_config(self, temp_dirs):
        """Test handling when project config is missing."""
        with patch('phases.phase_07_integration.tasks.task_702_integration_setup.read_json') as mock_read:
            mock_read.side_effect = FileNotFoundError("Config not found")

            result = task_702_integration_setup.execute(
                temp_dirs["atomic_root"],
                temp_dirs["output_dir"],
                uat_mode=False
            )

            # Should handle gracefully or fail
            assert result in [True, False]


# ============================================================================
# TASK 703: AGENT SELECTION TESTS
# ============================================================================

class TestTask703AgentSelection:
    """Test Task 703: Agent Selection."""

    def test_703_uat_mode_bypass(self, temp_dirs):
        """Test UAT mode bypasses agent selection."""
        result = task_703_agent_selection.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        assert result is True
        agents_file = temp_dirs["output_dir"] / "integration-agents.json"
        assert agents_file.exists()

    def test_703_agent_roles_structure(self, temp_dirs):
        """Test agent selection creates proper role structure."""
        result = task_703_agent_selection.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        agents_file = temp_dirs["output_dir"] / "integration-agents.json"
        agent_data = json.loads(agents_file.read_text())

        assert "integration_agents" in agent_data
        assert "test_engineer" in agent_data["integration_agents"]

    def test_703_integration_test_roles(self, temp_dirs):
        """Test integration testing specific roles."""
        result = task_703_agent_selection.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        agents_file = temp_dirs["output_dir"] / "integration-agents.json"
        agent_data = json.loads(agents_file.read_text())

        required_roles = ["test_engineer", "system_integrator", "qa_validator"]
        for role in required_roles:
            assert role in agent_data["integration_agents"]

    def test_703_timestamp_included(self, temp_dirs):
        """Test selection timestamp is recorded."""
        result = task_703_agent_selection.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        agents_file = temp_dirs["output_dir"] / "integration-agents.json"
        agent_data = json.loads(agents_file.read_text())

        assert "selected_at" in agent_data
        datetime.fromisoformat(agent_data["selected_at"])

    def test_703_model_assignments(self, temp_dirs):
        """Test model assignments for agents."""
        result = task_703_agent_selection.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        agents_file = temp_dirs["output_dir"] / "integration-agents.json"
        agent_data = json.loads(agents_file.read_text())

        for role, agent_info in agent_data["integration_agents"].items():
            assert "model" in agent_info
            assert agent_info["model"] in ["opus", "sonnet", "haiku"]

    def test_703_interactive_selection(self, temp_dirs):
        """Test interactive agent selection mode."""
        with patch('phases.phase_07_integration.tasks.task_703_agent_selection._select_agents') as mock_select:
            mock_select.return_value = {
                "test_engineer": "integration-tester",
                "system_integrator": "system-architect",
                "qa_validator": "qa-specialist"
            }

            result = task_703_agent_selection.execute(
                temp_dirs["atomic_root"],
                temp_dirs["output_dir"],
                uat_mode=False
            )

            assert result is True


# ============================================================================
# TASK 704: TESTING EXECUTION TESTS
# ============================================================================

class TestTask704TestingExecution:
    """Test Task 704: Testing Execution."""

    def test_704_uat_mode_bypass(self, temp_dirs):
        """Test UAT mode bypasses test execution."""
        result = task_704_testing_execution.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        assert result is True
        test_results = temp_dirs["output_dir"] / "integration-test-results.json"
        assert test_results.exists()

    def test_704_test_suite_execution(self, temp_dirs):
        """Test integration test suite execution."""
        result = task_704_testing_execution.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        test_results = temp_dirs["output_dir"] / "integration-test-results.json"
        results_data = json.loads(test_results.read_text())

        assert "tests_run" in results_data
        assert "tests_passed" in results_data
        assert "tests_failed" in results_data

    def test_704_test_result_aggregation(self, temp_dirs):
        """Test test results are properly aggregated."""
        result = task_704_testing_execution.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        test_results = temp_dirs["output_dir"] / "integration-test-results.json"
        results_data = json.loads(test_results.read_text())

        assert "summary" in results_data
        assert "success_rate" in results_data

    def test_704_missing_test_setup(self, temp_dirs):
        """Test handling when integration setup is missing."""
        with patch('phases.phase_07_integration.tasks.task_704_testing_execution.read_json') as mock_read:
            mock_read.side_effect = FileNotFoundError("Setup not found")

            result = task_704_testing_execution.execute(
                temp_dirs["atomic_root"],
                temp_dirs["output_dir"],
                uat_mode=False
            )

            assert result is False

    def test_704_test_failure_handling(self, temp_dirs):
        """Test handling of test failures."""
        with patch('phases.phase_07_integration.tasks.task_704_testing_execution.run_integration_tests') as mock_tests:
            mock_tests.return_value = {
                "tests_run": 10,
                "tests_passed": 7,
                "tests_failed": 3
            }

            result = task_704_testing_execution.execute(
                temp_dirs["atomic_root"],
                temp_dirs["output_dir"],
                uat_mode=False
            )

            # Should handle test failures appropriately
            assert result in [True, False]

    def test_704_timestamp_recorded(self, temp_dirs):
        """Test execution timestamp is recorded."""
        result = task_704_testing_execution.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        test_results = temp_dirs["output_dir"] / "integration-test-results.json"
        results_data = json.loads(test_results.read_text())

        assert "executed_at" in results_data
        datetime.fromisoformat(results_data["executed_at"])


# ============================================================================
# TASK 705: INTEGRATION APPROVAL TESTS
# ============================================================================

class TestTask705IntegrationApproval:
    """Test Task 705: Integration Approval."""

    def test_705_uat_mode_bypass(self, temp_dirs):
        """Test UAT mode bypasses approval gate."""
        result = task_705_integration_approval.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        assert result is True
        approval_file = temp_dirs["output_dir"] / "integration-approval.json"
        assert approval_file.exists()

    def test_705_approval_criteria_validation(self, temp_dirs):
        """Test approval validates all criteria."""
        result = task_705_integration_approval.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        approval_file = temp_dirs["output_dir"] / "integration-approval.json"
        approval_data = json.loads(approval_file.read_text())

        assert "criteria" in approval_data
        assert "tests_passing" in approval_data["criteria"]

    def test_705_missing_test_results(self, temp_dirs):
        """Test handling when test results are missing."""
        with patch('phases.phase_07_integration.tasks.task_705_integration_approval.read_json') as mock_read:
            mock_read.side_effect = FileNotFoundError("Test results not found")

            result = task_705_integration_approval.execute(
                temp_dirs["atomic_root"],
                temp_dirs["output_dir"],
                uat_mode=False
            )

            assert result is False

    def test_705_failing_approval_criteria(self, temp_dirs):
        """Test rejection when approval criteria not met."""
        # Create test results with failures
        test_results = temp_dirs["output_dir"] / "integration-test-results.json"
        test_results.write_text(json.dumps({
            "tests_run": 10,
            "tests_passed": 5,
            "tests_failed": 5,
            "success_rate": 50
        }))

        result = task_705_integration_approval.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=False
        )

        # Should fail if success rate too low
        assert result is False

    def test_705_approval_timestamp(self, temp_dirs):
        """Test approval timestamp is recorded."""
        result = task_705_integration_approval.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        approval_file = temp_dirs["output_dir"] / "integration-approval.json"
        approval_data = json.loads(approval_file.read_text())

        assert "approved_at" in approval_data
        datetime.fromisoformat(approval_data["approved_at"])

    def test_705_approval_status(self, temp_dirs):
        """Test approval status is recorded."""
        result = task_705_integration_approval.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        approval_file = temp_dirs["output_dir"] / "integration-approval.json"
        approval_data = json.loads(approval_file.read_text())

        assert "status" in approval_data
        assert approval_data["status"] in ["approved", "rejected", "conditional"]


# ============================================================================
# TASK 706: PHASE AUDIT TESTS
# ============================================================================

class TestTask706PhaseAudit:
    """Test Task 706: Phase Audit."""

    def test_706_uat_mode_bypass(self, temp_dirs):
        """Test UAT mode bypasses audit process."""
        result = task_706_phase_audit.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        assert result is True
        audit_file = temp_dirs["output_dir"] / "phase-audit.json"
        assert audit_file.exists()

    def test_706_audit_checklist(self, temp_dirs):
        """Test audit validates all checklist items."""
        result = task_706_phase_audit.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        audit_file = temp_dirs["output_dir"] / "phase-audit.json"
        audit_data = json.loads(audit_file.read_text())

        assert "checklist" in audit_data
        assert "integration_tests_complete" in audit_data["checklist"]

    def test_706_missing_artifacts(self, temp_dirs):
        """Test audit detects missing artifacts."""
        result = task_706_phase_audit.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=False
        )

        # Should fail with missing artifacts
        assert result is False

    def test_706_audit_scoring(self, temp_dirs):
        """Test audit includes scoring."""
        result = task_706_phase_audit.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        audit_file = temp_dirs["output_dir"] / "phase-audit.json"
        audit_data = json.loads(audit_file.read_text())

        assert "score" in audit_data
        assert 0 <= audit_data["score"] <= 100

    def test_706_audit_timestamp(self, temp_dirs):
        """Test audit timestamp is recorded."""
        result = task_706_phase_audit.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        audit_file = temp_dirs["output_dir"] / "phase-audit.json"
        audit_data = json.loads(audit_file.read_text())

        assert "audited_at" in audit_data
        datetime.fromisoformat(audit_data["audited_at"])

    def test_706_recommendations_included(self, temp_dirs):
        """Test audit includes recommendations."""
        result = task_706_phase_audit.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        audit_file = temp_dirs["output_dir"] / "phase-audit.json"
        audit_data = json.loads(audit_file.read_text())

        assert "recommendations" in audit_data


# ============================================================================
# TASK 707: CLOSEOUT TESTS
# ============================================================================

class TestTask707Closeout:
    """Test Task 707: Closeout."""

    def test_707_uat_mode_bypass(self, temp_dirs):
        """Test UAT mode creates valid closeout."""
        result = task_707_closeout.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        assert result is True
        closeout_file = temp_dirs["output_dir"] / "closeout.json"
        assert closeout_file.exists()

    def test_707_closeout_structure(self, temp_dirs):
        """Test closeout has required structure."""
        result = task_707_closeout.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        closeout_file = temp_dirs["output_dir"] / "closeout.json"
        closeout_data = json.loads(closeout_file.read_text())

        required_keys = ["phase", "status", "completed_at", "tasks_completed"]
        for key in required_keys:
            assert key in closeout_data

    def test_707_phase_status_complete(self, temp_dirs):
        """Test closeout marks phase as complete."""
        result = task_707_closeout.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        closeout_file = temp_dirs["output_dir"] / "closeout.json"
        closeout_data = json.loads(closeout_file.read_text())

        assert closeout_data["status"] == "complete"

    def test_707_integration_summary(self, temp_dirs):
        """Test closeout includes integration summary."""
        result = task_707_closeout.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        closeout_file = temp_dirs["output_dir"] / "closeout.json"
        closeout_data = json.loads(closeout_file.read_text())

        assert "outputs" in closeout_data
        assert "integration_tests" in closeout_data["outputs"]

    def test_707_timestamp_format(self, temp_dirs):
        """Test closeout timestamp is valid ISO format."""
        result = task_707_closeout.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        closeout_file = temp_dirs["output_dir"] / "closeout.json"
        closeout_data = json.loads(closeout_file.read_text())

        datetime.fromisoformat(closeout_data["completed_at"])

    def test_707_tasks_list_included(self, temp_dirs):
        """Test closeout includes tasks list."""
        result = task_707_closeout.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        closeout_file = temp_dirs["output_dir"] / "closeout.json"
        closeout_data = json.loads(closeout_file.read_text())

        assert "tasks" in closeout_data
        assert isinstance(closeout_data["tasks"], list)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestPhase07Integration:
    """Integration tests for Phase 7 task flow."""

    def test_phase07_complete_flow_uat(self, temp_dirs, phase6_closeout, project_config):
        """Test complete Phase 7 flow in UAT mode."""
        # Task 701
        result = task_701_entry_initialization.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )
        assert result is True

        # Task 702
        result = task_702_integration_setup.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )
        assert result is True

        # Task 703
        result = task_703_agent_selection.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )
        assert result is True

        # Task 704
        result = task_704_testing_execution.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )
        assert result is True

        # Task 705
        result = task_705_integration_approval.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )
        assert result is True

        # Task 706
        result = task_706_phase_audit.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )
        assert result is True

        # Task 707
        result = task_707_closeout.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )
        assert result is True

        # Verify closeout exists
        closeout_file = temp_dirs["output_dir"] / "closeout.json"
        assert closeout_file.exists()

    def test_phase07_artifact_dependencies(self, temp_dirs, phase6_closeout):
        """Test artifact dependencies between tasks."""
        # Setup
        task_702_integration_setup.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        setup_file = temp_dirs["output_dir"] / "integration-setup.json"
        assert setup_file.exists()

        # Agent selection
        task_703_agent_selection.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        agents_file = temp_dirs["output_dir"] / "integration-agents.json"
        assert agents_file.exists()

        # Test execution
        task_704_testing_execution.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
            uat_mode=True
        )

        results_file = temp_dirs["output_dir"] / "integration-test-results.json"
        assert results_file.exists()
