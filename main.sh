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
  run <phase>       Run a specific phase (e.g., run 00-setup)
  status            Show current pipeline status
  list              List available phases
  reset             Reset pipeline state

Options:
  -h, --help        Show this help message

Examples:
  $(basename "$0") run 00-setup     # Run the setup phase
  $(basename "$0") status           # Check where you are
  $(basename "$0") list             # See all phases

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
    local phase_id="$1"
    local phase_dir="$ROOT_DIR/phases/$phase_id"

    if [[ ! -d "$phase_dir" ]]; then
        atomic_error "Phase not found: $phase_id"
        echo ""
        echo "Available phases:"
        cmd_list
        exit 1
    fi

    if [[ ! -f "$phase_dir/run.sh" ]]; then
        atomic_error "Phase script not found: $phase_dir/run.sh"
        exit 1
    fi

    # Check prerequisites (previous phase completed)
    # For now, only 00-setup has no prereq
    if [[ "$phase_id" != "00-setup" ]]; then
        # Extract phase number
        local phase_num="${phase_id%%-*}"
        local prev_num=$(printf "%02d" $((10#$phase_num - 1)))

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
            atomic_info "Run: ./main.sh run $prev_phase"
            exit 1
        fi
    fi

    # Run the phase
    exec bash "$phase_dir/run.sh"
}

cmd_reset() {
    atomic_warn "This will reset all pipeline state!"
    read -p "Type 'reset' to confirm: " confirm

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
            cmd_run "$2"
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
