"""
Unit Tests for Phase 2 (PRD) Task Modules

Tests all 10 Phase 2 tasks with comprehensive coverage:
- Task 201: Entry Validation
- Task 202: PRD Setup
- Task 203: PRD Interview
- Task 204: Agent Selection
- Task 205: PRD Authoring
- Task 206: PRD Validation
- Task 206b: PRD Revision
- Task 207: PRD Approval
- Task 208: Phase Audit
- Task 209: Closeout
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import task modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phases.phase_02_prd.tasks import task_201_entry_validation
from phases.phase_02_prd.tasks import task_202_prd_setup
from phases.phase_02_prd.tasks import task_203_prd_interview
from phases.phase_02_prd.tasks import task_204_agent_selection
from phases.phase_02_prd.tasks import task_205_prd_authoring
from phases.phase_02_prd.tasks import task_206_prd_validation
from phases.phase_02_prd.tasks import task_206b_prd_revision
from phases.phase_02_prd.tasks import task_207_prd_approval
from phases.phase_02_prd.tasks import task_208_phase_audit
from phases.phase_02_prd.tasks import task_209_closeout

# ============================================================================
# Task 201: Entry Validation Tests
# ============================================================================

class TestTask201EntryValidation:
    """Unit tests for task_201_entry_validation."""

    def test_validate_phase1_artifacts_all_present(self, temp_dir):
        """Test artifact validation with all files present."""
        phase1_dir = temp_dir / ".outputs" / "1-discovery"
        phase1_dir.mkdir(parents=True)

        # Create all required artifacts
        (phase1_dir / "phase-01-closeout.json").write_text(
            json.dumps({"status": "complete"})
        )
        (phase1_dir / "selected-approach.json").write_text(
            json.dumps({"name": "microservices"})
        )

        all_valid, missing = task_201_entry_validation.validate_phase1_artifacts(
            phase1_dir
        )

        assert all_valid is True
        assert len(missing) == 0

    def test_validate_phase1_artifacts_missing_files(self, temp_dir):
        """Test artifact validation with missing files."""
        phase1_dir = temp_dir / ".outputs" / "1-discovery"
        phase1_dir.mkdir(parents=True)

        all_valid, missing = task_201_entry_validation.validate_phase1_artifacts(
            phase1_dir
        )

        assert all_valid is False
        assert len(missing) > 0

    def test_find_closeout_multiple_patterns(self, temp_dir):
        """Test closeout finding with multiple name patterns."""
        phase1_dir = temp_dir / ".outputs" / "1-discovery"
        phase1_dir.mkdir(parents=True)

        closeout_file = phase1_dir / "phase-01-closeout.json"
        closeout_file.write_text('{"status": "complete"}')

        result = task_201_entry_validation.find_closeout(phase1_dir)

        assert result is not None
        assert result.exists()

    def test_find_closeout_not_found(self, temp_dir):
        """Test closeout finding when file doesn't exist."""
        phase1_dir = temp_dir / ".outputs" / "1-discovery"
        phase1_dir.mkdir(parents=True)

        result = task_201_entry_validation.find_closeout(phase1_dir)

        assert result is None

    def test_load_phase1_context(self, temp_dir):
        """Test loading Phase 1 context."""
        phase1_dir = temp_dir / ".outputs" / "1-discovery"
        phase1_dir.mkdir(parents=True)

        # Create context files (Task 106 format with direction embedded)
        (phase1_dir / "selected-approach.json").write_text(
            json.dumps({
                "direction": {
                    "summary": "Build a scalable platform",
                    "rationale": "Scalability"
                },
                "key_decisions": ["Use microservices"],
                "open_items": ["Budget", "Timeline"],
                "confirmed_at": "2024-01-01T00:00:00",
                "confirmed_by": "human"
            })
        )

        context = task_201_entry_validation.load_phase1_context(phase1_dir)

        assert isinstance(context, dict)
        assert "approach" in context
        assert context["approach"]["name"] == "Build a scalable platform"
        assert context["vision"] == "Build a scalable platform"

    def test_load_phase1_context_with_corpus(self, temp_dir):
        """Test loading context including corpus data."""
        phase1_dir = temp_dir / ".outputs" / "1-discovery"
        phase1_dir.mkdir(parents=True)

        (phase1_dir / "corpus.json").write_text(
            json.dumps({
                "materials": ["README.md", "SPEC.md", "DESIGN.md"]
            })
        )

        context = task_201_entry_validation.load_phase1_context(phase1_dir)

        assert context["corpus_materials"] == 3

# ============================================================================
# Task 202: PRD Setup Tests
# ============================================================================

class TestTask202PrdSetup:
    """Unit tests for task_202_prd_setup."""

    def test_execute_creates_prd_template(self, temp_dir):
        """Test execute creates PRD template."""
        output_dir = temp_dir / ".outputs" / "2-prd"
        output_dir.mkdir(parents=True)

        task_202_prd_setup.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
        )

        prd_file = output_dir / "PRD.md"
        assert prd_file.exists()

    def test_create_prd_template_structure(self, temp_dir):
        """Test PRD template has proper structure."""
        prd_file = temp_dir / "PRD.md"

        task_202_prd_setup._create_prd_template(prd_file)

        assert prd_file.exists()
        content = prd_file.read_text()
        assert "# Product Requirements Document" in content
        assert "## Overview" in content
        assert "## Requirements" in content

    def test_load_discovery_context(self, temp_dir):
        """Test loading discovery context."""
        phase1_dir = temp_dir / ".outputs" / "1-discovery"
        phase1_dir.mkdir(parents=True)

        (phase1_dir / "selected-approach.json").write_text(
            json.dumps({"name": "Microservices"})
        )

        context = task_202_prd_setup._load_discovery_context(phase1_dir)

        assert isinstance(context, dict)
        assert "approach" in context

    def test_initialize_prd_metadata(self, temp_dir):
        """Test PRD metadata initialization."""
        output_file = temp_dir / "prd-metadata.json"

        metadata = {
            "created_at": datetime.now().isoformat(),
            "version": "1.0",
            "status": "draft"
        }

        task_202_prd_setup._initialize_prd_metadata(output_file, metadata)

        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert data["version"] == "1.0"

# ============================================================================
# Task 203: PRD Interview Tests
# ============================================================================

class TestTask203PrdInterview:
    """Unit tests for task_203_prd_interview."""

    @patch('core.llm.invoke_llm')
    def test_generate_interview_questions(self, mock_llm):
        """Test interview question generation."""
        mock_llm.return_value = json.dumps({
            "questions": [
                "What are the primary user goals?",
                "What are the key features?",
                "What are the success metrics?"
            ]
        })

        context = {"approach": "Microservices"}

        questions = task_203_prd_interview._generate_interview_questions(context)

        mock_llm.assert_called_once()
        assert isinstance(questions, list)
        assert len(questions) > 0

    @patch('builtins.input', side_effect=["User authentication", "Real-time updates", "done"])
    def test_conduct_interview_interactive(self, mock_input):
        """Test conducting interactive interview."""
        questions = [
            "What features are essential?",
            "What are the constraints?"
        ]

        responses = task_203_prd_interview._conduct_interview(questions)

        assert isinstance(responses, dict)

    def test_save_interview_transcript(self, temp_dir):
        """Test saving interview transcript."""
        output_file = temp_dir / "interview.json"

        transcript = {
            "questions": ["Q1", "Q2"],
            "responses": ["A1", "A2"],
            "conducted_at": datetime.now().isoformat()
        }

        task_203_prd_interview._save_interview_transcript(output_file, transcript)

        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert len(data["questions"]) == 2

# ============================================================================
# Task 204: Agent Selection Tests
# ============================================================================

class TestTask204AgentSelection:
    """Unit tests for task_204_agent_selection."""

    @patch('core.llm.invoke_llm')
    def test_recommend_prd_agent(self, mock_llm):
        """Test PRD agent recommendation."""
        mock_llm.return_value = json.dumps({
            "agent": "prd-technical-specialist",
            "rationale": "Best for technical PRDs"
        })

        context = {"project": {"type": "new-api"}}

        agent = task_204_agent_selection._recommend_prd_agent(context)

        mock_llm.assert_called_once()
        assert isinstance(agent, dict)

    def test_filter_agents_by_phase(self, temp_dir):
        """Test filtering agents by phase."""
        agents_dir = temp_dir / "agents"
        agents_dir.mkdir()

        inventory = agents_dir / "agent-inventory.csv"
        inventory.write_text("""name,phase,role
prd-author,2,PRD Writing
discovery-specialist,1,Discovery
architect,4,Design""")

        phase2_agents = task_204_agent_selection._filter_agents_by_phase(
            agents_dir, phase=2
        )

        assert len(phase2_agents) == 1
        assert phase2_agents[0]["name"] == "prd-author"

# ============================================================================
# Task 205: PRD Authoring Tests
# ============================================================================

class TestTask205PrdAuthoring:
    """Unit tests for task_205_prd_authoring."""

    def test_execute_creates_prd_document(self, temp_dir):
        """Test execute creates PRD document."""
        output_dir = temp_dir / ".outputs" / "2-prd"
        output_dir.mkdir(parents=True)

        # Create interview data
        (output_dir / "prd-interview.json").write_text(
            json.dumps({"questions": [], "responses": []})
        )

        task_205_prd_authoring.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
        )

        prd_file = output_dir / "PRD.md"
        assert prd_file.exists()

    @patch('core.llm.invoke_llm')
    def test_generate_prd_content(self, mock_llm, temp_dir):
        """Test PRD content generation."""
        mock_llm.return_value = """# Product Requirements Document

## Overview
This is a test PRD.

## Requirements
1. User authentication
2. Data management
3. API endpoints
"""

        context = {
            "interview": {"responses": []},
            "approach": {"name": "Microservices"}
        }

        content = task_205_prd_authoring._generate_prd_content(context)

        mock_llm.assert_called_once()
        assert "Product Requirements Document" in content
        assert "Requirements" in content

    def test_validate_prd_structure(self, temp_dir):
        """Test PRD structure validation."""
        prd_file = temp_dir / "PRD.md"
        prd_file.write_text("""# Product Requirements Document

## Overview
Project overview here.

## Requirements
### Functional Requirements
- Feature 1
- Feature 2

### Non-Functional Requirements
- Performance
- Security
""")

        valid = task_205_prd_authoring._validate_prd_structure(prd_file)

        assert valid is True

    def test_validate_prd_structure_incomplete(self, temp_dir):
        """Test PRD structure validation with incomplete document."""
        prd_file = temp_dir / "PRD.md"
        prd_file.write_text("# Incomplete PRD\n\nJust an overview.")

        valid = task_205_prd_authoring._validate_prd_structure(prd_file)

        assert valid is False

# ============================================================================
# Task 206: PRD Validation Tests
# ============================================================================

class TestTask206PrdValidation:
    """Unit tests for task_206_prd_validation."""

    @patch('core.llm.invoke_llm')
    def test_validate_prd_with_llm(self, mock_llm, temp_dir):
        """Test PRD validation with LLM."""
        mock_llm.return_value = json.dumps({
            "valid": True,
            "issues": [],
            "suggestions": ["Add more detail to section 3"]
        })

        prd_file = temp_dir / "PRD.md"
        prd_file.write_text("# Product Requirements Document\n\nContent here.")

        validation = task_206_prd_validation._validate_prd_with_llm(prd_file)

        mock_llm.assert_called_once()
        assert isinstance(validation, dict)
        assert "valid" in validation

    def test_check_completeness(self, temp_dir):
        """Test PRD completeness check."""
        prd_file = temp_dir / "PRD.md"
        prd_file.write_text("""# Product Requirements Document

## Overview
Complete overview

## Requirements
Complete requirements

## Success Metrics
Defined metrics
""")

        complete = task_206_prd_validation._check_completeness(prd_file)

        assert complete is True

    def test_save_validation_report(self, temp_dir):
        """Test saving validation report."""
        output_file = temp_dir / "validation.json"

        report = {
            "valid": True,
            "issues": [],
            "completeness_score": 95,
            "validated_at": datetime.now().isoformat()
        }

        task_206_prd_validation._save_validation_report(output_file, report)

        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert data["valid"] is True

# ============================================================================
# Task 206b: PRD Revision Tests
# ============================================================================

class TestTask206bPrdRevision:
    """Unit tests for task_206b_prd_revision."""

    @patch('core.llm.invoke_llm')
    def test_revise_prd_section(self, mock_llm, temp_dir):
        """Test PRD section revision."""
        mock_llm.return_value = "## Revised Section\n\nImproved content here."

        original = "## Section\n\nOriginal content."
        feedback = "Add more detail"

        revised = task_206b_prd_revision._revise_prd_section(original, feedback)

        mock_llm.assert_called_once()
        assert "Revised" in revised

    def test_apply_revisions_to_prd(self, temp_dir):
        """Test applying revisions to PRD."""
        prd_file = temp_dir / "PRD.md"
        prd_file.write_text("""# PRD

## Section 1
Original content.

## Section 2
More content.
""")

        revisions = {
            "Section 1": "## Section 1\nRevised content."
        }

        task_206b_prd_revision._apply_revisions_to_prd(prd_file, revisions)

        content = prd_file.read_text()
        assert "Revised content" in content

    def test_create_revision_history(self, temp_dir):
        """Test revision history creation."""
        history_file = temp_dir / "revision-history.json"

        revision = {
            "version": 2,
            "timestamp": datetime.now().isoformat(),
            "changes": ["Updated Overview", "Added Success Metrics"]
        }

        task_206b_prd_revision._create_revision_history(history_file, revision)

        assert history_file.exists()
        data = json.loads(history_file.read_text())
        assert data["version"] == 2

# ============================================================================
# Task 207: PRD Approval Tests
# ============================================================================

class TestTask207PrdApproval:
    """Unit tests for task_207_prd_approval."""

    def test_display_prd_for_approval(self, temp_dir, capsys):
        """Test displaying PRD for approval."""
        prd_file = temp_dir / "PRD.md"
        prd_file.write_text("""# Product Requirements Document

## Overview
Test project overview.
""")

        task_207_prd_approval._display_prd_for_approval(prd_file)

        captured = capsys.readouterr()
        assert "Product Requirements Document" in captured.out

    def test_record_approval(self, temp_dir):
        """Test recording PRD approval."""
        output_file = temp_dir / "approval.json"

        approval = {
            "approved": True,
            "approved_by": "user",
            "approved_at": datetime.now().isoformat(),
            "comments": "Looks good"
        }

        task_207_prd_approval._record_approval(output_file, approval)

        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert data["approved"] is True

# ============================================================================
# Task 208: Phase Audit Tests
# ============================================================================

class TestTask208PhaseAudit:
    """Unit tests for task_208_phase_audit."""

    @patch('phases.phase_02_prd.tasks.task_208_phase_audit.run_phase_audit',
           return_value=True)
    def test_delegates_to_run_phase_audit(self, mock_rpa, temp_dir):
        """Task 208 delegates to core.audit.run_phase_audit."""
        output_dir = temp_dir / ".outputs" / "2-prd"
        output_dir.mkdir(parents=True)

        task_208_phase_audit.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
        )

        mock_rpa.assert_called_once_with(2, "2-prd", output_dir, False)

    @patch('phases.phase_02_prd.tasks.task_208_phase_audit.run_phase_audit',
           return_value=True)
    def test_accepts_mem_parameter(self, mock_rpa, temp_dir):
        """Task 208 accepts optional mem parameter."""
        output_dir = temp_dir / ".outputs" / "2-prd"
        output_dir.mkdir(parents=True)

        result = task_208_phase_audit.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            mem=None,
        )

        assert result is True

    def test_bad_output_dir_non_blocking(self, temp_dir):
        """Non-standard output_dir name returns True (non-blocking)."""
        output_dir = temp_dir / ".outputs" / "nodash"
        output_dir.mkdir(parents=True)

        result = task_208_phase_audit.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
        )

        assert result is True

# ============================================================================
# Task 209: Closeout Tests
# ============================================================================

class TestTask209Closeout:
    """Unit tests for task_209_closeout."""

    def test_execute_creates_closeout_file(self, temp_dir):
        """Test execute creates closeout file."""
        output_dir = temp_dir / ".outputs" / "2-prd"
        output_dir.mkdir(parents=True)

        task_209_closeout.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
        )

        closeout_file = output_dir / "phase-02-closeout.json"
        if not closeout_file.exists():
            closeout_file = output_dir / "closeout.json"

        assert closeout_file.exists()

    def test_generate_closeout_summary(self, temp_dir):
        """Test closeout summary generation."""
        output_dir = temp_dir / ".outputs" / "2-prd"
        output_dir.mkdir(parents=True)

        # Create artifacts
        (output_dir / "PRD.md").write_text("# PRD")
        (output_dir / "prd-approval.json").write_text('{"approved": true}')

        summary = task_209_closeout._generate_closeout_summary(output_dir)

        assert isinstance(summary, dict)
        assert "artifacts" in summary or "status" in summary

    def test_verify_prd_phase_completion(self, temp_dir):
        """Test PRD phase completion verification."""
        output_dir = temp_dir / ".outputs" / "2-prd"
        output_dir.mkdir(parents=True)

        # Create all required artifacts
        (output_dir / "PRD.md").write_text("# PRD")
        (output_dir / "prd-validation.json").write_text("{}")
        (output_dir / "prd-approval.json").write_text('{"approved": true}')

        complete = task_209_closeout._verify_prd_phase_completion(output_dir)

        assert isinstance(complete, bool)

    def test_archive_prd_artifacts(self, temp_dir):
        """Test archiving PRD artifacts."""
        output_dir = temp_dir / ".outputs" / "2-prd"
        output_dir.mkdir(parents=True)

        (output_dir / "PRD.md").write_text("# PRD")
        (output_dir / "notes.txt").write_text("Working notes")

        archive_dir = temp_dir / "archive"

        task_209_closeout._archive_prd_artifacts(output_dir, archive_dir)

        assert archive_dir.exists()
        assert (archive_dir / "PRD.md").exists()

    def test_save_closeout_document(self, temp_dir):
        """Test saving closeout document."""
        output_file = temp_dir / "closeout.json"

        closeout = {
            "phase": "2-prd",
            "status": "complete",
            "completed_at": datetime.now().isoformat(),
            "artifacts": ["PRD.md", "validation.json", "approval.json"],
            "prd_version": "1.0"
        }

        task_209_closeout._save_closeout_document(output_file, closeout)

        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert data["status"] == "complete"
        assert data["phase"] == "2-prd"

    def test_update_pipeline_state(self, temp_dir):
        """Test pipeline state update for Phase 2."""
        state_dir = temp_dir / ".state"
        state_dir.mkdir()

        state_file = state_dir / "task-state.json"
        state_file.write_text(json.dumps({
            "phases": {
                "1-discovery": {"status": "complete"}
            }
        }))

        task_209_closeout._update_pipeline_state(temp_dir, "2-prd")

        state = json.loads(state_file.read_text())
        assert "2-prd" in state["phases"] or "current_phase" in state

    def test_generate_next_phase_handoff(self, temp_dir):
        """Test generating handoff document for next phase."""
        output_dir = temp_dir / ".outputs" / "2-prd"
        output_dir.mkdir(parents=True)

        (output_dir / "PRD.md").write_text("# PRD Document")

        handoff_file = temp_dir / "phase3-handoff.json"

        handoff = task_209_closeout._generate_next_phase_handoff(output_dir)

        assert isinstance(handoff, dict)
        assert "prd_location" in handoff or "summary" in handoff
