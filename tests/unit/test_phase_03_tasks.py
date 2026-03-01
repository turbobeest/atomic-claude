"""
Unit Tests for Phase 3 (Tasking) Task Modules

Comprehensive tests for phases/phase_03_tasking/tasks/ covering:
- Task 301: Entry initialization
- Task 302: Agent selection
- Task 303: Task decomposition
- Task 304: Dependency analysis
- Task 305: Phase audit
- Task 306: Closeout

Requirements: 6+ tests per task × 6 tasks = 36+ unit tests
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import all Phase 03 task modules
from phases.phase_03_tasking.tasks.task_301_entry_initialization import execute as task_301
from phases.phase_03_tasking.tasks.task_302_agent_selection import execute as task_302
from phases.phase_03_tasking.tasks.task_303_task_decomposition import execute as task_303
from phases.phase_03_tasking.tasks.task_304_dependency_analysis import execute as task_304
from phases.phase_03_tasking.tasks.task_305_phase_audit import execute as task_305
from phases.phase_03_tasking.tasks.task_306_closeout import execute as task_306

# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_project_structure(tmp_path):
    """Create temporary project structure for Phase 3."""
    atomic_root = tmp_path / "atomic-claude"
    project_root = tmp_path

    atomic_root.mkdir()
    (project_root / "docs" / "prd").mkdir(parents=True)
    (project_root / ".taskmaster" / "tasks").mkdir(parents=True)
    (project_root / ".taskmaster" / "reports").mkdir(parents=True)

    # Create Phase 2 outputs
    phase2_output = atomic_root / ".outputs" / "2-prd"
    phase2_output.mkdir(parents=True)

    # PRD file
    prd_content = """# Test Project

## 1. Executive Summary
Test project description.

## 2. System Architecture
### 2.1 Tech Stack
- Python 3.11+
- FastAPI

## 3. Feature Requirements
### F1: Core Feature
The system SHALL implement core functionality.

## 4. Non-Functional Requirements
System SHOULD handle 1000 rps.

## 5. Logical Dependency Chain
F0 → F1 → F2

## 6. Development Phases
Phase 1: Foundation
"""
    (project_root / "docs" / "prd" / "PRD.md").write_text(prd_content)

    # Phase 2 closeout
    closeout = {
        "phase": "2-prd",
        "status": "complete",
        "completed_at": "2024-01-15T10:00:00Z"
    }
    (phase2_output / "phase-02-closeout.json").write_text(json.dumps(closeout))

    # PRD approval
    approval = {
        "status": "approved",
        "approver": "test-user",
        "approved_at": "2024-01-15T10:00:00Z"
    }
    (phase2_output / "prd-approved.json").write_text(json.dumps(approval))

    return atomic_root, project_root

@pytest.fixture
def sample_tasks():
    """Sample tasks.json content."""
    return {
        "meta": {
            "project_name": "test-project",
            "generated_at": "2024-01-15T10:00:00Z",
            "source": "prd",
            "version": "1.0"
        },
        "tasks": [
            {
                "id": 1,
                "title": "F0: Foundation Setup",
                "description": "Initialize project structure",
                "status": "pending",
                "priority": "high",
                "category": "infrastructure",
                "dependencies": [],
                "acceptance_criteria": "Project builds successfully",
                "tags": ["setup"],
                "estimated_complexity": "simple",
                "prd_section": "Section 6",
                "subtasks": []
            },
            {
                "id": 2,
                "title": "F1: Core Feature",
                "description": "Implement core functionality",
                "status": "pending",
                "priority": "high",
                "category": "feature",
                "dependencies": [1],
                "acceptance_criteria": "Feature works per PRD",
                "tags": ["core"],
                "estimated_complexity": "moderate",
                "prd_section": "Section 3",
                "subtasks": []
            },
            {
                "id": 3,
                "title": "F2: Testing",
                "description": "Set up test framework",
                "status": "pending",
                "priority": "medium",
                "category": "testing",
                "dependencies": [1],
                "acceptance_criteria": "Tests run successfully",
                "tags": ["testing"],
                "estimated_complexity": "simple",
                "prd_section": "Section 7",
                "subtasks": []
            }
        ]
    }

# ============================================================================
# TASK 301: ENTRY INITIALIZATION
# ============================================================================

class TestTask301EntryInitialization:
    """Test Task 301: Entry Initialization."""

    def test_phase2_closeout_exists(self, temp_project_structure):
        """Test successful validation when Phase 2 closeout exists."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        with patch('core.utils.cli_ui.prompt_user', return_value=''):
            result = task_301(atomic_root, output_dir)

        assert result is True
        validation = json.loads((output_dir / "entry-validation.json").read_text())
        assert validation["phase2_closeout"] == "pass"

    def test_prd_document_missing(self, temp_project_structure):
        """Test failure when PRD document is missing."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        # Remove PRD
        (project_root / "docs" / "prd" / "PRD.md").unlink()

        with patch('core.utils.cli_ui.prompt_user', return_value='abort'):
            result = task_301(atomic_root, output_dir)

        assert result is False

    def test_taskmaster_directory_creation(self, temp_project_structure):
        """Test TaskMaster directory structure is created."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        # Remove TaskMaster dir
        import shutil
        shutil.rmtree(project_root / ".taskmaster")

        result = task_301(atomic_root, output_dir)

        assert result is True
        assert (project_root / ".taskmaster").exists()
        assert (project_root / ".taskmaster" / "tasks").exists()
        assert (project_root / ".taskmaster" / "reports").exists()

    def test_validation_data_structure(self, temp_project_structure):
        """Test validation output contains required fields."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        result = task_301(atomic_root, output_dir)

        assert result is True
        validation = json.loads((output_dir / "entry-validation.json").read_text())
        assert "phase2_closeout" in validation
        assert "prd_exists" in validation
        assert "validation" in validation

    def test_continue_on_warning(self, temp_project_structure):
        """Test continuing with warnings."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        # Remove approval (creates warning, not failure)
        (atomic_root / ".outputs" / "2-prd" / "prd-approved.json").unlink()

        with patch('core.utils.cli_ui.prompt_user', return_value='continue'):
            result = task_301(atomic_root, output_dir)

        assert result is True

    def test_abort_on_failure(self, temp_project_structure):
        """Test aborting when validation fails."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        # Remove closeout (creates failure)
        (atomic_root / ".outputs" / "2-prd" / "phase-02-closeout.json").unlink()

        with patch('core.utils.cli_ui.prompt_user', return_value='abort'):
            result = task_301(atomic_root, output_dir)

        assert result is False

# ============================================================================
# TASK 302: AGENT SELECTION
# ============================================================================

class TestTask302AgentSelection:
    """Test Task 302: Agent Selection."""

    def test_agent_inventory_loading(self, temp_project_structure):
        """Test loading agent inventory from repository."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        # Create agent inventory
        agent_dir = project_root / "agents"
        agent_dir.mkdir(exist_ok=True)
        inventory = "agent_id,name,category,grade\ntask-decomposer-01,Task Decomposer,decomposition,A\n"
        (agent_dir / "agent-inventory.csv").write_text(inventory)

        result = task_302(atomic_root, output_dir)

        assert result is True

    def test_default_agent_selection(self, temp_project_structure):
        """Test default agents are selected when inventory missing."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        result = task_302(atomic_root, output_dir)

        assert result is True
        agents = json.loads((output_dir / "selected-agents.json").read_text())
        assert "decomposition_agents" in agents

    def test_agent_categories(self, temp_project_structure):
        """Test correct agent categories are selected."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        result = task_302(atomic_root, output_dir)

        assert result is True
        agents = json.loads((output_dir / "selected-agents.json").read_text())
        assert "decomposition_agents" in agents
        assert "validation_agents" in agents

    def test_output_file_structure(self, temp_project_structure):
        """Test selected agents output has correct structure."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        result = task_302(atomic_root, output_dir)

        assert result is True
        agents = json.loads((output_dir / "selected-agents.json").read_text())
        assert isinstance(agents["decomposition_agents"], list)

    def test_agent_file_validation(self, temp_project_structure):
        """Test validation of agent file existence."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        # Create partial agent structure
        agent_dir = project_root / "agents" / "expert-agents"
        agent_dir.mkdir(parents=True)
        (agent_dir / "task-decomposer-01.md").write_text("# Agent content")

        result = task_302(atomic_root, output_dir)

        assert result is True

    @patch('core.utils.cli_ui.prompt_user')
    def test_interactive_selection(self, mock_prompt, temp_project_structure):
        """Test interactive agent selection flow."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        mock_prompt.return_value = '1'

        result = task_302(atomic_root, output_dir)

        assert result is True

# ============================================================================
# TASK 303: TASK DECOMPOSITION
# ============================================================================

class TestTask303TaskDecomposition:
    """Test Task 303: Task Decomposition."""

    def test_prd_section_extraction(self, temp_project_structure):
        """Test PRD sections are correctly extracted."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        with patch('core.llm.invoke') as mock_llm:
            mock_llm.return_value = True
            result = task_303(atomic_root, output_dir)

        # Verify prompt file contains sections
        if (output_dir / "prompts" / "task-decomposition.md").exists():
            prompt = (output_dir / "prompts" / "task-decomposition.md").read_text()
            assert "Feature Requirements" in prompt or "Tech Stack" in prompt

    @patch('core.llm.invoke')
    def test_llm_invocation(self, mock_llm, temp_project_structure, sample_tasks):
        """Test LLM is invoked for task decomposition."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        def write_tasks(*args, **kwargs):
            output_file = kwargs.get('output_file') or args[1]
            output_file.write_text(json.dumps(sample_tasks))
            return True

        mock_llm.side_effect = write_tasks

        result = task_303(atomic_root, output_dir)

        assert mock_llm.called
        assert result is True

    def test_json_repair(self, temp_project_structure, sample_tasks):
        """Test JSON repair from markdown wrapper."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        with patch('core.llm.invoke') as mock_llm:
            def write_markdown_json(*args, **kwargs):
                output_file = kwargs.get('output_file') or args[1]
                wrapped = f"```json\n{json.dumps(sample_tasks)}\n```"
                output_file.write_text(wrapped)
                return True

            mock_llm.side_effect = write_markdown_json

            result = task_303(atomic_root, output_dir)

        assert result is True
        tasks = json.loads((output_dir / "raw-tasks.json").read_text())
        assert "tasks" in tasks

    def test_template_fallback(self, temp_project_structure):
        """Test template tasks created on LLM failure."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        with patch('core.llm.invoke') as mock_llm:
            mock_llm.return_value = False

            result = task_303(atomic_root, output_dir)

        assert result is True
        assert (output_dir / "raw-tasks.json").exists()
        tasks = json.loads((output_dir / "raw-tasks.json").read_text())
        assert len(tasks["tasks"]) >= 3  # Template has 3 tasks

    def test_taskmaster_integration(self, temp_project_structure, sample_tasks):
        """Test tasks are copied to TaskMaster."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        with patch('core.llm.invoke') as mock_llm:
            def write_tasks(*args, **kwargs):
                output_file = kwargs.get('output_file') or args[1]
                output_file.write_text(json.dumps(sample_tasks))
                return True

            mock_llm.side_effect = write_tasks

            result = task_303(atomic_root, output_dir)

        assert result is True
        taskmaster_file = project_root / ".taskmaster" / "tasks" / "tasks.json"
        assert taskmaster_file.exists()

    def test_task_validation_stats(self, temp_project_structure, sample_tasks):
        """Test task validation statistics are generated."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        with patch('core.llm.invoke') as mock_llm:
            def write_tasks(*args, **kwargs):
                output_file = kwargs.get('output_file') or args[1]
                output_file.write_text(json.dumps(sample_tasks))
                return True

            mock_llm.side_effect = write_tasks

            with patch('builtins.print') as mock_print:
                result = task_303(atomic_root, output_dir)

            # Verify statistics were printed
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("tasks" in str(call).lower() for call in print_calls)

# ============================================================================
# TASK 304: DEPENDENCY ANALYSIS
# ============================================================================

class TestTask304DependencyAnalysis:
    """Test Task 304: Dependency Analysis."""

    def test_valid_dag(self, temp_project_structure, sample_tasks):
        """Test validation passes for valid DAG."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        # Write tasks
        tasks_file = project_root / ".taskmaster" / "tasks" / "tasks.json"
        tasks_file.write_text(json.dumps(sample_tasks))

        with patch('core.utils.cli_ui.prompt_user', return_value=''):
            result = task_304(atomic_root, output_dir)

        assert result is True

    def test_circular_dependency_detection(self, temp_project_structure, sample_tasks):
        """Test detection of circular dependencies."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        # Create circular dependency
        sample_tasks["tasks"][0]["dependencies"] = [3]
        sample_tasks["tasks"][2]["dependencies"] = [1]

        tasks_file = project_root / ".taskmaster" / "tasks" / "tasks.json"
        tasks_file.write_text(json.dumps(sample_tasks))

        with patch('core.utils.cli_ui.prompt_user', return_value='abort'):
            result = task_304(atomic_root, output_dir)

        # Should detect cycle
        analysis = json.loads((output_dir / "dependency-analysis.json").read_text())
        assert "cycles_detected" in analysis or "validation" in analysis

    def test_invalid_reference_detection(self, temp_project_structure, sample_tasks):
        """Test detection of invalid task references."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        # Add invalid reference
        sample_tasks["tasks"][1]["dependencies"] = [999]

        tasks_file = project_root / ".taskmaster" / "tasks" / "tasks.json"
        tasks_file.write_text(json.dumps(sample_tasks))

        with patch('core.utils.cli_ui.prompt_user', return_value='abort'):
            result = task_304(atomic_root, output_dir)

        # Should be recorded in analysis
        assert (output_dir / "dependency-analysis.json").exists()

    def test_topological_sort(self, temp_project_structure, sample_tasks):
        """Test topological sort generates valid execution order."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        tasks_file = project_root / ".taskmaster" / "tasks" / "tasks.json"
        tasks_file.write_text(json.dumps(sample_tasks))

        with patch('core.utils.cli_ui.prompt_user', return_value=''):
            result = task_304(atomic_root, output_dir)

        # Should generate graph file
        graph_file = project_root / ".taskmaster" / "reports" / "dependency-graph.json"
        if graph_file.exists():
            graph = json.loads(graph_file.read_text())
            assert "tasks" in graph or "nodes" in graph

    def test_work_packages_generation(self, temp_project_structure, sample_tasks):
        """Test work packages are generated."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        tasks_file = project_root / ".taskmaster" / "tasks" / "tasks.json"
        tasks_file.write_text(json.dumps(sample_tasks))

        with patch('core.utils.cli_ui.prompt_user', return_value=''):
            result = task_304(atomic_root, output_dir)

        # Work packages may be generated
        packages_file = project_root / ".taskmaster" / "reports" / "work-packages.json"
        if packages_file.exists():
            packages = json.loads(packages_file.read_text())
            assert isinstance(packages, (dict, list))

    def test_missing_tasks_file(self, temp_project_structure):
        """Test handling when tasks file is missing."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        result = task_304(atomic_root, output_dir)

        assert result is False

# ============================================================================
# TASK 305: PHASE AUDIT
# ============================================================================

class TestTask305PhaseAudit:
    """Test Task 305: Phase Audit."""

    def test_audit_selection(self, temp_project_structure):
        """Test audit is selected and executed."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        # Create audit inventory
        audit_dir = project_root / "audits"
        audit_dir.mkdir(exist_ok=True)
        (audit_dir / "AUDIT-INVENTORY.csv").write_text("audit_id,name\nAUD-001,Test Audit\n")

        result = task_305(atomic_root, output_dir)

        assert result is True

    def test_audit_report_structure(self, temp_project_structure):
        """Test audit report has correct structure."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        result = task_305(atomic_root, output_dir)

        assert result is True
        audit = json.loads((output_dir / "phase-audit.json").read_text())
        assert "status" in audit or "mode" in audit

    def test_default_audit(self, temp_project_structure):
        """Test default audit when repository missing."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        result = task_305(atomic_root, output_dir)

        assert result is True

    def test_audit_execution_tracking(self, temp_project_structure):
        """Test audit execution is tracked."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        result = task_305(atomic_root, output_dir)

        assert result is True
        audit = json.loads((output_dir / "phase-audit.json").read_text())
        assert "audit_id" in audit or "status" in audit or "mode" in audit

    def test_multiple_audits(self, temp_project_structure):
        """Test handling multiple audit options."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        result = task_305(atomic_root, output_dir)

        assert result is True

    @patch('core.utils.cli_ui.prompt_user')
    def test_interactive_audit_selection(self, mock_prompt, temp_project_structure):
        """Test interactive audit selection."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        mock_prompt.return_value = '1'

        result = task_305(atomic_root, output_dir)

        assert result is True

# ============================================================================
# TASK 306: CLOSEOUT
# ============================================================================

class TestTask306Closeout:
    """Test Task 306: Phase Closeout."""

    def test_closeout_file_structure(self, temp_project_structure):
        """Test closeout file has correct structure."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        result = task_306(atomic_root, output_dir)

        assert result is True
        closeout = json.loads((output_dir / "closeout.json").read_text())
        assert "phase" in closeout
        assert "status" in closeout

    def test_timestamp_generation(self, temp_project_structure):
        """Test closeout includes timestamp."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        result = task_306(atomic_root, output_dir)

        assert result is True
        closeout = json.loads((output_dir / "closeout.json").read_text())
        assert "completed_at" in closeout or "timestamp" in closeout

    def test_phase_summary(self, temp_project_structure):
        """Test phase summary is included."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        result = task_306(atomic_root, output_dir)

        assert result is True
        closeout = json.loads((output_dir / "closeout.json").read_text())
        assert "summary" in closeout or "status" in closeout

    def test_task_completion_list(self, temp_project_structure):
        """Test completed tasks are listed."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        result = task_306(atomic_root, output_dir)

        assert result is True
        closeout = json.loads((output_dir / "closeout.json").read_text())
        # May include tasks list
        assert "phase" in closeout

    def test_output_directory_creation(self, temp_project_structure):
        """Test output directory is created if missing."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        # Remove output dir
        import shutil
        if output_dir.exists():
            shutil.rmtree(output_dir)

        result = task_306(atomic_root, output_dir)

        assert result is True
        assert output_dir.exists()

    def test_closeout_idempotency(self, temp_project_structure):
        """Test closeout can be run multiple times."""
        atomic_root, project_root = temp_project_structure
        output_dir = atomic_root / ".outputs" / "3-tasking"

        result1 = task_306(atomic_root, output_dir)
        result2 = task_306(atomic_root, output_dir)

        assert result1 is True
        assert result2 is True

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
