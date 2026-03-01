"""Tests for sandbox security configuration."""

import json

import pytest

from core.sandbox import SandboxConfig, SandboxRule, generate_sandbox_config


@pytest.mark.unit
class TestSandboxRule:
    """Tests for SandboxRule dataclass."""

    def test_sandbox_rule_to_dict_with_pattern(self):
        """Tool + pattern produces both keys."""
        rule = SandboxRule(tool="Bash", pattern="pytest *")
        assert rule.to_dict() == {"tool": "Bash", "pattern": "pytest *"}

    def test_sandbox_rule_to_dict_without_pattern(self):
        """Tool only omits pattern key."""
        rule = SandboxRule(tool="Read")
        assert rule.to_dict() == {"tool": "Read"}


@pytest.mark.unit
class TestSandboxConfigDefaults:
    """Tests for default allow/deny rule generation."""

    def test_default_allow_rules(self, tmp_path):
        """Verify Read, Write, Edit, and Bash rules are present."""
        cfg = SandboxConfig(project_root=tmp_path)
        rules = cfg._default_allow_rules()
        tools = [r.tool for r in rules]
        assert "Read" in tools
        assert "Write" in tools
        assert "Edit" in tools
        assert "Bash" in tools

    def test_default_deny_rules_no_network(self, tmp_path):
        """curl and wget denied when allow_network=False."""
        cfg = SandboxConfig(project_root=tmp_path, allow_network=False)
        rules = cfg._default_deny_rules()
        patterns = [r.pattern for r in rules]
        assert "curl *" in patterns
        assert "wget *" in patterns

    def test_default_deny_rules_with_network(self, tmp_path):
        """curl and wget NOT denied when allow_network=True."""
        cfg = SandboxConfig(project_root=tmp_path, allow_network=True)
        rules = cfg._default_deny_rules()
        patterns = [r.pattern for r in rules]
        assert "curl *" not in patterns
        assert "wget *" not in patterns


@pytest.mark.unit
class TestSandboxConfigGenerate:
    """Tests for settings generation."""

    def test_generate_settings_structure(self, tmp_path):
        """Output has allowedTools and deniedTools keys."""
        cfg = SandboxConfig(project_root=tmp_path)
        settings = cfg.generate_settings()
        assert "allowedTools" in settings
        assert "deniedTools" in settings

    def test_generate_settings_contains_project_path(self, tmp_path):
        """project_root appears in allow patterns."""
        cfg = SandboxConfig(project_root=tmp_path)
        settings = cfg.generate_settings()
        project_str = str(tmp_path)
        allow_patterns = [
            r.get("pattern", "") for r in settings["allowedTools"]
        ]
        matching = [p for p in allow_patterns if project_str in p]
        assert len(matching) > 0, (
            f"No allowedTools patterns contain project path {project_str}"
        )

    def test_custom_allow_rules(self, tmp_path):
        """Custom allow rules appear in output."""
        custom = SandboxRule(tool="Bash", pattern="make build")
        cfg = SandboxConfig(project_root=tmp_path, custom_allow=[custom])
        settings = cfg.generate_settings()
        assert {"tool": "Bash", "pattern": "make build"} in settings["allowedTools"]

    def test_custom_deny_rules(self, tmp_path):
        """Custom deny rules appear in output."""
        custom = SandboxRule(tool="Bash", pattern="docker rm *")
        cfg = SandboxConfig(project_root=tmp_path, custom_deny=[custom])
        settings = cfg.generate_settings()
        assert {"tool": "Bash", "pattern": "docker rm *"} in settings["deniedTools"]

    def test_settings_json_valid(self, tmp_path):
        """Output is valid JSON with correct schema."""
        cfg = SandboxConfig(project_root=tmp_path)
        settings = cfg.generate_settings()
        # Round-trip through JSON to verify serializability
        serialized = json.dumps(settings)
        parsed = json.loads(serialized)
        assert isinstance(parsed["allowedTools"], list)
        assert isinstance(parsed["deniedTools"], list)
        for rule in parsed["allowedTools"] + parsed["deniedTools"]:
            assert "tool" in rule


@pytest.mark.unit
class TestSandboxConfigWrite:
    """Tests for writing settings.json."""

    def test_write_creates_file(self, tmp_path):
        """settings.json written to .claude/ directory."""
        cfg = SandboxConfig(project_root=tmp_path)
        result = cfg.write()
        assert result.exists()
        assert result.name == "settings.json"
        assert result.parent.name == ".claude"
        # Verify valid JSON
        data = json.loads(result.read_text())
        assert "allowedTools" in data

    def test_write_merges_existing(self, tmp_path):
        """Existing settings.json preserved, new rules merged."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        existing_file = claude_dir / "settings.json"
        existing_file.write_text(json.dumps({
            "customSetting": True,
            "allowedTools": [{"tool": "OldTool"}],
        }))

        cfg = SandboxConfig(project_root=tmp_path)
        result = cfg.write()
        data = json.loads(result.read_text())

        # Custom setting preserved
        assert data["customSetting"] is True
        # allowedTools overwritten with new rules (dict.update behavior)
        assert any(r["tool"] == "Read" for r in data["allowedTools"])

    def test_write_custom_target_dir(self, tmp_path):
        """target_dir override works."""
        custom_dir = tmp_path / "custom-config"
        cfg = SandboxConfig(project_root=tmp_path)
        result = cfg.write(target_dir=custom_dir)
        assert result.exists()
        assert result.parent == custom_dir


@pytest.mark.unit
class TestFactoryFunction:
    """Tests for generate_sandbox_config factory."""

    def test_factory_function(self, tmp_path):
        """generate_sandbox_config returns SandboxConfig."""
        cfg = generate_sandbox_config(project_root=tmp_path, allow_network=True)
        assert isinstance(cfg, SandboxConfig)
        assert cfg.project_root == tmp_path
        assert cfg.allow_network is True
