#!/bin/bash
#
# ATOMIC CLAUDE - Task State Management
# Provides persistent task-level state tracking for resumable workflows
#
# Features:
#   - Track completed tasks per phase
#   - Resume from any task
#   - Reset/redo from specific task
#   - Survive session boundaries
#
# State file: .claude/task-state.json
#
# Usage:
#   source lib/task-state.sh
#   task_state_init "1-ideation"
#   task_state_should_skip "101" && return 0
#   ... run task ...
#   task_state_complete "101" "Entry Validation"
#

# ============================================================================
# STATE FILE MANAGEMENT
# ============================================================================

# Use atomic_mktemp if available (from atomic.sh), else fall back to mktemp
_task_state_mktemp() {
    if type -t atomic_mktemp &>/dev/null; then
        atomic_mktemp
    else
        mktemp
    fi
}

# Lock file for concurrent access protection
TASK_STATE_LOCK_FILE=""

# Acquire lock on state file
# Usage: _task_state_lock
_task_state_lock() {
    if [[ -z "$TASK_STATE_LOCK_FILE" ]]; then
        TASK_STATE_LOCK_FILE="${TASK_STATE_FILE}.lock"
    fi

    # Use flock if available, otherwise use mkdir-based lock
    if command -v flock &>/dev/null; then
        exec 200>"$TASK_STATE_LOCK_FILE"
        if ! flock -w 10 200; then
            echo "ERROR: Failed to acquire state file lock after 10s" >&2
            return 1
        fi
    else
        # Fallback: mkdir is atomic on all POSIX systems
        local lock_dir="${TASK_STATE_LOCK_FILE}.d"
        local max_wait=10
        local waited=0
        while ! mkdir "$lock_dir" 2>/dev/null; do
            sleep 1
            ((waited++))
            if [[ $waited -ge $max_wait ]]; then
                # Check if lock holder is still alive (stale lock cleanup)
                local lock_pid_file="$lock_dir/pid"
                if [[ -f "$lock_pid_file" ]]; then
                    local lock_pid
                    lock_pid=$(cat "$lock_pid_file" 2>/dev/null || echo "")
                    if [[ -n "$lock_pid" ]] && ! kill -0 "$lock_pid" 2>/dev/null; then
                        # Lock holder is dead, remove stale lock
                        rm -rf "$lock_dir" 2>/dev/null
                        continue
                    fi
                fi
                echo "ERROR: Failed to acquire state file lock after ${max_wait}s" >&2
                return 1
            fi
        done
        echo "$$" > "$lock_dir/pid" 2>/dev/null || true
    fi
    return 0
}

# Release lock on state file
# Usage: _task_state_unlock
_task_state_unlock() {
    if [[ -z "$TASK_STATE_LOCK_FILE" ]]; then
        return
    fi
    if command -v flock &>/dev/null; then
        flock -u 200 2>/dev/null || true
    else
        # Remove mkdir-based lock
        rm -rf "${TASK_STATE_LOCK_FILE}.d" 2>/dev/null || true
    fi
}

# Safe jq update with error handling and file locking
# Usage: _task_state_jq_update "jq_filter" [jq_args...]
# Applies jq filter to TASK_STATE_FILE with validation
_task_state_jq_update() {
    local filter="$1"
    shift

    # Acquire lock for concurrent safety
    _task_state_lock || return 1

    local tmp
    tmp=$(_task_state_mktemp) || {
        echo "ERROR: Failed to create temp file for state update" >&2
        _task_state_unlock
        return 1
    }

    # Run jq and capture exit code
    if ! jq "$@" "$filter" "$TASK_STATE_FILE" > "$tmp" 2>/dev/null; then
        echo "ERROR: jq filter failed: $filter" >&2
        rm -f "$tmp" 2>/dev/null
        _task_state_unlock
        return 1
    fi

    # Validate output is non-empty
    if [[ ! -s "$tmp" ]]; then
        echo "ERROR: jq produced empty output for: $filter" >&2
        rm -f "$tmp" 2>/dev/null
        _task_state_unlock
        return 1
    fi

    # Validate output is valid JSON
    if ! jq empty "$tmp" 2>/dev/null; then
        echo "ERROR: jq produced invalid JSON for: $filter" >&2
        rm -f "$tmp" 2>/dev/null
        _task_state_unlock
        return 1
    fi

    # Atomically replace state file
    if ! mv "$tmp" "$TASK_STATE_FILE"; then
        echo "ERROR: Failed to update state file" >&2
        rm -f "$tmp" 2>/dev/null
        _task_state_unlock
        return 1
    fi

    _task_state_unlock
    return 0
}

TASK_STATE_FILE=""

task_state_init() {
    local phase_id="$1"

    TASK_STATE_FILE="$ATOMIC_ROOT/.claude/task-state.json"

    # Initialize state file if it doesn't exist
    if [[ ! -f "$TASK_STATE_FILE" ]]; then
        mkdir -p "$(dirname "$TASK_STATE_FILE")"
        cat > "$TASK_STATE_FILE" << 'EOF'
{
    "version": "1.0",
    "current_phase": null,
    "current_task": null,
    "phases": {}
}
EOF
    fi

    # Ensure phase entry exists
    _task_state_jq_update '
        .current_phase = $phase |
        if .phases[$phase] == null then
            .phases[$phase] = {
                "started_at": (now | todate),
                "tasks": {},
                "completed": false
            }
        else . end
    ' --arg phase "$phase_id"

    # Recover any tasks stuck in in_progress from previous interrupted sessions
    task_state_recover_stuck
}

# ============================================================================
# TASK STATE QUERIES
# ============================================================================

# Check if a task is already complete
# Usage: task_state_is_complete "101"
# Returns: 0 if complete, 1 if not
task_state_is_complete() {
    local task_id="$1"

    # Ensure TASK_STATE_FILE is set (needed for subshell contexts)
    if [[ -z "$TASK_STATE_FILE" ]]; then
        TASK_STATE_FILE="$ATOMIC_ROOT/.claude/task-state.json"
    fi
    [[ ! -f "$TASK_STATE_FILE" ]] && return 1

    local phase_id
    phase_id=$(jq -r '.current_phase // ""' "$TASK_STATE_FILE")

    [[ -z "$phase_id" ]] && return 1

    local status
    status=$(jq -r --arg phase "$phase_id" --arg task "$task_id" \
        '.phases[$phase].tasks[$task].status // "pending"' "$TASK_STATE_FILE")

    [[ "$status" == "complete" ]]
}

# Check if task should be skipped (complete and not forcing redo)
# Usage: task_state_should_skip "101"
# Returns: 0 if should skip, 1 if should run
task_state_should_skip() {
    local task_id="$1"

    # Ensure TASK_STATE_FILE is set (needed for subshell contexts)
    if [[ -z "$TASK_STATE_FILE" ]]; then
        TASK_STATE_FILE="$ATOMIC_ROOT/.claude/task-state.json"
    fi

    # Check for forced redo flag
    [[ "${TASK_FORCE_REDO:-}" == "true" ]] && return 1

    # Check for resume target - skip until we reach it
    if [[ -n "${TASK_RESUME_AT:-}" ]]; then
        if [[ "$task_id" == "$TASK_RESUME_AT" ]]; then
            # Reached resume point, clear it and run
            TASK_RESUME_AT=""
            return 1
        fi
        # Haven't reached resume point yet, skip
        return 0
    fi

    # Normal case: skip if complete
    task_state_is_complete "$task_id"
}

# Get the last completed task for current phase
# Usage: task_state_get_last_complete
# Outputs: task ID or empty string
task_state_get_last_complete() {
    local phase_id
    phase_id=$(jq -r '.current_phase // ""' "$TASK_STATE_FILE")

    [[ -z "$phase_id" ]] && return

    jq -r --arg phase "$phase_id" '
        .phases[$phase].tasks |
        to_entries |
        map(select(.value.status == "complete")) |
        sort_by(.value.completed_at) |
        last |
        .key // ""
    ' "$TASK_STATE_FILE"
}

# Get the next task to run (first incomplete)
# Usage: task_state_get_resume_point
# Outputs: task ID or empty string
task_state_get_resume_point() {
    local phase_id
    phase_id=$(jq -r '.current_phase // ""' "$TASK_STATE_FILE")

    [[ -z "$phase_id" ]] && return

    jq -r '.current_task // ""' "$TASK_STATE_FILE"
}

# ============================================================================
# TASK STATE UPDATES
# ============================================================================

# Mark a task as in-progress (idempotent - won't overwrite if already in_progress)
# Usage: task_state_start "101" "Entry Validation"
task_state_start() {
    local task_id="$1"
    local task_name="$2"
    local phase_id
    phase_id=$(jq -r '.current_phase // ""' "$TASK_STATE_FILE")

    [[ -z "$phase_id" ]] && return 1

    _task_state_jq_update '
        .current_task = $task |
        if (.phases[$phase].tasks[$task].status == "in_progress") then
            .phases[$phase].tasks[$task].name = $name
        else
            .phases[$phase].tasks[$task] = {
                "name": $name,
                "status": "in_progress",
                "started_at": (now | todate),
                "completed_at": null,
                "artifacts": []
            }
        end
    ' --arg phase "$phase_id" --arg task "$task_id" --arg name "$task_name"
}

# Mark a task as complete
# Usage: task_state_complete "101" "Entry Validation" ["artifact1.json" "artifact2.md"]
task_state_complete() {
    local task_id="$1"
    local task_name="$2"
    shift 2
    local artifacts=("$@")
    local phase_id
    phase_id=$(jq -r '.current_phase // ""' "$TASK_STATE_FILE")

    [[ -z "$phase_id" ]] && return 1

    # Build artifacts array for jq
    local artifacts_json="[]"
    if [[ ${#artifacts[@]} -gt 0 ]]; then
        artifacts_json=$(printf '%s\n' "${artifacts[@]}" | jq -R . | jq -s .)
    fi

    _task_state_jq_update '
        .current_task = null |
        .phases[$phase].tasks[$task].status = "complete" |
        .phases[$phase].tasks[$task].completed_at = (now | todate) |
        .phases[$phase].tasks[$task].artifacts = $artifacts
    ' --arg phase "$phase_id" --arg task "$task_id" --arg name "$task_name" \
      --argjson artifacts "$artifacts_json"
}

# Mark a task as failed
# Usage: task_state_fail "101" "Error message"
task_state_fail() {
    local task_id="$1"
    local error_msg="$2"
    local phase_id
    phase_id=$(jq -r '.current_phase // ""' "$TASK_STATE_FILE")

    [[ -z "$phase_id" ]] && return 1

    _task_state_jq_update '
        .phases[$phase].tasks[$task].status = "failed" |
        .phases[$phase].tasks[$task].error = $error |
        .phases[$phase].tasks[$task].failed_at = (now | todate)
    ' --arg phase "$phase_id" --arg task "$task_id" --arg error "$error_msg"
}

# ============================================================================
# TASK NAVIGATION
# ============================================================================

# Reset task state from a specific task (inclusive)
# All tasks from this point forward are marked pending
# Usage: task_state_reset_from "105"
task_state_reset_from() {
    local from_task="$1"
    local phase_id
    phase_id=$(jq -r '.current_phase // ""' "$TASK_STATE_FILE")

    [[ -z "$phase_id" ]] && return 1

    _task_state_jq_update '
        .current_task = $from |
        .phases[$phase].tasks |= with_entries(
            if (.key >= $from) then
                .value.status = "pending" |
                .value.completed_at = null
            else . end
        )
    ' --arg phase "$phase_id" --arg from "$from_task"

    echo "Reset to task $from_task - all subsequent tasks marked pending"
}

# Clear all task state for current phase (start fresh)
# Usage: task_state_clear_phase
task_state_clear_phase() {
    local phase_id
    phase_id=$(jq -r '.current_phase // ""' "$TASK_STATE_FILE")

    [[ -z "$phase_id" ]] && return 1

    _task_state_jq_update '
        .current_task = null |
        .phases[$phase].tasks = {} |
        .phases[$phase].completed = false
    ' --arg phase "$phase_id"

    echo "Cleared all task state for phase $phase_id"
}

# Mark entire phase as complete
# Usage: task_state_phase_complete
task_state_phase_complete() {
    local phase_id
    phase_id=$(jq -r '.current_phase // ""' "$TASK_STATE_FILE")

    [[ -z "$phase_id" ]] && return 1

    _task_state_jq_update '
        .current_task = null |
        .phases[$phase].completed = true |
        .phases[$phase].completed_at = (now | todate)
    ' --arg phase "$phase_id"
}

# ============================================================================
# CROSS-PHASE REVERSIBILITY
# ============================================================================

# Reset pipeline from any task across any phase
# Clears all progress from that task forward, including all subsequent phases
# Usage: task_state_pipeline_reset "204"  (resets from Phase 2, Task 204)
# Usage: task_state_pipeline_reset "2" "04" (explicit phase/task)
task_state_pipeline_reset() {
    local input="$1"
    local target_phase=""
    local target_task=""

    # Parse input: "204" -> phase 2, task 204
    # First digit(s) before the last 2 digits = phase
    if [[ ${#input} -eq 3 ]]; then
        # 3-digit: 204 -> phase 2, task 04
        target_phase="${input:0:1}"
        target_task="$input"
    elif [[ ${#input} -eq 4 ]]; then
        # 4-digit: 1204 -> phase 12, task 04 (future-proofing)
        target_phase="${input:0:2}"
        target_task="$input"
    else
        echo "Invalid task ID format. Use 3-digit (e.g., 204) or 4-digit (e.g., 1104)"
        return 1
    fi

    echo ""
    echo -e "${YELLOW}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║${NC} ${BOLD}PIPELINE RESET${NC}                                            ${YELLOW}║${NC}"
    echo -e "${YELLOW}╠═══════════════════════════════════════════════════════════╣${NC}"
    echo -e "${YELLOW}║${NC} Resetting from: Task $target_task (Phase $target_phase)                       ${YELLOW}║${NC}"
    echo -e "${YELLOW}║${NC}                                                           ${YELLOW}║${NC}"
    echo -e "${YELLOW}║${NC} This will:                                                ${YELLOW}║${NC}"
    echo -e "${YELLOW}║${NC}   • Reset Phase $target_phase from task $target_task                          ${YELLOW}║${NC}"
    echo -e "${YELLOW}║${NC}   • Clear ALL phases after Phase $target_phase                       ${YELLOW}║${NC}"
    echo -e "${YELLOW}║${NC}                                                           ${YELLOW}║${NC}"
    echo -e "${YELLOW}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Get list of all phases
    local all_phases
    all_phases=$(jq -r '.phases | keys[]' "$TASK_STATE_FILE" 2>/dev/null | sort -t'-' -k1 -n)

    local started_clearing=false
    local phases_cleared=0
    local tasks_reset=0

    for phase_entry in $all_phases; do
        # Extract phase number from phase ID (e.g., "2-discovery" -> "2")
        local phase_num="${phase_entry%%-*}"

        if [[ "$phase_num" -eq "$target_phase" ]]; then
            # This is the target phase - reset from the specific task
            echo -e "  ${YELLOW}→${NC} Phase $phase_num: Resetting from task $target_task"

            _task_state_jq_update '
                .phases[$phase].completed = false |
                .phases[$phase].completed_at = null |
                .phases[$phase].tasks |= with_entries(
                    if (.key >= $from) then
                        .value.status = "pending" |
                        .value.completed_at = null
                    else . end
                )
            ' --arg phase "$phase_entry" --arg from "$target_task"

            # Count reset tasks
            local reset_count
            reset_count=$(jq -r --arg phase "$phase_entry" --arg from "$target_task" '
                [.phases[$phase].tasks | to_entries[] | select(.key >= $from)] | length
            ' "$TASK_STATE_FILE")
            tasks_reset=$((tasks_reset + reset_count))

            started_clearing=true

        elif [[ "$started_clearing" == true ]] || [[ "$phase_num" -gt "$target_phase" ]]; then
            # This phase comes after target - clear entirely
            echo -e "  ${RED}✗${NC} Phase $phase_num: Clearing all tasks"

            _task_state_jq_update '
                .phases[$phase].completed = false |
                .phases[$phase].completed_at = null |
                .phases[$phase].tasks = {}
            ' --arg phase "$phase_entry"

            phases_cleared=$((phases_cleared + 1))
            started_clearing=true

        else
            # This phase is before target - keep it
            echo -e "  ${GREEN}✓${NC} Phase $phase_num: Preserved"
        fi
    done

    # Update current phase to target
    local target_phase_id
    target_phase_id=$(jq -r --arg num "$target_phase" '
        .phases | keys[] | select(startswith($num + "-"))
    ' "$TASK_STATE_FILE" | head -1)

    if [[ -n "$target_phase_id" ]]; then
        _task_state_jq_update '
            .current_phase = $phase |
            .current_task = $task
        ' --arg phase "$target_phase_id" --arg task "$target_task"
    fi

    echo ""
    echo -e "  ${BOLD}Summary:${NC}"
    echo -e "    Tasks reset in Phase $target_phase: $tasks_reset"
    echo -e "    Phases cleared: $phases_cleared"
    echo ""
    echo -e "  ${CYAN}To continue from task $target_task:${NC}"
    echo -e "    ./phases/$target_phase-*/run.sh"
    echo ""
}

# Show full pipeline state across all phases
# Usage: task_state_pipeline_status
task_state_pipeline_status() {
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}PIPELINE STATE${NC}                                            ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Get all phases sorted
    local all_phases
    all_phases=$(jq -r '.phases | keys[]' "$TASK_STATE_FILE" 2>/dev/null | sort -t'-' -k1 -n)

    if [[ -z "$all_phases" ]]; then
        echo "  No phases tracked yet."
        echo ""
        return
    fi

    local current_phase
    current_phase=$(jq -r '.current_phase // ""' "$TASK_STATE_FILE")

    for phase_entry in $all_phases; do
        local phase_num="${phase_entry%%-*}"
        local phase_name="${phase_entry#*-}"
        local is_complete
        is_complete=$(jq -r --arg phase "$phase_entry" '.phases[$phase].completed // false' "$TASK_STATE_FILE")

        # Count tasks
        local total_tasks complete_tasks pending_tasks failed_tasks
        total_tasks=$(jq -r --arg phase "$phase_entry" '[.phases[$phase].tasks | keys[]] | length' "$TASK_STATE_FILE")
        complete_tasks=$(jq -r --arg phase "$phase_entry" '[.phases[$phase].tasks | to_entries[] | select(.value.status == "complete")] | length' "$TASK_STATE_FILE")
        pending_tasks=$(jq -r --arg phase "$phase_entry" '[.phases[$phase].tasks | to_entries[] | select(.value.status == "pending" or .value.status == null)] | length' "$TASK_STATE_FILE")
        failed_tasks=$(jq -r --arg phase "$phase_entry" '[.phases[$phase].tasks | to_entries[] | select(.value.status == "failed")] | length' "$TASK_STATE_FILE")

        # Determine status icon and color
        local status_icon status_color
        if [[ "$is_complete" == "true" ]]; then
            status_icon="✓"
            status_color="${GREEN}"
        elif [[ "$phase_entry" == "$current_phase" ]]; then
            status_icon="→"
            status_color="${YELLOW}"
        elif [[ $total_tasks -eq 0 ]]; then
            status_icon="○"
            status_color="${DIM}"
        else
            status_icon="◐"
            status_color="${BLUE}"
        fi

        printf "  ${status_color}%s${NC} Phase %-2s %-20s " "$status_icon" "$phase_num" "$phase_name"

        if [[ $total_tasks -gt 0 ]]; then
            echo -e "[${GREEN}$complete_tasks${NC}/${total_tasks} tasks]"

            # Show individual tasks if phase is current or has issues
            if [[ "$phase_entry" == "$current_phase" ]] || [[ $failed_tasks -gt 0 ]]; then
                jq -r --arg phase "$phase_entry" '
                    .phases[$phase].tasks | to_entries | sort_by(.key)[] |
                    "      \(.key): \(.value.status // "pending")"
                ' "$TASK_STATE_FILE" 2>/dev/null | while read -r line; do
                    if [[ "$line" == *"complete"* ]]; then
                        echo -e "    ${GREEN}✓${NC}${line#*:}"
                    elif [[ "$line" == *"in_progress"* ]]; then
                        echo -e "    ${YELLOW}→${NC}${line#*:}"
                    elif [[ "$line" == *"failed"* ]]; then
                        echo -e "    ${RED}✗${NC}${line#*:}"
                    else
                        echo -e "    ${DIM}○${NC}${line#*:}"
                    fi
                done
            fi
        else
            echo -e "${DIM}[not started]${NC}"
        fi
    done

    echo ""
}

# ============================================================================
# STATUS DISPLAY
# ============================================================================

# Show task state for current phase
# Usage: task_state_show
task_state_show() {
    local phase_id
    phase_id=$(jq -r '.current_phase // ""' "$TASK_STATE_FILE")

    if [[ -z "$phase_id" ]]; then
        echo "No active phase"
        return
    fi

    echo ""
    echo -e "${CYAN}Task State: Phase $phase_id${NC}"
    echo -e "${DIM}─────────────────────────────────────────────${NC}"

    jq -r --arg phase "$phase_id" '
        .phases[$phase].tasks | to_entries[] |
        "\(.key): \(.value.status) - \(.value.name // "unnamed")"
    ' "$TASK_STATE_FILE" 2>/dev/null | while read -r line; do
        if [[ "$line" == *"complete"* ]]; then
            echo -e "  ${GREEN}✓${NC} $line"
        elif [[ "$line" == *"in_progress"* ]]; then
            echo -e "  ${YELLOW}→${NC} $line"
        elif [[ "$line" == *"failed"* ]]; then
            echo -e "  ${RED}✗${NC} $line"
        else
            echo -e "  ${DIM}○${NC} $line"
        fi
    done

    echo ""
}

# ============================================================================
# STUCK TASK RECOVERY
# ============================================================================

# Detect and reset tasks stuck in "in_progress" state
# Called automatically during task_state_init to recover from interrupted sessions
# Usage: task_state_recover_stuck
task_state_recover_stuck() {
    [[ ! -f "$TASK_STATE_FILE" ]] && return 0

    local phase_id
    phase_id=$(jq -r '.current_phase // ""' "$TASK_STATE_FILE")
    [[ -z "$phase_id" ]] && return 0

    # Find tasks stuck in in_progress
    local stuck_tasks
    stuck_tasks=$(jq -r --arg phase "$phase_id" '
        .phases[$phase].tasks // {} | to_entries[] |
        select(.value.status == "in_progress") | .key
    ' "$TASK_STATE_FILE" 2>/dev/null)

    if [[ -n "$stuck_tasks" ]]; then
        echo -e "  ${YELLOW}!${NC} Recovering stuck tasks from previous interrupted session:" >&2
        while IFS= read -r task_id; do
            local task_name
            task_name=$(jq -r --arg phase "$phase_id" --arg task "$task_id" \
                '.phases[$phase].tasks[$task].name // "unknown"' "$TASK_STATE_FILE")
            echo -e "    ${YELLOW}→${NC} Task $task_id ($task_name): in_progress → pending" >&2
            _task_state_jq_update '
                .phases[$phase].tasks[$task].status = "pending" |
                .phases[$phase].tasks[$task].completed_at = null
            ' --arg phase "$phase_id" --arg task "$task_id"
        done <<< "$stuck_tasks"
        echo "" >&2
    fi
}

# ============================================================================
# CLI INTERFACE
# ============================================================================

# Parse --resume-at and --redo flags
# Usage: task_state_parse_args "$@"
task_state_parse_args() {
    TASK_RESUME_AT=""
    TASK_FORCE_REDO=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --resume-at)
                TASK_RESUME_AT="$2"
                shift 2
                ;;
            --resume-at=*)
                TASK_RESUME_AT="${1#*=}"
                shift
                ;;
            --redo)
                TASK_FORCE_REDO="true"
                shift
                ;;
            --reset-from)
                task_state_reset_from "$2"
                shift 2
                ;;
            --reset-from=*)
                task_state_reset_from "${1#*=}"
                shift
                ;;
            --pipeline-reset)
                # Cross-phase reset: clears from task N through all subsequent phases
                task_state_pipeline_reset "$2"
                exit 0
                ;;
            --pipeline-reset=*)
                task_state_pipeline_reset "${1#*=}"
                exit 0
                ;;
            --pipeline-status)
                task_state_pipeline_status
                exit 0
                ;;
            --clear)
                task_state_clear_phase
                shift
                ;;
            --status)
                task_state_show
                exit 0
                ;;
            -h|--help|--skip-intro)
                # Known flags handled elsewhere — pass through silently
                shift
                ;;
            --*)
                echo "Warning: Unknown flag '$1' ignored" >&2
                echo "  Supported: --resume-at=N, --redo, --reset-from=N, --clear, --status, --pipeline-status, --pipeline-reset=N" >&2
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
}
