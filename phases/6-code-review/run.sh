#!/bin/bash
#
# Phase 6: Code Review
# Comprehensive code review with specialized agents
#
# Tasks:
#   601 - Entry & Initialization
#   602 - Agent Selection
#   603 - Comprehensive Review
#   604 - Refinement
#   605 - Phase Audit
#   606 - Closeout
#

PHASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source all tasks
source "$PHASE_DIR/tasks/601-entry-initialization.sh"
source "$PHASE_DIR/tasks/602-agent-selection.sh"
source "$PHASE_DIR/tasks/603-comprehensive-review.sh"
source "$PHASE_DIR/tasks/604-refinement.sh"
source "$PHASE_DIR/tasks/605-phase-audit.sh"
source "$PHASE_DIR/tasks/606-closeout.sh"

run_phase_6() {
    export CURRENT_PHASE=6
    export PHASE_NAME="Code Review"

    # Task 601: Entry & Initialization
    task_601_entry_initialization || return 1

    # Task 602: Agent Selection
    task_602_agent_selection || return 1

    # Task 603: Comprehensive Review
    task_603_comprehensive_review || return 1

    # Task 604: Refinement
    task_604_refinement || return 1

    # Task 605: Phase Audit
    task_605_phase_audit || return 1

    # Task 606: Closeout
    task_606_closeout || return 1

    return 0
}
