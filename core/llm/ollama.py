#!/usr/bin/env python3
"""
ATOMIC CLAUDE - Ollama Local LLM Provider

Ollama provider for running local LLMs without API costs or network dependencies.
Supports streaming, model pulling, and GPU acceleration.
"""

import json
import time
import urllib.request
import urllib.error
from typing import Dict, Generator, Optional, Any, List
from datetime import datetime

from .base import (
    BaseLLMProvider,
    LLMResponse,
    TokenUsage,
    HealthStatus,
    LLMError,
    LLMTimeoutError,
    APIError,
    ModelNotFoundError,
)


class ProviderUnavailableException(LLMError):
    """Ollama provider is not available (service not running)."""
    pass


# Tier-to-model mapping for Ollama (mirrors config/models.json).
# Allows tasks to use tier names (opus/sonnet/haiku) when running on Ollama.
OLLAMA_TIER_MAP = {
    "opus":   "qwen3:235b-a22b",
    "sonnet": "llama3.1:70b",
    "haiku":  "qwen2.5-coder:14b",
}


class OllamaProvider(BaseLLMProvider):
    """
    Ollama local LLM provider.

    Features:
    - Local model execution (no API costs)
    - HTTP REST API integration
    - Streaming support
    - Automatic model pulling
    - GPU detection and usage
    - Connection pooling

    Configuration:
    - host: Ollama server URL (default: http://localhost:11434)
    - default_model: Default model name (default: llama2)
    - timeout: Request timeout in seconds (default: 600)
    - auto_pull: Automatically pull missing models (default: True)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Ollama provider.

        Args:
            config: Provider configuration with optional keys:
                - host: Ollama server URL
                - default_model: Default model name
                - timeout: Request timeout
                - auto_pull: Auto-pull missing models
        """
        super().__init__(config)
        self.provider_name = "ollama"

        # Configuration
        self.host = self.config.get("host", "http://localhost:11434")
        self.default_model = self.config.get("default_model", "llama2")
        self.default_timeout = self.config.get("timeout", 600)  # 10 minutes for local processing
        self.auto_pull = self.config.get("auto_pull", True)

        # Ensure host doesn't have trailing slash
        self.host = self.host.rstrip('/')

    def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
        timeout: int = 600,
        **kwargs
    ) -> LLMResponse:
        """
        Invoke Ollama model with a prompt.

        Args:
            prompt: User prompt/message
            system_prompt: Optional system prompt
            model: Model name (e.g., "llama2", "mistral", "codellama")
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            timeout: Request timeout in seconds
            **kwargs: Additional Ollama parameters (e.g., num_ctx, top_p, top_k)

        Returns:
            LLMResponse with content and metadata

        Raises:
            ProviderUnavailableException: Ollama service not running
            ModelNotFoundError: Model not found
            TimeoutError: Request timeout
            APIError: Other API errors
        """
        start_time = time.time()
        model = model or self.get_default_model() or self.default_model

        # Resolve tier names (opus/sonnet/haiku) to Ollama model names
        if model in OLLAMA_TIER_MAP:
            model = OLLAMA_TIER_MAP[model]

        # Build combined prompt
        combined_prompt = prompt
        if system_prompt:
            combined_prompt = f"<system>{system_prompt}</system>\n\n{prompt}"

        # Build request
        request_data = {
            "model": model,
            "prompt": combined_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }

        # Add optional parameters
        if "num_ctx" in kwargs:
            request_data["options"]["num_ctx"] = kwargs["num_ctx"]
        if "top_p" in kwargs:
            request_data["options"]["top_p"] = kwargs["top_p"]
        if "top_k" in kwargs:
            request_data["options"]["top_k"] = kwargs["top_k"]

        # Make request
        try:
            url = f"{self.host}/api/generate"
            req = urllib.request.Request(
                url,
                data=json.dumps(request_data).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=timeout) as response:
                response_data = json.loads(response.read().decode('utf-8'))

        except urllib.error.URLError as e:
            if "Connection refused" in str(e) or "Connection reset" in str(e):
                raise ProviderUnavailableException(
                    f"Ollama service not running at {self.host}. "
                    "Start Ollama with: ollama serve",
                    provider="ollama"
                )
            raise APIError(f"Ollama API error: {e}", provider="ollama")

        except LLMTimeoutError as e:
            raise LLMTimeoutError(
                f"Ollama request timed out after {timeout}s",
                provider="ollama"
            )
        except Exception as e:
            raise APIError(f"Ollama request failed: {e}", provider="ollama")

        # Check for model not found
        if response_data.get("error"):
            error_msg = response_data["error"]
            if "model" in error_msg.lower() and "not found" in error_msg.lower():
                if self.auto_pull:
                    # Try to pull the model
                    if self.pull_model(model):
                        # Retry after successful pull
                        return self.invoke(prompt, system_prompt, model, max_tokens, temperature, timeout, **kwargs)
                raise ModelNotFoundError(f"Model not found: {model}", provider="ollama")
            raise APIError(error_msg, provider="ollama")

        # Parse response
        content = response_data.get("response", "")

        # Calculate token usage (approximate)
        input_tokens = self.get_token_count(combined_prompt, model)
        output_tokens = self.get_token_count(content, model)

        usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )

        # Calculate latency
        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)

        # Build response
        return LLMResponse(
            content=content,
            model=model,
            provider=self.provider_name,
            usage=usage,
            finish_reason=response_data.get("done_reason"),
            latency_ms=latency_ms,
            timestamp=datetime.now(),
            metadata={
                "total_duration": response_data.get("total_duration"),
                "load_duration": response_data.get("load_duration"),
                "prompt_eval_count": response_data.get("prompt_eval_count"),
                "eval_count": response_data.get("eval_count"),
                "context": response_data.get("context", []),
            }
        )

    def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Stream Ollama model response token by token.

        Args:
            prompt: User prompt/message
            system_prompt: Optional system prompt
            model: Model name
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional Ollama parameters

        Yields:
            Text chunks as they arrive

        Raises:
            Same exceptions as invoke()
        """
        model = model or self.get_default_model() or self.default_model

        # Resolve tier names (opus/sonnet/haiku) to Ollama model names
        if model in OLLAMA_TIER_MAP:
            model = OLLAMA_TIER_MAP[model]

        # Build combined prompt
        combined_prompt = prompt
        if system_prompt:
            combined_prompt = f"<system>{system_prompt}</system>\n\n{prompt}"

        # Build request
        request_data = {
            "model": model,
            "prompt": combined_prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }

        # Add optional parameters
        if "num_ctx" in kwargs:
            request_data["options"]["num_ctx"] = kwargs["num_ctx"]
        if "top_p" in kwargs:
            request_data["options"]["top_p"] = kwargs["top_p"]
        if "top_k" in kwargs:
            request_data["options"]["top_k"] = kwargs["top_k"]

        # Make streaming request
        try:
            url = f"{self.host}/api/generate"
            req = urllib.request.Request(
                url,
                data=json.dumps(request_data).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=self.default_timeout) as response:
                # Read NDJSON stream line by line
                for line in response:
                    if not line.strip():
                        continue

                    chunk_data = json.loads(line.decode('utf-8'))

                    # Yield response chunk
                    if "response" in chunk_data:
                        yield chunk_data["response"]

                    # Check if done
                    if chunk_data.get("done"):
                        break

        except urllib.error.URLError as e:
            if "Connection refused" in str(e):
                raise ProviderUnavailableException(
                    f"Ollama service not running at {self.host}",
                    provider="ollama"
                )
            raise APIError(f"Ollama streaming error: {e}", provider="ollama")
        except Exception as e:
            raise APIError(f"Ollama streaming failed: {e}", provider="ollama")

    def validate_model(self, model_name: str) -> bool:
        """
        Check if model is available locally.

        Args:
            model_name: Model identifier

        Returns:
            True if model is available
        """
        # Resolve tier names first
        resolved = OLLAMA_TIER_MAP.get(model_name, model_name)
        try:
            models = self.list_models()
            return resolved in models
        except Exception:
            return False

    def get_token_count(self, text: str, model: Optional[str] = None) -> int:
        """
        Estimate token count for text.

        Note: This is an approximation. Ollama doesn't provide a tokenization API,
        so we estimate based on whitespace splitting (roughly 0.75 tokens per word).

        Args:
            text: Input text
            model: Model name (unused, kept for interface compatibility)

        Returns:
            Estimated token count
        """
        # Simple approximation: split on whitespace
        words = text.split()
        # Rough estimate: 0.75 tokens per word on average
        return int(len(words) * 0.75)

    def health_check(self) -> HealthStatus:
        """
        Check Ollama service health.

        Returns:
            HealthStatus indicating provider state
        """
        try:
            # Try to list models (quick API call)
            url = f"{self.host}/api/tags"
            req = urllib.request.Request(url, method='GET')

            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    # Check if any models are available
                    if data.get("models"):
                        return HealthStatus.HEALTHY
                    else:
                        return HealthStatus.DEGRADED  # Service up but no models

        except urllib.error.URLError:
            return HealthStatus.UNAVAILABLE
        except Exception:
            return HealthStatus.UNAVAILABLE

        return HealthStatus.UNAVAILABLE

    def pull_model(self, model_name: str) -> bool:
        """
        Pull a model from Ollama registry.

        Args:
            model_name: Model to pull (e.g., "llama2", "mistral")

        Returns:
            True if pull successful, False otherwise
        """
        try:
            url = f"{self.host}/api/pull"
            request_data = {"name": model_name, "stream": False}

            req = urllib.request.Request(
                url,
                data=json.dumps(request_data).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )

            # This can take a while for large models
            with urllib.request.urlopen(req, timeout=1800) as response:  # 30 min timeout
                response_data = json.loads(response.read().decode('utf-8'))
                return response_data.get("status") == "success"

        except Exception:
            return False

    def list_models(self) -> List[str]:
        """
        List available models on Ollama server.

        Returns:
            List of model names
        """
        try:
            url = f"{self.host}/api/tags"
            req = urllib.request.Request(url, method='GET')

            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                return [model["name"] for model in data.get("models", [])]

        except Exception:
            return []

    def get_supported_models(self) -> List[str]:
        """
        Get list of locally available models.

        Returns:
            List of model names
        """
        return self.list_models()

    def get_default_model(self) -> Optional[str]:
        """
        Get default model for this provider.

        Returns:
            Default model name
        """
        return self.config.get("default_model", self.default_model)

    def __repr__(self) -> str:
        """String representation."""
        return f"OllamaProvider(host={self.host}, model={self.default_model})"
