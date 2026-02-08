#!/usr/bin/env python3
"""
LLM Router Demo

Demonstrates the LLM Router with mock providers showing:
- Provider registration
- Role-based routing
- Fallback chains
- Circuit breaker
- Response caching
- Usage statistics
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.llm import (
    BaseLLMProvider,
    LLMResponse,
    TokenUsage,
    HealthStatus,
    LLMRouter,
    RouterConfig,
    ModelRole,
    RateLimitException,
)


class MockAnthropicProvider(BaseLLMProvider):
    """Mock Anthropic provider."""

    def __init__(self):
        super().__init__()
        self.provider_name = "anthropic"
        self.call_count = 0

    def invoke(self, prompt, **kwargs):
        self.call_count += 1
        time.sleep(0.1)  # Simulate network delay

        return LLMResponse(
            content=f"Anthropic response to: {prompt[:50]}...",
            model="claude-sonnet-4-5",
            provider=self.provider_name,
            usage=TokenUsage(input_tokens=100, output_tokens=200),
            latency_ms=100,
        )

    def stream(self, prompt, **kwargs):
        self.call_count += 1
        chunks = ["Anthropic ", "streaming ", "response"]
        for chunk in chunks:
            yield chunk
            time.sleep(0.05)

    def validate_model(self, model_name):
        return model_name in ["claude-opus-4", "claude-sonnet-4-5", "claude-haiku-4"]

    def get_token_count(self, text, model=None):
        return len(text) // 4

    def health_check(self):
        return HealthStatus.HEALTHY


class MockOllamaProvider(BaseLLMProvider):
    """Mock Ollama provider (local)."""

    def __init__(self):
        super().__init__()
        self.provider_name = "ollama"
        self.call_count = 0

    def invoke(self, prompt, **kwargs):
        self.call_count += 1
        time.sleep(0.05)  # Faster than Anthropic

        return LLMResponse(
            content=f"Ollama response to: {prompt[:50]}...",
            model="llama3.2:70b",
            provider=self.provider_name,
            usage=TokenUsage(input_tokens=80, output_tokens=150),
            latency_ms=50,
        )

    def stream(self, prompt, **kwargs):
        self.call_count += 1
        chunks = ["Ollama ", "streaming ", "response"]
        for chunk in chunks:
            yield chunk
            time.sleep(0.02)

    def validate_model(self, model_name):
        return "llama" in model_name.lower()

    def get_token_count(self, text, model=None):
        return len(text) // 4

    def health_check(self):
        return HealthStatus.HEALTHY


class MockFailingProvider(BaseLLMProvider):
    """Mock provider that always fails (for testing fallback)."""

    def __init__(self):
        super().__init__()
        self.provider_name = "failing"
        self.call_count = 0

    def invoke(self, prompt, **kwargs):
        self.call_count += 1
        raise RateLimitException(
            "Mock rate limit error",
            provider=self.provider_name,
            retry_after=60
        )

    def stream(self, prompt, **kwargs):
        self.call_count += 1
        raise RateLimitException(
            "Mock rate limit error",
            provider=self.provider_name
        )
        yield  # Never reached

    def validate_model(self, model_name):
        return True

    def get_token_count(self, text, model=None):
        return len(text) // 4

    def health_check(self):
        return HealthStatus.DEGRADED


def print_section(title):
    """Print section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def demo_basic_routing():
    """Demonstrate basic provider routing."""
    print_section("1. Basic Provider Routing")

    # Create router
    config = RouterConfig(enable_cache=False)
    router = LLMRouter(config)

    # Create and register providers
    anthropic = MockAnthropicProvider()
    ollama = MockOllamaProvider()

    router.register_provider("anthropic", anthropic, [ModelRole.PRIMARY])
    router.register_provider("ollama", ollama, [ModelRole.FAST])

    print("Registered providers:")
    print(f"  - anthropic (PRIMARY role)")
    print(f"  - ollama (FAST role)")

    # Invoke primary provider
    print("\nInvoking PRIMARY role:")
    response = router.invoke(
        role="primary",
        prompt="What is the capital of France?",
    )
    print(f"  Provider: {response.provider}")
    print(f"  Model: {response.model}")
    print(f"  Response: {response.content}")
    print(f"  Latency: {response.latency_ms}ms")
    print(f"  Tokens: {response.usage.total_tokens}")

    # Invoke fast provider
    print("\nInvoking FAST role:")
    response = router.invoke(
        role="fast",
        prompt="Quick question: What is 2+2?",
    )
    print(f"  Provider: {response.provider}")
    print(f"  Model: {response.model}")
    print(f"  Response: {response.content}")
    print(f"  Latency: {response.latency_ms}ms")


def demo_fallback_chain():
    """Demonstrate fallback chain."""
    print_section("2. Fallback Chain (Primary Fails → Fallback Succeeds)")

    config = RouterConfig(enable_cache=False)
    router = LLMRouter(config)

    # Register failing provider as primary, working provider as fallback
    failing = MockFailingProvider()
    ollama = MockOllamaProvider()

    router.register_provider("failing", failing, [ModelRole.PRIMARY])
    router.register_provider("ollama", ollama, [ModelRole.PRIMARY])

    # Configure fallback chain
    router.config.fallback_chains = {
        "primary": ["failing", "ollama"]
    }

    print("Fallback chain: failing → ollama")
    print("\nInvoking PRIMARY role (failing provider will fail):")

    response = router.invoke(
        role="primary",
        prompt="Test fallback",
    )

    print(f"  Failing provider called: {failing.call_count} times")
    print(f"  Ollama provider called: {ollama.call_count} times")
    print(f"  Final response from: {response.provider}")
    print(f"  Response: {response.content}")


def demo_circuit_breaker():
    """Demonstrate circuit breaker."""
    print_section("3. Circuit Breaker (Disable After 3 Failures)")

    config = RouterConfig(
        enable_cache=False,
        failure_threshold=3,
        cooldown_minutes=0.05,  # 3 seconds
    )
    router = LLMRouter(config)

    failing = MockFailingProvider()
    router.register_provider("failing", failing)

    print("Triggering circuit breaker (3 failures):")

    # Cause 3 failures
    for i in range(3):
        try:
            router.invoke(role="primary", prompt=f"Test {i+1}")
        except Exception as e:
            print(f"  Attempt {i+1}: Failed ({type(e).__name__})")

    # Check if provider is disabled
    is_available = router._is_provider_available("failing")
    print(f"\nProvider available after 3 failures: {is_available}")

    failure = router._failures.get("failing")
    print(f"Failure count: {failure.failure_count}")
    print(f"Disabled until: {failure.disabled_until}")


def demo_response_caching():
    """Demonstrate response caching."""
    print_section("4. Response Caching")

    config = RouterConfig(
        enable_cache=True,
        cache_ttl=10,
        cache_max_size=100,
    )
    router = LLMRouter(config)

    anthropic = MockAnthropicProvider()
    router.register_provider("anthropic", anthropic, [ModelRole.PRIMARY])

    prompt = "What is machine learning?"

    # First request (cache miss)
    print("First request (cache miss):")
    start = time.time()
    response1 = router.invoke(role="primary", prompt=prompt, use_cache=True)
    elapsed1 = time.time() - start

    print(f"  Provider calls: {anthropic.call_count}")
    print(f"  Elapsed: {elapsed1*1000:.1f}ms")
    print(f"  Response: {response1.content}")

    # Second identical request (cache hit)
    print("\nSecond identical request (cache hit):")
    start = time.time()
    response2 = router.invoke(role="primary", prompt=prompt, use_cache=True)
    elapsed2 = time.time() - start

    print(f"  Provider calls: {anthropic.call_count}")
    print(f"  Elapsed: {elapsed2*1000:.1f}ms (from cache)")
    print(f"  Response: {response2.content}")

    # Cache stats
    cache_stats = router._cache.get_stats()
    print(f"\nCache statistics:")
    print(f"  Hits: {cache_stats['hits']}")
    print(f"  Misses: {cache_stats['misses']}")
    print(f"  Hit rate: {cache_stats['hit_rate']:.1%}")


def demo_usage_statistics():
    """Demonstrate usage statistics."""
    print_section("5. Usage Statistics")

    config = RouterConfig(enable_cache=False)
    router = LLMRouter(config)

    anthropic = MockAnthropicProvider()
    ollama = MockOllamaProvider()

    router.register_provider("anthropic", anthropic, [ModelRole.PRIMARY])
    router.register_provider("ollama", ollama, [ModelRole.FAST])

    # Make several requests
    print("Making 5 requests to Anthropic, 3 to Ollama:")

    for i in range(5):
        router.invoke(role="primary", prompt=f"Request {i+1}")

    for i in range(3):
        router.invoke(role="fast", prompt=f"Fast request {i+1}")

    # Get statistics
    stats = router.get_stats()

    print("\nProvider Statistics:")
    for provider_name, provider_stats in stats["providers"].items():
        print(f"\n  {provider_name}:")
        print(f"    Total requests: {provider_stats['total_requests']}")
        print(f"    Failed requests: {provider_stats['failed_requests']}")
        print(f"    Success rate: {provider_stats['success_rate']:.1%}")
        print(f"    Total tokens: {provider_stats['total_tokens']}")
        print(f"    Average latency: {provider_stats['avg_latency_ms']:.1f}ms")


def demo_streaming():
    """Demonstrate streaming responses."""
    print_section("6. Streaming Responses")

    config = RouterConfig(enable_cache=False)
    router = LLMRouter(config)

    anthropic = MockAnthropicProvider()
    router.register_provider("anthropic", anthropic, [ModelRole.PRIMARY])

    print("Streaming response:")
    print("  ", end="", flush=True)

    for chunk in router.stream(role="primary", prompt="Tell me a story"):
        print(chunk, end="", flush=True)

    print("\n\nStreaming complete!")


def demo_health_checks():
    """Demonstrate health checking."""
    print_section("7. Health Checks")

    config = RouterConfig(enable_cache=False)
    router = LLMRouter(config)

    anthropic = MockAnthropicProvider()
    ollama = MockOllamaProvider()
    failing = MockFailingProvider()

    router.register_provider("anthropic", anthropic)
    router.register_provider("ollama", ollama)
    router.register_provider("failing", failing)

    print("Checking provider health:")

    health = router.check_health()

    for provider_name, provider_health in health.items():
        status = provider_health.status
        available = provider_health.available
        print(f"\n  {provider_name}:")
        print(f"    Status: {status}")
        print(f"    Available: {available}")


def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("  LLM ROUTER DEMONSTRATION")
    print("=" * 70)

    try:
        demo_basic_routing()
        demo_fallback_chain()
        demo_circuit_breaker()
        demo_response_caching()
        demo_usage_statistics()
        demo_streaming()
        demo_health_checks()

        print("\n" + "=" * 70)
        print("  DEMO COMPLETE")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
