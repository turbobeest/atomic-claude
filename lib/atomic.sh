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

# ============================================================================
# COLORS & OUTPUT
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# Output functions
atomic_header() {
    echo ""
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${BLUE}  $1${NC}"
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

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

atomic_output_box() {
    echo -e "${DIM}┌─────────────────────────────────────────────────────────────${NC}"
    echo "$1" | sed 's/^/  │ /'
    echo -e "${DIM}└─────────────────────────────────────────────────────────────${NC}"
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
    local tmp_file=$(mktemp)
    jq ".$key = $value" "$state_file" > "$tmp_file" && mv "$tmp_file" "$state_file"
}

atomic_state_increment() {
    local key="$1"
    local state_file="$ATOMIC_STATE_DIR/session.json"
    local tmp_file=$(mktemp)
    jq ".$key = (.$key + 1)" "$state_file" > "$tmp_file" && mv "$tmp_file" "$state_file"
}

# ============================================================================
# CORE: ATOMIC INVOKE
# ============================================================================

# atomic_invoke <prompt_file|prompt_string> <output_file> <description> [options]
# Options:
#   --model=<model>        Override default model (sonnet|opus|haiku)
#   --format=json          Expect JSON output, validate it
#   --format=markdown      Expect markdown output
#   --timeout=<seconds>    Override default timeout
#   --stdin                Read additional context from stdin to append to prompt
#
atomic_invoke() {
    local prompt_source="$1"
    local output_file="$2"
    local description="$3"
    shift 3

    # Parse options
    local model="$CLAUDE_MODEL"
    local format=""
    local timeout="$CLAUDE_TIMEOUT"
    local use_stdin=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --model=*) model="${1#*=}" ;;
            --format=*) format="${1#*=}" ;;
            --timeout=*) timeout="${1#*=}" ;;
            --stdin) use_stdin=true ;;
            *) atomic_warn "Unknown option: $1" ;;
        esac
        shift
    done

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

    # Update state
    atomic_state_set "current_task" "\"$description\""

    # Create output directory if needed
    mkdir -p "$(dirname "$output_file")"

    atomic_waiting "Invoking Claude..."
    echo ""

    # THE ATOMIC INVOCATION
    local start_time=$(date +%s)
    local exit_code=0

    if timeout "$timeout" claude -p "$prompt_content" --model "$model" --dangerously-skip-permissions > "$output_file" 2>&1; then
        exit_code=0
    else
        exit_code=$?
    fi

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Log the invocation
    local log_file="$ATOMIC_LOG_DIR/$(date +%Y%m%d).log"
    echo "[$(date -Iseconds)] task=\"$description\" model=$model duration=${duration}s exit=$exit_code output=$output_file" >> "$log_file"

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
        atomic_error "Claude task failed (exit code: $exit_code)"
        atomic_substep "Check output file for details: $output_file"
        atomic_state_increment "tasks_failed"
        return $exit_code
    fi
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
# INITIALIZATION
# ============================================================================

# Auto-initialize state on source
atomic_state_init
