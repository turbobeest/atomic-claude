# Functional Test Runner

The Functional Test Runner validates task behavior with comprehensive code coverage (90%+ target).

## Overview

The functional test runner executes tasks with simulated inputs, tests all code paths, measures coverage, and validates outputs against expected results. It's designed to ensure every function and branch in the codebase is tested.

## What Functional Testing Covers

### Code Coverage
- **Line Coverage:** Every line of code executed at least once
- **Branch Coverage:** Every conditional branch tested (if/else, loops)
- **Function Coverage:** Every function called at least once
- **Target:** 90%+ coverage across all metrics

### Test Scenarios
1. **Happy Path:** Standard success scenarios
2. **Edge Cases:** Boundary conditions and unusual inputs
3. **Error Handling:** Expected failures and recovery

### Validation
- Output correctness (compare with expected results)
- State persistence (task state saved correctly)
- Error messages (proper error handling)
- File generation (required files created)
- Data integrity (JSON structure, field validation)

## Architecture

```
FunctionalTestRunner
├── load_phase_config()          # Load test configuration
├── run_phase_functional_tests() # Main test execution
│   ├── _run_scenario()         # Run single scenario
│   │   └── _execute_test()     # Execute single test case
│   ├── _run_pytest_with_coverage() # Run pytest with coverage
│   └── _print_summary()        # Print results
└── Coverage Report Generation
```

## Usage

### Basic Usage

```bash
# Run functional tests for Phase 0
python test/runners/functional_runner.py 0

# Run for Phase 1
python test/runners/functional_runner.py 1
```

### Advanced Usage

```bash
# Custom coverage target (95%)
python test/runners/functional_runner.py 0 --coverage-target 0.95

# Use custom config file
python test/runners/functional_runner.py 0 --config my_config.json
```

### From Python

```python
from test.runners.functional_runner import FunctionalTestRunner

# Create runner
runner = FunctionalTestRunner()

# Run tests with custom config
config = {
    "fixtures": "test/fixtures/phase00/functional/",
    "coverage_target": 0.90,
    "scenarios": ["happy_path", "edge_cases", "error_handling"],
    "mock_llm": True
}

results = runner.run_phase_functional_tests(phase_num=0, config=config)

# Check results
if results["scenarios_failed"] == 0:
    print("All tests passed!")
else:
    print(f"{results['scenarios_failed']} scenarios failed")
```

## Test Configuration

Each phase has a configuration file: `test/phase_configs/phase_NN_tests.json`

```json
{
  "phase": "0-setup",
  "functional": {
    "fixtures": "test/fixtures/phase00/functional/",
    "coverage_target": 0.90,
    "scenarios": ["happy_path", "edge_cases", "error_handling"],
    "mock_llm": true,
    "parallel_execution": false,
    "timeout_per_test": 30
  }
}
```

### Configuration Fields

- **fixtures:** Path to test fixtures directory
- **coverage_target:** Minimum coverage required (0.0-1.0)
- **scenarios:** List of test scenarios to run
- **mock_llm:** Use mock LLM provider (default: true)
- **parallel_execution:** Run tests in parallel (default: false)
- **timeout_per_test:** Timeout per test in seconds (default: 30)

## Writing Test Scenarios

### Directory Structure

```
test/fixtures/phase00/functional/
├── happy_path/
│   ├── input_test1.json
│   ├── expected_test1.json
│   ├── input_test2.json
│   └── expected_test2.json
├── edge_cases/
│   ├── input_boundary.json
│   └── expected_boundary.json
└── error_handling/
    ├── input_invalid.json
    └── expected_error_invalid.json
```

### Input File Format

```json
{
  "test_name": "quick_mode_defaults",
  "description": "Test Phase 00 with quick mode",
  "mode": "quick",
  "inputs": {
    "project_name": "test-project",
    "description": "Test description"
  },
  "environment": {
    "ANTHROPIC_API_KEY": "test-key"
  },
  "mocks": {
    "llm_enabled": false,
    "user_input": []
  }
}
```

### Expected Output Format

```json
{
  "outputs": {
    "config.json": {
      "project": {
        "name": "test-project"
      }
    },
    "closeout.json": {
      "status": "complete"
    }
  },
  "state": {
    "tasks_completed": ["001", "002"]
  },
  "exit_code": 0,
  "validation": {
    "required_files": [".outputs/0-setup/config.json"],
    "required_fields": {"config.json": ["project"]}
  }
}
```

## Coverage Requirements

### Minimum Thresholds
- **Line Coverage:** 90%+
- **Branch Coverage:** 85%+ (recommended)
- **Function Coverage:** 95%+ (recommended)

### Coverage Reports

Reports are generated in `reports/functional/`:

```
reports/functional/
├── phase_00_functional.json      # Test results JSON
├── coverage_phase00.json         # Coverage data JSON
└── htmlcov_phase00/             # HTML coverage report
    └── index.html               # Browse coverage
```

### Viewing HTML Coverage Report

```bash
# Open in browser (macOS)
open reports/functional/htmlcov_phase00/index.html

# Open in browser (Linux)
xdg-open reports/functional/htmlcov_phase00/index.html
```

The HTML report shows:
- Line-by-line coverage highlighting
- Uncovered lines in red
- Partially covered branches in yellow
- Coverage percentages per file

## Mock Usage

### Mock LLM Provider

The mock LLM provider simulates LLM responses without consuming tokens:

```python
from test.mocks.mock_llm import MockLLMProvider

# Create mock with delay simulation
mock = MockLLMProvider(
    delay_min=0.1,
    delay_max=0.5,
    error_rate=0.0,
    scenario="default"
)

# Add custom response
mock.add_response_template(
    "agent selection",
    {"agents": ["agent-001", "agent-002"]}
)

# Use mock
success = mock.invoke(
    prompt="Select agents for project",
    output_path=Path("/tmp/output.json"),
    description="agent selection"
)

# Check invocations
print(f"Invoked {mock.get_invocation_count()} times")
```

### Error Injection

Test error handling by injecting errors:

```python
# Force specific error
mock = MockLLMProvider()
success = mock.invoke(
    prompt="...",
    output_path=Path("/tmp/output.json"),
    description="test",
    force_error="rate_limit"  # Simulate rate limit error
)

# Random error injection
mock = MockLLMProvider(error_rate=0.1)  # 10% error rate
```

### Available Error Scenarios
- `rate_limit` - Rate limit exceeded
- `timeout` - Request timeout
- `invalid_api_key` - Authentication error
- `server_error` - Internal server error

## Adding New Test Cases

### 1. Create Input File

```bash
cd test/fixtures/phase00/functional/happy_path
cat > input_new_test.json << 'EOF'
{
  "test_name": "new_test",
  "description": "Description of new test",
  "inputs": {...}
}
EOF
```

### 2. Create Expected Output

```bash
cat > expected_new_test.json << 'EOF'
{
  "outputs": {...},
  "exit_code": 0
}
EOF
```

### 3. Run Tests

```bash
python test/runners/functional_runner.py 0
```

### 4. Check Coverage

If coverage drops below 90%, add more test cases to cover:
- Uncovered lines (check HTML report)
- Untested branches (if/else, loops)
- Edge cases and error paths

## Integration with pytest

The runner uses pytest for coverage measurement:

```bash
# Run pytest directly (alternative to runner)
pytest phases/phase_00/ --cov=phases/phase_00 --cov-report=html
```

### pytest Configuration

Create `pytest.ini` in project root:

```ini
[pytest]
testpaths = test
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --cov-report=term-missing
    --cov-report=html
    --cov-branch
```

## Best Practices

### Test Design
1. **One Test, One Assertion:** Each test validates one behavior
2. **Descriptive Names:** Use clear, descriptive test names
3. **Independent Tests:** Tests should not depend on each other
4. **Fast Execution:** Use mocks to keep tests fast (<1s per test)
5. **Repeatable:** Tests should produce same results every run

### Coverage Goals
1. **Start High:** Begin with 90%+ coverage from day one
2. **Maintain Coverage:** Never let coverage drop below threshold
3. **Test Edge Cases:** Cover boundary conditions and errors
4. **Test Branches:** Ensure all if/else paths are tested
5. **Test Recovery:** Validate error handling and recovery

### Fixture Management
1. **Organize by Scenario:** Group related fixtures
2. **Version Control:** Check fixtures into git
3. **Document Intent:** Add README explaining each fixture
4. **Keep Updated:** Update fixtures when code changes
5. **Share Fixtures:** Reuse fixtures across tests when appropriate

## Troubleshooting

### Coverage Below Target

**Problem:** Coverage is 85% but target is 90%

**Solution:**
1. Check HTML coverage report: `open reports/functional/htmlcov_phase00/index.html`
2. Find red (uncovered) lines
3. Add test cases to cover those lines
4. Look for untested error paths and branches

### Tests Timing Out

**Problem:** Tests hang or timeout

**Solution:**
1. Check for infinite loops
2. Increase timeout: `--timeout-per-test 60`
3. Use mocks to avoid slow operations
4. Check for deadlocks in concurrent code

### Mock Not Working

**Problem:** Mock LLM not being used

**Solution:**
1. Verify `"mock_llm": true` in config
2. Check mock is properly injected
3. Verify task code uses mock provider
4. Check for hardcoded LLM calls bypassing mock

### Flaky Tests

**Problem:** Tests pass sometimes, fail sometimes

**Solution:**
1. Remove timing dependencies
2. Fix test order dependencies
3. Use fixed random seeds
4. Mock external dependencies
5. Clean up state between tests

## FAQ

**Q: Why 90% coverage target?**
A: 90% provides high confidence while being achievable. Some code (error recovery, edge cases) is hard to test.

**Q: Should I test private functions?**
A: Test private functions indirectly through public API. Only test private functions directly if they have complex logic.

**Q: How do I exclude code from coverage?**
A: Use `# pragma: no cover` comment:
```python
if __name__ == "__main__":  # pragma: no cover
    main()
```

**Q: Can I run tests in parallel?**
A: Yes, set `"parallel_execution": true` in config. Ensure tests are independent.

**Q: How long should tests take?**
A: Aim for <5 minutes for full phase functional tests. Use mocks to keep tests fast.

## See Also

- [UAT Runner Documentation](../../test/UAT-QUICK-START.md)
- [Continuity Runner Documentation](../../test/README.md)
- [Test Framework Overview](../../test/TEST-FRAMEWORK-COMPLETE.md)
- [Mock LLM Provider](../../test/mocks/mock_llm.py)
