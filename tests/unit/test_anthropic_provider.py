#!/usr/bin/env python3
"""
Unit tests for Anthropic Provider.

Tests all functionality with mocked anthropic SDK calls.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import provider classes
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Mock anthropic module before importing provider
mock_anthropic_module = Mock()
mock_anthropic_module.Anthropic = Mock
mock_anthropic_module.AnthropicBedrock = Mock
mock_anthropic_module.AuthenticationError = type('AuthenticationError', (Exception,), {})
mock_anthropic_module.RateLimitError = type('RateLimitError', (Exception,), {})
mock_anthropic_module.APITimeoutError = type('APITimeoutError', (Exception,), {})
mock_anthropic_module.APIConnectionError = type('APIConnectionError', (Exception,), {})
mock_anthropic_module.NotFoundError = type('NotFoundError', (Exception,), {})
mock_anthropic_module.APIError = type('APIError', (Exception,), {})

sys.modules['anthropic'] = mock_anthropic_module

from core.llm.anthropic import AnthropicProvider, CLAUDE_MODELS, MODEL_TIER_MAP
from core.llm.base import (
    LLMResponse,
    TokenUsage,
    HealthStatus,
    AuthenticationError,
    RateLimitError,
    TimeoutError,
    APIError,
    ModelNotFoundError,
)


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    mock_client = Mock()
    mock_client.messages = Mock()
    mock_client.count_tokens = Mock(return_value=100)
    return mock_client


@pytest.fixture
def provider(mock_anthropic_client):
    """Create Anthropic provider with mocked client."""
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("core.llm.anthropic.Anthropic", return_value=mock_anthropic_client):
            provider = AnthropicProvider()
            return provider


class TestAnthropicProviderInitialization:
    """Test provider initialization."""

    def test_init_with_api_key_env(self, mock_anthropic_client):
        """Test initialization with API key from environment."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("core.llm.anthropic.Anthropic", return_value=mock_anthropic_client):
                provider = AnthropicProvider()
                assert provider.api_key == "test-key"
                assert provider.provider_name == "anthropic"

    def test_init_with_api_key_config(self, mock_anthropic_client):
        """Test initialization with API key from config."""
        with patch("core.llm.anthropic.Anthropic", return_value=mock_anthropic_client):
            provider = AnthropicProvider(config={"api_key": "config-key"})
            assert provider.api_key == "config-key"

    def test_init_without_api_key(self, mock_anthropic_client):
        """Test initialization fails without API key."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("core.llm.anthropic.Anthropic", return_value=mock_anthropic_client):
                with pytest.raises(AuthenticationError):
                    AnthropicProvider()

    def test_init_with_custom_config(self, mock_anthropic_client):
        """Test initialization with custom configuration."""
        config = {
            "api_key": "test-key",
            "default_model": "claude-opus-4-6",
            "timeout": 600,
            "max_retries": 5,
            "enable_caching": True,
        }
        with patch("core.llm.anthropic.Anthropic", return_value=mock_anthropic_client):
            provider = AnthropicProvider(config=config)
            assert provider.default_model == "claude-opus-4-6"
            assert provider.timeout == 600
            assert provider.max_retries == 5
            assert provider.enable_caching is True


class TestAnthropicProviderInvoke:
    """Test invoke method."""

    def test_invoke_basic(self, provider, mock_anthropic_client):
        """Test basic invocation."""
        # Mock response
        mock_response = Mock()
        mock_response.content = [Mock(text="Test response")]
        mock_response.usage = Mock(
            input_tokens=10,
            output_tokens=20,
        )
        mock_response.stop_reason = "end_turn"
        mock_response.id = "msg_123"
        mock_response.type = "message"
        mock_response.role = "assistant"

        mock_anthropic_client.messages.create.return_value = mock_response

        # Invoke
        response = provider.invoke(
            prompt="Test prompt",
            system_prompt="System prompt",
            model="sonnet",
            max_tokens=100,
            temperature=0.5
        )

        # Assertions
        assert isinstance(response, LLMResponse)
        assert response.content == "Test response"
        assert response.model == "claude-sonnet-4-5"  # Resolved from tier
        assert response.provider == "anthropic"
        assert response.usage.input_tokens == 10
        assert response.usage.output_tokens == 20
        assert response.finish_reason == "end_turn"

        # Check API was called correctly
        mock_anthropic_client.messages.create.assert_called_once()
        call_kwargs = mock_anthropic_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4-5"
        assert call_kwargs["messages"][0]["content"] == "Test prompt"
        assert call_kwargs["system"] == "System prompt"
        assert call_kwargs["max_tokens"] == 100
        assert call_kwargs["temperature"] == 0.5

    def test_invoke_with_tier_name(self, provider, mock_anthropic_client):
        """Test invocation with tier name (opus/sonnet/haiku)."""
        mock_response = Mock()
        mock_response.content = [Mock(text="Response")]
        mock_response.usage = Mock(input_tokens=5, output_tokens=10)
        mock_response.stop_reason = "end_turn"
        mock_response.id = "msg_123"
        mock_response.type = "message"
        mock_response.role = "assistant"

        mock_anthropic_client.messages.create.return_value = mock_response

        # Test each tier
        for tier, expected_model in MODEL_TIER_MAP.items():
            response = provider.invoke(prompt="Test", model=tier)
            call_kwargs = mock_anthropic_client.messages.create.call_args[1]
            assert call_kwargs["model"] == expected_model

    def test_invoke_with_full_model_name(self, provider, mock_anthropic_client):
        """Test invocation with full model name."""
        mock_response = Mock()
        mock_response.content = [Mock(text="Response")]
        mock_response.usage = Mock(input_tokens=5, output_tokens=10)
        mock_response.stop_reason = "end_turn"
        mock_response.id = "msg_123"
        mock_response.type = "message"
        mock_response.role = "assistant"

        mock_anthropic_client.messages.create.return_value = mock_response

        response = provider.invoke(prompt="Test", model="claude-opus-4-6")
        call_kwargs = mock_anthropic_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-opus-4-6"

    def test_invoke_with_caching(self, provider, mock_anthropic_client):
        """Test invocation with prompt caching enabled."""
        provider.enable_caching = True

        mock_response = Mock()
        mock_response.content = [Mock(text="Response")]
        mock_response.usage = Mock(
            input_tokens=5,
            output_tokens=10,
            cache_read_input_tokens=100,
            cache_creation_input_tokens=50,
        )
        mock_response.stop_reason = "end_turn"
        mock_response.id = "msg_123"
        mock_response.type = "message"
        mock_response.role = "assistant"

        mock_anthropic_client.messages.create.return_value = mock_response

        response = provider.invoke(
            prompt="Test",
            system_prompt="System"
        )

        # Check caching was used
        call_kwargs = mock_anthropic_client.messages.create.call_args[1]
        assert isinstance(call_kwargs["system"], list)
        assert call_kwargs["system"][0]["cache_control"]["type"] == "ephemeral"

        # Check cache tokens in response
        assert response.usage.cache_read_tokens == 100
        assert response.usage.cache_write_tokens == 50

    def test_invoke_authentication_error(self, provider, mock_anthropic_client):
        """Test authentication error handling."""
        import anthropic
        mock_anthropic_client.messages.create.side_effect = anthropic.AuthenticationError("Invalid API key")

        with pytest.raises(AuthenticationError) as exc_info:
            provider.invoke(prompt="Test")

        assert "authentication failed" in str(exc_info.value).lower()

    def test_invoke_rate_limit_error(self, provider, mock_anthropic_client):
        """Test rate limit error handling."""
        import anthropic

        # Mock rate limit error
        rate_limit_error = anthropic.RateLimitError("Rate limit exceeded")
        rate_limit_error.response = Mock()
        rate_limit_error.response.headers.get.return_value = "60"  # retry-after

        mock_anthropic_client.messages.create.side_effect = rate_limit_error

        with pytest.raises(RateLimitError) as exc_info:
            provider.invoke(prompt="Test")

        assert exc_info.value.retry_after == 60

    def test_invoke_rate_limit_with_retry(self, provider, mock_anthropic_client):
        """Test rate limit with successful retry."""
        import anthropic

        # First call fails, second succeeds
        mock_response = Mock()
        mock_response.content = [Mock(text="Success")]
        mock_response.usage = Mock(input_tokens=5, output_tokens=10)
        mock_response.stop_reason = "end_turn"
        mock_response.id = "msg_123"
        mock_response.type = "message"
        mock_response.role = "assistant"

        rate_limit_error = anthropic.RateLimitError("Rate limit")
        rate_limit_error.response = Mock()
        rate_limit_error.response.headers.get.return_value = None

        mock_anthropic_client.messages.create.side_effect = [
            rate_limit_error,
            mock_response
        ]

        with patch("time.sleep"):  # Mock sleep to speed up test
            response = provider.invoke(prompt="Test")

        assert response.content == "Success"

    def test_invoke_timeout_error(self, provider, mock_anthropic_client):
        """Test timeout error handling."""
        import anthropic
        mock_anthropic_client.messages.create.side_effect = anthropic.APITimeoutError("Timeout")

        with pytest.raises(TimeoutError):
            provider.invoke(prompt="Test")

    def test_invoke_model_not_found(self, provider, mock_anthropic_client):
        """Test model not found error."""
        import anthropic
        mock_anthropic_client.messages.create.side_effect = anthropic.NotFoundError("Model not found")

        with pytest.raises(ModelNotFoundError):
            provider.invoke(prompt="Test", model="invalid-model")

    def test_invoke_api_error(self, provider, mock_anthropic_client):
        """Test general API error."""
        import anthropic
        mock_anthropic_client.messages.create.side_effect = anthropic.APIError("API error")

        with pytest.raises(APIError):
            provider.invoke(prompt="Test")


class TestAnthropicProviderStream:
    """Test streaming method."""

    def test_stream_basic(self, provider, mock_anthropic_client):
        """Test basic streaming."""
        # Mock stream
        mock_stream = MagicMock()
        mock_stream.__enter__ = Mock(return_value=mock_stream)
        mock_stream.__exit__ = Mock(return_value=False)
        mock_stream.text_stream = ["Hello", " ", "world", "!"]

        mock_anthropic_client.messages.stream.return_value = mock_stream

        # Stream
        chunks = list(provider.stream(
            prompt="Test prompt",
            system_prompt="System",
            model="sonnet"
        ))

        # Assertions
        assert chunks == ["Hello", " ", "world", "!"]

        # Check API was called
        mock_anthropic_client.messages.stream.assert_called_once()

    def test_stream_authentication_error(self, provider, mock_anthropic_client):
        """Test streaming authentication error."""
        import anthropic

        mock_stream = MagicMock()
        mock_stream.__enter__ = Mock(side_effect=anthropic.AuthenticationError("Invalid key"))

        mock_anthropic_client.messages.stream.return_value = mock_stream

        with pytest.raises(AuthenticationError):
            list(provider.stream(prompt="Test"))

    def test_stream_rate_limit_error(self, provider, mock_anthropic_client):
        """Test streaming rate limit error."""
        import anthropic

        mock_stream = MagicMock()
        mock_stream.__enter__ = Mock(side_effect=anthropic.RateLimitError("Rate limit"))

        mock_anthropic_client.messages.stream.return_value = mock_stream

        with pytest.raises(RateLimitError):
            list(provider.stream(prompt="Test"))


class TestAnthropicProviderValidation:
    """Test model validation."""

    def test_validate_model_tier_names(self, provider):
        """Test validation of tier names."""
        assert provider.validate_model("opus") is True
        assert provider.validate_model("sonnet") is True
        assert provider.validate_model("haiku") is True

    def test_validate_model_full_names(self, provider):
        """Test validation of full model names."""
        for model in CLAUDE_MODELS:
            assert provider.validate_model(model) is True

    def test_validate_model_invalid(self, provider):
        """Test validation of invalid models."""
        assert provider.validate_model("invalid-model") is False
        assert provider.validate_model("gpt-4") is False


class TestAnthropicProviderTokenCount:
    """Test token counting."""

    def test_get_token_count_with_api(self, provider, mock_anthropic_client):
        """Test token count with API."""
        mock_anthropic_client.count_tokens.return_value = 42

        count = provider.get_token_count("Test text")

        assert count == 42
        mock_anthropic_client.count_tokens.assert_called_once_with("Test text")

    def test_get_token_count_fallback(self, provider, mock_anthropic_client):
        """Test token count fallback when API fails."""
        mock_anthropic_client.count_tokens.side_effect = Exception("API error")

        text = "A" * 100  # 100 characters
        count = provider.get_token_count(text)

        # Should use fallback (4 chars per token)
        assert count == 25


class TestAnthropicProviderHealthCheck:
    """Test health check."""

    def test_health_check_healthy(self, provider, mock_anthropic_client):
        """Test healthy status."""
        mock_response = Mock()
        mock_response.content = [Mock(text="pong")]
        mock_anthropic_client.messages.create.return_value = mock_response

        status = provider.health_check()

        assert status == HealthStatus.HEALTHY

    def test_health_check_authentication_error(self, provider, mock_anthropic_client):
        """Test health check with authentication error."""
        import anthropic
        mock_anthropic_client.messages.create.side_effect = anthropic.AuthenticationError("Invalid key")

        status = provider.health_check()

        assert status == HealthStatus.UNAVAILABLE

    def test_health_check_api_error(self, provider, mock_anthropic_client):
        """Test health check with API error."""
        import anthropic
        mock_anthropic_client.messages.create.side_effect = anthropic.APIError("Service error")

        status = provider.health_check()

        assert status == HealthStatus.DEGRADED

    def test_health_check_unknown_error(self, provider, mock_anthropic_client):
        """Test health check with unknown error."""
        mock_anthropic_client.messages.create.side_effect = Exception("Unknown error")

        status = provider.health_check()

        assert status == HealthStatus.UNAVAILABLE


class TestAnthropicProviderUtilities:
    """Test utility methods."""

    def test_get_supported_models(self, provider):
        """Test get supported models."""
        models = provider.get_supported_models()

        assert isinstance(models, list)
        assert len(models) > 0
        assert "claude-sonnet-4-5" in models
        assert "claude-opus-4-6" in models

    def test_get_default_model(self, provider):
        """Test get default model."""
        assert provider.get_default_model() == "claude-sonnet-4-5"

    def test_repr(self, provider):
        """Test string representation."""
        repr_str = repr(provider)
        assert "AnthropicProvider" in repr_str
        assert "anthropic" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
