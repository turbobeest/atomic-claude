"""
Task 003: Setup Wizard

Guided step-by-step wizard that collects project configuration interactively.
Consumes provider-inventory.json (written by Task 002) for pre-populated LLM
provider information, credential flags, Ollama hosts, and model inventories.
Uses an LLM (haiku) to pre-populate AI suggestions from reference materials.
Produces structured config directly -- no setup.md needed.

Steps:
  1. Project Identity (name, description, goal)
  2. Project Type (9-option selection)
  3. Pipeline Mode + Human Gates
  4. Repository (auto-detected URL, branch, strategies)
  5. LLM Preferences (provider chain, model roles, routing, fallback)
  6. Agent Assignment (default tier, per-phase assignments)
  7. Audit Configuration (profile, failure mode, severity)
  8. Sandbox & Security
  9. Constraints (optional)
  10. Summary & Confirm

Provider inventory (from Task 002) supplies:
  - credentials: {has_aws, has_anthropic, has_ollama}
  - detected_providers: ordered list of available providers
  - ollama_hosts: list of reachable Ollama server URLs
  - ollama_models: dict mapping host -> {model_name -> {size, category}}
  - env_vars: environment variable snapshot used during detection
  - health: per-provider health check results
"""

import os
import sys
import json
import re
import subprocess
import logging
import urllib.request
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user, clear_input_buffer
)
from core.utils.file_ops import ensure_dir, read_file, write_file

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_TYPES = [
    ("new-component", "Standalone service or module"),
    ("new-frontend",  "Web or mobile UI application"),
    ("new-api",       "Backend API service"),
    ("new-cli",       "Command-line tool"),
    ("new-library",   "Shared library or package"),
    ("new-monorepo",  "Multi-package repository"),
    ("existing",      "Add features to existing codebase"),
    ("migration",     "Technology migration"),
    ("refactor",      "Code modernization"),
]

PHASE_NAMES = {
    0: "Setup",        1: "Discovery",   2: "PRD",
    3: "Tasking",      4: "Specification", 5: "Implementation",
    6: "Code Review",  7: "Integration", 8: "Deploy Prep",
    9: "Release",
}

# Pipeline modes: (key, description, included_phases)
# All modes include Phase 0 (Setup) implicitly.
PIPELINE_MODES = [
    ("component", "Build and test, no deployment", [0, 1, 2, 3, 4, 5, 6, 7]),
    ("full",      "Complete pipeline with deployment and release", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
    ("library",   "Minimal for shared packages", [0, 1, 2, 3, 4, 5, 6]),
    ("prototype", "Quick validation only", [0, 1, 2, 3, 5]),
]

DEFAULT_HUMAN_GATES = [0, 2, 5, 9]

COMMAND_APPROVAL_MODES = [
    ("permissive", "Auto-approve safe commands"),
    ("cautious",   "Prompt for risky commands"),
    ("strict",     "Prompt before every command"),
]

NETWORK_MODES = [
    ("internet", "Allow outbound network access"),
    ("cui",      "Isolated -- no outbound network"),
]

# Ollama model name patterns that indicate code-specialized models
_CODE_MODEL_PATTERNS = [
    "devstral", "granite-code", "codestral", "starcoder", "deepseek-coder",
    "codellama", "codegemma", "codegeex", "qwen2.5-coder", "wizardcoder",
]

ROUTING_STRATEGIES = [
    ("all-cloud", "All tasks use cloud providers"),
    ("hybrid",    "Critical tasks cloud, bulk tasks local"),
    ("all-local", "All tasks use local models"),
]

MODEL_TIERS = ["opus", "sonnet", "haiku"]

MODEL_ROLES = [
    ("primary",     "Main model for most tasks"),
    ("fast",        "Quick tasks, summaries, formatting"),
    ("heavyweight", "Complex reasoning, architecture"),
    ("gardener",    "Context window management"),
]

AUDIT_PROFILES = [
    ("thorough",  "40+ checks per audit point"),
    ("standard",  "20-30 checks per audit point"),
    ("quick",     "10-15 checks per audit point"),
]

FAILURE_MODES = [
    ("loop-until-pass", "Retry until all checks pass"),
    ("gate-all",        "Block on any failure"),
    ("gate-critical",   "Block only on critical severity"),
    ("gate-high",       "Block on critical + high severity"),
    ("report-only",     "Log failures, never block"),
]

SEVERITY_LEVELS = ["critical", "high", "medium", "low"]

# ---------------------------------------------------------------------------
# Schema validation constants (merged from former Task 002)
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

VALID_NETWORK_MODES_SCHEMA = {"cui", "internet"}

VALID_AUDIT_PROFILES = {"quick", "standard", "thorough"}

VALID_FAILURE_MODES_SCHEMA = {"loop-until-pass", "gate-all", "gate-critical", "gate-high", "report-only"}

VALID_MODEL_TIERS_SCHEMA = {"opus", "sonnet", "haiku"}

VALID_EFFORT_LEVELS_SCHEMA = {"low", "medium", "high"}

# Provider-aware default profiles for Step 5
# Inline fallback -- used only when config/models.json is missing.
_PROVIDER_PROFILES = {
    "claude-code": {
        "models": {"primary": "opus", "fast": "opus", "heavyweight": "opus", "gardener": "sonnet"},
        "effort": "high",
        "thinking_budget": None,
    },
    "anthropic": {
        "models": {"primary": "sonnet", "fast": "haiku", "heavyweight": "opus", "gardener": "haiku"},
        "effort": None,
        "thinking_budget": 10000,
    },
    "aws-bedrock": {
        "models": {"primary": "sonnet", "fast": "haiku", "heavyweight": "opus", "gardener": "haiku"},
        "effort": None,
        "thinking_budget": 10000,
    },
    "ollama": {
        "models": {"primary": "sonnet", "fast": "haiku", "heavyweight": "sonnet", "gardener": "haiku"},
        "effort": None,
        "thinking_budget": None,
    },
}

# "low" is excluded for claude-code -- subscription is fixed-cost, so "low"
# gives worse output for the same price.  Only offered for API providers.
VALID_EFFORT_LEVELS = {"medium", "high"}
VALID_EFFORT_LEVELS_API = {"low", "medium", "high"}  # API providers only

# Phase role labels for the Guided/Detailed table
_PHASE_ROLE_LABELS = {
    "0-setup": "Setup",        "1-discovery": "Discovery",
    "2-prd": "PRD",            "3-tasking": "Tasking",
    "4-spec": "Specification", "5-impl": "Implementation",
    "6-review": "Code Review", "7-integration": "Integration",
    "8-deploy-prep": "Deploy Prep", "9-release": "Release",
}


def _load_models_config(atomic_root: Path) -> Dict[str, Any]:
    """Load config/models.json shipped defaults.

    Returns the parsed dict, or {} if the file is missing/invalid.
    """
    config_path = atomic_root / "config" / "models.json"
    try:
        return json.loads(config_path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _get_provider_profile(provider: str, atomic_root: Path) -> Dict[str, Any]:
    """Build a provider profile from config/models.json, with inline fallback."""
    models_cfg = _load_models_config(atomic_root)
    prov_overrides = models_cfg.get("provider_overrides", {}).get(provider, {})

    if prov_overrides:
        r2t = prov_overrides.get("role_to_tier", {})
        models = {
            "primary": r2t.get("primary", "sonnet"),
            "fast": r2t.get("fast", "haiku"),
            "heavyweight": r2t.get("heavyweight", "opus"),
            "gardener": r2t.get("gardener", "haiku"),
        }
        return {
            "models": models,
            "effort": prov_overrides.get("effort_level"),
            "thinking_budget": prov_overrides.get("thinking_budget"),
        }

    # Fallback to inline _PROVIDER_PROFILES
    return dict(_PROVIDER_PROFILES.get(provider, _PROVIDER_PROFILES["anthropic"]))


def _get_default_phase_roles(atomic_root: Path) -> Dict[str, str]:
    """Load default phase_roles from config/models.json."""
    models_cfg = _load_models_config(atomic_root)
    return dict(models_cfg.get("phase_roles", {
        "0-setup": "fast", "1-discovery": "fast", "2-prd": "heavyweight",
        "3-tasking": "primary", "4-spec": "primary", "5-impl": "primary",
        "6-review": "primary", "7-integration": "fast",
        "8-deploy-prep": "fast", "9-release": "fast",
    }))


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None) -> bool:
    """
    Execute Task 003: Setup Wizard.

    Loads provider-inventory.json (written by Task 002) for pre-populated
    provider detection results, then runs the interactive 10-step wizard
    to collect project configuration.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, generate stub config without interactive prompts
        mem: Optional TaskMemory instance for recording substantive memory

    Returns:
        True if task completed successfully, False otherwise
    """
    config_file = output_dir / "project-config.json"
    extracted_file = output_dir / "extracted-config.json"
    project_root = atomic_root.parent
    inventory_file = output_dir / "provider-inventory.json"

    # --- Load provider inventory from Task 002 ---
    provider_inventory: Dict[str, Any] = {}
    if inventory_file.exists():
        try:
            provider_inventory = json.loads(read_file(str(inventory_file)))
            print(print_green("  Provider inventory loaded"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load provider-inventory.json: %s", e)
            print(print_yellow("  Warning: Could not load provider-inventory.json"))
    else:
        print(print_yellow("  Warning: provider-inventory.json not found"))
        print(print_dim("  (Task 002 should have created it -- using empty defaults)"))

    # --- Detect environment ---
    env_info = _detect_environment(project_root)
    _show_reference_scan(project_root, env_info)

    # --- Infer project defaults from reference materials ---
    # Use env_vars from the inventory if available, otherwise fall back to os.environ
    env_vars = provider_inventory.get("env_vars", dict(os.environ))
    ai_defaults = _infer_project_defaults(env_vars, project_root, env_info)

    # --- Run the 10-step wizard (loop on RESTART sentinel) ---
    config = "RESTART"
    while config == "RESTART":
        config = _run_wizard(ai_defaults, env_info, provider_inventory, config_file, mem=mem)
    if config is None:
        print(print_red("Setup aborted"))
        return False

    # --- Save config ---
    _save_config(config_file, extracted_file, config)

    # Record substantive memory
    if mem and config:
        project = config.get("project", {})
        name = project.get("name", "unknown")
        desc = project.get("description", "")
        ptype = project.get("type", "")
        mem.decision(f"Project: {name} — {desc}" if desc else f"Project: {name}")
        pipeline = config.get("pipeline", {})
        mode = pipeline.get("mode", "")
        skip = pipeline.get("skip_phases", [])
        mem.decision(f"Type: {ptype} | Pipeline mode: {mode}"
                     + (f" | Skip phases: {skip}" if skip else ""))
        gates = pipeline.get("human_gates", [])
        if gates:
            mem.decision(f"Human gates at phases: {gates}")
        llm = config.get("llm", {})
        provider = llm.get("primary_provider", "")
        model = llm.get("primary_model", "")
        effort = llm.get("effort_level", "") or llm.get("effort", "")
        mem.configuration(f"LLM: {provider}/{model} (effort: {effort})")
        agents = config.get("agents", {})
        tier = agents.get("default_tier", "") or agents.get("tier", "")
        mem.configuration(f"Agents: {tier} tier")
        audit = config.get("audit", {})
        profile = audit.get("profile", "")
        if profile:
            mem.configuration(f"Audit profile: {profile}")
        constraints = config.get("constraints", {})
        tech = constraints.get("technical", [])
        if isinstance(tech, list) and tech:
            mem.finding(f"Technical constraints: {len(tech)} requirements")

    print()
    print(print_green("Setup complete"))
    print(print_dim(f"  Config: {config_file}"))
    print()
    return True


# ---------------------------------------------------------------------------
# Environment detection
# ---------------------------------------------------------------------------

def _detect_environment(project_root: Path) -> Dict[str, Any]:
    """Detect git URL, directory name, scan for reference files."""
    info: Dict[str, Any] = {
        "dir_name": project_root.name,
        "git_url": "",
        "default_branch": "main",
        "reference_files": [],
    }

    # Git URL
    try:
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            capture_output=True, text=True, timeout=5,
            cwd=str(project_root),
        )
        if result.returncode == 0:
            info["git_url"] = result.stdout.strip()
    except Exception as e:
        logger.debug("Git remote URL detection failed: %s", e)

    # Default branch
    try:
        result = subprocess.run(
            ['git', 'symbolic-ref', 'refs/remotes/origin/HEAD'],
            capture_output=True, text=True, timeout=5,
            cwd=str(project_root),
        )
        if result.returncode == 0:
            ref = result.stdout.strip()  # refs/remotes/origin/main
            info["default_branch"] = ref.rsplit('/', 1)[-1]
    except Exception as e:
        logger.debug("Git default branch detection failed: %s", e)

    # Reference files -- scan explicit names + common subdirectories
    candidates = [
        "README.md", "WHITEPAPER.md", "DESIGN.md", "ARCHITECTURE.md",
        "SPEC.md", "brief.md", "prompt.md", "BRIEF.md", "PROMPT.md",
        "PRD.md", "prd.md", "REQUIREMENTS.md", "requirements.md",
        "docs/README.md", "docs/design.md", "docs/architecture.md",
    ]
    for c in candidates:
        p = project_root / c
        if p.exists():
            info["reference_files"].append(str(p))

    # Scan common subdirectories for any .md files
    scan_dirs = ["reference", "initialization", "docs", "docs/reference", "specs"]
    for d in scan_dirs:
        scan_path = project_root / d
        if scan_path.is_dir():
            for md in sorted(scan_path.glob("*.md")):
                if str(md) not in info["reference_files"]:
                    info["reference_files"].append(str(md))

    return info


def _show_reference_scan(project_root: Path, env_info: Dict[str, Any]) -> None:
    """Display what reference files were found and where we looked."""
    ref_files = env_info.get("reference_files", [])

    # Show search locations
    scan_dirs = ["reference/", "initialization/", "docs/", "docs/reference/", "specs/"]
    existing_dirs = [str(project_root / d) for d in scan_dirs if (project_root / d).is_dir()]

    print()
    print(print_dim("  Scanned for reference materials:"))
    print(print_dim(f"    Root:  {project_root}/"))
    if existing_dirs:
        for d in existing_dirs:
            print(print_dim(f"    Dir:   {d}"))
    else:
        print(print_dim(f"    Dirs:  (none found of {', '.join(scan_dirs)})"))

    docs_ref = project_root / "docs" / "reference"
    if docs_ref.is_dir():
        print(print_dim(f"    Note:  {docs_ref}/ already exists (Task 004 will organize here)"))

    if ref_files:
        print(print_green(f"  Found {len(ref_files)} reference file(s):"))
        for rf in ref_files:
            print(print_dim(f"    - {rf}"))
    else:
        print(print_dim("  No reference materials found -- using directory name for defaults"))
    print()


# ---------------------------------------------------------------------------
# LLM inference for AI suggestions
# ---------------------------------------------------------------------------

def _infer_project_defaults(
    env_vars: Dict[str, str],
    project_root: Path,
    env_info: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Suggest values from reference docs using the best available LLM method.
    Returns dict with: project_name, description, type, primary_goal, technical_constraints.
    Falls back to directory-name defaults if LLM unavailable or fails.
    """
    fallback = {
        "project_name": _slugify(env_info["dir_name"]),
        "description": None,
        "type": None,
        "primary_goal": None,
        "technical_constraints": None,
    }

    # Gather reference material (up to 5 files, 200 lines each)
    ref_text = ""
    for ref_path in env_info.get("reference_files", [])[:5]:
        try:
            content = read_file(ref_path)
            lines = content.split('\n')[:200]
            ref_text += f"\n=== {Path(ref_path).name} ===\n"
            ref_text += '\n'.join(lines)
            ref_text += "\n\n"
        except Exception as e:
            logger.debug("Failed to read reference file %s: %s", ref_path, e)

    if not ref_text:
        return fallback

    prompt = (
        "You are a configuration assistant. Analyze the reference materials below "
        "and suggest project configuration values.\n\n"
        f"Directory name: {env_info['dir_name']}\n\n"
        f"Reference materials:\n{ref_text}\n\n"
        "Return ONLY a JSON object (no markdown fences) with these keys:\n"
        '- "project_name": short lowercase-hyphenated identifier (max 24 chars)\n'
        '- "description": one-sentence project description\n'
        '- "type": one of: new-component, new-frontend, new-api, new-cli, '
        "new-library, new-monorepo, existing, migration, refactor\n"
        '- "primary_goal": one-sentence primary goal\n'
        '- "technical_constraints": array of strings or null\n\n'
        "If you cannot determine a value, use null. Start with { and end with }."
    )

    print(print_dim("  Analyzing reference materials for suggestions..."))

    # Try Claude Code CLI first (works with subscription), then Python SDK
    text = _llm_invoke(prompt, env_vars)
    if text is None:
        return fallback

    try:
        # Strip markdown fences if present
        if text.startswith('```'):
            lines = text.split('\n')
            lines = [l for l in lines if not l.strip().startswith('```')]
            text = '\n'.join(lines)

        data = json.loads(text)
        print(print_green("  AI suggestions loaded"))
        return {
            "project_name": data.get("project_name") or fallback["project_name"],
            "description": data.get("description"),
            "type": data.get("type"),
            "primary_goal": data.get("primary_goal"),
            "technical_constraints": data.get("technical_constraints"),
        }
    except (json.JSONDecodeError, AttributeError) as e:
        logger.warning("LLM inference parse failed: %s", e)
        print(print_yellow("  AI suggestions unavailable -- using defaults"))
        return fallback


def _llm_invoke(prompt: str, env_vars: Dict[str, str]) -> Optional[str]:
    """
    Invoke LLM using the best available method.
    Tries: claude CLI > Anthropic SDK > Bedrock SDK > Ollama.
    Each provider is attempted with 1 retry on transient failure.
    Returns response text or None.
    """
    import time as _time

    def _with_retry(fn, label: str) -> Optional[str]:
        """Call fn() with one retry after a short delay."""
        for attempt in range(2):
            try:
                result = fn()
                if result is not None:
                    return result
            except Exception as e:
                logger.debug("%s attempt %d failed: %s", label, attempt + 1, e)
                if attempt == 0:
                    _time.sleep(1)
        return None

    # 1. Claude Code CLI (works with subscription -- no API key needed)
    #    NEVER pass --fast -- fast mode is strictly forbidden for Claude Code.
    #    Subscription is fixed-cost; fast mode degrades output for the same price.
    def _try_claude_cli() -> Optional[str]:
        try:
            result = subprocess.run(
                ['claude', '-p', prompt, '--output-format', 'text'],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except FileNotFoundError:
            return None  # claude CLI not on PATH -- no point retrying
        return None

    r = _with_retry(_try_claude_cli, "claude CLI")
    if r is not None:
        return r

    # 2. Anthropic Python SDK
    if env_vars.get('ANTHROPIC_API_KEY'):
        def _try_anthropic() -> Optional[str]:
            from core.llm import AnthropicProvider
            provider = AnthropicProvider(config={
                "api_key": env_vars['ANTHROPIC_API_KEY'],
            })
            response = provider.invoke(
                prompt=prompt,
                system_prompt="You extract structured project metadata. Output only JSON.",
                model="haiku", max_tokens=1024, temperature=0.2, timeout=30,
            )
            return response.content.strip() or None

        r = _with_retry(_try_anthropic, "AnthropicProvider")
        if r is not None:
            return r

    # 3. AWS Bedrock
    if env_vars.get('AWS_PROFILE') or env_vars.get('AWS_ACCESS_KEY_ID'):
        def _try_bedrock() -> Optional[str]:
            from core.llm import BedrockProvider
            provider = BedrockProvider(config={
                "aws_region": env_vars.get('AWS_REGION', 'us-east-1'),
                "aws_profile": env_vars.get('AWS_PROFILE'),
            })
            response = provider.invoke(
                prompt=prompt,
                system_prompt="You extract structured project metadata. Output only JSON.",
                model="haiku", max_tokens=1024, temperature=0.2, timeout=30,
            )
            return response.content.strip() or None

        r = _with_retry(_try_bedrock, "BedrockProvider")
        if r is not None:
            return r

    # 4. Ollama
    def _try_ollama() -> Optional[str]:
        from core.llm import OllamaProvider
        provider = OllamaProvider(config={"host": "http://localhost:11434"})
        response = provider.invoke(
            prompt=prompt, max_tokens=1024, temperature=0.2, timeout=60,
        )
        return response.content.strip() or None

    r = _with_retry(_try_ollama, "OllamaProvider")
    if r is not None:
        return r

    print(print_yellow("  AI suggestions unavailable -- using defaults"))
    return None


# ---------------------------------------------------------------------------
# Wizard
# ---------------------------------------------------------------------------

def _write_preliminary_config(config_file: Path, cfg: Dict[str, Any]) -> None:
    """Write a minimal project-config.json so the dashboard picks up the name early.

    Uses the same ``project.name`` structure the dashboard expects.
    """
    if config_file is None:
        return
    try:
        ensure_dir(config_file.parent)
        project = cfg.get("project", {})
        data = {"project": {"name": project.get("name", "")}, "preliminary": True}
        # Merge with existing file if present (e.g. after backtrack restart)
        if config_file.exists():
            try:
                existing = json.loads(config_file.read_text())
                existing["project"] = data["project"]
                existing["preliminary"] = True
                data = existing
            except (json.JSONDecodeError, OSError):
                pass
        config_file.write_text(json.dumps(data, indent=2))
    except Exception as e:
        logger.warning("Preliminary config write failed: %s", e)


def _run_wizard(
    ai: Dict[str, Any],
    env_info: Dict[str, Any],
    provider_inventory: Dict[str, Any],
    config_file: Path = None,
    mem=None,
) -> Optional[Dict[str, Any]]:
    """Run the 10-step interactive wizard. Returns config dict or None.

    Args:
        ai: AI-inferred project defaults from reference materials.
        env_info: Detected environment info (git URL, branch, reference files).
        provider_inventory: Provider inventory dict loaded from provider-inventory.json
                           (written by Task 002). Contains credentials, detected_providers,
                           ollama_hosts, ollama_models, env_vars, and health info.
        config_file: Path for preliminary config writes (dashboard integration).
        mem: Optional TaskMemory instance for mid-wizard checkpoints.
    """
    # Extract provider info from inventory
    credentials = provider_inventory.get("credentials", {})
    has_aws = credentials.get("has_aws", False)
    has_anthropic = credentials.get("has_anthropic", False)
    has_ollama = credentials.get("has_ollama", False)
    detected_providers = provider_inventory.get("detected_providers", [])
    ollama_hosts = provider_inventory.get("ollama_hosts", [])
    inventory_ollama_models = provider_inventory.get("ollama_models", {})
    env_vars = provider_inventory.get("env_vars", dict(os.environ))

    total_steps = 10

    # Accumulate answers
    cfg: Dict[str, Any] = {}

    # -- Step 1: Project Identity ------------------------------------------
    _step_header("Project Identity", 1, total_steps)

    name = _prompt_text(
        "PROJECT NAME",
        "Short identifier for state, logs, and commits.\n  Lowercase with hyphens, max 24 characters.",
        ai.get("project_name"),
        validator=_validate_project_name,
    )
    if name is None:
        return None

    desc = _prompt_text(
        "DESCRIPTION",
        "One-sentence summary of this project.",
        ai.get("description"),
    )
    if desc is None:
        return None

    goal = _prompt_text(
        "PRIMARY GOAL",
        "What should the pipeline produce?",
        ai.get("primary_goal"),
    )
    if goal is None:
        return None

    cfg["project"] = {
        "name": name,
        "description": desc or name,
        "primary_goal": goal or desc or name,
    }

    # Write preliminary config so the dashboard shows the project name immediately
    _write_preliminary_config(config_file, cfg)

    # -- Step 2: Project Type ----------------------------------------------
    _step_header("Project Type", 2, total_steps)
    print("  Determines which phase templates and task shapes the pipeline uses.")
    print("  Choose a primary type, or select " + print_cyan("hybrid") + " to describe a combination.")
    print()

    type_options = PROJECT_TYPES + [("hybrid", "Describe a custom combination of needs")]
    type_idx = _prompt_selection(
        type_options,
        ai_suggestion=ai.get("type"),
    )
    if type_idx is None:
        return None

    chosen_type = type_options[type_idx][0]

    if chosen_type == "hybrid":
        print("  Describe your project's combination of needs.")
        print(print_dim("  e.g. \"API backend + React frontend + CLI tooling\""))
        print()
        clear_input_buffer()
        hybrid_desc = prompt_user("  > ").strip()
        if hybrid_desc.lower() in ('q', 'quit'):
            return None
        if not hybrid_desc:
            hybrid_desc = "hybrid project"
        cfg["project"]["type"] = "hybrid"
        cfg["project"]["type_detail"] = hybrid_desc
    else:
        cfg["project"]["type"] = chosen_type

    # Checkpoint: project identity captured
    if mem:
        mem.checkpoint("Project identity configured")

    # -- Step 3: Pipeline Mode + Human Gates -------------------------------
    _step_header("Pipeline Mode", 3, total_steps)
    print("  Controls which phases run. Each mode includes a different set of phases.")
    print()

    mode_idx = _prompt_pipeline_mode()
    if mode_idx is None:
        return None

    mode_key, _, included_phases = PIPELINE_MODES[mode_idx]
    skip_phases = [p for p in range(10) if p not in included_phases]

    print()
    print(print_bold("  HUMAN GATES"))
    print()
    print("  Phases that pause for your approval before continuing.")
    print()

    # Default gates filtered to only included phases
    default_gates = [g for g in DEFAULT_HUMAN_GATES if g in included_phases]
    gates = _prompt_toggle_list(
        {p: PHASE_NAMES[p] for p in included_phases},
        default_gates,
    )
    if gates is None:
        return None

    cfg["pipeline"] = {
        "mode": mode_key,
        "skip_phases": skip_phases,
        "human_gates": sorted(gates),
    }

    # -- Step 4: Repository ------------------------------------------------
    _step_header("Repository", 4, total_steps)

    detected_url = env_info.get("git_url", "")
    detected_branch = env_info.get("default_branch", "main")

    if detected_url:
        print(f"  Detected: {print_green(detected_url)}")
        print(f"  Branch:   {print_green(detected_branch)}")
        print()

    repo_url = _prompt_text(
        "REPOSITORY URL",
        "Git remote URL (leave blank for none).",
        detected_url or None,
        allow_empty=True,
    )
    if repo_url == _QUIT_SENTINEL:
        return None

    branch = _prompt_text(
        "DEFAULT BRANCH",
        "Primary branch name.",
        detected_branch,
        allow_empty=False,
    )
    if branch is None:
        return None

    cfg["repository"] = {
        "url": repo_url or None,
        "default_branch": branch,
        "pr_strategy": "feature-branch",
        "commit_strategy": "per-task",
        "push_strategy": "per-phase",
        "commit_format": "conventional",
    }

    # -- Step 5: LLM Configuration -----------------------------------------
    _step_header("LLM Configuration", 5, total_steps)

    # Build default provider chain from inventory detection results
    # If inventory has detected_providers, use those; otherwise infer from credentials
    if detected_providers:
        chain_providers = list(detected_providers)
    else:
        chain_providers = []
        if env_vars.get('ATOMIC_LLM_PROVIDER') == 'claude-code':
            chain_providers.append("claude-code")
        if has_anthropic and "claude-code" not in chain_providers:
            chain_providers.append("anthropic")
        if has_aws:
            chain_providers.append("aws-bedrock")
        if has_ollama:
            chain_providers.append("ollama")
        if not chain_providers:
            chain_providers = ["anthropic"]

    # Merge Ollama model info: prefer inventory data, supplement with live detection
    ollama_models: Dict[str, Any] = {}
    if inventory_ollama_models:
        # Inventory may be keyed by host or flat -- normalize to a flat model dict
        if isinstance(inventory_ollama_models, dict):
            # Check if it's {host: {models}} or {model_name: {info}}
            first_val = next(iter(inventory_ollama_models.values()), None) if inventory_ollama_models else None
            if isinstance(first_val, dict) and "size" in first_val:
                # Already flat: {model_name: {size, category}}
                ollama_models = dict(inventory_ollama_models)
            elif isinstance(first_val, dict):
                # Keyed by host: {host_url: {model_name: {size, category}}}
                for _host_url, host_models in inventory_ollama_models.items():
                    if isinstance(host_models, dict):
                        ollama_models.update(host_models)
            elif isinstance(first_val, list):
                # Keyed by host: {host_url: [model_name, ...]}
                for _host_url, model_list in inventory_ollama_models.items():
                    if isinstance(model_list, list):
                        for model_name in model_list:
                            ollama_models[model_name] = {"size": 0, "category": "general"}
            else:
                ollama_models = dict(inventory_ollama_models)
    elif has_ollama:
        # Fallback: live detection if no inventory data
        default_host = "http://localhost:11434"
        if ollama_hosts:
            default_host = ollama_hosts[0] if isinstance(ollama_hosts[0], str) else ollama_hosts[0].get("host", default_host)
        ollama_models = _detect_ollama_models(default_host)

    # Provider-aware defaults from config/models.json (with inline fallback)
    chain_priority = chain_providers[:]
    primary_provider = chain_providers[0] if chain_providers else "anthropic"
    atomic_root = Path(os.environ.get("ATOMIC_ROOT", Path.cwd()))
    profile = _get_provider_profile(primary_provider, atomic_root)
    models = dict(profile["models"])
    effort_level = profile["effort"]
    thinking_budget = profile["thinking_budget"]
    routing_strategy = "hybrid" if has_ollama else "all-cloud"

    # Load default phase roles from config/models.json
    phase_roles = _get_default_phase_roles(atomic_root)

    # Initialize Ollama/fallback defaults from inventory
    fallback_api_to_ollama = has_ollama
    fallback_ollama_to_api = True
    offline_mode = False

    # Build ollama_servers from inventory hosts
    if ollama_hosts:
        ollama_servers = []
        for h in ollama_hosts:
            if isinstance(h, str):
                ollama_servers.append({"host": h})
            elif isinstance(h, dict):
                ollama_servers.append(h)
            else:
                ollama_servers.append({"host": str(h)})
    elif has_ollama:
        ollama_servers = [{"host": "http://localhost:11434"}]
    else:
        ollama_servers = []

    # Show provider and default model
    models_cfg = _load_models_config(atomic_root)
    tier_defs = models_cfg.get("tier_definitions", {})
    default_tier = models.get("primary", "sonnet")
    default_ctx = tier_defs.get(default_tier, {}).get("context_window", 200000)
    ctx_label = "1M" if default_ctx >= 1000000 else f"{default_ctx // 1000}K"
    model_ids = models_cfg.get("model_ids", {}).get(primary_provider, {})
    default_model_id = model_ids.get(default_tier, default_tier)

    provider_labels = {
        "claude-code": "Claude Code Subscription",
        "anthropic": "Anthropic API",
        "aws-bedrock": "AWS Bedrock",
        "ollama": "Ollama (local)",
    }
    print(f"  Provider: {provider_labels.get(primary_provider, primary_provider)}")
    ext_note = ", extended thinking" if tier_defs.get(default_tier, {}).get("extended_thinking") else ""
    print(f"  Default model: {default_model_id} ({ctx_label} context{ext_note})")

    # Show provider health from inventory
    health = provider_inventory.get("health", {})
    if health:
        healthy = [p for p, info in health.items()
                   if (isinstance(info, dict) and info.get("status") == "ok") or info is True]
        if healthy:
            print(f"  Healthy providers: {print_green(', '.join(healthy))}")

    print()

    # Effort level selection
    if primary_provider in ("claude-code", "anthropic", "aws-bedrock"):
        print(print_dim("  Effort level determines how much compute each request uses."))
        # "low" effort is forbidden for Claude Code -- fixed-cost subscription
        if primary_provider == "claude-code":
            effort_options = [
                ("1", "high",   "Maximum reasoning depth (recommended)"),
                ("2", "medium", "Balanced cost/quality"),
            ]
        else:
            effort_options = [
                ("1", "high",   "Maximum reasoning depth (recommended)"),
                ("2", "medium", "Balanced cost/quality"),
            ]
        for num, level, desc_text in effort_options:
            print(f"    {num}. {level:<10} {print_dim(desc_text)}")
        print()
        clear_input_buffer()
        raw = prompt_user("  Choice [1]: ").strip()
        if raw.lower() in ('q', 'quit'):
            return None
        effort_map = {"1": "high", "2": "medium"}
        effort_level = effort_map.get(raw, effort_level or "high")
        print()

    # Extended thinking budget (API providers only)
    if primary_provider in ("anthropic", "aws-bedrock"):
        default_tb = thinking_budget if thinking_budget is not None else 10000
        print(print_bold("  EXTENDED THINKING BUDGET"))
        print(print_dim("  Maximum tokens for model reasoning (0 to disable)."))
        print()
        clear_input_buffer()
        raw = prompt_user(f"  Tokens [{default_tb}]: ").strip()
        if raw.lower() in ('q', 'quit'):
            return None
        if raw:
            try:
                thinking_budget = int(raw)
                if thinking_budget == 0:
                    thinking_budget = None
            except ValueError:
                pass
        print()

    # Ollama configuration (only if detected)
    if has_ollama:
        print(print_bold("  LOCAL MODELS (Ollama)"))
        print()

        # Show all known hosts from inventory
        if ollama_servers:
            hosts_display = [s.get("host", s) if isinstance(s, dict) else s for s in ollama_servers]
            print(f"  Hosts: {', '.join(hosts_display)}")
        else:
            print(f"  Detected at: http://localhost:11434")

        if ollama_models:
            print()
            for model_name, info in list(ollama_models.items())[:6]:
                category = info.get("category", "general")
                size_gb = info.get("size", 0) / (1024 ** 3)
                if size_gb > 0:
                    print(f"    {model_name} ({category}, {size_gb:.0f}GB)")
                else:
                    print(f"    {model_name} ({category})")
            remaining = len(ollama_models) - 6
            if remaining > 0:
                print(print_dim(f"    ... and {remaining} more"))
        print()

        if primary_provider != "ollama":
            clear_input_buffer()
            raw = prompt_user("  Enable Ollama as fallback? [Y/n]: ").strip().lower()
            if raw in ('q', 'quit'):
                return None
            if raw in ('n', 'no'):
                fallback_api_to_ollama = False

        clear_input_buffer()
        raw = prompt_user("  Allow offline-only mode? [n]: ").strip().lower()
        if raw in ('q', 'quit'):
            return None
        if raw in ('y', 'yes'):
            offline_mode = True
        print()

    # Closing message
    print(print_dim("  Model assignments are shown before each task starts."))
    print(print_dim("  You can override any agent's model at that point."))
    print()
    print(print_green("  \u2713 LLM configuration saved"))
    print()

    # Build routing map from strategy
    if routing_strategy == "all-cloud":
        routing = {"critical": "cloud", "bulk": "cloud", "quick": "fast", "background": "cloud"}
    elif routing_strategy == "all-local":
        routing = {"critical": "local", "bulk": "local", "quick": "local", "background": "local"}
    else:  # hybrid
        routing = {"critical": "cloud", "bulk": "local", "quick": "fast", "background": "local"}

    cfg["providers"] = {
        "chain_priority": chain_priority,
        "models": models,
        "phase_roles": phase_roles,
        "effort_level": effort_level,
        "thinking_budget": thinking_budget,
        "ollama": {
            "enabled": has_ollama,
            "servers": ollama_servers,
            "models": ollama_models,
            "failover": fallback_api_to_ollama,
        },
        "routing": routing,
        "fallback": {
            "api_to_ollama": fallback_api_to_ollama,
            "ollama_to_api": fallback_ollama_to_api,
            "offline_mode": offline_mode,
        },
    }

    cfg["llm"] = {
        "primary_provider": chain_priority[0] if chain_priority else "anthropic",
        "primary_model": models.get("primary"),
        "fast_model": models.get("fast"),
        "local_fallback": has_ollama,
        "effort_level": effort_level,
        "thinking_budget": thinking_budget,
    }

    # Checkpoint: LLM and provider configuration captured
    if mem:
        mem.checkpoint("LLM and provider configuration")

    # -- Step 6: Agent Assignment ------------------------------------------
    _step_header("Agent Assignment", 6, total_steps)

    # Default agent tier from provider profile (opus for claude-code, sonnet for API)
    default_agent_tier = models.get("primary", "sonnet")

    # Build tier descriptions from config (context windows vary by provider)
    try:
        from core.llm.resolver import get_resolver
        _resolver = get_resolver()
        _tier_defs = _resolver._defaults.get("tier_definitions", {})
        _prov = primary_provider or _resolver._detect_bootstrap_provider() or "claude-code"
        _prov_ctx = _resolver._defaults.get("provider_overrides", {}).get(_prov, {}).get("context_window")
    except Exception as e:
        logger.debug("Failed to load tier definitions from resolver: %s", e)
        _tier_defs = {}
        _prov_ctx = None

    def _ctx_label(tier_name):
        ctx = _tier_defs.get(tier_name, {}).get("context_window", 200_000)
        if _prov_ctx:
            ctx = min(ctx, _prov_ctx)
        return f"{ctx // 1000}K" if ctx < 1_000_000 else "1M"

    tier_descriptions = {
        "opus": f"maximum capability, {_ctx_label('opus')} context",
        "sonnet": f"balanced speed/quality, {_ctx_label('sonnet')} context",
        "haiku": f"fast/lightweight, {_ctx_label('haiku')} context",
    }
    tier_desc = tier_descriptions.get(default_agent_tier, "")

    print(f"  Default agent model: {default_agent_tier} ({tier_desc})")
    print()
    print(print_dim("  Each phase selects the best agents for its tasks."))
    print(print_dim("  You can override any agent's model before each task runs."))
    print()

    clear_input_buffer()
    accept = prompt_user("  Accept defaults? [Y/n]: ").strip().lower()
    if accept in ('q', 'quit'):
        return None

    agent_tier = default_agent_tier

    if accept in ('n', 'no'):
        print()
        print(print_bold("  DEFAULT AGENT MODEL"))
        print()
        for i, tier in enumerate(MODEL_TIERS):
            desc_text = tier_descriptions.get(tier, "")
            marker = " (default)" if tier == default_agent_tier else ""
            print(f"    {i + 1}. {tier:<10} {print_dim(desc_text)}{marker}")
        print()
        default_idx = MODEL_TIERS.index(default_agent_tier) + 1 if default_agent_tier in MODEL_TIERS else 2
        clear_input_buffer()
        raw = prompt_user(f"  Tier [{default_idx}]: ").strip()
        if raw.lower() in ('q', 'quit'):
            return None
        try:
            idx = int(raw) - 1 if raw else (default_idx - 1)
            if 0 <= idx < len(MODEL_TIERS):
                agent_tier = MODEL_TIERS[idx]
        except ValueError:
            pass
        print()

    cfg["agents"] = {
        "default_tier": agent_tier,
        "source": "local",
        "phase_assignments": {f"phase_{i}": "infer" for i in range(10)},
    }

    # -- Step 7: Audit Configuration ---------------------------------------
    _step_header("Audit Configuration", 7, total_steps)

    default_audit_profile = "thorough"
    default_failure_mode = "loop-until-pass"
    default_severity = ["critical", "high", "medium", "low"]

    audit_profile_desc = dict(AUDIT_PROFILES).get(default_audit_profile, "")
    print(f"  Profile:       {default_audit_profile} ({audit_profile_desc})")
    failure_mode_desc = dict(FAILURE_MODES).get(default_failure_mode, "")
    print(f"  Failure mode:  {default_failure_mode} ({failure_mode_desc})")
    print(f"  Severity:      {', '.join(default_severity)}")
    print()

    clear_input_buffer()
    accept = prompt_user("  Accept defaults? [Y/n]: ").strip().lower()
    if accept in ('q', 'quit'):
        return None

    audit_profile = default_audit_profile
    failure_mode = default_failure_mode
    severity_filter = list(default_severity)

    if accept in ('n', 'no'):
        # Sub-prompt 1: Profile
        print()
        print(print_bold("  AUDIT PROFILE"))
        print()
        prof_idx = _prompt_selection(AUDIT_PROFILES, default_index=0)
        if prof_idx is None:
            return None
        audit_profile = AUDIT_PROFILES[prof_idx][0]

        # Sub-prompt 2: Failure mode
        print(print_bold("  FAILURE MODE"))
        print()
        fm_idx = _prompt_selection(FAILURE_MODES, default_index=0)
        if fm_idx is None:
            return None
        failure_mode = FAILURE_MODES[fm_idx][0]

        # Sub-prompt 3: Severity filter
        print(print_bold("  SEVERITY FILTER"))
        print(print_dim("  Toggle levels (comma-separated numbers):"))
        print()
        severity_map = {i: s for i, s in enumerate(SEVERITY_LEVELS)}
        default_sev_set = {0, 1, 2, 3}  # all levels
        sev_result = _prompt_toggle_list(severity_map, sorted(default_sev_set))
        if sev_result is None:
            return None
        severity_filter = [SEVERITY_LEVELS[i] for i in sev_result if i < len(SEVERITY_LEVELS)]
        if not severity_filter:
            severity_filter = list(SEVERITY_LEVELS)
        print()

    cfg["audits"] = {
        "default_profile": audit_profile,
        "failure_mode": failure_mode,
        "severity_filter": severity_filter,
    }

    # -- Step 8: Sandbox & Security ----------------------------------------
    _step_header("Sandbox & Security", 8, total_steps)

    print(print_bold("  COMMAND APPROVAL"))
    print()
    cmd_idx = _prompt_selection(COMMAND_APPROVAL_MODES, default_index=0)
    if cmd_idx is None:
        return None

    print()
    print(print_bold("  NETWORK MODE"))
    print()
    net_idx = _prompt_selection(NETWORK_MODES, default_index=0)  # internet first
    if net_idx is None:
        return None

    cfg["sandbox"] = {
        "allowed_paths": None,
        "forbidden_paths": [".env*", "secrets/"],
        "forbidden_commands": ["rm -rf /"],
        "command_approval_mode": COMMAND_APPROVAL_MODES[cmd_idx][0],
        "network_mode": NETWORK_MODES[net_idx][0],
        "network_access": "fetch-only" if NETWORK_MODES[net_idx][0] == "internet" else "none",
        "blocked_ips": ["169.254.169.254/32"],
    }

    # -- Step 9: Constraints -----------------------------------------------
    _step_header("Constraints (optional)", 9, total_steps)
    print("  Any technical or compliance constraints? Press Enter to skip each.")
    print()

    ai_constraints = ai.get("technical_constraints")
    ai_hint = None
    if ai_constraints and isinstance(ai_constraints, list):
        ai_hint = ", ".join(ai_constraints)

    tech = _prompt_text(
        "TECHNICAL CONSTRAINTS",
        "Comma-separated list (e.g., Python 3.9+, PostgreSQL, Docker).",
        ai_hint,
        allow_empty=True,
    )
    if tech == _QUIT_SENTINEL:
        return None

    infra = _prompt_text(
        "INFRASTRUCTURE",
        "Target environment (e.g., AWS GovCloud, on-prem).",
        None,
        allow_empty=True,
    )
    if infra == _QUIT_SENTINEL:
        return None

    cfg["constraints"] = {
        "technical": [s.strip() for s in tech.split(',')] if tech else None,
        "infrastructure": infra or None,
        "compliance": None,
        "dependencies": None,
    }

    # -- Step 10: Summary & Confirm ----------------------------------------
    _step_header("Summary", 10, total_steps)
    _show_summary(cfg)

    clear_input_buffer()
    choice = prompt_user("  Approve this configuration? [Y/n/q]: ").strip().lower()
    if choice in ('q', 'quit'):
        return None
    if choice in ('n', 'no'):
        print(print_yellow("  Restarting wizard..."))
        print()
        return "RESTART"

    # Fill in auto-defaults that are not prompted
    _apply_auto_defaults(cfg)

    return cfg


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

_QUIT_SENTINEL = object()


def _step_header(title: str, step: int, total: int) -> None:
    """Print wizard step header."""
    print()
    print(print_cyan("\u2501" * 60))
    right = f"Step {step} of {total}"
    left = "  ATOMIC CLAUDE Setup"
    padding = 60 - len(left) - len(right) - 2
    print(print_bold(left) + " " * max(padding, 2) + print_dim(right))
    print(print_cyan("\u2501" * 60))
    print()
    print(print_bold(f"  {title}"))
    print()


def _prompt_text(
    label: str,
    help_text: str,
    ai_suggestion: Optional[str] = None,
    validator=None,
    allow_empty: bool = False,
) -> Optional[str]:
    """
    Prompt for a text value.

    Returns the value, empty string if allowed, or None to quit.
    For allow_empty=True, returns _QUIT_SENTINEL on quit.
    """
    print(f"  {print_bold(label)}")
    print()
    for line in help_text.split('\n'):
        print(f"  {print_dim(line)}")
    print()

    if ai_suggestion:
        print(f"    AI suggestion:  {print_green(ai_suggestion)}")
        print()

    clear_input_buffer()

    while True:
        default_hint = ai_suggestion or ""
        if default_hint:
            raw = prompt_user(f"  > [{default_hint}] ").strip()
        else:
            raw = prompt_user("  > ").strip()

        if raw.lower() in ('q', 'quit'):
            if allow_empty:
                return _QUIT_SENTINEL
            return None

        value = raw or (ai_suggestion or "")

        if not value and not allow_empty:
            print(print_red("    Value required. Enter 'q' to quit."))
            continue

        if validator:
            error = validator(value)
            if error:
                print(print_red(f"    {error}"))
                continue

        print()
        return value


def _prompt_pipeline_mode(default_index: int = 0) -> Optional[int]:
    """
    Prompt for pipeline mode selection with phase breakdown.
    Returns 0-based index or None to quit.
    """
    all_phases = set(range(10))

    for i, (key, desc, included) in enumerate(PIPELINE_MODES):
        num = f"{i + 1}."
        print(f"    {num:>3} {print_bold(key)}")
        print(f"        {print_dim(desc)}")

        included_names = [f"{p}-{PHASE_NAMES[p]}" for p in sorted(included)]
        skipped = sorted(all_phases - set(included))
        skipped_names = [f"{p}-{PHASE_NAMES[p]}" for p in skipped]

        print(f"        Phases: {print_green(', '.join(included_names))}")
        if skipped_names:
            print(f"        Skips:  {print_dim(', '.join(skipped_names))}")
        print()

    clear_input_buffer()
    while True:
        raw = prompt_user(f"  Choice [{default_index + 1}]: ").strip()

        if raw.lower() in ('q', 'quit'):
            return None

        if not raw:
            return default_index

        try:
            chosen = int(raw) - 1
        except ValueError:
            print(print_red(f"    Enter 1-{len(PIPELINE_MODES)} or 'q' to quit."))
            continue

        if 0 <= chosen < len(PIPELINE_MODES):
            return chosen

        print(print_red(f"    Enter 1-{len(PIPELINE_MODES)} or 'q' to quit."))


def _prompt_selection(
    options: List[Tuple[str, str]],
    ai_suggestion: Optional[str] = None,
    default_index: int = 0,
) -> Optional[int]:
    """
    Prompt for numbered selection.
    Returns 0-based index or None to quit.
    """
    ai_idx = None
    for i, (key, _) in enumerate(options):
        if ai_suggestion and key == ai_suggestion:
            ai_idx = i

    for i, (key, desc) in enumerate(options):
        num = f"{i + 1}."
        marker = ""
        if ai_idx is not None and i == ai_idx:
            marker = print_cyan("  << AI")
        print(f"    {num:>3} {key:<16} {print_dim(desc)}{marker}")

    print()

    effective_default = (ai_idx if ai_idx is not None else default_index) + 1

    clear_input_buffer()
    while True:
        raw = prompt_user(f"  Choice [{effective_default}]: ").strip()

        if raw.lower() in ('q', 'quit'):
            return None

        if not raw:
            chosen = effective_default - 1
        else:
            try:
                chosen = int(raw) - 1
            except ValueError:
                print(print_red(f"    Enter 1-{len(options)} or 'q' to quit."))
                continue

        if 0 <= chosen < len(options):
            print()
            return chosen

        print(print_red(f"    Enter 1-{len(options)} or 'q' to quit."))


def _prompt_toggle_list(
    items: Dict[int, str],
    defaults: List[int],
) -> Optional[List[int]]:
    """
    Show a toggle checklist. Returns list of selected keys or None to quit.
    """
    selected = set(defaults)

    # Display in two columns
    keys = sorted(items.keys())
    mid = (len(keys) + 1) // 2

    for row in range(mid):
        left_k = keys[row]
        left_mark = "*" if left_k in selected else " "
        left_str = f"    [{left_mark}] {left_k} {items[left_k]:<16}"

        right_str = ""
        right_idx = row + mid
        if right_idx < len(keys):
            right_k = keys[right_idx]
            right_mark = "*" if right_k in selected else " "
            right_str = f"[{right_mark}] {right_k} {items[right_k]}"

        print(f"{left_str}{right_str}")

    print()
    print(print_dim("  Toggle (comma-separated numbers), or Enter for defaults:"))

    clear_input_buffer()
    raw = prompt_user("  > ").strip()

    if raw.lower() in ('q', 'quit'):
        return None

    if not raw:
        return sorted(selected)

    # Parse toggles
    for part in raw.split(','):
        part = part.strip()
        try:
            num = int(part)
            if num in items:
                if num in selected:
                    selected.discard(num)
                else:
                    selected.add(num)
        except ValueError:
            pass

    print()
    return sorted(selected)


def _show_summary(cfg: Dict[str, Any]) -> None:
    """Show configuration summary."""
    project = cfg.get("project", {})
    pipeline = cfg.get("pipeline", {})
    repo = cfg.get("repository", {})
    sandbox = cfg.get("sandbox", {})
    providers = cfg.get("providers", {})
    agents = cfg.get("agents", {})
    audits = cfg.get("audits", {})
    constraints = cfg.get("constraints", {})

    print(print_cyan("  PROJECT"))
    print(f"    Name:        {project.get('name')}")
    print(f"    Description: {project.get('description')}")
    print(f"    Type:        {project.get('type')}")
    print(f"    Goal:        {project.get('primary_goal')}")
    print()

    print(print_cyan("  PIPELINE"))
    print(f"    Mode:        {pipeline.get('mode')}")
    gates = pipeline.get('human_gates', [])
    gate_names = [PHASE_NAMES.get(g, str(g)) for g in gates]
    print(f"    Human Gates: {', '.join(gate_names)}")
    print()

    print(print_cyan("  REPOSITORY"))
    print(f"    URL:         {repo.get('url') or 'none'}")
    print(f"    Branch:      {repo.get('default_branch')}")
    print()

    print(print_cyan("  LLM PREFERENCES"))
    chain = providers.get("chain_priority", [])
    print(f"    Chain:       {' > '.join(chain) if chain else 'default'}")
    model_cfg = providers.get("models", {})
    print(f"    Primary:     {model_cfg.get('primary', 'sonnet')}")
    print(f"    Fast:        {model_cfg.get('fast', 'haiku')}")
    print(f"    Heavyweight: {model_cfg.get('heavyweight', 'opus')}")
    effort = providers.get("effort_level")
    thinking = providers.get("thinking_budget")
    if effort:
        print(f"    Effort:      {effort}")
    if thinking is not None:
        print(f"    Thinking:    {thinking} tokens")
    routing_display = providers.get("routing", {})
    if routing_display:
        r_summary = f"critical={routing_display.get('critical', '?')}, bulk={routing_display.get('bulk', '?')}"
        print(f"    Routing:     {r_summary}")
    pr = providers.get("phase_roles", {})
    if pr:
        customized = [f"{pid}={role}" for pid, role in sorted(pr.items())
                      if role not in (None, "")]
        if len(customized) <= 4:
            print(f"    Phase roles: {', '.join(customized)}")
        else:
            print(f"    Phase roles: {len(customized)} configured")
    print()

    print(print_cyan("  AGENTS"))
    print(f"    Tier:        {agents.get('default_tier', 'sonnet')}")
    assignments = agents.get("phase_assignments", {})
    custom = [k for k, v in assignments.items() if v not in ("default", "infer")]
    if custom:
        print(f"    Custom:      {', '.join(custom)}")
    else:
        print(f"    Assignments: auto-select all")
    print()

    print(print_cyan("  AUDITS"))
    print(f"    Profile:     {audits.get('default_profile', 'standard')}")
    print(f"    Failure:     {audits.get('failure_mode', 'gate-high')}")
    sev = audits.get("severity_filter", ["critical", "high"])
    print(f"    Severity:    {', '.join(sev) if sev else 'all'}")
    print()

    print(print_cyan("  SANDBOX"))
    print(f"    Commands:    {sandbox.get('command_approval_mode')}")
    print(f"    Network:     {sandbox.get('network_mode')}")
    print()

    if constraints.get("technical") or constraints.get("infrastructure"):
        print(print_cyan("  CONSTRAINTS"))
        if constraints.get("technical"):
            print(f"    Technical:   {', '.join(constraints['technical'])}")
        if constraints.get("infrastructure"):
            print(f"    Infra:       {constraints['infrastructure']}")
        print()


# ---------------------------------------------------------------------------
# Auto-defaults (not prompted)
# ---------------------------------------------------------------------------

def _apply_auto_defaults(cfg: Dict[str, Any]) -> None:
    """Fill in fields that always get sensible defaults (only for sections not already set)."""
    cfg.setdefault("mcp", {"enabled": False, "servers": [], "tool_permissions": "none"})

    # Agents -- only set flat fallback if structured agents section wasn't set by wizard
    if "agents" not in cfg:
        cfg["agents"] = {
            "default_tier": "sonnet",
            "source": "local",
            "phase_assignments": {f"phase_{i}": "default" for i in range(10)},
        }

    # Providers -- only set if wizard didn't produce one
    if "providers" not in cfg:
        has_ollama = cfg.get("llm", {}).get("local_fallback", False)
        provider = cfg.get("llm", {}).get("primary_provider", "anthropic")
        atomic_root = Path(os.environ.get("ATOMIC_ROOT", Path.cwd()))
        fallback_profile = _get_provider_profile(provider, atomic_root)
        phase_roles_default = _get_default_phase_roles(atomic_root)
        cfg["providers"] = {
            "chain_priority": ["claude-code", provider],
            "models": dict(fallback_profile["models"]),
            "phase_roles": phase_roles_default,
            "effort_level": fallback_profile["effort"],
            "thinking_budget": fallback_profile["thinking_budget"],
            "ollama": {"enabled": has_ollama, "servers": [], "models": {}, "failover": True},
            "routing": {"critical": "cloud", "bulk": "cloud", "quick": "fast", "background": "cloud"},
            "fallback": {"api_to_ollama": has_ollama, "ollama_to_api": True, "offline_mode": False},
        }
    else:
        # Ensure effort/thinking/phase_roles keys exist even if wizard ran
        cfg["providers"].setdefault("effort_level", None)
        cfg["providers"].setdefault("thinking_budget", None)
        if "phase_roles" not in cfg["providers"]:
            atomic_root = Path(os.environ.get("ATOMIC_ROOT", Path.cwd()))
            cfg["providers"]["phase_roles"] = _get_default_phase_roles(atomic_root)

    # Audits -- only set if wizard didn't produce one
    cfg.setdefault("audits", {
        "default_profile": "standard",
        "failure_mode": "loop-until-pass",
        "severity_filter": ["critical", "high"],
    })

    cfg.setdefault("gardener", {
        "model": "infer",
        "threshold_percent": 75,
        "fallback_chain": [],
        "preserve_recent_exchanges": 4,
        "preserve_opening": True,
    })


# ---------------------------------------------------------------------------
# Ollama detection
# ---------------------------------------------------------------------------

def _detect_ollama_models(host: str) -> Dict[str, Any]:
    """
    Query an Ollama server for installed models and categorize them.

    Args:
        host: Ollama server URL (e.g. http://localhost:11434)

    Returns:
        Dict mapping model name to {"size": bytes, "category": "code"|"general"}
    """
    try:
        url = f"{host.rstrip('/')}/api/tags"
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        logger.debug("Ollama model detection failed for %s: %s", host, e)
        return {}

    result: Dict[str, Any] = {}
    for model_info in data.get("models", []):
        name = model_info.get("name", "")
        size = model_info.get("size", 0)

        # Categorize by name pattern
        name_lower = name.lower()
        category = "general"
        for pattern in _CODE_MODEL_PATTERNS:
            if pattern in name_lower:
                category = "code"
                break

        result[name] = {"size": size, "category": category}

    return result


# ---------------------------------------------------------------------------
# Schema validation (merged from former Task 002)
# ---------------------------------------------------------------------------

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
        if net_mode and net_mode not in VALID_NETWORK_MODES_SCHEMA:
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
                if tier and tier not in VALID_MODEL_TIERS_SCHEMA:
                    errors.append(f"providers.models.{role} '{tier}' is not valid (expected one of {VALID_MODEL_TIERS_SCHEMA})")
        effort = providers.get("effort_level")
        if effort is not None and effort not in VALID_EFFORT_LEVELS_SCHEMA:
            errors.append(f"providers.effort_level '{effort}' is not valid (expected one of {VALID_EFFORT_LEVELS_SCHEMA})")
        thinking = providers.get("thinking_budget")
        if thinking is not None and not isinstance(thinking, int):
            errors.append("providers.thinking_budget must be an integer")

    # --- agents ---
    agents = config.get("agents")
    if isinstance(agents, dict):
        tier = agents.get("default_tier")
        if tier and tier not in VALID_MODEL_TIERS_SCHEMA:
            errors.append(f"agents.default_tier '{tier}' is not valid (expected one of {VALID_MODEL_TIERS_SCHEMA})")

    # --- audits ---
    audits = config.get("audits")
    if isinstance(audits, dict):
        audit_profile = audits.get("default_profile")
        if audit_profile and audit_profile not in VALID_AUDIT_PROFILES:
            errors.append(f"audits.default_profile '{audit_profile}' is not valid (expected one of {VALID_AUDIT_PROFILES})")
        fm = audits.get("failure_mode")
        if fm and fm not in VALID_FAILURE_MODES_SCHEMA:
            errors.append(f"audits.failure_mode '{fm}' is not valid (expected one of {VALID_FAILURE_MODES_SCHEMA})")

    return errors


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
        repo["url"] = _detect_git_remote_url() or None

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


def _detect_git_remote_url() -> str:
    """Detect Git repository URL (for marker resolution)."""
    try:
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        logger.debug("Git remote URL detection failed: %s", e)
    return ""


def _detect_dir_name() -> str:
    """Get current directory name as fallback project name."""
    name = Path.cwd().name.lower()
    name = re.sub(r'[^a-z0-9\-]', '-', name)
    name = re.sub(r'-+', '-', name).strip('-')
    return name[:24] or "my-project"


# ---------------------------------------------------------------------------
# Saving
# ---------------------------------------------------------------------------

def _save_config(
    config_file: Path, extracted_file: Path, config: Dict[str, Any],
) -> None:
    """Write project-config.json and extracted-config.json."""
    ensure_dir(config_file.parent)

    # extracted-config.json is the full structured config
    write_file(extracted_file, json.dumps(config, indent=2))

    # Validate schema and resolve markers before writing project-config
    errors = _validate_config_schema(config)
    if errors:
        from core.utils.cli_ui import print_yellow
        print(print_yellow("  Configuration warnings:"))
        for err in errors:
            print(print_yellow(f"    - {err}"))
        print()

    _resolve_markers(config)

    # Re-write extracted config with resolved markers
    write_file(extracted_file, json.dumps(config, indent=2))

    # project-config.json: flatten extracted config into top-level keys
    # and mark as approved (replaces the former Task 002 config review step)
    project_config = {
        "setup_mode": "wizard",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "config_approved": True,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "extracted": config,
    }
    # Flatten extracted sections into top-level for downstream consumers
    for key in ('project', 'repository', 'sandbox', 'mcp', 'pipeline',
                'agents', 'llm', 'constraints', 'providers', 'gardener', 'audits'):
        if key in config:
            project_config[key] = config[key]
    write_file(config_file, json.dumps(project_config, indent=2))


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def _validate_project_name(value: str) -> Optional[str]:
    """Return error message or None if valid."""
    if len(value) > 24:
        return "Max 24 characters"
    if not re.match(r'^[a-z0-9][a-z0-9\-]*$', value):
        return "Lowercase letters, numbers, and hyphens only (must start with letter/number)"
    return None


def _slugify(name: str) -> str:
    """Convert a directory name to a valid project slug."""
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\-]', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    return slug[:24] or "my-project"


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 003: Setup Wizard")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                        help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                        help='Path to phase output directory')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir)
    sys.exit(0 if success else 1)
