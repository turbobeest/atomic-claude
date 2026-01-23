#!/bin/bash
#
# PHASE 9: RELEASE
# Production Release + Distribution
#
# Tasks: 901-906 (9xx range)
#
# This is the FINAL PHASE of the ATOMIC CLAUDE pipeline.
# It executes the production release, distributes artifacts,
# and closes out the development cycle.
#
# ===================================================================
# PHASE STRUCTURE (Tasks 901-906)
# ===================================================================
#
# Entry:
#   901 - Entry & Initialization - verify Phase 8 complete, init release
#   902 - Release Setup - configure release targets, validate artifacts
#
# Release:
#   903 - Agent Selection - select release execution agents
#   904 - Release Execution - deploy to production, distribute artifacts
#   905 - Release Confirmation - HUMAN GATE for release verification
#
# Exit:
#   906 - Closeout - FINAL CLOSEOUT (no next phase)
#
# Artifacts produced:
#   - .claude/release/release-manifest.json         - Release manifest
#   - .claude/release/distribution-log.json         - Distribution log
#   - .claude/release/release-notes.md              - Public release notes
#   - .claude/release/confirmation.json             - Human confirmation
#   - .claude/closeout/phase-09-closeout.json       - Final closeout
#   - .claude/closeout/project-complete.json        - Project completion
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
    echo "Phase 9: Release (Production Deployment + Distribution)"
    echo ""
    echo "This is the FINAL PHASE of the ATOMIC CLAUDE pipeline."
    echo ""
    echo "Usage: ./run.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --resume-at <ID>   Resume from specific task (e.g., --resume-at 903)"
    echo "  --reset-from <ID>  Reset state from task, run from there"
    echo "  --redo             Force re-run of all tasks (ignore completion state)"
    echo "  --clear            Clear all task state, start fresh"
    echo "  --status           Show task completion status and exit"
    echo "  --skip-intro       Skip the intro animation"
    echo "  -h, --help         Show this help"
    echo ""
    echo "Examples:"
    echo "  ./run.sh                    # Normal run (resumes from last completed)"
    echo "  ./run.sh --resume-at 904    # Start from task 904"
    echo "  ./run.sh --reset-from 905   # Reset tasks 905+ and run from 905"
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

    phase_start "9-release" "Release"

    # ===================================================================
    # ENTRY & INITIALIZATION
    # ===================================================================

    # Task 901: Entry & Initialization
    phase_task_interactive "901" "Entry & Initialization" task_901_entry_initialization
    local result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 902: Release Setup
    phase_task_interactive "902" "Release Setup" task_902_release_setup
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ===================================================================
    # RELEASE EXECUTION
    # ===================================================================

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  RELEASE EXECUTION${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 903: Agent Selection
    phase_task_interactive "903" "Agent Selection" task_903_agent_selection
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 904: Release Execution
    phase_task_interactive "904" "Release Execution" task_904_release_execution
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 905: Release Confirmation (Human Gate)
    phase_task_interactive "905" "Release Confirmation" task_905_release_confirmation
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ===================================================================
    # FINAL CLOSEOUT
    # ===================================================================

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  FINAL CLOSEOUT${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 906: Closeout (FINAL)
    phase_task_interactive "906" "Final Closeout" task_906_closeout
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    phase_complete

    # ===================================================================
    # PIPELINE COMPLETE
    # ===================================================================

    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                           ║${NC}"
    echo -e "${GREEN}║   ${BOLD}ATOMIC CLAUDE PIPELINE COMPLETE${NC}${GREEN}                        ║${NC}"
    echo -e "${GREEN}║                                                           ║${NC}"
    echo -e "${GREEN}║   All 9 phases successfully executed.                     ║${NC}"
    echo -e "${GREEN}║   Project has been released to production.                ║${NC}"
    echo -e "${GREEN}║                                                           ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    return 0
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
