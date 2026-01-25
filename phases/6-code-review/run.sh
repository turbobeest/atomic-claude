#!/bin/bash
#
# PHASE 6: CODE REVIEW
# Comprehensive code review with specialized agents
#
# Tasks: 601-606 (6xx range)
#
# This phase performs comprehensive code review using specialized agents
# for deep code analysis, architecture compliance, performance, and documentation.
#
# ═══════════════════════════════════════════════════════════════════
# PHASE STRUCTURE (Tasks 601-606)
# ═══════════════════════════════════════════════════════════════════
#
# Entry:
#   601 - Entry & Initialization - verify Phase 5 complete, init review
#   602 - Agent Selection - select review agents (code, arch, perf, doc)
#
# Review:
#   603 - Comprehensive Review - parallel 4-agent code review
#   604 - Refinement - address findings, apply fixes
#
# Exit:
#   605 - Phase Audit - verify review thoroughness
#   606 - Closeout - prepare for Phase 7 (Integration)
#
# Artifacts produced:
#   - .claude/reviews/findings.json           - Combined review findings
#   - .claude/reviews/refinement-report.json  - Refinement actions taken
#   - .claude/audit/phase-06-audit.json       - Phase audit results
#   - .claude/closeout/phase-06-closeout.json - Phase closeout
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
    echo "Phase 6: Code Review (Comprehensive Multi-Agent Review)"
    echo ""
    echo "Usage: ./run.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --resume-at <ID>   Resume from specific task (e.g., --resume-at 603)"
    echo "  --reset-from <ID>  Reset state from task, run from there"
    echo "  --redo             Force re-run of all tasks (ignore completion state)"
    echo "  --clear            Clear all task state, start fresh"
    echo "  --status           Show task completion status and exit"
    echo "  --skip-intro       Skip the intro animation"
    echo "  -h, --help         Show this help"
    echo ""
    echo "Examples:"
    echo "  ./run.sh                    # Normal run (resumes from last completed)"
    echo "  ./run.sh --resume-at 603    # Start from task 603"
    echo "  ./run.sh --reset-from 604   # Reset tasks 604+ and run from 604"
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

    phase_start "6-code-review" "Code Review"

    # ═══════════════════════════════════════════════════════════════════════════
    # ENTRY & INITIALIZATION
    # ═══════════════════════════════════════════════════════════════════════════

    # Task 601: Entry & Initialization
    phase_task_interactive "601" "Entry & Initialization" task_601_entry_initialization
    local result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 602: Agent Selection
    phase_task_interactive "602" "Agent Selection" task_602_agent_selection
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ═══════════════════════════════════════════════════════════════════════════
    # COMPREHENSIVE REVIEW
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  COMPREHENSIVE REVIEW${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 603: Comprehensive Review (4 parallel agents)
    phase_task_interactive "603" "Comprehensive Review" task_603_comprehensive_review
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ═══════════════════════════════════════════════════════════════════════════
    # REFINEMENT
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  REFINEMENT${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 604: Refinement
    phase_task_interactive "604" "Refinement" task_604_refinement
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

    # Task 605: Phase Audit
    phase_task_interactive "605" "Phase Audit" task_605_phase_audit
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 606: Closeout
    phase_task_interactive "606" "Closeout" task_606_closeout
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    phase_complete

    # Chain to Phase 7: Integration
    phase_chain "6" "$ROOT_DIR/phases/7-integration/run.sh" "Integration"

    return 0
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
