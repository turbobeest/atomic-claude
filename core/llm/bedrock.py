#!/usr/bin/env python3
"""
ATOMIC CLAUDE - AWS Bedrock Provider

AWS Bedrock provider implementation using boto3.
"""

import json
import os
import time
from typing import Dict, Generator, Optional, Any

try:
    import boto3
    from botocore.exceptions import ClientError, BotoCoreError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from .base import (
    BaseLLMProvider,
    LLMResponse,
    TokenUsage,
    HealthStatus,
    AuthenticationError,
    RateLimitError,
    TimeoutError,
    APIError,
    ModelNotFoundError,
)


# Supported Bedrock Claude models
BEDROCK_CLAUDE_MODELS = [
    "anthropic.claude-3-opus-20240229-v1:0",
    "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "anthropic.claude-3-sonnet-20240229-v1:0",
    "anthropic.claude-3-haiku-20240307-v1:0",
    "anthropic.claude-v2:1",
    "anthropic.claude-v2",
]

# Model tier mapping for Bedrock
BEDROCK_TIER_MAP = {
    "opus": "anthropic.claude-opus-4-6-20250219-v1:0",
    "sonnet": "anthropic.claude-sonnet-4-5-20250929-v1:0",
    "haiku": "anthropic.claude-haiku-4-5-20251001-v1:0",
}


class BedrockProvider(BaseLLMProvider):
    """
    AWS Bedrock provider using boto3.

    Features:
    - Claude models via Bedrock
    - Request/response format translation (AWS ↔ Anthropic)
    - Regional endpoint support
    - IAM authentication (AWS credentials)
    - Streaming support
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Bedrock provider.

        Args:
            config: Configuration dict with:
                - aws_region: AWS region (default: us-east-1)
                - aws_access_key_id: AWS access key (or uses AWS_ACCESS_KEY_ID env)
                - aws_secret_access_key: AWS secret key (or uses AWS_SECRET_ACCESS_KEY env)
                - aws_profile: AWS profile name (optional)
                - default_model: Default model (default: anthropic.claude-3-5-sonnet-20241022-v2:0)
                - timeout: Default timeout (default: 300)
                - max_retries: Max retry attempts (default: 3)
        """
        super().__init__(config)
        self.provider_name = "aws-bedrock"

        if not BOTO3_AVAILABLE:
            raise ImportError(
                "boto3 package not installed. "
                "Install with: pip install boto3"
            )

        # Configuration
        self.region = self.config.get("aws_region") or os.environ.get("AWS_REGION", "us-east-1")
        self.default_model = self.config.get(
            "default_model",
            "anthropic.claude-3-5-sonnet-20241022-v2:0"
        )
        self.timeout = self.config.get("timeout", 300)
        self.max_retries = self.config.get("max_retries", 3)

        # Build session kwargs
        session_kwargs = {}

        # AWS profile (optional)
        aws_profile = self.config.get("aws_profile") or os.environ.get("AWS_PROFILE")
        if aws_profile:
            session_kwargs["profile_name"] = aws_profile

        # AWS credentials (optional - boto3 will use default credential chain)
        aws_access_key = self.config.get("aws_access_key_id") or os.environ.get("AWS_ACCESS_KEY_ID")
        aws_secret_key = self.config.get("aws_secret_access_key") or os.environ.get("AWS_SECRET_ACCESS_KEY")

        if aws_access_key and aws_secret_key:
            session_kwargs["aws_access_key_id"] = aws_access_key
            session_kwargs["aws_secret_access_key"] = aws_secret_key

        # Create boto3 session
        try:
            if session_kwargs:
                self.session = boto3.Session(**session_kwargs)
            else:
                self.session = boto3.Session()

            # Create bedrock-runtime client
            self.client = self.session.client(
                service_name="bedrock-runtime",
                region_name=self.region
            )

        except Exception as e:
            raise AuthenticationError(
                f"Failed to initialize AWS Bedrock client: {str(e)}",
                provider="aws-bedrock"
            )

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
        Invoke AWS Bedrock with prompt.

        Args:
            prompt: User message
            system_prompt: Optional system prompt
            model: Model name (or tier)
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            timeout: Request timeout
            **kwargs: Additional parameters

        Returns:
            LLMResponse with content and metadata

        Raises:
            AuthenticationError: IAM authentication failed
            RateLimitError: Throttling exception
            TimeoutError: Request timeout
            APIError: API errors
            ModelNotFoundError: Model not available
        """
        start_time = time.time()

        # Resolve model
        resolved_model = self._resolve_model(model)

        # Build request body (Anthropic format for Claude models)
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Add system prompt if provided
        if system_prompt:
            request_body["system"] = system_prompt

        # Merge additional kwargs
        for key, value in kwargs.items():
            if key not in ["model", "timeout"]:
                request_body[key] = value

        # Retry logic with exponential backoff
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                response = self.client.invoke_model(
                    modelId=resolved_model,
                    body=json.dumps(request_body),
                    contentType="application/json",
                    accept="application/json",
                )

                # Parse response body
                response_body = json.loads(response["body"].read())

                # Calculate latency
                latency_ms = int((time.time() - start_time) * 1000)

                # Extract usage
                usage_data = response_body.get("usage", {})
                usage = TokenUsage(
                    input_tokens=usage_data.get("input_tokens", 0),
                    output_tokens=usage_data.get("output_tokens", 0),
                )

                # Extract content
                content = ""
                for block in response_body.get("content", []):
                    if block.get("type") == "text":
                        content += block.get("text", "")

                return LLMResponse(
                    content=content,
                    model=resolved_model,
                    provider=self.provider_name,
                    usage=usage,
                    finish_reason=response_body.get("stop_reason"),
                    stop_reason=response_body.get("stop_reason"),
                    latency_ms=latency_ms,
                    metadata={
                        "id": response_body.get("id"),
                        "type": response_body.get("type"),
                        "role": response_body.get("role"),
                    }
                )

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")

                # Access denied
                if error_code == "AccessDeniedException":
                    raise AuthenticationError(
                        f"AWS Bedrock access denied: {str(e)}",
                        provider="aws-bedrock"
                    )

                # Throttling
                elif error_code == "ThrottlingException":
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue

                    raise RateLimitError(
                        f"AWS Bedrock throttling: {str(e)}",
                        provider="aws-bedrock"
                    )

                # Model not ready
                elif error_code == "ModelNotReadyException":
                    if attempt < self.max_retries - 1:
                        time.sleep(5)  # Wait longer for model to be ready
                        continue

                    raise ModelNotFoundError(
                        f"AWS Bedrock model not ready: {resolved_model}",
                        provider="aws-bedrock"
                    )

                # Resource not found
                elif error_code in ["ResourceNotFoundException", "ValidationException"]:
                    raise ModelNotFoundError(
                        f"AWS Bedrock model not found: {resolved_model}. Error: {str(e)}",
                        provider="aws-bedrock"
                    )

                # Service unavailable
                elif error_code == "ServiceUnavailableException":
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue

                    raise APIError(
                        f"AWS Bedrock service unavailable: {str(e)}",
                        provider="aws-bedrock",
                        error_code=error_code,
                        retryable=True
                    )

                # Other client errors
                last_exception = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue

                raise APIError(
                    f"AWS Bedrock API error: {str(e)}",
                    provider="aws-bedrock",
                    error_code=error_code
                )

            except BotoCoreError as e:
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue

                raise APIError(
                    f"AWS Bedrock connection error: {str(e)}",
                    provider="aws-bedrock",
                    error_code="connection_error",
                    retryable=True
                )

            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue

                raise APIError(
                    f"AWS Bedrock unexpected error: {str(e)}",
                    provider="aws-bedrock"
                )

        # All retries exhausted
        raise APIError(
            f"AWS Bedrock request failed after {self.max_retries} attempts: {str(last_exception)}",
            provider="aws-bedrock"
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
        Stream AWS Bedrock response.

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

        # Build request body
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Add system prompt if provided
        if system_prompt:
            request_body["system"] = system_prompt

        # Merge additional kwargs
        for key, value in kwargs.items():
            if key not in ["model", "timeout"]:
                request_body[key] = value

        try:
            response = self.client.invoke_model_with_response_stream(
                modelId=resolved_model,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json",
            )

            # Parse event stream
            stream = response.get("body")
            if stream:
                for event in stream:
                    chunk = event.get("chunk")
                    if chunk:
                        chunk_data = json.loads(chunk.get("bytes").decode())

                        # Extract text from delta
                        if chunk_data.get("type") == "content_block_delta":
                            delta = chunk_data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                text = delta.get("text", "")
                                if text:
                                    yield text

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")

            if error_code == "AccessDeniedException":
                raise AuthenticationError(
                    f"AWS Bedrock access denied: {str(e)}",
                    provider="aws-bedrock"
                )

            elif error_code == "ThrottlingException":
                raise RateLimitError(
                    f"AWS Bedrock throttling: {str(e)}",
                    provider="aws-bedrock"
                )

            else:
                raise APIError(
                    f"AWS Bedrock streaming error: {str(e)}",
                    provider="aws-bedrock",
                    error_code=error_code
                )

        except Exception as e:
            raise APIError(
                f"AWS Bedrock streaming error: {str(e)}",
                provider="aws-bedrock"
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
        if model_name in BEDROCK_TIER_MAP:
            return True

        # Check full model IDs
        return model_name in BEDROCK_CLAUDE_MODELS

    def get_token_count(self, text: str, model: Optional[str] = None) -> int:
        """
        Estimate token count for text.

        Bedrock doesn't provide direct token counting API, so we use approximation.

        Args:
            text: Input text
            model: Model name (optional)

        Returns:
            Estimated token count
        """
        # Rough estimate: 4 characters per token (Claude average)
        return len(text) // 4

    def health_check(self) -> HealthStatus:
        """
        Check AWS Bedrock health.

        Returns:
            HealthStatus
        """
        try:
            # List foundation models to verify access
            bedrock_client = self.session.client(
                service_name="bedrock",
                region_name=self.region
            )

            response = bedrock_client.list_foundation_models(
                byProvider="Anthropic"
            )

            if response and response.get("modelSummaries"):
                return HealthStatus.HEALTHY

            return HealthStatus.DEGRADED

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")

            if error_code == "AccessDeniedException":
                return HealthStatus.UNAVAILABLE

            return HealthStatus.DEGRADED

        except Exception:
            return HealthStatus.UNAVAILABLE

    def get_supported_models(self) -> list:
        """
        Get list of supported Bedrock Claude models.

        Returns:
            List of model IDs
        """
        return BEDROCK_CLAUDE_MODELS.copy()

    def get_default_model(self) -> str:
        """
        Get default model.

        Returns:
            Default model ID
        """
        return self.default_model

    def _resolve_model(self, model: Optional[str] = None) -> str:
        """
        Resolve model name (handles tier names like "sonnet").

        Args:
            model: Model name or tier

        Returns:
            Full Bedrock model ID
        """
        if not model:
            return self.default_model

        # Check if it's a tier name
        if model in BEDROCK_TIER_MAP:
            return BEDROCK_TIER_MAP[model]

        return model
