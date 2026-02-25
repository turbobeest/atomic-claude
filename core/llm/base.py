#!/usr/bin/env python3
"""
ATOMIC CLAUDE - Base LLM Provider Interface

Abstract base class defining the interface for all LLM providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Generator, Optional, Any


class HealthStatus(str, Enum):
    """Provider health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass
class TokenUsage:
    """Token usage statistics."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.input_tokens + self.output_tokens

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_write_tokens": self.cache_write_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class LLMResponse:
    """Standardized LLM response."""
    content: str
    model: str
    provider: str
    usage: TokenUsage
    finish_reason: Optional[str] = None
    stop_reason: Optional[str] = None
    latency_ms: Optional[int] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "model": self.model,
            "provider": self.provider,
            "usage": self.usage.to_dict(),
            "finish_reason": self.finish_reason,
            "stop_reason": self.stop_reason,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class LLMError(Exception):
    """Base exception for LLM provider errors."""

    def __init__(self, message: str, provider: Optional[str] = None,
                 error_code: Optional[str] = None, retryable: bool = False):
        super().__init__(message)
        self.provider = provider
        self.error_code = error_code
        self.retryable = retryable


class AuthenticationError(LLMError):
    """Authentication failed (invalid API key, etc.)."""
    pass


class RateLimitError(LLMError):
    """Rate limit exceeded."""

    def __init__(self, message: str, provider: Optional[str] = None,
                 retry_after: Optional[int] = None):
        super().__init__(message, provider, "rate_limit", retryable=True)
        self.retry_after = retry_after


class LLMTimeoutError(LLMError):
    """Request timed out."""

    def __init__(self, message: str, provider: Optional[str] = None):
        super().__init__(message, provider, "timeout", retryable=True)


TimeoutError = LLMTimeoutError  # noqa: A001 — backward compat


class APIError(LLMError):
    """General API error."""
    pass


class ModelNotFoundError(LLMError):
    """Requested model not available."""
    pass


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All providers must implement this interface to ensure consistent behavior
    across different LLM backends (Anthropic, AWS Bedrock, Ollama, etc.).
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize provider.

        Args:
            config: Provider-specific configuration
        """
        self.config = config or {}
        self.provider_name = "base"

    @abstractmethod
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
        Invoke LLM with a prompt and return response.

        Args:
            prompt: User prompt/message
            system_prompt: Optional system prompt
            model: Model name (provider-specific)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            timeout: Request timeout in seconds
            **kwargs: Provider-specific parameters

        Returns:
            LLMResponse with content and metadata

        Raises:
            AuthenticationError: Invalid credentials
            RateLimitError: Rate limit exceeded
            TimeoutError: Request timeout
            APIError: Other API errors
            ModelNotFoundError: Model not available
        """
        pass

    @abstractmethod
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
        Stream LLM response token by token.

        Args:
            prompt: User prompt/message
            system_prompt: Optional system prompt
            model: Model name (provider-specific)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            **kwargs: Provider-specific parameters

        Yields:
            Text chunks as they arrive

        Raises:
            Same exceptions as invoke()
        """
        pass

    @abstractmethod
    def validate_model(self, model_name: str) -> bool:
        """
        Check if model is supported by this provider.

        Args:
            model_name: Model identifier

        Returns:
            True if model is supported
        """
        pass

    @abstractmethod
    def get_token_count(self, text: str, model: Optional[str] = None) -> int:
        """
        Estimate token count for text.

        Args:
            text: Input text
            model: Model name (for model-specific tokenization)

        Returns:
            Estimated token count
        """
        pass

    @abstractmethod
    def health_check(self) -> HealthStatus:
        """
        Check provider health/availability.

        Returns:
            HealthStatus indicating provider state
        """
        pass

    def get_default_model(self) -> Optional[str]:
        """
        Get default model for this provider.

        Returns:
            Default model name or None
        """
        return self.config.get("default_model")

    def get_supported_models(self) -> list:
        """
        Get list of supported models.

        Returns:
            List of model names
        """
        return []

    def __repr__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(provider={self.provider_name})"
