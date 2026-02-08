"""
Subprocess Runner Module

Executes bash task scripts from Python orchestrators with proper environment setup.

This is the bridge between Python orchestration (orchestratorNN.py) and
bash task scripts (taskNNN.sh).
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple
import signal
import tempfile


def get_task_environment(phase_id: str, task_id: str) -> Dict[str, str]:
    """
    Build complete environment dictionary for task execution.

    Args:
        phase_id: Phase identifier (e.g., "0-setup", "2-prd")
        task_id: Task identifier (e.g., "001", "205")

    Returns:
        Dict of environment variables
    """
    # Get atomic-claude2 root
    atomic_root = Path(__file__).parent.parent.resolve()

    # Start with current environment
    env = os.environ.copy()

    # Core paths
    env["ATOMIC_ROOT"] = str(atomic_root)
    env["ROOT_DIR"] = str(atomic_root)  # Alias for legacy scripts
    env["ATOMIC_OUTPUT_DIR"] = str(atomic_root / ".outputs")
    env["ATOMIC_STATE_DIR"] = str(atomic_root / ".state")
    env["ATOMIC_LOG_DIR"] = str(atomic_root / ".logs")

    # Phase/task context
    env["CURRENT_PHASE"] = phase_id
    env["CURRENT_TASK_ID"] = task_id

    # Provider configuration (from environment or defaults)
    env.setdefault("CLAUDE_PROVIDER", "max")
    env.setdefault("CLAUDE_MODEL", "sonnet")
    env.setdefault("CLAUDE_MAX_TURNS", "30")
    env.setdefault("CLAUDE_TIMEOUT", "1200")

    # Ollama configuration
    env.setdefault("CLAUDE_OLLAMA_HOST", "http://localhost:11434")
    env.setdefault("CLAUDE_OLLAMA_CONTEXT", "65536")

    # Dashboard ports
    env.setdefault("ATOMIC_TASKS_PORT", "5174")  # Tasks dashboard
    env.setdefault("ATOMIC_AGENTS_PORT", "5175")  # Agents dashboard (future)
    env.setdefault("ATOMIC_AUDITS_PORT", "5176")  # Audits dashboard (future)

    # Network mode
    env.setdefault("ATOMIC_NETWORK_MODE", "cui")

    # Agent/Audit repos (if they exist)
    agent_repo = atomic_root / "agents"
    if agent_repo.exists():
        env["ATOMIC_AGENT_REPO"] = str(agent_repo)
    else:
        # Try parent directory (might be symlinked)
        parent_agent = atomic_root.parent / "atomic-claude" / "agents"
        if parent_agent.exists():
            env["ATOMIC_AGENT_REPO"] = str(parent_agent)

    audit_repo = atomic_root / "audits"
    if audit_repo.exists():
        env["ATOMIC_AUDIT_REPO"] = str(audit_repo)
    else:
        # Try parent directory (might be symlinked)
        parent_audit = atomic_root.parent / "atomic-claude" / "audits"
        if parent_audit.exists():
            env["ATOMIC_AUDIT_REPO"] = str(parent_audit)

    # Lib directory (for sourcing bash functions)
    # Point to original atomic-claude lib/ for now
    lib_dir = atomic_root / "lib"
    if not lib_dir.exists():
        # Use parent atomic-claude lib
        parent_lib = atomic_root.parent / "atomic-claude" / "lib"
        if parent_lib.exists():
            env["ATOMIC_LIB_DIR"] = str(parent_lib)
    else:
        env["ATOMIC_LIB_DIR"] = str(lib_dir)

    return env


def run_task_script(
    script_path: Path,
    phase_id: str,
    task_id: str,
    timeout: int = 600,
    capture_output: bool = True
) -> Tuple[int, str, str]:
    """
    Execute a bash task script with proper environment.

    Args:
        script_path: Path to the bash script to execute
        phase_id: Phase identifier (e.g., "0-setup")
        task_id: Task identifier (e.g., "001")
        timeout: Timeout in seconds (default: 600 = 10 minutes)
        capture_output: Whether to capture stdout/stderr (default: True)

    Returns:
        Tuple of (exit_code, stdout, stderr)

    Raises:
        FileNotFoundError: If script doesn't exist
        subprocess.TimeoutExpired: If script times out
    """
    if not script_path.exists():
        raise FileNotFoundError(f"Task script not found: {script_path}")

    # Build environment
    env = get_task_environment(phase_id, task_id)

    # Get atomic-claude2 root for working directory
    atomic_root = Path(__file__).parent.parent.resolve()

    # Determine stdout/stderr handling
    if capture_output:
        stdout = subprocess.PIPE
        stderr = subprocess.PIPE
    else:
        stdout = None
        stderr = None

    print(f"  🔧 Executing: {script_path.name}")

    try:
        # Execute script with bash
        result = subprocess.run(
            ["bash", str(script_path)],
            cwd=atomic_root,  # Run from atomic-claude2 root
            env=env,
            stdout=stdout,
            stderr=stderr,
            timeout=timeout,
            text=True
        )

        stdout_text = result.stdout or ""
        stderr_text = result.stderr or ""

        return result.returncode, stdout_text, stderr_text

    except subprocess.TimeoutExpired as e:
        stdout_text = e.stdout.decode() if e.stdout else ""
        stderr_text = e.stderr.decode() if e.stderr else ""
        print(f"  ⚠️  Task {task_id} timed out after {timeout}s")
        return 124, stdout_text, stderr_text

    except Exception as e:
        print(f"  ❌ Task {task_id} error: {e}")
        return 1, "", str(e)


def run_task_script_streaming(
    script_path: Path,
    phase_id: str,
    task_id: str,
    timeout: int = 600
) -> int:
    """
    Execute a bash task script with real-time output streaming.

    This version streams output to console in real-time (no capture).
    Use this for tasks that produce lots of output.

    Args:
        script_path: Path to the bash script to execute
        phase_id: Phase identifier
        task_id: Task identifier
        timeout: Timeout in seconds

    Returns:
        Exit code

    Raises:
        FileNotFoundError: If script doesn't exist
        subprocess.TimeoutExpired: If script times out
    """
    if not script_path.exists():
        raise FileNotFoundError(f"Task script not found: {script_path}")

    # Build environment
    env = get_task_environment(phase_id, task_id)

    # Get atomic-claude2 root for working directory
    atomic_root = Path(__file__).parent.parent.resolve()

    print(f"  🔧 Executing: {script_path.name}")

    try:
        # Execute script with bash, inherit stdout/stderr
        result = subprocess.run(
            ["bash", str(script_path)],
            cwd=atomic_root,
            env=env,
            timeout=timeout
        )

        return result.returncode

    except subprocess.TimeoutExpired:
        print(f"  ⚠️  Task {task_id} timed out after {timeout}s")
        return 124

    except Exception as e:
        print(f"  ❌ Task {task_id} error: {e}")
        return 1


def run_bash_command(
    command: str,
    phase_id: str,
    task_id: str,
    timeout: int = 60,
    capture_output: bool = True
) -> Tuple[int, str, str]:
    """
    Execute a single bash command (not a script file).

    Args:
        command: Bash command to execute
        phase_id: Phase identifier
        task_id: Task identifier
        timeout: Timeout in seconds
        capture_output: Whether to capture stdout/stderr

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    # Build environment
    env = get_task_environment(phase_id, task_id)

    # Get atomic-claude2 root for working directory
    atomic_root = Path(__file__).parent.parent.resolve()

    # Determine stdout/stderr handling
    if capture_output:
        stdout = subprocess.PIPE
        stderr = subprocess.PIPE
    else:
        stdout = None
        stderr = None

    try:
        result = subprocess.run(
            ["bash", "-c", command],
            cwd=atomic_root,
            env=env,
            stdout=stdout,
            stderr=stderr,
            timeout=timeout,
            text=True
        )

        stdout_text = result.stdout or ""
        stderr_text = result.stderr or ""

        return result.returncode, stdout_text, stderr_text

    except subprocess.TimeoutExpired as e:
        stdout_text = e.stdout.decode() if e.stdout else ""
        stderr_text = e.stderr.decode() if e.stderr else ""
        return 124, stdout_text, stderr_text

    except Exception as e:
        return 1, "", str(e)


def validate_script_exists(script_path: Path) -> bool:
    """
    Check if a task script exists and is executable.

    Args:
        script_path: Path to script

    Returns:
        True if script exists and is readable
    """
    if not script_path.exists():
        return False

    if not script_path.is_file():
        return False

    # Check if readable
    if not os.access(script_path, os.R_OK):
        return False

    return True


def make_script_executable(script_path: Path) -> bool:
    """
    Make a script executable (chmod +x).

    Args:
        script_path: Path to script

    Returns:
        True if successful
    """
    try:
        import stat
        current_permissions = script_path.stat().st_mode
        script_path.chmod(current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return True
    except Exception:
        return False


# ============================================================================
# HELPER: Source bash library functions (for future use)
# ============================================================================

def source_bash_library(lib_path: Path) -> Dict[str, str]:
    """
    Source a bash library and extract function definitions.

    This is for future use if we need to call bash functions directly.

    Args:
        lib_path: Path to bash library file

    Returns:
        Dict of exported variables/functions

    Note:
        This is a placeholder for future implementation.
        Currently, bash task scripts source lib files themselves.
    """
    # TODO: Implement if needed
    # For now, bash scripts will source their own libraries
    pass


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    # Test environment building
    print("Testing subprocess_runner module...\n")

    env = get_task_environment("0-setup", "001")

    print("Environment variables set:")
    for key in ["ATOMIC_ROOT", "ATOMIC_OUTPUT_DIR", "ATOMIC_STATE_DIR",
                "CURRENT_PHASE", "CURRENT_TASK_ID", "CLAUDE_PROVIDER"]:
        print(f"  {key} = {env.get(key)}")

    print("\n✓ subprocess_runner module ready")
