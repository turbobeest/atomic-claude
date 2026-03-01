# Anthropic Provider

The Anthropic provider implements the `BaseLLMProvider` interface for accessing Claude models via the official Anthropic API.

## Overview

**Module:** `core/llm/anthropic.py`
**Class:** `AnthropicProvider`
**Provider Name:** `anthropic`

## Features

- All Claude models (Opus, Sonnet, Haiku)
- Message API with system prompts
- Streaming support
- Prompt caching (optional)
- Comprehensive error handling
- Automatic retry with exponential backoff
- Token counting via API

## Installation

```bash
pip install anthropic
```

## Configuration

### Environment Variables

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

### Config Dictionary

```python
config = {
    "api_key": "your-api-key",           # Optional if ANTHROPIC_API_KEY is set
    "default_model": "claude-sonnet-4-5", # Default model
    "timeout": 300,                       # Request timeout in seconds
    "max_retries": 3,                     # Max retry attempts
    "enable_caching": False,              # Enable prompt caching
}

provider = AnthropicProvider(config=config)
```

## Supported Models

### Current Models

- `claude-opus-4-6` - Most capable, highest cost
- `claude-opus-4-5`
- `claude-opus-4`
- `claude-sonnet-4-5` - Balanced performance (default)
- `claude-sonnet-4`
- `claude-haiku-4` - Fast, lowest cost
- `claude-3-5-sonnet-20241022`
- `claude-3-5-sonnet-20240620`
- `claude-3-opus-20240229`
- `claude-3-sonnet-20240229`
- `claude-3-haiku-20240307`

### Tier Names (Abstract)

You can use tier names instead of full model IDs:

- `opus` → `claude-opus-4-6`
- `sonnet` → `claude-sonnet-4-5`
- `haiku` → `claude-haiku-4`

## Usage Examples

### Basic Invocation

```python
from core.llm.anthropic import AnthropicProvider

provider = AnthropicProvider()

response = provider.invoke(
    prompt="Explain quantum computing in simple terms.",
    system_prompt="You are a helpful science teacher.",
    model="sonnet",
    max_tokens=500,
    temperature=0.7
)

print(response.content)
print(f"Used {response.usage.total_tokens} tokens")
```

### Streaming

```python
provider = AnthropicProvider()

stream = provider.stream(
    prompt="Write a haiku about programming.",
    model="haiku",
    max_tokens=100
)

for chunk in stream:
    print(chunk, end="", flush=True)
```

### With Prompt Caching

```python
config = {
    "enable_caching": True,
}

provider = AnthropicProvider(config=config)

# System prompt will be cached (useful for repeated calls)
response = provider.invoke(
    prompt="Analyze this code: ...",
    system_prompt="You are a code reviewer with expertise in Python...",
    model="sonnet"
)

print(f"Cache read tokens: {response.usage.cache_read_tokens}")
print(f"Cache write tokens: {response.usage.cache_write_tokens}")
```

### Model Validation

```python
provider = AnthropicProvider()

# Check if model is supported
if provider.validate_model("opus"):
    print("Opus is supported")

# Get supported models
models = provider.get_supported_models()
print(f"Available models: {len(models)}")
```

### Token Counting

```python
provider = AnthropicProvider()

text = "This is a test prompt for token counting."
token_count = provider.get_token_count(text)

print(f"Estimated tokens: {token_count}")
```

### Health Check

```python
provider = AnthropicProvider()

status = provider.health_check()

if status == HealthStatus.HEALTHY:
    print("Anthropic API is healthy")
elif status == HealthStatus.DEGRADED:
    print("Anthropic API is degraded")
else:
    print("Anthropic API is unavailable")
```

## Error Handling

The provider maps Anthropic SDK exceptions to standard LLM errors:

### AuthenticationError

```python
try:
    response = provider.invoke(prompt="Test")
except AuthenticationError as e:
    print(f"Invalid API key: {e}")
```

### RateLimitError

```python
try:
    response = provider.invoke(prompt="Test")
except RateLimitError as e:
    print(f"Rate limited. Retry after: {e.retry_after} seconds")
    # Provider will automatically retry with exponential backoff
```

### TimeoutError

```python
try:
    response = provider.invoke(prompt="Test", timeout=10)
except TimeoutError as e:
    print(f"Request timed out: {e}")
```

### APIError

```python
try:
    response = provider.invoke(prompt="Test")
except APIError as e:
    print(f"API error: {e}")
    print(f"Error code: {e.error_code}")
    print(f"Retryable: {e.retryable}")
```

### ModelNotFoundError

```python
try:
    response = provider.invoke(prompt="Test", model="invalid-model")
except ModelNotFoundError as e:
    print(f"Model not found: {e}")
```

## Response Format

The `LLMResponse` object contains:

```python
response = provider.invoke(prompt="Test")

# Content
print(response.content)  # Generated text

# Model info
print(response.model)     # "claude-sonnet-4-5"
print(response.provider)  # "anthropic"

# Usage statistics
print(response.usage.input_tokens)      # Input token count
print(response.usage.output_tokens)     # Output token count
print(response.usage.cache_read_tokens) # Cached tokens read
print(response.usage.cache_write_tokens) # Cached tokens written
print(response.usage.total_tokens)      # Total tokens

# Metadata
print(response.finish_reason)  # "end_turn", "max_tokens", etc.
print(response.latency_ms)     # Request latency in milliseconds
print(response.timestamp)      # Response timestamp
print(response.metadata)       # Additional metadata (id, type, role)
```

## Advanced Configuration

### Custom Timeout

```python
# Per-request timeout
response = provider.invoke(
    prompt="Long analysis task...",
    timeout=600  # 10 minutes
)
```

### Custom Retry Behavior

```python
config = {
    "max_retries": 5,  # More retries for flaky networks
}

provider = AnthropicProvider(config=config)
```

### Additional API Parameters

```python
# Pass any additional Anthropic API parameters
response = provider.invoke(
    prompt="Test",
    top_p=0.9,
    top_k=50,
    stop_sequences=["END"],
)
```

## Performance Considerations

### Latency

- Typical invoke latency: 1-5 seconds (depends on model and output length)
- Streaming first token: < 1 second
- Error handling overhead: < 10ms

### Token Limits

| Model | Max Input Tokens | Max Output Tokens |
|-------|-----------------|-------------------|
| Opus  | 200,000         | 4,096             |
| Sonnet| 200,000         | 4,096             |
| Haiku | 200,000         | 4,096             |

### Cost Optimization

1. Use `haiku` for simple tasks (cheapest)
2. Use `sonnet` for balanced performance (default)
3. Use `opus` only for complex reasoning
4. Enable prompt caching for repeated system prompts
5. Set appropriate `max_tokens` to avoid waste

## Testing

### Unit Tests

```bash
# Run Anthropic provider unit tests
pytest tests/unit/test_anthropic_provider.py -v
```

### Integration Tests

```bash
# Run with real API (requires ANTHROPIC_API_KEY)
RUN_LLM_TESTS=1 pytest tests/integration/test_providers_integration.py::TestAnthropicIntegration -v
```

### Mocking for Tests

```python
from unittest.mock import Mock, patch

with patch("core.llm.anthropic.Anthropic") as mock_client_class:
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    # Mock response
    mock_response = Mock()
    mock_response.content = [Mock(text="Test response")]
    mock_response.usage = Mock(input_tokens=10, output_tokens=20)
    mock_client.messages.create.return_value = mock_response

    # Test your code
    provider = AnthropicProvider(config={"api_key": "test"})
    response = provider.invoke(prompt="Test")
```

## Troubleshooting

### API Key Issues

```
AuthenticationError: Anthropic authentication failed
```

**Solution:** Set `ANTHROPIC_API_KEY` environment variable or pass `api_key` in config.

### Rate Limiting

```
RateLimitError: Anthropic rate limit exceeded
```

**Solution:** The provider automatically retries with exponential backoff. You can increase `max_retries` in config.

### Model Not Found

```
ModelNotFoundError: Model not found: invalid-model
```

**Solution:** Use `provider.get_supported_models()` to see available models, or use tier names (`opus`, `sonnet`, `haiku`).

### Connection Timeouts

```
TimeoutError: Anthropic request timed out
```

**Solution:** Increase timeout in config or per-request, or check network connectivity.

## Reference

- **Anthropic API Docs:** https://docs.anthropic.com/
- **SDK Reference:** https://github.com/anthropics/anthropic-sdk-python
- **Base Implementation:** `/Users/jamesterbeest/dev/atomic-claude/lib/atomic.sh` lines 700-1200

## See Also

- [Base Provider Interface](base-provider.md)
- [Bedrock Provider](bedrock-provider.md)
- [Provider Router](provider-router.md)
