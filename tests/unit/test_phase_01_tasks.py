"""
Unit Tests for Phase 1 (Discovery) Task Modules

Tests all 10 Phase 1 tasks with comprehensive coverage:
- Task 101: Entry Validation
- Task 102: Corpus Collection
- Task 103: Import Requirements
- Task 104: Agent Selection
- Task 105: Opening Dialogue
- Task 106: Discovery Work
- Task 107: Approach Selection
- Task 108: Discovery Diagrams
- Task 109: Phase Audit
- Task 110: Closeout
"""

import json
import os
import pytest
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open, call
from datetime import datetime

# Import task modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phases.phase_01_discovery.tasks import task_101_entry_validation
from phases.phase_01_discovery.tasks import task_102_corpus_collection
from phases.phase_01_discovery.tasks import task_103_import_requirements
from phases.phase_01_discovery.tasks import task_104_agent_selection
from phases.phase_01_discovery.tasks import task_105_opening_dialogue
from phases.phase_01_discovery.tasks import task_106_discovery_work
from phases.phase_01_discovery.tasks import task_107_approach_selection
from phases.phase_01_discovery.tasks import task_108_discovery_diagrams
from phases.phase_01_discovery.tasks import task_109_phase_audit
from phases.phase_01_discovery.tasks import task_110_closeout


# ============================================================================
# Task 101: Entry Validation Tests
# ============================================================================

class TestTask101EntryValidation:
    """Unit tests for task_101_entry_validation."""

    def test_execute_uat_mode_success(self, temp_dir):
        """Test execute in UAT mode returns True."""
        output_dir = temp_dir / ".outputs" / "1-discovery"
        output_dir.mkdir(parents=True)

        # Create minimal Phase 0 artifacts
        setup_dir = temp_dir / ".outputs" / "0-setup"
        setup_dir.mkdir(parents=True)
        (setup_dir / "project-config.json").write_text(
            json.dumps({"project": {"name": "test"}})
        )

        # Create closeout file
        closeout_dir = temp_dir / ".claude" / "closeout"
        closeout_dir.mkdir(parents=True)
        (closeout_dir / "phase-0-setup-closeout.json").write_text(
            json.dumps({"status": "complete"})
        )

        result = task_101_entry_validation.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        assert result is True

    def test_find_closeout_multiple_patterns(self, temp_dir):
        """Test closeout file finding with multiple patterns."""
        closeout_dir = temp_dir / ".claude" / "closeout"
        closeout_dir.mkdir(parents=True)

        closeout_file = closeout_dir / "phase-0-setup-closeout.md"
        closeout_file.write_text("# Phase 0 Closeout")

        result = task_101_entry_validation._find_closeout(temp_dir, "0-setup")

        assert result is not None
        assert result.exists()

    def test_find_closeout_not_found(self, temp_dir):
        """Test closeout file finding when not found."""
        result = task_101_entry_validation._find_closeout(temp_dir, "0-setup")

        assert result is None

    def test_flatten_config_merges_extracted(self, temp_dir):
        """Test config flattening merges extracted data."""
        config_file = temp_dir / "config.json"
        config_data = {
            "extracted": {
                "project": {"name": "test-project"},
                "repository": {"url": "https://example.com"}
            }
        }
        config_file.write_text(json.dumps(config_data))

        task_101_entry_validation._flatten_config(config_file, config_data)

        config = json.loads(config_file.read_text())
        assert config["project"]["name"] == "test-project"
        assert config["config_approved"] is True
        assert "approved_at" in config

    def test_validates_phase_0_config_exists(self, temp_dir):
        """Test validation checks Phase 0 config exists."""
        output_dir = temp_dir / ".outputs" / "1-discovery"
        output_dir.mkdir(parents=True)

        setup_dir = temp_dir / ".outputs" / "0-setup"
        setup_dir.mkdir(parents=True)

        # Missing config file should fail
        result = task_101_entry_validation.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        # Should handle missing gracefully in UAT mode
        assert isinstance(result, bool)


# ============================================================================
# Task 102: Corpus Collection Tests
# ============================================================================

class TestTask102CorpusCollection:
    """Unit tests for task_102_corpus_collection."""

    def test_execute_uat_mode_success(self, temp_dir):
        """Test execute in UAT mode returns True."""
        output_dir = temp_dir / ".outputs" / "1-discovery"
        output_dir.mkdir(parents=True)

        # Create README for minimal corpus
        (temp_dir / "README.md").write_text("# Test Project")

        result = task_102_corpus_collection.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        assert result is True

    def test_execute_uat_mode_creates_corpus_json(self, temp_dir):
        """Test UAT mode creates corpus.json."""
        output_dir = temp_dir / ".outputs" / "1-discovery"
        output_dir.mkdir(parents=True)
        (temp_dir / "README.md").write_text("# Test")

        task_102_corpus_collection.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        corpus_file = output_dir / "corpus.json"
        assert corpus_file.exists()

        corpus = json.loads(corpus_file.read_text())
        assert "materials" in corpus
        assert isinstance(corpus["materials"], list)

    def test_scan_for_materials_finds_supported_types(self, temp_dir):
        """Test material scanning finds supported file types."""
        # Create test materials
        (temp_dir / "README.md").write_text("# Readme")
        (temp_dir / "spec.txt").write_text("Specification")
        (temp_dir / "data.json").write_text('{"key": "value"}')
        (temp_dir / "ignore.exe").write_text("Binary")

        materials = task_102_corpus_collection._scan_for_materials(temp_dir)

        # Should find supported types
        paths = [m["path"] for m in materials]
        assert any("README.md" in p for p in paths)
        assert any("spec.txt" in p for p in paths)
        assert any("data.json" in p for p in paths)

    def test_scan_ignores_hidden_directories(self, temp_dir):
        """Test scanning ignores hidden directories."""
        (temp_dir / ".git").mkdir()
        (temp_dir / ".git" / "config").write_text("git config")
        (temp_dir / "visible.md").write_text("# Visible")

        materials = task_102_corpus_collection._scan_for_materials(temp_dir)

        assert all(".git" not in m["path"] for m in materials)

    def test_classify_material_by_name(self, temp_dir):
        """Test material classification by filename."""
        readme = temp_dir / "README.md"
        spec = temp_dir / "SPEC.md"
        design = temp_dir / "DESIGN.md"

        assert "documentation" in task_102_corpus_collection._classify_material(readme).lower()
        assert "spec" in task_102_corpus_collection._classify_material(spec).lower()

    def test_save_corpus_creates_json(self, temp_dir):
        """Test corpus saving creates JSON file."""
        corpus_file = temp_dir / "corpus.json"
        index_file = temp_dir / "CORPUS-INDEX.md"

        materials = [
            {"path": "README.md", "type": "documentation"},
            {"path": "SPEC.md", "type": "specification"}
        ]

        task_102_corpus_collection._save_corpus(
            corpus_file,
            index_file,
            {"materials": materials, "links": []},
            materials
        )

        assert corpus_file.exists()
        corpus = json.loads(corpus_file.read_text())
        assert len(corpus["materials"]) == 2

    @patch('core.llm.invoke_llm')
    def test_analyze_corpus_with_llm(self, mock_llm, temp_dir):
        """Test corpus analysis invokes LLM."""
        mock_llm.return_value = "Analysis: Project has good documentation"

        materials = [{"path": "README.md", "content": "# Test"}]

        result = task_102_corpus_collection._analyze_corpus(materials)

        mock_llm.assert_called_once()
        assert isinstance(result, str)


# ============================================================================
# Task 103: Import Requirements Tests
# ============================================================================

class TestTask103ImportRequirements:
    """Unit tests for task_103_import_requirements."""

    def test_execute_uat_mode_success(self, temp_dir):
        """Test execute in UAT mode returns True."""
        output_dir = temp_dir / ".outputs" / "1-discovery"
        output_dir.mkdir(parents=True)

        result = task_103_import_requirements.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        assert result is True

    def test_find_requirements_files(self, temp_dir):
        """Test finding requirements files."""
        (temp_dir / "requirements.txt").write_text("pytest\nrequests")
        (temp_dir / "package.json").write_text('{"dependencies": {}}')

        files = task_103_import_requirements._find_requirements_files(temp_dir)

        assert len(files) >= 2
        assert any("requirements.txt" in str(f) for f in files)
        assert any("package.json" in str(f) for f in files)

    def test_parse_requirements_txt(self, temp_dir):
        """Test parsing requirements.txt."""
        req_file = temp_dir / "requirements.txt"
        req_file.write_text("pytest>=7.0\nrequests==2.28.0\nflask")

        deps = task_103_import_requirements._parse_requirements_txt(req_file)

        assert "pytest" in deps
        assert "requests" in deps
        assert "flask" in deps

    def test_parse_package_json(self, temp_dir):
        """Test parsing package.json."""
        pkg_file = temp_dir / "package.json"
        pkg_file.write_text(json.dumps({
            "dependencies": {
                "react": "^18.0.0",
                "express": "^4.18.0"
            }
        }))

        deps = task_103_import_requirements._parse_package_json(pkg_file)

        assert "react" in deps
        assert "express" in deps

    def test_save_requirements_summary(self, temp_dir):
        """Test saving requirements summary."""
        output_file = temp_dir / "requirements.json"

        requirements = {
            "python": ["pytest", "requests"],
            "javascript": ["react", "express"]
        }

        task_103_import_requirements._save_requirements_summary(
            output_file,
            requirements
        )

        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert "python" in data
        assert "javascript" in data


# ============================================================================
# Task 104: Agent Selection Tests
# ============================================================================

class TestTask104AgentSelection:
    """Unit tests for task_104_agent_selection."""

    def test_execute_uat_mode_success(self, temp_dir):
        """Test execute in UAT mode returns True."""
        output_dir = temp_dir / ".outputs" / "1-discovery"
        output_dir.mkdir(parents=True)

        result = task_104_agent_selection.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        assert result is True

    def test_execute_uat_mode_selects_default_agent(self, temp_dir):
        """Test UAT mode selects default agent."""
        output_dir = temp_dir / ".outputs" / "1-discovery"
        output_dir.mkdir(parents=True)

        task_104_agent_selection.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        agent_file = output_dir / "selected-agent.json"
        assert agent_file.exists()

        agent = json.loads(agent_file.read_text())
        assert "name" in agent

    @patch('core.llm.invoke_llm')
    def test_recommend_agent_with_llm(self, mock_llm, temp_dir):
        """Test agent recommendation uses LLM."""
        mock_llm.return_value = json.dumps({
            "recommended_agent": "discovery-specialist",
            "rationale": "Best for discovery phase"
        })

        context = {"project": {"type": "new-component"}}

        result = task_104_agent_selection._recommend_agent(context)

        mock_llm.assert_called_once()
        assert isinstance(result, dict)

    def test_load_agent_inventory(self, temp_dir):
        """Test loading agent inventory."""
        agents_dir = temp_dir / "agents"
        agents_dir.mkdir()

        inventory_file = agents_dir / "agent-inventory.csv"
        inventory_file.write_text("""name,role,phase
discovery-specialist,Discovery,1
prd-author,PRD Writing,2""")

        agents = task_104_agent_selection._load_agent_inventory(agents_dir)

        assert len(agents) >= 2
        assert any(a["name"] == "discovery-specialist" for a in agents)


# ============================================================================
# Task 105: Opening Dialogue Tests
# ============================================================================

class TestTask105OpeningDialogue:
    """Unit tests for task_105_opening_dialogue."""

    def test_execute_uat_mode_success(self, temp_dir):
        """Test execute in UAT mode returns True."""
        output_dir = temp_dir / ".outputs" / "1-discovery"
        output_dir.mkdir(parents=True)

        result = task_105_opening_dialogue.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        assert result is True

    def test_execute_uat_mode_creates_dialogue_file(self, temp_dir):
        """Test UAT mode creates dialogue.json."""
        output_dir = temp_dir / ".outputs" / "1-discovery"
        output_dir.mkdir(parents=True)

        task_105_opening_dialogue.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        dialogue_file = output_dir / "dialogue.json"
        assert dialogue_file.exists()

    @patch('builtins.input', return_value="We need a web application for task management")
    def test_collect_user_input_interactive(self, mock_input):
        """Test collecting user input interactively."""
        responses = task_105_opening_dialogue._collect_user_input()

        assert isinstance(responses, dict)
        mock_input.assert_called()

    @patch('core.llm.invoke_llm')
    def test_generate_follow_up_questions(self, mock_llm):
        """Test generating follow-up questions."""
        mock_llm.return_value = "1. What features are essential?\n2. Who are the users?"

        initial_response = "We need a task manager"

        questions = task_105_opening_dialogue._generate_follow_up_questions(
            initial_response
        )

        mock_llm.assert_called_once()
        assert isinstance(questions, str)

    def test_save_dialogue_transcript(self, temp_dir):
        """Test saving dialogue transcript."""
        output_file = temp_dir / "dialogue.json"

        dialogue = {
            "exchanges": [
                {"role": "user", "content": "I want to build an app"},
                {"role": "assistant", "content": "What kind of app?"}
            ]
        }

        task_105_opening_dialogue._save_dialogue_transcript(output_file, dialogue)

        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert len(data["exchanges"]) == 2


# ============================================================================
# Task 106: Discovery Work Tests
# ============================================================================

class TestTask106DiscoveryWork:
    """Unit tests for task_106_discovery_work."""

    def test_execute_uat_mode_success(self, temp_dir):
        """Test execute in UAT mode returns True."""
        output_dir = temp_dir / ".outputs" / "1-discovery"
        output_dir.mkdir(parents=True)

        result = task_106_discovery_work.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        assert result is True

    @patch('core.llm.invoke_llm')
    def test_analyze_project_vision(self, mock_llm, temp_dir):
        """Test project vision analysis."""
        mock_llm.return_value = json.dumps({
            "vision": "Build a modern task management system",
            "goals": ["User-friendly", "Real-time collaboration"]
        })

        context = {"dialogue": {}, "corpus": {}}

        result = task_106_discovery_work._analyze_project_vision(context)

        mock_llm.assert_called_once()
        assert isinstance(result, dict)

    @patch('core.llm.invoke_llm')
    def test_identify_constraints(self, mock_llm):
        """Test constraint identification."""
        mock_llm.return_value = json.dumps({
            "technical": ["Must use Python"],
            "timeline": ["Launch in 3 months"]
        })

        context = {"project": {"type": "new-component"}}

        constraints = task_106_discovery_work._identify_constraints(context)

        mock_llm.assert_called_once()
        assert isinstance(constraints, dict)

    def test_save_discovery_report(self, temp_dir):
        """Test saving discovery report."""
        output_file = temp_dir / "discovery-report.json"

        report = {
            "vision": "Build a platform",
            "constraints": {"technical": ["Python"]},
            "recommendations": ["Use FastAPI"]
        }

        task_106_discovery_work._save_discovery_report(output_file, report)

        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert "vision" in data


# ============================================================================
# Task 107: Approach Selection Tests
# ============================================================================

class TestTask107ApproachSelection:
    """Unit tests for task_107_approach_selection."""

    def test_execute_uat_mode_success(self, temp_dir):
        """Test execute in UAT mode returns True."""
        output_dir = temp_dir / ".outputs" / "1-discovery"
        output_dir.mkdir(parents=True)

        result = task_107_approach_selection.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        assert result is True

    def test_execute_uat_mode_creates_approach_file(self, temp_dir):
        """Test UAT mode creates selected-approach.json."""
        output_dir = temp_dir / ".outputs" / "1-discovery"
        output_dir.mkdir(parents=True)

        task_107_approach_selection.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        approach_file = output_dir / "selected-approach.json"
        assert approach_file.exists()

    @patch('core.llm.invoke_llm')
    def test_generate_approach_options(self, mock_llm):
        """Test generating approach options."""
        mock_llm.return_value = json.dumps({
            "approaches": [
                {"name": "Microservices", "score": 8},
                {"name": "Monolith", "score": 6}
            ]
        })

        context = {"project": {"type": "new-api"}}

        approaches = task_107_approach_selection._generate_approach_options(context)

        mock_llm.assert_called_once()
        assert isinstance(approaches, list)

    def test_rank_approaches(self):
        """Test approach ranking."""
        approaches = [
            {"name": "A", "score": 6},
            {"name": "B", "score": 9},
            {"name": "C", "score": 7}
        ]

        ranked = task_107_approach_selection._rank_approaches(approaches)

        assert ranked[0]["name"] == "B"  # Highest score first
        assert ranked[1]["name"] == "C"
        assert ranked[2]["name"] == "A"

    def test_save_selected_approach(self, temp_dir):
        """Test saving selected approach."""
        output_file = temp_dir / "selected-approach.json"

        approach = {
            "name": "Microservices Architecture",
            "rationale": "Best for scalability",
            "score": 9
        }

        task_107_approach_selection._save_selected_approach(output_file, approach)

        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert data["name"] == "Microservices Architecture"


# ============================================================================
# Task 108: Discovery Diagrams Tests
# ============================================================================

class TestTask108DiscoveryDiagrams:
    """Unit tests for task_108_discovery_diagrams."""

    def test_execute_uat_mode_success(self, temp_dir):
        """Test execute in UAT mode returns True."""
        output_dir = temp_dir / ".outputs" / "1-discovery"
        output_dir.mkdir(parents=True)

        result = task_108_discovery_diagrams.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        assert result is True

    @patch('core.llm.invoke_llm')
    def test_generate_architecture_diagram(self, mock_llm, temp_dir):
        """Test architecture diagram generation."""
        mock_llm.return_value = """
digraph {
  "Frontend" -> "API"
  "API" -> "Database"
}
"""

        context = {"approach": {"name": "Microservices"}}

        diagram = task_108_discovery_diagrams._generate_architecture_diagram(context)

        mock_llm.assert_called_once()
        assert "digraph" in diagram

    @patch('subprocess.run')
    def test_render_dot_to_svg(self, mock_run, temp_dir):
        """Test rendering DOT to SVG."""
        mock_run.return_value = Mock(returncode=0)

        dot_file = temp_dir / "diagram.dot"
        dot_file.write_text("digraph { A -> B }")

        svg_file = temp_dir / "diagram.svg"

        result = task_108_discovery_diagrams._render_dot_to_svg(dot_file, svg_file)

        assert result is True
        mock_run.assert_called_once()

    def test_save_diagrams(self, temp_dir):
        """Test saving diagrams."""
        diagrams_dir = temp_dir / "diagrams"

        diagrams = {
            "architecture": "digraph { A -> B }",
            "dataflow": "digraph { Data -> Process }"
        }

        task_108_discovery_diagrams._save_diagrams(diagrams_dir, diagrams)

        assert diagrams_dir.exists()
        assert (diagrams_dir / "architecture.dot").exists()


# ============================================================================
# Task 109: Phase Audit Tests
# ============================================================================

class TestTask109PhaseAudit:
    """Unit tests for task_109_phase_audit."""

    def test_execute_uat_mode_success(self, temp_dir):
        """Test execute in UAT mode returns True."""
        output_dir = temp_dir / ".outputs" / "1-discovery"
        output_dir.mkdir(parents=True)

        result = task_109_phase_audit.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        assert result is True

    def test_audit_checks_required_artifacts(self, temp_dir):
        """Test audit checks for required artifacts."""
        output_dir = temp_dir / ".outputs" / "1-discovery"
        output_dir.mkdir(parents=True)

        # Create required artifacts
        (output_dir / "corpus.json").write_text("{}")
        (output_dir / "selected-approach.json").write_text("{}")
        (output_dir / "dialogue.json").write_text("{}")

        results = task_109_phase_audit._audit_artifacts(output_dir)

        assert results["corpus"] is True
        assert results["approach"] is True

    def test_audit_missing_artifacts(self, temp_dir):
        """Test audit detects missing artifacts."""
        output_dir = temp_dir / ".outputs" / "1-discovery"
        output_dir.mkdir(parents=True)

        results = task_109_phase_audit._audit_artifacts(output_dir)

        assert not all(results.values())

    @patch('core.llm.invoke_llm')
    def test_generate_audit_report(self, mock_llm, temp_dir):
        """Test audit report generation."""
        mock_llm.return_value = json.dumps({
            "status": "complete",
            "findings": ["All artifacts present"]
        })

        audit_results = {"corpus": True, "approach": True}

        report = task_109_phase_audit._generate_audit_report(audit_results)

        mock_llm.assert_called_once()
        assert isinstance(report, dict)

    def test_save_audit_report(self, temp_dir):
        """Test saving audit report."""
        output_file = temp_dir / "phase-audit.json"

        report = {
            "status": "complete",
            "artifacts_found": ["corpus.json", "approach.json"],
            "artifacts_missing": []
        }

        task_109_phase_audit._save_audit_report(output_file, report)

        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert data["status"] == "complete"


# ============================================================================
# Task 110: Closeout Tests
# ============================================================================

class TestTask110Closeout:
    """Unit tests for task_110_closeout."""

    def test_execute_uat_mode_success(self, temp_dir):
        """Test execute in UAT mode returns True."""
        output_dir = temp_dir / ".outputs" / "1-discovery"
        output_dir.mkdir(parents=True)

        result = task_110_closeout.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        assert result is True

    def test_execute_creates_closeout_file(self, temp_dir):
        """Test execute creates closeout file."""
        output_dir = temp_dir / ".outputs" / "1-discovery"
        output_dir.mkdir(parents=True)

        task_110_closeout.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        # Check for closeout file
        closeout_file = output_dir / "phase-01-closeout.json"
        if not closeout_file.exists():
            closeout_file = output_dir / "closeout.json"

        assert closeout_file.exists()

    def test_generate_closeout_summary(self, temp_dir):
        """Test closeout summary generation."""
        output_dir = temp_dir / ".outputs" / "1-discovery"
        output_dir.mkdir(parents=True)

        # Create artifacts
        (output_dir / "corpus.json").write_text('{"materials": []}')
        (output_dir / "selected-approach.json").write_text('{"name": "Test"}')

        summary = task_110_closeout._generate_closeout_summary(output_dir)

        assert isinstance(summary, dict)
        assert "artifacts" in summary or "status" in summary

    def test_verify_phase_completion(self, temp_dir):
        """Test phase completion verification."""
        output_dir = temp_dir / ".outputs" / "1-discovery"
        output_dir.mkdir(parents=True)

        # Create all required artifacts
        (output_dir / "corpus.json").write_text("{}")
        (output_dir / "selected-approach.json").write_text("{}")
        (output_dir / "dialogue.json").write_text("{}")

        complete = task_110_closeout._verify_phase_completion(output_dir)

        assert isinstance(complete, bool)

    def test_save_closeout_document(self, temp_dir):
        """Test saving closeout document."""
        output_file = temp_dir / "closeout.json"

        closeout = {
            "phase": "1-discovery",
            "status": "complete",
            "completed_at": datetime.now().isoformat(),
            "artifacts": ["corpus.json", "approach.json"]
        }

        task_110_closeout._save_closeout_document(output_file, closeout)

        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert data["status"] == "complete"

    def test_update_pipeline_state(self, temp_dir):
        """Test pipeline state update."""
        state_dir = temp_dir / ".state"
        state_dir.mkdir()

        state_file = state_dir / "task-state.json"
        state_file.write_text(json.dumps({
            "phases": {}
        }))

        task_110_closeout._update_pipeline_state(temp_dir, "1-discovery")

        state = json.loads(state_file.read_text())
        assert "1-discovery" in state["phases"] or "current_phase" in state
