"""
Memory Module

Provides persistent memory storage across phases and sessions.
Currently wraps memory.sh bash functions via subprocess.

TODO: Convert to pure Python implementation later (Phase 0/1 don't need it heavily)
"""

import subprocess
import os
from pathlib import Path
from typing import Optional, List, Dict, Any


def _get_memory_script() -> Path:
    """Get path to memory.sh in parent atomic-claude directory."""
    atomic_root = Path(__file__).parent.parent.resolve()

    # Try parent directory first
    parent_memory = atomic_root.parent / "atomic-claude" / "lib" / "memory.sh"
    if parent_memory.exists():
        return parent_memory

    # Try local lib directory (if we copy it later)
    local_memory = atomic_root / "lib" / "memory.sh"
    if local_memory.exists():
        return local_memory

    raise FileNotFoundError("memory.sh not found (expected in ../atomic-claude/lib/)")


def _call_memory_function(func_name: str, *args: str) -> tuple[int, str, str]:
    """
    Call a bash memory function via subprocess.

    Args:
        func_name: Name of memory function (e.g., "memory_init")
        *args: Arguments to pass to the function

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    try:
        memory_script = _get_memory_script()
    except FileNotFoundError:
        # Memory system not available - fail gracefully
        return (1, "", "memory.sh not found")

    # Build environment
    atomic_root = Path(__file__).parent.parent.resolve()
    env = os.environ.copy()
    env["ATOMIC_ROOT"] = str(atomic_root)
    env["ATOMIC_STATE_DIR"] = str(atomic_root / ".state")
    env["ATOMIC_OUTPUT_DIR"] = str(atomic_root.parent / ".outputs")

    # Build command: source memory.sh, then call function
    args_str = " ".join(f'"{arg}"' for arg in args)
    command = f'source "{memory_script}" && {func_name} {args_str}'

    try:
        result = subprocess.run(
            ["bash", "-c", command],
            cwd=atomic_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            text=True
        )
        return (result.returncode, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return (124, "", "Memory function timed out")
    except Exception as e:
        return (1, "", str(e))


# ============================================================================
# Public API - Memory Lifecycle
# ============================================================================

def memory_init() -> bool:
    """
    Initialize memory system.

    Returns:
        True if successful
    """
    exit_code, _, _ = _call_memory_function("memory_init")
    return exit_code == 0


def memory_should_persist() -> bool:
    """
    Check if memory persistence is enabled.

    Returns:
        True if memory should be persisted
    """
    exit_code, _, _ = _call_memory_function("memory_should_persist")
    return exit_code == 0


def memory_has_remote() -> bool:
    """
    Check if remote memory (claude-mem) is configured.

    Returns:
        True if remote memory available
    """
    exit_code, _, _ = _call_memory_function("memory_has_remote")
    return exit_code == 0


# ============================================================================
# Public API - Phase Tracking
# ============================================================================

def memory_get_head_phase() -> Optional[str]:
    """
    Get the current head phase (last phase executed).

    Returns:
        Phase ID (e.g., "2-prd") or None if not set
    """
    exit_code, stdout, _ = _call_memory_function("memory_get_head_phase")
    if exit_code == 0 and stdout.strip():
        return stdout.strip()
    return None


def memory_set_head_phase(phase_id: str) -> bool:
    """
    Set the current head phase.

    Args:
        phase_id: Phase identifier (e.g., "0-setup", "2-prd")

    Returns:
        True if successful
    """
    exit_code, _, _ = _call_memory_function("memory_set_head_phase", phase_id)
    return exit_code == 0


# ============================================================================
# Public API - Checkpoints & Backtracking
# ============================================================================

def memory_add_checkpoint(phase_id: str, checkpoint_type: str, description: str) -> bool:
    """
    Add a checkpoint marker.

    Args:
        phase_id: Phase identifier
        checkpoint_type: Type of checkpoint (e.g., "phase_complete")
        description: Human-readable description

    Returns:
        True if successful
    """
    exit_code, _, _ = _call_memory_function(
        "memory_add_checkpoint", phase_id, checkpoint_type, description
    )
    return exit_code == 0


def memory_check_backtrack(target_phase: str) -> bool:
    """
    Check if we're backtracking to an earlier phase.

    Args:
        target_phase: Phase we're about to run

    Returns:
        True if backtracking detected (target < head)
    """
    exit_code, _, _ = _call_memory_function("memory_check_backtrack", target_phase)
    return exit_code == 0


def memory_handle_backtrack(target_phase: str) -> bool:
    """
    Handle backtracking (clear state ahead of target phase).

    Args:
        target_phase: Phase we're backtracking to

    Returns:
        True if successful
    """
    exit_code, _, _ = _call_memory_function("memory_handle_backtrack", target_phase)
    return exit_code == 0


def memory_create_checkpoint(phase_id: str, content: str, user_approved: bool = False) -> bool:
    """
    Create a phase checkpoint with content.

    Args:
        phase_id: Phase identifier
        content: Checkpoint content (summary)
        user_approved: Whether user approved this checkpoint

    Returns:
        True if successful
    """
    approval_flag = "1" if user_approved else "0"
    exit_code, _, _ = _call_memory_function(
        "memory_create_checkpoint", phase_id, content, approval_flag
    )
    return exit_code == 0


def memory_prompt_save(phase_num: int, phase_name: str, summary: str) -> bool:
    """
    Prompt user to save phase summary to memory.

    Args:
        phase_num: Phase number (0-9)
        phase_name: Phase name (e.g., "Setup")
        summary: Summary content

    Returns:
        True if saved
    """
    exit_code, _, _ = _call_memory_function(
        "memory_prompt_save", str(phase_num), phase_name, summary
    )
    return exit_code == 0


# ============================================================================
# Public API - Task Lifecycle
# ============================================================================

def memory_task_start(phase_id: str, task_id: str, task_name: str) -> bool:
    """
    Mark task as started (for memory tracking).

    Args:
        phase_id: Phase identifier
        task_id: Task identifier
        task_name: Task name

    Returns:
        True if successful
    """
    exit_code, _, _ = _call_memory_function(
        "memory_task_start", phase_id, task_id, task_name
    )
    return exit_code == 0


def memory_task_end(phase_id: str, task_id: str, success: bool = True) -> bool:
    """
    Mark task as ended (save outputs to memory if configured).

    Args:
        phase_id: Phase identifier
        task_id: Task identifier
        success: Whether task succeeded

    Returns:
        True if successful
    """
    status = "success" if success else "failed"
    exit_code, _, _ = _call_memory_function(
        "memory_task_end", phase_id, task_id, status
    )
    return exit_code == 0


# ============================================================================
# Public API - Session Lifecycle
# ============================================================================

def memory_session_start() -> Optional[str]:
    """
    Start memory session (recall context if available).

    Returns:
        Recalled context or None
    """
    exit_code, stdout, _ = _call_memory_function("memory_session_start")
    if exit_code == 0 and stdout.strip():
        return stdout.strip()
    return None


def memory_session_end() -> bool:
    """
    End memory session (cleanup).

    Returns:
        True if successful
    """
    exit_code, _, _ = _call_memory_function("memory_session_end")
    return exit_code == 0


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("Testing memory module...\n")

    try:
        script = _get_memory_script()
        print(f"✓ Found memory.sh: {script}")
    except FileNotFoundError as e:
        print(f"✗ {e}")
        exit(1)

    print("\n✓ memory.py module ready (wraps memory.sh via subprocess)")
