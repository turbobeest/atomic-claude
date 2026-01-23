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
source "$PHASE_LIB_DIR/task-state.sh"

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

    # Initialize context management for this phase
    atomic_context_init "$phase_id"

    # Initialize task state tracking
    task_state_init "$phase_id"

    # Get phase number from id (e.g., "0-setup" -> "0")
    local phase_num="${phase_id%%-*}"

    # Display header with project name
    local header
    header=$(atomic_phase_header "$phase_num" "$phase_name")
    atomic_header "$header"
    atomic_substep "Phase ID: $phase_id"
    atomic_substep "Started: $(date)"

    # Show resume status if applicable
    local last_task
    last_task=$(task_state_get_last_complete)
    if [[ -n "$last_task" ]]; then
        atomic_substep "Last completed: Task $last_task"
    fi
    echo ""
}

phase_task() {
    local task_id="$1"
    local task_name="$2"
    shift 2

    PHASE_TASKS_RUN=$((PHASE_TASKS_RUN + 1))

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
    local project_name
    project_name=$(atomic_get_project_name)

    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  PHASE COMPLETE: $CURRENT_PHASE_NAME [$project_name]${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${DIM}  Project:        $project_name${NC}"
    echo -e "${DIM}  Phase ID:       $CURRENT_PHASE${NC}"
    echo -e "${DIM}  Tasks Run:      $PHASE_TASKS_RUN${NC}"
    echo -e "${DIM}  Duration:       ${duration}s${NC}"
    echo -e "${DIM}  Completed:      $(date)${NC}"
    echo ""

    # Generate closeout artifact
    local closeout_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/closeout.json"
    local git_tag
    git_tag=$(atomic_git_tag "$CURRENT_PHASE")

    cat > "$closeout_file" << EOF
{
  "project_name": "$project_name",
  "phase_id": "$CURRENT_PHASE",
  "phase_name": "$CURRENT_PHASE_NAME",
  "tasks_run": $PHASE_TASKS_RUN,
  "duration_seconds": $duration,
  "started_at": "$(date -d "@$PHASE_START_TIME" -Iseconds)",
  "completed_at": "$(date -Iseconds)",
  "status": "complete",
  "git_tag": "$git_tag"
}
EOF

    atomic_substep "Closeout saved: $closeout_file"
    atomic_substep "Git tag available: $git_tag"

    # Refresh context summary before closing out
    atomic_context_refresh

    # Record phase completion as artifact
    atomic_context_artifact "$closeout_file" "Phase $CURRENT_PHASE closeout" "closeout"

    # Mark phase complete in task state
    task_state_phase_complete

    # Clear state
    atomic_state_set "current_phase" "null"
    atomic_state_set "current_task" "null"
}

# ============================================================================
# PHASE WORKFLOW HELPERS
# ============================================================================

# Exit codes for task navigation
TASK_CONTINUE=0
TASK_REDO=1
TASK_BACK=100
TASK_QUIT=101

# Interactive task wrapper - allows redo, go back, quit, jump
# Usage: phase_task_interactive <task_id> <task_name> <task_function>
#   task_id: 3-digit ID like 001, 002, 101, 102 (first digit = phase)
# Returns: 0=continue, 100=go back, 101=quit
#
# Task State Integration:
#   - Checks if task should be skipped (already complete)
#   - Marks task in_progress when starting
#   - Marks task complete when done
#   - Supports --resume-at, --redo, --reset-from flags
#
phase_task_interactive() {
    local task_id="$1"
    local task_name="$2"
    local task_func="$3"

    # Check if task should be skipped
    if task_state_should_skip "$task_id"; then
        echo ""
        echo -e "${DIM}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓${NC}"
        echo -e "${DIM}┃${NC} ${DIM}TASK $task_id: $task_name ${GREEN}[COMPLETE - SKIPPED]${NC}"
        echo -e "${DIM}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛${NC}"
        return $TASK_CONTINUE
    fi

    while true; do
        echo ""
        echo -e "${BOLD}${CYAN}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓${NC}"
        echo -e "${BOLD}${CYAN}┃${NC} ${BOLD}TASK $task_id: $task_name${NC}"
        echo -e "${BOLD}${CYAN}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛${NC}"

        # Mark task as started
        task_state_start "$task_id" "$task_name"

        # Run the task
        local task_result=0
        if $task_func; then
            # Mark task complete in persistent state
            task_state_complete "$task_id" "$task_name"
            atomic_success "Task completed"

            # Post-task navigation
            echo ""
            echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "  ${GREEN}[c]${NC} Continue    ${YELLOW}[r]${NC} Redo    ${BLUE}[b]${NC} Go back    ${MAGENTA}[j]${NC} Jump to    ${RED}[q]${NC} Quit"
            echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            read -p "  Choice [c]: " choice
            choice=${choice:-c}

            case "$choice" in
                c|C|"")
                    return $TASK_CONTINUE
                    ;;
                r|R)
                    atomic_info "Redoing task..."
                    task_state_reset_from "$task_id"
                    continue
                    ;;
                b|B)
                    atomic_info "Going back to previous task..."
                    return $TASK_BACK
                    ;;
                j|J)
                    echo ""
                    echo -e "  ${DIM}Enter task ID to jump to (e.g., 101, 105):${NC}"
                    read -p "  Jump to: " jump_target
                    if [[ "$jump_target" =~ ^[0-9]+$ ]]; then
                        task_state_reset_from "$jump_target"
                        TASK_RESUME_AT="$jump_target"
                        atomic_info "Jumping to task $jump_target..."
                        return $TASK_CONTINUE
                    else
                        atomic_error "Invalid task ID"
                    fi
                    ;;
                q|Q)
                    atomic_warn "Quitting phase..."
                    return $TASK_QUIT
                    ;;
                *)
                    atomic_info "Continuing..."
                    return $TASK_CONTINUE
                    ;;
            esac
        else
            # Mark task failed in persistent state
            task_state_fail "$task_id" "Task execution failed"
            atomic_error "Task failed"

            # Failure navigation
            echo ""
            echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "  ${YELLOW}[r]${NC} Retry    ${BLUE}[b]${NC} Go back    ${MAGENTA}[j]${NC} Jump to    ${DIM}[s]${NC} Skip    ${RED}[q]${NC} Quit"
            echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            read -p "  Choice [r]: " choice
            choice=${choice:-r}

            case "$choice" in
                r|R|"")
                    atomic_info "Retrying task..."
                    continue
                    ;;
                b|B)
                    atomic_info "Going back to previous task..."
                    return $TASK_BACK
                    ;;
                j|J)
                    echo ""
                    echo -e "  ${DIM}Enter task ID to jump to (e.g., 101, 105):${NC}"
                    read -p "  Jump to: " jump_target
                    if [[ "$jump_target" =~ ^[0-9]+$ ]]; then
                        task_state_reset_from "$jump_target"
                        TASK_RESUME_AT="$jump_target"
                        atomic_info "Jumping to task $jump_target..."
                        return $TASK_CONTINUE
                    else
                        atomic_error "Invalid task ID"
                    fi
                    ;;
                s|S)
                    atomic_warn "Skipping task..."
                    return $TASK_CONTINUE
                    ;;
                q|Q)
                    atomic_warn "Quitting phase..."
                    return $TASK_QUIT
                    ;;
                *)
                    atomic_info "Retrying..."
                    continue
                    ;;
            esac
        fi
    done
}

# Run a sequence of tasks with navigation support
# Usage: phase_run_tasks task_001_name task_002_name task_005_name ...
# Each task should be a function named: task_XXX_descriptive_name
#   where XXX is the 3-digit task ID (e.g., 001, 002, 101, 102)
phase_run_tasks() {
    local tasks=("$@")
    local task_ids=()
    local task_names=()
    local i=0
    local total=${#tasks[@]}

    # Extract task IDs and names from function names (task_001_foo_bar -> "001", "Foo Bar")
    for task in "${tasks[@]}"; do
        # Extract the 3-digit ID
        local id=$(echo "$task" | sed -n 's/task_\([0-9]\{3\}\)_.*/\1/p')
        if [[ -z "$id" ]]; then
            # Fallback: try 2-digit format and convert
            id=$(echo "$task" | sed -n 's/task_\([0-9]\{2\}\)_.*/\1/p')
            [[ -n "$id" ]] && id="0$id"
        fi
        [[ -z "$id" ]] && id="???"
        task_ids+=("$id")

        # Extract the name part after task_XXX_
        local name="${task#task_[0-9][0-9][0-9]_}"
        [[ "$name" == "$task" ]] && name="${task#task_[0-9][0-9]_}"  # Try 2-digit
        name="${name//_/ }"  # Replace underscores with spaces
        # Capitalize first letter of each word
        name=$(echo "$name" | sed 's/\b\(.\)/\u\1/g')
        task_names+=("$name")
    done

    while [[ $i -lt $total ]]; do
        phase_task_interactive "${task_ids[$i]}" "${task_names[$i]}" "${tasks[$i]}"
        local result=$?

        case $result in
            $TASK_CONTINUE)
                ((i++))
                ;;
            $TASK_BACK)
                if [[ $i -gt 0 ]]; then
                    ((i--))
                else
                    atomic_warn "Already at first task"
                fi
                ;;
            $TASK_QUIT)
                atomic_error "Phase aborted by user"
                return 1
                ;;
        esac
    done

    atomic_success "All tasks completed"
    return 0
}

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

# ============================================================================
# PHASE TRANSITIONS
# ============================================================================

# Transition banner between phases
phase_transition_banner() {
    local from_phase="$1"
    local to_phase="$2"
    local to_name="$3"

    echo ""
    echo ""
    echo -e "${MAGENTA}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║${NC}                                                           ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}║${NC}  ${BOLD}PHASE TRANSITION${NC}                                        ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}║${NC}                                                           ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}║${NC}  ${DIM}Completed:${NC} Phase $from_phase                                  ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}║${NC}  ${BOLD}Starting:${NC}  Phase $to_phase - $to_name                        ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}║${NC}                                                           ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Offer to continue to next phase
# Usage: phase_offer_continue <next_phase_id> <next_phase_name> <next_script_path>
# Returns: 0 if user wants to continue, 1 if not
phase_offer_continue() {
    local next_phase_id="$1"
    local next_phase_name="$2"
    local next_script="$3"

    echo ""
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${CYAN}Ready for Phase $next_phase_id: $next_phase_name${NC}"
    echo ""
    echo -e "  ${GREEN}[c]${NC} Continue to Phase $next_phase_id"
    echo -e "  ${YELLOW}[p]${NC} Pause here (resume later with: $next_script)"
    echo ""

    while true; do
        read -p "  Choice [c]: " choice
        choice=${choice:-c}
        case "$choice" in
            c|C|continue|Continue)
                return 0
                ;;
            p|P|pause|Pause|q|Q)
                echo ""
                atomic_info "Pausing pipeline."
                atomic_info "To resume: $next_script"
                echo ""
                return 1
                ;;
            *)
                atomic_error "Invalid choice. Enter 'c' to continue or 'p' to pause."
                ;;
        esac
    done
}

# Execute next phase script
# Usage: phase_chain <current_phase_num> <next_script_path> <next_phase_name>
phase_chain() {
    local current_phase="$1"
    local next_script="$2"
    local next_phase_name="$3"

    # Extract next phase number from script path (e.g., "1-discovery" -> "1")
    local next_phase_num=$(basename "$(dirname "$next_script")" | cut -d'-' -f1)

    if [[ ! -f "$next_script" ]]; then
        atomic_error "Next phase script not found: $next_script"
        atomic_info "Phase $next_phase_num may not be implemented yet."
        return 1
    fi

    if ! phase_offer_continue "$next_phase_num" "$next_phase_name" "$next_script"; then
        return 1
    fi

    phase_transition_banner "$current_phase" "$next_phase_num" "$next_phase_name"

    # Brief pause for user to see the transition
    sleep 1

    # Execute next phase (exec replaces current process)
    exec bash "$next_script" --skip-intro
}
