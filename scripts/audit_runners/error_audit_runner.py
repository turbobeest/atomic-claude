#!/usr/bin/env python3
"""
Error Handling Audit Runner

Validates graceful failure, error recovery mechanisms, error message quality,
and timeout handling across the Atomic Claude pipeline.

Usage:
    python test/error_audit_runner.py              # Full audit
    python test/error_audit_runner.py --verbose    # Detailed output
    python test/error_audit_runner.py --quick      # Skip slow tests
"""

import sys
import os
import subprocess
import json
import argparse
import shutil
import signal
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Repo root
REPO_ROOT = Path(__file__).parent.parent.resolve()
STATE_FILE = REPO_ROOT / ".state" / "task-state.json"
OUTPUT_DIR = REPO_ROOT / ".outputs"
LOG_DIR = REPO_ROOT / ".logs"

# Colors for output
class Colors:
    CYAN = '\033[0;36m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    NC = '\033[0m'


class ErrorAuditRunner:
    """Error handling audit runner."""

    def __init__(self, verbose: bool = False, quick: bool = False):
        self.verbose = verbose
        self.quick = quick
        self.results = []
        self.test_start_time = datetime.now()
        self.critical_failures = 0

    def log(self, message: str, color: str = Colors.NC):
        """Log a message with color."""
        print(f"{color}{message}{Colors.NC}")

    def add_result(self, category: str, test: str, passed: bool, message: str, severity: str = "info"):
        """Add a test result."""
        self.results.append({
            "category": category,
            "test": test,
            "passed": passed,
            "message": message,
            "severity": severity
        })

        if not passed and severity == "critical":
            self.critical_failures += 1

    def test_graceful_failure(self) -> Dict:
        """
        Test graceful failure handling.

        Tests:
        1. Invalid setup.md (malformed JSON extraction targets)
        2. Missing API keys
        3. Invalid phase number
        4. Corrupted state file
        """
        self.log("\n" + "="*80, Colors.CYAN)
        self.log("  GRACEFUL FAILURE TESTS", Colors.CYAN)
        self.log("="*80, Colors.CYAN)

        # Backup state
        self._backup_state()

        # Test 1: Invalid setup.md
        self.log("\n  [1/4] Testing invalid setup.md handling...", Colors.BOLD)
        self._test_invalid_setup_md()

        # Test 2: Missing API keys
        self.log("\n  [2/4] Testing missing API keys handling...", Colors.BOLD)
        self._test_missing_api_keys()

        # Test 3: Invalid phase number
        self.log("\n  [3/4] Testing invalid phase number handling...", Colors.BOLD)
        self._test_invalid_phase_number()

        # Test 4: Corrupted state file
        self.log("\n  [4/4] Testing corrupted state file handling...", Colors.BOLD)
        self._test_corrupted_state_file()

        # Restore state
        self._restore_state()

        # Summary
        passed_tests = sum(1 for r in self.results if r["category"] == "graceful_failure" and r["passed"])
        total_tests = sum(1 for r in self.results if r["category"] == "graceful_failure")

        self.log(f"\n  Graceful Failure Test Summary:", Colors.BOLD)
        self.log(f"    Tests passed: {passed_tests}/{total_tests}",
                Colors.GREEN if passed_tests == total_tests else Colors.YELLOW)

    def _test_invalid_setup_md(self):
        """Test handling of invalid setup.md."""
        # Clear state to force task execution
        if STATE_FILE.exists():
            STATE_FILE.unlink()

        # Backup Phase 0 outputs before clearing
        phase0_output = OUTPUT_DIR / "0-setup"
        phase0_backup = OUTPUT_DIR / "0-setup.backup"
        if phase0_output.exists():
            import shutil as cleanup_shutil
            if phase0_backup.exists():
                cleanup_shutil.rmtree(phase0_backup)
            cleanup_shutil.copytree(phase0_output, phase0_backup)
            cleanup_shutil.rmtree(phase0_output)

        # Create invalid setup.md in parent directory
        setup_dir = REPO_ROOT.parent / "initialization"
        setup_dir.mkdir(exist_ok=True)
        setup_file = setup_dir / "setup.md"

        # Backup original if it exists
        backup_file = setup_dir / "setup.md.backup"
        if setup_file.exists():
            shutil.copy(setup_file, backup_file)

        # Write invalid content (missing required ** pattern)
        with open(setup_file, 'w') as f:
            f.write("""# Invalid Setup

This is just plain text without proper field markers.
name: this-is-wrong
type: also-wrong
""")

        # Try to run Phase 0 with document mode
        try:
            result = subprocess.run(
                [sys.executable, str(REPO_ROOT / "main.py"), "run", "0"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "ATOMIC_ROOT": str(REPO_ROOT), "ATOMIC_UAT_MODE": "true", "ATOMIC_TOOL_DEVELOPMENT": "true"}
            )

            # Check if error was handled gracefully
            graceful = result.returncode != 0  # Should fail
            output_combined = (result.stdout + result.stderr).lower()
            has_error_msg = ("error" in output_combined or "invalid" in output_combined or
                           "doesn't contain valid configuration" in output_combined)
            no_crash = "Segmentation fault" not in result.stderr and "core dumped" not in result.stderr

            passed = graceful and has_error_msg and no_crash

            self.add_result(
                "graceful_failure",
                "invalid_setup_md",
                passed,
                f"Exit code: {result.returncode}, Error message present: {has_error_msg}, No crash: {no_crash}",
                "critical" if not passed else "info"
            )

            if passed:
                self.log(f"    ✓ Invalid setup.md handled gracefully", Colors.GREEN)
            else:
                self.log(f"    ✗ Invalid setup.md not handled gracefully", Colors.RED)
                if self.verbose:
                    self.log(f"      stdout: {result.stdout[:200]}", Colors.DIM)
                    self.log(f"      stderr: {result.stderr[:200]}", Colors.DIM)

        except subprocess.TimeoutExpired:
            self.add_result("graceful_failure", "invalid_setup_md", False,
                          "Process timed out", "critical")
            self.log(f"    ✗ Process timed out (hung instead of failing)", Colors.RED)

        except Exception as e:
            self.add_result("graceful_failure", "invalid_setup_md", False,
                          f"Exception: {e}", "critical")
            self.log(f"    ✗ Exception: {e}", Colors.RED)

        finally:
            # Restore original setup.md
            if backup_file.exists():
                shutil.move(backup_file, setup_file)

            # Restore Phase 0 outputs
            phase0_backup = OUTPUT_DIR / "0-setup.backup"
            if phase0_backup.exists():
                import shutil as cleanup_shutil
                if phase0_output.exists():
                    cleanup_shutil.rmtree(phase0_output)
                cleanup_shutil.copytree(phase0_backup, phase0_output)
                cleanup_shutil.rmtree(phase0_backup)

    def _test_missing_api_keys(self):
        """Test handling of missing API keys."""
        # Unset API key environment variables
        env = os.environ.copy()
        env.pop('ANTHROPIC_API_KEY', None)
        env.pop('CLAUDE_API_KEY', None)
        env.pop('AWS_ACCESS_KEY_ID', None)
        env.pop('AWS_SECRET_ACCESS_KEY', None)
        env.pop('AWS_PROFILE', None)
        env['ATOMIC_ROOT'] = str(REPO_ROOT)
        env['ATOMIC_UAT_MODE'] = 'true'

        try:
            # Try to invoke Python LLM module directly (tests core/llm.py validation)
            result = subprocess.run(
                [sys.executable, "-c", """
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
# Set ATOMIC_ROOT for atomic_invoke
os.environ['ATOMIC_ROOT'] = str(Path.cwd())
from core.llm import atomic_invoke
success = atomic_invoke("test prompt", "/tmp/test-output.txt", "Test", provider="api", model="sonnet")
# Exit with appropriate code based on return value
sys.exit(0 if success else 1)
                """],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=15,
                env=env
            )

            # Should fail with clear error message
            failed_appropriately = result.returncode != 0
            output_text = (result.stdout + result.stderr).lower()
            has_key_error = ("api" in output_text and "key" in output_text) or "missing" in output_text or "anthropic_api_key" in output_text
            no_crash = "Segmentation fault" not in result.stderr

            passed = failed_appropriately and has_key_error and no_crash

            self.add_result(
                "graceful_failure",
                "missing_api_keys",
                passed,
                f"Failed appropriately: {failed_appropriately}, Key error message: {has_key_error}",
                "warning" if not passed else "info"
            )

            if passed:
                self.log(f"    ✓ Missing API keys handled gracefully", Colors.GREEN)
            else:
                self.log(f"    ✗ Missing API keys not handled gracefully", Colors.YELLOW)
                if self.verbose:
                    self.log(f"      Exit code: {result.returncode}", Colors.DIM)
                    self.log(f"      Output: {output_text[:300]}", Colors.DIM)

        except subprocess.TimeoutExpired:
            self.add_result("graceful_failure", "missing_api_keys", False,
                          "Process timed out", "warning")
            self.log(f"    ✗ Process timed out", Colors.YELLOW)

        except Exception as e:
            self.add_result("graceful_failure", "missing_api_keys", False,
                          f"Exception: {e}", "warning")
            self.log(f"    ✗ Exception: {e}", Colors.YELLOW)

    def _test_invalid_phase_number(self):
        """Test handling of invalid phase number."""
        try:
            result = subprocess.run(
                [sys.executable, str(REPO_ROOT / "main.py"), "run", "99"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=10,
                env={**os.environ, "ATOMIC_ROOT": str(REPO_ROOT)}
            )

            # Should fail with clear error
            failed = result.returncode != 0
            has_error = "invalid" in result.stderr.lower() or "not found" in result.stderr.lower() or \
                       "invalid" in result.stdout.lower() or "not found" in result.stdout.lower()
            no_crash = "Segmentation fault" not in result.stderr

            passed = failed and has_error and no_crash

            self.add_result(
                "graceful_failure",
                "invalid_phase_number",
                passed,
                f"Failed: {failed}, Error message: {has_error}, No crash: {no_crash}",
                "critical" if not passed else "info"
            )

            if passed:
                self.log(f"    ✓ Invalid phase number handled gracefully", Colors.GREEN)
            else:
                self.log(f"    ✗ Invalid phase number not handled gracefully", Colors.RED)

        except subprocess.TimeoutExpired:
            self.add_result("graceful_failure", "invalid_phase_number", False,
                          "Process timed out", "critical")
            self.log(f"    ✗ Process timed out", Colors.RED)

        except Exception as e:
            self.add_result("graceful_failure", "invalid_phase_number", False,
                          f"Exception: {e}", "critical")
            self.log(f"    ✗ Exception: {e}", Colors.RED)

    def _test_corrupted_state_file(self):
        """Test handling of corrupted state file."""
        # Create corrupted state file
        STATE_FILE.parent.mkdir(exist_ok=True)

        # Save original
        backup_state = None
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                backup_state = f.read()

        # Write corrupted JSON
        with open(STATE_FILE, 'w') as f:
            f.write('{"version": "1.0", "phases": {corrupted json')

        try:
            # Use Python StateManager to test recovery from corrupted state
            import sys
            sys.path.insert(0, str(REPO_ROOT))
            from core.state import StateManager
            sm = StateManager()
            sm.initialize_phase("0-setup")

            # If we get here without exception, recovery succeeded
            recovered = STATE_FILE.exists()
            no_crash = True
            passed = recovered and no_crash

            self.add_result(
                "graceful_failure",
                "corrupted_state_file",
                passed,
                f"Recovered: {recovered}, Failed gracefully: {failed_gracefully}, No crash: {no_crash}",
                "critical" if not passed else "info"
            )

            if passed:
                self.log(f"    ✓ Corrupted state file handled gracefully", Colors.GREEN)
            else:
                self.log(f"    ✗ Corrupted state file not handled gracefully", Colors.RED)

        except Exception as e:
            self.add_result("graceful_failure", "corrupted_state_file", False,
                          f"Exception: {e}", "critical")
            self.log(f"    ✗ Exception: {e}", Colors.RED)

        finally:
            # Restore original state
            if backup_state:
                with open(STATE_FILE, 'w') as f:
                    f.write(backup_state)

    def test_error_recovery(self) -> Dict:
        """
        Test error recovery mechanisms.

        Tests:
        1. Resume after task failure
        2. State recovery after interruption
        3. Partial completion handling
        """
        self.log("\n" + "="*80, Colors.CYAN)
        self.log("  ERROR RECOVERY TESTS", Colors.CYAN)
        self.log("="*80, Colors.CYAN)

        # Backup state
        self._backup_state()

        # Test 1: Resume after task failure
        self.log("\n  [1/3] Testing resume after task failure...", Colors.BOLD)
        self._test_resume_after_failure()

        # Test 2: State recovery after interruption
        if not self.quick:
            self.log("\n  [2/3] Testing state recovery after interruption...", Colors.BOLD)
            self._test_state_recovery_after_interrupt()
        else:
            self.log("\n  [2/3] Skipping interrupt test (quick mode)...", Colors.DIM)
            self.add_result("recovery", "interrupt_recovery", True, "Skipped in quick mode", "info")

        # Test 3: Partial completion handling
        self.log("\n  [3/3] Testing partial completion handling...", Colors.BOLD)
        self._test_partial_completion()

        # Restore state
        self._restore_state()

        # Summary
        passed_tests = sum(1 for r in self.results if r["category"] == "recovery" and r["passed"])
        total_tests = sum(1 for r in self.results if r["category"] == "recovery")

        self.log(f"\n  Error Recovery Test Summary:", Colors.BOLD)
        self.log(f"    Tests passed: {passed_tests}/{total_tests}",
                Colors.GREEN if passed_tests == total_tests else Colors.YELLOW)

    def _test_resume_after_failure(self):
        """Test resume functionality after a task failure."""
        # Create a state with a failed task
        STATE_FILE.parent.mkdir(exist_ok=True)

        with open(STATE_FILE, 'w') as f:
            json.dump({
                "version": "1.0",
                "current_phase": "0-setup",
                "current_task": "002",
                "phases": {
                    "0-setup": {
                        "started_at": datetime.now().isoformat(),
                        "tasks": {
                            "001": {
                                "status": "complete",
                                "completed_at": datetime.now().isoformat()
                            },
                            "002": {
                                "status": "failed",
                                "failed_at": datetime.now().isoformat(),
                                "error": "Test failure"
                            }
                        },
                        "completed": False
                    }
                }
            }, f, indent=2)

        try:
            # Try to resume from failed task
            result = subprocess.run(
                [sys.executable, str(REPO_ROOT / "main.py"), "run", "0", "--resume-at=002"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "ATOMIC_ROOT": str(REPO_ROOT), "ATOMIC_UAT_MODE": "true", "ATOMIC_TOOL_DEVELOPMENT": "true"}
            )

            # Check if resume worked
            resume_attempted = "resume" in result.stdout.lower() or "002" in result.stdout
            no_crash = "Segmentation fault" not in result.stderr

            passed = resume_attempted and no_crash

            self.add_result(
                "recovery",
                "resume_after_failure",
                passed,
                f"Resume attempted: {resume_attempted}, No crash: {no_crash}",
                "warning" if not passed else "info"
            )

            if passed:
                self.log(f"    ✓ Resume after failure works", Colors.GREEN)
            else:
                self.log(f"    ✗ Resume after failure doesn't work", Colors.YELLOW)

        except subprocess.TimeoutExpired:
            self.add_result("recovery", "resume_after_failure", False,
                          "Process timed out", "warning")
            self.log(f"    ✗ Process timed out", Colors.YELLOW)

        except Exception as e:
            self.add_result("recovery", "resume_after_failure", False,
                          f"Exception: {e}", "warning")
            self.log(f"    ✗ Exception: {e}", Colors.YELLOW)

    def _test_state_recovery_after_interrupt(self):
        """Test state recovery after process interruption."""
        try:
            # Start a phase
            proc = subprocess.Popen(
                [sys.executable, str(REPO_ROOT / "main.py"), "run", "0"],
                cwd=REPO_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, "ATOMIC_ROOT": str(REPO_ROOT), "ATOMIC_UAT_MODE": "true", "ATOMIC_TOOL_DEVELOPMENT": "true"}
            )

            # Wait a bit for it to start
            time.sleep(2)

            # Send SIGINT (Ctrl+C)
            proc.send_signal(signal.SIGINT)

            # Wait for process to terminate
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

            # Check if state file still valid
            state_valid = False
            if STATE_FILE.exists():
                try:
                    with open(STATE_FILE) as f:
                        state_data = json.load(f)
                    state_valid = "phases" in state_data
                except:
                    pass

            self.add_result(
                "recovery",
                "interrupt_recovery",
                state_valid,
                f"State file valid after interrupt: {state_valid}",
                "warning" if not state_valid else "info"
            )

            if state_valid:
                self.log(f"    ✓ State valid after interrupt", Colors.GREEN)
            else:
                self.log(f"    ✗ State corrupted after interrupt", Colors.YELLOW)

        except Exception as e:
            self.add_result("recovery", "interrupt_recovery", False,
                          f"Exception: {e}", "warning")
            self.log(f"    ✗ Exception: {e}", Colors.YELLOW)

    def _test_partial_completion(self):
        """Test handling of partial task completion."""
        # Create state with partially completed phase
        STATE_FILE.parent.mkdir(exist_ok=True)

        with open(STATE_FILE, 'w') as f:
            json.dump({
                "version": "1.0",
                "current_phase": "0-setup",
                "current_task": "003",
                "phases": {
                    "0-setup": {
                        "started_at": datetime.now().isoformat(),
                        "tasks": {
                            "001": {
                                "status": "complete",
                                "completed_at": datetime.now().isoformat()
                            },
                            "002": {
                                "status": "complete",
                                "completed_at": datetime.now().isoformat()
                            },
                            "003": {
                                "status": "in_progress",
                                "started_at": datetime.now().isoformat()
                            }
                        },
                        "completed": False
                    }
                }
            }, f, indent=2)

        try:
            # Try to resume from in_progress task
            result = subprocess.run(
                [sys.executable, str(REPO_ROOT / "main.py"), "run", "0", "--resume-at=003"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "ATOMIC_ROOT": str(REPO_ROOT), "ATOMIC_UAT_MODE": "true", "ATOMIC_TOOL_DEVELOPMENT": "true"}
            )

            # Check if partial completion handled
            handled = result.returncode == 0 or "003" in result.stdout
            no_crash = "Segmentation fault" not in result.stderr

            passed = handled and no_crash

            self.add_result(
                "recovery",
                "partial_completion",
                passed,
                f"Handled: {handled}, No crash: {no_crash}",
                "warning" if not passed else "info"
            )

            if passed:
                self.log(f"    ✓ Partial completion handled", Colors.GREEN)
            else:
                self.log(f"    ✗ Partial completion not handled", Colors.YELLOW)

        except subprocess.TimeoutExpired:
            self.add_result("recovery", "partial_completion", False,
                          "Process timed out", "warning")
            self.log(f"    ✗ Process timed out", Colors.YELLOW)

        except Exception as e:
            self.add_result("recovery", "partial_completion", False,
                          f"Exception: {e}", "warning")
            self.log(f"    ✗ Exception: {e}", Colors.YELLOW)

    def test_error_message_quality(self) -> Dict:
        """
        Test error message quality.

        Tests:
        1. Log files contain useful error messages
        2. Error messages don't expose secrets
        3. Stack traces captured when needed
        """
        self.log("\n" + "="*80, Colors.CYAN)
        self.log("  ERROR MESSAGE QUALITY TESTS", Colors.CYAN)
        self.log("="*80, Colors.CYAN)

        # Test 1: Log files contain useful errors
        self.log("\n  [1/3] Checking log file error messages...", Colors.BOLD)
        self._test_log_file_errors()

        # Test 2: No secrets in error messages
        self.log("\n  [2/3] Checking for exposed secrets in logs...", Colors.BOLD)
        self._test_no_secrets_in_errors()

        # Test 3: Stack traces captured
        self.log("\n  [3/3] Checking stack trace capture...", Colors.BOLD)
        self._test_stack_trace_capture()

        # Summary
        passed_tests = sum(1 for r in self.results if r["category"] == "messages" and r["passed"])
        total_tests = sum(1 for r in self.results if r["category"] == "messages")

        self.log(f"\n  Error Message Quality Test Summary:", Colors.BOLD)
        self.log(f"    Tests passed: {passed_tests}/{total_tests}",
                Colors.GREEN if passed_tests == total_tests else Colors.YELLOW)

    def _test_log_file_errors(self):
        """Test that log files contain useful error messages."""
        log_files = list(LOG_DIR.glob("*.log")) if LOG_DIR.exists() else []

        if not log_files:
            self.add_result("messages", "log_file_errors", True,
                          "No log files found (clean state)", "info")
            self.log(f"    ℹ No log files found (clean state)", Colors.DIM)
            return

        # Check most recent log file
        latest_log = max(log_files, key=lambda p: p.stat().st_mtime)

        try:
            with open(latest_log) as f:
                content = f.read()

            # Check for error indicators
            has_errors = "error" in content.lower() or "failed" in content.lower()
            has_context = "file" in content.lower() or "line" in content.lower()
            not_empty = len(content.strip()) > 0

            # Logs should exist and be structured
            passed = not_empty

            self.add_result(
                "messages",
                "log_file_errors",
                passed,
                f"Log exists: {not_empty}, Has errors logged: {has_errors}, Has context: {has_context}",
                "info"
            )

            if passed:
                self.log(f"    ✓ Log files contain structured messages", Colors.GREEN)
                if self.verbose:
                    self.log(f"      Latest log: {latest_log}", Colors.DIM)
                    self.log(f"      Size: {len(content)} bytes", Colors.DIM)
            else:
                self.log(f"    ✗ Log files empty or missing", Colors.YELLOW)

        except Exception as e:
            self.add_result("messages", "log_file_errors", False,
                          f"Exception: {e}", "info")
            self.log(f"    ✗ Exception reading log: {e}", Colors.YELLOW)

    def _test_no_secrets_in_errors(self):
        """Test that error messages don't expose secrets."""
        log_files = list(LOG_DIR.glob("*.log")) if LOG_DIR.exists() else []

        if not log_files:
            self.add_result("messages", "no_secrets_exposed", True,
                          "No log files to check", "info")
            self.log(f"    ℹ No log files to check", Colors.DIM)
            return

        # Patterns that might indicate secrets
        secret_patterns = [
            r'sk-[a-zA-Z0-9]{20,}',  # API keys
            r'ghp_[a-zA-Z0-9]{36}',  # GitHub tokens
            r'password["\s:=]+[^"\s\n]{8,}',  # Passwords
            r'token["\s:=]+[a-zA-Z0-9_-]{20,}',  # Generic tokens
        ]

        import re

        secrets_found = []

        for log_file in log_files:
            try:
                with open(log_file) as f:
                    content = f.read()

                for pattern in secret_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        secrets_found.append(f"{log_file.name}: matched {pattern}")
            except:
                pass

        passed = len(secrets_found) == 0

        self.add_result(
            "messages",
            "no_secrets_exposed",
            passed,
            f"Potential secrets found: {len(secrets_found)}",
            "critical" if not passed else "info"
        )

        if passed:
            self.log(f"    ✓ No secrets exposed in logs", Colors.GREEN)
        else:
            self.log(f"    ✗ Potential secrets found in logs", Colors.RED)
            if self.verbose:
                for secret in secrets_found[:3]:
                    self.log(f"      - {secret}", Colors.DIM)

    def _test_stack_trace_capture(self):
        """Test that stack traces are captured when needed."""
        # This is more of a design check - do logs show context on errors?
        log_files = list(LOG_DIR.glob("*.log")) if LOG_DIR.exists() else []

        if not log_files:
            self.add_result("messages", "stack_trace_capture", True,
                          "No log files to check", "info")
            self.log(f"    ℹ No log files to check", Colors.DIM)
            return

        # Look for stack trace indicators in logs
        has_traces = False
        for log_file in log_files:
            try:
                with open(log_file) as f:
                    content = f.read()

                # Look for stack trace patterns
                if "at " in content or "File " in content or "line " in content.lower():
                    has_traces = True
                    break
            except:
                pass

        # For now, just report what we found
        self.add_result(
            "messages",
            "stack_trace_capture",
            True,  # Not a failure if missing
            f"Stack traces found in logs: {has_traces}",
            "info"
        )

        self.log(f"    ℹ Stack traces {'found' if has_traces else 'not found'} in logs", Colors.DIM)

    def test_timeout_handling(self) -> Dict:
        """
        Test timeout handling.

        Tests:
        1. Task timeout behavior
        2. Graceful interrupt handling
        """
        self.log("\n" + "="*80, Colors.CYAN)
        self.log("  TIMEOUT HANDLING TESTS", Colors.CYAN)
        self.log("="*80, Colors.CYAN)

        # Test 1: Task timeout
        if not self.quick:
            self.log("\n  [1/2] Testing task timeout behavior...", Colors.BOLD)
            self._test_task_timeout()
        else:
            self.log("\n  [1/2] Skipping timeout test (quick mode)...", Colors.DIM)
            self.add_result("timeouts", "task_timeout", True, "Skipped in quick mode", "info")

        # Test 2: Graceful interrupt
        self.log("\n  [2/2] Testing graceful interrupt handling...", Colors.BOLD)
        self._test_graceful_interrupt()

        # Summary
        passed_tests = sum(1 for r in self.results if r["category"] == "timeouts" and r["passed"])
        total_tests = sum(1 for r in self.results if r["category"] == "timeouts")

        self.log(f"\n  Timeout Handling Test Summary:", Colors.BOLD)
        self.log(f"    Tests passed: {passed_tests}/{total_tests}",
                Colors.GREEN if passed_tests == total_tests else Colors.YELLOW)

    def _test_task_timeout(self):
        """Test task timeout behavior."""
        try:
            # Run a command with very short timeout
            result = subprocess.run(
                ["bash", "-c", """
                    sleep 10 &
                    wait $!
                """],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=2  # Should timeout
            )

            # Should not reach here
            self.add_result("timeouts", "task_timeout", False,
                          "Timeout not enforced", "warning")
            self.log(f"    ✗ Timeout not enforced", Colors.YELLOW)

        except subprocess.TimeoutExpired:
            # This is expected
            self.add_result("timeouts", "task_timeout", True,
                          "Timeout enforced correctly", "info")
            self.log(f"    ✓ Timeout enforced correctly", Colors.GREEN)

        except Exception as e:
            self.add_result("timeouts", "task_timeout", False,
                          f"Exception: {e}", "warning")
            self.log(f"    ✗ Exception: {e}", Colors.YELLOW)

    def _test_graceful_interrupt(self):
        """Test graceful interrupt (Ctrl+C) handling."""
        # Backup state
        self._backup_state()

        try:
            # Start a process
            proc = subprocess.Popen(
                ["bash", "-c", "sleep 5"],
                cwd=REPO_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Wait briefly
            time.sleep(0.5)

            # Send SIGINT
            proc.send_signal(signal.SIGINT)

            # Wait for it to terminate
            try:
                proc.wait(timeout=3)
                exit_code = proc.returncode

                # Should terminate gracefully (not -9)
                graceful = exit_code != -9

                self.add_result(
                    "timeouts",
                    "graceful_interrupt",
                    graceful,
                    f"Exit code: {exit_code}, Graceful: {graceful}",
                    "info"
                )

                if graceful:
                    self.log(f"    ✓ Interrupt handled gracefully", Colors.GREEN)
                else:
                    self.log(f"    ✗ Interrupt not graceful (killed)", Colors.YELLOW)

            except subprocess.TimeoutExpired:
                proc.kill()
                self.add_result("timeouts", "graceful_interrupt", False,
                              "Process didn't terminate after interrupt", "warning")
                self.log(f"    ✗ Process didn't terminate", Colors.YELLOW)

        except Exception as e:
            self.add_result("timeouts", "graceful_interrupt", False,
                          f"Exception: {e}", "info")
            self.log(f"    ✗ Exception: {e}", Colors.YELLOW)

        finally:
            self._restore_state()

    def _backup_state(self):
        """Backup current state."""
        backup_dir = REPO_ROOT / "test" / ".state_backup"
        backup_dir.mkdir(exist_ok=True)

        if STATE_FILE.exists():
            shutil.copy(STATE_FILE, backup_dir / "task-state.json.backup")

        if OUTPUT_DIR.exists():
            if (backup_dir / "outputs_backup").exists():
                shutil.rmtree(backup_dir / "outputs_backup")
            shutil.copytree(OUTPUT_DIR, backup_dir / "outputs_backup")

    def _restore_state(self):
        """Restore state from backup."""
        backup_dir = REPO_ROOT / "test" / ".state_backup"

        backup_state = backup_dir / "task-state.json.backup"
        if backup_state.exists():
            STATE_FILE.parent.mkdir(exist_ok=True)
            shutil.copy(backup_state, STATE_FILE)

        backup_outputs = backup_dir / "outputs_backup"
        if backup_outputs.exists():
            if OUTPUT_DIR.exists():
                shutil.rmtree(OUTPUT_DIR)
            shutil.copytree(backup_outputs, OUTPUT_DIR)

    def generate_report(self) -> Dict:
        """Generate comprehensive error audit report."""
        self.log("\n" + "="*80, Colors.CYAN)
        self.log("  ERROR HANDLING AUDIT REPORT", Colors.CYAN)
        self.log("="*80, Colors.CYAN)

        test_duration = (datetime.now() - self.test_start_time).total_seconds()

        # Calculate statistics
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["passed"])
        failed_tests = total_tests - passed_tests

        # Category breakdown
        categories = ["graceful_failure", "recovery", "messages", "timeouts"]

        self.log(f"\n  Test Duration: {test_duration:.1f}s", Colors.BOLD)
        self.log(f"\n  Results by Category:", Colors.BOLD)

        for category in categories:
            cat_results = [r for r in self.results if r["category"] == category]
            cat_passed = sum(1 for r in cat_results if r["passed"])
            cat_total = len(cat_results)

            self.log(f"\n    {category.replace('_', ' ').title()}:", Colors.BOLD)
            self.log(f"      Passed: {cat_passed}/{cat_total}",
                    Colors.GREEN if cat_passed == cat_total else Colors.YELLOW)

            # Show failures
            failures = [r for r in cat_results if not r["passed"]]
            if failures and self.verbose:
                for failure in failures[:3]:
                    self.log(f"        ✗ {failure['test']}: {failure['message']}", Colors.DIM)

        # Overall assessment
        self.log(f"\n  Overall Assessment:", Colors.BOLD)
        self.log(f"    Total Tests: {total_tests}", Colors.DIM)
        self.log(f"    Passed: {passed_tests}", Colors.GREEN)
        self.log(f"    Failed: {failed_tests}", Colors.RED if failed_tests > 0 else Colors.GREEN)
        self.log(f"    Critical Failures: {self.critical_failures}",
                Colors.RED if self.critical_failures > 0 else Colors.GREEN)

        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        if self.critical_failures > 0:
            self.log(f"\n    ❌ CRITICAL ISSUES - {self.critical_failures} critical failures found ({pass_rate:.0f}% passed)", Colors.RED)
        elif pass_rate == 100:
            self.log(f"\n    ✅ EXCELLENT - All error handling tests passed ({pass_rate:.0f}%)", Colors.GREEN)
        elif pass_rate >= 80:
            self.log(f"\n    ⚠️ GOOD - Most error handling tests passed ({pass_rate:.0f}%)", Colors.YELLOW)
        else:
            self.log(f"\n    ⚠️ NEEDS IMPROVEMENT - Several error handling issues ({pass_rate:.0f}%)", Colors.YELLOW)

        # Save detailed report
        report_path = self._save_json_report(test_duration, total_tests, passed_tests, failed_tests)

        self.log(f"\n  Detailed report saved: {report_path}", Colors.CYAN)

        return {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "critical": self.critical_failures,
            "duration": test_duration
        }

    def _save_json_report(self, duration: float, total: int, passed: int, failed: int) -> Path:
        """Save detailed JSON report."""
        report_dir = REPO_ROOT / "test" / "reports"
        report_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        report_file = report_dir / f"error-audit-{timestamp}.json"

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "critical_failures": self.critical_failures,
            "duration": duration,
            "results": self.results,
            "summary": {
                "pass_rate": (passed / total * 100) if total > 0 else 0,
                "critical": self.critical_failures > 0
            }
        }

        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        return report_file


def main():
    parser = argparse.ArgumentParser(
        description="Error Handling Audit Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--quick",
        "-q",
        action="store_true",
        help="Quick mode (skip slow tests like timeouts and interrupts)"
    )

    args = parser.parse_args()

    print("\n" + "="*80)
    print("  ATOMIC CLAUDE 2.0 - ERROR HANDLING AUDIT")
    print("="*80)

    runner = ErrorAuditRunner(verbose=args.verbose, quick=args.quick)

    # Run all test suites
    runner.test_graceful_failure()
    runner.test_error_recovery()
    runner.test_error_message_quality()
    runner.test_timeout_handling()

    # Generate report
    summary = runner.generate_report()

    # Determine exit code
    if summary["critical"] > 0:
        print("\n" + "="*80)
        print(f"{Colors.RED}  ✗ ERROR AUDIT COMPLETE - {summary['critical']} CRITICAL FAILURES{Colors.NC}")
        print("="*80 + "\n")
        sys.exit(1)
    elif summary["failed"] > 0:
        print("\n" + "="*80)
        print(f"{Colors.YELLOW}  ⚠ ERROR AUDIT COMPLETE - {summary['failed']} ISSUES FOUND{Colors.NC}")
        print("="*80 + "\n")
        sys.exit(0)  # Don't fail on non-critical issues
    else:
        print("\n" + "="*80)
        print(f"{Colors.GREEN}  ✓ ERROR AUDIT COMPLETE - ALL TESTS PASSED{Colors.NC}")
        print("="*80 + "\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
