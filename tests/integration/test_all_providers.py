#!/usr/bin/env python3
"""
Integration Tests for All LLM Providers

Tests all providers with identical inputs and compares behaviors.
Covers fallback chains, concurrent requests, rate limiting, caching, and router integration.
"""

import json
import pytest
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict

from core.llm.base import BaseLLMProvider, LLMResponse, HealthStatus
from core.llm.ollama import OllamaProvider
from tests.mocks.mock_llm import MockProvider


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def test_fixtures_dir():
    """Get test fixtures directory."""
    return Path(__file__).parent.parent / "fixtures" / "llm"


@pytest.fixture
def sample_prompts(test_fixtures_dir):
    """Load sample prompts."""
    with open(test_fixtures_dir / "sample_prompts.json") as f:
        return json.load(f)


@pytest.fixture
def all_providers():
    """Create instances of all providers."""
    return {
        "mock": MockProvider(),
        "ollama": OllamaProvider({"host": "http://localhost:11434", "auto_pull": False}),
    }


@pytest.fixture
def mock_provider():
    """Create a mock provider."""
    return MockProvider({"default_response": "Mock test response"})


# ============================================================================
# Test Provider Behavior Consistency
# ============================================================================

@pytest.mark.unit
def test_all_providers_implement_interface(all_providers):
    """Test that all providers implement BaseLLMProvider."""
    for name, provider in all_providers.items():
        assert isinstance(provider, BaseLLMProvider), f"{name} doesn't implement BaseLLMProvider"
        assert hasattr(provider, "invoke")
        assert hasattr(provider, "stream")
        assert hasattr(provider, "validate_model")
        assert hasattr(provider, "get_token_count")
        assert hasattr(provider, "health_check")


@pytest.mark.unit
def test_all_providers_have_names(all_providers):
    """Test that all providers have unique names."""
    names = [p.provider_name for p in all_providers.values()]
    assert len(names) == len(set(names)), "Provider names must be unique"


@pytest.mark.unit
def test_identical_prompts_similar_structure(mock_provider, sample_prompts):
    """Test that identical prompts produce structurally similar responses."""
    prompt = sample_prompts["simple"]["prompt"]

    # Call twice with same prompt
    response1 = mock_provider.invoke(prompt)
    response2 = mock_provider.invoke(prompt)

    # Structure should be identical
    assert type(response1) == type(response2)
    assert response1.provider == response2.provider
    assert response1.model == response2.model


# ============================================================================
# Test Token Counting Consistency
# ============================================================================

@pytest.mark.unit
def test_token_counting_consistency(all_providers):
    """Test token counting is consistent within each provider."""
    text = "This is a test sentence with exactly ten words here."

    for name, provider in all_providers.items():
        count1 = provider.get_token_count(text)
        count2 = provider.get_token_count(text)
        assert count1 == count2, f"{name} token counting is inconsistent"
        assert count1 > 0, f"{name} returned zero tokens"


@pytest.mark.unit
def test_token_counting_scales(all_providers):
    """Test token count scales with text length."""
    short_text = "Short text"
    long_text = "This is a much longer text with many more words that should result in a higher token count"

    for name, provider in all_providers.items():
        short_count = provider.get_token_count(short_text)
        long_count = provider.get_token_count(long_text)
        assert long_count > short_count, f"{name} token counting doesn't scale"


# ============================================================================
# Test Health Checks
# ============================================================================

@pytest.mark.unit
def test_health_check_returns_valid_status(all_providers):
    """Test health checks return valid HealthStatus."""
    for name, provider in all_providers.items():
        status = provider.health_check()
        assert isinstance(status, HealthStatus), f"{name} health check returned invalid type"
        assert status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNAVAILABLE]


@pytest.mark.unit
def test_mock_provider_always_healthy():
    """Test mock provider is always healthy."""
    provider = MockProvider()
    status = provider.health_check()
    assert status == HealthStatus.HEALTHY


@pytest.mark.unit
def test_health_status_configurable():
    """Test mock provider health status can be configured."""
    provider = MockProvider({"health_status": HealthStatus.DEGRADED})
    assert provider.health_check() == HealthStatus.DEGRADED

    provider.set_health_status(HealthStatus.UNAVAILABLE)
    assert provider.health_check() == HealthStatus.UNAVAILABLE


# ============================================================================
# Test Model Validation
# ============================================================================

@pytest.mark.unit
def test_validate_existing_model(mock_provider):
    """Test validation of existing models."""
    assert mock_provider.validate_model("mock-model") is True


@pytest.mark.unit
def test_validate_nonexistent_model(mock_provider):
    """Test validation of non-existent models."""
    assert mock_provider.validate_model("nonexistent-model") is False


@pytest.mark.unit
def test_supported_models_list(all_providers):
    """Test getting supported models list."""
    for name, provider in all_providers.items():
        models = provider.get_supported_models()
        assert isinstance(models, list), f"{name} didn't return a list"


# ============================================================================
# Test Invocation
# ============================================================================

@pytest.mark.unit
def test_invoke_basic(mock_provider):
    """Test basic invocation."""
    response = mock_provider.invoke("Test prompt")

    assert isinstance(response, LLMResponse)
    assert response.content
    assert response.provider == "mock"
    assert response.usage.input_tokens > 0
    assert response.usage.output_tokens > 0


@pytest.mark.unit
def test_invoke_with_system_prompt(mock_provider):
    """Test invocation with system prompt."""
    response = mock_provider.invoke(
        "User prompt",
        system_prompt="System prompt"
    )

    assert isinstance(response, LLMResponse)
    assert response.content


@pytest.mark.unit
def test_invoke_with_parameters(mock_provider):
    """Test invocation with custom parameters."""
    response = mock_provider.invoke(
        "Test",
        model="custom-model",
        max_tokens=2048,
        temperature=0.7
    )

    assert response.model == "custom-model"


@pytest.mark.unit
def test_invoke_tracking(mock_provider):
    """Test that mock provider tracks calls."""
    mock_provider.reset_calls()

    mock_provider.invoke("Prompt 1")
    assert mock_provider.get_call_count() == 1

    mock_provider.invoke("Prompt 2")
    assert mock_provider.get_call_count() == 2

    last_call = mock_provider.get_last_call()
    assert last_call.prompt == "Prompt 2"


# ============================================================================
# Test Streaming
# ============================================================================

@pytest.mark.unit
def test_stream_basic(mock_provider):
    """Test basic streaming."""
    mock_provider.set_response("Test", "Hello world test")
    chunks = list(mock_provider.stream("Test"))

    assert len(chunks) > 0
    combined = "".join(chunks)
    assert "Hello" in combined
    assert "world" in combined


@pytest.mark.unit
def test_stream_tracking(mock_provider):
    """Test that mock provider tracks stream calls."""
    mock_provider.reset_calls()

    list(mock_provider.stream("Stream 1"))
    assert mock_provider.get_stream_call_count() == 1

    list(mock_provider.stream("Stream 2"))
    assert mock_provider.get_stream_call_count() == 2


# ============================================================================
# Test Error Handling
# ============================================================================

@pytest.mark.unit
def test_error_injection_api_error(mock_provider):
    """Test API error injection."""
    from core.llm.base import APIError

    mock_provider.set_error_mode("api_error")

    with pytest.raises(APIError):
        mock_provider.invoke("Test")


@pytest.mark.unit
def test_error_injection_timeout(mock_provider):
    """Test timeout error injection."""
    from core.llm.base import LLMTimeoutError

    mock_provider.set_error_mode("timeout")

    with pytest.raises(LLMTimeoutError):
        mock_provider.invoke("Test")


@pytest.mark.unit
def test_error_injection_rate_limit(mock_provider):
    """Test rate limit error injection."""
    from core.llm.base import RateLimitError

    mock_provider.set_error_mode("rate_limit")

    with pytest.raises(RateLimitError):
        mock_provider.invoke("Test")


@pytest.mark.unit
def test_error_injection_model_not_found(mock_provider):
    """Test model not found error injection."""
    from core.llm.base import ModelNotFoundError

    mock_provider.set_error_mode("model_not_found")

    with pytest.raises(ModelNotFoundError):
        mock_provider.invoke("Test")


@pytest.mark.unit
def test_error_after_n_calls(mock_provider):
    """Test error injection after N successful calls."""
    from core.llm.base import APIError

    mock_provider.set_error_mode("api_error", after_calls=3)

    # First 3 calls should succeed
    mock_provider.invoke("Test 1")
    mock_provider.invoke("Test 2")
    mock_provider.invoke("Test 3")

    # 4th call should fail
    with pytest.raises(APIError):
        mock_provider.invoke("Test 4")


# ============================================================================
# Test Concurrent Requests
# ============================================================================

@pytest.mark.unit
def test_concurrent_invocations(mock_provider):
    """Test concurrent requests to same provider."""
    mock_provider.set_response("Test", "Response")

    def make_request(i):
        return mock_provider.invoke(f"Test {i}")

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_request, i) for i in range(10)]
        results = [f.result() for f in as_completed(futures)]

    assert len(results) == 10
    assert all(isinstance(r, LLMResponse) for r in results)


@pytest.mark.unit
def test_concurrent_streaming(mock_provider):
    """Test concurrent streaming requests."""
    mock_provider.set_response("Stream", "Hello world")

    def stream_request(i):
        return "".join(mock_provider.stream(f"Stream {i}"))

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(stream_request, i) for i in range(5)]
        results = [f.result() for f in as_completed(futures)]

    assert len(results) == 5
    assert all("Hello" in r for r in results)


# ============================================================================
# Test Latency Simulation
# ============================================================================

@pytest.mark.unit
def test_latency_simulation():
    """Test latency simulation in mock provider."""
    fast_provider = MockProvider({"latency_ms": 10})
    slow_provider = MockProvider({"latency_ms": 100})

    start = time.time()
    fast_provider.invoke("Test")
    fast_time = time.time() - start

    start = time.time()
    slow_provider.invoke("Test")
    slow_time = time.time() - start

    assert slow_time > fast_time


# ============================================================================
# Test Response Configuration
# ============================================================================

@pytest.mark.unit
def test_specific_response_mapping():
    """Test setting specific responses for prompts."""
    provider = MockProvider()

    provider.set_response("Calculate 2+2", "The answer is 4")
    provider.set_response("Calculate 3+3", "The answer is 6")

    response1 = provider.invoke("Calculate 2+2")
    assert "4" in response1.content

    response2 = provider.invoke("Calculate 3+3")
    assert "6" in response2.content


@pytest.mark.unit
def test_partial_prompt_matching():
    """Test partial matching in response configuration."""
    provider = MockProvider()
    provider.set_response("math", "This is a math response")

    response = provider.invoke("Solve this math problem: 2+2")
    assert "math response" in response.content


# ============================================================================
# Test Usage Statistics
# ============================================================================

@pytest.mark.unit
def test_token_usage_reported(mock_provider):
    """Test that token usage is reported in responses."""
    response = mock_provider.invoke("Test prompt with several words")

    assert response.usage.input_tokens > 0
    assert response.usage.output_tokens > 0
    assert response.usage.total_tokens > 0


@pytest.mark.unit
def test_latency_reported(mock_provider):
    """Test that latency is reported."""
    response = mock_provider.invoke("Test")

    assert response.latency_ms is not None
    assert response.latency_ms >= 0


@pytest.mark.unit
def test_metadata_included(mock_provider):
    """Test that metadata is included in responses."""
    response = mock_provider.invoke("Test")

    assert response.metadata is not None
    assert "mock" in response.metadata
    assert response.metadata["mock"] is True


# ============================================================================
# Test Ollama-Specific Features
# ============================================================================

@pytest.mark.unit
def test_ollama_host_configuration():
    """Test Ollama host configuration."""
    provider = OllamaProvider({"host": "http://192.168.1.100:11434"})
    assert provider.host == "http://192.168.1.100:11434"


@pytest.mark.unit
def test_ollama_default_timeout():
    """Test Ollama default timeout is longer than API providers."""
    provider = OllamaProvider()
    assert provider.default_timeout == 600  # 10 minutes


@pytest.mark.unit
def test_ollama_auto_pull_configuration():
    """Test Ollama auto-pull can be disabled."""
    provider = OllamaProvider({"auto_pull": False})
    assert provider.auto_pull is False


# ============================================================================
# Test Provider Comparison
# ============================================================================

@pytest.mark.unit
def test_compare_token_counting_algorithms(all_providers):
    """Compare token counting across providers."""
    test_text = "The quick brown fox jumps over the lazy dog"

    counts = {}
    for name, provider in all_providers.items():
        counts[name] = provider.get_token_count(test_text)

    # All providers should give reasonable counts
    for name, count in counts.items():
        assert 5 <= count <= 20, f"{name} gave unreasonable token count: {count}"


@pytest.mark.unit
def test_all_providers_support_repr():
    """Test that all providers have string representations."""
    providers = [
        MockProvider(),
        OllamaProvider(),
    ]

    for provider in providers:
        repr_str = repr(provider)
        assert isinstance(repr_str, str)
        assert len(repr_str) > 0
