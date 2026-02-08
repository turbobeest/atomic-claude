# Test Infrastructure - atomic-claude2

Complete test infrastructure for validating the atomic-claude2 refactor.

## Overview

This directory contains three types of test runners for validating phase implementations:

1. **Continuity Test Runner** - Validates seamless task execution (COMPLETE)
2. **UAT Runner** - User experience validation (TBD - Agent 3)
3. **Functional Test Runner** - Code coverage validation (TBD - Agent 4)

## Directory Structure

```
tests/
├── README.md                    # This file
├── conftest.py                  # Pytest configuration & fixtures
├── __init__.py                  # Package marker
│
├── runners/                     # Test runners
│   ├── __init__.py
│   ├── continuity_runner.py    # Continuity test runner (COMPLETE)
│   ├── example_usage.py        # Example usage scenarios
│   ├── uat_runner.py           # UAT runner (TBD)
│   └── functional_runner.py    # Functional test runner (TBD)
│
├── phase_configs/               # Phase test configurations
│   ├── README.md
│   ├── __init__.py
│   ├── phase_00_tests.json     # Phase 0 configuration
│   ├── phase_01_tests.json     # Phase 1 configuration (TBD)
│   └── ...
│
├── fixtures/                    # Test fixtures & inputs
│   ├── __init__.py
│   ├── phase00/                # Phase 0 fixtures
│   │   ├── README.md
│   │   ├── continuity_inputs.txt
│   │   └── ...
│   └── ...
│
├── unit/                        # Unit tests
│   ├── __init__.py
│   ├── test_continuity_runner.py
│   └── ...
│
├── integration/                 # Integration tests (TBD)
├── e2e/                        # End-to-end tests (TBD)
└── reports/                    # Generated test reports
```

## Quick Start

### Continuity Test

Test that all tasks in a phase execute without crashes:

```bash
# Run continuity test for Phase 0
python tests/runners/continuity_runner.py 0 --mock

# View help
python tests/runners/continuity_runner.py --help
```

### Run Unit Tests

```bash
# All unit tests
python -m pytest tests/unit/ -v

# Specific test file
python -m pytest tests/unit/test_continuity_runner.py -v

# With coverage
python -m pytest tests/unit/ --cov=tests.runners --cov-report=html
```

## Test Runners

### 1. Continuity Test Runner (COMPLETE)

**Purpose:** Validate seamless task-to-task execution without terminal errors.

**What it tests:**
- All tasks execute sequentially without crashes
- No unhandled exceptions or exit code failures
- State transitions are valid
- No resource leaks (processes, file handles)
- Proper cleanup after completion

**Usage:**
```bash
python tests/runners/continuity_runner.py 0 --mock
```

**Documentation:** `docs/testing/continuity-runner.md`

### 2. UAT Runner (TBD - Agent 3)

**Purpose:** User experience validation (TUI/UX sniff test).

**What it will test:**
- CLI output formatting and readability
- Menu logic and navigation
- Wording clarity and grammar
- Interactive flows (Q&A, prompts, progress)
- Human review of UX quality

**Documentation:** `docs/testing/uat-runner.md` (TBD)

### 3. Functional Test Runner (TBD - Agent 4)

**Purpose:** Validate task behavior with 90%+ code coverage.

**What it will test:**
- All code paths (happy path, edge cases, errors)
- Output correctness against expected results
- State persistence and recovery
- Multiple input scenarios per task

**Documentation:** `docs/testing/functional-runner.md` (TBD)

## Configuration Files

Each phase has a test configuration file in `phase_configs/`:

```json
{
  "phase": "0-setup",
  "name": "Phase 0: Setup",
  "tasks": ["001", "002", "003", ...],
  "continuity": {
    "inputs": "fixtures/phase00/continuity_inputs.txt",
    "timeout_per_task": 120
  },
  "uat": {
    "scenarios": ["guided", "quick", "document"],
    "human_review": true
  },
  "functional": {
    "fixtures": "fixtures/phase00/",
    "coverage_target": 0.90,
    "scenarios": ["happy_path", "edge_cases", "error_handling"]
  }
}
```

See `phase_configs/README.md` for full documentation.

## Fixtures

Test fixtures provide prescribed inputs for non-interactive testing:

- `fixtures/phase00/continuity_inputs.txt` - Inputs for Phase 0 continuity test
- `fixtures/phase00/config_samples/` - Sample configuration files
- `fixtures/phase00/mock_responses/` - Mock LLM responses

See fixture README files for details.

## Pytest Configuration

`conftest.py` provides shared fixtures:

**Path fixtures:**
- `atomic_root` - Root directory
- `test_root` - Tests directory

**Temporary directories:**
- `temp_dir` - Isolated temp directory
- `temp_state_dir` - Temporary state directory
- `temp_output_dir` - Temporary outputs directory
- `temp_log_dir` - Temporary logs directory

**State fixtures:**
- `clean_state` - Empty state dict
- `sample_state` - Pre-populated state
- `state_file` - State file with data

**Mock fixtures:**
- `mock_llm_response` - Sample LLM response
- `mock_llm_json_response` - Sample JSON response
- `mock_llm_environment` - Mock environment setup

**Configuration fixtures:**
- `sample_config` - Sample configuration
- `config_file` - Config file with data

**Test script fixtures:**
- `sample_task_script` - Working task script
- `failing_task_script` - Failing task script

**Custom markers:**
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.slow` - Slow tests
- `@pytest.mark.requires_llm` - Tests requiring real LLM

## Running Tests

### All Tests

```bash
python -m pytest tests/
```

### By Type

```bash
# Unit tests only
python -m pytest tests/unit/ -v

# Integration tests only (when available)
python -m pytest tests/integration/ -v

# End-to-end tests only (when available)
python -m pytest tests/e2e/ -v
```

### By Marker

```bash
# Unit tests
python -m pytest -m unit

# Integration tests
python -m pytest -m integration

# Slow tests
python -m pytest -m slow

# Skip LLM tests
python -m pytest -m "not requires_llm"
```

### With Coverage

```bash
# Generate coverage report
python -m pytest tests/unit/ --cov=tests.runners --cov-report=html

# View report
open htmlcov/index.html
```

## Phase Implementation Workflow

When implementing a new phase:

### 1. Create Configuration

```bash
cp tests/phase_configs/phase_00_tests.json \
   tests/phase_configs/phase_NN_tests.json
```

Edit to match your phase tasks.

### 2. Create Fixtures

```bash
mkdir -p tests/fixtures/phaseNN
# Add continuity_inputs.txt and other fixtures
```

### 3. Implement Phase

Implement the phase tasks and orchestrator.

### 4. Run Continuity Test

```bash
python tests/runners/continuity_runner.py N --mock
```

Fix any failures.

### 5. Run UAT (when available)

```bash
python tests/runners/uat_runner.py N
```

Validate UX quality.

### 6. Run Functional Tests (when available)

```bash
python tests/runners/functional_runner.py N
```

Verify 90%+ coverage.

### 7. All Pass?

If all three tests pass, proceed to next phase.

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  continuity:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run continuity tests
        run: |
          for phase in 0 1 2; do
            python tests/runners/continuity_runner.py $phase --mock
          done
```

## Documentation

- `docs/testing/continuity-runner.md` - Continuity test documentation (complete)
- `docs/testing/QUICK-START.md` - Quick start guide
- `docs/testing/PHASE-1-DELIVERABLES.md` - Phase 1 deliverables
- `docs/testing/SUMMARY.md` - Summary document
- `tests/phase_configs/README.md` - Configuration format
- `tests/fixtures/phase00/README.md` - Phase 0 fixtures
- `REFACTOR-PLAN.md` - Overall testing strategy

## Current Status

### Phase 1: Foundation

- ✅ **Continuity Test Runner** - Complete (Agent 2)
- ⏳ **UAT Runner** - TBD (Agent 3)
- ⏳ **Functional Test Runner** - TBD (Agent 4)

### Test Coverage

- **Unit tests:** 20 tests, all passing
- **Integration tests:** TBD
- **E2E tests:** TBD

### Phase Configurations

- ✅ Phase 0 configuration complete
- ⏳ Phase 1-9 configurations TBD

## Examples

See `tests/runners/example_usage.py` for complete examples of:

1. Basic continuity test
2. Continuity test with custom validation
3. Saving and analyzing reports
4. Testing multiple phases in sequence

Run examples:

```bash
python tests/runners/example_usage.py
```

## Troubleshooting

### Tests Hang

Increase timeout in phase config:

```json
"continuity": {
  "timeout_per_task": 300
}
```

### Import Errors

Ensure you're running from the atomic-claude2 root:

```bash
cd /path/to/atomic-claude2
python tests/runners/continuity_runner.py 0
```

### Missing Dependencies

Install test dependencies:

```bash
pip install pytest pytest-cov psutil
```

### Mock Mode Not Working

Check environment variables:

```bash
export ATOMIC_TEST_MODE=1
export ATOMIC_MOCK_LLM=1
```

## Support

For questions or issues:

1. Check documentation in `docs/testing/`
2. Review example usage: `tests/runners/example_usage.py`
3. Run unit tests: `python -m pytest tests/unit/ -v`
4. Consult `REFACTOR-PLAN.md` for overall strategy

---

**Test Infrastructure Status:** Phase 1 (Continuity Runner) Complete

**Created:** 2026-02-06
**Agent:** Agent 2
**Phase:** Phase 1: Foundation
