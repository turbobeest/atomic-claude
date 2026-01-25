#!/bin/bash
#
# PHASE 5: TDD IMPLEMENTATION
# Execute RED/GREEN/REFACTOR/VERIFY cycles for all tasks
#
# Tasks: 501-507 (5xx range)
#
# This phase implements all tasks using Test-Driven Development,
# executing RED/GREEN/REFACTOR/VERIFY cycles for each task.
#
# ═══════════════════════════════════════════════════════════════════
# PHASE STRUCTURE (Tasks 501-507)
# ═══════════════════════════════════════════════════════════════════
#
# Entry:
#   501 - Entry & Initialization - verify Phase 4 complete, init implementation
#   502 - TDD Setup - configure test framework, prepare worktrees
#
# Implementation:
#   503 - Agent Selection - select TDD implementation agents
#   504 - TDD Execution - RED/GREEN/REFACTOR/VERIFY loops per task
#   505 - Validation - final implementation validation
#
# Exit:
#   506 - Phase Audit - verify implementation quality and coverage
#   507 - Closeout - prepare for Phase 6 (Code Review)
#
# Artifacts produced:
#   - src/**/*                              - Implementation code
#   - tests/**/*                            - Test files
#   - .claude/tdd/cycle-*.json              - TDD cycle records
#   - .claude/audit/phase-05-audit.json     - Phase audit results
#   - .claude/closeout/phase-05-closeout.json - Phase closeout
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
    echo "Phase 5: TDD Implementation (RED/GREEN/REFACTOR/VERIFY)"
    echo ""
    echo "Usage: ./run.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --resume-at <ID>   Resume from specific task (e.g., --resume-at 504)"
    echo "  --reset-from <ID>  Reset state from task, run from there"
    echo "  --redo             Force re-run of all tasks (ignore completion state)"
    echo "  --clear            Clear all task state, start fresh"
    echo "  --status           Show task completion status and exit"
    echo "  --skip-intro       Skip the intro animation"
    echo "  -h, --help         Show this help"
    echo ""
    echo "Examples:"
    echo "  ./run.sh                    # Normal run (resumes from last completed)"
    echo "  ./run.sh --resume-at 504    # Start from task 504"
    echo "  ./run.sh --reset-from 505   # Reset tasks 505+ and run from 505"
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

    phase_start "5-implementation" "TDD Implementation"

    # ═══════════════════════════════════════════════════════════════════════════
    # ENTRY & INITIALIZATION
    # ═══════════════════════════════════════════════════════════════════════════

    # Task 501: Entry & Initialization
    phase_task_interactive "501" "Entry & Initialization" task_501_entry_initialization
    local result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 502: TDD Setup
    phase_task_interactive "502" "TDD Setup" task_502_tdd_setup
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ═══════════════════════════════════════════════════════════════════════════
    # AGENT SELECTION
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  AGENT SELECTION${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 503: Agent Selection
    phase_task_interactive "503" "Agent Selection" task_503_agent_selection
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ═══════════════════════════════════════════════════════════════════════════
    # TDD CYCLE EXECUTION
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  TDD CYCLE EXECUTION${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 504: TDD Execution (RED/GREEN/REFACTOR/VERIFY loops)
    phase_task_interactive "504" "TDD Execution" task_504_tdd_execution
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ═══════════════════════════════════════════════════════════════════════════
    # VALIDATION
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  VALIDATION${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 505: Final Validation
    phase_task_interactive "505" "Validation" task_505_validation
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

    # Task 506: Phase Audit
    phase_task_interactive "506" "Phase Audit" task_506_phase_audit
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 507: Closeout
    phase_task_interactive "507" "Closeout" task_507_closeout
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    phase_complete

    # Chain to Phase 6: Code Review
    phase_chain "5" "$ROOT_DIR/phases/6-code-review/run.sh" "Code Review"

    return 0
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
