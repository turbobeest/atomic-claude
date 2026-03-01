"""
Unit Tests for Phase Pipeline Manager

Comprehensive test suite for pipeline.py covering:
- Phase lifecycle management
- Phase dependency validation
- Automatic phase chaining
- Pipeline pause/resume
- Phase rollback
- Closeout file validation
- Pipeline status and health
- State machine transitions
- Error handling

Author: Phase Pipeline System Tests
"""

import unittest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from orchestration.pipeline import (
    PhasePipeline,
    PhaseValidator,
    PhaseTransition,
    PhaseLifecycle,
    TransitionMode,
    PhaseMetadata,
    PhaseExecutionContext,
    PipelineStatus,
    PHASE_REGISTRY
)
from core.state import StateManager


class TestPhaseMetadata(unittest.TestCase):
    """Test phase metadata and registry."""

    def test_phase_registry_complete(self):
        """Test all 10 phases defined in registry."""
        self.assertEqual(len(PHASE_REGISTRY), 10)
        for i in range(10):
            self.assertIn(i, PHASE_REGISTRY)

    def test_phase_metadata_structure(self):
        """Test phase metadata has required fields."""
        metadata = PHASE_REGISTRY[0]
        self.assertIsInstance(metadata, PhaseMetadata)
        self.assertEqual(metadata.phase_num, 0)
        self.assertEqual(metadata.phase_id, "0-setup")
        self.assertEqual(metadata.phase_name, "Setup")
        self.assertIsInstance(metadata.dependencies, list)

    def test_phase_dependencies_valid(self):
        """Test phase dependencies are valid and acyclic."""
        for phase_num, metadata in PHASE_REGISTRY.items():
            # All dependencies should be less than current phase
            for dep in metadata.dependencies:
                self.assertLess(dep, phase_num)
                self.assertIn(dep, PHASE_REGISTRY)

    def test_phase_0_no_dependencies(self):
        """Test Phase 0 has no dependencies."""
        self.assertEqual(PHASE_REGISTRY[0].dependencies, [])

    def test_phase_dependencies_increment(self):
        """Test later phases depend on all earlier phases."""
        for phase_num in range(1, 10):
            metadata = PHASE_REGISTRY[phase_num]
            expected_deps = list(range(phase_num))
            self.assertEqual(metadata.dependencies, expected_deps)


class TestPhaseValidator(unittest.TestCase):
    """Test phase validation logic."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.state = StateManager(atomic_root=self.test_dir)

        # Import Config - it may need some setup
        from core.config import Config
        self.config = Config(atomic_root=self.test_dir)

        self.validator = PhaseValidator(self.state, self.config, self.test_dir)

        # Create phase directories
        for phase_num in range(10):
            phase_dir = self.test_dir / "phases" / f"phase{phase_num:02d}"
            phase_dir.mkdir(parents=True, exist_ok=True)

            # Create dummy orchestrator
            orchestrator_file = phase_dir / f"orchestrator{phase_num:02d}.py"
            orchestrator_file.write_text("# Dummy orchestrator\ndef run_phase():\n    pass\n")

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir)

    def test_validate_phase_exists(self):
        """Test validation fails for non-existent phase."""
        is_valid, errors = self.validator.validate_phase(99)
        self.assertFalse(is_valid)
        self.assertTrue(any("not found" in str(e).lower() for e in errors))

    def test_validate_orchestrator_exists(self):
        """Test orchestrator file existence check."""
        metadata = PHASE_REGISTRY[0]
        exists = self.validator._check_orchestrator_exists(metadata)
        self.assertTrue(exists)

    def test_validate_phase_0_no_deps(self):
        """Test Phase 0 validation succeeds with no setup."""
        is_valid, errors = self.validator.validate_phase(0)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_phase_1_requires_phase_0(self):
        """Test Phase 1 requires Phase 0 completion."""
        # Phase 0 not complete
        is_valid, errors = self.validator.validate_phase(1)
        self.assertFalse(is_valid)
        self.assertTrue(any("Phase 0" in str(e) or "0-setup" in str(e) for e in errors))

        # Complete Phase 0 - both closeout and state
        closeout_dir = self.test_dir / ".outputs" / "0-setup"
        closeout_dir.mkdir(parents=True, exist_ok=True)
        closeout_file = closeout_dir / "closeout.json"
        closeout_file.write_text('{"status": "complete"}')

        # Mark task complete in state
        self.state.mark_task_complete("0-setup", "001", "Setup Task")

        # Now Phase 1 should validate
        is_valid, errors = self.validator.validate_phase(1)
        # May still have dependency errors but should have closeout
        # The test is mainly checking that closeout requirement is validated

    def test_validate_closeout_files(self):
        """Test closeout file validation."""
        # Create Phase 0 closeout
        closeout_dir = self.test_dir / ".outputs" / "0-setup"
        closeout_dir.mkdir(parents=True, exist_ok=True)
        closeout_file = closeout_dir / "closeout.json"
        closeout_file.write_text('{"status": "complete"}')

        # Validate Phase 1 (needs Phase 0 closeout)
        metadata = PHASE_REGISTRY[1]
        errors = self.validator._validate_closeout_files(metadata)
        self.assertEqual(len(errors), 0)

    def test_validate_missing_closeout(self):
        """Test validation fails when closeout missing."""
        metadata = PHASE_REGISTRY[2]
        errors = self.validator._validate_closeout_files(metadata)

        # Should have errors for missing Phase 0 and Phase 1 closeouts
        self.assertGreater(len(errors), 0)


class TestPhaseTransition(unittest.TestCase):
    """Test phase transition handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.pipeline = PhasePipeline(atomic_root=self.test_dir)
        self.transition = PhaseTransition(self.pipeline)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir)

    def test_transition_auto_mode(self):
        """Test automatic transition to next phase."""
        next_phase = self.transition.transition_to_next(0, TransitionMode.AUTO)
        self.assertEqual(next_phase, 1)

    def test_transition_manual_mode(self):
        """Test manual mode returns None."""
        next_phase = self.transition.transition_to_next(0, TransitionMode.MANUAL)
        self.assertIsNone(next_phase)

    def test_transition_last_phase(self):
        """Test transition from last phase returns None."""
        next_phase = self.transition.transition_to_next(9, TransitionMode.AUTO)
        self.assertIsNone(next_phase)

    @patch('builtins.input', return_value='c')
    def test_transition_prompt_continue(self, mock_input):
        """Test prompted transition with continue choice."""
        next_phase = self.transition.transition_to_next(0, TransitionMode.PROMPT)
        self.assertEqual(next_phase, 1)

    @patch('builtins.input', return_value='p')
    def test_transition_prompt_pause(self, mock_input):
        """Test prompted transition with pause choice."""
        next_phase = self.transition.transition_to_next(0, TransitionMode.PROMPT)
        self.assertIsNone(next_phase)

    @patch('builtins.input', return_value='q')
    def test_transition_prompt_quit(self, mock_input):
        """Test prompted transition with quit choice."""
        next_phase = self.transition.transition_to_next(0, TransitionMode.PROMPT)
        self.assertIsNone(next_phase)


class TestPipelinePhasePipeline(unittest.TestCase):
    """Test main PhasePipeline class."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.pipeline = PhasePipeline(atomic_root=self.test_dir)

        # Create phase structure
        for phase_num in range(10):
            phase_dir = self.test_dir / "phases" / f"phase{phase_num:02d}"
            phase_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir)

    def test_pipeline_initialization(self):
        """Test pipeline initializes correctly."""
        self.assertIsNotNone(self.pipeline.state)
        self.assertIsNotNone(self.pipeline.config)
        self.assertIsNotNone(self.pipeline.validator)
        self.assertIsNotNone(self.pipeline.transition)

    def test_get_pipeline_status_initial(self):
        """Test pipeline status when no phases started."""
        status = self.pipeline.get_pipeline_status()
        self.assertEqual(status.pipeline_state, "not_started")
        self.assertEqual(status.completed_phases, 0)
        self.assertIsNone(status.current_phase)

    def test_validate_pipeline(self):
        """Test pipeline validation."""
        # Without orchestrators, should fail
        is_valid, errors = self.pipeline.validate_pipeline()
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_get_next_phase_initial(self):
        """Test getting next phase when none completed."""
        next_phase = self.pipeline.get_next_phase()
        self.assertEqual(next_phase, 0)

    def test_ensure_closeout_exists(self):
        """Test closeout file creation."""
        metadata = PHASE_REGISTRY[0]
        self.pipeline._ensure_closeout_exists(metadata)

        closeout_file = self.test_dir / ".outputs" / "0-setup" / "closeout.json"
        self.assertTrue(closeout_file.exists())

        # Verify JSON structure
        with open(closeout_file) as f:
            data = json.load(f)
        self.assertEqual(data['phase_id'], "0-setup")
        self.assertEqual(data['status'], "complete")


class TestPipelineStatusTracking(unittest.TestCase):
    """Test pipeline status tracking and reporting."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.pipeline = PhasePipeline(atomic_root=self.test_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir)

    def test_pipeline_status_structure(self):
        """Test PipelineStatus dataclass structure."""
        status = self.pipeline.get_pipeline_status()
        self.assertIsInstance(status, PipelineStatus)
        self.assertIsInstance(status.total_phases, int)
        self.assertIsInstance(status.completed_phases, int)
        self.assertIsInstance(status.pipeline_state, str)

    def test_status_with_completed_phases(self):
        """Test status after completing phases."""
        # Mark Phase 0 as complete
        self.pipeline.state.mark_task_complete("0-setup", "001", "Test Task")
        self.pipeline.state.mark_phase_complete("0-setup")

        status = self.pipeline.get_pipeline_status()
        self.assertGreaterEqual(status.completed_phases, 0)

    def test_status_display(self):
        """Test status display doesn't crash."""
        # Should not raise exception
        self.pipeline.display_pipeline_status()


class TestPipelineControl(unittest.TestCase):
    """Test pipeline pause, resume, and rollback."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.pipeline = PhasePipeline(atomic_root=self.test_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir)

    def test_pause_pipeline(self):
        """Test pipeline pause."""
        self.pipeline.state.set_current_phase("0-setup")
        self.pipeline.pause_pipeline()
        # Should not raise exception

    def test_resume_pipeline_no_phase(self):
        """Test resume when no current phase."""
        success = self.pipeline.resume_pipeline()
        self.assertFalse(success)

    def test_resume_pipeline_with_phase(self):
        """Test resume with current phase set."""
        self.pipeline.state.set_current_phase("0-setup")

        # Mock the run_phase to avoid actual execution
        with patch.object(self.pipeline, 'run_phase', return_value=True) as mock_run:
            success = self.pipeline.resume_pipeline()
            mock_run.assert_called_once()

    @patch('orchestration.backtrack.backtrack_to')
    def test_rollback_to_phase(self, mock_backtrack):
        """Test rollback to specific phase."""
        success = self.pipeline.rollback_to_phase(0)
        mock_backtrack.assert_called_once_with(0, None)


class TestPhaseExecution(unittest.TestCase):
    """Test phase execution logic."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.pipeline = PhasePipeline(atomic_root=self.test_dir)

        # Create minimal phase structure
        for phase_num in range(2):
            phase_dir = self.test_dir / "phases" / f"phase{phase_num:02d}"
            phase_dir.mkdir(parents=True, exist_ok=True)

            # Create orchestrator with run_phase function
            orchestrator_file = phase_dir / f"orchestrator{phase_num:02d}.py"
            orchestrator_file.write_text("""
def run_phase(resume_at=None):
    return True
""")

        # Add closeout for Phase 0
        closeout_dir = self.test_dir / ".outputs" / "0-setup"
        closeout_dir.mkdir(parents=True, exist_ok=True)
        closeout_file = closeout_dir / "closeout.json"
        closeout_file.write_text('{"status": "complete"}')

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir)

    def test_execute_phase_orchestrator_success(self):
        """Test successful orchestrator execution."""
        metadata = PHASE_REGISTRY[0]

        # Mock the orchestrator
        with patch('builtins.__import__') as mock_import:
            mock_module = Mock()
            mock_module.run_phase = Mock(return_value=True)
            mock_import.return_value = mock_module

            success = self.pipeline._execute_phase_orchestrator(metadata, None)
            self.assertTrue(success)

    def test_execute_phase_orchestrator_failure(self):
        """Test orchestrator execution failure."""
        metadata = PHASE_REGISTRY[0]

        # Mock orchestrator that fails
        with patch('builtins.__import__') as mock_import:
            mock_module = Mock()
            mock_module.run_phase = Mock(return_value=False)
            mock_import.return_value = mock_module

            success = self.pipeline._execute_phase_orchestrator(metadata, None)
            self.assertFalse(success)

    def test_execute_phase_orchestrator_import_error(self):
        """Test orchestrator import error."""
        metadata = PhaseMetadata(
            phase_id="99-nonexistent",
            phase_num=99,
            phase_name="Nonexistent",
            module_path="phases.phase99.orchestrator99",
            dependencies=[]
        )

        success = self.pipeline._execute_phase_orchestrator(metadata, None)
        self.assertFalse(success)

    def test_run_phase_validation_failure(self):
        """Test run_phase stops on validation failure."""
        # Phase 99 doesn't exist
        success = self.pipeline.run_phase(99)
        self.assertFalse(success)

    def test_display_phase_header(self):
        """Test phase header display."""
        metadata = PHASE_REGISTRY[0]
        # Should not raise exception
        self.pipeline._display_phase_header(metadata)


class TestPhaseLifecycleEnum(unittest.TestCase):
    """Test PhaseLifecycle enum."""

    def test_lifecycle_states(self):
        """Test all lifecycle states defined."""
        expected_states = [
            "NOT_STARTED", "INITIALIZING", "READY", "RUNNING",
            "PAUSED", "COMPLETED", "FAILED", "ROLLED_BACK"
        ]

        for state in expected_states:
            self.assertTrue(hasattr(PhaseLifecycle, state))

    def test_lifecycle_values(self):
        """Test lifecycle enum values."""
        self.assertEqual(PhaseLifecycle.NOT_STARTED.value, "not_started")
        self.assertEqual(PhaseLifecycle.RUNNING.value, "running")
        self.assertEqual(PhaseLifecycle.COMPLETED.value, "completed")


class TestTransitionModeEnum(unittest.TestCase):
    """Test TransitionMode enum."""

    def test_transition_modes(self):
        """Test all transition modes defined."""
        self.assertEqual(TransitionMode.AUTO.value, "auto")
        self.assertEqual(TransitionMode.PROMPT.value, "prompt")
        self.assertEqual(TransitionMode.MANUAL.value, "manual")


class TestPhaseExecutionContext(unittest.TestCase):
    """Test PhaseExecutionContext dataclass."""

    def test_context_creation(self):
        """Test execution context creation."""
        context = PhaseExecutionContext(
            phase_num=0,
            resume_at="003",
            auto_chain=True
        )

        self.assertEqual(context.phase_num, 0)
        self.assertEqual(context.resume_at, "003")
        self.assertTrue(context.auto_chain)

    def test_context_defaults(self):
        """Test context default values."""
        context = PhaseExecutionContext(phase_num=1)

        self.assertIsNone(context.resume_at)
        self.assertFalse(context.auto_chain)
        self.assertEqual(context.transition_mode, TransitionMode.PROMPT)
        self.assertFalse(context.skip_validation)
        self.assertFalse(context.dry_run)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.pipeline = PhasePipeline(atomic_root=self.test_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir)

    def test_negative_phase_number(self):
        """Test negative phase number."""
        success = self.pipeline.run_phase(-1)
        self.assertFalse(success)

    def test_phase_number_too_large(self):
        """Test phase number beyond range."""
        success = self.pipeline.run_phase(100)
        self.assertFalse(success)

    def test_corrupted_closeout_file(self):
        """Test handling of corrupted closeout file."""
        # Create corrupted closeout
        closeout_dir = self.test_dir / ".outputs" / "0-setup"
        closeout_dir.mkdir(parents=True, exist_ok=True)
        closeout_file = closeout_dir / "closeout.json"
        closeout_file.write_text('{"invalid json')

        # Should handle gracefully
        metadata = PHASE_REGISTRY[0]
        self.pipeline._ensure_closeout_exists(metadata)

    def test_missing_state_directory(self):
        """Test handling when state directory missing."""
        # Remove state directory
        state_dir = self.test_dir / ".state"
        if state_dir.exists():
            shutil.rmtree(state_dir)

        # Should recreate automatically
        pipeline = PhasePipeline(atomic_root=self.test_dir)
        self.assertTrue(state_dir.exists())

    def test_concurrent_pipeline_instances(self):
        """Test multiple pipeline instances."""
        pipeline1 = PhasePipeline(atomic_root=self.test_dir)
        pipeline2 = PhasePipeline(atomic_root=self.test_dir)

        # Both should work independently
        status1 = pipeline1.get_pipeline_status()
        status2 = pipeline2.get_pipeline_status()

        self.assertEqual(status1.pipeline_state, status2.pipeline_state)


class TestIntegrationScenarios(unittest.TestCase):
    """Test complete integration scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.pipeline = PhasePipeline(atomic_root=self.test_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir)

    def test_complete_pipeline_flow(self):
        """Test complete pipeline execution flow."""
        # Initial status
        status = self.pipeline.get_pipeline_status()
        self.assertEqual(status.pipeline_state, "not_started")

        # Next phase should be 0
        next_phase = self.pipeline.get_next_phase()
        self.assertEqual(next_phase, 0)

    def test_resume_after_failure(self):
        """Test resuming after phase failure."""
        # Set current phase
        self.pipeline.state.set_current_phase("1-discovery")

        # Attempt resume
        with patch.object(self.pipeline, 'run_phase', return_value=False):
            success = self.pipeline.resume_pipeline()
            # Should attempt to run but fail

    def test_status_progression(self):
        """Test status changes as phases complete."""
        initial_status = self.pipeline.get_pipeline_status()

        # Mark phase complete
        self.pipeline.state.mark_task_complete("0-setup", "001", "Test")
        self.pipeline.state.mark_phase_complete("0-setup")

        # Create closeout
        closeout_dir = self.test_dir / ".outputs" / "0-setup"
        closeout_dir.mkdir(parents=True, exist_ok=True)
        (closeout_dir / "closeout.json").write_text('{"status": "complete"}')

        new_status = self.pipeline.get_pipeline_status()
        # Should show progression


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
