"""
Unit Tests for Configuration System

Comprehensive tests for core/config.py covering:
- Multi-source loading (env, .env, JSON, CLI)
- Override hierarchy validation
- Dot notation access
- Pydantic validation
- Hot reload
- Type safety
- Default values
- Provider/model role selection

Requirements: 20+ tests with 95%+ coverage
"""

import pytest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.config import (
    Config,
    ConfigLoader,
    NetworkMode,
    Provider,
    ModelRole,
    get_config
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_atomic_root(tmp_path):
    """Create temporary atomic root directory."""
    return tmp_path


@pytest.fixture
def sample_project_config():
    """Sample project config JSON."""
    return {
        "extracted": {
            "project": {
                "name": "test-project",
                "type": "webapp",
                "version": "1.0.0"
            },
            "llm": {
                "primary_provider": "api",
                "primary_model": "sonnet",
                "fast_model": "haiku"
            },
            "sandbox": {
                "network_mode": "internet"
            },
            "pipeline": {
                "auto_chain": True
            }
        }
    }


@pytest.fixture
def sample_secrets():
    """Sample secrets JSON."""
    return {
        "bedrock_enabled": True,
        "aws_region": "us-west-2",
        "aws_profile": "default",
        "ollama_enabled": False
    }


@pytest.fixture
def setup_project_config(temp_atomic_root, sample_project_config, sample_secrets):
    """Setup Phase 00 output files."""
    outputs_dir = temp_atomic_root / ".outputs" / "0-setup"
    outputs_dir.mkdir(parents=True)

    # Write project config
    with open(outputs_dir / "project-config.json", 'w') as f:
        json.dump(sample_project_config, f)

    # Write secrets
    with open(outputs_dir / "secrets.json", 'w') as f:
        json.dump(sample_secrets, f)

    return temp_atomic_root


# ============================================================================
# LOADER TESTS
# ============================================================================

class TestConfigLoader:
    """Test ConfigLoader multi-source loading."""

    def test_load_defaults(self, temp_atomic_root):
        """Test loading default configuration."""
        loader = ConfigLoader(temp_atomic_root)
        defaults = loader.load_defaults()

        assert defaults['version'] == '1.0'
        assert defaults['project']['name'] == 'unknown'
        assert defaults['llm']['primary_model'] == 'sonnet'
        assert defaults['llm']['fast_model'] == 'haiku'

    def test_load_from_env(self, temp_atomic_root):
        """Test loading from environment variables."""
        with patch.dict(os.environ, {
            'CLAUDE_MODEL': 'opus',
            'CLAUDE_PROVIDER': 'bedrock',
            'ATOMIC_PROJECT_NAME': 'env-project'
        }):
            loader = ConfigLoader(temp_atomic_root)
            env_config = loader.load_from_env()

            assert env_config['llm']['primary_model'] == 'opus'
            assert env_config['llm']['primary_provider'] == 'bedrock'
            assert env_config['project']['name'] == 'env-project'

    def test_load_from_dotenv(self, temp_atomic_root):
        """Test loading from .env file."""
        env_file = temp_atomic_root / ".env"
        env_file.write_text("""
CLAUDE_MODEL=haiku
CLAUDE_PROVIDER=ollama
ATOMIC_PROJECT_NAME=dotenv-project
""")

        loader = ConfigLoader(temp_atomic_root)
        dotenv_config = loader.load_from_dotenv()

        assert dotenv_config['llm']['primary_model'] == 'haiku'
        assert dotenv_config['llm']['primary_provider'] == 'ollama'

    def test_load_from_json_files(self, setup_project_config):
        """Test loading from Phase 00 JSON outputs."""
        loader = ConfigLoader(setup_project_config)
        json_config = loader.load_from_json_files()

        assert json_config['project']['name'] == 'test-project'
        assert json_config['project']['type'] == 'webapp'
        assert json_config['llm']['primary_model'] == 'sonnet'
        assert json_config['secrets']['bedrock_enabled'] is True

    def test_merge_configs_priority(self, temp_atomic_root):
        """Test config merge with priority (later overrides earlier)."""
        loader = ConfigLoader(temp_atomic_root)

        config1 = {'project': {'name': 'first'}, 'llm': {'primary_model': 'sonnet'}}
        config2 = {'project': {'name': 'second'}}  # Should override
        config3 = {'llm': {'primary_model': 'opus'}}  # Should override

        merged = loader.merge_configs(config1, config2, config3)

        assert merged['project']['name'] == 'second'
        assert merged['llm']['primary_model'] == 'opus'

    def test_deep_merge(self, temp_atomic_root):
        """Test deep merge of nested dicts."""
        loader = ConfigLoader(temp_atomic_root)

        config1 = {'a': {'b': 1, 'c': 2}, 'd': 3}
        config2 = {'a': {'b': 10}, 'e': 4}

        merged = loader.merge_configs(config1, config2)

        assert merged['a']['b'] == 10  # Overridden
        assert merged['a']['c'] == 2   # Preserved
        assert merged['d'] == 3        # Preserved
        assert merged['e'] == 4        # Added


# ============================================================================
# CONFIG CLASS TESTS
# ============================================================================

class TestConfig:
    """Test main Config class."""

    def test_init_with_defaults(self, temp_atomic_root):
        """Test initialization with default values."""
        config = Config(atomic_root=temp_atomic_root)

        assert config.get_project_name() == 'unknown'
        assert config.get_provider() == 'max'
        assert config.get_model('primary') == 'sonnet'

    def test_init_with_json_files(self, setup_project_config):
        """Test initialization with Phase 00 outputs."""
        config = Config(atomic_root=setup_project_config)

        assert config.get_project_name() == 'test-project'
        assert config.get('project.type') == 'webapp'
        assert config.get('llm.primary_model') == 'sonnet'

    def test_dot_notation_access(self, setup_project_config):
        """Test dot notation for nested config access."""
        config = Config(atomic_root=setup_project_config)

        assert config.get('project.name') == 'test-project'
        assert config.get('llm.primary_model') == 'sonnet'
        assert config.get('sandbox.network_mode') == 'internet'

    def test_dot_notation_with_default(self, temp_atomic_root):
        """Test dot notation with default value."""
        config = Config(atomic_root=temp_atomic_root)

        assert config.get('nonexistent.key', 'default_value') == 'default_value'
        assert config.get('project.nonexistent', 'fallback') == 'fallback'

    def test_environment_override(self, setup_project_config):
        """Test environment variables override file config."""
        with patch.dict(os.environ, {'ATOMIC_PROJECT_NAME': 'env-override'}):
            config = Config(atomic_root=setup_project_config)

            # Env should override file
            assert config.get('project.name') == 'env-override'

    def test_cli_args_override(self, setup_project_config):
        """Test CLI args have highest priority."""
        cli_args = {
            'project': {'name': 'cli-override'},
            'llm': {'primary_model': 'opus'}
        }

        config = Config(atomic_root=setup_project_config, cli_args=cli_args)

        assert config.get('project.name') == 'cli-override'
        assert config.get('llm.primary_model') == 'opus'

    def test_set_runtime_value(self, temp_atomic_root):
        """Test setting configuration at runtime."""
        config = Config(atomic_root=temp_atomic_root)

        config.set('project.name', 'runtime-name')
        assert config.get('project.name') == 'runtime-name'

        config.set('new.nested.key', 'value')
        assert config.get('new.nested.key') == 'value'

    def test_reload(self, temp_atomic_root):
        """Test hot-reload of configuration."""
        config = Config(atomic_root=temp_atomic_root)
        initial_name = config.get_project_name()

        # Create config file
        outputs_dir = temp_atomic_root / ".outputs" / "0-setup"
        outputs_dir.mkdir(parents=True)
        with open(outputs_dir / "project-config.json", 'w') as f:
            json.dump({
                "extracted": {
                    "project": {"name": "reloaded-project"}
                }
            }, f)

        # Reload
        config.reload()

        assert config.get_project_name() == 'reloaded-project'
        assert config.get_project_name() != initial_name

    def test_to_dict(self, setup_project_config):
        """Test export configuration to dict."""
        config = Config(atomic_root=setup_project_config)
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert 'project' in config_dict
        assert 'llm' in config_dict
        assert config_dict['project']['name'] == 'test-project'

    def test_save_config(self, temp_atomic_root):
        """Test saving configuration to file."""
        config = Config(atomic_root=temp_atomic_root)
        config.set('project.name', 'saved-project')

        save_path = temp_atomic_root / "saved-config.json"
        config.save(save_path)

        assert save_path.exists()

        with open(save_path) as f:
            saved = json.load(f)
        assert saved['project']['name'] == 'saved-project'

    def test_validate(self, setup_project_config):
        """Test configuration validation."""
        config = Config(atomic_root=setup_project_config)

        # Should be valid
        assert config.validate() is True


# ============================================================================
# CONVENIENCE ACCESSORS
# ============================================================================

class TestConvenienceAccessors:
    """Test convenience accessor methods."""

    def test_get_provider_roles(self, setup_project_config):
        """Test provider selection by role."""
        config = Config(atomic_root=setup_project_config)

        # Primary provider from config
        assert config.get_provider('primary') == 'api'

        # Fallback to primary for unspecified roles
        assert config.get_provider('fast') in ['api', 'max']

    def test_get_model_roles(self, setup_project_config):
        """Test model selection by role."""
        config = Config(atomic_root=setup_project_config)

        assert config.get_model('primary') == 'sonnet'
        assert config.get_model('fast') == 'haiku'
        assert config.get_model('heavyweight') == 'opus'
        assert config.get_model('gardener') == 'haiku'

    def test_get_project_name(self, setup_project_config):
        """Test get project name."""
        config = Config(atomic_root=setup_project_config)
        assert config.get_project_name() == 'test-project'

    def test_get_project_type(self, setup_project_config):
        """Test get project type."""
        config = Config(atomic_root=setup_project_config)
        assert config.get_project_type() == 'webapp'

    def test_get_network_mode(self, setup_project_config):
        """Test get network mode."""
        config = Config(atomic_root=setup_project_config)
        assert config.get_network_mode() == 'internet'

    def test_has_bedrock(self, setup_project_config):
        """Test Bedrock detection."""
        config = Config(atomic_root=setup_project_config)
        assert config.has_bedrock() is True

    def test_has_ollama(self, setup_project_config):
        """Test Ollama detection."""
        config = Config(atomic_root=setup_project_config)
        assert config.has_ollama() is False

    def test_get_aws_region(self, setup_project_config):
        """Test AWS region getter (from config file)."""
        config = Config(atomic_root=setup_project_config)
        # Config file has us-west-2, which should take precedence
        region = config.get_aws_region()
        # Should return the config value (us-west-2) or environment fallback
        assert region in ['us-west-2', os.environ.get('AWS_REGION')]

    def test_get_aws_profile(self, setup_project_config):
        """Test AWS profile getter (from config file)."""
        config = Config(atomic_root=setup_project_config)
        # Config file has default, which should take precedence
        profile = config.get_aws_profile()
        # Should return the config value (default) or environment fallback
        assert profile in ['default', os.environ.get('AWS_PROFILE')]

    def test_get_ollama_host(self, temp_atomic_root):
        """Test Ollama host getter."""
        config = Config(atomic_root=temp_atomic_root)
        assert config.get_ollama_host() == 'http://localhost:11434'

    def test_get_ollama_context(self, temp_atomic_root):
        """Test Ollama context getter."""
        config = Config(atomic_root=temp_atomic_root)
        assert config.get_ollama_context() == 65536


# ============================================================================
# GLOBAL SINGLETON
# ============================================================================

class TestGlobalSingleton:
    """Test global config singleton."""

    def test_get_config_singleton(self, temp_atomic_root):
        """Test get_config returns singleton."""
        config1 = get_config(atomic_root=temp_atomic_root)
        config2 = get_config()  # Should return same instance

        assert config1 is config2

    def test_get_config_with_new_root(self, temp_atomic_root):
        """Test get_config with new root creates new instance."""
        config1 = get_config(atomic_root=temp_atomic_root)

        new_root = temp_atomic_root / "subdir"
        new_root.mkdir()
        config2 = get_config(atomic_root=new_root)

        # Should be different instances
        assert config1.atomic_root != config2.atomic_root


# ============================================================================
# EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_missing_config_files(self, temp_atomic_root):
        """Test behavior with missing config files."""
        config = Config(atomic_root=temp_atomic_root)

        # Should fall back to defaults
        assert config.get_project_name() == 'unknown'
        assert config.get_model('primary') == 'sonnet'

    def test_invalid_json_file(self, temp_atomic_root):
        """Test handling of invalid JSON files."""
        outputs_dir = temp_atomic_root / ".outputs" / "0-setup"
        outputs_dir.mkdir(parents=True)

        # Write invalid JSON
        with open(outputs_dir / "project-config.json", 'w') as f:
            f.write("{invalid json")

        # Should not crash, fall back to defaults
        config = Config(atomic_root=temp_atomic_root)
        assert config.get_project_name() == 'unknown'

    def test_empty_dotenv_file(self, temp_atomic_root):
        """Test handling of empty .env file."""
        env_file = temp_atomic_root / ".env"
        env_file.write_text("")

        config = Config(atomic_root=temp_atomic_root)
        assert config.get_project_name() == 'unknown'

    def test_dotenv_with_comments(self, temp_atomic_root):
        """Test .env file with comments and blank lines."""
        env_file = temp_atomic_root / ".env"
        env_file.write_text("""
# This is a comment
CLAUDE_MODEL=sonnet

# Another comment
CLAUDE_PROVIDER=api
""")

        config = Config(atomic_root=temp_atomic_root)
        assert config.get_model('primary') == 'sonnet'

    def test_nested_key_nonexistent_parent(self, temp_atomic_root):
        """Test accessing nested key with nonexistent parent."""
        config = Config(atomic_root=temp_atomic_root)

        result = config.get('nonexistent.parent.child', 'default')
        assert result == 'default'


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Test performance requirements."""

    def test_config_load_performance(self, setup_project_config):
        """Test config loading is under 10ms."""
        import time

        start = time.time()
        config = Config(atomic_root=setup_project_config)
        duration_ms = (time.time() - start) * 1000

        # Should load in < 10ms
        assert duration_ms < 10, f"Config load took {duration_ms:.2f}ms (target: <10ms)"

    def test_get_performance(self, setup_project_config):
        """Test config.get() is fast."""
        import time

        config = Config(atomic_root=setup_project_config)

        start = time.time()
        for _ in range(1000):
            config.get('project.name')
        duration_ms = (time.time() - start) * 1000

        # 1000 gets should be < 10ms
        assert duration_ms < 10, f"1000 get() calls took {duration_ms:.2f}ms"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestConfigIntegration:
    """Integration tests with multiple sources."""

    def test_full_priority_chain(self, temp_atomic_root):
        """Test full priority chain: CLI > env > .env > JSON > defaults."""
        # Setup JSON file
        outputs_dir = temp_atomic_root / ".outputs" / "0-setup"
        outputs_dir.mkdir(parents=True)
        with open(outputs_dir / "project-config.json", 'w') as f:
            json.dump({
                "extracted": {
                    "project": {"name": "json-name"},
                    "llm": {"primary_model": "sonnet"}
                }
            }, f)

        # Setup .env file
        env_file = temp_atomic_root / ".env"
        env_file.write_text("CLAUDE_MODEL=haiku\n")

        # Setup CLI args
        cli_args = {'project': {'name': 'cli-name'}}

        with patch.dict(os.environ, {'ATOMIC_PROJECT_NAME': 'env-name'}):
            config = Config(atomic_root=temp_atomic_root, cli_args=cli_args)

            # CLI should win for project name
            assert config.get('project.name') == 'cli-name'

            # .env should win for model (no CLI override)
            assert config.get('llm.primary_model') == 'haiku'

    def test_partial_overrides(self, setup_project_config):
        """Test partial overrides preserve other values."""
        cli_args = {'project': {'name': 'new-name'}}
        config = Config(atomic_root=setup_project_config, cli_args=cli_args)

        # Name overridden
        assert config.get('project.name') == 'new-name'

        # Type preserved from JSON
        assert config.get('project.type') == 'webapp'

        # LLM config preserved
        assert config.get('llm.primary_model') == 'sonnet'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
