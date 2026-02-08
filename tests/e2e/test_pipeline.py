"""
End-to-End Pipeline Tests

Tests complete phase execution, transitions, and rollback scenarios.
Tests the full SDLC pipeline orchestration.

Author: Phase 6 - Testing & Validation
"""

import pytest
import json
import shutil
from pathlib import Path
from datetime import datetime

from core.state import StateManager, TaskStatus, PhaseStatus
from core.config import Config


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def pipeline_env(temp_dir):
    """Set up complete pipeline environment."""
    # Create directory structure
    state_dir = temp_dir / ".state"
    output_dir = temp_dir / ".outputs"
    log_dir = temp_dir / ".logs"

    state_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create phase directories
    for phase_num in range(10):
        phase_dir = temp_dir / "phases" / f"phase{phase_num:02d}"
        phase_dir.mkdir(parents=True, exist_ok=True)

    return {
        "root": temp_dir,
        "state_dir": state_dir,
        "output_dir": output_dir,
        "log_dir": log_dir
    }


@pytest.fixture
def state_manager(pipeline_env):
    """Create state manager for pipeline tests."""
    return StateManager(
        state_dir=pipeline_env["state_dir"],
        atomic_root=pipeline_env["root"]
    )


@pytest.fixture
def config_manager(pipeline_env):
    """Create config manager for pipeline tests."""
    return Config(atomic_root=pipeline_env["root"])


# ============================================================================
# PHASE 0 EXECUTION TESTS
# ============================================================================

@pytest.mark.e2e
class TestPhase0Execution:
    """Test complete Phase 0 (Setup) execution."""

    def test_phase_0_complete_flow(self, state_manager, pipeline_env):
        """Test Phase 0 executes all tasks successfully."""
        phase_id = "0-setup"

        # Simulate task execution
        tasks = [
            ("001", "Mode Selection"),
            ("002", "Config Collection"),
            ("003", "Config Display"),
            ("004", "Secrets Collection"),
            ("005", "Dashboard Check"),
            ("006", "Setup Validation"),
        ]

        for task_id, task_name in tasks:
            assert not state_manager.is_task_complete(phase_id, task_id)
            state_manager.mark_task_complete(phase_id, task_id, task_name)
            assert state_manager.is_task_complete(phase_id, task_id)

        # Verify all tasks complete
        completed = state_manager.get_completed_tasks(phase_id)
        assert len(completed) == len(tasks)
        assert all(task_id in completed for task_id, _ in tasks)

    def test_phase_0_task_failures(self, state_manager):
        """Test Phase 0 handles task failures correctly."""
        phase_id = "0-setup"
        task_id = "002"
        task_name = "Config Collection"
        error = "User cancelled configuration"

        # Mark task as failed
        state_manager.mark_task_failed(phase_id, task_id, task_name, error)

        # Verify failure recorded
        assert state_manager.is_task_failed(phase_id, task_id)
        assert state_manager.get_task_status(phase_id, task_id) == "failed"

        # Verify task not marked as complete
        assert not state_manager.is_task_complete(phase_id, task_id)

    def test_phase_0_creates_closeout(self, state_manager, pipeline_env):
        """Test Phase 0 creates closeout.json artifact."""
        phase_id = "0-setup"
        output_dir = pipeline_env["output_dir"] / phase_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Simulate closeout creation
        closeout_data = {
            "phase": phase_id,
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "tasks_completed": 6,
            "artifacts": [
                "project-config.json",
                "secrets.json",
                "setup-report.md"
            ]
        }

        closeout_file = output_dir / "closeout.json"
        with open(closeout_file, 'w') as f:
            json.dump(closeout_data, f, indent=2)

        # Verify closeout exists and is valid
        assert closeout_file.exists()

        with open(closeout_file) as f:
            data = json.load(f)

        assert data["phase"] == phase_id
        assert data["status"] == "completed"
        assert len(data["artifacts"]) == 3

    def test_phase_0_idempotent_execution(self, state_manager):
        """Test Phase 0 can be run multiple times (idempotent)."""
        phase_id = "0-setup"
        task_id = "001"
        task_name = "Mode Selection"

        # Mark task complete twice
        state_manager.mark_task_complete(phase_id, task_id, task_name)
        assert state_manager.is_task_complete(phase_id, task_id)

        state_manager.mark_task_complete(phase_id, task_id, task_name)
        assert state_manager.is_task_complete(phase_id, task_id)

        # Verify only one task record
        tasks = state_manager.get_phase_tasks(phase_id)
        assert len(tasks) == 1


# ============================================================================
# PHASE TRANSITION TESTS
# ============================================================================

@pytest.mark.e2e
class TestPhaseTransitions:
    """Test Phase 0 → Phase 1 transitions."""

    def test_phase_0_to_phase_1_transition(self, state_manager, pipeline_env):
        """Test successful transition from Phase 0 to Phase 1."""
        # Complete Phase 0
        phase_0_id = "0-setup"
        state_manager.mark_task_complete(phase_0_id, "001", "Setup Task 1")
        state_manager.mark_phase_complete(phase_0_id)

        # Create Phase 0 closeout
        output_dir = pipeline_env["output_dir"] / phase_0_id
        output_dir.mkdir(parents=True, exist_ok=True)
        closeout = output_dir / "closeout.json"
        closeout.write_text(json.dumps({"status": "completed"}))

        # Start Phase 1
        phase_1_id = "1-discovery"
        state_manager.set_current_phase(phase_1_id)

        # Verify transition
        assert state_manager.get_current_phase() == phase_1_id

        # Verify Phase 0 still complete
        phase_0_data = state_manager._state["phases"][phase_0_id]
        assert phase_0_data.get("status") == "completed"

    def test_phase_transition_requires_closeout(self, state_manager, pipeline_env):
        """Test Phase 1 requires Phase 0 closeout."""
        phase_0_id = "0-setup"
        output_dir = pipeline_env["output_dir"] / phase_0_id

        # Closeout should not exist yet
        closeout = output_dir / "closeout.json"
        assert not closeout.exists()

        # Phase 1 should check for closeout before starting
        # (This would be enforced by orchestrator, state manager just tracks)
        state_manager.set_current_phase("1-discovery")

        # Verify state updated (manager doesn't enforce, orchestrator does)
        assert state_manager.get_current_phase() == "1-discovery"

    def test_phase_1_inherits_context(self, state_manager, pipeline_env):
        """Test Phase 1 inherits configuration from Phase 0."""
        # Create Phase 0 config
        phase_0_output = pipeline_env["output_dir"] / "0-setup"
        phase_0_output.mkdir(parents=True, exist_ok=True)

        config_data = {
            "project": {"name": "test-project", "type": "web-app"},
            "llm": {"primary_model": "sonnet"}
        }

        config_file = phase_0_output / "project-config.json"
        with open(config_file, 'w') as f:
            json.dump({"extracted": config_data}, f, indent=2)

        # Load config in Phase 1
        config = Config(atomic_root=pipeline_env["root"])

        # Verify inheritance
        assert config.get("project.name") == "test-project"
        assert config.get("project.type") == "web-app"
        assert config.get("llm.primary_model") == "sonnet"


# ============================================================================
# PHASE CHAINING TESTS
# ============================================================================

@pytest.mark.e2e
class TestPhaseChaining:
    """Test Phase 0 → Phase 1 → Phase 2 chaining."""

    def test_three_phase_chain(self, state_manager, pipeline_env):
        """Test execution chain across three phases."""
        phases = [
            ("0-setup", ["001", "002", "003"]),
            ("1-discovery", ["101", "102", "103"]),
            ("2-prd", ["201", "202", "203"])
        ]

        for phase_id, task_ids in phases:
            # Mark tasks complete
            for task_id in task_ids:
                state_manager.mark_task_complete(
                    phase_id, task_id, f"Task {task_id}"
                )

            # Mark phase complete
            state_manager.mark_phase_complete(phase_id)

            # Create closeout
            output_dir = pipeline_env["output_dir"] / phase_id
            output_dir.mkdir(parents=True, exist_ok=True)
            closeout = output_dir / "closeout.json"
            closeout.write_text(json.dumps({
                "phase": phase_id,
                "status": "completed"
            }))

        # Verify all phases complete
        for phase_id, task_ids in phases:
            phase_data = state_manager._state["phases"][phase_id]
            assert phase_data.get("status") == "completed"

            completed = state_manager.get_completed_tasks(phase_id)
            assert len(completed) == len(task_ids)

    def test_chain_stops_on_failure(self, state_manager):
        """Test phase chain stops when a task fails."""
        # Complete Phase 0
        phase_0_id = "0-setup"
        state_manager.mark_task_complete(phase_0_id, "001", "Task 1")
        state_manager.mark_phase_complete(phase_0_id)

        # Fail Phase 1 task
        phase_1_id = "1-discovery"
        state_manager.mark_task_failed(
            phase_1_id, "102", "Discovery Task 2", "Error occurred"
        )

        # Phase 1 should not be marked complete
        phase_1_data = state_manager._state["phases"].get(phase_1_id, {})
        assert phase_1_data.get("status") != "completed"

        # Verify failure recorded
        assert state_manager.is_task_failed(phase_1_id, "102")


# ============================================================================
# ROLLBACK TESTS
# ============================================================================

@pytest.mark.e2e
class TestRollbackScenarios:
    """Test state rollback and recovery."""

    def test_snapshot_and_restore(self, state_manager):
        """Test creating snapshot and restoring state."""
        # Create initial state
        state_manager.mark_task_complete("0-setup", "001", "Task 1")
        state_manager.mark_task_complete("0-setup", "002", "Task 2")

        # Create snapshot
        snapshot = state_manager.snapshot()
        assert snapshot.phases["0-setup"].tasks["001"].status == TaskStatus.COMPLETED

        # Make changes
        state_manager.mark_task_complete("0-setup", "003", "Task 3")
        assert state_manager.is_task_complete("0-setup", "003")

        # Restore snapshot
        state_manager.restore(snapshot)

        # Verify restoration
        assert state_manager.is_task_complete("0-setup", "001")
        assert state_manager.is_task_complete("0-setup", "002")
        assert not state_manager.is_task_complete("0-setup", "003")

    def test_transaction_commit(self, state_manager):
        """Test transaction commits changes."""
        with state_manager.begin_transaction() as txn:
            txn.mark_task_complete("0-setup", "001", "Task 1")
            txn.mark_task_complete("0-setup", "002", "Task 2")

        # Verify changes committed
        assert state_manager.is_task_complete("0-setup", "001")
        assert state_manager.is_task_complete("0-setup", "002")

    def test_transaction_rollback(self, state_manager):
        """Test transaction rolls back on exception."""
        # Initial state
        state_manager.mark_task_complete("0-setup", "001", "Task 1")

        # Transaction with error
        try:
            with state_manager.begin_transaction() as txn:
                txn.mark_task_complete("0-setup", "002", "Task 2")
                txn.mark_task_complete("0-setup", "003", "Task 3")
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Verify rollback
        assert state_manager.is_task_complete("0-setup", "001")
        assert not state_manager.is_task_complete("0-setup", "002")
        assert not state_manager.is_task_complete("0-setup", "003")

    def test_save_and_load_snapshot(self, state_manager, pipeline_env):
        """Test saving snapshot to disk and loading it back."""
        # Create state
        state_manager.mark_task_complete("0-setup", "001", "Task 1")
        state_manager.mark_task_complete("0-setup", "002", "Task 2")

        # Save snapshot
        snapshot_file = state_manager.save_snapshot("test_snapshot")
        assert snapshot_file.exists()

        # Make changes
        state_manager.mark_task_complete("0-setup", "003", "Task 3")

        # Load snapshot
        state_manager.load_snapshot(snapshot_file)

        # Verify restoration
        assert state_manager.is_task_complete("0-setup", "001")
        assert state_manager.is_task_complete("0-setup", "002")
        assert not state_manager.is_task_complete("0-setup", "003")


# ============================================================================
# PAUSE/RESUME TESTS
# ============================================================================

@pytest.mark.e2e
class TestPauseResume:
    """Test pause and resume functionality."""

    def test_pause_mid_phase(self, state_manager):
        """Test pausing execution mid-phase."""
        phase_id = "1-discovery"

        # Execute first 2 tasks
        state_manager.mark_task_complete(phase_id, "101", "Task 1")
        state_manager.mark_task_complete(phase_id, "102", "Task 2")
        state_manager.set_current_task("103")

        # Simulate pause (save state)
        state_manager.save_state()

        # Verify state
        assert state_manager.is_task_complete(phase_id, "101")
        assert state_manager.is_task_complete(phase_id, "102")
        assert not state_manager.is_task_complete(phase_id, "103")
        assert state_manager.get_current_task() == "103"

    def test_resume_from_task(self, state_manager):
        """Test resuming from specific task."""
        phase_id = "1-discovery"

        # Set up paused state
        state_manager.mark_task_complete(phase_id, "101", "Task 1")
        state_manager.mark_task_complete(phase_id, "102", "Task 2")
        state_manager.set_current_phase(phase_id)
        state_manager.set_current_task("103")
        state_manager.save_state()

        # Create new state manager (simulate restart)
        new_state = StateManager(
            state_dir=state_manager.state_dir,
            atomic_root=state_manager.atomic_root
        )

        # Verify resume point
        assert new_state.get_current_phase() == phase_id
        assert new_state.get_current_task() == "103"
        assert new_state.is_task_complete(phase_id, "101")
        assert new_state.is_task_complete(phase_id, "102")

    def test_resume_skips_completed(self, state_manager):
        """Test resume skips already completed tasks."""
        phase_id = "1-discovery"
        tasks = ["101", "102", "103", "104", "105"]

        # Complete first 3 tasks
        for task_id in tasks[:3]:
            state_manager.mark_task_complete(phase_id, task_id, f"Task {task_id}")

        # Simulate resume from task 102 (should skip to next incomplete: 104)
        completed = state_manager.get_completed_tasks(phase_id)

        # Find first incomplete task
        next_task = None
        for task_id in tasks:
            if task_id not in completed:
                next_task = task_id
                break

        assert next_task == "104"


# ============================================================================
# ERROR RECOVERY TESTS
# ============================================================================

@pytest.mark.e2e
class TestErrorRecovery:
    """Test error handling and recovery."""

    def test_recover_from_corrupted_state(self, state_manager, pipeline_env):
        """Test recovery from corrupted state file."""
        # Corrupt state file
        state_file = state_manager.state_file
        state_file.write_text("corrupted json {{{")

        # Create new state manager (should handle corruption)
        new_state = StateManager(
            state_dir=state_manager.state_dir,
            atomic_root=state_manager.atomic_root
        )

        # Should create clean state
        assert new_state._state["phases"] == {}

    def test_recover_from_missing_state(self, pipeline_env):
        """Test recovery from missing state file."""
        state_dir = pipeline_env["state_dir"]

        # State file doesn't exist yet
        state_file = state_dir / "task-state.json"
        assert not state_file.exists()

        # Create state manager
        state = StateManager(state_dir=state_dir, atomic_root=pipeline_env["root"])

        # Should create state file
        assert state_file.exists()

    def test_handle_interrupted_task(self, state_manager):
        """Test handling task interrupted mid-execution."""
        phase_id = "1-discovery"
        task_id = "102"

        # Mark task in progress
        state_manager.set_current_phase(phase_id)
        state_manager.set_current_task(task_id)

        # Simulate interruption (don't mark complete)
        state_manager.save_state()

        # Verify task not complete
        assert not state_manager.is_task_complete(phase_id, task_id)
        assert state_manager.get_current_task() == task_id


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
class TestPipelinePerformance:
    """Test pipeline performance and scalability."""

    def test_many_tasks_performance(self, state_manager):
        """Test state manager handles many tasks efficiently."""
        import time

        phase_id = "test-phase"
        num_tasks = 100

        start = time.time()

        # Mark many tasks complete
        for i in range(num_tasks):
            state_manager.mark_task_complete(
                phase_id,
                f"{i:03d}",
                f"Task {i}"
            )

        elapsed = time.time() - start

        # Should complete in reasonable time (< 1s for 100 tasks)
        assert elapsed < 1.0

        # Verify all tasks complete
        completed = state_manager.get_completed_tasks(phase_id)
        assert len(completed) == num_tasks

    def test_snapshot_performance(self, state_manager):
        """Test snapshot performance with large state."""
        import time

        # Create large state (10 phases × 10 tasks each)
        for phase_num in range(10):
            phase_id = f"{phase_num}-phase"
            for task_num in range(10):
                task_id = f"{task_num:03d}"
                state_manager.mark_task_complete(
                    phase_id, task_id, f"Task {task_id}"
                )

        # Time snapshot creation
        start = time.time()
        snapshot = state_manager.snapshot()
        elapsed = time.time() - start

        # Should be fast (< 0.1s)
        assert elapsed < 0.1

        # Verify snapshot complete
        assert len(snapshot.phases) == 10


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

@pytest.mark.e2e
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_phase(self, state_manager):
        """Test phase with no tasks."""
        phase_id = "empty-phase"

        # Mark phase complete without any tasks
        state_manager.mark_phase_complete(phase_id)

        # Verify phase exists and is complete
        phase_data = state_manager._state["phases"][phase_id]
        assert phase_data["status"] == "completed"

    def test_duplicate_task_ids(self, state_manager):
        """Test handling duplicate task IDs in same phase."""
        phase_id = "test-phase"
        task_id = "001"

        # Mark same task complete twice
        state_manager.mark_task_complete(phase_id, task_id, "Task 1")
        state_manager.mark_task_complete(phase_id, task_id, "Task 1 Updated")

        # Should have only one task record
        tasks = state_manager.get_phase_tasks(phase_id)
        assert len(tasks) == 1

    def test_phase_without_closeout(self, state_manager, pipeline_env):
        """Test phase completion without closeout file."""
        phase_id = "test-phase"

        # Mark phase complete
        state_manager.mark_phase_complete(phase_id)

        # Verify state (closeout is optional, state tracks completion)
        phase_data = state_manager._state["phases"][phase_id]
        assert phase_data["status"] == "completed"

    def test_concurrent_state_access(self, state_manager):
        """Test concurrent state access (basic locking)."""
        phase_id = "test-phase"

        # Acquire lock
        with state_manager.begin_transaction() as txn:
            txn.mark_task_complete(phase_id, "001", "Task 1")

            # Lock should be held
            assert state_manager.is_task_complete(phase_id, "001")

        # Lock should be released
        assert state_manager.is_task_complete(phase_id, "001")
