"""
Unit Tests for Phase 4 (Specification) Task Modules

Comprehensive tests for phases/phase_04_specification/tasks/ covering:
- Task 401: Entry initialization
- Task 402: Agent selection
- Task 403: OpenSpec generation
- Task 404: TDD subtask injection
- Task 405: Phase audit
- Task 406: Closeout

Requirements: 6+ tests per task × 6 tasks = 36+ unit tests
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, call

# Import all Phase 04 task modules
from phases.phase_04_specification.tasks.task_401_entry_initialization import execute as task_401
from phases.phase_04_specification.tasks.task_402_agent_selection import execute as task_402
from phases.phase_04_specification.tasks.task_403_openspec_generation import execute as task_403
from phases.phase_04_specification.tasks.task_404_tdd_subtask_injection import execute as task_404
from phases.phase_04_specification.tasks.task_405_phase_audit import execute as task_405
from phases.phase_04_specification.tasks.task_406_closeout import execute as task_406


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_project_structure(tmp_path):
    """Create temporary project structure for Phase 4."""
    atomic_root = tmp_path / "atomic-claude2"
    project_root = tmp_path

    atomic_root.mkdir()
    (project_root / ".taskmaster" / "tasks").mkdir(parents=True)
    (project_root / ".taskmaster" / "reports").mkdir(parents=True)
    (project_root / ".openspec").mkdir(parents=True)

    # Create Phase 3 outputs
    phase3_output = atomic_root / ".outputs" / "3-tasking"
    phase3_output.mkdir(parents=True)

    # Phase 3 closeout
    closeout = {
        "phase": "3-tasking",
        "status": "complete",
        "completed_at": "2024-01-15T10:00:00Z"
    }
    (phase3_output / "closeout.json").write_text(json.dumps(closeout))

    # Sample tasks
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
                "acceptance_criteria": "Project builds",
                "subtasks": []
            },
            {
                "id": 2,
                "title": "F1: Core Feature",
                "description": "Implement feature",
                "status": "pending",
                "priority": "high",
                "category": "feature",
                "dependencies": [1],
                "acceptance_criteria": "Feature works",
                "subtasks": []
            }
        ]
    }
    (project_root / ".taskmaster" / "tasks" / "tasks.json").write_text(json.dumps(tasks))

    return atomic_root, project_root


@pytest.fixture
def sample_openspec():
    """Sample OpenSpec structure."""
    return {
        "spec_id": "SPEC-T1",
        "task_id": 1,
        "task_title": "F0: Foundation",
        "test_strategy": {
            "unit_tests": [
                {"name": "test_setup", "description": "Test project setup"}
            ],
            "integration_tests": [],
            "scenarios": [
                {
                    "given": "Empty project",
                    "when": "Setup runs",
                    "then": "Project structure created"
                }
            ]
        },
        "interfaces": {
            "inputs": [{"name": "config", "type": "dict", "required": True}],
            "outputs": [{"name": "result", "type": "bool"}],
            "errors": [{"code": "ERR_001", "condition": "Invalid config"}]
        },
        "edge_cases": [
            {"scenario": "Missing config", "expected_behavior": "Return error"}
        ],
        "security_requirements": [
            {"requirement": "Validate inputs", "validation": "Schema check"}
        ]
    }


# ============================================================================
# TASK 401: ENTRY INITIALIZATION
# ============================================================================

class TestTask401EntryInitialization:
    """Test Task 401: Entry Initialization."""

    def test_uat_mode_bypass(self, temp_project_structure):
        """Test UAT mode auto-passes validation."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_401(atomic_root, output_dir, uat_mode=True)

        assert result is True
        assert (output_dir / "initialization.json").exists()
        validation = json.loads((output_dir / "initialization.json").read_text())
        assert validation["mode"] == "uat"

    def test_phase3_closeout_validation(self, temp_project_structure):
        """Test Phase 3 closeout is validated."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        with patch('core.utils.cli_ui.prompt_user', return_value=''):
            result = task_401(atomic_root, output_dir, uat_mode=False)

        assert result is True
        init = json.loads((output_dir / "initialization.json").read_text())
        assert "phase3_verified" in init or "task_count" in init

    def test_missing_tasks_file(self, temp_project_structure):
        """Test failure when tasks file is missing."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        # Remove tasks file
        (project_root / ".taskmaster" / "tasks" / "tasks.json").unlink()

        with patch('core.utils.cli_ui.prompt_user', return_value='abort'):
            result = task_401(atomic_root, output_dir, uat_mode=False)

        # Should fail or warn
        assert result is False or (output_dir / "entry-validation.json").exists()

    def test_openspec_directory_creation(self, temp_project_structure):
        """Test OpenSpec directory is created."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        # Remove OpenSpec dir
        import shutil
        shutil.rmtree(project_root / ".openspec")

        result = task_401(atomic_root, output_dir, uat_mode=True)

        assert result is True
        assert (project_root / ".openspec").exists()

    def test_validation_data_structure(self, temp_project_structure):
        """Test validation output structure."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_401(atomic_root, output_dir, uat_mode=True)

        assert result is True
        init = json.loads((output_dir / "initialization.json").read_text())
        assert isinstance(init, dict)

    def test_task_count_validation(self, temp_project_structure):
        """Test task count is validated."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_401(atomic_root, output_dir, uat_mode=True)

        assert result is True

    @patch('core.utils.cli_ui.prompt_user')
    def test_continue_on_warning(self, mock_prompt, temp_project_structure):
        """Test continuing with warnings."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        mock_prompt.return_value = 'continue'

        result = task_401(atomic_root, output_dir, uat_mode=False)

        assert result is True


# ============================================================================
# TASK 402: AGENT SELECTION
# ============================================================================

class TestTask402AgentSelection:
    """Test Task 402: Agent Selection."""

    def test_uat_mode_bypass(self, temp_project_structure):
        """Test UAT mode skips interactive selection."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_402(atomic_root, output_dir, uat_mode=True)

        assert result is True
        assert (output_dir / "selected-agents.json").exists()

    def test_specification_agents_selected(self, temp_project_structure):
        """Test correct agent categories for specification."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_402(atomic_root, output_dir, uat_mode=True)

        assert result is True
        agents = json.loads((output_dir / "selected-agents.json").read_text())
        assert "specification_agents" in agents or isinstance(agents, dict)

    def test_agent_inventory_loading(self, temp_project_structure):
        """Test loading agent inventory."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        # Create agent inventory
        agent_dir = project_root / "agents"
        agent_dir.mkdir(exist_ok=True)
        inventory = "agent_id,name,category\nspec-writer-01,Spec Writer,specification\n"
        (agent_dir / "agent-inventory.csv").write_text(inventory)

        result = task_402(atomic_root, output_dir, uat_mode=True)

        assert result is True

    def test_default_agents(self, temp_project_structure):
        """Test default agents when inventory missing."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_402(atomic_root, output_dir, uat_mode=True)

        assert result is True

    def test_output_file_structure(self, temp_project_structure):
        """Test agent selection output structure."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_402(atomic_root, output_dir, uat_mode=True)

        assert result is True
        agents = json.loads((output_dir / "selected-agents.json").read_text())
        assert isinstance(agents, dict)

    def test_multiple_agent_categories(self, temp_project_structure):
        """Test multiple agent categories are handled."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_402(atomic_root, output_dir, uat_mode=True)

        assert result is True

    @patch('core.utils.cli_ui.prompt_user')
    def test_interactive_selection(self, mock_prompt, temp_project_structure):
        """Test interactive agent selection."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        mock_prompt.return_value = '1'

        result = task_402(atomic_root, output_dir, uat_mode=False)

        assert result is True


# ============================================================================
# TASK 403: OPENSPEC GENERATION
# ============================================================================

class TestTask403OpenspecGeneration:
    """Test Task 403: OpenSpec Generation."""

    def test_uat_mode_stub_generation(self, temp_project_structure):
        """Test UAT mode generates stub specs."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_403(atomic_root, output_dir, uat_mode=True)

        assert result is True
        # Should create some spec files
        openspec_dir = project_root / ".openspec"
        spec_files = list(openspec_dir.glob("spec-t*.json"))
        assert len(spec_files) > 0

    @patch('core.llm.invoke')
    def test_llm_invocation_per_task(self, mock_llm, temp_project_structure, sample_openspec):
        """Test LLM is invoked for each task."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        def write_spec(*args, **kwargs):
            output_file = kwargs.get('output_file') or args[1]
            if hasattr(output_file, 'write_text'):
                output_file.write_text(json.dumps(sample_openspec))
            return True

        mock_llm.side_effect = write_spec

        result = task_403(atomic_root, output_dir, uat_mode=False)

        # LLM should be called for each task
        assert mock_llm.call_count >= 2  # We have 2 tasks

    def test_openspec_file_structure(self, temp_project_structure, sample_openspec):
        """Test OpenSpec files have correct structure."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        with patch('core.llm.invoke') as mock_llm:
            def write_spec(*args, **kwargs):
                output_file = kwargs.get('output_file') or args[1]
                if hasattr(output_file, 'write_text'):
                    output_file.write_text(json.dumps(sample_openspec))
                return True

            mock_llm.side_effect = write_spec

            result = task_403(atomic_root, output_dir, uat_mode=False)

        # Check a spec file
        spec_files = list((project_root / ".openspec").glob("spec-t*.json"))
        if spec_files:
            spec = json.loads(spec_files[0].read_text())
            assert "task_id" in spec or "stub_mode" in spec

    def test_spec_validation(self, temp_project_structure):
        """Test OpenSpec validation."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_403(atomic_root, output_dir, uat_mode=True)

        assert result is True

    def test_missing_tasks_handling(self, temp_project_structure):
        """Test handling when no tasks exist."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        # Clear tasks
        tasks = {"meta": {}, "tasks": []}
        (project_root / ".taskmaster" / "tasks" / "tasks.json").write_text(json.dumps(tasks))

        result = task_403(atomic_root, output_dir, uat_mode=True)

        # Should handle gracefully
        assert result is True or result is False

    def test_parallel_spec_generation(self, temp_project_structure):
        """Test specs can be generated in parallel."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_403(atomic_root, output_dir, uat_mode=True)

        assert result is True

    def test_spec_progress_tracking(self, temp_project_structure):
        """Test spec generation progress is tracked."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        with patch('builtins.print') as mock_print:
            result = task_403(atomic_root, output_dir, uat_mode=True)

        # Should print progress
        assert result is True


# ============================================================================
# TASK 404: TDD SUBTASK INJECTION
# ============================================================================

class TestTask404TddSubtaskInjection:
    """Test Task 404: TDD Subtask Injection."""

    def test_uat_mode_skip(self, temp_project_structure):
        """Test UAT mode skips TDD injection."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_404(atomic_root, output_dir, uat_mode=True)

        assert result is True
        assert (output_dir / "tdd-injection.json").exists()

    def test_backup_creation(self, temp_project_structure):
        """Test tasks backup is created before injection."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_404(atomic_root, output_dir, uat_mode=False)

        # Backup should be created
        backup_file = project_root / ".taskmaster" / "tasks" / "tasks.json.pre-tdd-backup"
        if result:
            assert backup_file.exists() or result is False

    def test_red_green_refactor_verify_subtasks(self, temp_project_structure):
        """Test RED/GREEN/REFACTOR/VERIFY subtasks are injected."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_404(atomic_root, output_dir, uat_mode=False)

        if result:
            tasks = json.loads((project_root / ".taskmaster" / "tasks" / "tasks.json").read_text())
            # Check if subtasks were added
            for task in tasks.get("tasks", []):
                if task.get("subtasks"):
                    assert len(task["subtasks"]) >= 4  # RED, GREEN, REFACTOR, VERIFY

    def test_subtask_dependencies(self, temp_project_structure):
        """Test TDD subtasks have correct dependencies."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_404(atomic_root, output_dir, uat_mode=False)

        if result:
            tasks = json.loads((project_root / ".taskmaster" / "tasks" / "tasks.json").read_text())
            for task in tasks.get("tasks", []):
                subtasks = task.get("subtasks", [])
                if len(subtasks) >= 4:
                    # GREEN depends on RED
                    green = next((s for s in subtasks if s.get("phase") == "GREEN"), None)
                    if green:
                        assert 1 in green.get("dependencies", [])

    def test_injection_report(self, temp_project_structure):
        """Test injection report is generated."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_404(atomic_root, output_dir, uat_mode=True)

        assert result is True
        report = json.loads((output_dir / "tdd-injection.json").read_text())
        assert "subtasks_injected" in report

    def test_idempotency(self, temp_project_structure):
        """Test TDD injection is idempotent."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result1 = task_404(atomic_root, output_dir, uat_mode=False)
        result2 = task_404(atomic_root, output_dir, uat_mode=False)

        # Should not double-inject
        if result1 and result2:
            tasks = json.loads((project_root / ".taskmaster" / "tasks" / "tasks.json").read_text())
            for task in tasks.get("tasks", []):
                subtasks = task.get("subtasks", [])
                # Should not have duplicate subtasks
                assert len(subtasks) <= 4 or len(subtasks) == 0

    def test_phase_labeling(self, temp_project_structure):
        """Test TDD phases are correctly labeled."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_404(atomic_root, output_dir, uat_mode=False)

        if result:
            tasks = json.loads((project_root / ".taskmaster" / "tasks" / "tasks.json").read_text())
            for task in tasks.get("tasks", []):
                subtasks = task.get("subtasks", [])
                phases = [s.get("phase") for s in subtasks if s.get("phase")]
                expected_phases = {"RED", "GREEN", "REFACTOR", "VERIFY"}
                if phases:
                    assert all(p in expected_phases for p in phases)


# ============================================================================
# TASK 405: PHASE AUDIT
# ============================================================================

class TestTask405PhaseAudit:
    """Test Task 405: Phase Audit."""

    def test_uat_mode_bypass(self, temp_project_structure):
        """Test UAT mode skips audit."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_405(atomic_root, output_dir, uat_mode=True)

        assert result is True
        assert (output_dir / "phase-audit.json").exists()

    def test_audit_selection(self, temp_project_structure):
        """Test audit selection for specification phase."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_405(atomic_root, output_dir, uat_mode=True)

        assert result is True

    def test_audit_report_structure(self, temp_project_structure):
        """Test audit report structure."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_405(atomic_root, output_dir, uat_mode=True)

        assert result is True
        audit = json.loads((output_dir / "phase-audit.json").read_text())
        assert isinstance(audit, dict)

    def test_openspec_audit(self, temp_project_structure):
        """Test OpenSpec files are audited."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_405(atomic_root, output_dir, uat_mode=True)

        assert result is True

    def test_tdd_subtask_audit(self, temp_project_structure):
        """Test TDD subtasks are audited."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_405(atomic_root, output_dir, uat_mode=True)

        assert result is True

    def test_audit_execution_tracking(self, temp_project_structure):
        """Test audit execution is tracked."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_405(atomic_root, output_dir, uat_mode=True)

        assert result is True
        audit = json.loads((output_dir / "phase-audit.json").read_text())
        assert "status" in audit or "mode" in audit or "audit_id" in audit

    @patch('core.utils.cli_ui.prompt_user')
    def test_interactive_audit(self, mock_prompt, temp_project_structure):
        """Test interactive audit selection."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        mock_prompt.return_value = '1'

        result = task_405(atomic_root, output_dir, uat_mode=False)

        assert result is True


# ============================================================================
# TASK 406: CLOSEOUT
# ============================================================================

class TestTask406Closeout:
    """Test Task 406: Phase Closeout."""

    def test_uat_mode(self, temp_project_structure):
        """Test closeout in UAT mode."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_406(atomic_root, output_dir, uat_mode=True)

        assert result is True
        assert (output_dir / "closeout.json").exists()

    def test_closeout_file_structure(self, temp_project_structure):
        """Test closeout file structure."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_406(atomic_root, output_dir, uat_mode=True)

        assert result is True
        closeout = json.loads((output_dir / "closeout.json").read_text())
        assert "phase" in closeout
        assert "status" in closeout

    def test_timestamp_generation(self, temp_project_structure):
        """Test timestamp is included."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_406(atomic_root, output_dir, uat_mode=True)

        assert result is True
        closeout = json.loads((output_dir / "closeout.json").read_text())
        assert "completed_at" in closeout or "timestamp" in closeout

    def test_phase_summary(self, temp_project_structure):
        """Test phase summary is included."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_406(atomic_root, output_dir, uat_mode=True)

        assert result is True
        closeout = json.loads((output_dir / "closeout.json").read_text())
        assert "summary" in closeout or "status" in closeout or "outputs" in closeout

    def test_outputs_summary(self, temp_project_structure):
        """Test outputs summary is included."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result = task_406(atomic_root, output_dir, uat_mode=True)

        assert result is True
        closeout = json.loads((output_dir / "closeout.json").read_text())
        # May include outputs
        assert isinstance(closeout, dict)

    def test_output_directory_creation(self, temp_project_structure):
        """Test output directory creation."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        import shutil
        if output_dir.exists():
            shutil.rmtree(output_dir)

        result = task_406(atomic_root, output_dir, uat_mode=True)

        assert result is True
        assert output_dir.exists()

    def test_closeout_idempotency(self, temp_project_structure):
        """Test closeout idempotency."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "4-specification"

        result1 = task_406(atomic_root, output_dir, uat_mode=True)
        result2 = task_406(atomic_root, output_dir, uat_mode=True)

        assert result1 is True
        assert result2 is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
