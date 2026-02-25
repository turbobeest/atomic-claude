"""
Git Worktree Manager — Isolated working directories for parallel tasks.

Provides safe parallel execution by giving each task its own worktree
(a lightweight clone of the repo with shared .git objects).
Used by Phase 5 TDD execution to avoid file conflicts between
concurrent Claude Code invocations.
"""

import logging
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class WorktreeInfo:
    """Metadata for an active worktree."""
    task_id: str
    path: Path
    branch: str
    created: bool = True


class WorktreeManager:
    """Manages git worktrees for parallel task isolation.

    Each task gets its own worktree under {project_root}/.worktrees/task-{id}.
    Worktrees share .git objects with the main repo (disk-efficient).

    Args:
        project_root: Path to the project repository root
        base_branch: Branch to create worktrees from (default: current HEAD)
    """

    def __init__(self, project_root: Path, base_branch: Optional[str] = None):
        self.project_root = project_root
        self.base_branch = base_branch
        self._worktrees_dir = project_root / ".worktrees"
        self._active: Dict[str, WorktreeInfo] = {}

    @property
    def worktrees_dir(self) -> Path:
        return self._worktrees_dir

    def is_available(self) -> bool:
        """Check if git worktree is supported in this repo."""
        try:
            result = subprocess.run(
                ["git", "worktree", "list"],
                cwd=str(self.project_root),
                capture_output=True, text=True, timeout=10,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, OSError):
            return False

    def create(self, task_id: str) -> Optional[Path]:
        """Create an isolated worktree for a task.

        Args:
            task_id: Unique task identifier

        Returns:
            Path to the worktree, or None on failure
        """
        wt_path = self._worktrees_dir / f"task-{task_id}"
        branch_name = f"wt/task-{task_id}"

        if wt_path.exists():
            # Already exists — reuse
            logger.debug("Worktree already exists for task %s", task_id)
            info = WorktreeInfo(task_id=task_id, path=wt_path, branch=branch_name, created=False)
            self._active[task_id] = info
            return wt_path

        self._worktrees_dir.mkdir(parents=True, exist_ok=True)

        # Build the git worktree add command
        cmd = ["git", "worktree", "add", "-b", branch_name, str(wt_path)]
        if self.base_branch:
            cmd.append(self.base_branch)

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                logger.warning("Failed to create worktree for task %s: %s", task_id, result.stderr.strip())
                return None

            info = WorktreeInfo(task_id=task_id, path=wt_path, branch=branch_name)
            self._active[task_id] = info
            logger.info("Created worktree for task %s at %s", task_id, wt_path)
            return wt_path

        except (subprocess.SubprocessError, OSError) as e:
            logger.warning("Worktree creation failed for task %s: %s", task_id, e)
            return None

    def remove(self, task_id: str) -> bool:
        """Remove a task's worktree and its branch.

        Args:
            task_id: Task identifier

        Returns:
            True if removed successfully
        """
        wt_path = self._worktrees_dir / f"task-{task_id}"
        branch_name = f"wt/task-{task_id}"

        success = True

        # Remove the worktree
        try:
            result = subprocess.run(
                ["git", "worktree", "remove", "--force", str(wt_path)],
                cwd=str(self.project_root),
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                # Fallback: manual removal
                if wt_path.exists():
                    shutil.rmtree(wt_path, ignore_errors=True)
                # Prune stale worktree refs
                subprocess.run(
                    ["git", "worktree", "prune"],
                    cwd=str(self.project_root),
                    capture_output=True, text=True, timeout=10,
                )
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Worktree removal issue for task %s: %s", task_id, e)
            if wt_path.exists():
                shutil.rmtree(wt_path, ignore_errors=True)
            success = False

        # Delete the temporary branch
        try:
            subprocess.run(
                ["git", "branch", "-D", branch_name],
                cwd=str(self.project_root),
                capture_output=True, text=True, timeout=10,
            )
        except (subprocess.SubprocessError, OSError):
            pass  # Branch may already be gone

        self._active.pop(task_id, None)
        return success

    def merge_back(self, task_id: str) -> bool:
        """Merge a task's worktree changes back to the base branch.

        Performs a no-ff merge of the worktree branch into the current branch.

        Args:
            task_id: Task identifier

        Returns:
            True if merge succeeded (or no changes to merge)
        """
        branch_name = f"wt/task-{task_id}"

        # Check if branch has any commits ahead
        try:
            result = subprocess.run(
                ["git", "log", f"HEAD..{branch_name}", "--oneline"],
                cwd=str(self.project_root),
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0 or not result.stdout.strip():
                logger.debug("No changes to merge for task %s", task_id)
                return True
        except (subprocess.SubprocessError, OSError):
            return False

        # Merge
        try:
            result = subprocess.run(
                ["git", "merge", "--no-ff", "-m", f"Merge worktree task-{task_id}", branch_name],
                cwd=str(self.project_root),
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                logger.warning("Merge failed for task %s: %s", task_id, result.stderr.strip())
                return False
            return True
        except (subprocess.SubprocessError, OSError) as e:
            logger.warning("Merge failed for task %s: %s", task_id, e)
            return False

    def list_active(self) -> Dict[str, WorktreeInfo]:
        """Return all tracked active worktrees."""
        return dict(self._active)

    def cleanup_stale(self) -> int:
        """Remove worktrees that exist on disk but aren't tracked.

        Returns:
            Number of stale worktrees cleaned up
        """
        if not self._worktrees_dir.exists():
            return 0

        cleaned = 0
        for entry in self._worktrees_dir.iterdir():
            if entry.is_dir() and entry.name.startswith("task-"):
                task_id = entry.name[5:]  # Strip "task-" prefix
                if task_id not in self._active:
                    logger.info("Cleaning stale worktree: %s", entry)
                    self.remove(task_id)
                    cleaned += 1

        # Prune git's internal worktree list
        try:
            subprocess.run(
                ["git", "worktree", "prune"],
                cwd=str(self.project_root),
                capture_output=True, text=True, timeout=10,
            )
        except (subprocess.SubprocessError, OSError):
            pass

        return cleaned

    def cleanup_all(self) -> int:
        """Remove all managed worktrees. Called during backtrack/reset.

        Returns:
            Number of worktrees cleaned up
        """
        if not self._worktrees_dir.exists():
            return 0

        cleaned = 0
        for entry in self._worktrees_dir.iterdir():
            if entry.is_dir() and entry.name.startswith("task-"):
                task_id = entry.name[5:]
                self.remove(task_id)
                cleaned += 1

        # Remove the worktrees directory itself if empty
        try:
            self._worktrees_dir.rmdir()
        except OSError:
            pass

        return cleaned
