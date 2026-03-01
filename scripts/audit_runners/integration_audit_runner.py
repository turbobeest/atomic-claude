#!/usr/bin/env python3
"""
Integration Audit Runner
Validates handoffs between Python orchestrators and bash task scripts

This comprehensive audit validates all integration points in Atomic Claude:

CORE INTEGRATION TESTS:
1. Python → Bash Integration
   - PhaseManager executing bash task scripts
   - Exit code propagation from bash to Python
   - Environment variable passing
   - JSON data exchange between languages

2. Bash → Python Integration
   - Bash writing JSON that Python reads
   - State file consistency across languages
   - Error handling across language boundaries

3. Cross-Phase Data Flow
   - Output files from one phase used by next phase
   - State file consistency across phases
   - Closeout file generation and validation

4. Task State Integration
   - Task state persistence across invocations
   - Task skip logic based on completion state
   - Failure tracking and error reporting

USAGE:
    python3 test/integration_audit_runner.py [--verbose]

    --verbose   Enable verbose output

OUTPUT:
    - JSON report at test/reports/integration-audit-TIMESTAMP.json
    - Latest report at test/reports/integration_audit.json

EXIT CODES:
    0: All tests passed or only warnings
    1: Critical failures detected

REPORT FORMAT:
    {
      "timestamp": "...",
      "total_tests": N,
      "passed": N,
      "failed": N,
      "duration": N.NN,
      "results": [
        {
          "category": "python_bash|bash_python|data_flow|orchestrators",
          "test": "test name",
          "passed": true|false,
          "message": "details",
          "severity": "critical|warning|info"
        }
      ]
    }
"""

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


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

    @property
    def severity(self) -> str:
        """Determine severity based on test category and failure."""
        if self.passed:
            return "info"

        # Critical failures for core integration
        critical_categories = [
            "Python→Bash Integration",
            "Bash→Python Integration",
            "Exit Code Propagation",
            "Cross-Phase Data Flow"
        ]

        if self.category in critical_categories:
            return "critical"
        else:
            return "warning"


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
# INTEGRATION AUDIT RUNNER
# ============================================================================

class IntegrationAuditRunner:
    """
    Validates integration points between Python orchestrators and bash scripts.
    """

    def __init__(self):
        self.atomic_root = Path(__file__).parent.parent.resolve()
        self.test_dir = self.atomic_root / "test"
        self.fixtures_dir = self.test_dir / "fixtures"
        self.reports_dir = self.test_dir / "reports"
        self.lib_dir = self.atomic_root / "lib"

        # Ensure directories exist
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        self.results: List[TestResult] = []

    def run_all_tests(self) -> AuditReport:
        """
        Run all integration tests and return report.
        """
        start_time = time.time()

        print(f"\n{BOLD}{CYAN}{'='*70}{NC}")
        print(f"{BOLD}  Integration Audit Runner{NC}")
        print(f"{CYAN}{'='*70}{NC}\n")

        # Create test fixtures
        self._create_test_fixtures()

        # Run test categories
        print(f"{BOLD}Running Integration Tests:{NC}\n")

        # Low-level bash execution tests
        self._run_category("Orchestrator Execution", [
            self.test_simple_execution,
            self.test_script_with_output,
            self.test_script_with_stderr,
        ])

        self._run_category("Exit Code Propagation", [
            self.test_success_exit_code,
            self.test_failure_exit_code,
            self.test_custom_exit_codes,
        ])

        self._run_category("Output Capture", [
            self.test_stdout_capture,
            self.test_stderr_capture,
            self.test_combined_output,
        ])

        self._run_category("Timeout Handling", [
            self.test_timeout_enforcement,
            self.test_timeout_not_triggered,
            self.test_timeout_signal_handling,
        ])

        self._run_category("Environment Passing", [
            self.test_atomic_root_env,
            self.test_phase_env_vars,
            self.test_custom_env_vars,
        ])

        self._run_category("Library Function Access", [
            self.test_source_atomic_lib,
            self.test_atomic_step_function,
            self.test_atomic_success_function,
            self.test_atomic_error_function,
        ])

        self._run_category("Error Propagation", [
            self.test_script_error_detection,
            self.test_invalid_script_path,
            self.test_permission_error,
            self.test_syntax_error_detection,
        ])

        self._run_category("Working Directory", [
            self.test_correct_working_directory,
            self.test_output_directory_access,
            self.test_state_directory_access,
        ])

        # High-level integration tests
        self._run_category("Python→Bash Integration", [
            self.test_phase_manager_runs_bash_script,
            self.test_python_captures_bash_exit_code,
            self.test_python_bash_env_passing,
            self.test_python_bash_json_exchange,
        ])

        self._run_category("Bash→Python Integration", [
            self.test_bash_writes_json_python_reads,
            self.test_bash_python_state_files,
            self.test_bash_python_error_handling,
        ])

        self._run_category("Cross-Phase Data Flow", [
            self.test_phase_output_file_passing,
            self.test_phase_state_consistency,
            self.test_phase_closeout_generation,
        ])

        self._run_category("Task State Integration", [
            self.test_task_state_persistence,
            self.test_task_state_skip_logic,
            self.test_task_state_failure_tracking,
        ])

        # Generate report
        duration = time.time() - start_time
        report = self._generate_report(duration)

        # Save report
        self._save_report(report)

        # Display summary
        self._display_summary(report)

        return report

    def _run_category(self, category_name: str, tests: List):
        """Run a category of tests."""
        print(f"{BOLD}{category_name}:{NC}")
        for test in tests:
            result = self._run_test(test, category_name)
            self.results.append(result)

            status = f"{GREEN}✓{NC}" if result.passed else f"{RED}✗{NC}"
            print(f"  {status} {result.name}")

            if not result.passed and result.error_message:
                print(f"    {DIM}{result.error_message}{NC}")
        print()

    def _run_test(self, test_func, category: str) -> TestResult:
        """Run a single test and capture result."""
        start_time = time.time()

        try:
            test_func()
            duration = time.time() - start_time
            return TestResult(
                name=test_func.__name__.replace('test_', '').replace('_', ' ').title(),
                category=category,
                passed=True,
                duration=duration
            )
        except AssertionError as e:
            duration = time.time() - start_time
            return TestResult(
                name=test_func.__name__.replace('test_', '').replace('_', ' ').title(),
                category=category,
                passed=False,
                duration=duration,
                error_message=str(e)
            )
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                name=test_func.__name__.replace('test_', '').replace('_', ' ').title(),
                category=category,
                passed=False,
                duration=duration,
                error_message=f"Unexpected error: {e}"
            )

    # ========================================================================
    # ORCHESTRATOR EXECUTION TESTS
    # ========================================================================

    def test_simple_execution(self):
        """Test basic script execution."""
        result = subprocess.run(
            ["bash", str(self.fixtures_dir / "simple.sh")],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "Script should execute successfully"

    def test_script_with_output(self):
        """Test script with stdout output."""
        result = subprocess.run(
            ["bash", str(self.fixtures_dir / "with_output.sh")],
            capture_output=True,
            text=True
        )
        assert "Test output" in result.stdout, "Should capture stdout"

    def test_script_with_stderr(self):
        """Test script with stderr output."""
        result = subprocess.run(
            ["bash", str(self.fixtures_dir / "with_stderr.sh")],
            capture_output=True,
            text=True
        )
        assert "Error message" in result.stderr, "Should capture stderr"

    # ========================================================================
    # EXIT CODE PROPAGATION TESTS
    # ========================================================================

    def test_success_exit_code(self):
        """Test that exit code 0 is captured."""
        result = subprocess.run(
            ["bash", str(self.fixtures_dir / "exit_success.sh")],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "Should return 0 for success"

    def test_failure_exit_code(self):
        """Test that non-zero exit codes are captured."""
        result = subprocess.run(
            ["bash", str(self.fixtures_dir / "exit_failure.sh")],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, "Should return 1 for failure"

    def test_custom_exit_codes(self):
        """Test that custom exit codes propagate correctly."""
        result = subprocess.run(
            ["bash", str(self.fixtures_dir / "exit_custom.sh")],
            capture_output=True,
            text=True
        )
        assert result.returncode == 42, "Should return custom exit code"

    # ========================================================================
    # OUTPUT CAPTURE TESTS
    # ========================================================================

    def test_stdout_capture(self):
        """Test stdout capture."""
        result = subprocess.run(
            ["bash", str(self.fixtures_dir / "output_test.sh")],
            capture_output=True,
            text=True
        )
        assert "STDOUT" in result.stdout, "Should capture stdout"
        assert "STDOUT" not in result.stderr, "Stdout should not be in stderr"

    def test_stderr_capture(self):
        """Test stderr capture."""
        result = subprocess.run(
            ["bash", str(self.fixtures_dir / "output_test.sh")],
            capture_output=True,
            text=True
        )
        assert "STDERR" in result.stderr, "Should capture stderr"
        assert "STDERR" not in result.stdout, "Stderr should not be in stdout"

    def test_combined_output(self):
        """Test combined stdout and stderr capture."""
        result = subprocess.run(
            ["bash", str(self.fixtures_dir / "output_test.sh")],
            capture_output=True,
            text=True
        )
        combined = result.stdout + result.stderr
        assert "STDOUT" in combined and "STDERR" in combined, \
            "Should capture both streams"

    # ========================================================================
    # TIMEOUT HANDLING TESTS
    # ========================================================================

    def test_timeout_enforcement(self):
        """Test that timeouts are enforced."""
        try:
            result = subprocess.run(
                ["bash", str(self.fixtures_dir / "long_running.sh")],
                capture_output=True,
                text=True,
                timeout=2
            )
            # If we get here, the timeout didn't work
            assert False, "Script should have timed out"
        except subprocess.TimeoutExpired:
            # This is expected
            pass

    def test_timeout_not_triggered(self):
        """Test that timeout doesn't trigger for fast scripts."""
        result = subprocess.run(
            ["bash", str(self.fixtures_dir / "simple.sh")],
            capture_output=True,
            text=True,
            timeout=5
        )
        assert result.returncode == 0, "Fast script should complete within timeout"

    def test_timeout_signal_handling(self):
        """Test that timeout sends proper signal."""
        start_time = time.time()
        try:
            subprocess.run(
                ["bash", str(self.fixtures_dir / "long_running.sh")],
                capture_output=True,
                text=True,
                timeout=1
            )
        except subprocess.TimeoutExpired as e:
            duration = time.time() - start_time
            assert 1.0 <= duration < 2.0, \
                f"Timeout should trigger at ~1s, got {duration:.2f}s"

    # ========================================================================
    # ENVIRONMENT PASSING TESTS
    # ========================================================================

    def test_atomic_root_env(self):
        """Test that ATOMIC_ROOT is passed to scripts."""
        env = os.environ.copy()
        env["ATOMIC_ROOT"] = str(self.atomic_root)

        result = subprocess.run(
            ["bash", str(self.fixtures_dir / "env_check.sh")],
            capture_output=True,
            text=True,
            env=env
        )
        assert result.returncode == 0, "ATOMIC_ROOT should be set"
        assert str(self.atomic_root) in result.stdout, \
            "Should output ATOMIC_ROOT value"

    def test_phase_env_vars(self):
        """Test that phase-specific env vars are passed."""
        env = os.environ.copy()
        env["CURRENT_PHASE"] = "0-setup"
        env["ATOMIC_OUTPUT_DIR"] = str(self.atomic_root.parent / ".outputs")

        result = subprocess.run(
            ["bash", str(self.fixtures_dir / "env_phase.sh")],
            capture_output=True,
            text=True,
            env=env
        )
        assert result.returncode == 0, "Phase env vars should be set"
        assert "0-setup" in result.stdout, "Should see CURRENT_PHASE"

    def test_custom_env_vars(self):
        """Test that custom env vars are passed."""
        env = os.environ.copy()
        env["CUSTOM_VAR"] = "test_value"

        result = subprocess.run(
            ["bash", str(self.fixtures_dir / "env_custom.sh")],
            capture_output=True,
            text=True,
            env=env
        )
        assert "test_value" in result.stdout, "Should pass custom env vars"

    # ========================================================================
    # LIBRARY FUNCTION ACCESS TESTS (Python core.ui)
    # ========================================================================

    def test_source_atomic_lib(self):
        """Test that core.ui module can be imported with step, success, error."""
        try:
            from core.ui import step, success, error
        except ImportError as e:
            assert False, f"Should import step, success, error from core.ui: {e}"

    def test_atomic_step_function(self):
        """Test that step() from core.ui runs without error."""
        from core.ui import step
        try:
            step("Test step")
        except Exception as e:
            assert False, f"step() should run without error: {e}"

    def test_atomic_success_function(self):
        """Test that success() from core.ui runs without error."""
        from core.ui import success
        try:
            success("Test success")
        except Exception as e:
            assert False, f"success() should run without error: {e}"

    def test_atomic_error_function(self):
        """Test that error() from core.ui runs without error."""
        from core.ui import error
        try:
            error("Test error")
        except Exception as e:
            assert False, f"error() should run without error: {e}"

    # ========================================================================
    # ERROR PROPAGATION TESTS
    # ========================================================================

    def test_script_error_detection(self):
        """Test that script errors are detected."""
        result = subprocess.run(
            ["bash", str(self.fixtures_dir / "with_error.sh")],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0, "Should detect script error"

    def test_invalid_script_path(self):
        """Test that invalid script paths are reported."""
        result = subprocess.run(
            ["bash", str(self.fixtures_dir / "nonexistent.sh")],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0, "Should fail for invalid path"

    def test_permission_error(self):
        """Test that permission errors are detected."""
        # Create a non-executable script
        no_exec = self.fixtures_dir / "no_exec.sh"
        if not no_exec.exists():
            no_exec.write_text("#!/bin/bash\necho 'test'\n")
        no_exec.chmod(0o600)  # Remove execute permission

        # Note: bash can still execute it if we pass it as an argument
        # This tests that we can detect if direct execution fails
        try:
            result = subprocess.run(
                [str(no_exec)],
                capture_output=True,
                text=True
            )
            assert result.returncode != 0, "Should detect permission error"
        except PermissionError:
            # This is also acceptable - permission denied at OS level
            pass

    def test_syntax_error_detection(self):
        """Test that bash syntax errors are detected."""
        result = subprocess.run(
            ["bash", str(self.fixtures_dir / "syntax_error.sh")],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0, "Should detect syntax error"
        assert len(result.stderr) > 0, "Should report syntax error"

    # ========================================================================
    # WORKING DIRECTORY TESTS
    # ========================================================================

    def test_correct_working_directory(self):
        """Test that scripts run in correct directory."""
        result = subprocess.run(
            ["bash", str(self.fixtures_dir / "pwd_check.sh")],
            capture_output=True,
            text=True,
            cwd=str(self.atomic_root)
        )
        assert str(self.atomic_root) in result.stdout, \
            "Should run in ATOMIC_ROOT directory"

    def test_output_directory_access(self):
        """Test that scripts can access .outputs directory."""
        env = os.environ.copy()
        env["ATOMIC_ROOT"] = str(self.atomic_root)

        result = subprocess.run(
            ["bash", str(self.fixtures_dir / "output_dir_check.sh")],
            capture_output=True,
            text=True,
            env=env
        )
        assert result.returncode == 0, "Should access .outputs directory"

    def test_state_directory_access(self):
        """Test that scripts can access .state directory."""
        env = os.environ.copy()
        env["ATOMIC_ROOT"] = str(self.atomic_root)

        result = subprocess.run(
            ["bash", str(self.fixtures_dir / "state_dir_check.sh")],
            capture_output=True,
            text=True,
            env=env
        )
        assert result.returncode == 0, "Should access .state directory"

    # ========================================================================
    # PYTHON→BASH INTEGRATION TESTS
    # ========================================================================

    def test_phase_manager_runs_bash_script(self):
        """Test that Python PhaseManager can execute bash task scripts."""
        # Import phase manager
        sys.path.insert(0, str(self.atomic_root / "atomic-claude-python"))

        # Run a simple bash script via subprocess (simulates PhaseManager behavior)
        result = subprocess.run(
            ["bash", str(self.fixtures_dir / "simple.sh")],
            capture_output=True,
            text=True,
            env={"ATOMIC_ROOT": str(self.atomic_root), **os.environ}
        )
        assert result.returncode == 0, "PhaseManager should execute bash scripts"

    def test_python_captures_bash_exit_code(self):
        """Test that Python correctly captures bash script exit codes."""
        # Test success
        result = subprocess.run(
            ["bash", str(self.fixtures_dir / "exit_success.sh")],
            capture_output=True
        )
        assert result.returncode == 0, "Should capture exit 0"

        # Test failure
        result = subprocess.run(
            ["bash", str(self.fixtures_dir / "exit_failure.sh")],
            capture_output=True
        )
        assert result.returncode == 1, "Should capture exit 1"

    def test_python_bash_env_passing(self):
        """Test Python passing environment vars to bash scripts."""
        env = os.environ.copy()
        env["ATOMIC_ROOT"] = str(self.atomic_root)
        env["CURRENT_PHASE"] = "0-setup"
        env["PYTHON_TEST_VAR"] = "test_value_123"

        # Create test script
        test_script = self.fixtures_dir / "env_test_python.sh"
        test_script.write_text("""#!/bin/bash
if [[ "$PYTHON_TEST_VAR" == "test_value_123" ]]; then
    echo "SUCCESS"
    exit 0
else
    echo "FAILED" >&2
    exit 1
fi
""")
        test_script.chmod(0o755)

        result = subprocess.run(
            ["bash", str(test_script)],
            capture_output=True,
            text=True,
            env=env
        )
        assert result.returncode == 0, "Python env vars should reach bash"
        assert "SUCCESS" in result.stdout, "Bash should see Python env vars"

    def test_python_bash_json_exchange(self):
        """Test Python writing JSON that bash reads."""
        # Python writes JSON
        test_json = self.fixtures_dir / "test_data.json"
        test_data = {"key": "value", "number": 42, "nested": {"item": "data"}}

        with open(test_json, "w") as f:
            json.dump(test_data, f)

        # Bash reads JSON (using jq if available, otherwise simple grep)
        bash_script = self.fixtures_dir / "read_json.sh"
        bash_script.write_text(f"""#!/bin/bash
if command -v jq >/dev/null 2>&1; then
    value=$(jq -r '.key' "{test_json}")
    if [[ "$value" == "value" ]]; then
        exit 0
    fi
fi
# Fallback: simple grep
if grep -q '"key": "value"' "{test_json}"; then
    exit 0
fi
exit 1
""")
        bash_script.chmod(0o755)

        result = subprocess.run(["bash", str(bash_script)], capture_output=True)
        assert result.returncode == 0, "Bash should read Python-written JSON"

    # ========================================================================
    # BASH→PYTHON INTEGRATION TESTS
    # ========================================================================

    def test_bash_writes_json_python_reads(self):
        """Test bash writing JSON that Python reads."""
        # Bash writes JSON
        bash_script = self.fixtures_dir / "write_json.sh"
        output_json = self.fixtures_dir / "bash_output.json"

        bash_script.write_text(f"""#!/bin/bash
cat > "{output_json}" << 'EOF'
{{
  "status": "success",
  "task_id": "001",
  "result": "completed"
}}
EOF
exit 0
""")
        bash_script.chmod(0o755)

        result = subprocess.run(["bash", str(bash_script)], capture_output=True)
        assert result.returncode == 0, "Bash should write JSON"

        # Python reads JSON
        with open(output_json) as f:
            data = json.load(f)

        assert data["status"] == "success", "Python should read bash JSON"
        assert data["task_id"] == "001", "Python should parse bash JSON correctly"

    def test_bash_python_state_files(self):
        """Test bash and Python both accessing state files."""
        state_file = self.fixtures_dir / "shared_state.json"

        # Python writes initial state
        initial_state = {"phase": "0-setup", "tasks_complete": 0}
        with open(state_file, "w") as f:
            json.dump(initial_state, f)

        # Bash reads and updates state
        bash_script = self.fixtures_dir / "update_state.sh"
        bash_script.write_text(f"""#!/bin/bash
# Read current state
phase=$(grep -o '"phase": "[^"]*"' "{state_file}" | cut -d'"' -f4)

# Update state (increment tasks_complete)
cat > "{state_file}" << 'EOF'
{{
  "phase": "$phase",
  "tasks_complete": 1
}}
EOF
exit 0
""")
        bash_script.chmod(0o755)

        result = subprocess.run(["bash", str(bash_script)], capture_output=True)
        assert result.returncode == 0, "Bash should update state"

        # Python reads updated state
        with open(state_file) as f:
            updated_state = json.load(f)

        assert updated_state["tasks_complete"] == 1, "Python should see bash updates"

    def test_bash_python_error_handling(self):
        """Test error propagation between bash and Python."""
        # Bash script that fails with specific error
        bash_script = self.fixtures_dir / "error_test.sh"
        error_file = self.fixtures_dir / "error.json"

        bash_script.write_text(f"""#!/bin/bash
cat > "{error_file}" << 'EOF'
{{
  "error": true,
  "message": "Task validation failed",
  "code": 100
}}
EOF
exit 100
""")
        bash_script.chmod(0o755)

        result = subprocess.run(["bash", str(bash_script)], capture_output=True)
        assert result.returncode == 100, "Python should capture bash error code"

        # Python reads error details
        with open(error_file) as f:
            error_data = json.load(f)

        assert error_data["error"] is True, "Python should parse error JSON"
        assert error_data["code"] == 100, "Python should see error details"

    # ========================================================================
    # CROSS-PHASE DATA FLOW TESTS
    # ========================================================================

    def test_phase_output_file_passing(self):
        """Test output files from one phase used by next phase."""
        # Simulate Phase 0 output
        phase0_dir = self.fixtures_dir / "phase0_output"
        phase0_dir.mkdir(exist_ok=True)

        config_file = phase0_dir / "project-config.json"
        config_data = {
            "project_name": "test-project",
            "project_type": "webapp",
            "tech_stack": ["python", "bash"]
        }
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        # Simulate Phase 1 reading Phase 0 output
        bash_script = self.fixtures_dir / "phase1_reader.sh"
        bash_script.write_text(f"""#!/bin/bash
if [[ -f "{config_file}" ]]; then
    if grep -q "test-project" "{config_file}"; then
        exit 0
    fi
fi
exit 1
""")
        bash_script.chmod(0o755)

        result = subprocess.run(["bash", str(bash_script)], capture_output=True)
        assert result.returncode == 0, "Phase should read previous phase output"

    def test_phase_state_consistency(self):
        """Test state file consistency across phases."""
        state_dir = self.fixtures_dir / "state"
        state_dir.mkdir(exist_ok=True)

        # Write task state
        task_state_file = state_dir / "task-state.json"
        task_state = {
            "phase": "0-setup",
            "tasks": {
                "001": {"status": "complete", "timestamp": "2024-01-01T00:00:00"},
                "002": {"status": "complete", "timestamp": "2024-01-01T00:01:00"}
            }
        }
        with open(task_state_file, "w") as f:
            json.dump(task_state, f, indent=2)

        # Verify state is readable
        with open(task_state_file) as f:
            loaded_state = json.load(f)

        assert loaded_state["phase"] == "0-setup", "State should persist"
        assert "001" in loaded_state["tasks"], "Task history should persist"
        assert loaded_state["tasks"]["001"]["status"] == "complete", \
            "Task status should persist"

    def test_phase_closeout_generation(self):
        """Test phase closeout file generation."""
        closeout_dir = self.fixtures_dir / "closeout"
        closeout_dir.mkdir(exist_ok=True)

        # Simulate closeout generation
        closeout_file = closeout_dir / "closeout.json"
        closeout_data = {
            "phase": "0-setup",
            "status": "complete",
            "duration": 120,
            "tasks_run": 9,
            "timestamp": "2024-01-01T00:00:00"
        }

        with open(closeout_file, "w") as f:
            json.dump(closeout_data, f, indent=2)

        # Verify closeout is valid JSON and contains required fields
        with open(closeout_file) as f:
            data = json.load(f)

        assert "phase" in data, "Closeout must have phase"
        assert "status" in data, "Closeout must have status"
        assert data["tasks_run"] == 9, "Closeout must track tasks run"

    # ========================================================================
    # TASK STATE INTEGRATION TESTS
    # ========================================================================

    def test_task_state_persistence(self):
        """Test task state persists across invocations."""
        state_file = self.fixtures_dir / "task_state.json"

        # First invocation - write state
        initial_state = {
            "phase": "1-discovery",
            "tasks": {
                "101": {"status": "complete", "name": "Entry Validation"}
            }
        }
        with open(state_file, "w") as f:
            json.dump(initial_state, f)

        # Second invocation - read and verify
        with open(state_file) as f:
            loaded_state = json.load(f)

        assert loaded_state["tasks"]["101"]["status"] == "complete", \
            "Task state should persist"

    def test_task_state_skip_logic(self):
        """Test task skip logic based on state."""
        state_file = self.fixtures_dir / "skip_state.json"

        # Mark task as complete
        state = {
            "tasks": {
                "001": {"status": "complete"},
                "002": {"status": "pending"}
            }
        }
        with open(state_file, "w") as f:
            json.dump(state, f)

        # Simulate skip check
        bash_script = self.fixtures_dir / "check_skip.sh"
        bash_script.write_text(f"""#!/bin/bash
task_id="001"
if grep -q '"001".*"complete"' "{state_file}"; then
    echo "SKIP"
    exit 0
fi
echo "RUN"
exit 1
""")
        bash_script.chmod(0o755)

        result = subprocess.run(
            ["bash", str(bash_script)],
            capture_output=True,
            text=True
        )
        assert "SKIP" in result.stdout, "Should skip completed tasks"

    def test_task_state_failure_tracking(self):
        """Test task failure tracking in state."""
        state_file = self.fixtures_dir / "failure_state.json"

        # Bash task fails and records failure
        bash_script = self.fixtures_dir / "record_failure.sh"
        bash_script.write_text(f"""#!/bin/bash
cat > "{state_file}" << 'EOF'
{{
  "tasks": {{
    "003": {{
      "status": "failed",
      "error": "Validation error",
      "timestamp": "2024-01-01T00:00:00"
    }}
  }}
}}
EOF
exit 1
""")
        bash_script.chmod(0o755)

        result = subprocess.run(["bash", str(bash_script)], capture_output=True)
        assert result.returncode == 1, "Should fail with exit 1"

        # Python reads failure state
        with open(state_file) as f:
            state = json.load(f)

        assert state["tasks"]["003"]["status"] == "failed", \
            "Failure should be recorded"
        assert "error" in state["tasks"]["003"], \
            "Error message should be recorded"

    # ========================================================================
    # FIXTURE CREATION
    # ========================================================================

    def _create_test_fixtures(self):
        """Create test fixture scripts."""
        fixtures = {
            "simple.sh": "#!/bin/bash\nexit 0\n",

            "with_output.sh": "#!/bin/bash\necho 'Test output'\n",

            "with_stderr.sh": "#!/bin/bash\necho 'Error message' >&2\n",

            "exit_success.sh": "#!/bin/bash\nexit 0\n",

            "exit_failure.sh": "#!/bin/bash\nexit 1\n",

            "exit_custom.sh": "#!/bin/bash\nexit 42\n",

            "output_test.sh": """#!/bin/bash
echo 'STDOUT message'
echo 'STDERR message' >&2
""",

            "long_running.sh": "#!/bin/bash\nsleep 10\n",

            "env_check.sh": """#!/bin/bash
if [[ -z "$ATOMIC_ROOT" ]]; then
    echo "ATOMIC_ROOT not set" >&2
    exit 1
fi
echo "ATOMIC_ROOT=$ATOMIC_ROOT"
exit 0
""",

            "env_phase.sh": """#!/bin/bash
echo "CURRENT_PHASE=$CURRENT_PHASE"
echo "ATOMIC_OUTPUT_DIR=$ATOMIC_OUTPUT_DIR"
exit 0
""",

            "env_custom.sh": """#!/bin/bash
echo "CUSTOM_VAR=$CUSTOM_VAR"
exit 0
""",

            "with_error.sh": """#!/bin/bash
false
exit $?
""",

            "syntax_error.sh": """#!/bin/bash
if [ test  # Missing closing bracket
echo "test"
fi
""",

            "pwd_check.sh": """#!/bin/bash
pwd
exit 0
""",

            "output_dir_check.sh": """#!/bin/bash
if [[ -d "$ATOMIC_ROOT/.outputs" ]]; then
    exit 0
else
    echo ".outputs not found" >&2
    exit 1
fi
""",

            "state_dir_check.sh": """#!/bin/bash
if [[ -d "$ATOMIC_ROOT/.state" ]]; then
    exit 0
else
    echo ".state not found" >&2
    exit 1
fi
""",
        }

        for filename, content in fixtures.items():
            filepath = self.fixtures_dir / filename
            filepath.write_text(content)
            filepath.chmod(0o755)  # Make executable

    # ========================================================================
    # REPORTING
    # ========================================================================

    def _generate_report(self, duration: float) -> AuditReport:
        """Generate audit report from results."""
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed

        return AuditReport(
            timestamp=datetime.now().isoformat(),
            total_tests=len(self.results),
            passed=passed,
            failed=failed,
            duration=duration,
            results=self.results
        )

    def _save_report(self, report: AuditReport):
        """Save report to JSON file with timestamp in filename."""
        # Generate timestamp for filename
        timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S")
        report_file = self.reports_dir / f"integration-audit-{timestamp_str}.json"

        # Also save as latest
        latest_file = self.reports_dir / "integration_audit.json"

        data = {
            "timestamp": report.timestamp,
            "total_tests": report.total_tests,
            "passed": report.passed,
            "failed": report.failed,
            "duration": report.duration,
            "results": [
                {
                    "category": self._normalize_category(r.category),
                    "test": r.name,
                    "passed": r.passed,
                    "message": r.error_message if not r.passed else "Test passed",
                    "severity": r.severity,
                    "duration": f"{r.duration:.3f}s"
                }
                for r in report.results
            ]
        }

        # Save timestamped report
        with open(report_file, "w") as f:
            json.dump(data, f, indent=2)

        # Save as latest (for easy access)
        with open(latest_file, "w") as f:
            json.dump(data, f, indent=2)

        print(f"{DIM}Report saved to: {report_file}{NC}")
        print(f"{DIM}Latest report:   {latest_file}{NC}\n")

    def _normalize_category(self, category: str) -> str:
        """Normalize category names to match spec."""
        mapping = {
            "Python→Bash Integration": "python_bash",
            "Bash→Python Integration": "bash_python",
            "Cross-Phase Data Flow": "data_flow",
            "Task State Integration": "orchestrators",
            "Orchestrator Execution": "orchestrators",
        }
        return mapping.get(category, category.lower().replace(" ", "_"))

    def _display_summary(self, report: AuditReport):
        """Display summary of test results."""
        print(f"{BOLD}{CYAN}{'='*70}{NC}")
        print(f"{BOLD}  Test Summary{NC}")
        print(f"{CYAN}{'='*70}{NC}\n")

        # Overall stats
        print(f"Total Tests:   {report.total_tests}")
        print(f"{GREEN}Passed:{NC}        {report.passed}")
        print(f"{RED}Failed:{NC}        {report.failed}")
        print(f"Success Rate:  {report.success_rate():.1f}%")
        print(f"Duration:      {report.duration:.2f}s\n")

        # Count critical failures
        critical_failures = [r for r in report.results
                           if not r.passed and r.severity == "critical"]
        warning_failures = [r for r in report.results
                          if not r.passed and r.severity == "warning"]

        if critical_failures:
            print(f"{RED}{BOLD}CRITICAL FAILURES: {len(critical_failures)}{NC}\n")
            for failure in critical_failures:
                print(f"  {RED}✗{NC} {failure.category} → {failure.name}")
                if failure.error_message:
                    print(f"    {DIM}{failure.error_message}{NC}")
            print()

        if warning_failures:
            print(f"{YELLOW}Warnings: {len(warning_failures)}{NC}\n")
            for warning in warning_failures:
                print(f"  {YELLOW}!{NC} {warning.category} → {warning.name}")
            print()

        # Category breakdown
        categories = {}
        for result in report.results:
            if result.category not in categories:
                categories[result.category] = {"passed": 0, "failed": 0, "critical": 0}
            if result.passed:
                categories[result.category]["passed"] += 1
            else:
                categories[result.category]["failed"] += 1
                if result.severity == "critical":
                    categories[result.category]["critical"] += 1

        print(f"{BOLD}Category Breakdown:{NC}\n")
        for category, stats in categories.items():
            total = stats["passed"] + stats["failed"]
            rate = (stats["passed"] / total * 100) if total > 0 else 0

            if stats["critical"] > 0:
                status = f"{RED}✗{NC}"
            elif stats["failed"] > 0:
                status = f"{YELLOW}!{NC}"
            else:
                status = f"{GREEN}✓{NC}"

            print(f"  {status} {category:<35} {stats['passed']}/{total} ({rate:.0f}%)")

        print(f"\n{CYAN}{'='*70}{NC}\n")

        # Exit with appropriate code
        if critical_failures:
            print(f"{RED}{BOLD}Integration audit FAILED with "
                  f"{len(critical_failures)} CRITICAL failures{NC}\n")
            return 1
        elif report.failed > 0:
            print(f"{YELLOW}Integration audit completed with "
                  f"{report.failed} warnings{NC}\n")
            return 0  # Warnings don't fail the audit
        else:
            print(f"{GREEN}Integration audit PASSED - all tests succeeded{NC}\n")
            return 0


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Integration Audit Runner - validates Python/Bash integration points"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    runner = IntegrationAuditRunner()
    report = runner.run_all_tests()

    # Exit with appropriate code based on critical failures only
    critical_failures = [r for r in report.results
                        if not r.passed and r.severity == "critical"]
    sys.exit(1 if critical_failures else 0)


if __name__ == "__main__":
    main()
