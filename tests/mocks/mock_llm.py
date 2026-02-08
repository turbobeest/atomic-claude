#!/usr/bin/env python3
"""
Mock LLM Provider for Testing

Provides a fully-featured mock provider implementing BaseLLMProvider
for testing without real API calls or local LLM services.

Features:
- Configurable responses
- Latency simulation
- Error injection
- Token counting
- Call tracking
"""

import time
from typing import Dict, Generator, Optional, Any, List
from datetime import datetime
from dataclasses import dataclass, field

from core.llm.base import (
    BaseLLMProvider,
    LLMResponse,
    TokenUsage,
    HealthStatus,
    LLMError,
    APIError,
    RateLimitError,
    TimeoutError,
    ModelNotFoundError,
)


@dataclass
class MockCall:
    """Record of a mock LLM call."""
    prompt: str
    system_prompt: Optional[str]
    model: Optional[str]
    timestamp: datetime = field(default_factory=datetime.now)
    kwargs: Dict[str, Any] = field(default_factory=dict)


class MockProvider(BaseLLMProvider):
    """
    Mock LLM provider for testing.

    Configuration:
    - default_response: Default response text (default: "Mock response")
    - responses: Dict mapping prompts to specific responses
    - latency_ms: Simulated latency in milliseconds (default: 100)
    - error_mode: Error to raise (None, "api_error", "timeout", "rate_limit", "model_not_found")
    - error_after_calls: Raise error after N successful calls (default: None)
    - token_ratio: Tokens per word ratio for counting (default: 0.75)
    - health_status: Simulated health status (default: HealthStatus.HEALTHY)
    - supported_models: List of supported models (default: ["mock-model"])
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize mock provider.

        Args:
            config: Provider configuration
        """
        super().__init__(config)
        self.provider_name = "mock"

        # Configuration
        self.default_response = self.config.get("default_response", "Mock response")
        self.responses = self.config.get("responses", {})
        self.latency_ms = self.config.get("latency_ms", 100)
        self.error_mode = self.config.get("error_mode", None)
        self.error_after_calls = self.config.get("error_after_calls", None)
        self.token_ratio = self.config.get("token_ratio", 0.75)
        self.health_status_value = self.config.get("health_status", HealthStatus.HEALTHY)
        self.supported_models_list = self.config.get("supported_models", ["mock-model"])

        # Call tracking
        self.calls: List[MockCall] = []
        self.stream_calls: List[MockCall] = []

    def _simulate_latency(self):
        """Simulate network/processing latency."""
        if self.latency_ms > 0:
            time.sleep(self.latency_ms / 1000.0)

    def _check_error_injection(self):
        """Check if we should raise an error."""
        # Check if we should error after N calls (count happens BEFORE this call)
        if self.error_after_calls is not None:
            # We want to error on the (N+1)th call, after N successful calls
            # calls list has already been appended to, so len(calls)-1 is the previous count
            if len(self.calls) > self.error_after_calls:
                # Inject error then reset
                if self.error_mode:
                    error_mode = self.error_mode
                    self.error_mode = None  # Reset before raising
                    self.error_after_calls = None
                    if error_mode == "api_error":
                        raise APIError("Mock API error", provider="mock")
                    elif error_mode == "timeout":
                        raise TimeoutError("Mock timeout error", provider="mock")
                    elif error_mode == "rate_limit":
                        raise RateLimitError("Mock rate limit error", provider="mock", retry_after=60)
                    elif error_mode == "model_not_found":
                        raise ModelNotFoundError("Mock model not found", provider="mock")
        # Check immediate error mode (only if not after_calls mode)
        elif self.error_mode:
            self._raise_error()

    def _raise_error(self):
        """Raise configured error."""
        if self.error_mode == "api_error":
            raise APIError("Mock API error", provider="mock")
        elif self.error_mode == "timeout":
            raise TimeoutError("Mock timeout error", provider="mock")
        elif self.error_mode == "rate_limit":
            raise RateLimitError("Mock rate limit error", provider="mock", retry_after=60)
        elif self.error_mode == "model_not_found":
            raise ModelNotFoundError("Mock model not found", provider="mock")

    def _get_response(self, prompt: str) -> str:
        """Get response for a prompt."""
        # Check for specific response mapping
        if prompt in self.responses:
            return self.responses[prompt]

        # Check for partial match
        for key, value in self.responses.items():
            if key in prompt:
                return value

        # Return default
        return self.default_response

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
        Mock invocation.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            model: Model name
            max_tokens: Maximum tokens
            temperature: Sampling temperature
            timeout: Request timeout
            **kwargs: Additional parameters

        Returns:
            LLMResponse with mock content
        """
        start_time = time.time()

        # Record call with all parameters
        call_kwargs = {
            'max_tokens': max_tokens,
            'temperature': temperature,
            'timeout': timeout,
        }
        call_kwargs.update(kwargs)

        self.calls.append(MockCall(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            kwargs=call_kwargs
        ))

        # Check for error injection
        self._check_error_injection()

        # Simulate latency
        self._simulate_latency()

        # Get response
        content = self._get_response(prompt)

        # Build combined prompt for token counting
        combined_prompt = prompt
        if system_prompt:
            combined_prompt = f"{system_prompt}\n\n{prompt}"

        # Calculate token usage
        input_tokens = self.get_token_count(combined_prompt, model)
        output_tokens = self.get_token_count(content, model)

        usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )

        # Calculate latency
        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)

        return LLMResponse(
            content=content,
            model=model or "mock-model",
            provider=self.provider_name,
            usage=usage,
            finish_reason="stop",
            latency_ms=latency_ms,
            timestamp=datetime.now(),
            metadata={
                "mock": True,
                "call_number": len(self.calls),
            }
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
        Mock streaming.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            model: Model name
            max_tokens: Maximum tokens
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Yields:
            Text chunks
        """
        # Record call
        self.stream_calls.append(MockCall(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            kwargs=kwargs
        ))

        # Check for error injection
        self._check_error_injection()

        # Get response
        content = self._get_response(prompt)

        # Split into chunks (simulate streaming)
        words = content.split()
        for i, word in enumerate(words):
            # Simulate latency between chunks
            if self.latency_ms > 0:
                time.sleep(self.latency_ms / 1000.0 / len(words))

            # Yield word with space
            if i > 0:
                yield " "
            yield word

    def validate_model(self, model_name: str) -> bool:
        """
        Check if model is supported.

        Args:
            model_name: Model identifier

        Returns:
            True if model is in supported list
        """
        return model_name in self.supported_models_list

    def get_token_count(self, text: str, model: Optional[str] = None) -> int:
        """
        Estimate token count.

        Args:
            text: Input text
            model: Model name (unused)

        Returns:
            Estimated token count
        """
        words = text.split()
        return int(len(words) * self.token_ratio)

    def health_check(self) -> HealthStatus:
        """
        Mock health check.

        Returns:
            Configured health status
        """
        return self.health_status_value

    def get_default_model(self) -> Optional[str]:
        """Get default model."""
        return self.config.get("default_model", "mock-model")

    def get_supported_models(self) -> List[str]:
        """Get list of supported models."""
        return self.supported_models_list

    def reset_calls(self):
        """Reset call tracking."""
        self.calls.clear()
        self.stream_calls.clear()

    def get_call_count(self) -> int:
        """Get number of invoke() calls."""
        return len(self.calls)

    def get_stream_call_count(self) -> int:
        """Get number of stream() calls."""
        return len(self.stream_calls)

    def get_last_call(self) -> Optional[MockCall]:
        """Get last invoke() call."""
        return self.calls[-1] if self.calls else None

    def get_last_stream_call(self) -> Optional[MockCall]:
        """Get last stream() call."""
        return self.stream_calls[-1] if self.stream_calls else None

    def set_response(self, prompt: str, response: str):
        """
        Set specific response for a prompt.

        Args:
            prompt: Prompt text or partial match
            response: Response to return
        """
        self.responses[prompt] = response

    def set_error_mode(self, error_mode: Optional[str], after_calls: Optional[int] = None):
        """
        Configure error injection.

        Args:
            error_mode: Error type (None, "api_error", "timeout", "rate_limit", "model_not_found")
            after_calls: Raise error after N successful calls
        """
        self.error_mode = error_mode
        self.error_after_calls = after_calls

    def set_health_status(self, status: HealthStatus):
        """
        Set health status.

        Args:
            status: Health status to return
        """
        self.health_status_value = status

    def __repr__(self) -> str:
        """String representation."""
        return f"MockProvider(calls={len(self.calls)}, stream_calls={len(self.stream_calls)})"
