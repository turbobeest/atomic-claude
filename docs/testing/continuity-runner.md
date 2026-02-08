# Continuity Test Runner

## Overview

The Continuity Test Runner validates seamless task-to-task execution within a phase without terminal errors, crashes, or resource leaks. It is one of three phase-end test runners used to validate quality before proceeding to the next phase.

## Purpose

The Continuity Test Runner ensures:

- All tasks in a phase execute sequentially without crashes
- No unhandled exceptions or exit code failures
- Proper state transitions between tasks
- No resource leaks (processes, file handles)
- Proper cleanup after task completion

## What It Tests

### Exit Codes

Every task must exit with code 0 (success). Non-zero exit codes indicate failure.

### State Transitions

After each task completes, the runner validates:
- Task is marked complete in `.state/task-state.json`
- State file is valid JSON
- Phase state is correctly updated

### Resource Cleanup

The runner detects:
- **Orphaned processes**: Child processes not terminated
- **File handle leaks**: Unclosed files or sockets
- **Temporary files**: Leftover temp files not cleaned up

### Error Handling

The runner distinguishes:
- **Hard failures**: Crashes, segfaults, unhandled exceptions
- **Expected errors**: Validation failures, user cancellations (handled gracefully)

## When to Use

Run the Continuity Test:

1. **After implementing a new phase**: Validate all tasks work together
2. **After modifying phase tasks**: Ensure changes don't break flow
3. **Before UAT and functional testing**: Catch crashes early
4. **In CI/CD pipeline**: Automated quality gate

## Usage

### Basic Usage

```bash
# Run continuity test for Phase 0
python tests/runners/continuity_runner.py 0
```

### With Custom Configuration

```bash
# Use custom test config
python tests/runners/continuity_runner.py 0 \
    --config tests/phase_configs/phase_00_tests.json
```

### With Mocked Inputs

```bash
# Use mock LLM responses (faster, no API calls)
python tests/runners/continuity_runner.py 0 --mock
```

### Custom Output Directory

```bash
# Save reports to custom location
python tests/runners/continuity_runner.py 0 \
    --output-dir /tmp/test-reports
```

## Configuration

### Test Configuration File

Each phase has a configuration file: `tests/phase_configs/phase_NN_tests.json`

Example:

```json
{
  "phase": "0-setup",
  "name": "Phase 0: Setup",
  "tasks": ["001", "002", "003", "004", "006", "009"],
  "continuity": {
    "inputs": "fixtures/phase00/continuity_inputs.txt",
    "timeout_per_task": 120
  }
}
```

### Configuration Fields

- `phase`: Phase identifier (e.g., "0-setup")
- `name`: Human-readable phase name
- `tasks`: Array of task IDs to test in order
- `continuity.inputs`: Path to input file for mocked/prescribed inputs
- `continuity.timeout_per_task`: Timeout in seconds (default: 60)

## Output

### Console Output

The runner provides real-time progress:

```
================================================================================
CONTINUITY TEST: Phase 0: Setup
================================================================================

  Testing Task 001: Mode selection...
    ✓ Mode selection (2.3s)
  Testing Task 002: Config collection...
    ✓ Config collection (5.1s)
  Testing Task 003: Config display...
    ✓ Config display (1.8s)

...

================================================================================
CONTINUITY TEST RESULTS: Phase 0: Setup
================================================================================

Duration: 45.3s
Tasks: 6 total, 6 passed, 0 failed, 0 skipped

Task Results:
  ✓ Task 001: Mode selection [PASS] (2.3s)
  ✓ Task 002: Config collection [PASS] (5.1s)
  ✓ Task 003: Config display [PASS] (1.8s)
  ✓ Task 004: Config approval [PASS] (3.2s)
  ✓ Task 006: Memory initialization [PASS] (12.4s)
  ✓ Task 009: Phase closeout [PASS] (20.5s)

Validation Checks:
  ✓ State transitions valid
  ✓ No resource leaks
  ✓ Cleanup successful

✓ Overall Result: PASSED

================================================================================
```

### Report Files

Two report files are generated:

#### JSON Report

Structured data for programmatic analysis:

```json
{
  "phase_id": "0-setup",
  "phase_name": "Phase 0: Setup",
  "started_at": "2026-02-06T14:30:00",
  "completed_at": "2026-02-06T14:30:45",
  "duration_seconds": 45.3,
  "total_tasks": 6,
  "tasks_passed": 6,
  "tasks_failed": 0,
  "success": true,
  "task_results": [...],
  "errors": [],
  "warnings": []
}
```

#### Text Report

Human-readable summary for review.

## Interpreting Results

### Success Criteria

A phase passes continuity testing when:

- ✓ All tasks complete with exit code 0
- ✓ State transitions are valid after each task
- ✓ No orphaned processes remain
- ✓ No file handle leaks detected
- ✓ Temporary files cleaned up

### Common Failures

#### Task Exit Code Failure

```
✗ Task 003: Config display [FAIL] (1.8s)
   Error: Exit code 1: Configuration validation failed
```

**Fix**: Debug the task script, check error messages in stderr.

#### State Transition Failure

```
⚠️ Warning: Invalid state transition after task 004
```

**Fix**: Ensure task properly calls `state.mark_task_complete()`.

#### Resource Leak

```
⚠️ Warning: 3 orphaned processes
```

**Fix**: Ensure task scripts properly terminate child processes.

#### Cleanup Failure

```
⚠️ Warning: 5 temp files not cleaned up
```

**Fix**: Add cleanup logic to task scripts or use trap handlers.

## Integration with Development Workflow

### Phase Implementation Workflow

```
1. Implement phase tasks
2. Run Continuity Test ← YOU ARE HERE
3. Fix any failures
4. Run UAT (user validation)
5. Run Functional Tests (coverage)
6. All pass? → Proceed to next phase
```

### CI/CD Integration

Add to `.github/workflows/test.yml`:

```yaml
- name: Continuity Test - Phase 0
  run: python tests/runners/continuity_runner.py 0 --mock
```

## Advanced Usage

### Programmatic Usage

```python
from tests.runners import ContinuityTestRunner, load_phase_config

# Load config
config = load_phase_config("tests/phase_configs/phase_00_tests.json")

# Run test
runner = ContinuityTestRunner()
report = runner.run_phase_continuity_test(
    phase_num=0,
    config=config,
    mock_inputs=True
)

# Check result
if report.success:
    print("Phase passed continuity test!")
else:
    print(f"Failed: {report.errors}")
```

### Custom Assertions

```python
# Add custom validation
def custom_validation(report):
    # Check task duration
    for result in report.task_results:
        if result.duration_seconds > 30:
            print(f"Warning: Task {result.task_id} is slow")

    # Check memory usage
    total_memory_mb = sum(
        r.resource_usage.get("memory_delta_mb", 0)
        for r in report.task_results
    )
    assert total_memory_mb < 500, "Memory usage too high"

runner = ContinuityTestRunner()
report = runner.run_phase_continuity_test(0, config)
custom_validation(report)
```

## Limitations

### What Continuity Testing Does NOT Validate

- **Correctness**: Tasks may pass but produce wrong outputs
- **User Experience**: UI/UX quality not validated (use UAT)
- **Code Coverage**: Coverage not measured (use Functional Tests)
- **Business Logic**: Only validates execution, not behavior

### Known Issues

- **Interactive tasks**: Tasks requiring user input may hang (use mock mode)
- **External dependencies**: Network calls may fail in isolated environments
- **Timing issues**: Race conditions may appear intermittently

## Troubleshooting

### Test Hangs

If test hangs on a task:

1. Check task timeout: Increase `timeout_per_task` in config
2. Check for interactive prompts: Use `--mock` flag
3. Check for deadlocks: Review task script for blocking calls

### False Positives

If test reports failures incorrectly:

1. Check task exit codes: Ensure tasks exit with 0 on success
2. Check state updates: Ensure tasks mark themselves complete
3. Check cleanup: Ensure temp files use proper cleanup handlers

### Resource Leaks

If resource leaks reported:

1. Add trap handlers to bash scripts:
   ```bash
   cleanup() {
       kill $CHILD_PID 2>/dev/null
       rm -f /tmp/tempfile
   }
   trap cleanup EXIT
   ```
2. Close file handles explicitly
3. Terminate background processes before exit

## See Also

- `tests/phase_configs/README.md` - Test configuration format
- `REFACTOR-PLAN.md` - Overall testing strategy
- `docs/testing/uat-runner.md` - UAT documentation (TBD)
- `docs/testing/functional-runner.md` - Functional test docs (TBD)

## Support

For issues or questions:

1. Check this documentation
2. Review test configuration in `tests/phase_configs/`
3. Examine test reports in `tests/reports/`
4. Review REFACTOR-PLAN.md for testing strategy
