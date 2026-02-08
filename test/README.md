# Test Framework - Quick Reference

This directory contains test scripts for validating atomic-claude2 functionality.

---

## Important: Tool Development Mode

Since atomic-claude2 is a tool repository (not a project being built WITH the tool), you must set the `ATOMIC_TOOL_DEVELOPMENT` environment variable to disable the forcing function:

```bash
export ATOMIC_TOOL_DEVELOPMENT="true"
```

**All test scripts in this directory automatically set this variable.**

---

## Available Test Scripts

### 1. Continuity Test (Full Pipeline)

**Script**: `continuity-test-scenario1.sh`

**What it does**:
- Executes all 10 phases (Phase 0-9)
- Validates state persistence
- Checks output generation
- Uses UAT mode (automated, no user input)

**How to run**:
```bash
./test/continuity-test-scenario1.sh
```

**Duration**: 1-2 hours (depending on LLM API speed)

**Expected output**:
```
✓ Phase 0 complete (9 tasks)
✓ Phase 1 complete (10 tasks)
...
✓ Phase 9 complete (6 tasks)

Total: 74 tasks completed
```

---

### 2. UX/UI Evaluation (Interactive)

**Script**: `uxui-evaluation.sh`

**What it does**:
- Walks through user interaction touchpoints
- Collects ratings (1-5 scale)
- Documents feedback
- Generates evaluation report

**How to run**:
```bash
./test/uxui-evaluation.sh
```

**Duration**: 30 minutes

**Output**: `test/uxui-evaluation-results.txt`

---

### 3. Comprehensive Test Runner

**Script**: `run-comprehensive-tests.sh`

**What it does**:
- Runs all test phases
- Unit, integration, E2E, continuity, UX/UI
- Interactive prompts
- Summary report

**How to run**:
```bash
./test/run-comprehensive-tests.sh
```

**Duration**: 3+ hours

---

## Running Tests Manually

If you want to run tests manually (not using the scripts):

### Option 1: Set Environment Variable

```bash
export ATOMIC_TOOL_DEVELOPMENT="true"
python main.py run 0
```

### Option 2: Temporarily Disable Forcing Function

Edit `orchestration/pre_task_validation.py` and set:
```python
ENABLE_VALIDATION = False
```

---

## Unit Tests (pytest)

Unit tests don't need the forcing function disabled:

```bash
cd /Users/jamesterbeest/dev/atomic-claude2
export PYTHONPATH=$(pwd):$PYTHONPATH

# Run all unit tests
python -m pytest tests/unit/ -v

# Run specific test file
python -m pytest tests/unit/test_core_state.py -v

# Run with coverage
python -m pytest tests/unit/ --cov=core --cov=phases --cov-report=html
```

---

## Test Fixtures

Test fixtures are in `tests/conftest.py`:
- `temp_dir` - Temporary directory (auto-cleanup)
- `temp_state_dir` - State directory
- `temp_output_dir` - Output directory
- `mock_llm_response` - Mock LLM responses
- `sample_config` - Sample configuration

---

## Troubleshooting

### Issue: "TASK BLOCKED - FIX VIOLATIONS FIRST"

**Cause**: Forcing function is enabled and detecting files

**Solution**: Ensure `ATOMIC_TOOL_DEVELOPMENT=true` is set
```bash
export ATOMIC_TOOL_DEVELOPMENT="true"
python main.py run 0
```

### Issue: "No module named 'core'"

**Cause**: PYTHONPATH not set

**Solution**:
```bash
export PYTHONPATH=$(pwd):$PYTHONPATH
```

### Issue: Tests hanging or timing out

**Cause**: LLM API calls taking too long

**Solutions**:
1. Use UAT mode: `export ATOMIC_UAT_MODE=true`
2. Increase timeout: `export ATOMIC_TASK_TIMEOUT=600`
3. Use local LLM: Set Ollama as provider

---

## Test Environment Variables

Set these before running tests:

```bash
# Required
export PYTHONPATH=$(pwd):$PYTHONPATH
export ATOMIC_TOOL_DEVELOPMENT="true"

# Optional
export ATOMIC_UAT_MODE="true"           # Automated mode (no prompts)
export ATOMIC_TASK_TIMEOUT="600"        # Task timeout in seconds
export ATOMIC_ROOT="$(pwd)"             # Project root
export ATOMIC_STATE_DIR="$(pwd)/.state" # State directory
export ATOMIC_OUTPUT_DIR="$(pwd)/.outputs" # Output directory
```

---

## Test Results

After running tests, results are in:

- **State**: `.state/task-state.json`
- **Outputs**: `.outputs/0-setup/`, `.outputs/1-discovery/`, etc.
- **UX/UI Results**: `test/uxui-evaluation-results.txt`
- **Coverage**: `htmlcov/index.html` (after pytest --cov)
- **Continuity Test**: `/tmp/atomic-claude2-test-<timestamp>/`

---

## Quick Start

```bash
cd /Users/jamesterbeest/dev/atomic-claude2

# Run continuity test (recommended first)
./test/continuity-test-scenario1.sh

# Or run unit tests
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m pytest tests/unit/ -v

# Or run UX/UI evaluation
./test/uxui-evaluation.sh
```

---

## Documentation

- **Test Plan**: `docs/CONTINUITY-UXUI-TEST-PLAN.md`
- **Test Status**: `docs/TEST-STATUS.md`
- **Test Summary**: `docs/TESTING-SUMMARY.md`
- **This File**: `test/README.md`

---

**Last Updated**: 2026-02-07
**Status**: All scripts ready to run
