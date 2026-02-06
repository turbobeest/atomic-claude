# Integration Audit Runner

## Overview

The Integration Audit Runner validates the critical handoff points between Python orchestrators and bash task scripts in Atomic Claude. This ensures that the hybrid Python-Bash architecture works correctly and that all integration points are functioning as expected.

## Purpose

The integration audit runner tests:

1. **Orchestrator → Bash Execution**: Python can execute bash scripts correctly
2. **Exit Code Propagation**: Success (0) and failure (non-zero) codes are captured
3. **Output Capture**: stdout and stderr are properly captured and separated
4. **Timeout Handling**: Long-running scripts are terminated at specified timeouts
5. **Environment Variables**: Required env vars (ATOMIC_ROOT, CURRENT_PHASE, etc.) are passed
6. **Library Function Access**: Bash scripts can source and call lib/atomic.sh functions
7. **Error Propagation**: Script errors are detected and reported correctly
8. **Working Directory**: Scripts execute in the correct directory with proper file access

## Running the Audit

### Basic Execution

```bash
# From the repository root
python3 test/integration_audit_runner.py
```

### Expected Output

```
======================================================================
  Integration Audit Runner
======================================================================

Running Integration Tests:

Orchestrator Execution:
  ✓ Simple Execution
  ✓ Script With Output
  ✓ Script With Stderr

Exit Code Propagation:
  ✓ Success Exit Code
  ✓ Failure Exit Code
  ✓ Custom Exit Codes

...

======================================================================
  Test Summary
======================================================================

Total Tests:   26
Passed:        26
Failed:        0
Success Rate:  100.0%
Duration:      3.42s

Category Breakdown:

  ✓ Orchestrator Execution         3/3 (100%)
  ✓ Exit Code Propagation          3/3 (100%)
  ✓ Output Capture                 3/3 (100%)
  ✓ Timeout Handling               3/3 (100%)
  ✓ Environment Passing            3/3 (100%)
  ✓ Library Function Access        4/4 (100%)
  ✓ Error Propagation              4/4 (100%)
  ✓ Working Directory              3/3 (100%)

======================================================================

Integration audit PASSED - all tests succeeded
```

## Test Categories

### 1. Orchestrator Execution (3 tests)

Tests basic ability to execute bash scripts:

- **Simple Execution**: Can execute a minimal bash script
- **Script With Output**: Captures stdout from scripts
- **Script With Stderr**: Captures stderr from scripts

### 2. Exit Code Propagation (3 tests)

Validates that exit codes flow correctly from bash to Python:

- **Success Exit Code**: Exit code 0 indicates success
- **Failure Exit Code**: Exit code 1 indicates failure
- **Custom Exit Codes**: Non-standard exit codes (e.g., 42) are preserved

### 3. Output Capture (3 tests)

Ensures output streams are captured correctly:

- **Stdout Capture**: Standard output is captured separately
- **Stderr Capture**: Error output is captured separately
- **Combined Output**: Both streams can be accessed independently

### 4. Timeout Handling (3 tests)

Validates timeout mechanisms work correctly:

- **Timeout Enforcement**: Long-running scripts are terminated
- **Timeout Not Triggered**: Fast scripts complete before timeout
- **Timeout Signal Handling**: Timeouts trigger at correct times

### 5. Environment Passing (3 tests)

Tests that environment variables reach bash scripts:

- **Atomic Root Env**: ATOMIC_ROOT is set and accessible
- **Phase Env Vars**: CURRENT_PHASE, ATOMIC_OUTPUT_DIR are set
- **Custom Env Vars**: Additional env vars can be passed

### 6. Library Function Access (4 tests)

Validates bash scripts can use lib/atomic.sh functions:

- **Source Atomic Lib**: Scripts can source lib/atomic.sh
- **Atomic Step Function**: atomic_step() is callable
- **Atomic Success Function**: atomic_success() is callable
- **Atomic Error Function**: atomic_error() is callable

### 7. Error Propagation (4 tests)

Ensures errors are detected and reported:

- **Script Error Detection**: Scripts that fail are detected
- **Invalid Script Path**: Missing scripts report clear errors
- **Permission Error**: Non-executable scripts are handled
- **Syntax Error Detection**: Bash syntax errors are caught

### 8. Working Directory (3 tests)

Validates directory context is correct:

- **Correct Working Directory**: Scripts run in ATOMIC_ROOT
- **Output Directory Access**: Scripts can access .outputs/
- **State Directory Access**: Scripts can access .state/

## Test Fixtures

The audit runner automatically creates test fixtures in `test/fixtures/`:

| Fixture | Purpose |
|---------|---------|
| `simple.sh` | Minimal script that exits 0 |
| `exit_success.sh` | Explicitly exits with 0 |
| `exit_failure.sh` | Explicitly exits with 1 |
| `exit_custom.sh` | Exits with custom code (42) |
| `with_output.sh` | Writes to stdout |
| `with_stderr.sh` | Writes to stderr |
| `output_test.sh` | Writes to both stdout and stderr |
| `long_running.sh` | Sleeps for 10 seconds (for timeout tests) |
| `env_check.sh` | Validates ATOMIC_ROOT is set |
| `env_phase.sh` | Displays phase environment variables |
| `env_custom.sh` | Displays custom environment variable |
| `lib_source.sh` | Sources lib/atomic.sh |
| `lib_atomic_step.sh` | Calls atomic_step() |
| `lib_atomic_success.sh` | Calls atomic_success() |
| `lib_atomic_error.sh` | Calls atomic_error() |
| `with_error.sh` | Script that fails |
| `syntax_error.sh` | Script with bash syntax error |
| `pwd_check.sh` | Outputs current directory |
| `output_dir_check.sh` | Checks .outputs/ exists |
| `state_dir_check.sh` | Checks .state/ exists |
| `no_exec.sh` | Non-executable script (permissions test) |

## Report Output

### JSON Report

A detailed JSON report is saved to `test/reports/integration_audit.json`:

```json
{
  "timestamp": "2026-02-04T21:20:20.863538",
  "summary": {
    "total_tests": 26,
    "passed": 26,
    "failed": 0,
    "success_rate": "100.0%",
    "duration": "3.42s"
  },
  "results": [
    {
      "name": "Simple Execution",
      "category": "Orchestrator Execution",
      "passed": true,
      "duration": "0.022s",
      "error": null
    },
    ...
  ]
}
```

### Console Output

The console output provides:

- Real-time test execution with pass/fail indicators
- Detailed error messages for failures
- Summary statistics (total, passed, failed, success rate)
- Category breakdown showing performance by test category
- Overall pass/fail status

## Exit Codes

The audit runner returns:

- **0**: All tests passed
- **1**: One or more tests failed

This makes it suitable for CI/CD integration.

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Integration Audit
on: [push, pull_request]

jobs:
  integration-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'

      - name: Run Integration Audit
        run: python3 test/integration_audit_runner.py

      - name: Upload Report
        if: always()
        uses: actions/upload-artifact@v2
        with:
          name: integration-audit-report
          path: test/reports/integration_audit.json
```

## Troubleshooting

### Common Issues

**Issue**: Tests fail with "ATOMIC_ROOT not set"

**Solution**: The audit runner automatically sets ATOMIC_ROOT. If tests fail, ensure you're running from the repository root.

---

**Issue**: Library function tests fail

**Solution**: Ensure lib/atomic.sh exists and is properly formatted. Check that bash can source it without errors.

---

**Issue**: Timeout tests are flaky

**Solution**: Timeout tests have some variance (±0.1s). The test allows for this. If consistently failing, check system load.

---

**Issue**: Permission error test fails

**Solution**: The permission test creates a non-executable file. Some systems handle this differently. The test accepts both subprocess failures and PermissionError exceptions.

## Architecture Notes

### Why This Audit Matters

Atomic Claude uses a **hybrid Python-Bash architecture**:

- **Python**: Orchestration, state management, provider routing
- **Bash**: Task execution, LLM invocation, git operations

The integration points between these layers are critical. This audit ensures:

1. **Deterministic Execution**: Same inputs produce same outputs
2. **Error Transparency**: Bash failures are visible to Python
3. **State Consistency**: Environment and working directory are correct
4. **Library Access**: Bash scripts can use shared functions

### Design Decisions

**Q: Why not pure Python?**

A: Bash provides superior shell integration, git operations, and file manipulation. The pipeline tasks are heavily shell-oriented.

**Q: Why not pure Bash?**

A: Python provides better state management, data structures, error handling, and testing infrastructure.

**Q: How do you ensure reliability?**

A: This integration audit validates all handoff points. Run it before committing changes to orchestration or lib/ code.

## Development Guidelines

### Adding New Integration Tests

When adding new integration points:

1. **Create test fixture** in `test/fixtures/`
2. **Add test method** to `IntegrationAuditRunner` class
3. **Add to category** in `run_all_tests()`
4. **Document** in this README

Example:

```python
def test_new_feature(self):
    """Test description."""
    result = subprocess.run(
        ["bash", str(self.fixtures_dir / "new_feature.sh")],
        capture_output=True,
        text=True,
        env={"ATOMIC_ROOT": str(self.atomic_root)}
    )
    assert result.returncode == 0, "Feature should work"
```

### Fixture Guidelines

Test fixtures should be:

- **Minimal**: Only test one thing
- **Fast**: Complete in <1s (except timeout tests)
- **Isolated**: No side effects or state changes
- **Documented**: Clear purpose in filename and comments

## Related Documentation

- **lib/atomic.sh**: Core bash library functions
- **lib/phase.py**: Python phase orchestrator
- **atomic-claude-python/**: Python implementation
- **CLAUDE.md**: Overall architecture and patterns

## Version History

- **v1.0.0** (2026-02-04): Initial implementation with 26 tests across 8 categories
