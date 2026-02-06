# ATOMIC CLAUDE Python Tests

Comprehensive integration test suite for the Python implementation of ATOMIC CLAUDE.

## Test Coverage

### Module Coverage

- **atomic.py**: Core invocation primitives, output functions, state management
- **provider.py**: Multi-provider routing, availability detection, model selection
- **memory.py**: Persistent memory layer, checkpoints, backtrack handling
- **phase.py**: Phase lifecycle management, task execution
- **task_state.py**: Task state tracking, resumability, state transitions

### Test Categories

1. **Unit Tests**: Individual function/method testing
2. **Integration Tests**: Multi-module workflow testing
3. **End-to-End Tests**: Complete phase execution workflows

## Running Tests

### Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-mock pytest-cov
```

### Run All Tests

```bash
# From project root
cd /Users/jamesterbeest/dev/atomic-claude/atomic-claude-python
pytest tests/ -v

# With coverage report
pytest tests/ -v --cov=lib --cov-report=html
```

### Run Specific Test Files

```bash
# Integration tests only
pytest tests/test_integration.py -v

# Specific test class
pytest tests/test_integration.py::TestAtomic -v

# Specific test method
pytest tests/test_integration.py::TestAtomic::test_atomic_step_output -v
```

### Run Tests by Pattern

```bash
# All atomic tests
pytest tests/ -k "atomic" -v

# All provider tests
pytest tests/ -k "provider" -v

# All memory tests
pytest tests/ -k "memory" -v
```

## Test Structure

```
tests/
├── __init__.py              # Test package marker
├── conftest.py              # Shared pytest fixtures
├── test_integration.py      # Main integration test suite
└── README.md                # This file
```

## Test Fixtures

### Available Fixtures

- `temp_dir`: Temporary directory for test isolation (auto-cleanup)
- `atomic_env`: Test environment with ATOMIC_* variables set
- `reset_globals`: Resets module-level globals between tests
- `isolate_environment`: Isolates environment variables per test

### Example Usage

```python
def test_example(temp_dir, atomic_env):
    """Test with isolated temp directory and environment."""
    # temp_dir is Path object to temporary directory
    test_file = temp_dir / "test.json"

    # atomic_env contains ATOMIC_ROOT, ATOMIC_STATE_DIR, etc.
    assert atomic_env["ATOMIC_ROOT"] == str(temp_dir)
```

## Writing New Tests

### Test Naming Conventions

- Test files: `test_*.py`
- Test classes: `Test*` (e.g., `TestAtomic`, `TestProvider`)
- Test methods: `test_*` (e.g., `test_atomic_step_output`)

### Example Test

```python
class TestNewModule:
    """Test suite for new_module.py."""

    def test_basic_functionality(self, temp_dir):
        """Test basic functionality with description."""
        # Arrange
        test_input = "test"

        # Act
        result = some_function(test_input)

        # Assert
        assert result == expected_output

    def test_error_handling(self):
        """Test error handling."""
        with pytest.raises(ValueError):
            some_function(invalid_input)
```

## Debugging Tests

### Run with Print Output

```bash
pytest tests/ -v -s
```

### Drop into Debugger on Failure

```bash
pytest tests/ --pdb
```

### Run Last Failed Tests

```bash
pytest tests/ --lf
```

### Verbose Output

```bash
pytest tests/ -vv
```

## Coverage Reports

### Generate HTML Coverage Report

```bash
pytest tests/ --cov=lib --cov-report=html
open htmlcov/index.html
```

### Generate Terminal Coverage Report

```bash
pytest tests/ --cov=lib --cov-report=term-missing
```

## Continuous Integration

These tests are designed to run in CI/CD pipelines:

```bash
# Example CI command
pytest tests/ -v --cov=lib --cov-report=xml --junit-xml=test-results.xml
```

## Test Data

Tests use temporary directories for all file operations. No permanent test data files are required.

## Mocking

Tests use `unittest.mock` and `pytest-mock` for mocking external dependencies:

- Subprocess calls
- Network requests
- File system operations (when needed)
- Time-dependent operations

## Performance

### Test Execution Time

Expected test execution times:
- Unit tests: < 1s per test
- Integration tests: < 5s per test
- Full suite: < 30s

### Parallel Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel
pytest tests/ -n auto
```

## Troubleshooting

### Import Errors

If you encounter import errors, ensure the lib directory is in your path:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
```

### Environment Issues

Tests automatically isolate environment variables. If issues persist, check `conftest.py` fixtures.

### Cleanup Issues

Temporary directories are automatically cleaned up. If cleanup fails, manually remove:

```bash
rm -rf /tmp/atomic-test-*
```

## Contributing

When adding new functionality:

1. Write tests first (TDD approach)
2. Ensure tests cover success and failure cases
3. Mock external dependencies
4. Use descriptive test names
5. Add docstrings explaining what's being tested
6. Verify all tests pass before committing

```bash
# Pre-commit checklist
pytest tests/ -v                    # All tests pass
pytest tests/ --cov=lib            # Coverage acceptable
pylint lib tests                    # Linting passes
black lib tests                     # Code formatted
```
