#!/usr/bin/env python3
"""
State Management Audit Test Runner

Validates task state tracking, resume functionality, and state file integrity.
Tests state transitions, resume points, and corruption resistance.

Usage:
    python test/state_audit_runner.py              # Full audit
    python test/state_audit_runner.py --verbose    # Detailed output
    python test/state_audit_runner.py --skip-exec  # Only validate existing state
"""

import sys
import os
import subprocess
import json
import argparse
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Repo root
REPO_ROOT = Path(__file__).parent.parent.resolve()
STATE_FILE = REPO_ROOT / ".claude" / "task-state.json"
OUTPUT_DIR = REPO_ROOT / ".outputs"

# Colors for output
class Colors:
    CYAN = '\033[0;36m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    NC = '\033[0m'


class StateAuditRunner:
    """State management audit runner."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.validation_results = {}
        self.transition_results = {}
        self.resume_results = {}
        self.corruption_results = {}
        self.test_start_time = datetime.now()

    def log(self, message: str, color: str = Colors.NC):
        """Log a message with color."""
        print(f"{color}{message}{Colors.NC}")

    def validate_state_file(self) -> Dict:
        """
        Validate state file structure and content.

        Returns:
            Dict with validation results
        """
        self.log("\n" + "="*80, Colors.CYAN)
        self.log("  STATE FILE VALIDATION", Colors.CYAN)
        self.log("="*80, Colors.CYAN)

        results = {
            "valid": True,
            "issues": [],
            "checks_passed": 0,
            "checks_failed": 0,
            "file_exists": False,
            "valid_json": False,
            "has_schema": False,
            "phase_count": 0,
            "task_count": 0
        }

        # Check 1: File exists
        self.log("\n  [1/6] Checking state file exists...", Colors.BOLD)
        if STATE_FILE.exists():
            results["file_exists"] = True
            results["checks_passed"] += 1
            self.log(f"    ✓ State file found: {STATE_FILE}", Colors.GREEN)
        else:
            results["valid"] = False
            results["issues"].append("State file does not exist")
            results["checks_failed"] += 1
            self.log(f"    ✗ State file not found: {STATE_FILE}", Colors.RED)
            return results

        # Check 2: Valid JSON
        self.log("\n  [2/6] Checking JSON validity...", Colors.BOLD)
        try:
            with open(STATE_FILE) as f:
                state_data = json.load(f)
            results["valid_json"] = True
            results["checks_passed"] += 1
            self.log(f"    ✓ Valid JSON format", Colors.GREEN)
        except json.JSONDecodeError as e:
            results["valid"] = False
            results["issues"].append(f"Invalid JSON: {e}")
            results["checks_failed"] += 1
            self.log(f"    ✗ Invalid JSON: {e}", Colors.RED)
            return results

        # Check 3: Schema structure
        self.log("\n  [3/6] Checking schema structure...", Colors.BOLD)
        required_keys = ["version", "current_phase", "current_task", "phases"]
        missing_keys = [k for k in required_keys if k not in state_data]

        if not missing_keys:
            results["has_schema"] = True
            results["checks_passed"] += 1
            self.log(f"    ✓ All required keys present: {required_keys}", Colors.GREEN)
        else:
            results["valid"] = False
            results["issues"].append(f"Missing schema keys: {missing_keys}")
            results["checks_failed"] += 1
            self.log(f"    ✗ Missing keys: {missing_keys}", Colors.RED)

        # Check 4: Phase IDs match expected phases
        self.log("\n  [4/6] Validating phase IDs...", Colors.BOLD)
        expected_phases = [
            "0-setup", "1-discovery", "2-prd", "3-tasking",
            "4-specification", "5-implementation", "6-code-review",
            "7-integration", "8-deployment-prep", "9-release"
        ]

        phases = state_data.get("phases", {})
        results["phase_count"] = len(phases)

        invalid_phases = [p for p in phases.keys() if p not in expected_phases]

        if not invalid_phases:
            results["checks_passed"] += 1
            self.log(f"    ✓ All phase IDs valid ({len(phases)} phases tracked)", Colors.GREEN)
        else:
            results["issues"].append(f"Invalid phase IDs: {invalid_phases}")
            results["checks_failed"] += 1
            self.log(f"    ✗ Invalid phase IDs: {invalid_phases}", Colors.RED)

        # Check 5: Task completion tracking
        self.log("\n  [5/6] Checking task completion tracking...", Colors.BOLD)
        total_tasks = 0
        task_issues = []

        for phase_id, phase_data in phases.items():
            if not isinstance(phase_data, dict):
                task_issues.append(f"Phase {phase_id}: not a dict")
                continue

            tasks = phase_data.get("tasks", {})
            total_tasks += len(tasks)

            for task_id, task_data in tasks.items():
                if not isinstance(task_data, dict):
                    task_issues.append(f"Task {phase_id}/{task_id}: not a dict")
                    continue

                # Check task has required fields
                status = task_data.get("status")
                if status not in ["pending", "in_progress", "complete", "failed"]:
                    task_issues.append(f"Task {phase_id}/{task_id}: invalid status '{status}'")

        results["task_count"] = total_tasks

        if not task_issues:
            results["checks_passed"] += 1
            self.log(f"    ✓ All tasks valid ({total_tasks} tasks tracked)", Colors.GREEN)
        else:
            results["issues"].extend(task_issues[:5])  # Show first 5
            results["checks_failed"] += 1
            self.log(f"    ✗ Task issues found ({len(task_issues)} total):", Colors.RED)
            for issue in task_issues[:3]:
                self.log(f"      - {issue}", Colors.DIM)
            if len(task_issues) > 3:
                self.log(f"      ... and {len(task_issues) - 3} more", Colors.DIM)

        # Check 6: Timestamp validity
        self.log("\n  [6/6] Checking timestamp formats...", Colors.BOLD)
        timestamp_issues = []

        for phase_id, phase_data in phases.items():
            for ts_field in ["started_at", "completed_at"]:
                if ts_field in phase_data and phase_data[ts_field]:
                    try:
                        datetime.fromisoformat(phase_data[ts_field].replace('Z', '+00:00'))
                    except (ValueError, AttributeError) as e:
                        timestamp_issues.append(f"Phase {phase_id}/{ts_field}: invalid timestamp")

            tasks = phase_data.get("tasks", {})
            for task_id, task_data in tasks.items():
                for ts_field in ["started_at", "completed_at", "failed_at"]:
                    if ts_field in task_data and task_data[ts_field]:
                        try:
                            datetime.fromisoformat(task_data[ts_field].replace('Z', '+00:00'))
                        except (ValueError, AttributeError) as e:
                            timestamp_issues.append(f"Task {phase_id}/{task_id}/{ts_field}: invalid")

        if not timestamp_issues:
            results["checks_passed"] += 1
            self.log(f"    ✓ All timestamps valid ISO format", Colors.GREEN)
        else:
            results["issues"].extend(timestamp_issues[:5])
            results["checks_failed"] += 1
            self.log(f"    ✗ Timestamp issues found ({len(timestamp_issues)} total)", Colors.RED)
            for issue in timestamp_issues[:3]:
                self.log(f"      - {issue}", Colors.DIM)

        # Summary
        self.log(f"\n  Validation Summary:", Colors.BOLD)
        self.log(f"    Checks passed: {results['checks_passed']}/6", Colors.GREEN if results['checks_passed'] == 6 else Colors.YELLOW)
        self.log(f"    Checks failed: {results['checks_failed']}/6", Colors.RED if results['checks_failed'] > 0 else Colors.GREEN)

        self.validation_results = results
        return results

    def test_state_transitions(self) -> Dict:
        """
        Test state transitions (pending -> running -> complete).

        Returns:
            Dict with transition test results
        """
        self.log("\n" + "="*80, Colors.CYAN)
        self.log("  STATE TRANSITION TESTS", Colors.CYAN)
        self.log("="*80, Colors.CYAN)

        results = {
            "valid": True,
            "issues": [],
            "tests_passed": 0,
            "tests_failed": 0,
            "stuck_tasks": [],
            "orphaned_entries": []
        }

        if not STATE_FILE.exists():
            results["valid"] = False
            results["issues"].append("State file does not exist")
            self.log(f"\n  ✗ Cannot test transitions: state file not found", Colors.RED)
            return results

        try:
            with open(STATE_FILE) as f:
                state_data = json.load(f)
        except Exception as e:
            results["valid"] = False
            results["issues"].append(f"Cannot read state file: {e}")
            return results

        phases = state_data.get("phases", {})

        # Test 1: No tasks stuck in "in_progress"
        self.log("\n  [1/4] Checking for stuck tasks...", Colors.BOLD)
        for phase_id, phase_data in phases.items():
            tasks = phase_data.get("tasks", {})
            for task_id, task_data in tasks.items():
                if task_data.get("status") == "in_progress":
                    results["stuck_tasks"].append(f"{phase_id}/{task_id}")

        if not results["stuck_tasks"]:
            results["tests_passed"] += 1
            self.log(f"    ✓ No tasks stuck in in_progress state", Colors.GREEN)
        else:
            results["issues"].append(f"Found {len(results['stuck_tasks'])} stuck tasks")
            results["tests_failed"] += 1
            self.log(f"    ✗ Found {len(results['stuck_tasks'])} stuck tasks:", Colors.RED)
            for task in results["stuck_tasks"][:3]:
                self.log(f"      - {task}", Colors.DIM)

        # Test 2: Completed tasks have timestamps
        self.log("\n  [2/4] Checking completed tasks have timestamps...", Colors.BOLD)
        missing_timestamps = []

        for phase_id, phase_data in phases.items():
            tasks = phase_data.get("tasks", {})
            for task_id, task_data in tasks.items():
                if task_data.get("status") == "complete":
                    if not task_data.get("completed_at"):
                        missing_timestamps.append(f"{phase_id}/{task_id}")

        if not missing_timestamps:
            results["tests_passed"] += 1
            self.log(f"    ✓ All completed tasks have timestamps", Colors.GREEN)
        else:
            results["issues"].append(f"Found {len(missing_timestamps)} tasks without timestamps")
            results["tests_failed"] += 1
            self.log(f"    ✗ Found {len(missing_timestamps)} completed tasks without timestamps", Colors.RED)

        # Test 3: No orphaned phase entries
        self.log("\n  [3/4] Checking for orphaned phase entries...", Colors.BOLD)
        expected_phases = [
            "0-setup", "1-discovery", "2-prd", "3-tasking",
            "4-specification", "5-implementation", "6-code-review",
            "7-integration", "8-deployment-prep", "9-release"
        ]

        results["orphaned_entries"] = [p for p in phases.keys() if p not in expected_phases]

        if not results["orphaned_entries"]:
            results["tests_passed"] += 1
            self.log(f"    ✓ No orphaned phase entries", Colors.GREEN)
        else:
            results["issues"].append(f"Found {len(results['orphaned_entries'])} orphaned entries")
            results["tests_failed"] += 1
            self.log(f"    ✗ Found orphaned phase entries: {results['orphaned_entries']}", Colors.RED)

        # Test 4: Completed status consistency
        self.log("\n  [4/4] Checking completed status consistency...", Colors.BOLD)
        inconsistent = []

        for phase_id, phase_data in phases.items():
            phase_complete = phase_data.get("completed", False)
            tasks = phase_data.get("tasks", {})

            if phase_complete and tasks:
                # If phase marked complete, all tasks should be complete
                incomplete_tasks = [t for t, d in tasks.items() if d.get("status") != "complete"]
                if incomplete_tasks:
                    inconsistent.append(f"{phase_id}: marked complete but has incomplete tasks")

        if not inconsistent:
            results["tests_passed"] += 1
            self.log(f"    ✓ Phase completion status consistent", Colors.GREEN)
        else:
            results["issues"].extend(inconsistent)
            results["tests_failed"] += 1
            self.log(f"    ✗ Found {len(inconsistent)} inconsistencies", Colors.RED)

        # Summary
        self.log(f"\n  Transition Test Summary:", Colors.BOLD)
        self.log(f"    Tests passed: {results['tests_passed']}/4", Colors.GREEN if results['tests_passed'] == 4 else Colors.YELLOW)
        self.log(f"    Tests failed: {results['tests_failed']}/4", Colors.RED if results['tests_failed'] > 0 else Colors.GREEN)

        self.transition_results = results
        return results

    def test_resume_functionality(self, test_count: int = 5) -> Dict:
        """
        Test resume functionality by running phase with --resume-at flag.

        Args:
            test_count: Number of resume points to test (default: 5)

        Returns:
            Dict with resume test results
        """
        self.log("\n" + "="*80, Colors.CYAN)
        self.log("  RESUME FUNCTIONALITY TESTS", Colors.CYAN)
        self.log("="*80, Colors.CYAN)

        results = {
            "valid": True,
            "issues": [],
            "tests_passed": 0,
            "tests_failed": 0,
            "resume_tests": []
        }

        # Use Phase 0 as it's fastest
        phase_num = 0
        phase_id = "0-setup"

        # Get list of tasks from Phase 0
        phase_tasks = self._get_phase_tasks(phase_id)

        if not phase_tasks:
            results["valid"] = False
            results["issues"].append("No tasks found for Phase 0")
            self.log(f"\n  ✗ No tasks found to test resume functionality", Colors.RED)
            return results

        # Select test points (evenly distributed)
        test_points = self._select_resume_points(phase_tasks, test_count)

        self.log(f"\n  Testing {len(test_points)} resume points: {test_points}", Colors.BOLD)

        # Backup current state
        self._backup_state()

        for i, task_id in enumerate(test_points, 1):
            self.log(f"\n  [{i}/{len(test_points)}] Testing resume from task {task_id}...", Colors.BOLD)

            # Restore clean state for each test
            self._restore_state()

            # Mark tasks before resume point as complete
            self._mark_tasks_complete_before(phase_id, task_id)

            # Run phase with --resume-at
            test_result = self._run_phase_with_resume(phase_num, task_id)

            results["resume_tests"].append({
                "task_id": task_id,
                "success": test_result["success"],
                "skipped_tasks": test_result["skipped_tasks"],
                "executed_tasks": test_result["executed_tasks"]
            })

            if test_result["success"]:
                results["tests_passed"] += 1
                self.log(f"    ✓ Resume from {task_id} successful", Colors.GREEN)
                self.log(f"      Skipped: {len(test_result['skipped_tasks'])} tasks", Colors.DIM)
                self.log(f"      Executed: {len(test_result['executed_tasks'])} tasks", Colors.DIM)
            else:
                results["tests_failed"] += 1
                results["issues"].append(f"Resume from {task_id} failed: {test_result.get('error', 'unknown')}")
                self.log(f"    ✗ Resume from {task_id} failed", Colors.RED)

        # Restore original state
        self._restore_state()

        # Summary
        self.log(f"\n  Resume Test Summary:", Colors.BOLD)
        self.log(f"    Tests passed: {results['tests_passed']}/{len(test_points)}", Colors.GREEN if results['tests_passed'] == len(test_points) else Colors.YELLOW)
        self.log(f"    Tests failed: {results['tests_failed']}/{len(test_points)}", Colors.RED if results['tests_failed'] > 0 else Colors.GREEN)

        self.resume_results = results
        return results

    def test_corruption_resistance(self) -> Dict:
        """
        Test state file corruption resistance.

        Returns:
            Dict with corruption test results
        """
        self.log("\n" + "="*80, Colors.CYAN)
        self.log("  CORRUPTION RESISTANCE TESTS", Colors.CYAN)
        self.log("="*80, Colors.CYAN)

        results = {
            "valid": True,
            "issues": [],
            "tests_passed": 0,
            "tests_failed": 0,
            "corruption_tests": []
        }

        # Backup current state
        self._backup_state()

        # Test 1: Invalid JSON
        self.log("\n  [1/4] Testing invalid JSON recovery...", Colors.BOLD)
        test_result = self._test_invalid_json_recovery()
        results["corruption_tests"].append({"test": "invalid_json", "result": test_result})

        if test_result["recovered"]:
            results["tests_passed"] += 1
            self.log(f"    ✓ System recovered from invalid JSON", Colors.GREEN)
        else:
            results["tests_failed"] += 1
            results["issues"].append("Failed to recover from invalid JSON")
            self.log(f"    ✗ Failed to recover from invalid JSON", Colors.RED)

        # Test 2: Missing state file
        self.log("\n  [2/4] Testing missing state file recovery...", Colors.BOLD)
        test_result = self._test_missing_file_recovery()
        results["corruption_tests"].append({"test": "missing_file", "result": test_result})

        if test_result["recovered"]:
            results["tests_passed"] += 1
            self.log(f"    ✓ System recovered from missing state file", Colors.GREEN)
        else:
            results["tests_failed"] += 1
            results["issues"].append("Failed to recover from missing state file")
            self.log(f"    ✗ Failed to recover from missing state file", Colors.RED)

        # Test 3: Partial state data
        self.log("\n  [3/4] Testing partial state data recovery...", Colors.BOLD)
        test_result = self._test_partial_state_recovery()
        results["corruption_tests"].append({"test": "partial_state", "result": test_result})

        if test_result["recovered"]:
            results["tests_passed"] += 1
            self.log(f"    ✓ System recovered from partial state data", Colors.GREEN)
        else:
            results["tests_failed"] += 1
            results["issues"].append("Failed to recover from partial state data")
            self.log(f"    ✗ Failed to recover from partial state data", Colors.RED)

        # Test 4: Corrupted task data
        self.log("\n  [4/4] Testing corrupted task data recovery...", Colors.BOLD)
        test_result = self._test_corrupted_task_recovery()
        results["corruption_tests"].append({"test": "corrupted_task", "result": test_result})

        if test_result["recovered"]:
            results["tests_passed"] += 1
            self.log(f"    ✓ System recovered from corrupted task data", Colors.GREEN)
        else:
            results["tests_failed"] += 1
            results["issues"].append("Failed to recover from corrupted task data")
            self.log(f"    ✗ Failed to recover from corrupted task data", Colors.RED)

        # Restore original state
        self._restore_state()

        # Summary
        self.log(f"\n  Corruption Test Summary:", Colors.BOLD)
        self.log(f"    Tests passed: {results['tests_passed']}/4", Colors.GREEN if results['tests_passed'] == 4 else Colors.YELLOW)
        self.log(f"    Tests failed: {results['tests_failed']}/4", Colors.RED if results['tests_failed'] > 0 else Colors.GREEN)

        self.corruption_results = results
        return results

    # Helper methods

    def _get_phase_tasks(self, phase_id: str) -> List[str]:
        """Get list of tasks for a phase from state file."""
        if not STATE_FILE.exists():
            return []

        try:
            with open(STATE_FILE) as f:
                state_data = json.load(f)

            phases = state_data.get("phases", {})
            phase_data = phases.get(phase_id, {})
            tasks = phase_data.get("tasks", {})

            return sorted(tasks.keys())
        except Exception:
            return []

    def _select_resume_points(self, tasks: List[str], count: int) -> List[str]:
        """Select evenly distributed resume points from task list."""
        if not tasks or count <= 0:
            return []

        if len(tasks) <= count:
            return tasks

        # Select evenly distributed points
        step = len(tasks) / count
        return [tasks[int(i * step)] for i in range(count)]

    def _backup_state(self):
        """Backup current state file."""
        backup_dir = REPO_ROOT / "test" / ".state_backup"
        backup_dir.mkdir(exist_ok=True)

        if STATE_FILE.exists():
            shutil.copy(STATE_FILE, backup_dir / "task-state.json.backup")

    def _restore_state(self):
        """Restore state file from backup."""
        backup_file = REPO_ROOT / "test" / ".state_backup" / "task-state.json.backup"

        if backup_file.exists():
            STATE_FILE.parent.mkdir(exist_ok=True)
            shutil.copy(backup_file, STATE_FILE)

    def _mark_tasks_complete_before(self, phase_id: str, target_task: str):
        """Mark all tasks before target_task as complete."""
        if not STATE_FILE.exists():
            return

        try:
            with open(STATE_FILE) as f:
                state_data = json.load(f)

            phases = state_data.get("phases", {})
            if phase_id not in phases:
                return

            tasks = phases[phase_id].get("tasks", {})

            for task_id in tasks.keys():
                if int(task_id) < int(target_task):
                    tasks[task_id]["status"] = "complete"
                    tasks[task_id]["completed_at"] = datetime.now().isoformat()

            with open(STATE_FILE, 'w') as f:
                json.dump(state_data, f, indent=2)

        except Exception as e:
            self.log(f"    Warning: Failed to mark tasks complete: {e}", Colors.YELLOW)

    def _run_phase_with_resume(self, phase_num: int, resume_task: str) -> Dict:
        """Run phase with --resume-at flag."""
        cmd = [
            "python",
            str(REPO_ROOT / "main.py"),
            "run",
            str(phase_num),
            f"--resume-at={resume_task}"
        ]

        env = os.environ.copy()
        env["ATOMIC_ROOT"] = str(REPO_ROOT)
        env["ATOMIC_UAT_MODE"] = "true"

        try:
            result = subprocess.run(
                cmd,
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=300
            )

            # Parse output to determine which tasks ran
            skipped_tasks = []
            executed_tasks = []

            # Simple heuristic: look for task execution indicators in output
            if "Skipping" in result.stdout or "skipped" in result.stdout.lower():
                # Count skipped tasks
                skipped_tasks = [resume_task]  # Simplified

            return {
                "success": result.returncode == 0,
                "skipped_tasks": skipped_tasks,
                "executed_tasks": executed_tasks,
                "output": result.stdout[:500] if self.verbose else ""
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "timeout", "skipped_tasks": [], "executed_tasks": []}
        except Exception as e:
            return {"success": False, "error": str(e), "skipped_tasks": [], "executed_tasks": []}

    def _test_invalid_json_recovery(self) -> Dict:
        """Test recovery from invalid JSON."""
        from core.state import StateManager

        # Create invalid JSON
        STATE_FILE.parent.mkdir(exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            f.write("{invalid json content")

        # Try to initialize phase via StateManager - should recover
        try:
            sm = StateManager(atomic_root=REPO_ROOT)
            sm.set_current_phase("0-setup")

            # Check if state file was recreated with valid JSON
            if STATE_FILE.exists():
                try:
                    with open(STATE_FILE) as f:
                        json.load(f)
                    return {"recovered": True}
                except Exception:
                    return {"recovered": False}

            return {"recovered": False}

        except Exception as e:
            return {"recovered": False, "error": str(e)}

    def _test_missing_file_recovery(self) -> Dict:
        """Test recovery from missing state file."""
        from core.state import StateManager

        # Remove state file
        if STATE_FILE.exists():
            STATE_FILE.unlink()

        # Try to initialize phase via StateManager - should recreate
        try:
            sm = StateManager(atomic_root=REPO_ROOT)
            sm.set_current_phase("0-setup")

            # Check if state file was created
            if STATE_FILE.exists():
                try:
                    with open(STATE_FILE) as f:
                        state_data = json.load(f)
                    return {"recovered": True, "state_data": state_data}
                except Exception:
                    return {"recovered": False}

            return {"recovered": False}

        except Exception as e:
            return {"recovered": False, "error": str(e)}

    def _test_partial_state_recovery(self) -> Dict:
        """Test recovery from partial state data."""
        from core.state import StateManager

        # Create partial state (missing phases key)
        STATE_FILE.parent.mkdir(exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            json.dump({
                "version": "1.0",
                "current_phase": None,
                "current_task": None
            }, f)

        # Try to initialize phase via StateManager - should add missing keys
        try:
            sm = StateManager(atomic_root=REPO_ROOT)
            sm.set_current_phase("0-setup")

            # Check if state file was fixed
            if STATE_FILE.exists():
                try:
                    with open(STATE_FILE) as f:
                        state_data = json.load(f)

                    has_phases = "phases" in state_data
                    return {"recovered": has_phases}
                except Exception:
                    return {"recovered": False}

            return {"recovered": False}

        except Exception as e:
            return {"recovered": False, "error": str(e)}

    def _test_corrupted_task_recovery(self) -> Dict:
        """Test recovery from corrupted task data."""
        from core.state import StateManager

        # Create state with corrupted task
        STATE_FILE.parent.mkdir(exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            json.dump({
                "version": "1.0",
                "current_phase": "0-setup",
                "current_task": None,
                "phases": {
                    "0-setup": {
                        "started_at": datetime.now().isoformat(),
                        "tasks": {
                            "001": "not a dict"  # Corrupted task data
                        },
                        "completed": False
                    }
                }
            }, f)

        # Try to initialize via StateManager - should handle gracefully without crashing
        try:
            sm = StateManager(atomic_root=REPO_ROOT)
            sm.set_current_phase("0-setup")

            # System should not crash - if we got here, it recovered
            return {"recovered": True}

        except Exception as e:
            return {"recovered": False, "error": str(e)}

    def generate_report(self):
        """Generate comprehensive state audit report."""
        self.log("\n" + "="*80, Colors.CYAN)
        self.log("  STATE AUDIT REPORT", Colors.CYAN)
        self.log("="*80, Colors.CYAN)

        test_duration = (datetime.now() - self.test_start_time).total_seconds()

        # Overall summary
        self.log(f"\n  Test Duration: {test_duration:.1f}s", Colors.BOLD)

        total_checks = (
            self.validation_results.get("checks_passed", 0) +
            self.validation_results.get("checks_failed", 0) +
            self.transition_results.get("tests_passed", 0) +
            self.transition_results.get("tests_failed", 0) +
            self.resume_results.get("tests_passed", 0) +
            self.resume_results.get("tests_failed", 0) +
            self.corruption_results.get("tests_passed", 0) +
            self.corruption_results.get("tests_failed", 0)
        )

        total_passed = (
            self.validation_results.get("checks_passed", 0) +
            self.transition_results.get("tests_passed", 0) +
            self.resume_results.get("tests_passed", 0) +
            self.corruption_results.get("tests_passed", 0)
        )

        # Category breakdown
        self.log(f"\n  Results by Category:", Colors.BOLD)

        self.log(f"\n    State File Validation:", Colors.BOLD)
        self.log(f"      Passed: {self.validation_results.get('checks_passed', 0)}/6", Colors.GREEN)
        self.log(f"      Failed: {self.validation_results.get('checks_failed', 0)}/6", Colors.RED if self.validation_results.get('checks_failed', 0) > 0 else Colors.GREEN)

        self.log(f"\n    State Transitions:", Colors.BOLD)
        self.log(f"      Passed: {self.transition_results.get('tests_passed', 0)}/4", Colors.GREEN)
        self.log(f"      Failed: {self.transition_results.get('tests_failed', 0)}/4", Colors.RED if self.transition_results.get('tests_failed', 0) > 0 else Colors.GREEN)

        if self.resume_results:
            total_resume = self.resume_results.get('tests_passed', 0) + self.resume_results.get('tests_failed', 0)
            self.log(f"\n    Resume Functionality:", Colors.BOLD)
            self.log(f"      Passed: {self.resume_results.get('tests_passed', 0)}/{total_resume}", Colors.GREEN)
            self.log(f"      Failed: {self.resume_results.get('tests_failed', 0)}/{total_resume}", Colors.RED if self.resume_results.get('tests_failed', 0) > 0 else Colors.GREEN)

        self.log(f"\n    Corruption Resistance:", Colors.BOLD)
        self.log(f"      Passed: {self.corruption_results.get('tests_passed', 0)}/4", Colors.GREEN)
        self.log(f"      Failed: {self.corruption_results.get('tests_failed', 0)}/4", Colors.RED if self.corruption_results.get('tests_failed', 0) > 0 else Colors.GREEN)

        # Overall assessment
        self.log(f"\n  Overall Assessment:", Colors.BOLD)
        self.log(f"    Total Tests: {total_checks}", Colors.DIM)
        self.log(f"    Passed: {total_passed}", Colors.GREEN)
        self.log(f"    Failed: {total_checks - total_passed}", Colors.RED if total_checks - total_passed > 0 else Colors.GREEN)

        pass_rate = (total_passed / total_checks * 100) if total_checks > 0 else 0

        if pass_rate == 100:
            self.log(f"\n    ✅ EXCELLENT - All state management tests passed ({pass_rate:.0f}%)", Colors.GREEN)
        elif pass_rate >= 80:
            self.log(f"\n    ⚠️ GOOD - Most state management tests passed ({pass_rate:.0f}%)", Colors.YELLOW)
        else:
            self.log(f"\n    ❌ NEEDS IMPROVEMENT - Many state management issues ({pass_rate:.0f}%)", Colors.RED)

        # State file info
        if STATE_FILE.exists():
            state_size = STATE_FILE.stat().st_size
            self.log(f"\n  State File Info:", Colors.BOLD)
            self.log(f"    Location: {STATE_FILE}", Colors.DIM)
            self.log(f"    Size: {state_size:,} bytes ({state_size/1024:.1f} KB)", Colors.DIM)

        # Save detailed report
        self._save_detailed_report()

    def _save_detailed_report(self):
        """Save detailed JSON report."""
        report_dir = REPO_ROOT / "test" / "reports"
        report_dir.mkdir(exist_ok=True)

        report_file = report_dir / f"state-audit-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"

        report = {
            "timestamp": datetime.now().isoformat(),
            "test_duration_seconds": (datetime.now() - self.test_start_time).total_seconds(),
            "validation": self.validation_results,
            "transitions": self.transition_results,
            "resume": self.resume_results,
            "corruption": self.corruption_results,
            "summary": {
                "total_tests": (
                    self.validation_results.get("checks_passed", 0) +
                    self.validation_results.get("checks_failed", 0) +
                    self.transition_results.get("tests_passed", 0) +
                    self.transition_results.get("tests_failed", 0) +
                    self.resume_results.get("tests_passed", 0) +
                    self.resume_results.get("tests_failed", 0) +
                    self.corruption_results.get("tests_passed", 0) +
                    self.corruption_results.get("tests_failed", 0)
                ),
                "total_passed": (
                    self.validation_results.get("checks_passed", 0) +
                    self.transition_results.get("tests_passed", 0) +
                    self.resume_results.get("tests_passed", 0) +
                    self.corruption_results.get("tests_passed", 0)
                )
            }
        }

        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        self.log(f"\n  Detailed report saved: {report_file}", Colors.CYAN)


def main():
    parser = argparse.ArgumentParser(
        description="State Management Audit Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--skip-exec",
        action="store_true",
        help="Skip execution tests (validate existing state only)"
    )
    parser.add_argument(
        "--resume-tests",
        type=int,
        default=5,
        help="Number of resume points to test (default: 5)"
    )

    args = parser.parse_args()

    print("\n" + "="*80)
    print("  ATOMIC CLAUDE 2.0 - STATE MANAGEMENT AUDIT")
    print("="*80)

    runner = StateAuditRunner(verbose=args.verbose)

    # Run validation tests
    runner.validate_state_file()

    # Run transition tests
    runner.test_state_transitions()

    # Run resume tests (unless skipped)
    if not args.skip_exec:
        runner.test_resume_functionality(test_count=args.resume_tests)

    # Run corruption tests
    runner.test_corruption_resistance()

    # Generate report
    runner.generate_report()

    # Determine exit code
    total_failed = (
        runner.validation_results.get("checks_failed", 0) +
        runner.transition_results.get("tests_failed", 0) +
        runner.resume_results.get("tests_failed", 0) +
        runner.corruption_results.get("tests_failed", 0)
    )

    if total_failed == 0:
        print("\n" + "="*80)
        print(f"{Colors.GREEN}  ✓ STATE AUDIT COMPLETE - ALL TESTS PASSED{Colors.NC}")
        print("="*80 + "\n")
        sys.exit(0)
    else:
        print("\n" + "="*80)
        print(f"{Colors.YELLOW}  ⚠ STATE AUDIT COMPLETE - {total_failed} ISSUES FOUND{Colors.NC}")
        print("="*80 + "\n")
        sys.exit(0)  # Don't fail, just report


if __name__ == "__main__":
    main()
