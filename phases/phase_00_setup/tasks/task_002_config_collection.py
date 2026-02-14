"""
Task 002: Configuration Validation

Validates the structured config produced by the Task 001 wizard.
Resolves any remaining marker strings ("infer", "default", "detect")
and merges into project-config.json under the 'extracted' key.

Input: .outputs/0-setup/extracted-config.json (from wizard)
Output: .outputs/0-setup/project-config.json (validated + merged)
"""

import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_cyan, print_yellow, print_green,
    print_red, print_dim
)
from core.utils.file_ops import read_file, write_file


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

VALID_PROJECT_TYPES = {
    "new-component", "new-frontend", "new-api", "new-cli", "new-library",
    "new-monorepo", "existing", "migration", "refactor", "hybrid",
}

VALID_PIPELINE_MODES = {"full", "component", "library", "prototype"}

VALID_PROVIDERS = {
    "anthropic", "openai", "aws-bedrock", "google", "ollama", "openrouter", "azure",
    "claude-code",
}

VALID_COMMAND_MODES = {"strict", "cautious", "permissive"}

VALID_NETWORK_MODES = {"cui", "internet"}

VALID_AUDIT_PROFILES = {"quick", "standard", "thorough"}

VALID_FAILURE_MODES = {"loop-until-pass", "gate-all", "gate-critical", "gate-high", "report-only"}

VALID_MODEL_TIERS = {"opus", "sonnet", "haiku"}

VALID_EFFORT_LEVELS = {"low", "medium", "high"}


def _validate_config_schema(config: Dict[str, Any]) -> List[str]:
    """
    Validate required keys, enum values, and types.

    Returns list of error messages (empty = valid).
    """
    errors: List[str] = []

    # --- project ---
    project = config.get("project")
    if not isinstance(project, dict):
        errors.append("Missing 'project' section")
    else:
        if not project.get("name"):
            errors.append("project.name is required")
        ptype = project.get("type")
        if ptype and ptype not in VALID_PROJECT_TYPES:
            errors.append(f"project.type '{ptype}' is not valid (expected one of {VALID_PROJECT_TYPES})")

    # --- pipeline ---
    pipeline = config.get("pipeline")
    if not isinstance(pipeline, dict):
        errors.append("Missing 'pipeline' section")
    else:
        mode = pipeline.get("mode")
        if mode and mode not in VALID_PIPELINE_MODES:
            errors.append(f"pipeline.mode '{mode}' is not valid")
        gates = pipeline.get("human_gates")
        if gates is not None and not isinstance(gates, list):
            errors.append("pipeline.human_gates must be a list")

    # --- llm ---
    llm = config.get("llm")
    if not isinstance(llm, dict):
        errors.append("Missing 'llm' section")
    else:
        provider = llm.get("primary_provider")
        if provider and provider not in VALID_PROVIDERS:
            errors.append(f"llm.primary_provider '{provider}' is not valid")

    # --- sandbox ---
    sandbox = config.get("sandbox")
    if isinstance(sandbox, dict):
        cmd_mode = sandbox.get("command_approval_mode")
        if cmd_mode and cmd_mode not in VALID_COMMAND_MODES:
            errors.append(f"sandbox.command_approval_mode '{cmd_mode}' is not valid")
        net_mode = sandbox.get("network_mode")
        if net_mode and net_mode not in VALID_NETWORK_MODES:
            errors.append(f"sandbox.network_mode '{net_mode}' is not valid")

    # --- repository (optional but must be dict if present) ---
    repo = config.get("repository")
    if repo is not None and not isinstance(repo, dict):
        errors.append("repository must be a dict")

    # --- providers ---
    providers = config.get("providers")
    if isinstance(providers, dict):
        chain = providers.get("chain_priority")
        if chain is not None:
            if not isinstance(chain, list) or len(chain) == 0:
                errors.append("providers.chain_priority must be a non-empty list")
        model_cfg = providers.get("models")
        if isinstance(model_cfg, dict):
            for role in ("primary", "fast", "heavyweight", "gardener"):
                tier = model_cfg.get(role)
                if tier and tier not in VALID_MODEL_TIERS:
                    errors.append(f"providers.models.{role} '{tier}' is not valid (expected one of {VALID_MODEL_TIERS})")
        effort = providers.get("effort_level")
        if effort is not None and effort not in VALID_EFFORT_LEVELS:
            errors.append(f"providers.effort_level '{effort}' is not valid (expected one of {VALID_EFFORT_LEVELS})")
        thinking = providers.get("thinking_budget")
        if thinking is not None and not isinstance(thinking, int):
            errors.append("providers.thinking_budget must be an integer")

    # --- agents ---
    agents = config.get("agents")
    if isinstance(agents, dict):
        tier = agents.get("default_tier")
        if tier and tier not in VALID_MODEL_TIERS:
            errors.append(f"agents.default_tier '{tier}' is not valid (expected one of {VALID_MODEL_TIERS})")

    # --- audits ---
    audits = config.get("audits")
    if isinstance(audits, dict):
        profile = audits.get("default_profile")
        if profile and profile not in VALID_AUDIT_PROFILES:
            errors.append(f"audits.default_profile '{profile}' is not valid (expected one of {VALID_AUDIT_PROFILES})")
        fm = audits.get("failure_mode")
        if fm and fm not in VALID_FAILURE_MODES:
            errors.append(f"audits.failure_mode '{fm}' is not valid (expected one of {VALID_FAILURE_MODES})")

    return errors


# ---------------------------------------------------------------------------
# Resolve marker strings
# ---------------------------------------------------------------------------

def _resolve_markers(config: Dict[str, Any]) -> None:
    """Resolve any remaining 'infer', 'default', 'detect' marker strings in-place."""
    project = config.get("project", {})

    # project.name fallback
    if project.get("name") in ("infer", "default", None):
        project["name"] = _detect_dir_name()

    # project.type fallback
    if project.get("type") in ("infer", "default", None):
        project["type"] = "new-component"

    # repository.url detect
    repo = config.get("repository", {})
    if repo.get("url") in ("detect", "infer"):
        repo["url"] = _detect_git_repo() or None

    if repo.get("default_branch") in ("default", "infer", None):
        repo["default_branch"] = "main"

    # agents: resolve "default" / "infer" in phase_assignments
    agents = config.get("agents", {})
    if isinstance(agents, dict):
        assignments = agents.get("phase_assignments", agents)
        if isinstance(assignments, dict):
            for key in list(assignments.keys()):
                val = assignments[key]
                if isinstance(val, str) and val in ("default", "infer"):
                    assignments[key] = "default"

    # gardener.model: resolve "infer"
    gardener = config.get("gardener", {})
    if gardener.get("model") == "infer":
        gardener["model"] = "haiku"


def _detect_git_repo() -> str:
    """Detect Git repository URL."""
    try:
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def _detect_dir_name() -> str:
    """Get current directory name as fallback project name."""
    import re
    name = Path.cwd().name.lower()
    name = re.sub(r'[^a-z0-9\-]', '-', name)
    name = re.sub(r'-+', '-', name).strip('-')
    return name[:24] or "my-project"


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------

def _merge_into_config(config_file: Path, extracted_file: Path) -> None:
    """Merge extracted config into main config file under 'extracted' key."""
    if config_file.exists():
        config = json.loads(read_file(config_file))
    else:
        config = {}

    extracted = json.loads(read_file(extracted_file))
    config['extracted'] = extracted

    write_file(config_file, json.dumps(config, indent=2))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 002: Configuration Validation.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, skip interactive prompts

    Returns:
        True if task completed successfully, False otherwise
    """
    config_file = output_dir / "project-config.json"
    extracted_file = output_dir / "extracted-config.json"

    print()
    print(print_cyan("Configuration Validation"))
    print()

    # 1. Load extracted-config.json (produced by wizard)
    if not extracted_file.exists():
        print(print_red("extracted-config.json not found"))
        print(print_dim(f"  Expected at: {extracted_file}"))
        print(print_dim("  Run Task 001 (setup wizard) first."))
        return False

    try:
        config = json.loads(read_file(extracted_file))
    except json.JSONDecodeError as e:
        print(print_red(f"Invalid JSON in extracted-config.json: {e}"))
        return False

    # 2. Validate schema
    errors = _validate_config_schema(config)
    if errors:
        print(print_yellow("  Configuration warnings:"))
        for err in errors:
            print(print_yellow(f"    - {err}"))
        print()

    # 3. Resolve remaining marker strings
    _resolve_markers(config)

    # 4. Re-write cleaned config
    write_file(extracted_file, json.dumps(config, indent=2))

    # 5. Merge into project-config.json under 'extracted' key
    _merge_into_config(config_file, extracted_file)

    # 6. Display summary
    project = config.get("project", {})
    print(print_green("  Configuration validated"))
    print()
    print(print_dim(f"  Project: {project.get('name')}"))
    print(print_dim(f"  Type:    {project.get('type')}"))
    print(print_dim(f"  Mode:    {config.get('pipeline', {}).get('mode')}"))
    print()

    return True


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 002: Configuration Validation")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                        help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                        help='Path to phase output directory')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir)
    sys.exit(0 if success else 1)
