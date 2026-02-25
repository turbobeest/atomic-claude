"""Tests for feature flag system."""

import pytest
from core.features.flags import Feature, FeatureConfig, FeatureFlags, get_feature_flags, set_feature_flags
from core.features.profiles import EnvironmentProfile
from core.llm.capabilities import (
    ModelCapability, provider_supports, get_provider_capabilities,
    get_model_context_window, get_model_max_output,
)


class TestFeatureFlags:
    """Test feature flag functionality."""

    def test_feature_enum_values(self):
        """Test feature enum has expected values."""
        assert Feature.OPUS_46 == "opus_46"
        assert Feature.EXTENDED_THINKING == "extended_thinking"
        assert Feature.AGENT_SWARMS == "agent_swarms"

    def test_feature_config_creation(self):
        """Test creating feature config."""
        config = FeatureConfig(
            enabled=True,
            required_provider="anthropic",
            fallback_behavior="disable"
        )
        assert config.enabled is True
        assert config.required_provider == "anthropic"
        assert config.fallback_behavior == "disable"

    def test_feature_flags_default(self):
        """Test default feature flags."""
        flags = FeatureFlags()
        assert flags.is_enabled(Feature.EXTENDED_THINKING) is True
        assert flags.is_enabled(Feature.COMPUTER_USE) is False

    def test_is_enabled_with_dependencies(self):
        """Test feature dependencies."""
        flags = FeatureFlags()

        # MCP_TOOLS depends on INTERNET_ACCESS
        # If internet disabled, MCP should be disabled
        flags.features[Feature.INTERNET_ACCESS].enabled = False
        assert flags.is_enabled(Feature.MCP_TOOLS) is False

    def test_can_use_feature_checks_provider(self):
        """Test provider requirements."""
        flags = FeatureFlags()

        # OPUS_46 requires anthropic provider
        can_use, reason = flags.can_use_feature(
            Feature.OPUS_46,
            "bedrock",
            "some-model"
        )
        assert can_use is False
        assert "requires anthropic" in reason.lower()

    def test_fallback_behavior(self):
        """Test getting fallback behavior."""
        flags = FeatureFlags()
        behavior = flags.get_fallback_behavior(Feature.OPUS_46)
        assert behavior == "downgrade"


class TestEnvironmentProfiles:
    """Test environment profile functionality."""

    def test_cloud_full_profile(self):
        """Test cloud full profile enables most features."""
        flags = EnvironmentProfile.cloud_full()
        assert flags.is_enabled(Feature.OPUS_46) is True
        assert flags.is_enabled(Feature.EXTENDED_THINKING) is True
        assert flags.is_enabled(Feature.AGENT_SWARMS) is True

    def test_air_gapped_profile(self):
        """Test air-gapped profile disables network features."""
        flags = EnvironmentProfile.air_gapped()
        assert flags.is_enabled(Feature.INTERNET_ACCESS) is False
        assert flags.is_enabled(Feature.API_CALLS) is False
        assert flags.is_enabled(Feature.OPUS_46) is False
        assert flags.is_enabled(Feature.FILE_SYSTEM) is True

    def test_enterprise_secure_profile(self):
        """Test enterprise profile balances features and security."""
        flags = EnvironmentProfile.enterprise_secure()
        assert flags.is_enabled(Feature.OPUS_46) is True
        assert flags.is_enabled(Feature.COMPUTER_USE) is False
        assert flags.is_enabled(Feature.MCP_TOOLS) is False

    def test_development_profile(self):
        """Test development profile enables everything."""
        flags = EnvironmentProfile.development()
        # All features should be enabled
        for feature in Feature:
            assert flags.is_enabled(feature) is True

    def test_from_name(self):
        """Test loading profile by name."""
        flags = EnvironmentProfile.from_name("cloud_full")
        assert flags.is_enabled(Feature.OPUS_46) is True

        with pytest.raises(ValueError):
            EnvironmentProfile.from_name("invalid_profile")


class TestProviderCapabilities:
    """Test provider capability registry."""

    def test_get_provider_capabilities(self):
        """Test getting provider capabilities."""
        caps = get_provider_capabilities("anthropic")
        assert caps is not None
        assert caps.provider_name == "anthropic"
        assert "claude-opus-4-6" in caps.available_models

    def test_provider_supports(self):
        """Test checking provider support."""
        assert provider_supports("anthropic", ModelCapability.EXTENDED_THINKING) is True
        assert provider_supports("ollama", ModelCapability.EXTENDED_THINKING) is False

    def test_bedrock_capabilities(self):
        """Test Bedrock has correct capabilities."""
        caps = get_provider_capabilities("bedrock")
        assert caps is not None
        assert ModelCapability.VISION in caps.capabilities
        assert ModelCapability.EXTENDED_THINKING not in caps.capabilities

    def test_ollama_capabilities(self):
        """Test Ollama has limited capabilities."""
        caps = get_provider_capabilities("ollama")
        assert caps is not None
        assert ModelCapability.STREAMING in caps.capabilities
        assert ModelCapability.COMPUTER_USE not in caps.capabilities

    def test_claude_code_provider(self):
        """Test claude-code provider has full capabilities."""
        caps = get_provider_capabilities("claude-code")
        assert caps is not None
        assert caps.max_tokens == 1_000_000
        assert ModelCapability.EXTENDED_THINKING in caps.capabilities

    def test_opus_context_window(self):
        """Test Opus 4.6 has 1M context window."""
        assert get_model_context_window("opus") == 1_000_000
        assert get_model_context_window("claude-opus-4-6") == 1_000_000

    def test_sonnet_context_window(self):
        """Test Sonnet has 200K context window."""
        assert get_model_context_window("sonnet") == 200_000
        assert get_model_context_window("claude-sonnet-4-5") == 200_000

    def test_model_max_output(self):
        """Test per-model max output tokens."""
        assert get_model_max_output("opus") == 32_000
        assert get_model_max_output("sonnet") == 16_000
        assert get_model_max_output("haiku") == 8_192

    def test_unknown_model_defaults(self):
        """Test unknown models get safe defaults."""
        assert get_model_context_window("unknown-model") == 200_000
        assert get_model_max_output("unknown-model") == 4_096


class TestFeatureFlagIntegration:
    """Test feature flag integration."""

    def test_singleton_behavior(self):
        """Test feature flags singleton."""
        flags1 = get_feature_flags()
        flags2 = get_feature_flags()
        assert flags1 is flags2

    def test_set_feature_flags(self):
        """Test setting custom feature flags."""
        custom_flags = FeatureFlags()
        custom_flags.features[Feature.OPUS_46].enabled = False

        set_feature_flags(custom_flags)
        flags = get_feature_flags()

        assert flags.is_enabled(Feature.OPUS_46) is False

        # Reset to default
        set_feature_flags(FeatureFlags())
