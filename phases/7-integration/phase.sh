#!/bin/bash
#
# Phase 7: Integration
# System Integration + E2E Validation
#

PHASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source all tasks
source "$PHASE_DIR/tasks/701-entry-initialization.sh"
source "$PHASE_DIR/tasks/702-integration-setup.sh"
source "$PHASE_DIR/tasks/703-agent-selection.sh"
source "$PHASE_DIR/tasks/704-testing-execution.sh"
source "$PHASE_DIR/tasks/705-integration-approval.sh"
source "$PHASE_DIR/tasks/706-phase-audit.sh"
source "$PHASE_DIR/tasks/707-closeout.sh"

phase_7_integration() {
    export CURRENT_PHASE=7
    export CURRENT_PHASE_NAME="Integration"

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # PHASE BANNER
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    clear
    echo ""
    echo -e "${CYAN}"
    cat << 'EOF'
 ___ _  _ _____ ___  ___ ___    _ _____ ___ ___  _  _
|_ _| \| |_   _| __\/ __| _ \  /_\_   _|_ _/ _ \| \| |
 | || .` | | | | _| | (_ |   / / _ \| |  | | (_) | .` |
|___|_|\_| |_| |___|\___\_|_\/_/ \_\_| |___\___/|_|\_|
EOF
    echo -e "${NC}"
    echo ""
    echo -e "  ${DIM}System Integration + E2E Validation${NC}"
    echo ""
    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # TASK EXECUTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    # Task 701: Entry & Initialization
    task_701_entry_initialization || return 1

    # Task 702: Integration Setup
    task_702_integration_setup || return 1

    # Task 703: Agent Selection
    task_703_agent_selection || return 1

    # Task 704: Testing Execution
    task_704_testing_execution || return 1

    # Task 705: Integration Approval (Human Gate)
    task_705_integration_approval || return 1

    # Task 706: Phase Audit
    task_706_phase_audit || return 1

    # Task 707: Closeout
    task_707_closeout || return 1

    return 0
}
