"""
ATOMIC CLAUDE - LLM Abstraction Layer

Provider-agnostic LLM interface for flexible model access.
"""

from .base import (
    BaseLLMProvider,
    LLMResponse,
    LLMError,
    HealthStatus,
    TokenUsage,
    AuthenticationError,
    RateLimitError,
    LLMTimeoutError,
    APIError,
    ModelNotFoundError,
)

from .exceptions import (
    LLMException,
    ProviderUnavailableException,
    ModelNotFoundException,
    RateLimitException,
    TimeoutException,
    AuthenticationException,
    InvalidResponseException,
    ContentFilterException,
    ContextLengthException,
    ServiceUnavailableException,
    ValidationException,
)

from .types import (
    ModelRole,
    ProviderType,
    HealthStatus as HealthStatusEnum,
    LLMRequest,
    UsageStats,
    ModelInfo,
    ProviderHealth,
)

from .cache import LLMCache

from .router import LLMRouter, RouterConfig

from .anthropic import AnthropicProvider
from .bedrock import BedrockProvider
from .ollama import OllamaProvider
from .claude_code import ClaudeCodeProvider

from .invoke import invoke_llm, stream_llm, FeatureAwareLLMInvoker
from .invoke import invoke_llm as invoke  # Alias for compatibility
from .capabilities import (
    ModelCapability, provider_supports,
    get_model_context_window, get_model_max_output,
)
from .resolver import (
    resolve_model, get_resolver, reset_resolver,
    ResolvedModel, ModelResolver,
    CLAUDE_CODE_FAST_MODE_FORBIDDEN,
)

__all__ = [
    # Base classes and types
    "BaseLLMProvider",
    "LLMResponse",
    "LLMError",
    "HealthStatus",
    "TokenUsage",
    # Base exceptions
    "AuthenticationError",
    "RateLimitError",
    "LLMTimeoutError",
    "APIError",
    "ModelNotFoundError",
    # Extended exceptions
    "LLMException",
    "ProviderUnavailableException",
    "ModelNotFoundException",
    "RateLimitException",
    "TimeoutException",
    "AuthenticationException",
    "InvalidResponseException",
    "ContentFilterException",
    "ContextLengthException",
    "ServiceUnavailableException",
    "ValidationException",
    # Types
    "ModelRole",
    "ProviderType",
    "HealthStatusEnum",
    "LLMRequest",
    "UsageStats",
    "ModelInfo",
    "ProviderHealth",
    # Cache
    "LLMCache",
    # Router
    "LLMRouter",
    "RouterConfig",
    # Providers
    "AnthropicProvider",
    "BedrockProvider",
    "OllamaProvider",
    "ClaudeCodeProvider",
    # Invocation
    "invoke_llm",
    "invoke",
    "stream_llm",
    "FeatureAwareLLMInvoker",
    # Capabilities
    "ModelCapability",
    "provider_supports",
    "get_model_context_window",
    "get_model_max_output",
    # Resolver
    "resolve_model",
    "get_resolver",
    "reset_resolver",
    "ResolvedModel",
    "ModelResolver",
    "CLAUDE_CODE_FAST_MODE_FORBIDDEN",
]
