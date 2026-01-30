#!/bin/bash
#
# PHASE 8: DEPLOYMENT PREP
# Release Preparation + Documentation
#
# Tasks: 801-807 (8xx range)
#
# This phase prepares the release artifacts, generates documentation,
# and creates deployment packages ready for production release.
#
# ===================================================================
# PHASE STRUCTURE (Tasks 801-807)
# ===================================================================
#
# Entry:
#   801 - Entry & Initialization - verify Phase 7 complete, init deployment
#   802 - Deployment Setup - configure release environments, prepare packaging
#
# Deployment:
#   803 - Agent Selection - select deployment preparation agents
#   804 - Artifact Generation - build release packages, documentation
#   805 - Phase Audit - verify phase artifacts and quality
#   806 - Deployment Approval - HUMAN GATE for deployment sign-off
#
# Exit:
#   807 - Closeout - prepare for Phase 9 (Release)
#
# Artifacts produced:
#   - .claude/deployment/release-package/           - Release artifacts
#   - .claude/deployment/changelog.md               - Release changelog
#   - .claude/deployment/installation-guide.md      - Installation guide
#   - .claude/deployment/deployment-checklist.json  - Deployment checklist
#   - .claude/deployment/approval.json              - Human approval record
#   - .claude/closeout/phase-08-closeout.json       - Phase closeout
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
    echo "Phase 8: Deployment Prep (Release Artifacts + Documentation)"
    echo ""
    echo "Usage: ./run.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --resume-at <ID>   Resume from specific task (e.g., --resume-at 803)"
    echo "  --reset-from <ID>  Reset state from task, run from there"
    echo "  --redo             Force re-run of all tasks (ignore completion state)"
    echo "  --clear            Clear all task state, start fresh"
    echo "  --status           Show task completion status and exit"
    echo "  --skip-intro       Skip the intro animation"
    echo "  -h, --help         Show this help"
    echo ""
    echo "Examples:"
    echo "  ./run.sh                    # Normal run (resumes from last completed)"
    echo "  ./run.sh --resume-at 804    # Start from task 804"
    echo "  ./run.sh --reset-from 805   # Reset tasks 805+ and run from 805"
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

    phase_start "8-deployment-prep" "Deployment Prep"

    # ===================================================================
    # ENTRY & INITIALIZATION
    # ===================================================================

    # Task 801: Entry & Initialization
    phase_task_interactive "801" "Entry & Initialization" task_801_entry_initialization
    local result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 802: Deployment Setup
    phase_task_interactive "802" "Deployment Setup" task_802_deployment_setup
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ===================================================================
    # ARTIFACT GENERATION
    # ===================================================================

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  ARTIFACT GENERATION${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 803: Agent Selection
    phase_task_interactive "803" "Agent Selection" task_803_agent_selection
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 804: Artifact Generation
    phase_task_interactive "804" "Artifact Generation" task_804_artifact_generation
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ===================================================================
    # APPROVAL
    # ===================================================================

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  APPROVAL${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 805: Phase Audit
    phase_task_interactive "805" "Phase Audit" task_805_phase_audit
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 806: Deployment Approval (Human Gate)
    phase_task_interactive "806" "Deployment Approval" task_806_deployment_approval
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ===================================================================
    # CLOSEOUT
    # ===================================================================

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  PHASE CLOSEOUT${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 807: Closeout
    phase_task_interactive "807" "Closeout" task_807_closeout
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    phase_complete

    # Chain to Phase 9: Release
    phase_chain "8" "$ROOT_DIR/phases/9-release/run.sh" "Release"

    return 0
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
