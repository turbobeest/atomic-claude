"""
Unit Tests for Core Configuration Management

Tests Config, ConfigLoader, and configuration loading from multiple sources.

Author: Phase 6 - Testing & Validation
"""

import pytest
import json
import os
from pathlib import Path

from core.config import (
    Config,
    ConfigLoader,
    NetworkMode,
    Provider,
    ModelRole,
    get_config
)


# ============================================================================
# CONFIG LOADER TESTS
# ============================================================================

@pytest.mark.unit
class TestConfigLoader:
    """Test ConfigLoader class."""

    def test_load_defaults(self, temp_dir):
        """Test loading default configuration."""
        loader = ConfigLoader(temp_dir)
        defaults = loader.load_defaults()

        assert defaults["version"] == "1.0"
        assert "project" in defaults
        assert "llm" in defaults
        assert defaults["project"]["name"] == "unknown"
        assert defaults["llm"]["primary_model"] == "sonnet"

    def test_load_from_env(self, temp_dir, monkeypatch):
        """Test loading configuration from environment variables."""
        # Set environment variables
        monkeypatch.setenv("ATOMIC_PROJECT_NAME", "test-project")
        monkeypatch.setenv("CLAUDE_MODEL", "opus")
        monkeypatch.setenv("CLAUDE_PROVIDER", "bedrock")
        monkeypatch.setenv("AWS_REGION", "us-east-1")

        loader = ConfigLoader(temp_dir)
        config = loader.load_from_env()

        assert config["project"]["name"] == "test-project"
        assert config["llm"]["primary_model"] == "opus"
        assert config["llm"]["primary_provider"] == "bedrock"
        assert config["secrets"]["aws_region"] == "us-east-1"

    def test_load_from_dotenv(self, temp_dir):
        """Test loading configuration from .env file."""
        # Create .env file
        env_file = temp_dir / ".env"
        env_file.write_text("""
ATOMIC_PROJECT_NAME=dotenv-project
CLAUDE_MODEL=sonnet
CLAUDE_MAX_TURNS=25
""")

        loader = ConfigLoader(temp_dir)
        config = loader.load_from_dotenv()

        assert config["project"]["name"] == "dotenv-project"
        assert config["llm"]["primary_model"] == "sonnet"
        assert config["llm"]["max_turns"] == 25

    def test_load_from_json_files(self, temp_dir):
        """Test loading configuration from JSON files."""
        # Create output directory structure
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create project config
        project_config = {
            "extracted": {
                "project": {"name": "json-project", "type": "web-app"},
                "llm": {"primary_model": "haiku"}
            }
        }

        config_file = output_dir / "project-config.json"
        with open(config_file, 'w') as f:
            json.dump(project_config, f)

        # Create secrets
        secrets = {
            "bedrock_enabled": True,
            "aws_region": "us-west-2"
        }

        secrets_file = output_dir / "secrets.json"
        with open(secrets_file, 'w') as f:
            json.dump(secrets, f)

        # Load
        loader = ConfigLoader(temp_dir)
        config = loader.load_from_json_files()

        assert config["project"]["name"] == "json-project"
        assert config["llm"]["primary_model"] == "haiku"
        assert config["secrets"]["bedrock_enabled"] is True

    def test_merge_configs(self, temp_dir):
        """Test merging multiple configurations."""
        loader = ConfigLoader(temp_dir)

        config1 = {"project": {"name": "test1"}}
        config2 = {"project": {"type": "web-app"}}
        config3 = {"project": {"name": "test3", "version": "1.0"}}

        merged = loader.merge_configs(config1, config2, config3)

        # Later configs override earlier ones
        assert merged["project"]["name"] == "test3"
        assert merged["project"]["type"] == "web-app"
        assert merged["project"]["version"] == "1.0"

    def test_deep_merge(self, temp_dir):
        """Test deep merging of nested configurations."""
        loader = ConfigLoader(temp_dir)

        config1 = {
            "llm": {
                "primary_model": "sonnet",
                "fast_model": "haiku"
            }
        }

        config2 = {
            "llm": {
                "primary_model": "opus"  # Override
                # fast_model should be preserved
            }
        }

        merged = loader.merge_configs(config1, config2)

        assert merged["llm"]["primary_model"] == "opus"
        assert merged["llm"]["fast_model"] == "haiku"


# ============================================================================
# CONFIG CLASS TESTS
# ============================================================================

@pytest.mark.unit
class TestConfig:
    """Test Config class."""

    def test_init_with_defaults(self, temp_dir):
        """Test Config initializes with default values."""
        config = Config(atomic_root=temp_dir)

        assert config.get("project.name") == "unknown"
        assert config.get("llm.primary_model") == "sonnet"
        assert config.get("llm.timeout") == 1200

    def test_get_with_dot_notation(self, temp_dir):
        """Test getting config values with dot notation."""
        config = Config(atomic_root=temp_dir)

        # Nested access
        assert config.get("llm.primary_model") == "sonnet"
        assert config.get("llm.fast_model") == "haiku"

        # Default value
        assert config.get("nonexistent.key", "default") == "default"

    def test_set_with_dot_notation(self, temp_dir):
        """Test setting config values with dot notation."""
        config = Config(atomic_root=temp_dir)

        config.set("project.name", "my-project")
        assert config.get("project.name") == "my-project"

        # Nested set (creates structure)
        config.set("custom.nested.value", 42)
        assert config.get("custom.nested.value") == 42

    def test_get_project_name(self, temp_dir):
        """Test getting project name."""
        config = Config(atomic_root=temp_dir)

        assert config.get_project_name() == "unknown"

        config.set("project.name", "test-project")
        assert config.get_project_name() == "test-project"

    def test_get_project_type(self, temp_dir):
        """Test getting project type."""
        config = Config(atomic_root=temp_dir)

        assert config.get_project_type() == "unknown"

        config.set("project.type", "cli-tool")
        assert config.get_project_type() == "cli-tool"

    def test_get_network_mode(self, temp_dir):
        """Test getting network mode."""
        config = Config(atomic_root=temp_dir)

        # Default
        assert config.get_network_mode() == "cui"

        config.set("sandbox.network_mode", "internet")
        assert config.get_network_mode() == "internet"

    def test_get_provider_default(self, temp_dir):
        """Test getting default provider."""
        config = Config(atomic_root=temp_dir)

        # Default provider
        provider = config.get_provider()
        assert provider == "max"

    def test_get_provider_by_role(self, temp_dir):
        """Test getting provider by role."""
        config = Config(atomic_root=temp_dir)

        # Set role-specific provider
        config.set("llm.fast_provider", "ollama")

        assert config.get_provider("fast") == "ollama"
        assert config.get_provider("primary") == "max"  # Falls back to default

    def test_get_model_default(self, temp_dir):
        """Test getting default model."""
        config = Config(atomic_root=temp_dir)

        assert config.get_model("primary") == "sonnet"
        assert config.get_model("fast") == "haiku"
        assert config.get_model("heavyweight") == "opus"

    def test_get_model_with_override(self, temp_dir, monkeypatch):
        """Test getting model with environment override."""
        monkeypatch.setenv("CLAUDE_MODEL", "custom-model")

        config = Config(atomic_root=temp_dir)

        # Environment variable should override
        assert config.get_model("primary") == "custom-model"

    def test_has_bedrock(self, temp_dir):
        """Test checking if Bedrock is configured."""
        config = Config(atomic_root=temp_dir)

        assert config.has_bedrock() is False

        config.set("secrets.bedrock_enabled", True)
        assert config.has_bedrock() is True

    def test_has_ollama(self, temp_dir):
        """Test checking if Ollama is configured."""
        config = Config(atomic_root=temp_dir)

        assert config.has_ollama() is False

        config.set("secrets.ollama_enabled", True)
        assert config.has_ollama() is True

    def test_get_aws_region(self, temp_dir):
        """Test getting AWS region."""
        config = Config(atomic_root=temp_dir)

        assert config.get_aws_region() is None

        config.set("secrets.aws_region", "us-gov-west-1")
        assert config.get_aws_region() == "us-gov-west-1"

    def test_get_aws_profile(self, temp_dir):
        """Test getting AWS profile."""
        config = Config(atomic_root=temp_dir)

        assert config.get_aws_profile() is None

        config.set("secrets.aws_profile", "my-profile")
        assert config.get_aws_profile() == "my-profile"

    def test_reload(self, temp_dir):
        """Test hot-reloading configuration."""
        config = Config(atomic_root=temp_dir)

        # Initial value
        assert config.get("project.name") == "unknown"

        # Create config file
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True, exist_ok=True)

        project_config = {
            "extracted": {
                "project": {"name": "reloaded-project"}
            }
        }

        config_file = output_dir / "project-config.json"
        with open(config_file, 'w') as f:
            json.dump(project_config, f)

        # Reload
        config.reload()

        # Should pick up new value
        assert config.get("project.name") == "reloaded-project"

    def test_to_dict(self, temp_dir):
        """Test exporting config to dict."""
        config = Config(atomic_root=temp_dir)

        data = config.to_dict()

        assert isinstance(data, dict)
        assert "project" in data
        assert "llm" in data

    def test_save(self, temp_dir):
        """Test saving config to file."""
        config = Config(atomic_root=temp_dir)
        config.set("project.name", "saved-project")

        save_path = temp_dir / "saved-config.json"
        config.save(save_path)

        assert save_path.exists()

        # Verify content
        with open(save_path) as f:
            data = json.load(f)

        assert data["project"]["name"] == "saved-project"

    def test_validate(self, temp_dir):
        """Test config validation."""
        config = Config(atomic_root=temp_dir)

        # Valid config
        assert config.validate() is True

        # Invalid config (if Pydantic available)
        # Note: This depends on Pydantic being installed


# ============================================================================
# ENVIRONMENT VARIABLE PRIORITY TESTS
# ============================================================================

@pytest.mark.unit
class TestEnvironmentPriority:
    """Test environment variable priority in config loading."""

    def test_env_overrides_file(self, temp_dir, monkeypatch):
        """Test environment variables override file config."""
        # Create file config
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True, exist_ok=True)

        project_config = {
            "extracted": {
                "project": {"name": "file-project"}
            }
        }

        config_file = output_dir / "project-config.json"
        with open(config_file, 'w') as f:
            json.dump(project_config, f)

        # Set environment variable
        monkeypatch.setenv("ATOMIC_PROJECT_NAME", "env-project")

        # Load config
        config = Config(atomic_root=temp_dir)

        # Environment should win
        assert config.get("project.name") == "env-project"

    def test_cli_overrides_env(self, temp_dir, monkeypatch):
        """Test CLI args override environment variables."""
        # Set environment variable
        monkeypatch.setenv("ATOMIC_PROJECT_NAME", "env-project")

        # CLI args
        cli_args = {
            "project": {"name": "cli-project"}
        }

        # Load config
        config = Config(atomic_root=temp_dir, cli_args=cli_args)

        # CLI should win
        assert config.get("project.name") == "cli-project"

    def test_priority_order(self, temp_dir, monkeypatch):
        """Test complete priority order: CLI > env > dotenv > file > defaults."""
        # Create .env file
        env_file = temp_dir / ".env"
        env_file.write_text("ATOMIC_PROJECT_NAME=dotenv-project\n")

        # Create JSON file
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True, exist_ok=True)

        project_config = {
            "extracted": {
                "project": {"name": "file-project"}
            }
        }

        config_file = output_dir / "project-config.json"
        with open(config_file, 'w') as f:
            json.dump(project_config, f)

        # Set environment variable (highest priority except CLI)
        monkeypatch.setenv("ATOMIC_PROJECT_NAME", "env-project")

        # Load config
        config = Config(atomic_root=temp_dir)

        # Environment should win over file and .env
        assert config.get("project.name") == "env-project"

    def test_fallback_to_env_on_missing(self, temp_dir, monkeypatch):
        """Test fallback to environment when config file missing."""
        # Only set environment variable
        monkeypatch.setenv("AWS_REGION", "us-west-2")

        config = Config(atomic_root=temp_dir)

        # Should use environment value
        assert config.get_aws_region() == "us-west-2"


# ============================================================================
# DEFAULT VALUES TESTS
# ============================================================================

@pytest.mark.unit
class TestDefaultValues:
    """Test default configuration values."""

    def test_default_project_values(self, temp_dir):
        """Test default project configuration."""
        config = Config(atomic_root=temp_dir)

        assert config.get("project.name") == "unknown"
        assert config.get("project.type") == "unknown"
        assert config.get("project.version") == "0.1.0"

    def test_default_llm_values(self, temp_dir):
        """Test default LLM configuration."""
        config = Config(atomic_root=temp_dir)

        assert config.get("llm.primary_provider") == "max"
        assert config.get("llm.primary_model") == "sonnet"
        assert config.get("llm.fast_model") == "haiku"
        assert config.get("llm.heavyweight_model") == "opus"
        assert config.get("llm.max_turns") == 30
        assert config.get("llm.timeout") == 1200

    def test_default_memory_values(self, temp_dir):
        """Test default memory configuration."""
        config = Config(atomic_root=temp_dir)

        assert config.get("memory.enabled") is True
        assert config.get("memory.checkpoint_frequency") == 5
        assert config.get("memory.max_size_mb") == 100

    def test_default_dashboard_values(self, temp_dir):
        """Test default dashboard configuration."""
        config = Config(atomic_root=temp_dir)

        assert config.get("dashboard.enabled") is True
        assert config.get("dashboard.host") == "localhost"
        assert config.get("dashboard.tasks_port") == 5173
        assert config.get("dashboard.agents_port") == 5174

    def test_default_secrets_values(self, temp_dir):
        """Test default secrets configuration."""
        config = Config(atomic_root=temp_dir)

        assert config.get("secrets.bedrock_enabled") is False
        assert config.get("secrets.ollama_enabled") is False
        assert config.get("secrets.ollama_host") == "http://localhost:11434"


# ============================================================================
# GLOBAL SINGLETON TESTS
# ============================================================================

@pytest.mark.unit
class TestGlobalConfig:
    """Test global config singleton."""

    def test_get_config_singleton(self, temp_dir):
        """Test get_config returns singleton instance."""
        config1 = get_config(atomic_root=temp_dir)
        config2 = get_config()  # Should return same instance

        # Same instance
        assert config1 is config2

    def test_singleton_resets_on_new_root(self, temp_dir):
        """Test singleton resets when new root provided."""
        config1 = get_config(atomic_root=temp_dir)

        # Create new temp dir
        import tempfile
        temp_dir2 = Path(tempfile.mkdtemp())

        config2 = get_config(atomic_root=temp_dir2)

        # Different instance (new root provided)
        assert config1 is not config2

        # Cleanup
        import shutil
        shutil.rmtree(temp_dir2)


# ============================================================================
# EDGE CASES
# ============================================================================

@pytest.mark.unit
class TestConfigEdgeCases:
    """Test edge cases in configuration management."""

    def test_missing_config_files(self, temp_dir):
        """Test handling missing config files."""
        # No config files exist
        config = Config(atomic_root=temp_dir)

        # Should use defaults
        assert config.get("project.name") == "unknown"

    def test_invalid_json_file(self, temp_dir):
        """Test handling invalid JSON config file."""
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write invalid JSON
        config_file = output_dir / "project-config.json"
        config_file.write_text("{ invalid json }")

        # Should not crash, use defaults
        config = Config(atomic_root=temp_dir)
        assert config.get("project.name") == "unknown"

    def test_empty_dotenv_file(self, temp_dir):
        """Test handling empty .env file."""
        env_file = temp_dir / ".env"
        env_file.write_text("")

        config = Config(atomic_root=temp_dir)

        # Should use defaults
        assert config.get("project.name") == "unknown"

    def test_malformed_dotenv_entries(self, temp_dir):
        """Test handling malformed .env entries."""
        env_file = temp_dir / ".env"
        env_file.write_text("""
# Comment
VALID_KEY=valid_value
INVALID_LINE_NO_EQUALS
=NO_KEY
""")

        config = Config(atomic_root=temp_dir)

        # Should skip invalid lines, load valid ones
        # (ConfigLoader should handle this gracefully)

    def test_nested_key_on_nondict_value(self, temp_dir):
        """Test setting nested key when parent is not a dict."""
        config = Config(atomic_root=temp_dir)

        # Set parent as string
        config.set("test", "string_value")

        # Try to set nested key (should replace parent with dict)
        config.set("test.nested", "value")

        assert config.get("test.nested") == "value"

    def test_get_with_none_default(self, temp_dir):
        """Test get with None as default."""
        config = Config(atomic_root=temp_dir)

        result = config.get("nonexistent.key", None)
        assert result is None
