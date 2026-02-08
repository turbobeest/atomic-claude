# Feature Flag Architecture for Anthropic Releases

**Date**: 2026-02-07
**Purpose**: Design system to leverage new Anthropic features while supporting air-gapped environments

---

## Recent Anthropic Releases to Support

### 1. Claude Opus 4.6 (Latest Frontier Model)
- Most capable model to date
- Enhanced reasoning and coding
- Better context understanding

### 2. Extended Thinking
- Claude can "think" for longer periods before responding
- Better for complex reasoning tasks
- Controlled via `thinking` parameter

### 3. Agent Swarms
- Multiple Claude instances collaborating
- Distributed problem-solving
- Requires orchestration layer

### 4. Model Context Protocol (MCP)
- Standardized tool/skill integration
- Dynamic capability discovery
- Server-based architecture

### 5. Computer Use
- Claude can control desktop environments
- Screen capture and interaction
- Requires special setup

### 6. Prompt Caching
- Reuse common context efficiently
- Reduce token costs
- Requires cache-aware prompting

### 7. Analysis Tool
- Built-in data analysis capabilities
- Python code execution sandbox
- Chart/graph generation

---

## Design Goals

1. **Feature Toggles**: Every new feature can be enabled/disabled via config
2. **Environment Profiles**: Presets for cloud, air-gapped, enterprise, etc.
3. **Graceful Degradation**: Fallback when features unavailable
4. **Provider Capability Discovery**: Runtime detection of what's available
5. **Zero-Config Defaults**: Works out-of-box with basic features
6. **Rapid Adaptation**: Add new features without refactoring core code

---

## Architecture

### 1. Feature Flag System

**File**: `core/features/flags.py`

```python
from enum import Enum
from typing import Dict, Optional
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
    dependencies: list[Feature] = []         # Features this depends on
    incompatible_with: list[Feature] = []    # Mutually exclusive features


class FeatureFlags(BaseModel):
    """Global feature flag configuration."""

    features: Dict[Feature, FeatureConfig] = {
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
        config = self.features[feature]
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
        if not self.is_enabled(feature):
            return False, "Feature disabled in config"

        config = self.features[feature]

        # Check provider requirement
        if config.required_provider and provider != config.required_provider:
            return False, f"Feature requires {config.required_provider} provider"

        # Check model requirement
        if config.required_model and model != config.required_model:
            return False, f"Feature requires {config.required_model} model"

        return True, None

    def get_fallback_behavior(self, feature: Feature) -> str:
        """Get fallback behavior when feature unavailable."""
        return self.features[feature].fallback_behavior


# Singleton instance
_feature_flags: Optional[FeatureFlags] = None


def get_feature_flags() -> FeatureFlags:
    """Get global feature flags instance."""
    global _feature_flags
    if _feature_flags is None:
        _feature_flags = load_feature_flags()
    return _feature_flags


def load_feature_flags() -> FeatureFlags:
    """Load feature flags from config file or environment."""
    from core.config import Config
    config = Config()

    # Load from config file if exists
    flags_dict = config.get("features", {})

    # Override with environment variables
    import os
    for feature in Feature:
        env_var = f"ATOMIC_FEATURE_{feature.value.upper()}"
        if env_var in os.environ:
            enabled = os.environ[env_var].lower() in ("true", "1", "yes")
            if feature.value not in flags_dict:
                flags_dict[feature.value] = {}
            flags_dict[feature.value]["enabled"] = enabled

    return FeatureFlags(features=flags_dict) if flags_dict else FeatureFlags()
```

---

### 2. Environment Profiles

**File**: `core/features/profiles.py`

```python
from typing import Dict
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
            raise ValueError(f"Unknown profile: {name}. Available: {list(profiles.keys())}")

        return profiles[name]()
```

---

### 3. Provider Capability Registry

**File**: `core/llm/capabilities.py`

```python
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
        available_models=["qwen2.5-coder:32b"],  # Example
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
```

---

### 4. Feature-Aware LLM Invocation

**File**: `core/llm/invoke.py`

```python
from typing import Optional, Dict, Any
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
        """
        params = kwargs.copy()

        # Extended thinking
        if use_extended_thinking:
            can_use, reason = self._can_use_extended_thinking()
            if can_use:
                params["thinking"] = {"type": "enabled", "budget_tokens": 10000}
            else:
                print(f"⚠️  Extended thinking disabled: {reason}")

        # Prompt caching
        if use_caching:
            can_use, reason = self._can_use_caching()
            if can_use:
                params["cache_control"] = {"type": "ephemeral"}
            else:
                print(f"⚠️  Prompt caching disabled: {reason}")

        # Analysis tool
        if use_analysis:
            can_use, reason = self._can_use_analysis()
            if can_use:
                params["tools"] = params.get("tools", []) + [self._get_analysis_tool()]
            else:
                print(f"⚠️  Analysis tool disabled: {reason}")

        # Invoke with processed parameters
        return self.provider.invoke(prompt, **params)

    def _can_use_extended_thinking(self) -> tuple[bool, Optional[str]]:
        """Check if extended thinking can be used."""
        # Check feature flag
        can_use, reason = self.flags.can_use_feature(
            Feature.EXTENDED_THINKING,
            self.provider.provider_name,
            self.provider.model
        )
        if not can_use:
            return False, reason

        # Check provider capability
        if not provider_supports(self.provider.provider_name, ModelCapability.EXTENDED_THINKING):
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

        if not provider_supports(self.provider.provider_name, ModelCapability.PROMPT_CACHING):
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

        if not provider_supports(self.provider.provider_name, ModelCapability.ANALYSIS):
            return False, "Provider doesn't support analysis tool"

        return True, None

    def _get_analysis_tool(self) -> Dict[str, Any]:
        """Get analysis tool definition."""
        return {
            "type": "computer_20241022",
            "name": "code_analysis",
            "display_width_px": 1024,
            "display_height_px": 768,
            "display_number": 1,
        }
```

---

### 5. Agent Swarm Support (Optional Feature)

**File**: `core/swarm/orchestrator.py` (Only loaded if feature enabled)

```python
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.features.flags import Feature, get_feature_flags


class AgentSwarmOrchestrator:
    """
    Orchestrate multiple Claude instances working together.

    Only available if AGENT_SWARMS feature is enabled.
    """

    def __init__(self, max_agents: int = 5):
        flags = get_feature_flags()
        if not flags.is_enabled(Feature.AGENT_SWARMS):
            raise RuntimeError("Agent swarms feature is disabled")

        self.max_agents = max_agents

    def distribute_work(
        self,
        tasks: List[str],
        provider: str = "anthropic",
        model: str = "claude-sonnet-4.5"
    ) -> List[str]:
        """
        Distribute tasks across multiple Claude instances.

        Returns:
            List of results in same order as tasks
        """
        results = [None] * len(tasks)

        with ThreadPoolExecutor(max_workers=self.max_agents) as executor:
            # Submit all tasks
            future_to_index = {
                executor.submit(self._execute_task, task, provider, model): i
                for i, task in enumerate(tasks)
            }

            # Collect results as they complete
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    results[index] = future.result()
                except Exception as e:
                    results[index] = f"Error: {e}"

        return results

    def _execute_task(self, task: str, provider: str, model: str) -> str:
        """Execute a single task with Claude."""
        from core.llm.router import get_provider
        llm = get_provider(provider, model)
        return llm.invoke(task)
```

---

### 6. Configuration File Format

**File**: `config/features.json` (or .yaml)

```json
{
  "environment": "cloud_full",
  "custom_overrides": {
    "features": {
      "opus_46": {
        "enabled": true,
        "fallback_behavior": "downgrade"
      },
      "extended_thinking": {
        "enabled": true
      },
      "agent_swarms": {
        "enabled": false,
        "reason": "Resource constraints"
      },
      "computer_use": {
        "enabled": false,
        "reason": "Security policy"
      }
    }
  },
  "provider_preferences": {
    "primary": "anthropic",
    "fallback": "bedrock",
    "local": "ollama"
  },
  "model_preferences": {
    "heavy": "claude-opus-4.6",
    "standard": "claude-sonnet-4.5",
    "fast": "claude-haiku-3.5"
  }
}
```

---

## Usage Examples

### Example 1: Air-Gapped Environment

```python
from core.features.profiles import EnvironmentProfile
from core.features.flags import set_feature_flags

# Load air-gapped profile
flags = EnvironmentProfile.air_gapped()
set_feature_flags(flags)

# Now all code respects these constraints
from core.llm.router import get_provider

# This will use local Ollama, no internet calls
llm = get_provider("ollama", "qwen2.5-coder:32b")
result = llm.invoke("Write a function...")
```

### Example 2: Selective Feature Use

```python
from core.llm.invoke import FeatureAwareLLMInvoker
from core.llm.router import get_provider

provider = get_provider("anthropic", "claude-opus-4.6")
invoker = FeatureAwareLLMInvoker(provider)

# Request extended thinking (will auto-disable if unavailable)
result = invoker.invoke(
    "Solve this complex problem...",
    use_extended_thinking=True,
    use_caching=True
)
```

### Example 3: Agent Swarms (If Enabled)

```python
from core.swarm.orchestrator import AgentSwarmOrchestrator

try:
    swarm = AgentSwarmOrchestrator(max_agents=5)

    tasks = [
        "Analyze file1.py",
        "Analyze file2.py",
        "Analyze file3.py",
        "Analyze file4.py",
        "Analyze file5.py",
    ]

    results = swarm.distribute_work(tasks)
    print(results)

except RuntimeError as e:
    print(f"Swarms disabled: {e}")
    # Fall back to sequential processing
```

---

## Integration with Existing Code

### Update LLM Router

```python
# core/llm/router.py

from .invoke import FeatureAwareLLMInvoker

def invoke_llm(prompt: str, **kwargs) -> str:
    """
    High-level LLM invocation with automatic feature handling.
    """
    provider = get_provider(kwargs.get("provider"), kwargs.get("model"))
    invoker = FeatureAwareLLMInvoker(provider)
    return invoker.invoke(prompt, **kwargs)
```

### Update Task Execution

```python
# phases/phase_XX/tasks/task_XXX.py

from core.llm.router import invoke_llm
from core.features.flags import Feature, get_feature_flags

def execute_task():
    """Execute task with feature-aware LLM calls."""

    # Check if we can use advanced features
    flags = get_feature_flags()
    use_thinking = flags.is_enabled(Feature.EXTENDED_THINKING)

    result = invoke_llm(
        "Complex analysis task...",
        use_extended_thinking=use_thinking,
        use_caching=True,  # Will auto-disable if unavailable
        use_analysis=True
    )

    return result
```

---

## Rapid Adaptation Process

When Anthropic releases new features:

1. **Add to Feature Enum** (`core/features/flags.py`)
   ```python
   class Feature(str, Enum):
       NEW_FEATURE = "new_feature"
   ```

2. **Add to Capability Enum** (if provider-specific)
   ```python
   class ModelCapability(str, Enum):
       NEW_CAPABILITY = "new_capability"
   ```

3. **Update Provider Capabilities**
   ```python
   PROVIDER_CAPABILITIES["anthropic"].capabilities.add(
       ModelCapability.NEW_CAPABILITY
   )
   ```

4. **Add Feature Config**
   ```python
   Feature.NEW_FEATURE: FeatureConfig(
       enabled=True,
       required_provider="anthropic",
       fallback_behavior="disable"
   )
   ```

5. **Implement Feature Handler** (if needed)
   ```python
   # core/llm/invoke.py
   def _can_use_new_feature(self) -> tuple[bool, Optional[str]]:
       # Check logic here
   ```

6. **Update Profiles** (optional)
   ```python
   # Add to appropriate environment profiles
   ```

7. **Done** - Feature is now available with toggle

**Time to integrate new feature: ~30 minutes**

---

## Benefits

1. **Air-Gap Ready**: Complete feature isolation for secure environments
2. **Graceful Degradation**: Automatic fallback when features unavailable
3. **Zero Breaking Changes**: Old code continues working
4. **Rapid Adaptation**: New features integrated in minutes, not hours
5. **Testing Friendly**: Disable features for unit testing
6. **Cost Control**: Disable expensive features (extended thinking, Opus 4.6)
7. **Security**: Computer use and other risky features off by default
8. **Flexibility**: Environment-specific profiles for different deployments

---

## Next Steps

1. Implement feature flag system in Phase 2 (Core Systems)
2. Update LLM abstraction to be feature-aware
3. Create environment profiles
4. Add feature tests to test suite
5. Document feature usage in user guide

