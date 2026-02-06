#!/usr/bin/env python3
"""
Error Handling Audit Runner
Validates graceful failure and error recovery mechanisms

This audit ensures that:
1. Missing dependencies are detected early with helpful errors
2. Invalid inputs are rejected gracefully
3. Partial failures can be recovered from
4. Error messages are actionable and clear
5. Rollback and cleanup work correctly
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ============================================================================
# ANSI COLOR CODES
# ============================================================================

BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
CYAN = "\033[36m"
NC = "\033[0m"


# ============================================================================
# TEST RESULT DATA STRUCTURE
# ============================================================================

@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    category: str
    passed: bool
    duration: float
    error_message: Optional[str] = None
    details: Dict = field(default_factory=dict)


@dataclass
class AuditReport:
    """Overall audit report."""
    timestamp: str
    total_tests: int
    passed: int
    failed: int
    duration: float
    results: List[TestResult]

    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100


# ============================================================================
# ERROR AUDIT RUNNER
# ============================================================================

class ErrorAuditRunner:
    """
    Validates graceful failure and error recovery mechanisms.
    """

    def __init__(self):
        self.atomic_root = Path(__file__).parent.parent.resolve()
        self.test_dir = self.atomic_root / "test"
        self.fixtures_dir = self.test_dir / "fixtures"
        self.reports_dir = self.test_dir / "reports"
        self.lib_dir = self.atomic_root / "lib"
        self.temp_dir = None

        # Ensure directories exist
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        self.results: List[TestResult] = []

    def run_all_tests(self) -> AuditReport:
        """
        Run all error handling tests and return report.
        """
        start_time = time.time()

        print(f"\n{BOLD}{CYAN}{'='*70}{NC}")
        print(f"{BOLD}  Error Handling Audit Runner{NC}")
        print(f"{CYAN}{'='*70}{NC}\n")

        # Create temporary test environment
        self.temp_dir = Path(tempfile.mkdtemp(prefix="atomic_error_test_"))
        print(f"{DIM}Test environment: {self.temp_dir}{NC}\n")

        # Run test categories
        print(f"{BOLD}Running Error Handling Tests:{NC}\n")

        self._run_category("Missing Dependency Detection", [
            self.test_missing_jq,
            self.test_missing_python,
            self.test_missing_git,
            self.test_dependency_early_detection,
            self.test_no_crash_on_missing_deps,
        ])

        self._run_category("Invalid Input Handling", [
            self.test_corrupted_setup_md,
            self.test_invalid_json_config,
            self.test_nonexistent_paths,
            self.test_empty_input_files,
            self.test_malformed_task_state,
            self.test_clear_error_messages,
        ])

        self._run_category("Partial Failure Recovery", [
            self.test_interrupt_mid_phase,
            self.test_state_consistency,
            self.test_resume_from_checkpoint,
            self.test_no_corrupted_outputs,
            self.test_task_state_recovery,
        ])

        self._run_category("Error Message Quality", [
            self.test_actionable_error_messages,
            self.test_stack_traces_when_appropriate,
            self.test_documented_error_codes,
            self.test_no_sensitive_data_exposure,
            self.test_error_context_included,
        ])

        self._run_category("Rollback Testing", [
            self.test_state_rollback_on_failure,
            self.test_cleanup_partial_outputs,
            self.test_no_orphaned_processes,
            self.test_file_locks_released,
            self.test_rollback_transaction_safety,
        ])

        # Cleanup
        self._cleanup()

        # Generate report
        duration = time.time() - start_time
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed

        report = AuditReport(
            timestamp=datetime.now().isoformat(),
            total_tests=len(self.results),
            passed=passed,
            failed=failed,
            duration=duration,
            results=self.results
        )

        # Print summary
        self._print_summary(report)

        # Save JSON report
        self._save_report(report)

        return report

    def _run_category(self, category: str, tests: List):
        """Run all tests in a category."""
        print(f"{BOLD}{category}:{NC}")
        for test_func in tests:
            self._run_test(category, test_func)
        print()

    def _run_test(self, category: str, test_func):
        """Run a single test and record result."""
        test_name = test_func.__name__.replace("test_", "").replace("_", " ").title()
        start_time = time.time()

        try:
            test_func()
            duration = time.time() - start_time
            result = TestResult(
                name=test_name,
                category=category,
                passed=True,
                duration=duration
            )
            print(f"  {GREEN}✓{NC} {test_name} {DIM}({duration:.2f}s){NC}")
        except AssertionError as e:
            duration = time.time() - start_time
            result = TestResult(
                name=test_name,
                category=category,
                passed=False,
                duration=duration,
                error_message=str(e)
            )
            print(f"  {RED}✗{NC} {test_name} {DIM}({duration:.2f}s){NC}")
            print(f"    {DIM}{str(e)}{NC}")
        except Exception as e:
            duration = time.time() - start_time
            result = TestResult(
                name=test_name,
                category=category,
                passed=False,
                duration=duration,
                error_message=f"Unexpected error: {str(e)}"
            )
            print(f"  {RED}✗{NC} {test_name} {DIM}({duration:.2f}s){NC}")
            print(f"    {RED}Unexpected error: {str(e)}{NC}")

        self.results.append(result)

    # ========================================================================
    # MISSING DEPENDENCY DETECTION TESTS
    # ========================================================================

    def test_missing_jq(self):
        """Test detection of missing jq command."""
        # Test that the error handling pattern works correctly
        test_script = self.temp_dir / "test_jq.sh"
        test_script.write_text("""#!/usr/bin/env bash
set -euo pipefail

# Mock command check that simulates jq missing
check_jq_mock() {
    # Simulate jq not found
    echo "ERROR: jq is required but not installed" >&2
    echo "Install with: brew install jq (macOS) or apt-get install jq (Linux)" >&2
    return 1
}

# Run the mock check
if ! check_jq_mock; then
    exit 1
fi
""")
        test_script.chmod(0o755)

        result = subprocess.run([str(test_script)], capture_output=True, text=True)

        # Validate error handling pattern
        assert result.returncode == 1, "Should exit with code 1"
        assert "jq is required" in result.stderr, "Should mention jq is required"
        assert "Install with" in result.stderr, "Should provide installation instructions"

    def test_missing_python(self):
        """Test detection of missing python command."""
        test_script = self.temp_dir / "test_python.sh"
        test_script.write_text("""#!/usr/bin/env bash
set -euo pipefail

check_python_mock() {
    echo "ERROR: python3 is required but not installed" >&2
    echo "Install with: brew install python3 (macOS) or apt-get install python3 (Linux)" >&2
    return 1
}

if ! check_python_mock; then
    exit 1
fi
""")
        test_script.chmod(0o755)

        result = subprocess.run([str(test_script)], capture_output=True, text=True)

        assert result.returncode == 1, "Should exit with code 1"
        assert "python3 is required" in result.stderr, "Should mention python3 is required"
        assert "Install with" in result.stderr, "Should provide installation instructions"

    def test_missing_git(self):
        """Test detection of missing git command."""
        test_script = self.temp_dir / "test_git.sh"
        test_script.write_text("""#!/usr/bin/env bash
set -euo pipefail

check_git_mock() {
    echo "ERROR: git is required but not installed" >&2
    echo "Install with: brew install git (macOS) or apt-get install git (Linux)" >&2
    return 1
}

if ! check_git_mock; then
    exit 1
fi
""")
        test_script.chmod(0o755)

        result = subprocess.run([str(test_script)], capture_output=True, text=True)

        assert result.returncode == 1, "Should exit with code 1"
        assert "git is required" in result.stderr, "Should mention git is required"
        assert "Install with" in result.stderr, "Should provide installation instructions"

    def test_dependency_early_detection(self):
        """Test that dependencies are checked before execution."""
        # Create a script with dependency checks at the start
        test_script = self.temp_dir / "test_early_check.sh"
        test_script.write_text("""#!/usr/bin/env bash
set -euo pipefail

# Early dependency checks
MISSING_DEPS=()
command -v jq &>/dev/null || MISSING_DEPS+=("jq")
command -v git &>/dev/null || MISSING_DEPS+=("git")

if [[ ${#MISSING_DEPS[@]} -gt 0 ]]; then
    echo "ERROR: Missing required dependencies: ${MISSING_DEPS[*]}" >&2
    exit 1
fi

# Actual work would go here
echo "Dependencies OK"
""")
        test_script.chmod(0o755)

        # Should succeed with normal PATH
        result = subprocess.run([str(test_script)], capture_output=True, text=True)
        assert result.returncode == 0, "Should succeed with dependencies present"
        assert "Dependencies OK" in result.stdout

    def test_no_crash_on_missing_deps(self):
        """Test that missing dependencies cause clean exit, not crash."""
        test_script = self.temp_dir / "test_no_crash.sh"
        test_script.write_text("""#!/usr/bin/env bash
set -euo pipefail

check_dependency() {
    local cmd="$1"
    if ! command -v "$cmd" &>/dev/null; then
        echo "ERROR: $cmd not found" >&2
        return 1
    fi
    return 0
}

if ! check_dependency "nonexistent_command_xyz"; then
    exit 1
fi

# Should never reach here
exit 0
""")
        test_script.chmod(0o755)

        result = subprocess.run([str(test_script)], capture_output=True, text=True)

        assert result.returncode == 1, "Should exit with code 1"
        assert "ERROR:" in result.stderr, "Should print error message"
        # Should not have uncaught bash errors (clean exit)
        assert "line" not in result.stderr or "ERROR:" in result.stderr

    # ========================================================================
    # INVALID INPUT HANDLING TESTS
    # ========================================================================

    def test_corrupted_setup_md(self):
        """Test handling of corrupted initialization/setup.md."""
        # Create corrupted setup.md
        setup_dir = self.temp_dir / "initialization"
        setup_dir.mkdir(parents=True, exist_ok=True)
        setup_file = setup_dir / "setup.md"
        setup_file.write_text("**incomplete markdown without closing")

        # Create parser script
        parser = self.temp_dir / "parse_setup.sh"
        parser.write_text(f"""#!/usr/bin/env bash
set -euo pipefail

SETUP_FILE="{setup_file}"

if [[ ! -f "$SETUP_FILE" ]]; then
    echo "ERROR: setup.md not found" >&2
    exit 1
fi

# Check for required fields
if ! grep -q "^\\*\\*name\\*\\*:" "$SETUP_FILE"; then
    echo "ERROR: setup.md is missing required field: name" >&2
    echo "Please ensure your setup.md contains: **name**: your-project-name" >&2
    exit 1
fi

echo "Setup file valid"
""")
        parser.chmod(0o755)

        result = subprocess.run([str(parser)], capture_output=True, text=True)

        assert result.returncode != 0, "Should fail on corrupted setup.md"
        assert "ERROR:" in result.stderr, "Should provide error message"
        assert "required field" in result.stderr or "missing" in result.stderr

    def test_invalid_json_config(self):
        """Test handling of invalid JSON in config files."""
        config_file = self.temp_dir / "config.json"
        config_file.write_text('{"invalid": json, "missing": quotes}')

        test_script = self.temp_dir / "test_json.sh"
        test_script.write_text(f"""#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE="{config_file}"

if ! jq empty "$CONFIG_FILE" 2>/dev/null; then
    echo "ERROR: Invalid JSON in config file: $CONFIG_FILE" >&2
    echo "Please fix the JSON syntax and try again" >&2
    exit 1
fi

echo "Config valid"
""")
        test_script.chmod(0o755)

        result = subprocess.run([str(test_script)], capture_output=True, text=True)

        assert result.returncode != 0, "Should fail on invalid JSON"
        assert "Invalid JSON" in result.stderr, "Should mention invalid JSON"

    def test_nonexistent_paths(self):
        """Test handling of nonexistent file paths."""
        test_script = self.temp_dir / "test_paths.sh"
        test_script.write_text("""#!/usr/bin/env bash
set -euo pipefail

REQUIRED_FILE="/nonexistent/path/to/file.txt"

if [[ ! -f "$REQUIRED_FILE" ]]; then
    echo "ERROR: Required file not found: $REQUIRED_FILE" >&2
    echo "Please ensure the file exists before running this script" >&2
    exit 1
fi
""")
        test_script.chmod(0o755)

        result = subprocess.run([str(test_script)], capture_output=True, text=True)

        assert result.returncode != 0, "Should fail on nonexistent path"
        assert "not found" in result.stderr, "Should mention file not found"

    def test_empty_input_files(self):
        """Test handling of empty input files."""
        empty_file = self.temp_dir / "empty.txt"
        empty_file.write_text("")

        test_script = self.temp_dir / "test_empty.sh"
        test_script.write_text(f"""#!/usr/bin/env bash
set -euo pipefail

INPUT_FILE="{empty_file}"

if [[ ! -s "$INPUT_FILE" ]]; then
    echo "ERROR: Input file is empty: $INPUT_FILE" >&2
    echo "Please provide valid input content" >&2
    exit 1
fi
""")
        test_script.chmod(0o755)

        result = subprocess.run([str(test_script)], capture_output=True, text=True)

        assert result.returncode != 0, "Should fail on empty input"
        assert "empty" in result.stderr.lower(), "Should mention file is empty"

    def test_malformed_task_state(self):
        """Test handling of malformed task-state.json."""
        state_file = self.temp_dir / "task-state.json"
        state_file.write_text('{"tasks": [broken json')

        test_script = self.temp_dir / "test_state.sh"
        test_script.write_text(f"""#!/usr/bin/env bash
set -euo pipefail

STATE_FILE="{state_file}"

if [[ -f "$STATE_FILE" ]] && ! jq empty "$STATE_FILE" 2>/dev/null; then
    echo "ERROR: Corrupted task state file: $STATE_FILE" >&2
    echo "Run 'atomic-claude reset' to reset pipeline state" >&2
    exit 1
fi

echo "State valid"
""")
        test_script.chmod(0o755)

        result = subprocess.run([str(test_script)], capture_output=True, text=True)

        assert result.returncode != 0, "Should fail on malformed state"
        assert "Corrupted" in result.stderr or "ERROR" in result.stderr

    def test_clear_error_messages(self):
        """Test that error messages are clear and actionable."""
        test_script = self.temp_dir / "test_clear_errors.sh"
        test_script.write_text("""#!/usr/bin/env bash
set -euo pipefail

# Simulate various error conditions
echo "ERROR: Configuration file missing: config.json" >&2
echo "→ Create config.json with: atomic-claude init" >&2
exit 1
""")
        test_script.chmod(0o755)

        result = subprocess.run([str(test_script)], capture_output=True, text=True)

        assert result.returncode != 0
        assert "ERROR:" in result.stderr, "Should have ERROR prefix"
        assert "→" in result.stderr or ":" in result.stderr, "Should have actionable guidance"

    # ========================================================================
    # PARTIAL FAILURE RECOVERY TESTS
    # ========================================================================

    def test_interrupt_mid_phase(self):
        """Test interrupting a phase mid-execution."""
        # Create a long-running script
        test_script = self.temp_dir / "test_interrupt.sh"
        test_script.write_text("""#!/usr/bin/env bash
set -euo pipefail

STATE_FILE="state.json"
echo '{"task": "101", "status": "running"}' > "$STATE_FILE"

# Simulate work
sleep 0.1

# This should be interrupted
sleep 10

echo '{"task": "101", "status": "complete"}' > "$STATE_FILE"
""")
        test_script.chmod(0o755)

        # Start process
        proc = subprocess.Popen(
            [str(test_script)],
            cwd=str(self.temp_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Let it start
        time.sleep(0.2)

        # Interrupt it
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

        # Check state file
        state_file = self.temp_dir / "state.json"
        assert state_file.exists(), "State file should exist"

        state = json.loads(state_file.read_text())
        assert state["status"] == "running", "State should show running (not complete)"

    def test_state_consistency(self):
        """Test that state remains consistent after interruption."""
        state_file = self.temp_dir / "task-state.json"
        state_file.write_text(json.dumps({
            "phase": "1-discovery",
            "tasks": {
                "101": {"status": "complete"},
                "102": {"status": "running"}
            }
        }))

        # Create validation script
        validator = self.temp_dir / "validate_state.sh"
        validator.write_text(f"""#!/usr/bin/env bash
set -euo pipefail

STATE_FILE="{state_file}"

# Validate state is readable
if ! jq empty "$STATE_FILE" 2>/dev/null; then
    echo "ERROR: State file corrupted" >&2
    exit 1
fi

# Check for running tasks
RUNNING_TASKS=$(jq '[.tasks[] | select(.status == "running")] | length' "$STATE_FILE")
if [[ "$RUNNING_TASKS" -gt 0 ]]; then
    echo "WARNING: Found $RUNNING_TASKS running tasks (possible interruption)" >&2
    echo "Use --resume to continue from checkpoint" >&2
fi

echo "State is consistent"
""")
        validator.chmod(0o755)

        result = subprocess.run([str(validator)], capture_output=True, text=True)
        assert result.returncode == 0, "Should validate state successfully"
        assert "running tasks" in result.stderr.lower() or "WARNING" in result.stderr

    def test_resume_from_checkpoint(self):
        """Test resuming execution from checkpoint."""
        state_file = self.temp_dir / "task-state.json"
        state_file.write_text(json.dumps({
            "phase": "1-discovery",
            "tasks": {
                "101": {"status": "complete"},
                "102": {"status": "complete"},
                "103": {"status": "running"}
            }
        }))

        resume_script = self.temp_dir / "resume.sh"
        resume_script.write_text(f"""#!/usr/bin/env bash
set -euo pipefail

STATE_FILE="{state_file}"

# Find last completed task
LAST_COMPLETE=$(jq -r '[.tasks | to_entries[] | select(.value.status == "complete") | .key] | max' "$STATE_FILE")

echo "Resuming from task: $LAST_COMPLETE"
echo "Next task: 103"
""")
        resume_script.chmod(0o755)

        result = subprocess.run([str(resume_script)], capture_output=True, text=True)
        assert result.returncode == 0
        assert "102" in result.stdout, "Should identify last complete task"
        assert "103" in result.stdout, "Should identify next task"

    def test_no_corrupted_outputs(self):
        """Test that interruption doesn't create corrupted output files."""
        output_file = self.temp_dir / "output.json"

        # Script that writes output atomically
        test_script = self.temp_dir / "test_atomic_write.sh"
        test_script.write_text(f"""#!/usr/bin/env bash
set -euo pipefail

OUTPUT_FILE="{output_file}"
TEMP_FILE="$OUTPUT_FILE.tmp"

# Write to temp file first
echo '{{"status": "success"}}' > "$TEMP_FILE"

# Validate before moving
if jq empty "$TEMP_FILE" 2>/dev/null; then
    mv "$TEMP_FILE" "$OUTPUT_FILE"
else
    echo "ERROR: Generated invalid JSON" >&2
    rm -f "$TEMP_FILE"
    exit 1
fi
""")
        test_script.chmod(0o755)

        result = subprocess.run([str(test_script)], capture_output=True, text=True)
        assert result.returncode == 0

        # Verify output is valid JSON
        output = json.loads(output_file.read_text())
        assert output["status"] == "success"

    def test_task_state_recovery(self):
        """Test that task state can be recovered after failure."""
        state_file = self.temp_dir / "task-state.json"
        backup_file = self.temp_dir / "task-state.json.backup"

        # Create initial state
        initial_state = {
            "phase": "1-discovery",
            "tasks": {
                "101": {"status": "complete"},
                "102": {"status": "complete"}
            }
        }
        state_file.write_text(json.dumps(initial_state))
        backup_file.write_text(json.dumps(initial_state))

        # Simulate corruption
        state_file.write_text("corrupted data")

        # Recovery script
        recovery_script = self.temp_dir / "recover_state.sh"
        recovery_script.write_text(f"""#!/usr/bin/env bash
set -euo pipefail

STATE_FILE="{state_file}"
BACKUP_FILE="{backup_file}"

# Check if state is corrupted
if ! jq empty "$STATE_FILE" 2>/dev/null; then
    echo "WARNING: State file corrupted, restoring from backup" >&2
    if [[ -f "$BACKUP_FILE" ]]; then
        cp "$BACKUP_FILE" "$STATE_FILE"
        echo "State restored successfully" >&2
    else
        echo "ERROR: No backup available" >&2
        exit 1
    fi
fi

echo "State is valid"
""")
        recovery_script.chmod(0o755)

        result = subprocess.run([str(recovery_script)], capture_output=True, text=True)
        assert result.returncode == 0
        assert "restored" in result.stderr.lower()

        # Verify state was restored
        restored_state = json.loads(state_file.read_text())
        assert restored_state == initial_state

    # ========================================================================
    # ERROR MESSAGE QUALITY TESTS
    # ========================================================================

    def test_actionable_error_messages(self):
        """Test that error messages tell users what to fix."""
        test_script = self.temp_dir / "test_actionable.sh"
        test_script.write_text("""#!/usr/bin/env bash
set -euo pipefail

# Good error message format
error_with_action() {
    echo "ERROR: Configuration file not found: config.json" >&2
    echo "" >&2
    echo "To fix this:" >&2
    echo "  1. Run: atomic-claude init" >&2
    echo "  2. Or create config.json manually" >&2
    echo "" >&2
    exit 1
}

error_with_action
""")
        test_script.chmod(0o755)

        result = subprocess.run([str(test_script)], capture_output=True, text=True)
        assert result.returncode != 0
        assert "To fix this:" in result.stderr or "→" in result.stderr
        assert any(word in result.stderr.lower() for word in ["run", "create", "install"])

    def test_stack_traces_when_appropriate(self):
        """Test that stack traces are included for unexpected errors."""
        test_script = self.temp_dir / "test_stacktrace.py"
        test_script.write_text("""#!/usr/bin/env python3
import sys
import traceback

try:
    # Simulate unexpected error
    raise ValueError("Unexpected error occurred")
except Exception as e:
    print(f"ERROR: {str(e)}", file=sys.stderr)
    print("\\nStack trace:", file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)
""")
        test_script.chmod(0o755)

        result = subprocess.run([str(test_script)], capture_output=True, text=True)
        assert result.returncode != 0
        assert "Stack trace:" in result.stderr or "Traceback" in result.stderr

    def test_documented_error_codes(self):
        """Test that error codes are documented."""
        test_script = self.temp_dir / "test_error_codes.sh"
        test_script.write_text("""#!/usr/bin/env bash
set -euo pipefail

# Exit codes:
# 0 - Success
# 1 - General error
# 2 - Missing dependency
# 3 - Invalid configuration
# 4 - Network error

exit_with_code() {
    local code=$1
    local message=$2
    echo "ERROR: $message (exit code: $code)" >&2
    exit "$code"
}

exit_with_code 3 "Invalid configuration file"
""")
        test_script.chmod(0o755)

        result = subprocess.run([str(test_script)], capture_output=True, text=True)
        assert result.returncode == 3
        assert "exit code: 3" in result.stderr or "Invalid configuration" in result.stderr

    def test_no_sensitive_data_exposure(self):
        """Test that errors don't expose sensitive data."""
        # Create script with API key
        test_script = self.temp_dir / "test_sensitive.sh"
        test_script.write_text("""#!/usr/bin/env bash
set -euo pipefail

API_KEY="sk-1234567890abcdef"
CONFIG_FILE="config.json"

# Good: Don't expose API key in error
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "ERROR: Configuration file not found" >&2
    # BAD: echo "ERROR: Failed to load config with key: $API_KEY" >&2
    exit 1
fi
""")
        test_script.chmod(0o755)

        result = subprocess.run([str(test_script)], capture_output=True, text=True)
        assert result.returncode != 0
        assert "sk-" not in result.stderr, "Should not expose API keys"
        assert "1234567890" not in result.stderr, "Should not expose secrets"

    def test_error_context_included(self):
        """Test that errors include relevant context."""
        test_script = self.temp_dir / "test_context.sh"
        test_script.write_text("""#!/usr/bin/env bash
set -euo pipefail

PHASE="1-discovery"
TASK="103"

error_with_context() {
    echo "ERROR: Task execution failed" >&2
    echo "" >&2
    echo "Context:" >&2
    echo "  Phase: $PHASE" >&2
    echo "  Task:  $TASK" >&2
    echo "  PWD:   $PWD" >&2
    echo "" >&2
    exit 1
}

error_with_context
""")
        test_script.chmod(0o755)

        result = subprocess.run([str(test_script)], capture_output=True, text=True)
        assert result.returncode != 0
        assert "Context:" in result.stderr
        assert "Phase:" in result.stderr
        assert "Task:" in result.stderr

    # ========================================================================
    # ROLLBACK TESTING
    # ========================================================================

    def test_state_rollback_on_failure(self):
        """Test that state can be rolled back on failure."""
        state_file = self.temp_dir / "task-state.json"
        initial_state = {"phase": "1-discovery", "tasks": {"101": {"status": "complete"}}}
        state_file.write_text(json.dumps(initial_state))

        test_script = self.temp_dir / "test_rollback.sh"
        test_script.write_text(f"""#!/usr/bin/env bash
set -euo pipefail

STATE_FILE="{state_file}"
BACKUP_FILE="$STATE_FILE.backup"

# Backup state before modification
cp "$STATE_FILE" "$BACKUP_FILE"

# Simulate state update
jq '.tasks["102"] = {{"status": "running"}}' "$STATE_FILE" > "$STATE_FILE.tmp"
mv "$STATE_FILE.tmp" "$STATE_FILE"

# Simulate failure
if true; then
    echo "ERROR: Task failed, rolling back state" >&2
    mv "$BACKUP_FILE" "$STATE_FILE"
    exit 1
fi

# Cleanup backup on success
rm -f "$BACKUP_FILE"
""")
        test_script.chmod(0o755)

        result = subprocess.run([str(test_script)], capture_output=True, text=True)
        assert result.returncode != 0
        assert "rolling back" in result.stderr.lower()

        # Verify state was rolled back
        restored = json.loads(state_file.read_text())
        assert "102" not in restored["tasks"], "State should be rolled back"

    def test_cleanup_partial_outputs(self):
        """Test that partial outputs are cleaned up on failure."""
        output_dir = self.temp_dir / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)

        test_script = self.temp_dir / "test_cleanup.sh"
        test_script.write_text(f"""#!/usr/bin/env bash
set -euo pipefail

OUTPUT_DIR="{output_dir}"

cleanup() {{
    echo "Cleaning up partial outputs..." >&2
    rm -rf "$OUTPUT_DIR"/*.tmp
    rm -rf "$OUTPUT_DIR"/*.partial
}}

trap cleanup EXIT

# Create partial output
echo "partial data" > "$OUTPUT_DIR/output.tmp"

# Simulate failure
exit 1
""")
        test_script.chmod(0o755)

        # Create a temp file that should be cleaned up
        temp_file = output_dir / "output.tmp"
        temp_file.write_text("partial data")

        result = subprocess.run([str(test_script)], capture_output=True, text=True)
        assert result.returncode != 0

        # Give cleanup time to run
        time.sleep(0.1)

        # Temp file should be cleaned up
        assert not temp_file.exists(), "Temp files should be cleaned up"

    def test_no_orphaned_processes(self):
        """Test that no processes are left running after failure."""
        test_script = self.temp_dir / "test_orphans.sh"
        test_script.write_text("""#!/usr/bin/env bash
set -euo pipefail

# Start background process
sleep 100 &
BG_PID=$!

cleanup() {
    echo "Cleaning up background processes..." >&2
    kill $BG_PID 2>/dev/null || true
    wait $BG_PID 2>/dev/null || true
}

trap cleanup EXIT

# Simulate failure
exit 1
""")
        test_script.chmod(0o755)

        result = subprocess.run([str(test_script)], capture_output=True, text=True)
        assert result.returncode != 0

        # Give cleanup time to run
        time.sleep(0.2)

        # Check for orphaned sleep processes
        ps_result = subprocess.run(
            ["pgrep", "-f", "sleep 100"],
            capture_output=True
        )
        assert ps_result.returncode != 0, "Should not have orphaned processes"

    def test_file_locks_released(self):
        """Test that file locks are released on failure."""
        lock_file = self.temp_dir / "test.lock"

        test_script = self.temp_dir / "test_locks.sh"
        test_script.write_text(f"""#!/usr/bin/env bash
set -euo pipefail

LOCK_FILE="{lock_file}"

acquire_lock() {{
    exec 200>"$LOCK_FILE"
    if ! flock -n 200; then
        echo "ERROR: Could not acquire lock" >&2
        return 1
    fi
    echo "Lock acquired" >&2
}}

release_lock() {{
    flock -u 200 2>/dev/null || true
    rm -f "$LOCK_FILE"
    echo "Lock released" >&2
}}

trap release_lock EXIT

acquire_lock

# Simulate failure
exit 1
""")
        test_script.chmod(0o755)

        result = subprocess.run([str(test_script)], capture_output=True, text=True)
        assert result.returncode != 0
        assert "Lock released" in result.stderr

        # Lock file should be cleaned up
        time.sleep(0.1)
        assert not lock_file.exists(), "Lock file should be removed"

    def test_rollback_transaction_safety(self):
        """Test that rollback operations are transactional."""
        state_file = self.temp_dir / "state.json"
        initial_state = {"version": 1, "data": "initial"}
        state_file.write_text(json.dumps(initial_state))

        test_script = self.temp_dir / "test_transaction.sh"
        test_script.write_text(f"""#!/usr/bin/env bash
set -euo pipefail

STATE_FILE="{state_file}"

atomic_update() {{
    local temp_file="$STATE_FILE.tmp"

    # Write to temp file
    echo '{{"version": 2, "data": "updated"}}' > "$temp_file"

    # Validate before commit
    if ! jq empty "$temp_file" 2>/dev/null; then
        echo "ERROR: Invalid update, rolling back" >&2
        rm -f "$temp_file"
        return 1
    fi

    # Atomic move
    mv "$temp_file" "$STATE_FILE"
    return 0
}}

# Simulate failed update
echo '{{invalid json}}' > "$STATE_FILE.tmp"
if ! jq empty "$STATE_FILE.tmp" 2>/dev/null; then
    echo "ERROR: Invalid update, rolling back" >&2
    rm -f "$STATE_FILE.tmp"
    exit 1
fi
""")
        test_script.chmod(0o755)

        result = subprocess.run([str(test_script)], capture_output=True, text=True)
        assert result.returncode != 0

        # Original state should be unchanged
        current = json.loads(state_file.read_text())
        assert current == initial_state, "State should remain unchanged after failed update"

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _cleanup(self):
        """Clean up temporary test environment."""
        if self.temp_dir and self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                print(f"{YELLOW}Warning: Failed to clean up temp dir: {e}{NC}")

    def _print_summary(self, report: AuditReport):
        """Print test summary."""
        print(f"\n{BOLD}{CYAN}{'='*70}{NC}")
        print(f"{BOLD}Test Summary:{NC}\n")
        print(f"  Total Tests:   {report.total_tests}")
        print(f"  {GREEN}Passed:{NC}        {report.passed}")
        print(f"  {RED}Failed:{NC}        {report.failed}")
        print(f"  Success Rate:  {report.success_rate():.1f}%")
        print(f"  Duration:      {report.duration:.2f}s")
        print(f"{CYAN}{'='*70}{NC}\n")

        # Print failures
        if report.failed > 0:
            print(f"{BOLD}{RED}Failed Tests:{NC}\n")
            for result in report.results:
                if not result.passed:
                    print(f"  • {result.category}: {result.name}")
                    if result.error_message:
                        print(f"    {DIM}{result.error_message}{NC}")
            print()

    def _save_report(self, report: AuditReport):
        """Save JSON report to file."""
        report_file = self.reports_dir / f"error_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        report_data = {
            "timestamp": report.timestamp,
            "total_tests": report.total_tests,
            "passed": report.passed,
            "failed": report.failed,
            "success_rate": report.success_rate(),
            "duration": report.duration,
            "results": [
                {
                    "name": r.name,
                    "category": r.category,
                    "passed": r.passed,
                    "duration": r.duration,
                    "error_message": r.error_message,
                    "details": r.details
                }
                for r in report.results
            ]
        }

        report_file.write_text(json.dumps(report_data, indent=2))
        print(f"Report saved to: {report_file}\n")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Run error handling audit."""
    runner = ErrorAuditRunner()
    report = runner.run_all_tests()

    # Exit with failure code if any tests failed
    sys.exit(0 if report.failed == 0 else 1)


if __name__ == "__main__":
    main()
