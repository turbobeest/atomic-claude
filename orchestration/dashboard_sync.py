"""
Dashboard Sync Module

Validates state files and ensures dashboard shows accurate information.
Triggers dashboard refresh after task completion.
"""

import json
from pathlib import Path
import requests
from typing import Dict, Any, Optional


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
    try:
        requests.post(
            "http://localhost:5173/api/refresh",
            json={"phase": phase_id, "task": task_id},
            timeout=1
        )
        print("✅ Dashboard synced")
    except requests.exceptions.RequestException:
        # Dashboard not running, that's ok
        pass


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
    try:
        response = requests.get("http://localhost:5173/api/status", timeout=1)
        if response.status_code == 200:
            return {
                "running": True,
                "port": 5173,
                "url": "http://localhost:5173",
            }
    except requests.exceptions.RequestException:
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

        print("✓ Dashboard started at http://localhost:5173")

    except Exception as e:
        print(f"⚠️  Could not start dashboard: {e}")
