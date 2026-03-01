#!/usr/bin/env python3
"""
LLM Performance Tests

Measures provider resolution time, invoke latency, cache performance,
concurrent request handling, and generates performance reports.
"""

import json
import time
import pytest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean, median

from dev.tests.mocks.mock_llm import MockProvider
from core.llm.ollama import OllamaProvider


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def performance_benchmarks():
    """Load performance benchmarks."""
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "llm"
    with open(fixtures_dir / "performance_benchmarks.json") as f:
        return json.load(f)


@pytest.fixture
def fast_provider():
    """Fast mock provider (low latency)."""
    return MockProvider({"latency_ms": 10})


@pytest.fixture
def slow_provider():
    """Slow mock provider (high latency)."""
    return MockProvider({"latency_ms": 100})


# ============================================================================
# Provider Resolution Performance
# ============================================================================

@pytest.mark.performance
def test_provider_instantiation_speed():
    """Test provider instantiation performance."""
    iterations = 100
    start = time.time()

    for _ in range(iterations):
        MockProvider()

    duration_ms = (time.time() - start) * 1000
    avg_ms = duration_ms / iterations

    assert avg_ms < 5, f"Provider instantiation too slow: {avg_ms:.2f}ms"


@pytest.mark.performance
def test_health_check_speed(fast_provider, performance_benchmarks):
    """Test health check performance."""
    baseline = performance_benchmarks["health_check"]["baseline_ms"]
    acceptable = performance_benchmarks["health_check"]["acceptable_ms"]

    start = time.time()
    status = fast_provider.health_check()
    duration_ms = (time.time() - start) * 1000

    assert duration_ms < acceptable, f"Health check too slow: {duration_ms:.2f}ms"


# ============================================================================
# Invocation Latency
# ============================================================================

@pytest.mark.performance
def test_invoke_latency(fast_provider, performance_benchmarks):
    """Test invoke latency."""
    benchmarks = performance_benchmarks["invoke_latency"]["providers"]["mock"]

    response = fast_provider.invoke("Test prompt for latency")

    # Check reported latency
    assert response.latency_ms is not None
    assert response.latency_ms < benchmarks["acceptable_ms"]


@pytest.mark.performance
def test_invoke_latency_distribution(fast_provider):
    """Test invoke latency distribution."""
    latencies = []

    for i in range(20):
        response = fast_provider.invoke(f"Test prompt {i}")
        latencies.append(response.latency_ms)

    # Calculate percentiles
    sorted_latencies = sorted(latencies)
    p50 = sorted_latencies[len(sorted_latencies) // 2]
    p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)]

    assert p50 < 200, f"P50 latency too high: {p50}ms"
    assert p95 < 300, f"P95 latency too high: {p95}ms"


# ============================================================================
# Token Counting Performance
# ============================================================================

@pytest.mark.performance
def test_token_counting_speed(fast_provider, performance_benchmarks):
    """Test token counting performance."""
    text = "This is a test text " * 50  # ~100 words
    baseline = performance_benchmarks["token_counting"]["baseline_ms"]
    acceptable = performance_benchmarks["token_counting"]["acceptable_ms"]

    iterations = 100
    start = time.time()

    for _ in range(iterations):
        fast_provider.get_token_count(text)

    duration_ms = (time.time() - start) * 1000
    avg_ms = duration_ms / iterations

    assert avg_ms < acceptable, f"Token counting too slow: {avg_ms:.2f}ms"


@pytest.mark.performance
def test_token_counting_scales():
    """Test token counting scales linearly."""
    provider = MockProvider()

    # Test with different lengths
    times = []
    for length in [100, 500, 1000, 5000]:
        text = "word " * length
        start = time.time()
        provider.get_token_count(text)
        times.append((length, (time.time() - start) * 1000))

    # Verify roughly linear scaling
    # Allow up to 50x ratio because string operations can have overhead
    ratio = times[-1][1] / times[0][1] if times[0][1] > 0 else 1
    assert ratio < 50, f"Token counting doesn't scale reasonably: {ratio}x"


# ============================================================================
# Concurrent Request Performance
# ============================================================================

@pytest.mark.performance
def test_concurrent_invocations(fast_provider, performance_benchmarks):
    """Test concurrent request handling."""
    benchmark = performance_benchmarks["concurrent_requests"]
    concurrent = benchmark["concurrent_count"]

    def make_request(i):
        return fast_provider.invoke(f"Concurrent test {i}")

    start = time.time()
    with ThreadPoolExecutor(max_workers=concurrent) as executor:
        futures = [executor.submit(make_request, i) for i in range(concurrent)]
        results = [f.result() for f in as_completed(futures)]
    duration_ms = (time.time() - start) * 1000

    assert len(results) == concurrent
    assert duration_ms < benchmark["max_total_time_ms"]


@pytest.mark.performance
def test_concurrent_streaming():
    """Test concurrent streaming performance."""
    provider = MockProvider({"latency_ms": 20})

    def stream_request(i):
        return list(provider.stream(f"Stream {i}"))

    start = time.time()
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(stream_request, i) for i in range(10)]
        results = [f.result() for f in as_completed(futures)]
    duration_ms = (time.time() - start) * 1000

    assert len(results) == 10
    # Should complete in reasonable time even with concurrent streams
    assert duration_ms < 5000


# ============================================================================
# Model Validation Performance
# ============================================================================

@pytest.mark.performance
def test_model_validation_speed():
    """Test model validation performance."""
    provider = MockProvider({"supported_models": [f"model-{i}" for i in range(100)]})

    iterations = 100
    start = time.time()

    for _ in range(iterations):
        provider.validate_model("model-50")

    duration_ms = (time.time() - start) * 1000
    avg_ms = duration_ms / iterations

    assert avg_ms < 1, f"Model validation too slow: {avg_ms:.2f}ms"


# ============================================================================
# Streaming Performance
# ============================================================================

@pytest.mark.performance
def test_streaming_throughput():
    """Test streaming throughput."""
    provider = MockProvider({
        "default_response": " ".join([f"word{i}" for i in range(100)]),
        "latency_ms": 10
    })

    start = time.time()
    chunks = list(provider.stream("Test streaming throughput"))
    duration_ms = (time.time() - start) * 1000

    # Should get ~100 words
    assert len(chunks) > 50
    # Should complete in reasonable time
    assert duration_ms < 5000


@pytest.mark.performance
def test_streaming_first_chunk_latency():
    """Test time to first chunk in streaming."""
    provider = MockProvider({"latency_ms": 50})

    start = time.time()
    stream = provider.stream("Test first chunk")
    first_chunk = next(stream)
    first_chunk_ms = (time.time() - start) * 1000

    assert first_chunk is not None
    # First chunk should arrive quickly
    assert first_chunk_ms < 200


# ============================================================================
# Performance Report Generation
# ============================================================================

@pytest.mark.performance
def test_generate_performance_report():
    """Generate comprehensive performance report."""
    provider = MockProvider({"latency_ms": 50})

    report = {
        "provider": "mock",
        "tests": {},
        "timestamp": time.time()
    }

    # Test invocation
    latencies = []
    for i in range(10):
        response = provider.invoke(f"Test {i}")
        latencies.append(response.latency_ms)

    report["tests"]["invocation"] = {
        "count": len(latencies),
        "mean_ms": mean(latencies),
        "median_ms": median(latencies),
        "min_ms": min(latencies),
        "max_ms": max(latencies)
    }

    # Test token counting
    text = "test word " * 100
    count_times = []
    for _ in range(100):
        start = time.time()
        provider.get_token_count(text)
        count_times.append((time.time() - start) * 1000)

    report["tests"]["token_counting"] = {
        "count": len(count_times),
        "mean_ms": mean(count_times),
        "median_ms": median(count_times)
    }

    # Test health check
    health_times = []
    for _ in range(100):
        start = time.time()
        provider.health_check()
        health_times.append((time.time() - start) * 1000)

    report["tests"]["health_check"] = {
        "count": len(health_times),
        "mean_ms": mean(health_times),
        "median_ms": median(health_times)
    }

    # Verify all tests completed
    assert len(report["tests"]) == 3
    assert all(t["count"] > 0 for t in report["tests"].values())


@pytest.mark.performance
def test_compare_provider_performance():
    """Compare performance across different providers."""
    fast = MockProvider({"latency_ms": 10})
    slow = MockProvider({"latency_ms": 100})

    results = {}

    for name, provider in [("fast", fast), ("slow", slow)]:
        latencies = []
        for i in range(5):
            response = provider.invoke(f"Test {i}")
            latencies.append(response.latency_ms)

        results[name] = {
            "mean_ms": mean(latencies),
            "median_ms": median(latencies)
        }

    # Verify fast is actually faster
    assert results["fast"]["mean_ms"] < results["slow"]["mean_ms"]
    assert results["fast"]["median_ms"] < results["slow"]["median_ms"]
