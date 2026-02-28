"""
Feature-aware LLM invocation.

Automatically handles feature flags, provider capabilities, and graceful
degradation when features are unavailable.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, Iterator

logger = logging.getLogger(__name__)

from .base import BaseLLMProvider
from .capabilities import ModelCapability, provider_supports
from core.features.flags import Feature, get_feature_flags


# Default thinking budget (can be overridden via project config)
_DEFAULT_THINKING_BUDGET = 10_000

# Tier names that need resolution to provider-specific model IDs
_TIER_NAMES = frozenset({"opus", "sonnet", "haiku"})

# Lazy singleton router
_default_router = None

# Cached model_ids from config/models.json (loaded once)
_model_ids_cache: Optional[Dict[str, Dict[str, str]]] = None


def _load_model_ids() -> Dict[str, Dict[str, str]]:
    """Load model_ids from config/models.json (cached)."""
    global _model_ids_cache
    if _model_ids_cache is not None:
        return _model_ids_cache

    config_path = Path(__file__).parent.parent.parent / "config" / "models.json"
    try:
        data = json.loads(config_path.read_text())
        _model_ids_cache = data.get("model_ids", {})
    except Exception as e:
        logger.debug("Failed to load model_ids from config: %s", e)
        _model_ids_cache = {}

    return _model_ids_cache


def _resolve_model_for_provider(model: str, provider: BaseLLMProvider) -> str:
    """
    Resolve a tier name (opus/sonnet/haiku) to a provider-specific model ID.

    Uses config/models.json as the single source of truth.
    If the model is already a full model ID (not a tier name), returns it as-is.

    Args:
        model: Tier name or full model ID
        provider: Active provider instance

    Returns:
        Provider-specific model ID
    """
    if model not in _TIER_NAMES:
        return model  # Already a full model ID, pass through

    provider_name = getattr(provider, "provider_name", "")
    model_ids = _load_model_ids()

    # Look up provider-specific model ID
    provider_models = model_ids.get(provider_name, {})
    if model in provider_models:
        return provider_models[model]

    # Fallback: return tier name and let the provider's own _resolve_model handle it
    return model


def _get_default_router():
    """Lazy singleton router initialized from Config."""
    global _default_router
    if _default_router is not None:
        return _default_router

    from .router import LLMRouter
    from .types import ModelRole

    _default_router = LLMRouter()

    # Try to create provider from config
    try:
        from core.config import Config
        config = Config()
        provider_name = config.get("llm.primary_provider", "api")
    except Exception as e:
        logger.debug("Failed to load provider config, defaulting to api: %s", e)
        provider_name = "api"

    # Register provider based on config
    if provider_name == "claude-code":
        try:
            from .claude_code import ClaudeCodeProvider
            import shutil
            if shutil.which("claude"):
                provider = ClaudeCodeProvider(config={})
                _default_router.register_provider(
                    "claude-code", provider,
                    [ModelRole.PRIMARY, ModelRole.FAST, ModelRole.HEAVYWEIGHT]
                )
        except Exception as e:
            print(f"  [llm] Claude Code provider init warning: {e}")

    elif provider_name in ("api", "max"):
        try:
            from .anthropic import AnthropicProvider
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if api_key:
                provider = AnthropicProvider(config={"api_key": api_key})
                _default_router.register_provider(
                    "anthropic", provider,
                    [ModelRole.PRIMARY, ModelRole.FAST, ModelRole.HEAVYWEIGHT]
                )
        except Exception as e:
            print(f"  [llm] Anthropic provider init warning: {e}")

    elif provider_name == "bedrock":
        try:
            from .bedrock import BedrockProvider
            provider = BedrockProvider(config={})
            _default_router.register_provider(
                "bedrock", provider,
                [ModelRole.PRIMARY, ModelRole.FAST, ModelRole.HEAVYWEIGHT]
            )
        except Exception as e:
            print(f"  [llm] Bedrock provider init warning: {e}")

    elif provider_name == "ollama":
        try:
            from .ollama import OllamaProvider
            provider = OllamaProvider(config={})
            _default_router.register_provider(
                "ollama", provider,
                [ModelRole.PRIMARY, ModelRole.FAST]
            )
        except Exception as e:
            print(f"  [llm] Ollama provider init warning: {e}")

    # Fallback: if no provider registered yet but claude CLI is available, use it
    if not _default_router.get_provider():
        try:
            import shutil
            if shutil.which("claude"):
                from .claude_code import ClaudeCodeProvider
                provider = ClaudeCodeProvider(config={})
                _default_router.register_provider(
                    "claude-code", provider,
                    [ModelRole.PRIMARY, ModelRole.FAST, ModelRole.HEAVYWEIGHT]
                )
        except Exception as e:
            logger.debug("Fallback Claude Code provider init failed: %s", e)

    return _default_router


# Per-million-token pricing (USD) by model tier.
# Source: https://platform.claude.com/docs/en/about-claude/pricing
_MODEL_PRICING = {
    # Opus 4.6 / 4.5
    "opus": {"input": 5.0, "output": 25.0},
    # Sonnet 4.5 / 4
    "sonnet": {"input": 3.0, "output": 15.0},
    # Haiku 4.5
    "haiku": {"input": 1.0, "output": 5.0},
}

# Providers where per-token cost is not applicable
_NO_COST_PROVIDERS = {"claude-code", "ollama"}


def _resolve_tier(model_id: str) -> str | None:
    """Map a model ID string to a pricing tier."""
    if not model_id:
        return None
    m = model_id.lower()
    if "opus" in m:
        return "opus"
    if "sonnet" in m:
        return "sonnet"
    if "haiku" in m:
        return "haiku"
    return None


def _track_tokens(response):
    """Update session token tracking file with usage and cost."""
    try:
        tokens_file = Path(os.environ.get("ATOMIC_ROOT", ".")) / ".state" / "session-tokens.json"
        if tokens_file.exists():
            data = json.loads(tokens_file.read_text())
        else:
            data = {
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "estimated_cost_usd": 0,
                "cost_available": True,
                "by_provider": {},
                "by_model": {},
            }

        # Extract usage
        input_toks = 0
        output_toks = 0
        if hasattr(response, 'usage'):
            usage = response.usage
            input_toks = getattr(usage, 'input_tokens', 0) or 0
            output_toks = getattr(usage, 'output_tokens', 0) or 0

        if input_toks == 0 and output_toks == 0:
            return

        data["total_input_tokens"] += input_toks
        data["total_output_tokens"] += output_toks

        # Determine provider and model
        provider_name = getattr(response, 'provider', None) or "unknown"
        model_id = getattr(response, 'model', None) or "unknown"

        # Track by_provider
        if provider_name not in data["by_provider"]:
            data["by_provider"][provider_name] = {
                "input_tokens": 0, "output_tokens": 0, "cost_usd": 0,
            }
        prov = data["by_provider"][provider_name]
        prov["input_tokens"] += input_toks
        prov["output_tokens"] += output_toks

        # Track by_model
        if model_id not in data["by_model"]:
            data["by_model"][model_id] = {
                "input_tokens": 0, "output_tokens": 0, "cost_usd": 0,
            }
        mdl = data["by_model"][model_id]
        mdl["input_tokens"] += input_toks
        mdl["output_tokens"] += output_toks

        # Calculate cost (skip for subscription/local providers)
        if provider_name in _NO_COST_PROVIDERS:
            data["cost_available"] = False
        else:
            tier = _resolve_tier(model_id)
            if tier and tier in _MODEL_PRICING:
                pricing = _MODEL_PRICING[tier]
                call_cost = (
                    (input_toks / 1_000_000) * pricing["input"]
                    + (output_toks / 1_000_000) * pricing["output"]
                )
                data["estimated_cost_usd"] += call_cost
                prov["cost_usd"] += call_cost
                mdl["cost_usd"] += call_cost

        tokens_file.parent.mkdir(parents=True, exist_ok=True)
        tokens_file.write_text(json.dumps(data, indent=2))
    except Exception as e:
        logger.warning("Token tracking failed: %s", e)


class FeatureAwareLLMInvoker:
    """LLM invoker that respects feature flags and provider capabilities."""

    def __init__(self, provider: BaseLLMProvider, thinking_budget: Optional[int] = None):
        self.provider = provider
        self.flags = get_feature_flags()
        self.thinking_budget = thinking_budget or _DEFAULT_THINKING_BUDGET

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

        # Auto-inject skill context into system_prompt
        try:
            from core.skills.context_formatter import get_active_skill_context
            skill_ctx = get_active_skill_context()
            if skill_ctx:
                existing = params.get("system_prompt") or ""
                params["system_prompt"] = (
                    f"{existing}\n\n{skill_ctx}".strip() if existing else skill_ctx
                )
        except Exception:
            pass  # Skill context injection is best-effort

        # Extended thinking
        if use_extended_thinking:
            can_use, reason = self._can_use_extended_thinking()
            if can_use:
                params["thinking"] = {"type": "enabled", "budget_tokens": self.thinking_budget}
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
                params["thinking"] = {"type": "enabled", "budget_tokens": self.thinking_budget}

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
    prompt_or_file=None,
    output_or_provider=None,
    description=None,
    *,
    prompt=None,
    prompt_file=None,
    output_file=None,
    model=None,
    provider=None,
    **kwargs
) -> str:
    """
    High-level LLM invocation with automatic feature handling.

    Supports multiple calling patterns:
      invoke_llm("prompt text", model="sonnet")
      invoke_llm(prompt="text", output_file="out.md", model="opus")
      invoke_llm("prompt.md", "output.md", "description", model="sonnet")

    Args:
        prompt_or_file: Prompt text or path to prompt file
        output_or_provider: Output file path or provider instance
        description: Optional description (ignored, for compatibility)
        prompt: Keyword prompt text (takes priority)
        prompt_file: Path to prompt file (keyword)
        output_file: Path to write output (keyword)
        model: Model name or tier ("sonnet", "opus", "haiku")
        provider: Provider instance (if None, uses default router)
        **kwargs: Additional parameters including feature flags

    Returns:
        Response string from LLM
    """
    # --- Resolve prompt text ---
    actual_prompt = prompt  # keyword takes priority
    if actual_prompt is None and prompt_file is not None:
        actual_prompt = Path(prompt_file).read_text()
    if actual_prompt is None and prompt_or_file is not None:
        try:
            p = Path(str(prompt_or_file))
            if p.exists() and p.is_file():
                actual_prompt = p.read_text()
            else:
                actual_prompt = str(prompt_or_file)
        except OSError:
            # Handles ENAMETOOLONG and similar OS errors when the string
            # is clearly prompt text, not a file path
            actual_prompt = str(prompt_or_file)
    if actual_prompt is None:
        raise ValueError("No prompt provided")

    # --- Resolve output file ---
    actual_output_file = output_file  # keyword takes priority
    if actual_output_file is None and output_or_provider is not None:
        if isinstance(output_or_provider, str):
            actual_output_file = output_or_provider
        elif isinstance(output_or_provider, BaseLLMProvider):
            provider = output_or_provider

    # --- Get provider ---
    if provider is None:
        router = _get_default_router()
        provider = router.get_provider()
    if provider is None:
        raise RuntimeError(
            "No LLM provider available. Set ANTHROPIC_API_KEY or configure a provider."
        )

    # --- Resolve model tier to provider-specific model ID ---
    invoke_kwargs = {k: v for k, v in kwargs.items()
                     if k not in ('prompt_file', 'output_file', 'description')}
    if model is not None:
        invoke_kwargs['model'] = _resolve_model_for_provider(model, provider)

    invoker = FeatureAwareLLMInvoker(provider)
    response = invoker.invoke(actual_prompt, **invoke_kwargs)

    # Track token usage
    _track_tokens(response)

    # response may be str or LLMResponse
    if hasattr(response, 'content'):
        result_text = response.content
    else:
        result_text = str(response)

    # --- Write output file if specified ---
    if actual_output_file:
        out_path = Path(actual_output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(result_text)

    return result_text


def stream_llm(
    prompt: str,
    provider: Optional[BaseLLMProvider] = None,
    **kwargs
) -> Iterator[str]:
    """
    High-level LLM streaming with automatic feature handling.

    Args:
        prompt: The prompt to send
        provider: Provider instance (if None, uses default router)
        **kwargs: Additional parameters including feature flags

    Yields:
        Response chunks from LLM
    """
    if provider is None:
        router = _get_default_router()
        provider = router.get_provider()
    if provider is None:
        raise RuntimeError(
            "No LLM provider available. Set ANTHROPIC_API_KEY or configure a provider."
        )

    # Resolve model tier if present in kwargs
    if "model" in kwargs:
        kwargs = dict(kwargs)
        kwargs["model"] = _resolve_model_for_provider(kwargs["model"], provider)

    invoker = FeatureAwareLLMInvoker(provider)
    yield from invoker.stream(prompt, **kwargs)
