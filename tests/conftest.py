"""
Pytest Configuration and Fixtures

Provides shared fixtures and configuration for atomic-claude tests.
"""

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Generator
import pytest


# ============================================================================
# Test Environment Setup
# ============================================================================

@pytest.fixture(scope="session")
def atomic_root() -> Path:
    """Get the atomic-claude root directory."""
    return Path(__file__).parent.parent.resolve()


@pytest.fixture(scope="session")
def test_root() -> Path:
    """Get the tests directory."""
    return Path(__file__).parent.resolve()


# ============================================================================
# Temporary Directory Fixtures
# ============================================================================

@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """
    Create a temporary directory for test isolation.

    Yields:
        Path to temporary directory (cleaned up after test)
    """
    temp_path = Path(tempfile.mkdtemp())
    try:
        yield temp_path
    finally:
        if temp_path.exists():
            shutil.rmtree(temp_path)


@pytest.fixture
def temp_state_dir(temp_dir: Path) -> Path:
    """
    Create a temporary .state directory.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Path to temporary state directory
    """
    state_dir = temp_dir / ".state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


@pytest.fixture
def temp_output_dir(temp_dir: Path) -> Path:
    """
    Create a temporary .outputs directory.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Path to temporary outputs directory
    """
    output_dir = temp_dir / ".outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@pytest.fixture
def temp_log_dir(temp_dir: Path) -> Path:
    """
    Create a temporary .logs directory.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Path to temporary logs directory
    """
    log_dir = temp_dir / ".logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


# ============================================================================
# State Management Fixtures
# ============================================================================

@pytest.fixture
def clean_state(temp_state_dir: Path) -> Dict:
    """
    Provide a clean state dictionary.

    Returns:
        Empty state dictionary
    """
    return {"phases": {}}


@pytest.fixture
def sample_state() -> Dict:
    """
    Provide a sample state with completed tasks.

    Returns:
        Sample state dictionary
    """
    return {
        "phases": {
            "0-setup": {
                "started": "2026-02-06T10:00:00",
                "completed": "2026-02-06T10:15:00",
                "tasks": {
                    "001": {"name": "Mode selection", "status": "completed"},
                    "002": {"name": "Config collection", "status": "completed"},
                    "003": {"name": "Config display", "status": "completed"}
                }
            }
        },
        "current_phase": "0-setup"
    }


@pytest.fixture
def state_file(temp_state_dir: Path, clean_state: Dict) -> Path:
    """
    Create a state file for testing.

    Args:
        temp_state_dir: Temporary state directory
        clean_state: Clean state dictionary

    Returns:
        Path to state file
    """
    state_file = temp_state_dir / "task-state.json"
    with open(state_file, "w") as f:
        json.dump(clean_state, f, indent=2)
    return state_file


# ============================================================================
# Mock LLM Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_response() -> str:
    """
    Provide a mock LLM response.

    Returns:
        Sample LLM response text
    """
    return """
    # Analysis Complete

    This is a mock LLM response for testing purposes.

    ## Summary
    - Item 1: Complete
    - Item 2: Complete
    - Item 3: Complete

    ## Recommendations
    All tasks completed successfully.
    """


@pytest.fixture
def mock_llm_json_response() -> Dict:
    """
    Provide a mock LLM JSON response.

    Returns:
        Sample JSON response
    """
    return {
        "status": "success",
        "analysis": {
            "findings": ["Finding 1", "Finding 2", "Finding 3"],
            "recommendations": ["Recommendation 1", "Recommendation 2"]
        },
        "confidence": 0.95
    }


@pytest.fixture
def mock_llm_environment() -> Generator[Dict[str, str], None, None]:
    """
    Set up environment for mocked LLM calls.

    Yields:
        Dict of environment variables set
    """
    env_backup = {}
    mock_vars = {
        "ATOMIC_TEST_MODE": "1",
        "ATOMIC_MOCK_LLM": "1",
        "CLAUDE_PROVIDER": "mock",
    }

    # Backup and set
    for key, value in mock_vars.items():
        env_backup[key] = os.environ.get(key)
        os.environ[key] = value

    try:
        yield mock_vars
    finally:
        # Restore
        for key, value in env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def sample_config() -> Dict:
    """
    Provide a sample configuration.

    Returns:
        Sample configuration dictionary
    """
    return {
        "project": {
            "name": "test-project",
            "directory": "/tmp/test-project",
            "description": "Test project for atomic-claude"
        },
        "provider": {
            "name": "anthropic",
            "model": "claude-sonnet-4",
            "max_turns": 30,
            "timeout": 1200
        },
        "mode": "quick"
    }


@pytest.fixture
def config_file(temp_dir: Path, sample_config: Dict) -> Path:
    """
    Create a configuration file.

    Args:
        temp_dir: Temporary directory
        sample_config: Sample configuration

    Returns:
        Path to config file
    """
    config_file = temp_dir / "config.json"
    with open(config_file, "w") as f:
        json.dump(sample_config, f, indent=2)
    return config_file


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_task_script(temp_dir: Path) -> Path:
    """
    Create a sample task script for testing.

    Args:
        temp_dir: Temporary directory

    Returns:
        Path to task script
    """
    script = temp_dir / "task001.sh"
    script.write_text("""#!/usr/bin/env bash
# Test task script

echo "Task 001: Test"
echo "Task executing..."
exit 0
""")
    script.chmod(0o755)
    return script


@pytest.fixture
def failing_task_script(temp_dir: Path) -> Path:
    """
    Create a task script that fails.

    Args:
        temp_dir: Temporary directory

    Returns:
        Path to failing task script
    """
    script = temp_dir / "task_fail.sh"
    script.write_text("""#!/usr/bin/env bash
# Failing task script

echo "Task failed!" >&2
exit 1
""")
    script.chmod(0o755)
    return script


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_test_artifacts():
    """
    Auto-cleanup test artifacts after each test.

    This fixture runs automatically for every test.
    """
    yield  # Run test

    # Cleanup after test
    test_artifacts = [
        ".test-state",
        ".test-outputs",
        ".test-logs",
        "test-config.json",
    ]

    for artifact in test_artifacts:
        artifact_path = Path(artifact)
        if artifact_path.exists():
            if artifact_path.is_dir():
                shutil.rmtree(artifact_path)
            else:
                artifact_path.unlink()


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """
    Pytest configuration hook.

    Args:
        config: Pytest config object
    """
    # Register custom markers
    config.addinivalue_line(
        "markers",
        "unit: Unit tests (fast, isolated)"
    )
    config.addinivalue_line(
        "markers",
        "integration: Integration tests (multi-module)"
    )
    config.addinivalue_line(
        "markers",
        "e2e: End-to-end tests (full phase runs)"
    )
    config.addinivalue_line(
        "markers",
        "slow: Slow tests (may timeout)"
    )
    config.addinivalue_line(
        "markers",
        "requires_llm: Tests that require real LLM access"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection.

    Args:
        config: Pytest config
        items: Test items
    """
    # Skip tests requiring LLM if ATOMIC_TEST_MODE is set
    if os.environ.get("ATOMIC_TEST_MODE") == "1":
        skip_llm = pytest.mark.skip(reason="Skipping LLM tests in test mode")
        for item in items:
            if "requires_llm" in item.keywords:
                item.add_marker(skip_llm)
