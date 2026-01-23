#!/bin/bash
#
# Phase 8: Deployment Prep
# Release Preparation + Documentation
#

PHASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source all tasks
source "$PHASE_DIR/tasks/801-entry-initialization.sh"
source "$PHASE_DIR/tasks/802-deployment-setup.sh"
source "$PHASE_DIR/tasks/803-agent-selection.sh"
source "$PHASE_DIR/tasks/804-artifact-generation.sh"
source "$PHASE_DIR/tasks/805-deployment-approval.sh"
source "$PHASE_DIR/tasks/806-closeout.sh"

phase_8_deployment_prep() {
    export CURRENT_PHASE=8
    export CURRENT_PHASE_NAME="Deployment Prep"

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # PHASE BANNER
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    clear
    echo ""
    echo -e "${CYAN}"
    cat << 'EOF'
 ___  ___ ___ _    _____   ____  ___ ___ ___
|   \| __| _ \ |  / _ \ \ / /  \/  | __| \| |_   _|
| |) | _||  _/ |_| (_) \ V /| |\/| | _|| .` | | |
|___/|___|_| |____\___/ |_| |_|  |_|___|_|\_| |_|
EOF
    echo -e "${NC}"
    echo ""
    echo -e "  ${DIM}Release Preparation + Documentation${NC}"
    echo ""
    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # TASK EXECUTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    # Task 801: Entry & Initialization
    task_801_entry_initialization || return 1

    # Task 802: Deployment Setup
    task_802_deployment_setup || return 1

    # Task 803: Agent Selection
    task_803_agent_selection || return 1

    # Task 804: Artifact Generation
    task_804_artifact_generation || return 1

    # Task 805: Deployment Approval (Human Gate)
    task_805_deployment_approval || return 1

    # Task 806: Closeout
    task_806_closeout || return 1

    return 0
}
