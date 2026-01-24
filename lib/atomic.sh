#!/bin/bash
#
# ATOMIC CLAUDE - Core Library
# Provides atomic Claude invocation primitives for script-controlled LLM tasks
#
# Usage:
#   source lib/atomic.sh
#   atomic_invoke "prompt.md" "output.json" "Analyze codebase"
#

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

ATOMIC_VERSION="0.1.0"
ATOMIC_ROOT="${ATOMIC_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
ATOMIC_STATE_DIR="${ATOMIC_STATE_DIR:-$ATOMIC_ROOT/.state}"
ATOMIC_OUTPUT_DIR="${ATOMIC_OUTPUT_DIR:-$ATOMIC_ROOT/.outputs}"
ATOMIC_LOG_DIR="${ATOMIC_LOG_DIR:-$ATOMIC_ROOT/.logs}"

# Claude configuration
CLAUDE_MODEL="${CLAUDE_MODEL:-sonnet}"
CLAUDE_MAX_TURNS="${CLAUDE_MAX_TURNS:-1}"
CLAUDE_TIMEOUT="${CLAUDE_TIMEOUT:-300}"

# Claude-local wrapper configuration
CLAUDE_LOCAL_PATH="${CLAUDE_LOCAL_PATH:-$ATOMIC_ROOT/../claude-local}"
CLAUDE_PROVIDER="${CLAUDE_PROVIDER:-max}"
CLAUDE_OLLAMA_HOST="${CLAUDE_OLLAMA_HOST:-http://localhost:11434}"
CLAUDE_OLLAMA_CONTEXT="${CLAUDE_OLLAMA_CONTEXT:-32768}"

# Provider-to-role mapping (loaded from config/models.json)
declare -A PROVIDER_ROLE_MAP
PROVIDER_ROLE_MAP[primary]="${PROVIDER_ROLE_PRIMARY:-max}"
PROVIDER_ROLE_MAP[fast]="${PROVIDER_ROLE_FAST:-ollama}"
PROVIDER_ROLE_MAP[gardener]="${PROVIDER_ROLE_GARDENER:-ollama}"
PROVIDER_ROLE_MAP[heavyweight]="${PROVIDER_ROLE_HEAVYWEIGHT:-max}"

# ============================================================================
# CONFIGURATION LOADER
# ============================================================================

# Load provider configuration from config/models.json
# Called automatically on first invoke, or manually for refresh
_atomic_load_provider_config() {
    local config_file="$ATOMIC_ROOT/config/models.json"

    if [[ ! -f "$config_file" ]]; then
        return 0  # Use defaults if config doesn't exist
    fi

    # Load claude-local path
    local wrapper_path
    wrapper_path=$(jq -r '.providers.claude_local_path // empty' "$config_file" 2>/dev/null)
    if [[ -n "$wrapper_path" ]]; then
        # Resolve relative paths
        if [[ "$wrapper_path" != /* ]]; then
            wrapper_path="$ATOMIC_ROOT/$wrapper_path"
        fi
        CLAUDE_LOCAL_PATH="$wrapper_path"
    fi

    # Load default provider
    local default_provider
    default_provider=$(jq -r '.providers.default_provider // empty' "$config_file" 2>/dev/null)
    [[ -n "$default_provider" ]] && CLAUDE_PROVIDER="$default_provider"

    # Load Ollama settings
    local ollama_host ollama_context ollama_model
    ollama_host=$(jq -r '.providers.ollama.host // empty' "$config_file" 2>/dev/null)
    ollama_context=$(jq -r '.providers.ollama.context_length // empty' "$config_file" 2>/dev/null)
    ollama_model=$(jq -r '.providers.ollama.default_model // empty' "$config_file" 2>/dev/null)
    [[ -n "$ollama_host" ]] && CLAUDE_OLLAMA_HOST="$ollama_host"
    [[ -n "$ollama_context" ]] && CLAUDE_OLLAMA_CONTEXT="$ollama_context"
    [[ -n "$ollama_model" ]] && CLAUDE_OLLAMA_MODEL="$ollama_model"

    # Load role-to-provider mapping
    local role_primary role_fast role_gardener role_heavyweight
    role_primary=$(jq -r '.providers.role_routing.primary // empty' "$config_file" 2>/dev/null)
    role_fast=$(jq -r '.providers.role_routing.fast // empty' "$config_file" 2>/dev/null)
    role_gardener=$(jq -r '.providers.role_routing.gardener // empty' "$config_file" 2>/dev/null)
    role_heavyweight=$(jq -r '.providers.role_routing.heavyweight // empty' "$config_file" 2>/dev/null)

    [[ -n "$role_primary" ]] && PROVIDER_ROLE_MAP[primary]="$role_primary"
    [[ -n "$role_fast" ]] && PROVIDER_ROLE_MAP[fast]="$role_fast"
    [[ -n "$role_gardener" ]] && PROVIDER_ROLE_MAP[gardener]="$role_gardener"
    [[ -n "$role_heavyweight" ]] && PROVIDER_ROLE_MAP[heavyweight]="$role_heavyweight"

    _ATOMIC_CONFIG_LOADED=true
}

# Flag to track if config has been loaded
_ATOMIC_CONFIG_LOADED=false

# Ensure config is loaded (called by atomic_invoke)
_atomic_ensure_config() {
    if [[ "$_ATOMIC_CONFIG_LOADED" != "true" ]]; then
        _atomic_load_provider_config
    fi
}

# ============================================================================
# TEMP FILE MANAGEMENT
# ============================================================================

# Global array to track temp files for cleanup
declare -a _ATOMIC_TEMP_FILES=()

# Cleanup function called on EXIT/ERR
_atomic_cleanup_temp_files() {
    local file
    for file in "${_ATOMIC_TEMP_FILES[@]:-}"; do
        [[ -f "$file" ]] && rm -f "$file" 2>/dev/null
    done
    _ATOMIC_TEMP_FILES=()
}

# Register cleanup trap (only once)
if [[ -z "${_ATOMIC_TRAP_SET:-}" ]]; then
    trap '_atomic_cleanup_temp_files' EXIT
    _ATOMIC_TRAP_SET=1
fi

# Create a tracked temp file that will be cleaned up on exit
# Usage: local tmp=$(atomic_mktemp)
atomic_mktemp() {
    local tmp
    tmp=$(command mktemp) || return 1
    _ATOMIC_TEMP_FILES+=("$tmp")
    echo "$tmp"
}

# Remove a temp file from tracking (call after successful mv/rm)
# Usage: atomic_mktemp_done "$tmp"
atomic_mktemp_done() {
    local file="$1"
    local i
    for i in "${!_ATOMIC_TEMP_FILES[@]}"; do
        if [[ "${_ATOMIC_TEMP_FILES[$i]}" == "$file" ]]; then
            unset '_ATOMIC_TEMP_FILES[i]'
            break
        fi
    done
}

# ============================================================================
# DEPENDENCY VALIDATION
# ============================================================================

# Required dependencies for ATOMIC CLAUDE
declare -a ATOMIC_REQUIRED_DEPS=("jq" "git")
declare -a ATOMIC_OPTIONAL_DEPS=("claude" "curl" "ollama")

# Validate all required dependencies are available
# Usage: atomic_validate_deps [--strict]
# --strict: Also require optional dependencies
# Returns: 0 if all required deps available, 1 if missing
atomic_validate_deps() {
    local strict="${1:-false}"
    local missing_required=()
    local missing_optional=()
    local dep

    # Check required dependencies
    for dep in "${ATOMIC_REQUIRED_DEPS[@]}"; do
        if ! command -v "$dep" &>/dev/null; then
            missing_required+=("$dep")
        fi
    done

    # Check optional dependencies
    for dep in "${ATOMIC_OPTIONAL_DEPS[@]}"; do
        if ! command -v "$dep" &>/dev/null; then
            missing_optional+=("$dep")
        fi
    done

    # Report missing required
    if [[ ${#missing_required[@]} -gt 0 ]]; then
        echo "ERROR: Missing required dependencies:" >&2
        for dep in "${missing_required[@]}"; do
            echo "  - $dep" >&2
        done
        echo "" >&2
        echo "Install missing dependencies and try again." >&2
        return 1
    fi

    # Report missing optional (warning only unless strict)
    if [[ ${#missing_optional[@]} -gt 0 ]]; then
        if [[ "$strict" == "--strict" ]] || [[ "$strict" == "true" ]]; then
            echo "ERROR: Missing optional dependencies (strict mode):" >&2
            for dep in "${missing_optional[@]}"; do
                echo "  - $dep" >&2
            done
            return 1
        else
            # Just warn about missing optional deps
            for dep in "${missing_optional[@]}"; do
                echo "WARN: Optional dependency not found: $dep" >&2
            done
        fi
    fi

    return 0
}

# Check if a specific dependency is available
# Usage: atomic_has_dep "claude"
atomic_has_dep() {
    local dep="$1"
    command -v "$dep" &>/dev/null
}

# Validate dependencies and print status
# Usage: atomic_deps_status
atomic_deps_status() {
    echo "Dependency Status:"
    echo "=================="
    echo ""
    echo "Required:"
    for dep in "${ATOMIC_REQUIRED_DEPS[@]}"; do
        if command -v "$dep" &>/dev/null; then
            local version
            version=$("$dep" --version 2>/dev/null | head -1 || echo "installed")
            echo "  [OK] $dep - $version"
        else
            echo "  [MISSING] $dep"
        fi
    done
    echo ""
    echo "Optional:"
    for dep in "${ATOMIC_OPTIONAL_DEPS[@]}"; do
        if command -v "$dep" &>/dev/null; then
            local version
            version=$("$dep" --version 2>/dev/null | head -1 || echo "installed")
            echo "  [OK] $dep - $version"
        else
            echo "  [MISSING] $dep"
        fi
    done
}

# ============================================================================
# COLORS & OUTPUT
# ============================================================================

# Standard colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# High-tech theme colors
LIGHT_BLUE='\033[94m'    # Header 1 (Matrix Dots)
LIGHT_GREY='\033[90m'    # Header 2 (Light Trace)

# Terminal width for dynamic sizing
TERM_WIDTH="${COLUMNS:-72}"

# ============================================================================
# HEADER STYLES (High-Tech Theme)
# ============================================================================

# Header 1: Matrix Dots - Major sections, phase headers
# Usage: atomic_h1 "PHASE 1: DISCOVERY"
atomic_h1() {
    local title="$1"
    local dots=$(printf '∙%.0s' $(seq 1 $TERM_WIDTH))
    echo ""
    echo -e "${LIGHT_BLUE}${dots}${NC}"
    echo -e "${LIGHT_BLUE}  ⬢ ${title}${NC}"
    echo -e "${LIGHT_BLUE}${dots}${NC}"
}

# Header 2: Light Trace - Subsections, task headers
# Usage: atomic_h2 "Agent Selection"
atomic_h2() {
    local title="$1"
    local trace=""
    for ((i=0; i<TERM_WIDTH/2; i++)); do trace+="─ "; done
    echo ""
    echo -e "${LIGHT_GREY}${trace}${NC}"
    echo -e "${LIGHT_GREY}  ${title}${NC}"
}

# Entry Banner: Compact Tech - Phase entry tasks (x01)
# Usage: atomic_entry_banner "PHASE 1: DISCOVERY" "101"
atomic_entry_banner() {
    local phase_title="$1"
    local task_num="$2"
    local bar=$(printf '═%.0s' $(seq 1 $TERM_WIDTH))
    local inner_width=$((TERM_WIDTH - ${#phase_title} - ${#task_num} - 12))
    local dashes=$(printf '─%.0s' $(seq 1 $inner_width))
    echo ""
    echo -e "${LIGHT_BLUE}${bar}${NC}"
    echo -e "${LIGHT_BLUE}  ▶▶ ${phase_title} ${dashes} [${task_num}]${NC}"
    echo -e "${LIGHT_BLUE}${bar}${NC}"
}

# Closeout: Terminal Return - Phase completion
# Usage: atomic_closeout_banner "Phase 1 Complete"
atomic_closeout_banner() {
    local message="${1:-CLOSEOUT}"
    local padding=$((TERM_WIDTH - ${#message} - 10))
    local spaces=$(printf ' %.0s' $(seq 1 $padding))
    echo ""
    echo -e "${spaces}${LIGHT_GREY}▪▪▪ ${message} ▪▪▪${NC}"
    echo ""
}

# ============================================================================
# STICKY MODE INDICATOR BAR
# ============================================================================

# Track if sticky bar is active
_ATOMIC_STICKY_BAR_ACTIVE=false

# Initialize sticky mode bar (reserves line 0 for the bar)
# Call once at start of LLM task
atomic_mode_bar_init() {
    local provider="${1:-$CLAUDE_PROVIDER}"
    local model="${2:-$CLAUDE_MODEL}"

    _ATOMIC_STICKY_BAR_ACTIVE=true
    _ATOMIC_STICKY_PROVIDER="$provider"
    _ATOMIC_STICKY_MODEL="$model"

    # Set up scroll region to leave line 0 for the bar
    tput sc              # Save cursor
    tput cup 0 0         # Move to top
    tput el              # Clear line
    _atomic_render_mode_bar "$provider" "$model"
    tput csr 1 $(($(tput lines) - 1))  # Set scroll region (line 1 to bottom)
    tput rc              # Restore cursor
    tput cup 1 0         # Move to line 1
}

# Update the sticky mode bar (call when status changes)
atomic_mode_bar_update() {
    local provider="${1:-$_ATOMIC_STICKY_PROVIDER}"
    local model="${2:-$_ATOMIC_STICKY_MODEL}"

    [[ "$_ATOMIC_STICKY_BAR_ACTIVE" != "true" ]] && return

    tput sc              # Save cursor
    tput cup 0 0         # Move to top
    _atomic_render_mode_bar "$provider" "$model"
    tput rc              # Restore cursor
}

# Remove sticky mode bar and restore normal scrolling
atomic_mode_bar_clear() {
    [[ "$_ATOMIC_STICKY_BAR_ACTIVE" != "true" ]] && return

    _ATOMIC_STICKY_BAR_ACTIVE=false
    tput csr 0 $(($(tput lines) - 1))  # Reset scroll region to full screen
    tput sc
    tput cup 0 0
    tput el              # Clear the bar line
    tput rc
}

# Render the mode bar content (internal)
_atomic_render_mode_bar() {
    local provider="${1:-$CLAUDE_PROVIDER}"
    local model="${2:-$CLAUDE_MODEL}"
    local width="${COLUMNS:-$(tput cols)}"

    # Determine mode label, status, and color based on provider
    local mode_label status_label bg_color fg_color
    local is_online=false

    case "$provider" in
        max)
            mode_label="MAX MODE"
            # Check if we have credentials
            if [[ -f "$HOME/.claude/.credentials.json" ]]; then
                is_online=true
            fi
            ;;
        api)
            mode_label="API MODE"
            # Check if API key is set
            if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
                is_online=true
            fi
            ;;
        ollama)
            mode_label="OLLAMA MODE"
            # Check if Ollama is reachable
            if curl -s --connect-timeout 1 "${CLAUDE_OLLAMA_HOST:-http://localhost:11434}/api/tags" &>/dev/null 2>&1; then
                is_online=true
            fi
            ;;
        *)
            mode_label="LOCAL MODE"
            ;;
    esac

    # Set colors based on online/offline status
    if $is_online; then
        status_label="online"
        bg_color='\033[42m'  # Green background
        fg_color='\033[97m'  # Bright white text
    else
        status_label="OFFLINE"
        bg_color='\033[41m'  # Red background
        fg_color='\033[97m'  # Bright white text
    fi

    # Build the bar content
    local content="  ${mode_label}   |   ${model}   |   ${status_label}  "
    local content_len=${#content}
    local padding=$(( (width - content_len) / 2 ))
    [[ $padding -lt 0 ]] && padding=0
    local left_pad=$(printf '%*s' "$padding" '')
    local right_pad=$(printf '%*s' "$((width - content_len - padding))" '')

    # Print the bar (no newline - we're on line 0)
    echo -ne "${bg_color}${fg_color}${BOLD}${left_pad}${content}${right_pad}${NC}"
}

# Simple non-sticky mode bar (fallback for non-interactive)
atomic_mode_bar_simple() {
    local provider="${1:-$CLAUDE_PROVIDER}"
    local model="${2:-$CLAUDE_MODEL}"

    echo ""
    _atomic_render_mode_bar "$provider" "$model"
    echo ""
}

# ============================================================================
# LEGACY ALIASES (map old functions to new style)
# ============================================================================

# atomic_header now uses H1 style
atomic_header() {
    atomic_h1 "$1"
}

# Output functions
atomic_step() {
    echo ""
    echo -e "${CYAN}▶ ${BOLD}$1${NC}"
}

atomic_substep() {
    echo -e "${DIM}  → $1${NC}"
}

atomic_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

atomic_error() {
    echo -e "${RED}✗ $1${NC}"
}

atomic_warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

atomic_waiting() {
    echo -e "${YELLOW}⏳ $1${NC}"
}

atomic_info() {
    echo -e "${DIM}ℹ $1${NC}"
}

# Deprecated: Use atomic_h2 for section headers instead
atomic_output_box() {
    echo -e "${LIGHT_GREY}─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─${NC}"
    echo "$1" | sed 's/^/  /'
    echo -e "${LIGHT_GREY}─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─${NC}"
}

# ============================================================================
# STATE MANAGEMENT
# ============================================================================

atomic_state_init() {
    mkdir -p "$ATOMIC_STATE_DIR" "$ATOMIC_OUTPUT_DIR" "$ATOMIC_LOG_DIR"

    local state_file="$ATOMIC_STATE_DIR/session.json"
    if [[ ! -f "$state_file" ]]; then
        cat > "$state_file" << EOF
{
  "session_id": "$(date +%Y%m%d-%H%M%S)-$$",
  "started_at": "$(date -Iseconds)",
  "tasks_completed": 0,
  "tasks_failed": 0,
  "current_phase": null,
  "current_task": null
}
EOF
    fi
}

atomic_state_get() {
    local key="$1"
    jq -r ".$key // empty" "$ATOMIC_STATE_DIR/session.json"
}

atomic_state_set() {
    local key="$1"
    local value="$2"
    local state_file="$ATOMIC_STATE_DIR/session.json"
    local tmp_file
    tmp_file=$(atomic_mktemp) || { echo "ERROR: Failed to create temp file" >&2; return 1; }

    if ! jq ".$key = $value" "$state_file" > "$tmp_file" 2>/dev/null; then
        echo "ERROR: jq failed in atomic_state_set for key: $key" >&2
        rm -f "$tmp_file" 2>/dev/null
        return 1
    fi

    if [[ ! -s "$tmp_file" ]] || ! jq empty "$tmp_file" 2>/dev/null; then
        echo "ERROR: Invalid JSON output in atomic_state_set" >&2
        rm -f "$tmp_file" 2>/dev/null
        return 1
    fi

    mv "$tmp_file" "$state_file"
}

atomic_state_increment() {
    local key="$1"
    local state_file="$ATOMIC_STATE_DIR/session.json"
    local tmp_file
    tmp_file=$(atomic_mktemp) || { echo "ERROR: Failed to create temp file" >&2; return 1; }

    if ! jq ".$key = (.$key + 1)" "$state_file" > "$tmp_file" 2>/dev/null; then
        echo "ERROR: jq failed in atomic_state_increment for key: $key" >&2
        rm -f "$tmp_file" 2>/dev/null
        return 1
    fi

    if [[ ! -s "$tmp_file" ]] || ! jq empty "$tmp_file" 2>/dev/null; then
        echo "ERROR: Invalid JSON output in atomic_state_increment" >&2
        rm -f "$tmp_file" 2>/dev/null
        return 1
    fi

    mv "$tmp_file" "$state_file"
}

# ============================================================================
# CORE: INVOKE COMMAND BUILDER
# ============================================================================

# Build the invocation command for the claude-local wrapper
# Usage: _atomic_build_invoke_cmd <prompt> <model> <provider> <ollama_host>
# Returns: Command string to execute
_atomic_build_invoke_cmd() {
    local prompt="$1"
    local model="$2"
    local provider="$3"
    local ollama_host="$4"

    # Escape prompt for shell
    local escaped_prompt
    escaped_prompt=$(printf '%s' "$prompt" | sed "s/'/'\\\\''/g")

    # Resolve wrapper path
    local wrapper_path="$CLAUDE_LOCAL_PATH"
    if [[ ! -d "$wrapper_path" ]]; then
        # Try relative to ATOMIC_ROOT
        wrapper_path="$ATOMIC_ROOT/../claude-local"
    fi
    if [[ ! -d "$wrapper_path" ]]; then
        # Fallback to direct claude if wrapper not found
        atomic_warn "claude-local wrapper not found at $CLAUDE_LOCAL_PATH, falling back to direct claude"
        echo "claude -p '$escaped_prompt' --model '$model' --dangerously-skip-permissions"
        return
    fi

    # Build command based on provider
    local cmd="cd '$wrapper_path' && python -m local_launcher"
    cmd="$cmd --provider '$provider'"
    cmd="$cmd --model '$model'"
    cmd="$cmd --no-banner"
    cmd="$cmd --skip-checks"

    # Add Ollama-specific options
    if [[ "$provider" == "ollama" ]]; then
        cmd="$cmd --ollama-host '$ollama_host'"
        cmd="$cmd --context-length '$CLAUDE_OLLAMA_CONTEXT'"
    fi

    # Add prompt
    cmd="$cmd -p '$escaped_prompt'"

    echo "$cmd"
}

# Verify wrapper is available (call during init)
_atomic_verify_wrapper() {
    local wrapper_path="$CLAUDE_LOCAL_PATH"
    if [[ ! -d "$wrapper_path" ]]; then
        wrapper_path="$ATOMIC_ROOT/../claude-local"
    fi

    if [[ -d "$wrapper_path" && -f "$wrapper_path/local_launcher/__main__.py" ]]; then
        return 0
    else
        return 1
    fi
}

# Get wrapper status for diagnostics
atomic_wrapper_status() {
    _atomic_ensure_config

    local wrapper_path="$CLAUDE_LOCAL_PATH"
    if [[ ! -d "$wrapper_path" ]]; then
        wrapper_path="$ATOMIC_ROOT/../claude-local"
    fi

    echo "Claude-Local Wrapper Status:"
    echo "  Path: $wrapper_path"
    if [[ -d "$wrapper_path" ]]; then
        echo "  Status: Found"
        if [[ -f "$wrapper_path/local_launcher/__main__.py" ]]; then
            echo "  Main module: OK"
        else
            echo "  Main module: MISSING"
        fi
    else
        echo "  Status: NOT FOUND"
    fi
    echo "  Default provider: $CLAUDE_PROVIDER"
    echo "  Ollama host: $CLAUDE_OLLAMA_HOST"
    echo "  Role mapping:"
    for role in "${!PROVIDER_ROLE_MAP[@]}"; do
        echo "    $role → ${PROVIDER_ROLE_MAP[$role]}"
    done
}

# ============================================================================
# CORE: ATOMIC INVOKE
# ============================================================================

# atomic_invoke <prompt_file|prompt_string> <output_file> <description> [options]
# Options:
#   --model=<model>        Override default model (sonnet|opus|haiku|ollama-model)
#   --provider=<provider>  Override provider (ollama|api|max)
#   --role=<role>          Use role-based provider routing (primary|fast|gardener|heavyweight)
#   --format=json          Expect JSON output, validate it
#   --format=markdown      Expect markdown output
#   --timeout=<seconds>    Override default timeout
#   --stdin                Read additional context from stdin to append to prompt
#   --ollama-host=<url>    Override Ollama host URL
#
atomic_invoke() {
    local prompt_source="$1"
    local output_file="$2"
    local description="$3"
    shift 3

    # Ensure provider configuration is loaded
    _atomic_ensure_config

    # Parse options
    local model="$CLAUDE_MODEL"
    local provider="$CLAUDE_PROVIDER"
    local role=""
    local format=""
    local timeout="$CLAUDE_TIMEOUT"
    local use_stdin=false
    local max_retries="${ATOMIC_MAX_RETRIES:-2}"
    local retry_delay="${ATOMIC_RETRY_DELAY:-5}"
    local ollama_host="$CLAUDE_OLLAMA_HOST"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --model=*) model="${1#*=}" ;;
            --provider=*) provider="${1#*=}" ;;
            --role=*) role="${1#*=}" ;;
            --format=*) format="${1#*=}" ;;
            --timeout=*) timeout="${1#*=}" ;;
            --retries=*) max_retries="${1#*=}" ;;
            --retry-delay=*) retry_delay="${1#*=}" ;;
            --stdin) use_stdin=true ;;
            --ollama-host=*) ollama_host="${1#*=}" ;;
            *) atomic_warn "Unknown option: $1" ;;
        esac
        shift
    done

    # Role-based provider routing
    if [[ -n "$role" ]]; then
        provider="${PROVIDER_ROLE_MAP[$role]:-$provider}"
        atomic_substep "Role '$role' → Provider '$provider'"
    fi

    atomic_step "ATOMIC TASK: $description"

    # Determine prompt content
    local prompt_content
    if [[ -f "$prompt_source" ]]; then
        atomic_substep "Prompt file: $prompt_source"
        prompt_content=$(cat "$prompt_source")
    else
        atomic_substep "Prompt: inline string"
        prompt_content="$prompt_source"
    fi

    # Append stdin if requested
    if $use_stdin; then
        local stdin_content
        stdin_content=$(cat)
        prompt_content="$prompt_content

---
CONTEXT:
$stdin_content"
    fi

    atomic_substep "Output: $output_file"
    atomic_substep "Model: $model"
    atomic_substep "Provider: $provider"

    # Update state
    atomic_state_set "current_task" "\"$description\""

    # Create output directory if needed
    mkdir -p "$(dirname "$output_file")"

    # Show sticky mode indicator bar (green=online, red=offline)
    if [[ -t 1 ]]; then
        # Interactive terminal - use sticky bar
        atomic_mode_bar_init "$provider" "$model"
    else
        # Non-interactive - use simple bar
        atomic_mode_bar_simple "$provider" "$model"
    fi

    atomic_waiting "Invoking Claude..."
    echo ""

    # Build the invocation command using claude-local wrapper
    local invoke_cmd
    invoke_cmd=$(_atomic_build_invoke_cmd "$prompt_content" "$model" "$provider" "$ollama_host")

    # THE ATOMIC INVOCATION (with retry logic)
    local start_time=$(date +%s)
    local exit_code=0
    local attempt=1
    local total_duration=0

    while [[ $attempt -le $((max_retries + 1)) ]]; do
        local attempt_start=$(date +%s)

        if timeout "$timeout" bash -c "$invoke_cmd" > "$output_file" 2>&1; then
            exit_code=0
            break
        else
            exit_code=$?
        fi

        local attempt_end=$(date +%s)
        local attempt_duration=$((attempt_end - attempt_start))
        total_duration=$((total_duration + attempt_duration))

        # Check if it's a timeout (exit code 124) and we have retries left
        if [[ $exit_code -eq 124 ]] && [[ $attempt -lt $((max_retries + 1)) ]]; then
            atomic_warn "Timeout on attempt $attempt/$((max_retries + 1)), retrying in ${retry_delay}s..."
            sleep "$retry_delay"
            # Exponential backoff
            retry_delay=$((retry_delay * 2))
            ((attempt++))
        else
            # Not a timeout or no retries left
            break
        fi
    done

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Log the invocation (project-prefixed log file)
    local log_file
    log_file=$(atomic_log_file)
    mkdir -p "$(dirname "$log_file")"
    echo "[$(date -Iseconds)] task=\"$description\" provider=$provider model=$model duration=${duration}s exit=$exit_code output=$output_file" >> "$log_file"

    # Clear sticky mode bar before reporting results
    atomic_mode_bar_clear

    if [[ $exit_code -eq 0 ]]; then
        atomic_success "Claude completed task (${duration}s)"
        atomic_substep "Output written to: $output_file"

        # Validate output format if specified
        if [[ "$format" == "json" ]]; then
            if jq . "$output_file" > /dev/null 2>&1; then
                atomic_success "JSON output validated"
            else
                atomic_warn "Output is not valid JSON - may need extraction"
            fi
        fi

        atomic_state_increment "tasks_completed"
        return 0
    else
        if [[ $exit_code -eq 124 ]]; then
            atomic_error "Claude task timed out after $attempt attempt(s)"
        else
            atomic_error "Claude task failed (exit code: $exit_code)"
        fi
        atomic_substep "Check output file for details: $output_file"
        atomic_state_increment "tasks_failed"
        return $exit_code
    fi
}

# ============================================================================
# ROLE-BASED INVOCATION HELPERS
# ============================================================================

# atomic_invoke_fast - Use fast/cheap model (typically Ollama)
# For: validation, extraction, simple tasks
atomic_invoke_fast() {
    atomic_invoke "$@" --role=fast
}

# atomic_invoke_primary - Use primary workhorse model (typically Max/API sonnet)
# For: complex analysis, code generation, PRD authoring
atomic_invoke_primary() {
    atomic_invoke "$@" --role=primary
}

# atomic_invoke_heavyweight - Use most capable model (typically Max opus)
# For: architecture decisions, critical reasoning, complex synthesis
atomic_invoke_heavyweight() {
    atomic_invoke "$@" --role=heavyweight
}

# atomic_invoke_gardener - Use context gardening model (typically Ollama haiku)
# For: summarization, context compression, adjudication
atomic_invoke_gardener() {
    atomic_invoke "$@" --role=gardener
}

# atomic_invoke_ollama - Explicitly use Ollama provider
# For: bulk operations, offline mode, cost-free tasks
atomic_invoke_ollama() {
    local model="${CLAUDE_OLLAMA_MODEL:-devstral:24b}"
    atomic_invoke "$@" --provider=ollama --model="$model"
}

# atomic_invoke_max - Explicitly use Claude Max subscription
# For: premium tasks requiring best quality
atomic_invoke_max() {
    local model="${1:-sonnet}"
    shift
    atomic_invoke "$@" --provider=max --model="$model"
}

# atomic_invoke_api - Explicitly use Anthropic API
# For: programmatic access, specific API requirements
atomic_invoke_api() {
    local model="${1:-sonnet}"
    shift
    atomic_invoke "$@" --provider=api --model="$model"
}

# ============================================================================
# TASK CHAINING HELPERS
# ============================================================================

# atomic_chain runs a series of tasks, stopping on first failure
atomic_chain() {
    local tasks=("$@")
    local task_num=1
    local total_tasks=${#tasks[@]}

    atomic_header "Running ${total_tasks} chained tasks"

    for task in "${tasks[@]}"; do
        atomic_step "Task $task_num/$total_tasks"
        if ! eval "$task"; then
            atomic_error "Chain stopped at task $task_num"
            return 1
        fi
        ((task_num++))
    done

    atomic_success "All $total_tasks tasks completed"
    return 0
}

# atomic_gate prompts user for confirmation before proceeding
atomic_gate() {
    local message="$1"
    local default="${2:-n}"

    echo ""
    echo -e "${MAGENTA}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║${NC} ${BOLD}HUMAN GATE${NC}                                              ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}╠═══════════════════════════════════════════════════════════╣${NC}"
    echo -e "${MAGENTA}║${NC} $message"
    echo -e "${MAGENTA}╚═══════════════════════════════════════════════════════════╝${NC}"

    local prompt="Proceed? [y/N]: "
    [[ "$default" == "y" ]] && prompt="Proceed? [Y/n]: "

    read -p "$prompt" response
    response=${response:-$default}

    if [[ "$response" =~ ^[Yy] ]]; then
        atomic_success "Gate passed"
        return 0
    else
        atomic_info "Gate declined by user"
        return 1
    fi
}

# atomic_validate checks if required files exist
atomic_validate_files() {
    local missing=()

    for file in "$@"; do
        if [[ ! -f "$file" ]]; then
            missing+=("$file")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        atomic_error "Missing required files:"
        for f in "${missing[@]}"; do
            echo "  - $f"
        done
        return 1
    fi

    atomic_success "All required files present"
    return 0
}

# atomic_extract_json extracts JSON from mixed Claude output
atomic_extract_json() {
    local input_file="$1"
    local output_file="$2"

    # Try to find JSON block in output
    if grep -q '```json' "$input_file"; then
        sed -n '/```json/,/```/p' "$input_file" | sed '1d;$d' > "$output_file"
    elif grep -q '^{' "$input_file"; then
        # Assume raw JSON
        cp "$input_file" "$output_file"
    else
        atomic_error "No JSON found in output"
        return 1
    fi

    # Validate
    if jq . "$output_file" > /dev/null 2>&1; then
        atomic_success "JSON extracted and validated"
        return 0
    else
        atomic_error "Extracted content is not valid JSON"
        return 1
    fi
}

# ============================================================================
# PROMPT TEMPLATE HELPERS
# ============================================================================

# atomic_template substitutes variables in a prompt template
# Usage: atomic_template template.md VAR1=value1 VAR2=value2
atomic_template() {
    local template_file="$1"
    shift

    local content
    content=$(cat "$template_file")

    for pair in "$@"; do
        local key="${pair%%=*}"
        local value="${pair#*=}"
        content="${content//\{\{$key\}\}/$value}"
    done

    echo "$content"
}

# atomic_compose builds a prompt from multiple parts
atomic_compose() {
    local output=""

    for part in "$@"; do
        if [[ -f "$part" ]]; then
            output+="$(cat "$part")"
        else
            output+="$part"
        fi
        output+=$'\n\n'
    done

    echo "$output"
}

# ============================================================================
# PROJECT NAME UTILITIES
# ============================================================================

# Validate project name
# Rules: 3-24 chars, alphanumeric + hyphens + underscores, must start with alphanumeric
atomic_validate_project_name() {
    local name="$1"

    # Check length
    if [[ ${#name} -lt 3 ]]; then
        echo "Too short (minimum 3 characters)"
        return 1
    fi
    if [[ ${#name} -gt 24 ]]; then
        echo "Too long (maximum 24 characters)"
        return 1
    fi

    # Check for valid characters only
    if [[ ! "$name" =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]]; then
        if [[ "$name" =~ [[:space:]] ]]; then
            echo "Spaces not allowed"
        elif [[ "$name" =~ ^[-_] ]]; then
            echo "Must start with a letter or number"
        else
            echo "Only letters, numbers, hyphens (-) and underscores (_) allowed"
        fi
        return 1
    fi

    return 0
}

# Sanitize a string for safe use in file paths
# Removes/replaces dangerous characters
# Usage: atomic_sanitize_path "user input"
atomic_sanitize_path() {
    local input="$1"
    local sanitized

    # Remove null bytes
    sanitized="${input//$'\0'/}"

    # Remove path traversal patterns
    sanitized="${sanitized//\.\./}"

    # Remove leading/trailing whitespace
    sanitized="${sanitized#"${sanitized%%[![:space:]]*}"}"
    sanitized="${sanitized%"${sanitized##*[![:space:]]}"}"

    # Replace potentially dangerous characters with underscores
    sanitized=$(echo "$sanitized" | tr -cd 'A-Za-z0-9._-/')

    echo "$sanitized"
}

# Sanitize a string for safe use in shell commands
# More restrictive than path sanitization
# Usage: atomic_sanitize_string "user input"
atomic_sanitize_string() {
    local input="$1"
    local sanitized

    # Remove null bytes and newlines
    sanitized="${input//$'\0'/}"
    sanitized="${sanitized//$'\n'/ }"
    sanitized="${sanitized//$'\r'/}"

    # Remove shell-dangerous characters
    sanitized=$(echo "$sanitized" | tr -cd 'A-Za-z0-9 ._-')

    echo "$sanitized"
}

# Validate a file path is safe
# Returns 0 if safe, 1 if dangerous
# Usage: atomic_validate_path "/some/path"
atomic_validate_path() {
    local path="$1"

    # Check for null bytes
    if [[ "$path" == *$'\0'* ]]; then
        echo "Path contains null byte"
        return 1
    fi

    # Check for path traversal
    if [[ "$path" == *".."* ]]; then
        echo "Path contains directory traversal"
        return 1
    fi

    # Check for suspicious patterns
    if [[ "$path" =~ ^\~|^\$|^\||^\; ]]; then
        echo "Path contains suspicious prefix"
        return 1
    fi

    return 0
}

# ============================================================================
# CONFIG SCHEMA VALIDATION
# ============================================================================

# Validate models.json configuration
# Usage: atomic_validate_models_config [config_file]
atomic_validate_models_config() {
    local config_file="${1:-$ATOMIC_ROOT/config/models.json}"

    # Check file exists
    if [[ ! -f "$config_file" ]]; then
        echo "Models config not found: $config_file"
        return 1
    fi

    # Check valid JSON
    if ! jq empty "$config_file" 2>/dev/null; then
        echo "Invalid JSON in models config"
        return 1
    fi

    # Check required structure
    if ! jq -e '.models' "$config_file" >/dev/null 2>&1; then
        echo "Missing required 'models' key in config"
        return 1
    fi

    # Check at least one provider exists
    local provider_count
    provider_count=$(jq '.models | keys | length' "$config_file")
    if [[ "$provider_count" -lt 1 ]]; then
        echo "No providers defined in models config"
        return 1
    fi

    # Validate each model has required fields
    local invalid_models
    invalid_models=$(jq -r '
        [.models | to_entries[] | .value | to_entries[] |
         select(.value.context_window == null or .value.cost_tier == null) |
         .key] | join(", ")
    ' "$config_file")

    if [[ -n "$invalid_models" ]]; then
        echo "Models missing required fields (context_window, cost_tier): $invalid_models"
        return 1
    fi

    return 0
}

# Validate project-config.json
# Usage: atomic_validate_project_config [config_file]
atomic_validate_project_config() {
    local config_file="${1:-$ATOMIC_OUTPUT_DIR/0-setup/project-config.json}"

    # Check file exists
    if [[ ! -f "$config_file" ]]; then
        echo "Project config not found: $config_file"
        return 1
    fi

    # Check valid JSON
    if ! jq empty "$config_file" 2>/dev/null; then
        echo "Invalid JSON in project config"
        return 1
    fi

    # Check required structure
    local missing_fields=()

    if ! jq -e '.project' "$config_file" >/dev/null 2>&1; then
        missing_fields+=("project")
    fi

    if ! jq -e '.project.name' "$config_file" >/dev/null 2>&1; then
        missing_fields+=("project.name")
    fi

    if [[ ${#missing_fields[@]} -gt 0 ]]; then
        echo "Missing required fields: ${missing_fields[*]}"
        return 1
    fi

    # Validate project name
    local project_name
    project_name=$(jq -r '.project.name // ""' "$config_file")
    if ! atomic_validate_project_name "$project_name" >/dev/null 2>&1; then
        echo "Invalid project name: $(atomic_validate_project_name "$project_name")"
        return 1
    fi

    return 0
}

# Validate all configuration files
# Usage: atomic_validate_all_configs
atomic_validate_all_configs() {
    local errors=()

    # Validate models config if it exists
    if [[ -f "$ATOMIC_ROOT/config/models.json" ]]; then
        if ! atomic_validate_models_config; then
            errors+=("models.json")
        fi
    fi

    # Validate project config if it exists
    if [[ -f "$ATOMIC_OUTPUT_DIR/0-setup/project-config.json" ]]; then
        if ! atomic_validate_project_config; then
            errors+=("project-config.json")
        fi
    fi

    if [[ ${#errors[@]} -gt 0 ]]; then
        echo "Config validation failed for: ${errors[*]}"
        return 1
    fi

    return 0
}

# Get project name from config (or fallback to directory name)
atomic_get_project_name() {
    local config_file="$ATOMIC_OUTPUT_DIR/0-setup/project-config.json"

    # Try to get from config
    if [[ -f "$config_file" ]]; then
        local name
        name=$(jq -r '.project.name // empty' "$config_file" 2>/dev/null || true)
        if [[ -n "$name" ]]; then
            echo "$name"
            return 0
        fi
    fi

    # Fallback to sanitized directory name
    local dir_name
    dir_name=$(basename "$(pwd)")
    dir_name=$(echo "$dir_name" | tr ' ' '-' | tr -cd 'A-Za-z0-9_-' | cut -c1-24)
    [[ -z "$dir_name" ]] && dir_name="project"

    echo "$dir_name"
}

# Get project-prefixed output directory for a phase
# Usage: atomic_output_path "0-setup" -> ".outputs/PRD-100-XYZ/0-setup"
atomic_output_path() {
    local phase="${1:-}"
    local project_name
    project_name=$(atomic_get_project_name)

    if [[ -n "$phase" ]]; then
        echo "$ATOMIC_OUTPUT_DIR/$project_name/$phase"
    else
        echo "$ATOMIC_OUTPUT_DIR/$project_name"
    fi
}

# Get project-prefixed log file name
# Usage: atomic_log_file -> "PRD-100-XYZ-2024-01-15.log"
atomic_log_file() {
    local project_name
    project_name=$(atomic_get_project_name)
    local date_stamp
    date_stamp=$(date +%Y-%m-%d)

    echo "$ATOMIC_LOG_DIR/${project_name}-${date_stamp}.log"
}

# Get git tag name for phase completion
# Usage: atomic_git_tag "0-setup" -> "PRD-100-XYZ-phase-0-setup-complete"
atomic_git_tag() {
    local phase="$1"
    local project_name
    project_name=$(atomic_get_project_name)

    echo "${project_name}-phase-${phase}-complete"
}

# Format phase header with project name
# Usage: atomic_phase_header "0" "Setup" -> "PHASE 0: SETUP [PRD-100-XYZ]"
atomic_phase_header() {
    local phase_num="$1"
    local phase_name="$2"
    local project_name
    project_name=$(atomic_get_project_name)

    echo "PHASE ${phase_num}: ${phase_name^^} [${project_name}]"
}

# ============================================================================
# CONTEXT MANAGEMENT
# ============================================================================

# Context directory for current phase
ATOMIC_CONTEXT_DIR=""

# Task context state (set by tasks via atomic_task_context)
TASK_CONTEXT_REQUIRED=()
TASK_CONTEXT_OPTIONAL=()
TASK_HEAVY_LIFT=false
TASK_ASK_SUFFICIENCY=false
TASK_CONTEXT=""
TASK_AMENDED_CONTEXT=""

# Initialize context directory for a phase
# Usage: atomic_context_init "0-setup"
atomic_context_init() {
    local phase_id="$1"
    ATOMIC_CONTEXT_DIR="$ATOMIC_OUTPUT_DIR/$phase_id/context"
    mkdir -p "$ATOMIC_CONTEXT_DIR"

    # Initialize summary if doesn't exist
    if [[ ! -f "$ATOMIC_CONTEXT_DIR/summary.md" ]]; then
        cat > "$ATOMIC_CONTEXT_DIR/summary.md" << 'EOF'
# Project Context Summary

*This file is automatically maintained. It provides rolling context for LLM tasks.*

## Project
- Name: (not yet configured)
- Type: (not yet configured)
- Goal: (not yet configured)

## Current Phase
- Phase: (initializing)
- Status: (starting)

## Key Decisions
(none yet)

## Recent Activity
(none yet)
EOF
    fi

    # Initialize decisions log if doesn't exist
    if [[ ! -f "$ATOMIC_CONTEXT_DIR/decisions.json" ]]; then
        echo '[]' > "$ATOMIC_CONTEXT_DIR/decisions.json"
    fi

    # Initialize artifacts index if doesn't exist
    if [[ ! -f "$ATOMIC_CONTEXT_DIR/artifacts.json" ]]; then
        echo '{"artifacts": []}' > "$ATOMIC_CONTEXT_DIR/artifacts.json"
    fi
}

# Record a decision to the context (simple version)
# Usage: atomic_context_decision "Selected guided setup mode" "user_choice"
atomic_context_decision() {
    local decision="$1"
    local category="${2:-general}"
    local decisions_file="$ATOMIC_CONTEXT_DIR/decisions.json"

    if [[ -f "$decisions_file" ]]; then
        local tmp=$(atomic_mktemp)
        jq ". + [{
            \"decision\": \"$decision\",
            \"category\": \"$category\",
            \"timestamp\": \"$(date -Iseconds)\",
            \"task\": \"$(atomic_state_get current_task)\",
            \"phase\": \"${CURRENT_PHASE:-unknown}\"
        }]" "$decisions_file" > "$tmp" && mv "$tmp" "$decisions_file"
    fi
}

# Record a decision with full rationale (enhanced version)
# Usage: atomic_context_decision_with_rationale \
#          "decision" "category" "rationale" "alternatives" "impact"
atomic_context_decision_with_rationale() {
    local decision="$1"
    local category="${2:-general}"
    local rationale="${3:-}"
    local alternatives="${4:-}"  # Comma-separated list
    local impact="${5:-}"
    local decisions_file="$ATOMIC_CONTEXT_DIR/decisions.json"

    # Convert alternatives to JSON array
    local alternatives_json="[]"
    if [[ -n "$alternatives" ]]; then
        alternatives_json=$(echo "$alternatives" | tr ',' '\n' | jq -R . | jq -s .)
    fi

    if [[ -f "$decisions_file" ]]; then
        local tmp=$(atomic_mktemp)
        jq --arg decision "$decision" \
           --arg category "$category" \
           --arg rationale "$rationale" \
           --argjson alternatives "$alternatives_json" \
           --arg impact "$impact" \
           --arg timestamp "$(date -Iseconds)" \
           --arg task "$(atomic_state_get current_task)" \
           --arg phase "${CURRENT_PHASE:-unknown}" \
           '. + [{
               "decision": $decision,
               "category": $category,
               "timestamp": $timestamp,
               "task": $task,
               "phase": $phase,
               "rationale": (if $rationale != "" then $rationale else null end),
               "alternatives_considered": $alternatives,
               "impact_assessment": (if $impact != "" then $impact else null end)
           }]' "$decisions_file" > "$tmp" && mv "$tmp" "$decisions_file"
    fi

    # Also log to decision log for human review
    local decision_log="$ATOMIC_CONTEXT_DIR/decision-log.md"
    if [[ -d "$ATOMIC_CONTEXT_DIR" ]]; then
        {
            echo ""
            echo "## Decision: $decision"
            echo ""
            echo "- **Category:** $category"
            echo "- **Phase:** ${CURRENT_PHASE:-unknown}"
            echo "- **Timestamp:** $(date -Iseconds)"
            [[ -n "$rationale" ]] && echo "- **Rationale:** $rationale"
            [[ -n "$alternatives" ]] && echo "- **Alternatives Considered:** $alternatives"
            [[ -n "$impact" ]] && echo "- **Impact:** $impact"
            echo ""
            echo "---"
        } >> "$decision_log"
    fi
}

# Record an artifact to the context
# Usage: atomic_context_artifact "project-config.json" "Project configuration" "config"
atomic_context_artifact() {
    local file_path="$1"
    local description="$2"
    local artifact_type="${3:-output}"
    local artifacts_file="$ATOMIC_CONTEXT_DIR/artifacts.json"

    if [[ -f "$artifacts_file" ]]; then
        local tmp=$(atomic_mktemp)
        jq ".artifacts += [{
            \"path\": \"$file_path\",
            \"description\": \"$description\",
            \"type\": \"$artifact_type\",
            \"created_at\": \"$(date -Iseconds)\"
        }]" "$artifacts_file" > "$tmp" && mv "$tmp" "$artifacts_file"
    fi
}

# Build context from files
# Usage: context=$(atomic_build_context file1.md file2.json ...)
atomic_build_context() {
    local context=""

    # Always include summary if it exists and context dir is set
    if [[ -n "$ATOMIC_CONTEXT_DIR" ]] && [[ -f "$ATOMIC_CONTEXT_DIR/summary.md" ]]; then
        context+="# Project Context Summary
$(cat "$ATOMIC_CONTEXT_DIR/summary.md")

"
    fi

    # Add each requested file
    for file in "$@"; do
        if [[ -f "$file" ]]; then
            local filename=$(basename "$file")
            local extension="${filename##*.}"

            context+="---
=== $filename ===
"
            # Format based on file type
            case "$extension" in
                json)
                    context+='```json
'
                    context+="$(cat "$file")"
                    context+='
```'
                    ;;
                md)
                    context+="$(cat "$file")"
                    ;;
                *)
                    context+="$(cat "$file")"
                    ;;
            esac
            context+="

"
        else
            context+="---
=== $file ===
(file not found)

"
        fi
    done

    echo "$context"
}

# Declare task context requirements
# Usage: atomic_task_context required=file1,file2 optional=file3 heavy=true ask=true
atomic_task_context() {
    # Reset state
    TASK_CONTEXT_REQUIRED=()
    TASK_CONTEXT_OPTIONAL=()
    TASK_HEAVY_LIFT=false
    TASK_ASK_SUFFICIENCY=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            required=*)
                IFS=',' read -ra TASK_CONTEXT_REQUIRED <<< "${1#*=}"
                ;;
            optional=*)
                IFS=',' read -ra TASK_CONTEXT_OPTIONAL <<< "${1#*=}"
                ;;
            heavy=*)
                [[ "${1#*=}" == "true" ]] && TASK_HEAVY_LIFT=true
                ;;
            ask=*)
                [[ "${1#*=}" == "true" ]] && TASK_ASK_SUFFICIENCY=true
                ;;
        esac
        shift
    done

    # Build context from declared files
    TASK_CONTEXT=$(atomic_build_context "${TASK_CONTEXT_REQUIRED[@]}" "${TASK_CONTEXT_OPTIONAL[@]}")
}

# Pre-flight context sufficiency check
# Uses haiku for speed/cost efficiency
# Returns: 0 if sufficient, 1 if needs more context
atomic_preflight_check() {
    local task_description="$1"
    local context="$2"
    local preflight_output="$ATOMIC_CONTEXT_DIR/preflight-check.json"

    atomic_substep "Running pre-flight context check..."

    local preflight_prompt=$(cat << EOF
# Pre-flight Context Check

You are about to help with: **$task_description**

## Context Provided:
$context

## Your Assessment

Evaluate if you have sufficient context to complete this task effectively.

Respond with ONLY valid JSON (no markdown, no explanation):
{
  "sufficient": "yes" | "partially" | "no",
  "confidence": 0.0-1.0,
  "missing": ["list of specific information that would help"],
  "questions": ["clarifying questions you would ask before starting"]
}
EOF
)

    # Quick check with haiku
    if atomic_invoke "$preflight_prompt" "$preflight_output" "Context sufficiency check" --model=haiku --format=json; then
        # Parse result
        local sufficient=$(jq -r '.sufficient // "unknown"' "$preflight_output" 2>/dev/null || echo "unknown")

        if [[ "$sufficient" == "yes" ]]; then
            atomic_success "Context check: sufficient"
            return 0
        elif [[ "$sufficient" == "partially" ]]; then
            atomic_warn "Context check: partially sufficient"
            return 1
        else
            atomic_warn "Context check: insufficient"
            return 1
        fi
    else
        atomic_warn "Pre-flight check failed, proceeding anyway"
        return 0
    fi
}

# Interactive context amendment
# Allows user to add more context when pre-flight indicates insufficiency
atomic_amend_context() {
    local preflight_file="$ATOMIC_CONTEXT_DIR/preflight-check.json"

    # Display what's missing
    if [[ -f "$preflight_file" ]]; then
        local missing=$(jq -r '.missing[]? // empty' "$preflight_file" 2>/dev/null)
        local questions=$(jq -r '.questions[]? // empty' "$preflight_file" 2>/dev/null)

        if [[ -n "$missing" ]]; then
            echo ""
            echo -e "${YELLOW}  Claude identified missing context:${NC}"
            echo "$missing" | while read -r item; do
                [[ -n "$item" ]] && echo -e "    ${DIM}•${NC} $item"
            done
        fi

        if [[ -n "$questions" ]]; then
            echo ""
            echo -e "${YELLOW}  Claude has questions:${NC}"
            echo "$questions" | while read -r q; do
                [[ -n "$q" ]] && echo -e "    ${DIM}?${NC} $q"
            done
        fi
    fi

    echo ""
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${GREEN}[a]${NC} Add file to context"
    echo -e "  ${GREEN}[t]${NC} Type additional context"
    echo -e "  ${GREEN}[r]${NC} Re-run pre-flight check"
    echo -e "  ${DIM}[p]${NC} Proceed anyway"
    echo -e "  ${RED}[q]${NC} Abort task"
    echo ""

    while true; do
        read -p "  Choice [p]: " choice
        choice=${choice:-p}

        case "$choice" in
            a|A)
                read -p "  File path: " file_path
                if [[ -f "$file_path" ]]; then
                    TASK_AMENDED_CONTEXT+="
---
=== $(basename "$file_path") (user added) ===
$(cat "$file_path")
"
                    atomic_success "Added: $file_path"
                else
                    atomic_error "File not found: $file_path"
                fi
                ;;
            t|T)
                echo -e "  ${DIM}Enter additional context (Ctrl+D when done):${NC}"
                local user_input
                user_input=$(cat)
                TASK_AMENDED_CONTEXT+="
---
=== User Provided Context ===
$user_input
"
                atomic_success "Context added"
                ;;
            r|R)
                # Re-run check with amended context
                local full_context="$TASK_CONTEXT$TASK_AMENDED_CONTEXT"
                atomic_preflight_check "$(atomic_state_get current_task)" "$full_context"
                ;;
            p|P)
                atomic_info "Proceeding with available context"
                return 0
                ;;
            q|Q)
                atomic_error "Task aborted by user"
                return 1
                ;;
            *)
                atomic_error "Invalid choice"
                ;;
        esac
    done
}

# Invoke with full context management
# Usage: atomic_invoke_contextual <prompt_file> <output_file> <description> [options]
# Handles: context building, pre-flight check, amendment, final invocation
atomic_invoke_contextual() {
    local prompt_source="$1"
    local output_file="$2"
    local description="$3"
    shift 3

    # Parse options (same as atomic_invoke plus context options)
    local model="$CLAUDE_MODEL"
    local format=""
    local timeout="$CLAUDE_TIMEOUT"
    local skip_preflight=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --model=*) model="${1#*=}" ;;
            --format=*) format="${1#*=}" ;;
            --timeout=*) timeout="${1#*=}" ;;
            --skip-preflight) skip_preflight=true ;;
            *) ;; # Ignore unknown for now
        esac
        shift
    done

    # Build full context
    local full_context="$TASK_CONTEXT$TASK_AMENDED_CONTEXT"

    # Pre-flight check for heavy tasks
    if [[ "$TASK_HEAVY_LIFT" == true ]] && [[ "$TASK_ASK_SUFFICIENCY" == true ]] && [[ "$skip_preflight" == false ]]; then
        if ! atomic_preflight_check "$description" "$full_context"; then
            # Offer to amend context
            if ! atomic_amend_context; then
                return 1  # User aborted
            fi
            # Rebuild with amendments
            full_context="$TASK_CONTEXT$TASK_AMENDED_CONTEXT"
        fi
    fi

    # Determine prompt content
    local prompt_content
    if [[ -f "$prompt_source" ]]; then
        prompt_content=$(cat "$prompt_source")
    else
        prompt_content="$prompt_source"
    fi

    # Combine context + prompt
    local full_prompt="$full_context

---
# Task Instructions

$prompt_content"

    # Invoke
    atomic_invoke "$full_prompt" "$output_file" "$description" --model="$model" --format="$format" --timeout="$timeout"
    local result=$?

    # Record artifact
    if [[ $result -eq 0 ]]; then
        atomic_context_artifact "$output_file" "$description" "llm_output"
    fi

    return $result
}

# Update context summary (LLM task to refresh the rolling summary)
# Usage: atomic_context_refresh
atomic_context_refresh() {
    local summary_file="$ATOMIC_CONTEXT_DIR/summary.md"
    local decisions_file="$ATOMIC_CONTEXT_DIR/decisions.json"
    local artifacts_file="$ATOMIC_CONTEXT_DIR/artifacts.json"
    local refresh_output="$ATOMIC_CONTEXT_DIR/summary-new.md"

    atomic_substep "Refreshing context summary..."

    local refresh_prompt=$(cat << EOF
# Task: Update Project Context Summary

You are maintaining a rolling context summary for a software development pipeline.
Update the summary based on recent activity.

## Current Summary:
$(cat "$summary_file")

## Recent Decisions:
$(jq -r '.[-10:][] | "- [\(.category)] \(.decision)"' "$decisions_file" 2>/dev/null || echo "(none)")

## Recent Artifacts:
$(jq -r '.artifacts[-10:][] | "- \(.path): \(.description)"' "$artifacts_file" 2>/dev/null || echo "(none)")

## Instructions:
1. Update the summary to reflect current project state
2. Keep it concise (under 50 lines)
3. Preserve the markdown structure
4. Focus on information useful for subsequent LLM tasks
5. Output ONLY the updated markdown summary, no explanations

Updated summary:
EOF
)

    if atomic_invoke "$refresh_prompt" "$refresh_output" "Refresh context summary" --model=haiku; then
        # Validate output isn't empty/broken
        if [[ -s "$refresh_output" ]] && grep -q "^#" "$refresh_output"; then
            mv "$refresh_output" "$summary_file"
            atomic_success "Context summary updated"
        else
            atomic_warn "Summary refresh produced invalid output, keeping original"
            rm -f "$refresh_output"
        fi
    fi
}

# ============================================================================
# MODEL REGISTRY & TOKEN MANAGEMENT
# ============================================================================

ATOMIC_MODELS_CONFIG="${ATOMIC_MODELS_CONFIG:-$ATOMIC_ROOT/config/models.json}"

# Discover available Ollama models and merge with known registry
# Usage: atomic_discover_models
atomic_discover_models() {
    local models_config="$ATOMIC_MODELS_CONFIG"
    local discovered_file="$ATOMIC_STATE_DIR/discovered-models.json"

    mkdir -p "$ATOMIC_STATE_DIR"

    # Start with static config or create minimal default
    if [[ -f "$models_config" ]]; then
        cp "$models_config" "$discovered_file"
    else
        cat > "$discovered_file" << 'DEFAULTMODELS'
{
  "models": {
    "claude": {
      "opus": {"context_window": 200000, "cost_tier": "high"},
      "sonnet": {"context_window": 200000, "cost_tier": "medium"},
      "haiku": {"context_window": 200000, "cost_tier": "low"}
    },
    "ollama": {}
  },
  "defaults": {"primary": "sonnet", "fast": "haiku", "gardener": "haiku"}
}
DEFAULTMODELS
    fi

    # Check if Ollama is available
    if ! command -v ollama &>/dev/null; then
        return 0
    fi

    atomic_substep "Discovering Ollama models..."

    # Get list of installed models
    local ollama_models=$(ollama list 2>/dev/null | tail -n +2 | awk '{print $1}')

    [[ -z "$ollama_models" ]] && return 0

    # For each discovered model, add to registry if not already present
    while IFS= read -r model; do
        [[ -z "$model" ]] && continue

        local exists=$(jq -r ".models.ollama[\"$model\"] // null" "$discovered_file" 2>/dev/null)

        if [[ "$exists" == "null" ]]; then
            local context_window=$(atomic_infer_context_window "$model")
            local tmp=$(atomic_mktemp)
            jq --arg model "$model" --argjson ctx "$context_window" '
                .models.ollama[$model] = {
                    "context_window": $ctx,
                    "cost_tier": "free",
                    "discovered": true
                }
            ' "$discovered_file" > "$tmp" && mv "$tmp" "$discovered_file"

            atomic_substep "  Found: $model (${context_window} tokens)"
        fi
    done <<< "$ollama_models"
}

# Infer context window from model name patterns
atomic_infer_context_window() {
    local model="$1"

    case "$model" in
        *llama3.1*|*llama-3.1*) echo "128000" ;;
        *llama3*|*llama-3*) echo "8000" ;;
        *llama2*|*llama-2*) echo "4096" ;;
        *mistral*|*mixtral*) echo "32000" ;;
        *codellama*|*code-llama*) echo "16000" ;;
        *phi3*|*phi-3*) echo "128000" ;;
        *phi*) echo "4096" ;;
        *qwen2*|*qwen-2*) echo "32000" ;;
        *qwen*) echo "8000" ;;
        *deepseek*coder*) echo "16000" ;;
        *deepseek*) echo "32000" ;;
        *gemma*) echo "8000" ;;
        *yi*) echo "32000" ;;
        *wizard*|*starcoder*) echo "8000" ;;
        *) echo "4096" ;;  # Conservative default
    esac
}

# Get token limit for a model
# Usage: limit=$(atomic_model_token_limit "llama3.1:8b")
atomic_model_token_limit() {
    local model="$1"
    local discovered_file="$ATOMIC_STATE_DIR/discovered-models.json"

    [[ ! -f "$discovered_file" ]] && atomic_discover_models

    # Check Claude models (short names)
    case "$model" in
        opus|sonnet|haiku)
            jq -r ".models.claude.${model}.context_window // 200000" "$discovered_file" 2>/dev/null || echo "200000"
            return ;;
    esac

    # Check Ollama models
    local limit=$(jq -r ".models.ollama[\"${model}\"].context_window // null" "$discovered_file" 2>/dev/null)

    if [[ "$limit" != "null" && -n "$limit" ]]; then
        echo "$limit"
    else
        echo "4096"  # Conservative fallback
    fi
}

# Get the configured model for a role (primary, fast, gardener)
# Usage: model=$(atomic_get_model "gardener")
atomic_get_model() {
    local role="$1"
    local project_config="$ATOMIC_OUTPUT_DIR/${CURRENT_PHASE:-0-setup}/project-config.json"
    local discovered_file="$ATOMIC_STATE_DIR/discovered-models.json"

    [[ ! -f "$discovered_file" ]] && atomic_discover_models

    # Try project config first
    if [[ -f "$project_config" ]]; then
        local model=""
        case "$role" in
            primary)  model=$(jq -r '.extracted.llm.primary_model // empty' "$project_config" 2>/dev/null) ;;
            fast)     model=$(jq -r '.extracted.llm.fast_model // empty' "$project_config" 2>/dev/null) ;;
            gardener) model=$(jq -r '.extracted.gardener.model // empty' "$project_config" 2>/dev/null) ;;
        esac

        # Handle "infer" - auto-select fastest available
        if [[ "$model" == "infer" ]]; then
            model=$(atomic_infer_best_model "$role")
        fi

        [[ -n "$model" && "$model" != "null" ]] && echo "$model" && return
    fi

    # Fall back to defaults
    jq -r ".defaults.${role} // \"haiku\"" "$discovered_file" 2>/dev/null || echo "haiku"
}

# Auto-select best model for a role based on available models
atomic_infer_best_model() {
    local role="$1"
    local discovered_file="$ATOMIC_STATE_DIR/discovered-models.json"

    case "$role" in
        gardener|fast)
            # Prefer fast/cheap: haiku > phi3 > mistral > llama3.1:8b
            for candidate in haiku phi3:medium mistral:7b llama3.1:8b; do
                if atomic_model_available "$candidate"; then
                    echo "$candidate"
                    return
                fi
            done
            echo "haiku"  # Default fallback
            ;;
        primary)
            # Prefer capable: sonnet > llama3.1:70b > mixtral > llama3.1:8b
            for candidate in sonnet llama3.1:70b mixtral:8x7b llama3.1:8b; do
                if atomic_model_available "$candidate"; then
                    echo "$candidate"
                    return
                fi
            done
            echo "sonnet"
            ;;
    esac
}

# Check if a model is available
atomic_model_available() {
    local model="$1"
    local discovered_file="$ATOMIC_STATE_DIR/discovered-models.json"

    case "$model" in
        opus|sonnet|haiku)
            # Claude models assumed available if ANTHROPIC_API_KEY is set
            [[ -n "${ANTHROPIC_API_KEY:-}" ]] && return 0
            ;;
        *)
            # Check Ollama models
            [[ -f "$discovered_file" ]] && \
                jq -e ".models.ollama[\"$model\"]" "$discovered_file" &>/dev/null && return 0
            ;;
    esac
    return 1
}

# Get gardener configuration
# Usage: threshold=$(atomic_gardener_config "threshold_percent")
atomic_gardener_config() {
    local key="$1"
    local project_config="$ATOMIC_OUTPUT_DIR/${CURRENT_PHASE:-0-setup}/project-config.json"

    local defaults=(
        ["threshold_percent"]=70
        ["preserve_recent_exchanges"]=4
        ["preserve_opening"]=true
    )

    if [[ -f "$project_config" ]]; then
        local value=$(jq -r ".extracted.gardener.${key} // empty" "$project_config" 2>/dev/null)
        [[ -n "$value" && "$value" != "null" ]] && echo "$value" && return
    fi

    # Return default
    case "$key" in
        threshold_percent) echo "70" ;;
        preserve_recent_exchanges) echo "4" ;;
        preserve_opening) echo "true" ;;
        fallback_chain) echo '["haiku", "mistral:7b", "phi3:medium", "llama3.1:8b"]' ;;
        *) echo "" ;;
    esac
}

# Estimate token count (rough: 1 token ≈ 4 chars for English)
atomic_estimate_tokens() {
    local text="$1"
    local char_count=${#text}
    echo $((char_count / 4))
}

# Check token budget for a task before execution
# Usage: atomic_check_token_budget "$context_content" "Task Name"
# Returns: 0 if OK, 1 if over budget (with warning)
atomic_check_token_budget() {
    local content="$1"
    local task_name="${2:-Current task}"
    local model="${3:-$(atomic_get_model primary)}"
    local reserve_pct="${4:-30}"  # Reserve 30% for output by default

    local token_limit=$(atomic_model_token_limit "$model")
    local estimated_tokens=$(atomic_estimate_tokens "$content")
    local usable_budget=$((token_limit * (100 - reserve_pct) / 100))
    local usage_pct=$((estimated_tokens * 100 / usable_budget))

    # Log token budget status
    if [[ $estimated_tokens -gt $usable_budget ]]; then
        atomic_warn "Token budget EXCEEDED for $task_name"
        echo "  Context: ~$estimated_tokens tokens (budget: $usable_budget for $model)" >&2
        echo "  Action: Context will be auto-gardened before invocation" >&2
        return 1
    elif [[ $usage_pct -ge 80 ]]; then
        atomic_substep "Token budget HIGH for $task_name: ${usage_pct}% of $usable_budget tokens"
    elif [[ $usage_pct -ge 50 ]]; then
        atomic_substep "Token budget OK for $task_name: ${usage_pct}% of $usable_budget tokens"
    fi

    return 0
}

# Get token budget summary for display
# Usage: summary=$(atomic_token_budget_summary "$file1" "$file2" ...)
atomic_token_budget_summary() {
    local total_tokens=0
    local file_summaries=()

    for file in "$@"; do
        if [[ -f "$file" ]]; then
            local content=$(cat "$file")
            local tokens=$(atomic_estimate_tokens "$content")
            total_tokens=$((total_tokens + tokens))
            file_summaries+=("$(basename "$file"): ~$tokens tokens")
        fi
    done

    local model=$(atomic_get_model primary)
    local limit=$(atomic_model_token_limit "$model")
    local usage_pct=$((total_tokens * 100 / limit))

    echo "Token Budget Summary (model: $model, limit: $limit)"
    echo "═════════════════════════════════════════"
    for summary in "${file_summaries[@]}"; do
        echo "  $summary"
    done
    echo "─────────────────────────────────────────"
    echo "  TOTAL: ~$total_tokens tokens (${usage_pct}% of limit)"
}

# ============================================================================
# JSON SCHEMA VALIDATION
# ============================================================================

# Validate JSON structure against expected schema
# Usage: atomic_json_validate "$json_file" "required_fields" "optional_types"
# Example: atomic_json_validate "$file" "status,findings" "findings:array,status:string"
# Returns: 0 if valid, 1 if invalid (with error message on stderr)
atomic_json_validate() {
    local json_file="$1"
    local required_fields="${2:-}"
    local field_types="${3:-}"
    local schema_name="${4:-JSON output}"

    # Check file exists and is readable
    if [[ ! -f "$json_file" ]]; then
        echo "VALIDATION ERROR: $schema_name - File not found: $json_file" >&2
        return 1
    fi

    # Check syntax first
    if ! jq -e . "$json_file" &>/dev/null; then
        echo "VALIDATION ERROR: $schema_name - Invalid JSON syntax" >&2
        # Try to extract JSON from markdown if present
        if grep -q '```json' "$json_file"; then
            local extracted=$(sed -n '/```json/,/```/p' "$json_file" | sed '1d;$d')
            if echo "$extracted" | jq -e . &>/dev/null; then
                # Fix the file by extracting the JSON
                echo "$extracted" > "$json_file"
                echo "VALIDATION WARNING: Extracted JSON from markdown wrapper" >&2
            else
                return 1
            fi
        else
            return 1
        fi
    fi

    local errors=()

    # Check required fields
    if [[ -n "$required_fields" ]]; then
        IFS=',' read -ra fields <<< "$required_fields"
        for field in "${fields[@]}"; do
            field=$(echo "$field" | xargs)  # Trim whitespace
            if ! jq -e ".$field" "$json_file" &>/dev/null; then
                errors+=("Missing required field: $field")
            fi
        done
    fi

    # Check field types
    if [[ -n "$field_types" ]]; then
        IFS=',' read -ra types <<< "$field_types"
        for type_spec in "${types[@]}"; do
            type_spec=$(echo "$type_spec" | xargs)
            local field_name="${type_spec%%:*}"
            local expected_type="${type_spec##*:}"

            # Only check if field exists
            if jq -e ".$field_name" "$json_file" &>/dev/null; then
                local actual_type=$(jq -r ".$field_name | type" "$json_file")
                if [[ "$actual_type" != "$expected_type" ]]; then
                    errors+=("Field '$field_name' should be $expected_type, got $actual_type")
                fi
            fi
        done
    fi

    # Report errors
    if [[ ${#errors[@]} -gt 0 ]]; then
        echo "VALIDATION ERROR: $schema_name - Structure validation failed:" >&2
        for err in "${errors[@]}"; do
            echo "  - $err" >&2
        done
        return 1
    fi

    return 0
}

# Validate and fix common LLM JSON output issues
# Usage: fixed_json=$(atomic_json_fix "$json_file")
atomic_json_fix() {
    local json_file="$1"
    local json_content

    if [[ ! -f "$json_file" ]]; then
        echo "{}"
        return 1
    fi

    json_content=$(cat "$json_file")

    # If already valid, return as-is
    if echo "$json_content" | jq -e . &>/dev/null; then
        echo "$json_content"
        return 0
    fi

    # Try to extract JSON from markdown code blocks
    if echo "$json_content" | grep -q '```'; then
        local extracted=$(echo "$json_content" | sed -n '/```json\|```JSON\|```/,/```/p' | sed '1d;$d')
        if echo "$extracted" | jq -e . &>/dev/null; then
            echo "$extracted"
            return 0
        fi
    fi

    # Try to find JSON object in the content
    local json_start=$(echo "$json_content" | grep -n '^{' | head -1 | cut -d: -f1)
    if [[ -n "$json_start" ]]; then
        local extracted=$(echo "$json_content" | tail -n +"$json_start")
        if echo "$extracted" | jq -e . &>/dev/null; then
            echo "$extracted"
            return 0
        fi
    fi

    # Could not fix, return original for error reporting
    echo "$json_content"
    return 1
}

# ============================================================================
# CONTEXT HANDOFF VERIFICATION
# ============================================================================

# Verify that required context from previous phases exists
# Usage: atomic_verify_context_handoff "$phase_num" "artifact1,artifact2"
# Returns: 0 if all present, 1 if missing (with warnings)
atomic_verify_context_handoff() {
    local current_phase="${1:-$CURRENT_PHASE}"
    local required_artifacts="${2:-}"  # Comma-separated list of artifact keys
    local strict="${3:-false}"  # If true, fail on missing artifacts

    local phase_num=${current_phase%%[-_]*}  # Extract number from "1-discovery"
    phase_num=${phase_num:-0}

    local artifacts_file="$ATOMIC_CONTEXT_DIR/artifacts.json"
    local decisions_file="$ATOMIC_CONTEXT_DIR/decisions.json"
    local missing=()
    local warnings=()

    echo ""
    echo "CONTEXT HANDOFF VERIFICATION (Phase $phase_num)"
    echo "═════════════════════════════════════════════════"

    # Check if context directory exists
    if [[ ! -d "$ATOMIC_CONTEXT_DIR" ]]; then
        echo "  WARNING: Context directory not found"
        warnings+=("Context directory missing")
    fi

    # Check artifacts file
    if [[ -f "$artifacts_file" ]]; then
        local artifact_count=$(jq '.artifacts | length' "$artifacts_file" 2>/dev/null || echo 0)
        echo "  Artifacts registered: $artifact_count"
    else
        echo "  WARNING: No artifacts file found"
        warnings+=("Artifacts file missing")
    fi

    # Check decisions file
    if [[ -f "$decisions_file" ]]; then
        local decision_count=$(jq 'length' "$decisions_file" 2>/dev/null || echo 0)
        echo "  Decisions recorded: $decision_count"
    else
        echo "  WARNING: No decisions file found"
        warnings+=("Decisions file missing")
    fi

    # Verify required artifacts if specified
    if [[ -n "$required_artifacts" && -f "$artifacts_file" ]]; then
        echo ""
        echo "  Required Artifacts:"
        IFS=',' read -ra artifacts <<< "$required_artifacts"
        for artifact in "${artifacts[@]}"; do
            artifact=$(echo "$artifact" | xargs)  # Trim whitespace
            local found=$(jq -r ".artifacts[] | select(.path | contains(\"$artifact\")) | .path" "$artifacts_file" 2>/dev/null | head -1)
            if [[ -n "$found" ]]; then
                echo "    ✓ $artifact: $found"
            else
                echo "    ✗ $artifact: NOT FOUND"
                missing+=("$artifact")
            fi
        done
    fi

    # Phase-specific checks
    echo ""
    echo "  Phase Continuity:"

    case "$phase_num" in
        1)
            # Phase 1 should have Phase 0 closeout
            local closeout="$ATOMIC_ROOT/.claude/closeout/phase-00-closeout.json"
            if [[ -f "$closeout" ]]; then
                echo "    ✓ Phase 0 closeout present"
            else
                echo "    ✗ Phase 0 closeout missing"
                warnings+=("Phase 0 closeout missing")
            fi
            ;;
        2)
            # Phase 2 should have dialogue.json from Phase 1
            local dialogue="$ATOMIC_OUTPUT_DIR/1-discovery/dialogue.json"
            [[ -f "$dialogue" ]] && echo "    ✓ Discovery dialogue present" || warnings+=("Discovery dialogue missing")

            local approach="$ATOMIC_OUTPUT_DIR/1-discovery/selected-approach.json"
            [[ -f "$approach" ]] && echo "    ✓ Selected approach present" || warnings+=("Selected approach missing")
            ;;
        3)
            # Phase 3 should have PRD
            local prd="$ATOMIC_ROOT/docs/prd/PRD.md"
            [[ -f "$prd" ]] && echo "    ✓ PRD document present" || missing+=("PRD document")
            ;;
        4|5|6)
            # Phases 4-6 should have tasks.json
            local tasks="$ATOMIC_ROOT/.taskmaster/tasks/tasks.json"
            [[ -f "$tasks" ]] && echo "    ✓ Tasks file present" || missing+=("Tasks file")
            ;;
    esac

    echo ""
    echo "─────────────────────────────────────────────────"

    # Summary
    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "  MISSING: ${missing[*]}"
        if [[ "$strict" == "true" ]]; then
            echo "  STATUS: FAIL (strict mode)"
            return 1
        else
            echo "  STATUS: WARN (continuing with gaps)"
        fi
    elif [[ ${#warnings[@]} -gt 0 ]]; then
        echo "  WARNINGS: ${warnings[*]}"
        echo "  STATUS: PASS (with warnings)"
    else
        echo "  STATUS: PASS"
    fi

    echo ""

    # Log verification to decisions
    atomic_context_decision "Context handoff verified for Phase $phase_num: ${#missing[@]} missing, ${#warnings[@]} warnings" "handoff_verification"

    return 0
}

# Quick check for essential handoff (used by entry validation tasks)
# Usage: atomic_handoff_ready || return 1
atomic_handoff_ready() {
    local phase="${1:-$CURRENT_PHASE}"

    # Check context directory
    [[ -d "$ATOMIC_CONTEXT_DIR" ]] || return 1

    # Check summary exists
    [[ -f "$ATOMIC_CONTEXT_DIR/summary.md" ]] || return 1

    return 0
}

# ============================================================================
# DIFF TRACKING FOR ITERATIVE OUTPUTS
# ============================================================================

# Save baseline version before iteration
# Usage: atomic_diff_baseline "$file" "iteration_name"
atomic_diff_baseline() {
    local file="$1"
    local iteration_name="${2:-baseline}"
    local diff_dir="${ATOMIC_STATE_DIR:-$ATOMIC_ROOT/.claude}/diffs"

    mkdir -p "$diff_dir"

    if [[ ! -f "$file" ]]; then
        echo "DIFF: No file to baseline: $file" >&2
        return 1
    fi

    local filename=$(basename "$file")
    local baseline_file="$diff_dir/${filename}.${iteration_name}.baseline"

    cp "$file" "$baseline_file"
    echo "DIFF: Baseline saved: $baseline_file"

    # Return baseline path for later comparison
    echo "$baseline_file"
}

# Generate diff between baseline and current version
# Usage: atomic_diff_generate "$baseline_file" "$current_file" "description"
atomic_diff_generate() {
    local baseline_file="$1"
    local current_file="$2"
    local description="${3:-Changes}"
    local diff_dir="${ATOMIC_STATE_DIR:-$ATOMIC_ROOT/.claude}/diffs"

    mkdir -p "$diff_dir"

    if [[ ! -f "$baseline_file" ]]; then
        echo "DIFF: Baseline not found: $baseline_file" >&2
        return 1
    fi

    if [[ ! -f "$current_file" ]]; then
        echo "DIFF: Current file not found: $current_file" >&2
        return 1
    fi

    local filename=$(basename "$current_file")
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local diff_file="$diff_dir/${filename}.${timestamp}.diff"
    local summary_file="$diff_dir/${filename}.${timestamp}.summary.json"

    # Generate unified diff
    diff -u "$baseline_file" "$current_file" > "$diff_file" 2>/dev/null || true

    # Calculate diff statistics
    local lines_added=$(grep -c '^+[^+]' "$diff_file" 2>/dev/null || echo 0)
    local lines_removed=$(grep -c '^-[^-]' "$diff_file" 2>/dev/null || echo 0)
    local lines_changed=$((lines_added + lines_removed))

    # Generate summary JSON
    jq -n \
        --arg desc "$description" \
        --arg baseline "$baseline_file" \
        --arg current "$current_file" \
        --arg diff "$diff_file" \
        --argjson added "$lines_added" \
        --argjson removed "$lines_removed" \
        --argjson changed "$lines_changed" \
        '{
            "description": $desc,
            "timestamp": (now | todate),
            "baseline": $baseline,
            "current": $current,
            "diff_file": $diff,
            "statistics": {
                "lines_added": $added,
                "lines_removed": $removed,
                "total_changed": $changed
            }
        }' > "$summary_file"

    # Display summary
    echo ""
    echo "DIFF SUMMARY: $description"
    echo "─────────────────────────────────────────"
    echo "  Lines added:   +$lines_added"
    echo "  Lines removed: -$lines_removed"
    echo "  Total changed: $lines_changed"
    echo "  Diff saved:    $diff_file"
    echo ""

    # Register as artifact
    atomic_context_artifact "diff_${filename}_${timestamp}" "$diff_file" "Diff: $description"

    echo "$diff_file"
}

# Track iterative refinement (combines baseline + diff in one call)
# Usage: atomic_diff_track "$file" "before_refinement" "after_refinement"
atomic_diff_track() {
    local file="$1"
    local before_label="${2:-before}"
    local after_label="${3:-after}"

    local baseline=$(atomic_diff_baseline "$file" "$before_label")

    # Return baseline for later use
    # Caller should update the file, then call atomic_diff_generate
    echo "$baseline"
}

# ============================================================================
# CONTEXT HELPERS (Truncation, Windowing, Validation, Adjudication)
# ============================================================================

# Truncate file content with notice
# Usage: content=$(atomic_context_truncate "$file" 500)
atomic_context_truncate() {
    local file="$1"
    local max_lines="${2:-500}"

    if [[ ! -f "$file" ]]; then
        echo "(file not found: $file)"
        return 1
    fi

    local total_lines=$(wc -l < "$file")
    if [[ $total_lines -le $max_lines ]]; then
        cat "$file"
    else
        head -"$max_lines" "$file"
        echo ""
        echo "[TRUNCATED: Showing $max_lines of $total_lines lines]"
    fi
}

# Smart summarize file content using LLM
# Usage: content=$(atomic_context_summarize "$file" "corpus analysis" 150)
# This replaces blind truncation with intelligent summarization
atomic_context_summarize() {
    local file="$1"
    local context_desc="${2:-document}"
    local target_lines="${3:-200}"
    local cache_dir="${ATOMIC_STATE_DIR:-$ATOMIC_ROOT/.claude}/summary-cache"

    if [[ ! -f "$file" ]]; then
        echo "(file not found: $file)"
        return 1
    fi

    local total_lines=$(wc -l < "$file")
    local filename=$(basename "$file")

    # If content is small enough, return as-is
    if [[ $total_lines -le $((target_lines + 50)) ]]; then
        cat "$file"
        return 0
    fi

    mkdir -p "$cache_dir"

    # Generate cache key based on file content hash and target lines
    local file_hash=$(md5sum "$file" 2>/dev/null | cut -d' ' -f1 || shasum "$file" | cut -d' ' -f1)
    local cache_key="${filename}-${file_hash:0:12}-${target_lines}"
    local cache_file="$cache_dir/$cache_key.summary"

    # Check cache first
    if [[ -f "$cache_file" ]]; then
        cat "$cache_file"
        return 0
    fi

    # Determine file type and extraction strategy
    local file_type="text"
    local key_sections=""

    case "$filename" in
        *.json)
            file_type="json"
            # For JSON, extract top-level structure
            key_sections=$(jq -r 'keys | "Top-level keys: " + (. | join(", "))' "$file" 2>/dev/null || echo "")
            ;;
        *.md)
            file_type="markdown"
            # For markdown, extract headers
            key_sections=$(grep -E '^#{1,3} ' "$file" 2>/dev/null | head -20 | sed 's/^/  /' || echo "")
            ;;
        *dialogue*.json|*conversation*.json)
            file_type="dialogue"
            # For dialogues, extract first and last exchanges
            key_sections=$(jq -r '
                if .conversation then
                    "Exchanges: \(.conversation | length)\n" +
                    "Opening: \(.conversation[0].content[:200] // "N/A")...\n" +
                    "Recent: \(.conversation[-1].content[:200] // "N/A")..."
                else
                    "Structure: \(keys | join(", "))"
                end
            ' "$file" 2>/dev/null || echo "")
            ;;
    esac

    # Build summarization prompt
    local prompt_file=$(atomic_mktemp)
    local summary_output=$(atomic_mktemp)

    cat > "$prompt_file" << SUMMARY_PROMPT
# Task: Summarize $context_desc

You are a context-preservation assistant. Summarize this content for an LLM that will use it in a later task. Your goal is to preserve ALL important information while reducing size.

## Original Content ($total_lines lines, type: $file_type)

$(head -$((target_lines * 2)) "$file")

$(if [[ $total_lines -gt $((target_lines * 2)) ]]; then
    echo "... [${total_lines} total lines - content continues] ..."
    echo ""
    echo "## Final Section"
    tail -50 "$file"
fi)

## Key Structural Elements
$key_sections

## Summarization Requirements

1. **Preserve Critical Information**
   - Names, IDs, versions, paths
   - Decisions and their rationale
   - Key findings and conclusions
   - Technical specifications

2. **Condense Repetitive Content**
   - Merge similar items into counts ("12 similar tasks...")
   - Summarize patterns instead of listing all instances

3. **Maintain Context Chain**
   - Include enough for the next task to understand provenance
   - Reference source file: $filename

4. **Target Size**: Approximately $target_lines lines

## Output Format

Return ONLY the summarized content, optimized for downstream LLM consumption.
Start directly with the summary - no preamble.
SUMMARY_PROMPT

    # Use haiku for speed (summarization doesn't need opus)
    if atomic_invoke "$prompt_file" "$summary_output" "Summarizing $context_desc" --model=haiku 2>/dev/null; then
        if [[ -s "$summary_output" ]]; then
            # Add provenance header and cache
            {
                echo "[SUMMARY of $filename ($total_lines lines -> ~$target_lines lines)]"
                echo ""
                cat "$summary_output"
                echo ""
                echo "[End summary - original: $file]"
            } | tee "$cache_file"
            rm -f "$prompt_file" "$summary_output"
            return 0
        fi
    fi

    # Fallback to smart truncation with structural preservation
    rm -f "$prompt_file" "$summary_output"

    echo "[CONDENSED: $filename ($total_lines lines)]"
    echo ""

    if [[ "$file_type" == "json" ]]; then
        echo "## Structure"
        echo "$key_sections"
        echo ""
        echo "## Content Preview"
        head -$((target_lines - 20)) "$file"
    elif [[ "$file_type" == "markdown" ]]; then
        echo "## Headers"
        echo "$key_sections"
        echo ""
        echo "## Content"
        head -$((target_lines - 30)) "$file"
    else
        head -$target_lines "$file"
    fi

    echo ""
    echo "[CONDENSED: Showing ~$target_lines of $total_lines lines with structure]"
}

# Sliding window for JSON conversation arrays
# Usage: windowed_json=$(atomic_context_window "$dialogue_json" 12)
atomic_context_window() {
    local json="$1"
    local window_size="${2:-12}"
    local preserve_opening="${3:-true}"

    if [[ "$preserve_opening" == "true" ]]; then
        echo "$json" | jq --argjson win "$window_size" '
            .conversation as $conv |
            if ($conv | length) <= ($win + 2) then
                .
            else
                .conversation = ($conv[:2] +
                    [{"role": "system", "content": "[...earlier exchanges omitted...]"}] +
                    $conv[-$win:])
            end
        '
    else
        echo "$json" | jq --argjson win "$window_size" '
            .conversation = .conversation[-$win:]
        '
    fi
}

# Auto-garden dialogue JSON when approaching token threshold
# Usage: gardened_json=$(atomic_context_autogarden "$dialogue_json" 8000)
# This automatically manages dialogue size, applying summarization when needed
atomic_context_autogarden() {
    local dialogue_json="$1"
    local max_tokens="${2:-8000}"  # Target token budget for dialogue
    local preserve_opening="${3:-true}"

    # Check if this looks like valid JSON with exchanges
    if ! echo "$dialogue_json" | jq -e '.exchanges or .conversation' &>/dev/null; then
        echo "$dialogue_json"
        return 0
    fi

    # Determine key name (exchanges vs conversation)
    local key_name="exchanges"
    if echo "$dialogue_json" | jq -e '.conversation' &>/dev/null; then
        key_name="conversation"
    fi

    # Count exchanges and estimate tokens
    local exchange_count=$(echo "$dialogue_json" | jq ".$key_name | length")
    local char_count=$(echo "$dialogue_json" | jq -r ".$key_name | tostring | length")
    local estimated_tokens=$((char_count / 4))

    # If under budget, return as-is
    if [[ $estimated_tokens -le $max_tokens ]]; then
        echo "$dialogue_json"
        return 0
    fi

    # Calculate target window size (aim for 70% of budget to leave room)
    local target_chars=$((max_tokens * 4 * 70 / 100))
    local avg_chars_per_exchange=$((char_count / exchange_count))
    local target_window=$((target_chars / avg_chars_per_exchange))

    # Ensure minimum window of 6
    [[ $target_window -lt 6 ]] && target_window=6

    # Apply windowing with smart summarization of omitted content
    if [[ "$preserve_opening" == "true" && $exchange_count -gt $((target_window + 4)) ]]; then
        local omitted_start=2
        local omitted_end=$((exchange_count - target_window))
        local omitted_count=$((omitted_end - omitted_start))

        # Create a summary of omitted exchanges
        local omitted_summary
        local jq_filter=".${key_name}[${omitted_start}:${omitted_end}] | group_by(.agent // .role) | map(\"  \" + (.[0].agent // .[0].role) + \": \" + (. | length | tostring) + \" messages\") | join(\"\n\")"
        omitted_summary=$(echo "$dialogue_json" | jq -r "$jq_filter")

        # Build gardened dialogue
        echo "$dialogue_json" | jq --argjson win "$target_window" --arg omitted "[$omitted_count exchanges omitted]
Speakers in omitted section:
$omitted_summary" --arg key "$key_name" '
            .[$key] as $conv |
            .[$key] = ($conv[:2] +
                [{"role": "system", "agent": "context-manager", "content": $omitted, "gardened": true}] +
                $conv[-$win:]) |
            .gardening = {
                "original_exchanges": ($conv | length),
                "retained_exchanges": ($win + 2),
                "omitted_exchanges": (($conv | length) - $win - 2),
                "estimated_tokens_saved": (((($conv | length) - $win - 2) * 4 * 200) / 4)
            }
        '
    else
        # Simple windowing without opening preservation
        echo "$dialogue_json" | jq --argjson win "$target_window" --arg key "$key_name" '
            .[$key] = .[$key][-$win:] |
            .gardening = {
                "original_exchanges": (.[$key] | length),
                "retained_exchanges": $win,
                "type": "tail_only"
            }
        '
    fi
}

# Validate required context variables are set
# Usage: atomic_context_validate "corpus_content" "approach_context" || return 1
atomic_context_validate() {
    local missing=()

    for var in "$@"; do
        if [[ -z "${!var:-}" ]]; then
            missing+=("$var")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        atomic_warn "Missing required context: ${missing[*]}"
        return 1
    fi
    return 0
}

# Context adjudication with model-aware thresholds and fallback chain
# Usage: adjudicated_json=$(atomic_context_adjudicate "$dialogue_json" "Opening Dialogue" "$primary_model")
atomic_context_adjudicate() {
    local dialogue_json="$1"
    local conversation_name="${2:-Conversation}"
    local primary_model="${3:-$(atomic_get_model primary)}"
    local output_dir="${ATOMIC_CONTEXT_DIR:-$ATOMIC_STATE_DIR}"
    local output_file="$output_dir/adjudication-$(date +%s).json"

    mkdir -p "$output_dir"

    # Get configuration
    local threshold_pct=$(atomic_gardener_config "threshold_percent")
    local preserve_recent=$(atomic_gardener_config "preserve_recent_exchanges")
    local preserve_opening=$(atomic_gardener_config "preserve_opening")
    local fallback_chain=$(atomic_gardener_config "fallback_chain")

    # Calculate threshold based on primary model
    local token_limit=$(atomic_model_token_limit "$primary_model")
    local threshold=$((token_limit * threshold_pct / 100))

    # Estimate current conversation size
    local conversation_text=$(echo "$dialogue_json" | jq -r '.conversation | map(.content) | join(" ")' 2>/dev/null)
    local estimated_tokens=$(atomic_estimate_tokens "$conversation_text")

    if [[ $estimated_tokens -lt $threshold ]]; then
        # Under threshold, no adjudication needed
        echo "$dialogue_json"
        return 0
    fi

    atomic_substep "Context threshold exceeded (~$estimated_tokens of $threshold tokens for $primary_model)"

    # STAGE 1: Try simple auto-gardening first (no LLM call)
    local gardened_json=$(atomic_context_autogarden "$dialogue_json" $threshold)
    local gardened_text=$(echo "$gardened_json" | jq -r '(.conversation // .exchanges) | map(.content // .message) | join(" ")' 2>/dev/null)
    local gardened_tokens=$(atomic_estimate_tokens "$gardened_text")

    if [[ $gardened_tokens -lt $threshold ]]; then
        atomic_substep "Auto-gardening reduced context to ~$gardened_tokens tokens"
        echo "$gardened_json"
        return 0
    fi

    # STAGE 2: Auto-gardening wasn't enough, invoke full LLM adjudication
    atomic_substep "Auto-gardening insufficient (~$gardened_tokens tokens), invoking LLM context gardener..."

    # Build adjudication prompt
    local full_conversation=$(echo "$dialogue_json" | jq -r '.conversation | map("\(.role): \(.content)") | join("\n\n")' 2>/dev/null)

    local prompt=$(cat << ADJUDICATE_PROMPT
# Task: Adjudicate Conversation Context

You are a context gardener. This conversation has exceeded its token budget and needs intelligent compression.

## Conversation: $conversation_name

$full_conversation

## Your Task

Produce a compressed context summary that preserves:
1. Key decisions made
2. Critical context future responses depend on
3. Open threads still being discussed
4. Constraints that were established

Output ONLY valid JSON:
{
    "level_set": "2-4 sentences starting with 'Here is where we left off:' capturing current state",
    "decisions_made": ["Concrete decisions or agreements reached"],
    "open_threads": ["Topics still under discussion"],
    "constraints_captured": {
        "technical": "Tech constraints mentioned or null",
        "timeline": "Timeline constraints or null",
        "other": "Other constraints or null"
    },
    "key_context": "Critical context that must not be lost"
}
ADJUDICATE_PROMPT
)

    # Try gardener model with fallback chain
    local gardener_model=$(atomic_get_model gardener)
    local models_to_try=("$gardener_model")

    # Add fallback chain
    while IFS= read -r fallback; do
        [[ -n "$fallback" && "$fallback" != "$gardener_model" ]] && models_to_try+=("$fallback")
    done < <(echo "$fallback_chain" | jq -r '.[]' 2>/dev/null)

    local success=false
    for model in "${models_to_try[@]}"; do
        atomic_substep "Trying gardener model: $model"

        if atomic_invoke "$prompt" "$output_file" "Adjudicate context" --model="$model" --format=json 2>/dev/null; then
            if jq -e '.level_set' "$output_file" &>/dev/null; then
                success=true
                atomic_success "Adjudication complete with $model"
                break
            fi
        fi
        atomic_warn "Model $model failed, trying next..."
    done

    if [[ "$success" == true ]]; then
        # Merge adjudication into dialogue JSON
        local adjudication=$(cat "$output_file")

        # Build new conversation: opening (if preserved) + level-set + recent exchanges
        echo "$dialogue_json" | jq \
            --argjson adj "$adjudication" \
            --argjson recent "$preserve_recent" \
            --argjson keep_opening "$([[ "$preserve_opening" == "true" ]] && echo "true" || echo "false")" '
            .adjudication_history = ((.adjudication_history // []) + [$adj]) |
            .conversation = (
                (if $keep_opening then .conversation[:2] else [] end) +
                [{"role": "system", "content": ("CONTEXT SUMMARY: " + $adj.level_set + "\nDecisions: " + ($adj.decisions_made | join("; ")) + "\nOpen threads: " + ($adj.open_threads | join("; ")))}] +
                .conversation[-$recent:]
            )
        '
    else
        # All models failed, use simple window fallback
        atomic_warn "All gardener models failed, using simple window fallback"
        atomic_context_window "$dialogue_json" "$((preserve_recent * 2))" "$preserve_opening"
    fi
}

# ============================================================================
# INITIALIZATION
# ============================================================================

# Auto-initialize state on source
atomic_state_init
