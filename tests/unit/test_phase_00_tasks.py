"""
Unit Tests for Phase 0 (Setup) Task Modules

Tests all 5 Phase 0 tasks with comprehensive coverage:
- Task 001: Environment Bootstrap (OS detection, tool checking, dashboard deps)
- Task 002: Provider Detection (credentials, Ollama hosts, health checks, inventory)
- Task 003: Setup Wizard (validation, slugify, schema validation, marker resolution)
- Task 004: Material Scan (file scanning, stack detection, key files, reference collection)
- Task 005: Repository Setup (agent/audit/skill verification, git validation, system assessment)
"""

import json
import os
import platform
import pytest
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime

# Import task modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phases.phase_00_setup.tasks import task_001_environment_bootstrap
from phases.phase_00_setup.tasks import task_002_provider_detection
from phases.phase_00_setup.tasks import task_003_setup_wizard
from phases.phase_00_setup.tasks import task_004_material_scan
from phases.phase_00_setup.tasks import task_005_repository_setup


# ============================================================================
# Task 001: Environment Bootstrap Tests
# ============================================================================

@pytest.mark.unit
class TestTask001EnvironmentBootstrap:
    """Unit tests for task_001_environment_bootstrap."""

    @patch('phases.phase_00_setup.tasks.task_001_environment_bootstrap._record_environment')
    @patch('phases.phase_00_setup.tasks.task_001_environment_bootstrap._launch_dashboard')
    @patch('phases.phase_00_setup.tasks.task_001_environment_bootstrap._install_dashboard_deps')
    @patch('phases.phase_00_setup.tasks.task_001_environment_bootstrap._show_summary')
    @patch('phases.phase_00_setup.tasks.task_001_environment_bootstrap._show_airgap_note')
    @patch('phases.phase_00_setup.tasks.task_001_environment_bootstrap._show_recommended_tools')
    @patch('phases.phase_00_setup.tasks.task_001_environment_bootstrap._show_required_tools')
    @patch('phases.phase_00_setup.tasks.task_001_environment_bootstrap._detect_os', return_value='linux')
    @patch('phases.phase_00_setup.tasks.task_001_environment_bootstrap._show_info_box')
    def test_execute_uat_mode_returns_true(
        self, mock_info, mock_os, mock_req, mock_rec, mock_air,
        mock_summary, mock_deps, mock_launch, mock_record, temp_dir
    ):
        """Test execute in UAT mode returns True when all tools installed."""
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True)

        # Simulate all required tools installed
        task_001_environment_bootstrap.REQUIRED_TOTAL = 6
        task_001_environment_bootstrap.REQUIRED_INSTALLED = 6

        result = task_001_environment_bootstrap.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        assert result is True

    @patch('phases.phase_00_setup.tasks.task_001_environment_bootstrap._record_environment')
    @patch('phases.phase_00_setup.tasks.task_001_environment_bootstrap._launch_dashboard')
    @patch('phases.phase_00_setup.tasks.task_001_environment_bootstrap._install_dashboard_deps')
    @patch('phases.phase_00_setup.tasks.task_001_environment_bootstrap._show_summary')
    @patch('phases.phase_00_setup.tasks.task_001_environment_bootstrap._show_airgap_note')
    @patch('phases.phase_00_setup.tasks.task_001_environment_bootstrap._show_quick_install')
    @patch('phases.phase_00_setup.tasks.task_001_environment_bootstrap._show_recommended_tools')
    @patch('phases.phase_00_setup.tasks.task_001_environment_bootstrap._show_required_tools')
    @patch('phases.phase_00_setup.tasks.task_001_environment_bootstrap._detect_os', return_value='linux')
    @patch('phases.phase_00_setup.tasks.task_001_environment_bootstrap._show_info_box')
    def test_execute_uat_mode_continues_with_missing_tools(
        self, mock_info, mock_os, mock_req, mock_rec, mock_quick,
        mock_air, mock_summary, mock_deps, mock_launch, mock_record, temp_dir
    ):
        """Test execute in UAT mode continues even with missing tools."""
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True)

        # Simulate missing tools -- _show_required_tools sets these globals
        task_001_environment_bootstrap.REQUIRED_TOTAL = 6
        task_001_environment_bootstrap.REQUIRED_INSTALLED = 4

        result = task_001_environment_bootstrap.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        # UAT mode continues despite missing tools
        assert result is True

    def test_detect_os_returns_known_type(self):
        """Test _detect_os returns a recognized OS type."""
        os_type = task_001_environment_bootstrap._detect_os()
        assert os_type in ("macos", "debian", "redhat", "arch", "linux", "windows", "unknown")

    @patch('shutil.which', return_value='/usr/bin/git')
    @patch('subprocess.run')
    def test_check_tool_git_returns_version(self, mock_run, mock_which):
        """Test _check_tool returns version for git."""
        mock_run.return_value = Mock(returncode=0, stdout="git version 2.43.0\n")

        version = task_001_environment_bootstrap._check_tool("git")

        assert version == "2.43.0"

    @patch('shutil.which', return_value='/usr/bin/node')
    @patch('subprocess.run')
    def test_check_tool_node_strips_v_prefix(self, mock_run, mock_which):
        """Test _check_tool strips leading 'v' from node version."""
        mock_run.return_value = Mock(returncode=0, stdout="v20.11.0\n")

        version = task_001_environment_bootstrap._check_tool("node")

        assert version == "20.11.0"

    @patch('shutil.which', return_value=None)
    def test_check_tool_missing_returns_none(self, mock_which):
        """Test _check_tool returns None for missing tool."""
        version = task_001_environment_bootstrap._check_tool("nonexistent-tool")
        assert version is None

    @patch('shutil.which', return_value='/usr/bin/jq')
    @patch('subprocess.run')
    def test_check_tool_jq_strips_prefix(self, mock_run, mock_which):
        """Test _check_tool strips 'jq-' prefix from version."""
        mock_run.return_value = Mock(returncode=0, stdout="jq-1.7\n")

        version = task_001_environment_bootstrap._check_tool("jq")

        assert version == "1.7"

    def test_get_install_cmd_returns_platform_specific(self):
        """Test _get_install_cmd returns OS-specific commands."""
        cmd_macos = task_001_environment_bootstrap._get_install_cmd("git", "macos")
        assert "brew" in cmd_macos

        cmd_debian = task_001_environment_bootstrap._get_install_cmd("git", "debian")
        assert "apt" in cmd_debian

        cmd_windows = task_001_environment_bootstrap._get_install_cmd("git", "windows")
        assert "winget" in cmd_windows

    def test_get_install_cmd_wildcard_fallback(self):
        """Test _get_install_cmd uses wildcard fallback for npm tools."""
        cmd = task_001_environment_bootstrap._get_install_cmd("claude", "linux")
        assert "npm install -g" in cmd

    def test_record_environment_writes_config(self, temp_dir):
        """Test _record_environment writes environment info to config file."""
        config_file = temp_dir / "project-config.json"

        # Set globals
        task_001_environment_bootstrap.REQUIRED_TOTAL = 6
        task_001_environment_bootstrap.REQUIRED_INSTALLED = 5
        task_001_environment_bootstrap.RECOMMENDED_TOTAL = 2
        task_001_environment_bootstrap.RECOMMENDED_INSTALLED = 1

        task_001_environment_bootstrap._record_environment(config_file, "linux")

        assert config_file.exists()
        data = json.loads(config_file.read_text())
        assert data["environment"]["os_type"] == "linux"
        assert data["environment"]["required_total"] == 6
        assert data["environment"]["required_installed"] == 5

    def test_record_environment_merges_with_existing(self, temp_dir):
        """Test _record_environment merges with existing config."""
        config_file = temp_dir / "project-config.json"
        config_file.write_text(json.dumps({"project": {"name": "test"}}))

        task_001_environment_bootstrap.REQUIRED_TOTAL = 6
        task_001_environment_bootstrap.REQUIRED_INSTALLED = 6
        task_001_environment_bootstrap.RECOMMENDED_TOTAL = 2
        task_001_environment_bootstrap.RECOMMENDED_INSTALLED = 2

        task_001_environment_bootstrap._record_environment(config_file, "macos")

        data = json.loads(config_file.read_text())
        assert data["project"]["name"] == "test"
        assert data["environment"]["os_type"] == "macos"

    @patch('socket.socket')
    def test_get_hostname_returns_string(self, mock_socket_cls):
        """Test _get_hostname returns a string."""
        mock_sock = Mock()
        mock_sock.getsockname.return_value = ("192.168.1.100", 12345)
        mock_socket_cls.return_value = mock_sock

        hostname = task_001_environment_bootstrap._get_hostname()

        assert isinstance(hostname, str)
        assert len(hostname) > 0


# ============================================================================
# Task 002: Provider Detection Tests
# ============================================================================

@pytest.mark.unit
class TestTask002ProviderDetection:
    """Unit tests for task_002_provider_detection."""

    def test_load_env_file_parses_key_value_pairs(self, temp_dir):
        """Test _load_env_file correctly parses .env format."""
        env_file = temp_dir / ".env"
        env_file.write_text(
            "# Comment line\n"
            "ANTHROPIC_API_KEY=sk-ant-test123\n"
            "AWS_REGION=us-west-2\n"
            "\n"
            "ATOMIC_NETWORK_MODE=open\n"
        )

        env_vars = {}
        task_002_provider_detection._load_env_file(env_file, env_vars)

        assert env_vars["ANTHROPIC_API_KEY"] == "sk-ant-test123"
        assert env_vars["AWS_REGION"] == "us-west-2"
        assert env_vars["ATOMIC_NETWORK_MODE"] == "open"
        # Comments should not be parsed
        assert "#" not in "".join(env_vars.keys())

    def test_load_env_file_skips_comments_and_blanks(self, temp_dir):
        """Test _load_env_file ignores comments and blank lines."""
        env_file = temp_dir / ".env"
        env_file.write_text(
            "# This is a comment\n"
            "\n"
            "KEY=value\n"
        )

        env_vars = {}
        task_002_provider_detection._load_env_file(env_file, env_vars)

        assert len(env_vars) == 1
        assert env_vars["KEY"] == "value"

    def test_detect_credentials_claude_code(self):
        """Test _detect_credentials detects claude-code provider."""
        env_vars = {"ATOMIC_LLM_PROVIDER": "claude-code"}

        has_aws, has_anthropic, has_ollama = task_002_provider_detection._detect_credentials(env_vars)

        assert has_anthropic is True
        assert has_aws is False

    def test_detect_credentials_anthropic_key(self):
        """Test _detect_credentials detects Anthropic API key."""
        env_vars = {"ANTHROPIC_API_KEY": "sk-ant-test123"}

        with patch('subprocess.run', side_effect=Exception("no curl")):
            has_aws, has_anthropic, has_ollama = task_002_provider_detection._detect_credentials(env_vars)

        assert has_anthropic is True

    def test_detect_credentials_aws_profile(self):
        """Test _detect_credentials detects AWS profile."""
        env_vars = {"AWS_PROFILE": "govcloud", "AWS_REGION": "us-gov-west-1"}

        with patch('subprocess.run', side_effect=Exception("no curl")):
            has_aws, has_anthropic, has_ollama = task_002_provider_detection._detect_credentials(env_vars)

        assert has_aws is True

    @patch('urllib.request.urlopen')
    def test_check_ollama_host_healthy(self, mock_urlopen):
        """Test _check_ollama_host returns True for healthy host."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = task_002_provider_detection._check_ollama_host("http://localhost:11434")
        assert result is True

    @patch('urllib.request.urlopen', side_effect=Exception("connection refused"))
    def test_check_ollama_host_unreachable(self, mock_urlopen):
        """Test _check_ollama_host returns False for unreachable host."""
        result = task_002_provider_detection._check_ollama_host("http://localhost:11434")
        assert result is False

    @patch('urllib.request.urlopen')
    def test_list_ollama_models_returns_names(self, mock_urlopen):
        """Test _list_ollama_models returns model names from API response."""
        response_data = json.dumps({
            "models": [
                {"name": "llama3.2:latest"},
                {"name": "codestral:latest"},
                {"name": "devstral:latest"},
            ]
        }).encode("utf-8")

        mock_response = Mock()
        mock_response.read.return_value = response_data
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        models = task_002_provider_detection._list_ollama_models("http://localhost:11434")

        assert "llama3.2:latest" in models
        assert "codestral:latest" in models
        assert len(models) == 3

    @patch('urllib.request.urlopen', side_effect=Exception("timeout"))
    def test_list_ollama_models_returns_empty_on_failure(self, mock_urlopen):
        """Test _list_ollama_models returns empty list on failure."""
        models = task_002_provider_detection._list_ollama_models("http://unreachable:11434")
        assert models == []

    @patch('urllib.request.urlopen')
    def test_detect_ollama_models_categorized(self, mock_urlopen):
        """Test _detect_ollama_models_categorized categorizes code vs general models."""
        response_data = json.dumps({
            "models": [
                {"name": "llama3.2:latest", "size": 4000000000},
                {"name": "devstral:latest", "size": 8000000000},
                {"name": "codestral:7b", "size": 7000000000},
            ]
        }).encode("utf-8")

        mock_response = Mock()
        mock_response.read.return_value = response_data
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = task_002_provider_detection._detect_ollama_models_categorized("http://localhost:11434")

        assert result["llama3.2:latest"]["category"] == "general"
        assert result["devstral:latest"]["category"] == "code"
        assert result["codestral:7b"]["category"] == "code"

    def test_create_secrets_file_with_aws(self, temp_dir):
        """Test _create_secrets_file writes AWS Bedrock config."""
        output_dir = temp_dir / "outputs"
        output_dir.mkdir()

        env_vars = {
            "AWS_REGION": "us-gov-west-1",
            "AWS_PROFILE": "govcloud",
            "ATOMIC_NETWORK_MODE": "cui",
        }

        task_002_provider_detection._create_secrets_file(
            output_dir, env_vars, has_aws=True, has_anthropic=False, has_ollama=False
        )

        secrets_file = output_dir / "secrets.json"
        assert secrets_file.exists()
        secrets = json.loads(secrets_file.read_text())
        assert secrets["bedrock_enabled"] is True
        assert secrets["aws_region"] == "us-gov-west-1"
        assert "us-gov" in secrets["bedrock_model"]

    def test_create_secrets_file_with_anthropic(self, temp_dir):
        """Test _create_secrets_file writes Anthropic API key."""
        output_dir = temp_dir / "outputs"
        output_dir.mkdir()

        env_vars = {
            "ANTHROPIC_API_KEY": "sk-ant-test-key",
            "ATOMIC_NETWORK_MODE": "open",
        }

        task_002_provider_detection._create_secrets_file(
            output_dir, env_vars, has_aws=False, has_anthropic=True, has_ollama=False
        )

        secrets_file = output_dir / "secrets.json"
        secrets = json.loads(secrets_file.read_text())
        assert secrets["anthropic_api_key"] == "sk-ant-test-key"

    def test_create_secrets_file_with_ollama(self, temp_dir):
        """Test _create_secrets_file writes Ollama config."""
        output_dir = temp_dir / "outputs"
        output_dir.mkdir()

        env_vars = {"ATOMIC_NETWORK_MODE": "open"}

        task_002_provider_detection._create_secrets_file(
            output_dir, env_vars, has_aws=False, has_anthropic=False, has_ollama=True
        )

        secrets_file = output_dir / "secrets.json"
        secrets = json.loads(secrets_file.read_text())
        assert secrets["ollama_enabled"] is True
        assert secrets["ollama_host"] == "localhost:11434"


# ============================================================================
# Task 003: Setup Wizard Tests
# ============================================================================

@pytest.mark.unit
class TestTask003SetupWizard:
    """Unit tests for task_003_setup_wizard."""

    def test_validate_project_name_valid(self):
        """Test _validate_project_name accepts valid names."""
        assert task_003_setup_wizard._validate_project_name("my-project") is None
        assert task_003_setup_wizard._validate_project_name("foo123") is None
        assert task_003_setup_wizard._validate_project_name("a") is None

    def test_validate_project_name_too_long(self):
        """Test _validate_project_name rejects names over 24 chars."""
        error = task_003_setup_wizard._validate_project_name("a" * 25)
        assert error is not None
        assert "24" in error

    def test_validate_project_name_invalid_chars(self):
        """Test _validate_project_name rejects uppercase and special chars."""
        error = task_003_setup_wizard._validate_project_name("My_Project")
        assert error is not None
        assert "Lowercase" in error or "lowercase" in error.lower()

    def test_validate_project_name_leading_hyphen(self):
        """Test _validate_project_name rejects leading hyphen."""
        error = task_003_setup_wizard._validate_project_name("-leading")
        assert error is not None

    def test_slugify_converts_names(self):
        """Test _slugify converts various directory names to valid slugs."""
        assert task_003_setup_wizard._slugify("My Project") == "my-project"
        assert task_003_setup_wizard._slugify("UPPERCASE") == "uppercase"
        assert task_003_setup_wizard._slugify("foo_bar_baz") == "foo-bar-baz"
        assert task_003_setup_wizard._slugify("  spaces  ") == "spaces"

    def test_slugify_truncates_to_24(self):
        """Test _slugify truncates result to 24 characters."""
        long_name = "this-is-a-very-long-project-name-that-exceeds-limit"
        result = task_003_setup_wizard._slugify(long_name)
        assert len(result) <= 24

    def test_slugify_empty_returns_default(self):
        """Test _slugify returns 'my-project' for empty/invalid input."""
        assert task_003_setup_wizard._slugify("") == "my-project"
        assert task_003_setup_wizard._slugify("---") == "my-project"

    def test_validate_config_schema_valid(self):
        """Test _validate_config_schema accepts valid config."""
        config = {
            "project": {"name": "test-project", "type": "new-component"},
            "pipeline": {"mode": "component", "human_gates": [0, 2]},
            "llm": {"primary_provider": "anthropic"},
            "sandbox": {"command_approval_mode": "cautious", "network_mode": "internet"},
            "providers": {
                "chain_priority": ["anthropic"],
                "models": {"primary": "sonnet", "fast": "haiku", "heavyweight": "opus", "gardener": "haiku"},
                "effort_level": "high",
                "thinking_budget": 10000,
            },
            "agents": {"default_tier": "sonnet"},
            "audits": {"default_profile": "standard", "failure_mode": "gate-high"},
        }
        errors = task_003_setup_wizard._validate_config_schema(config)
        assert errors == []

    def test_validate_config_schema_missing_project(self):
        """Test _validate_config_schema detects missing project section."""
        config = {"pipeline": {"mode": "component"}, "llm": {"primary_provider": "anthropic"}}
        errors = task_003_setup_wizard._validate_config_schema(config)
        assert any("project" in e.lower() for e in errors)

    def test_validate_config_schema_invalid_project_type(self):
        """Test _validate_config_schema catches invalid project type."""
        config = {
            "project": {"name": "test", "type": "invalid-type"},
            "pipeline": {"mode": "component"},
            "llm": {"primary_provider": "anthropic"},
        }
        errors = task_003_setup_wizard._validate_config_schema(config)
        assert any("project.type" in e for e in errors)

    def test_validate_config_schema_invalid_pipeline_mode(self):
        """Test _validate_config_schema catches invalid pipeline mode."""
        config = {
            "project": {"name": "test"},
            "pipeline": {"mode": "turbo"},
            "llm": {"primary_provider": "anthropic"},
        }
        errors = task_003_setup_wizard._validate_config_schema(config)
        assert any("pipeline.mode" in e for e in errors)

    def test_validate_config_schema_invalid_provider(self):
        """Test _validate_config_schema catches invalid LLM provider."""
        config = {
            "project": {"name": "test"},
            "pipeline": {"mode": "full"},
            "llm": {"primary_provider": "gpt5"},
        }
        errors = task_003_setup_wizard._validate_config_schema(config)
        assert any("primary_provider" in e for e in errors)

    def test_validate_config_schema_invalid_model_tier(self):
        """Test _validate_config_schema catches invalid model tier."""
        config = {
            "project": {"name": "test"},
            "pipeline": {"mode": "full"},
            "llm": {"primary_provider": "anthropic"},
            "providers": {
                "chain_priority": ["anthropic"],
                "models": {"primary": "turbo"},
            },
        }
        errors = task_003_setup_wizard._validate_config_schema(config)
        assert any("primary" in e and "turbo" in e for e in errors)

    def test_validate_config_schema_invalid_effort(self):
        """Test _validate_config_schema catches invalid effort level."""
        config = {
            "project": {"name": "test"},
            "pipeline": {"mode": "full"},
            "llm": {"primary_provider": "anthropic"},
            "providers": {
                "chain_priority": ["anthropic"],
                "effort_level": "turbo",
            },
        }
        errors = task_003_setup_wizard._validate_config_schema(config)
        assert any("effort_level" in e for e in errors)

    def test_resolve_markers_replaces_infer(self):
        """Test _resolve_markers replaces 'infer' and 'default' values."""
        config = {
            "project": {"name": "infer", "type": "infer"},
            "repository": {"url": "detect", "default_branch": "infer"},
            "agents": {"phase_assignments": {"phase_0": "infer", "phase_1": "default"}},
            "gardener": {"model": "infer"},
        }
        task_003_setup_wizard._resolve_markers(config)

        assert config["project"]["name"] != "infer"
        assert config["project"]["type"] == "new-component"
        assert config["repository"]["default_branch"] == "main"
        assert config["agents"]["phase_assignments"]["phase_0"] == "default"
        assert config["agents"]["phase_assignments"]["phase_1"] == "default"
        assert config["gardener"]["model"] == "haiku"

    def test_apply_auto_defaults_fills_missing_sections(self):
        """Test _apply_auto_defaults fills in required sections."""
        cfg = {
            "project": {"name": "test"},
            "llm": {"primary_provider": "anthropic", "local_fallback": False},
        }

        task_003_setup_wizard._apply_auto_defaults(cfg)

        assert "mcp" in cfg
        assert "agents" in cfg
        assert "providers" in cfg
        assert "audits" in cfg
        assert "gardener" in cfg

    def test_apply_auto_defaults_preserves_existing(self):
        """Test _apply_auto_defaults does not overwrite existing sections."""
        cfg = {
            "project": {"name": "test"},
            "llm": {"primary_provider": "anthropic"},
            "agents": {"default_tier": "opus", "source": "local", "phase_assignments": {}},
            "providers": {
                "chain_priority": ["claude-code"],
                "models": {"primary": "opus"},
            },
        }

        task_003_setup_wizard._apply_auto_defaults(cfg)

        assert cfg["agents"]["default_tier"] == "opus"
        assert cfg["providers"]["chain_priority"] == ["claude-code"]

    @patch('subprocess.run')
    def test_detect_environment_gets_git_url(self, mock_run, temp_dir):
        """Test _detect_environment detects git remote URL."""
        mock_run.side_effect = [
            Mock(returncode=0, stdout="https://github.com/user/repo.git\n"),
            Mock(returncode=0, stdout="refs/remotes/origin/main\n"),
        ]

        env_info = task_003_setup_wizard._detect_environment(temp_dir)

        assert env_info["git_url"] == "https://github.com/user/repo.git"
        assert env_info["default_branch"] == "main"

    def test_detect_environment_finds_reference_files(self, temp_dir):
        """Test _detect_environment finds standard reference files."""
        (temp_dir / "README.md").write_text("# Test")
        (temp_dir / "docs").mkdir()
        (temp_dir / "docs" / "design.md").write_text("# Design")

        with patch('subprocess.run', side_effect=Exception("no git")):
            env_info = task_003_setup_wizard._detect_environment(temp_dir)

        assert any("README.md" in f for f in env_info["reference_files"])

    def test_constants_are_defined(self):
        """Test that key constants are defined correctly."""
        assert len(task_003_setup_wizard.PROJECT_TYPES) == 9
        assert len(task_003_setup_wizard.PIPELINE_MODES) == 4
        assert "opus" in task_003_setup_wizard.MODEL_TIERS
        assert "sonnet" in task_003_setup_wizard.MODEL_TIERS
        assert "haiku" in task_003_setup_wizard.MODEL_TIERS


# ============================================================================
# Task 004: Material Scan Tests
# ============================================================================

@pytest.mark.unit
class TestTask004MaterialScan:
    """Unit tests for task_004_material_scan."""

    def test_execute_uat_mode_returns_true(self, temp_dir):
        """Test execute in UAT mode returns True."""
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True)

        # Create project-config.json required by _record_reference_info
        (output_dir / "project-config.json").write_text(json.dumps({"project": {"name": "test"}}))

        result = task_004_material_scan.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        assert result is True

    def test_execute_uat_mode_creates_manifest(self, temp_dir):
        """Test execute creates material-manifest.json in UAT mode."""
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True)
        (output_dir / "project-config.json").write_text(json.dumps({"project": {"name": "test"}}))

        task_004_material_scan.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        manifest_file = output_dir / "material-manifest.json"
        assert manifest_file.exists()
        manifest = json.loads(manifest_file.read_text())
        assert "scanned_at" in manifest
        assert "summary" in manifest

    def test_detect_key_files_finds_readme(self, temp_dir):
        """Test _detect_key_files detects README.md."""
        (temp_dir / "README.md").write_text("# Test Project")

        manifest = {"key_files": [], "project_indicators": []}
        task_004_material_scan._detect_key_files(manifest, temp_dir)

        assert "README.md" in manifest["key_files"]

    def test_detect_key_files_finds_package_json(self, temp_dir):
        """Test _detect_key_files detects package.json."""
        (temp_dir / "package.json").write_text('{"name": "test"}')

        manifest = {"key_files": [], "project_indicators": []}
        task_004_material_scan._detect_key_files(manifest, temp_dir)

        assert "package.json" in manifest["key_files"]

    def test_detect_key_files_finds_python_files(self, temp_dir):
        """Test _detect_key_files detects Python project files."""
        (temp_dir / "pyproject.toml").write_text("[project]\nname='test'")

        manifest = {"key_files": [], "project_indicators": []}
        task_004_material_scan._detect_key_files(manifest, temp_dir)

        assert "pyproject.toml" in manifest["key_files"]

    def test_detect_key_files_detects_docker(self, temp_dir):
        """Test _detect_key_files detects Docker files."""
        (temp_dir / "Dockerfile").write_text("FROM python:3.11")
        (temp_dir / "docker-compose.yml").write_text("version: '3'")

        manifest = {"key_files": [], "project_indicators": []}
        task_004_material_scan._detect_key_files(manifest, temp_dir)

        assert "Dockerfile" in manifest["key_files"]
        assert "docker-compose.yml" in manifest["key_files"]

    def test_detect_stack_finds_python(self, temp_dir):
        """Test _detect_stack detects Python language."""
        (temp_dir / "requirements.txt").write_text("flask==2.0\nfastapi==0.100")

        manifest = {"detected_stack": {}}
        task_004_material_scan._detect_stack(manifest, temp_dir)

        assert "Python" in manifest["detected_stack"]["languages"]
        assert "Flask" in manifest["detected_stack"]["frameworks"]
        assert "FastAPI" in manifest["detected_stack"]["frameworks"]

    def test_detect_stack_finds_typescript(self, temp_dir):
        """Test _detect_stack detects TypeScript."""
        (temp_dir / "package.json").write_text('{"dependencies": {"react": "^18"}}')
        (temp_dir / "tsconfig.json").write_text("{}")

        manifest = {"detected_stack": {}}
        task_004_material_scan._detect_stack(manifest, temp_dir)

        assert "TypeScript" in manifest["detected_stack"]["languages"]
        assert "React" in manifest["detected_stack"]["frameworks"]

    def test_find_files_respects_max_depth(self, temp_dir):
        """Test _find_files respects max_depth parameter."""
        # Create files at various depths
        (temp_dir / "top.md").write_text("top")
        deep = temp_dir / "a" / "b" / "c" / "d" / "e"
        deep.mkdir(parents=True)
        (deep / "deep.md").write_text("deep")

        files = task_004_material_scan._find_files(temp_dir, ["**/*.md"], max_depth=2)

        # top.md (depth 1) should be found, deep.md (depth 5) should not
        names = [f.name for f in files]
        assert "top.md" in names
        assert "deep.md" not in names

    def test_find_files_excludes_node_modules(self, temp_dir):
        """Test _find_files excludes node_modules."""
        (temp_dir / "real.md").write_text("real")
        nm = temp_dir / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        (nm / "readme.md").write_text("package readme")

        files = task_004_material_scan._find_files(temp_dir, ["**/*.md"], max_depth=4)

        names = [f.name for f in files]
        assert "real.md" in names
        # node_modules should be excluded
        assert all("node_modules" not in str(f) for f in files)

    def test_find_files_respects_max_files(self, temp_dir):
        """Test _find_files limits result count."""
        for i in range(20):
            (temp_dir / f"file_{i}.md").write_text(f"file {i}")

        files = task_004_material_scan._find_files(temp_dir, ["**/*.md"], max_files=5)

        assert len(files) <= 5

    def test_count_lines_counts_correctly(self, temp_dir):
        """Test _count_lines returns correct line count."""
        f1 = temp_dir / "a.txt"
        f1.write_text("line1\nline2\nline3\n")
        f2 = temp_dir / "b.txt"
        f2.write_text("one\ntwo\n")

        total = task_004_material_scan._count_lines([f1, f2])

        assert total == 5  # 3 + 2

    def test_calculate_totals(self):
        """Test _calculate_totals sums all categories."""
        manifest = {
            "summary": {
                "documentation": {"count": 5, "lines": 200},
                "configuration": {"count": 3},
                "source_code": {"count": 20, "lines": 1500},
                "tests": {"count": 8},
            }
        }

        task_004_material_scan._calculate_totals(manifest)

        assert manifest["summary"]["total"]["files"] == 36
        assert manifest["summary"]["total"]["lines"] == 1700

    def test_scan_for_reference_materials_finds_files(self, temp_dir):
        """Test _scan_for_reference_materials finds reference files."""
        atomic_root = temp_dir / "atomic-claude"
        atomic_root.mkdir()
        project_root = temp_dir

        # Create reference material
        (temp_dir / "README.md").write_text("# Project README")
        docs_dir = temp_dir / "docs"
        docs_dir.mkdir()
        (docs_dir / "design.md").write_text("# Design")

        found = task_004_material_scan._scan_for_reference_materials(project_root, atomic_root)

        rel_paths = [rel for _, rel in found]
        assert any("README.md" in p for p in rel_paths)

    def test_scan_for_reference_materials_skips_atomic_dir(self, temp_dir):
        """Test _scan_for_reference_materials skips the atomic-claude directory."""
        atomic_root = temp_dir / "atomic-claude"
        atomic_root.mkdir()
        (atomic_root / "internal.md").write_text("# Internal")
        project_root = temp_dir

        found = task_004_material_scan._scan_for_reference_materials(project_root, atomic_root)

        rel_paths = [rel for _, rel in found]
        assert not any("atomic-claude" in p for p in rel_paths)

    def test_collect_dir_files_recursive(self, temp_dir):
        """Test _collect_dir_files scans recursively."""
        sub = temp_dir / "subdir"
        sub.mkdir()
        (sub / "doc.md").write_text("# Doc")
        (sub / "data.json").write_text("{}")
        deeper = sub / "nested"
        deeper.mkdir()
        (deeper / "spec.md").write_text("# Spec")

        found = task_004_material_scan._collect_dir_files(temp_dir)

        names = [Path(display).name for _, display in found]
        assert "doc.md" in names
        assert "spec.md" in names

    def test_collect_dir_files_skips_git(self, temp_dir):
        """Test _collect_dir_files skips .git directories."""
        git_dir = temp_dir / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("[core]")
        (temp_dir / "real.md").write_text("real")

        found = task_004_material_scan._collect_dir_files(temp_dir)

        # .git contents should not appear
        assert all(".git" not in str(f) for f, _ in found)


# ============================================================================
# Task 005: Repository & System Setup Tests
# ============================================================================

@pytest.mark.unit
class TestTask005RepositorySetup:
    """Unit tests for task_005_repository_setup."""

    def _setup_task_005_env(self, temp_dir):
        """Helper: create the minimum files and directories for execute()."""
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True)

        # project-config.json (required for _save_configuration)
        config_file = output_dir / "project-config.json"
        config_file.write_text(json.dumps({"project": {"name": "test"}}))

        # env-validation.json (written by execute, but _save_configuration reads it)
        report_file = output_dir / "env-validation.json"
        report_file.write_text(json.dumps({"checks": [], "capabilities": {}}))

        # Create agent-manifest.json
        agents_dir = temp_dir / "agents"
        agents_dir.mkdir(parents=True)
        manifest = {
            "version": "3.0.0",
            "agents": [
                {"name": "test-agent", "category": "setup"},
                {"name": "test-agent-2", "category": "discovery"},
            ]
        }
        (agents_dir / "agent-manifest.json").write_text(json.dumps(manifest))

        # Create audits structure
        audits_dir = temp_dir / "audits"
        audits_dir.mkdir(parents=True)
        (audits_dir / "AUDIT-MENU.md").write_text("# Audits\n")
        (audits_dir / "AUDIT-INVENTORY.csv").write_text("id,name\n1,test\n2,test2\n")
        categories_dir = audits_dir / "categories"
        categories_dir.mkdir()
        (categories_dir / "security.md").write_text("# Security")

        # Create skills structure
        skills_dir = temp_dir / "skills"
        skills_dir.mkdir(parents=True)

        return output_dir

    @patch('phases.phase_00_setup.tasks.task_005_repository_setup._assess_network')
    @patch('phases.phase_00_setup.tasks.task_005_repository_setup._assess_storage')
    @patch('phases.phase_00_setup.tasks.task_005_repository_setup._assess_memory')
    @patch('phases.phase_00_setup.tasks.task_005_repository_setup._assess_gpu')
    @patch('phases.phase_00_setup.tasks.task_005_repository_setup._assess_cpu')
    @patch('phases.phase_00_setup.tasks.task_005_repository_setup._validate_git')
    def test_execute_uat_mode_returns_true(
        self, mock_git, mock_cpu, mock_gpu, mock_mem, mock_storage, mock_net, temp_dir
    ):
        """Test execute in UAT mode returns True."""
        output_dir = self._setup_task_005_env(temp_dir)

        result = task_005_repository_setup.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        assert result is True

    def test_verify_agents_reads_manifest(self, temp_dir):
        """Test _verify_agents reads agent manifest and counts agents."""
        agents_dir = temp_dir / "agents"
        agents_dir.mkdir(parents=True)
        manifest_file = agents_dir / "agent-manifest.json"
        manifest_data = {
            "version": "3.0.0",
            "agents": [
                {"name": "agent-1", "category": "setup"},
                {"name": "agent-2", "category": "setup"},
                {"name": "agent-3", "category": "discovery"},
            ]
        }
        manifest_file.write_text(json.dumps(manifest_data))

        total_agents, total_categories = task_005_repository_setup._verify_agents(
            agents_dir, manifest_file
        )

        assert total_agents == 3
        assert total_categories == 2

    def test_verify_agents_missing_manifest(self, temp_dir):
        """Test _verify_agents handles missing manifest gracefully."""
        agents_dir = temp_dir / "agents"
        agents_dir.mkdir(parents=True)
        manifest_file = agents_dir / "agent-manifest.json"

        total_agents, total_categories = task_005_repository_setup._verify_agents(
            agents_dir, manifest_file
        )

        assert total_agents == 0
        assert total_categories == 0

    def test_verify_audits_counts_correctly(self, temp_dir):
        """Test _verify_audits counts audits from inventory CSV."""
        audits_dir = temp_dir / "audits"
        audits_dir.mkdir(parents=True)
        (audits_dir / "AUDIT-MENU.md").write_text("# Audit Menu")
        (audits_dir / "AUDIT-INVENTORY.csv").write_text(
            "id,name,category\n1,test-1,security\n2,test-2,quality\n3,test-3,security\n"
        )
        categories_dir = audits_dir / "categories"
        categories_dir.mkdir()
        (categories_dir / "security.md").write_text("# Security")
        (categories_dir / "quality.md").write_text("# Quality")

        audit_count = task_005_repository_setup._verify_audits(
            audits_dir, audits_dir / "AUDIT-MENU.md"
        )

        assert audit_count == 3

    def test_verify_audits_missing_menu(self, temp_dir):
        """Test _verify_audits returns 0 when menu is missing."""
        audits_dir = temp_dir / "audits"
        audits_dir.mkdir(parents=True)

        audit_count = task_005_repository_setup._verify_audits(
            audits_dir, audits_dir / "AUDIT-MENU.md"
        )

        assert audit_count == 0

    def test_verify_skills_counts_sources(self, temp_dir):
        """Test _verify_skills counts skills from all sources."""
        skills_dir = temp_dir / "skills"
        skills_dir.mkdir()

        # Create tactical skills
        tactical = skills_dir / "tactical" / "category1"
        tactical.mkdir(parents=True)
        (tactical / "skill_a").mkdir()
        (tactical / "skill_b").mkdir()

        # Create superpowers
        sp = skills_dir / "community" / "superpowers" / "skills"
        sp.mkdir(parents=True)
        (sp / "power1").mkdir()

        # Create trailofbits
        tob = skills_dir / "community" / "trailofbits" / "plugins"
        tob.mkdir(parents=True)
        (tob / "plugin1").mkdir()
        (tob / "plugin2").mkdir()

        total, sources = task_005_repository_setup._verify_skills(skills_dir)

        assert total == 5
        assert sources["tactical"] == 2
        assert sources["superpowers"] == 1
        assert sources["trailofbits"] == 2

    def test_verify_skills_empty(self, temp_dir):
        """Test _verify_skills handles empty skills directory."""
        skills_dir = temp_dir / "skills"
        skills_dir.mkdir()

        total, sources = task_005_repository_setup._verify_skills(skills_dir)

        assert total == 0

    def test_configure_routing_with_ollama(self):
        """Test _configure_routing returns hybrid config when ollama is configured."""
        routing = task_005_repository_setup._configure_routing(ollama_configured=True)

        assert routing["critical"] == "primary"
        assert routing["bulk"] == "ollama"
        assert routing["background"] == "ollama"

    def test_configure_routing_without_ollama(self):
        """Test _configure_routing returns primary-only config without ollama."""
        routing = task_005_repository_setup._configure_routing(ollama_configured=False)

        assert routing["critical"] == "primary"
        assert routing["bulk"] == "primary"
        assert routing["background"] == "primary"

    def test_detect_os_returns_valid_type(self):
        """Test _detect_os returns a known OS type."""
        os_type = task_005_repository_setup._detect_os()
        assert os_type in ("macos", "linux", "windows", "unknown")

    def test_add_check_appends_to_report(self, temp_dir):
        """Test _add_check adds check entry to report file."""
        report_file = temp_dir / "report.json"
        report_file.write_text(json.dumps({"checks": [], "capabilities": {}}))

        task_005_repository_setup._add_check(
            report_file, "test_check", "pass", "required", "1.0"
        )

        report = json.loads(report_file.read_text())
        assert len(report["checks"]) == 1
        assert report["checks"][0]["name"] == "test_check"
        assert report["checks"][0]["status"] == "pass"

    def test_update_report_capability(self, temp_dir):
        """Test _update_report_capability writes capability data."""
        report_file = temp_dir / "report.json"
        report_file.write_text(json.dumps({"checks": [], "capabilities": {}}))

        task_005_repository_setup._update_report_capability(
            report_file, "cpu", {"cores": 8, "model": "Test CPU"}
        )

        report = json.loads(report_file.read_text())
        assert report["capabilities"]["cpu"]["cores"] == 8

    @patch('subprocess.run')
    def test_validate_git_records_user(self, mock_run, temp_dir):
        """Test _validate_git records git user info."""
        mock_run.side_effect = [
            Mock(returncode=0, stdout="Test User\n"),
            Mock(returncode=0, stdout="test@example.com\n"),
            Mock(returncode=0, stdout=".git\n"),
            Mock(returncode=0, stdout="main\n"),
        ]

        report_file = temp_dir / "report.json"
        report_file.write_text(json.dumps({"checks": [], "capabilities": {}}))

        task_005_repository_setup.CHECKS_PASS = 0
        task_005_repository_setup.CHECKS_WARN = 0
        task_005_repository_setup.CHECKS_FAIL = 0

        task_005_repository_setup._validate_git(report_file)

        assert task_005_repository_setup.CHECKS_PASS >= 1

    @patch('subprocess.run')
    def test_validate_git_warns_on_missing_user(self, mock_run, temp_dir):
        """Test _validate_git warns when git user is not configured."""
        mock_run.side_effect = [
            Mock(returncode=0, stdout=""),  # empty user.name
            Mock(returncode=0, stdout=""),  # empty user.email
            Mock(returncode=0, stdout=".git\n"),
            Mock(returncode=0, stdout="main\n"),
        ]

        report_file = temp_dir / "report.json"
        report_file.write_text(json.dumps({"checks": [], "capabilities": {}}))

        task_005_repository_setup.CHECKS_PASS = 0
        task_005_repository_setup.CHECKS_WARN = 0
        task_005_repository_setup.CHECKS_FAIL = 0

        task_005_repository_setup._validate_git(report_file)

        assert task_005_repository_setup.CHECKS_WARN >= 1
