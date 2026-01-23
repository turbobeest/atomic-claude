#!/bin/bash
#
# PHASE 1: DISCOVERY
# Ideation + Technical Research + Agent Planning
#
# Tasks: 101-110 (1xx range)
#
# This phase transforms raw project materials into a validated
# technical approach with agent roster for the pipeline.
#
# ═══════════════════════════════════════════════════════════════════
# PHASE STRUCTURE (Tasks 101-110)
# ═══════════════════════════════════════════════════════════════════
#
# Conversations:
#   1. Corpus Collection - gather all project materials
#   2. Opening Dialogue - understand vision and constraints
#   3. Agent Selection - choose agents for the pipeline
#
# Then:
#   - Discovery Work - multi-agent deliberation on approaches
#   - Approach Selection - human confirms direction (GATE)
#   - Discovery Diagrams - generate architecture diagrams (DOT/SVG)
#   - Phase Audit - independent review of outputs
#   - Closeout - prepare for Phase 2 (PRD)
#
# Note: Custom agents can be created in the agent repository.
# Users are reminded of this option during agent selection.
#
# Artifacts produced:
#   - corpus.json                 - Collected materials
#   - docs/corpus/CORPUS-INDEX.md - Organized corpus
#   - dialogue.json               - Opening dialogue capture
#   - selected-agents.json        - Agents for pipeline
#   - approaches.json             - Generated approaches
#   - first-principles.json       - First principles analysis
#   - selected-approach.json      - Human-selected approach
#   - direction-confirmed.json    - Confirmed project direction
#   - deliberation-log.json       - Multi-agent discussion log
#   - docs/diagrams/*.dot         - Architecture diagrams (DOT)
#   - docs/diagrams/*.svg         - Architecture diagrams (SVG)
#   - phase-01-audit.json         - Phase audit results
#   - phase-01-closeout.json      - Phase closeout
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
    echo "Phase 1: Discovery (Ideation + Technical Research)"
    echo ""
    echo "Usage: ./run.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --resume-at <ID>   Resume from specific task (e.g., --resume-at 105)"
    echo "  --reset-from <ID>  Reset state from task, run from there"
    echo "  --redo             Force re-run of all tasks (ignore completion state)"
    echo "  --clear            Clear all task state, start fresh"
    echo "  --status           Show task completion status and exit"
    echo "  --skip-intro       Skip the intro animation"
    echo "  -h, --help         Show this help"
    echo ""
    echo "Examples:"
    echo "  ./run.sh                    # Normal run (resumes from last completed)"
    echo "  ./run.sh --resume-at 106    # Start from task 106"
    echo "  ./run.sh --reset-from 105   # Reset tasks 105+ and run from 105"
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

    phase_start "1-discovery" "Discovery"

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE ENTRY
    # ═══════════════════════════════════════════════════════════════════════════

    # Task 101: Entry Validation
    phase_task_interactive "101" "Entry Validation" task_101_entry_validation
    local result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ═══════════════════════════════════════════════════════════════════════════
    # CONVERSATION 1: CORPUS COLLECTION
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  CONVERSATION 1: CORPUS COLLECTION${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 102: Corpus Collection
    phase_task_interactive "102" "Corpus Collection" task_102_corpus_collection
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 103: Import Existing Requirements (Optional)
    phase_task_interactive "103" "Import Requirements" task_103_import_requirements
    # Don't abort on failure - this is optional

    # ═══════════════════════════════════════════════════════════════════════════
    # CONVERSATION 2: OPENING DIALOGUE
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  CONVERSATION 2: OPENING DIALOGUE${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 104: Opening Dialogue
    phase_task_interactive "104" "Opening Dialogue" task_104_opening_dialogue
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

    # Task 105: Agent Selection
    phase_task_interactive "105" "Agent Selection" task_105_agent_selection
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ═══════════════════════════════════════════════════════════════════════════
    # DISCOVERY WORK
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  DISCOVERY WORK${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 106: Discovery Work
    phase_task_interactive "106" "Discovery Work" task_106_discovery_work
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ═══════════════════════════════════════════════════════════════════════════
    # HUMAN GATE: APPROACH SELECTION
    # ═══════════════════════════════════════════════════════════════════════════

    # Task 107: Approach Selection (Human Gate)
    phase_task_interactive "107" "Approach Selection" task_107_approach_selection
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # ═══════════════════════════════════════════════════════════════════════════
    # DISCOVERY DIAGRAMS
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  DISCOVERY DIAGRAMS${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Task 108: Discovery Diagrams
    phase_task_interactive "108" "Discovery Diagrams" task_108_discovery_diagrams
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

    # Task 109: Phase Audit
    phase_task_interactive "109" "Phase Audit" task_109_phase_audit
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

    # Task 110: Closeout
    phase_task_interactive "110" "Closeout" task_110_closeout
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Mark phase complete in task state
    task_state_phase_complete

    phase_complete

    # Chain to Phase 2
    phase_chain "1" "$ROOT_DIR/phases/2-prd/run.sh" "PRD"
}

main "$@"
