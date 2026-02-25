"""
Sandbox Security Configuration for Claude Code Invocations.

Generates .claude/settings.json with allow/deny rules that constrain
what Claude Code agents can do when invoked as subprocesses.
Applied during Phase 0 repository setup (task_005).
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SandboxRule:
    """A single allow or deny rule."""
    tool: str          # Tool name: "Bash", "Read", "Write", "Edit", etc.
    pattern: str = ""  # Optional glob/regex pattern for the tool's arguments

    def to_dict(self) -> Dict[str, str]:
        if self.pattern:
            return {"tool": self.tool, "pattern": self.pattern}
        return {"tool": self.tool}


@dataclass
class SandboxConfig:
    """Security configuration for Claude Code subprocess invocations.

    Generates a .claude/settings.json that constrains agent behavior.
    Rules follow Claude Code's settings format.

    Args:
        project_root: Path to the target project root
        allow_network: Whether to allow network access (default False)
        custom_allow: Additional allow rules
        custom_deny: Additional deny rules
    """
    project_root: Path
    allow_network: bool = False
    custom_allow: List[SandboxRule] = field(default_factory=list)
    custom_deny: List[SandboxRule] = field(default_factory=list)

    def generate_settings(self) -> Dict[str, Any]:
        """Generate the full settings.json content.

        Returns:
            Dict ready for json.dump()
        """
        settings: Dict[str, Any] = {}

        allow_rules = self._default_allow_rules() + self.custom_allow
        deny_rules = self._default_deny_rules() + self.custom_deny

        if allow_rules:
            settings["allowedTools"] = [r.to_dict() for r in allow_rules]
        if deny_rules:
            settings["deniedTools"] = [r.to_dict() for r in deny_rules]

        return settings

    def write(self, target_dir: Optional[Path] = None) -> Path:
        """Write settings.json to the project's .claude directory.

        Args:
            target_dir: Override directory (default: project_root/.claude)

        Returns:
            Path to the written settings file
        """
        claude_dir = target_dir or (self.project_root / ".claude")
        claude_dir.mkdir(parents=True, exist_ok=True)

        settings_file = claude_dir / "settings.json"

        # Merge with existing settings if present
        existing = {}
        if settings_file.exists():
            try:
                existing = json.loads(settings_file.read_text())
            except (json.JSONDecodeError, OSError):
                pass

        new_settings = self.generate_settings()
        existing.update(new_settings)

        settings_file.write_text(json.dumps(existing, indent=2) + "\n")
        logger.info("Sandbox settings written to %s", settings_file)
        return settings_file

    def _default_allow_rules(self) -> List[SandboxRule]:
        """Default allow rules for atomic-claude agents."""
        project = str(self.project_root)
        rules = [
            # Read access to project files
            SandboxRule(tool="Read", pattern=f"{project}/**"),
            # Write access scoped to project
            SandboxRule(tool="Write", pattern=f"{project}/**"),
            SandboxRule(tool="Edit", pattern=f"{project}/**"),
            # Bash for test execution and build commands
            SandboxRule(tool="Bash", pattern="pytest *"),
            SandboxRule(tool="Bash", pattern="python *"),
            SandboxRule(tool="Bash", pattern="npm *"),
            SandboxRule(tool="Bash", pattern="cargo *"),
            SandboxRule(tool="Bash", pattern="go *"),
            SandboxRule(tool="Bash", pattern="git status*"),
            SandboxRule(tool="Bash", pattern="git diff*"),
            SandboxRule(tool="Bash", pattern="git log*"),
            SandboxRule(tool="Bash", pattern="git add*"),
            SandboxRule(tool="Bash", pattern="git commit*"),
        ]
        return rules

    def _default_deny_rules(self) -> List[SandboxRule]:
        """Default deny rules for safety."""
        project = str(self.project_root)
        rules = [
            # No writes outside project
            SandboxRule(tool="Write", pattern="/*"),
            SandboxRule(tool="Edit", pattern="/*"),
            # No destructive git operations
            SandboxRule(tool="Bash", pattern="git push --force*"),
            SandboxRule(tool="Bash", pattern="git reset --hard*"),
            SandboxRule(tool="Bash", pattern="rm -rf *"),
            # No credential access
            SandboxRule(tool="Read", pattern="**/.env"),
            SandboxRule(tool="Read", pattern="**/credentials*"),
            SandboxRule(tool="Read", pattern="**/*.pem"),
            SandboxRule(tool="Read", pattern="**/*.key"),
        ]

        if not self.allow_network:
            rules.extend([
                SandboxRule(tool="Bash", pattern="curl *"),
                SandboxRule(tool="Bash", pattern="wget *"),
            ])

        return rules


def generate_sandbox_config(
    project_root: Path,
    allow_network: bool = False,
) -> SandboxConfig:
    """Factory function for creating a sandbox config.

    Args:
        project_root: Path to the target project
        allow_network: Whether agents can access the network

    Returns:
        Configured SandboxConfig instance
    """
    return SandboxConfig(
        project_root=project_root,
        allow_network=allow_network,
    )
