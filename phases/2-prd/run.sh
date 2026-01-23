#!/bin/bash
#
# PHASE 2: PRD
# PRD Authoring + Validation
#
# Tasks: 201-209 (2xx range)
#
# This phase transforms the selected approach from Phase 1 into
# a formal Product Requirements Document (PRD).
#
# ═══════════════════════════════════════════════════════════════════
# PHASE STRUCTURE (Tasks 201-209)
# ═══════════════════════════════════════════════════════════════════
#
# Conversations:
#   1. PRD Setup - recap approach, confirm scope
#   2. PRD Interview - confirmatory stakeholder/requirements discussion
#   3. Agent Selection - choose agents for PRD authoring
#
# Then:
#   - PRD Authoring - multi-agent document creation (15 sections)
#   - PRD Validation - completeness, testability, consistency
#   - PRD Approval - human confirms PRD (GATE)
#   - Phase Audit - independent review of outputs
#   - Closeout - prepare for Phase 3 (Architecture)
#
# Artifacts produced:
#   - prd-setup.json             - Setup decisions
#   - prd-interview.json         - Interview responses
#   - selected-agents.json       - Agents for PRD authoring
#   - docs/prd/PRD.md            - The PRD document (15 sections)
#   - prd-validation.json        - Validation results
#   - prd-approved.json          - Human approval record
#   - phase-02-audit.json        - Phase audit results
#   - phase-02-closeout.json     - Phase closeout
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
    echo "Phase 2: PRD (Product Requirements Document)"
    echo ""
    echo "Usage: ./run.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --resume-at <ID>   Resume from specific task (e.g., --resume-at 205)"
    echo "  --reset-from <ID>  Reset state from task, run from there"
    echo "  --redo             Force re-run of all tasks (ignore completion state)"
    echo "  --clear            Clear all task state, start fresh"
    echo "  --status           Show task completion status and exit"
    echo "  --skip-intro       Skip the intro animation"
    echo "  -h, --help         Show this help"
    echo ""
    echo "Examples:"
    echo "  ./run.sh                    # Normal run (resumes from last completed)"
    echo "  ./run.sh --resume-at 205    # Start from task 205"
    echo "  ./run.sh --reset-from 203   # Reset tasks 203+ and run from 203"
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

    phase_start "2-prd" "PRD"

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE ENTRY
    # ═══════════════════════════════════════════════════════════════════════════

    # Task 201: Entry Validation
    phase_task_interactive "201" "Entry Validation" task_201_entry_validation
    local result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ═══════════════════════════════════════════════════════════════════════════
    # CONVERSATION 1: PRD SETUP
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  CONVERSATION 1: PRD SETUP${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 202: PRD Setup
    phase_task_interactive "202" "PRD Setup" task_202_prd_setup
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ═══════════════════════════════════════════════════════════════════════════
    # CONVERSATION 2: PRD INTERVIEW
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  CONVERSATION 2: PRD INTERVIEW${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 203: PRD Interview
    phase_task_interactive "203" "PRD Interview" task_203_prd_interview
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ═══════════════════════════════════════════════════════════════════════════
    # CONVERSATION 3: AGENT SELECTION
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  CONVERSATION 3: AGENT SELECTION${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 204: Agent Selection
    phase_task_interactive "204" "Agent Selection" task_204_agent_selection
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ═══════════════════════════════════════════════════════════════════════════
    # PRD AUTHORING
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  PRD AUTHORING${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 205: PRD Authoring
    phase_task_interactive "205" "PRD Authoring" task_205_prd_authoring
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ═══════════════════════════════════════════════════════════════════════════
    # PRD VALIDATION
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  PRD VALIDATION${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 206: PRD Validation
    phase_task_interactive "206" "PRD Validation" task_206_prd_validation
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ═══════════════════════════════════════════════════════════════════════════
    # HUMAN GATE: PRD APPROVAL
    # ═══════════════════════════════════════════════════════════════════════════

    # Task 207: PRD Approval (Human Gate)
    phase_task_interactive "207" "PRD Approval" task_207_prd_approval
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE AUDIT
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  PHASE AUDIT${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 208: Phase Audit
    phase_task_interactive "208" "Phase Audit" task_208_phase_audit
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE CLOSEOUT
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  PHASE CLOSEOUT${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 209: Closeout
    phase_task_interactive "209" "Closeout" task_209_closeout
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Mark phase complete in task state
    task_state_phase_complete

    phase_complete

    # Chain to Phase 3
    phase_chain "2" "$ROOT_DIR/phases/3-tasking/run.sh" "Tasking"
}

main "$@"
