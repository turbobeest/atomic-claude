"""
Feature flag system for toggling Anthropic capabilities.

Supports:
- Feature toggles (enable/disable per feature)
- Environment profiles (cloud, air-gapped, enterprise, dev)
- Provider capability requirements
- Graceful degradation (disable, downgrade, error)
- Dependency management between features
"""

from enum import Enum
from typing import Dict, Optional, List
from pydantic import BaseModel


class Feature(str, Enum):
    """Available features that can be toggled."""

    # Model features
    OPUS_46 = "opus_46"
    EXTENDED_THINKING = "extended_thinking"
    PROMPT_CACHING = "prompt_caching"

    # Tool/capability features
    MCP_TOOLS = "mcp_tools"
    COMPUTER_USE = "computer_use"
    ANALYSIS_TOOL = "analysis_tool"

    # Orchestration features
    AGENT_SWARMS = "agent_swarms"
    PARALLEL_EXECUTION = "parallel_execution"

    # Infrastructure
    INTERNET_ACCESS = "internet_access"
    API_CALLS = "api_calls"
    FILE_SYSTEM = "file_system"


class FeatureConfig(BaseModel):
    """Configuration for a single feature."""
    enabled: bool = False
    required_provider: Optional[str] = None  # "anthropic", "bedrock", etc.
    required_model: Optional[str] = None     # "opus-4.6", etc.
    fallback_behavior: str = "disable"       # "disable", "downgrade", "error"
    dependencies: List[str] = []             # Features this depends on
    incompatible_with: List[str] = []        # Mutually exclusive features


class FeatureFlags(BaseModel):
    """Global feature flag configuration."""

    features: Dict[str, FeatureConfig] = {}

    def __init__(self, **data):
        if "features" not in data:
            data["features"] = self._default_features()
        super().__init__(**data)

    @staticmethod
    def _default_features() -> Dict[str, FeatureConfig]:
        """Get default feature configurations."""
        return {
            # Model features
            Feature.OPUS_46: FeatureConfig(
                enabled=True,
                required_provider="anthropic",
                required_model="claude-opus-4.6",
                fallback_behavior="downgrade"  # Fall back to Sonnet 4.5
            ),

            Feature.EXTENDED_THINKING: FeatureConfig(
                enabled=True,
                required_provider="anthropic",
                fallback_behavior="disable"
            ),

            Feature.PROMPT_CACHING: FeatureConfig(
                enabled=True,
                fallback_behavior="disable"  # Works without, just less efficient
            ),

            # Tool features
            Feature.MCP_TOOLS: FeatureConfig(
                enabled=True,
                dependencies=[Feature.INTERNET_ACCESS],
                fallback_behavior="disable"
            ),

            Feature.COMPUTER_USE: FeatureConfig(
                enabled=False,  # Disabled by default (security concern)
                required_provider="anthropic",
                dependencies=[Feature.INTERNET_ACCESS],
                fallback_behavior="error"  # Fail loudly if attempted
            ),

            Feature.ANALYSIS_TOOL: FeatureConfig(
                enabled=True,
                fallback_behavior="disable"
            ),

            # Orchestration
            Feature.AGENT_SWARMS: FeatureConfig(
                enabled=False,  # Disabled by default (resource intensive)
                dependencies=[Feature.PARALLEL_EXECUTION],
                fallback_behavior="disable"
            ),

            Feature.PARALLEL_EXECUTION: FeatureConfig(
                enabled=True,
                fallback_behavior="disable"  # Fall back to sequential
            ),

            # Infrastructure
            Feature.INTERNET_ACCESS: FeatureConfig(
                enabled=True,
                fallback_behavior="error"  # Fail if required but unavailable
            ),

            Feature.API_CALLS: FeatureConfig(
                enabled=True,
                dependencies=[Feature.INTERNET_ACCESS],
                fallback_behavior="error"
            ),

            Feature.FILE_SYSTEM: FeatureConfig(
                enabled=True,
                fallback_behavior="error"
            ),
        }

    def is_enabled(self, feature: Feature) -> bool:
        """Check if a feature is enabled and its dependencies are met."""
        feature_key = feature.value if isinstance(feature, Feature) else feature

        if feature_key not in self.features:
            return False

        config = self.features[feature_key]
        if not config.enabled:
            return False

        # Check dependencies
        for dep in config.dependencies:
            if not self.is_enabled(dep):
                return False

        return True

    def can_use_feature(
        self,
        feature: Feature,
        provider: str,
        model: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Check if feature can be used with given provider/model.

        Returns:
            (can_use, reason_if_not)
        """
        feature_key = feature.value if isinstance(feature, Feature) else feature

        if not self.is_enabled(feature):
            return False, "Feature disabled in config"

        if feature_key not in self.features:
            return False, "Feature not configured"

        config = self.features[feature_key]

        # Check provider requirement
        if config.required_provider and provider != config.required_provider:
            return False, f"Feature requires {config.required_provider} provider"

        # Check model requirement
        if config.required_model and model != config.required_model:
            return False, f"Feature requires {config.required_model} model"

        return True, None

    def get_fallback_behavior(self, feature: Feature) -> str:
        """Get fallback behavior when feature unavailable."""
        feature_key = feature.value if isinstance(feature, Feature) else feature

        if feature_key not in self.features:
            return "disable"

        return self.features[feature_key].fallback_behavior


# Singleton instance
_feature_flags: Optional[FeatureFlags] = None


def get_feature_flags() -> FeatureFlags:
    """Get global feature flags instance."""
    global _feature_flags
    if _feature_flags is None:
        _feature_flags = load_feature_flags()
    return _feature_flags


def set_feature_flags(flags: FeatureFlags) -> None:
    """Set global feature flags instance (for testing/profiles)."""
    global _feature_flags
    _feature_flags = flags


def load_feature_flags() -> FeatureFlags:
    """Load feature flags from config file or environment."""
    import os
    import json
    from pathlib import Path

    # Try to load from config file
    config_file = Path("config/features.json")
    flags_data = {}

    if config_file.exists():
        try:
            with open(config_file) as f:
                config = json.load(f)

            # Check if using a profile
            if "environment" in config:
                from .profiles import EnvironmentProfile
                flags = EnvironmentProfile.from_name(config["environment"])

                # Apply custom overrides if present
                if "custom_overrides" in config and "features" in config["custom_overrides"]:
                    for feature_name, feature_config in config["custom_overrides"]["features"].items():
                        if feature_name in flags.features:
                            # Merge override into existing config
                            for key, value in feature_config.items():
                                setattr(flags.features[feature_name], key, value)

                return flags

            flags_data = config.get("features", {})
        except Exception:
            pass  # Fall back to defaults

    # Override with environment variables
    features_dict = FeatureFlags._default_features()

    for feature in Feature:
        env_var = f"ATOMIC_FEATURE_{feature.value.upper()}"
        if env_var in os.environ:
            enabled = os.environ[env_var].lower() in ("true", "1", "yes")
            feature_key = feature.value

            if feature_key in features_dict:
                features_dict[feature_key].enabled = enabled
            else:
                features_dict[feature_key] = FeatureConfig(enabled=enabled)

    # Apply config file overrides
    for feature_name, feature_config in flags_data.items():
        if feature_name in features_dict:
            for key, value in feature_config.items():
                setattr(features_dict[feature_name], key, value)

    return FeatureFlags(features=features_dict)
