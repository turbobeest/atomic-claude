"""
Task 002: Provider Detection

Load credentials, detect available LLM providers, health-check each one,
configure Ollama hosts, and produce provider-inventory.json.

Features:
- Loads .env and detects credentials in env vars / existing secrets.json
- Credential wizard if no credentials found (API key prompts)
- Creates/updates secrets.json
- Checks local Ollama at localhost:11434
- Offers to add remote LAN Ollama hosts (connectivity test + model listing)
- Health-checks all providers: Claude Code CLI, Anthropic API, AWS Bedrock, Ollama
- Builds provider-inventory.json for downstream consumption (Task 003)
- Pushes detected provider to dashboard
"""

import os
import sys
import json
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

# Provider imports (graceful degradation if SDK not installed)
try:
    from core.llm.claude_code import ClaudeCodeProvider
    HAS_CLAUDE_CODE = True
except ImportError:
    HAS_CLAUDE_CODE = False
    ClaudeCodeProvider = None

try:
    from core.llm.anthropic import AnthropicProvider
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    AnthropicProvider = None

try:
    from core.llm.bedrock import BedrockProvider
    HAS_BEDROCK = True
except ImportError:
    HAS_BEDROCK = False
    BedrockProvider = None

try:
    from core.llm.ollama import OllamaProvider
    HAS_OLLAMA = True
except ImportError:
    HAS_OLLAMA = False
    OllamaProvider = None

# Ollama model name patterns that indicate code-specialized models
_CODE_MODEL_PATTERNS = [
    "devstral", "granite-code", "codestral", "starcoder", "deepseek-coder",
    "codellama", "codegemma", "codegeex", "qwen2.5-coder", "wizardcoder",
]


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None) -> bool:
    """
    Execute Task 002: Provider Detection.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, generate stub config without interactive prompts
        mem: Optional TaskMemory instance for recording substantive memory

    Returns:
        True if task completed successfully, False otherwise
    """
    secrets_file = output_dir / "secrets.json"
    inventory_file = output_dir / "provider-inventory.json"

    print()
    print(print_cyan("Provider Detection"))
    print()

    # --- Step 1: Credential check ---
    creds = _check_credentials(atomic_root, output_dir)
    if creds is None:
        return False

    has_aws, has_anthropic, has_ollama, env_vars = creds

    # --- Step 2: Push detected provider to dashboard immediately ---
    _push_provider_to_dashboard(env_vars, has_aws, has_anthropic, has_ollama)

    # --- Step 3: Ollama host configuration (local + remote LAN) ---
    ollama_hosts = _configure_ollama_hosts(secrets_file, uat_mode)

    # --- Step 4: Health-check all providers ---
    provider_health = _health_check_providers(secrets_file, output_dir)

    # --- Step 5: Detect Ollama models per host ---
    ollama_models: Dict[str, List[str]] = {}
    for host in ollama_hosts:
        models = _list_ollama_models(host)
        if models:
            ollama_models[host] = models

    # --- Step 6: Build provider-inventory.json ---
    detected_providers: List[str] = []
    if env_vars.get('ATOMIC_LLM_PROVIDER') == 'claude-code':
        detected_providers.append("claude-code")
    if has_anthropic and "claude-code" not in detected_providers:
        detected_providers.append("anthropic")
    if has_aws:
        detected_providers.append("aws-bedrock")
    if has_ollama or ollama_hosts:
        detected_providers.append("ollama")

    inventory = {
        "detected_providers": detected_providers,
        "provider_health": provider_health,
        "ollama_hosts": ollama_hosts,
        "ollama_models": ollama_models,
        "credentials": {
            "has_aws": has_aws,
            "has_anthropic": has_anthropic,
            "has_ollama": has_ollama or len(ollama_hosts) > 0,
        },
        "detected_at": datetime.now().isoformat(),
    }

    ensure_dir(inventory_file.parent)
    write_file(inventory_file, json.dumps(inventory, indent=2))

    # --- Summary ---
    print()
    print(print_bold("  Provider Summary:"))
    print()
    for name, info in provider_health.items():
        status = info.get("status", "unknown")
        if status == "healthy":
            print(print_green(f"    ✓ {name} (healthy)"))
        elif status == "degraded":
            print(print_yellow(f"    ! {name} (degraded)"))
        else:
            print(print_red(f"    ✗ {name} (unavailable)"))
    print()

    if ollama_models:
        total_models = sum(len(m) for m in ollama_models.values())
        print(print_dim(f"    Ollama models: {total_models} across {len(ollama_models)} host(s)"))
        print()

    print(print_dim(f"  Inventory: {inventory_file}"))
    print()

    # Record substantive memory
    if mem:
        mem.finding(f"Detected providers: {', '.join(detected_providers)}")
        healthy = [k for k, v in provider_health.items()
                   if isinstance(v, dict) and v.get("status") == "healthy"]
        unavail = [k for k, v in provider_health.items()
                   if isinstance(v, dict) and v.get("status") == "unavailable"]
        mem.finding(f"Healthy: {', '.join(healthy) if healthy else 'none'}; "
                    f"Unavailable: {', '.join(unavail) if unavail else 'none'}")
        mem.decision(f"Primary chain: {' → '.join(detected_providers)}")
        cred_parts = []
        if has_anthropic:
            cred_parts.append("Anthropic")
        if has_aws:
            cred_parts.append("AWS")
        mem.configuration(f"Credentials: {', '.join(cred_parts) if cred_parts else 'none'}")
        mem.configuration(f"Ollama: {'enabled (' + ', '.join(ollama_hosts) + ')' if ollama_hosts else 'disabled'}")
        if ollama_models:
            total_m = sum(len(m) for m in ollama_models.values())
            mem.finding(f"Ollama models: {total_m} across {len(ollama_models)} host(s)")

    print(print_green("✓ Provider detection complete"))
    return True


# ---------------------------------------------------------------------------
# Credential checking
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

    print(print_bold("  Validating API credentials..."))
    print()

    env_vars = dict(os.environ)

    # Load .env if it exists
    if env_file.exists():
        print(print_dim("  Loading credentials from .env..."))
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
    print(print_green("  Credentials validated"))

    # Create secrets.json
    _create_secrets_file(output_dir, env_vars, has_aws, has_anthropic, has_ollama)
    return has_aws, has_anthropic, has_ollama, env_vars


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
    except Exception as e:
        logger.debug("Ollama local detection failed: %s", e)

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
        print(print_green("  Anthropic API key set"))

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
        except Exception as e:
            logger.debug("Ollama connectivity check failed during wizard: %s", e)
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
        except Exception as e:
            logger.warning("Failed to set permissions on %s: %s", env_file, e)

    print()
    print(print_green(f"  Saved: {env_file}"))
    print(print_dim("  (permissions: owner read/write only)"))

    return has_aws, has_anthropic, has_ollama


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

    ensure_dir(output_dir)
    write_file(secrets_file, json.dumps(secrets, indent=2))

    if os.name != 'nt':
        try:
            os.chmod(secrets_file, 0o600)
        except Exception as e:
            logger.warning("Failed to set permissions on %s: %s", secrets_file, e)

    print(print_dim(f"  Secrets file: {secrets_file}"))
    print()


# ---------------------------------------------------------------------------
# Dashboard provider push
# ---------------------------------------------------------------------------

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
        rm = resolve_model("0-setup", "002")
        if rm.provider:
            update_current_task_provider(rm.provider, rm.model_id,
                                         phase_id="0-setup")
    except Exception as e:
        logger.debug("Resolver-based dashboard push failed: %s", e)
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
# Ollama host configuration
# ---------------------------------------------------------------------------

def _configure_ollama_hosts(
    secrets_file: Path, uat_mode: bool
) -> List[str]:
    """
    Configure Ollama hosts — detect local and offer remote LAN hosts.

    Returns:
        List of Ollama host URLs (may be empty).
    """
    print(print_cyan("  OLLAMA HOSTS"))
    print()

    # Load existing config
    existing_hosts: List[str] = []
    if secrets_file.exists():
        try:
            secrets = json.loads(read_file(secrets_file))
            existing_hosts = secrets.get('ollama_hosts', [])
            # Migrate from legacy single-host key
            if not existing_hosts:
                legacy = secrets.get('ollama_host')
                if legacy:
                    host = legacy if legacy.startswith("http") else f"http://{legacy}"
                    existing_hosts = [host]
        except Exception as e:
            logger.debug("Failed to load existing secrets for Ollama hosts: %s", e)

    # Check local Ollama
    local_host = "http://localhost:11434"
    local_available = _check_ollama_host(local_host)

    if local_available:
        print(print_green(f"  ✓ Local Ollama ({local_host})"))
        if local_host not in existing_hosts:
            existing_hosts.insert(0, local_host)
    else:
        print(print_dim(f"  ○ Local Ollama not detected ({local_host})"))

    # Show any existing remote hosts
    for host in existing_hosts:
        if host == local_host:
            continue
        available = _check_ollama_host(host)
        if available:
            print(print_green(f"  ✓ Remote Ollama ({host})"))
        else:
            print(print_yellow(f"  ! Remote Ollama unreachable ({host})"))

    print()

    # Offer to add remote hosts
    if not uat_mode:
        print(print_bold("  Add remote Ollama hosts?"))
        print(print_dim("  Machines on your LAN running Ollama (e.g. GPU workstation)."))
        print(print_dim("  Format: hostname:port or IP:port (default port: 11434)"))
        print()

        clear_input_buffer()
        choice = prompt_user("  Add remote hosts? [n]: ").strip().lower()

        if choice in ('y', 'yes'):
            print(print_dim("  One host per line, blank line to finish:"))
            while True:
                clear_input_buffer()
                raw = prompt_user("    > ").strip()
                if not raw:
                    break

                # Normalize the URL
                host = raw
                if not host.startswith("http"):
                    host = f"http://{host}"
                if ":" not in host.split("//", 1)[-1]:
                    host = f"{host}:11434"

                # Test connectivity
                available = _check_ollama_host(host)
                if available:
                    print(print_green(f"    ✓ Connected to {host}"))
                    models = _list_ollama_models(host)
                    if models:
                        print(print_dim(f"      Models: {', '.join(models[:8])}"))
                        if len(models) > 8:
                            print(print_dim(f"      ... and {len(models) - 8} more"))
                else:
                    print(print_yellow(f"    ! Could not reach {host}"))
                    print(print_dim(f"      Adding anyway — it may come online later"))

                if host not in existing_hosts:
                    existing_hosts.append(host)

            print()

    # Write updated hosts back to secrets
    if existing_hosts and secrets_file.exists():
        try:
            secrets = json.loads(read_file(secrets_file))
            secrets['ollama_hosts'] = existing_hosts
            # Remove legacy single-host key
            secrets.pop('ollama_host', None)
            write_file(secrets_file, json.dumps(secrets, indent=2))
        except Exception as e:
            logger.debug("Failed to write updated Ollama hosts to secrets: %s", e)

    return existing_hosts


def _check_ollama_host(host: str) -> bool:
    """Check if an Ollama host is reachable."""
    try:
        url = f"{host}/api/tags"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception as e:
        logger.debug("Ollama host %s unreachable: %s", host, e)
        return False


def _list_ollama_models(host: str) -> List[str]:
    """List available models on an Ollama host."""
    try:
        url = f"{host}/api/tags"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [m.get("name", "") for m in data.get("models", [])]
    except Exception as e:
        logger.debug("Failed to list Ollama models on %s: %s", host, e)
        return []


def _detect_ollama_models_categorized(host: str) -> Dict[str, Any]:
    """
    Query an Ollama server for installed models and categorize them.

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
# Provider health checks
# ---------------------------------------------------------------------------

def _health_check_providers(
    secrets_file: Path, output_dir: Path,
) -> Dict[str, Dict[str, Any]]:
    """Run health checks on all available providers."""
    print(print_cyan("  LLM Provider Health:"))
    print()

    secrets: Dict[str, Any] = {}
    if secrets_file.exists():
        try:
            secrets = json.loads(read_file(secrets_file))
        except Exception as e:
            logger.debug("Failed to load secrets for health check: %s", e)

    # Read network mode from config
    config_file = output_dir / "project-config.json"
    network_mode = "internet"
    if config_file.exists():
        try:
            config = json.loads(read_file(config_file))
            network_mode = config.get("sandbox", {}).get("network_mode", "internet")
        except Exception as e:
            logger.debug("Failed to load project config: %s", e)

    provider_results: Dict[str, Dict[str, Any]] = {}

    # 1. Claude Code CLI
    if HAS_CLAUDE_CODE:
        try:
            provider = ClaudeCodeProvider()
            status = provider.health_check()
            use_bedrock = os.environ.get(
                "CLAUDE_CODE_USE_BEDROCK", ""
            ).lower() in ("1", "true", "yes")
            provider_results["Claude Code CLI"] = {
                "status": status.value,
                "cui_compatible": use_bedrock,
                "detail": "Bedrock backend" if use_bedrock else "",
            }
        except Exception as e:
            logger.debug("Claude Code CLI health check failed: %s", e)
            provider_results["Claude Code CLI"] = {
                "status": "unavailable", "cui_compatible": False,
                "detail": "error during check",
            }
    else:
        provider_results["Claude Code CLI"] = {
            "status": "unavailable", "cui_compatible": False,
            "detail": "module not available",
        }

    # 2. Anthropic API
    anthropic_key = (
        secrets.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY")
    )
    if anthropic_key:
        if HAS_ANTHROPIC:
            try:
                provider = AnthropicProvider({"api_key": anthropic_key})
                status = provider.health_check()
                provider_results["Anthropic API"] = {
                    "status": status.value, "cui_compatible": False, "detail": "",
                }
            except Exception as e:
                logger.debug("Anthropic API health check failed: %s", e)
                provider_results["Anthropic API"] = {
                    "status": "unavailable", "cui_compatible": False,
                    "detail": "error during check",
                }
        else:
            provider_results["Anthropic API"] = {
                "status": "unavailable", "cui_compatible": False,
                "detail": "anthropic SDK not installed",
            }

    # 3. AWS Bedrock
    if secrets.get("bedrock_enabled"):
        if HAS_BEDROCK:
            try:
                bedrock_config = {
                    "aws_region": secrets.get(
                        "aws_region", os.environ.get("AWS_REGION", "us-east-1")
                    ),
                }
                if secrets.get("aws_profile"):
                    bedrock_config["aws_profile"] = secrets["aws_profile"]
                provider = BedrockProvider(bedrock_config)
                status = provider.health_check()
                provider_results["AWS Bedrock"] = {
                    "status": status.value, "cui_compatible": True,
                    "detail": f"region: {bedrock_config['aws_region']}",
                }
            except Exception as e:
                logger.debug("AWS Bedrock health check failed: %s", e)
                provider_results["AWS Bedrock"] = {
                    "status": "unavailable", "cui_compatible": True,
                    "detail": "error during check",
                }
        else:
            provider_results["AWS Bedrock"] = {
                "status": "unavailable", "cui_compatible": True,
                "detail": "boto3 SDK not installed",
            }

    # 4. Ollama (supports multiple hosts)
    ollama_hosts = secrets.get("ollama_hosts")
    if not ollama_hosts:
        ollama_hosts = [secrets.get("ollama_host", "http://localhost:11434")]

    if HAS_OLLAMA:
        servers: Dict[str, Dict[str, Any]] = {}
        for host in ollama_hosts:
            try:
                provider = OllamaProvider({"host": host})
                status = provider.health_check()
                models: List[str] = []
                if status.value == "healthy":
                    models = provider.list_models()
                servers[host] = {"status": status.value, "models": models}
            except Exception as e:
                logger.debug("Ollama health check failed for %s: %s", host, e)
                servers[host] = {"status": "unavailable", "models": []}

        up = sum(1 for s in servers.values() if s["status"] in ("healthy", "degraded"))
        total = len(servers)
        if up == total:
            overall = "healthy"
        elif up > 0:
            overall = "degraded"
        else:
            overall = "unavailable"

        detail = f"{up}/{total} servers" if total > 1 else ""
        provider_results["Ollama"] = {
            "status": overall, "cui_compatible": True,
            "detail": detail, "servers": servers,
        }
    else:
        provider_results["Ollama"] = {
            "status": "unavailable", "cui_compatible": True,
            "detail": "module not available",
        }

    # Display results
    for name, result in provider_results.items():
        status_val = result["status"]
        detail = result.get("detail", "")

        if status_val == "healthy":
            suffix = f" ({detail})" if detail else ""
            print(print_green(f"    ✓ {name} (healthy){suffix}"))
        elif status_val == "degraded":
            suffix = f" ({detail})" if detail else ""
            print(print_yellow(f"    ! {name} (degraded){suffix}"))
        else:
            suffix = f" — {detail}" if detail else ""
            print(print_dim(f"    ✗ {name} (unavailable){suffix}"))

        # Show Ollama server details
        if status_val != "unavailable" and result.get("servers"):
            srv = result["servers"]
            if len(srv) == 1:
                info = next(iter(srv.values()))
                if info.get("models"):
                    print(print_dim(f"      Models: {', '.join(info['models'])}"))
            else:
                for host, info in srv.items():
                    label = host.replace("http://", "").replace("https://", "")
                    if info["status"] in ("healthy", "degraded"):
                        models_list = info.get("models", [])
                        models_str = f": {', '.join(models_list)}" if models_list else ""
                        print(print_dim(f"      {label}{models_str}"))
                    else:
                        print(print_red(f"      ✗ {label} (unavailable)"))

    print()
    return provider_results


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 002: Provider Detection")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                        help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                        help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                        help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
