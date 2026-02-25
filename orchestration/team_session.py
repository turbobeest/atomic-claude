"""
Agent Team Session — tmux-backed parallel agent execution with live monitoring.

Provides visual multi-agent orchestration using tmux panes.
Each agent runs in its own pane within a tmux window, allowing
the operator to observe all agents working simultaneously.

Falls back to ThreadPoolExecutor when tmux is unavailable.
"""

import logging
import os
import shlex
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class AgentPane:
    """Tracks one agent's tmux pane."""
    agent_id: str
    pane_id: str         # tmux pane identifier (e.g. "%3")
    command: str         # Command being executed
    cwd: Optional[str] = None
    output_file: Optional[Path] = None  # File for capturing output
    status: str = "pending"  # pending, running, done, failed


@dataclass
class TeamResult:
    """Result from a single agent in a team run."""
    agent_id: str
    success: bool
    output: str
    duration: float = 0.0
    error: Optional[str] = None


class TeamSession:
    """Manages a tmux session for parallel agent execution.

    Creates a tmux session with one window, splits into panes
    for each agent. Monitors completion and collects results.

    Falls back to ThreadPoolExecutor if tmux is not available.

    Args:
        session_name: tmux session name (must be unique)
        work_dir: Directory for temporary files (output capture)
    """

    def __init__(self, session_name: str, work_dir: Optional[Path] = None):
        self.session_name = session_name
        self.work_dir = work_dir or Path(tempfile.mkdtemp(prefix="team-"))
        self._panes: Dict[str, AgentPane] = {}
        self._results: Dict[str, TeamResult] = {}
        self._tmux_available: Optional[bool] = None
        self._session_started = False

    @property
    def tmux_available(self) -> bool:
        """Check if tmux is available on this system."""
        if self._tmux_available is None:
            self._tmux_available = shutil.which("tmux") is not None
        return self._tmux_available

    def start(self) -> bool:
        """Start the tmux session.

        Returns:
            True if session started (or tmux unavailable — will use fallback)
        """
        if not self.tmux_available:
            logger.info("tmux not available — running agents in parallel threads")
            return True

        try:
            # Create detached session
            result = subprocess.run(
                ["tmux", "new-session", "-d", "-s", self.session_name,
                 "-x", "200", "-y", "50"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                logger.warning("Failed to start tmux session: %s", result.stderr.strip())
                self._tmux_available = False
                return True  # Will use fallback

            self._session_started = True
            logger.info("Started tmux session: %s", self.session_name)
            return True

        except (subprocess.SubprocessError, OSError) as e:
            logger.warning("tmux session start failed: %s", e)
            self._tmux_available = False
            return True  # Will use fallback

    def add_agent(self, agent_id: str, command: str,
                  cwd: Optional[str] = None) -> Optional[AgentPane]:
        """Add an agent pane to the session.

        Args:
            agent_id: Unique agent identifier
            command: Shell command to execute
            cwd: Working directory for the command

        Returns:
            AgentPane if added, None on failure
        """
        output_file = self.work_dir / f"{agent_id}.output"

        if not self.tmux_available or not self._session_started:
            # Track for fallback execution
            pane = AgentPane(
                agent_id=agent_id,
                pane_id="fallback",
                command=command,
                cwd=cwd,
                output_file=output_file,
            )
            self._panes[agent_id] = pane
            return pane

        # Wrap command to capture output (use shlex.quote for safety)
        quoted_output = shlex.quote(str(output_file))
        wrapped_cmd = f"({command}) > {quoted_output} 2>&1; echo '---DONE---' >> {quoted_output}"
        if cwd:
            wrapped_cmd = f"cd {shlex.quote(cwd)} && {wrapped_cmd}"

        try:
            if len(self._panes) == 0:
                # Use the initial pane (send command to it)
                result = subprocess.run(
                    ["tmux", "send-keys", "-t", self.session_name, wrapped_cmd, "Enter"],
                    capture_output=True, text=True, timeout=10,
                )
                # Get the pane ID
                id_result = subprocess.run(
                    ["tmux", "display-message", "-t", self.session_name, "-p", "#{pane_id}"],
                    capture_output=True, text=True, timeout=5,
                )
                pane_id = id_result.stdout.strip() if id_result.returncode == 0 else "%0"
            else:
                # Split and send
                split_result = subprocess.run(
                    ["tmux", "split-window", "-t", self.session_name, "-h"],
                    capture_output=True, text=True, timeout=10,
                )
                if split_result.returncode != 0:
                    # Try vertical split if horizontal fails
                    split_result = subprocess.run(
                        ["tmux", "split-window", "-t", self.session_name, "-v"],
                        capture_output=True, text=True, timeout=10,
                    )

                # Get new pane ID
                id_result = subprocess.run(
                    ["tmux", "display-message", "-t", self.session_name, "-p", "#{pane_id}"],
                    capture_output=True, text=True, timeout=5,
                )
                pane_id = id_result.stdout.strip() if id_result.returncode == 0 else f"%{len(self._panes)}"

                # Send command
                subprocess.run(
                    ["tmux", "send-keys", "-t", f"{self.session_name}:{pane_id}",
                     wrapped_cmd, "Enter"],
                    capture_output=True, text=True, timeout=10,
                )

                # Rebalance layout
                subprocess.run(
                    ["tmux", "select-layout", "-t", self.session_name, "tiled"],
                    capture_output=True, text=True, timeout=5,
                )

            pane = AgentPane(
                agent_id=agent_id,
                pane_id=pane_id,
                command=command,
                cwd=cwd,
                output_file=output_file,
                status="running",
            )
            self._panes[agent_id] = pane
            return pane

        except (subprocess.SubprocessError, OSError) as e:
            logger.warning("Failed to add agent pane %s: %s", agent_id, e)
            return None

    def run_all(self, timeout: int = 600) -> Dict[str, TeamResult]:
        """Execute all agents and wait for completion.

        If tmux is available and session started, agents are already running
        in panes — this monitors them. Otherwise, runs via ThreadPoolExecutor.

        Args:
            timeout: Maximum seconds to wait for all agents

        Returns:
            Dict mapping agent_id to TeamResult
        """
        if not self.tmux_available or not self._session_started:
            return self._run_fallback(timeout)

        return self._monitor_tmux(timeout)

    def _run_fallback(self, timeout: int) -> Dict[str, TeamResult]:
        """Run agents via ThreadPoolExecutor (no tmux)."""
        results: Dict[str, TeamResult] = {}

        def _execute_agent(pane: AgentPane) -> TeamResult:
            start = time.monotonic()
            try:
                # Use shell=False with shlex.split for simple commands;
                # fall back to shell=True only for compound commands (pipes, &&, etc.)
                cmd = pane.command
                use_shell = any(c in cmd for c in ('|', '&&', '||', ';', '>', '<'))
                if use_shell:
                    # Command requires shell interpretation
                    run_cmd = cmd
                else:
                    run_cmd = shlex.split(cmd)
                proc = subprocess.run(
                    run_cmd,
                    shell=use_shell,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=pane.cwd,
                )
                duration = time.monotonic() - start

                output = proc.stdout
                if pane.output_file:
                    pane.output_file.write_text(output)

                return TeamResult(
                    agent_id=pane.agent_id,
                    success=proc.returncode == 0,
                    output=output,
                    duration=duration,
                    error=proc.stderr if proc.returncode != 0 else None,
                )
            except subprocess.TimeoutExpired:
                return TeamResult(
                    agent_id=pane.agent_id,
                    success=False,
                    output="",
                    duration=time.monotonic() - start,
                    error=f"Timed out after {timeout}s",
                )
            except Exception as e:
                return TeamResult(
                    agent_id=pane.agent_id,
                    success=False,
                    output="",
                    duration=time.monotonic() - start,
                    error=str(e),
                )

        max_workers = min(len(self._panes), 4)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_execute_agent, pane): agent_id
                for agent_id, pane in self._panes.items()
            }
            for future in as_completed(futures):
                agent_id = futures[future]
                try:
                    result = future.result()
                except Exception as e:
                    result = TeamResult(
                        agent_id=agent_id,
                        success=False,
                        output="",
                        error=str(e),
                    )
                results[agent_id] = result

        self._results = results
        return results

    def _monitor_tmux(self, timeout: int) -> Dict[str, TeamResult]:
        """Monitor tmux panes for completion by checking output files."""
        results: Dict[str, TeamResult] = {}
        start_time = time.monotonic()
        pending = set(self._panes.keys())

        # Track file sizes for stability check (Finding #21)
        prev_sizes: Dict[str, int] = {}

        while pending and (time.monotonic() - start_time) < timeout:
            for agent_id in list(pending):
                pane = self._panes[agent_id]
                if pane.output_file and pane.output_file.exists():
                    try:
                        current_size = pane.output_file.stat().st_size
                    except OSError:
                        continue
                    prev_size = prev_sizes.get(agent_id, -1)
                    prev_sizes[agent_id] = current_size

                    # Only read when file size has stabilized (same as previous check)
                    if current_size > 0 and current_size == prev_size:
                        content = pane.output_file.read_text()
                        if "---DONE---" in content:
                            # Agent finished
                            output = content.replace("---DONE---", "").strip()
                            duration = time.monotonic() - start_time
                            results[agent_id] = TeamResult(
                                agent_id=agent_id,
                                success=True,  # We can't know return code from tmux easily
                                output=output,
                                duration=duration,
                            )
                            pane.status = "done"
                            pending.discard(agent_id)

            if pending:
                time.sleep(1.0)

        # Handle timeouts
        for agent_id in pending:
            results[agent_id] = TeamResult(
                agent_id=agent_id,
                success=False,
                output="",
                duration=timeout,
                error=f"Timed out after {timeout}s",
            )
            self._panes[agent_id].status = "failed"

        self._results = results
        return results

    def get_results(self) -> Dict[str, TeamResult]:
        """Return collected results from the last run."""
        return dict(self._results)

    def shutdown(self) -> None:
        """Kill the tmux session and clean up."""
        if self._session_started and self.tmux_available:
            try:
                subprocess.run(
                    ["tmux", "kill-session", "-t", self.session_name],
                    capture_output=True, text=True, timeout=10,
                )
            except (subprocess.SubprocessError, OSError):
                pass
            self._session_started = False

        # Clean up output files and temp directory
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir, ignore_errors=True)

        self._panes.clear()
        self._results.clear()
        logger.info("Team session %s shut down", self.session_name)
