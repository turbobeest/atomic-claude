# Testing LLM Providers

Comprehensive guide to testing LLM providers in atomic-claude.

## Test Categories

### Unit Tests
- **Location**: `tests/unit/test_*_provider.py`
- **Purpose**: Test individual provider methods with mocked HTTP/API calls
- **Speed**: Fast (<1s per test)
- **Coverage**: All methods, error paths, edge cases

### Integration Tests
- **Location**: `tests/integration/test_all_providers.py`
- **Purpose**: Test multiple providers together, compare behavior
- **Speed**: Fast (uses mocks)
- **Coverage**: Provider consistency, fallback chains, concurrent requests

### E2E Tests
- **Location**: `tests/e2e/test_llm_e2e.py`
- **Purpose**: Real API tests with actual LLMs
- **Speed**: Slow (seconds to minutes)
- **Coverage**: Full workflows, real response validation
- **Marker**: `@pytest.mark.requires_llm`

### Performance Tests
- **Location**: `tests/performance/test_llm_performance.py`
- **Purpose**: Measure latency, throughput, resource usage
- **Marker**: `@pytest.mark.performance`

## Running Tests

```bash
# All tests (unit + integration)
pytest tests/

# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Performance tests
pytest tests/performance/ -m performance

# E2E tests (requires LLM access)
ATOMIC_TEST_MODE=0 pytest tests/e2e/ -m requires_llm

# Specific provider tests
pytest tests/unit/test_ollama_provider.py -v

# With coverage
pytest --cov=core/llm --cov-report=html
```

## Mock Provider

Use `MockProvider` for testing without real APIs:

```python
from dev.tests.mocks.mock_llm import MockProvider

# Basic usage
provider = MockProvider()
response = provider.invoke("Test")
assert response.content == "Mock response"

# Configure responses
provider.set_response("Calculate 2+2", "The answer is 4")
response = provider.invoke("Calculate 2+2")
assert "4" in response.content

# Simulate errors
provider.set_error_mode("timeout")
with pytest.raises(TimeoutError):
    provider.invoke("Test")

# Simulate latency
provider = MockProvider({"latency_ms": 100})
start = time.time()
response = provider.invoke("Test")
assert time.time() - start >= 0.1

# Track calls
provider.reset_calls()
provider.invoke("Call 1")
provider.invoke("Call 2")
assert provider.get_call_count() == 2
```

## Test Fixtures

Located in `tests/fixtures/llm/`:

- **sample_prompts.json**: Test prompts by category
- **expected_responses.json**: Response validation patterns
- **error_scenarios.json**: Error test cases
- **performance_benchmarks.json**: Performance baselines

## Writing Provider Tests

### Unit Test Template

```python
import pytest
from unittest.mock import MagicMock, patch
from core.llm.yourprovider import YourProvider

@pytest.fixture
def provider():
    return YourProvider({"config": "value"})

def test_invoke_success(provider):
    with patch('urllib.request.urlopen') as mock:
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"response": "test"}'
        mock.return_value.__enter__.return_value = mock_response

        response = provider.invoke("test")
        assert response.content

def test_invoke_error(provider):
    with patch('urllib.request.urlopen') as mock:
        mock.side_effect = Exception("API Error")

        with pytest.raises(APIError):
            provider.invoke("test")
```

## Test Best Practices

1. **Mock External Calls**: Never make real API calls in unit tests
2. **Use Fixtures**: Reuse common setup with pytest fixtures
3. **Test Error Paths**: Cover all exception types
4. **Verify Tracking**: Check token usage, latency, metadata
5. **Parametrize**: Use `@pytest.mark.parametrize` for variations
6. **Mark Slow Tests**: Use `@pytest.mark.slow` for tests >1s
7. **Skip When Needed**: Skip E2E tests without credentials

## Coverage Goals

- **Line Coverage**: 95%+
- **Branch Coverage**: 90%+
- **All Methods**: 100%
- **Error Paths**: All exceptions tested

Run coverage:
```bash
pytest --cov=core/llm --cov-report=term --cov-report=html
open htmlcov/index.html
```
