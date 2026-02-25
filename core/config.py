"""
Configuration Management System

Comprehensive configuration manager with multi-source loading, validation,
hot-reload, and type-safe access.

Features:
- Multi-source loading (env vars, .env, JSON, CLI args)
- Pydantic validation with schema versioning
- Override hierarchy: CLI > env > file > defaults
- Dot notation access (config.get("project.name"))
- Hot-reload capability
- Type-safe access with proper defaults
- Provider/model role-based selection

Architecture:
- ConfigSchema: Pydantic models for validation
- ConfigLoader: Multi-source loading with priority
- Config: Main configuration manager

Author: Phase 2 - Configuration System
"""

import logging
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)

try:
    from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
    HAS_PYDANTIC = True
except ImportError:
    # Fallback if pydantic not installed
    HAS_PYDANTIC = False
    BaseModel = object


# ============================================================================
# ENUMS
# ============================================================================

class NetworkMode(str, Enum):
    """Network access modes."""
    CUI = "cui"  # Completely Unclassified Information
    INTERNET = "internet"  # Full internet access
    RESTRICTED = "restricted"  # Limited network access


class Provider(str, Enum):
    """LLM providers."""
    MAX = "max"  # Claude Desktop
    API = "api"  # Anthropic API
    BEDROCK = "bedrock"  # AWS Bedrock
    OLLAMA = "ollama"  # Ollama local
    CLAUDE_CODE = "claude-code"  # Claude Code CLI


class ModelRole(str, Enum):
    """Model roles for task routing."""
    PRIMARY = "primary"  # Main workhorse
    FAST = "fast"  # Quick validation
    HEAVYWEIGHT = "heavyweight"  # Complex reasoning
    GARDENER = "gardener"  # Context maintenance


# ============================================================================
# PYDANTIC SCHEMAS (if available)
# ============================================================================

if HAS_PYDANTIC:
    class ProjectConfig(BaseModel):
        """Project configuration schema."""
        name: str = Field(default="unknown", description="Project name")
        type: str = Field(default="unknown", description="Project type")
        description: Optional[str] = Field(default=None, description="Project description")
        target_directory: Optional[str] = Field(default=None, description="Target build directory")
        version: str = Field(default="0.1.0", description="Project version")

        @field_validator('name')
        @classmethod
        def validate_name(cls, v):
            if not v or v == "unknown":
                return v
            if not v.replace('-', '').replace('_', '').isalnum():
                raise ValueError("Project name must be alphanumeric with dashes/underscores")
            return v

    class LLMConfig(BaseModel):
        """LLM configuration schema."""
        primary_provider: Provider = Field(default=Provider.MAX, description="Primary LLM provider")
        fast_provider: Optional[Provider] = Field(default=None, description="Fast operations provider")
        gardener_provider: Optional[Provider] = Field(default=None, description="Context maintenance provider")
        heavyweight_provider: Optional[Provider] = Field(default=None, description="Complex reasoning provider")

        primary_model: str = Field(default="sonnet", description="Primary model")
        fast_model: str = Field(default="haiku", description="Fast model")
        heavyweight_model: str = Field(default="opus", description="Heavyweight model")
        gardener_model: str = Field(default="haiku", description="Gardener model")

        max_turns: int = Field(default=30, ge=1, le=100, description="Max conversation turns")
        timeout: int = Field(default=1200, ge=10, le=3600, description="Request timeout in seconds")

    class MemoryConfig(BaseModel):
        """Memory system configuration."""
        enabled: bool = Field(default=True, description="Enable memory system")
        checkpoint_frequency: int = Field(default=5, ge=1, description="Checkpoint every N tasks")
        max_size_mb: int = Field(default=100, ge=1, le=1000, description="Max memory size in MB")
        compression_enabled: bool = Field(default=True, description="Enable memory compression")

    class DashboardConfig(BaseModel):
        """Dashboard configuration."""
        enabled: bool = Field(default=True, description="Enable dashboard")
        host: str = Field(default="localhost", description="Dashboard host")
        tasks_port: int = Field(default=5173, ge=1024, le=65535, description="Tasks dashboard port")
        agents_port: int = Field(default=5174, ge=1024, le=65535, description="Agents dashboard port")
        audits_port: int = Field(default=5175, ge=1024, le=65535, description="Audits dashboard port")

    class SecretsConfig(BaseModel):
        """Secrets configuration."""
        bedrock_enabled: bool = Field(default=False, description="AWS Bedrock enabled")
        ollama_enabled: bool = Field(default=False, description="Ollama enabled")
        aws_region: Optional[str] = Field(default=None, description="AWS region")
        aws_profile: Optional[str] = Field(default=None, description="AWS profile")
        bedrock_model: Optional[str] = Field(default=None, description="Bedrock model ID")
        ollama_host: str = Field(default="http://localhost:11434", description="Ollama host")
        ollama_context: int = Field(default=65536, ge=2048, description="Ollama context length")

    class ConfigSchema(BaseModel):
        """Complete configuration schema with validation."""
        version: str = Field(default="1.0", description="Config schema version")
        project: ProjectConfig = Field(default_factory=ProjectConfig)
        llm: LLMConfig = Field(default_factory=LLMConfig)
        memory: MemoryConfig = Field(default_factory=MemoryConfig)
        dashboard: DashboardConfig = Field(default_factory=DashboardConfig)
        secrets: SecretsConfig = Field(default_factory=SecretsConfig)
        sandbox: Dict[str, Any] = Field(default_factory=dict, description="Sandbox configuration")
        pipeline: Dict[str, Any] = Field(default_factory=dict, description="Pipeline configuration")

        current_phase: Optional[str] = Field(default=None, description="Current phase ID")
        resume_task: Optional[str] = Field(default=None, description="Task to resume from")

        @model_validator(mode='after')
        def validate_ports_unique(self):
            """Ensure dashboard ports are unique."""
            ports = [
                self.dashboard.tasks_port,
                self.dashboard.agents_port,
                self.dashboard.audits_port
            ]
            if len(ports) != len(set(ports)):
                raise ValueError("Dashboard ports must be unique")
            return self

        model_config = ConfigDict(extra="allow")  # Allow additional fields for extensibility


# ============================================================================
# CONFIGURATION LOADER
# ============================================================================

class ConfigLoader:
    """
    Multi-source configuration loader with priority handling.

    Priority order:
    1. CLI arguments (highest)
    2. Environment variables
    3. .env file
    4. JSON config files (Phase 00 outputs)
    5. Defaults (lowest)
    """

    def __init__(self, atomic_root: Path):
        self.atomic_root = atomic_root
        self.env_cache: Dict[str, str] = {}

    def load_from_env(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = {}

        # Cache all ATOMIC_* and CLAUDE_* env vars
        for key, value in os.environ.items():
            if key.startswith(('ATOMIC_', 'CLAUDE_', 'AWS_')):
                self.env_cache[key] = value

        # Map to config structure
        # Project
        if 'ATOMIC_PROJECT_NAME' in self.env_cache:
            config['project'] = config.get('project', {})
            config['project']['name'] = self.env_cache['ATOMIC_PROJECT_NAME']

        # LLM
        if 'CLAUDE_MODEL' in self.env_cache:
            config['llm'] = config.get('llm', {})
            config['llm']['primary_model'] = self.env_cache['CLAUDE_MODEL']

        if 'CLAUDE_PROVIDER' in self.env_cache:
            config['llm'] = config.get('llm', {})
            config['llm']['primary_provider'] = self.env_cache['CLAUDE_PROVIDER']

        if 'CLAUDE_MAX_TURNS' in self.env_cache:
            config['llm'] = config.get('llm', {})
            try:
                config['llm']['max_turns'] = int(self.env_cache['CLAUDE_MAX_TURNS'])
            except ValueError:
                logger.warning("Invalid CLAUDE_MAX_TURNS value: %s (expected integer)", self.env_cache['CLAUDE_MAX_TURNS'])

        if 'CLAUDE_TIMEOUT' in self.env_cache:
            config['llm'] = config.get('llm', {})
            try:
                config['llm']['timeout'] = int(self.env_cache['CLAUDE_TIMEOUT'])
            except ValueError:
                logger.warning("Invalid CLAUDE_TIMEOUT value: %s (expected integer)", self.env_cache['CLAUDE_TIMEOUT'])

        # Secrets
        if 'AWS_REGION' in self.env_cache:
            config['secrets'] = config.get('secrets', {})
            config['secrets']['aws_region'] = self.env_cache['AWS_REGION']

        if 'AWS_PROFILE' in self.env_cache:
            config['secrets'] = config.get('secrets', {})
            config['secrets']['aws_profile'] = self.env_cache['AWS_PROFILE']

        return config

    def load_from_dotenv(self) -> Dict[str, Any]:
        """Load configuration from .env file."""
        env_file = self.atomic_root / ".env"
        if not env_file.exists():
            return {}

        config = {}
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue

                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")

                # Store in env cache
                self.env_cache[key] = value

        # Process like environment variables
        return self.load_from_env()

    def load_from_json_files(self) -> Dict[str, Any]:
        """Load configuration from Phase 00 JSON outputs."""
        config = {}

        # Load project config (Phase 00 Task 002/003)
        project_config_file = self.atomic_root.parent / ".outputs" / "0-setup" / "project-config.json"
        if project_config_file.exists():
            try:
                with open(project_config_file, 'r') as f:
                    data = json.load(f)
                    extracted = data.get('extracted', {})

                    if 'project' in extracted:
                        config['project'] = extracted['project']
                    if 'llm' in extracted:
                        config['llm'] = extracted['llm']
                    if 'sandbox' in extracted:
                        config['sandbox'] = extracted['sandbox']
                    if 'pipeline' in extracted:
                        config['pipeline'] = extracted['pipeline']
            except (json.JSONDecodeError, IOError):
                # Invalid JSON, skip this file
                pass

        # Load secrets (Phase 00 Task 004)
        secrets_file = self.atomic_root.parent / ".outputs" / "0-setup" / "secrets.json"
        if secrets_file.exists():
            try:
                with open(secrets_file, 'r') as f:
                    config['secrets'] = json.load(f)
            except (json.JSONDecodeError, IOError):
                # Invalid JSON, skip this file
                pass

        return config

    def load_defaults(self) -> Dict[str, Any]:
        """Load default configuration values."""
        return {
            'version': '1.0',
            'project': {
                'name': 'unknown',
                'type': 'unknown',
                'version': '0.1.0'
            },
            'llm': {
                'primary_provider': 'max',
                'primary_model': 'sonnet',
                'fast_model': 'haiku',
                'heavyweight_model': 'opus',
                'gardener_model': 'haiku',
                'max_turns': 30,
                'timeout': 1200
            },
            'memory': {
                'enabled': True,
                'checkpoint_frequency': 5,
                'max_size_mb': 100,
                'compression_enabled': True
            },
            'dashboard': {
                'enabled': True,
                'host': 'localhost',
                'tasks_port': 5173,
                'agents_port': 5174,
                'audits_port': 5175
            },
            'secrets': {
                'bedrock_enabled': False,
                'ollama_enabled': False,
                'ollama_host': 'http://localhost:11434',
                'ollama_context': 65536
            },
            'sandbox': {},
            'pipeline': {}
        }

    def merge_configs(self, *configs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge multiple config dicts with priority.
        Later configs override earlier ones.
        """
        result = {}
        for config in configs:
            self._deep_merge(result, config)
        return result

    def _deep_merge(self, target: Dict, source: Dict) -> None:
        """Deep merge source into target."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value


# ============================================================================
# MAIN CONFIG CLASS
# ============================================================================

class Config:
    """
    Main configuration manager with multi-source loading and validation.

    Features:
    - Load from env vars, .env, JSON files, CLI args
    - Pydantic validation (if available)
    - Override hierarchy: CLI > env > file > defaults
    - Dot notation access
    - Hot-reload capability
    - Type-safe access

    Usage:
        config = Config()
        project_name = config.get("project.name")
        provider = config.get_provider()
        model = config.get_model("primary")
    """

    def __init__(self, atomic_root: Path = None, cli_args: Dict[str, Any] = None):
        """
        Initialize configuration manager.

        Args:
            atomic_root: Root directory (defaults to cwd)
            cli_args: CLI arguments for override
        """
        self.atomic_root = atomic_root or Path.cwd()
        self.cli_args = cli_args or {}
        self.loader = ConfigLoader(self.atomic_root)
        self._config: Dict[str, Any] = {}
        self._schema: Optional[Any] = None  # ConfigSchema instance if Pydantic available
        self._load_timestamp: Optional[datetime] = None

        # Load configuration
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from all sources with priority."""
        # Load in priority order (lowest to highest)
        defaults = self.loader.load_defaults()
        json_config = self.loader.load_from_json_files()
        dotenv_config = self.loader.load_from_dotenv()
        env_config = self.loader.load_from_env()

        # Merge with priority
        self._config = self.loader.merge_configs(
            defaults,
            json_config,
            dotenv_config,
            env_config,
            self.cli_args  # Highest priority
        )

        # Validate with Pydantic if available
        if HAS_PYDANTIC:
            try:
                self._schema = ConfigSchema(**self._config)
                # Update config with validated values
                self._config = self._schema.model_dump()
            except Exception as e:
                # Validation failed, continue with unvalidated config
                print(f"Warning: Config validation failed: {e}")
                self._schema = None

        self._load_timestamp = datetime.now(timezone.utc)

    def reload(self) -> None:
        """Hot-reload configuration from all sources."""
        self._load_config()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key: Dot-separated key path (e.g., "project.name")
            default: Default value if key not found

        Returns:
            Configuration value or default

        Examples:
            config.get("project.name")
            config.get("llm.primary_model")
            config.get("sandbox.network_mode", "cui")
        """
        # Navigate nested config (already includes env vars via loading)
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value at runtime.

        Args:
            key: Dot-separated key path
            value: Value to set
        """
        keys = key.split('.')
        target = self._config
        for k in keys[:-1]:
            if k not in target or not isinstance(target[k], dict):
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value

    def validate(self) -> bool:
        """
        Validate current configuration.

        Returns:
            True if valid, False otherwise
        """
        if not HAS_PYDANTIC:
            return True  # Can't validate without Pydantic

        try:
            ConfigSchema(**self._config)
            return True
        except Exception as e:
            logger.debug("Config validation failed: %s", e)
            return False

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration to dictionary."""
        return dict(self._config)

    def save(self, path: Path) -> None:
        """
        Persist configuration to JSON file.

        Args:
            path: File path to save to
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self._config, f, indent=2)

    # ========================================================================
    # CONVENIENCE ACCESSORS
    # ========================================================================

    def get_project_name(self) -> str:
        """Get project name."""
        return self.get("project.name", "unknown")

    def get_project_type(self) -> str:
        """Get project type."""
        return self.get("project.type", "unknown")

    def get_network_mode(self) -> str:
        """Get network mode (cui, internet, restricted)."""
        return self.get("sandbox.network_mode", "cui")

    def get_provider(self, role: str = "primary") -> str:
        """
        Get LLM provider for specific role.

        Args:
            role: Model role (primary, fast, heavyweight, gardener)

        Returns:
            Provider name (max, api, bedrock, ollama)
        """
        # Check role-specific provider
        provider_key = f"llm.{role}_provider"
        provider = self.get(provider_key)

        if provider:
            return provider

        # Fallback to primary provider
        primary = self.get("llm.primary_provider")
        if primary:
            return primary

        # Check if Bedrock configured
        if self.get("secrets.bedrock_enabled"):
            return "bedrock"

        # Default
        return "max"

    def get_model(self, role: str = "primary") -> str:
        """
        Get model for specific role.

        Args:
            role: Model role (primary, fast, heavyweight, gardener)

        Returns:
            Model name (sonnet, haiku, opus, etc.)
        """
        # Check environment first
        if role == "primary":
            env_model = os.environ.get("CLAUDE_MODEL")
            if env_model:
                return env_model

        # Check config
        model_key = f"llm.{role}_model"
        model = self.get(model_key)
        if model:
            return model

        # Defaults by role
        defaults = {
            "primary": "sonnet",
            "fast": "haiku",
            "heavyweight": "opus",
            "gardener": "haiku"
        }
        return defaults.get(role, "sonnet")

    def has_bedrock(self) -> bool:
        """Check if AWS Bedrock is configured."""
        return self.get("secrets.bedrock_enabled", False)

    def has_ollama(self) -> bool:
        """Check if Ollama is configured."""
        return self.get("secrets.ollama_enabled", False)

    def get_aws_region(self) -> Optional[str]:
        """Get AWS region for Bedrock."""
        # Config takes precedence, then environment as fallback
        region = self.get("secrets.aws_region")
        if region:
            return region
        return os.environ.get("AWS_REGION") or None

    def get_aws_profile(self) -> Optional[str]:
        """Get AWS profile for Bedrock."""
        # Config takes precedence, then environment as fallback
        profile = self.get("secrets.aws_profile")
        if profile:
            return profile
        return os.environ.get("AWS_PROFILE") or None

    def get_bedrock_model(self) -> Optional[str]:
        """Get Bedrock model ID."""
        return self.get("secrets.bedrock_model") or os.environ.get("ANTHROPIC_MODEL")

    def get_ollama_host(self) -> str:
        """Get Ollama host URL."""
        return self.get("secrets.ollama_host", "http://localhost:11434")

    def get_ollama_context(self) -> int:
        """Get Ollama context length."""
        return self.get("secrets.ollama_context", 65536)


# ============================================================================
# GLOBAL SINGLETON
# ============================================================================

_config_instance: Optional[Config] = None


def get_config(atomic_root: Path = None, cli_args: Dict[str, Any] = None) -> Config:
    """
    Get global config instance (singleton pattern).

    Args:
        atomic_root: Root directory (only used on first call)
        cli_args: CLI arguments (only used on first call)

    Returns:
        Global Config instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(atomic_root, cli_args)
    elif atomic_root is not None and atomic_root != _config_instance.atomic_root:
        _config_instance = Config(atomic_root, cli_args)
    return _config_instance


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("Testing config module...\n")

    config = Config()

    print("Project Configuration:")
    print(f"  Name: {config.get_project_name()}")
    print(f"  Type: {config.get_project_type()}")
    print(f"  Network mode: {config.get_network_mode()}")
    print()

    print("LLM Configuration:")
    print(f"  Provider: {config.get_provider()}")
    print(f"  Primary model: {config.get_model('primary')}")
    print(f"  Fast model: {config.get_model('fast')}")
    print(f"  Has Bedrock: {config.has_bedrock()}")
    print(f"  Has Ollama: {config.has_ollama()}")
    print()

    if config.has_bedrock():
        print("AWS Bedrock:")
        print(f"  Region: {config.get_aws_region()}")
        print(f"  Profile: {config.get_aws_profile()}")
        print(f"  Model: {config.get_bedrock_model()}")
        print()

    print("✓ config.py module ready")
