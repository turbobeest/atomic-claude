#!/usr/bin/env python3
"""
ATOMIC CLAUDE - Phase Management Library
Provides phase lifecycle management for multi-step workflows

Usage:
    from lib.phase import PhaseManager

    manager = PhaseManager()
    manager.phase_start("0-setup", "Project Setup")
    # ... run tasks ...
    manager.phase_complete()
"""

import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# Import dependencies (will be implemented separately)
try:
    from lib.atomic import (
        atomic_validate_deps,
        atomic_state_set,
        atomic_context_init,
        atomic_phase_header,
        atomic_header,
        atomic_substep,
        atomic_success,
        atomic_error,
        atomic_warn,
        atomic_info,
        atomic_step,
        atomic_get_project_name,
        atomic_git_tag,
        atomic_context_refresh,
        atomic_context_artifact,
        atomic_mktemp,
        atomic_invoke,
        atomic_drain_stdin,
        ATOMIC_ROOT,
        ATOMIC_OUTPUT_DIR,
        ATOMIC_STATE_DIR,
    )
    from lib.task_state import (
        task_state_init,
        task_state_should_skip,
        task_state_start,
        task_state_complete,
        task_state_fail,
        task_state_get_last_complete,
        task_state_phase_complete,
        task_state_reset_from,
    )
    from lib.memory import memory_init, memory_task_start, memory_task_end
except ImportError as e:
    # Graceful degradation for development
    print(f"Warning: Failed to import dependencies: {e}", file=sys.stderr)
    # Define placeholder paths
    ATOMIC_ROOT = Path.cwd()
    ATOMIC_OUTPUT_DIR = ATOMIC_ROOT / ".outputs"
    ATOMIC_STATE_DIR = ATOMIC_ROOT / ".state"


# ============================================================================
# COLOR CONSTANTS (ANSI escape codes)
# ============================================================================

BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
NC = "\033[0m"  # No Color


# ============================================================================
# TASK NAVIGATION EXIT CODES
# ============================================================================

TASK_CONTINUE = 0
TASK_REDO = 1
TASK_BACK = 100
TASK_QUIT = 101


# ============================================================================
# PHASE STATE DATA CLASS
# ============================================================================

@dataclass
class PhaseState:
    """Tracks the current phase execution state."""

    current_phase: str = ""
    current_phase_name: str = ""
    phase_start_time: float = 0.0
    phase_tasks_run: int = 0
    phase_snapshot_dir: Path = field(default_factory=Path)
    active_task_id: str = ""
    active_task_name: str = ""


# ============================================================================
# PHASE MANAGER CLASS
# ============================================================================

class PhaseManager:
    """Manages phase lifecycle and task execution."""

    def __init__(self, atomic_root: Optional[Path] = None):
        """
        Initialize the Phase Manager.

        Args:
            atomic_root: Root directory of the atomic-claude installation.
                        If None, uses ATOMIC_ROOT from environment or cwd.
        """
        self.state = PhaseState()
        self.atomic_root = atomic_root or ATOMIC_ROOT
        self.output_dir = ATOMIC_OUTPUT_DIR
        self.state_dir = ATOMIC_STATE_DIR

        # Global variable for task resume point
        self.task_resume_at: Optional[str] = None

        # Register signal handlers
        self._register_signal_handlers()

    # ========================================================================
    # SIGNAL HANDLING
    # ========================================================================

    def _register_signal_handlers(self) -> None:
        """Register signal handlers for clean interruption."""
        signal.signal(signal.SIGINT, self._signal_cleanup)
        signal.signal(signal.SIGTERM, self._signal_cleanup)

    def _signal_cleanup(self, signum: int, frame: Any) -> None:
        """
        Handle interruption signals and mark active task as failed.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = signal.Signals(signum).name

        if self.state.active_task_id:
            print(f"\n  {YELLOW}!{NC} Interrupted ({signal_name}) — "
                  f"marking task {self.state.active_task_id} as failed",
                  file=sys.stderr)
            try:
                task_state_fail(
                    self.state.active_task_id,
                    f"Interrupted by {signal_name}"
                )
            except Exception:
                pass

            self.state.active_task_id = ""
            self.state.active_task_name = ""

        # Exit with appropriate code
        sys.exit(128 + signum)

    # ========================================================================
    # UTILITY FUNCTIONS
    # ========================================================================

    @staticmethod
    def _epoch_to_iso(epoch: float) -> str:
        """
        Convert epoch timestamp to ISO 8601 format.

        Args:
            epoch: Unix timestamp

        Returns:
            ISO 8601 formatted string
        """
        try:
            dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
            return dt.isoformat()
        except Exception:
            return str(int(epoch))

    # ========================================================================
    # PHASE SNAPSHOTS & ROLLBACK
    # ========================================================================

    def phase_snapshot(self, phase_id: str) -> Path:
        """
        Create a snapshot of phase state before execution.

        Args:
            phase_id: Phase identifier (e.g., "0-setup")

        Returns:
            Path to the snapshot directory
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        snapshot_dir = self.state_dir / "snapshots" / f"{phase_id}-{timestamp}"
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        # Snapshot task state
        task_state_file = self.atomic_root / ".claude" / "task-state.json"
        if task_state_file.exists():
            self._copy_file(task_state_file, snapshot_dir / "task-state.json")

        # Snapshot session state
        session_file = self.state_dir / "session.json"
        if session_file.exists():
            self._copy_file(session_file, snapshot_dir / "session.json")

        # Snapshot context
        context_dir = self.state_dir / "context"
        if context_dir.exists():
            self._copy_tree(context_dir, snapshot_dir / "context")

        # Record snapshot metadata
        metadata = {
            "phase_id": phase_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "snapshot_dir": str(snapshot_dir),
        }

        with open(snapshot_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        return snapshot_dir

    def phase_rollback(self, snapshot_dir: Path) -> bool:
        """
        Rollback to a previous snapshot.

        Args:
            snapshot_dir: Path to the snapshot directory

        Returns:
            True if rollback succeeded, False otherwise
        """
        if not snapshot_dir.exists():
            print(f"ERROR: Snapshot directory not found: {snapshot_dir}",
                  file=sys.stderr)
            return False

        print(f"Rolling back to snapshot: {snapshot_dir}")

        # Restore task state
        task_state_snap = snapshot_dir / "task-state.json"
        if task_state_snap.exists():
            task_state_dest = self.atomic_root / ".claude" / "task-state.json"
            self._copy_file(task_state_snap, task_state_dest)
            print("  Restored: task-state.json")

        # Restore session state
        session_snap = snapshot_dir / "session.json"
        if session_snap.exists():
            session_dest = self.state_dir / "session.json"
            self._copy_file(session_snap, session_dest)
            print("  Restored: session.json")

        # Restore context
        context_snap = snapshot_dir / "context"
        if context_snap.exists():
            context_dest = self.state_dir / "context"
            if context_dest.exists():
                self._rmtree(context_dest)
            self._copy_tree(context_snap, context_dest)
            print("  Restored: context/")

        print("Rollback complete")
        return True

    def phase_list_snapshots(self) -> None:
        """List available snapshots."""
        snapshot_base = self.state_dir / "snapshots"

        if not snapshot_base.exists():
            print("No snapshots found")
            return

        print("Available snapshots:")
        for snapshot in sorted(snapshot_base.iterdir()):
            if snapshot.is_dir():
                metadata_file = snapshot / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file) as f:
                            metadata = json.load(f)
                        phase_id = metadata.get("phase_id", "unknown")
                        timestamp = metadata.get("timestamp", "unknown")
                        print(f"  {snapshot}")
                        print(f"    Phase: {phase_id}")
                        print(f"    Time: {timestamp}")
                    except Exception:
                        pass

    def phase_cleanup_snapshots(self, keep_count: int = 3) -> None:
        """
        Cleanup old snapshots (keep last N per phase).

        Args:
            keep_count: Number of snapshots to keep per phase
        """
        snapshot_base = self.state_dir / "snapshots"

        if not snapshot_base.exists():
            return

        # Group snapshots by phase
        phase_snapshots: Dict[str, List[Path]] = {}

        for snapshot in snapshot_base.iterdir():
            if snapshot.is_dir():
                # Extract phase ID from directory name (e.g., "0-setup-20240101-120000")
                parts = snapshot.name.split("-")
                if len(parts) >= 2:
                    phase_id = f"{parts[0]}-{parts[1]}"
                    if phase_id not in phase_snapshots:
                        phase_snapshots[phase_id] = []
                    phase_snapshots[phase_id].append(snapshot)

        # Sort and remove excess snapshots
        for phase_id, snapshots in phase_snapshots.items():
            snapshots.sort(reverse=True)  # Newest first

            for i, snapshot in enumerate(snapshots):
                if i >= keep_count:
                    self._rmtree(snapshot)
                    print(f"Removed old snapshot: {snapshot}")

    def phase_validate_task_id(self, task_id: str) -> Tuple[bool, str]:
        """
        Validate that a task ID exists for the current phase.

        Args:
            task_id: Task ID to validate (e.g., "101")

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Must be numeric
        if not task_id.isdigit():
            return False, "Task ID must be numeric"

        # Extract phase number from task ID (first digit)
        task_phase = task_id[0]

        # If we have a current phase, validate against it
        if self.state.current_phase:
            current_phase_num = self.state.current_phase.split("-")[0]
            if task_phase != current_phase_num:
                return False, f"Task {task_id} is not in current phase ({current_phase_num})"

        # Check if task script exists
        phase_dirs = list(self.atomic_root.glob(f"phases/{task_phase}-*"))
        if phase_dirs:
            phase_dir = phase_dirs[0]
            task_scripts = list(phase_dir.glob(f"tasks/{task_id}-*.sh"))
            if not task_scripts:
                return False, f"Task {task_id} not found in phase {task_phase}"

        return True, ""

    # ========================================================================
    # PHASE LIFECYCLE
    # ========================================================================

    def phase_start(self, phase_id: str, phase_name: str) -> bool:
        """
        Start a new phase.

        Args:
            phase_id: Phase identifier (e.g., "0-setup")
            phase_name: Human-readable phase name

        Returns:
            True if phase started successfully, False otherwise
        """
        # Validate dependencies before starting phase
        if not atomic_validate_deps():
            print("ERROR: Cannot start phase - missing dependencies",
                  file=sys.stderr)
            return False

        # Create snapshot before starting (for rollback capability)
        self.state.phase_snapshot_dir = self.phase_snapshot(phase_id)

        self.state.current_phase = phase_id
        self.state.current_phase_name = phase_name
        self.state.phase_start_time = time.time()
        self.state.phase_tasks_run = 0

        # Update state
        atomic_state_set("current_phase", f'"{phase_id}"')

        # Create phase output directory
        phase_output = self.output_dir / phase_id
        phase_output.mkdir(parents=True, exist_ok=True)

        # Initialize context management for this phase
        atomic_context_init(phase_id)

        # Initialize task state tracking
        task_state_init(phase_id)

        # Get phase number from id (e.g., "0-setup" -> "0")
        phase_num = phase_id.split("-")[0]

        # Display header with project name
        header = atomic_phase_header(phase_num, phase_name)
        atomic_header(header)
        atomic_substep(f"Phase ID: {phase_id}")
        atomic_substep(f"Started: {datetime.now()}")

        # Show resume status if applicable
        last_task = task_state_get_last_complete()
        if last_task:
            atomic_substep(f"Last completed: Task {last_task}")

        print()
        return True

    def phase_task(self, task_id: str, task_name: str,
                   task_func: Callable[[], bool]) -> bool:
        """
        Execute a phase task.

        Args:
            task_id: Task identifier
            task_name: Human-readable task name
            task_func: Function to execute the task

        Returns:
            True if task succeeded, False otherwise
        """
        self.state.phase_tasks_run += 1

        print()
        print(f"{BOLD}{CYAN}▶ Task {task_id}:{NC} {BOLD}{task_name}{NC}")

        # Execute the task function
        try:
            if task_func():
                atomic_success(f"Task '{task_name}' completed")
                return True
            else:
                atomic_error(f"Task '{task_name}' failed")
                return False
        except Exception as e:
            atomic_error(f"Task '{task_name}' failed: {e}")
            return False

    def phase_checkpoint(self, checkpoint_name: str,
                        checkpoint_data: Dict[str, Any]) -> bool:
        """
        Save a checkpoint during phase execution.

        Args:
            checkpoint_name: Name of the checkpoint
            checkpoint_data: Data to save in the checkpoint

        Returns:
            True if checkpoint saved successfully, False otherwise
        """
        checkpoint_file = (self.output_dir / self.state.current_phase /
                          "checkpoints.json")

        # Initialize or load existing checkpoints
        if checkpoint_file.exists():
            with open(checkpoint_file) as f:
                checkpoints = json.load(f)
        else:
            checkpoints = {"checkpoints": []}

        # Add new checkpoint
        checkpoints["checkpoints"].append({
            "name": checkpoint_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": checkpoint_data,
        })

        # Save to file
        try:
            with open(checkpoint_file, "w") as f:
                json.dump(checkpoints, f, indent=2)
            atomic_info(f"Checkpoint saved: {checkpoint_name}")
            return True
        except Exception as e:
            print(f"ERROR: Failed to save checkpoint: {e}", file=sys.stderr)
            return False

    def phase_verify(self, verification_script: Path) -> bool:
        """
        Run phase verification script.

        Args:
            verification_script: Path to the verification script

        Returns:
            True if verification passed, False otherwise
        """
        atomic_step("Phase Verification")

        if not verification_script.exists():
            atomic_warn("No verification script found, skipping")
            return True

        try:
            result = subprocess.run(
                ["bash", str(verification_script)],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                atomic_success("Phase verification passed")
                return True
            else:
                atomic_error("Phase verification failed")
                return False
        except Exception as e:
            atomic_error(f"Phase verification error: {e}")
            return False

    def phase_complete(self) -> bool:
        """
        Complete the current phase and generate closeout artifact.

        Returns:
            True if phase completed successfully, False otherwise
        """
        end_time = time.time()
        duration = int(end_time - self.state.phase_start_time)
        project_name = atomic_get_project_name()

        print()
        print(f"{GREEN}{'━' * 62}{NC}")
        print(f"{GREEN}  PHASE COMPLETE: {self.state.current_phase_name} "
              f"[{project_name}]{NC}")
        print(f"{GREEN}{'━' * 62}{NC}")
        print()
        print(f"{DIM}  Project:        {project_name}{NC}")
        print(f"{DIM}  Phase ID:       {self.state.current_phase}{NC}")
        print(f"{DIM}  Tasks Run:      {self.state.phase_tasks_run}{NC}")
        print(f"{DIM}  Duration:       {duration}s{NC}")
        print(f"{DIM}  Completed:      {datetime.now()}{NC}")
        print()

        # Generate closeout artifact
        closeout_file = (self.output_dir / self.state.current_phase /
                        "closeout.json")
        git_tag = atomic_git_tag(self.state.current_phase)

        closeout_data = {
            "project_name": project_name,
            "phase_id": self.state.current_phase,
            "phase_name": self.state.current_phase_name,
            "tasks_run": self.state.phase_tasks_run,
            "duration_seconds": duration,
            "started_at": self._epoch_to_iso(self.state.phase_start_time),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "status": "complete",
            "git_tag": git_tag,
        }

        try:
            with open(closeout_file, "w") as f:
                json.dump(closeout_data, f, indent=2)

            atomic_substep(f"Closeout saved: {closeout_file}")
            atomic_substep(f"Git tag available: {git_tag}")

            # Refresh context summary before closing out
            atomic_context_refresh()

            # Record phase completion as artifact
            atomic_context_artifact(
                str(closeout_file),
                f"Phase {self.state.current_phase} closeout",
                "closeout"
            )

            # Mark phase complete in task state
            task_state_phase_complete()

            # Clear state
            atomic_state_set("current_phase", "null")
            atomic_state_set("current_task", "null")

            return True
        except Exception as e:
            atomic_error(f"Failed to save closeout: {e}")
            return False

    # ========================================================================
    # PHASE WORKFLOW HELPERS
    # ========================================================================

    def phase_task_interactive(self, task_id: str, task_name: str,
                              task_func: Callable[[], bool]) -> int:
        """
        Execute a task with interactive navigation (redo, back, quit, jump).

        Args:
            task_id: 3-digit task ID (e.g., "001", "101")
            task_name: Human-readable task name
            task_func: Function to execute the task

        Returns:
            Exit code: TASK_CONTINUE, TASK_BACK, or TASK_QUIT
        """
        # Check if task should be skipped
        if task_state_should_skip(task_id):
            print()
            print(f"{DIM}▶ Task {task_id}: {task_name} "
                  f"{GREEN}[COMPLETE - SKIPPED]{NC}")
            print()
            return TASK_CONTINUE

        while True:
            print()
            print(f"{BOLD}{CYAN}▶ Task {task_id}:{NC} {BOLD}{task_name}{NC}")
            print()

            # Mark task as started and track for signal cleanup
            task_state_start(task_id, task_name)
            self.state.active_task_id = task_id
            self.state.active_task_name = task_name

            # Recall context for this task (if memory enabled)
            memory_task_start(task_id, task_name, self.state.current_phase)

            # Run the task
            try:
                task_succeeded = task_func()
            except Exception as e:
                print(f"ERROR: Task failed with exception: {e}",
                      file=sys.stderr)
                task_succeeded = False

            if task_succeeded:
                # Mark task complete in persistent state
                task_state_complete(task_id, task_name)
                self.state.active_task_id = ""
                self.state.active_task_name = ""

                # Save task outcomes to memory (if memory enabled)
                memory_task_end(task_id, task_name, self.state.current_phase)

                atomic_success("Task completed")

                # Post-task navigation
                print()
                print(f"{DIM}{'━' * 62}{NC}")
                print(f"  {GREEN}[c]{NC} Continue    {YELLOW}[r]{NC} Redo    "
                      f"{BLUE}[b]{NC} Go back    {MAGENTA}[j]{NC} Jump to    "
                      f"{RED}[q]{NC} Quit")
                print(f"{DIM}{'━' * 62}{NC}")

                atomic_drain_stdin()
                choice = input("  Choice [c]: ").strip().lower() or "c"

                if choice in ("c", ""):
                    return TASK_CONTINUE
                elif choice == "r":
                    atomic_info("Redoing task...")
                    task_state_reset_from(task_id)
                    continue
                elif choice == "b":
                    atomic_info("Going back to previous task...")
                    return TASK_BACK
                elif choice == "j":
                    print()
                    print(f"  {DIM}Enter task ID to jump to (e.g., 101, 105):{NC}")
                    jump_target = input("  Jump to: ").strip()
                    is_valid, error_msg = self.phase_validate_task_id(jump_target)
                    if is_valid:
                        task_state_reset_from(jump_target)
                        self.task_resume_at = jump_target
                        atomic_info(f"Jumping to task {jump_target}...")
                        return TASK_CONTINUE
                    else:
                        atomic_error(f"Invalid task ID: {error_msg}")
                elif choice == "q":
                    atomic_warn("Quitting phase...")
                    return TASK_QUIT
                else:
                    atomic_info("Continuing...")
                    return TASK_CONTINUE
            else:
                # Mark task failed in persistent state
                task_state_fail(task_id, "Task execution failed")
                self.state.active_task_id = ""
                self.state.active_task_name = ""
                atomic_error("Task failed")

                # Failure navigation
                print()
                print(f"{DIM}{'━' * 62}{NC}")
                print(f"  {YELLOW}[r]{NC} Retry    {BLUE}[b]{NC} Go back    "
                      f"{MAGENTA}[j]{NC} Jump to    {DIM}[s]{NC} Skip    "
                      f"{RED}[q]{NC} Quit")
                print(f"{DIM}{'━' * 62}{NC}")

                atomic_drain_stdin()
                choice = input("  Choice [r]: ").strip().lower() or "r"

                if choice in ("r", ""):
                    atomic_info("Retrying task...")
                    continue
                elif choice == "b":
                    atomic_info("Going back to previous task...")
                    return TASK_BACK
                elif choice == "j":
                    print()
                    print(f"  {DIM}Enter task ID to jump to (e.g., 101, 105):{NC}")
                    jump_target = input("  Jump to: ").strip()
                    is_valid, error_msg = self.phase_validate_task_id(jump_target)
                    if is_valid:
                        task_state_reset_from(jump_target)
                        self.task_resume_at = jump_target
                        atomic_info(f"Jumping to task {jump_target}...")
                        return TASK_CONTINUE
                    else:
                        atomic_error(f"Invalid task ID: {error_msg}")
                elif choice == "s":
                    atomic_warn("Skipping task...")
                    return TASK_CONTINUE
                elif choice == "q":
                    atomic_warn("Quitting phase...")
                    return TASK_QUIT
                else:
                    atomic_info("Retrying...")
                    continue

    def phase_run_tasks(self, task_functions: List[Callable[[], bool]]) -> bool:
        """
        Run a sequence of tasks with navigation support.

        Args:
            task_functions: List of task functions named task_XXX_descriptive_name

        Returns:
            True if all tasks completed successfully, False otherwise
        """
        tasks = []

        # Extract task IDs and names from function names
        for task_func in task_functions:
            func_name = task_func.__name__

            # Extract 3-digit ID (e.g., task_001_foo_bar -> "001")
            import re
            match = re.search(r'task_(\d{3})_', func_name)
            if match:
                task_id = match.group(1)
            else:
                # Try 2-digit format
                match = re.search(r'task_(\d{2})_', func_name)
                if match:
                    task_id = f"0{match.group(1)}"
                else:
                    task_id = "???"

            # Extract name part (task_XXX_descriptive_name -> "Descriptive Name")
            name_part = re.sub(r'^task_\d+_', '', func_name)
            task_name = name_part.replace("_", " ").title()

            tasks.append((task_id, task_name, task_func))

        # Execute tasks with navigation
        i = 0
        total = len(tasks)

        while i < total:
            task_id, task_name, task_func = tasks[i]
            result = self.phase_task_interactive(task_id, task_name, task_func)

            if result == TASK_CONTINUE:
                i += 1
            elif result == TASK_BACK:
                if i > 0:
                    i -= 1
                else:
                    atomic_warn("Already at first task")
            elif result == TASK_QUIT:
                atomic_error("Phase aborted by user")
                return False

        atomic_success("All tasks completed")
        return True

    def phase_deterministic(self, task_name: str,
                           task_func: Callable[[], bool]) -> bool:
        """
        Run a deterministic (non-LLM) task.

        Args:
            task_name: Human-readable task name
            task_func: Function to execute

        Returns:
            True if task succeeded, False otherwise
        """
        atomic_step(task_name)

        try:
            if task_func():
                atomic_success(task_name)
                return True
            else:
                atomic_error(f"{task_name} failed")
                return False
        except Exception as e:
            atomic_error(f"{task_name} failed: {e}")
            return False

    def phase_llm_task(self, task_name: str, prompt_file: Path,
                      output_file: Path, *args: str) -> bool:
        """
        Run an LLM task with bounded prompt.

        Args:
            task_name: Human-readable task name
            prompt_file: Path to the prompt file
            output_file: Path to the output file
            *args: Additional arguments for atomic_invoke

        Returns:
            True if task succeeded, False otherwise
        """
        # Default output to phase output directory if relative path
        if not output_file.is_absolute():
            output_file = (self.output_dir / self.state.current_phase /
                          output_file)

        return atomic_invoke(str(prompt_file), str(output_file),
                           task_name, *args)

    def phase_human_gate(self, gate_message: str) -> bool:
        """
        Require human approval before continuing.

        Args:
            gate_message: Message to display for the approval gate

        Returns:
            True if approved, False if declined
        """
        print()
        print(f"{MAGENTA}╔{'═' * 59}╗{NC}")
        print(f"{MAGENTA}║{NC} {BOLD}🛑 HUMAN APPROVAL REQUIRED{NC}"
              f"{'':32}{MAGENTA}║{NC}")
        print(f"{MAGENTA}╠{'═' * 59}╣{NC}")
        print(f"{MAGENTA}║{NC} {gate_message}")
        print(f"{MAGENTA}║{NC}")
        print(f"{MAGENTA}║{NC} Phase: {self.state.current_phase_name}")
        print(f"{MAGENTA}║{NC} Tasks completed so far: {self.state.phase_tasks_run}")
        print(f"{MAGENTA}╚{'═' * 59}╝{NC}")
        print()

        response = input("Type 'approve' to continue, anything else to abort: ")

        if response == "approve":
            atomic_success("Human gate approved")
            self.phase_checkpoint("human_gate", {
                "approved": True,
                "message": gate_message
            })
            return True
        else:
            atomic_error("Human gate declined")
            self.phase_checkpoint("human_gate", {
                "approved": False,
                "message": gate_message
            })
            return False

    def phase_review(self, review_file: Path,
                    review_name: str = "Review") -> None:
        """
        Display a summary and wait for user to review.

        Args:
            review_file: Path to the review content file
            review_name: Name of the review
        """
        print()
        print(f"{CYAN}╔{'═' * 59}╗{NC}")
        print(f"{CYAN}║{NC} {BOLD}📋 {review_name}{NC}")
        print(f"{CYAN}╚{'═' * 59}╝{NC}")
        print()

        if review_file.exists():
            with open(review_file) as f:
                print(f.read())
        else:
            print(f"(Review content not found: {review_file})")

        print()
        input("Press Enter to continue...")

    # ========================================================================
    # PHASE TRANSITIONS
    # ========================================================================

    def phase_transition_banner(self, from_phase: str, to_phase: str,
                               to_name: str) -> None:
        """
        Display transition banner between phases.

        Args:
            from_phase: Phase ID transitioning from
            to_phase: Phase ID transitioning to
            to_name: Name of the phase transitioning to
        """
        print()
        print()

        completed_text = f"Completed: Phase {from_phase}".ljust(55)[:55]
        starting_text = f"Starting:  Phase {to_phase} - {to_name}".ljust(55)[:55]

        print(f"{MAGENTA}╔{'═' * 59}╗{NC}")
        print(f"{MAGENTA}║{' ' * 59}║{NC}")
        print(f"{MAGENTA}║{NC}  {BOLD}PHASE TRANSITION{NC}"
              f"{' ' * 40}{MAGENTA}║{NC}")
        print(f"{MAGENTA}║{' ' * 59}║{NC}")
        print(f"{MAGENTA}║{NC}  {DIM}{completed_text}{NC} {MAGENTA}║{NC}")
        print(f"{MAGENTA}║{NC}  {BOLD}{starting_text}{NC} {MAGENTA}║{NC}")
        print(f"{MAGENTA}║{' ' * 59}║{NC}")
        print(f"{MAGENTA}╚{'═' * 59}╝{NC}")
        print()

    def phase_offer_continue(self, next_phase_id: str, next_phase_name: str,
                           next_script: Path) -> bool:
        """
        Offer to continue to next phase.

        Args:
            next_phase_id: ID of the next phase
            next_phase_name: Name of the next phase
            next_script: Path to the next phase script

        Returns:
            True if user wants to continue, False otherwise
        """
        print()
        print(f"{DIM}{'━' * 62}{NC}")
        print()
        print(f"  {CYAN}Ready for Phase {next_phase_id}: {next_phase_name}{NC}")
        print()
        print(f"  {GREEN}[c]{NC} Continue to Phase {next_phase_id}")
        print(f"  {YELLOW}[p]{NC} Pause here "
              f"(resume later with: {next_script})")
        print()

        while True:
            atomic_drain_stdin()
            choice = input("  Choice [c]: ").strip().lower() or "c"

            if choice in ("c", "continue"):
                return True
            elif choice in ("p", "pause", "q"):
                print()
                atomic_info("Pausing pipeline.")
                atomic_info(f"To resume: {next_script}")
                print()
                return False
            else:
                atomic_error("Invalid choice. Enter 'c' to continue or 'p' to pause.")

    def phase_chain(self, current_phase: str, next_script: Path,
                   next_phase_name: str) -> bool:
        """
        Execute next phase script.

        Args:
            current_phase: Current phase number
            next_script: Path to the next phase script
            next_phase_name: Name of the next phase

        Returns:
            True if chaining succeeded, False otherwise
        """
        # Extract next phase number from script path
        next_phase_num = next_script.parent.name.split("-")[0]

        if not next_script.exists():
            atomic_error(f"Next phase script not found: {next_script}")
            atomic_info(f"Phase {next_phase_num} may not be implemented yet.")
            return False

        if not self.phase_offer_continue(next_phase_num, next_phase_name,
                                        next_script):
            return False

        self.phase_transition_banner(current_phase, next_phase_num,
                                    next_phase_name)

        # Brief pause for user to see the transition
        time.sleep(1)

        # Build flags to forward to next phase
        forward_flags = ["--skip-intro"]
        if os.environ.get("TASK_FORCE_REDO") == "true":
            forward_flags.append("--redo")

        # Execute next phase
        try:
            os.execv("/bin/bash", ["bash", str(next_script)] + forward_flags)
        except Exception as e:
            atomic_error(f"Failed to execute next phase script: {e}")
            atomic_info(f"Try running it manually: bash {next_script} --skip-intro")
            return False

        # This code should never be reached if exec succeeds
        return False

    # ========================================================================
    # FILE UTILITIES (HELPER METHODS)
    # ========================================================================

    @staticmethod
    def _copy_file(src: Path, dst: Path) -> None:
        """Copy a file from src to dst."""
        import shutil
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    @staticmethod
    def _copy_tree(src: Path, dst: Path) -> None:
        """Recursively copy a directory tree."""
        import shutil
        shutil.copytree(src, dst, dirs_exist_ok=True)

    @staticmethod
    def _rmtree(path: Path) -> None:
        """Recursively remove a directory tree."""
        import shutil
        shutil.rmtree(path, ignore_errors=True)


# ============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# ============================================================================

# Global instance for module-level functions
_phase_manager: Optional[PhaseManager] = None


def get_phase_manager() -> PhaseManager:
    """Get or create the global PhaseManager instance."""
    global _phase_manager
    if _phase_manager is None:
        _phase_manager = PhaseManager()
    return _phase_manager


def phase_start(phase_id: str, phase_name: str) -> bool:
    """Module-level wrapper for phase_start."""
    return get_phase_manager().phase_start(phase_id, phase_name)


def phase_complete() -> bool:
    """Module-level wrapper for phase_complete."""
    return get_phase_manager().phase_complete()


def phase_task_interactive(task_id: str, task_name: str,
                          task_func: Callable[[], bool]) -> int:
    """Module-level wrapper for phase_task_interactive."""
    return get_phase_manager().phase_task_interactive(task_id, task_name,
                                                      task_func)


def phase_run_tasks(task_functions: List[Callable[[], bool]]) -> bool:
    """Module-level wrapper for phase_run_tasks."""
    return get_phase_manager().phase_run_tasks(task_functions)


def phase_human_gate(gate_message: str) -> bool:
    """Module-level wrapper for phase_human_gate."""
    return get_phase_manager().phase_human_gate(gate_message)


def phase_checkpoint(checkpoint_name: str,
                    checkpoint_data: Dict[str, Any]) -> bool:
    """Module-level wrapper for phase_checkpoint."""
    return get_phase_manager().phase_checkpoint(checkpoint_name,
                                                checkpoint_data)


# ============================================================================
# MAIN (FOR TESTING)
# ============================================================================

if __name__ == "__main__":
    print("ATOMIC CLAUDE - Phase Management Library (Python)")
    print("This module is meant to be imported, not run directly.")
    print()
    print("Example usage:")
    print("  from lib.phase import PhaseManager")
    print("  manager = PhaseManager()")
    print("  manager.phase_start('0-setup', 'Project Setup')")
    print("  # ... run tasks ...")
    print("  manager.phase_complete()")
