# State Management Audit Runner

Comprehensive audit tool for validating ATOMIC CLAUDE's task state tracking, resume functionality, and state file integrity.

## Overview

The State Audit Runner validates the core state management system that enables:
- Task completion tracking across phases
- Resume functionality (--resume-at flag)
- State persistence across sessions
- Corruption resistance and recovery

## Quick Start

```bash
# Full audit (validation + transitions + resume + corruption)
python test/state_audit_runner.py

# Validation only (no execution tests)
python test/state_audit_runner.py --skip-exec

# Verbose output
python test/state_audit_runner.py --verbose

# Custom number of resume tests (default: 5)
python test/state_audit_runner.py --resume-tests 10
```

## What It Tests

### 1. State File Validation (6 checks)

Validates `.claude/task-state.json` structure and content:

- **File exists**: Checks state file is present
- **Valid JSON**: Validates JSON format
- **Schema structure**: Verifies required keys (version, current_phase, current_task, phases)
- **Phase IDs**: Validates phase IDs match expected phases (0-setup through 9-release)
- **Task completion tracking**: Checks task status values are valid
- **Timestamp formats**: Validates ISO format timestamps

**Example output:**
```
  [1/6] Checking state file exists...
    ✓ State file found: .claude/task-state.json

  [2/6] Checking JSON validity...
    ✓ Valid JSON format

  [3/6] Checking schema structure...
    ✓ All required keys present

  [4/6] Validating phase IDs...
    ✓ All phase IDs valid (1 phases tracked)

  [5/6] Checking task completion tracking...
    ✓ All tasks valid (5 tasks tracked)

  [6/6] Checking timestamp formats...
    ✓ All timestamps valid ISO format
```

### 2. State Transitions (4 tests)

Validates state machine integrity:

- **No stuck tasks**: Checks no tasks left in "in_progress" state
- **Timestamp consistency**: Completed tasks have completion timestamps
- **No orphaned entries**: Phase IDs match expected phases
- **Completion status consistency**: Phase completion matches task status

**Example output:**
```
  [1/4] Checking for stuck tasks...
    ✓ No tasks stuck in in_progress state

  [2/4] Checking completed tasks have timestamps...
    ✓ All completed tasks have timestamps

  [3/4] Checking for orphaned phase entries...
    ✓ No orphaned phase entries

  [4/4] Checking completed status consistency...
    ✓ Phase completion status consistent
```

### 3. Resume Functionality (3-5 tests)

Tests resume capability by:

1. Selecting resume points (evenly distributed across tasks)
2. Marking tasks before resume point as complete
3. Running phase with `--resume-at` flag
4. Verifying completed tasks are skipped
5. Verifying resume task and subsequent tasks execute

**Example output:**
```
  Testing 5 resume points: ['001', '002', '003', '004', '005']

  [1/5] Testing resume from task 001...
    ✓ Resume from 001 successful
      Skipped: 0 tasks
      Executed: 5 tasks

  [2/5] Testing resume from task 003...
    ✓ Resume from 003 successful
      Skipped: 2 tasks
      Executed: 3 tasks
```

### 4. Corruption Resistance (4 tests)

Tests graceful recovery from:

- **Invalid JSON**: Malformed JSON content
- **Missing state file**: Deleted or never created
- **Partial state data**: Missing required keys
- **Corrupted task data**: Invalid task structure

**Example output:**
```
  [1/4] Testing invalid JSON recovery...
    ✗ Failed to recover from invalid JSON

  [2/4] Testing missing state file recovery...
    ✓ System recovered from missing state file

  [3/4] Testing partial state data recovery...
    ✓ System recovered from partial state data

  [4/4] Testing corrupted task data recovery...
    ✓ System recovered from corrupted task data
```

## Report Output

### Console Report

Color-coded summary with:
- Test duration
- Category-by-category results
- Overall pass/fail counts
- State file information

**Example:**
```
  STATE AUDIT REPORT
  ═══════════════════════════════════════════════════════════

  Test Duration: 0.2s

  Results by Category:

    State File Validation:
      Passed: 6/6
      Failed: 0/6

    State Transitions:
      Passed: 4/4
      Failed: 0/4

    Resume Functionality:
      Passed: 5/5
      Failed: 0/5

    Corruption Resistance:
      Passed: 3/4
      Failed: 1/4

  Overall Assessment:
    Total Tests: 19
    Passed: 18
    Failed: 1

    ⚠️ GOOD - Most state management tests passed (95%)

  State File Info:
    Location: /path/to/.claude/task-state.json
    Size: 1,240 bytes (1.2 KB)
```

### JSON Report

Detailed report saved to `test/reports/state-audit-YYYYMMDD-HHMMSS.json`:

```json
{
  "timestamp": "2026-02-04T21:20:20.684153",
  "test_duration_seconds": 0.247377,
  "validation": {
    "valid": true,
    "issues": [],
    "checks_passed": 6,
    "checks_failed": 0,
    "file_exists": true,
    "valid_json": true,
    "has_schema": true,
    "phase_count": 1,
    "task_count": 5
  },
  "transitions": {
    "valid": true,
    "issues": [],
    "tests_passed": 4,
    "tests_failed": 0,
    "stuck_tasks": [],
    "orphaned_entries": []
  },
  "resume": {
    "valid": true,
    "tests_passed": 5,
    "tests_failed": 0,
    "resume_tests": [...]
  },
  "corruption": {
    "valid": true,
    "issues": [],
    "tests_passed": 4,
    "tests_failed": 0,
    "corruption_tests": [...]
  },
  "summary": {
    "total_tests": 19,
    "total_passed": 18
  }
}
```

## Use Cases

### 1. Pre-Release Validation

Before releasing a new version, validate state management:

```bash
python test/state_audit_runner.py
```

Expected: 100% pass rate (all tests green)

### 2. Post-Merge Verification

After merging state management changes:

```bash
python test/state_audit_runner.py --verbose
```

Review detailed output for any issues introduced.

### 3. Debugging State Issues

When users report state problems:

```bash
# Validate existing state
python test/state_audit_runner.py --skip-exec

# Test corruption resistance
python test/state_audit_runner.py --skip-exec | grep -A 10 "CORRUPTION RESISTANCE"
```

### 4. CI/CD Integration

Add to continuous integration:

```bash
# Run as part of test suite
python test/state_audit_runner.py --skip-exec
exit_code=$?

if [ $exit_code -ne 0 ]; then
  echo "State audit failed"
  exit 1
fi
```

### 5. State File Forensics

Investigate corrupted state:

```bash
# Run with verbose output
python test/state_audit_runner.py --skip-exec --verbose

# Check specific report
cat test/reports/state-audit-*.json | jq .validation.issues
```

## Architecture

### State File Structure

```json
{
  "version": "1.0",
  "current_phase": "2-prd",
  "current_task": "205",
  "phases": {
    "0-setup": {
      "started_at": "2026-02-04T20:00:00Z",
      "completed_at": "2026-02-04T20:10:00Z",
      "completed": true,
      "tasks": {
        "001": {
          "name": "Mode Selection",
          "status": "complete",
          "started_at": "2026-02-04T20:00:00Z",
          "completed_at": "2026-02-04T20:01:00Z",
          "artifacts": []
        }
      }
    }
  }
}
```

### Task Status Values

- `pending`: Not yet started
- `in_progress`: Currently executing
- `complete`: Successfully finished
- `failed`: Encountered error

### State Transitions

```
pending → in_progress → complete
              ↓
           failed
```

### Resume Logic

1. Check if `TASK_RESUME_AT` flag is set
2. Skip tasks until resume point is reached
3. Execute resume task and all subsequent tasks
4. Tasks marked `complete` stay complete (unless `--redo` flag used)

## Implementation Details

### Class: StateAuditRunner

Main audit orchestration class with methods:

- `validate_state_file()`: Validates file structure
- `test_state_transitions()`: Tests state machine integrity
- `test_resume_functionality()`: Tests resume capability
- `test_corruption_resistance()`: Tests recovery mechanisms
- `generate_report()`: Creates comprehensive report

### Helper Methods

- `_get_phase_tasks()`: Extracts task list from state file
- `_select_resume_points()`: Chooses evenly distributed test points
- `_backup_state()`: Saves current state before tests
- `_restore_state()`: Restores original state after tests
- `_mark_tasks_complete_before()`: Sets up test scenarios
- `_run_phase_with_resume()`: Executes phase with resume flag

### Test Strategies

**Validation**: Static analysis of state file structure

**Transitions**: Logical checks on state consistency

**Resume**: Dynamic execution with various resume points

**Corruption**: Destructive tests with automatic recovery

## Known Limitations

1. **Invalid JSON Recovery**: Currently fails because task-state.sh doesn't have explicit invalid JSON recovery (by design - relies on atomic writes)

2. **Resume Tests**: Requires Phase 0 to be configured (uses it as test phase because it's fastest)

3. **Execution Tests**: `--skip-exec` flag skips resume tests which require actual phase execution

4. **State Backup**: Tests create backups in `test/.state_backup/` - cleaned automatically

## Integration Points

### With Pipeline

State audit validates the same state file used by:
- `lib/task-state.sh`: Core state management library
- `phases/*/run.sh`: Phase runners that track state
- `main.py`: CLI that reads state for status display

### With Other Audits

Complements:
- `memory_audit_runner.py`: Validates persistent memory
- `uat_runner.py`: End-to-end phase execution
- `script_audit_runner.py`: Bash script linting

### With Dashboard

State file is read by:
- `tasks-dashboard/server.js`: Real-time task monitoring
- Task status indicators in web UI

## Troubleshooting

### "State file not found"

No state file exists yet. Run Phase 0 to initialize:

```bash
python main.py run 0
```

### "Invalid JSON"

State file is corrupted. Reset and reinitialize:

```bash
rm .claude/task-state.json
python main.py run 0
```

### "Resume tests failed"

Phase 0 tasks not found or changed. Update test expectations:

```bash
python test/state_audit_runner.py --skip-exec  # Skip resume tests
```

### "Permission denied"

State file or directory not writable:

```bash
chmod -R u+w .claude/
```

## Contributing

When modifying state management:

1. Run state audit before changes: `python test/state_audit_runner.py`
2. Make your changes to `lib/task-state.sh`
3. Run state audit after changes: `python test/state_audit_runner.py`
4. Compare reports to ensure no regressions
5. Update test expectations if behavior intentionally changed

## Future Enhancements

Potential improvements:

- [ ] Add concurrency tests (multiple phases running)
- [ ] Test cross-phase navigation (--pipeline-reset)
- [ ] Validate state file size limits
- [ ] Test state migration across versions
- [ ] Add performance benchmarks (state reads/writes)
- [ ] Test state file locking mechanisms
- [ ] Validate state backups and snapshots

## See Also

- `lib/task-state.sh`: Core state management implementation
- `CLAUDE.md`: State management documentation
- `test/UAT-QUICK-START.md`: End-to-end testing guide
- `test/TEST-FRAMEWORK-COMPLETE.md`: Full test framework overview
