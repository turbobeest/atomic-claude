"""
Unit Tests for Phase Chaining Logic

Comprehensive tests for orchestration/chaining.py covering:
- Closeout parsing and validation
- Phase completion detection
- User prompts (mocked)
- Next phase detection
- Phase launching
- Resume logic
- Auto-chaining

Requirements: 15+ unit tests with high coverage
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, call

from orchestration.chaining import (
    PhaseChaining,
    CloseoutParser,
    CloseoutData,
    PromptFormatter,
    PhaseDetector
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_atomic_root(tmp_path):
    """Create temporary atomic root with outputs directory."""
    outputs_dir = tmp_path / ".outputs"
    outputs_dir.mkdir()
    return tmp_path


@pytest.fixture
def sample_closeout_data():
    """Sample closeout data for testing."""
    return {
        "phase": "0-setup",
        "phase_num": 0,
        "completed_at": "2024-01-01T12:00:00",
        "tasks_completed": ["001", "002", "003"],
        "summary": "Phase 0 (Setup) completed successfully."
    }


@pytest.fixture
def phase_chaining(temp_atomic_root):
    """Create PhaseChaining instance."""
    return PhaseChaining(atomic_root=temp_atomic_root)


def create_closeout_file(atomic_root: Path, phase_num: int, closeout_data: dict):
    """Helper to create closeout file."""
    phase_names = {
        0: "setup",
        1: "discovery",
        2: "prd",
        3: "tasking",
        4: "specification",
        5: "implementation",
        6: "code-review",
        7: "integration",
        8: "deployment-prep",
        9: "release"
    }
    phase_name = phase_names.get(phase_num, f"phase{phase_num}")
    phase_id = f"{phase_num}-{phase_name}"

    phase_dir = atomic_root / ".outputs" / phase_id
    phase_dir.mkdir(parents=True, exist_ok=True)

    closeout_path = phase_dir / "closeout.json"
    with open(closeout_path, "w") as f:
        json.dump(closeout_data, f, indent=2)

    return closeout_path


# ============================================================================
# CLOSEOUT PARSER TESTS
# ============================================================================

class TestCloseoutParser:
    """Test CloseoutParser functionality."""

    def test_parse_valid_closeout(self, temp_atomic_root, sample_closeout_data):
        """Test parsing valid closeout file."""
        closeout_path = create_closeout_file(temp_atomic_root, 0, sample_closeout_data)

        result = CloseoutParser.parse(closeout_path)

        assert result is not None
        assert result.phase == "0-setup"
        assert result.phase_num == 0
        assert len(result.tasks_completed) == 3
        assert result.summary == "Phase 0 (Setup) completed successfully."

    def test_parse_missing_file(self, temp_atomic_root):
        """Test parsing non-existent closeout file."""
        closeout_path = temp_atomic_root / ".outputs" / "0-setup" / "closeout.json"

        result = CloseoutParser.parse(closeout_path)

        assert result is None

    def test_parse_invalid_json(self, temp_atomic_root):
        """Test parsing invalid JSON."""
        phase_dir = temp_atomic_root / ".outputs" / "0-setup"
        phase_dir.mkdir(parents=True)

        closeout_path = phase_dir / "closeout.json"
        with open(closeout_path, "w") as f:
            f.write("{ invalid json }")

        result = CloseoutParser.parse(closeout_path)

        assert result is None

    def test_parse_missing_required_fields(self, temp_atomic_root):
        """Test parsing closeout with missing required fields."""
        incomplete_data = {
            "phase": "0-setup",
            "phase_num": 0
            # Missing: completed_at, tasks_completed, summary
        }

        closeout_path = create_closeout_file(temp_atomic_root, 0, incomplete_data)
        result = CloseoutParser.parse(closeout_path)

        assert result is None

    def test_validate_valid_closeout(self, sample_closeout_data):
        """Test validation of valid closeout data."""
        closeout = CloseoutData(**sample_closeout_data)

        valid, error = CloseoutParser.validate(closeout)

        assert valid is True
        assert error is None

    def test_validate_invalid_phase_format(self):
        """Test validation with invalid phase format."""
        closeout = CloseoutData(
            phase="invalid",  # No hyphen
            phase_num=0,
            completed_at="2024-01-01T12:00:00",
            tasks_completed=["001"],
            summary="Test"
        )

        valid, error = CloseoutParser.validate(closeout)

        assert valid is False
        assert "Invalid phase format" in error

    def test_validate_invalid_phase_number(self, sample_closeout_data):
        """Test validation with invalid phase number."""
        sample_closeout_data['phase_num'] = 99
        closeout = CloseoutData(**sample_closeout_data)

        valid, error = CloseoutParser.validate(closeout)

        assert valid is False
        assert "Invalid phase number" in error

    def test_validate_no_tasks_completed(self, sample_closeout_data):
        """Test validation with no tasks completed."""
        sample_closeout_data['tasks_completed'] = []
        closeout = CloseoutData(**sample_closeout_data)

        valid, error = CloseoutParser.validate(closeout)

        assert valid is False
        assert "No tasks completed" in error

    def test_validate_invalid_timestamp(self, sample_closeout_data):
        """Test validation with invalid timestamp."""
        sample_closeout_data['completed_at'] = "invalid-timestamp"
        closeout = CloseoutData(**sample_closeout_data)

        valid, error = CloseoutParser.validate(closeout)

        assert valid is False
        assert "Invalid timestamp" in error


# ============================================================================
# PROMPT FORMATTER TESTS
# ============================================================================

class TestPromptFormatter:
    """Test PromptFormatter functionality."""

    def test_phase_complete_banner(self, sample_closeout_data):
        """Test phase completion banner formatting."""
        closeout = CloseoutData(**sample_closeout_data)

        banner = PromptFormatter.phase_complete_banner(closeout)

        assert "PHASE 0 COMPLETE" in banner
        assert "SETUP" in banner
        assert "Tasks Completed: 3" in banner
        assert sample_closeout_data['summary'] in banner

    def test_next_phase_prompt(self):
        """Test next phase prompt formatting."""
        prompt = PromptFormatter.next_phase_prompt(0, 1)

        assert "Phase 1" in prompt
        assert "Discovery" in prompt
        assert "continue" in prompt.lower()

    def test_pipeline_complete_banner(self):
        """Test pipeline completion banner."""
        banner = PromptFormatter.pipeline_complete_banner()

        assert "PIPELINE COMPLETE" in banner
        assert "All phases completed" in banner

    def test_phase_already_complete_message(self):
        """Test already-complete message."""
        message = PromptFormatter.phase_already_complete_message(0)

        assert "Phase 0" in message
        assert "Setup" in message
        assert "complete" in message.lower()


# ============================================================================
# PHASE DETECTOR TESTS
# ============================================================================

class TestPhaseDetector:
    """Test PhaseDetector functionality."""

    def test_is_phase_complete_true(self, temp_atomic_root, sample_closeout_data):
        """Test detecting completed phase."""
        create_closeout_file(temp_atomic_root, 0, sample_closeout_data)
        detector = PhaseDetector(temp_atomic_root)

        result = detector.is_phase_complete(0)

        assert result is True

    def test_is_phase_complete_false(self, temp_atomic_root):
        """Test detecting incomplete phase."""
        detector = PhaseDetector(temp_atomic_root)

        result = detector.is_phase_complete(0)

        assert result is False

    def test_is_phase_complete_invalid_closeout(self, temp_atomic_root):
        """Test detecting phase with invalid closeout."""
        invalid_data = {"phase": "0-setup"}  # Missing required fields
        create_closeout_file(temp_atomic_root, 0, invalid_data)
        detector = PhaseDetector(temp_atomic_root)

        result = detector.is_phase_complete(0)

        assert result is False

    def test_get_closeout_exists(self, temp_atomic_root, sample_closeout_data):
        """Test getting closeout data when exists."""
        create_closeout_file(temp_atomic_root, 0, sample_closeout_data)
        detector = PhaseDetector(temp_atomic_root)

        result = detector.get_closeout(0)

        assert result is not None
        assert result.phase_num == 0

    def test_get_closeout_missing(self, temp_atomic_root):
        """Test getting closeout when missing."""
        detector = PhaseDetector(temp_atomic_root)

        result = detector.get_closeout(0)

        assert result is None

    def test_get_next_phase(self, temp_atomic_root):
        """Test getting next phase number."""
        detector = PhaseDetector(temp_atomic_root)

        assert detector.get_next_phase(0) == 1
        assert detector.get_next_phase(5) == 6
        assert detector.get_next_phase(8) == 9

    def test_get_next_phase_at_end(self, temp_atomic_root):
        """Test getting next phase at end of pipeline."""
        detector = PhaseDetector(temp_atomic_root)

        result = detector.get_next_phase(9)

        assert result is None


# ============================================================================
# PHASE CHAINING TESTS
# ============================================================================

class TestPhaseChaining:
    """Test PhaseChaining main coordinator."""

    def test_is_phase_complete(self, phase_chaining, temp_atomic_root, sample_closeout_data):
        """Test checking if phase is complete."""
        create_closeout_file(temp_atomic_root, 0, sample_closeout_data)

        result = phase_chaining.is_phase_complete(0)

        assert result is True

    def test_get_phase_closeout(self, phase_chaining, temp_atomic_root, sample_closeout_data):
        """Test getting phase closeout data."""
        create_closeout_file(temp_atomic_root, 0, sample_closeout_data)

        result = phase_chaining.get_phase_closeout(0)

        assert result is not None
        assert result.phase_num == 0
        assert len(result.tasks_completed) == 3

    @patch('builtins.input', return_value='yes')
    def test_prompt_for_next_phase_yes(self, mock_input, phase_chaining, temp_atomic_root, sample_closeout_data):
        """Test user prompt with 'yes' response."""
        create_closeout_file(temp_atomic_root, 0, sample_closeout_data)

        result = phase_chaining.prompt_for_next_phase(0, 1)

        assert result is True
        mock_input.assert_called_once()

    @patch('builtins.input', return_value='no')
    def test_prompt_for_next_phase_no(self, mock_input, phase_chaining, temp_atomic_root, sample_closeout_data):
        """Test user prompt with 'no' response."""
        create_closeout_file(temp_atomic_root, 0, sample_closeout_data)

        result = phase_chaining.prompt_for_next_phase(0, 1)

        assert result is False

    @patch('builtins.input', return_value='y')
    def test_prompt_for_next_phase_y(self, mock_input, phase_chaining, temp_atomic_root, sample_closeout_data):
        """Test user prompt with 'y' response."""
        create_closeout_file(temp_atomic_root, 0, sample_closeout_data)

        result = phase_chaining.prompt_for_next_phase(0, 1)

        assert result is True

    @patch('builtins.input', side_effect=KeyboardInterrupt)
    def test_prompt_for_next_phase_cancelled(self, mock_input, phase_chaining, temp_atomic_root, sample_closeout_data):
        """Test user prompt with keyboard interrupt."""
        create_closeout_file(temp_atomic_root, 0, sample_closeout_data)

        result = phase_chaining.prompt_for_next_phase(0, 1)

        assert result is False

    def test_should_continue_to_next_phase_true(self, phase_chaining, temp_atomic_root, sample_closeout_data):
        """Test should_continue when phase is complete."""
        create_closeout_file(temp_atomic_root, 0, sample_closeout_data)

        result = phase_chaining.should_continue_to_next_phase(0)

        assert result is True

    def test_should_continue_to_next_phase_incomplete(self, phase_chaining):
        """Test should_continue when phase is incomplete."""
        result = phase_chaining.should_continue_to_next_phase(0)

        assert result is False

    def test_should_continue_to_next_phase_at_end(self, phase_chaining, temp_atomic_root):
        """Test should_continue at end of pipeline."""
        closeout_data = {
            "phase": "9-release",
            "phase_num": 9,
            "completed_at": "2024-01-01T12:00:00",
            "tasks_completed": ["901"],
            "summary": "Phase 9 complete."
        }
        create_closeout_file(temp_atomic_root, 9, closeout_data)

        result = phase_chaining.should_continue_to_next_phase(9)

        assert result is False

    def test_get_resume_phase_none_complete(self, phase_chaining):
        """Test resume phase when no phases complete."""
        result = phase_chaining.get_resume_phase()

        assert result == 0

    def test_get_resume_phase_some_complete(self, phase_chaining, temp_atomic_root):
        """Test resume phase when some phases complete."""
        # Complete phases 0 and 1
        for phase_num in [0, 1]:
            closeout_data = {
                "phase": f"{phase_num}-phase",
                "phase_num": phase_num,
                "completed_at": "2024-01-01T12:00:00",
                "tasks_completed": ["001"],
                "summary": f"Phase {phase_num} complete."
            }
            create_closeout_file(temp_atomic_root, phase_num, closeout_data)

        result = phase_chaining.get_resume_phase()

        assert result == 2

    def test_get_resume_phase_all_complete(self, phase_chaining, temp_atomic_root):
        """Test resume phase when all phases complete."""
        # Complete all phases
        for phase_num in range(10):
            closeout_data = {
                "phase": f"{phase_num}-phase",
                "phase_num": phase_num,
                "completed_at": "2024-01-01T12:00:00",
                "tasks_completed": ["001"],
                "summary": f"Phase {phase_num} complete."
            }
            create_closeout_file(temp_atomic_root, phase_num, closeout_data)

        result = phase_chaining.get_resume_phase()

        assert result is None

    @patch.object(PhaseChaining, '_execute_phase', return_value=True)
    def test_launch_next_phase_with_auto_confirm(self, mock_execute, phase_chaining, temp_atomic_root, sample_closeout_data):
        """Test launching next phase with auto-confirm."""
        create_closeout_file(temp_atomic_root, 0, sample_closeout_data)

        result = phase_chaining.launch_next_phase(0, auto_confirm=True)

        assert result is True
        mock_execute.assert_called_once_with(1)

    @patch.object(PhaseChaining, '_execute_phase', return_value=True)
    def test_launch_next_phase_at_end(self, mock_execute, phase_chaining, temp_atomic_root):
        """Test launching next phase at end of pipeline."""
        closeout_data = {
            "phase": "9-release",
            "phase_num": 9,
            "completed_at": "2024-01-01T12:00:00",
            "tasks_completed": ["901"],
            "summary": "Phase 9 complete."
        }
        create_closeout_file(temp_atomic_root, 9, closeout_data)

        result = phase_chaining.launch_next_phase(9, auto_confirm=True)

        assert result is False
        mock_execute.assert_not_called()

    @patch.object(PhaseChaining, '_execute_phase', return_value=True)
    def test_launch_next_phase_already_complete(self, mock_execute, phase_chaining, temp_atomic_root):
        """Test launching next phase when already complete."""
        # Complete phases 0 and 1
        for phase_num in [0, 1]:
            closeout_data = {
                "phase": f"{phase_num}-phase",
                "phase_num": phase_num,
                "completed_at": "2024-01-01T12:00:00",
                "tasks_completed": ["001"],
                "summary": f"Phase {phase_num} complete."
            }
            create_closeout_file(temp_atomic_root, phase_num, closeout_data)

        result = phase_chaining.launch_next_phase(0, auto_confirm=True)

        # Should skip phase 1 since it's already complete
        assert result is True
        mock_execute.assert_not_called()


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestPhaseChainingSummary:
    """Summary test to verify complete functionality."""

    def test_complete_phase_chaining_workflow(self, temp_atomic_root):
        """Test complete workflow: phase completion -> prompt -> launch."""
        # Setup: Create closeout for phase 0
        closeout_data = {
            "phase": "0-setup",
            "phase_num": 0,
            "completed_at": datetime.now().isoformat(),
            "tasks_completed": ["001", "002", "003"],
            "summary": "Phase 0 (Setup) completed successfully."
        }
        create_closeout_file(temp_atomic_root, 0, closeout_data)

        chaining = PhaseChaining(atomic_root=temp_atomic_root)

        # Test: Verify phase completion
        assert chaining.is_phase_complete(0) is True
        assert chaining.is_phase_complete(1) is False

        # Test: Should continue to next phase
        assert chaining.should_continue_to_next_phase(0) is True

        # Test: Get resume phase
        assert chaining.get_resume_phase() == 1

        # Test: Closeout data retrieval
        closeout = chaining.get_phase_closeout(0)
        assert closeout is not None
        assert closeout.phase_num == 0
        assert len(closeout.tasks_completed) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
