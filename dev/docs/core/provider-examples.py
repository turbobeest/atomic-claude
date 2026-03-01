#!/usr/bin/env python3
"""
Example usage of Anthropic and AWS Bedrock providers.

Run with:
    python docs/core/provider-examples.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.llm.anthropic import AnthropicProvider
from core.llm.bedrock import BedrockProvider
from core.llm.base import (
    HealthStatus,
    AuthenticationError,
    RateLimitError,
)


def example_anthropic_basic():
    """Basic Anthropic provider usage."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Anthropic Invocation")
    print("="*60)

    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  ANTHROPIC_API_KEY not set, skipping example")
        return

    # Create provider
    provider = AnthropicProvider()

    # Simple invocation
    response = provider.invoke(
        prompt="What is 2+2? Answer with just the number.",
        model="haiku",  # Use fastest/cheapest model
        max_tokens=10,
        temperature=0.0
    )

    print(f"Response: {response.content}")
    print(f"Model: {response.model}")
    print(f"Tokens: {response.usage.total_tokens}")
    print(f"Latency: {response.latency_ms}ms")


def example_anthropic_streaming():
    """Streaming with Anthropic provider."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Anthropic Streaming")
    print("="*60)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  ANTHROPIC_API_KEY not set, skipping example")
        return

    provider = AnthropicProvider()

    print("Streaming response: ", end="", flush=True)

    for chunk in provider.stream(
        prompt="Count from 1 to 5.",
        model="haiku",
        max_tokens=50,
        temperature=0.0
    ):
        print(chunk, end="", flush=True)

    print()


def example_anthropic_system_prompt():
    """Using system prompts."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Anthropic with System Prompt")
    print("="*60)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  ANTHROPIC_API_KEY not set, skipping example")
        return

    provider = AnthropicProvider()

    response = provider.invoke(
        prompt="What do you think about Python?",
        system_prompt="You are a grumpy old programmer who only likes Assembly.",
        model="haiku",
        max_tokens=100,
        temperature=0.7
    )

    print(f"Response: {response.content}")


def example_bedrock_basic():
    """Basic Bedrock provider usage."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Basic AWS Bedrock Invocation")
    print("="*60)

    # Check for AWS credentials
    has_creds = (
        os.environ.get("AWS_ACCESS_KEY_ID") or
        os.environ.get("AWS_PROFILE")
    )

    if not has_creds:
        print("⚠️  AWS credentials not configured, skipping example")
        return

    try:
        # Create provider
        provider = BedrockProvider(config={
            "aws_region": "us-east-1"
        })

        # Simple invocation
        response = provider.invoke(
            prompt="What is the capital of France? Answer with just the city name.",
            model="haiku",
            max_tokens=20,
            temperature=0.0
        )

        print(f"Response: {response.content}")
        print(f"Model: {response.model}")
        print(f"Tokens: {response.usage.total_tokens}")
        print(f"Latency: {response.latency_ms}ms")

    except AuthenticationError as e:
        print(f"⚠️  AWS Bedrock not accessible: {e}")


def example_bedrock_streaming():
    """Streaming with Bedrock provider."""
    print("\n" + "="*60)
    print("EXAMPLE 5: AWS Bedrock Streaming")
    print("="*60)

    has_creds = (
        os.environ.get("AWS_ACCESS_KEY_ID") or
        os.environ.get("AWS_PROFILE")
    )

    if not has_creds:
        print("⚠️  AWS credentials not configured, skipping example")
        return

    try:
        provider = BedrockProvider()

        print("Streaming response: ", end="", flush=True)

        for chunk in provider.stream(
            prompt="Name three programming languages.",
            model="haiku",
            max_tokens=50,
            temperature=0.0
        ):
            print(chunk, end="", flush=True)

        print()

    except AuthenticationError as e:
        print(f"⚠️  AWS Bedrock not accessible: {e}")


def example_health_checks():
    """Health check examples."""
    print("\n" + "="*60)
    print("EXAMPLE 6: Health Checks")
    print("="*60)

    # Anthropic health check
    if os.environ.get("ANTHROPIC_API_KEY"):
        provider = AnthropicProvider()
        status = provider.health_check()
        print(f"Anthropic Status: {status.value}")
    else:
        print("Anthropic: SKIPPED (no API key)")

    # Bedrock health check
    has_aws_creds = (
        os.environ.get("AWS_ACCESS_KEY_ID") or
        os.environ.get("AWS_PROFILE")
    )

    if has_aws_creds:
        try:
            provider = BedrockProvider()
            status = provider.health_check()
            print(f"Bedrock Status: {status.value}")
        except Exception as e:
            print(f"Bedrock: UNAVAILABLE ({e})")
    else:
        print("Bedrock: SKIPPED (no AWS credentials)")


def example_error_handling():
    """Error handling examples."""
    print("\n" + "="*60)
    print("EXAMPLE 7: Error Handling")
    print("="*60)

    # Test with invalid API key
    try:
        provider = AnthropicProvider(config={
            "api_key": "invalid-key-12345"
        })

        response = provider.invoke(
            prompt="Test",
            model="haiku",
            max_tokens=10
        )

    except AuthenticationError as e:
        print(f"✓ Caught AuthenticationError: {type(e).__name__}")

    # Test with invalid model
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            provider = AnthropicProvider()
            response = provider.invoke(
                prompt="Test",
                model="nonexistent-model-xyz",
                max_tokens=10
            )
        except Exception as e:
            print(f"✓ Caught error for invalid model: {type(e).__name__}")


def example_model_validation():
    """Model validation examples."""
    print("\n" + "="*60)
    print("EXAMPLE 8: Model Validation")
    print("="*60)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  ANTHROPIC_API_KEY not set, skipping example")
        return

    provider = AnthropicProvider()

    # Check tier names
    print("Tier name validation:")
    for tier in ["opus", "sonnet", "haiku"]:
        is_valid = provider.validate_model(tier)
        print(f"  {tier}: {'✓' if is_valid else '✗'}")

    # Get supported models
    models = provider.get_supported_models()
    print(f"\nSupported models: {len(models)}")
    print(f"Examples: {', '.join(models[:3])}")

    # Check invalid model
    is_valid = provider.validate_model("gpt-4")
    print(f"\ngpt-4 (invalid): {'✓' if is_valid else '✗'}")


def example_token_counting():
    """Token counting examples."""
    print("\n" + "="*60)
    print("EXAMPLE 9: Token Counting")
    print("="*60)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  ANTHROPIC_API_KEY not set, skipping example")
        return

    provider = AnthropicProvider()

    texts = [
        "Hello, world!",
        "This is a longer text that should have more tokens.",
        "The quick brown fox jumps over the lazy dog. " * 10,
    ]

    for text in texts:
        count = provider.get_token_count(text)
        print(f"Text: {text[:50]}...")
        print(f"Characters: {len(text)}, Estimated tokens: {count}\n")


def main():
    """Run all examples."""
    print("\n" + "#"*60)
    print("# LLM Provider Examples")
    print("#"*60)

    # Run examples
    example_anthropic_basic()
    example_anthropic_streaming()
    example_anthropic_system_prompt()
    example_bedrock_basic()
    example_bedrock_streaming()
    example_health_checks()
    example_error_handling()
    example_model_validation()
    example_token_counting()

    print("\n" + "#"*60)
    print("# Examples Complete")
    print("#"*60)
    print("\nNote: Some examples may be skipped if credentials are not configured.")
    print("Set ANTHROPIC_API_KEY for Anthropic examples.")
    print("Set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY or AWS_PROFILE for Bedrock examples.")


if __name__ == "__main__":
    main()
