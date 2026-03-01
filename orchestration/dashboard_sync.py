"""
Dashboard Sync Module

Validates state files and ensures dashboard shows accurate information.
Triggers dashboard refresh after task completion.
Writes current-task.json, session-tokens.json, and errors.json for dashboard consumption.
"""

import json
import logging
import os
import sys
import tempfile
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

try:
    import fcntl
    _HAS_FCNTL = True
except ImportError:
    _HAS_FCNTL = False

logger = logging.getLogger(__name__)


try:
    import requests
except ImportError:
    requests = None


def _get_state_dir(atomic_root: Optional[Path] = None) -> Path:
    """Return the .state directory, resolving atomic_root from env if needed."""
    if atomic_root is None:
        atomic_root = Path(os.environ.get("ATOMIC_ROOT", "."))
    return Path(atomic_root) / ".state"


@contextmanager
def _locked_file(filepath: Path, mode: str = "r+"):
    """Context manager providing exclusive file locking.

    Uses fcntl.flock on Unix, msvcrt.locking on Windows.

    Args:
        filepath: Path to the file to lock
        mode: File open mode ('r+' for read-modify-write, 'w' for write)
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    # Ensure file exists for r+ mode
    if "r" in mode and not filepath.exists():
        filepath.write_text("{}")
    fh = open(filepath, mode)
    try:
        try:
            if _HAS_FCNTL:
                fcntl.flock(fh, fcntl.LOCK_EX)
            elif sys.platform == 'win32':
                import msvcrt
                msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 2**20)
        except OSError as e:
            raise OSError(f"Failed to acquire lock on {filepath}: {e}") from e
        fh.seek(0)
        yield fh
    finally:
        if _HAS_FCNTL:
            fcntl.flock(fh, fcntl.LOCK_UN)
        elif sys.platform == 'win32':
            import msvcrt
            try:
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 2**20)
            except OSError:
                pass  # Unlock failure on Windows is non-fatal; file handle close releases it
        fh.close()


def write_current_task(phase_id: str, task_id: str, task_name: str,
                       resolved=None, provider: str = None, model: str = None,
                       agent_roster=None, atomic_root: Optional[Path] = None):
    """Write current-task.json for dashboard status display.

    Args:
        phase_id: Phase identifier (e.g. "0-setup")
        task_id: Task identifier (e.g. "001")
        task_name: Human-readable task name
        resolved: Optional ResolvedModel from core.llm.resolver
        provider: Optional provider override (fallback if no resolved)
        model: Optional model tier override (fallback if no resolved)
        agent_roster: Optional list of (AgentEntry, ResolvedModel) tuples
        atomic_root: Optional project root (defaults to ATOMIC_ROOT env or cwd)
    """
    state_dir = _get_state_dir(atomic_root)
    state_dir.mkdir(parents=True, exist_ok=True)

    effort_level = None

    tier = None
    source = None
    extended_thinking = None
    thinking_budget = None

    if resolved is not None:
        provider = resolved.provider
        model = resolved.model_id
        phase_weight = resolved.role
        context_window = resolved.context_window
        max_output = resolved.max_output
        effort_level = resolved.effort_level
        tier = resolved.tier
        source = resolved.source
        extended_thinking = resolved.extended_thinking
        thinking_budget = resolved.thinking_budget
    elif provider is None or model is None:
        cfg_provider, cfg_model = _resolve_phase_model(phase_id)
        provider = provider or cfg_provider
        model = model or cfg_model
        context_window, max_output = _get_model_limits(model)
        phase_weight = None
    else:
        context_window, max_output = _get_model_limits(model)
        phase_weight = None

    data = {
        "active": True,
        "phase": phase_id,
        "task": task_id,
        "description": task_name,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "model": model,
        "tier": tier,
        "source": source,
        "phase_weight": phase_weight,
        "effort_level": effort_level,
        "extended_thinking": extended_thinking,
        "thinking_budget": thinking_budget,
        "online": provider is not None,
        "context_window": context_window,
        "max_output": max_output,
    }

    # Add agent roster if provided
    if agent_roster:
        data["agents"] = [
            {
                "name": entry.name,
                "label": entry.label,
                "provider": rm.provider,
                "model": rm.model_id,
                "tier": rm.tier,
                "source": rm.source,
                "context_window": rm.context_window,
                "effort_level": rm.effort_level,
            }
            for entry, rm in agent_roster
            if entry.name != "\u2014"  # Skip placeholder entries
        ]

    # Atomic write: temp file + os.replace to prevent corrupt JSON on crash
    target = state_dir / "current-task.json"
    fd, tmp = tempfile.mkstemp(dir=state_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, target)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def update_current_task_provider(provider: str, model: str = None,
                                 phase_id: str = None,
                                 atomic_root: Optional[Path] = None):
    """Update provider/model in current-task.json without replacing other fields.

    Called by task_001 once credentials are detected, before config exists.
    Uses file locking to prevent concurrent access corruption.
    """
    ct = _get_state_dir(atomic_root) / "current-task.json"
    if not ct.exists():
        return
    try:
        with _locked_file(ct, "r+") as fh:
            content = fh.read()
            data = json.loads(content)
            data["provider"] = provider
            if model:
                data["model"] = model
            data["online"] = True

            # Use resolver for context_window (respects provider overrides)
            context_window = None
            max_output = None
            if phase_id:
                try:
                    from core.llm.resolver import resolve_model
                    rm = resolve_model(phase_id)
                    context_window = rm.context_window
                    max_output = rm.max_output
                    data["effort_level"] = rm.effort_level
                except Exception as e:
                    logger.debug("Could not resolve model for phase %s: %s", phase_id, e)

            if not context_window:
                context_window, max_output = _get_model_limits(model)

            if context_window:
                data["context_window"] = context_window
            if max_output:
                data["max_output"] = max_output

            fh.seek(0)
            fh.write(json.dumps(data, indent=2))
            fh.truncate()
    except (json.JSONDecodeError, OSError) as e:
        logger.debug("Failed to update current-task.json: %s", e)


def init_session_tokens(atomic_root: Optional[Path] = None):
    """Initialize session-tokens.json at pipeline start so the dashboard has data immediately."""
    state_dir = _get_state_dir(atomic_root)
    state_dir.mkdir(parents=True, exist_ok=True)
    tokens_file = state_dir / "session-tokens.json"
    if not tokens_file.exists():
        from core.utils.file_ops import write_json
        data = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "estimated_cost_usd": 0,
            "by_provider": {},
            "by_model": {},
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        write_json(tokens_file, data)


def _resolve_phase_model(phase_id: str) -> Tuple[Optional[str], Optional[str]]:
    """Resolve the provider and full model ID for a given phase.

    Delegates to core.llm.resolver for the full resolution hierarchy.

    Returns:
        (provider, model_id) tuple, either may be None.
    """
    try:
        from core.llm.resolver import resolve_model
        result = resolve_model(phase_id)
        return result.provider, result.model_id
    except Exception as e:
        logger.debug("Could not resolve phase model for %s: %s", phase_id, e)
        return None, None


def _get_model_limits(model: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    """Look up context window and max output for a model tier."""
    if not model:
        return None, None
    try:
        from core.llm.capabilities import get_model_context_window, get_model_max_output
        return get_model_context_window(model), get_model_max_output(model)
    except ImportError:
        return None, None


def clear_current_task(atomic_root: Optional[Path] = None):
    """Clear current-task.json when task completes.

    Uses atomic write (write empty to temp, rename) instead of direct
    delete to avoid a race with the dashboard reader (Finding #19).
    """
    ct = _get_state_dir(atomic_root) / "current-task.json"
    if ct.exists():
        try:
            # Write empty marker to temp file, then atomically replace
            fd, tmp = tempfile.mkstemp(dir=ct.parent, suffix=".tmp")
            os.write(fd, b'{"active": false}')
            os.close(fd)
            os.replace(tmp, ct)
        except OSError:
            # Fallback: direct unlink
            try:
                ct.unlink()
            except OSError:
                pass


def _get_dashboard_port() -> str:
    """Get configured dashboard port."""
    return os.environ.get("ATOMIC_TASKS_PORT", "5174")


def ensure_dashboard(atomic_root=None) -> bool:
    """Pre-task dashboard health check.

    Verifies the main dashboard server is running.  Calls
    start-dashboard.sh to start it if it is down.

    Args:
        atomic_root: Expected project root (Path or str).
                     Defaults to ATOMIC_ROOT env or cwd.

    Returns:
        True if healthy (or successfully restarted), False on failure.
    """
    if atomic_root is None:
        atomic_root = Path(os.environ.get("ATOMIC_ROOT", Path.cwd()))
    atomic_root = Path(atomic_root)

    port = _get_dashboard_port()
    expected = str(atomic_root.resolve())

    # Check main dashboard
    main_ok = False
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/root")
        with urllib.request.urlopen(req, timeout=1) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            running = str(Path(data.get("root", "")).resolve())
            if running == expected:
                main_ok = True
    except Exception as e:
        logger.debug("Dashboard health check failed: %s", e)

    if main_ok:
        return True

    # Something is down — call start-dashboard.sh which handles everything
    return _restart_dashboard(atomic_root, port)


def _restart_dashboard(atomic_root: Path, port: str) -> bool:
    """Start (or restart) the dashboard via start-dashboard.sh.

    Blocks until the main dashboard responds or times out (10s).
    """
    import subprocess
    import time

    script = atomic_root / "dashboard" / "start-dashboard.sh"
    if not script.exists():
        return False

    env = os.environ.copy()
    env["ATOMIC_ROOT"] = str(atomic_root)
    env["ATOMIC_TASKS_PORT"] = port

    try:
        popen_kwargs = dict(
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if sys.platform == 'win32':
            popen_kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs['start_new_session'] = True

        subprocess.Popen(["bash", str(script)], **popen_kwargs)
    except Exception as e:
        logger.warning("Failed to start dashboard: %s", e)
        return False

    # Wait for main dashboard to respond (up to 10s)
    for _ in range(20):
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/api/root")
            with urllib.request.urlopen(req, timeout=1):
                return True
        except Exception as e:
            logger.debug("Dashboard not yet responding: %s", e)
            time.sleep(0.5)
    return False


def stop_dashboard(atomic_root=None):
    """Stop all dashboard processes via stop-dashboard.sh.

    Args:
        atomic_root: Project root (Path or str). Defaults to ATOMIC_ROOT env or cwd.
    """
    import subprocess

    if atomic_root is None:
        atomic_root = Path(os.environ.get("ATOMIC_ROOT", Path.cwd()))
    atomic_root = Path(atomic_root)

    stop_script = atomic_root / "dashboard" / "stop-dashboard.sh"
    if not stop_script.exists():
        return

    env = os.environ.copy()
    env["ATOMIC_ROOT"] = str(atomic_root)

    try:
        subprocess.run(
            ["bash", str(stop_script)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except Exception as e:
        logger.warning("Failed to stop dashboard: %s", e)


def log_error(phase_id: str, task_id: str, error: str, traceback_str: str = None,
              atomic_root: Optional[Path] = None):
    """Append error to .logs/errors.json with file locking."""
    if atomic_root is None:
        atomic_root = Path(os.environ.get("ATOMIC_ROOT", "."))
    logs_dir = Path(atomic_root) / ".logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    errors_file = logs_dir / "errors.json"
    try:
        with _locked_file(errors_file, "r+") as fh:
            content = fh.read()
            try:
                errors = json.loads(content) if content.strip() else {"errors": []}
            except json.JSONDecodeError:
                errors = {"errors": []}
            errors["errors"].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "phase": phase_id,
                "task": task_id,
                "error": error,
                "traceback": traceback_str,
            })
            fh.seek(0)
            fh.write(json.dumps(errors, indent=2))
            fh.truncate()
    except OSError as e:
        logger.debug("Failed to log error to errors.json: %s", e)


def sync_dashboard(phase_id: Optional[str] = None, task_id: Optional[str] = None):
    """
    Ensure dashboard shows accurate state.

    Args:
        phase_id: Optional current phase for context
        task_id: Optional current task for context
    """
    # Validate state files
    if not validate_state_files():
        print("⚠️  State files inconsistent, attempting fix...")
        fix_state_inconsistencies()

    # Trigger dashboard refresh (if server running)
    port = _get_dashboard_port()
    if requests:
        try:
            requests.post(
                f"http://127.0.0.1:{port}/api/refresh",
                json={"phase": phase_id, "task": task_id},
                timeout=1
            )
        except Exception as e:
            logger.debug("Dashboard refresh failed (server may not be running): %s", e)


def validate_state_files(atomic_root: Optional[Path] = None) -> bool:
    """
    Check state files for consistency.

    Returns:
        bool: True if state files are consistent
    """
    state_dir = _get_state_dir(atomic_root)
    task_state_file = state_dir / "task-state.json"
    current_task_file = state_dir / "current-task.json"

    # Ensure task-state.json exists
    if not task_state_file.exists():
        return False

    # Load and validate structure
    try:
        with open(task_state_file, encoding="utf-8") as f:
            state = json.load(f)

        # Check required keys
        if "phases" not in state:
            return False

        # Validate phase structure
        for phase_id, phase_data in state.get("phases", {}).items():
            if not isinstance(phase_data, dict):
                return False
            if "tasks" not in phase_data:
                return False

        return True

    except (json.JSONDecodeError, OSError):
        return False


def fix_state_inconsistencies(atomic_root: Optional[Path] = None):
    """
    Attempt to fix state file inconsistencies.
    """
    state_dir = _get_state_dir(atomic_root)
    state_dir.mkdir(parents=True, exist_ok=True)

    task_state_file = state_dir / "task-state.json"

    # Create minimal valid state if missing
    if not task_state_file.exists():
        from core.utils.file_ops import write_json
        write_json(task_state_file, {"phases": {}})
        print("✓ Created task-state.json")

    # Clear stale current-task.json
    current_task_file = state_dir / "current-task.json"
    if current_task_file.exists():
        try:
            with open(current_task_file, encoding="utf-8") as f:
                current = json.load(f)

            # Check if it's stale (older than 5 minutes)
            import time
            import os

            file_age = time.time() - os.path.getmtime(current_task_file)
            if file_age > 300:  # 5 minutes
                # Only delete if task is not actively running (M9 fix).
                # Long-running LLM tasks (10+ min) should not have their
                # marker deleted while still active.
                if not current.get("active", False):
                    current_task_file.unlink()
                    print("✓ Cleared stale current-task.json")
                else:
                    logger.debug("current-task.json is old but marked active — keeping")

        except (json.JSONDecodeError, OSError):
            current_task_file.unlink()
            print("✓ Cleared invalid current-task.json")


def get_dashboard_status() -> Dict[str, Any]:
    """
    Get current dashboard status.

    Returns:
        dict: Dashboard status (running, port, etc.)
    """
    port = _get_dashboard_port()
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/root")
        with urllib.request.urlopen(req, timeout=1) as resp:
            if resp.status == 200:
                return {
                    "running": True,
                    "port": int(port),
                    "url": f"http://127.0.0.1:{port}",
                }
    except Exception as e:
        logger.debug("Dashboard status check failed: %s", e)

    return {"running": False}


def start_dashboard():
    """
    Start the dashboard server if not already running.
    """
    status = get_dashboard_status()

    if status["running"]:
        print(f"✓ Dashboard already running at {status['url']}")
        return

    print("🚀 Starting dashboard...")

    import subprocess

    dashboard_dir = Path(__file__).parent.parent / "dashboard"

    try:
        # Start dashboard in background
        popen_kwargs = dict(
            cwd=dashboard_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if sys.platform == 'win32':
            popen_kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs['start_new_session'] = True

        subprocess.Popen(
            ["npm", "start"],
            **popen_kwargs,
        )

        port = _get_dashboard_port()
        print(f"✓ Dashboard started at http://localhost:{port}")

    except Exception as e:
        print(f"⚠️  Could not start dashboard: {e}")
