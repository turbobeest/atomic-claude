#!/usr/bin/env python3
"""
Unit tests for LLM Types.

Tests Pydantic models and dataclasses.
"""

import pytest
from datetime import datetime

from core.llm.types import (
    ModelRole,
    ProviderType,
    HealthStatus,
    LLMRequest,
    LLMResponse,
    UsageStats,
    ModelInfo,
    ProviderHealth,
)


class TestLLMTypes:
    """Test suite for LLM types."""

    def test_model_role_enum(self):
        """Test ModelRole enum."""
        assert ModelRole.PRIMARY == "primary"
        assert ModelRole.FAST == "fast"
        assert ModelRole.GARDENER == "gardener"
        assert ModelRole.HEAVYWEIGHT == "heavyweight"

    def test_provider_type_enum(self):
        """Test ProviderType enum."""
        assert ProviderType.ANTHROPIC == "anthropic"
        assert ProviderType.BEDROCK == "bedrock"
        assert ProviderType.OLLAMA == "ollama"
        assert ProviderType.OPENAI == "openai"
        assert ProviderType.GOOGLE == "google"

    def test_health_status_enum(self):
        """Test HealthStatus enum."""
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNAVAILABLE == "unavailable"
        assert HealthStatus.UNKNOWN == "unknown"

    def test_llm_request_creation(self):
        """Test LLMRequest creation."""
        request = LLMRequest(
            prompt="test prompt",
            system_prompt="system",
            model="gpt-4",
            max_tokens=100,
            temperature=0.7,
            timeout=300,
            stream=False,
            metadata={"key": "value"}
        )

        assert request.prompt == "test prompt"
        assert request.system_prompt == "system"
        assert request.model == "gpt-4"
        assert request.max_tokens == 100
        assert request.temperature == 0.7
        assert request.timeout == 300
        assert request.stream is False
        assert request.metadata["key"] == "value"

    def test_llm_request_defaults(self):
        """Test LLMRequest default values."""
        request = LLMRequest(prompt="test")

        assert request.prompt == "test"
        assert request.system_prompt is None
        assert request.model is None
        assert request.max_tokens == 4096
        assert request.temperature == 1.0
        assert request.timeout == 300
        assert request.stream is False
        assert request.metadata == {}

    def test_llm_response_creation(self):
        """Test LLMResponse creation."""
        response = LLMResponse(
            content="test response",
            model="gpt-4",
            provider="openai",
            usage={"input_tokens": 10, "output_tokens": 20},
            finish_reason="stop",
            latency_ms=100,
        )

        assert response.content == "test response"
        assert response.model == "gpt-4"
        assert response.provider == "openai"
        assert response.usage["input_tokens"] == 10
        assert response.usage["output_tokens"] == 20
        assert response.finish_reason == "stop"
        assert response.latency_ms == 100

    def test_usage_stats_creation(self):
        """Test UsageStats creation."""
        stats = UsageStats(
            input_tokens=100,
            output_tokens=200,
            cache_read_tokens=50,
            cache_write_tokens=25,
            total_requests=10,
            failed_requests=2,
            avg_latency_ms=150.5,
        )

        assert stats.input_tokens == 100
        assert stats.output_tokens == 200
        assert stats.cache_read_tokens == 50
        assert stats.cache_write_tokens == 25
        assert stats.total_requests == 10
        assert stats.failed_requests == 2
        assert stats.avg_latency_ms == 150.5

    def test_usage_stats_total_tokens(self):
        """Test UsageStats total_tokens property."""
        stats = UsageStats(
            input_tokens=100,
            output_tokens=200,
        )

        assert stats.total_tokens == 300

    def test_usage_stats_success_rate(self):
        """Test UsageStats success_rate property."""
        stats = UsageStats(
            total_requests=10,
            failed_requests=2,
        )

        assert stats.success_rate == 0.8

        # Zero requests
        stats_zero = UsageStats()
        assert stats_zero.success_rate == 0.0

    def test_model_info_creation(self):
        """Test ModelInfo creation."""
        info = ModelInfo(
            name="gpt-4",
            provider="openai",
            context_window=8192,
            max_output_tokens=4096,
            supports_streaming=True,
            supports_vision=True,
            supports_tools=True,
            cost_per_1k_input=0.03,
            cost_per_1k_output=0.06,
            tier="premium",
        )

        assert info.name == "gpt-4"
        assert info.provider == "openai"
        assert info.context_window == 8192
        assert info.max_output_tokens == 4096
        assert info.supports_streaming is True
        assert info.supports_vision is True
        assert info.supports_tools is True
        assert info.cost_per_1k_input == 0.03
        assert info.cost_per_1k_output == 0.06
        assert info.tier == "premium"

    def test_model_info_defaults(self):
        """Test ModelInfo default values."""
        info = ModelInfo(
            name="test-model",
            provider="test",
            context_window=4096,
            max_output_tokens=2048,
        )

        assert info.supports_streaming is True
        assert info.supports_vision is False
        assert info.supports_tools is False
        assert info.cost_per_1k_input is None
        assert info.cost_per_1k_output is None
        assert info.tier is None

    def test_provider_health_creation(self):
        """Test ProviderHealth creation."""
        health = ProviderHealth(
            provider="anthropic",
            status=HealthStatus.HEALTHY,
            available=True,
            last_check=datetime.now(),
            error_message=None,
            metadata={"region": "us-east-1"},
        )

        assert health.provider == "anthropic"
        assert health.status == HealthStatus.HEALTHY
        assert health.available is True
        assert isinstance(health.last_check, datetime)
        assert health.error_message is None
        assert health.metadata["region"] == "us-east-1"

    def test_provider_health_unavailable(self):
        """Test ProviderHealth for unavailable provider."""
        health = ProviderHealth(
            provider="test",
            status=HealthStatus.UNAVAILABLE,
            available=False,
            error_message="Connection timeout",
        )

        assert health.status == HealthStatus.UNAVAILABLE
        assert health.available is False
        assert health.error_message == "Connection timeout"
