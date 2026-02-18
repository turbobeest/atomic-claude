"""
Dashboard Sync Module

Validates state files and ensures dashboard shows accurate information.
Triggers dashboard refresh after task completion.
Writes current-task.json, session-tokens.json, and errors.json for dashboard consumption.
"""

import json
import os
import urllib.request
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

try:
    import requests
except ImportError:
    requests = None


def write_current_task(phase_id: str, task_id: str, task_name: str,
                       resolved=None, provider: str = None, model: str = None,
                       agent_roster=None):
    """Write current-task.json for dashboard status display.

    Args:
        phase_id: Phase identifier (e.g. "0-setup")
        task_id: Task identifier (e.g. "001")
        task_name: Human-readable task name
        resolved: Optional ResolvedModel from core.llm.resolver
        provider: Optional provider override (fallback if no resolved)
        model: Optional model tier override (fallback if no resolved)
        agent_roster: Optional list of (AgentEntry, ResolvedModel) tuples
    """
    state_dir = Path(".state")
    state_dir.mkdir(parents=True, exist_ok=True)

    effort_level = None

    if resolved is not None:
        provider = resolved.provider
        model = resolved.model_id
        phase_weight = resolved.role
        context_window = resolved.context_window
        max_output = resolved.max_output
        effort_level = resolved.effort_level
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
        "started_at": datetime.now().isoformat(),
        "provider": provider,
        "model": model,
        "phase_weight": phase_weight,
        "effort_level": effort_level,
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
                "context_window": rm.context_window,
                "effort_level": rm.effort_level,
            }
            for entry, rm in agent_roster
            if entry.name != "\u2014"  # Skip placeholder entries
        ]

    with open(state_dir / "current-task.json", "w") as f:
        json.dump(data, f, indent=2)


def update_current_task_provider(provider: str, model: str = None,
                                 phase_id: str = None):
    """Update provider/model in current-task.json without replacing other fields.

    Called by task_001 once credentials are detected, before config exists.
    """
    ct = Path(".state/current-task.json")
    if not ct.exists():
        return
    try:
        data = json.loads(ct.read_text())
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
            except Exception:
                pass

        if not context_window:
            context_window, max_output = _get_model_limits(model)

        if context_window:
            data["context_window"] = context_window
        if max_output:
            data["max_output"] = max_output

        ct.write_text(json.dumps(data, indent=2))
    except (json.JSONDecodeError, OSError):
        pass


def init_session_tokens():
    """Initialize session-tokens.json at pipeline start so the dashboard has data immediately."""
    state_dir = Path(".state")
    state_dir.mkdir(parents=True, exist_ok=True)
    tokens_file = state_dir / "session-tokens.json"
    if not tokens_file.exists():
        data = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "estimated_cost_usd": 0,
            "by_provider": {},
            "by_model": {},
            "started_at": datetime.now().isoformat(),
        }
        tokens_file.write_text(json.dumps(data, indent=2))


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
    except Exception:
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


def clear_current_task():
    """Clear current-task.json when task completes."""
    ct = Path(".state/current-task.json")
    if ct.exists():
        ct.unlink()


def _get_dashboard_port() -> str:
    """Get configured dashboard port."""
    return os.environ.get("ATOMIC_TASKS_PORT", "5174")


def _check_port_listening(port) -> bool:
    """Quick check if something is listening on a port."""
    import socket
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=0.5):
            return True
    except (OSError, ConnectionRefusedError):
        return False


def ensure_dashboard(atomic_root=None) -> bool:
    """Pre-task dashboard health check.

    Verifies the main dashboard server and browser sub-apps (agents,
    audits, skills) are all running.  Calls start-dashboard.sh to
    start anything that is down.

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
    except Exception:
        pass

    # Check sub-apps (agent-manager:5175, audit-browser:5176, skills-browser:5177)
    subapps_ok = all(_check_port_listening(p) for p in (5175, 5176, 5177))

    if main_ok and subapps_ok:
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
        subprocess.Popen(
            ["bash", str(script)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        return False

    # Wait for main dashboard to respond (up to 10s)
    for _ in range(20):
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/api/root")
            with urllib.request.urlopen(req, timeout=1):
                return True
        except Exception:
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
    except Exception:
        pass


def log_error(phase_id: str, task_id: str, error: str, traceback_str: str = None):
    """Append error to .logs/errors.json."""
    logs_dir = Path(".logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    errors_file = logs_dir / "errors.json"
    try:
        errors = json.loads(errors_file.read_text()) if errors_file.exists() else {"errors": []}
    except json.JSONDecodeError:
        errors = {"errors": []}
    errors["errors"].append({
        "timestamp": datetime.now().isoformat(),
        "phase": phase_id,
        "task": task_id,
        "error": error,
        "traceback": traceback_str,
    })
    errors_file.write_text(json.dumps(errors, indent=2))


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
        except Exception:
            pass  # Dashboard not running, that's ok


def validate_state_files() -> bool:
    """
    Check state files for consistency.

    Returns:
        bool: True if state files are consistent
    """
    state_dir = Path(".state")
    task_state_file = state_dir / "task-state.json"
    current_task_file = state_dir / "current-task.json"

    # Ensure task-state.json exists
    if not task_state_file.exists():
        return False

    # Load and validate structure
    try:
        with open(task_state_file) as f:
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


def fix_state_inconsistencies():
    """
    Attempt to fix state file inconsistencies.
    """
    state_dir = Path(".state")
    state_dir.mkdir(parents=True, exist_ok=True)

    task_state_file = state_dir / "task-state.json"

    # Create minimal valid state if missing
    if not task_state_file.exists():
        with open(task_state_file, "w") as f:
            json.dump({"phases": {}}, f, indent=2)
        print("✓ Created task-state.json")

    # Clear stale current-task.json
    current_task_file = state_dir / "current-task.json"
    if current_task_file.exists():
        try:
            with open(current_task_file) as f:
                current = json.load(f)

            # Check if it's stale (older than 5 minutes)
            import time
            import os

            file_age = time.time() - os.path.getmtime(current_task_file)
            if file_age > 300:  # 5 minutes
                current_task_file.unlink()
                print("✓ Cleared stale current-task.json")

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
    except Exception:
        pass

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
        subprocess.Popen(
            ["npm", "start"],
            cwd=dashboard_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        port = _get_dashboard_port()
        print(f"✓ Dashboard started at http://localhost:{port}")

    except Exception as e:
        print(f"⚠️  Could not start dashboard: {e}")
