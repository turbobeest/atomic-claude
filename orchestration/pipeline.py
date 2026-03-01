"""
Phase Pipeline Manager

Comprehensive pipeline lifecycle management with phase dependencies, automatic
chaining, rollback, pause/resume, and state machine orchestration.

Features:
- Phase lifecycle (initialize, start, running, completed, failed)
- Phase dependency resolution and validation
- Automatic phase chaining with transition prompts
- Pipeline pause and resume capability
- Phase rollback with state restoration
- Closeout file parsing and validation
- Integration with StateManager and Config
- Phase state machine with validation
- Pre-flight checks for phase execution
- Pipeline health monitoring

Architecture:
- PhasePipeline: Main coordinator for pipeline execution
- PhaseLifecycle: Enum for phase states
- PhaseDependency: Phase dependency graph
- PhaseTransition: Phase transition handler
- PhaseValidator: Pre-flight validation

Usage:
    pipeline = PhasePipeline()

    # Execute single phase
    pipeline.run_phase(0)

    # Execute phase with auto-chaining
    pipeline.run_phase(1, auto_chain=True)

    # Resume from specific task
    pipeline.run_phase(2, resume_at="205")

    # Rollback to previous phase
    pipeline.rollback_to_phase(1)

    # Check pipeline health
    status = pipeline.get_pipeline_status()

Author: Phase Pipeline System
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.state import StateManager, StateLock
from core.config import Config
from core.memory import memory_init, memory_checkpoint, memory_handle_backtrack
from core.utils.file_ops import write_json

try:
    from core.graph import get_graph
    from core.graph.exceptions import GraphUnavailableError
except ImportError:
    get_graph = None
    GraphUnavailableError = Exception

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS & TYPES
# ============================================================================

class PhaseLifecycle(str, Enum):
    """Phase lifecycle states."""
    NOT_STARTED = "not_started"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class TransitionMode(str, Enum):
    """Phase transition modes."""
    AUTO = "auto"  # Automatic chaining
    PROMPT = "prompt"  # Prompt user before transition
    MANUAL = "manual"  # Manual phase execution only


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class PhaseMetadata:
    """Phase metadata and configuration."""
    phase_id: str
    phase_num: int
    phase_name: str
    module_path: str
    dependencies: List[int] = field(default_factory=list)
    required_closeout: bool = True
    can_skip: bool = False
    estimated_duration: Optional[int] = None  # seconds


@dataclass
class PipelineStatus:
    """Pipeline health status."""
    current_phase: Optional[int]
    last_completed_phase: Optional[int]
    total_phases: int
    completed_phases: int
    failed_phases: int
    pipeline_state: str
    last_updated: str
    estimated_completion: Optional[str] = None


# ============================================================================
# PHASE DEFINITIONS
# ============================================================================

# Phase metadata registry
PHASE_REGISTRY: Dict[int, PhaseMetadata] = {
    0: PhaseMetadata(
        phase_id="0-setup",
        phase_num=0,
        phase_name="Setup",
        module_path="phases.phase00.orchestrator00",
        dependencies=[],
        required_closeout=True,
        can_skip=False
    ),
    1: PhaseMetadata(
        phase_id="1-discovery",
        phase_num=1,
        phase_name="Discovery",
        module_path="phases.phase01.orchestrator01",
        dependencies=[0],
        required_closeout=True,
        can_skip=False
    ),
    2: PhaseMetadata(
        phase_id="2-prd",
        phase_num=2,
        phase_name="PRD",
        module_path="phases.phase02.orchestrator02",
        dependencies=[0, 1],
        required_closeout=True,
        can_skip=False
    ),
    3: PhaseMetadata(
        phase_id="3-tasking",
        phase_num=3,
        phase_name="Tasking",
        module_path="phases.phase03.orchestrator03",
        dependencies=[0, 1, 2],
        required_closeout=True,
        can_skip=False
    ),
    4: PhaseMetadata(
        phase_id="4-specification",
        phase_num=4,
        phase_name="Specification",
        module_path="phases.phase04.orchestrator04",
        dependencies=[0, 1, 2, 3],
        required_closeout=True,
        can_skip=False
    ),
    5: PhaseMetadata(
        phase_id="5-implementation",
        phase_num=5,
        phase_name="Implementation",
        module_path="phases.phase05.orchestrator05",
        dependencies=[0, 1, 2, 3, 4],
        required_closeout=True,
        can_skip=False
    ),
    6: PhaseMetadata(
        phase_id="6-code-review",
        phase_num=6,
        phase_name="Code Review",
        module_path="phases.phase06.orchestrator06",
        dependencies=[0, 1, 2, 3, 4, 5],
        required_closeout=True,
        can_skip=False
    ),
    7: PhaseMetadata(
        phase_id="7-integration",
        phase_num=7,
        phase_name="Integration",
        module_path="phases.phase07.orchestrator07",
        dependencies=[0, 1, 2, 3, 4, 5, 6],
        required_closeout=True,
        can_skip=False
    ),
    8: PhaseMetadata(
        phase_id="8-deployment-prep",
        phase_num=8,
        phase_name="Deployment Prep",
        module_path="phases.phase08.orchestrator08",
        dependencies=[0, 1, 2, 3, 4, 5, 6, 7],
        required_closeout=True,
        can_skip=False
    ),
    9: PhaseMetadata(
        phase_id="9-release",
        phase_num=9,
        phase_name="Release",
        module_path="phases.phase09.orchestrator09",
        dependencies=[0, 1, 2, 3, 4, 5, 6, 7, 8],
        required_closeout=True,
        can_skip=False
    ),
}


# ============================================================================
# PHASE VALIDATOR
# ============================================================================

class PhaseValidator:
    """Pre-flight validation for phase execution."""

    def __init__(self, state: StateManager, config: Config, atomic_root: Path):
        self.state = state
        self.config = config
        self.atomic_root = atomic_root

    def validate_phase(self, phase_num: int) -> Tuple[bool, List[str]]:
        """
        Validate phase can be executed.

        Args:
            phase_num: Phase number to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check phase exists
        if phase_num not in PHASE_REGISTRY:
            errors.append(f"Phase {phase_num} not found in registry")
            return False, errors

        metadata = PHASE_REGISTRY[phase_num]

        # Check orchestrator exists
        if not self._check_orchestrator_exists(metadata):
            errors.append(f"Orchestrator not found: {metadata.module_path}")

        # Check dependencies
        dep_errors = self._validate_dependencies(metadata)
        errors.extend(dep_errors)

        # Check closeout files for dependencies
        closeout_errors = self._validate_closeout_files(metadata)
        errors.extend(closeout_errors)

        # Check configuration (Phase 0 must be complete for phases 1+)
        if phase_num > 0 and not self._check_phase_0_complete():
            errors.append("Phase 0 (Setup) must be completed before other phases")

        return len(errors) == 0, errors

    def _check_orchestrator_exists(self, metadata: PhaseMetadata) -> bool:
        """Check orchestrator module exists."""
        module_parts = metadata.module_path.split('.')
        file_path = self.atomic_root / Path(*module_parts[:-1]) / f"{module_parts[-1]}.py"
        return file_path.exists()

    def _validate_dependencies(self, metadata: PhaseMetadata) -> List[str]:
        """Validate phase dependencies are complete."""
        errors = []
        for dep_phase_num in metadata.dependencies:
            dep_metadata = PHASE_REGISTRY.get(dep_phase_num)
            if not dep_metadata:
                errors.append(f"Dependency phase {dep_phase_num} not found")
                continue

            # Check phase-level completion first (set by mark_phase_complete)
            state_data = self.state.get_raw_state()
            phase_state = state_data.get('phases', {}).get(dep_metadata.phase_id, {})
            if phase_state.get('status') == 'completed':
                continue

            # Fallback: check if first task is complete
            if self.state.is_task_complete(dep_metadata.phase_id, "001"):
                continue

            # Phase hasn't started or isn't complete
            phase_data = self.state.get_phase_tasks(dep_metadata.phase_id)
            if not phase_data:
                errors.append(
                    f"Dependency phase {dep_phase_num} ({dep_metadata.phase_name}) "
                    f"has not been started"
                )
            else:
                # Phase has tasks but none completed — not satisfied
                has_completed = any(
                    t.get('status') == 'completed'
                    for t in phase_data.values()
                    if isinstance(t, dict)
                )
                if not has_completed:
                    errors.append(
                        f"Dependency phase {dep_phase_num} ({dep_metadata.phase_name}) "
                        f"has been started but has no completed tasks"
                    )

        return errors

    def _validate_closeout_files(self, metadata: PhaseMetadata) -> List[str]:
        """Validate required closeout files exist for dependencies."""
        errors = []
        for dep_phase_num in metadata.dependencies:
            dep_metadata = PHASE_REGISTRY.get(dep_phase_num)
            if not dep_metadata or not dep_metadata.required_closeout:
                continue

            closeout_file = (
                self.atomic_root / ".outputs" /
                dep_metadata.phase_id / "closeout.json"
            )

            if not closeout_file.exists():
                errors.append(
                    f"Dependency phase {dep_phase_num} ({dep_metadata.phase_name}) "
                    f"missing closeout file: {closeout_file}"
                )

        return errors

    def _check_phase_0_complete(self) -> bool:
        """Check if Phase 0 is complete."""
        phase_0_closeout = self.atomic_root / ".outputs" / "0-setup" / "closeout.json"
        return phase_0_closeout.exists()


# ============================================================================
# PHASE TRANSITION HANDLER
# ============================================================================

class PhaseTransition:
    """Handle transitions between phases."""

    def __init__(self, pipeline: 'PhasePipeline'):
        self.pipeline = pipeline

    def transition_to_next(
        self,
        current_phase: int,
        mode: TransitionMode = TransitionMode.PROMPT
    ) -> Optional[int]:
        """
        Transition to next phase.

        Args:
            current_phase: Current phase number
            mode: Transition mode (auto, prompt, manual)

        Returns:
            Next phase number if transitioning, None if staying
        """
        next_phase = current_phase + 1

        # Check if next phase exists
        if next_phase not in PHASE_REGISTRY:
            print(f"\n✅ Pipeline complete! No more phases after Phase {current_phase}.")
            return None

        next_metadata = PHASE_REGISTRY[next_phase]

        if mode == TransitionMode.AUTO:
            return next_phase

        elif mode == TransitionMode.PROMPT:
            return self._prompt_user_transition(current_phase, next_phase, next_metadata)

        else:  # MANUAL
            print(f"\n✓ Phase {current_phase} complete.")
            print(f"To continue to Phase {next_phase}: python main.py run {next_phase}")
            return None

    def _prompt_user_transition(
        self,
        current_phase: int,
        next_phase: int,
        next_metadata: PhaseMetadata
    ) -> Optional[int]:
        """Prompt user for phase transition."""
        print("\n" + "="*80)
        print(f"  Phase {current_phase} Complete!")
        print("="*80)
        print(f"\nNext: Phase {next_phase} - {next_metadata.phase_name}")
        print("\nOptions:")
        print("  [C] Continue to next phase (default)")
        print("  [p] Pause (resume later)")
        print("  [q] Quit")
        print()

        while True:
            choice = input("Choice (C/p/q): ").strip().lower()

            if choice in ('c', 'continue', ''):
                return next_phase
            elif choice in ('p', 'pause'):
                print(f"\n⏸️  Pipeline paused.")
                print(f"To resume: python main.py run {next_phase}")
                return None
            elif choice in ('q', 'quit'):
                print("\n👋 Exiting pipeline.")
                return None
            else:
                print("Invalid choice. Please enter 'c', 'p', or 'q'.")

    def display_transition_banner(self, from_phase: int, to_phase: int) -> None:
        """Display transition banner between phases."""
        from_metadata = PHASE_REGISTRY.get(from_phase)
        to_metadata = PHASE_REGISTRY.get(to_phase)

        if not from_metadata or not to_metadata:
            return

        print("\n" + "="*80)
        print(f"  PHASE TRANSITION")
        print("="*80)
        print(f"  From: Phase {from_phase} - {from_metadata.phase_name}")
        print(f"  To:   Phase {to_phase} - {to_metadata.phase_name}")
        print("="*80 + "\n")


# ============================================================================
# MAIN PIPELINE MANAGER
# ============================================================================

class PhasePipeline:
    """
    Main pipeline coordinator for phase lifecycle management.

    Features:
    - Phase execution with dependency validation
    - Automatic phase chaining
    - Pause and resume capability
    - Phase rollback with state restoration
    - Pipeline health monitoring
    - Pre-flight validation

    Usage:
        pipeline = PhasePipeline()
        pipeline.run_phase(0)
        pipeline.run_phase(1, auto_chain=True)
    """

    def __init__(self, atomic_root: Path = None):
        """
        Initialize pipeline manager.

        Args:
            atomic_root: Atomic root directory (defaults to cwd)
        """
        self.atomic_root = atomic_root or Path.cwd()
        self.state = StateManager(atomic_root=self.atomic_root)
        self.config = Config(atomic_root=self.atomic_root)
        self.validator = PhaseValidator(self.state, self.config, self.atomic_root)
        self.transition = PhaseTransition(self)

    # ========================================================================
    # PHASE EXECUTION
    # ========================================================================

    def run_phase(
        self,
        phase_num: int,
        resume_at: Optional[str] = None,
        auto_chain: bool = False,
        transition_mode: TransitionMode = TransitionMode.PROMPT
    ) -> bool:
        """
        Execute a phase with dependency validation.

        Args:
            phase_num: Phase number to execute (0-9)
            resume_at: Optional task ID to resume from
            auto_chain: Automatically chain to next phase on success
            transition_mode: How to handle phase transitions

        Returns:
            True if phase completed successfully, False otherwise
        """
        # Validate phase
        is_valid, errors = self.validator.validate_phase(phase_num)
        if not is_valid:
            print(f"\n❌ Phase {phase_num} validation failed:")
            for error in errors:
                print(f"   - {error}")
            return False

        metadata = PHASE_REGISTRY[phase_num]

        # Check if phase is already complete (all tasks done + closeout exists)
        # If so, auto-advance instead of running the full orchestrator
        if self._is_phase_already_complete(metadata) and not resume_at:
            print(f"\n  ✓ Phase {phase_num} ({metadata.phase_name}) already complete, advancing...")
            # Skip directly to transition handling
            return self._handle_phase_transition(
                phase_num, auto_chain, transition_mode
            )

        # Display phase header (skip when resuming — orchestrator prints its own)
        if not resume_at:
            self._display_phase_header(metadata)

        # Set current phase in state
        self.state.set_current_phase(metadata.phase_id)

        # Initialize memory system with FalkorDB graph support
        self._setup_phase_memory()

        # Execute phase via orchestrator
        success = self._execute_phase_orchestrator(metadata, resume_at)

        if not success:
            print(f"\n❌ Phase {phase_num} failed or stopped.")
            return False

        # Finalize: closeout, state update, memory checkpoint
        self._finalize_phase(metadata)

        print(f"\n✅ Phase {phase_num} complete!")

        # Handle phase transition
        return self._handle_phase_transition(
            phase_num, auto_chain, transition_mode
        )

    def _is_phase_already_complete(self, metadata: PhaseMetadata) -> bool:
        """Check if a phase is already fully complete (status + closeout)."""
        state_data = self.state.get_raw_state()
        phase_state = state_data.get('phases', {}).get(metadata.phase_id, {})
        if phase_state.get('status') != 'completed':
            return False
        # Also verify closeout file exists
        closeout_file = self._closeout_path(metadata.phase_id)
        return closeout_file.exists()

    def _handle_phase_transition(
        self,
        phase_num: int,
        auto_chain: bool,
        transition_mode: TransitionMode
    ) -> bool:
        """Handle transition to the next phase after completion."""
        if auto_chain or transition_mode != TransitionMode.MANUAL:
            next_phase_num = phase_num + 1
            # Check human gates — force PROMPT even if auto_chain
            human_gates = self.config.get("pipeline.human_gates", [0, 2, 5, 9])
            effective_mode = TransitionMode.AUTO if auto_chain else transition_mode
            if next_phase_num in human_gates:
                effective_mode = TransitionMode.PROMPT

            next_phase = self.transition.transition_to_next(
                phase_num,
                effective_mode
            )

            if next_phase is not None:
                self.transition.display_transition_banner(phase_num, next_phase)
                return self.run_phase(next_phase, auto_chain=auto_chain,
                                      transition_mode=transition_mode)

        return True

    def _execute_phase_orchestrator(
        self,
        metadata: PhaseMetadata,
        resume_at: Optional[str]
    ) -> bool:
        """Execute phase orchestrator module."""
        try:
            # Import orchestrator dynamically
            module = __import__(metadata.module_path, fromlist=['run_phase'])

            # Execute run_phase function
            success = module.run_phase(resume_at=resume_at)

            return success

        except ImportError as e:
            print(f"\n❌ Failed to import orchestrator: {metadata.module_path}")
            print(f"   Error: {e}")
            return False
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception as e:
            logger.error("Phase execution error in %s: %s", metadata.module_path, e, exc_info=True)
            print(f"\n❌ Phase execution error: {e}")
            return False

    def _display_phase_header(self, metadata: PhaseMetadata) -> None:
        """Display phase execution header."""
        print("\n" + "="*80)
        print(f"  PHASE {metadata.phase_num}: {metadata.phase_name.upper()}")
        print("="*80)
        print(f"  Phase ID: {metadata.phase_id}")
        if metadata.dependencies:
            print(f"  Dependencies: {', '.join(map(str, metadata.dependencies))}")
        print("="*80 + "\n")

    def _closeout_path(self, phase_id: str) -> Path:
        """Return the canonical closeout file path for a phase."""
        return self.atomic_root / ".outputs" / phase_id / "closeout.json"

    def _setup_phase_memory(self) -> None:
        """Initialize memory system with optional FalkorDB graph support."""
        graph = None
        if get_graph is not None:
            try:
                graph = get_graph(phase_id="pipeline")
            except GraphUnavailableError:
                logger.debug("FalkorDB unavailable for pipeline memory init")
            except Exception as e:
                logger.debug("Graph init failed for pipeline memory: %s", e)

        try:
            memory_init(self.atomic_root / ".state", graph=graph)
        except Exception as e:
            logger.warning("memory_init failed: %s", e, exc_info=True)
            print(f"  [memory] init warning: {e}")

    def _finalize_phase(self, metadata: PhaseMetadata) -> None:
        """Write closeout, mark phase complete, and create memory checkpoint.

        Closeout is written first so that a crash between steps does not
        leave the phase marked complete without a closeout file.
        """
        # Reload state from disk (orchestrator saved task completions via its own StateManager)
        # Lock covers reload + mark_phase_complete + set_current_phase to prevent
        # concurrent dashboard writes from being overwritten (TOCTOU fix)
        lock = StateLock(self.state.lock_file)
        with lock:
            self.state.reload()

            # Write closeout BEFORE marking phase complete (Finding #2)
            if metadata.required_closeout:
                self._ensure_closeout_exists(metadata)

            # Mark phase complete (after closeout is safely on disk)
            # auto_save=False to avoid double save — set_current_phase will save both changes
            self.state.mark_phase_complete(metadata.phase_id, auto_save=False)

            # Clear current_phase so get_pipeline_status doesn't report stale "running"
            self.state.set_current_phase(None)

        # Memory checkpoint at phase boundary
        try:
            memory_checkpoint(
                phase=metadata.phase_num,
                phase_name=metadata.phase_name,
                summary=f"Phase {metadata.phase_num} ({metadata.phase_name}) completed",
                artifacts=[str(self._closeout_path(metadata.phase_id))],
                state_snapshot={"phase_id": metadata.phase_id, "completed_at": datetime.now(timezone.utc).isoformat()}
            )
        except Exception as e:
            logger.warning("memory_checkpoint failed: %s", e, exc_info=True)
            print(f"  [memory] checkpoint warning: {e}")

    def _ensure_closeout_exists(self, metadata: PhaseMetadata) -> None:
        """Ensure closeout file exists for phase."""
        import json
        import os
        import tempfile

        closeout_file = self._closeout_path(metadata.phase_id)

        if closeout_file.exists():
            return

        # Create minimal closeout if missing
        print(f"\n⚠️  Creating minimal closeout file for {metadata.phase_id}")

        closeout_data = {
            "phase_id": metadata.phase_id,
            "phase_name": metadata.phase_name,
            "status": "complete",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "note": "Generated by pipeline manager"
        }

        # Atomic write: temp file + os.replace to avoid corruption on crash
        closeout_file.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=closeout_file.parent, suffix=".tmp", prefix="closeout_")
        try:
            with os.fdopen(fd, 'w') as tmp_f:
                tmp_f.write(json.dumps(closeout_data, indent=2))
            os.replace(tmp_path, closeout_file)
        except BaseException:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    # ========================================================================
    # PIPELINE CONTROL
    # ========================================================================

    def rollback_to_phase(
        self,
        phase_num: int,
        task_id: Optional[str] = None
    ) -> bool:
        """
        Rollback pipeline to specific phase.

        This clears all state after the target phase and deletes outputs.

        Args:
            phase_num: Phase to rollback to
            task_id: Optional task within phase to rollback to

        Returns:
            True if rollback successful
        """
        # Use existing backtrack functionality
        from orchestration.backtrack import backtrack_to

        print(f"\n🔄 Rolling back to Phase {phase_num}")
        if task_id:
            print(f"   Task: {task_id}")

        # Clear memory state for phases being rolled back
        try:
            memory_init(self.atomic_root / ".state")
            result = memory_handle_backtrack(phase_num)
            print(f"   Memory: cleared {result.get('cleared_entries', 0)} entries, "
                  f"invalidated {result.get('invalidated_checkpoints', 0)} checkpoints")
        except Exception as e:
            print(f"  [memory] backtrack warning: {e}")

        try:
            backtrack_to(phase_num, task_id)
            print(f"\n✅ Rollback complete")
            return True
        except Exception as e:
            print(f"\n❌ Rollback failed: {e}")
            return False

    # ========================================================================
    # PIPELINE STATUS & HEALTH
    # ========================================================================

    def get_pipeline_status(self) -> PipelineStatus:
        """
        Get current pipeline status.

        Returns:
            PipelineStatus with health information
        """
        current_phase_id = self.state.get_current_phase()
        current_phase = None
        if current_phase_id:
            try:
                current_phase = int(current_phase_id.split('-')[0])
            except (ValueError, IndexError):
                logger.warning("Cannot parse phase number from '%s'", current_phase_id)

        # Count completed phases
        completed_phases = 0
        failed_phases = 0
        last_completed = None

        for phase_num in sorted(PHASE_REGISTRY.keys()):
            metadata = PHASE_REGISTRY[phase_num]
            phase_data = self.state.get_phase_tasks(metadata.phase_id)

            if phase_data:
                # Check phase-level status from state
                state_data = self.state.get_raw_state()
                phase_state = state_data.get('phases', {}).get(metadata.phase_id, {})
                phase_status = phase_state.get('status')

                if phase_status == 'failed':
                    failed_phases += 1
                elif phase_status == 'completed' or self.state.is_task_complete(metadata.phase_id, "001"):
                    completed_phases += 1
                    last_completed = phase_num

        # Determine pipeline state
        if current_phase is not None:
            pipeline_state = "running"
        elif completed_phases == len(PHASE_REGISTRY):
            pipeline_state = "complete"
        elif completed_phases > 0:
            pipeline_state = "paused"
        else:
            pipeline_state = "not_started"

        return PipelineStatus(
            current_phase=current_phase,
            last_completed_phase=last_completed,
            total_phases=len(PHASE_REGISTRY),
            completed_phases=completed_phases,
            failed_phases=failed_phases,
            pipeline_state=pipeline_state,
            last_updated=datetime.now(timezone.utc).isoformat()
        )

    def display_pipeline_status(self) -> None:
        """Display formatted pipeline status."""
        status = self.get_pipeline_status()

        print("\n" + "="*80)
        print("  PIPELINE STATUS")
        print("="*80)
        print(f"  State: {status.pipeline_state.upper()}")
        print(f"  Progress: {status.completed_phases}/{status.total_phases} phases complete")

        if status.current_phase is not None:
            metadata = PHASE_REGISTRY[status.current_phase]
            print(f"  Current: Phase {status.current_phase} - {metadata.phase_name}")

        if status.last_completed_phase is not None:
            last_metadata = PHASE_REGISTRY[status.last_completed_phase]
            print(f"  Last Complete: Phase {status.last_completed_phase} - {last_metadata.phase_name}")

        print("="*80)
        print()

        # Display phase breakdown
        for phase_num in sorted(PHASE_REGISTRY.keys()):
            metadata = PHASE_REGISTRY[phase_num]

            # Check completion
            closeout_file = self._closeout_path(metadata.phase_id)

            if closeout_file.exists():
                icon = "✅"
                status_str = "COMPLETE"
            elif phase_num == status.current_phase:
                icon = "▶️"
                status_str = "RUNNING"
            else:
                icon = "⭕"
                status_str = "PENDING"

            print(f"  {icon} Phase {phase_num}: {metadata.phase_name:<20} [{status_str}]")

        print()

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def validate_pipeline(self) -> Tuple[bool, List[str]]:
        """
        Validate entire pipeline configuration.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check all orchestrators exist
        for phase_num, metadata in PHASE_REGISTRY.items():
            if not self.validator._check_orchestrator_exists(metadata):
                errors.append(
                    f"Phase {phase_num} orchestrator missing: {metadata.module_path}"
                )

        # Check dependency graph is acyclic
        # (Current structure is linear so no cycles possible)

        return len(errors) == 0, errors


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("Testing pipeline module...\n")

    pipeline = PhasePipeline()

    print("Pipeline validation:")
    is_valid, errors = pipeline.validate_pipeline()
    if is_valid:
        print("  ✓ Pipeline configuration valid")
    else:
        print("  ✗ Pipeline validation errors:")
        for error in errors:
            print(f"    - {error}")

    print("\nPipeline status:")
    pipeline.display_pipeline_status()

    print("\n✓ pipeline.py module ready")
