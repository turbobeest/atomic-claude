"""
Provider capability registry.

Tracks what capabilities each provider/model supports for runtime
feature detection and graceful degradation.
"""

from typing import Set, Optional
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
    max_tokens: int
    supports_system_prompt: bool = True
    supports_multiple_images: bool = False

    class Config:
        use_enum_values = False

    def supports(self, capability: ModelCapability) -> bool:
        """Check if provider supports a capability."""
        return capability in self.capabilities


# Registry of provider capabilities
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


def get_provider_capabilities(provider: str) -> Optional[ProviderCapabilities]:
    """Get capabilities for a provider."""
    return PROVIDER_CAPABILITIES.get(provider)


def provider_supports(provider: str, capability: ModelCapability) -> bool:
    """Check if provider supports a capability."""
    caps = get_provider_capabilities(provider)
    return caps.supports(capability) if caps else False


def model_supports(
    provider: str,
    model: str,
    capability: ModelCapability
) -> bool:
    """
    Check if specific model supports a capability.

    For now, assumes all models from a provider have same capabilities.
    Can be extended later for per-model capability differences.
    """
    return provider_supports(provider, capability)
