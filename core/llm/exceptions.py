#!/usr/bin/env python3
"""
ATOMIC CLAUDE - LLM Exception Hierarchy

Comprehensive exception types for LLM operations.
"""


class LLMException(Exception):
    """
    Base exception for all LLM-related errors.

    All LLM exceptions inherit from this base class.
    """

    def __init__(self, message: str, provider: str = None,
                 error_code: str = None, retryable: bool = False):
        """
        Initialize LLM exception.

        Args:
            message: Error message
            provider: Provider name (anthropic, bedrock, ollama)
            error_code: Error code from provider
            retryable: Whether error is retryable
        """
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.error_code = error_code
        self.retryable = retryable

    def to_dict(self):
        """Convert to dictionary representation."""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "provider": self.provider,
            "error_code": self.error_code,
            "retryable": self.retryable,
        }


class ProviderUnavailableException(LLMException):
    """
    Provider is not available or not configured.

    Examples:
    - API key missing
    - Service unreachable
    - Provider not installed
    """

    def __init__(self, message: str, provider: str = None):
        super().__init__(message, provider, "provider_unavailable", retryable=False)


class ModelNotFoundException(LLMException):
    """
    Requested model not found or not accessible.

    Examples:
    - Invalid model name
    - Model not available in region
    - Model access not granted
    """

    def __init__(self, message: str, provider: str = None, model: str = None):
        super().__init__(message, provider, "model_not_found", retryable=False)
        self.model = model


class RateLimitException(LLMException):
    """
    Rate limit exceeded.

    Provider is throttling requests.
    """

    def __init__(self, message: str, provider: str = None, retry_after: int = None):
        super().__init__(message, provider, "rate_limit", retryable=True)
        self.retry_after = retry_after


class TimeoutException(LLMException):
    """
    Request timed out.

    Request took longer than timeout duration.
    """

    def __init__(self, message: str, provider: str = None, timeout_seconds: int = None):
        super().__init__(message, provider, "timeout", retryable=True)
        self.timeout_seconds = timeout_seconds


class AuthenticationException(LLMException):
    """
    Authentication failed.

    Examples:
    - Invalid API key
    - Expired credentials
    - IAM role issues
    """

    def __init__(self, message: str, provider: str = None):
        super().__init__(message, provider, "authentication_failed", retryable=False)


class InvalidResponseException(LLMException):
    """
    Response format invalid or unexpected.

    Examples:
    - Malformed JSON
    - Missing required fields
    - Unexpected response structure
    """

    def __init__(self, message: str, provider: str = None, response: str = None):
        super().__init__(message, provider, "invalid_response", retryable=False)
        self.response = response


class ContentFilterException(LLMException):
    """
    Content was filtered by provider.

    Request or response violated content policy.
    """

    def __init__(self, message: str, provider: str = None):
        super().__init__(message, provider, "content_filtered", retryable=False)


class ContextLengthException(LLMException):
    """
    Context length exceeded.

    Request exceeds model's maximum context window.
    """

    def __init__(self, message: str, provider: str = None,
                 token_count: int = None, max_tokens: int = None):
        super().__init__(message, provider, "context_length_exceeded", retryable=False)
        self.token_count = token_count
        self.max_tokens = max_tokens


class ServiceUnavailableException(LLMException):
    """
    Service temporarily unavailable.

    Examples:
    - Provider maintenance
    - Service outage
    - Temporary network issues
    """

    def __init__(self, message: str, provider: str = None):
        super().__init__(message, provider, "service_unavailable", retryable=True)


class ValidationException(LLMException):
    """
    Request validation failed.

    Examples:
    - Invalid parameters
    - Missing required fields
    - Parameter out of range
    """

    def __init__(self, message: str, provider: str = None, field: str = None):
        super().__init__(message, provider, "validation_error", retryable=False)
        self.field = field
