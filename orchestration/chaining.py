"""
Phase Chaining Logic

Automatic phase-to-phase transitions with user confirmation prompts.

Features:
- Detect phase completion via closeout.json
- Parse and validate closeout metadata
- User confirmation prompts with rich formatting
- Automatic next phase launch
- Skip completed phases on resume
- Integration with StateManager and main pipeline

Architecture:
- PhaseChaining: Main coordinator for phase transitions
- CloseoutParser: Validates and extracts closeout metadata
- PromptFormatter: Rich console formatting for user prompts
- PhaseDetector: Detects available and completed phases

Usage:
    chaining = PhaseChaining()

    # Check if phase should proceed to next
    if chaining.should_continue_to_next_phase(current_phase=0):
        chaining.launch_next_phase(current_phase=0)

    # Or use automatic chaining
    chaining.auto_chain_phases(starting_phase=0)

Author: Phase Chaining Implementation
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from dataclasses import dataclass

from core.state import StateManager


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class CloseoutData:
    """Parsed closeout metadata."""
    phase: str
    phase_num: int
    completed_at: str
    tasks_completed: List[str]
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            'phase': self.phase,
            'phase_num': self.phase_num,
            'completed_at': self.completed_at,
            'tasks_completed': self.tasks_completed,
            'summary': self.summary
        }


# ============================================================================
# CLOSEOUT PARSER
# ============================================================================

class CloseoutParser:
    """
    Validates and parses phase closeout files.

    Closeout file structure (from orchestrator create_closeout):
    {
        "phase": "0-setup",
        "phase_num": 0,
        "completed_at": "2024-01-01T00:00:00",
        "tasks_completed": ["001", "002", "003", ...],
        "summary": "Phase 0 (Setup) completed successfully."
    }
    """

    @staticmethod
    def parse(closeout_path: Path) -> Optional[CloseoutData]:
        """
        Parse closeout file.

        Args:
            closeout_path: Path to closeout.json

        Returns:
            CloseoutData if valid, None if invalid or missing
        """
        if not closeout_path.exists():
            return None

        try:
            with open(closeout_path, 'r') as f:
                data = json.load(f)

            # Validate required fields
            required_fields = ['phase', 'phase_num', 'completed_at', 'tasks_completed', 'summary']
            for field in required_fields:
                if field not in data:
                    print(f"Warning: closeout.json missing required field: {field}")
                    return None

            # Create CloseoutData
            return CloseoutData(
                phase=data['phase'],
                phase_num=data['phase_num'],
                completed_at=data['completed_at'],
                tasks_completed=data['tasks_completed'],
                summary=data['summary']
            )

        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse closeout.json: {e}")
            return None
        except Exception as e:
            print(f"Warning: Error reading closeout.json: {e}")
            return None

    @staticmethod
    def validate(closeout_data: CloseoutData) -> Tuple[bool, Optional[str]]:
        """
        Validate closeout data.

        Args:
            closeout_data: Parsed closeout data

        Returns:
            (is_valid, error_message)
        """
        # Validate phase format
        if not closeout_data.phase or '-' not in closeout_data.phase:
            return False, f"Invalid phase format: {closeout_data.phase}"

        # Validate phase number
        if closeout_data.phase_num < 0 or closeout_data.phase_num > 9:
            return False, f"Invalid phase number: {closeout_data.phase_num}"

        # Validate tasks completed
        if not closeout_data.tasks_completed:
            return False, "No tasks completed"

        # Validate completed_at timestamp
        try:
            datetime.fromisoformat(closeout_data.completed_at.replace('Z', '+00:00'))
        except ValueError:
            return False, f"Invalid timestamp: {closeout_data.completed_at}"

        return True, None


# ============================================================================
# PROMPT FORMATTER
# ============================================================================

class PromptFormatter:
    """Rich console formatting for user prompts."""

    # Phase names
    PHASE_NAMES = {
        0: "Setup",
        1: "Discovery",
        2: "PRD",
        3: "Tasking",
        4: "Specification",
        5: "Implementation",
        6: "Code Review",
        7: "Integration",
        8: "Deployment Prep",
        9: "Release"
    }

    @staticmethod
    def phase_complete_banner(closeout: CloseoutData) -> str:
        """Format phase completion banner."""
        phase_name = PromptFormatter.PHASE_NAMES.get(closeout.phase_num, "Unknown")

        lines = [
            "",
            "=" * 80,
            f"  PHASE {closeout.phase_num} COMPLETE: {phase_name.upper()}",
            "=" * 80,
            "",
            f"  Summary: {closeout.summary}",
            f"  Tasks Completed: {len(closeout.tasks_completed)}",
            f"  Completed At: {closeout.completed_at}",
            "=" * 80,
            ""
        ]
        return "\n".join(lines)

    @staticmethod
    def next_phase_prompt(current_phase: int, next_phase: int) -> str:
        """Format next phase prompt."""
        current_name = PromptFormatter.PHASE_NAMES.get(current_phase, "Unknown")
        next_name = PromptFormatter.PHASE_NAMES.get(next_phase, "Unknown")

        lines = [
            "",
            f"Next: Phase {next_phase} - {next_name}",
            "",
            "Would you like to continue to the next phase? (yes/no): "
        ]
        return "\n".join(lines[:-1]) + lines[-1]

    @staticmethod
    def pipeline_complete_banner() -> str:
        """Format pipeline completion banner."""
        lines = [
            "",
            "=" * 80,
            "  PIPELINE COMPLETE",
            "=" * 80,
            "",
            "  All phases completed successfully!",
            "  Your project is ready for deployment.",
            "",
            "=" * 80,
            ""
        ]
        return "\n".join(lines)

    @staticmethod
    def phase_already_complete_message(phase_num: int) -> str:
        """Format already-complete message."""
        phase_name = PromptFormatter.PHASE_NAMES.get(phase_num, "Unknown")
        return f"\nPhase {phase_num} ({phase_name}) already complete, skipping...\n"


# ============================================================================
# PHASE DETECTOR
# ============================================================================

class PhaseDetector:
    """Detects available and completed phases."""

    def __init__(self, atomic_root: Path):
        """
        Initialize phase detector.

        Args:
            atomic_root: Atomic Claude root directory
        """
        self.atomic_root = atomic_root
        self.outputs_dir = atomic_root / ".outputs"

    def is_phase_complete(self, phase_num: int) -> bool:
        """
        Check if phase is complete by checking for closeout.json.

        Args:
            phase_num: Phase number (0-9)

        Returns:
            True if phase has closeout.json, False otherwise
        """
        phase_id = self._phase_num_to_id(phase_num)
        closeout_path = self.outputs_dir / phase_id / "closeout.json"

        if not closeout_path.exists():
            return False

        # Validate closeout
        closeout = CloseoutParser.parse(closeout_path)
        if not closeout:
            return False

        valid, _ = CloseoutParser.validate(closeout)
        return valid

    def get_closeout(self, phase_num: int) -> Optional[CloseoutData]:
        """
        Get parsed closeout data for a phase.

        Args:
            phase_num: Phase number (0-9)

        Returns:
            CloseoutData if exists and valid, None otherwise
        """
        phase_id = self._phase_num_to_id(phase_num)
        closeout_path = self.outputs_dir / phase_id / "closeout.json"
        return CloseoutParser.parse(closeout_path)

    def get_next_phase(self, current_phase: int) -> Optional[int]:
        """
        Get next phase number.

        Args:
            current_phase: Current phase number

        Returns:
            Next phase number (current + 1) or None if at end
        """
        next_phase = current_phase + 1
        if next_phase > 9:
            return None
        return next_phase

    def _phase_num_to_id(self, phase_num: int) -> str:
        """
        Convert phase number to phase ID.

        Args:
            phase_num: Phase number (0-9)

        Returns:
            Phase ID (e.g., "0-setup", "1-discovery")
        """
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

        name = phase_names.get(phase_num, f"phase{phase_num}")
        return f"{phase_num}-{name}"


# ============================================================================
# PHASE CHAINING COORDINATOR
# ============================================================================

class PhaseChaining:
    """
    Main coordinator for phase-to-phase transitions.

    Features:
    - Automatic phase completion detection
    - User confirmation prompts
    - Next phase launching
    - Skip completed phases on resume
    - Integration with StateManager

    Usage:
        chaining = PhaseChaining()

        # Manual control
        if chaining.should_continue_to_next_phase(0):
            chaining.launch_next_phase(0)

        # Automatic chaining
        chaining.auto_chain_phases(starting_phase=0)
    """

    def __init__(self, atomic_root: Path = None, state_manager: StateManager = None):
        """
        Initialize phase chaining.

        Args:
            atomic_root: Atomic Claude root directory (defaults to cwd)
            state_manager: StateManager instance (creates new if None)
        """
        self.atomic_root = atomic_root or Path.cwd()
        self.state_manager = state_manager or StateManager(atomic_root=self.atomic_root)
        self.detector = PhaseDetector(self.atomic_root)
        self.formatter = PromptFormatter()

    # ========================================================================
    # PHASE COMPLETION DETECTION
    # ========================================================================

    def is_phase_complete(self, phase_num: int) -> bool:
        """
        Check if phase is complete.

        Args:
            phase_num: Phase number (0-9)

        Returns:
            True if phase has valid closeout.json
        """
        return self.detector.is_phase_complete(phase_num)

    def get_phase_closeout(self, phase_num: int) -> Optional[CloseoutData]:
        """
        Get closeout data for a phase.

        Args:
            phase_num: Phase number

        Returns:
            CloseoutData if exists, None otherwise
        """
        return self.detector.get_closeout(phase_num)

    # ========================================================================
    # USER CONFIRMATION
    # ========================================================================

    def prompt_for_next_phase(self, current_phase: int, next_phase: int) -> bool:
        """
        Prompt user to continue to next phase.

        Args:
            current_phase: Current phase number
            next_phase: Next phase number

        Returns:
            True if user confirms, False otherwise
        """
        # Get closeout for current phase
        closeout = self.get_phase_closeout(current_phase)
        if not closeout:
            print("\nWarning: No closeout data found for current phase")
            return False

        # Display completion banner
        print(self.formatter.phase_complete_banner(closeout))

        # Prompt for next phase
        prompt = self.formatter.next_phase_prompt(current_phase, next_phase)

        try:
            response = input(prompt).strip().lower()
            return response in ('y', 'yes')
        except (KeyboardInterrupt, EOFError):
            print("\n\nOperation cancelled by user.")
            return False

    # ========================================================================
    # PHASE LAUNCHING
    # ========================================================================

    def launch_next_phase(self, current_phase: int, auto_confirm: bool = False) -> bool:
        """
        Launch next phase.

        Args:
            current_phase: Current phase number
            auto_confirm: Skip user confirmation (for testing)

        Returns:
            True if launched successfully, False otherwise
        """
        # Get next phase
        next_phase = self.detector.get_next_phase(current_phase)
        if next_phase is None:
            print(self.formatter.pipeline_complete_banner())
            return False

        # Check if already complete
        if self.is_phase_complete(next_phase):
            print(self.formatter.phase_already_complete_message(next_phase))
            return True

        # Prompt user (unless auto_confirm)
        if not auto_confirm:
            if not self.prompt_for_next_phase(current_phase, next_phase):
                print("\nStopping at Phase", current_phase)
                print(f"To continue later: python main.py run {next_phase}")
                return False

        # Launch next phase
        try:
            return self._execute_phase(next_phase)
        except Exception as e:
            print(f"\nError launching Phase {next_phase}: {e}")
            return False

    def _execute_phase(self, phase_num: int) -> bool:
        """
        Execute a phase by importing and running its orchestrator.

        Args:
            phase_num: Phase number to execute

        Returns:
            True if phase completed successfully
        """
        phase_name = self.formatter.PHASE_NAMES.get(phase_num, "Unknown")

        print(f"\n{'='*80}")
        print(f"  LAUNCHING PHASE {phase_num}: {phase_name.upper()}")
        print(f"{'='*80}\n")

        try:
            # Import phase orchestrator dynamically
            phase_module = __import__(
                f"phases.phase{phase_num:02d}.orchestrator{phase_num:02d}",
                fromlist=["run_phase"]
            )

            # Execute phase
            success = phase_module.run_phase()

            if not success:
                print(f"\nPhase {phase_num} stopped.")
                return False

            return True

        except ImportError as e:
            print(f"\nError: Could not load Phase {phase_num} orchestrator")
            print(f"Expected: phases/phase{phase_num:02d}/orchestrator{phase_num:02d}.py")
            print(f"Error: {e}")
            return False

    # ========================================================================
    # AUTOMATIC CHAINING
    # ========================================================================

    def should_continue_to_next_phase(self, current_phase: int) -> bool:
        """
        Check if should continue to next phase.

        Args:
            current_phase: Current phase number

        Returns:
            True if current phase is complete and next phase exists
        """
        # Check if current phase is complete
        if not self.is_phase_complete(current_phase):
            return False

        # Check if next phase exists
        next_phase = self.detector.get_next_phase(current_phase)
        if next_phase is None:
            return False

        return True

    def auto_chain_phases(self, starting_phase: int = 0, auto_confirm: bool = False) -> bool:
        """
        Automatically chain phases from starting point to end.

        Args:
            starting_phase: Phase to start from (defaults to 0)
            auto_confirm: Skip user confirmation prompts (for testing)

        Returns:
            True if all phases completed, False if stopped
        """
        current_phase = starting_phase

        while current_phase <= 9:
            # Skip if already complete
            if self.is_phase_complete(current_phase):
                print(self.formatter.phase_already_complete_message(current_phase))
                current_phase += 1
                continue

            # Execute current phase
            if not self._execute_phase(current_phase):
                return False

            # Check if should continue
            if not self.should_continue_to_next_phase(current_phase):
                break

            # Launch next phase
            if not self.launch_next_phase(current_phase, auto_confirm=auto_confirm):
                return False

            current_phase += 1

        # All phases complete
        if current_phase > 9:
            print(self.formatter.pipeline_complete_banner())

        return True

    # ========================================================================
    # RESUME LOGIC
    # ========================================================================

    def get_resume_phase(self) -> Optional[int]:
        """
        Get the next phase that needs to be executed.

        Returns:
            Next incomplete phase number, or None if all complete
        """
        for phase_num in range(10):
            if not self.is_phase_complete(phase_num):
                return phase_num

        # All phases complete
        return None

    def resume_from_phase(self, phase_num: int, auto_confirm: bool = False) -> bool:
        """
        Resume pipeline from a specific phase.

        Args:
            phase_num: Phase to resume from
            auto_confirm: Skip user confirmation prompts

        Returns:
            True if resumed successfully
        """
        # Skip completed phases
        while phase_num <= 9 and self.is_phase_complete(phase_num):
            print(self.formatter.phase_already_complete_message(phase_num))
            phase_num += 1

        if phase_num > 9:
            print(self.formatter.pipeline_complete_banner())
            return True

        # Resume from first incomplete phase
        return self.auto_chain_phases(starting_phase=phase_num, auto_confirm=auto_confirm)


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("Testing phase chaining module...\n")

    # Create temp test environment
    import tempfile
    import shutil

    test_dir = Path(tempfile.mkdtemp())
    outputs_dir = test_dir / ".outputs"
    outputs_dir.mkdir()

    # Create fake closeout
    phase0_dir = outputs_dir / "0-setup"
    phase0_dir.mkdir()

    closeout_data = {
        "phase": "0-setup",
        "phase_num": 0,
        "completed_at": datetime.now().isoformat(),
        "tasks_completed": ["001", "002", "003"],
        "summary": "Phase 0 (Setup) completed successfully."
    }

    with open(phase0_dir / "closeout.json", "w") as f:
        json.dump(closeout_data, f, indent=2)

    # Test chaining
    chaining = PhaseChaining(atomic_root=test_dir)

    print("Testing phase completion detection...")
    assert chaining.is_phase_complete(0), "Phase 0 should be complete"
    assert not chaining.is_phase_complete(1), "Phase 1 should not be complete"

    print("Testing closeout parsing...")
    closeout = chaining.get_phase_closeout(0)
    assert closeout is not None, "Should parse closeout"
    assert closeout.phase_num == 0, "Phase num should be 0"
    assert len(closeout.tasks_completed) == 3, "Should have 3 tasks"

    print("Testing next phase detection...")
    assert chaining.should_continue_to_next_phase(0), "Should continue to phase 1"
    assert not chaining.should_continue_to_next_phase(1), "Phase 1 not complete"

    print("Testing resume phase detection...")
    resume_phase = chaining.get_resume_phase()
    assert resume_phase == 1, "Should resume from phase 1"

    # Cleanup
    shutil.rmtree(test_dir)

    print("\n✓ Phase chaining module ready")
