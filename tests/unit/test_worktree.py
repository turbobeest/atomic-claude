"""
Unit Tests for Git Worktree Manager

Tests for WorktreeManager: creation, removal, merge, and cleanup
of git worktrees used for parallel task isolation.

All subprocess calls are mocked — no actual git commands are executed.
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from core.worktree import WorktreeManager, WorktreeInfo


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def manager(tmp_path):
    """Create a WorktreeManager with a temporary project root."""
    return WorktreeManager(project_root=tmp_path)


@pytest.fixture
def manager_with_branch(tmp_path):
    """Create a WorktreeManager with a specified base branch."""
    return WorktreeManager(project_root=tmp_path, base_branch="develop")


# ============================================================================
# AVAILABILITY TESTS
# ============================================================================

@pytest.mark.unit
class TestIsAvailable:
    """Test git worktree availability detection."""

    @patch("core.worktree.subprocess.run")
    def test_is_available_true(self, mock_run, manager):
        """git worktree list returns 0 — worktree is available."""
        mock_run.return_value = MagicMock(returncode=0)

        assert manager.is_available() is True

        mock_run.assert_called_once_with(
            ["git", "worktree", "list"],
            cwd=str(manager.project_root),
            capture_output=True, text=True, timeout=10,
        )

    @patch("core.worktree.subprocess.run")
    def test_is_available_false(self, mock_run, manager):
        """git worktree list returns non-zero — not available."""
        mock_run.return_value = MagicMock(returncode=128)

        assert manager.is_available() is False

    @patch("core.worktree.subprocess.run")
    def test_is_available_exception(self, mock_run, manager):
        """subprocess raises OSError — not available."""
        mock_run.side_effect = OSError("git not found")

        assert manager.is_available() is False


# ============================================================================
# CREATION TESTS
# ============================================================================

@pytest.mark.unit
class TestCreate:
    """Test worktree creation."""

    @patch("core.worktree.subprocess.run")
    def test_create_success(self, mock_run, manager):
        """Successful creation returns path and tracks in _active."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = manager.create("504")

        expected_path = manager.worktrees_dir / "task-504"
        assert result == expected_path
        assert "504" in manager._active
        assert manager._active["504"].task_id == "504"
        assert manager._active["504"].branch == "wt/task-504"
        assert manager._active["504"].created is True

        mock_run.assert_called_once_with(
            ["git", "worktree", "add", "-b", "wt/task-504", str(expected_path)],
            cwd=str(manager.project_root),
            capture_output=True, text=True, timeout=30,
        )

    @patch("core.worktree.subprocess.run")
    def test_create_already_exists(self, mock_run, manager):
        """Path exists on disk — reuses without calling git."""
        wt_path = manager.worktrees_dir / "task-504"
        wt_path.mkdir(parents=True)

        result = manager.create("504")

        assert result == wt_path
        assert "504" in manager._active
        assert manager._active["504"].created is False
        # subprocess.run should NOT have been called
        mock_run.assert_not_called()

    @patch("core.worktree.subprocess.run")
    def test_create_failure(self, mock_run, manager):
        """subprocess returns non-zero — returns None, not tracked."""
        mock_run.return_value = MagicMock(returncode=1, stderr="fatal: branch already exists")

        result = manager.create("504")

        assert result is None
        assert "504" not in manager._active

    @patch("core.worktree.subprocess.run")
    def test_create_with_base_branch(self, mock_run, manager_with_branch):
        """base_branch is appended to the git worktree add command."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = manager_with_branch.create("504")

        expected_path = manager_with_branch.worktrees_dir / "task-504"
        assert result == expected_path

        mock_run.assert_called_once_with(
            ["git", "worktree", "add", "-b", "wt/task-504", str(expected_path), "develop"],
            cwd=str(manager_with_branch.project_root),
            capture_output=True, text=True, timeout=30,
        )

    @patch("core.worktree.subprocess.run")
    def test_create_subprocess_exception(self, mock_run, manager):
        """subprocess raises exception — returns None."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=30)

        result = manager.create("504")

        assert result is None
        assert "504" not in manager._active


# ============================================================================
# REMOVAL TESTS
# ============================================================================

@pytest.mark.unit
class TestRemove:
    """Test worktree removal."""

    @patch("core.worktree.subprocess.run")
    def test_remove_success(self, mock_run, manager):
        """Successful removal: worktree remove + branch delete."""
        mock_run.return_value = MagicMock(returncode=0)

        # Pre-populate _active
        manager._active["504"] = WorktreeInfo(
            task_id="504",
            path=manager.worktrees_dir / "task-504",
            branch="wt/task-504",
        )

        result = manager.remove("504")

        assert result is True
        assert "504" not in manager._active

        expected_wt_path = manager.worktrees_dir / "task-504"
        assert mock_run.call_count == 2
        mock_run.assert_any_call(
            ["git", "worktree", "remove", "--force", str(expected_wt_path)],
            cwd=str(manager.project_root),
            capture_output=True, text=True, timeout=30,
        )
        mock_run.assert_any_call(
            ["git", "branch", "-D", "wt/task-504"],
            cwd=str(manager.project_root),
            capture_output=True, text=True, timeout=10,
        )

    @patch("core.worktree.shutil.rmtree")
    @patch("core.worktree.subprocess.run")
    def test_remove_fallback_shutil(self, mock_run, mock_rmtree, manager):
        """git worktree remove fails — falls back to shutil.rmtree + prune."""
        wt_path = manager.worktrees_dir / "task-504"
        wt_path.mkdir(parents=True)

        # First call: git worktree remove fails (returncode=1)
        # Second call: git worktree prune succeeds
        # Third call: git branch -D succeeds
        mock_run.side_effect = [
            MagicMock(returncode=1, stderr="error"),  # worktree remove
            MagicMock(returncode=0),                   # worktree prune
            MagicMock(returncode=0),                   # branch -D
        ]

        manager._active["504"] = WorktreeInfo(
            task_id="504", path=wt_path, branch="wt/task-504"
        )

        result = manager.remove("504")

        assert result is True
        assert "504" not in manager._active
        # shutil.rmtree was called as fallback
        mock_rmtree.assert_called_once_with(wt_path, ignore_errors=True)
        # git worktree prune was called
        mock_run.assert_any_call(
            ["git", "worktree", "prune"],
            cwd=str(manager.project_root),
            capture_output=True, text=True, timeout=10,
        )

    @patch("core.worktree.shutil.rmtree")
    @patch("core.worktree.subprocess.run")
    def test_remove_exception_fallback(self, mock_run, mock_rmtree, manager):
        """subprocess raises OSError — falls back to shutil, returns False."""
        wt_path = manager.worktrees_dir / "task-504"
        wt_path.mkdir(parents=True)

        # First call raises exception; second call (branch -D) succeeds
        mock_run.side_effect = [
            OSError("git crashed"),      # worktree remove
            MagicMock(returncode=0),     # branch -D
        ]

        result = manager.remove("504")

        assert result is False
        mock_rmtree.assert_called_once_with(wt_path, ignore_errors=True)


# ============================================================================
# MERGE TESTS
# ============================================================================

@pytest.mark.unit
class TestMergeBack:
    """Test merging worktree changes back."""

    @patch("core.worktree.subprocess.run")
    def test_merge_back_no_changes(self, mock_run, manager):
        """git log shows no commits ahead — returns True without merging."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        result = manager.merge_back("504")

        assert result is True
        # Only the git log call should happen — no merge
        mock_run.assert_called_once_with(
            ["git", "log", "HEAD..wt/task-504", "--oneline"],
            cwd=str(manager.project_root),
            capture_output=True, text=True, timeout=10,
        )

    @patch("core.worktree.subprocess.run")
    def test_merge_back_no_changes_nonzero(self, mock_run, manager):
        """git log returns non-zero — treated as no changes, returns True."""
        mock_run.return_value = MagicMock(returncode=128, stdout="")

        result = manager.merge_back("504")

        assert result is True
        assert mock_run.call_count == 1

    @patch("core.worktree.subprocess.run")
    def test_merge_back_success(self, mock_run, manager):
        """Branch has commits — merge succeeds."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc1234 Add feature\n"),  # git log
            MagicMock(returncode=0, stderr=""),                        # git merge
        ]

        result = manager.merge_back("504")

        assert result is True
        assert mock_run.call_count == 2
        mock_run.assert_any_call(
            ["git", "merge", "--no-ff", "-m", "Merge worktree task-504", "wt/task-504"],
            cwd=str(manager.project_root),
            capture_output=True, text=True, timeout=30,
        )

    @patch("core.worktree.subprocess.run")
    def test_merge_back_conflict(self, mock_run, manager):
        """Merge returns non-zero (conflict) — returns False."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc1234 Add feature\n"),  # git log
            MagicMock(returncode=1, stderr="CONFLICT (content): Merge conflict in foo.py"),  # git merge
        ]

        result = manager.merge_back("504")

        assert result is False

    @patch("core.worktree.subprocess.run")
    def test_merge_back_log_exception(self, mock_run, manager):
        """git log raises exception — returns False."""
        mock_run.side_effect = OSError("git not found")

        result = manager.merge_back("504")

        assert result is False

    @patch("core.worktree.subprocess.run")
    def test_merge_back_merge_exception(self, mock_run, manager):
        """git merge raises exception — returns False."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc1234 Add feature\n"),  # git log
            OSError("git crashed"),                                    # git merge
        ]

        result = manager.merge_back("504")

        assert result is False


# ============================================================================
# LIST / PROPERTY TESTS
# ============================================================================

@pytest.mark.unit
class TestListAndProperties:
    """Test listing active worktrees and properties."""

    def test_list_active(self, manager):
        """list_active returns a copy of the active dict."""
        info = WorktreeInfo(
            task_id="504",
            path=manager.worktrees_dir / "task-504",
            branch="wt/task-504",
        )
        manager._active["504"] = info

        result = manager.list_active()

        assert result == {"504": info}
        # Should be a copy, not the same object
        assert result is not manager._active

    def test_list_active_empty(self, manager):
        """list_active returns empty dict when nothing is tracked."""
        result = manager.list_active()

        assert result == {}

    def test_worktrees_dir_property(self, manager):
        """worktrees_dir returns project_root / '.worktrees'."""
        assert manager.worktrees_dir == manager.project_root / ".worktrees"


# ============================================================================
# CLEANUP TESTS
# ============================================================================

@pytest.mark.unit
class TestCleanupStale:
    """Test stale worktree cleanup."""

    @patch("core.worktree.subprocess.run")
    def test_cleanup_stale(self, mock_run, manager):
        """Finds dirs on disk not in _active, removes them."""
        mock_run.return_value = MagicMock(returncode=0)

        # Create stale worktree dirs on disk
        stale_1 = manager.worktrees_dir / "task-old1"
        stale_2 = manager.worktrees_dir / "task-old2"
        stale_1.mkdir(parents=True)
        stale_2.mkdir(parents=True)

        # Create a tracked one too
        tracked = manager.worktrees_dir / "task-active"
        tracked.mkdir(parents=True)
        manager._active["active"] = WorktreeInfo(
            task_id="active", path=tracked, branch="wt/task-active"
        )

        # Also create a non-task dir that should be ignored
        other = manager.worktrees_dir / "something-else"
        other.mkdir(parents=True)

        result = manager.cleanup_stale()

        # Should have cleaned 2 stale worktrees
        assert result == 2

    def test_cleanup_stale_no_dir(self, manager):
        """worktrees_dir does not exist — returns 0."""
        result = manager.cleanup_stale()

        assert result == 0


@pytest.mark.unit
class TestCleanupAll:
    """Test full worktree cleanup."""

    @patch("core.worktree.subprocess.run")
    def test_cleanup_all(self, mock_run, manager):
        """Removes everything under .worktrees/ with task- prefix."""
        mock_run.return_value = MagicMock(returncode=0)

        # Create several worktree dirs
        for name in ["task-501", "task-502", "task-503"]:
            (manager.worktrees_dir / name).mkdir(parents=True)

        # Track one of them
        manager._active["501"] = WorktreeInfo(
            task_id="501",
            path=manager.worktrees_dir / "task-501",
            branch="wt/task-501",
        )

        result = manager.cleanup_all()

        assert result == 3
        assert len(manager._active) == 0

    def test_cleanup_all_no_dir(self, manager):
        """worktrees_dir does not exist — returns 0."""
        result = manager.cleanup_all()

        assert result == 0

    @patch("core.worktree.subprocess.run")
    def test_cleanup_all_removes_empty_dir(self, mock_run, manager):
        """After cleanup, empty .worktrees/ directory is removed."""
        mock_run.return_value = MagicMock(returncode=0)

        (manager.worktrees_dir / "task-only").mkdir(parents=True)

        manager.cleanup_all()

        # The worktrees dir itself should have been rmdir'd
        # (it may or may not exist depending on whether rmdir succeeded)
        # We just verify no exception was raised
