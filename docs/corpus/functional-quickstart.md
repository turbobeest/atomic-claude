# Functional Test Runner - Quick Start

Run functional tests with 90%+ code coverage for any phase.

## Install Dependencies

```bash
pip install pytest pytest-cov
```

## Run Tests

```bash
# Run functional tests for Phase 0
python test/runners/functional_runner.py 0

# Run for Phase 1
python test/runners/functional_runner.py 1

# Custom coverage target (95%)
python test/runners/functional_runner.py 0 --coverage-target 0.95
```

## Check Results

```bash
# View JSON report
cat reports/functional/phase_00_functional.json | python -m json.tool

# Open HTML coverage report
open reports/functional/htmlcov_phase00/index.html
```

## Add New Tests

1. Create input file:
```bash
cd test/fixtures/phase00/functional/happy_path
cat > input_my_test.json << 'EOF'
{
  "test_name": "my_test",
  "description": "Test description",
  "inputs": {...}
}
EOF
```

2. Create expected output:
```bash
cat > expected_my_test.json << 'EOF'
{
  "outputs": {...},
  "exit_code": 0
}
EOF
```

3. Run tests:
```bash
python test/runners/functional_runner.py 0
```

## Coverage Reports

The runner generates:
- `phase_NN_functional.json` - Test results
- `coverage_phaseNN.json` - Coverage data
- `htmlcov_phaseNN/` - Interactive HTML report

View coverage:
```bash
open reports/functional/htmlcov_phase00/index.html
```

Coverage shows:
- ✅ Green lines = covered
- ❌ Red lines = not covered
- ⚠️ Yellow = partially covered branches

## Troubleshooting

**Tests fail:**
```bash
# Check test logs
cat reports/functional/phase_00_functional.json

# Run with verbose output
python test/runners/functional_runner.py 0 -v
```

**Coverage too low:**
1. Open HTML report: `open reports/functional/htmlcov_phase00/index.html`
2. Find red (uncovered) lines
3. Add test cases to cover those lines
4. Re-run tests

**Mock LLM not working:**
- Verify `"mock_llm": true` in `test/phase_configs/phase_NN_tests.json`
- Check mock responses in `test/mocks/mock_llm.py`

## See Also

- [Full Documentation](functional-runner.md)
- [Writing Test Fixtures](../fixtures/phase00/functional/README.md)
- [Mock LLM Usage](../../test/mocks/mock_llm.py)
