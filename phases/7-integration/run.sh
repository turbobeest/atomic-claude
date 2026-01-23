#!/bin/bash
#
# PHASE 7: INTEGRATION
# System Integration + E2E Validation
#
# Tasks: 701-707 (7xx range)
#
# This phase integrates all components and validates the complete system
# through end-to-end testing, acceptance criteria verification, and
# performance benchmarking.
#
# ===================================================================
# PHASE STRUCTURE (Tasks 701-707)
# ===================================================================
#
# Entry:
#   701 - Entry & Initialization - verify Phase 6 complete, init integration
#   702 - Integration Setup - configure test environments, prepare fixtures
#
# Integration:
#   703 - Agent Selection - select integration testing agents
#   704 - Testing Execution - run E2E tests, acceptance, performance
#   705 - Integration Approval - HUMAN GATE for integration sign-off
#
# Exit:
#   706 - Phase Audit - verify integration quality and coverage
#   707 - Closeout - prepare for Phase 8 (Deployment Prep)
#
# Artifacts produced:
#   - .claude/integration/e2e-results.json          - E2E test results
#   - .claude/integration/acceptance-results.json   - Acceptance validation
#   - .claude/integration/performance-results.json  - Performance benchmarks
#   - .claude/integration/integration-report.json   - Integration report
#   - .claude/integration/approval.json             - Human approval record
#   - .claude/audit/phase-07-audit.json            - Phase audit results
#   - .claude/closeout/phase-07-closeout.json      - Phase closeout
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
    echo "Phase 7: Integration (E2E Testing + Validation)"
    echo ""
    echo "Usage: ./run.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --resume-at <ID>   Resume from specific task (e.g., --resume-at 703)"
    echo "  --reset-from <ID>  Reset state from task, run from there"
    echo "  --redo             Force re-run of all tasks (ignore completion state)"
    echo "  --clear            Clear all task state, start fresh"
    echo "  --status           Show task completion status and exit"
    echo "  --skip-intro       Skip the intro animation"
    echo "  -h, --help         Show this help"
    echo ""
    echo "Examples:"
    echo "  ./run.sh                    # Normal run (resumes from last completed)"
    echo "  ./run.sh --resume-at 704    # Start from task 704"
    echo "  ./run.sh --reset-from 705   # Reset tasks 705+ and run from 705"
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

    phase_start "7-integration" "Integration"

    # ===================================================================
    # ENTRY & INITIALIZATION
    # ===================================================================

    # Task 701: Entry & Initialization
    phase_task_interactive "701" "Entry & Initialization" task_701_entry_initialization
    local result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 702: Integration Setup
    phase_task_interactive "702" "Integration Setup" task_702_integration_setup
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ===================================================================
    # INTEGRATION TESTING
    # ===================================================================

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  INTEGRATION TESTING${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 703: Agent Selection
    phase_task_interactive "703" "Agent Selection" task_703_agent_selection
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 704: Testing Execution
    phase_task_interactive "704" "Testing Execution" task_704_testing_execution
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 705: Integration Approval (Human Gate)
    phase_task_interactive "705" "Integration Approval" task_705_integration_approval
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ===================================================================
    # PHASE AUDIT & CLOSEOUT
    # ===================================================================

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  PHASE AUDIT & CLOSEOUT${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 706: Phase Audit
    phase_task_interactive "706" "Phase Audit" task_706_phase_audit
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 707: Closeout
    phase_task_interactive "707" "Closeout" task_707_closeout
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    phase_complete

    # Chain to Phase 8: Deployment Prep
    phase_chain "7" "$ROOT_DIR/phases/8-deployment-prep/run.sh" "Deployment Prep"

    return 0
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
