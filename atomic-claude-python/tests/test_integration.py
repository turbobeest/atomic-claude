#!/usr/bin/env python3
"""
ATOMIC CLAUDE - Integration Tests
Comprehensive test suite for Python implementation modules

Coverage:
- atomic.py: Core invocation, output functions, file operations
- provider.py: Provider management, availability checks, model selection
- memory.py: Memory initialization, save/recall operations
- phase.py: Phase lifecycle management
- task_state.py: Task state transitions and tracking
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from atomic import (
    atomic_error,
    atomic_extract_json,
    atomic_info,
    atomic_json_escape,
    atomic_mktemp,
    atomic_mktemp_done,
    atomic_state_get,
    atomic_state_increment,
    atomic_state_init,
    atomic_state_set,
    atomic_step,
    atomic_substep,
    atomic_success,
    atomic_timeout,
    atomic_validate_files,
    atomic_warn,
    cleanup_temp_files,
)
from memory import (
    MemoryConfig,
    get_config,
    memory_check_backtrack,
    memory_create_checkpoint,
    memory_get_head_phase,
    memory_init,
    memory_set_head_phase,
    memory_should_persist,
)
from phase import PhaseManager, PhaseState
from provider import (
    AvailabilityCache,
    OllamaServer,
    ProviderConfig,
    ProviderManager,
    TaskType,
)
from task_state import (
    Phase,
    Task,
    TaskState,
    TaskStateManager,
    TaskStatus,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test isolation."""
    tmpdir = tempfile.mkdtemp(prefix="atomic-test-")
    yield Path(tmpdir)
    # Cleanup after test
    if Path(tmpdir).exists():
        shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def atomic_env(temp_dir):
    """Set up test environment variables."""
    old_env = {}
    test_env = {
        "ATOMIC_ROOT": str(temp_dir),
        "ATOMIC_STATE_DIR": str(temp_dir / ".state"),
        "ATOMIC_OUTPUT_DIR": str(temp_dir / ".outputs"),
        "ATOMIC_LOG_DIR": str(temp_dir / ".logs"),
    }

    # Save old values
    for key in test_env:
        old_env[key] = os.environ.get(key)

    # Set test values
    os.environ.update(test_env)

    yield test_env

    # Restore old values
    for key, value in old_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


# ============================================================================
# ATOMIC.PY TESTS
# ============================================================================


class TestAtomic:
    """Test suite for atomic.py module."""

    def test_atomic_step_output(self, capsys):
        """Test that atomic_step prints formatted output."""
        atomic_step("Testing step message")
        captured = capsys.readouterr()
        assert "Testing step message" in captured.out
        assert "▶" in captured.out

    def test_atomic_substep_output(self, capsys):
        """Test that atomic_substep prints formatted output."""
        atomic_substep("Testing substep message")
        captured = capsys.readouterr()
        assert "Testing substep message" in captured.out
        assert "→" in captured.out

    def test_atomic_success_output(self, capsys):
        """Test that atomic_success prints formatted output."""
        atomic_success("Operation completed")
        captured = capsys.readouterr()
        assert "Operation completed" in captured.out
        assert "✓" in captured.out

    def test_atomic_error_output(self, capsys):
        """Test that atomic_error prints to stderr."""
        atomic_error("Error occurred")
        captured = capsys.readouterr()
        assert "Error occurred" in captured.err
        assert "✗" in captured.err

    def test_atomic_warn_output(self, capsys):
        """Test that atomic_warn prints to stderr."""
        atomic_warn("Warning message")
        captured = capsys.readouterr()
        assert "Warning message" in captured.err
        assert "⚠" in captured.err

    def test_atomic_info_output(self, capsys):
        """Test that atomic_info prints formatted output."""
        atomic_info("Info message")
        captured = capsys.readouterr()
        assert "Info message" in captured.out
        assert "ℹ" in captured.out

    def test_atomic_json_escape(self):
        """Test JSON string escaping."""
        # Test basic escaping
        assert atomic_json_escape('hello "world"') == 'hello \\"world\\"'
        assert atomic_json_escape("line1\nline2") == "line1\\nline2"
        assert atomic_json_escape("tab\there") == "tab\\there"
        assert atomic_json_escape("back\\slash") == "back\\\\slash"

        # Test combined escapes
        input_str = 'test "quote" and\nnewline and\\backslash'
        result = atomic_json_escape(input_str)
        assert '\\"' in result
        assert '\\n' in result
        assert '\\\\' in result

    def test_atomic_mktemp_tracking(self, temp_dir):
        """Test temporary file creation and tracking."""
        temp_file = atomic_mktemp()
        assert Path(temp_file).exists()

        # File should be tracked
        from atomic import _ATOMIC_TEMP_FILES
        assert temp_file in _ATOMIC_TEMP_FILES

        # Mark as done
        atomic_mktemp_done(temp_file)
        assert temp_file not in _ATOMIC_TEMP_FILES

        # Cleanup
        if Path(temp_file).exists():
            os.unlink(temp_file)

    def test_cleanup_temp_files(self):
        """Test cleanup of tracked temporary files."""
        # Create some temp files
        temp1 = atomic_mktemp()
        temp2 = atomic_mktemp()

        assert Path(temp1).exists()
        assert Path(temp2).exists()

        # Cleanup
        cleanup_temp_files()

        # Files should be removed
        assert not Path(temp1).exists()
        assert not Path(temp2).exists()

    def test_atomic_state_init(self, atomic_env, temp_dir):
        """Test state directory and session file initialization."""
        atomic_state_init()

        state_dir = Path(atomic_env["ATOMIC_STATE_DIR"])
        assert state_dir.exists()

        session_file = state_dir / "session.json"
        assert session_file.exists()

        with open(session_file) as f:
            session = json.load(f)
        assert "session_id" in session
        assert "started_at" in session

    def test_atomic_state_get_set(self, atomic_env, temp_dir):
        """Test state get/set operations."""
        atomic_state_init()

        # Set a value
        assert atomic_state_set("test_key", "test_value")

        # Get the value
        value = atomic_state_get("test_key")
        assert value == "test_value"

        # Get non-existent key
        assert atomic_state_get("missing_key") is None

    def test_atomic_state_increment(self, atomic_env, temp_dir):
        """Test state increment operation."""
        atomic_state_init()

        # Increment non-existent key (should start at 0)
        assert atomic_state_increment("counter")
        assert atomic_state_get("counter") == 1

        # Increment again
        assert atomic_state_increment("counter")
        assert atomic_state_get("counter") == 2

    def test_atomic_timeout(self):
        """Test command timeout functionality."""
        # Test successful command
        result = atomic_timeout(5, ["echo", "test"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "test" in result.stdout

        # Test timeout (should raise TimeoutExpired)
        with pytest.raises(subprocess.TimeoutExpired):
            atomic_timeout(1, ["sleep", "5"])

    def test_atomic_validate_files(self, temp_dir, capsys):
        """Test file validation."""
        # Create test files
        file1 = temp_dir / "file1.txt"
        file2 = temp_dir / "file2.txt"
        file1.write_text("test")

        # Validate existing file
        assert atomic_validate_files(str(file1))

        # Validate missing file
        assert not atomic_validate_files(str(file2))
        captured = capsys.readouterr()
        assert "Missing required files" in captured.err

        # Validate multiple files
        assert not atomic_validate_files(str(file1), str(file2))

    def test_atomic_extract_json(self, temp_dir):
        """Test JSON extraction from mixed output."""
        # Test with JSON block
        input_file = temp_dir / "input.txt"
        output_file = temp_dir / "output.json"

        input_file.write_text('''
        Some text before
        ```json
        {"key": "value", "number": 42}
        ```
        Some text after
        ''')

        assert atomic_extract_json(str(input_file), str(output_file))

        with open(output_file) as f:
            data = json.load(f)
        assert data["key"] == "value"
        assert data["number"] == 42

        # Test with raw JSON
        input_file.write_text('{"raw": "json"}')
        assert atomic_extract_json(str(input_file), str(output_file))

        with open(output_file) as f:
            data = json.load(f)
        assert data["raw"] == "json"


# ============================================================================
# PROVIDER.PY TESTS
# ============================================================================


class TestProvider:
    """Test suite for provider.py module."""

    def test_ollama_server_from_dict(self):
        """Test OllamaServer creation from dictionary."""
        data = {
            "name": "local",
            "host": "localhost:11434",
            "model": "llama3.1:8b",
            "priority": 1,
        }
        server = OllamaServer.from_dict(data)
        assert server.name == "local"
        assert server.host == "localhost:11434"
        assert server.model == "llama3.1:8b"
        assert server.priority == 1

    def test_ollama_server_to_dict(self):
        """Test OllamaServer conversion to dictionary."""
        server = OllamaServer(
            name="remote", host="remote:11434", model="llama3.1:70b", priority=2
        )
        data = server.to_dict()
        assert data["name"] == "remote"
        assert data["host"] == "remote:11434"
        assert data["model"] == "llama3.1:70b"
        assert data["priority"] == 2

    def test_provider_config_from_dict(self):
        """Test ProviderConfig creation from dictionary."""
        data = {
            "providers": {
                "ollama": {
                    "enabled": True,
                    "failover": True,
                    "health_check": True,
                    "servers": [
                        {
                            "name": "local",
                            "host": "localhost:11434",
                            "model": "llama3.1:8b",
                            "priority": 1,
                        }
                    ],
                },
                "routing": {
                    "critical": "primary",
                    "bulk": "ollama",
                    "background": "ollama",
                    "background_model": "llama3.2:3b",
                },
                "chains": {
                    "critical": "claude-code anthropic aws-bedrock ollama",
                    "bulk": "ollama anthropic",
                },
            }
        }

        config = ProviderConfig.from_dict(data)
        assert config.ollama_enabled is True
        assert config.critical_provider == "primary"
        assert config.bulk_provider == "ollama"
        assert len(config.ollama_servers) == 1
        assert config.ollama_servers[0].name == "local"
        assert "critical" in config.chains
        assert config.chains["critical"] == [
            "claude-code",
            "anthropic",
            "aws-bedrock",
            "ollama",
        ]

    def test_availability_cache(self):
        """Test AvailabilityCache expiration logic."""
        cache = AvailabilityCache(
            provider="anthropic", available=True, timestamp=time.time()
        )
        assert not cache.is_expired(60)

        # Simulate old cache
        old_cache = AvailabilityCache(
            provider="anthropic", available=True, timestamp=time.time() - 120
        )
        assert old_cache.is_expired(60)

    def test_provider_manager_init(self, atomic_env, temp_dir):
        """Test ProviderManager initialization."""
        manager = ProviderManager(
            config_file=temp_dir / "config.json", cache_dir=temp_dir / "cache"
        )
        assert manager.config_file.exists() or not manager.config_file.exists()
        assert manager.cache_dir.exists()

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_check_anthropic_available(self, atomic_env, temp_dir):
        """Test Anthropic API availability check."""
        manager = ProviderManager(cache_dir=temp_dir / "cache")
        assert manager.check_anthropic() is True

    @patch.dict(os.environ, {}, clear=True)
    def test_check_anthropic_unavailable(self, atomic_env, temp_dir):
        """Test Anthropic API unavailable."""
        os.environ.pop("ANTHROPIC_API_KEY", None)
        manager = ProviderManager(cache_dir=temp_dir / "cache")
        assert manager.check_anthropic() is False

    def test_get_chain(self, atomic_env, temp_dir):
        """Test getting provider chain for task type."""
        # Create config file
        config_file = temp_dir / "config.json"
        config_data = {
            "providers": {
                "chains": {
                    "critical": ["claude-code", "anthropic"],
                    "bulk": ["ollama", "anthropic"],
                }
            }
        }
        config_file.write_text(json.dumps(config_data))

        manager = ProviderManager(
            config_file=config_file, cache_dir=temp_dir / "cache"
        )
        manager.init()

        chain = manager.get_chain("critical")
        assert chain == ["claude-code", "anthropic"]

        chain = manager.get_chain("bulk")
        assert chain == ["ollama", "anthropic"]

    def test_resolve_for_task(self, atomic_env, temp_dir):
        """Test provider resolution for task type."""
        manager = ProviderManager(cache_dir=temp_dir / "cache")
        manager.init()

        # Should return some provider (default or available)
        provider = manager.resolve_for_task("critical")
        assert provider in [
            "claude-code",
            "anthropic",
            "aws-bedrock",
            "ollama",
            "openai",
            "google",
            "azure",
            "openrouter",
        ]


# ============================================================================
# MEMORY.PY TESTS
# ============================================================================


class TestMemory:
    """Test suite for memory.py module."""

    def test_memory_config_init(self, atomic_env, temp_dir):
        """Test MemoryConfig initialization."""
        config = MemoryConfig(atomic_root=str(temp_dir))
        assert config.atomic_root == temp_dir
        assert config.memory_head_file.parent.name == ".state"
        assert config.memory_local_dir.parent.name == ".state"

    def test_memory_init(self, atomic_env, temp_dir):
        """Test memory system initialization."""
        # Enable memory
        os.environ["ATOMIC_MEMORY_ENABLED"] = "true"

        memory_init()

        config = get_config()
        assert config.memory_head_file.parent.exists()
        assert config.memory_checkpoints_dir.exists()
        assert config.memory_local_dir.exists()

    def test_memory_should_persist(self, atomic_env, temp_dir):
        """Test memory persistence check."""
        # Memory disabled
        os.environ.pop("ATOMIC_MEMORY_ENABLED", None)
        assert not memory_should_persist()

        # Memory enabled but no phase
        os.environ["ATOMIC_MEMORY_ENABLED"] = "true"
        os.environ.pop("ATOMIC_PHASE", None)
        os.environ.pop("CURRENT_PHASE", None)
        assert not memory_should_persist()

        # Memory enabled with phase
        os.environ["ATOMIC_MEMORY_ENABLED"] = "true"
        os.environ["CURRENT_PHASE"] = "1-discovery"
        assert memory_should_persist()

    def test_memory_head_tracking(self, atomic_env, temp_dir):
        """Test memory head phase tracking."""
        os.environ["ATOMIC_MEMORY_ENABLED"] = "true"
        memory_init()

        # Initial head should be -1
        assert memory_get_head_phase() == -1

        # Set head phase
        memory_set_head_phase(1, "checkpoint-001")
        assert memory_get_head_phase() == 1

        # Update to phase 2
        memory_set_head_phase(2, "checkpoint-002")
        assert memory_get_head_phase() == 2

    def test_memory_checkpoint_creation(self, atomic_env, temp_dir):
        """Test checkpoint creation."""
        os.environ["ATOMIC_MEMORY_ENABLED"] = "true"
        memory_init()

        checkpoint_id = memory_create_checkpoint(
            phase=1,
            phase_name="Discovery",
            summary="Phase 1 completed successfully",
            decisions=[{"key": "value"}],
            artifacts=[{"file": "output.json"}],
        )

        assert checkpoint_id.startswith("phase1-")

        config = get_config()
        checkpoint_file = config.memory_checkpoints_dir / f"{checkpoint_id}.json"
        assert checkpoint_file.exists()

        with open(checkpoint_file) as f:
            data = json.load(f)
        assert data["phase"] == 1
        assert data["phase_name"] == "Discovery"
        assert data["summary"] == "Phase 1 completed successfully"

    def test_memory_check_backtrack(self, atomic_env, temp_dir):
        """Test backtrack detection."""
        os.environ["ATOMIC_MEMORY_ENABLED"] = "true"
        memory_init()

        # Set head to phase 2
        memory_set_head_phase(2, "checkpoint-002")

        # Attempting phase 1 should be a backtrack
        assert memory_check_backtrack(1) is True

        # Attempting phase 3 should not be a backtrack
        assert memory_check_backtrack(3) is False


# ============================================================================
# PHASE.PY TESTS
# ============================================================================


class TestPhase:
    """Test suite for phase.py module."""

    def test_phase_state_init(self):
        """Test PhaseState initialization."""
        state = PhaseState()
        assert state.current_phase == ""
        assert state.phase_tasks_run == 0
        assert state.active_task_id == ""

    def test_phase_manager_init(self, atomic_env, temp_dir):
        """Test PhaseManager initialization."""
        manager = PhaseManager(atomic_root=temp_dir)
        assert manager.atomic_root == temp_dir
        assert manager.output_dir == Path(atomic_env["ATOMIC_OUTPUT_DIR"])

    @patch("phase.atomic_validate_deps", return_value=True)
    @patch("phase.atomic_context_init")
    @patch("phase.task_state_init")
    def test_phase_start(
        self, mock_task_init, mock_context_init, mock_validate, atomic_env, temp_dir
    ):
        """Test phase start."""
        manager = PhaseManager(atomic_root=temp_dir)
        result = manager.phase_start("0-setup", "Project Setup")

        assert result is True
        assert manager.state.current_phase == "0-setup"
        assert manager.state.current_phase_name == "Project Setup"
        assert manager.state.phase_start_time > 0

        # Check that phase output directory was created
        phase_dir = Path(atomic_env["ATOMIC_OUTPUT_DIR"]) / "0-setup"
        assert phase_dir.exists()

    @patch("phase.atomic_context_refresh")
    @patch("phase.atomic_context_artifact")
    @patch("phase.task_state_phase_complete")
    @patch("phase.atomic_state_set")
    def test_phase_complete(
        self,
        mock_state_set,
        mock_task_complete,
        mock_artifact,
        mock_refresh,
        atomic_env,
        temp_dir,
    ):
        """Test phase completion."""
        manager = PhaseManager(atomic_root=temp_dir)
        manager.state.current_phase = "0-setup"
        manager.state.current_phase_name = "Project Setup"
        manager.state.phase_start_time = time.time()
        manager.state.phase_tasks_run = 5

        result = manager.phase_complete()
        assert result is True

        # Check closeout file was created
        closeout_file = Path(atomic_env["ATOMIC_OUTPUT_DIR"]) / "0-setup" / "closeout.json"
        assert closeout_file.exists()

        with open(closeout_file) as f:
            data = json.load(f)
        assert data["phase_id"] == "0-setup"
        assert data["tasks_run"] == 5
        assert data["status"] == "complete"

    def test_phase_snapshot(self, atomic_env, temp_dir):
        """Test phase snapshot creation."""
        manager = PhaseManager(atomic_root=temp_dir)

        # Create some state to snapshot
        state_dir = Path(atomic_env["ATOMIC_STATE_DIR"])
        state_dir.mkdir(parents=True, exist_ok=True)
        session_file = state_dir / "session.json"
        session_file.write_text('{"test": "data"}')

        snapshot_dir = manager.phase_snapshot("0-setup")
        assert snapshot_dir.exists()
        assert (snapshot_dir / "metadata.json").exists()


# ============================================================================
# TASK_STATE.PY TESTS
# ============================================================================


class TestTaskState:
    """Test suite for task_state.py module."""

    def test_task_status_enum(self):
        """Test TaskStatus enum values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETE.value == "complete"
        assert TaskStatus.FAILED.value == "failed"

    def test_task_to_from_dict(self):
        """Test Task serialization."""
        task = Task(
            name="Test Task",
            status=TaskStatus.COMPLETE,
            completed_at="2024-01-01T00:00:00Z",
        )

        # To dict
        data = task.to_dict()
        assert data["name"] == "Test Task"
        assert data["status"] == "complete"
        assert data["completed_at"] == "2024-01-01T00:00:00Z"

        # From dict
        task2 = Task.from_dict(data)
        assert task2.name == "Test Task"
        assert task2.status == TaskStatus.COMPLETE
        assert task2.completed_at == "2024-01-01T00:00:00Z"

    def test_phase_to_from_dict(self):
        """Test Phase serialization."""
        phase = Phase(
            started_at="2024-01-01T00:00:00Z",
            tasks={"001": Task(name="Task 1", status=TaskStatus.COMPLETE)},
            completed=True,
            completed_at="2024-01-01T01:00:00Z",
        )

        # To dict
        data = phase.to_dict()
        assert data["started_at"] == "2024-01-01T00:00:00Z"
        assert "001" in data["tasks"]
        assert data["completed"] is True

        # From dict
        phase2 = Phase.from_dict(data)
        assert phase2.started_at == "2024-01-01T00:00:00Z"
        assert "001" in phase2.tasks
        assert phase2.completed is True

    def test_task_state_manager_init(self, atomic_env, temp_dir):
        """Test TaskStateManager initialization."""
        manager = TaskStateManager(atomic_root=str(temp_dir))
        assert manager.atomic_root == temp_dir
        assert manager.state_file.parent.name == ".claude"

    def test_task_state_init(self, atomic_env, temp_dir):
        """Test task state initialization."""
        manager = TaskStateManager(atomic_root=str(temp_dir))
        manager.task_state_init("1-discovery")

        # Verify state file was created
        assert manager.state_file.exists()

        state = manager._load_state()
        assert state.current_phase == "1-discovery"
        assert "1-discovery" in state.phases

    def test_task_state_complete(self, atomic_env, temp_dir):
        """Test task completion."""
        manager = TaskStateManager(atomic_root=str(temp_dir))
        manager.task_state_init("1-discovery")

        # Start and complete a task
        manager.task_state_start("101", "Requirements Gathering")
        manager.task_state_complete("101", "Requirements Gathering")

        # Verify task is complete
        assert manager.task_state_is_complete("101")

        state = manager._load_state()
        task = state.phases["1-discovery"].tasks["101"]
        assert task.status == TaskStatus.COMPLETE
        assert task.completed_at is not None

    def test_task_state_fail(self, atomic_env, temp_dir):
        """Test task failure."""
        manager = TaskStateManager(atomic_root=str(temp_dir))
        manager.task_state_init("1-discovery")

        manager.task_state_start("101", "Requirements Gathering")
        manager.task_state_fail("101", "Test error")

        state = manager._load_state()
        task = state.phases["1-discovery"].tasks["101"]
        assert task.status == TaskStatus.FAILED
        assert task.error == "Test error"
        assert task.failed_at is not None

    def test_task_state_should_skip(self, atomic_env, temp_dir):
        """Test task skip logic."""
        manager = TaskStateManager(atomic_root=str(temp_dir))
        manager.task_state_init("1-discovery")

        # Not complete - should not skip
        assert not manager.task_state_should_skip("101")

        # Complete task
        manager.task_state_start("101", "Task 1")
        manager.task_state_complete("101", "Task 1")

        # Should skip completed task
        assert manager.task_state_should_skip("101")

        # Force redo - should not skip
        manager.force_redo = True
        assert not manager.task_state_should_skip("101")

    def test_task_state_get_last_complete(self, atomic_env, temp_dir):
        """Test getting last completed task."""
        manager = TaskStateManager(atomic_root=str(temp_dir))
        manager.task_state_init("1-discovery")

        # No tasks completed yet
        assert manager.task_state_get_last_complete() is None

        # Complete some tasks
        for task_id in ["101", "102", "103"]:
            manager.task_state_start(task_id, f"Task {task_id}")
            time.sleep(0.01)  # Ensure different timestamps
            manager.task_state_complete(task_id, f"Task {task_id}")

        # Should return last completed
        assert manager.task_state_get_last_complete() == "103"

    def test_task_state_reset_from(self, atomic_env, temp_dir):
        """Test resetting from specific task."""
        manager = TaskStateManager(atomic_root=str(temp_dir))
        manager.task_state_init("1-discovery")

        # Complete several tasks
        for task_id in ["101", "102", "103", "104"]:
            manager.task_state_start(task_id, f"Task {task_id}")
            manager.task_state_complete(task_id, f"Task {task_id}")

        # Reset from task 103
        manager.task_state_reset_from("103")

        # Tasks 101-102 should still be complete
        assert manager.task_state_is_complete("101")
        assert manager.task_state_is_complete("102")

        # Tasks 103-104 should be pending
        assert not manager.task_state_is_complete("103")
        assert not manager.task_state_is_complete("104")

    def test_task_state_phase_complete(self, atomic_env, temp_dir):
        """Test marking phase as complete."""
        manager = TaskStateManager(atomic_root=str(temp_dir))
        manager.task_state_init("1-discovery")

        manager.task_state_phase_complete()

        state = manager._load_state()
        phase = state.phases["1-discovery"]
        assert phase.completed is True
        assert phase.completed_at is not None


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestIntegration:
    """End-to-end integration tests."""

    def test_full_phase_workflow(self, atomic_env, temp_dir):
        """Test complete phase workflow with state tracking."""
        # Initialize managers
        task_manager = TaskStateManager(atomic_root=str(temp_dir))
        phase_manager = PhaseManager(atomic_root=temp_dir)

        # Start phase
        task_manager.task_state_init("0-setup")

        # Simulate task execution
        task_manager.task_state_start("001", "Mode Selection")
        time.sleep(0.01)
        task_manager.task_state_complete("001", "Mode Selection")

        task_manager.task_state_start("002", "Config Collection")
        time.sleep(0.01)
        task_manager.task_state_complete("002", "Config Collection")

        # Mark phase complete
        task_manager.task_state_phase_complete()

        # Verify state
        state = task_manager._load_state()
        assert state.phases["0-setup"].completed is True
        assert state.phases["0-setup"].tasks["001"].status == TaskStatus.COMPLETE
        assert state.phases["0-setup"].tasks["002"].status == TaskStatus.COMPLETE

    def test_memory_integration_with_phases(self, atomic_env, temp_dir):
        """Test memory system integration with phase tracking."""
        os.environ["ATOMIC_MEMORY_ENABLED"] = "true"
        memory_init()

        # Create checkpoint for phase 0
        checkpoint_id = memory_create_checkpoint(
            phase=0,
            phase_name="Setup",
            summary="Setup completed",
        )

        # Verify checkpoint
        config = get_config()
        checkpoint_file = config.memory_checkpoints_dir / f"{checkpoint_id}.json"
        assert checkpoint_file.exists()

        # Verify head tracking
        assert memory_get_head_phase() == 0

    def test_resume_workflow(self, atomic_env, temp_dir):
        """Test resume workflow after interruption."""
        manager = TaskStateManager(atomic_root=str(temp_dir))
        manager.task_state_init("1-discovery")

        # Complete first two tasks
        for task_id in ["101", "102"]:
            manager.task_state_start(task_id, f"Task {task_id}")
            manager.task_state_complete(task_id, f"Task {task_id}")

        # Simulate interruption - task 103 started but not completed
        manager.task_state_start("103", "Task 103")

        # Reinitialize (simulating new session)
        manager2 = TaskStateManager(atomic_root=str(temp_dir))
        manager2.task_state_init("1-discovery")

        # Check resume point
        last_complete = manager2.task_state_get_last_complete()
        assert last_complete == "102"

        # Completed tasks should be skipped
        assert manager2.task_state_should_skip("101")
        assert manager2.task_state_should_skip("102")

        # Incomplete task should not be skipped
        assert not manager2.task_state_should_skip("103")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
