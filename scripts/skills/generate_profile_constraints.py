#!/usr/bin/env python3
"""
generate_profile_constraints.py — Generate .claude/rules/profile-constraints.md

Reads the active environment profile and produces a rule file that tells
Claude Code what it can and cannot do in this environment.

Called by resolve-profile.sh after locking the profile, or standalone:
    python3 scripts/skills/generate_profile_constraints.py
    python3 scripts/skills/generate_profile_constraints.py --profile air-gapped
"""

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

ACTIVE_PROFILE_YAML = PROJECT_ROOT / ".claude" / "active-profile.yaml"
PROFILES_YAML = PROJECT_ROOT / "config" / "environment-profiles.yaml"
OUTPUT_PATH = PROJECT_ROOT / ".claude" / "rules" / "profile-constraints.md"

# ── YAML helpers ──────────────────────────────────────────────────────────────

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def read_yaml(path):
    """Read a YAML file with PyYAML or minimal fallback."""
    if not path.exists():
        return None
    with open(path) as f:
        content = f.read()
    if HAS_YAML:
        return yaml.safe_load(content)
    return _minimal_parse(content)


def _minimal_parse(content):
    """Minimal YAML parser for our known structures."""
    result = {}
    current_section = None
    current_block = None

    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Top-level key
        m = re.match(r"^(\w[\w_-]*):\s*(.*)?$", line)
        if m:
            key, val = m.group(1), (m.group(2) or "").strip()
            if val:
                result[key] = _parse_val(val)
            else:
                result[key] = {}
                current_section = key
            current_block = None
            continue

        # Second-level key (2 spaces)
        m = re.match(r"^  (\w[\w_-]*):\s*(.*)?$", line)
        if m and current_section:
            key, val = m.group(1), (m.group(2) or "").strip()
            if val:
                result[current_section][key] = _parse_val(val)
            else:
                result[current_section][key] = {}
                current_block = key
            continue

        # Third-level key (4 spaces)
        m = re.match(r"^    (\w[\w_-]*):\s*(.+)$", line)
        if m and current_section and current_block:
            key, val = m.group(1), m.group(2).strip()
            result[current_section][current_block][key] = _parse_val(val)

    return result


def _parse_val(val):
    val = val.strip()
    if val in ("true", "True"):
        return True
    if val in ("false", "False"):
        return False
    if val in ("null", "~"):
        return None
    if val.startswith("[") and val.endswith("]"):
        return [i.strip().strip('"').strip("'") for i in val[1:-1].split(",") if i.strip()]
    if val.startswith('"') and val.endswith('"'):
        return val[1:-1]
    return val


# ── Constraint templates ──────────────────────────────────────────────────────

PROFILE_CONSTRAINTS = {
    "air-gapped": {
        "title": "Air-Gapped Environment",
        "summary": "This environment has NO network connectivity. All operations must be fully offline.",
        "rules": [
            "DO NOT make any network calls (HTTP, HTTPS, DNS, or otherwise)",
            "DO NOT attempt to install packages from remote registries (pip, npm, cargo, etc.)",
            "DO NOT call any external APIs (REST, GraphQL, gRPC, or webhook)",
            "DO NOT use curl, wget, fetch, requests, or any HTTP client",
            "DO NOT reference URLs that require live network access",
            "All skills and dependencies MUST be pre-installed locally",
            "Use only tools and libraries already present on the filesystem",
            "If a task requires network access, report it as blocked and suggest offline alternatives",
            "File-based caching and local databases (SQLite, FalkorDB on localhost) are allowed",
        ],
    },
    "sensitive": {
        "title": "Sensitive Environment",
        "summary": "Internet is available for reading code and documentation only. No SaaS integrations.",
        "rules": [
            "DO NOT integrate with any external SaaS services (Jira, Slack, GitHub API, etc.)",
            "DO NOT send project data, code, or metadata to external services",
            "DO NOT use cloud-hosted AI APIs (except the configured LLM provider)",
            "Internet access is permitted ONLY for: reading documentation, downloading packages from verified sources",
            "DO NOT upload files, logs, or artifacts to external storage (S3, GCS, Azure Blob, etc.)",
            "All SaaS-dependent skills are blocked and must not be invoked",
            "Prefer local tools over cloud-hosted alternatives",
            "If a task requires SaaS integration, report it as blocked and suggest local alternatives",
        ],
    },
    "standard": {
        "title": "Standard Environment",
        "summary": "Full internet access. SaaS integrations allowed with approval. High-risk skills require explicit approval.",
        "rules": [
            "Internet access and package installation are allowed",
            "SaaS integrations (GitHub API, CI/CD, etc.) are available",
            "High-risk skills (risk_level: High) require explicit user approval via --approve-high-risk flag",
            "DO NOT execute High-risk skills without the approval flag being set",
            "Review Medium-risk skills before execution and note any side effects",
            "All skill invocations should be logged for audit trail",
            "Prefer verified and well-known packages over obscure alternatives",
        ],
    },
    "unrestricted": {
        "title": "Unrestricted Environment (Development/Lab)",
        "summary": "All skills and capabilities are available. This is a development or lab environment.",
        "rules": [
            "All internet access, SaaS integrations, and skill risk levels are permitted",
            "All skills are available without approval gates",
            "Still follow best practices: log actions, prefer safe defaults",
            "This profile is intended for development and testing only",
            "DO NOT use this profile in production or customer-facing environments",
        ],
    },
}


def generate_constraints_md(profile_name, profile_config=None):
    """Generate the profile-constraints.md content for a given profile."""
    constraints = PROFILE_CONSTRAINTS.get(profile_name)
    if constraints is None:
        # Unknown profile — fall back to standard
        constraints = PROFILE_CONSTRAINTS["standard"]

    lines = [
        f"# Environment Profile Constraints: {constraints['title']}",
        "",
        f"> **Active profile:** `{profile_name}`",
        f"> **Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"> **Auto-generated by:** `scripts/skills/generate_profile_constraints.py`",
        "",
        "## Summary",
        "",
        constraints["summary"],
        "",
        "## Rules",
        "",
    ]

    for i, rule in enumerate(constraints["rules"], 1):
        lines.append(f"{i}. {rule}")

    lines.append("")

    # Add profile-specific details from config if available
    if profile_config:
        lines.append("## Active Configuration")
        lines.append("")
        allow_inet = profile_config.get("allow_internet", "unknown")
        allow_saas = profile_config.get("allow_saas", "unknown")
        risk_levels = profile_config.get("acceptable_risk_levels", [])
        strategy = profile_config.get("skill_install_strategy", "unknown")

        lines.append(f"- **Internet access:** {'Allowed' if allow_inet else 'BLOCKED'}")
        lines.append(f"- **SaaS integrations:** {'Allowed' if allow_saas else 'BLOCKED'}")
        if isinstance(risk_levels, list):
            lines.append(f"- **Acceptable risk levels:** {', '.join(risk_levels)}")
        else:
            lines.append(f"- **Acceptable risk levels:** {risk_levels}")
        lines.append(f"- **Install strategy:** {strategy}")
        lines.append("")

    lines.append("---")
    lines.append("*This file is auto-generated. Do not edit manually.*")
    lines.append("*Re-run `source scripts/skills/resolve-profile.sh` to regenerate.*")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate .claude/rules/profile-constraints.md",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="Override profile name (default: read from active-profile.yaml)",
    )
    parser.add_argument(
        "--output",
        default=str(OUTPUT_PATH),
        help=f"Output path (default: {OUTPUT_PATH})",
    )
    args = parser.parse_args()

    # Determine profile
    profile_name = args.profile
    profile_config = None

    if profile_name is None:
        # Read from active profile
        active = read_yaml(ACTIVE_PROFILE_YAML)
        if active:
            profile_name = active.get("profile", "standard")
        else:
            profile_name = os.environ.get("ATOMIC_ENV_PROFILE", "standard")

    # Read full profile config
    profiles = read_yaml(PROFILES_YAML)
    if profiles:
        profile_config = profiles.get("profiles", {}).get(profile_name, {})

    print(f"[generate_profile_constraints] Profile: {profile_name}")

    # Generate content
    content = generate_constraints_md(profile_name, profile_config)

    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write file
    with open(output_path, "w") as f:
        f.write(content)

    print(f"[generate_profile_constraints] Written to: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
