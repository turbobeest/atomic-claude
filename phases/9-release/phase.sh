#!/bin/bash
#
# Phase 9: Release
# Production Release + Distribution
#

PHASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source all tasks
source "$PHASE_DIR/tasks/901-entry-initialization.sh"
source "$PHASE_DIR/tasks/902-release-setup.sh"
source "$PHASE_DIR/tasks/903-agent-selection.sh"
source "$PHASE_DIR/tasks/904-release-execution.sh"
source "$PHASE_DIR/tasks/905-release-confirmation.sh"
source "$PHASE_DIR/tasks/906-closeout.sh"

phase_9_release() {
    export CURRENT_PHASE=9
    export CURRENT_PHASE_NAME="Release"

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # PHASE BANNER
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    clear
    echo ""
    echo -e "${CYAN}"
    cat << 'EOF'
 ____  _____ _     _____    _    ____  _____
|  _ \| ____| |   | ____|  / \  / ___|| ____|
| |_) |  _| | |   |  _|   / _ \ \___ \|  _|
|  _ <| |___| |___| |___ / ___ \ ___) | |___
|_| \_\_____|_____|_____/_/   \_\____/|_____|
EOF
    echo -e "${NC}"
    echo ""
    echo -e "  ${DIM}Production Release + Distribution${NC}"
    echo ""
    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # TASK EXECUTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    # Task 901: Entry & Initialization
    task_901_entry_initialization || return 1

    # Task 902: Release Setup
    task_902_release_setup || return 1

    # Task 903: Agent Selection
    task_903_agent_selection || return 1

    # Task 904: Release Execution
    task_904_release_execution || return 1

    # Task 905: Release Confirmation (Human Gate)
    task_905_release_confirmation || return 1

    # Task 906: Closeout
    task_906_closeout || return 1

    return 0
}
