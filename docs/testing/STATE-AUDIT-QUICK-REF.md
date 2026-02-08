# State Audit Runner - Quick Reference

## One-Line Commands

```bash
# Fast validation (recommended)
python test/state_audit_runner.py --skip-exec

# Full audit including resume tests
python test/state_audit_runner.py

# Verbose output
python test/state_audit_runner.py --verbose

# Test more resume points
python test/state_audit_runner.py --resume-tests 10
```

## What It Tests

| Category | Tests | Pass Threshold |
|----------|-------|----------------|
| State File Validation | 6 | File exists, valid JSON, schema, phases, tasks, timestamps |
| State Transitions | 4 | No stuck tasks, timestamps, no orphans, consistency |
| Resume Functionality | 3-5 | Skip completed, execute resume, execute subsequent |
| Corruption Resistance | 4 | Invalid JSON, missing file, partial data, corrupted tasks |

## Expected Results

### Healthy State
```
✓ State file found
✓ Valid JSON format
✓ All required keys present
✓ All phase IDs valid
✓ All tasks valid
✓ All timestamps valid ISO format
✓ No tasks stuck in in_progress
✓ All completed tasks have timestamps
✓ No orphaned phase entries
✓ Phase completion status consistent

Pass Rate: 93-100% (13-14/14 tests)
```

### Common Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| State file not found | "✗ State file not found" | Run Phase 0: `python main.py run 0` |
| Invalid JSON | "✗ Invalid JSON" | Reset state: `rm .claude/task-state.json` |
| Stuck tasks | "✗ Found N stuck tasks" | Run `--redo` to clear: `./phases/N-*/run.sh --redo` |
| Missing timestamps | "✗ Found N tasks without timestamps" | State corruption - reset and rerun |

## Report Locations

- **Console**: Real-time colored output
- **JSON**: `test/reports/state-audit-YYYYMMDD-HHMMSS.json`

## Quick Diagnostics

```bash
# Check if state file exists
ls -lh .claude/task-state.json

# Validate JSON
cat .claude/task-state.json | jq .

# See phase status
cat .claude/task-state.json | jq .phases

# Check current phase
cat .claude/task-state.json | jq .current_phase

# List all tasks
cat .claude/task-state.json | jq '.phases[].tasks | keys'

# Find stuck tasks
cat .claude/task-state.json | jq '.phases[].tasks | to_entries[] | select(.value.status == "in_progress")'
```

## Integration

```bash
# Run before commits
git add . && python test/state_audit_runner.py --skip-exec && git commit

# CI/CD pipeline
python test/state_audit_runner.py --skip-exec || exit 1

# Debug user issues
python test/state_audit_runner.py --skip-exec --verbose > debug.log
```

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--verbose` | off | Show detailed output |
| `--skip-exec` | off | Skip resume tests (validation only) |
| `--resume-tests N` | 5 | Number of resume points to test |

## Exit Codes

Always exits `0` - check JSON report for actual results:

```bash
python test/state_audit_runner.py --skip-exec
total_passed=$(jq .summary.total_passed test/reports/state-audit-*.json | tail -1)
echo "Tests passed: $total_passed"
```

## State File Schema

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

## Task Status Values

- `pending`: Not started
- `in_progress`: Currently executing
- `complete`: Finished successfully
- `failed`: Encountered error

## Performance

- **Validation only**: ~0.25 seconds (14 tests)
- **With resume tests**: ~60 seconds (19 tests, includes Phase 0 execution)
- **Report size**: 1-2 KB JSON

## Files Created

| File | Purpose |
|------|---------|
| `state_audit_runner.py` | Main audit tool (950 lines) |
| `STATE-AUDIT-README.md` | Full documentation (466 lines) |
| `STATE-AUDIT-SUMMARY.md` | Implementation summary (276 lines) |
| `STATE-AUDIT-QUICK-REF.md` | This file (quick reference) |

## Common Workflows

### Pre-Release Check
```bash
python test/state_audit_runner.py --skip-exec
# Expected: 93-100% pass rate
```

### Debug State Issues
```bash
python test/state_audit_runner.py --skip-exec --verbose
cat test/reports/state-audit-*.json | jq .validation.issues
```

### Test Resume Functionality
```bash
python test/state_audit_runner.py --resume-tests 10
# Tests 10 different resume points
```

### CI/CD Integration
```bash
python test/state_audit_runner.py --skip-exec
jq -e '.summary.total_passed >= 13' test/reports/state-audit-*.json > /dev/null
```

## See Also

- **Full Docs**: `test/STATE-AUDIT-README.md`
- **Implementation**: `test/STATE-AUDIT-SUMMARY.md`
- **State Library**: `lib/task-state.sh`
- **Main Docs**: `CLAUDE.md` (state management section)
