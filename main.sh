#!/bin/bash
#
# ATOMIC CLAUDE - Main Entry Point
# Orchestrates phase execution for software development pipelines
#

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$ROOT_DIR/lib/atomic.sh"

# ============================================================================
# USAGE
# ============================================================================

usage() {
    cat << EOF
ATOMIC CLAUDE - Script-controlled LLM development pipeline

Usage: $(basename "$0") <command> [options]

Commands:
  run <phase>       Run a specific phase (e.g., run 0)
  status            Show current pipeline status
  list              List available phases
  reset             Reset pipeline state

Phase Flags (passed after phase number):
  --resume-at=NNN   Resume from specific task (e.g., --resume-at=107)
  --redo            Force redo of all tasks in the phase
  --reset-from=NNN  Reset all tasks from NNN onward, then run
  --pipeline-status Show full pipeline state across all phases
  --pipeline-reset=NNN  Reset from task NNN across all phases
  --status          Show task state for current phase

Phase 0 Only:
  --task=NNN        Resume Phase 0 from specific task
  --mode=MODE       Set setup mode (document|guided|quick)
  --skip-intro      Skip the intro animation

Options:
  -h, --help        Show this help message

Examples:
  $(basename "$0") run 0                  # Run Phase 0 (Setup)
  $(basename "$0") run 1                  # Run Phase 1 (Discovery)
  $(basename "$0") run 1 --resume-at=107  # Resume Phase 1 from Task 107
  $(basename "$0") run 1 --redo           # Redo all tasks in Phase 1
  $(basename "$0") status                 # Check where you are
  $(basename "$0") list                   # See all phases

EOF
}

# ============================================================================
# COMMANDS
# ============================================================================

cmd_list() {
    atomic_header "Available Phases"
    echo ""

    for phase_dir in "$ROOT_DIR"/phases/*/; do
        if [[ -f "$phase_dir/run.sh" ]]; then
            local phase_id=$(basename "$phase_dir")
            local status="pending"

            # Check if completed
            if [[ -f "$ATOMIC_OUTPUT_DIR/$phase_id/closeout.json" ]]; then
                status="completed"
            fi

            printf "  %-20s [%s]\n" "$phase_id" "$status"
        fi
    done
    echo ""
}

cmd_status() {
    atomic_header "Pipeline Status"

    local session_file="$ATOMIC_STATE_DIR/session.json"

    if [[ ! -f "$session_file" ]]; then
        echo ""
        atomic_info "No active session. Run 'main.sh run 00-setup' to begin."
        return 0
    fi

    echo ""
    echo "Session ID:      $(jq -r '.session_id' "$session_file")"
    echo "Started:         $(jq -r '.started_at' "$session_file")"
    echo "Current Phase:   $(jq -r '.current_phase // "none"' "$session_file")"
    echo "Tasks Completed: $(jq -r '.tasks_completed' "$session_file")"
    echo "Tasks Failed:    $(jq -r '.tasks_failed' "$session_file")"
    echo ""

    # Show phase completion status
    echo "Phase Status:"
    for phase_dir in "$ROOT_DIR"/phases/*/; do
        if [[ -f "$phase_dir/run.sh" ]]; then
            local phase_id=$(basename "$phase_dir")
            local closeout="$ATOMIC_OUTPUT_DIR/$phase_id/closeout.json"

            if [[ -f "$closeout" ]]; then
                local completed_at=$(jq -r '.completed_at' "$closeout")
                echo "  ✓ $phase_id (completed: $completed_at)"
            else
                echo "  ○ $phase_id"
            fi
        fi
    done
    echo ""
}

cmd_run() {
    local phase_input="$1"
    local phase_dir=""

    # Support both "0" and "0-setup" formats
    if [[ "$phase_input" =~ ^[0-9]$ ]]; then
        # Single digit - find matching phase
        for p in "$ROOT_DIR"/phases/${phase_input}-*/; do
            if [[ -d "$p" ]]; then
                phase_dir="$p"
                break
            fi
        done
    else
        phase_dir="$ROOT_DIR/phases/$phase_input"
    fi

    if [[ ! -d "$phase_dir" ]]; then
        atomic_error "Phase not found: $phase_input"
        echo ""
        echo "Available phases:"
        cmd_list
        exit 1
    fi

    local phase_id=$(basename "$phase_dir")

    if [[ ! -f "$phase_dir/run.sh" ]]; then
        atomic_error "Phase script not found: $phase_dir/run.sh"
        atomic_info "Phase $phase_id exists but has no run.sh yet"
        exit 1
    fi

    # Check prerequisites (previous phase completed)
    # Phase 0 has no prereq
    local phase_num="${phase_id%%-*}"
    if [[ "$phase_num" != "0" ]]; then
        local prev_num=$((phase_num - 1))

        # Find previous phase
        local prev_phase=""
        for p in "$ROOT_DIR"/phases/${prev_num}-*/; do
            if [[ -d "$p" ]]; then
                prev_phase=$(basename "$p")
                break
            fi
        done

        if [[ -n "$prev_phase" ]] && [[ ! -f "$ATOMIC_OUTPUT_DIR/$prev_phase/closeout.json" ]]; then
            atomic_error "Previous phase not completed: $prev_phase"
            atomic_info "Run: ./main.sh run $prev_num"
            exit 1
        fi
    fi

    # Run the phase, passing through extra flags (--task=, --mode=, etc.)
    shift
    exec bash "$phase_dir/run.sh" "$@"
}

cmd_reset() {
    atomic_warn "This will reset all pipeline state!"
    read -e -p "Type 'reset' to confirm: " confirm

    if [[ "$confirm" == "reset" ]]; then
        rm -rf "$ATOMIC_STATE_DIR" "$ATOMIC_OUTPUT_DIR" "$ATOMIC_LOG_DIR"
        atomic_success "Pipeline state reset"
    else
        atomic_info "Reset cancelled"
    fi
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    case "${1:-}" in
        run)
            [[ -z "${2:-}" ]] && { echo "Usage: $0 run <phase>"; exit 1; }
            cmd_run "${@:2}"
            ;;
        status)
            cmd_status
            ;;
        list)
            cmd_list
            ;;
        reset)
            cmd_reset
            ;;
        -h|--help|"")
            usage
            ;;
        *)
            echo "Unknown command: $1"
            usage
            exit 1
            ;;
    esac
}

main "$@"
