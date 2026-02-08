# Continuity Test Runner - Quick Start

**Get started with continuity testing in 5 minutes.**

## Installation

No installation needed - the runner is part of the atomic-claude2 repository.

## Quick Test

Run continuity test for Phase 0:

```bash
cd /path/to/atomic-claude2
python tests/runners/continuity_runner.py 0 --mock
```

Expected output:

```
================================================================================
CONTINUITY TEST: Phase 0: Setup
================================================================================

  Testing Task 001: Mode selection...
    ✓ Mode selection (2.3s)
  Testing Task 002: Config collection...
    ✓ Config collection (5.1s)
  ...

✓ Overall Result: PASSED
```

## Common Commands

### Run Phase Test

```bash
# Phase 0
python tests/runners/continuity_runner.py 0

# Phase 1
python tests/runners/continuity_runner.py 1

# Any phase (0-9)
python tests/runners/continuity_runner.py N
```

### Use Mock Mode (Faster)

```bash
python tests/runners/continuity_runner.py 0 --mock
```

Mock mode:
- No real LLM API calls
- Faster execution
- Good for development/CI

### Custom Configuration

```bash
python tests/runners/continuity_runner.py 0 \
    --config tests/phase_configs/custom_config.json
```

### Save Reports to Custom Location

```bash
python tests/runners/continuity_runner.py 0 \
    --output-dir /tmp/test-reports
```

## Interpreting Results

### Success

```
✓ Overall Result: PASSED
```

Means:
- All tasks completed (exit code 0)
- State transitions valid
- No resource leaks
- Cleanup successful

### Failure

```
✗ Overall Result: FAILED

Errors:
  • Task 003 failed: Exit code 1: Configuration validation failed
```

**Action:** Debug the failing task, check error logs.

## Quick Fixes

### Task Hangs

If a task hangs:

```bash
# Increase timeout
# Edit tests/phase_configs/phase_00_tests.json
"timeout_per_task": 300  # 5 minutes
```

### Interactive Prompt Blocks Test

If test blocks on interactive prompt:

```bash
# Use mock mode
python tests/runners/continuity_runner.py 0 --mock
```

### Resource Leak Warning

If you see: `⚠️ Warning: 3 orphaned processes`

Add cleanup to task script:

```bash
# In task script
cleanup() {
    kill $CHILD_PID 2>/dev/null
}
trap cleanup EXIT
```

## Unit Tests

Run unit tests:

```bash
python -m pytest tests/unit/test_continuity_runner.py -v
```

Expected: 20 tests pass

## Example Usage

See complete examples:

```bash
python tests/runners/example_usage.py
```

This runs 4 different example scenarios showing various use cases.

## Next Steps

1. ✓ Run continuity test for Phase 0
2. Review report: `tests/reports/continuity_0-setup_*.json`
3. If failed, debug and fix
4. Run UAT test (when available)
5. Run functional test (when available)

## Full Documentation

For complete documentation, see:

- `docs/testing/continuity-runner.md` - Full documentation
- `tests/phase_configs/README.md` - Configuration format
- `docs/testing/PHASE-1-DELIVERABLES.md` - Complete deliverables

## Support

Questions? Check:
1. Full documentation (above)
2. Example usage: `tests/runners/example_usage.py`
3. Unit tests: `tests/unit/test_continuity_runner.py`
4. Refactor plan: `REFACTOR-PLAN.md`

---

**Quick Start Complete!** You're ready to run continuity tests.
