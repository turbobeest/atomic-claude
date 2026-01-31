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
source "$PHASE_LIB_DIR/memory.sh"

# ============================================================================
# PHASE STATE
# ============================================================================

CURRENT_PHASE=""
CURRENT_PHASE_NAME=""
PHASE_START_TIME=""
PHASE_TASKS_RUN=0
PHASE_SNAPSHOT_DIR=""

# Track current in-progress task for signal cleanup
_PHASE_ACTIVE_TASK_ID=""
_PHASE_ACTIVE_TASK_NAME=""

# Signal handler: mark active task as failed on interruption
_phase_signal_cleanup() {
    local signal="${1:-UNKNOWN}"
    if [[ -n "$_PHASE_ACTIVE_TASK_ID" ]]; then
        echo "" >&2
        echo -e "  ${YELLOW}!${NC} Interrupted (${signal}) — marking task $_PHASE_ACTIVE_TASK_ID as failed" >&2
        task_state_fail "$_PHASE_ACTIVE_TASK_ID" "Interrupted by $signal" 2>/dev/null || true
        _PHASE_ACTIVE_TASK_ID=""
        _PHASE_ACTIVE_TASK_NAME=""
    fi
    # Re-raise signal for default handler
    trap - "$signal" 2>/dev/null || true
    kill -s "$signal" $$ 2>/dev/null || exit 1
}

# Register signal handlers (called once during phase_start)
_phase_register_traps() {
    trap '_phase_signal_cleanup INT' INT
    trap '_phase_signal_cleanup TERM' TERM
}

# ============================================================================
# CROSS-PLATFORM HELPERS
# ============================================================================

# Convert epoch timestamp to ISO 8601 format (cross-platform)
# Usage: _phase_epoch_to_iso 1706123456
_phase_epoch_to_iso() {
    local epoch="$1"
    if date -d "@$epoch" -Iseconds 2>/dev/null; then
        # GNU date
        return 0
    elif date -r "$epoch" -Iseconds 2>/dev/null; then
        # BSD/macOS date
        return 0
    elif date -r "$epoch" +%Y-%m-%dT%H:%M:%S%z 2>/dev/null; then
        # BSD/macOS date fallback format
        return 0
    else
        # Fallback: just return the epoch
        echo "$epoch"
    fi
}

# ============================================================================
# PHASE SNAPSHOTS & ROLLBACK
# ============================================================================

# Create a snapshot of phase state before execution
# Usage: phase_snapshot "0-setup"
phase_snapshot() {
    local phase_id="$1"
    PHASE_SNAPSHOT_DIR="$ATOMIC_STATE_DIR/snapshots/$phase_id-$(date +%Y%m%d-%H%M%S)"

    mkdir -p "$PHASE_SNAPSHOT_DIR"

    # Snapshot task state
    if [[ -f "$ATOMIC_ROOT/.claude/task-state.json" ]]; then
        cp "$ATOMIC_ROOT/.claude/task-state.json" "$PHASE_SNAPSHOT_DIR/task-state.json"
    fi

    # Snapshot session state
    if [[ -f "$ATOMIC_STATE_DIR/session.json" ]]; then
        cp "$ATOMIC_STATE_DIR/session.json" "$PHASE_SNAPSHOT_DIR/session.json"
    fi

    # Snapshot context
    if [[ -d "$ATOMIC_STATE_DIR/context" ]]; then
        cp -r "$ATOMIC_STATE_DIR/context" "$PHASE_SNAPSHOT_DIR/context"
    fi

    # Record snapshot metadata
    cat > "$PHASE_SNAPSHOT_DIR/metadata.json" << EOF
{
    "phase_id": "$phase_id",
    "timestamp": "$(date -Iseconds)",
    "snapshot_dir": "$PHASE_SNAPSHOT_DIR"
}
EOF

    echo "$PHASE_SNAPSHOT_DIR"
}

# Rollback to a previous snapshot
# Usage: phase_rollback "$snapshot_dir"
phase_rollback() {
    local snapshot_dir="$1"

    if [[ ! -d "$snapshot_dir" ]]; then
        echo "ERROR: Snapshot directory not found: $snapshot_dir" >&2
        return 1
    fi

    echo "Rolling back to snapshot: $snapshot_dir"

    # Restore task state
    if [[ -f "$snapshot_dir/task-state.json" ]]; then
        cp "$snapshot_dir/task-state.json" "$ATOMIC_ROOT/.claude/task-state.json"
        echo "  Restored: task-state.json"
    fi

    # Restore session state
    if [[ -f "$snapshot_dir/session.json" ]]; then
        cp "$snapshot_dir/session.json" "$ATOMIC_STATE_DIR/session.json"
        echo "  Restored: session.json"
    fi

    # Restore context
    if [[ -d "$snapshot_dir/context" ]]; then
        rm -rf "$ATOMIC_STATE_DIR/context"
        cp -r "$snapshot_dir/context" "$ATOMIC_STATE_DIR/context"
        echo "  Restored: context/"
    fi

    echo "Rollback complete"
    return 0
}

# List available snapshots
# Usage: phase_list_snapshots
phase_list_snapshots() {
    local snapshot_base="$ATOMIC_STATE_DIR/snapshots"

    if [[ ! -d "$snapshot_base" ]]; then
        echo "No snapshots found"
        return 0
    fi

    echo "Available snapshots:"
    for snapshot in "$snapshot_base"/*; do
        if [[ -d "$snapshot" && -f "$snapshot/metadata.json" ]]; then
            local phase_id timestamp
            phase_id=$(jq -r '.phase_id' "$snapshot/metadata.json" 2>/dev/null || echo "unknown")
            timestamp=$(jq -r '.timestamp' "$snapshot/metadata.json" 2>/dev/null || echo "unknown")
            echo "  $snapshot"
            echo "    Phase: $phase_id"
            echo "    Time: $timestamp"
        fi
    done
}

# Cleanup old snapshots (keep last N per phase)
# Usage: phase_cleanup_snapshots [keep_count]
phase_cleanup_snapshots() {
    local keep_count="${1:-3}"
    local snapshot_base="$ATOMIC_STATE_DIR/snapshots"

    if [[ ! -d "$snapshot_base" ]]; then
        return 0
    fi

    # Group by phase and remove old ones
    for phase_dir in "$snapshot_base"/*; do
        if [[ -d "$phase_dir" ]]; then
            local phase_id="${phase_dir##*/}"
            phase_id="${phase_id%%-[0-9]*}"

            # Count snapshots for this phase
            local snapshots
            mapfile -t snapshots < <(ls -d "$snapshot_base/$phase_id"-* 2>/dev/null | sort -r)

            # Remove excess
            local i=0
            for snap in "${snapshots[@]}"; do
                ((i++))
                if [[ $i -gt $keep_count ]]; then
                    rm -rf "$snap"
                    echo "Removed old snapshot: $snap"
                fi
            done
        fi
    done
}

# Validate that a task ID exists for the current phase
# Usage: phase_validate_task_id "101"
# Returns: 0 if valid, 1 if invalid
phase_validate_task_id() {
    local task_id="$1"
    local phase_id="${CURRENT_PHASE:-}"

    # Must be numeric
    if [[ ! "$task_id" =~ ^[0-9]+$ ]]; then
        echo "Task ID must be numeric"
        return 1
    fi

    # Extract phase number from task ID (first digit for single-digit phases)
    local task_phase="${task_id:0:1}"

    # If we have a current phase, validate against it
    if [[ -n "$phase_id" ]]; then
        local current_phase_num="${phase_id%%-*}"
        if [[ "$task_phase" != "$current_phase_num" ]]; then
            echo "Task $task_id is not in current phase ($current_phase_num)"
            return 1
        fi
    fi

    # Check if task script exists
    local phase_dir="$ATOMIC_ROOT/phases/${task_phase}-"*/
    if [[ -d $phase_dir ]]; then
        local task_script
        task_script=$(find "$phase_dir/tasks" -name "${task_id}-*.sh" 2>/dev/null | head -1)
        if [[ -z "$task_script" ]]; then
            echo "Task $task_id not found in phase $task_phase"
            return 1
        fi
    fi

    return 0
}

# ============================================================================
# PHASE LIFECYCLE
# ============================================================================

phase_start() {
    local phase_id="$1"
    local phase_name="$2"

    # Validate dependencies before starting phase
    if ! atomic_validate_deps; then
        echo "ERROR: Cannot start phase - missing dependencies" >&2
        return 1
    fi

    # Get phase number from id (e.g., "0-setup" -> "0")
    local phase_num="${phase_id%%-*}"

    # Check for memory backtrack (starting a phase <= current head)
    if memory_check_backtrack "$phase_num"; then
        if ! memory_handle_backtrack "$phase_num"; then
            echo "Backtrack cancelled by user" >&2
            return 1
        fi
    fi

    # Create snapshot before starting (for rollback capability)
    PHASE_SNAPSHOT_DIR=$(phase_snapshot "$phase_id")

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

    # Register signal handlers for clean interruption
    _phase_register_traps

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
    # Use printf with precision for fixed-width (58 chars, truncate if longer)
    local box_text
    box_text=$(printf "%-58.58s" "TASK $PHASE_TASKS_RUN: $task_name")
    echo -e "${BOLD}${CYAN}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓${NC}"
    echo -e "${BOLD}${CYAN}┃${NC} ${BOLD}${box_text}${NC} ${BOLD}${CYAN}┃${NC}"
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

    local tmp_file
    tmp_file=$(atomic_mktemp) || { echo "ERROR: Failed to create temp file for checkpoint" >&2; return 1; }

    if ! jq ".checkpoints += [{\"name\": \"$checkpoint_name\", \"timestamp\": \"$(date -Iseconds)\", \"data\": $checkpoint_data}]" \
        "$checkpoint_file" > "$tmp_file" 2>/dev/null; then
        echo "ERROR: jq failed in phase_checkpoint" >&2
        rm -f "$tmp_file" 2>/dev/null
        return 1
    fi

    if [[ ! -s "$tmp_file" ]] || ! jq empty "$tmp_file" 2>/dev/null; then
        echo "ERROR: Invalid JSON output in phase_checkpoint" >&2
        rm -f "$tmp_file" 2>/dev/null
        return 1
    fi

    mv "$tmp_file" "$checkpoint_file"
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
    local end_time
    end_time=$(date +%s)
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
  "started_at": "$(_phase_epoch_to_iso "$PHASE_START_TIME")",
  "completed_at": "$(date -Iseconds 2>/dev/null || date +%Y-%m-%dT%H:%M:%S%z)",
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
        # Use printf with precision for fixed-width (58 chars, truncate if longer)
        local skip_text
        skip_text=$(printf "%-58.58s" "TASK $task_id: $task_name [COMPLETE - SKIPPED]")
        echo -e "${DIM}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓${NC}"
        echo -e "${DIM}┃${NC} ${skip_text} ${DIM}┃${NC}"
        echo -e "${DIM}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛${NC}"
        return $TASK_CONTINUE
    fi

    while true; do
        echo ""
        # Use printf with precision for fixed-width (58 chars, truncate if longer)
        local box_text
        box_text=$(printf "%-58.58s" "TASK $task_id: $task_name")
        echo -e "${BOLD}${CYAN}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓${NC}"
        echo -e "${BOLD}${CYAN}┃${NC} ${BOLD}${box_text}${NC} ${BOLD}${CYAN}┃${NC}"
        echo -e "${BOLD}${CYAN}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛${NC}"

        # Mark task as started and track for signal cleanup
        task_state_start "$task_id" "$task_name"
        _PHASE_ACTIVE_TASK_ID="$task_id"
        _PHASE_ACTIVE_TASK_NAME="$task_name"

        # Run the task
        local task_result=0
        if $task_func; then
            # Mark task complete in persistent state
            task_state_complete "$task_id" "$task_name"
            _PHASE_ACTIVE_TASK_ID=""
            _PHASE_ACTIVE_TASK_NAME=""
            atomic_success "Task completed"

            # Post-task navigation
            echo ""
            echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "  ${GREEN}[c]${NC} Continue    ${YELLOW}[r]${NC} Redo    ${BLUE}[b]${NC} Go back    ${MAGENTA}[j]${NC} Jump to    ${RED}[q]${NC} Quit"
            echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    atomic_drain_stdin
            read -e -p "  Choice [c]: " choice || true
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
                    read -e -p "  Jump to: " jump_target || true
                    local validation_error
                    if validation_error=$(phase_validate_task_id "$jump_target" 2>&1); then
                        task_state_reset_from "$jump_target"
                        TASK_RESUME_AT="$jump_target"
                        atomic_info "Jumping to task $jump_target..."
                        return $TASK_CONTINUE
                    else
                        atomic_error "Invalid task ID: $validation_error"
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
            _PHASE_ACTIVE_TASK_ID=""
            _PHASE_ACTIVE_TASK_NAME=""
            atomic_error "Task failed"

            # Failure navigation
            echo ""
            echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "  ${YELLOW}[r]${NC} Retry    ${BLUE}[b]${NC} Go back    ${MAGENTA}[j]${NC} Jump to    ${DIM}[s]${NC} Skip    ${RED}[q]${NC} Quit"
            echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    atomic_drain_stdin
            read -e -p "  Choice [r]: " choice || true
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
                    read -e -p "  Jump to: " jump_target || true
                    local validation_error
                    if validation_error=$(phase_validate_task_id "$jump_target" 2>&1); then
                        task_state_reset_from "$jump_target"
                        TASK_RESUME_AT="$jump_target"
                        atomic_info "Jumping to task $jump_target..."
                        return $TASK_CONTINUE
                    else
                        atomic_error "Invalid task ID: $validation_error"
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
    local id name
    for task in "${tasks[@]}"; do
        # Extract the 3-digit ID
        id=$(echo "$task" | sed -n 's/task_\([0-9]\{3\}\)_.*/\1/p')
        if [[ -z "$id" ]]; then
            # Fallback: try 2-digit format and convert
            id=$(echo "$task" | sed -n 's/task_\([0-9]\{2\}\)_.*/\1/p')
            [[ -n "$id" ]] && id="0$id"
        fi
        [[ -z "$id" ]] && id="???"
        task_ids+=("$id")

        # Extract the name part after task_XXX_
        name="${task#task_[0-9][0-9][0-9]_}"
        [[ "$name" == "$task" ]] && name="${task#task_[0-9][0-9]_}"  # Try 2-digit
        name="${name//_/ }"  # Replace underscores with spaces
        # Capitalize first letter of each word (portable - works on BSD/GNU)
        name=$(echo "$name" | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2)} 1')
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

    read -e -p "Type 'approve' to continue, anything else to abort: " response || true

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
    read -e -p "Press Enter to continue..." _ || true
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
    local completed_text starting_text
    completed_text=$(printf "%-55.55s" "Completed: Phase $from_phase")
    starting_text=$(printf "%-55.55s" "Starting:  Phase $to_phase - $to_name")

    echo -e "${MAGENTA}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║${NC}                                                           ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}║${NC}  ${BOLD}PHASE TRANSITION${NC}                                        ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}║${NC}                                                           ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}║${NC}  ${DIM}${completed_text}${NC} ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}║${NC}  ${BOLD}${starting_text}${NC} ${MAGENTA}║${NC}"
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
        atomic_drain_stdin
        read -e -p "  Choice [c]: " choice || true
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
    local next_phase_num
    next_phase_num=$(basename "$(dirname "$next_script")" | cut -d'-' -f1)

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

    # Build flags to forward to next phase
    local forward_flags=("--skip-intro")
    [[ "${TASK_FORCE_REDO:-}" == "true" ]] && forward_flags+=("--redo")

    # Execute next phase (exec replaces current process)
    # Note: If exec fails, it returns non-zero but doesn't exit
    exec bash "$next_script" "${forward_flags[@]}"

    # If we reach here, exec failed
    atomic_error "Failed to execute next phase script: $next_script"
    atomic_info "Try running it manually: bash $next_script --skip-intro"
    return 1
}
