#!/usr/bin/env python3
"""
ATOMIC CLAUDE - Anthropic Provider

Anthropic API provider implementation using official SDK.
"""

import logging
import os
import time
from typing import Dict, Generator, Optional, Any

logger = logging.getLogger(__name__)

try:
    import anthropic
    from anthropic import Anthropic, AnthropicBedrock
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from .base import (
    BaseLLMProvider,
    LLMResponse,
    TokenUsage,
    HealthStatus,
    AuthenticationError,
    RateLimitError,
    LLMTimeoutError,
    APIError,
    ModelNotFoundError,
)


# Supported Claude models
CLAUDE_MODELS = [
    "claude-opus-4-6",
    "claude-opus-4-5",
    "claude-opus-4",
    "claude-sonnet-4-5",
    "claude-sonnet-4",
    "claude-haiku-4",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-20240620",
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
]

# Model tier mapping (abstract names)
MODEL_TIER_MAP = {
    "opus": "claude-opus-4-6",
    "sonnet": "claude-sonnet-4-5",
    "haiku": "claude-haiku-4",
}


class AnthropicProvider(BaseLLMProvider):
    """
    Anthropic API provider using official anthropic SDK.

    Features:
    - All Claude models (opus, sonnet, haiku)
    - Message API with system prompts
    - Streaming support
    - Prompt caching (if enabled)
    - Comprehensive error handling
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Anthropic provider.

        Args:
            config: Configuration dict with:
                - api_key: Anthropic API key (or uses ANTHROPIC_API_KEY env)
                - default_model: Default model (default: claude-sonnet-4-5)
                - timeout: Default timeout in seconds (default: 300)
                - max_retries: Max retry attempts (default: 3)
                - enable_caching: Enable prompt caching (default: False)
        """
        super().__init__(config)
        self.provider_name = "anthropic"

        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic package not installed. "
                "Install with: pip install anthropic"
            )

        # Get API key from config or environment
        self.api_key = self.config.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise AuthenticationError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable "
                "or provide 'api_key' in config.",
                provider="anthropic"
            )

        # Configuration
        self.default_model = self.config.get("default_model", "claude-sonnet-4-5")
        self.timeout = self.config.get("timeout", 300)
        self.max_retries = self.config.get("max_retries", 3)
        self.enable_caching = self.config.get("enable_caching", False)

        # Initialize client
        self.client = Anthropic(api_key=self.api_key)

    def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
        timeout: int = 300,
        **kwargs
    ) -> LLMResponse:
        """
        Invoke Anthropic API with prompt.

        Args:
            prompt: User message
            system_prompt: Optional system prompt
            model: Model name (or tier like "sonnet")
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            timeout: Request timeout
            **kwargs: Additional Anthropic API parameters

        Returns:
            LLMResponse with content and metadata

        Raises:
            AuthenticationError: Invalid API key
            RateLimitError: Rate limit exceeded
            TimeoutError: Request timeout
            APIError: API errors
            ModelNotFoundError: Model not available
        """
        start_time = time.time()

        # Resolve model (handle tier names)
        resolved_model = self._resolve_model(model)

        # Build messages
        messages = [{"role": "user", "content": prompt}]

        # Build request kwargs
        request_kwargs = {
            "model": resolved_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Add system prompt if provided
        if system_prompt:
            request_kwargs["system"] = system_prompt

        # Add prompt caching headers if enabled
        if self.enable_caching and system_prompt:
            request_kwargs["system"] = [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"}
                }
            ]

        # Merge additional kwargs
        request_kwargs.update(kwargs)

        # Retry logic with exponential backoff
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                response = self.client.messages.create(**request_kwargs)

                # Calculate latency
                latency_ms = int((time.time() - start_time) * 1000)

                # Extract usage
                usage = TokenUsage(
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    cache_read_tokens=getattr(response.usage, "cache_read_input_tokens", 0),
                    cache_write_tokens=getattr(response.usage, "cache_creation_input_tokens", 0),
                )

                # Extract content
                content = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        content += block.text

                return LLMResponse(
                    content=content,
                    model=resolved_model,
                    provider=self.provider_name,
                    usage=usage,
                    finish_reason=response.stop_reason,
                    stop_reason=response.stop_reason,
                    latency_ms=latency_ms,
                    metadata={
                        "id": response.id,
                        "type": response.type,
                        "role": response.role,
                    }
                )

            except anthropic.AuthenticationError as e:
                raise AuthenticationError(
                    f"Anthropic authentication failed: {str(e)}",
                    provider="anthropic"
                )

            except anthropic.RateLimitError as e:
                # Check for retry-after header
                retry_after = None
                if hasattr(e, "response") and e.response:
                    retry_after = e.response.headers.get("retry-after")
                    if retry_after:
                        retry_after = int(retry_after)

                # Retry with exponential backoff
                if attempt < self.max_retries - 1:
                    wait_time = retry_after or (2 ** attempt)
                    time.sleep(wait_time)
                    continue

                raise RateLimitError(
                    f"Anthropic rate limit exceeded: {str(e)}",
                    provider="anthropic",
                    retry_after=retry_after
                )

            except anthropic.APITimeoutError as e:
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue

                raise LLMTimeoutError(
                    f"Anthropic request timed out: {str(e)}",
                    provider="anthropic"
                )

            except anthropic.APIConnectionError as e:
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue

                raise APIError(
                    f"Anthropic connection error: {str(e)}",
                    provider="anthropic",
                    error_code="connection_error",
                    retryable=True
                )

            except anthropic.NotFoundError as e:
                raise ModelNotFoundError(
                    f"Model not found: {resolved_model}. Error: {str(e)}",
                    provider="anthropic"
                )

            except anthropic.APIError as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue

                raise APIError(
                    f"Anthropic API error: {str(e)}",
                    provider="anthropic",
                    error_code=getattr(e, "status_code", None)
                )

        # All retries exhausted
        raise APIError(
            f"Anthropic request failed after {self.max_retries} attempts: {str(last_exception)}",
            provider="anthropic"
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
        Stream Anthropic API response.

        Args:
            prompt: User message
            system_prompt: Optional system prompt
            model: Model name
            max_tokens: Max tokens
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Yields:
            Text chunks as they arrive

        Raises:
            Same exceptions as invoke()
        """
        # Resolve model
        resolved_model = self._resolve_model(model)

        # Build messages
        messages = [{"role": "user", "content": prompt}]

        # Build request kwargs
        request_kwargs = {
            "model": resolved_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Add system prompt if provided
        if system_prompt:
            request_kwargs["system"] = system_prompt

        # Merge additional kwargs
        request_kwargs.update(kwargs)

        try:
            with self.client.messages.stream(**request_kwargs) as stream:
                for text in stream.text_stream:
                    yield text

        except anthropic.AuthenticationError as e:
            raise AuthenticationError(
                f"Anthropic authentication failed: {str(e)}",
                provider="anthropic"
            )

        except anthropic.RateLimitError as e:
            raise RateLimitError(
                f"Anthropic rate limit exceeded: {str(e)}",
                provider="anthropic"
            )

        except anthropic.APITimeoutError as e:
            raise LLMTimeoutError(
                f"Anthropic request timed out: {str(e)}",
                provider="anthropic"
            )

        except anthropic.APIError as e:
            raise APIError(
                f"Anthropic API error: {str(e)}",
                provider="anthropic"
            )

    def validate_model(self, model_name: str) -> bool:
        """
        Check if model is supported.

        Args:
            model_name: Model identifier or tier name

        Returns:
            True if supported
        """
        # Check tier names
        if model_name in MODEL_TIER_MAP:
            return True

        # Check full model names
        return model_name in CLAUDE_MODELS

    def get_token_count(self, text: str, model: Optional[str] = None) -> int:
        """
        Estimate token count for text.

        Uses Anthropic's token counting method (approximate).

        Args:
            text: Input text
            model: Model name (optional)

        Returns:
            Estimated token count
        """
        try:
            # Use Anthropic's count_tokens method
            count = self.client.count_tokens(text)
            return count
        except Exception as e:
            # Fallback to rough estimate (4 chars per token)
            logger.debug("Token counting failed, using estimate: %s", e)
            return len(text) // 4

    def health_check(self) -> HealthStatus:
        """
        Check Anthropic API health.

        Returns:
            HealthStatus
        """
        try:
            # Make minimal API call to verify connectivity
            response = self.client.messages.create(
                model=self.default_model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=10,
            )

            if response and response.content:
                return HealthStatus.HEALTHY

            return HealthStatus.DEGRADED

        except anthropic.AuthenticationError:
            return HealthStatus.UNAVAILABLE

        except anthropic.APIError:
            return HealthStatus.DEGRADED

        except Exception as e:
            logger.debug("Anthropic health check failed: %s", e)
            return HealthStatus.UNAVAILABLE

    def get_supported_models(self) -> list:
        """
        Get list of supported Claude models.

        Returns:
            List of model names
        """
        return CLAUDE_MODELS.copy()

    def get_default_model(self) -> str:
        """
        Get default model.

        Returns:
            Default model name
        """
        return self.default_model

    def _resolve_model(self, model: Optional[str] = None) -> str:
        """
        Resolve model name (handles tier names like "sonnet").

        Args:
            model: Model name or tier

        Returns:
            Full model identifier
        """
        if not model:
            return self.default_model

        # Check if it's a tier name
        if model in MODEL_TIER_MAP:
            return MODEL_TIER_MAP[model]

        return model
