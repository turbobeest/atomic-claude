# Atomic Claude 2.0 - Test Suite

Automated testing framework for validating phase functionality **without consuming LLM tokens**.

---

## Quick Start

Run tests in a **separate terminal window** (not in Claude Code session):

```bash
# From atomic-claude2 root
chmod +x test/run_tests.sh
./test/run_tests.sh
```

---

## What It Does

✅ **Tests Phase 00 (Setup)**
- Validates all 6 tasks can execute
- Verifies configuration loading
- Checks state tracking
- Confirms output file creation

✅ **Tests Phase 01 (Discovery)**
- Validates Phase 00 → 01 transition
- Tests entry validation
- Verifies state persistence
- Checks closeout handling

✅ **Mock Mode**
- No actual LLM API calls
- No token consumption
- Pre-canned responses
- Fast execution (~30 seconds per phase)

---

## Usage

### Run All Tests

```bash
./test/run_tests.sh
```

### Test Specific Phase

```bash
./test/run_tests.sh --phase 0    # Phase 00 only
./test/run_tests.sh --phase 1    # Phase 01 only
```

### Verbose Output

```bash
./test/run_tests.sh --verbose
```

### Clean Before Running

```bash
./test/run_tests.sh --clean
```

### Python Direct

```bash
python3 test/test_runner.py
python3 test/test_runner.py --phase 0 --verbose
```

---

## How It Works

### Mock LLM Responses

All `atomic_invoke()` calls are intercepted and replaced with pre-canned responses:

```python
# Instead of calling Claude/Bedrock:
response = call_actual_llm(prompt)

# Mock mode returns:
response = get_mock_response(task_description)
```

**Mock responses include:**
- Config extraction (Phase 00 Task 002)
- Default success responses for other tasks
- Properly formatted JSON/Markdown

### Test Environment

Tests run in isolated environment:

```
.test-env/
├── .outputs/        # Phase outputs
├── .state/          # Task state tracking
└── .logs/           # Execution logs

initialization/
└── setup.md         # Minimal test config
```

### Environment Variables

```bash
ATOMIC_MOCK_MODE=1              # Enable mock mode
ATOMIC_NETWORK_MODE=cui         # Restrict network
ATOMIC_OFFLINE_MODE=true        # Offline mode
```

---

## Directory Structure

```
test/
├── run_tests.sh                # Main test wrapper (run this!)
├── test_runner.py              # Python test orchestrator
├── README.md                   # This file
│
├── mocks/                      # Mock implementations
│   ├── __init__.py
│   ├── mock_llm.py             # Mock LLM responses
│   └── mock_atomic.sh          # Mock atomic_invoke (future)
│
├── fixtures/                   # Test data
│   └── minimal_setup.md        # Minimal setup config
│
└── test_phases/                # Phase-specific tests (future)
    ├── test_phase00.py
    └── test_phase01.py
```

---

## Adding New Tests

### 1. Add Mock Response

Edit `test/mocks/mock_llm.py`:

```python
MOCK_RESPONSES["New Task"] = {
    "field": "value",
    "data": {...}
}
```

### 2. Add Phase Test Module

Create `test/test_phases/test_phaseNN.py`:

```python
def test_phase_NN_task_NNN():
    """Test Phase NN Task NNN."""
    # Test logic here
    pass
```

### 3. Update Test Runner

Edit `test/test_runner.py` to include new phase:

```python
phases_to_test = [0, 1, 2]  # Add phase 2
```

---

## Verification

After tests run, verify:

### 1. Output Files Created

```bash
ls -la .test-env/.outputs/0-setup/
# Should show:
# - project-config.json
# - secrets.json
# - closeout.json
```

### 2. State Tracking

```bash
cat .test-env/.state/task-state.json
# Should show completed tasks
```

### 3. Test Report

```bash
cat test/test-report.json
# Shows pass/fail status
```

---

## Mock vs Real Execution

| Aspect | Mock Mode | Real Mode |
|--------|-----------|-----------|
| LLM Calls | Pre-canned responses | Actual API calls |
| Token Usage | 0 tokens | ~1000+ tokens per phase |
| Speed | ~30 sec/phase | ~5-10 min/phase |
| Cost | Free | ~$0.50-$2.00 per phase |
| User Input | Auto-enter | Interactive prompts |
| Network | Disabled | Enabled |

---

## Troubleshooting

### Tests Hang

- Check for interactive prompts not being auto-answered
- Use `--verbose` to see where it stops
- Ctrl+C to cancel

### Import Errors

```bash
# Ensure you're in repo root
cd /path/to/atomic-claude2

# Run from correct location
./test/run_tests.sh
```

### Permission Denied

```bash
chmod +x test/run_tests.sh
```

### Python Version

Tests require Python 3.8+:

```bash
python3 --version
```

---

## UAT Runner (`uat_runner.py`)

**Purpose**: User Acceptance Testing for full pipeline validation

**Usage**:
```bash
# Test all phases (0-9)
python test/uat_runner.py

# Test specific phase
python test/uat_runner.py --phase 2

# Verbose output
python test/uat_runner.py --verbose
```

**Features**:
- ✅ Tests complete 10-phase pipeline (70 tasks)
- ✅ Uses UAT mode (bypasses LLM calls for speed)
- ✅ Validates outputs and closeout files
- ✅ Verifies task completion tracking
- ✅ ~5-8 minutes for full pipeline

---

## Memory Audit Runner (`memory_audit_runner.py`)

**Purpose**: Validate claude-mem (memory persistence) integration across all tasks

**Usage**:
```bash
# Audit all phases
python test/memory_audit_runner.py

# Audit specific phase
python test/memory_audit_runner.py --phase 2

# Verbose output
python test/memory_audit_runner.py --verbose
```

**Features**:
- ✅ Tests memory artifact creation in `.state/memory/`
- ✅ Validates memory saves/recalls
- ✅ Checks memory file integrity
- ✅ Tracks per-phase memory usage
- ✅ Generates detailed JSON reports in `test/reports/`
- ✅ ~5-8 minutes for full audit

**Documentation**: See `docs/MEMORY-AUDIT-TESTING.md` for detailed guide

**Example Output**:
```
  Memory Analysis:
    ✓ Created 12 memory artifacts
    ✓ Detected 8 memory saves
    ✓ Detected 3 memory recalls

  Memory Integrity Checks:
    ✓ Phase 02: 12/12 artifacts valid

  Overall Assessment:
    ✅ EXCELLENT - All phases use memory correctly
```

---

## Script Quality Audit Runner (`script_audit_runner.py`)

**Purpose**: Comprehensive validation of bash and Python code quality across the repository

**Usage**:
```bash
# Full audit (bash + Python)
python test/script_audit_runner.py

# Bash scripts only
python test/script_audit_runner.py --bash-only

# Python scripts only
python test/script_audit_runner.py --python-only

# Generate JSON report
python test/script_audit_runner.py --json-report
```

**Features**:

**Bash Script Validation**:
- ✅ Syntax check with `bash -n`
- ✅ ShellCheck integration (if available)
- ✅ Shebang validation (`#!/usr/bin/env bash`)
- ✅ Execute permissions check
- ✅ Antipattern detection:
  - Unquoted variables (`$var` vs `"$var"`)
  - Missing error handling (`set -euo pipefail`)
  - Dangerous `rm -rf` with variables
  - `cd` without error checking

**Python Script Validation**:
- ✅ Syntax check with `python -m py_compile`
- ✅ Shebang validation for executable scripts
- ✅ Import resolution checking
- ✅ Debug statement detection (print, pdb, breakpoint)
- ✅ TODO/FIXME comment tracking

**Output**:
- ✅ Color-coded console output
- ✅ Detailed issue reports with line numbers
- ✅ Severity levels: critical, warning, info
- ✅ Actionable suggestions for fixes
- ✅ JSON reports saved to `test/reports/`

**Example Output**:
```
================================================================================
AUDIT SUMMARY
================================================================================

Status: FAILED

Files Checked:
  Total:  163
  Bash:   97
  Python: 66
  Passed: 149
  Failed: 14

Issues Found:
  Total:    5897
  Critical: 58
  Warnings: 4999

Execution Time: 5.23s
================================================================================
```

**Exit Codes**:
- `0`: All scripts valid (no critical issues)
- `1`: Critical issues found

**Files Audited**:
- `phases/*/tasks/*.sh` - Phase task scripts
- `phases/*/orchestrator*.py` - Python orchestrators
- `lib/*.sh` - Core bash libraries
- `core/*.py` - Core Python modules
- `test/*.py` - Test scripts

**Installation Requirements**:
```bash
# Optional: Install shellcheck for enhanced bash validation
brew install shellcheck  # macOS
apt install shellcheck   # Ubuntu/Debian
```

---

## Regression Test Runner (`regression_runner.py`)

**Purpose**: Validate that all documented bug patterns from `docs/BUG-PATTERNS.md` remain fixed

**Usage**:
```bash
# Quick start
./test/run-regression-tests.sh

# Direct Python execution
python3 test/regression_runner.py

# Specify root directory
python3 test/regression_runner.py --root /path/to/atomic-claude2
```

**Features**:
- ✅ Tests 10 critical bug patterns
- ✅ Validates bash syntax across all scripts
- ✅ Checks for arithmetic operations without `|| true`
- ✅ Verifies UAT bypasses in interactive tasks
- ✅ Validates library sourcing and execution blocks
- ✅ Tests closeout file creation
- ✅ Checks dashboard port configuration
- ✅ Validates documentation completeness
- ✅ Fast execution (5-15 seconds)
- ✅ No LLM calls required

**Documentation**: See `test/REGRESSION-TEST-GUIDE.md` for detailed usage

**Example Output**:
```
================================================================================
REGRESSION TEST SUITE - Bug Pattern Validation
================================================================================

TEST: Arithmetic with set -e
✅ Arithmetic with set -e: PASSED

TEST: Bash Syntax Validation
✅ Bash Syntax Validation: PASSED

REGRESSION TEST SUMMARY
────────────────────────────────────────────────────────────────────────────────
Total Tests:   9
✅ Passed:     9
❌ Failed:     0

Pass Rate:     100.0%

✅ ALL REGRESSION TESTS PASSED
```

**Bug Patterns Tested**:
1. Arithmetic with `set -e` - `((var++))` without `|| true`
2. Corrupted bash syntax - Invalid conditionals, mismatched brackets
3. Missing closeout files - Phase orchestrators without closeout creation
4. Missing library sourcing - Task scripts without `source atomic.sh`
5. Missing execution blocks - Scripts without execution guard
6. UAT input handling - Interactive tasks without UAT bypass
7. macOS command compatibility - GNU-specific flags
8. Interactive conversation loops - Multi-turn dialogues in UAT
9. Dashboard port configuration - Port 5174 consistency
10. Documentation completeness - Missing docs, broken links

**Reports Generated**:
- JSON: `test/reports/regression-YYYYMMDD-HHMMSS.json`
- Markdown: `test/reports/regression-YYYYMMDD-HHMMSS.md`

---

## Future Enhancements

### Planned Features

- [x] Phase 02-09 test coverage (UAT runner)
- [x] Integration test suite (UAT runner + Memory audit)
- [ ] Unit tests for core modules
- [ ] Performance benchmarks
- [ ] CI/CD integration
- [ ] Test coverage reports
- [ ] Parallel test execution
- [ ] Interactive mode testing

### Mock Improvements

- [ ] More realistic LLM responses
- [ ] Response variation/randomness
- [ ] Error scenario testing
- [ ] Network failure simulation
- [ ] Timeout simulation

---

## Contributing

To add tests for new phases:

1. Copy `test/fixtures/minimal_setup.md` pattern
2. Add mock responses to `test/mocks/mock_llm.py`
3. Create phase test module in `test/test_phases/`
4. Update `test_runner.py` phases list
5. Run `./test/run_tests.sh` to validate

---

## Test Report Format

```json
{
  "timestamp": "2026-02-04T11:00:00",
  "duration_seconds": 45.2,
  "total": 2,
  "passed": 2,
  "failed": 0,
  "results": [
    {
      "phase": 0,
      "success": true,
      "returncode": 0
    },
    {
      "phase": 1,
      "success": true,
      "returncode": 0
    }
  ]
}
```

---

**Status:** Phase 00 & 01 tests ready ✅

Run `./test/run_tests.sh` to validate!
