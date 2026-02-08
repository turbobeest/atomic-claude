# Smoke Test Runner - Quick Reference

## Overview

The smoke test runner provides quick validation that basic Atomic Claude flows work correctly in under 2 minutes.

**Purpose**: Pre-flight checks for CI/CD, local development validation, and quick system health checks.

## Usage

### Basic Usage

```bash
# Run all smoke tests
python test/smoke_test_runner.py

# Verbose output
python test/smoke_test_runner.py --verbose

# JSON report only
python test/smoke_test_runner.py --json
```

### Exit Codes

- **0**: All smoke tests passed
- **1**: One or more tests failed

## Tests Included

### 1. Log File System Test
- Verifies `.logs/` directory exists or can be created
- Tests write access to log files
- Tests read access and content verification
- Cleans up test artifacts

**Expected Duration**: < 1 second

### 2. Phase 0 Execution Test
- Runs Phase 0 (Setup) in UAT mode
- Verifies completion in < 30 seconds
- Checks that closeout file is created
- Validates basic phase execution flow

**Expected Duration**: < 30 seconds

### 3. Phase 1 Execution Test
- Runs Phase 1 (Discovery) in UAT mode
- Verifies completion in < 30 seconds
- Checks that closeout file is created
- Validates requirements gathering flow

**Expected Duration**: < 30 seconds

### 4. Phase 2 Execution Test
- Runs Phase 2 (PRD) in UAT mode
- Verifies completion in < 30 seconds
- Checks that closeout file is created
- Validates PRD authoring flow

**Expected Duration**: < 30 seconds

### 5. Dashboard Service Test
- Checks if dashboard is running on port 5174
- Attempts to start dashboard if not running
- Verifies HTTP 200 response
- Validates web service accessibility

**Expected Duration**: < 10 seconds (if already running), < 15 seconds (if starting)

### 6. State Management Test
- Cleans previous state
- Runs Phase 0 to create state
- Verifies state directories created (`.state/`, `.outputs/`)
- Cleans state again
- Verifies state fully removed

**Expected Duration**: < 30 seconds

## Test Flow

```
┌─────────────────────────────────────────┐
│ 1. Clean State                          │
│    - Remove .state/                     │
│    - Remove .outputs/                   │
│    - Remove .claude/                    │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│ 2. Setup UAT Fixtures                   │
│    - Copy uat_setup.md to               │
│      initialization/setup.md            │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│ 3. Run Tests in Order                   │
│    a. Log File System                   │
│    b. Phase 0 Execution                 │
│    c. Phase 1 Execution                 │
│    d. Phase 2 Execution                 │
│    e. Dashboard Service                 │
│    f. State Management                  │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│ 4. Generate Report                      │
│    - Console output with colors         │
│    - JSON report to test/reports/       │
│    - Pass/fail status                   │
└─────────────────────────────────────────┘
```

## Time Limits

- **Per-Phase Timeout**: 30 seconds
- **Dashboard Timeout**: 10 seconds
- **Total Suite Timeout**: 120 seconds (2 minutes)

If any test exceeds its timeout, it fails and the suite continues.

If the total suite exceeds 2 minutes, a warning is displayed.

## Report Output

### Console Report

```
================================================================================
  ATOMIC CLAUDE 2.0 - SMOKE TEST SUITE
================================================================================

▶ Testing: Log File System
  ✓ Log File System passed (0.01s)

▶ Testing: Phase 0 Execution
  ✓ Phase 0 Execution passed (12.34s)

▶ Testing: Phase 1 Execution
  ✓ Phase 1 Execution passed (15.67s)

▶ Testing: Phase 2 Execution
  ✓ Phase 2 Execution passed (18.92s)

▶ Testing: Dashboard Service
  ✓ Dashboard Service passed (2.11s)

▶ Testing: State Management
  ✓ State Management passed (11.23s)

================================================================================
  SMOKE TEST RESULTS
================================================================================

  Total tests:  6
  Passed:       6
  Failed:       0
  Total time:   60.28s / 120s

  Test Details:
    ✓ Log File System              (0.01s)
    ✓ Phase 0 Execution            (12.34s)
    ✓ Phase 1 Execution            (15.67s)
    ✓ Phase 2 Execution            (18.92s)
    ✓ Dashboard Service            (2.11s)
    ✓ State Management             (11.23s)

  ✓ All smoke tests passed!
```

### JSON Report

Located at: `test/reports/smoke-test-report.json`

```json
{
  "timestamp": "2024-02-04T21:30:00.000000",
  "total_time": 60.28,
  "timeout_limit": 120,
  "all_passed": true,
  "total_tests": 6,
  "passed": 6,
  "failed": 0,
  "tests": [
    {
      "name": "Log File System",
      "passed": true,
      "duration": 0.01,
      "error": null
    },
    {
      "name": "Phase 0 Execution",
      "passed": true,
      "duration": 12.34,
      "error": null
    },
    {
      "name": "Phase 1 Execution",
      "passed": true,
      "duration": 15.67,
      "error": null
    },
    {
      "name": "Phase 2 Execution",
      "passed": true,
      "duration": 18.92,
      "error": null
    },
    {
      "name": "Dashboard Service",
      "passed": true,
      "duration": 2.11,
      "error": null
    },
    {
      "name": "State Management",
      "passed": true,
      "duration": 11.23,
      "error": null
    }
  ]
}
```

## Environment Variables

The smoke test runner sets these automatically:

- `ATOMIC_UAT_MODE=true` - Enables UAT mode for phases
- `ATOMIC_AUTO_APPROVE=true` - Auto-approves all prompts

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Smoke Tests

on: [push, pull_request]

jobs:
  smoke:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run smoke tests
        run: python test/smoke_test_runner.py
      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v2
        with:
          name: smoke-test-report
          path: test/reports/smoke-test-report.json
```

### Pre-commit Hook Example

```bash
#!/bin/bash
# .git/hooks/pre-push

echo "Running smoke tests..."
python test/smoke_test_runner.py

if [ $? -ne 0 ]; then
    echo "❌ Smoke tests failed! Push aborted."
    exit 1
fi

echo "✓ Smoke tests passed!"
```

## Troubleshooting

### Test Hangs on Phase Execution

**Symptom**: Phase test doesn't complete within 30 seconds

**Solutions**:
1. Check if LLM provider is accessible
2. Verify `.env` file has valid API keys
3. Run phase manually to see error messages:
   ```bash
   python main.py run 0
   ```

### Dashboard Test Fails

**Symptom**: Cannot connect to dashboard

**Solutions**:
1. Check if port 5174 is available:
   ```bash
   lsof -i :5174
   ```
2. Verify Node.js is installed:
   ```bash
   node --version
   ```
3. Check dashboard dependencies:
   ```bash
   cd dashboard && npm install
   ```

### State Management Test Fails

**Symptom**: State directories not created or not cleaned

**Solutions**:
1. Check file permissions on repo root
2. Verify disk space available
3. Manually clean state:
   ```bash
   rm -rf .state .outputs .claude
   ```

### Timeout Exceeded

**Symptom**: Total suite takes > 2 minutes

**Solutions**:
1. Run tests individually to identify slow test
2. Check system load (CPU, memory)
3. Verify network connectivity for LLM calls
4. Consider increasing `SMOKE_TIMEOUT` for slower systems

## Development

### Adding New Tests

```python
def test_new_feature(self) -> Dict:
    """
    Test new feature.

    Returns:
        Dict with test results
    """
    test_name = "New Feature"
    self.log(f"\n▶ Testing: {test_name}", Colors.CYAN)

    result = {
        "name": test_name,
        "passed": False,
        "duration": 0,
        "error": None,
    }

    start = time.time()

    try:
        # Test logic here

        result["passed"] = True
        result["duration"] = time.time() - start
        self.log(f"  ✓ {test_name} passed ({result['duration']:.2f}s)", Colors.GREEN)

    except Exception as e:
        result["duration"] = time.time() - start
        result["error"] = str(e)
        self.log(f"  ✗ {test_name} failed: {result['error']}", Colors.RED)

    self.results.append(result)
    return result
```

Then add to `run_all_tests()`:

```python
tests = [
    lambda: self.test_logging(),
    lambda: self.test_phase_execution(0),
    lambda: self.test_phase_execution(1),
    lambda: self.test_phase_execution(2),
    lambda: self.test_dashboard(),
    lambda: self.test_state_management(),
    lambda: self.test_new_feature(),  # Add here
]
```

## See Also

- `test/uat_runner.py` - Full UAT test suite (longer duration)
- `test/test_runner.py` - Unit test suite
- `test/TEST-QUICK-START.md` - General testing guide
