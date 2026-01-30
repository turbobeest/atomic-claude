#!/bin/bash
#
# PHASE 3: TASKING
# Break down PRD into implementable tasks
#
# Tasks: 301-306 (3xx range)
#
# This phase transforms the PRD into a structured set of tasks
# with dependencies, complexity scores, and implementation order.
#
# ═══════════════════════════════════════════════════════════════════
# PHASE STRUCTURE (Tasks 301-306)
# ═══════════════════════════════════════════════════════════════════
#
# Entry:
#   301 - Entry & Initialization - verify Phase 2 artifacts, init TaskMaster
#   302 - Agent Selection - analyze PRD, select decomposition agents
#
# Decomposition:
#   303 - Task Decomposition - break PRD into TaskMaster tasks
#   304 - Dependency Analysis - validate DAG, visualize execution levels, generate work packages
#
# Exit:
#   305 - Phase Audit - user-guided quality audit (loop-until-pass)
#   306 - Closeout - prepare for Phase 4 (Specification)
#
# Artifacts produced:
#   - .taskmaster/tasks/tasks.json       - TaskMaster task definitions
#   - .taskmaster/reports/work-packages.json - Grouped work packages
#   - .taskmaster/reports/dependency-graph.json - Task dependencies (DAG)
#   - phase-03-audit.json                - Phase audit results
#   - phase-03-closeout.json             - Phase closeout
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
    echo "Phase 3: Tasking (PRD → Tasks)"
    echo ""
    echo "Usage: ./run.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --resume-at <ID>   Resume from specific task (e.g., --resume-at 305)"
    echo "  --reset-from <ID>  Reset state from task, run from there"
    echo "  --redo             Force re-run of all tasks (ignore completion state)"
    echo "  --clear            Clear all task state, start fresh"
    echo "  --status           Show task completion status and exit"
    echo "  --skip-intro       Skip the intro animation"
    echo "  -h, --help         Show this help"
    echo ""
    echo "Examples:"
    echo "  ./run.sh                    # Normal run (resumes from last completed)"
    echo "  ./run.sh --resume-at 305    # Start from task 305"
    echo "  ./run.sh --reset-from 304   # Reset tasks 304+ and run from 304"
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

    phase_start "3-tasking" "Tasking"

    # ═══════════════════════════════════════════════════════════════════════════
    # ENTRY & INITIALIZATION
    # ═══════════════════════════════════════════════════════════════════════════

    # Task 301: Entry & Initialization
    phase_task_interactive "301" "Entry & Initialization" task_301_entry_initialization
    local result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 302: Agent Selection
    phase_task_interactive "302" "Agent Selection" task_302_agent_selection
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ═══════════════════════════════════════════════════════════════════════════
    # TASK DECOMPOSITION
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  TASK DECOMPOSITION${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 303: Task Decomposition (main work)
    phase_task_interactive "303" "Task Decomposition" task_303_task_decomposition
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ═══════════════════════════════════════════════════════════════════════════
    # DEPENDENCY ANALYSIS & WORK PACKAGES
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  DEPENDENCY ANALYSIS & WORK PACKAGES${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 304: Dependency Analysis (DAG validation, execution levels, work packages)
    phase_task_interactive "304" "Dependency Analysis" task_304_dependency_analysis
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

    # Task 305: Phase Audit (user-guided quality audit, loop-until-pass)
    phase_task_interactive "305" "Phase Audit" task_305_phase_audit
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 306: Closeout
    phase_task_interactive "306" "Closeout" task_306_closeout
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    phase_complete

    # Chain to Phase 4: Specification
    phase_chain "3" "$ROOT_DIR/phases/4-specification/run.sh" "Specification"

    return 0
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
