"""
Unit Tests for Phase 8: Deployment Prep Task Modules

Comprehensive tests for phase_08_deployment_prep task modules covering:
- Task 801: Entry initialization
- Task 802: Deployment setup
- Task 803: Agent selection
- Task 804: Artifact generation
- Task 805: Phase audit
- Task 806: Deployment approval
- Task 807: Closeout

Target: 6+ tests per task × 7 tasks = 42+ unit tests
Requirements: Mock LLM calls, file operations, and test all code paths
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# Import task modules
from phases.phase_08_deployment_prep.tasks import (
    task_801_entry_initialization,
    task_802_deployment_setup,
    task_803_agent_selection,
    task_804_artifact_generation,
    task_805_phase_audit,
    task_806_deployment_approval,
    task_807_closeout,
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
def phase7_closeout(temp_dirs):
    """Create Phase 7 closeout file."""
    closeout_dir = temp_dirs["outputs_dir"] / "7-integration"
    closeout_dir.mkdir(parents=True, exist_ok=True)
    closeout_file = closeout_dir / "closeout.json"

    closeout_data = {
        "phase": "7-integration",
        "status": "complete",
        "tasks_completed": 7,
        "outputs": {
            "integration_tests": "Complete",
            "test_results": "All passing"
        }
    }

    closeout_file.write_text(json.dumps(closeout_data, indent=2))
    return closeout_file

@pytest.fixture
def integration_report(temp_dirs):
    """Create integration report file."""
    integration_dir = temp_dirs["claude_dir"] / "integration"
    integration_dir.mkdir(parents=True, exist_ok=True)
    report_file = integration_dir / "integration-report.json"

    report_data = {
        "status": "complete",
        "tests_passed": 100,
        "coverage": 95
    }

    report_file.write_text(json.dumps(report_data, indent=2))
    return report_file

# ============================================================================
# TASK 801: ENTRY INITIALIZATION TESTS
# ============================================================================

class TestTask801EntryInitialization:
    """Test Task 801: Entry & Initialization."""

    def test_801_missing_phase7_closeout(self, temp_dirs):
        """Test failure when Phase 7 closeout is missing."""
        result = task_801_entry_initialization.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        assert result is False

    def test_801_phase7_incomplete_status(self, temp_dirs, phase7_closeout):
        """Test failure when Phase 7 status is not complete."""
        closeout_data = json.loads(phase7_closeout.read_text())
        closeout_data["status"] = "in_progress"
        phase7_closeout.write_text(json.dumps(closeout_data, indent=2))

        result = task_801_entry_initialization.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        assert result is False

    def test_801_successful_validation(self, temp_dirs, phase7_closeout, integration_report):
        """Test successful prerequisite validation."""
        result = task_801_entry_initialization.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        assert result is True

    def test_801_invalid_closeout_json(self, temp_dirs):
        """Test handling of invalid closeout JSON."""
        closeout_dir = temp_dirs["outputs_dir"] / "7-integration"
        closeout_dir.mkdir(parents=True, exist_ok=True)
        closeout_file = closeout_dir / "closeout.json"
        closeout_file.write_text("invalid json {")

        result = task_801_entry_initialization.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        assert result is False

    def test_801_prerequisite_display(self, temp_dirs, phase7_closeout):
        """Test prerequisite checks are displayed."""
        with patch('builtins.print') as mock_print:
            result = task_801_entry_initialization.execute(
                temp_dirs["atomic_root"],
                temp_dirs["output_dir"],
            )

            # Verify output was printed
            assert mock_print.called

# ============================================================================
# TASK 802: DEPLOYMENT SETUP TESTS
# ============================================================================

class TestTask802DeploymentSetup:
    """Test Task 802: Deployment Setup."""

    def test_802_setup_configuration(self, temp_dirs):
        """Test deployment setup creates proper configuration."""
        result = task_802_deployment_setup.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        setup_file = temp_dirs["output_dir"] / "deployment-setup.json"
        setup_data = json.loads(setup_file.read_text())

        assert "deployment_environments" in setup_data
        assert "deployment_strategy" in setup_data

    def test_802_environment_detection(self, temp_dirs):
        """Test detection of deployment environments."""
        result = task_802_deployment_setup.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        setup_file = temp_dirs["output_dir"] / "deployment-setup.json"
        setup_data = json.loads(setup_file.read_text())

        assert isinstance(setup_data["deployment_environments"], list)
        # Common environments: dev, staging, production
        assert len(setup_data["deployment_environments"]) > 0

    def test_802_deployment_strategy_selection(self, temp_dirs):
        """Test deployment strategy is selected."""
        result = task_802_deployment_setup.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        setup_file = temp_dirs["output_dir"] / "deployment-setup.json"
        setup_data = json.loads(setup_file.read_text())

        assert setup_data["deployment_strategy"] in [
            "blue-green", "rolling", "canary", "recreate"
        ]

    def test_802_timestamp_recorded(self, temp_dirs):
        """Test setup timestamp is recorded."""
        result = task_802_deployment_setup.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        setup_file = temp_dirs["output_dir"] / "deployment-setup.json"
        setup_data = json.loads(setup_file.read_text())

        assert "setup_at" in setup_data
        datetime.fromisoformat(setup_data["setup_at"])

    def test_802_output_directory_creation(self, temp_dirs):
        """Test output directory is created if missing."""
        output_dir = temp_dirs["atomic_root"] / "new_output"

        result = task_802_deployment_setup.execute(
            temp_dirs["atomic_root"],
            output_dir,
        )

        assert result is True
        assert output_dir.exists()

# ============================================================================
# TASK 803: AGENT SELECTION TESTS
# ============================================================================

class TestTask803AgentSelection:
    """Test Task 803: Agent Selection."""

    def test_803_agent_roles_structure(self, temp_dirs):
        """Test agent selection creates proper role structure."""
        result = task_803_agent_selection.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        agents_file = temp_dirs["output_dir"] / "deployment-agents.json"
        agent_data = json.loads(agents_file.read_text())

        assert "deployment_agents" in agent_data

    def test_803_deployment_specific_roles(self, temp_dirs):
        """Test deployment-specific agent roles."""
        result = task_803_agent_selection.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        agents_file = temp_dirs["output_dir"] / "deployment-agents.json"
        agent_data = json.loads(agents_file.read_text())

        required_roles = ["deployment_engineer", "devops_specialist", "release_manager"]
        for role in required_roles:
            assert role in agent_data["deployment_agents"]

    def test_803_model_assignments(self, temp_dirs):
        """Test model assignments for agents."""
        result = task_803_agent_selection.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        agents_file = temp_dirs["output_dir"] / "deployment-agents.json"
        agent_data = json.loads(agents_file.read_text())

        for role, agent_info in agent_data["deployment_agents"].items():
            assert "model" in agent_info
            assert agent_info["model"] in ["opus", "sonnet", "haiku"]

    def test_803_timestamp_included(self, temp_dirs):
        """Test selection timestamp is recorded."""
        result = task_803_agent_selection.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        agents_file = temp_dirs["output_dir"] / "deployment-agents.json"
        agent_data = json.loads(agents_file.read_text())

        assert "selected_at" in agent_data
        datetime.fromisoformat(agent_data["selected_at"])

    def test_803_interactive_selection(self, temp_dirs):
        """Test interactive agent selection mode."""
        with patch('phases.phase_08_deployment_prep.tasks.task_803_agent_selection._select_agents') as mock_select:
            mock_select.return_value = {
                "deployment_engineer": "devops-pro",
                "devops_specialist": "cloud-architect",
                "release_manager": "release-coordinator"
            }

            result = task_803_agent_selection.execute(
                temp_dirs["atomic_root"],
                temp_dirs["output_dir"],
            )

            assert result is True

# ============================================================================
# TASK 804: ARTIFACT GENERATION TESTS
# ============================================================================

class TestTask804ArtifactGeneration:
    """Test Task 804: Artifact Generation."""

    def test_804_artifact_types_generated(self, temp_dirs):
        """Test various artifact types are generated."""
        result = task_804_artifact_generation.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        artifacts_file = temp_dirs["output_dir"] / "deployment-artifacts.json"
        artifacts_data = json.loads(artifacts_file.read_text())

        assert "artifacts" in artifacts_data
        assert "deployment_manifest" in artifacts_data["artifacts"]
        assert "configuration_files" in artifacts_data["artifacts"]

    def test_804_build_artifacts_creation(self, temp_dirs):
        """Test build artifacts are created."""
        result = task_804_artifact_generation.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        artifacts_file = temp_dirs["output_dir"] / "deployment-artifacts.json"
        artifacts_data = json.loads(artifacts_file.read_text())

        assert "build_info" in artifacts_data
        assert "version" in artifacts_data["build_info"]

    def test_804_missing_deployment_setup(self, temp_dirs):
        """Test handling when deployment setup is missing."""
        with patch('phases.phase_08_deployment_prep.tasks.task_804_artifact_generation.read_json') as mock_read:
            mock_read.side_effect = FileNotFoundError("Setup not found")

            result = task_804_artifact_generation.execute(
                temp_dirs["atomic_root"],
                temp_dirs["output_dir"],
            )

            assert result is False

    def test_804_artifact_manifest_structure(self, temp_dirs):
        """Test artifact manifest has proper structure."""
        result = task_804_artifact_generation.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        artifacts_file = temp_dirs["output_dir"] / "deployment-artifacts.json"
        artifacts_data = json.loads(artifacts_file.read_text())

        assert "generated_at" in artifacts_data
        assert "artifact_count" in artifacts_data

    def test_804_timestamp_recorded(self, temp_dirs):
        """Test generation timestamp is recorded."""
        result = task_804_artifact_generation.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        artifacts_file = temp_dirs["output_dir"] / "deployment-artifacts.json"
        artifacts_data = json.loads(artifacts_file.read_text())

        assert "generated_at" in artifacts_data
        datetime.fromisoformat(artifacts_data["generated_at"])

# ============================================================================
# TASK 805: PHASE AUDIT TESTS
# ============================================================================

class TestTask805PhaseAudit:
    """Test Task 805: Phase Audit."""

    def test_805_audit_checklist(self, temp_dirs):
        """Test audit validates all checklist items."""
        result = task_805_phase_audit.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        audit_file = temp_dirs["output_dir"] / "phase-audit.json"
        audit_data = json.loads(audit_file.read_text())

        assert "checklist" in audit_data
        assert "artifacts_generated" in audit_data["checklist"]
        assert "deployment_plan_complete" in audit_data["checklist"]

    def test_805_missing_artifacts(self, temp_dirs):
        """Test audit detects missing artifacts."""
        result = task_805_phase_audit.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        # Should fail with missing artifacts
        assert result is False

    def test_805_audit_scoring(self, temp_dirs):
        """Test audit includes scoring."""
        result = task_805_phase_audit.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        audit_file = temp_dirs["output_dir"] / "phase-audit.json"
        audit_data = json.loads(audit_file.read_text())

        assert "score" in audit_data
        assert 0 <= audit_data["score"] <= 100

    def test_805_audit_timestamp(self, temp_dirs):
        """Test audit timestamp is recorded."""
        result = task_805_phase_audit.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        audit_file = temp_dirs["output_dir"] / "phase-audit.json"
        audit_data = json.loads(audit_file.read_text())

        assert "audited_at" in audit_data
        datetime.fromisoformat(audit_data["audited_at"])

    def test_805_recommendations_included(self, temp_dirs):
        """Test audit includes recommendations."""
        result = task_805_phase_audit.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        audit_file = temp_dirs["output_dir"] / "phase-audit.json"
        audit_data = json.loads(audit_file.read_text())

        assert "recommendations" in audit_data

# ============================================================================
# TASK 806: DEPLOYMENT APPROVAL TESTS
# ============================================================================

class TestTask806DeploymentApproval:
    """Test Task 806: Deployment Approval."""

    def test_806_approval_criteria_validation(self, temp_dirs):
        """Test approval validates all criteria."""
        result = task_806_deployment_approval.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        approval_file = temp_dirs["output_dir"] / "deployment-approval.json"
        approval_data = json.loads(approval_file.read_text())

        assert "criteria" in approval_data
        assert "artifacts_complete" in approval_data["criteria"]

    def test_806_missing_artifacts(self, temp_dirs):
        """Test handling when artifacts are missing."""
        with patch('phases.phase_08_deployment_prep.tasks.task_806_deployment_approval.read_json') as mock_read:
            mock_read.side_effect = FileNotFoundError("Artifacts not found")

            result = task_806_deployment_approval.execute(
                temp_dirs["atomic_root"],
                temp_dirs["output_dir"],
            )

            assert result is False

    def test_806_failing_approval_criteria(self, temp_dirs):
        """Test rejection when approval criteria not met."""
        # Create incomplete audit
        audit_file = temp_dirs["output_dir"] / "phase-audit.json"
        audit_file.write_text(json.dumps({
            "score": 50,
            "checklist": {"artifacts_generated": False}
        }))

        result = task_806_deployment_approval.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        # Should fail if criteria not met
        assert result is False

    def test_806_approval_timestamp(self, temp_dirs):
        """Test approval timestamp is recorded."""
        result = task_806_deployment_approval.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        approval_file = temp_dirs["output_dir"] / "deployment-approval.json"
        approval_data = json.loads(approval_file.read_text())

        assert "approved_at" in approval_data
        datetime.fromisoformat(approval_data["approved_at"])

    def test_806_approval_status(self, temp_dirs):
        """Test approval status is recorded."""
        result = task_806_deployment_approval.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        approval_file = temp_dirs["output_dir"] / "deployment-approval.json"
        approval_data = json.loads(approval_file.read_text())

        assert "status" in approval_data
        assert approval_data["status"] in ["approved", "rejected", "conditional"]

# ============================================================================
# TASK 807: CLOSEOUT TESTS
# ============================================================================

class TestTask807Closeout:
    """Test Task 807: Closeout."""

    def test_807_closeout_structure(self, temp_dirs):
        """Test closeout has required structure."""
        result = task_807_closeout.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        closeout_file = temp_dirs["output_dir"] / "closeout.json"
        closeout_data = json.loads(closeout_file.read_text())

        required_keys = ["phase", "status", "completed_at", "tasks_completed"]
        for key in required_keys:
            assert key in closeout_data

    def test_807_phase_status_complete(self, temp_dirs):
        """Test closeout marks phase as complete."""
        result = task_807_closeout.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        closeout_file = temp_dirs["output_dir"] / "closeout.json"
        closeout_data = json.loads(closeout_file.read_text())

        assert closeout_data["status"] == "complete"

    def test_807_deployment_summary(self, temp_dirs):
        """Test closeout includes deployment summary."""
        result = task_807_closeout.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        closeout_file = temp_dirs["output_dir"] / "closeout.json"
        closeout_data = json.loads(closeout_file.read_text())

        assert "outputs" in closeout_data
        assert "deployment_artifacts" in closeout_data["outputs"]

    def test_807_timestamp_format(self, temp_dirs):
        """Test closeout timestamp is valid ISO format."""
        result = task_807_closeout.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        closeout_file = temp_dirs["output_dir"] / "closeout.json"
        closeout_data = json.loads(closeout_file.read_text())

        datetime.fromisoformat(closeout_data["completed_at"])

    def test_807_tasks_list_included(self, temp_dirs):
        """Test closeout includes tasks list."""
        result = task_807_closeout.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        closeout_file = temp_dirs["output_dir"] / "closeout.json"
        closeout_data = json.loads(closeout_file.read_text())

        assert "tasks" in closeout_data
        assert isinstance(closeout_data["tasks"], list)

    def test_807_artifact_references(self, temp_dirs):
        """Test closeout includes artifact references."""
        result = task_807_closeout.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        closeout_file = temp_dirs["output_dir"] / "closeout.json"
        closeout_data = json.loads(closeout_file.read_text())

        assert "outputs" in closeout_data
        assert "deployment_plan" in closeout_data["outputs"]

# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestPhase08Integration:
    """Integration tests for Phase 8 task flow."""

    def test_phase08_artifact_pipeline(self, temp_dirs, phase7_closeout):
        """Test artifact pipeline from setup to approval."""
        # Setup
        task_802_deployment_setup.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        setup_file = temp_dirs["output_dir"] / "deployment-setup.json"
        assert setup_file.exists()

        # Artifact generation
        task_804_artifact_generation.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        artifacts_file = temp_dirs["output_dir"] / "deployment-artifacts.json"
        assert artifacts_file.exists()

        # Approval uses artifacts
        task_806_deployment_approval.execute(
            temp_dirs["atomic_root"],
            temp_dirs["output_dir"],
        )

        approval_file = temp_dirs["output_dir"] / "deployment-approval.json"
        assert approval_file.exists()
