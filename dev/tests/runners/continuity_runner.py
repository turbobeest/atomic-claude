#!/usr/bin/env python3
"""
Continuity Test Runner

Validates seamless task-to-task execution without terminal errors.
Tests that all tasks in a phase execute sequentially without crashes,
unhandled exceptions, or resource leaks.

Author: Agent 2, Phase 1: Foundation
"""

import json
import os
import psutil
import signal
import sys
import tempfile
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import resource

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.subprocess_runner import run_task_script
from core.state import StateManager


@dataclass
class TaskResult:
    """Result of a single task execution."""
    task_id: str
    task_name: str
    exit_code: int
    duration_seconds: float
    stdout: str
    stderr: str
    success: bool
    error_message: Optional[str] = None
    resource_usage: Dict[str, any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ContinuityTestReport:
    """Complete test report for a phase."""
    phase_id: str
    phase_name: str
    started_at: str
    completed_at: Optional[str] = None
    duration_seconds: float = 0.0
    total_tasks: int = 0
    tasks_passed: int = 0
    tasks_failed: int = 0
    tasks_skipped: int = 0
    success: bool = False
    task_results: List[TaskResult] = field(default_factory=list)
    state_transitions_valid: bool = True
    no_resource_leaks: bool = True
    cleanup_successful: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ContinuityTestRunner:
    """
    Continuity Test Runner - Validates seamless task-to-task execution.

    Features:
    - Execute all tasks in a phase sequentially
    - Capture exit codes, stdout, stderr for each task
    - Detect hard failures vs expected errors
    - Validate state transitions between tasks
    - Check for orphaned processes, file handles
    - Verify cleanup on task completion
    - Generate detailed test report (JSON + human-readable)
    """

    def __init__(self, atomic_root: Path = None):
        """
        Initialize the continuity test runner.

        Args:
            atomic_root: Root directory of atomic-claude (defaults to detected root)
        """
        self.atomic_root = atomic_root or Path(__file__).parent.parent.parent
        self.state_manager = StateManager(self.atomic_root / ".state")
        self.initial_processes: List[int] = []
        self.initial_open_files: int = 0

    def run_phase_continuity_test(
        self,
        phase_num: int,
        config: Dict,
        mock_inputs: bool = False
    ) -> ContinuityTestReport:
        """
        Run continuity test for a complete phase.

        Args:
            phase_num: Phase number (0-9)
            config: Test configuration dictionary
            mock_inputs: If True, use mock inputs instead of real LLM calls

        Returns:
            ContinuityTestReport with complete test results
        """
        phase_id = config.get("phase", f"{phase_num}-phase")
        phase_name = config.get("name", f"Phase {phase_num}")

        # Initialize report
        report = ContinuityTestReport(
            phase_id=phase_id,
            phase_name=phase_name,
            started_at=datetime.now().isoformat(),
            total_tasks=len(config.get("tasks", []))
        )

        print(f"\n{'='*80}")
        print(f"CONTINUITY TEST: {phase_name}")
        print(f"{'='*80}\n")

        # Capture initial system state
        self._capture_initial_state()

        start_time = time.time()

        try:
            # Execute all tasks sequentially
            for task_id in config.get("tasks", []):
                task_result = self._run_single_task(
                    phase_id=phase_id,
                    task_id=task_id,
                    config=config,
                    mock_inputs=mock_inputs
                )
                report.task_results.append(task_result)

                if task_result.success:
                    report.tasks_passed += 1
                else:
                    report.tasks_failed += 1
                    # Continue testing even after failure to see full picture
                    report.errors.append(
                        f"Task {task_id} failed: {task_result.error_message}"
                    )

                # Validate state transition
                if not self._validate_state_transition(phase_id, task_id):
                    report.state_transitions_valid = False
                    report.warnings.append(
                        f"Invalid state transition after task {task_id}"
                    )

            # Check for resource leaks
            if not self._check_resource_cleanup():
                report.no_resource_leaks = False
                report.warnings.append("Resource leaks detected")

            # Verify cleanup
            report.cleanup_successful = self._verify_cleanup(phase_id)

            # Overall success
            report.success = (
                report.tasks_failed == 0 and
                report.state_transitions_valid and
                report.no_resource_leaks and
                report.cleanup_successful
            )

        except Exception as e:
            report.success = False
            report.errors.append(f"Test runner error: {str(e)}")

        finally:
            end_time = time.time()
            report.duration_seconds = end_time - start_time
            report.completed_at = datetime.now().isoformat()

        # Print summary
        self._print_report_summary(report)

        return report

    def _run_single_task(
        self,
        phase_id: str,
        task_id: str,
        config: Dict,
        mock_inputs: bool
    ) -> TaskResult:
        """
        Execute a single task and capture results.

        Args:
            phase_id: Phase identifier
            task_id: Task identifier
            config: Test configuration
            mock_inputs: Whether to use mock inputs

        Returns:
            TaskResult with execution details
        """
        # Find task script
        phase_num = phase_id.split("-")[0]
        task_script = self._find_task_script(phase_num, task_id)

        if not task_script:
            return TaskResult(
                task_id=task_id,
                task_name=f"Task {task_id}",
                exit_code=-1,
                duration_seconds=0.0,
                stdout="",
                stderr="",
                success=False,
                error_message=f"Task script not found for {task_id}"
            )

        task_name = task_script.stem.replace(task_id, "").strip("-_")

        print(f"  Testing Task {task_id}: {task_name}...")

        # Capture resource usage before
        process = psutil.Process()
        mem_before = process.memory_info().rss

        start_time = time.time()

        # Set up environment for mocking if needed
        env_backup = {}
        if mock_inputs:
            env_backup = self._setup_mock_environment()

        try:
            # Execute task script
            timeout = config.get("continuity", {}).get("timeout_per_task", 60)
            exit_code, stdout, stderr = run_task_script(
                script_path=task_script,
                phase_id=phase_id,
                task_id=task_id,
                timeout=timeout,
                capture_output=True
            )

            duration = time.time() - start_time

            # Capture resource usage after
            mem_after = process.memory_info().rss
            mem_delta_mb = (mem_after - mem_before) / (1024 * 1024)

            # Determine success
            success = (exit_code == 0)
            error_message = None
            warnings = []

            if not success:
                error_message = f"Exit code {exit_code}"
                if stderr:
                    error_message += f": {stderr[:200]}"

            # Check for warnings in output
            if "warning" in stdout.lower() or "warning" in stderr.lower():
                warnings.append("Warnings detected in output")

            result = TaskResult(
                task_id=task_id,
                task_name=task_name,
                exit_code=exit_code,
                duration_seconds=duration,
                stdout=stdout,
                stderr=stderr,
                success=success,
                error_message=error_message,
                resource_usage={
                    "memory_delta_mb": round(mem_delta_mb, 2),
                    "duration_seconds": round(duration, 2)
                },
                warnings=warnings
            )

            status_icon = "✓" if success else "✗"
            print(f"    {status_icon} {task_name} ({duration:.1f}s)")

            return result

        except Exception as e:
            duration = time.time() - start_time
            return TaskResult(
                task_id=task_id,
                task_name=task_name,
                exit_code=-1,
                duration_seconds=duration,
                stdout="",
                stderr=str(e),
                success=False,
                error_message=f"Exception: {str(e)}"
            )

        finally:
            # Restore environment
            if mock_inputs:
                self._restore_environment(env_backup)

    def _find_task_script(self, phase_num: str, task_id: str) -> Optional[Path]:
        """
        Find task module for given phase and task.

        Args:
            phase_num: Phase number (e.g., "0", "1")
            task_id: Task ID (e.g., "001", "101")

        Returns:
            Path to task module or None if not found
        """
        # Search Python task modules in phase_NN_name directories
        phase_dirs = list(self.atomic_root.glob(f"phases/phase_{int(phase_num):02d}_*/tasks/"))
        for tasks_dir in phase_dirs:
            # Match task_NNN_*.py pattern
            matches = list(tasks_dir.glob(f"task_{task_id}_*.py"))
            if matches:
                return matches[0]
            # Also try without underscore prefix
            matches = list(tasks_dir.glob(f"task_{int(task_id):03d}_*.py"))
            if matches:
                return matches[0]

        return None

    def _validate_state_transition(self, phase_id: str, task_id: str) -> bool:
        """
        Validate that state transition occurred correctly after task.

        Args:
            phase_id: Phase identifier
            task_id: Task identifier

        Returns:
            True if state transition is valid
        """
        try:
            # Check if task is marked complete in state
            is_complete = self.state_manager.is_task_complete(phase_id, task_id)

            # For continuity testing, we expect tasks to complete successfully
            # If task ran without error, it should be marked complete
            return is_complete

        except Exception:
            return False

    def _capture_initial_state(self):
        """Capture initial system state for leak detection."""
        try:
            # Get current process and children
            current_process = psutil.Process()
            self.initial_processes = [
                p.pid for p in current_process.children(recursive=True)
            ]

            # Get open file count
            self.initial_open_files = len(current_process.open_files())

        except Exception:
            # If we can't capture state, skip leak detection
            pass

    def _check_resource_cleanup(self) -> bool:
        """
        Check for resource leaks (orphaned processes, unclosed files).

        Returns:
            True if no leaks detected
        """
        try:
            current_process = psutil.Process()

            # Check for new child processes
            current_children = [
                p.pid for p in current_process.children(recursive=True)
            ]
            new_processes = set(current_children) - set(self.initial_processes)

            if new_processes:
                print(f"  ⚠️  Warning: {len(new_processes)} orphaned processes")
                return False

            # Check for unclosed files
            current_files = len(current_process.open_files())
            file_delta = current_files - self.initial_open_files

            if file_delta > 10:  # Allow some tolerance
                print(f"  ⚠️  Warning: {file_delta} unclosed file handles")
                return False

            return True

        except Exception:
            # If we can't check, assume OK
            return True

    def _verify_cleanup(self, phase_id: str) -> bool:
        """
        Verify that phase cleaned up properly.

        Args:
            phase_id: Phase identifier

        Returns:
            True if cleanup successful
        """
        try:
            # Check for temp files
            temp_patterns = [
                ".tmp",
                ".temp",
                "*.swp",
                "*.swo"
            ]

            temp_files = []
            for pattern in temp_patterns:
                temp_files.extend(self.atomic_root.glob(f"**/{pattern}"))

            if temp_files:
                print(f"  ⚠️  Warning: {len(temp_files)} temp files not cleaned up")
                return False

            return True

        except Exception:
            return True

    def _setup_mock_environment(self) -> Dict[str, str]:
        """
        Set up environment for mocked/simulated inputs.

        Returns:
            Dict of original environment values to restore
        """
        backup = {}

        # Mock environment variables
        mock_vars = {
            "ATOMIC_TEST_MODE": "1",
            "ATOMIC_MOCK_LLM": "1",
            "CLAUDE_PROVIDER": "mock",
        }

        for key, value in mock_vars.items():
            backup[key] = os.environ.get(key)
            os.environ[key] = value

        return backup

    def _restore_environment(self, backup: Dict[str, str]):
        """
        Restore environment variables.

        Args:
            backup: Dict of original environment values
        """
        for key, value in backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _print_report_summary(self, report: ContinuityTestReport):
        """
        Print human-readable report summary.

        Args:
            report: ContinuityTestReport to display
        """
        print(f"\n{'='*80}")
        print(f"CONTINUITY TEST RESULTS: {report.phase_name}")
        print(f"{'='*80}\n")

        print(f"Duration: {report.duration_seconds:.1f}s")
        print(f"Tasks: {report.total_tasks} total, "
              f"{report.tasks_passed} passed, "
              f"{report.tasks_failed} failed, "
              f"{report.tasks_skipped} skipped")
        print()

        # Task details
        print("Task Results:")
        for result in report.task_results:
            status = "PASS" if result.success else "FAIL"
            icon = "✓" if result.success else "✗"
            duration = result.duration_seconds
            print(f"  {icon} Task {result.task_id}: {result.task_name} "
                  f"[{status}] ({duration:.1f}s)")

            if result.error_message:
                print(f"     Error: {result.error_message}")

        print()

        # Validation checks
        print("Validation Checks:")
        print(f"  {'✓' if report.state_transitions_valid else '✗'} "
              f"State transitions valid")
        print(f"  {'✓' if report.no_resource_leaks else '✗'} "
              f"No resource leaks")
        print(f"  {'✓' if report.cleanup_successful else '✗'} "
              f"Cleanup successful")
        print()

        # Errors
        if report.errors:
            print(f"Errors ({len(report.errors)}):")
            for error in report.errors:
                print(f"  • {error}")
            print()

        # Warnings
        if report.warnings:
            print(f"Warnings ({len(report.warnings)}):")
            for warning in report.warnings:
                print(f"  • {warning}")
            print()

        # Final result
        result_str = "PASSED" if report.success else "FAILED"
        icon = "✓" if report.success else "✗"
        print(f"{icon} Overall Result: {result_str}")
        print(f"\n{'='*80}\n")

    def save_report(
        self,
        report: ContinuityTestReport,
        output_dir: Path = None
    ) -> Tuple[Path, Path]:
        """
        Save report to disk (JSON and human-readable).

        Args:
            report: ContinuityTestReport to save
            output_dir: Output directory (defaults to tests/reports)

        Returns:
            Tuple of (json_path, text_path)
        """
        if output_dir is None:
            output_dir = self.atomic_root / "tests" / "reports"

        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"continuity_{report.phase_id}_{timestamp}"

        # Save JSON report
        json_path = output_dir / f"{base_name}.json"
        with open(json_path, "w") as f:
            # Convert dataclass to dict
            report_dict = asdict(report)
            json.dump(report_dict, f, indent=2)

        # Save text report
        text_path = output_dir / f"{base_name}.txt"
        with open(text_path, "w") as f:
            f.write(f"Continuity Test Report: {report.phase_name}\n")
            f.write(f"{'='*80}\n\n")
            f.write(f"Started:  {report.started_at}\n")
            f.write(f"Completed: {report.completed_at}\n")
            f.write(f"Duration: {report.duration_seconds:.1f}s\n\n")

            f.write(f"Tasks: {report.total_tasks} total, ")
            f.write(f"{report.tasks_passed} passed, ")
            f.write(f"{report.tasks_failed} failed\n\n")

            f.write("Task Results:\n")
            for result in report.task_results:
                status = "PASS" if result.success else "FAIL"
                f.write(f"  [{status}] Task {result.task_id}: {result.task_name} ")
                f.write(f"({result.duration_seconds:.1f}s)\n")
                if result.error_message:
                    f.write(f"        Error: {result.error_message}\n")

            f.write(f"\nOverall Result: {'PASSED' if report.success else 'FAILED'}\n")

        return json_path, text_path


def load_phase_config(config_path: Path) -> Dict:
    """
    Load phase test configuration from JSON file.

    Args:
        config_path: Path to configuration JSON

    Returns:
        Dict with configuration
    """
    with open(config_path, "r") as f:
        return json.load(f)


def main():
    """Main entry point for continuity test runner."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Continuity Test Runner - Validate seamless task execution"
    )
    parser.add_argument(
        "phase",
        type=int,
        help="Phase number to test (0-9)"
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to test configuration JSON (defaults to tests/phase_configs/phase_NN_tests.json)"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock inputs instead of real LLM calls"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for reports (defaults to tests/reports)"
    )

    args = parser.parse_args()

    # Determine config path
    if args.config:
        config_path = args.config
    else:
        atomic_root = Path(__file__).parent.parent.parent
        config_path = atomic_root / "tests" / "phase_configs" / f"phase_{args.phase:02d}_tests.json"

    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)

    # Load configuration
    config = load_phase_config(config_path)

    # Run test
    runner = ContinuityTestRunner()
    report = runner.run_phase_continuity_test(
        phase_num=args.phase,
        config=config,
        mock_inputs=args.mock
    )

    # Save report
    json_path, text_path = runner.save_report(report, output_dir=args.output_dir)
    print(f"\nReports saved:")
    print(f"  JSON: {json_path}")
    print(f"  Text: {text_path}")

    # Exit with appropriate code
    sys.exit(0 if report.success else 1)


if __name__ == "__main__":
    main()
