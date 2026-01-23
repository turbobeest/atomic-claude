#!/bin/bash
#
# PHASE 4: SPECIFICATION
# Expand tasks into TDD-ready OpenSpec definitions
#
# Tasks: 401-406 (4xx range)
#
# This phase transforms TaskMaster tasks into detailed specifications
# with TDD subtasks (RED/GREEN/REFACTOR/VERIFY) for implementation.
#
# ═══════════════════════════════════════════════════════════════════
# PHASE STRUCTURE (Tasks 401-406)
# ═══════════════════════════════════════════════════════════════════
#
# Entry:
#   401 - Entry & Initialization - verify tasks.json, init spec directory
#   402 - Agent Selection - select specification agents
#
# Specification:
#   403 - OpenSpec Generation - create spec files for each task
#   404 - TDD Subtask Injection - write RED/GREEN/REFACTOR/VERIFY subtasks
#
# Exit:
#   405 - Phase Audit - verify spec coverage and quality
#   406 - Closeout - prepare for Phase 5 (TDD Implementation)
#
# Artifacts produced:
#   - .claude/specs/spec-*.json          - OpenSpec definitions per task
#   - .taskmaster/tasks/tasks.json       - Updated with TDD subtasks
#   - phase-04-audit.json                - Phase audit results
#   - phase-04-closeout.json             - Phase closeout
#

set -euo pipefail

PHASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$PHASE_DIR/../.." && pwd)"

# Source libraries
source "$ROOT_DIR/lib/phase.sh"

# Source task files
for task_file in "$PHASE_DIR/tasks/"*.sh; do
    [[ -f "$task_file" ]] && source "$task_file"
done

# ============================================================================
# USAGE
# ============================================================================

show_usage() {
    echo ""
    echo "Phase 4: Specification (Tasks → OpenSpec + TDD Subtasks)"
    echo ""
    echo "Usage: ./run.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --resume-at <ID>   Resume from specific task (e.g., --resume-at 403)"
    echo "  --reset-from <ID>  Reset state from task, run from there"
    echo "  --redo             Force re-run of all tasks (ignore completion state)"
    echo "  --clear            Clear all task state, start fresh"
    echo "  --status           Show task completion status and exit"
    echo "  --skip-intro       Skip the intro animation"
    echo "  -h, --help         Show this help"
    echo ""
    echo "Examples:"
    echo "  ./run.sh                    # Normal run (resumes from last completed)"
    echo "  ./run.sh --resume-at 403    # Start from task 403"
    echo "  ./run.sh --reset-from 404   # Reset tasks 404+ and run from 404"
    echo "  ./run.sh --redo             # Force re-run everything"
    echo "  ./run.sh --status           # Show what's complete"
    echo ""
}

# ============================================================================
# MAIN WORKFLOW
# ============================================================================

main() {
    # Parse task state arguments
    task_state_parse_args "$@"

    # Handle help
    for arg in "$@"; do
        case "$arg" in
            -h|--help)
                show_usage
                exit 0
                ;;
        esac
    done

    phase_start "4-specification" "Specification"

    # ═══════════════════════════════════════════════════════════════════════════
    # ENTRY & INITIALIZATION
    # ═══════════════════════════════════════════════════════════════════════════

    # Task 401: Entry & Initialization
    phase_task_interactive "401" "Entry & Initialization" task_401_entry_initialization
    local result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 402: Agent Selection
    phase_task_interactive "402" "Agent Selection" task_402_agent_selection
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ═══════════════════════════════════════════════════════════════════════════
    # OPENSPEC GENERATION
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  OPENSPEC GENERATION${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 403: OpenSpec Generation
    phase_task_interactive "403" "OpenSpec Generation" task_403_openspec_generation
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 404: TDD Subtask Injection
    phase_task_interactive "404" "TDD Subtask Injection" task_404_tdd_subtask_injection
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE AUDIT & CLOSEOUT
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  PHASE AUDIT & CLOSEOUT${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 405: Phase Audit
    phase_task_interactive "405" "Phase Audit" task_405_phase_audit
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 406: Closeout
    phase_task_interactive "406" "Closeout" task_406_closeout
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    phase_complete

    return 0
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
