#!/bin/bash
#
# Phase 5: TDD Implementation
# Execute RED/GREEN/REFACTOR/VERIFY cycles for all tasks
#

source "$ATOMIC_ROOT/orchestrator/lib/atomic-helpers.sh"

# Load all tasks
source "$ATOMIC_ROOT/phases/5-implementation/tasks/501-entry-initialization.sh"
source "$ATOMIC_ROOT/phases/5-implementation/tasks/502-tdd-setup.sh"
source "$ATOMIC_ROOT/phases/5-implementation/tasks/503-agent-selection.sh"
source "$ATOMIC_ROOT/phases/5-implementation/tasks/504-tdd-execution.sh"
source "$ATOMIC_ROOT/phases/5-implementation/tasks/505-validation.sh"
source "$ATOMIC_ROOT/phases/5-implementation/tasks/506-phase-audit.sh"
source "$ATOMIC_ROOT/phases/5-implementation/tasks/507-closeout.sh"

run_phase_5() {
    export CURRENT_PHASE="5-implementation"

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 5: TDD IMPLEMENTATION
    # ═══════════════════════════════════════════════════════════════════════════

    # Task 501: Entry & Initialization
    task_501_entry_initialization || return 1

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # TDD SETUP
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    # Task 502: TDD Setup
    task_502_tdd_setup || return 1

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # AGENT SELECTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    # Task 503: Agent Selection
    task_503_agent_selection || return 1

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # TDD CYCLE EXECUTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    # Task 504: TDD Execution (RED/GREEN/REFACTOR/VERIFY loops)
    task_504_tdd_execution || return 1

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # VALIDATION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    # Task 505: Final Validation
    task_505_validation || return 1

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # PHASE AUDIT
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    # Task 506: Phase Audit
    task_506_phase_audit || return 1

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # CLOSEOUT
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    # Task 507: Phase Closeout
    task_507_closeout || return 1

    return 0
}

# Execute if run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    run_phase_5
fi
