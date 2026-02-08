#!/usr/bin/env python3
"""
Unit tests for LLM Exceptions.

Tests exception hierarchy and error handling.
"""

import pytest

from core.llm.exceptions import (
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


class TestLLMExceptions:
    """Test suite for LLM exceptions."""

    def test_base_exception(self):
        """Test base LLM exception."""
        exc = LLMException(
            "Test error",
            provider="test",
            error_code="test_code",
            retryable=True
        )

        assert str(exc) == "Test error"
        assert exc.provider == "test"
        assert exc.error_code == "test_code"
        assert exc.retryable is True

    def test_exception_to_dict(self):
        """Test exception to_dict conversion."""
        exc = LLMException(
            "Test error",
            provider="test",
            error_code="test_code",
            retryable=True
        )

        result = exc.to_dict()

        assert result["type"] == "LLMException"
        assert result["message"] == "Test error"
        assert result["provider"] == "test"
        assert result["error_code"] == "test_code"
        assert result["retryable"] is True

    def test_provider_unavailable_exception(self):
        """Test ProviderUnavailableException."""
        exc = ProviderUnavailableException("Provider down", provider="test")

        assert str(exc) == "Provider down"
        assert exc.provider == "test"
        assert exc.error_code == "provider_unavailable"
        assert exc.retryable is False

    def test_model_not_found_exception(self):
        """Test ModelNotFoundException."""
        exc = ModelNotFoundException(
            "Model not found",
            provider="test",
            model="test-model"
        )

        assert str(exc) == "Model not found"
        assert exc.provider == "test"
        assert exc.model == "test-model"
        assert exc.error_code == "model_not_found"
        assert exc.retryable is False

    def test_rate_limit_exception(self):
        """Test RateLimitException."""
        exc = RateLimitException(
            "Rate limit exceeded",
            provider="test",
            retry_after=60
        )

        assert str(exc) == "Rate limit exceeded"
        assert exc.provider == "test"
        assert exc.retry_after == 60
        assert exc.error_code == "rate_limit"
        assert exc.retryable is True

    def test_timeout_exception(self):
        """Test TimeoutException."""
        exc = TimeoutException(
            "Request timed out",
            provider="test",
            timeout_seconds=300
        )

        assert str(exc) == "Request timed out"
        assert exc.provider == "test"
        assert exc.timeout_seconds == 300
        assert exc.error_code == "timeout"
        assert exc.retryable is True

    def test_authentication_exception(self):
        """Test AuthenticationException."""
        exc = AuthenticationException(
            "Auth failed",
            provider="test"
        )

        assert str(exc) == "Auth failed"
        assert exc.provider == "test"
        assert exc.error_code == "authentication_failed"
        assert exc.retryable is False

    def test_invalid_response_exception(self):
        """Test InvalidResponseException."""
        exc = InvalidResponseException(
            "Invalid response",
            provider="test",
            response="bad json"
        )

        assert str(exc) == "Invalid response"
        assert exc.provider == "test"
        assert exc.response == "bad json"
        assert exc.error_code == "invalid_response"
        assert exc.retryable is False

    def test_content_filter_exception(self):
        """Test ContentFilterException."""
        exc = ContentFilterException(
            "Content filtered",
            provider="test"
        )

        assert str(exc) == "Content filtered"
        assert exc.provider == "test"
        assert exc.error_code == "content_filtered"
        assert exc.retryable is False

    def test_context_length_exception(self):
        """Test ContextLengthException."""
        exc = ContextLengthException(
            "Context too long",
            provider="test",
            token_count=10000,
            max_tokens=8192
        )

        assert str(exc) == "Context too long"
        assert exc.provider == "test"
        assert exc.token_count == 10000
        assert exc.max_tokens == 8192
        assert exc.error_code == "context_length_exceeded"
        assert exc.retryable is False

    def test_service_unavailable_exception(self):
        """Test ServiceUnavailableException."""
        exc = ServiceUnavailableException(
            "Service down",
            provider="test"
        )

        assert str(exc) == "Service down"
        assert exc.provider == "test"
        assert exc.error_code == "service_unavailable"
        assert exc.retryable is True

    def test_validation_exception(self):
        """Test ValidationException."""
        exc = ValidationException(
            "Validation failed",
            provider="test",
            field="temperature"
        )

        assert str(exc) == "Validation failed"
        assert exc.provider == "test"
        assert exc.field == "temperature"
        assert exc.error_code == "validation_error"
        assert exc.retryable is False

    def test_exception_inheritance(self):
        """Test exception inheritance."""
        # All should inherit from LLMException
        assert issubclass(ProviderUnavailableException, LLMException)
        assert issubclass(ModelNotFoundException, LLMException)
        assert issubclass(RateLimitException, LLMException)
        assert issubclass(TimeoutException, LLMException)
        assert issubclass(AuthenticationException, LLMException)

    def test_exception_catching(self):
        """Test catching exceptions."""
        # Should catch specific exception
        with pytest.raises(RateLimitException):
            raise RateLimitException("Rate limit")

        # Should catch base exception
        with pytest.raises(LLMException):
            raise RateLimitException("Rate limit")

        # Should catch Exception
        with pytest.raises(Exception):
            raise LLMException("Error")
