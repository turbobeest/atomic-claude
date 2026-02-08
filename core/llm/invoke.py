"""
Feature-aware LLM invocation.

Automatically handles feature flags, provider capabilities, and graceful
degradation when features are unavailable.
"""

from typing import Optional, Dict, Any, Iterator
from .base import BaseLLMProvider
from .capabilities import ModelCapability, provider_supports
from core.features.flags import Feature, get_feature_flags


class FeatureAwareLLMInvoker:
    """LLM invoker that respects feature flags and provider capabilities."""

    def __init__(self, provider: BaseLLMProvider):
        self.provider = provider
        self.flags = get_feature_flags()

    def invoke(
        self,
        prompt: str,
        *,
        use_extended_thinking: bool = False,
        use_caching: bool = False,
        use_analysis: bool = False,
        **kwargs
    ) -> str:
        """
        Invoke LLM with feature-aware parameter handling.

        Features are automatically disabled if:
        - Feature flag is off
        - Provider doesn't support it
        - Dependencies not met

        Args:
            prompt: The prompt to send
            use_extended_thinking: Enable extended thinking if available
            use_caching: Enable prompt caching if available
            use_analysis: Enable analysis tool if available
            **kwargs: Additional provider-specific parameters

        Returns:
            Response string from LLM
        """
        params = kwargs.copy()

        # Extended thinking
        if use_extended_thinking:
            can_use, reason = self._can_use_extended_thinking()
            if can_use:
                params["thinking"] = {"type": "enabled", "budget_tokens": 10000}
            elif reason:
                print(f"⚠️  Extended thinking disabled: {reason}")

        # Prompt caching
        if use_caching:
            can_use, reason = self._can_use_caching()
            if can_use:
                params["cache_control"] = {"type": "ephemeral"}
            elif reason:
                print(f"⚠️  Prompt caching disabled: {reason}")

        # Analysis tool
        if use_analysis:
            can_use, reason = self._can_use_analysis()
            if can_use:
                params["tools"] = params.get("tools", []) + [self._get_analysis_tool()]
            elif reason:
                print(f"⚠️  Analysis tool disabled: {reason}")

        # Invoke with processed parameters
        return self.provider.invoke(prompt, **params)

    def stream(
        self,
        prompt: str,
        *,
        use_extended_thinking: bool = False,
        use_caching: bool = False,
        use_analysis: bool = False,
        **kwargs
    ) -> Iterator[str]:
        """
        Stream LLM response with feature-aware parameter handling.

        Args:
            prompt: The prompt to send
            use_extended_thinking: Enable extended thinking if available
            use_caching: Enable prompt caching if available
            use_analysis: Enable analysis tool if available
            **kwargs: Additional provider-specific parameters

        Yields:
            Response chunks from LLM
        """
        params = kwargs.copy()

        # Apply same feature handling as invoke
        if use_extended_thinking:
            can_use, reason = self._can_use_extended_thinking()
            if can_use:
                params["thinking"] = {"type": "enabled", "budget_tokens": 10000}

        if use_caching:
            can_use, reason = self._can_use_caching()
            if can_use:
                params["cache_control"] = {"type": "ephemeral"}

        if use_analysis:
            can_use, reason = self._can_use_analysis()
            if can_use:
                params["tools"] = params.get("tools", []) + [self._get_analysis_tool()]

        # Stream with processed parameters
        yield from self.provider.stream(prompt, **params)

    def _can_use_extended_thinking(self) -> tuple[bool, Optional[str]]:
        """Check if extended thinking can be used."""
        # Check feature flag
        can_use, reason = self.flags.can_use_feature(
            Feature.EXTENDED_THINKING,
            self.provider.provider_name,
            getattr(self.provider, 'model', None)
        )
        if not can_use:
            return False, reason

        # Check provider capability
        if not provider_supports(
            self.provider.provider_name,
            ModelCapability.EXTENDED_THINKING
        ):
            return False, "Provider doesn't support extended thinking"

        return True, None

    def _can_use_caching(self) -> tuple[bool, Optional[str]]:
        """Check if prompt caching can be used."""
        can_use, reason = self.flags.can_use_feature(
            Feature.PROMPT_CACHING,
            self.provider.provider_name
        )
        if not can_use:
            return False, reason

        if not provider_supports(
            self.provider.provider_name,
            ModelCapability.PROMPT_CACHING
        ):
            return False, "Provider doesn't support prompt caching"

        return True, None

    def _can_use_analysis(self) -> tuple[bool, Optional[str]]:
        """Check if analysis tool can be used."""
        can_use, reason = self.flags.can_use_feature(
            Feature.ANALYSIS_TOOL,
            self.provider.provider_name
        )
        if not can_use:
            return False, reason

        if not provider_supports(
            self.provider.provider_name,
            ModelCapability.ANALYSIS
        ):
            return False, "Provider doesn't support analysis tool"

        return True, None

    def _get_analysis_tool(self) -> Dict[str, Any]:
        """Get analysis tool definition."""
        return {
            "type": "analysis",
            "name": "code_analysis",
            "description": "Analyze code, data, or perform computations",
        }


def invoke_llm(
    prompt: str,
    provider: Optional[BaseLLMProvider] = None,
    **kwargs
) -> str:
    """
    High-level LLM invocation with automatic feature handling.

    Args:
        prompt: The prompt to send
        provider: Provider instance (if None, uses router)
        **kwargs: Additional parameters including feature flags

    Returns:
        Response string from LLM
    """
    if provider is None:
        from .router import LLMRouter
        router = LLMRouter()
        provider = router.get_provider()

    invoker = FeatureAwareLLMInvoker(provider)
    return invoker.invoke(prompt, **kwargs)


def stream_llm(
    prompt: str,
    provider: Optional[BaseLLMProvider] = None,
    **kwargs
) -> Iterator[str]:
    """
    High-level LLM streaming with automatic feature handling.

    Args:
        prompt: The prompt to send
        provider: Provider instance (if None, uses router)
        **kwargs: Additional parameters including feature flags

    Yields:
        Response chunks from LLM
    """
    if provider is None:
        from .router import LLMRouter
        router = LLMRouter()
        provider = router.get_provider()

    invoker = FeatureAwareLLMInvoker(provider)
    yield from invoker.stream(prompt, **kwargs)
