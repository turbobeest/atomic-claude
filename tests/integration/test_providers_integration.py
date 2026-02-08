#!/usr/bin/env python3
"""
Integration tests for LLM providers.

These tests can run against real APIs when credentials are available.
Mark with @pytest.mark.requires_llm to skip by default.
"""

import os
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.llm.anthropic import AnthropicProvider
from core.llm.bedrock import BedrockProvider
from core.llm.base import (
    LLMResponse,
    HealthStatus,
    AuthenticationError,
)


# Skip tests requiring real LLM API unless explicitly enabled
requires_llm = pytest.mark.skipif(
    os.environ.get("RUN_LLM_TESTS") != "1",
    reason="Requires real LLM API (set RUN_LLM_TESTS=1 to enable)"
)


class TestAnthropicIntegration:
    """Integration tests for Anthropic provider."""

    @requires_llm
    def test_anthropic_invoke_real(self):
        """Test real Anthropic API invocation."""
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")

        provider = AnthropicProvider()

        response = provider.invoke(
            prompt="What is 2+2? Answer with just the number.",
            model="haiku",  # Use cheapest model
            max_tokens=10,
            temperature=0.0
        )

        assert isinstance(response, LLMResponse)
        assert response.content
        assert "4" in response.content
        assert response.provider == "anthropic"
        assert response.usage.total_tokens > 0

    @requires_llm
    def test_anthropic_stream_real(self):
        """Test real Anthropic streaming."""
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")

        provider = AnthropicProvider()

        chunks = list(provider.stream(
            prompt="Count from 1 to 3.",
            model="haiku",
            max_tokens=20,
            temperature=0.0
        ))

        assert len(chunks) > 0
        full_response = "".join(chunks)
        assert full_response

    @requires_llm
    def test_anthropic_health_check_real(self):
        """Test real Anthropic health check."""
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")

        provider = AnthropicProvider()
        status = provider.health_check()

        assert status == HealthStatus.HEALTHY


class TestBedrockIntegration:
    """Integration tests for Bedrock provider."""

    @requires_llm
    def test_bedrock_invoke_real(self):
        """Test real Bedrock API invocation."""
        # Check for AWS credentials
        has_creds = (
            os.environ.get("AWS_ACCESS_KEY_ID") or
            os.environ.get("AWS_PROFILE")
        )

        if not has_creds:
            pytest.skip("AWS credentials not configured")

        try:
            provider = BedrockProvider()

            response = provider.invoke(
                prompt="What is 2+2? Answer with just the number.",
                model="haiku",  # Use cheapest model
                max_tokens=10,
                temperature=0.0
            )

            assert isinstance(response, LLMResponse)
            assert response.content
            assert "4" in response.content
            assert response.provider == "aws-bedrock"
            assert response.usage.total_tokens > 0

        except AuthenticationError:
            pytest.skip("AWS Bedrock not accessible in this region/account")

    @requires_llm
    def test_bedrock_stream_real(self):
        """Test real Bedrock streaming."""
        has_creds = (
            os.environ.get("AWS_ACCESS_KEY_ID") or
            os.environ.get("AWS_PROFILE")
        )

        if not has_creds:
            pytest.skip("AWS credentials not configured")

        try:
            provider = BedrockProvider()

            chunks = list(provider.stream(
                prompt="Count from 1 to 3.",
                model="haiku",
                max_tokens=20,
                temperature=0.0
            ))

            assert len(chunks) > 0
            full_response = "".join(chunks)
            assert full_response

        except AuthenticationError:
            pytest.skip("AWS Bedrock not accessible")

    @requires_llm
    def test_bedrock_health_check_real(self):
        """Test real Bedrock health check."""
        has_creds = (
            os.environ.get("AWS_ACCESS_KEY_ID") or
            os.environ.get("AWS_PROFILE")
        )

        if not has_creds:
            pytest.skip("AWS credentials not configured")

        try:
            provider = BedrockProvider()
            status = provider.health_check()

            assert status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]

        except AuthenticationError:
            pytest.skip("AWS Bedrock not accessible")


class TestProviderComparison:
    """Compare behavior across providers."""

    @requires_llm
    def test_consistent_responses(self):
        """Test that providers give consistent responses."""
        prompt = "What is the capital of France? Answer with just the city name."

        providers = []

        # Add Anthropic if available
        if os.environ.get("ANTHROPIC_API_KEY"):
            providers.append(("anthropic", AnthropicProvider()))

        # Add Bedrock if available
        has_aws_creds = (
            os.environ.get("AWS_ACCESS_KEY_ID") or
            os.environ.get("AWS_PROFILE")
        )
        if has_aws_creds:
            try:
                providers.append(("bedrock", BedrockProvider()))
            except AuthenticationError:
                pass

        if len(providers) < 2:
            pytest.skip("Need at least 2 providers configured")

        responses = {}

        for name, provider in providers:
            try:
                response = provider.invoke(
                    prompt=prompt,
                    model="haiku",
                    max_tokens=20,
                    temperature=0.0
                )
                responses[name] = response.content.strip().lower()
            except Exception as e:
                pytest.skip(f"Provider {name} failed: {e}")

        # All responses should contain "paris"
        for name, content in responses.items():
            assert "paris" in content, f"Provider {name} didn't mention Paris"

    @requires_llm
    def test_concurrent_requests(self):
        """Test concurrent requests to multiple providers."""
        import concurrent.futures

        providers = []

        if os.environ.get("ANTHROPIC_API_KEY"):
            providers.append(AnthropicProvider())

        if len(providers) == 0:
            pytest.skip("No providers configured")

        def make_request(provider, index):
            """Make a request to a provider."""
            return provider.invoke(
                prompt=f"Say the number {index}.",
                model="haiku",
                max_tokens=10,
                temperature=0.0
            )

        # Make 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(make_request, providers[0], i)
                for i in range(5)
            ]

            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == 5
        for result in results:
            assert isinstance(result, LLMResponse)
            assert result.content


class TestProviderPerformance:
    """Performance benchmarks for providers."""

    @requires_llm
    def test_invoke_latency(self):
        """Benchmark invocation latency."""
        import time

        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")

        provider = AnthropicProvider()

        start_time = time.time()

        response = provider.invoke(
            prompt="Say 'hello'.",
            model="haiku",
            max_tokens=10,
            temperature=0.0
        )

        elapsed_ms = (time.time() - start_time) * 1000

        assert response.content
        # Response should come back within reasonable time
        assert elapsed_ms < 10000, f"Response took {elapsed_ms}ms (too slow)"

        # Check reported latency is reasonable
        if response.latency_ms:
            assert response.latency_ms < elapsed_ms

    @requires_llm
    def test_streaming_first_token_latency(self):
        """Benchmark streaming first token latency."""
        import time

        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")

        provider = AnthropicProvider()

        start_time = time.time()

        # Get first chunk
        stream = provider.stream(
            prompt="Write a short sentence.",
            model="haiku",
            max_tokens=50,
            temperature=0.0
        )

        first_chunk = next(stream)
        first_token_ms = (time.time() - start_time) * 1000

        assert first_chunk
        # First token should arrive within reasonable time
        assert first_token_ms < 5000, f"First token took {first_token_ms}ms"


class TestErrorHandling:
    """Test error handling across providers."""

    def test_anthropic_invalid_api_key(self):
        """Test Anthropic with invalid API key."""
        provider = AnthropicProvider(config={"api_key": "invalid-key-12345"})

        with pytest.raises(AuthenticationError):
            provider.invoke(prompt="Test", model="haiku", max_tokens=10)

    def test_bedrock_invalid_credentials(self):
        """Test Bedrock with invalid credentials."""
        provider = BedrockProvider(config={
            "aws_access_key_id": "invalid",
            "aws_secret_access_key": "invalid"
        })

        # Health check should fail
        status = provider.health_check()
        assert status == HealthStatus.UNAVAILABLE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
