"""
Integration tests for phase orchestrators.

Tests full phase execution (orchestrator + all tasks) for all 10 phases.
Each phase class contains 10+ tests covering:
- Success path (all tasks pass)
- Failure path (task fails, phase stops)
- Resume functionality
- Closeout generation
- State management
- Pre-task validation
- Error handling
- Task skipping (already complete)
"""

import pytest
import json
import sys
import os
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.state import StateManager


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up test environment for each test."""
    # Set environment variables for testing
    monkeypatch.setenv('ATOMIC_ROOT', str(Path.cwd()))
    monkeypatch.setenv('ATOMIC_TOOL_DEVELOPMENT', 'true')  # Disable forcing function

    # Clean state before test
    state_dir = Path('.state')
    output_dir = Path('.outputs')

    if state_dir.exists():
        shutil.rmtree(state_dir, ignore_errors=True)
    if output_dir.exists():
        shutil.rmtree(output_dir, ignore_errors=True)

    # Create fresh directories
    state_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)

    yield

    # Cleanup after test
    if output_dir.exists():
        shutil.rmtree(output_dir, ignore_errors=True)
    if state_dir.exists():
        shutil.rmtree(state_dir, ignore_errors=True)


# ============================================================================
# PHASE 0: SETUP
# ============================================================================

class TestPhase00Orchestrator:
    """Integration tests for Phase 0: Setup orchestrator."""

    @pytest.fixture
    def mock_tasks(self):
        """Mock all Phase 0 task modules."""
        with patch('phases.phase_00_setup.tasks.task_001') as mock_001, \
             patch('phases.phase_00_setup.tasks.task_002') as mock_002, \
             patch('phases.phase_00_setup.tasks.task_003') as mock_003, \
             patch('phases.phase_00_setup.tasks.task_004') as mock_004, \
             patch('phases.phase_00_setup.tasks.task_005') as mock_005, \
             patch('phases.phase_00_setup.tasks.task_006') as mock_006, \
             patch('phases.phase_00_setup.tasks.task_007') as mock_007, \
             patch('phases.phase_00_setup.tasks.task_008') as mock_008, \
             patch('phases.phase_00_setup.tasks.task_009') as mock_009:

            # All tasks succeed by default
            for mock in [mock_001, mock_002, mock_003, mock_004, mock_005,
                        mock_006, mock_007, mock_008, mock_009]:
                mock.return_value = True

            yield {
                '001': mock_001,
                '002': mock_002,
                '003': mock_003,
                '004': mock_004,
                '005': mock_005,
                '006': mock_006,
                '007': mock_007,
                '008': mock_008,
                '009': mock_009,
            }

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_all_tasks_success(self, mock_validate, mock_tasks, temp_state_dir):
        """Test complete phase execution with all tasks succeeding."""
        mock_validate.return_value = True

        from phases.phase00.orchestrator00 import run_phase
        result = run_phase()

        assert result is True

        # Verify all 9 tasks were called
        for task_id, mock in mock_tasks.items():
            assert mock.called, f"Task {task_id} was not called"

        # Verify closeout was created
        closeout_path = Path(".outputs/0-setup/closeout.json")
        assert closeout_path.exists()

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_task_failure(self, mock_validate, mock_tasks, temp_state_dir):
        """Test phase stops when task fails."""
        mock_validate.return_value = True

        # Task 005 fails
        mock_tasks['005'].return_value = False

        from phases.phase00.orchestrator00 import run_phase
        result = run_phase()

        assert result is False

        # Tasks 001-005 should be called, 006-009 should not
        for task_id in ['001', '002', '003', '004', '005']:
            assert mock_tasks[task_id].called
        for task_id in ['006', '007', '008', '009']:
            assert not mock_tasks[task_id].called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_resume_at(self, mock_validate, mock_tasks, temp_state_dir):
        """Test resuming from specific task."""
        mock_validate.return_value = True

        # Mark tasks 001-003 as complete
        state = StateManager()
        state.mark_task_complete("0-setup", "001", "Mode selection")
        state.mark_task_complete("0-setup", "002", "Config collection")
        state.mark_task_complete("0-setup", "003", "Config review")

        from phases.phase00.orchestrator00 import run_phase
        result = run_phase(resume_at="004")

        assert result is True

        # Tasks 001-003 should be skipped
        for task_id in ['001', '002', '003']:
            assert not mock_tasks[task_id].called

        # Tasks 004-009 should be called
        for task_id in ['004', '005', '006', '007', '008', '009']:
            assert mock_tasks[task_id].called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_creates_closeout(self, mock_validate, mock_tasks, temp_state_dir):
        """Test phase creates closeout.json with correct structure."""
        mock_validate.return_value = True

        from phases.phase00.orchestrator00 import run_phase
        result = run_phase()

        assert result is True

        # Read closeout
        closeout_path = Path(".outputs/0-setup/closeout.json")
        assert closeout_path.exists()

        with open(closeout_path) as f:
            closeout = json.load(f)

        assert closeout['phase'] == '0-setup'
        assert closeout['phase_num'] == 0
        assert 'completed_at' in closeout
        assert len(closeout['tasks_completed']) == 9
        assert '001' in closeout['tasks_completed']
        assert '009' in closeout['tasks_completed']

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_state_tracking(self, mock_validate, mock_tasks, temp_state_dir):
        """Test state is tracked correctly."""
        mock_validate.return_value = True

        from phases.phase00.orchestrator00 import run_phase
        result = run_phase()

        assert result is True

        # Verify all tasks marked complete
        state = StateManager()
        for task_id in ['001', '002', '003', '004', '005', '006', '007', '008', '009']:
            assert state.is_task_complete("0-setup", task_id)

    def test_run_phase_pre_task_validation_failure(self, mock_tasks, temp_state_dir):
        """Test phase stops when pre-task validation fails."""
        with patch('orchestration.pre_task_validation.validate_directory_pristine') as mock_validate:
            # First 3 tasks pass validation, 4th fails
            mock_validate.side_effect = [True, True, True, False]

            from phases.phase00.orchestrator00 import run_phase
            result = run_phase()

            assert result is False

            # Only first 3 tasks should be called
            for task_id in ['001', '002', '003']:
                assert mock_tasks[task_id].called
            for task_id in ['004', '005', '006', '007', '008', '009']:
                assert not mock_tasks[task_id].called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_exception_handling(self, mock_validate, mock_tasks, temp_state_dir):
        """Test phase handles exceptions gracefully."""
        mock_validate.return_value = True

        # Task 005 raises exception
        mock_tasks['005'].side_effect = Exception("Simulated error")

        from phases.phase00.orchestrator00 import run_phase
        result = run_phase()

        assert result is False

        # Verify error was logged to state
        state = StateManager()
        state_data = state.load_state()
        task_state = state_data.get('phases', {}).get('0-setup', {}).get('tasks', {}).get('005', {})
        assert task_state.get('status') == 'failed'
        assert 'error' in task_state

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_skip_completed_tasks(self, mock_validate, mock_tasks, temp_state_dir):
        """Test already completed tasks are skipped."""
        mock_validate.return_value = True

        # Mark some tasks as complete
        state = StateManager()
        state.mark_task_complete("0-setup", "001", "Mode selection")
        state.mark_task_complete("0-setup", "003", "Config review")
        state.mark_task_complete("0-setup", "007", "Environment setup")

        from phases.phase00.orchestrator00 import run_phase
        result = run_phase()

        assert result is True

        # Completed tasks should not be called
        assert not mock_tasks['001'].called
        assert not mock_tasks['003'].called
        assert not mock_tasks['007'].called

        # Other tasks should be called
        assert mock_tasks['002'].called
        assert mock_tasks['004'].called
        assert mock_tasks['008'].called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_output_directory_creation(self, mock_validate, mock_tasks, temp_state_dir):
        """Test phase creates output directory."""
        mock_validate.return_value = True

        from phases.phase00.orchestrator00 import run_phase
        result = run_phase()

        assert result is True
        assert Path(".outputs/0-setup").exists()

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_partial_completion(self, mock_validate, mock_tasks, temp_state_dir):
        """Test partial completion and resume."""
        mock_validate.return_value = True

        # First run: fail at task 005
        mock_tasks['005'].return_value = False

        from phases.phase00.orchestrator00 import run_phase
        result = run_phase()
        assert result is False

        # Verify tasks 001-004 are complete
        state = StateManager()
        for task_id in ['001', '002', '003', '004']:
            assert state.is_task_complete("0-setup", task_id)
        assert not state.is_task_complete("0-setup", "005")

        # Second run: fix task 005
        mock_tasks['005'].return_value = True
        result = run_phase(resume_at="005")
        assert result is True

        # Now all tasks should be complete
        for task_id in ['001', '002', '003', '004', '005', '006', '007', '008', '009']:
            assert state.is_task_complete("0-setup", task_id)


# ============================================================================
# PHASE 1: DISCOVERY
# ============================================================================

class TestPhase01Orchestrator:
    """Integration tests for Phase 1: Discovery orchestrator."""

    @pytest.fixture
    def mock_tasks(self):
        """Mock all Phase 1 task modules."""
        with patch('phases.phase_01_discovery.tasks.task_101') as mock_101, \
             patch('phases.phase_01_discovery.tasks.task_102') as mock_102, \
             patch('phases.phase_01_discovery.tasks.task_103') as mock_103, \
             patch('phases.phase_01_discovery.tasks.task_104') as mock_104, \
             patch('phases.phase_01_discovery.tasks.task_105') as mock_105, \
             patch('phases.phase_01_discovery.tasks.task_106') as mock_106, \
             patch('phases.phase_01_discovery.tasks.task_107') as mock_107, \
             patch('phases.phase_01_discovery.tasks.task_108') as mock_108, \
             patch('phases.phase_01_discovery.tasks.task_109') as mock_109, \
             patch('phases.phase_01_discovery.tasks.task_110') as mock_110:

            for mock in [mock_101, mock_102, mock_103, mock_104, mock_105,
                        mock_106, mock_107, mock_108, mock_109, mock_110]:
                mock.return_value = True

            yield {
                '101': mock_101,
                '102': mock_102,
                '103': mock_103,
                '104': mock_104,
                '105': mock_105,
                '106': mock_106,
                '107': mock_107,
                '108': mock_108,
                '109': mock_109,
                '110': mock_110,
            }

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_all_tasks_success(self, mock_validate, mock_tasks, temp_state_dir):
        """Test complete phase execution with all tasks succeeding."""
        mock_validate.return_value = True

        from phases.phase01.orchestrator01 import run_phase
        result = run_phase()

        assert result is True

        # Verify all 10 tasks were called
        for task_id, mock in mock_tasks.items():
            assert mock.called, f"Task {task_id} was not called"

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_task_failure(self, mock_validate, mock_tasks, temp_state_dir):
        """Test phase stops when task fails."""
        mock_validate.return_value = True

        # Task 105 fails
        mock_tasks['105'].return_value = False

        from phases.phase01.orchestrator01 import run_phase
        result = run_phase()

        assert result is False

        # Tasks 101-105 should be called, 106-110 should not
        for task_id in ['101', '102', '103', '104', '105']:
            assert mock_tasks[task_id].called
        for task_id in ['106', '107', '108', '109', '110']:
            assert not mock_tasks[task_id].called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_resume_at(self, mock_validate, mock_tasks, temp_state_dir):
        """Test resuming from specific task."""
        mock_validate.return_value = True

        # Mark tasks 101-103 as complete
        state = StateManager()
        state.mark_task_complete("1-discovery", "101", "Entry validation")
        state.mark_task_complete("1-discovery", "102", "Corpus collection")
        state.mark_task_complete("1-discovery", "103", "Import requirements")

        from phases.phase01.orchestrator01 import run_phase
        result = run_phase(resume_at="104")

        assert result is True

        # Tasks 101-103 should be skipped
        for task_id in ['101', '102', '103']:
            assert not mock_tasks[task_id].called

        # Tasks 104-110 should be called
        for task_id in ['104', '105', '106', '107', '108', '109', '110']:
            assert mock_tasks[task_id].called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_creates_closeout(self, mock_validate, mock_tasks, temp_state_dir):
        """Test phase creates closeout.json."""
        mock_validate.return_value = True

        from phases.phase01.orchestrator01 import run_phase
        result = run_phase()

        assert result is True

        closeout_path = Path(".outputs/1-discovery/closeout.json")
        assert closeout_path.exists()

        with open(closeout_path) as f:
            closeout = json.load(f)

        assert closeout['phase'] == '1-discovery'
        assert closeout['phase_num'] == 1
        assert len(closeout['tasks_completed']) == 10

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_state_tracking(self, mock_validate, mock_tasks, temp_state_dir):
        """Test state is tracked correctly."""
        mock_validate.return_value = True

        from phases.phase01.orchestrator01 import run_phase
        result = run_phase()

        assert result is True

        state = StateManager()
        for task_id in ['101', '102', '103', '104', '105', '106', '107', '108', '109', '110']:
            assert state.is_task_complete("1-discovery", task_id)

    def test_run_phase_pre_task_validation_failure(self, mock_tasks, temp_state_dir):
        """Test phase stops when pre-task validation fails."""
        with patch('orchestration.pre_task_validation.validate_directory_pristine') as mock_validate:
            mock_validate.side_effect = [True, True, False]

            from phases.phase01.orchestrator01 import run_phase
            result = run_phase()

            assert result is False

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_exception_handling(self, mock_validate, mock_tasks, temp_state_dir):
        """Test phase handles exceptions."""
        mock_validate.return_value = True

        mock_tasks['106'].side_effect = Exception("Discovery error")

        from phases.phase01.orchestrator01 import run_phase
        result = run_phase()

        assert result is False

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_skip_completed_tasks(self, mock_validate, mock_tasks, temp_state_dir):
        """Test completed tasks are skipped."""
        mock_validate.return_value = True

        state = StateManager()
        state.mark_task_complete("1-discovery", "101", "Entry validation")
        state.mark_task_complete("1-discovery", "105", "Opening dialogue")

        from phases.phase01.orchestrator01 import run_phase
        result = run_phase()

        assert result is True
        assert not mock_tasks['101'].called
        assert not mock_tasks['105'].called
        assert mock_tasks['102'].called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_output_directory_creation(self, mock_validate, mock_tasks, temp_state_dir):
        """Test phase creates output directory."""
        mock_validate.return_value = True

        from phases.phase01.orchestrator01 import run_phase
        result = run_phase()

        assert result is True
        assert Path(".outputs/1-discovery").exists()

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_partial_completion(self, mock_validate, mock_tasks, temp_state_dir):
        """Test partial completion and resume."""
        mock_validate.return_value = True

        # First run: fail at task 107
        mock_tasks['107'].return_value = False

        from phases.phase01.orchestrator01 import run_phase
        result = run_phase()
        assert result is False

        # Second run: continue from 107
        mock_tasks['107'].return_value = True
        result = run_phase(resume_at="107")
        assert result is True


# ============================================================================
# PHASE 2: PRD
# ============================================================================

class TestPhase02Orchestrator:
    """Integration tests for Phase 2: PRD orchestrator."""

    @pytest.fixture
    def mock_tasks(self):
        """Mock all Phase 2 task modules."""
        with patch('phases.phase_02_prd.tasks.task_201_entry_validation') as mock_201, \
             patch('phases.phase_02_prd.tasks.task_202_prd_setup') as mock_202, \
             patch('phases.phase_02_prd.tasks.task_203_prd_interview') as mock_203, \
             patch('phases.phase_02_prd.tasks.task_204_agent_selection') as mock_204, \
             patch('phases.phase_02_prd.tasks.task_205_prd_authoring') as mock_205, \
             patch('phases.phase_02_prd.tasks.task_206_prd_validation') as mock_206, \
             patch('phases.phase_02_prd.tasks.task_206b_prd_revision') as mock_206b, \
             patch('phases.phase_02_prd.tasks.task_207_prd_approval') as mock_207, \
             patch('phases.phase_02_prd.tasks.task_208_phase_audit') as mock_208, \
             patch('phases.phase_02_prd.tasks.task_209_closeout') as mock_209:

            for mock in [mock_201, mock_202, mock_203, mock_204, mock_205,
                        mock_206, mock_206b, mock_207, mock_208, mock_209]:
                mock.execute.return_value = True

            yield {
                '201': mock_201,
                '202': mock_202,
                '203': mock_203,
                '204': mock_204,
                '205': mock_205,
                '206': mock_206,
                '206b': mock_206b,
                '207': mock_207,
                '208': mock_208,
                '209': mock_209,
            }

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_all_tasks_success(self, mock_validate, mock_tasks, temp_state_dir):
        """Test complete phase execution with all tasks succeeding."""
        mock_validate.return_value = True

        from phases.phase02.orchestrator02 import run_phase
        result = run_phase()

        assert result is True

        # Task 206b should be skipped (since 206 passed)
        for task_id in ['201', '202', '203', '204', '205', '206', '207', '208', '209']:
            assert mock_tasks[task_id].execute.called
        assert not mock_tasks['206b'].execute.called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_validation_failure_triggers_revision(self, mock_validate, mock_tasks, temp_state_dir):
        """Test that task 206 failure triggers 206b (revision)."""
        mock_validate.return_value = True

        # Task 206 fails (validation)
        mock_tasks['206'].execute.return_value = False

        from phases.phase02.orchestrator02 import run_phase
        result = run_phase()

        assert result is True  # Phase continues despite 206 failure

        # Task 206b should be called
        assert mock_tasks['206b'].execute.called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_task_failure(self, mock_validate, mock_tasks, temp_state_dir):
        """Test phase stops when non-206 task fails."""
        mock_validate.return_value = True

        # Task 204 fails
        mock_tasks['204'].execute.return_value = False

        from phases.phase02.orchestrator02 import run_phase
        result = run_phase()

        assert result is False

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_resume_at(self, mock_validate, mock_tasks, temp_state_dir):
        """Test resuming from specific task."""
        mock_validate.return_value = True

        state = StateManager()
        state.mark_task_complete("2-prd", "201", "Entry validation")
        state.mark_task_complete("2-prd", "202", "PRD setup")

        from phases.phase02.orchestrator02 import run_phase
        result = run_phase(resume_at="203")

        assert result is True

        assert not mock_tasks['201'].execute.called
        assert not mock_tasks['202'].execute.called
        assert mock_tasks['203'].execute.called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_creates_closeout(self, mock_validate, mock_tasks, temp_state_dir):
        """Test phase creates closeout.json."""
        mock_validate.return_value = True

        from phases.phase02.orchestrator02 import run_phase
        result = run_phase()

        assert result is True

        closeout_path = Path(".outputs/2-prd/closeout.json")
        assert closeout_path.exists()

        with open(closeout_path) as f:
            closeout = json.load(f)

        assert closeout['phase'] == '2-prd'
        assert closeout['phase_num'] == 2

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_state_tracking(self, mock_validate, mock_tasks, temp_state_dir):
        """Test state is tracked correctly."""
        mock_validate.return_value = True

        from phases.phase02.orchestrator02 import run_phase
        result = run_phase()

        assert result is True

        state = StateManager()
        for task_id in ['201', '202', '203', '204', '205', '206', '207', '208', '209']:
            assert state.is_task_complete("2-prd", task_id)

    def test_run_phase_pre_task_validation_failure(self, mock_tasks, temp_state_dir):
        """Test phase stops when pre-task validation fails."""
        with patch('orchestration.pre_task_validation.validate_directory_pristine') as mock_validate:
            mock_validate.side_effect = [True, False]

            from phases.phase02.orchestrator02 import run_phase
            result = run_phase()

            assert result is False

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_exception_handling(self, mock_validate, mock_tasks, temp_state_dir):
        """Test phase handles exceptions."""
        mock_validate.return_value = True

        mock_tasks['205'].execute.side_effect = Exception("PRD authoring error")

        from phases.phase02.orchestrator02 import run_phase
        result = run_phase()

        assert result is False

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_skip_completed_tasks(self, mock_validate, mock_tasks, temp_state_dir):
        """Test completed tasks are skipped."""
        mock_validate.return_value = True

        state = StateManager()
        state.mark_task_complete("2-prd", "201", "Entry validation")
        state.mark_task_complete("2-prd", "205", "PRD authoring")

        from phases.phase02.orchestrator02 import run_phase
        result = run_phase()

        assert result is True
        assert not mock_tasks['201'].execute.called
        assert not mock_tasks['205'].execute.called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_206b_conditional_logic(self, mock_validate, mock_tasks, temp_state_dir):
        """Test 206b is only run when 206 fails."""
        mock_validate.return_value = True

        # First scenario: 206 passes
        from phases.phase02.orchestrator02 import run_phase
        result = run_phase()

        assert result is True
        assert mock_tasks['206'].execute.called
        assert not mock_tasks['206b'].execute.called

        # Reset
        for mock in mock_tasks.values():
            mock.execute.reset_mock()

        # Clean state
        import shutil
        shutil.rmtree(".state", ignore_errors=True)

        # Second scenario: 206 fails
        mock_tasks['206'].execute.return_value = False
        result = run_phase()

        assert result is True
        assert mock_tasks['206'].execute.called
        assert mock_tasks['206b'].execute.called


# ============================================================================
# PHASE 3: TASKING
# ============================================================================

class TestPhase03Orchestrator:
    """Integration tests for Phase 3: Tasking orchestrator."""

    @pytest.fixture
    def mock_tasks(self):
        """Mock all Phase 3 task modules."""
        with patch('phases.phase_03_tasking.tasks.task_301') as mock_301, \
             patch('phases.phase_03_tasking.tasks.task_302') as mock_302, \
             patch('phases.phase_03_tasking.tasks.task_303') as mock_303, \
             patch('phases.phase_03_tasking.tasks.task_304') as mock_304, \
             patch('phases.phase_03_tasking.tasks.task_305') as mock_305, \
             patch('phases.phase_03_tasking.tasks.task_306') as mock_306:

            for mock in [mock_301, mock_302, mock_303, mock_304, mock_305, mock_306]:
                mock.return_value = True

            yield {
                '301': mock_301,
                '302': mock_302,
                '303': mock_303,
                '304': mock_304,
                '305': mock_305,
                '306': mock_306,
            }

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_all_tasks_success(self, mock_validate, mock_tasks, temp_state_dir):
        """Test complete phase execution."""
        mock_validate.return_value = True

        from phases.phase03.orchestrator03 import run_phase
        result = run_phase()

        assert result is True
        for mock in mock_tasks.values():
            assert mock.called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_task_failure(self, mock_validate, mock_tasks, temp_state_dir):
        """Test phase stops on failure."""
        mock_validate.return_value = True

        mock_tasks['303'].return_value = False

        from phases.phase03.orchestrator03 import run_phase
        result = run_phase()

        assert result is False

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_resume_at(self, mock_validate, mock_tasks, temp_state_dir):
        """Test resuming from specific task."""
        mock_validate.return_value = True

        state = StateManager()
        state.mark_task_complete("3-tasking", "301", "Entry initialization")

        from phases.phase03.orchestrator03 import run_phase
        result = run_phase(resume_at="302")

        assert result is True
        assert not mock_tasks['301'].called
        assert mock_tasks['302'].called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_creates_closeout(self, mock_validate, mock_tasks, temp_state_dir):
        """Test closeout creation."""
        mock_validate.return_value = True

        from phases.phase03.orchestrator03 import run_phase
        result = run_phase()

        assert result is True
        assert Path(".outputs/3-tasking/closeout.json").exists()

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_state_tracking(self, mock_validate, mock_tasks, temp_state_dir):
        """Test state tracking."""
        mock_validate.return_value = True

        from phases.phase03.orchestrator03 import run_phase
        result = run_phase()

        state = StateManager()
        for task_id in ['301', '302', '303', '304', '305', '306']:
            assert state.is_task_complete("3-tasking", task_id)

    def test_run_phase_pre_task_validation_failure(self, mock_tasks, temp_state_dir):
        """Test validation failure."""
        with patch('orchestration.pre_task_validation.validate_directory_pristine') as mock_validate:
            mock_validate.return_value = False

            from phases.phase03.orchestrator03 import run_phase
            result = run_phase()

            assert result is False

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_exception_handling(self, mock_validate, mock_tasks, temp_state_dir):
        """Test exception handling."""
        mock_validate.return_value = True

        mock_tasks['304'].side_effect = Exception("Dependency error")

        from phases.phase03.orchestrator03 import run_phase
        result = run_phase()

        assert result is False

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_skip_completed(self, mock_validate, mock_tasks, temp_state_dir):
        """Test skip completed tasks."""
        mock_validate.return_value = True

        state = StateManager()
        state.mark_task_complete("3-tasking", "301", "Entry")
        state.mark_task_complete("3-tasking", "303", "Decomposition")

        from phases.phase03.orchestrator03 import run_phase
        result = run_phase()

        assert not mock_tasks['301'].called
        assert not mock_tasks['303'].called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_output_directory(self, mock_validate, mock_tasks, temp_state_dir):
        """Test output directory creation."""
        mock_validate.return_value = True

        from phases.phase03.orchestrator03 import run_phase
        result = run_phase()

        assert Path(".outputs/3-tasking").exists()

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_partial_completion(self, mock_validate, mock_tasks, temp_state_dir):
        """Test partial completion."""
        mock_validate.return_value = True

        mock_tasks['304'].return_value = False

        from phases.phase03.orchestrator03 import run_phase
        result = run_phase()
        assert result is False

        mock_tasks['304'].return_value = True
        result = run_phase(resume_at="304")
        assert result is True


# ============================================================================
# PHASE 4: SPECIFICATION
# ============================================================================

class TestPhase04Orchestrator:
    """Integration tests for Phase 4: Specification orchestrator."""

    @pytest.fixture
    def mock_tasks(self):
        """Mock all Phase 4 task modules."""
        with patch('phases.phase_04_specification.tasks.task_401') as mock_401, \
             patch('phases.phase_04_specification.tasks.task_402') as mock_402, \
             patch('phases.phase_04_specification.tasks.task_403') as mock_403, \
             patch('phases.phase_04_specification.tasks.task_404') as mock_404, \
             patch('phases.phase_04_specification.tasks.task_405') as mock_405, \
             patch('phases.phase_04_specification.tasks.task_406') as mock_406:

            for mock in [mock_401, mock_402, mock_403, mock_404, mock_405, mock_406]:
                mock.return_value = True

            yield {
                '401': mock_401,
                '402': mock_402,
                '403': mock_403,
                '404': mock_404,
                '405': mock_405,
                '406': mock_406,
            }

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_all_tasks_success(self, mock_validate, mock_tasks, temp_state_dir):
        """Test complete phase execution."""
        mock_validate.return_value = True

        from phases.phase04.orchestrator04 import run_phase
        result = run_phase()

        assert result is True
        for mock in mock_tasks.values():
            assert mock.called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_task_failure(self, mock_validate, mock_tasks, temp_state_dir):
        """Test phase stops on failure."""
        mock_validate.return_value = True

        mock_tasks['403'].return_value = False

        from phases.phase04.orchestrator04 import run_phase
        result = run_phase()

        assert result is False

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_resume_at(self, mock_validate, mock_tasks, temp_state_dir):
        """Test resuming."""
        mock_validate.return_value = True

        state = StateManager()
        state.mark_task_complete("4-specification", "401", "Entry")

        from phases.phase04.orchestrator04 import run_phase
        result = run_phase(resume_at="402")

        assert result is True
        assert not mock_tasks['401'].called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_creates_closeout(self, mock_validate, mock_tasks, temp_state_dir):
        """Test closeout creation."""
        mock_validate.return_value = True

        from phases.phase04.orchestrator04 import run_phase
        result = run_phase()

        assert Path(".outputs/4-specification/closeout.json").exists()

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_state_tracking(self, mock_validate, mock_tasks, temp_state_dir):
        """Test state tracking."""
        mock_validate.return_value = True

        from phases.phase04.orchestrator04 import run_phase
        result = run_phase()

        state = StateManager()
        for task_id in ['401', '402', '403', '404', '405', '406']:
            assert state.is_task_complete("4-specification", task_id)

    def test_run_phase_validation_failure(self, mock_tasks, temp_state_dir):
        """Test validation failure."""
        with patch('orchestration.pre_task_validation.validate_directory_pristine') as mock_validate:
            mock_validate.return_value = False

            from phases.phase04.orchestrator04 import run_phase
            result = run_phase()

            assert result is False

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_exception_handling(self, mock_validate, mock_tasks, temp_state_dir):
        """Test exception handling."""
        mock_validate.return_value = True

        mock_tasks['403'].side_effect = Exception("OpenSpec error")

        from phases.phase04.orchestrator04 import run_phase
        result = run_phase()

        assert result is False

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_skip_completed(self, mock_validate, mock_tasks, temp_state_dir):
        """Test skip completed."""
        mock_validate.return_value = True

        state = StateManager()
        state.mark_task_complete("4-specification", "402", "Agent")

        from phases.phase04.orchestrator04 import run_phase
        result = run_phase()

        assert not mock_tasks['402'].called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_output_directory(self, mock_validate, mock_tasks, temp_state_dir):
        """Test output directory."""
        mock_validate.return_value = True

        from phases.phase04.orchestrator04 import run_phase
        result = run_phase()

        assert Path(".outputs/4-specification").exists()

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_partial_completion(self, mock_validate, mock_tasks, temp_state_dir):
        """Test partial completion."""
        mock_validate.return_value = True

        mock_tasks['404'].return_value = False

        from phases.phase04.orchestrator04 import run_phase
        result = run_phase()
        assert result is False

        mock_tasks['404'].return_value = True
        result = run_phase(resume_at="404")
        assert result is True


# ============================================================================
# PHASE 5: IMPLEMENTATION
# ============================================================================

class TestPhase05Orchestrator:
    """Integration tests for Phase 5: Implementation orchestrator."""

    @pytest.fixture
    def mock_tasks(self):
        """Mock all Phase 5 task modules."""
        with patch('phases.phase_05_implementation.tasks.task_501') as mock_501, \
             patch('phases.phase_05_implementation.tasks.task_502') as mock_502, \
             patch('phases.phase_05_implementation.tasks.task_503') as mock_503, \
             patch('phases.phase_05_implementation.tasks.task_504') as mock_504, \
             patch('phases.phase_05_implementation.tasks.task_505') as mock_505, \
             patch('phases.phase_05_implementation.tasks.task_506') as mock_506, \
             patch('phases.phase_05_implementation.tasks.task_507') as mock_507:

            for mock in [mock_501, mock_502, mock_503, mock_504, mock_505, mock_506, mock_507]:
                mock.return_value = True

            yield {
                '501': mock_501,
                '502': mock_502,
                '503': mock_503,
                '504': mock_504,
                '505': mock_505,
                '506': mock_506,
                '507': mock_507,
            }

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_all_tasks_success(self, mock_validate, mock_tasks, temp_state_dir):
        """Test complete phase execution."""
        mock_validate.return_value = True

        from phases.phase05.orchestrator05 import run_phase
        result = run_phase()

        assert result is True
        for mock in mock_tasks.values():
            assert mock.called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_task_failure(self, mock_validate, mock_tasks, temp_state_dir):
        """Test phase stops on failure."""
        mock_validate.return_value = True

        mock_tasks['504'].return_value = False

        from phases.phase05.orchestrator05 import run_phase
        result = run_phase()

        assert result is False

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_resume_at(self, mock_validate, mock_tasks, temp_state_dir):
        """Test resuming."""
        mock_validate.return_value = True

        state = StateManager()
        state.mark_task_complete("5-implementation", "501", "Entry")
        state.mark_task_complete("5-implementation", "502", "TDD setup")

        from phases.phase05.orchestrator05 import run_phase
        result = run_phase(resume_at="503")

        assert result is True
        assert not mock_tasks['501'].called
        assert not mock_tasks['502'].called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_creates_closeout(self, mock_validate, mock_tasks, temp_state_dir):
        """Test closeout creation."""
        mock_validate.return_value = True

        from phases.phase05.orchestrator05 import run_phase
        result = run_phase()

        assert Path(".outputs/5-implementation/closeout.json").exists()

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_state_tracking(self, mock_validate, mock_tasks, temp_state_dir):
        """Test state tracking."""
        mock_validate.return_value = True

        from phases.phase05.orchestrator05 import run_phase
        result = run_phase()

        state = StateManager()
        for task_id in ['501', '502', '503', '504', '505', '506', '507']:
            assert state.is_task_complete("5-implementation", task_id)

    def test_run_phase_validation_failure(self, mock_tasks, temp_state_dir):
        """Test validation failure."""
        with patch('orchestration.pre_task_validation.validate_directory_pristine') as mock_validate:
            mock_validate.return_value = False

            from phases.phase05.orchestrator05 import run_phase
            result = run_phase()

            assert result is False

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_exception_handling(self, mock_validate, mock_tasks, temp_state_dir):
        """Test exception handling."""
        mock_validate.return_value = True

        mock_tasks['504'].side_effect = Exception("TDD execution error")

        from phases.phase05.orchestrator05 import run_phase
        result = run_phase()

        assert result is False

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_skip_completed(self, mock_validate, mock_tasks, temp_state_dir):
        """Test skip completed."""
        mock_validate.return_value = True

        state = StateManager()
        state.mark_task_complete("5-implementation", "503", "Agent")

        from phases.phase05.orchestrator05 import run_phase
        result = run_phase()

        assert not mock_tasks['503'].called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_output_directory(self, mock_validate, mock_tasks, temp_state_dir):
        """Test output directory."""
        mock_validate.return_value = True

        from phases.phase05.orchestrator05 import run_phase
        result = run_phase()

        assert Path(".outputs/5-implementation").exists()

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_partial_completion(self, mock_validate, mock_tasks, temp_state_dir):
        """Test partial completion."""
        mock_validate.return_value = True

        mock_tasks['505'].return_value = False

        from phases.phase05.orchestrator05 import run_phase
        result = run_phase()
        assert result is False

        mock_tasks['505'].return_value = True
        result = run_phase(resume_at="505")
        assert result is True


# ============================================================================
# PHASE 6: CODE REVIEW
# ============================================================================

class TestPhase06Orchestrator:
    """Integration tests for Phase 6: Code Review orchestrator."""

    @pytest.fixture
    def mock_tasks(self):
        """Mock all Phase 6 task modules."""
        with patch('phases.phase_06_code_review.tasks.task_601') as mock_601, \
             patch('phases.phase_06_code_review.tasks.task_602') as mock_602, \
             patch('phases.phase_06_code_review.tasks.task_603') as mock_603, \
             patch('phases.phase_06_code_review.tasks.task_604') as mock_604, \
             patch('phases.phase_06_code_review.tasks.task_605') as mock_605, \
             patch('phases.phase_06_code_review.tasks.task_606') as mock_606:

            for mock in [mock_601, mock_602, mock_603, mock_604, mock_605, mock_606]:
                mock.return_value = True

            yield {
                '601': mock_601,
                '602': mock_602,
                '603': mock_603,
                '604': mock_604,
                '605': mock_605,
                '606': mock_606,
            }

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_all_tasks_success(self, mock_validate, mock_tasks, temp_state_dir):
        """Test complete phase execution."""
        mock_validate.return_value = True

        from phases.phase06.orchestrator06 import run_phase
        result = run_phase()

        assert result is True
        for mock in mock_tasks.values():
            assert mock.called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_task_failure(self, mock_validate, mock_tasks, temp_state_dir):
        """Test phase stops on failure."""
        mock_validate.return_value = True

        mock_tasks['603'].return_value = False

        from phases.phase06.orchestrator06 import run_phase
        result = run_phase()

        assert result is False

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_resume_at(self, mock_validate, mock_tasks, temp_state_dir):
        """Test resuming."""
        mock_validate.return_value = True

        state = StateManager()
        state.mark_task_complete("6-code-review", "601", "Entry")

        from phases.phase06.orchestrator06 import run_phase
        result = run_phase(resume_at="602")

        assert result is True
        assert not mock_tasks['601'].called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_creates_closeout(self, mock_validate, mock_tasks, temp_state_dir):
        """Test closeout creation."""
        mock_validate.return_value = True

        from phases.phase06.orchestrator06 import run_phase
        result = run_phase()

        assert Path(".outputs/6-code-review/closeout.json").exists()

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_state_tracking(self, mock_validate, mock_tasks, temp_state_dir):
        """Test state tracking."""
        mock_validate.return_value = True

        from phases.phase06.orchestrator06 import run_phase
        result = run_phase()

        state = StateManager()
        for task_id in ['601', '602', '603', '604', '605', '606']:
            assert state.is_task_complete("6-code-review", task_id)

    def test_run_phase_validation_failure(self, mock_tasks, temp_state_dir):
        """Test validation failure."""
        with patch('orchestration.pre_task_validation.validate_directory_pristine') as mock_validate:
            mock_validate.return_value = False

            from phases.phase06.orchestrator06 import run_phase
            result = run_phase()

            assert result is False

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_exception_handling(self, mock_validate, mock_tasks, temp_state_dir):
        """Test exception handling."""
        mock_validate.return_value = True

        mock_tasks['603'].side_effect = Exception("Review error")

        from phases.phase06.orchestrator06 import run_phase
        result = run_phase()

        assert result is False

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_skip_completed(self, mock_validate, mock_tasks, temp_state_dir):
        """Test skip completed."""
        mock_validate.return_value = True

        state = StateManager()
        state.mark_task_complete("6-code-review", "602", "Agent")

        from phases.phase06.orchestrator06 import run_phase
        result = run_phase()

        assert not mock_tasks['602'].called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_output_directory(self, mock_validate, mock_tasks, temp_state_dir):
        """Test output directory."""
        mock_validate.return_value = True

        from phases.phase06.orchestrator06 import run_phase
        result = run_phase()

        assert Path(".outputs/6-code-review").exists()

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_partial_completion(self, mock_validate, mock_tasks, temp_state_dir):
        """Test partial completion."""
        mock_validate.return_value = True

        mock_tasks['604'].return_value = False

        from phases.phase06.orchestrator06 import run_phase
        result = run_phase()
        assert result is False

        mock_tasks['604'].return_value = True
        result = run_phase(resume_at="604")
        assert result is True


# ============================================================================
# PHASE 7: INTEGRATION
# ============================================================================

class TestPhase07Orchestrator:
    """Integration tests for Phase 7: Integration orchestrator."""

    @pytest.fixture
    def mock_tasks(self):
        """Mock all Phase 7 task modules."""
        with patch('phases.phase_07_integration.tasks.task_701') as mock_701, \
             patch('phases.phase_07_integration.tasks.task_702') as mock_702, \
             patch('phases.phase_07_integration.tasks.task_703') as mock_703, \
             patch('phases.phase_07_integration.tasks.task_704') as mock_704, \
             patch('phases.phase_07_integration.tasks.task_705') as mock_705, \
             patch('phases.phase_07_integration.tasks.task_706') as mock_706, \
             patch('phases.phase_07_integration.tasks.task_707') as mock_707:

            for mock in [mock_701, mock_702, mock_703, mock_704, mock_705, mock_706, mock_707]:
                mock.return_value = True

            yield {
                '701': mock_701,
                '702': mock_702,
                '703': mock_703,
                '704': mock_704,
                '705': mock_705,
                '706': mock_706,
                '707': mock_707,
            }

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_all_tasks_success(self, mock_validate, mock_tasks, temp_state_dir):
        """Test complete phase execution."""
        mock_validate.return_value = True

        from phases.phase07.orchestrator07 import run_phase
        result = run_phase()

        assert result is True
        for mock in mock_tasks.values():
            assert mock.called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_task_failure(self, mock_validate, mock_tasks, temp_state_dir):
        """Test phase stops on failure."""
        mock_validate.return_value = True

        mock_tasks['704'].return_value = False

        from phases.phase07.orchestrator07 import run_phase
        result = run_phase()

        assert result is False

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_resume_at(self, mock_validate, mock_tasks, temp_state_dir):
        """Test resuming."""
        mock_validate.return_value = True

        state = StateManager()
        state.mark_task_complete("7-integration", "701", "Entry")
        state.mark_task_complete("7-integration", "702", "Setup")

        from phases.phase07.orchestrator07 import run_phase
        result = run_phase(resume_at="703")

        assert result is True
        assert not mock_tasks['701'].called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_creates_closeout(self, mock_validate, mock_tasks, temp_state_dir):
        """Test closeout creation."""
        mock_validate.return_value = True

        from phases.phase07.orchestrator07 import run_phase
        result = run_phase()

        assert Path(".outputs/7-integration/closeout.json").exists()

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_state_tracking(self, mock_validate, mock_tasks, temp_state_dir):
        """Test state tracking."""
        mock_validate.return_value = True

        from phases.phase07.orchestrator07 import run_phase
        result = run_phase()

        state = StateManager()
        for task_id in ['701', '702', '703', '704', '705', '706', '707']:
            assert state.is_task_complete("7-integration", task_id)

    def test_run_phase_validation_failure(self, mock_tasks, temp_state_dir):
        """Test validation failure."""
        with patch('orchestration.pre_task_validation.validate_directory_pristine') as mock_validate:
            mock_validate.return_value = False

            from phases.phase07.orchestrator07 import run_phase
            result = run_phase()

            assert result is False

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_exception_handling(self, mock_validate, mock_tasks, temp_state_dir):
        """Test exception handling."""
        mock_validate.return_value = True

        mock_tasks['704'].side_effect = Exception("Integration test error")

        from phases.phase07.orchestrator07 import run_phase
        result = run_phase()

        assert result is False

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_skip_completed(self, mock_validate, mock_tasks, temp_state_dir):
        """Test skip completed."""
        mock_validate.return_value = True

        state = StateManager()
        state.mark_task_complete("7-integration", "703", "Agent")

        from phases.phase07.orchestrator07 import run_phase
        result = run_phase()

        assert not mock_tasks['703'].called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_output_directory(self, mock_validate, mock_tasks, temp_state_dir):
        """Test output directory."""
        mock_validate.return_value = True

        from phases.phase07.orchestrator07 import run_phase
        result = run_phase()

        assert Path(".outputs/7-integration").exists()

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_partial_completion(self, mock_validate, mock_tasks, temp_state_dir):
        """Test partial completion."""
        mock_validate.return_value = True

        mock_tasks['705'].return_value = False

        from phases.phase07.orchestrator07 import run_phase
        result = run_phase()
        assert result is False

        mock_tasks['705'].return_value = True
        result = run_phase(resume_at="705")
        assert result is True


# ============================================================================
# PHASE 8: DEPLOYMENT PREP
# ============================================================================

class TestPhase08Orchestrator:
    """Integration tests for Phase 8: Deployment Prep orchestrator."""

    @pytest.fixture
    def mock_tasks(self):
        """Mock all Phase 8 task modules."""
        with patch('phases.phase_08_deployment_prep.tasks.task_801') as mock_801, \
             patch('phases.phase_08_deployment_prep.tasks.task_802') as mock_802, \
             patch('phases.phase_08_deployment_prep.tasks.task_803') as mock_803, \
             patch('phases.phase_08_deployment_prep.tasks.task_804') as mock_804, \
             patch('phases.phase_08_deployment_prep.tasks.task_805') as mock_805, \
             patch('phases.phase_08_deployment_prep.tasks.task_806') as mock_806, \
             patch('phases.phase_08_deployment_prep.tasks.task_807') as mock_807:

            for mock in [mock_801, mock_802, mock_803, mock_804, mock_805, mock_806, mock_807]:
                mock.return_value = True

            yield {
                '801': mock_801,
                '802': mock_802,
                '803': mock_803,
                '804': mock_804,
                '805': mock_805,
                '806': mock_806,
                '807': mock_807,
            }

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_all_tasks_success(self, mock_validate, mock_tasks, temp_state_dir):
        """Test complete phase execution."""
        mock_validate.return_value = True

        from phases.phase08.orchestrator08 import run_phase
        result = run_phase()

        assert result is True
        for mock in mock_tasks.values():
            assert mock.called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_task_failure(self, mock_validate, mock_tasks, temp_state_dir):
        """Test phase stops on failure."""
        mock_validate.return_value = True

        mock_tasks['804'].return_value = False

        from phases.phase08.orchestrator08 import run_phase
        result = run_phase()

        assert result is False

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_resume_at(self, mock_validate, mock_tasks, temp_state_dir):
        """Test resuming."""
        mock_validate.return_value = True

        state = StateManager()
        state.mark_task_complete("8-deployment-prep", "801", "Entry")

        from phases.phase08.orchestrator08 import run_phase
        result = run_phase(resume_at="802")

        assert result is True
        assert not mock_tasks['801'].called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_creates_closeout(self, mock_validate, mock_tasks, temp_state_dir):
        """Test closeout creation."""
        mock_validate.return_value = True

        from phases.phase08.orchestrator08 import run_phase
        result = run_phase()

        assert Path(".outputs/8-deployment-prep/closeout.json").exists()

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_state_tracking(self, mock_validate, mock_tasks, temp_state_dir):
        """Test state tracking."""
        mock_validate.return_value = True

        from phases.phase08.orchestrator08 import run_phase
        result = run_phase()

        state = StateManager()
        for task_id in ['801', '802', '803', '804', '805', '806', '807']:
            assert state.is_task_complete("8-deployment-prep", task_id)

    def test_run_phase_validation_failure(self, mock_tasks, temp_state_dir):
        """Test validation failure."""
        with patch('orchestration.pre_task_validation.validate_directory_pristine') as mock_validate:
            mock_validate.return_value = False

            from phases.phase08.orchestrator08 import run_phase
            result = run_phase()

            assert result is False

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_exception_handling(self, mock_validate, mock_tasks, temp_state_dir):
        """Test exception handling."""
        mock_validate.return_value = True

        mock_tasks['804'].side_effect = Exception("Artifact generation error")

        from phases.phase08.orchestrator08 import run_phase
        result = run_phase()

        assert result is False

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_skip_completed(self, mock_validate, mock_tasks, temp_state_dir):
        """Test skip completed."""
        mock_validate.return_value = True

        state = StateManager()
        state.mark_task_complete("8-deployment-prep", "803", "Agent")

        from phases.phase08.orchestrator08 import run_phase
        result = run_phase()

        assert not mock_tasks['803'].called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_output_directory(self, mock_validate, mock_tasks, temp_state_dir):
        """Test output directory."""
        mock_validate.return_value = True

        from phases.phase08.orchestrator08 import run_phase
        result = run_phase()

        assert Path(".outputs/8-deployment-prep").exists()

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_partial_completion(self, mock_validate, mock_tasks, temp_state_dir):
        """Test partial completion."""
        mock_validate.return_value = True

        mock_tasks['806'].return_value = False

        from phases.phase08.orchestrator08 import run_phase
        result = run_phase()
        assert result is False

        mock_tasks['806'].return_value = True
        result = run_phase(resume_at="806")
        assert result is True


# ============================================================================
# PHASE 9: RELEASE
# ============================================================================

class TestPhase09Orchestrator:
    """Integration tests for Phase 9: Release orchestrator."""

    @pytest.fixture
    def mock_tasks(self):
        """Mock all Phase 9 task modules."""
        with patch('phases.phase_09_release.tasks.task_901') as mock_901, \
             patch('phases.phase_09_release.tasks.task_902') as mock_902, \
             patch('phases.phase_09_release.tasks.task_903') as mock_903, \
             patch('phases.phase_09_release.tasks.task_904') as mock_904, \
             patch('phases.phase_09_release.tasks.task_905') as mock_905, \
             patch('phases.phase_09_release.tasks.task_906') as mock_906:

            for mock in [mock_901, mock_902, mock_903, mock_904, mock_905, mock_906]:
                mock.return_value = True

            yield {
                '901': mock_901,
                '902': mock_902,
                '903': mock_903,
                '904': mock_904,
                '905': mock_905,
                '906': mock_906,
            }

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_all_tasks_success(self, mock_validate, mock_tasks, temp_state_dir):
        """Test complete phase execution."""
        mock_validate.return_value = True

        from phases.phase09.orchestrator09 import run_phase
        result = run_phase()

        assert result is True
        for mock in mock_tasks.values():
            assert mock.called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_task_failure(self, mock_validate, mock_tasks, temp_state_dir):
        """Test phase stops on failure."""
        mock_validate.return_value = True

        mock_tasks['904'].return_value = False

        from phases.phase09.orchestrator09 import run_phase
        result = run_phase()

        assert result is False

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_resume_at(self, mock_validate, mock_tasks, temp_state_dir):
        """Test resuming."""
        mock_validate.return_value = True

        state = StateManager()
        state.mark_task_complete("9-release", "901", "Entry")
        state.mark_task_complete("9-release", "902", "Setup")

        from phases.phase09.orchestrator09 import run_phase
        result = run_phase(resume_at="903")

        assert result is True
        assert not mock_tasks['901'].called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_creates_closeout(self, mock_validate, mock_tasks, temp_state_dir):
        """Test closeout creation."""
        mock_validate.return_value = True

        from phases.phase09.orchestrator09 import run_phase
        result = run_phase()

        assert Path(".outputs/9-release/closeout.json").exists()

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_state_tracking(self, mock_validate, mock_tasks, temp_state_dir):
        """Test state tracking."""
        mock_validate.return_value = True

        from phases.phase09.orchestrator09 import run_phase
        result = run_phase()

        state = StateManager()
        for task_id in ['901', '902', '903', '904', '905', '906']:
            assert state.is_task_complete("9-release", task_id)

    def test_run_phase_validation_failure(self, mock_tasks, temp_state_dir):
        """Test validation failure."""
        with patch('orchestration.pre_task_validation.validate_directory_pristine') as mock_validate:
            mock_validate.return_value = False

            from phases.phase09.orchestrator09 import run_phase
            result = run_phase()

            assert result is False

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_exception_handling(self, mock_validate, mock_tasks, temp_state_dir):
        """Test exception handling."""
        mock_validate.return_value = True

        mock_tasks['904'].side_effect = Exception("Release execution error")

        from phases.phase09.orchestrator09 import run_phase
        result = run_phase()

        assert result is False

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_skip_completed(self, mock_validate, mock_tasks, temp_state_dir):
        """Test skip completed."""
        mock_validate.return_value = True

        state = StateManager()
        state.mark_task_complete("9-release", "903", "Agent")

        from phases.phase09.orchestrator09 import run_phase
        result = run_phase()

        assert not mock_tasks['903'].called

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_output_directory(self, mock_validate, mock_tasks, temp_state_dir):
        """Test output directory."""
        mock_validate.return_value = True

        from phases.phase09.orchestrator09 import run_phase
        result = run_phase()

        assert Path(".outputs/9-release").exists()

    @patch('orchestration.pre_task_validation.validate_directory_pristine')
    def test_run_phase_partial_completion(self, mock_validate, mock_tasks, temp_state_dir):
        """Test partial completion."""
        mock_validate.return_value = True

        mock_tasks['905'].return_value = False

        from phases.phase09.orchestrator09 import run_phase
        result = run_phase()
        assert result is False

        mock_tasks['905'].return_value = True
        result = run_phase(resume_at="905")
        assert result is True
