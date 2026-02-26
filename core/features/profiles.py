"""
Environment profiles for different deployment scenarios.

Provides predefined feature configurations for:
- Cloud (full-featured)
- Air-gapped (no internet)
- Enterprise (security-restricted)
- Development (all features for testing)
"""

from .flags import Feature, FeatureConfig, FeatureFlags


class EnvironmentProfile:
    """Predefined environment profiles."""

    @staticmethod
    def cloud_full() -> FeatureFlags:
        """Full-featured cloud deployment with all Anthropic features."""
        return FeatureFlags(features={
            Feature.OPUS_46: FeatureConfig(enabled=True),
            Feature.EXTENDED_THINKING: FeatureConfig(enabled=True),
            Feature.PROMPT_CACHING: FeatureConfig(enabled=True),
            Feature.MCP_TOOLS: FeatureConfig(enabled=True),
            Feature.COMPUTER_USE: FeatureConfig(enabled=False),  # Still dangerous
            Feature.ANALYSIS_TOOL: FeatureConfig(enabled=True),
            Feature.AGENT_SWARMS: FeatureConfig(enabled=True),
            Feature.PARALLEL_EXECUTION: FeatureConfig(enabled=True),
            Feature.INTERNET_ACCESS: FeatureConfig(enabled=True),
            Feature.API_CALLS: FeatureConfig(enabled=True),
            Feature.FILE_SYSTEM: FeatureConfig(enabled=True),
        })

    @staticmethod
    def air_gapped() -> FeatureFlags:
        """Air-gapped environment with local LLM only."""
        return FeatureFlags(features={
            Feature.OPUS_46: FeatureConfig(enabled=False),  # Not available locally
            Feature.EXTENDED_THINKING: FeatureConfig(enabled=False),
            Feature.PROMPT_CACHING: FeatureConfig(enabled=True),  # Can work locally
            Feature.MCP_TOOLS: FeatureConfig(enabled=False),  # Requires network
            Feature.COMPUTER_USE: FeatureConfig(enabled=False),
            Feature.ANALYSIS_TOOL: FeatureConfig(enabled=True),  # Local Python exec
            Feature.AGENT_SWARMS: FeatureConfig(enabled=False),
            Feature.PARALLEL_EXECUTION: FeatureConfig(enabled=True),  # Local threads
            Feature.INTERNET_ACCESS: FeatureConfig(enabled=False),
            Feature.API_CALLS: FeatureConfig(enabled=False),
            Feature.FILE_SYSTEM: FeatureConfig(enabled=True),
        })

    @staticmethod
    def enterprise_secure() -> FeatureFlags:
        """Enterprise deployment with security restrictions."""
        return FeatureFlags(features={
            Feature.OPUS_46: FeatureConfig(enabled=True),
            Feature.EXTENDED_THINKING: FeatureConfig(enabled=True),
            Feature.PROMPT_CACHING: FeatureConfig(enabled=True),
            Feature.MCP_TOOLS: FeatureConfig(enabled=False),  # Too permissive
            Feature.COMPUTER_USE: FeatureConfig(enabled=False),  # Security risk
            Feature.ANALYSIS_TOOL: FeatureConfig(enabled=True),
            Feature.AGENT_SWARMS: FeatureConfig(enabled=False),  # Resource control
            Feature.PARALLEL_EXECUTION: FeatureConfig(enabled=True),
            Feature.INTERNET_ACCESS: FeatureConfig(enabled=True),
            Feature.API_CALLS: FeatureConfig(enabled=True),
            Feature.FILE_SYSTEM: FeatureConfig(enabled=True),
        })

    @staticmethod
    def development() -> FeatureFlags:
        """Development environment with all features for testing."""
        return FeatureFlags(features={
            feature: FeatureConfig(enabled=True)
            for feature in Feature
        })

    @staticmethod
    def from_name(name: str) -> FeatureFlags:
        """Load profile by name."""
        profiles = {
            "cloud_full": EnvironmentProfile.cloud_full,
            "air_gapped": EnvironmentProfile.air_gapped,
            "enterprise_secure": EnvironmentProfile.enterprise_secure,
            "development": EnvironmentProfile.development,
        }

        if name not in profiles:
            raise ValueError(
                f"Unknown profile: {name}. "
                f"Available: {list(profiles.keys())}"
            )

        return profiles[name]()

    @staticmethod
    def skill_constraints(profile_name: str) -> dict:
        """Return skill gating rules for a profile.

        Each profile defines what skill attributes are acceptable:
        - allow_internet: whether skills requiring network access are permitted
        - allow_saas: whether skills requiring SaaS integrations are permitted
        - max_risk: maximum acceptable risk level (None < Low < Medium < High)
        """
        constraints = {
            "air_gapped": {
                "allow_internet": False,
                "allow_saas": False,
                "max_risk": "Low",
            },
            "enterprise_secure": {
                "allow_internet": True,
                "allow_saas": False,
                "max_risk": "Low",
            },
            "cloud_full": {
                "allow_internet": True,
                "allow_saas": True,
                "max_risk": "Medium",
            },
            "development": {
                "allow_internet": True,
                "allow_saas": True,
                "max_risk": "High",
            },
        }
        if profile_name not in constraints:
            raise ValueError(
                f"Unknown profile: {profile_name}. "
                f"Available: {list(constraints.keys())}"
            )
        return constraints[profile_name]
