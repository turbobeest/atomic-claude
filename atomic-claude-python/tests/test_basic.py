#!/usr/bin/env python3
"""
Basic smoke tests for Python implementation
"""
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test all modules import successfully."""
    from lib import atomic, provider, memory, phase, task_state
    assert atomic is not None
    assert provider is not None
    assert memory is not None
    assert phase is not None
    assert task_state is not None
    print("✅ All imports successful")

def test_atomic_functions():
    """Test atomic.py basic functions exist."""
    from lib.atomic import (
        atomic_step, atomic_success, atomic_error, atomic_info,
        atomic_h1, atomic_h2, atomic_invoke
    )
    assert callable(atomic_step)
    assert callable(atomic_success)
    assert callable(atomic_error)
    assert callable(atomic_info)
    assert callable(atomic_h1)
    assert callable(atomic_h2)
    assert callable(atomic_invoke)
    print("✅ All atomic functions exist")

def test_provider_manager():
    """Test ProviderManager can be instantiated."""
    from lib.provider import ProviderManager
    mgr = ProviderManager()
    assert mgr is not None
    assert hasattr(mgr, 'check_anthropic')
    assert hasattr(mgr, 'init')
    print("✅ ProviderManager works")

def test_memory_functions():
    """Test memory module functions exist."""
    from lib.memory import memory_init, memory_session_start, memory_task_start
    assert callable(memory_init)
    assert callable(memory_session_start)
    assert callable(memory_task_start)
    print("✅ Memory functions exist")

def test_phase_functions():
    """Test phase module functions exist."""
    from lib.phase import phase_start, phase_complete
    assert callable(phase_start)
    assert callable(phase_complete)
    print("✅ Phase functions exist")

def test_task_state_functions():
    """Test task_state module functions exist."""
    from lib.task_state import task_state_init, task_state_complete
    assert callable(task_state_init)
    assert callable(task_state_complete)
    print("✅ Task state functions exist")

if __name__ == "__main__":
    print("\n🧪 Running basic smoke tests...\n")
    test_imports()
    test_atomic_functions()
    test_provider_manager()
    test_memory_functions()
    test_phase_functions()
    test_task_state_functions()
    print("\n✅ All basic tests passed!\n")
