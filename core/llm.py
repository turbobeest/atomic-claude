#!/usr/bin/env python3
"""
ATOMIC CLAUDE - Core Library (Python Implementation)

Provides atomic Claude invocation primitives for script-controlled LLM tasks.
Converted from bash to Python with identical functionality.

Usage:
    from lib.atomic import atomic_invoke
    atomic_invoke("prompt.md", "output.json", "Analyze codebase")
"""

import os
import sys
import json
import subprocess
import signal
import time
import re
import tempfile
import shutil
import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
import urllib.request
import urllib.error

# ============================================================================
# CONSTANTS AND CONFIGURATION
# ============================================================================

ATOMIC_VERSION = "0.1.0"
ATOMIC_ROOT = os.environ.get(
    "ATOMIC_ROOT",
    str(Path(__file__).parent.parent.resolve())
)

# Detect embedded installation
ATOMIC_ORCHESTRATOR = os.environ.get("ATOMIC_ORCHESTRATOR")
if not ATOMIC_ORCHESTRATOR:
    atomic_parent = Path(ATOMIC_ROOT).parent
    if Path(ATOMIC_ROOT).name == "ATOMIC-CLAUDE" and \
       (atomic_parent / "docs").is_dir() or (atomic_parent / "README.md").is_file():
        ATOMIC_ORCHESTRATOR = str(atomic_parent)
        os.environ["ATOMIC_ORCHESTRATOR"] = ATOMIC_ORCHESTRATOR

ATOMIC_STATE_DIR = os.environ.get("ATOMIC_STATE_DIR", f"{ATOMIC_ROOT}/.state")
ATOMIC_OUTPUT_DIR = os.environ.get("ATOMIC_OUTPUT_DIR", f"{ATOMIC_ROOT}/.outputs")
ATOMIC_LOG_DIR = os.environ.get("ATOMIC_LOG_DIR", f"{ATOMIC_ROOT}/.logs")

# Claude configuration
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "sonnet")
CLAUDE_MAX_TURNS = int(os.environ.get("CLAUDE_MAX_TURNS", "30"))
CLAUDE_TIMEOUT = int(os.environ.get("CLAUDE_TIMEOUT", "1200"))

# Claude-local wrapper configuration
CLAUDE_LOCAL_PATH = os.environ.get("CLAUDE_LOCAL_PATH", f"{ATOMIC_ROOT}/../claude-local")
CLAUDE_PROVIDER = os.environ.get("CLAUDE_PROVIDER", "max")
CLAUDE_OLLAMA_HOST = os.environ.get("CLAUDE_OLLAMA_HOST", "http://localhost:11434")
CLAUDE_OLLAMA_CONTEXT = int(os.environ.get("CLAUDE_OLLAMA_CONTEXT", "65536"))

# Provider-to-role mapping
PROVIDER_ROLE_MAP: Dict[str, str] = {
    "primary": os.environ.get("PROVIDER_ROLE_PRIMARY", "max"),
    "fast": os.environ.get("PROVIDER_ROLE_FAST", "ollama"),
    "gardener": os.environ.get("PROVIDER_ROLE_GARDENER", "ollama"),
    "heavyweight": os.environ.get("PROVIDER_ROLE_HEAVYWEIGHT", "max"),
}

# Dashboard ports
ATOMIC_TASKS_PORT = int(os.environ.get("ATOMIC_TASKS_PORT", "5173"))
ATOMIC_AGENTS_PORT = int(os.environ.get("ATOMIC_AGENTS_PORT", "5174"))
ATOMIC_AUDITS_PORT = int(os.environ.get("ATOMIC_AUDITS_PORT", "5175"))

# Network mode
ATOMIC_NETWORK_MODE = "cui"

# Config loaded flag
_ATOMIC_CONFIG_LOADED = False

# Temp files tracking
_ATOMIC_TEMP_FILES: List[str] = []

# ============================================================================
# COLORS AND OUTPUT
# ============================================================================

@dataclass
class Colors:
    """ANSI color codes for terminal output."""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    BLUE = '\033[0;34m'
    YELLOW = '\033[1;33m'
    CYAN = '\033[0;36m'
    MAGENTA = '\033[0;35m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    NC = '\033[0m'
    LIGHT_BLUE = '\033[94m'
    LIGHT_GREY = '\033[90m'


C = Colors()
TERM_WIDTH = int(os.environ.get("COLUMNS", "72"))


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def atomic_json_escape(text: str) -> str:
    """
    Escape a string for safe inclusion in JSON.

    Args:
        text: Raw string to escape

    Returns:
        Escaped string safe for JSON
    """
    # Escape backslashes first
    text = text.replace("\\", "\\\\")
    # Escape double quotes
    text = text.replace('"', '\\"')
    # Escape newlines
    text = text.replace("\n", "\\n")
    # Escape tabs
    text = text.replace("\t", "\\t")
    # Escape carriage returns
    text = text.replace("\r", "\\r")
    # Escape form feeds
    text = text.replace("\f", "\\f")
    # Escape backspaces
    text = text.replace("\b", "\\b")
    return text


def atomic_timeout(timeout_sec: int, args: List[str], **kwargs) -> subprocess.CompletedProcess:
    """
    Run a command with timeout (cross-platform).

    Args:
        timeout_sec: Timeout in seconds
        args: Command and arguments as list
        **kwargs: Additional arguments for subprocess.run

    Returns:
        CompletedProcess instance

    Raises:
        subprocess.TimeoutExpired: If command times out
    """
    return subprocess.run(
        args,
        timeout=timeout_sec,
        **kwargs
    )


def atomic_mktemp() -> str:
    """
    Create a tracked temporary file.

    Returns:
        Path to temporary file
    """
    fd, path = tempfile.mkstemp()
    os.close(fd)
    _ATOMIC_TEMP_FILES.append(path)
    return path


def atomic_mktemp_done(path: str) -> None:
    """
    Remove a temp file from tracking (after successful move/rm).

    Args:
        path: Path to temp file
    """
    if path in _ATOMIC_TEMP_FILES:
        _ATOMIC_TEMP_FILES.remove(path)


def cleanup_temp_files() -> None:
    """Clean up all tracked temporary files."""
    for path in _ATOMIC_TEMP_FILES[:]:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
    _ATOMIC_TEMP_FILES.clear()


# ============================================================================
# OUTPUT FUNCTIONS
# ============================================================================

def atomic_step(message: str) -> None:
    """Print a step message."""
    print(f"\n{C.CYAN}▶ {C.BOLD}{message}{C.NC}")


def atomic_substep(message: str) -> None:
    """Print a sub-step message."""
    print(f"{C.DIM}  → {message}{C.NC}")


def atomic_success(message: str) -> None:
    """Print a success message."""
    print(f"{C.GREEN}✓ {message}{C.NC}")


def atomic_error(message: str) -> None:
    """Print an error message."""
    print(f"{C.RED}✗ {message}{C.NC}", file=sys.stderr)


def atomic_warn(message: str) -> None:
    """Print a warning message."""
    print(f"{C.YELLOW}⚠ {message}{C.NC}", file=sys.stderr)


def atomic_waiting(message: str) -> None:
    """Print a waiting message."""
    print(f"{C.YELLOW}⏳ {message}{C.NC}")


def atomic_info(message: str) -> None:
    """Print an info message."""
    print(f"{C.DIM}ℹ {message}{C.NC}")


def atomic_h1(title: str) -> None:
    """Print a major header."""
    dots = '∙' * TERM_WIDTH
    print()
    print(f"{C.LIGHT_BLUE}{dots}{C.NC}")
    print(f"{C.LIGHT_BLUE}  ⬢ {title}{C.NC}")
    print(f"{C.LIGHT_BLUE}{dots}{C.NC}")


def atomic_h2(title: str) -> None:
    """Print a section header."""
    trace = "─ " * (TERM_WIDTH // 2)
    print()
    print(f"{C.LIGHT_GREY}{trace}{C.NC}")
    print(f"{C.LIGHT_GREY}  {title}{C.NC}")


# ============================================================================
# CONFIGURATION LOADING
# ============================================================================

def atomic_get_primary_model() -> str:
    """
    Get the primary model from project config or fallback to default.

    Returns:
        Model name (e.g., "sonnet")
    """
    project_config = Path(ATOMIC_OUTPUT_DIR) / "0-setup" / "project-config.json"

    if project_config.exists():
        try:
            with open(project_config) as f:
                config = json.load(f)
                model = config.get("extracted", {}).get("llm", {}).get("primary_model")
                if model:
                    return model
        except Exception:
            pass

    return CLAUDE_MODEL


def atomic_get_fast_model() -> str:
    """
    Get the fast model from project config or fallback to haiku.

    Returns:
        Model name (e.g., "haiku")
    """
    project_config = Path(ATOMIC_OUTPUT_DIR) / "0-setup" / "project-config.json"

    if project_config.exists():
        try:
            with open(project_config) as f:
                config = json.load(f)
                model = config.get("extracted", {}).get("llm", {}).get("fast_model")
                if model:
                    return model
        except Exception:
            pass

    return "haiku"


def _atomic_load_provider_config() -> None:
    """Load provider configuration from config/models.json."""
    global CLAUDE_LOCAL_PATH, CLAUDE_PROVIDER, CLAUDE_OLLAMA_HOST
    global CLAUDE_OLLAMA_CONTEXT, PROVIDER_ROLE_MAP, _ATOMIC_CONFIG_LOADED

    config_file = Path(ATOMIC_ROOT) / "config" / "models.json"

    if not config_file.exists():
        _ATOMIC_CONFIG_LOADED = True
        return

    try:
        with open(config_file) as f:
            config = json.load(f)

        # Load claude-local path
        wrapper_path = config.get("providers", {}).get("claude_local_path")
        if wrapper_path:
            if not wrapper_path.startswith("/"):
                wrapper_path = str(Path(ATOMIC_ROOT) / wrapper_path)
            CLAUDE_LOCAL_PATH = wrapper_path

        # Load default provider
        default_provider = config.get("providers", {}).get("default_provider")
        if default_provider:
            CLAUDE_PROVIDER = default_provider

        # Load Ollama settings
        ollama = config.get("providers", {}).get("ollama", {})
        if ollama.get("host"):
            CLAUDE_OLLAMA_HOST = ollama["host"]
        if ollama.get("context_length"):
            CLAUDE_OLLAMA_CONTEXT = ollama["context_length"]

        # Load role-to-provider mapping
        role_routing = config.get("providers", {}).get("role_routing", {})
        for role, provider in role_routing.items():
            if provider:
                PROVIDER_ROLE_MAP[role] = provider

        # Load Bedrock config
        _atomic_load_bedrock_config()

        _ATOMIC_CONFIG_LOADED = True
    except Exception as e:
        atomic_warn(f"Failed to load config: {e}")
        _ATOMIC_CONFIG_LOADED = True


def _atomic_load_bedrock_config() -> None:
    """Load AWS Bedrock configuration from secrets.json."""
    global CLAUDE_PROVIDER

    secrets_file = Path(ATOMIC_OUTPUT_DIR) / "0-setup" / "secrets.json"

    if not secrets_file.exists():
        return

    try:
        with open(secrets_file) as f:
            secrets = json.load(f)

        if secrets.get("bedrock_enabled"):
            os.environ["CLAUDE_CODE_USE_BEDROCK"] = "1"

            if secrets.get("aws_region"):
                os.environ["AWS_REGION"] = secrets["aws_region"]

            if secrets.get("aws_profile") and secrets["aws_profile"] != "default":
                os.environ["AWS_PROFILE"] = secrets["aws_profile"]

            if secrets.get("bedrock_model"):
                os.environ["ANTHROPIC_MODEL"] = secrets["bedrock_model"]

            # Recommended token settings
            os.environ.setdefault("CLAUDE_CODE_MAX_OUTPUT_TOKENS", "4096")
            os.environ.setdefault("MAX_THINKING_TOKENS", "1024")

            CLAUDE_PROVIDER = "bedrock"
    except Exception:
        pass


def _atomic_load_network_mode() -> None:
    """Load network mode configuration from secrets.json."""
    global ATOMIC_NETWORK_MODE

    secrets_file = Path(ATOMIC_OUTPUT_DIR) / "0-setup" / "secrets.json"

    if not secrets_file.exists():
        ATOMIC_NETWORK_MODE = "cui"
        return

    try:
        with open(secrets_file) as f:
            secrets = json.load(f)
        ATOMIC_NETWORK_MODE = secrets.get("network_mode", "cui")
    except Exception:
        ATOMIC_NETWORK_MODE = "cui"


def _atomic_ensure_config() -> None:
    """Ensure configuration is loaded."""
    if not _ATOMIC_CONFIG_LOADED:
        _atomic_load_provider_config()
        _atomic_load_network_mode()


# ============================================================================
# STATE MANAGEMENT
# ============================================================================

def atomic_state_init() -> None:
    """Initialize state directories and session file."""
    Path(ATOMIC_STATE_DIR).mkdir(parents=True, exist_ok=True)
    Path(ATOMIC_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(ATOMIC_LOG_DIR).mkdir(parents=True, exist_ok=True)

    state_file = Path(ATOMIC_STATE_DIR) / "session.json"
    if not state_file.exists():
        session = {
            "session_id": f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{os.getpid()}",
            "started_at": datetime.now().isoformat(),
            "tasks_completed": 0,
            "tasks_failed": 0,
            "current_phase": None,
            "current_task": None
        }
        with open(state_file, 'w') as f:
            json.dump(session, f, indent=2)


def atomic_state_get(key: str) -> Optional[str]:
    """
    Get a value from session state.

    Args:
        key: Key to retrieve

    Returns:
        Value or None if not found
    """
    state_file = Path(ATOMIC_STATE_DIR) / "session.json"
    try:
        with open(state_file) as f:
            state = json.load(f)
        return state.get(key)
    except Exception:
        return None


def atomic_state_set(key: str, value: Any) -> bool:
    """
    Set a value in session state.

    Args:
        key: Key to set
        value: Value to store

    Returns:
        True on success, False on failure
    """
    state_file = Path(ATOMIC_STATE_DIR) / "session.json"
    try:
        with open(state_file) as f:
            state = json.load(f)
        state[key] = value
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
        return True
    except Exception as e:
        atomic_error(f"Failed to set state: {e}")
        return False


def atomic_state_increment(key: str) -> bool:
    """
    Increment a numeric value in session state.

    Args:
        key: Key to increment

    Returns:
        True on success, False on failure
    """
    state_file = Path(ATOMIC_STATE_DIR) / "session.json"
    try:
        with open(state_file) as f:
            state = json.load(f)
        state[key] = state.get(key, 0) + 1
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
        return True
    except Exception as e:
        atomic_error(f"Failed to increment state: {e}")
        return False


# ============================================================================
# TASK HEADER AND STATUS
# ============================================================================

def atomic_task_header(
    description: str,
    provider: str,
    model: str,
    role: str,
    timeout: int,
    prompt_source: str,
    output_file: str,
    ollama_host: str = ""
) -> None:
    """
    Print unified task header and write status JSON.

    Args:
        description: Task description
        provider: Provider name (max/api/ollama/bedrock)
        model: Model name
        role: Role name (optional)
        timeout: Timeout in seconds
        prompt_source: Prompt file or string
        output_file: Output file path
        ollama_host: Ollama host URL (if applicable)
    """
    # Online/offline detection
    is_online = False
    if provider == "max":
        is_online = Path.home().joinpath(".claude/.credentials.json").exists()
    elif provider == "api":
        is_online = bool(os.environ.get("ANTHROPIC_API_KEY"))
    elif provider == "bedrock":
        is_online = os.environ.get("CLAUDE_CODE_USE_BEDROCK") == "1"
    elif provider == "ollama":
        try:
            url = f"{ollama_host or CLAUDE_OLLAMA_HOST}/api/tags"
            req = urllib.request.Request(url, method='GET')
            urllib.request.urlopen(req, timeout=1)
            is_online = True
        except Exception:
            is_online = False

    # Override provider display if Bedrock
    if os.environ.get("CLAUDE_CODE_USE_BEDROCK") == "1":
        provider = "bedrock"
        is_online = True

    # Context window + cost lookup
    context_window = "?"
    cost_tier = "?"
    config_file = Path(ATOMIC_ROOT) / "config" / "models.json"
    if config_file.exists():
        try:
            with open(config_file) as f:
                config = json.load(f)
            ctx = config.get("models", {}).get("claude", {}).get(model, {}).get("context_window") or \
                  config.get("models", {}).get("ollama", {}).get(model, {}).get("context_window")
            cost = config.get("models", {}).get("claude", {}).get(model, {}).get("cost_tier") or \
                   config.get("models", {}).get("ollama", {}).get(model, {}).get("cost_tier")
            if ctx:
                context_window = str(ctx)
            if cost:
                cost_tier = cost
        except Exception:
            pass

    # Host type
    host_type = "CLAUDECODE" if provider in ("max", "api", "bedrock") else "OLLAMA" if provider == "ollama" else "LOCAL"

    # Write status JSON for dashboard
    status_file = Path(ATOMIC_STATE_DIR) / "current-task.json"
    Path(ATOMIC_STATE_DIR).mkdir(parents=True, exist_ok=True)

    status = {
        "active": True,
        "description": description,
        "provider": provider,
        "model": model,
        "role": role or "",
        "timeout": timeout,
        "online": is_online,
        "network_mode": ATOMIC_NETWORK_MODE,
        "context_window": context_window,
        "cost_tier": cost_tier,
        "host_type": host_type,
        "ollama_host": ollama_host or "",
        "prompt_source": prompt_source,
        "output_file": output_file,
        "phase": os.environ.get("CURRENT_PHASE", ""),
        "task_id": os.environ.get("CURRENT_TASK_ID", ""),
        "timestamp": datetime.now().isoformat()
    }

    with open(status_file, 'w') as f:
        json.dump(status, f, indent=2)

    # Minimal CLI output
    print()
    print(f"  {C.CYAN}▶{C.NC} {description} {C.DIM}({provider}/{model}){C.NC}")


def atomic_task_clear() -> None:
    """Clear task status (mark as inactive)."""
    status_file = Path(ATOMIC_STATE_DIR) / "current-task.json"
    if status_file.exists():
        status = {
            "active": False,
            "message": "No active task",
            "timestamp": datetime.now().isoformat()
        }
        with open(status_file, 'w') as f:
            json.dump(status, f, indent=2)


# ============================================================================
# COMMAND BUILDER
# ============================================================================

def _atomic_build_invoke_cmd(
    prompt: str,
    model: str,
    provider: str,
    ollama_host: str
) -> str:
    """
    Build the invocation command for Claude CLI.

    Args:
        prompt: Prompt text
        model: Model name
        provider: Provider name
        ollama_host: Ollama host URL

    Returns:
        Command string to execute
    """
    # Validate inputs
    if any(c in model for c in ("'", '"', '$')):
        raise ValueError(f"Invalid characters in model name: {model}")
    if any(c in provider for c in ("'", '"', '$')):
        raise ValueError(f"Invalid characters in provider name: {provider}")

    # Escape prompt for shell
    escaped_prompt = prompt.replace("'", "'\\''")
    escaped_atomic_root = ATOMIC_ROOT.replace("'", "'\\''")

    # Network block for CUI mode
    network_block = ""
    if ATOMIC_NETWORK_MODE == "cui":
        network_block = "--disallowedTools 'WebSearch,WebFetch,Browser'"

    # BEDROCK mode
    if os.environ.get("CLAUDE_CODE_USE_BEDROCK") == "1" or provider == "bedrock":
        cmd = f"cd '{escaped_atomic_root}' && claude"
        cmd += f" -p '{escaped_prompt}'"
        cmd += " --dangerously-skip-permissions"
        cmd += " --output-format text"
        cmd += " --max-turns 1"
        if network_block:
            cmd += f" {network_block}"
        if os.environ.get("CLAUDE_TOOLS"):
            cmd += f" --tools '{os.environ['CLAUDE_TOOLS']}'"
        return cmd

    # OLLAMA mode
    if provider == "ollama":
        if not re.match(r'^https?://[a-zA-Z0-9._-]+(:[0-9]+)?$', ollama_host):
            ollama_host = "http://localhost:11434"

        cmd = f"cd '{escaped_atomic_root}' && "
        cmd += f"ANTHROPIC_BASE_URL='{ollama_host}' "
        # SECURITY NOTE: 'ollama' is a placeholder value, not a real API key.
        # Ollama doesn't require authentication; this satisfies the Anthropic SDK's requirement for a key.
        cmd += "ANTHROPIC_API_KEY='ollama' "
        cmd += "claude"
        cmd += f" --model '{model}'"
        cmd += f" -p '{escaped_prompt}'"
        cmd += " --dangerously-skip-permissions"
        cmd += " --output-format text"
        cmd += " --max-turns 1"
        if network_block:
            cmd += f" {network_block}"
        if os.environ.get("CLAUDE_TOOLS"):
            cmd += f" --tools '{os.environ['CLAUDE_TOOLS']}'"
        return cmd

    # DEFAULT (max/api mode)
    cmd = f"cd '{escaped_atomic_root}' && claude"
    cmd += f" -p '{escaped_prompt}'"
    cmd += " --dangerously-skip-permissions"
    cmd += " --output-format text"
    cmd += " --max-turns 1"
    if model not in ("opus", "sonnet"):
        cmd += f" --model '{model}'"
    if network_block:
        cmd += f" {network_block}"
    if os.environ.get("CLAUDE_TOOLS"):
        cmd += f" --tools '{os.environ['CLAUDE_TOOLS']}'"
    return cmd


# ============================================================================
# CORE: ATOMIC INVOKE
# ============================================================================

def atomic_invoke(
    prompt_source: str,
    output_file: str,
    description: str,
    model: Optional[str] = None,
    provider: Optional[str] = None,
    role: Optional[str] = None,
    format_type: Optional[str] = None,
    timeout: Optional[int] = None,
    use_stdin: bool = False,
    ollama_host: Optional[str] = None,
    task_type: Optional[str] = None,
    max_retries: int = 2,
    retry_delay: int = 5
) -> bool:
    """
    Core atomic Claude invocation function.

    Args:
        prompt_source: Path to prompt file or prompt string
        output_file: Path to output file
        description: Description of the task
        model: Model override (opus/sonnet/haiku)
        provider: Provider override (max/api/ollama/bedrock)
        role: Role-based routing (primary/fast/gardener/heavyweight)
        format_type: Expected format (json/markdown)
        timeout: Timeout override in seconds
        use_stdin: Read additional context from stdin
        ollama_host: Ollama host override
        task_type: Task type for provider chain resolution
        max_retries: Maximum retry attempts
        retry_delay: Delay between retries in seconds

    Returns:
        True on success, False on failure
    """
    # Ensure config is loaded
    _atomic_ensure_config()

    # Set defaults
    if model is None:
        model = atomic_get_primary_model()
    if provider is None:
        provider = CLAUDE_PROVIDER
    if timeout is None:
        timeout = CLAUDE_TIMEOUT
    if ollama_host is None:
        ollama_host = CLAUDE_OLLAMA_HOST

    # Role-based provider routing
    if role:
        provider = PROVIDER_ROLE_MAP.get(role, provider)

    # Validate API keys for provider
    if provider == "api" and not os.environ.get("ANTHROPIC_API_KEY"):
        print(f"\n{C.RED}❌ Missing API Key{C.NC}")
        print(f"\n{C.DIM}The 'api' provider requires ANTHROPIC_API_KEY environment variable.{C.NC}")
        print(f"\n{C.DIM}Set it with:{C.NC}")
        print(f"  export ANTHROPIC_API_KEY=sk-ant-...")
        print(f"\n{C.DIM}Or use a different provider:{C.NC}")
        print(f"  --provider=ollama  {C.DIM}(local, no API key needed){C.NC}")
        print(f"  --provider=bedrock {C.DIM}(AWS credentials required){C.NC}")
        print()
        return False

    if provider == "bedrock":
        # Check for AWS credentials
        has_env_creds = os.environ.get("AWS_ACCESS_KEY_ID") or os.environ.get("AWS_PROFILE")
        has_credentials_file = Path.home().joinpath(".aws", "credentials").exists()

        if not (has_env_creds or has_credentials_file):
            print(f"\n{C.RED}❌ Missing AWS Credentials{C.NC}")
            print(f"\n{C.DIM}The 'bedrock' provider requires AWS credentials.{C.NC}")
            print(f"\n{C.DIM}Set them with:{C.NC}")
            print(f"  export AWS_ACCESS_KEY_ID=...")
            print(f"  export AWS_SECRET_ACCESS_KEY=...")
            print(f"  export AWS_REGION=us-gov-west-1")
            print(f"\n{C.DIM}Or configure AWS CLI:{C.NC}")
            print(f"  aws configure")
            print(f"\n{C.DIM}Or use a different provider:{C.NC}")
            print(f"  --provider=ollama {C.DIM}(local, no credentials needed){C.NC}")
            print()
            return False

    # Determine prompt content
    prompt_path = Path(prompt_source)
    if prompt_path.exists() and prompt_path.is_file():
        prompt_content = prompt_path.read_text()
    else:
        prompt_content = prompt_source

    # Append stdin if requested
    if use_stdin:
        stdin_content = sys.stdin.read()
        prompt_content += f"\n\n---\nCONTEXT:\n{stdin_content}"

    # Inject task context from memory
    task_context_file = Path(ATOMIC_ROOT) / ".outputs" / "task-context.md"
    if task_context_file.exists() and task_context_file.stat().st_size > 0:
        task_context = task_context_file.read_text()
        prompt_content = f"## Recalled Context from Previous Tasks\n\n{task_context}\n\n---\n\n{prompt_content}"

    # Update state
    atomic_state_set("current_task", description)

    # Create output directory
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    # Task header
    if os.environ.get("ATOMIC_QUIET") != "true":
        atomic_task_header(description, provider, model, role or "", timeout, prompt_source, output_file, ollama_host)
        atomic_waiting("Invoking Claude...")
        print()
    else:
        print(f"  {C.DIM}⏳ {description}...{C.NC}", end="", flush=True)

    # Build invocation command
    invoke_cmd = _atomic_build_invoke_cmd(prompt_content, model, provider, ollama_host)

    # Execute with retry logic
    start_time = time.time()
    exit_code = 0
    attempt = 1

    while attempt <= max_retries + 1:
        attempt_start = time.time()
        temp_output = f"{output_file}.tmp.{os.getpid()}"

        try:
            # Run command
            result = subprocess.run(
                ["bash", "-c", invoke_cmd],
                stdin=subprocess.DEVNULL,
                stdout=open(temp_output, 'w'),
                stderr=open(f"{output_file}.err", 'w'),
                timeout=timeout
            )
            exit_code = result.returncode

            if exit_code == 0:
                shutil.move(temp_output, output_file)
                break
        except subprocess.TimeoutExpired:
            exit_code = 124
        except Exception as e:
            atomic_error(f"Invocation failed: {e}")
            exit_code = 1

        # Clean up temp file
        if Path(temp_output).exists():
            try:
                shutil.move(temp_output, output_file)
            except Exception:
                Path(temp_output).unlink(missing_ok=True)

        attempt_end = time.time()

        # Check if we should retry
        if exit_code == 124 and attempt < max_retries + 1:
            atomic_warn(f"Timeout on attempt {attempt}/{max_retries + 1}, retrying in {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff
            attempt += 1
        else:
            break

    end_time = time.time()
    duration = int(end_time - start_time)

    # Log the invocation
    log_file = Path(ATOMIC_LOG_DIR) / f"atomic-{datetime.now().strftime('%Y-%m-%d')}.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, 'a') as f:
        f.write(f"[{datetime.now().isoformat()}] task=\"{description}\" provider={provider} model={model} duration={duration}s exit={exit_code} output={output_file}\n")

    # Handle result
    if exit_code == 0:
        if os.environ.get("ATOMIC_QUIET") != "true":
            atomic_success(f"Claude completed task ({duration}s)")
            atomic_substep(f"Output written to: {output_file}")
        else:
            print(f" {C.GREEN}✓{C.NC} {C.DIM}({duration}s){C.NC}")

        # Validate format if specified
        if format_type == "json":
            try:
                with open(output_file) as f:
                    json.load(f)
                atomic_success("JSON output validated")
            except json.JSONDecodeError:
                pass  # Caller handles extraction

        Path(f"{output_file}.err").unlink(missing_ok=True)
        atomic_state_increment("tasks_completed")
        atomic_task_clear()
        return True
    else:
        if exit_code == 124:
            atomic_error(f"Claude task timed out after {attempt} attempt(s)")
        else:
            atomic_error(f"Claude task failed (exit code: {exit_code})")

        err_file = Path(f"{output_file}.err")
        if err_file.exists() and err_file.stat().st_size > 0:
            atomic_substep(f"Stderr: {err_file.read_text()[:500]}")

        atomic_substep(f"Check output file for details: {output_file}")
        atomic_state_increment("tasks_failed")
        atomic_task_clear()
        return False


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def atomic_extract_json(input_file: str, output_file: str) -> bool:
    """
    Extract JSON from mixed Claude output.

    Args:
        input_file: Input file path
        output_file: Output file path

    Returns:
        True on success, False on failure
    """
    try:
        content = Path(input_file).read_text()

        # Try to find JSON block
        json_match = re.search(r'```json\s*\n(.*?)\n```', content, re.DOTALL)
        if json_match:
            json_content = json_match.group(1)
        elif content.strip().startswith('{'):
            json_content = content
        else:
            atomic_error("No JSON found in output")
            return False

        # Validate
        parsed = json.loads(json_content)
        with open(output_file, 'w') as f:
            json.dump(parsed, f, indent=2)

        atomic_success("JSON extracted and validated")
        return True
    except Exception as e:
        atomic_error(f"JSON extraction failed: {e}")
        return False


def atomic_validate_files(*files: str) -> bool:
    """
    Check if required files exist.

    Args:
        *files: Variable number of file paths

    Returns:
        True if all exist, False otherwise
    """
    missing = [f for f in files if not Path(f).exists()]

    if missing:
        atomic_error("Missing required files:")
        for f in missing:
            print(f"  - {f}")
        return False

    atomic_success("All required files present")
    return True


# ============================================================================
# DEPENDENCY VALIDATION
# ============================================================================

# Required and optional dependencies
ATOMIC_REQUIRED_DEPS = ["jq", "git"]
ATOMIC_OPTIONAL_DEPS = ["claude", "curl", "ollama", "realpath"]


def atomic_validate_deps(strict: bool = False) -> bool:
    """
    Validate that required (and optionally, optional) dependencies are available.

    Args:
        strict: If True, also require optional dependencies

    Returns:
        True if all required (and optional, if strict) dependencies are available,
        False otherwise
    """
    missing_required: List[str] = []
    missing_optional: List[str] = []

    # Check required dependencies
    for dep in ATOMIC_REQUIRED_DEPS:
        if not shutil.which(dep):
            missing_required.append(dep)

    # Check optional dependencies
    for dep in ATOMIC_OPTIONAL_DEPS:
        if not shutil.which(dep):
            missing_optional.append(dep)

    # Report missing required
    if missing_required:
        print("ERROR: Missing required dependencies:", file=sys.stderr)
        for dep in missing_required:
            print(f"  - {dep}", file=sys.stderr)
        print("", file=sys.stderr)
        print("Install missing dependencies and try again.", file=sys.stderr)
        return False

    # Report missing optional only in strict mode (they're optional, no need to warn)
    if missing_optional and strict:
        print("ERROR: Missing optional dependencies (strict mode):", file=sys.stderr)
        for dep in missing_optional:
            print(f"  - {dep}", file=sys.stderr)
        return False

    return True


# ============================================================================
# INITIALIZATION
# ============================================================================

# Auto-initialize state on import
atomic_state_init()


# ============================================================================
# CLEANUP HANDLER
# ============================================================================

import atexit
atexit.register(cleanup_temp_files)


if __name__ == "__main__":
    # Simple test/demo
    print(f"ATOMIC CLAUDE Python Library v{ATOMIC_VERSION}")
    print(f"ATOMIC_ROOT: {ATOMIC_ROOT}")
    print(f"Provider: {CLAUDE_PROVIDER}")
    print(f"Model: {CLAUDE_MODEL}")


def atomic_context_init(phase_id: str) -> None:
    """
    Initialize context directory for a phase.
    
    Creates context directory and inherits summary from previous phase if available.
    
    Args:
        phase_id: Phase identifier (e.g., "4-specification")
    """
    import shutil
    from pathlib import Path
    
    output_dir = Path(os.getenv("ATOMIC_OUTPUT_DIR", ".outputs"))
    context_dir = output_dir / phase_id / "context"
    context_dir.mkdir(parents=True, exist_ok=True)
    
    summary_file = context_dir / "summary.md"
    
    # Try to inherit from previous phase
    if not summary_file.exists():
        # Extract phase number
        phase_num_str = phase_id.split("-")[0]
        try:
            phase_num = int(phase_num_str)
            if phase_num > 0:
                # Find previous phase summary
                prev_num = phase_num - 1
                for prev_dir in output_dir.glob(f"{prev_num}-*/context/summary.md"):
                    if prev_dir.exists():
                        shutil.copy(prev_dir, summary_file)
                        break
        except ValueError:
            pass
    
    # Create default summary if still doesn't exist
    if not summary_file.exists():
        summary_file.write_text(f"""# Project Context Summary

*This file is automatically maintained. It provides rolling context for LLM tasks.*

## Phase: {phase_id}

Context will be accumulated as tasks execute.
""")


def atomic_phase_header(phase_id: str, project_name: str = "atomic-test") -> None:
    """
    Print phase header with project name.
    
    Args:
        phase_id: Phase identifier (e.g., "0-setup")
        project_name: Name of the project
    """
    c = Colors()
    print()
    print(f"{c.BRIGHT_BLUE}{'∙' * 72}{c.NC}")
    print(f"{c.BRIGHT_BLUE}  ⬢ PHASE {phase_id.upper()} [{project_name}]{c.NC}")
    print(f"{c.BRIGHT_BLUE}{'∙' * 72}{c.NC}")


def atomic_header(title: str) -> None:
    """
    Print a formatted header.
    
    Args:
        title: Header title text
    """
    c = Colors()
    print()
    print(f"{c.BRIGHT_BLUE}{'∙' * 72}{c.NC}")
    print(f"{c.BRIGHT_BLUE}  ⬢ {title}{c.NC}")
    print(f"{c.BRIGHT_BLUE}{'∙' * 72}{c.NC}")
    print()


def atomic_get_project_name() -> str:
    """
    Get project name from configuration.
    
    Returns:
        Project name from config, or "atomic-test" as fallback
    """
    import json
    from pathlib import Path
    
    output_dir = Path(os.getenv("ATOMIC_OUTPUT_DIR", ".outputs"))
    config_file = output_dir / "0-setup" / "project-config.json"
    
    if config_file.exists():
        try:
            with open(config_file) as f:
                config = json.load(f)
                return config.get("project", {}).get("name", "atomic-test")
        except Exception:
            pass
    
    return "atomic-test"


def atomic_git_tag(tag_name: str, message: str = "") -> bool:
    """
    Create a git tag.
    
    Args:
        tag_name: Name of the tag
        message: Optional tag message
        
    Returns:
        True if tag created successfully, False otherwise
    """
    import subprocess
    
    try:
        if message:
            subprocess.run(
                ["git", "tag", "-a", tag_name, "-m", message],
                check=True,
                capture_output=True
            )
        else:
            subprocess.run(
                ["git", "tag", tag_name],
                check=True,
                capture_output=True
            )
        return True
    except subprocess.CalledProcessError:
        return False


def atomic_context_refresh(phase_id: str) -> None:
    """
    Refresh context summary for a phase.
    
    TODO: Implement context refresh logic
    
    Args:
        phase_id: Phase identifier
    """
    pass


def atomic_llm_available() -> bool:
    """
    Check if an LLM provider is available.

    Returns:
        True if at least one provider is available
    """
    from core.providers import ProviderManager
    mgr = ProviderManager()
    mgr.init()
    return (mgr.check_anthropic() or
            mgr.check_aws_bedrock() or
            mgr.check_claude_code())


def atomic_context_artifact(name: str, path: str) -> None:
    """Record a context artifact. TODO: Implement"""
    pass

def atomic_context_decision(decision: str, rationale: str) -> None:
    """Record a context decision. TODO: Implement"""
    pass

def atomic_context_save() -> None:
    """Save context to file. TODO: Implement"""
    pass

# Stub functions - TODO: Implement these
def atomic_drain_stdin() -> None:
    """Drain stdin to prevent input issues. TODO: Implement"""
    import sys
    if not sys.stdin.isatty():
        sys.stdin.read()

def atomic_log(message: str) -> None:
    """Log message to atomic log file. TODO: Implement"""
    pass

def atomic_get_model_for_role(role: str) -> str:
    """Get model for a specific role. TODO: Implement"""
    return "sonnet"

def atomic_get_fast_model_for_role(role: str) -> str:
    """Get fast model for role. TODO: Implement"""
    return "haiku"
