"""Skill installation, validation, and hashing."""

import hashlib
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.skills.models import SkillMetadata, PROFILE_SKILL_RULES, risk_at_most, RiskLevel

logger = logging.getLogger(__name__)


class SkillInstaller:
    """Install skills from catalog with profile gating."""

    def __init__(self, atomic_root: Path = None):
        self.atomic_root = atomic_root or Path(os.environ.get("ATOMIC_ROOT", Path.cwd()))
        self.skills_dir = self.atomic_root / ".claude" / "skills"

    def install_from_catalog(
        self,
        profile_name: str = "cloud_full",
        approve_high_risk: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Install skills from catalog based on profile gates.

        Returns summary dict with counts.
        """
        from core.skills.catalog import SKILL_CATALOG

        rules = PROFILE_SKILL_RULES.get(profile_name, PROFILE_SKILL_RULES["development"])
        max_risk = rules["max_risk"]

        results = {
            "profile": profile_name,
            "installed": 0,
            "skipped_profile": 0,
            "skipped_high_risk": 0,
            "failed": 0,
            "total": len(SKILL_CATALOG),
            "skills": [],
        }

        if not dry_run:
            self.skills_dir.mkdir(parents=True, exist_ok=True)

        for skill in SKILL_CATALOG:
            # Profile gate
            if profile_name not in skill.installable_in_profiles():
                results["skipped_profile"] += 1
                continue

            # High-risk gate
            rl = skill.risk_level if isinstance(skill.risk_level, RiskLevel) else RiskLevel(skill.risk_level)
            if rl == RiskLevel.HIGH and not approve_high_risk:
                results["skipped_high_risk"] += 1
                continue

            if dry_run:
                results["installed"] += 1
                results["skills"].append({"id": skill.id, "status": "would_install"})
                continue

            # Install
            try:
                install_path = self._install_skill(skill)
                content_hash, _ = self.compute_hash(install_path)
                results["installed"] += 1
                results["skills"].append({
                    "id": skill.id,
                    "status": "installed",
                    "path": str(install_path),
                    "hash": content_hash,
                })
            except Exception as e:
                logger.warning("Failed to install skill %s: %s", skill.id, e)
                results["failed"] += 1
                results["skills"].append({"id": skill.id, "status": "failed", "error": str(e)})

        return results

    def _install_skill(self, skill: SkillMetadata) -> Path:
        """Generate SKILL.md for a single skill. Returns the skill directory."""
        skill_dir = self.skills_dir / skill.category / skill.id
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"

        # Determine tools based on category
        tools_map = {
            "formatting": ["Read", "Write", "Bash"],
            "file-ops": ["Read", "Write", "Bash"],
            "doc-gen": ["Read", "Write", "Bash"],
            "git-ops": ["Bash"],
            "validation": ["Read", "Bash"],
            "extraction": ["Read", "Bash"],
            "phase-checks": ["Read", "Bash"],
            "data": ["Read", "Write", "Bash"],
            "architecture": ["Read", "Bash"],
        }
        tools = tools_map.get(skill.category, ["Read", "Bash"])
        tools_yaml = "\n".join(f"  - {t}" for t in tools)

        phases_list = "\n".join(f"- Phase {p}" for p in skill.sdlc_phases)
        risk_line = str(skill.risk_level.value if isinstance(skill.risk_level, RiskLevel) else skill.risk_level)
        if skill.risk_notes:
            risk_line += f" — {skill.risk_notes}"

        content = f"""---
name: {skill.id}
description: {skill.description}
model: haiku
tools:
{tools_yaml}
context: fork
disable-model-invocation: false
---

# {skill.name}

{skill.description}

## Category
{skill.category}

## SDLC Phases
{phases_list}

## Risk Level
{risk_line}

## License
{skill.license}
"""
        skill_file.write_text(content)
        return skill_dir

    def validate_skill(self, skill_dir: Path) -> Tuple[bool, List[str]]:
        """
        Validate a skill directory.

        Checks: SKILL.md exists, no binaries, no credentials, size limits.
        Returns (valid, errors).
        """
        errors = []
        skill_dir = Path(skill_dir)

        if not skill_dir.is_dir():
            return False, [f"Not a directory: {skill_dir}"]

        # Check SKILL.md exists
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            errors.append("Missing SKILL.md")

        # Check for binary files
        binary_extensions = {".exe", ".dll", ".so", ".dylib", ".bin", ".o", ".a", ".pyc", ".pyo"}
        for f in skill_dir.rglob("*"):
            if f.is_file():
                if f.suffix.lower() in binary_extensions:
                    errors.append(f"Binary file found: {f.name}")

        # Check for credential patterns
        credential_patterns = [".env", "credentials", "secret", "private_key", "id_rsa"]
        for f in skill_dir.rglob("*"):
            if f.is_file():
                name_lower = f.name.lower()
                for pattern in credential_patterns:
                    if pattern in name_lower:
                        errors.append(f"Potential credential file: {f.name}")

        # Size limit: 1MB per skill
        total_size = sum(f.stat().st_size for f in skill_dir.rglob("*") if f.is_file())
        if total_size > 1_048_576:
            errors.append(f"Skill exceeds 1MB size limit: {total_size} bytes")

        return len(errors) == 0, errors

    def compute_hash(self, skill_dir: Path) -> Tuple[str, str]:
        """
        Compute SHA256 of SKILL.md and total directory hash.
        Returns (skill_md_hash, dir_hash).
        """
        skill_dir = Path(skill_dir)
        skill_md = skill_dir / "SKILL.md"

        # SKILL.md hash
        if skill_md.exists():
            skill_hash = hashlib.sha256(skill_md.read_bytes()).hexdigest()
        else:
            skill_hash = ""

        # Directory hash (sorted file contents)
        hasher = hashlib.sha256()
        for f in sorted(skill_dir.rglob("*")):
            if f.is_file():
                hasher.update(f.read_bytes())
        dir_hash = hasher.hexdigest()

        return skill_hash, dir_hash
