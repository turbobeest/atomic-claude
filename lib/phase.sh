#!/bin/bash
#
# ATOMIC CLAUDE - Phase Management Library
# Provides phase lifecycle management for multi-step workflows
#
# Usage:
#   source lib/phase.sh
#   phase_start "00-setup" "Project Setup"
#   ... run tasks ...
#   phase_complete
#

set -euo pipefail

# Source core library
PHASE_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$PHASE_LIB_DIR/atomic.sh"

# ============================================================================
# PHASE STATE
# ============================================================================

CURRENT_PHASE=""
CURRENT_PHASE_NAME=""
PHASE_START_TIME=""
PHASE_TASKS_RUN=0

# ============================================================================
# PHASE LIFECYCLE
# ============================================================================

phase_start() {
    local phase_id="$1"
    local phase_name="$2"

    CURRENT_PHASE="$phase_id"
    CURRENT_PHASE_NAME="$phase_name"
    PHASE_START_TIME=$(date +%s)
    PHASE_TASKS_RUN=0

    # Update state
    atomic_state_set "current_phase" "\"$phase_id\""

    # Create phase output directory
    mkdir -p "$ATOMIC_OUTPUT_DIR/$phase_id"

    atomic_header "PHASE: $phase_name"
    atomic_substep "Phase ID: $phase_id"
    atomic_substep "Started: $(date)"
    echo ""
}

phase_task() {
    local task_id="$1"
    local task_name="$2"
    shift 2

    ((PHASE_TASKS_RUN++))

    echo ""
    echo -e "${BOLD}${CYAN}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓${NC}"
    echo -e "${BOLD}${CYAN}┃${NC} ${BOLD}TASK $PHASE_TASKS_RUN: $task_name${NC}"
    echo -e "${BOLD}${CYAN}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛${NC}"

    # Execute the task function/command passed
    if "$@"; then
        atomic_success "Task '$task_name' completed"
        return 0
    else
        atomic_error "Task '$task_name' failed"
        return 1
    fi
}

phase_checkpoint() {
    local checkpoint_name="$1"
    local checkpoint_data="$2"

    local checkpoint_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/checkpoints.json"

    # Initialize or append to checkpoints
    if [[ ! -f "$checkpoint_file" ]]; then
        echo '{"checkpoints":[]}' > "$checkpoint_file"
    fi

    local tmp_file=$(mktemp)
    jq ".checkpoints += [{\"name\": \"$checkpoint_name\", \"timestamp\": \"$(date -Iseconds)\", \"data\": $checkpoint_data}]" \
        "$checkpoint_file" > "$tmp_file" && mv "$tmp_file" "$checkpoint_file"

    atomic_info "Checkpoint saved: $checkpoint_name"
}

phase_verify() {
    local verification_script="$1"

    atomic_step "Phase Verification"

    if [[ -f "$verification_script" ]]; then
        if bash "$verification_script"; then
            atomic_success "Phase verification passed"
            return 0
        else
            atomic_error "Phase verification failed"
            return 1
        fi
    else
        atomic_warn "No verification script found, skipping"
        return 0
    fi
}

phase_complete() {
    local end_time=$(date +%s)
    local duration=$((end_time - PHASE_START_TIME))

    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  PHASE COMPLETE: $CURRENT_PHASE_NAME${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${DIM}  Phase ID:       $CURRENT_PHASE${NC}"
    echo -e "${DIM}  Tasks Run:      $PHASE_TASKS_RUN${NC}"
    echo -e "${DIM}  Duration:       ${duration}s${NC}"
    echo -e "${DIM}  Completed:      $(date)${NC}"
    echo ""

    # Generate closeout artifact
    local closeout_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/closeout.json"
    cat > "$closeout_file" << EOF
{
  "phase_id": "$CURRENT_PHASE",
  "phase_name": "$CURRENT_PHASE_NAME",
  "tasks_run": $PHASE_TASKS_RUN,
  "duration_seconds": $duration,
  "started_at": "$(date -d "@$PHASE_START_TIME" -Iseconds)",
  "completed_at": "$(date -Iseconds)",
  "status": "complete"
}
EOF

    atomic_substep "Closeout saved: $closeout_file"

    # Clear state
    atomic_state_set "current_phase" "null"
    atomic_state_set "current_task" "null"
}

# ============================================================================
# PHASE WORKFLOW HELPERS
# ============================================================================

# Run a deterministic (non-LLM) task
phase_deterministic() {
    local task_name="$1"
    shift

    atomic_step "$task_name"

    if "$@"; then
        atomic_success "$task_name"
        return 0
    else
        atomic_error "$task_name failed"
        return 1
    fi
}

# Run an LLM task with bounded prompt
phase_llm_task() {
    local task_name="$1"
    local prompt_file="$2"
    local output_file="$3"
    shift 3

    # Default output to phase output directory
    if [[ "$output_file" != /* ]]; then
        output_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/$output_file"
    fi

    atomic_invoke "$prompt_file" "$output_file" "$task_name" "$@"
}

# Require human approval before continuing
phase_human_gate() {
    local gate_message="$1"

    echo ""
    echo -e "${MAGENTA}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║${NC} ${BOLD}🛑 HUMAN APPROVAL REQUIRED${NC}                                ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}╠═══════════════════════════════════════════════════════════╣${NC}"
    echo -e "${MAGENTA}║${NC} $gate_message"
    echo -e "${MAGENTA}║${NC}"
    echo -e "${MAGENTA}║${NC} Phase: $CURRENT_PHASE_NAME"
    echo -e "${MAGENTA}║${NC} Tasks completed so far: $PHASE_TASKS_RUN"
    echo -e "${MAGENTA}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    read -p "Type 'approve' to continue, anything else to abort: " response

    if [[ "$response" == "approve" ]]; then
        atomic_success "Human gate approved"
        phase_checkpoint "human_gate" "{\"approved\": true, \"message\": \"$gate_message\"}"
        return 0
    else
        atomic_error "Human gate declined"
        phase_checkpoint "human_gate" "{\"approved\": false, \"message\": \"$gate_message\"}"
        return 1
    fi
}

# Display a summary and wait for user to review
phase_review() {
    local review_file="$1"
    local review_name="${2:-Review}"

    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}📋 $review_name${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if [[ -f "$review_file" ]]; then
        cat "$review_file"
    else
        echo "(Review content not found: $review_file)"
    fi

    echo ""
    read -p "Press Enter to continue..." _
}
