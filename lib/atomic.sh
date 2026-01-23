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
            local tmp=$(mktemp)
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
    atomic_substep "Invoking context gardener..."

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
