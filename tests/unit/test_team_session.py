"""
Unit Tests for TeamSession

Tests for tmux-backed parallel agent execution with thread fallback.
All subprocess calls are mocked — no real tmux sessions are created.
"""

import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from orchestration.team_session import AgentPane, TeamResult, TeamSession


# ---------------------------------------------------------------------------
# Dataclass tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestAgentPaneDataclass:
    """Test AgentPane defaults and field access."""

    def test_agent_pane_dataclass(self):
        pane = AgentPane(agent_id="a1", pane_id="%0", command="echo hi")
        assert pane.agent_id == "a1"
        assert pane.pane_id == "%0"
        assert pane.command == "echo hi"
        assert pane.cwd is None
        assert pane.output_file is None
        assert pane.status == "pending"

    def test_agent_pane_with_all_fields(self):
        pane = AgentPane(
            agent_id="a2",
            pane_id="%1",
            command="ls",
            cwd="/tmp",
            output_file=Path("/tmp/a2.output"),
            status="running",
        )
        assert pane.cwd == "/tmp"
        assert pane.output_file == Path("/tmp/a2.output")
        assert pane.status == "running"


@pytest.mark.unit
class TestTeamResultDataclass:
    """Test TeamResult defaults and field access."""

    def test_team_result_dataclass(self):
        result = TeamResult(agent_id="a1", success=True, output="hello")
        assert result.agent_id == "a1"
        assert result.success is True
        assert result.output == "hello"
        assert result.duration == 0.0
        assert result.error is None

    def test_team_result_with_error(self):
        result = TeamResult(
            agent_id="a1",
            success=False,
            output="",
            duration=5.2,
            error="something broke",
        )
        assert result.success is False
        assert result.duration == 5.2
        assert result.error == "something broke"


# ---------------------------------------------------------------------------
# tmux availability
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestTmuxAvailability:

    @patch("orchestration.team_session.shutil.which", return_value="/usr/bin/tmux")
    def test_tmux_available_true(self, mock_which, tmp_path):
        session = TeamSession("test-sess", work_dir=tmp_path)
        assert session.tmux_available is True
        mock_which.assert_called_once_with("tmux")

    @patch("orchestration.team_session.shutil.which", return_value=None)
    def test_tmux_available_false(self, mock_which, tmp_path):
        session = TeamSession("test-sess", work_dir=tmp_path)
        assert session.tmux_available is False
        mock_which.assert_called_once_with("tmux")

    @patch("orchestration.team_session.shutil.which", return_value="/usr/bin/tmux")
    def test_tmux_available_cached(self, mock_which, tmp_path):
        session = TeamSession("test-sess", work_dir=tmp_path)
        _ = session.tmux_available
        _ = session.tmux_available
        # Only called once due to caching
        mock_which.assert_called_once()


# ---------------------------------------------------------------------------
# start()
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestStartSession:

    @patch("orchestration.team_session.subprocess.run")
    @patch("orchestration.team_session.shutil.which", return_value="/usr/bin/tmux")
    def test_start_session_success(self, mock_which, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        session = TeamSession("test-sess", work_dir=tmp_path)

        result = session.start()

        assert result is True
        assert session._session_started is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[:4] == ["tmux", "new-session", "-d", "-s"]
        assert "test-sess" in args

    @patch("orchestration.team_session.shutil.which", return_value=None)
    def test_start_session_no_tmux(self, mock_which, tmp_path):
        session = TeamSession("test-sess", work_dir=tmp_path)

        result = session.start()

        assert result is True
        assert session._session_started is False

    @patch("orchestration.team_session.subprocess.run")
    @patch("orchestration.team_session.shutil.which", return_value="/usr/bin/tmux")
    def test_start_session_failure(self, mock_which, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=1, stderr="duplicate session")
        session = TeamSession("test-sess", work_dir=tmp_path)

        result = session.start()

        assert result is True  # graceful fallback
        assert session._session_started is False
        assert session._tmux_available is False

    @patch("orchestration.team_session.subprocess.run", side_effect=OSError("no tmux"))
    @patch("orchestration.team_session.shutil.which", return_value="/usr/bin/tmux")
    def test_start_session_os_error(self, mock_which, mock_run, tmp_path):
        session = TeamSession("test-sess", work_dir=tmp_path)

        result = session.start()

        assert result is True
        assert session._tmux_available is False


# ---------------------------------------------------------------------------
# add_agent()
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestAddAgent:

    @patch("orchestration.team_session.subprocess.run")
    @patch("orchestration.team_session.shutil.which", return_value="/usr/bin/tmux")
    def test_add_agent_first_pane(self, mock_which, mock_run, tmp_path):
        """First agent uses send-keys to the initial pane (no split)."""
        mock_run.return_value = MagicMock(returncode=0, stdout="%0", stderr="")
        session = TeamSession("test-sess", work_dir=tmp_path)
        session._session_started = True

        pane = session.add_agent("agent-1", "echo hello")

        assert pane is not None
        assert pane.agent_id == "agent-1"
        assert pane.status == "running"
        assert pane.output_file == tmp_path / "agent-1.output"
        # First call should be send-keys, second display-message
        calls = mock_run.call_args_list
        assert any("send-keys" in str(c) for c in calls)
        # No split-window for first pane
        assert not any("split-window" in str(c) for c in calls)

    @patch("orchestration.team_session.subprocess.run")
    @patch("orchestration.team_session.shutil.which", return_value="/usr/bin/tmux")
    def test_add_agent_splits_pane(self, mock_which, mock_run, tmp_path):
        """Subsequent agents use split-window."""
        mock_run.return_value = MagicMock(returncode=0, stdout="%1", stderr="")
        session = TeamSession("test-sess", work_dir=tmp_path)
        session._session_started = True
        # Simulate first agent already added
        session._panes["agent-0"] = AgentPane(
            agent_id="agent-0", pane_id="%0", command="echo first"
        )

        pane = session.add_agent("agent-1", "echo second")

        assert pane is not None
        assert pane.agent_id == "agent-1"
        calls = mock_run.call_args_list
        assert any("split-window" in str(c) for c in calls)
        assert any("select-layout" in str(c) for c in calls)

    @patch("orchestration.team_session.shutil.which", return_value=None)
    def test_add_agent_fallback_mode(self, mock_which, tmp_path):
        """tmux unavailable: pane tracked with 'fallback' id."""
        session = TeamSession("test-sess", work_dir=tmp_path)

        pane = session.add_agent("agent-1", "echo hello", cwd="/tmp")

        assert pane is not None
        assert pane.pane_id == "fallback"
        assert pane.agent_id == "agent-1"
        assert pane.command == "echo hello"
        assert pane.cwd == "/tmp"
        assert "agent-1" in session._panes

    @patch("orchestration.team_session.subprocess.run", side_effect=OSError("fail"))
    @patch("orchestration.team_session.shutil.which", return_value="/usr/bin/tmux")
    def test_add_agent_exception(self, mock_which, mock_run, tmp_path):
        """On subprocess error, agent tracked with 'failed' pane id."""
        session = TeamSession("test-sess", work_dir=tmp_path)
        session._session_started = True

        pane = session.add_agent("agent-1", "echo hello")

        assert pane is not None
        assert pane.pane_id == "failed"


# ---------------------------------------------------------------------------
# run_all() — fallback path
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestRunFallback:

    @patch("orchestration.team_session.subprocess.run")
    @patch("orchestration.team_session.shutil.which", return_value=None)
    def test_run_fallback(self, mock_which, mock_run, tmp_path):
        """Fallback uses ThreadPoolExecutor and returns results."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="output-data", stderr=""
        )
        session = TeamSession("test-sess", work_dir=tmp_path)
        session.add_agent("a1", "echo one")
        session.add_agent("a2", "echo two")

        results = session.run_all(timeout=10)

        assert len(results) == 2
        assert "a1" in results
        assert "a2" in results
        assert results["a1"].success is True
        assert results["a1"].output == "output-data"
        assert results["a1"].duration > 0
        assert results["a1"].error is None

    @patch("orchestration.team_session.subprocess.run")
    @patch("orchestration.team_session.shutil.which", return_value=None)
    def test_run_fallback_timeout(self, mock_which, mock_run, tmp_path):
        """Agent that exceeds timeout gets a timeout error."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="echo", timeout=1)
        session = TeamSession("test-sess", work_dir=tmp_path)
        session.add_agent("slow-agent", "sleep 999")

        results = session.run_all(timeout=1)

        assert len(results) == 1
        assert results["slow-agent"].success is False
        assert "Timed out" in results["slow-agent"].error

    @patch("orchestration.team_session.subprocess.run")
    @patch("orchestration.team_session.shutil.which", return_value=None)
    def test_run_fallback_failure(self, mock_which, mock_run, tmp_path):
        """Non-zero exit code marks result as failed."""
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="command not found"
        )
        session = TeamSession("test-sess", work_dir=tmp_path)
        session.add_agent("bad-agent", "nonexistent-cmd")

        results = session.run_all(timeout=10)

        assert results["bad-agent"].success is False
        assert results["bad-agent"].error == "command not found"

    @patch("orchestration.team_session.subprocess.run")
    @patch("orchestration.team_session.shutil.which", return_value=None)
    def test_run_fallback_exception(self, mock_which, mock_run, tmp_path):
        """Generic exception in subprocess is caught."""
        mock_run.side_effect = RuntimeError("unexpected")
        session = TeamSession("test-sess", work_dir=tmp_path)
        session.add_agent("err-agent", "echo boom")

        results = session.run_all(timeout=10)

        assert results["err-agent"].success is False
        assert "unexpected" in results["err-agent"].error


# ---------------------------------------------------------------------------
# run_all() — tmux monitor path
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestMonitorTmux:

    def test_monitor_tmux_completion(self, tmp_path):
        """Output files with ---DONE--- marker trigger completion."""
        session = TeamSession("test-sess", work_dir=tmp_path)
        session._tmux_available = True
        session._session_started = True

        # Pre-create output files with done markers
        out_a = tmp_path / "agent-a.output"
        out_b = tmp_path / "agent-b.output"
        out_a.write_text("result from a\n---DONE---\n")
        out_b.write_text("result from b\n---DONE---\n")

        session._panes = {
            "agent-a": AgentPane(
                agent_id="agent-a", pane_id="%0", command="echo a",
                output_file=out_a, status="running",
            ),
            "agent-b": AgentPane(
                agent_id="agent-b", pane_id="%1", command="echo b",
                output_file=out_b, status="running",
            ),
        }

        results = session.run_all(timeout=5)

        assert len(results) == 2
        assert results["agent-a"].success is True
        assert "result from a" in results["agent-a"].output
        assert results["agent-b"].success is True
        assert "result from b" in results["agent-b"].output
        assert session._panes["agent-a"].status == "done"
        assert session._panes["agent-b"].status == "done"

    @patch("orchestration.team_session.time.sleep")
    def test_monitor_tmux_timeout(self, mock_sleep, tmp_path):
        """Agents that never produce ---DONE--- are marked as timed out."""
        session = TeamSession("test-sess", work_dir=tmp_path)
        session._tmux_available = True
        session._session_started = True

        # Output file exists but never gets done marker
        out = tmp_path / "stuck.output"
        out.write_text("partial output...")

        session._panes = {
            "stuck": AgentPane(
                agent_id="stuck", pane_id="%0", command="sleep 999",
                output_file=out, status="running",
            ),
        }

        # Use a very short timeout so test doesn't actually wait
        # We need to advance monotonic time. Patch time.monotonic.
        call_count = [0]
        base_time = time.monotonic()

        def advancing_monotonic():
            call_count[0] += 1
            # After first couple calls, jump past timeout
            if call_count[0] > 3:
                return base_time + 100
            return base_time

        with patch("orchestration.team_session.time.monotonic", side_effect=advancing_monotonic):
            results = session.run_all(timeout=5)

        assert len(results) == 1
        assert results["stuck"].success is False
        assert "Timed out" in results["stuck"].error
        assert session._panes["stuck"].status == "failed"


# ---------------------------------------------------------------------------
# get_results()
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetResults:

    def test_get_results(self, tmp_path):
        """get_results returns a copy of results dict."""
        session = TeamSession("test-sess", work_dir=tmp_path)
        original = {
            "a1": TeamResult(agent_id="a1", success=True, output="ok"),
        }
        session._results = original

        returned = session.get_results()

        assert returned == original
        # Should be a copy, not the same object
        assert returned is not session._results

    def test_get_results_empty(self, tmp_path):
        """get_results returns empty dict before any run."""
        session = TeamSession("test-sess", work_dir=tmp_path)
        assert session.get_results() == {}


# ---------------------------------------------------------------------------
# shutdown()
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestShutdown:

    @patch("orchestration.team_session.subprocess.run")
    def test_shutdown_kills_session(self, mock_run, tmp_path):
        """Shutdown calls tmux kill-session."""
        mock_run.return_value = MagicMock(returncode=0)
        session = TeamSession("test-sess", work_dir=tmp_path)
        session._tmux_available = True
        session._session_started = True
        session._panes["a1"] = AgentPane(
            agent_id="a1", pane_id="%0", command="echo hi"
        )

        session.shutdown()

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args == ["tmux", "kill-session", "-t", "test-sess"]
        assert session._session_started is False
        assert len(session._panes) == 0
        assert len(session._results) == 0

    def test_shutdown_cleans_files(self, tmp_path):
        """Shutdown removes .output files from work_dir."""
        # Create some output files
        (tmp_path / "agent-a.output").write_text("data")
        (tmp_path / "agent-b.output").write_text("data")
        (tmp_path / "unrelated.txt").write_text("keep me")

        session = TeamSession("test-sess", work_dir=tmp_path)
        session._tmux_available = False  # skip tmux kill
        session._panes["a"] = AgentPane(agent_id="a", pane_id="x", command="echo")

        session.shutdown()

        assert not (tmp_path / "agent-a.output").exists()
        assert not (tmp_path / "agent-b.output").exists()
        # Non-.output files are not removed
        assert (tmp_path / "unrelated.txt").exists()

    @patch("orchestration.team_session.subprocess.run", side_effect=OSError("gone"))
    def test_shutdown_tolerates_tmux_error(self, mock_run, tmp_path):
        """Shutdown handles tmux kill-session failure gracefully."""
        session = TeamSession("test-sess", work_dir=tmp_path)
        session._tmux_available = True
        session._session_started = True

        # Should not raise
        session.shutdown()

        assert session._session_started is False

    def test_shutdown_no_tmux_session(self, tmp_path):
        """Shutdown with no tmux session skips kill-session."""
        session = TeamSession("test-sess", work_dir=tmp_path)
        session._tmux_available = False
        session._session_started = False

        # Should not raise
        session.shutdown()
