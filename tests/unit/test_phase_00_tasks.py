"""
Unit Tests for Phase 0 (Setup) Task Modules

Tests all 9 Phase 0 tasks with comprehensive coverage:
- Task 001: Mode Selection
- Task 002: Config Collection
- Task 003: Config Review
- Task 004: API Keys
- Task 005: Material Scan
- Task 006: Reference Materials
- Task 007: Environment Setup
- Task 008: Repository Setup
- Task 009: Environment Check
"""

import json
import os
import pytest
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime

# Import task modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phases.phase_00_setup.tasks import task_001_mode_selection
from phases.phase_00_setup.tasks import task_002_config_collection
from phases.phase_00_setup.tasks import task_003_config_review
from phases.phase_00_setup.tasks import task_004_api_keys
from phases.phase_00_setup.tasks import task_005_material_scan
from phases.phase_00_setup.tasks import task_006_reference_materials
from phases.phase_00_setup.tasks import task_007_environment_setup
from phases.phase_00_setup.tasks import task_008_repository_setup
from phases.phase_00_setup.tasks import task_009_environment_check


# ============================================================================
# Task 001: Mode Selection Tests
# ============================================================================

class TestTask001ModeSelection:
    """Unit tests for task_001_mode_selection."""

    def test_execute_uat_mode_success(self, temp_dir):
        """Test execute in UAT mode returns True."""
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True)

        result = task_001_mode_selection.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        assert result is True

    def test_execute_uat_mode_creates_output_files(self, temp_dir):
        """Test execute creates required output files in UAT mode."""
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True)

        task_001_mode_selection.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        # Check secrets.json created
        secrets_file = output_dir / "secrets.json"
        assert secrets_file.exists()

        secrets_data = json.loads(secrets_file.read_text())
        assert secrets_data.get("uat_mode") is True

    def test_execute_uat_mode_creates_setup_template(self, temp_dir):
        """Test execute creates setup.md template in UAT mode."""
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True)

        project_root = temp_dir.parent
        init_dir = project_root / "initialization"

        task_001_mode_selection.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        setup_file = init_dir / "setup.md"
        assert setup_file.exists()
        assert "Project Setup" in setup_file.read_text()

    def test_ensure_setup_template_creates_file(self, temp_dir):
        """Test helper function creates setup template."""
        target_file = temp_dir / "setup.md"

        result = task_001_mode_selection.ensure_setup_template(
            target_file=target_file,
            atomic_root=temp_dir
        )

        assert result is True
        assert target_file.exists()
        content = target_file.read_text()
        assert "**name**:" in content
        assert "**description**:" in content

    def test_validate_env_file_with_aws_credentials(self, temp_dir, monkeypatch):
        """Test env file validation with valid AWS credentials."""
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True)

        # Mock AWS credentials
        monkeypatch.setenv("AWS_PROFILE", "test-profile")
        monkeypatch.setenv("AWS_REGION", "us-west-2")

        result = task_001_mode_selection.validate_env_file(
            atomic_root=temp_dir,
            output_dir=output_dir
        )

        assert result is True
        assert (output_dir / "secrets.json").exists()

    def test_validate_env_file_with_anthropic_key(self, temp_dir, monkeypatch):
        """Test env file validation with Anthropic API key."""
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True)

        # Mock Anthropic API key
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")

        result = task_001_mode_selection.validate_env_file(
            atomic_root=temp_dir,
            output_dir=output_dir
        )

        assert result is True

    def test_validate_env_file_no_credentials(self, temp_dir):
        """Test env file validation with no credentials fails."""
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True)

        # Clear environment
        for key in ['AWS_PROFILE', 'AWS_ACCESS_KEY_ID', 'ANTHROPIC_API_KEY']:
            os.environ.pop(key, None)

        result = task_001_mode_selection.validate_env_file(
            atomic_root=temp_dir,
            output_dir=output_dir
        )

        assert result is False

    def test_create_secrets_file_with_bedrock(self, temp_dir):
        """Test secrets file creation with AWS Bedrock config."""
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True)

        env_vars = {
            "AWS_REGION": "us-gov-west-1",
            "AWS_PROFILE": "govcloud"
        }

        result = task_001_mode_selection.create_secrets_file(
            output_dir=output_dir,
            env_vars=env_vars,
            has_aws=True,
            has_anthropic=False,
            has_ollama=False
        )

        assert result is True
        secrets_file = output_dir / "secrets.json"
        assert secrets_file.exists()

        secrets = json.loads(secrets_file.read_text())
        assert secrets["bedrock_enabled"] is True
        assert secrets["aws_region"] == "us-gov-west-1"


# ============================================================================
# Task 002: Config Collection Tests
# ============================================================================

class TestTask002ConfigCollection:
    """Unit tests for task_002_config_collection."""

    def test_execute_uat_mode_success(self, temp_dir):
        """Test execute in UAT mode returns True."""
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True)

        result = task_002_config_collection.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        assert result is True

    def test_execute_uat_mode_creates_minimal_config(self, temp_dir):
        """Test execute creates minimal config in UAT mode."""
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True)

        task_002_config_collection.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        extracted_file = output_dir / "extracted-config.json"
        assert extracted_file.exists()

        config = json.loads(extracted_file.read_text())
        assert config["project"]["name"] == "uat-test-project"
        assert "repository" in config
        assert "sandbox" in config

    def test_validate_setup_format_valid(self, temp_dir):
        """Test setup format validation with valid file."""
        setup_file = temp_dir / "setup.md"
        setup_file.write_text("""
# Project Setup

**name**: test-project
**type**: new-component
**description**: Test description
        """)

        result = task_002_config_collection._validate_setup_format(setup_file)
        assert result is True

    def test_validate_setup_format_invalid(self, temp_dir):
        """Test setup format validation with invalid file."""
        setup_file = temp_dir / "setup.md"
        setup_file.write_text("# Just a regular markdown file\nNo configuration here.")

        result = task_002_config_collection._validate_setup_format(setup_file)
        assert result is False

    def test_read_setup_content_truncation(self, temp_dir):
        """Test setup content is truncated at 500 lines."""
        setup_file = temp_dir / "setup.md"
        content = "\n".join([f"Line {i}" for i in range(1000)])
        setup_file.write_text(content)

        result = task_002_config_collection._read_setup_content(setup_file)

        assert "[TRUNCATED:" in result
        assert result.count("\n") <= 502  # 500 lines + truncation message

    def test_read_optional_file_exists(self, temp_dir):
        """Test reading optional file that exists."""
        file_path = temp_dir / "llm-preferences.md"
        file_path.write_text("# LLM Preferences\n\nUse Claude Sonnet")

        result = task_002_config_collection._read_optional_file(file_path)

        assert "LLM Preferences" in result

    def test_read_optional_file_missing(self, temp_dir):
        """Test reading optional file that doesn't exist."""
        file_path = temp_dir / "missing.md"

        result = task_002_config_collection._read_optional_file(file_path)

        assert result == ""

    @patch('subprocess.run')
    def test_detect_git_repo_success(self, mock_run):
        """Test git repository detection success."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="https://github.com/user/repo.git\n"
        )

        result = task_002_config_collection._detect_git_repo()

        assert result == "https://github.com/user/repo.git"

    @patch('subprocess.run')
    def test_detect_git_repo_failure(self, mock_run):
        """Test git repository detection failure."""
        mock_run.return_value = Mock(returncode=1, stdout="")

        result = task_002_config_collection._detect_git_repo()

        assert result == ""

    def test_clean_and_validate_json_with_fences(self, temp_dir):
        """Test JSON cleaning removes markdown fences."""
        json_file = temp_dir / "test.json"
        json_file.write_text("""```json
{
  "test": "value",
  "number": 123
}
```""")

        result = task_002_config_collection._clean_and_validate_json(json_file)

        assert result is True
        cleaned = json.loads(json_file.read_text())
        assert cleaned["test"] == "value"
        assert cleaned["number"] == 123


# ============================================================================
# Task 003: Config Review Tests
# ============================================================================

class TestTask003ConfigReview:
    """Unit tests for task_003_config_review."""

    def test_execute_uat_mode_success(self, temp_dir):
        """Test execute in UAT mode returns True."""
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True)

        config_file = output_dir / "project-config.json"
        config_file.write_text(json.dumps({
            "extracted": {
                "project": {"name": "test", "description": "Test project"}
            }
        }))

        result = task_003_config_review.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        assert result is True

    def test_execute_uat_mode_approves_config(self, temp_dir):
        """Test UAT mode auto-approves configuration."""
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True)

        config_file = output_dir / "project-config.json"
        config_data = {
            "extracted": {
                "project": {"name": "test", "description": "Test project"}
            }
        }
        config_file.write_text(json.dumps(config_data))

        task_003_config_review.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        # Check config was approved
        config = json.loads(config_file.read_text())
        assert config.get("config_approved") is True

    def test_display_config_shows_all_sections(self, temp_dir, capsys):
        """Test config display shows all configuration sections."""
        config_file = temp_dir / "config.json"
        config_data = {
            "extracted": {
                "project": {
                    "name": "test-project",
                    "description": "A test project",
                    "type": "new-component"
                },
                "repository": {
                    "url": "https://github.com/test/repo"
                }
            }
        }
        config_file.write_text(json.dumps(config_data))

        task_003_config_review._display_config(config_file)

        captured = capsys.readouterr()
        assert "PROJECT" in captured.out
        assert "test-project" in captured.out
        assert "REPOSITORY" in captured.out

    def test_approve_config_flattens_extracted(self, temp_dir):
        """Test config approval flattens extracted configuration."""
        config_file = temp_dir / "config.json"
        config_data = {
            "extracted": {
                "project": {"name": "test"},
                "repository": {"url": "https://example.com"}
            }
        }
        config_file.write_text(json.dumps(config_data))

        task_003_config_review._approve_config(config_file)

        config = json.loads(config_file.read_text())
        assert config.get("config_approved") is True
        assert "project" in config
        assert config["project"]["name"] == "test"

    def test_show_info_box_displays(self, capsys):
        """Test info box displays instructions."""
        task_003_config_review._show_info_box()

        captured = capsys.readouterr()
        assert "Review" in captured.out
        assert "approve" in captured.out or "edit" in captured.out


# ============================================================================
# Task 004: API Keys Tests
# ============================================================================

class TestTask004ApiKeys:
    """Unit tests for task_004_api_keys."""

    def test_execute_uat_mode_success(self, temp_dir):
        """Test execute in UAT mode returns True."""
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True)

        result = task_004_api_keys.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        assert result is True

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"})
    def test_check_anthropic_key_found(self):
        """Test Anthropic API key detection."""
        result = task_004_api_keys._check_anthropic_key()

        assert result is True

    def test_check_anthropic_key_missing(self):
        """Test Anthropic API key detection when missing."""
        # Clear environment
        os.environ.pop("ANTHROPIC_API_KEY", None)

        result = task_004_api_keys._check_anthropic_key()

        assert result is False

    @patch.dict(os.environ, {"AWS_PROFILE": "test", "AWS_REGION": "us-west-2"})
    def test_check_aws_credentials_found(self):
        """Test AWS credentials detection."""
        result = task_004_api_keys._check_aws_credentials()

        assert result is True

    @patch('subprocess.run')
    def test_check_ollama_running(self, mock_run):
        """Test Ollama detection when running."""
        mock_run.return_value = Mock(returncode=0)

        result = task_004_api_keys._check_ollama()

        assert result is True

    @patch('subprocess.run')
    def test_check_ollama_not_running(self, mock_run):
        """Test Ollama detection when not running."""
        mock_run.side_effect = Exception("Connection refused")

        result = task_004_api_keys._check_ollama()

        assert result is False


# ============================================================================
# Task 005: Material Scan Tests
# ============================================================================

class TestTask005MaterialScan:
    """Unit tests for task_005_material_scan."""

    def test_execute_uat_mode_success(self, temp_dir):
        """Test execute in UAT mode returns True."""
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True)

        result = task_005_material_scan.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        assert result is True

    def test_scan_directory_finds_markdown(self, temp_dir):
        """Test directory scan finds markdown files."""
        # Create test files
        (temp_dir / "README.md").write_text("# Test")
        (temp_dir / "docs").mkdir()
        (temp_dir / "docs" / "guide.md").write_text("# Guide")

        materials = task_005_material_scan._scan_directory(temp_dir)

        assert len(materials) >= 2
        assert any("README.md" in m["path"] for m in materials)

    def test_scan_directory_ignores_hidden(self, temp_dir):
        """Test directory scan ignores hidden directories."""
        (temp_dir / ".git").mkdir()
        (temp_dir / ".git" / "config").write_text("test")
        (temp_dir / "visible.md").write_text("# Visible")

        materials = task_005_material_scan._scan_directory(temp_dir)

        assert all(".git" not in m["path"] for m in materials)

    def test_classify_material_identifies_spec(self, temp_dir):
        """Test material classification identifies specs."""
        spec_file = temp_dir / "SPEC.md"
        spec_file.write_text("# Specification")

        classification = task_005_material_scan._classify_material(spec_file)

        assert classification in ["spec", "specification", "technical"]

    def test_scan_respects_file_types(self, temp_dir):
        """Test scan finds supported file types."""
        (temp_dir / "doc.md").write_text("# Markdown")
        (temp_dir / "data.json").write_text('{"key": "value"}')
        (temp_dir / "config.yaml").write_text("key: value")
        (temp_dir / "script.py").write_text("# Should be ignored")

        materials = task_005_material_scan._scan_directory(temp_dir)

        # Should find md, json, yaml but not py
        paths = [m["path"] for m in materials]
        assert any("doc.md" in p for p in paths)
        assert any("data.json" in p for p in paths)
        assert any("config.yaml" in p for p in paths)


# ============================================================================
# Task 006: Reference Materials Tests
# ============================================================================

class TestTask006ReferenceMaterials:
    """Unit tests for task_006_reference_materials."""

    def test_execute_uat_mode_success(self, temp_dir):
        """Test execute in UAT mode returns True."""
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True)

        result = task_006_reference_materials.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        assert result is True

    def test_organize_materials_creates_structure(self, temp_dir):
        """Test material organization creates directory structure."""
        materials = [
            {"path": str(temp_dir / "README.md"), "type": "documentation"},
            {"path": str(temp_dir / "SPEC.md"), "type": "specification"}
        ]

        result = task_006_reference_materials._organize_materials(
            temp_dir,
            materials
        )

        assert result is True
        assert (temp_dir / "docs").exists()

    def test_copy_material_preserves_content(self, temp_dir):
        """Test material copying preserves content."""
        source = temp_dir / "source.md"
        source.write_text("# Original Content")

        dest_dir = temp_dir / "dest"
        dest_dir.mkdir()

        task_006_reference_materials._copy_material(source, dest_dir)

        dest = dest_dir / "source.md"
        assert dest.exists()
        assert dest.read_text() == "# Original Content"


# ============================================================================
# Task 007: Environment Setup Tests
# ============================================================================

class TestTask007EnvironmentSetup:
    """Unit tests for task_007_environment_setup."""

    def test_execute_uat_mode_success(self, temp_dir):
        """Test execute in UAT mode returns True."""
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True)

        result = task_007_environment_setup.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        assert result is True

    def test_create_directory_structure(self, temp_dir):
        """Test directory structure creation."""
        task_007_environment_setup._create_directory_structure(temp_dir)

        # Check standard directories
        assert (temp_dir / ".outputs").exists()
        assert (temp_dir / ".state").exists()
        assert (temp_dir / ".logs").exists()
        assert (temp_dir / "docs").exists()

    def test_create_gitignore(self, temp_dir):
        """Test .gitignore creation."""
        task_007_environment_setup._create_gitignore(temp_dir)

        gitignore = temp_dir / ".gitignore"
        assert gitignore.exists()

        content = gitignore.read_text()
        assert ".outputs" in content
        assert ".state" in content
        assert ".logs" in content

    def test_initialize_state_directory(self, temp_dir):
        """Test state directory initialization."""
        state_dir = temp_dir / ".state"

        task_007_environment_setup._initialize_state_directory(state_dir)

        assert state_dir.exists()
        assert (state_dir / "task-state.json").exists()


# ============================================================================
# Task 008: Repository Setup Tests
# ============================================================================

class TestTask008RepositorySetup:
    """Unit tests for task_008_repository_setup."""

    def test_execute_uat_mode_success(self, temp_dir):
        """Test execute in UAT mode returns True."""
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True)

        result = task_008_repository_setup.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        assert result is True

    @patch('subprocess.run')
    def test_check_git_installed(self, mock_run):
        """Test git installation check."""
        mock_run.return_value = Mock(returncode=0, stdout="git version 2.39.0")

        result = task_008_repository_setup._check_git_installed()

        assert result is True

    @patch('subprocess.run')
    def test_initialize_git_repo(self, mock_run, temp_dir):
        """Test git repository initialization."""
        mock_run.return_value = Mock(returncode=0)

        result = task_008_repository_setup._initialize_git_repo(temp_dir)

        assert result is True
        mock_run.assert_called()

    @patch('subprocess.run')
    def test_configure_git_repo(self, mock_run, temp_dir):
        """Test git repository configuration."""
        mock_run.return_value = Mock(returncode=0)

        config = {
            "repository": {
                "default_branch": "main",
                "commit_format": "conventional"
            }
        }

        result = task_008_repository_setup._configure_git_repo(temp_dir, config)

        assert result is True


# ============================================================================
# Task 009: Environment Check Tests
# ============================================================================

class TestTask009EnvironmentCheck:
    """Unit tests for task_009_environment_check."""

    def test_execute_uat_mode_success(self, temp_dir):
        """Test execute in UAT mode returns True."""
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True)

        # Create required files
        (output_dir / "project-config.json").write_text(
            json.dumps({"project": {"name": "test"}})
        )
        (output_dir / "secrets.json").write_text(
            json.dumps({"memory_enabled": True})
        )

        result = task_009_environment_check.execute(
            atomic_root=temp_dir,
            output_dir=output_dir,
            uat_mode=True
        )

        assert result is True

    def test_check_required_files(self, temp_dir):
        """Test required file checking."""
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True)

        # Create required files
        (output_dir / "project-config.json").write_text("{}")
        (output_dir / "secrets.json").write_text("{}")

        result = task_009_environment_check._check_required_files(output_dir)

        assert result is True

    def test_check_required_files_missing(self, temp_dir):
        """Test required file checking with missing files."""
        output_dir = temp_dir / ".outputs" / "0-setup"
        output_dir.mkdir(parents=True)

        result = task_009_environment_check._check_required_files(output_dir)

        assert result is False

    def test_validate_directory_structure(self, temp_dir):
        """Test directory structure validation."""
        # Create expected directories
        (temp_dir / ".outputs").mkdir()
        (temp_dir / ".state").mkdir()
        (temp_dir / ".logs").mkdir()

        result = task_009_environment_check._validate_directory_structure(temp_dir)

        assert result is True

    def test_validate_configuration(self, temp_dir):
        """Test configuration validation."""
        config_file = temp_dir / "project-config.json"
        config_data = {
            "project": {
                "name": "test-project",
                "type": "new-component"
            },
            "config_approved": True
        }
        config_file.write_text(json.dumps(config_data))

        result = task_009_environment_check._validate_configuration(config_file)

        assert result is True

    def test_validate_api_credentials(self, temp_dir, monkeypatch):
        """Test API credentials validation."""
        secrets_file = temp_dir / "secrets.json"
        secrets_file.write_text(json.dumps({
            "anthropic_api_key": "sk-ant-test"
        }))

        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        result = task_009_environment_check._validate_api_credentials(secrets_file)

        assert result is True
