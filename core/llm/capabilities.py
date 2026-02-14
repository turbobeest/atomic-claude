"""
Provider capability registry.

Tracks what capabilities each provider/model supports for runtime
feature detection and graceful degradation.
"""

from typing import Dict, Set, Optional
from enum import Enum
from pydantic import BaseModel


class ModelCapability(str, Enum):
    """Capabilities a model/provider might support."""
    EXTENDED_THINKING = "extended_thinking"
    PROMPT_CACHING = "prompt_caching"
    VISION = "vision"
    TOOL_USE = "tool_use"
    STREAMING = "streaming"
    JSON_MODE = "json_mode"
    COMPUTER_USE = "computer_use"
    ANALYSIS = "analysis"


class ProviderCapabilities(BaseModel):
    """Capabilities supported by a provider."""
    provider_name: str
    available_models: list[str]
    capabilities: Set[ModelCapability]
    max_tokens: int  # Default/fallback context window for provider
    supports_system_prompt: bool = True
    supports_multiple_images: bool = False

    class Config:
        use_enum_values = False

    def supports(self, capability: ModelCapability) -> bool:
        """Check if provider supports a capability."""
        return capability in self.capabilities


# ---------------------------------------------------------------------------
# Per-model context windows (input token limits)
# ---------------------------------------------------------------------------
# Opus 4.6 has a 1M context window; Sonnet 4.5 and Haiku have 200K.
# Keys match both tier names and full model IDs for flexible lookup.

MODEL_CONTEXT_WINDOWS: Dict[str, int] = {
    # Tier shorthand
    "opus":   1_000_000,
    "sonnet":   200_000,
    "haiku":    200_000,
    # Full Anthropic model IDs
    "claude-opus-4-6":              1_000_000,
    "claude-opus-4-5":                200_000,
    "claude-opus-4":                  200_000,
    "claude-sonnet-4-5":              200_000,
    "claude-sonnet-4":                200_000,
    "claude-haiku-4":                 200_000,
    "claude-3-5-sonnet-20241022":     200_000,
    "claude-3-5-sonnet-20240620":     200_000,
    "claude-3-opus-20240229":         200_000,
    "claude-3-sonnet-20240229":       200_000,
    "claude-3-haiku-20240307":        200_000,
    # Bedrock model IDs
    "anthropic.claude-sonnet-4-5":                          200_000,
    "anthropic.claude-sonnet-3-5":                          200_000,
    "anthropic.claude-haiku-3-5":                           200_000,
    "us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0":     200_000,
}

# Per-model max output tokens
MODEL_MAX_OUTPUT: Dict[str, int] = {
    "opus":   32_000,
    "sonnet": 16_000,
    "haiku":   8_192,
    "claude-opus-4-6":              32_000,
    "claude-opus-4-5":              16_000,
    "claude-sonnet-4-5":            16_000,
    "claude-sonnet-4":              16_000,
    "claude-haiku-4":                8_192,
    "claude-3-5-sonnet-20241022":    8_192,
    "claude-3-5-sonnet-20240620":    8_192,
    "claude-3-opus-20240229":        4_096,
    "claude-3-sonnet-20240229":      4_096,
    "claude-3-haiku-20240307":       4_096,
}

# Models that support extended thinking
EXTENDED_THINKING_MODELS = {
    "opus", "claude-opus-4-6", "claude-opus-4-5",
    "sonnet", "claude-sonnet-4-5", "claude-sonnet-4",
}


# ---------------------------------------------------------------------------
# Registry of provider capabilities
# ---------------------------------------------------------------------------

PROVIDER_CAPABILITIES = {
    "anthropic": ProviderCapabilities(
        provider_name="anthropic",
        available_models=[
            "claude-opus-4.6",
            "claude-sonnet-4.5",
            "claude-sonnet-3.5",
            "claude-haiku-3.5",
        ],
        capabilities={
            ModelCapability.EXTENDED_THINKING,
            ModelCapability.PROMPT_CACHING,
            ModelCapability.VISION,
            ModelCapability.TOOL_USE,
            ModelCapability.STREAMING,
            ModelCapability.JSON_MODE,
            ModelCapability.COMPUTER_USE,
            ModelCapability.ANALYSIS,
        },
        max_tokens=200_000,
        supports_system_prompt=True,
        supports_multiple_images=True,
    ),

    "claude-code": ProviderCapabilities(
        provider_name="claude-code",
        available_models=[
            "claude-opus-4.6",
            "claude-sonnet-4.5",
            "claude-haiku-3.5",
        ],
        capabilities={
            ModelCapability.EXTENDED_THINKING,
            ModelCapability.PROMPT_CACHING,
            ModelCapability.VISION,
            ModelCapability.TOOL_USE,
            ModelCapability.STREAMING,
            ModelCapability.JSON_MODE,
            ModelCapability.COMPUTER_USE,
            ModelCapability.ANALYSIS,
        },
        max_tokens=1_000_000,  # Opus 4.6 default for subscription users
        supports_system_prompt=True,
        supports_multiple_images=True,
    ),

    "bedrock": ProviderCapabilities(
        provider_name="bedrock",
        available_models=[
            "us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0",
            "anthropic.claude-sonnet-4-5",
            "anthropic.claude-sonnet-3-5",
            "anthropic.claude-haiku-3-5",
        ],
        capabilities={
            ModelCapability.PROMPT_CACHING,  # May be delayed
            ModelCapability.VISION,
            ModelCapability.TOOL_USE,
            ModelCapability.STREAMING,
            ModelCapability.JSON_MODE,
        },
        max_tokens=200_000,
        supports_system_prompt=True,
        supports_multiple_images=True,
    ),

    "ollama": ProviderCapabilities(
        provider_name="ollama",
        available_models=["qwen2.5-coder:32b", "llama3.1", "mistral"],
        capabilities={
            ModelCapability.STREAMING,
            ModelCapability.JSON_MODE,
        },
        max_tokens=32_000,
        supports_system_prompt=True,
        supports_multiple_images=False,
    ),
}


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

def get_provider_capabilities(provider: str) -> Optional[ProviderCapabilities]:
    """Get capabilities for a provider."""
    return PROVIDER_CAPABILITIES.get(provider)


def provider_supports(provider: str, capability: ModelCapability) -> bool:
    """Check if provider supports a capability."""
    caps = get_provider_capabilities(provider)
    return caps.supports(capability) if caps else False


def get_model_context_window(model: str) -> int:
    """
    Get the context window (max input tokens) for a model.

    Args:
        model: Model name or tier (e.g. "opus", "claude-opus-4-6")

    Returns:
        Context window size in tokens (defaults to 200_000 if unknown)
    """
    return MODEL_CONTEXT_WINDOWS.get(model, 200_000)


def get_model_max_output(model: str) -> int:
    """
    Get the max output tokens for a model.

    Args:
        model: Model name or tier

    Returns:
        Max output tokens (defaults to 4_096 if unknown)
    """
    return MODEL_MAX_OUTPUT.get(model, 4_096)


def model_supports(
    provider: str,
    model: str,
    capability: ModelCapability
) -> bool:
    """
    Check if specific model supports a capability.

    For extended thinking, checks per-model support.
    Other capabilities use provider-level check.
    """
    if capability == ModelCapability.EXTENDED_THINKING:
        if model not in EXTENDED_THINKING_MODELS:
            return False
    return provider_supports(provider, capability)
