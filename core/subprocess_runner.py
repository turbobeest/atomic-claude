"""
Subprocess Runner Module

Executes external scripts and commands from Python orchestrators with proper environment setup.
"""

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def get_task_environment(phase_id: str, task_id: str) -> Dict[str, str]:
    """
    Build complete environment dictionary for task execution.

    Args:
        phase_id: Phase identifier (e.g., "0-setup", "2-prd")
        task_id: Task identifier (e.g., "001", "205")

    Returns:
        Dict of environment variables
    """
    # Get atomic-claude root
    atomic_root = Path(__file__).parent.parent.resolve()

    # Start with current environment
    env = os.environ.copy()

    # Core paths
    env["ATOMIC_ROOT"] = str(atomic_root)
    env["ATOMIC_OUTPUT_DIR"] = str(atomic_root.parent / ".outputs")
    env["ATOMIC_STATE_DIR"] = str(atomic_root / ".state")
    env["ATOMIC_LOG_DIR"] = str(atomic_root / ".logs")

    # Phase/task context
    env["CURRENT_PHASE"] = phase_id
    env["CURRENT_TASK_ID"] = task_id

    # Dashboard ports
    env.setdefault("ATOMIC_TASKS_PORT", "5174")
    env.setdefault("ATOMIC_AGENTS_PORT", "5175")
    env.setdefault("ATOMIC_AUDITS_PORT", "5176")

    # Network mode
    env.setdefault("ATOMIC_NETWORK_MODE", "cui")

    # Agent/Audit repos (if they exist)
    agent_repo = atomic_root / "agents"
    if agent_repo.exists():
        env["ATOMIC_AGENT_REPO"] = str(agent_repo)

    audit_repo = atomic_root / "audits"
    if audit_repo.exists():
        env["ATOMIC_AUDIT_REPO"] = str(audit_repo)

    return env


def run_task_script(
    script_path: Path,
    phase_id: str,
    task_id: str,
    timeout: int = 600,
    capture_output: bool = True
) -> Tuple[int, str, str]:
    """
    Execute a script with proper environment.

    Args:
        script_path: Path to the script to execute
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

    # Get atomic-claude root for working directory
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
        result = subprocess.run(
            ["bash", str(script_path)],
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
        stdout_text = (e.stdout or "") if isinstance(e.stdout, str) else (e.stdout.decode() if e.stdout else "")
        stderr_text = (e.stderr or "") if isinstance(e.stderr, str) else (e.stderr.decode() if e.stderr else "")
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
    Execute a script with real-time output streaming.

    Args:
        script_path: Path to the script to execute
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

    # Get atomic-claude root for working directory
    atomic_root = Path(__file__).parent.parent.resolve()

    print(f"  🔧 Executing: {script_path.name}")

    try:
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
    env = get_task_environment(phase_id, task_id)
    atomic_root = Path(__file__).parent.parent.resolve()

    if capture_output:
        stdout = subprocess.PIPE
        stderr = subprocess.PIPE
    else:
        stdout = None
        stderr = None

    # SECURITY: command is passed directly to bash -c. Only call this function
    # with trusted input. Never pass unsanitized user input as the command string.
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
        stdout_text = (e.stdout or "") if isinstance(e.stdout, str) else (e.stdout.decode() if e.stdout else "")
        stderr_text = (e.stderr or "") if isinstance(e.stderr, str) else (e.stderr.decode() if e.stderr else "")
        return 124, stdout_text, stderr_text

    except Exception as e:
        return 1, "", str(e)


def validate_script_exists(script_path: Path) -> bool:
    """Check if a script exists and is readable."""
    return script_path.is_file() and os.access(script_path, os.R_OK)


def make_script_executable(script_path: Path) -> bool:
    """Make a script executable (chmod +x)."""
    try:
        import stat
        current_permissions = script_path.stat().st_mode
        script_path.chmod(current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return True
    except Exception as e:
        logger.debug("Failed to make script executable at %s: %s", script_path, e)
        return False
