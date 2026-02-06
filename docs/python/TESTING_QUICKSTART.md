# Testing Quick Start

## One-Line Commands

```bash
# Install dependencies
pip install -r tests/requirements.txt

# Run all tests
./run_tests.sh

# Run with coverage
pytest tests/ -v --cov=lib --cov-report=term-missing

# Run specific module tests
pytest tests/ -k "atomic" -v      # atomic.py tests
pytest tests/ -k "provider" -v    # provider.py tests
pytest tests/ -k "memory" -v      # memory.py tests
pytest tests/ -k "phase" -v       # phase.py tests
pytest tests/ -k "task_state" -v  # task_state.py tests
```

## Test Suite Overview

```
tests/test_integration.py - 20+ comprehensive tests

TestAtomic (8 tests)
├── Output functions (step, success, error, warn, info)
├── JSON escaping
├── Temp file management
├── State management
├── File validation
└── JSON extraction

TestProvider (6 tests)
├── Server configuration
├── Provider availability
├── Chain resolution
└── Task-based routing

TestMemory (5 tests)
├── Initialization
├── Persistence checks
├── Head tracking
├── Checkpoints
└── Backtrack detection

TestPhase (4 tests)
├── State management
├── Phase lifecycle
├── Completion tracking
└── Snapshots

TestTaskState (10 tests)
├── Status tracking
├── Serialization
├── State transitions
├── Skip logic
├── Resume support
└── Phase completion

TestIntegration (3 tests)
├── Full phase workflow
├── Memory integration
└── Resume workflow
```

## Common Test Patterns

```bash
# Run all tests with coverage
./run_tests.sh

# Verbose mode
./run_tests.sh -vv

# HTML coverage report
./run_tests.sh --html-coverage

# Parallel execution
./run_tests.sh --parallel

# Run specific test class
pytest tests/test_integration.py::TestAtomic -v

# Run specific test method
pytest tests/test_integration.py::TestAtomic::test_atomic_step_output -v

# Debug mode (show prints)
pytest tests/ -v -s

# Debug on failure
pytest tests/ --pdb

# Re-run last failed
pytest tests/ --lf

# CI/CD mode
./run_tests.sh --junit --html-coverage
```

## Test Files

- `test_integration.py` - Main test suite
- `conftest.py` - Shared fixtures
- `requirements.txt` - Dependencies
- `README.md` - Full documentation

## Fixtures Available

- `temp_dir` - Isolated temporary directory
- `atomic_env` - Test environment variables
- `reset_globals` - Clear module state (auto)
- `isolate_environment` - Isolate env vars (auto)

## Coverage Metrics

Target coverage goals:
- Line coverage: >80%
- Branch coverage: >70%
- Function coverage: >90%

## Test Characteristics

- **Fast**: Unit tests < 1s, integration < 5s
- **Isolated**: Each test in clean environment
- **Parallel-safe**: Can run concurrently
- **Well-documented**: Clear docstrings

## Quick Examples

### Run specific module tests
```bash
./run_tests.sh -k "atomic"
```

### Generate HTML coverage
```bash
./run_tests.sh --html-coverage
open htmlcov/index.html
```

### Debug failing test
```bash
pytest tests/test_integration.py::TestAtomic::test_specific -vv -s --pdb
```

### Run in parallel
```bash
./run_tests.sh --parallel
```

## Exit Codes

- `0` - All tests passed
- `1` - Test failures
- `2` - Test collection errors
- `3` - Internal errors

## Troubleshooting

**Import errors:**
```bash
# Ensure lib directory is in path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/lib"
```

**Missing pytest:**
```bash
pip install -r tests/requirements.txt
```

**Permission denied:**
```bash
chmod +x run_tests.sh
```

**Cleanup temp files:**
```bash
rm -rf /tmp/atomic-test-*
```

## CI/CD Integration

```yaml
# GitHub Actions example
- run: pip install -r tests/requirements.txt
- run: pytest tests/ -v --cov=lib --cov-report=xml --junit-xml=test-results.xml
```

## Documentation

- `tests/README.md` - Full documentation
- `TEST_IMPLEMENTATION_SUMMARY.md` - Detailed summary
- Test docstrings - What each test does

## Support

For detailed information, see:
- `tests/README.md` - Complete testing guide
- `TEST_IMPLEMENTATION_SUMMARY.md` - Implementation details
- `test_integration.py` - Test source code
