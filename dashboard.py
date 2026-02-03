#!/usr/bin/env python3
"""ATOMIC-CLAUDE Live Pipeline Progress Dashboard.

Self-contained HTTP server that monitors pipeline progress by reading
state files from a target project directory. Displays per-phase and
per-task status with color coding, timing, error details, and optional
LLM-generated summaries.

Usage:
    python tools/dashboard.py /path/to/project --port 8420
    python tools/dashboard.py /path/to/project --llm --llm-interval 300
"""

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

PHASE_NAMES = {
    "0-setup": "Setup",
    "1-discovery": "Discovery",
    "2-prd": "PRD",
    "3-tasking": "Tasking",
    "4-specification": "Specification",
    "5-implementation": "Implementation",
    "6-code-review": "Code Review",
    "7-integration": "Integration",
    "8-deployment-prep": "Deployment Prep",
    "9-release": "Release",
}

PHASE_ORDER = list(PHASE_NAMES.keys())

# Full task manifest for all phases (task_id: task_name)
PHASE_TASKS = {
    "0-setup": {
        "001": "Mode Selection",
        "002": "Config Collection",
        "003": "Config Review",
        "004": "API Keys",
        "005": "Material Scan",
        "006": "Reference Materials",
        "007": "Environment Setup",
        "008": "Repository Setup",
        "009": "Environment Check",
    },
    "1-discovery": {
        "101": "Entry Validation",
        "102": "Corpus Collection",
        "103": "Import Requirements",
        "104": "Opening Dialogue",
        "105": "Agent Selection",
        "106": "Discovery Work",
        "107": "Approach Selection",
        "108": "Discovery Diagrams",
        "109": "Phase Audit",
        "110": "Closeout",
    },
    "2-prd": {
        "201": "Entry Validation",
        "202": "PRD Setup",
        "203": "PRD Interview",
        "204": "Agent Selection",
        "205": "PRD Authoring",
        "206": "PRD Validation",
        "207": "PRD Approval",
        "208": "Phase Audit",
        "209": "Closeout",
    },
    "3-tasking": {
        "301": "Entry Initialization",
        "302": "Agent Selection",
        "303": "Task Decomposition",
        "304": "Dependency Analysis",
        "305": "Phase Audit",
        "306": "Closeout",
    },
    "4-specification": {
        "401": "Entry Initialization",
        "402": "Agent Selection",
        "403": "OpenSpec Generation",
        "404": "TDD Subtask Injection",
        "405": "Phase Audit",
        "406": "Closeout",
    },
    "5-implementation": {
        "501": "Entry Initialization",
        "502": "TDD Setup",
        "503": "Agent Selection",
        "504": "TDD Execution",
        "505": "Validation",
        "506": "Phase Audit",
        "507": "Closeout",
    },
    "6-code-review": {
        "601": "Entry Initialization",
        "602": "Agent Selection",
        "603": "Code Review",
        "604": "Refinement",
        "605": "Phase Audit",
        "606": "Closeout",
    },
    "7-integration": {
        "701": "Entry Initialization",
        "702": "Integration Setup",
        "703": "Agent Selection",
        "704": "Testing Execution",
        "705": "Integration Approval",
        "706": "Phase Audit",
        "707": "Closeout",
    },
    "8-deployment-prep": {
        "801": "Entry Initialization",
        "802": "Deployment Setup",
        "803": "Agent Selection",
        "804": "Artifact Generation",
        "805": "Phase Audit",
        "806": "Deployment Approval",
        "807": "Closeout",
    },
    "9-release": {
        "901": "Entry Initialization",
        "902": "Release Setup",
        "903": "Agent Selection",
        "904": "Release Execution",
        "905": "Release Confirmation",
        "906": "Closeout",
    },
}


def _read_json(path):
    """Read a JSON file, returning None on any error."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def _iso_to_dt(iso_str):
    """Parse an ISO 8601 timestamp string into a datetime, or None."""
    if not iso_str:
        return None
    try:
        # Handle both Z and ±offset formats
        s = iso_str.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _format_duration(seconds):
    """Format seconds into human-readable duration."""
    if seconds is None or seconds < 0:
        return "-"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {secs:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


class PipelineState:
    """Reads pipeline state from project directory files."""

    def __init__(self, project_dir):
        self.project_dir = Path(project_dir)
        self._previous = None
        self._changes = []

    def read(self):
        """Return complete pipeline snapshot dict."""
        session = self._read_session()
        task_state = self._read_task_state()
        phases = self._build_phases(task_state)
        audit_results = self._read_audit_results()
        artifacts = self._read_artifacts()
        project_name = self._read_project_name()

        snapshot = {
            "project_name": project_name,
            "session": session,
            "phases": phases,
            "task_state_meta": {
                "current_phase": task_state.get("current_phase") if task_state else None,
                "current_task": task_state.get("current_task") if task_state else None,
            },
            "audit_results": audit_results,
            "artifacts": artifacts,
            "timestamp": datetime.now().isoformat(),
            "changes": [],
        }

        # Detect changes against previous snapshot
        if self._previous is not None:
            snapshot["changes"] = self._detect_changes(self._previous, snapshot)

        self._previous = snapshot
        return snapshot

    def _read_project_name(self):
        path = self.project_dir / ".outputs" / "0-setup" / "project-config.json"
        data = _read_json(path)
        if data and data.get("project", {}).get("name"):
            return data["project"]["name"]
        # Fallback to directory name
        return self.project_dir.name

    def _read_session(self):
        path = self.project_dir / ".state" / "session.json"
        data = _read_json(path)
        if not data:
            return {"session_id": None, "started_at": None, "tasks_completed": 0,
                    "tasks_failed": 0, "current_phase": None, "current_task": None}
        return data

    def _read_task_state(self):
        path = self.project_dir / ".claude" / "task-state.json"
        return _read_json(path) or {}

    def _build_phases(self, task_state):
        """Build phase list from task-state.json merged with full task manifest."""
        ts_phases = task_state.get("phases", {})
        phases = []

        for phase_id in PHASE_ORDER:
            phase_data = ts_phases.get(phase_id, {})
            closeout = self._read_closeout(phase_id)

            completed = phase_data.get("completed", False)
            started_at = phase_data.get("started_at")
            completed_at = phase_data.get("completed_at")

            # Get recorded task states
            tasks_raw = phase_data.get("tasks", {})

            # Build tasks from manifest, overlaying recorded state
            manifest_tasks = PHASE_TASKS.get(phase_id, {})
            tasks = []
            has_in_progress = False
            has_failed = False

            for tid in sorted(manifest_tasks.keys()):
                task_name = manifest_tasks[tid]
                recorded = tasks_raw.get(tid, {})
                status = recorded.get("status", "pending")

                if status == "in_progress":
                    has_in_progress = True
                if status == "failed":
                    has_failed = True

                tasks.append({
                    "id": tid,
                    "name": recorded.get("name", task_name),
                    "status": status,
                    "started_at": recorded.get("started_at"),
                    "completed_at": recorded.get("completed_at"),
                    "artifacts": recorded.get("artifacts", []),
                    "error": recorded.get("error"),
                })

            # Also include any tasks in recorded state not in manifest
            for tid in sorted(tasks_raw.keys()):
                if tid not in manifest_tasks:
                    t = tasks_raw[tid]
                    status = t.get("status", "pending")
                    if status == "in_progress":
                        has_in_progress = True
                    if status == "failed":
                        has_failed = True
                    tasks.append({
                        "id": tid,
                        "name": t.get("name", f"Task {tid}"),
                        "status": status,
                        "started_at": t.get("started_at"),
                        "completed_at": t.get("completed_at"),
                        "artifacts": t.get("artifacts", []),
                        "error": t.get("error"),
                    })

            if completed:
                phase_status = "complete"
            elif has_failed:
                phase_status = "failed"
            elif has_in_progress or started_at:
                phase_status = "in_progress"
            else:
                phase_status = "pending"

            # Duration from closeout or timestamps
            duration = None
            if closeout and closeout.get("duration_seconds"):
                duration = closeout["duration_seconds"]
            elif started_at:
                start_dt = _iso_to_dt(started_at)
                end_dt = _iso_to_dt(completed_at) if completed_at else datetime.now(timezone.utc)
                if start_dt:
                    if start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=timezone.utc)
                    if end_dt.tzinfo is None:
                        end_dt = end_dt.replace(tzinfo=timezone.utc)
                    duration = (end_dt - start_dt).total_seconds()

            phases.append({
                "id": phase_id,
                "name": PHASE_NAMES.get(phase_id, phase_id),
                "status": phase_status,
                "started_at": started_at,
                "completed_at": completed_at,
                "duration": duration,
                "tasks": tasks,
                "closeout": closeout,
            })

        return phases

    def _read_closeout(self, phase_id):
        path = self.project_dir / ".outputs" / phase_id / "closeout.json"
        return _read_json(path)

    def _read_audit_results(self):
        cache_dir = self.project_dir / ".state" / "audit-cache"
        results = []
        if not cache_dir.is_dir():
            return results
        for f in sorted(cache_dir.glob("result-phase*.json")):
            data = _read_json(f)
            if data:
                data["_file"] = f.name
                results.append(data)
        return results

    def _read_artifacts(self):
        path = self.project_dir / ".state" / "context" / "artifacts.json"
        data = _read_json(path)
        if data and isinstance(data, dict):
            return data.get("artifacts", [])
        return []

    def _detect_changes(self, prev, curr):
        """Compare two snapshots and return list of change dicts."""
        changes = []
        now = curr["timestamp"]

        prev_phases = {p["id"]: p for p in prev.get("phases", [])}
        curr_phases = {p["id"]: p for p in curr.get("phases", [])}

        for pid, cp in curr_phases.items():
            pp = prev_phases.get(pid)
            if not pp:
                continue

            # Phase-level status change
            if cp["status"] != pp["status"]:
                reverse = (
                    pp["status"] == "complete"
                    and cp["status"] in ("in_progress", "pending")
                )
                changes.append({
                    "timestamp": now,
                    "type": "phase_redo" if reverse else "phase_status",
                    "phase": pid,
                    "from": pp["status"],
                    "to": cp["status"],
                    "reverse": reverse,
                })

            # Task-level changes
            prev_tasks = {t["id"]: t for t in pp.get("tasks", [])}
            for ct in cp.get("tasks", []):
                pt = prev_tasks.get(ct["id"])
                if not pt:
                    continue
                if ct["status"] != pt["status"]:
                    reverse = (
                        pt["status"] == "complete"
                        and ct["status"] in ("in_progress", "pending")
                    )
                    changes.append({
                        "timestamp": now,
                        "type": "task_redo" if reverse else "task_status",
                        "phase": pid,
                        "task": ct["id"],
                        "task_name": ct["name"],
                        "from": pt["status"],
                        "to": ct["status"],
                        "reverse": reverse,
                    })

        return changes


# ---------------------------------------------------------------------------
# Activity Monitor
# ---------------------------------------------------------------------------

_LOG_LINE_RE = re.compile(
    r'\[([^\]]+)\]\s+task="([^"]+)"\s+provider=(\S+)\s+model=(\S+)\s+duration=(\d+)s\s+exit=(\d+)\s+output=(\S+)'
)


class ActivityMonitor:
    """Monitors log files and file-system changes for per-task activity.

    Attributes new log-file invocations and new/modified output files to
    whichever pipeline task is currently active, then expires activity
    that is more than KEEP_TASKS tasks behind the current one.
    """

    KEEP_TASKS = 3  # current + 2 previous

    def __init__(self, project_dir):
        self.project_dir = Path(project_dir)
        self._log_offsets = {}       # {str_path: byte_offset}
        self._file_mtimes = {}       # {str_path: mtime}
        self._task_events = {}       # {"phase:task_id": [event, ...]}
        self._task_order = []        # ordered keys for pruning
        self._initialized = False
        self._lock = threading.Lock()

    def poll(self, current_phase, current_task):
        """Read new activity, attribute to current task, return events dict."""
        key = (
            f"{current_phase}:{current_task}"
            if current_phase and current_task
            else None
        )

        if not self._initialized:
            # First poll: build baselines, emit nothing
            self._build_log_baseline()
            self._build_file_baseline()
            self._initialized = True
            events = []
        else:
            log_events = self._read_new_log_lines()
            file_events = self._scan_file_changes()
            events = log_events + file_events

        with self._lock:
            if key and events:
                if key not in self._task_events:
                    self._task_events[key] = []
                    self._task_order.append(key)
                self._task_events[key].extend(events)
                self._task_events[key] = self._task_events[key][-30:]

            self._prune()
            return {k: list(v) for k, v in self._task_events.items()}

    # -- log file parsing ---------------------------------------------------

    def _build_log_baseline(self):
        """Set log file offsets to current end so we don't replay history."""
        log_dir = self.project_dir / ".logs"
        if not log_dir.is_dir():
            return
        for log_file in log_dir.glob("*.log"):
            try:
                self._log_offsets[str(log_file)] = log_file.stat().st_size
            except OSError:
                pass

    def _read_new_log_lines(self):
        events = []
        log_dir = self.project_dir / ".logs"
        if not log_dir.is_dir():
            return events

        for log_file in sorted(log_dir.glob("*.log")):
            path_str = str(log_file)
            try:
                size = log_file.stat().st_size
            except OSError:
                continue

            offset = self._log_offsets.get(path_str, 0)
            if size <= offset:
                continue

            try:
                with open(log_file, "r") as f:
                    f.seek(offset)
                    new_text = f.read()
                    self._log_offsets[path_str] = f.tell()
            except OSError:
                continue

            for line in new_text.strip().split("\n"):
                ev = self._parse_log_line(line)
                if ev:
                    events.append(ev)

        return events

    def _parse_log_line(self, line):
        m = _LOG_LINE_RE.match(line.strip())
        if not m:
            return None
        timestamp, task, _provider, model, duration, exit_code, output = m.groups()
        try:
            rel = str(Path(output).relative_to(self.project_dir))
        except ValueError:
            rel = Path(output).name
        return {
            "type": "invocation",
            "time": timestamp,
            "task": task,
            "model": model,
            "duration": int(duration),
            "exit": int(exit_code),
            "output": rel,
        }

    # -- file-system scanning -----------------------------------------------

    def _scan_file_changes(self):
        events = []
        for d in (self.project_dir / ".outputs", self.project_dir / ".state"):
            if not d.is_dir():
                continue
            for entry in self._walk(d):
                path_str = str(entry)
                try:
                    mtime = entry.stat().st_mtime
                except OSError:
                    continue
                prev = self._file_mtimes.get(path_str)
                if prev is None:
                    events.append({
                        "type": "file_created",
                        "time": datetime.fromtimestamp(mtime).isoformat(),
                        "path": str(entry.relative_to(self.project_dir)),
                    })
                elif mtime > prev + 0.5:
                    events.append({
                        "type": "file_modified",
                        "time": datetime.fromtimestamp(mtime).isoformat(),
                        "path": str(entry.relative_to(self.project_dir)),
                    })
                self._file_mtimes[path_str] = mtime
        return events

    def _build_file_baseline(self):
        for d in (self.project_dir / ".outputs", self.project_dir / ".state"):
            if not d.is_dir():
                continue
            for entry in self._walk(d):
                try:
                    self._file_mtimes[str(entry)] = entry.stat().st_mtime
                except OSError:
                    pass

    def _walk(self, directory, depth=0):
        if depth > 4:
            return
        try:
            for entry in directory.iterdir():
                if entry.is_file():
                    yield entry
                elif entry.is_dir() and not entry.name.startswith("."):
                    yield from self._walk(entry, depth + 1)
        except OSError:
            pass

    # -- pruning ------------------------------------------------------------

    def _prune(self):
        while len(self._task_order) > self.KEEP_TASKS:
            old = self._task_order.pop(0)
            self._task_events.pop(old, None)


# ---------------------------------------------------------------------------
# LLM Summary
# ---------------------------------------------------------------------------

class LLMSummarizer:
    """Periodically generates LLM-powered pipeline summaries."""

    def __init__(self, claude_local_path, interval=300):
        self.claude_local_path = Path(claude_local_path) if claude_local_path else None
        self.interval = interval
        self._last_summary = None
        self._last_summary_at = None
        self._poll_count = 0
        self._lock = threading.Lock()

    def maybe_update(self, state):
        """Called each poll cycle. Generates summary every N cycles."""
        self._poll_count += 1
        cycles_per_summary = max(1, self.interval // 30)
        if self._poll_count % cycles_per_summary != 0:
            return
        # Run in background thread to avoid blocking the poll
        t = threading.Thread(target=self._generate, args=(state,), daemon=True)
        t.start()

    def get_summary(self):
        with self._lock:
            return {
                "text": self._last_summary,
                "generated_at": self._last_summary_at,
            }

    def _generate(self, state):
        if not self.claude_local_path or not self.claude_local_path.is_dir():
            with self._lock:
                self._last_summary = "(LLM path not found)"
                self._last_summary_at = datetime.now().isoformat()
            return

        # Build a compact state summary for the prompt
        compact = self._compact_state(state)
        prompt = (
            "Summarize this ATOMIC-CLAUDE pipeline state concisely in 2-3 sentences. "
            "Highlight current progress, any failures or warnings, and what's next.\n\n"
            + json.dumps(compact, indent=2)
        )

        try:
            result = subprocess.run(
                [
                    "python", "-m", "local_launcher",
                    "--provider", "ollama",
                    "--model", "llama3.2:3b",
                    "--max-turns", "1",
                    "-p", prompt,
                ],
                capture_output=True,
                text=True,
                cwd=str(self.claude_local_path),
                timeout=60,
            )
            summary = result.stdout.strip() if result.returncode == 0 else f"LLM error: {result.stderr[:200]}"
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            summary = f"LLM unavailable: {e}"

        with self._lock:
            self._last_summary = summary
            self._last_summary_at = datetime.now().isoformat()

    @staticmethod
    def _compact_state(state):
        """Reduce state to essentials for LLM prompt."""
        phases = []
        for p in state.get("phases", []):
            task_summary = {}
            for t in p.get("tasks", []):
                s = t["status"]
                task_summary[s] = task_summary.get(s, 0) + 1
            phases.append({
                "id": p["id"],
                "name": p["name"],
                "status": p["status"],
                "duration": _format_duration(p.get("duration")),
                "tasks": task_summary,
            })
        session = state.get("session", {})
        return {
            "session_id": session.get("session_id"),
            "started_at": session.get("started_at"),
            "tasks_completed": session.get("tasks_completed", 0),
            "tasks_failed": session.get("tasks_failed", 0),
            "phases": phases,
        }


# ---------------------------------------------------------------------------
# HTML Template
# ---------------------------------------------------------------------------

def _html_template(poll_interval_ms, popup_mode=False):
    popup_script = """
    // Popup mode: resize window on load
    if (window.opener || window.name === 'pipeline_dashboard') {
      window.resizeTo(420, 800);
    }
    """ if popup_mode else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pipeline Dashboard</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'><circle cx='8' cy='8' r='7' fill='%233b82f6'/><circle cx='8' cy='8' r='3' fill='%231a1a2e'/></svg>">
<style>
:root {{
  --bg: #1a1a2e;
  --card: #16213e;
  --card-border: #0f3460;
  --text: #e0e0e0;
  --text-muted: #9ca3af;
  --green: #22c55e;
  --blue: #3b82f6;
  --red: #ef4444;
  --gray: #6b7280;
  --orange: #f59e0b;
  --yellow: #eab308;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace;
  background: var(--bg);
  color: var(--text);
  font-size: 14px;
  line-height: 1.5;
  min-height: 100vh;
  display: flex;
  justify-content: center;
  padding: 16px;
}}
.dashboard {{
  width: 380px;
  max-width: 100%;
}}
.header {{
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 8px;
}}
.header h1 {{
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 8px;
  color: var(--blue);
}}
.header .meta {{
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 4px;
}}
.progress-bar-container {{
  background: #0d1b2a;
  border-radius: 4px;
  height: 20px;
  margin-top: 10px;
  overflow: hidden;
  position: relative;
}}
.progress-bar {{
  height: 100%;
  background: linear-gradient(90deg, var(--green), #16a34a);
  border-radius: 4px;
  transition: width 0.5s ease;
}}
.progress-label {{
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  text-shadow: 0 1px 2px rgba(0,0,0,0.5);
}}
.phase {{
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 8px;
  margin-bottom: 4px;
  overflow: hidden;
}}
.phase-header {{
  display: flex;
  align-items: center;
  padding: 10px 14px;
  cursor: pointer;
  gap: 8px;
  user-select: none;
}}
.phase-header:hover {{
  background: rgba(255,255,255,0.03);
}}
.phase-icon {{
  font-size: 14px;
  width: 18px;
  text-align: center;
  flex-shrink: 0;
}}
.phase-name {{
  flex: 1;
  font-size: 13px;
  font-weight: 600;
}}
.phase-duration {{
  font-size: 11px;
  color: var(--text-muted);
}}
.phase-tasks {{
  padding: 0 14px 10px 40px;
}}
.task {{
  display: flex;
  align-items: center;
  padding: 3px 0;
  gap: 6px;
  font-size: 12px;
}}
.task-icon {{
  width: 14px;
  text-align: center;
  flex-shrink: 0;
  font-size: 12px;
}}
.task-id {{
  color: var(--text-muted);
  width: 28px;
  flex-shrink: 0;
}}
.task-name {{
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.task-time {{
  font-size: 11px;
  color: var(--text-muted);
  flex-shrink: 0;
}}
.task-error {{
  font-size: 11px;
  color: var(--red);
  padding: 2px 0 2px 48px;
}}
.task-activity {{
  padding: 4px 0 6px 48px;
  border-left: 2px solid var(--card-border);
  margin-left: 20px;
}}
.task-activity-item {{
  font-size: 10px;
  color: var(--text-muted);
  padding: 1px 0;
  display: flex;
  gap: 6px;
  align-items: baseline;
}}
.task-activity-item .act-icon {{
  flex-shrink: 0;
  width: 10px;
  text-align: center;
}}
.task-activity-item .act-model {{
  color: var(--blue);
  flex-shrink: 0;
}}
.task-activity-item .act-dur {{
  color: var(--text-muted);
  flex-shrink: 0;
}}
.task-activity-item .act-file {{
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  direction: rtl;
  text-align: left;
}}
.task-activity-item.act-fail {{
  color: var(--red);
}}
.task-activity-item.act-fail .act-model {{
  color: var(--red);
}}
.act-more {{
  font-size: 10px;
  color: var(--gray);
  padding: 1px 0 1px 16px;
  cursor: pointer;
}}
.act-more:hover {{
  color: var(--text-muted);
}}
.status-complete {{ color: var(--green); }}
.status-in_progress {{ color: var(--blue); }}
.status-failed {{ color: var(--red); }}
.status-pending {{ color: var(--gray); }}
.status-redo {{ color: var(--orange); }}

@keyframes pulse {{
  0%, 100% {{ opacity: 1; }}
  50% {{ opacity: 0.5; }}
}}
.pulse {{ animation: pulse 2s ease-in-out infinite; }}

.footer {{
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 8px;
  padding: 10px 14px;
  margin-top: 8px;
  font-size: 11px;
  color: var(--text-muted);
  display: flex;
  justify-content: space-between;
}}
.activity {{
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 8px;
  padding: 10px 14px;
  margin-top: 8px;
}}
.activity h3 {{
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 6px;
  color: var(--text-muted);
}}
.activity-item {{
  font-size: 11px;
  padding: 2px 0;
  color: var(--text-muted);
}}
.activity-item.reverse {{
  color: var(--orange);
}}
.llm-summary {{
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 8px;
  padding: 10px 14px;
  margin-top: 8px;
}}
.llm-summary h3 {{
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 6px;
  color: var(--text-muted);
  cursor: pointer;
}}
.llm-summary .body {{
  font-size: 12px;
  color: var(--text);
  line-height: 1.5;
}}
.collapsed .body {{ display: none; }}
.hidden {{ display: none; }}
.conn-error {{
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid var(--red);
  border-radius: 8px;
  padding: 10px 14px;
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--red);
  text-align: center;
}}
#loading {{
  text-align: center;
  padding: 40px 16px;
  color: var(--text-muted);
  font-size: 13px;
}}
#loading .spinner {{
  display: inline-block;
  width: 24px;
  height: 24px;
  border: 3px solid var(--card-border);
  border-top-color: var(--blue);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 12px;
}}
@keyframes spin {{
  to {{ transform: rotate(360deg); }}
}}
#js-error {{
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid var(--red);
  border-radius: 8px;
  padding: 14px;
  margin: 8px 0;
  font-size: 12px;
  color: var(--red);
  white-space: pre-wrap;
  word-break: break-all;
  display: none;
}}
</style>
</head>
<body>
<div class="dashboard" id="root">
  <div class="conn-error hidden" id="conn-error">Connection lost &mdash; retrying&hellip;</div>
  <div class="header" id="header">
    <h1 style="font-size:16px;font-weight:700;color:#3b82f6">Pipeline Dashboard</h1>
    <div style="font-size:12px;color:#9ca3af">Connecting&hellip;</div>
  </div>
  <div id="loading"><div class="spinner"></div><br>Loading pipeline state&hellip;</div>
  <div id="js-error"></div>
  <div id="phases"></div>
  <div id="activity-section"></div>
  <div id="llm-section"></div>
  <div class="footer" id="footer">
    <span>Starting&hellip;</span>
    <span></span>
  </div>
  <noscript>
    <div style="text-align:center;padding:20px;color:#ef4444">
      JavaScript is required for this dashboard.
    </div>
  </noscript>
</div>
<script>
var POLL_MS = {poll_interval_ms};
const STATUS_ICON = {{
  complete: '\\u2713',
  in_progress: '\\u25B6',
  failed: '\\u2717',
  pending: '\\u25CB',
  redo: '\\u21BA'
}};

let activityLog = [];
// Start with all phases expanded for full agenda view
let expandedPhases = {{'0-setup': true, '1-discovery': true, '2-prd': true, '3-tasking': true, '4-specification': true, '5-implementation': true, '6-code-review': true, '7-integration': true, '8-deployment-prep': true, '9-release': true}};
let llmCollapsed = false;
{popup_script}

function escHtml(s) {{
  const d = document.createElement('div');
  d.textContent = s || '';
  return d.innerHTML;
}}

function fmtDuration(sec) {{
  if (sec == null || sec < 0) return '';
  sec = Math.floor(sec);
  if (sec < 60) return sec + 's';
  const m = Math.floor(sec / 60), s = sec % 60;
  if (m < 60) return m + 'm ' + String(s).padStart(2, '0') + 's';
  const h = Math.floor(m / 60), rm = m % 60;
  return h + 'h ' + String(rm).padStart(2, '0') + 'm';
}}

function taskDuration(t) {{
  if (!t.started_at) return '';
  const start = new Date(t.started_at);
  const end = t.completed_at ? new Date(t.completed_at) : new Date();
  const sec = (end - start) / 1000;
  return fmtDuration(sec);
}}

function renderTaskActivity(phaseId, taskId, data) {{
  var activity = data.task_activity || {{}};
  var key = phaseId + ':' + taskId;
  var events = activity[key];
  if (!events || events.length === 0) return '';

  // Show last 6 events, with "N more" link
  var visible = events.slice(-6);
  var hidden = events.length - visible.length;

  var items = visible.map(function(ev) {{
    if (ev.type === 'invocation') {{
      var failCls = ev.exit !== 0 ? ' act-fail' : '';
      var icon = ev.exit !== 0 ? '\\u2717' : '\\u2192';
      var file = ev.output.split('/').pop();
      var durStr = ev.duration + 's';
      return '<div class="task-activity-item' + failCls + '">'
        + '<span class="act-icon">' + icon + '</span>'
        + '<span class="act-model">' + escHtml(ev.model) + '</span>'
        + '<span class="act-dur">' + durStr + '</span>'
        + '<span class="act-file" title="' + escHtml(ev.output) + '">' + escHtml(file) + '</span>'
        + '</div>';
    }} else {{
      var verb = ev.type === 'file_created' ? '+' : '~';
      var fname = (ev.path || '').split('/').pop();
      return '<div class="task-activity-item">'
        + '<span class="act-icon">' + verb + '</span>'
        + '<span class="act-file" title="' + escHtml(ev.path || '') + '">' + escHtml(fname) + '</span>'
        + '</div>';
    }}
  }}).join('');

  var moreHtml = hidden > 0 ? '<div class="act-more">' + hidden + ' earlier&hellip;</div>' : '';

  return '<div class="task-activity">' + moreHtml + items + '</div>';
}}

function renderHeader(data) {{
  const s = data.session || {{}};
  const meta = data.task_state_meta || {{}};
  const sid = s.session_id || 'N/A';
  const startedAt = s.started_at;
  let elapsed = '';
  if (startedAt) {{
    const sec = (Date.now() - new Date(startedAt).getTime()) / 1000;
    elapsed = fmtDuration(sec);
  }}

  const phases = data.phases || [];
  const total = phases.length;
  const done = phases.filter(p => p.status === 'complete').length;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  const failCount = (s.tasks_failed || 0);
  const warnings = (data.audit_results || []).filter(a => a.status === 'warn').length;

  const projName = escHtml(data.project_name || 'Pipeline');
  document.title = projName + ' Dashboard';
  document.getElementById('header').innerHTML = `
    <h1>${{projName}} Dashboard</h1>
    <div class="meta">Session: ${{escHtml(sid)}}</div>
    ${{elapsed ? '<div class="meta">Elapsed: ' + escHtml(elapsed) + '</div>' : ''}}
    ${{meta.current_phase ? '<div class="meta">Phase: ' + escHtml(meta.current_phase) + (meta.current_task ? ' / Task ' + escHtml(meta.current_task) : '') + '</div>' : ''}}
    <div class="progress-bar-container">
      <div class="progress-bar" style="width:${{pct}}%"></div>
      <div class="progress-label">${{pct}}% (${{done}}/${{total}})</div>
    </div>
  `;

  document.getElementById('footer').innerHTML = `
    <span>Updated: ${{new Date().toLocaleTimeString()}}</span>
    <span>Errors: ${{failCount}} &middot; Warnings: ${{warnings}}</span>
  `;
}}

function renderPhases(data) {{
  const phases = data.phases || [];
  const meta = data.task_state_meta || {{}};
  const container = document.getElementById('phases');

  // Auto-expand active phase on first load
  const activePhase = phases.find(p => p.status === 'in_progress');
  if (activePhase && !(activePhase.id in expandedPhases)) {{
    expandedPhases[activePhase.id] = true;
  }}

  container.innerHTML = phases.map(p => {{
    const icon = STATUS_ICON[p.status] || STATUS_ICON.pending;
    const cls = 'status-' + p.status;
    const dur = p.duration != null ? fmtDuration(p.duration) : '';
    const expanded = !!expandedPhases[p.id];
    const hasTasks = p.tasks && p.tasks.length > 0;
    const pulseClass = p.status === 'in_progress' ? ' pulse' : '';

    let tasksHtml = '';
    if (expanded && hasTasks) {{
      tasksHtml = '<div class="phase-tasks">' + p.tasks.map(t => {{
        const ti = STATUS_ICON[t.status] || STATUS_ICON.pending;
        const tc = 'status-' + t.status;
        const tPulse = t.status === 'in_progress' ? ' pulse' : '';
        const tDur = taskDuration(t);
        let html = `<div class="task">
          <span class="task-icon ${{tc}}${{tPulse}}">${{ti}}</span>
          <span class="task-id">${{escHtml(t.id)}}</span>
          <span class="task-name" title="${{escHtml(t.name)}}">${{escHtml(t.name)}}</span>
          <span class="task-time">${{escHtml(tDur)}}</span>
        </div>`;
        if (t.error) {{
          html += `<div class="task-error">${{escHtml(t.error)}}</div>`;
        }}
        html += renderTaskActivity(p.id, t.id, data);
        return html;
      }}).join('') + '</div>';
    }}

    return `<div class="phase" data-phase="${{p.id}}">
      <div class="phase-header" onclick="togglePhase('${{p.id}}')">
        <span class="phase-icon ${{cls}}${{pulseClass}}">${{icon}}</span>
        <span class="phase-name">Phase ${{escHtml(p.id.split('-')[0])}}: ${{escHtml(p.name)}}</span>
        <span class="phase-duration">${{escHtml(dur)}}</span>
      </div>
      ${{tasksHtml}}
    </div>`;
  }}).join('');
}}

function togglePhase(id) {{
  expandedPhases[id] = !expandedPhases[id];
  // Re-render from last data
  if (window._lastData) renderPhases(window._lastData);
}}

function renderActivity(data) {{
  const changes = data.changes || [];
  changes.forEach(c => {{
    activityLog.unshift(c);
  }});
  // Keep last 20
  activityLog = activityLog.slice(0, 20);

  const section = document.getElementById('activity-section');
  if (activityLog.length === 0) {{
    section.innerHTML = '';
    return;
  }}
  section.innerHTML = `<div class="activity">
    <h3>Recent Activity</h3>
    ${{activityLog.slice(0, 10).map(c => {{
      const rev = c.reverse ? ' reverse' : '';
      const icon = c.reverse ? STATUS_ICON.redo : (STATUS_ICON[c.to] || '');
      const target = c.task ? ('Task ' + c.task + ' (' + (c.task_name || '') + ')') : ('Phase ' + c.phase);
      const ts = c.timestamp ? new Date(c.timestamp).toLocaleTimeString() : '';
      return `<div class="activity-item${{rev}}">${{icon}} ${{escHtml(target)}}: ${{escHtml(c.from)}} → ${{escHtml(c.to)}} <span style="float:right">${{ts}}</span></div>`;
    }}).join('')}}
  </div>`;
}}

function renderLLM(data) {{
  const section = document.getElementById('llm-section');
  const summary = data.llm_summary;
  if (!summary || !summary.text) {{
    section.innerHTML = '';
    return;
  }}
  const collapsed = llmCollapsed ? ' collapsed' : '';
  const ts = summary.generated_at ? new Date(summary.generated_at).toLocaleTimeString() : '';
  section.innerHTML = `<div class="llm-summary${{collapsed}}">
    <h3 onclick="llmCollapsed=!llmCollapsed;if(window._lastData)renderLLM(window._lastData)">
      LLM Summary ${{ts ? '(' + ts + ')' : ''}} ${{llmCollapsed ? '▸' : '▾'}}
    </h3>
    <div class="body">${{escHtml(summary.text)}}</div>
  </div>`;
}}

function render(data) {{
  window._lastData = data;
  renderHeader(data);
  renderPhases(data);
  renderActivity(data);
  renderLLM(data);
  document.getElementById('conn-error').classList.add('hidden');
  var ld = document.getElementById('loading');
  if (ld) ld.style.display = 'none';
}}

function showError(msg) {{
  var el = document.getElementById('js-error');
  if (el) {{
    el.style.display = 'block';
    el.textContent = msg;
  }}
}}

function poll() {{
  var xhr = new XMLHttpRequest();
  xhr.open('GET', '/api/state', true);
  xhr.onload = function() {{
    try {{
      if (xhr.status !== 200) throw new Error('HTTP ' + xhr.status);
      var data = JSON.parse(xhr.responseText);
      render(data);
    }} catch (e) {{
      showError('Render error: ' + e.message);
      document.getElementById('conn-error').classList.remove('hidden');
    }}
  }};
  xhr.onerror = function() {{
    document.getElementById('conn-error').classList.remove('hidden');
    showError('Network error — cannot reach /api/state');
  }};
  xhr.send();
}}

// Initial load + polling
try {{
  poll();
  setInterval(poll, POLL_MS);
}} catch (e) {{
  showError('Init error: ' + e.message + '\\n' + e.stack);
}}
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# HTTP Server
# ---------------------------------------------------------------------------

class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the dashboard."""

    # Set by the server factory
    pipeline_state = None
    activity_monitor = None
    poll_interval = 30
    llm_summarizer = None
    popup_mode = False
    _state_lock = threading.Lock()
    _cached_state = None
    _cached_at = 0

    def do_GET(self):
        if self.path == "/":
            self._serve_html()
        elif self.path == "/api/state":
            self._serve_state()
        elif self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        else:
            self.send_error(404)

    def _serve_html(self):
        html = _html_template(self.poll_interval * 1000, self.popup_mode)
        payload = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _serve_state(self):
        state = self._get_state()
        payload = json.dumps(state).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(payload)

    def _get_state(self):
        """Return state, caching for half the poll interval to avoid excessive reads."""
        now = time.monotonic()
        cache_ttl = max(2, self.poll_interval / 2)

        with self._state_lock:
            if self._cached_state and (now - self._cached_at) < cache_ttl:
                return self._cached_state

            state = self.pipeline_state.read()

            # Poll activity monitor for per-task events
            if self.activity_monitor:
                meta = state.get("task_state_meta", {})
                state["task_activity"] = self.activity_monitor.poll(
                    meta.get("current_phase"),
                    meta.get("current_task"),
                )
            else:
                state["task_activity"] = {}

            # Add LLM summary if available
            if self.llm_summarizer:
                self.llm_summarizer.maybe_update(state)
                state["llm_summary"] = self.llm_summarizer.get_summary()

            self._cached_state = state
            self._cached_at = now
            return state

    def log_message(self, format, *args):
        """Suppress default request logging to keep console clean."""
        pass


def run_server(project_dir, port=8420, poll_interval=30,
               llm_enabled=False, llm_interval=300, claude_local=None,
               popup=False, no_browser=False):
    """Start the HTTP dashboard server."""
    state = PipelineState(project_dir)
    activity = ActivityMonitor(project_dir)

    DashboardHandler.pipeline_state = state
    DashboardHandler.activity_monitor = activity
    DashboardHandler.poll_interval = poll_interval
    DashboardHandler.popup_mode = popup

    if llm_enabled:
        DashboardHandler.llm_summarizer = LLMSummarizer(claude_local, llm_interval)

    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    # Read project name for display
    _init_state = state.read()
    _proj_label = _init_state.get("project_name", Path(project_dir).name)
    print(f"{_proj_label} Dashboard")
    print(f"  Project: {project_dir}")
    print(f"  URL:     http://localhost:{port}")
    print(f"  Poll:    {poll_interval}s")
    if not no_browser:
        print(f"  Mode:    {'popup' if popup else 'browser'}")
    if llm_enabled:
        print(f"  LLM:     enabled (every {llm_interval}s)")
    print(f"\nPress Ctrl+C to stop.\n")

    # Open browser/popup after a short delay (unless --no-browser)
    if not no_browser:
        if popup:
            def open_popup():
                time.sleep(0.5)
                # Try to open as a popup using JavaScript-capable method
                # Most browsers don't support direct popup from command line,
                # so we use a small HTML page that opens the real dashboard as popup
                popup_html = f'''data:text/html,<html><body><script>
                    var w = window.open("http://localhost:{port}", "pipeline_dashboard",
                        "width=420,height=800,menubar=no,toolbar=no,location=no,status=no,resizable=yes,scrollbars=yes");
                    if (w) {{ w.focus(); window.close(); }}
                    else {{ window.location = "http://localhost:{port}"; }}
                </script></body></html>'''
                webbrowser.open(popup_html)
            threading.Thread(target=open_popup, daemon=True).start()
        else:
            def open_browser():
                time.sleep(0.5)
                webbrowser.open(f"http://localhost:{port}")
            threading.Thread(target=open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="ATOMIC-CLAUDE Live Pipeline Progress Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example:\n  python tools/dashboard.py /path/to/project --port 8420",
    )
    parser.add_argument(
        "project_dir",
        help="Path to the target project directory (e.g., my-project)",
    )
    parser.add_argument(
        "--port", type=int, default=8420,
        help="HTTP server port (default: 8420)",
    )
    parser.add_argument(
        "--interval", type=int, default=30,
        help="Poll interval in seconds (default: 30)",
    )
    parser.add_argument(
        "--llm", action="store_true",
        help="Enable LLM-powered status summaries",
    )
    parser.add_argument(
        "--llm-interval", type=int, default=300,
        help="LLM summary generation interval in seconds (default: 300)",
    )
    parser.add_argument(
        "--claude-local", default=None,
        help="Path to claude-local wrapper (default: ../claude-local relative to project)",
    )
    parser.add_argument(
        "--popup", action="store_true",
        help="Open dashboard in a popup window with fixed dimensions (420x800)",
    )
    parser.add_argument(
        "--no-browser", action="store_true",
        help="Don't automatically open browser",
    )

    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    if not project_dir.is_dir():
        print(f"Error: project directory does not exist: {project_dir}", file=sys.stderr)
        sys.exit(1)

    claude_local = args.claude_local
    if claude_local is None and args.llm:
        # Default: sibling directory to project
        claude_local = str(project_dir.parent / "claude-local")

    run_server(
        project_dir=str(project_dir),
        port=args.port,
        poll_interval=args.interval,
        llm_enabled=args.llm,
        llm_interval=args.llm_interval,
        claude_local=claude_local,
        popup=args.popup,
        no_browser=args.no_browser,
    )


if __name__ == "__main__":
    main()
