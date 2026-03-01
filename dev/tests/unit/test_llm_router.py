#!/usr/bin/env python3
"""
Unit tests for LLM Router.

Tests provider routing, fallback chains, circuit breaker, and health tracking.
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch

from core.llm.router import LLMRouter, RouterConfig
from core.llm.base import BaseLLMProvider, LLMResponse, TokenUsage, HealthStatus
from core.llm.exceptions import (
    ProviderUnavailableException,
    RateLimitException,
    TimeoutException,
)
from core.llm.types import ModelRole


class MockProvider(BaseLLMProvider):
    """Mock provider for testing."""

    def __init__(self, name="mock", fail=False, health=HealthStatus.HEALTHY):
        super().__init__()
        self.provider_name = name
        self._fail = fail
        self._health = health
        self.invoke_count = 0
        self.stream_count = 0

    def invoke(self, prompt, **kwargs):
        self.invoke_count += 1
        if self._fail:
            raise RateLimitException("Mock failure", provider=self.provider_name)

        return LLMResponse(
            content=f"Response from {self.provider_name}",
            model="mock-model",
            provider=self.provider_name,
            usage=TokenUsage(input_tokens=10, output_tokens=20),
        )

    def stream(self, prompt, **kwargs):
        self.stream_count += 1
        if self._fail:
            raise TimeoutException("Mock stream failure", provider=self.provider_name)
        yield f"Stream from {self.provider_name}"

    def validate_model(self, model_name):
        return True

    def get_token_count(self, text, model=None):
        return len(text) // 4

    def health_check(self):
        return self._health


class TestLLMRouter:
    """Test suite for LLM router."""

    @pytest.fixture
    def router(self):
        """Create router instance."""
        config = RouterConfig(
            enable_cache=False,  # Disable cache for clearer testing
            failure_threshold=3,
            cooldown_minutes=1,
        )
        return LLMRouter(config)

    @pytest.fixture
    def router_with_cache(self):
        """Create router with cache enabled."""
        config = RouterConfig(
            enable_cache=True,
            cache_ttl=2,
        )
        return LLMRouter(config)

    def test_router_initialization(self, router):
        """Test router initializes correctly."""
        assert router.config.failure_threshold == 3
        assert router.config.cooldown_minutes == 1
        assert not router.config.enable_cache

    def test_register_provider(self, router):
        """Test registering a provider."""
        provider = MockProvider("test_provider")
        router.register_provider("test", provider, [ModelRole.PRIMARY])

        assert "test" in router._providers
        assert "test" in router._roles[ModelRole.PRIMARY]

    def test_unregister_provider(self, router):
        """Test unregistering a provider."""
        provider = MockProvider()
        router.register_provider("test", provider, [ModelRole.PRIMARY])

        result = router.unregister_provider("test")
        assert result is True
        assert "test" not in router._providers
        assert "test" not in router._roles[ModelRole.PRIMARY]

        # Unregister non-existent
        result = router.unregister_provider("nonexistent")
        assert result is False

    def test_get_provider(self, router):
        """Test getting provider for a role."""
        provider1 = MockProvider("provider1")
        provider2 = MockProvider("provider2")

        router.register_provider("provider1", provider1, [ModelRole.PRIMARY])
        router.register_provider("provider2", provider2, [ModelRole.FAST])

        # Get primary provider
        result = router.get_provider("primary")
        assert result is not None
        assert result.provider_name == "provider1"

        # Get fast provider
        result = router.get_provider("fast")
        assert result is not None
        assert result.provider_name == "provider2"

    def test_invoke_basic(self, router):
        """Test basic invoke with single provider."""
        provider = MockProvider("test")
        router.register_provider("test", provider, [ModelRole.PRIMARY])

        response = router.invoke(
            role="primary",
            prompt="test prompt",
        )

        assert response is not None
        assert response.content == "Response from test"
        assert response.provider == "test"
        assert provider.invoke_count == 1

    def test_invoke_with_fallback(self, router):
        """Test invoke with fallback to second provider."""
        # Primary provider fails
        provider1 = MockProvider("provider1", fail=True)
        # Fallback provider succeeds
        provider2 = MockProvider("provider2", fail=False)

        router.register_provider("provider1", provider1, [ModelRole.PRIMARY])
        router.register_provider("provider2", provider2, [ModelRole.PRIMARY])

        # Configure fallback chain
        router.config.fallback_chains = {
            "primary": ["provider1", "provider2"]
        }

        response = router.invoke(
            role="primary",
            prompt="test prompt",
        )

        # Should fallback to provider2
        assert response is not None
        assert response.provider == "provider2"
        assert provider1.invoke_count == 1
        assert provider2.invoke_count == 1

    def test_invoke_all_providers_fail(self, router):
        """Test invoke when all providers fail."""
        provider1 = MockProvider("provider1", fail=True)
        provider2 = MockProvider("provider2", fail=True)

        router.register_provider("provider1", provider1, [ModelRole.PRIMARY])
        router.register_provider("provider2", provider2, [ModelRole.PRIMARY])

        router.config.fallback_chains = {
            "primary": ["provider1", "provider2"]
        }

        with pytest.raises(ProviderUnavailableException) as exc_info:
            router.invoke(role="primary", prompt="test")

        assert "All providers failed" in str(exc_info.value)

    def test_circuit_breaker(self, router):
        """Test circuit breaker disables provider after threshold."""
        provider = MockProvider("test", fail=True)
        router.register_provider("test", provider, [ModelRole.PRIMARY])

        # Fail 3 times (threshold)
        for i in range(3):
            try:
                router.invoke(role="primary", prompt="test")
            except ProviderUnavailableException:
                pass

        # Provider should be circuit broken
        assert not router._is_provider_available("test")
        failure = router._failures.get("test")
        assert failure is not None
        assert failure.failure_count >= 3
        assert failure.disabled_until is not None

    def test_circuit_breaker_cooldown(self, router):
        """Test circuit breaker re-enables after cooldown."""
        provider = MockProvider("test", fail=True)
        router.register_provider("test", provider, [ModelRole.PRIMARY])

        # Set very short cooldown
        router.config.cooldown_minutes = 0.01  # ~0.6 seconds

        # Trigger circuit breaker
        for i in range(3):
            try:
                router.invoke(role="primary", prompt="test")
            except:
                pass

        # Should be disabled
        assert not router._is_provider_available("test")

        # Wait for cooldown
        time.sleep(1)

        # Should be re-enabled
        assert router._is_provider_available("test")

    def test_stream_basic(self, router):
        """Test basic streaming."""
        provider = MockProvider("test")
        router.register_provider("test", provider, [ModelRole.PRIMARY])

        chunks = list(router.stream(role="primary", prompt="test"))

        assert len(chunks) > 0
        assert "Stream from test" in chunks[0]
        assert provider.stream_count == 1

    def test_stream_with_fallback(self, router):
        """Test streaming with fallback."""
        provider1 = MockProvider("provider1", fail=True)
        provider2 = MockProvider("provider2", fail=False)

        router.register_provider("provider1", provider1, [ModelRole.PRIMARY])
        router.register_provider("provider2", provider2, [ModelRole.PRIMARY])

        router.config.fallback_chains = {
            "primary": ["provider1", "provider2"]
        }

        chunks = list(router.stream(role="primary", prompt="test"))

        # Should fallback to provider2
        assert len(chunks) > 0
        assert "provider2" in chunks[0]

    def test_health_check(self, router):
        """Test health checking."""
        provider1 = MockProvider("provider1", health=HealthStatus.HEALTHY)
        provider2 = MockProvider("provider2", health=HealthStatus.DEGRADED)

        router.register_provider("provider1", provider1)
        router.register_provider("provider2", provider2)

        health = router.check_health()

        assert "provider1" in health
        assert "provider2" in health
        assert health["provider1"].status == HealthStatus.HEALTHY
        assert health["provider2"].status == HealthStatus.DEGRADED

    def test_usage_stats(self, router):
        """Test usage statistics tracking."""
        provider = MockProvider("test")
        router.register_provider("test", provider, [ModelRole.PRIMARY])

        # Make several requests
        for i in range(5):
            router.invoke(role="primary", prompt="test")

        stats = router.get_stats()

        assert "providers" in stats
        assert "test" in stats["providers"]
        provider_stats = stats["providers"]["test"]
        assert provider_stats["total_requests"] == 5
        assert provider_stats["failed_requests"] == 0
        assert provider_stats["success_rate"] == 1.0
        assert provider_stats["total_tokens"] > 0

    def test_cache_integration(self, router_with_cache):
        """Test cache integration."""
        router = router_with_cache
        provider = MockProvider("test")
        router.register_provider("test", provider, [ModelRole.PRIMARY])

        # First request (cache miss)
        response1 = router.invoke(
            role="primary",
            prompt="test prompt",
            use_cache=True
        )

        assert provider.invoke_count == 1

        # Second identical request (cache hit)
        response2 = router.invoke(
            role="primary",
            prompt="test prompt",
            use_cache=True
        )

        # Should not invoke provider again
        assert provider.invoke_count == 1
        assert response2.content == response1.content

    def test_cache_bypass(self, router_with_cache):
        """Test bypassing cache."""
        router = router_with_cache
        provider = MockProvider("test")
        router.register_provider("test", provider, [ModelRole.PRIMARY])

        # First request with cache
        router.invoke(role="primary", prompt="test", use_cache=True)
        assert provider.invoke_count == 1

        # Second request bypassing cache
        router.invoke(role="primary", prompt="test", use_cache=False)
        assert provider.invoke_count == 2

    def test_fallback_chain_resolution(self, router):
        """Test fallback chain resolution."""
        router.config.fallback_chains = {
            "primary": ["provider1", "provider2", "provider3"]
        }

        chain = router.get_fallback_chain("primary")
        assert chain == ["provider1", "provider2", "provider3"]

        # Unknown role should return empty or all providers
        chain = router.get_fallback_chain("unknown")
        assert isinstance(chain, list)

    def test_invalidate_cache(self, router_with_cache):
        """Test cache invalidation."""
        router = router_with_cache
        provider = MockProvider("test")
        router.register_provider("test", provider, [ModelRole.PRIMARY])

        # Populate cache
        router.invoke(role="primary", prompt="test", use_cache=True)
        assert provider.invoke_count == 1

        # Invalidate
        router.invalidate_cache()

        # Should invoke again
        router.invoke(role="primary", prompt="test", use_cache=True)
        assert provider.invoke_count == 2

    def test_reset_failures(self, router):
        """Test resetting failure tracking."""
        provider = MockProvider("test", fail=True)
        router.register_provider("test", provider)

        # Cause failures
        try:
            router.invoke(role="primary", prompt="test")
        except:
            pass

        assert "test" in router._failures

        # Reset
        router.reset_failures("test")
        assert "test" not in router._failures

    def test_multiple_roles(self, router):
        """Test provider registered for multiple roles."""
        provider = MockProvider("multi")
        router.register_provider(
            "multi",
            provider,
            [ModelRole.PRIMARY, ModelRole.FAST]
        )

        assert "multi" in router._roles[ModelRole.PRIMARY]
        assert "multi" in router._roles[ModelRole.FAST]

    def test_no_providers_available(self, router):
        """Test error when no providers available."""
        with pytest.raises(ProviderUnavailableException) as exc_info:
            router.invoke(role="primary", prompt="test")

        assert "No providers available" in str(exc_info.value)
