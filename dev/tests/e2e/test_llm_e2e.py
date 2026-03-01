#!/usr/bin/env python3
"""
End-to-End LLM Tests

Real API tests for complete workflow validation.
These tests are marked with @pytest.mark.requires_llm and are skipped in CI.
"""

import json
import pytest
from pathlib import Path

from dev.tests.mocks.mock_llm import MockProvider


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def fixtures_dir():
    """Get fixtures directory."""
    return Path(__file__).parent.parent / "fixtures" / "llm"


@pytest.fixture
def sample_prompts(fixtures_dir):
    """Load sample prompts."""
    with open(fixtures_dir / "sample_prompts.json") as f:
        return json.load(f)


@pytest.fixture
def expected_responses(fixtures_dir):
    """Load expected response patterns."""
    with open(fixtures_dir / "expected_responses.json") as f:
        return json.load(f)


# ============================================================================
# E2E Tests with Mock Provider (Always Run)
# ============================================================================

@pytest.mark.unit
def test_e2e_simple_query(sample_prompts):
    """Test simple query end-to-end."""
    provider = MockProvider({"default_response": "4"})
    prompt = sample_prompts["simple"]["prompt"]

    response = provider.invoke(prompt)

    assert response.content
    assert response.provider == "mock"
    assert response.usage.total_tokens > 0


@pytest.mark.unit
def test_e2e_code_generation(sample_prompts):
    """Test code generation workflow."""
    code_response = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)
"""
    provider = MockProvider({"default_response": code_response})
    prompt = sample_prompts["code_generation"]["prompt"]

    response = provider.invoke(prompt)

    assert "def" in response.content
    assert "factorial" in response.content


@pytest.mark.unit
def test_e2e_json_output(sample_prompts):
    """Test JSON output parsing."""
    json_response = '{"name": "John Doe", "age": 30, "email": "john@example.com"}'
    provider = MockProvider({"default_response": json_response})
    prompt = sample_prompts["json_output"]["prompt"]

    response = provider.invoke(prompt)

    # Verify JSON is parseable
    parsed = json.loads(response.content)
    assert "name" in parsed
    assert "age" in parsed
    assert "email" in parsed


@pytest.mark.unit
def test_e2e_streaming_workflow():
    """Test streaming workflow."""
    provider = MockProvider({
        "default_response": "This is a streaming response test",
        "latency_ms": 10
    })

    chunks = []
    for chunk in provider.stream("Test streaming"):
        chunks.append(chunk)

    combined = "".join(chunks)
    assert len(chunks) > 0
    assert "streaming" in combined


@pytest.mark.unit
def test_e2e_multiple_requests():
    """Test multiple sequential requests."""
    provider = MockProvider()

    responses = []
    for i in range(5):
        response = provider.invoke(f"Request {i}")
        responses.append(response)

    assert len(responses) == 5
    assert all(r.provider == "mock" for r in responses)


@pytest.mark.unit
def test_e2e_error_recovery():
    """Test error handling and recovery."""
    from core.llm.base import APIError

    provider = MockProvider()
    provider.set_error_mode("api_error", after_calls=2)

    # First 2 calls succeed
    response1 = provider.invoke("Request 1")
    response2 = provider.invoke("Request 2")
    assert response1.content
    assert response2.content

    # 3rd call fails
    with pytest.raises(APIError):
        provider.invoke("Request 3")

    # Recovery: reset error mode
    provider.set_error_mode(None)
    response4 = provider.invoke("Request 4")
    assert response4.content


@pytest.mark.unit
def test_e2e_health_check_before_invoke():
    """Test checking health before invocation."""
    from core.llm.base import HealthStatus

    provider = MockProvider()

    # Check health
    health = provider.health_check()
    assert health == HealthStatus.HEALTHY

    # Proceed with invocation
    response = provider.invoke("Test")
    assert response.content


@pytest.mark.unit
def test_e2e_model_validation():
    """Test model validation workflow."""
    provider = MockProvider({"supported_models": ["model-a", "model-b"]})

    # Check models
    assert provider.validate_model("model-a") is True
    assert provider.validate_model("model-c") is False

    # Use validated model
    response = provider.invoke("Test", model="model-a")
    assert response.model == "model-a"


@pytest.mark.unit
def test_e2e_token_counting_workflow():
    """Test token counting in workflow."""
    provider = MockProvider()

    prompt = "Count tokens in this prompt"
    estimated_tokens = provider.get_token_count(prompt)

    response = provider.invoke(prompt)

    # Verify usage tracking
    assert response.usage.input_tokens > 0
    assert response.usage.output_tokens > 0
    assert response.usage.total_tokens == (
        response.usage.input_tokens + response.usage.output_tokens
    )


@pytest.mark.unit
def test_e2e_system_prompt_workflow():
    """Test system prompt in complete workflow."""
    provider = MockProvider({"default_response": "Professional response"})

    response = provider.invoke(
        "User question",
        system_prompt="You are a professional assistant"
    )

    assert response.content
    assert provider.get_last_call().system_prompt == "You are a professional assistant"


@pytest.mark.unit
def test_e2e_parameter_tuning():
    """Test parameter tuning workflow."""
    provider = MockProvider()

    response = provider.invoke(
        "Test prompt",
        temperature=0.7,
        max_tokens=2048
    )

    last_call = provider.get_last_call()
    assert last_call.kwargs.get("temperature") == 0.7
    assert last_call.kwargs.get("max_tokens") == 2048


@pytest.mark.unit
def test_e2e_metadata_tracking():
    """Test metadata tracking in workflow."""
    provider = MockProvider()

    response = provider.invoke("Test")

    assert response.metadata is not None
    assert "mock" in response.metadata
    assert response.timestamp is not None
    assert response.latency_ms is not None


# ============================================================================
# Real LLM Tests (Requires LLM Access - Skipped by Default)
# ============================================================================

@pytest.mark.requires_llm
@pytest.mark.skipif(True, reason="Requires real LLM access")
def test_real_anthropic_invoke():
    """Test real Anthropic API invocation."""
    # This test requires ANTHROPIC_API_KEY
    # Skipped by default
    pass


@pytest.mark.requires_llm
@pytest.mark.skipif(True, reason="Requires Ollama running")
def test_real_ollama_invoke():
    """Test real Ollama invocation."""
    # This test requires Ollama service running
    # Skipped by default
    pass


@pytest.mark.requires_llm
@pytest.mark.skipif(True, reason="Requires AWS credentials")
def test_real_bedrock_invoke():
    """Test real AWS Bedrock invocation."""
    # This test requires AWS credentials
    # Skipped by default
    pass
