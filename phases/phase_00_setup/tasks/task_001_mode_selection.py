"""
Task 001: Interactive Setup Wizard

Guided step-by-step wizard that collects project configuration interactively.
Uses an LLM (haiku) to pre-populate AI suggestions from reference materials.
Produces structured config directly — no setup.md needed.

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
from datetime import datetime

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
    ("strict",     "Prompt before every command"),
    ("cautious",   "Prompt for risky commands (recommended)"),
    ("permissive", "Auto-approve safe commands"),
]

NETWORK_MODES = [
    ("cui",      "Isolated — no outbound network"),
    ("internet", "Allow outbound network access"),
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
    ("quick",     "10-15 checks per audit point"),
    ("standard",  "20-30 checks per audit point"),
    ("thorough",  "40+ checks per audit point"),
]

FAILURE_MODES = [
    ("loop-until-pass", "Retry until all checks pass"),
    ("gate-all",        "Block on any failure"),
    ("gate-critical",   "Block only on critical severity"),
    ("gate-high",       "Block on critical + high severity"),
    ("report-only",     "Log failures, never block"),
]

SEVERITY_LEVELS = ["critical", "high", "medium", "low"]

# Provider-aware default profiles for Step 5
# Inline fallback — used only when config/models.json is missing.
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

# "low" is excluded for claude-code — subscription is fixed-cost, so "low"
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

def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 001: Interactive Setup Wizard.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, generate stub config without interactive prompts

    Returns:
        True if task completed successfully, False otherwise
    """
    config_file = output_dir / "project-config.json"
    extracted_file = output_dir / "extracted-config.json"
    project_root = atomic_root.parent

    # --- Launch web companion dashboard ---
    _launch_dashboard(atomic_root)

    # --- Step 0a: Credential check ---
    creds = _check_credentials(atomic_root, output_dir)
    if creds is None:
        return False

    has_aws, has_anthropic, has_ollama, env_vars = creds

    # --- Push detected provider to dashboard immediately ---
    _push_provider_to_dashboard(env_vars, has_aws, has_anthropic, has_ollama)

    # --- Step 0b: Detect environment ---
    env_info = _detect_environment(project_root)

    # --- Step 0c: Infer project defaults from reference materials ---
    ai_defaults = _infer_project_defaults(env_vars, project_root, env_info)

    # --- Run the 8-step wizard ---
    config = _run_wizard(ai_defaults, env_info, creds)
    if config is None:
        print(print_red("Setup aborted"))
        return False

    # --- Save config ---
    _save_config(config_file, extracted_file, config)

    print()
    print(print_green("Setup complete"))
    print(print_dim(f"  Config: {config_file}"))
    print()
    return True


# ---------------------------------------------------------------------------
# Dashboard launcher
# ---------------------------------------------------------------------------

def _launch_dashboard(atomic_root: Path) -> None:
    """Launch the web companion dashboard server and display URL."""
    dashboard_script = atomic_root / "dashboard" / "start-dashboard.sh"
    if not dashboard_script.exists():
        logger.debug("Dashboard script not found: %s", dashboard_script)
        return

    port = os.environ.get("ATOMIC_TASKS_PORT", "5174")

    try:
        env = os.environ.copy()
        env["ATOMIC_ROOT"] = str(atomic_root)
        subprocess.Popen(
            ["bash", str(dashboard_script)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        # Give server a moment to bind
        import time
        time.sleep(1.5)

        # Detect hostname/IP for remote access
        hostname = _get_hostname()
        url = f"http://{hostname}:{port}"

        title = "Web Companion Dashboard"
        inner = max(len(title), len(url)) + 4
        print(print_cyan(f"  ┌{'─' * inner}┐"))
        print(print_cyan("  │") + print_bold(f"  {title}") + " " * (inner - len(title) - 2) + print_cyan("│"))
        print(print_cyan("  │") + f"  {url}" + " " * (inner - len(url) - 2) + print_cyan("│"))
        print(print_cyan(f"  └{'─' * inner}┘"))
        print()
    except Exception as e:
        logger.debug("Dashboard launch failed: %s", e)


def _get_hostname() -> str:
    """Get the best hostname/IP for dashboard access."""
    import socket
    # Try to get a routable IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        pass
    # Fallback to hostname
    try:
        return socket.gethostname()
    except Exception:
        return "localhost"


def _push_provider_to_dashboard(
    env_vars: Dict[str, str], has_aws: bool, has_anthropic: bool, has_ollama: bool,
) -> None:
    """Push detected LLM provider + default model to dashboard immediately."""
    try:
        from orchestration.dashboard_sync import update_current_task_provider, init_session_tokens
    except ImportError:
        return

    # Use the resolver to get consistent provider/model info
    try:
        from core.llm.resolver import resolve_model, reset_resolver
        reset_resolver()
        rm = resolve_model("0-setup", "001")
        if rm.provider:
            update_current_task_provider(rm.provider, rm.model_id,
                                         phase_id="0-setup")
    except Exception:
        # Fallback: detect provider manually
        provider = None
        if env_vars.get('ATOMIC_LLM_PROVIDER') == 'claude-code':
            provider = "claude-code"
        elif has_anthropic:
            provider = "anthropic"
        elif has_aws:
            provider = "aws-bedrock"
        elif has_ollama:
            provider = "ollama"
        if provider:
            update_current_task_provider(provider)

    # Initialize token tracking file so dashboard shows zeros immediately
    init_session_tokens()


# ---------------------------------------------------------------------------
# Credential checking (reused logic from original Task 001)
# ---------------------------------------------------------------------------

def _check_credentials(
    atomic_root: Path, output_dir: Path
) -> Optional[Tuple[bool, bool, bool, Dict[str, str]]]:
    """
    Load .env, validate API keys, create secrets.json.

    Returns:
        (has_aws, has_anthropic, has_ollama, env_vars) or None on failure.
    """
    env_file = atomic_root / ".env"
    has_aws = False
    has_anthropic = False
    has_ollama = False

    print()
    print(print_bold("Validating API credentials..."))
    print()

    env_vars = dict(os.environ)

    # Load .env if it exists
    if env_file.exists():
        print(print_dim("Loading credentials from .env..."))
        _load_env_file(env_file, env_vars)

    # Check what we have
    has_aws, has_anthropic, has_ollama = _detect_credentials(env_vars)

    # If nothing found, run the credential wizard to create .env
    if not has_aws and not has_anthropic and not has_ollama:
        print(print_yellow("  No API credentials found"))
        print()
        result = _credential_wizard(env_file, env_vars)
        if result is None:
            return None
        has_aws, has_anthropic, has_ollama = result

    print()
    print(print_green("Credentials validated"))

    # Create secrets.json
    _create_secrets_file(output_dir, env_vars, has_aws, has_anthropic, has_ollama)
    return has_aws, has_anthropic, has_ollama, env_vars


def _create_secrets_file(
    output_dir: Path,
    env_vars: Dict[str, str],
    has_aws: bool,
    has_anthropic: bool,
    has_ollama: bool,
) -> None:
    """Create secrets.json from environment variables."""
    secrets_file = output_dir / "secrets.json"
    secrets: Dict[str, Any] = {}

    if has_aws:
        aws_region = env_vars.get('AWS_REGION', 'us-east-1')
        aws_profile = env_vars.get('AWS_PROFILE', 'default')
        bedrock_model = env_vars.get('ANTHROPIC_MODEL', '')
        if not bedrock_model:
            if aws_region.startswith('us-gov-'):
                bedrock_model = "us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0"
            else:
                bedrock_model = "anthropic.claude-sonnet-4-5-20250929-v1:0"
        secrets.update({
            "bedrock_enabled": True,
            "aws_region": aws_region,
            "aws_profile": aws_profile,
            "bedrock_model": bedrock_model,
            "use_bedrock": int(env_vars.get('CLAUDE_CODE_USE_BEDROCK', '1')),
        })

    if has_anthropic:
        secrets["anthropic_api_key"] = env_vars.get('ANTHROPIC_API_KEY')

    if has_ollama:
        secrets.update({"ollama_enabled": True, "ollama_host": "localhost:11434"})

    secrets["memory_enabled"] = True
    secrets["network_mode"] = env_vars.get('ATOMIC_NETWORK_MODE', 'cui')

    write_file(secrets_file, json.dumps(secrets, indent=2))

    if os.name != 'nt':
        try:
            os.chmod(secrets_file, 0o600)
        except Exception:
            pass

    print(print_dim(f"  Secrets file: {secrets_file}"))
    print()


# ---------------------------------------------------------------------------
# Credential helpers
# ---------------------------------------------------------------------------

def _load_env_file(env_file: Path, env_vars: Dict[str, str]) -> None:
    """Parse a .env file into env_vars dict."""
    try:
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    except Exception as e:
        print(print_yellow(f"  Failed to load .env: {e}"))


def _detect_credentials(
    env_vars: Dict[str, str],
) -> Tuple[bool, bool, bool]:
    """Check env_vars and system for AWS, Anthropic, Ollama credentials."""
    has_aws = False
    has_anthropic = False
    has_ollama = False

    # Claude Code subscription (no API key needed)
    if env_vars.get('ATOMIC_LLM_PROVIDER') == 'claude-code':
        print(print_green("  Claude Code subscription (no API key needed)"))
        # Treat as anthropic-compatible for provider selection
        has_anthropic = True
        return has_aws, has_anthropic, has_ollama

    if (env_vars.get('AWS_PROFILE') or
            env_vars.get('AWS_ACCESS_KEY_ID') or
            Path.home().joinpath('.aws', 'credentials').exists()):
        has_aws = True
        if env_vars.get('AWS_PROFILE'):
            print(print_green(f"  AWS profile: {env_vars['AWS_PROFILE']}"))
            print(print_dim(f"    Region: {env_vars.get('AWS_REGION', 'us-east-1')}"))
        else:
            print(print_green("  AWS credentials found"))

    if env_vars.get('ANTHROPIC_API_KEY'):
        has_anthropic = True
        print(print_green("  Anthropic API key loaded"))

    try:
        result = subprocess.run(
            ['curl', '-s', '--connect-timeout', '1', 'http://localhost:11434/api/tags'],
            capture_output=True, timeout=2,
        )
        if result.returncode == 0:
            has_ollama = True
            print(print_green("  Ollama available"))
    except Exception:
        pass

    return has_aws, has_anthropic, has_ollama


def _credential_wizard(
    env_file: Path, env_vars: Dict[str, str],
) -> Optional[Tuple[bool, bool, bool]]:
    """
    Interactive credential collection. Writes .env and returns credential flags.
    Returns None if user quits.
    """
    import getpass

    print(print_bold("  Credential Setup"))
    print()
    print("  Which LLM provider will you use?")
    print()
    print(f"    1. Claude Code       {print_dim('Subscription — no API key needed')}")
    print(f"    2. Anthropic API     {print_dim('Direct API key')}")
    print(f"    3. AWS Bedrock       {print_dim('AWS credentials or profile')}")
    print(f"    4. Ollama            {print_dim('Local models (localhost:11434)')}")
    print()

    clear_input_buffer()
    choice = prompt_user("  Provider [1]: ").strip() or "1"

    if choice.lower() in ('q', 'quit'):
        return None

    lines = [
        "# Atomic Claude 2.0 - Environment Configuration",
        f"# Generated by setup wizard: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]

    has_aws = False
    has_anthropic = False
    has_ollama = False

    if choice == "1":
        # Claude Code subscription
        has_anthropic = True  # Compatible with anthropic provider path
        env_vars['ATOMIC_LLM_PROVIDER'] = 'claude-code'
        lines.append("# Claude Code subscription (no API key required)")
        lines.append("ATOMIC_LLM_PROVIDER=claude-code")
        print()
        print(print_green("  Claude Code subscription configured"))

    elif choice == "2":
        # Anthropic API
        print()
        print(print_bold("  ANTHROPIC API KEY"))
        print(print_dim("  Get yours at: https://console.anthropic.com/settings/keys"))
        print()
        clear_input_buffer()
        api_key = getpass.getpass("  API key (hidden): ").strip()
        if not api_key:
            print(print_red("  API key required"))
            return None
        env_vars['ANTHROPIC_API_KEY'] = api_key
        has_anthropic = True
        lines.append("# Anthropic API")
        lines.append(f"ANTHROPIC_API_KEY={api_key}")
        masked = api_key[:7] + "..." + api_key[-4:] if len(api_key) > 15 else "***"
        print(print_green(f"  Anthropic API key set ({masked})"))

    elif choice == "3":
        # AWS Bedrock
        print()
        print(print_bold("  AWS BEDROCK"))
        print()

        clear_input_buffer()
        profile = prompt_user("  AWS profile name [default]: ").strip() or "default"

        region_options = [
            ("us-east-1",     "US East (Virginia)"),
            ("us-west-2",     "US West (Oregon)"),
            ("us-gov-west-1", "AWS GovCloud (West)"),
        ]
        print()
        for i, (r, desc) in enumerate(region_options):
            print(f"    {i + 1}. {r:<16} {print_dim(desc)}")
        print()
        clear_input_buffer()
        region_choice = prompt_user("  Region [1]: ").strip() or "1"
        try:
            region = region_options[int(region_choice) - 1][0]
        except (ValueError, IndexError):
            region = "us-east-1"

        env_vars['AWS_PROFILE'] = profile
        env_vars['AWS_REGION'] = region
        has_aws = True

        lines.append("# AWS Bedrock")
        lines.append(f"AWS_PROFILE={profile}")
        lines.append(f"AWS_REGION={region}")
        lines.append("CLAUDE_CODE_USE_BEDROCK=1")
        print()
        print(print_green(f"  AWS profile: {profile}, region: {region}"))

    elif choice == "4":
        # Ollama
        print()
        print(print_dim("  Checking Ollama at localhost:11434..."))
        try:
            result = subprocess.run(
                ['curl', '-s', '--connect-timeout', '2', 'http://localhost:11434/api/tags'],
                capture_output=True, timeout=3,
            )
            if result.returncode == 0:
                has_ollama = True
                print(print_green("  Ollama is running"))
            else:
                print(print_red("  Ollama not responding"))
                print(print_dim("  Start it with: ollama serve"))
                return None
        except Exception:
            print(print_red("  Ollama not reachable"))
            print(print_dim("  Start it with: ollama serve"))
            return None

        lines.append("# Ollama (local)")
        lines.append("OLLAMA_HOST=http://localhost:11434")
    else:
        print(print_red("  Invalid choice"))
        return None

    # Common settings
    lines.append("")
    lines.append("# Network mode: cui (restricted) or open (standard)")
    lines.append("ATOMIC_NETWORK_MODE=open")
    lines.append("")

    # Write .env
    write_file(env_file, '\n'.join(lines) + '\n')
    if os.name != 'nt':
        try:
            os.chmod(env_file, 0o600)
        except Exception:
            pass

    print()
    print(print_green(f"  Saved: {env_file}"))
    print(print_dim("  (permissions: owner read/write only)"))

    return has_aws, has_anthropic, has_ollama


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
    except Exception:
        pass

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
    except Exception:
        pass

    # Reference files — scan explicit names + common subdirectories
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
        except Exception:
            pass

    if not ref_text:
        print(print_dim("  No reference materials found — using directory defaults"))
        return fallback

    ref_count = len(env_info.get("reference_files", [])[:5])
    print(print_dim(f"  Found {ref_count} reference file(s)"))

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
        print(print_yellow("  AI suggestions unavailable — using defaults"))
        return fallback


def _llm_invoke(prompt: str, env_vars: Dict[str, str]) -> Optional[str]:
    """
    Invoke LLM using the best available method.
    Tries: claude CLI > Anthropic SDK > Bedrock SDK > Ollama.
    Returns response text or None.
    """
    # 1. Claude Code CLI (works with subscription — no API key needed)
    #    NEVER pass --fast — fast mode is strictly forbidden for Claude Code.
    #    Subscription is fixed-cost; fast mode degrades output for the same price.
    try:
        result = subprocess.run(
            ['claude', '-p', prompt, '--output-format', 'text'],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except FileNotFoundError:
        pass  # claude CLI not on PATH
    except Exception as e:
        logger.debug("claude CLI failed: %s", e)

    # 2. Anthropic Python SDK
    if env_vars.get('ANTHROPIC_API_KEY'):
        try:
            from core.llm import AnthropicProvider
            provider = AnthropicProvider(config={
                "api_key": env_vars['ANTHROPIC_API_KEY'],
            })
            response = provider.invoke(
                prompt=prompt,
                system_prompt="You extract structured project metadata. Output only JSON.",
                model="haiku", max_tokens=1024, temperature=0.2, timeout=30,
            )
            return response.content.strip()
        except Exception as e:
            logger.debug("AnthropicProvider failed: %s", e)

    # 3. AWS Bedrock
    if env_vars.get('AWS_PROFILE') or env_vars.get('AWS_ACCESS_KEY_ID'):
        try:
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
            return response.content.strip()
        except Exception as e:
            logger.debug("BedrockProvider failed: %s", e)

    # 4. Ollama
    try:
        from core.llm import OllamaProvider
        provider = OllamaProvider(config={"host": "http://localhost:11434"})
        response = provider.invoke(
            prompt=prompt, max_tokens=1024, temperature=0.2, timeout=60,
        )
        return response.content.strip()
    except Exception as e:
        logger.debug("OllamaProvider failed: %s", e)

    print(print_yellow("  AI suggestions unavailable — using defaults"))
    return None


# ---------------------------------------------------------------------------
# Wizard
# ---------------------------------------------------------------------------

def _run_wizard(
    ai: Dict[str, Any],
    env_info: Dict[str, Any],
    creds: Tuple[bool, bool, bool, Dict[str, str]],
) -> Optional[Dict[str, Any]]:
    """Run the 10-step interactive wizard. Returns config dict or None."""
    has_aws, has_anthropic, has_ollama, env_vars = creds
    total_steps = 10

    # Accumulate answers
    cfg: Dict[str, Any] = {}

    # ── Step 1: Project Identity ──────────────────────────────────────
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

    # ── Step 2: Project Type ──────────────────────────────────────────
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

    # ── Step 3: Pipeline Mode + Human Gates ───────────────────────────
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

    # ── Step 4: Repository ────────────────────────────────────────────
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

    # ── Step 5: LLM Configuration ────────────────────────────────────
    _step_header("LLM Configuration", 5, total_steps)

    # Build default provider chain from detected credentials
    detected_providers: List[str] = []
    if env_vars.get('ATOMIC_LLM_PROVIDER') == 'claude-code':
        detected_providers.append("claude-code")
    if has_anthropic and "claude-code" not in detected_providers:
        detected_providers.append("anthropic")
    if has_aws:
        detected_providers.append("aws-bedrock")
    if has_ollama:
        detected_providers.append("ollama")
    if not detected_providers:
        detected_providers = ["anthropic"]

    # Detect Ollama models if available
    ollama_models: Dict[str, Any] = {}
    if has_ollama:
        ollama_models = _detect_ollama_models("http://localhost:11434")

    # Provider-aware defaults from config/models.json (with inline fallback)
    chain_priority = detected_providers[:]
    primary_provider = detected_providers[0]
    atomic_root = Path(os.environ.get("ATOMIC_ROOT", Path.cwd()))
    profile = _get_provider_profile(primary_provider, atomic_root)
    models = dict(profile["models"])
    effort_level = profile["effort"]
    thinking_budget = profile["thinking_budget"]
    routing_strategy = "hybrid" if has_ollama else "all-cloud"

    # Load default phase roles from config/models.json
    phase_roles = _get_default_phase_roles(atomic_root)

    # Initialize Ollama/fallback defaults
    fallback_api_to_ollama = has_ollama
    fallback_ollama_to_api = True
    offline_mode = False
    ollama_servers = [{"host": "http://localhost:11434"}] if has_ollama else []

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
    print()

    # Effort level selection
    if primary_provider in ("claude-code", "anthropic", "aws-bedrock"):
        print(print_dim("  Effort level determines how much compute each request uses."))
        # "low" effort is forbidden for Claude Code — fixed-cost subscription
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
        for num, level, desc in effort_options:
            print(f"    {num}. {level:<10} {print_dim(desc)}")
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
        print(f"  Detected at: http://localhost:11434")
        if ollama_models:
            for model_name, info in list(ollama_models.items())[:6]:
                category = info.get("category", "general")
                size_gb = info.get("size", 0) / (1024 ** 3)
                if size_gb > 0:
                    print(f"    {model_name} ({category}, {size_gb:.0f}GB)")
                else:
                    print(f"    {model_name} ({category})")
        print()

        if primary_provider != "ollama":
            clear_input_buffer()
            raw = prompt_user("  Enable Ollama as fallback? [Y/n]: ").strip().lower()
            if raw in ('q', 'quit'):
                return None
            if raw in ('n', 'no'):
                fallback_api_to_ollama = False

        clear_input_buffer()
        raw = prompt_user("  Add additional Ollama hosts? [n]: ").strip().lower()
        if raw in ('q', 'quit'):
            return None
        if raw in ('y', 'yes'):
            print(print_dim("  One per line, blank line to finish:"))
            while True:
                clear_input_buffer()
                host_raw = prompt_user("    > ").strip()
                if not host_raw:
                    break
                if host_raw.lower() in ('q', 'quit'):
                    return None
                ollama_servers.append({"host": host_raw})

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

    # ── Step 6: Agent Assignment ──────────────────────────────────────
    _step_header("Agent Assignment", 6, total_steps)

    # Default agent tier from provider profile (opus for claude-code, sonnet for API)
    default_agent_tier = models.get("primary", "sonnet")

    tier_descriptions = {
        "opus": "maximum capability, 200K context",
        "sonnet": "balanced speed/quality, 200K context",
        "haiku": "fast/lightweight, 200K context",
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
            desc = tier_descriptions.get(tier, "")
            marker = " (default)" if tier == default_agent_tier else ""
            print(f"    {i + 1}. {tier:<10} {print_dim(desc)}{marker}")
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

    # ── Step 7: Audit Configuration ──────────────────────────────────
    _step_header("Audit Configuration", 7, total_steps)

    default_audit_profile = "standard"
    default_failure_mode = "gate-high"
    default_severity = ["critical", "high"]

    print(f"  Profile:       {default_audit_profile} (20-30 checks per audit point)")
    print(f"  Failure mode:  {default_failure_mode} (block on critical + high severity)")
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
        prof_idx = _prompt_selection(AUDIT_PROFILES, default_index=1)
        if prof_idx is None:
            return None
        audit_profile = AUDIT_PROFILES[prof_idx][0]

        # Sub-prompt 2: Failure mode
        print(print_bold("  FAILURE MODE"))
        print()
        fm_idx = _prompt_selection(FAILURE_MODES, default_index=3)
        if fm_idx is None:
            return None
        failure_mode = FAILURE_MODES[fm_idx][0]

        # Sub-prompt 3: Severity filter
        print(print_bold("  SEVERITY FILTER"))
        print(print_dim("  Toggle levels (comma-separated numbers):"))
        print()
        severity_map = {i: s for i, s in enumerate(SEVERITY_LEVELS)}
        default_sev_set = {0, 1}  # critical, high
        sev_result = _prompt_toggle_list(severity_map, sorted(default_sev_set))
        if sev_result is None:
            return None
        severity_filter = [SEVERITY_LEVELS[i] for i in sev_result if i < len(SEVERITY_LEVELS)]
        if not severity_filter:
            severity_filter = ["critical", "high"]
        print()

    cfg["audits"] = {
        "default_profile": audit_profile,
        "failure_mode": failure_mode,
        "severity_filter": severity_filter,
    }

    # ── Step 8: Sandbox & Security ────────────────────────────────────
    _step_header("Sandbox & Security", 8, total_steps)

    print(print_bold("  COMMAND APPROVAL"))
    print()
    cmd_idx = _prompt_selection(COMMAND_APPROVAL_MODES, default_index=1)
    if cmd_idx is None:
        return None

    print()
    print(print_bold("  NETWORK MODE"))
    print()
    net_idx = _prompt_selection(NETWORK_MODES, default_index=0)
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

    # ── Step 9: Constraints ───────────────────────────────────────────
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

    # ── Step 10: Summary & Confirm ────────────────────────────────────
    _step_header("Summary", 10, total_steps)
    _show_summary(cfg)

    clear_input_buffer()
    choice = prompt_user("  Approve this configuration? [Y/n/q]: ").strip().lower()
    if choice in ('q', 'quit'):
        return None
    if choice in ('n', 'no'):
        print(print_yellow("  Restarting wizard..."))
        print()
        return _run_wizard(ai, env_info, creds)

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
    print(print_cyan("━" * 60))
    right = f"Step {step} of {total}"
    left = "  ATOMIC CLAUDE Setup"
    padding = 60 - len(left) - len(right) - 2
    print(print_bold(left) + " " * max(padding, 2) + print_dim(right))
    print(print_cyan("━" * 60))
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
    routing = providers.get("routing", {})
    if routing:
        r_summary = f"critical={routing.get('critical', '?')}, bulk={routing.get('bulk', '?')}"
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

    # Agents — only set flat fallback if structured agents section wasn't set by wizard
    if "agents" not in cfg:
        cfg["agents"] = {
            "default_tier": "sonnet",
            "source": "local",
            "phase_assignments": {f"phase_{i}": "default" for i in range(10)},
        }

    # Providers — only set if wizard didn't produce one
    if "providers" not in cfg:
        has_ollama = cfg.get("llm", {}).get("local_fallback", False)
        provider = cfg.get("llm", {}).get("primary_provider", "anthropic")
        atomic_root = Path(os.environ.get("ATOMIC_ROOT", Path.cwd()))
        fallback_profile = _get_provider_profile(provider, atomic_root)
        phase_roles = _get_default_phase_roles(atomic_root)
        cfg["providers"] = {
            "chain_priority": ["claude-code", provider],
            "models": dict(fallback_profile["models"]),
            "phase_roles": phase_roles,
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

    # Audits — only set if wizard didn't produce one
    cfg.setdefault("audits", {
        "default_profile": "standard",
        "failure_mode": "gate-high",
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
# Saving
# ---------------------------------------------------------------------------

def _save_config(
    config_file: Path, extracted_file: Path, config: Dict[str, Any],
) -> None:
    """Write project-config.json and extracted-config.json."""
    ensure_dir(config_file.parent)

    # extracted-config.json is the full structured config
    write_file(extracted_file, json.dumps(config, indent=2))

    # project-config.json wraps it under 'extracted' for Task 002/003 compat
    wrapper = {
        "setup_mode": "wizard",
        "created_at": datetime.now().isoformat(),
        "extracted": config,
    }
    write_file(config_file, json.dumps(wrapper, indent=2))


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

    parser = argparse.ArgumentParser(description="Task 001: Interactive Setup Wizard")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                        help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                        help='Path to phase output directory')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir)
    sys.exit(0 if success else 1)
