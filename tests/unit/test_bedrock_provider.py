#!/usr/bin/env python3
"""
Unit tests for AWS Bedrock Provider.

Tests all functionality with mocked boto3 calls.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import provider classes
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Mock boto3 and botocore modules before importing provider
mock_boto3 = Mock()
mock_botocore = Mock()
mock_botocore.exceptions = Mock()
mock_botocore.exceptions.ClientError = type('ClientError', (Exception,), {
    '__init__': lambda self, error_response, operation_name: setattr(self, 'response', error_response) or Exception.__init__(self)
})
mock_botocore.exceptions.BotoCoreError = type('BotoCoreError', (Exception,), {})

sys.modules['boto3'] = mock_boto3
sys.modules['botocore'] = mock_botocore
sys.modules['botocore.exceptions'] = mock_botocore.exceptions

from core.llm.bedrock import BedrockProvider, BEDROCK_CLAUDE_MODELS, BEDROCK_TIER_MAP
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

# Get the ClientError/BotoCoreError that bedrock.py actually imported — this may
# be the real botocore class if another test loaded the module first, or our mock
# if we got here first.  Using the same class ensures `except ClientError` matches.
import core.llm.bedrock as _bedrock_mod
ClientError = getattr(_bedrock_mod, 'ClientError', mock_botocore.exceptions.ClientError)
BotoCoreError = getattr(_bedrock_mod, 'BotoCoreError', mock_botocore.exceptions.BotoCoreError)


@pytest.fixture
def mock_boto3_session():
    """Mock boto3 session."""
    mock_session = Mock()
    mock_client = Mock()
    mock_session.client.return_value = mock_client

    with patch("core.llm.bedrock.boto3.Session", return_value=mock_session):
        yield mock_session, mock_client


@pytest.fixture
def provider(mock_boto3_session):
    """Create Bedrock provider with mocked client."""
    mock_session, mock_client = mock_boto3_session

    with patch.dict("os.environ", {"AWS_REGION": "us-east-1"}):
        with patch("core.llm.bedrock.boto3.Session", return_value=mock_session):
            provider = BedrockProvider()
            return provider


class TestBedrockProviderInitialization:
    """Test provider initialization."""

    def test_init_basic(self, mock_boto3_session):
        """Test basic initialization."""
        with patch.dict("os.environ", {"AWS_REGION": "us-east-1"}):
            provider = BedrockProvider()
            assert provider.provider_name == "aws-bedrock"
            assert provider.region == "us-east-1"

    def test_init_with_custom_region(self, mock_boto3_session):
        """Test initialization with custom region."""
        provider = BedrockProvider(config={"aws_region": "us-west-2"})
        assert provider.region == "us-west-2"

    def test_init_with_profile(self, mock_boto3_session):
        """Test initialization with AWS profile."""
        mock_session, _ = mock_boto3_session

        provider = BedrockProvider(config={"aws_profile": "test-profile"})

        # Check session was created with profile
        mock_session_class = mock_boto3_session[0].__class__
        # Boto3.Session should have been called with profile_name

    def test_init_with_credentials(self, mock_boto3_session):
        """Test initialization with explicit credentials."""
        config = {
            "aws_access_key_id": "test-key",
            "aws_secret_access_key": "test-secret",
        }
        provider = BedrockProvider(config=config)

    def test_init_with_custom_config(self, mock_boto3_session):
        """Test initialization with custom configuration."""
        config = {
            "aws_region": "eu-west-1",
            "default_model": "anthropic.claude-3-opus-20240229-v1:0",
            "timeout": 600,
            "max_retries": 5,
        }
        provider = BedrockProvider(config=config)
        assert provider.region == "eu-west-1"
        assert provider.default_model == "anthropic.claude-3-opus-20240229-v1:0"
        assert provider.timeout == 600
        assert provider.max_retries == 5


class TestBedrockProviderInvoke:
    """Test invoke method."""

    def test_invoke_basic(self, provider, mock_boto3_session):
        """Test basic invocation."""
        _, mock_client = mock_boto3_session

        # Mock response
        mock_response_body = {
            "id": "msg-123",
            "type": "message",
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Test response"}
            ],
            "usage": {
                "input_tokens": 10,
                "output_tokens": 20
            },
            "stop_reason": "end_turn"
        }

        mock_response = {
            "body": Mock()
        }
        mock_response["body"].read.return_value = json.dumps(mock_response_body).encode()

        mock_client.invoke_model.return_value = mock_response

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
        assert response.model == "anthropic.claude-sonnet-4-5-20250929-v1:0"  # Resolved from tier
        assert response.provider == "aws-bedrock"
        assert response.usage.input_tokens == 10
        assert response.usage.output_tokens == 20
        assert response.finish_reason == "end_turn"

        # Check API was called correctly
        mock_client.invoke_model.assert_called_once()
        call_kwargs = mock_client.invoke_model.call_args[1]
        assert call_kwargs["modelId"] == "anthropic.claude-sonnet-4-5-20250929-v1:0"

        # Check request body
        request_body = json.loads(call_kwargs["body"])
        assert request_body["messages"][0]["content"] == "Test prompt"
        assert request_body["system"] == "System prompt"
        assert request_body["max_tokens"] == 100
        assert request_body["temperature"] == 0.5

    def test_invoke_with_tier_name(self, provider, mock_boto3_session):
        """Test invocation with tier name."""
        _, mock_client = mock_boto3_session

        mock_response_body = {
            "content": [{"type": "text", "text": "Response"}],
            "usage": {"input_tokens": 5, "output_tokens": 10},
            "stop_reason": "end_turn"
        }

        mock_response = {"body": Mock()}
        mock_response["body"].read.return_value = json.dumps(mock_response_body).encode()
        mock_client.invoke_model.return_value = mock_response

        # Test each tier
        for tier, expected_model in BEDROCK_TIER_MAP.items():
            response = provider.invoke(prompt="Test", model=tier)
            call_kwargs = mock_client.invoke_model.call_args[1]
            assert call_kwargs["modelId"] == expected_model

    def test_invoke_with_full_model_id(self, provider, mock_boto3_session):
        """Test invocation with full model ID."""
        _, mock_client = mock_boto3_session

        mock_response_body = {
            "content": [{"type": "text", "text": "Response"}],
            "usage": {"input_tokens": 5, "output_tokens": 10},
            "stop_reason": "end_turn"
        }

        mock_response = {"body": Mock()}
        mock_response["body"].read.return_value = json.dumps(mock_response_body).encode()
        mock_client.invoke_model.return_value = mock_response

        response = provider.invoke(
            prompt="Test",
            model="anthropic.claude-3-opus-20240229-v1:0"
        )

        call_kwargs = mock_client.invoke_model.call_args[1]
        assert call_kwargs["modelId"] == "anthropic.claude-3-opus-20240229-v1:0"

    def test_invoke_access_denied_error(self, provider, mock_boto3_session):
        """Test access denied error."""

        _, mock_client = mock_boto3_session

        error_response = {"Error": {"Code": "AccessDeniedException"}}
        mock_client.invoke_model.side_effect = ClientError(error_response, "InvokeModel")

        with pytest.raises(AuthenticationError) as exc_info:
            provider.invoke(prompt="Test")

        assert "access denied" in str(exc_info.value).lower()

    def test_invoke_throttling_error(self, provider, mock_boto3_session):
        """Test throttling error."""

        _, mock_client = mock_boto3_session

        error_response = {"Error": {"Code": "ThrottlingException"}}
        mock_client.invoke_model.side_effect = ClientError(error_response, "InvokeModel")

        with pytest.raises(RateLimitError):
            provider.invoke(prompt="Test")

    def test_invoke_throttling_with_retry(self, provider, mock_boto3_session):
        """Test throttling with successful retry."""

        _, mock_client = mock_boto3_session

        # First call fails, second succeeds
        mock_response_body = {
            "content": [{"type": "text", "text": "Success"}],
            "usage": {"input_tokens": 5, "output_tokens": 10},
            "stop_reason": "end_turn"
        }

        mock_response = {"body": Mock()}
        mock_response["body"].read.return_value = json.dumps(mock_response_body).encode()

        error_response = {"Error": {"Code": "ThrottlingException"}}
        mock_client.invoke_model.side_effect = [
            ClientError(error_response, "InvokeModel"),
            mock_response
        ]

        with patch("time.sleep"):  # Mock sleep
            response = provider.invoke(prompt="Test")

        assert response.content == "Success"

    def test_invoke_model_not_ready(self, provider, mock_boto3_session):
        """Test model not ready error."""

        _, mock_client = mock_boto3_session

        error_response = {"Error": {"Code": "ModelNotReadyException"}}
        mock_client.invoke_model.side_effect = ClientError(error_response, "InvokeModel")

        with pytest.raises(ModelNotFoundError):
            provider.invoke(prompt="Test")

    def test_invoke_resource_not_found(self, provider, mock_boto3_session):
        """Test resource not found error."""

        _, mock_client = mock_boto3_session

        error_response = {"Error": {"Code": "ResourceNotFoundException"}}
        mock_client.invoke_model.side_effect = ClientError(error_response, "InvokeModel")

        with pytest.raises(ModelNotFoundError):
            provider.invoke(prompt="Test", model="invalid-model")

    def test_invoke_service_unavailable(self, provider, mock_boto3_session):
        """Test service unavailable error."""

        _, mock_client = mock_boto3_session

        error_response = {"Error": {"Code": "ServiceUnavailableException"}}
        mock_client.invoke_model.side_effect = ClientError(error_response, "InvokeModel")

        with pytest.raises(APIError):
            provider.invoke(prompt="Test")

    def test_invoke_botocore_error(self, provider, mock_boto3_session):
        """Test botocore connection error."""

        _, mock_client = mock_boto3_session

        mock_client.invoke_model.side_effect = BotoCoreError()

        with pytest.raises(APIError):
            provider.invoke(prompt="Test")


class TestBedrockProviderStream:
    """Test streaming method."""

    def test_stream_basic(self, provider, mock_boto3_session):
        """Test basic streaming."""
        _, mock_client = mock_boto3_session

        # Mock streaming response
        mock_events = [
            {
                "chunk": {
                    "bytes": json.dumps({
                        "type": "content_block_delta",
                        "delta": {"type": "text_delta", "text": "Hello"}
                    }).encode()
                }
            },
            {
                "chunk": {
                    "bytes": json.dumps({
                        "type": "content_block_delta",
                        "delta": {"type": "text_delta", "text": " world"}
                    }).encode()
                }
            },
            {
                "chunk": {
                    "bytes": json.dumps({
                        "type": "content_block_delta",
                        "delta": {"type": "text_delta", "text": "!"}
                    }).encode()
                }
            },
        ]

        mock_response = {"body": iter(mock_events)}
        mock_client.invoke_model_with_response_stream.return_value = mock_response

        # Stream
        chunks = list(provider.stream(
            prompt="Test prompt",
            system_prompt="System",
            model="sonnet"
        ))

        # Assertions
        assert chunks == ["Hello", " world", "!"]

    def test_stream_access_denied(self, provider, mock_boto3_session):
        """Test streaming access denied error."""

        _, mock_client = mock_boto3_session

        error_response = {"Error": {"Code": "AccessDeniedException"}}
        mock_client.invoke_model_with_response_stream.side_effect = ClientError(
            error_response, "InvokeModelWithResponseStream"
        )

        with pytest.raises(AuthenticationError):
            list(provider.stream(prompt="Test"))

    def test_stream_throttling(self, provider, mock_boto3_session):
        """Test streaming throttling error."""

        _, mock_client = mock_boto3_session

        error_response = {"Error": {"Code": "ThrottlingException"}}
        mock_client.invoke_model_with_response_stream.side_effect = ClientError(
            error_response, "InvokeModelWithResponseStream"
        )

        with pytest.raises(RateLimitError):
            list(provider.stream(prompt="Test"))


class TestBedrockProviderValidation:
    """Test model validation."""

    def test_validate_model_tier_names(self, provider):
        """Test validation of tier names."""
        assert provider.validate_model("opus") is True
        assert provider.validate_model("sonnet") is True
        assert provider.validate_model("haiku") is True

    def test_validate_model_full_ids(self, provider):
        """Test validation of full model IDs."""
        for model in BEDROCK_CLAUDE_MODELS:
            assert provider.validate_model(model) is True

    def test_validate_model_invalid(self, provider):
        """Test validation of invalid models."""
        assert provider.validate_model("invalid-model") is False
        assert provider.validate_model("gpt-4") is False


class TestBedrockProviderTokenCount:
    """Test token counting."""

    def test_get_token_count_approximation(self, provider):
        """Test token count approximation."""
        text = "A" * 100  # 100 characters
        count = provider.get_token_count(text)

        # Should use approximation (4 chars per token)
        assert count == 25


class TestBedrockProviderHealthCheck:
    """Test health check."""

    def test_health_check_healthy(self, provider, mock_boto3_session):
        """Test healthy status."""
        mock_session, _ = mock_boto3_session

        # Mock bedrock client (not bedrock-runtime)
        mock_bedrock_client = Mock()
        mock_bedrock_client.list_foundation_models.return_value = {
            "modelSummaries": [
                {"modelId": "anthropic.claude-3-sonnet-20240229-v1:0"}
            ]
        }

        # Make session.client return different clients based on service_name
        def client_side_effect(service_name, **kwargs):
            if service_name == "bedrock":
                return mock_bedrock_client
            return Mock()

        mock_session.client.side_effect = client_side_effect

        status = provider.health_check()

        assert status == HealthStatus.HEALTHY

    def test_health_check_access_denied(self, provider, mock_boto3_session):
        """Test health check with access denied."""

        mock_session, _ = mock_boto3_session

        mock_bedrock_client = Mock()
        error_response = {"Error": {"Code": "AccessDeniedException"}}
        mock_bedrock_client.list_foundation_models.side_effect = ClientError(
            error_response, "ListFoundationModels"
        )

        def client_side_effect(service_name, **kwargs):
            if service_name == "bedrock":
                return mock_bedrock_client
            return Mock()

        mock_session.client.side_effect = client_side_effect

        status = provider.health_check()

        assert status == HealthStatus.UNAVAILABLE

    def test_health_check_degraded(self, provider, mock_boto3_session):
        """Test health check degraded status."""

        mock_session, _ = mock_boto3_session

        mock_bedrock_client = Mock()
        error_response = {"Error": {"Code": "ServiceException"}}
        mock_bedrock_client.list_foundation_models.side_effect = ClientError(
            error_response, "ListFoundationModels"
        )

        def client_side_effect(service_name, **kwargs):
            if service_name == "bedrock":
                return mock_bedrock_client
            return Mock()

        mock_session.client.side_effect = client_side_effect

        status = provider.health_check()

        assert status == HealthStatus.DEGRADED

    def test_health_check_unknown_error(self, provider, mock_boto3_session):
        """Test health check with unknown error."""
        mock_session, _ = mock_boto3_session

        mock_bedrock_client = Mock()
        mock_bedrock_client.list_foundation_models.side_effect = Exception("Unknown error")

        def client_side_effect(service_name, **kwargs):
            if service_name == "bedrock":
                return mock_bedrock_client
            return Mock()

        mock_session.client.side_effect = client_side_effect

        status = provider.health_check()

        assert status == HealthStatus.UNAVAILABLE


class TestBedrockProviderUtilities:
    """Test utility methods."""

    def test_get_supported_models(self, provider):
        """Test get supported models."""
        models = provider.get_supported_models()

        assert isinstance(models, list)
        assert len(models) > 0
        assert "anthropic.claude-3-5-sonnet-20241022-v2:0" in models
        assert "anthropic.claude-3-opus-20240229-v1:0" in models

    def test_get_default_model(self, provider):
        """Test get default model."""
        assert provider.get_default_model() == "anthropic.claude-3-5-sonnet-20241022-v2:0"

    def test_repr(self, provider):
        """Test string representation."""
        repr_str = repr(provider)
        assert "BedrockProvider" in repr_str
        assert "aws-bedrock" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
