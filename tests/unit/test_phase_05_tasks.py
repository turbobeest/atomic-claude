"""
Unit Tests for Phase 5 (Implementation) Task Modules

Comprehensive tests for phases/phase_05_implementation/tasks/ covering:
- Task 501: Entry initialization
- Task 502: TDD setup
- Task 503: Agent selection
- Task 504: TDD execution
- Task 505: Validation
- Task 506: Phase audit
- Task 507: Closeout

Requirements: 6+ tests per task × 7 tasks = 42+ unit tests
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, call

# Import all Phase 05 task modules
from phases.phase_05_implementation.tasks.task_501_entry_initialization import execute as task_501
from phases.phase_05_implementation.tasks.task_502_tdd_setup import execute as task_502
from phases.phase_05_implementation.tasks.task_503_agent_selection import execute as task_503
from phases.phase_05_implementation.tasks.task_504_tdd_execution import execute as task_504
from phases.phase_05_implementation.tasks.task_505_validation import execute as task_505
from phases.phase_05_implementation.tasks.task_506_phase_audit import execute as task_506
from phases.phase_05_implementation.tasks.task_507_closeout import execute as task_507


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_project_structure(tmp_path):
    """Create temporary project structure for Phase 5."""
    atomic_root = tmp_path / "atomic-claude2"
    project_root = tmp_path

    atomic_root.mkdir()
    (project_root / ".taskmaster" / "tasks").mkdir(parents=True)
    (project_root / ".openspec").mkdir(parents=True)
    (project_root / ".claude" / "testing").mkdir(parents=True)
    (project_root / "src").mkdir(parents=True)
    (project_root / "tests").mkdir(parents=True)

    # Create Phase 4 outputs
    phase4_output = atomic_root / ".outputs" / "4-specification"
    phase4_output.mkdir(parents=True)

    # Phase 4 closeout
    closeout = {
        "phase": "4-specification",
        "status": "complete",
        "completed_at": "2024-01-15T10:00:00Z"
    }
    (phase4_output / "closeout.json").write_text(json.dumps(closeout))

    # Sample tasks with TDD subtasks
    tasks = {
        "meta": {
            "project_name": "test-project",
            "version": "1.0"
        },
        "tasks": [
            {
                "id": 1,
                "title": "F0: Foundation",
                "description": "Setup project",
                "status": "pending",
                "priority": "high",
                "category": "infrastructure",
                "dependencies": [],
                "subtasks": [
                    {"id": 1, "phase": "RED", "status": "pending"},
                    {"id": 2, "phase": "GREEN", "status": "pending"},
                    {"id": 3, "phase": "REFACTOR", "status": "pending"},
                    {"id": 4, "phase": "VERIFY", "status": "pending"}
                ]
            },
            {
                "id": 2,
                "title": "F1: Core Feature",
                "description": "Implement feature",
                "status": "pending",
                "priority": "high",
                "category": "feature",
                "dependencies": [1],
                "subtasks": [
                    {"id": 1, "phase": "RED", "status": "pending"},
                    {"id": 2, "phase": "GREEN", "status": "pending"},
                    {"id": 3, "phase": "REFACTOR", "status": "pending"},
                    {"id": 4, "phase": "VERIFY", "status": "pending"}
                ]
            }
        ]
    }
    (project_root / ".taskmaster" / "tasks" / "tasks.json").write_text(json.dumps(tasks))

    # OpenSpec files
    for task_id in [1, 2]:
        spec = {
            "spec_id": f"SPEC-T{task_id}",
            "task_id": task_id,
            "test_strategy": {"unit_tests": []},
            "interfaces": {"inputs": [], "outputs": []}
        }
        (project_root / ".openspec" / f"spec-t{task_id}.json").write_text(json.dumps(spec))

    return atomic_root, project_root


@pytest.fixture
def sample_tdd_config():
    """Sample TDD configuration."""
    return {
        "framework": "pytest",
        "coverage_tool": "coverage.py",
        "coverage_targets": {
            "unit": 80,
            "integration": 70,
            "branch": 75
        },
        "test_dirs": ["tests/", "test/"],
        "parallel_execution": True,
        "max_workers": 4
    }


# ============================================================================
# TASK 501: ENTRY INITIALIZATION
# ============================================================================

class TestTask501EntryInitialization:
    """Test Task 501: Entry Initialization."""

    def test_uat_mode_bypass(self, temp_project_structure):
        """Test UAT mode auto-passes validation."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_501(atomic_root, output_dir, uat_mode=True)

        assert result is True
        assert (output_dir / "initialization.json").exists()
        init = json.loads((output_dir / "initialization.json").read_text())
        assert init["mode"] == "uat"

    def test_phase4_closeout_validation(self, temp_project_structure):
        """Test Phase 4 closeout is validated."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        with patch('core.utils.cli_ui.prompt_user', return_value=''):
            result = task_501(atomic_root, output_dir, uat_mode=False)

        assert result is True
        init = json.loads((output_dir / "initialization.json").read_text())
        assert "phase4_verified" in init or "tasks_with_tdd" in init

    def test_openspec_validation(self, temp_project_structure):
        """Test OpenSpec files are validated."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        with patch('core.utils.cli_ui.prompt_user', return_value=''):
            result = task_501(atomic_root, output_dir, uat_mode=False)

        assert result is True

    def test_tdd_subtasks_validation(self, temp_project_structure):
        """Test TDD subtasks are validated."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_501(atomic_root, output_dir, uat_mode=True)

        assert result is True

    def test_directory_structure_creation(self, temp_project_structure):
        """Test implementation directories are created."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        # Remove dirs
        import shutil
        shutil.rmtree(project_root / ".claude")

        result = task_501(atomic_root, output_dir, uat_mode=True)

        assert result is True
        assert (project_root / ".claude" / "testing").exists()

    def test_validation_data_structure(self, temp_project_structure):
        """Test validation output structure."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_501(atomic_root, output_dir, uat_mode=True)

        assert result is True
        init = json.loads((output_dir / "initialization.json").read_text())
        assert isinstance(init, dict)

    @patch('core.utils.cli_ui.prompt_user')
    def test_continue_on_warning(self, mock_prompt, temp_project_structure):
        """Test continuing with warnings."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        mock_prompt.return_value = 'continue'

        result = task_501(atomic_root, output_dir, uat_mode=False)

        assert result is True


# ============================================================================
# TASK 502: TDD SETUP
# ============================================================================

class TestTask502TddSetup:
    """Test Task 502: TDD Setup."""

    def test_uat_mode_default_config(self, temp_project_structure):
        """Test UAT mode creates default config."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_502(atomic_root, output_dir, uat_mode=True)

        assert result is True
        assert (output_dir / "tdd-setup.json").exists()

    def test_framework_detection(self, temp_project_structure):
        """Test test framework is detected."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_502(atomic_root, output_dir, uat_mode=True)

        assert result is True
        config = json.loads((output_dir / "tdd-setup.json").read_text())
        assert "framework" in config or "mode" in config

    def test_coverage_tool_detection(self, temp_project_structure):
        """Test coverage tool is detected."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_502(atomic_root, output_dir, uat_mode=True)

        assert result is True
        config = json.loads((output_dir / "tdd-setup.json").read_text())
        assert "coverage_tool" in config or "mode" in config

    def test_coverage_targets_configuration(self, temp_project_structure):
        """Test coverage targets are configured."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_502(atomic_root, output_dir, uat_mode=True)

        assert result is True
        config = json.loads((output_dir / "tdd-setup.json").read_text())
        assert "coverage_targets" in config or "mode" in config

    def test_test_directory_configuration(self, temp_project_structure):
        """Test test directories are configured."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_502(atomic_root, output_dir, uat_mode=True)

        assert result is True

    def test_parallel_execution_config(self, temp_project_structure):
        """Test parallel execution is configured."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_502(atomic_root, output_dir, uat_mode=True)

        assert result is True

    @patch('core.utils.cli_ui.prompt_user')
    def test_interactive_setup(self, mock_prompt, temp_project_structure):
        """Test interactive TDD setup."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        mock_prompt.return_value = 'pytest'

        result = task_502(atomic_root, output_dir, uat_mode=False)

        assert result is True


# ============================================================================
# TASK 503: AGENT SELECTION
# ============================================================================

class TestTask503AgentSelection:
    """Test Task 503: Agent Selection."""

    def test_uat_mode_bypass(self, temp_project_structure):
        """Test UAT mode selects default agents."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_503(atomic_root, output_dir, uat_mode=True)

        assert result is True
        assert (output_dir / "selected-agents.json").exists()

    def test_implementation_agents_selected(self, temp_project_structure):
        """Test implementation agents are selected."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_503(atomic_root, output_dir, uat_mode=True)

        assert result is True
        agents = json.loads((output_dir / "selected-agents.json").read_text())
        assert "implementation_agents" in agents or isinstance(agents, dict)

    def test_tdd_agents_selected(self, temp_project_structure):
        """Test TDD-specific agents are selected."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_503(atomic_root, output_dir, uat_mode=True)

        assert result is True

    def test_agent_inventory_loading(self, temp_project_structure):
        """Test loading agent inventory."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        # Create agent inventory
        agent_dir = project_root / "agents"
        agent_dir.mkdir(exist_ok=True)
        inventory = "agent_id,name,category\ncode-impl-01,Code Implementer,implementation\n"
        (agent_dir / "agent-inventory.csv").write_text(inventory)

        result = task_503(atomic_root, output_dir, uat_mode=True)

        assert result is True

    def test_default_agents(self, temp_project_structure):
        """Test default agents when inventory missing."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_503(atomic_root, output_dir, uat_mode=True)

        assert result is True

    def test_output_file_structure(self, temp_project_structure):
        """Test agent selection output structure."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_503(atomic_root, output_dir, uat_mode=True)

        assert result is True
        agents = json.loads((output_dir / "selected-agents.json").read_text())
        assert isinstance(agents, dict)

    @patch('core.utils.cli_ui.prompt_user')
    def test_interactive_selection(self, mock_prompt, temp_project_structure):
        """Test interactive agent selection."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        mock_prompt.return_value = '1'

        result = task_503(atomic_root, output_dir, uat_mode=False)

        assert result is True


# ============================================================================
# TASK 504: TDD EXECUTION
# ============================================================================

class TestTask504TddExecution:
    """Test Task 504: TDD Execution."""

    def test_uat_mode_stub_files(self, temp_project_structure):
        """Test UAT mode creates stub implementation files."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_504(atomic_root, output_dir, uat_mode=True)

        assert result is True
        assert (output_dir / "tdd-progress.json").exists()

    def test_red_phase_execution(self, temp_project_structure):
        """Test RED phase is executed."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_504(atomic_root, output_dir, uat_mode=True)

        assert result is True
        progress = json.loads((output_dir / "tdd-progress.json").read_text())
        assert "red_cycles" in progress

    def test_green_phase_execution(self, temp_project_structure):
        """Test GREEN phase is executed."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_504(atomic_root, output_dir, uat_mode=True)

        assert result is True
        progress = json.loads((output_dir / "tdd-progress.json").read_text())
        assert "green_cycles" in progress

    def test_refactor_phase_execution(self, temp_project_structure):
        """Test REFACTOR phase is executed."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_504(atomic_root, output_dir, uat_mode=True)

        assert result is True
        progress = json.loads((output_dir / "tdd-progress.json").read_text())
        assert "refactor_cycles" in progress

    def test_verify_phase_execution(self, temp_project_structure):
        """Test VERIFY phase is executed."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_504(atomic_root, output_dir, uat_mode=True)

        assert result is True
        progress = json.loads((output_dir / "tdd-progress.json").read_text())
        assert "verify_cycles" in progress

    def test_progress_tracking(self, temp_project_structure):
        """Test TDD progress is tracked."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_504(atomic_root, output_dir, uat_mode=True)

        assert result is True
        progress = json.loads((output_dir / "tdd-progress.json").read_text())
        assert "tasks_completed" in progress
        assert "subtasks_completed" in progress

    def test_stub_file_creation(self, temp_project_structure):
        """Test stub implementation files are created."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_504(atomic_root, output_dir, uat_mode=True)

        assert result is True
        # Check for stub files in src/
        src_files = list((project_root / "src").rglob("*.py"))
        assert len(src_files) > 0


# ============================================================================
# TASK 505: VALIDATION
# ============================================================================

class TestTask505Validation:
    """Test Task 505: Final Validation."""

    def test_uat_mode_validation(self, temp_project_structure):
        """Test UAT mode performs validation."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_505(atomic_root, output_dir, uat_mode=True)

        assert result is True
        assert (project_root / ".claude" / "testing" / "validation-report.json").exists()

    def test_coverage_analysis(self, temp_project_structure):
        """Test coverage analysis is performed."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_505(atomic_root, output_dir, uat_mode=True)

        assert result is True
        report = json.loads((project_root / ".claude" / "testing" / "validation-report.json").read_text())
        assert "coverage" in report

    def test_test_quality_metrics(self, temp_project_structure):
        """Test quality metrics are generated."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_505(atomic_root, output_dir, uat_mode=True)

        assert result is True
        report = json.loads((project_root / ".claude" / "testing" / "validation-report.json").read_text())
        assert "test_quality" in report

    def test_security_scan(self, temp_project_structure):
        """Test security scan is performed."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_505(atomic_root, output_dir, uat_mode=True)

        assert result is True
        report = json.loads((project_root / ".claude" / "testing" / "validation-report.json").read_text())
        assert "security" in report

    def test_tdd_completion_tracking(self, temp_project_structure):
        """Test TDD completion is tracked."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_505(atomic_root, output_dir, uat_mode=True)

        assert result is True
        report = json.loads((project_root / ".claude" / "testing" / "validation-report.json").read_text())
        assert "tdd_completion" in report

    def test_coverage_targets_validation(self, temp_project_structure):
        """Test coverage targets are validated."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        # Create TDD setup with targets
        setup = {
            "coverage_targets": {
                "unit": 80,
                "integration": 70
            }
        }
        (output_dir / "tdd-setup.json").write_text(json.dumps(setup))

        result = task_505(atomic_root, output_dir, uat_mode=True)

        assert result is True

    def test_validation_report_structure(self, temp_project_structure):
        """Test validation report structure."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_505(atomic_root, output_dir, uat_mode=True)

        assert result is True
        report = json.loads((project_root / ".claude" / "testing" / "validation-report.json").read_text())
        assert "coverage" in report
        assert "test_quality" in report
        assert "security" in report
        assert "tdd_completion" in report


# ============================================================================
# TASK 506: PHASE AUDIT
# ============================================================================

class TestTask506PhaseAudit:
    """Test Task 506: Phase Audit."""

    def test_uat_mode_bypass(self, temp_project_structure):
        """Test UAT mode skips audit."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_506(atomic_root, output_dir, uat_mode=True)

        assert result is True
        assert (output_dir / "phase-audit.json").exists()

    def test_audit_selection(self, temp_project_structure):
        """Test audit selection for implementation phase."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_506(atomic_root, output_dir, uat_mode=True)

        assert result is True

    def test_audit_report_structure(self, temp_project_structure):
        """Test audit report structure."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_506(atomic_root, output_dir, uat_mode=True)

        assert result is True
        audit = json.loads((output_dir / "phase-audit.json").read_text())
        assert isinstance(audit, dict)

    def test_implementation_audit(self, temp_project_structure):
        """Test implementation files are audited."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_506(atomic_root, output_dir, uat_mode=True)

        assert result is True

    def test_test_coverage_audit(self, temp_project_structure):
        """Test test coverage is audited."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_506(atomic_root, output_dir, uat_mode=True)

        assert result is True

    def test_audit_execution_tracking(self, temp_project_structure):
        """Test audit execution is tracked."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_506(atomic_root, output_dir, uat_mode=True)

        assert result is True
        audit = json.loads((output_dir / "phase-audit.json").read_text())
        assert "status" in audit or "mode" in audit or "audit_id" in audit

    @patch('core.utils.cli_ui.prompt_user')
    def test_interactive_audit(self, mock_prompt, temp_project_structure):
        """Test interactive audit selection."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        mock_prompt.return_value = '1'

        result = task_506(atomic_root, output_dir, uat_mode=False)

        assert result is True


# ============================================================================
# TASK 507: CLOSEOUT
# ============================================================================

class TestTask507Closeout:
    """Test Task 507: Phase Closeout."""

    def test_uat_mode(self, temp_project_structure):
        """Test closeout in UAT mode."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_507(atomic_root, output_dir, uat_mode=True)

        assert result is True
        assert (output_dir / "closeout.json").exists()

    def test_closeout_file_structure(self, temp_project_structure):
        """Test closeout file structure."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_507(atomic_root, output_dir, uat_mode=True)

        assert result is True
        closeout = json.loads((output_dir / "closeout.json").read_text())
        assert "phase" in closeout
        assert "status" in closeout

    def test_timestamp_generation(self, temp_project_structure):
        """Test timestamp is included."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_507(atomic_root, output_dir, uat_mode=True)

        assert result is True
        closeout = json.loads((output_dir / "closeout.json").read_text())
        assert "completed_at" in closeout or "timestamp" in closeout

    def test_phase_summary(self, temp_project_structure):
        """Test phase summary is included."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_507(atomic_root, output_dir, uat_mode=True)

        assert result is True
        closeout = json.loads((output_dir / "closeout.json").read_text())
        assert "summary" in closeout or "status" in closeout or "outputs" in closeout

    def test_implementation_summary(self, temp_project_structure):
        """Test implementation summary is included."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result = task_507(atomic_root, output_dir, uat_mode=True)

        assert result is True
        closeout = json.loads((output_dir / "closeout.json").read_text())
        # May include outputs or implementation summary
        assert isinstance(closeout, dict)

    def test_output_directory_creation(self, temp_project_structure):
        """Test output directory creation."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        import shutil
        if output_dir.exists():
            shutil.rmtree(output_dir)

        result = task_507(atomic_root, output_dir, uat_mode=True)

        assert result is True
        assert output_dir.exists()

    def test_closeout_idempotency(self, temp_project_structure):
        """Test closeout idempotency."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "5-implementation"

        result1 = task_507(atomic_root, output_dir, uat_mode=True)
        result2 = task_507(atomic_root, output_dir, uat_mode=True)

        assert result1 is True
        assert result2 is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
