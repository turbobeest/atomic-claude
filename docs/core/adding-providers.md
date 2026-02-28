# Adding New LLM Providers

Guide to implementing a new LLM provider for atomic-claude.

## Overview

All providers implement `BaseLLMProvider` interface with:
- `invoke()` - Synchronous invocation
- `stream()` - Streaming response
- `validate_model()` - Model validation
- `get_token_count()` - Token estimation
- `health_check()` - Service health

## Step-by-Step Guide

### 1. Create Provider File

```python
# core/llm/myprovider.py

from typing import Dict, Generator, Optional, Any, List
from .base import (
    BaseLLMProvider,
    LLMResponse,
    TokenUsage,
    HealthStatus,
    APIError,
    TimeoutError,
)

class MyProvider(BaseLLMProvider):
    """Your provider description."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.provider_name = "myprovider"
        # Load config
        self.api_key = self.config.get("api_key")
        self.base_url = self.config.get("base_url", "https://api.example.com")

    def invoke(self, prompt, system_prompt=None, model=None,
               max_tokens=4096, temperature=1.0, timeout=300, **kwargs):
        # Implement API call
        # Return LLMResponse
        pass

    def stream(self, prompt, system_prompt=None, model=None,
               max_tokens=4096, temperature=1.0, **kwargs):
        # Implement streaming
        # Yield chunks
        pass

    def validate_model(self, model_name: str) -> bool:
        # Check if model exists
        pass

    def get_token_count(self, text: str, model=None) -> int:
        # Estimate tokens
        pass

    def health_check(self) -> HealthStatus:
        # Check service availability
        pass
```

### 2. Update __init__.py

```python
# core/llm/__init__.py

from .myprovider import MyProvider

__all__ = [
    # ... existing
    "MyProvider",
]
```

### 3. Write Tests

```python
# tests/unit/test_myprovider.py

import pytest
from unittest.mock import patch, MagicMock
from core.llm.myprovider import MyProvider

@pytest.fixture
def provider():
    return MyProvider({"api_key": "test_key"})

def test_invoke_success(provider):
    with patch('requests.post') as mock_post:
        mock_post.return_value.json.return_value = {"response": "test"}
        response = provider.invoke("test prompt")
        assert response.content

def test_health_check(provider):
    status = provider.health_check()
    assert status in [HealthStatus.HEALTHY, HealthStatus.UNAVAILABLE]
```

### 4. Add Documentation

Create `docs/core/myprovider-provider.md` with:
- Overview
- Installation
- Usage examples
- Configuration
- Error handling
- Best practices

### 5. Integration

Add to provider router and configuration system.

## Implementation Checklist

- [ ] Create provider class inheriting BaseLLMProvider
- [ ] Implement all required methods
- [ ] Handle errors with proper exception types
- [ ] Calculate token usage
- [ ] Report latency
- [ ] Support streaming (if available)
- [ ] Write 20+ unit tests
- [ ] Add integration tests
- [ ] Document usage
- [ ] Update __init__.py
- [ ] Test with Continuity Runner
- [ ] Test with Functional Runner

## Best Practices

1. **Error Handling**: Map API errors to standard exceptions
2. **Timeouts**: Respect timeout parameter
3. **Retries**: Implement retry logic for transient failures
4. **Logging**: Log requests for debugging
5. **Token Counting**: Accurate token estimation
6. **Metadata**: Include useful debug info
7. **Streaming**: Implement if API supports it

## Example: Full Provider

See `core/llm/ollama.py` for complete reference implementation.
