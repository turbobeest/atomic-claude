# Ollama Provider Documentation

## Overview

The Ollama provider enables local LLM execution without API costs or network dependencies. It supports streaming, automatic model pulling, and GPU acceleration through the Ollama REST API.

## Features

- **Local Execution**: Run models on your own hardware
- **No API Costs**: No per-token charges
- **Offline Capable**: Works without internet connection
- **Streaming Support**: Real-time token-by-token output
- **Auto Model Pulling**: Automatically downloads missing models
- **GPU Acceleration**: Leverages CUDA/Metal when available
- **Multiple Models**: Support for Llama 2, Mistral, CodeLlama, and more

## Installation

### 1. Install Ollama

```bash
# macOS/Linux
curl https://ollama.ai/install.sh | sh

# Or download from https://ollama.ai/download
```

### 2. Start Ollama Service

```bash
ollama serve
```

### 3. Pull a Model

```bash
ollama pull llama2        # 7B general purpose
ollama pull mistral       # 7B, fast and capable
ollama pull codellama     # 7B, optimized for code
ollama pull llama2:13b    # 13B, more capable
```

## Usage

### Basic Invocation

```python
from core.llm.ollama import OllamaProvider

# Create provider
provider = OllamaProvider({
    "host": "http://localhost:11434",
    "default_model": "llama2",
    "timeout": 600,
    "auto_pull": True
})

# Invoke model
response = provider.invoke(
    "Explain quantum computing in simple terms",
    temperature=0.7,
    max_tokens=2048
)

print(response.content)
print(f"Tokens: {response.usage.total_tokens}")
print(f"Latency: {response.latency_ms}ms")
```

### With System Prompt

```python
response = provider.invoke(
    "Write a Python factorial function",
    system_prompt="You are an expert Python developer. Write clean, documented code.",
    model="codellama"
)
```

### Streaming

```python
print("Response: ", end="", flush=True)
for chunk in provider.stream("Tell me a story about a robot"):
    print(chunk, end="", flush=True)
print()
```

### Model Management

```python
# List available models
models = provider.list_models()
print(f"Available models: {models}")

# Check if model exists
if not provider.validate_model("mistral"):
    print("Pulling mistral model...")
    provider.pull_model("mistral")

# Use the model
response = provider.invoke("Test prompt", model="mistral")
```

### Health Checking

```python
from core.llm.base import HealthStatus

status = provider.health_check()

if status == HealthStatus.HEALTHY:
    print("Ollama is ready")
elif status == HealthStatus.DEGRADED:
    print("Ollama is running but no models available")
else:
    print("Ollama service is not running")
```

## Configuration

### Provider Config

```python
config = {
    "host": "http://localhost:11434",  # Ollama server URL
    "default_model": "llama2",         # Default model
    "timeout": 600,                    # Request timeout (seconds)
    "auto_pull": True                  # Auto-download missing models
}

provider = OllamaProvider(config)
```

### Model Parameters

```python
response = provider.invoke(
    "Your prompt",
    model="llama2",           # Model name
    max_tokens=4096,          # Maximum tokens to generate
    temperature=0.7,          # Sampling temperature (0.0-1.0)
    num_ctx=8192,            # Context window size
    top_p=0.9,               # Nucleus sampling threshold
    top_k=40                 # Top-K sampling
)
```

## Supported Models

### General Purpose
- `llama2` - Meta's Llama 2 7B
- `llama2:13b` - Llama 2 13B (more capable)
- `mistral` - Mistral 7B (fast, high quality)

### Code Generation
- `codellama` - Code Llama 7B
- `codellama:13b` - Code Llama 13B
- `deepseek-coder` - DeepSeek Coder

### Specialized
- `llama2-uncensored` - Uncensored variant
- `neural-chat` - Conversational model
- `starling-lm` - Instruction-following

See full list: https://ollama.ai/library

## Performance

### Expected Latency

| Model | Size | CPU (M1) | GPU (RTX 3090) |
|-------|------|----------|----------------|
| llama2 | 7B | 3-5s | 1-2s |
| mistral | 7B | 2-4s | 0.8-1.5s |
| llama2:13b | 13B | 8-12s | 2-4s |

### Optimization Tips

1. **Use GPU**: Ollama automatically uses CUDA/Metal
2. **Smaller Models**: Use 7B models for faster responses
3. **Context Window**: Reduce `num_ctx` if not needed
4. **Quantization**: Use quantized models (default in Ollama)

## Error Handling

```python
from core.llm.ollama import ProviderUnavailableException
from core.llm.base import ModelNotFoundError, TimeoutError

try:
    response = provider.invoke("Test prompt")
except ProviderUnavailableException:
    print("Ollama service not running. Start with: ollama serve")
except ModelNotFoundError as e:
    print(f"Model not found: {e}. Pull with: ollama pull {model}")
except TimeoutError:
    print("Request timed out. Try smaller model or increase timeout.")
```

## Advanced Usage

### Remote Ollama Server

```python
# Connect to Ollama on another machine
provider = OllamaProvider({
    "host": "http://192.168.1.100:11434"
})
```

### Custom Context Length

```python
response = provider.invoke(
    "Very long document...",
    num_ctx=16384  # Increase context window to 16K tokens
)
```

### Disable Auto-Pull

```python
# Disable automatic model pulling
provider = OllamaProvider({"auto_pull": False})

# Manually handle missing models
try:
    response = provider.invoke("Test", model="newmodel")
except ModelNotFoundError:
    print("Model not found and auto_pull is disabled")
```

## Troubleshooting

### Service Not Running

**Error**: `ProviderUnavailableException: Ollama service not running`

**Solution**:
```bash
# Start Ollama service
ollama serve

# Or check if already running
ps aux | grep ollama
```

### Model Not Found

**Error**: `ModelNotFoundError: model 'mistral' not found`

**Solution**:
```bash
# Pull the model
ollama pull mistral

# Or enable auto_pull in config
```

### Slow Performance

**Issue**: Requests taking too long

**Solutions**:
1. Use smaller models (7B instead of 13B)
2. Check GPU availability: `nvidia-smi` or `system_profiler SPDisplaysDataType`
3. Reduce context window: `num_ctx=4096`
4. Increase timeout: `timeout=900`

### Out of Memory

**Error**: GPU/RAM exhausted

**Solutions**:
1. Use smaller model
2. Reduce batch size (for multiple requests)
3. Close other applications
4. Use quantized models (default)

## Best Practices

1. **Check Health First**: Always call `health_check()` before heavy usage
2. **Model Selection**: Use appropriate models (codellama for code, llama2 for general)
3. **Timeout Management**: Set timeouts based on model size (600s for 7B, 900s for 13B)
4. **Error Handling**: Always catch `ProviderUnavailableException` and `ModelNotFoundError`
5. **Resource Management**: Monitor GPU/CPU usage, especially with concurrent requests

## Integration with Atomic Claude

### In Phase Task Scripts

```python
from core.llm.ollama import OllamaProvider

def task_analyze_code():
    """Analyze code using local Ollama."""
    provider = OllamaProvider()

    # Check if service is available
    if provider.health_check() != HealthStatus.HEALTHY:
        print("Warning: Ollama not available, falling back to API")
        return False

    # Analyze code
    code = Path("src/main.py").read_text()
    response = provider.invoke(
        f"Review this code for issues:\\n\\n{code}",
        model="codellama",
        system_prompt="You are a code review expert"
    )

    # Save analysis
    Path(".outputs/analysis.md").write_text(response.content)
    return True
```

## See Also

- [Testing Providers](testing-providers.md) - How to test providers
- [Adding Providers](adding-providers.md) - How to add new providers
- [Base Provider Interface](../../core/llm/base.py) - Provider interface specification
