"""
pytest configuration and shared fixtures
"""

import os
import sys
from pathlib import Path

import pytest

# Add lib directory to path for all tests
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))


@pytest.fixture(autouse=True)
def reset_globals():
    """Reset global state between tests."""
    # Clear module-level state
    from atomic import _ATOMIC_TEMP_FILES

    _ATOMIC_TEMP_FILES.clear()

    yield

    # Cleanup after test
    _ATOMIC_TEMP_FILES.clear()


@pytest.fixture(autouse=True)
def isolate_environment(monkeypatch):
    """Isolate environment variables for each test."""
    # Store original environment
    original_env = os.environ.copy()

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
