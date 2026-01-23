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

    # Log the invocation (project-prefixed log file)
    local log_file
    log_file=$(atomic_log_file)
    mkdir -p "$(dirname "$log_file")"
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

# Record a decision to the context
# Usage: atomic_context_decision "Selected guided setup mode" "user_choice"
atomic_context_decision() {
    local decision="$1"
    local category="${2:-general}"
    local decisions_file="$ATOMIC_CONTEXT_DIR/decisions.json"

    if [[ -f "$decisions_file" ]]; then
        local tmp=$(mktemp)
        jq ". + [{
            \"decision\": \"$decision\",
            \"category\": \"$category\",
            \"timestamp\": \"$(date -Iseconds)\",
            \"task\": \"$(atomic_state_get current_task)\"
        }]" "$decisions_file" > "$tmp" && mv "$tmp" "$decisions_file"
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
        local tmp=$(mktemp)
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
# INITIALIZATION
# ============================================================================

# Auto-initialize state on source
atomic_state_init
