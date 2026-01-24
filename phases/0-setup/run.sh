#!/bin/bash
#
# PHASE 0: SETUP
# Configuration via Initialization Files, Guided Setup, or Quick Defaults
#
# Tasks: 001-009 (0xx range)
#
# Three modes:
#   DOCUMENT MODE: Parse initialization/ files, Claude extracts config (1 LLM task)
#   GUIDED MODE:   Answer questions one by one (deterministic)
#   QUICK MODE:    Use sensible defaults for greenfield projects
#
# Initialization files (in initialization/ directory):
#   setup.md       - Project configuration
#   agent-plan.md  - Agent assignments per phase
#   audit-plan.md  - Audit profiles and overrides
#
# CLI Flags:
#   --mode=document|guided|quick   Skip mode selection, use specified mode
#   --skip-intro                   Skip the WarGames intro animation
#
# Navigation: After each task, you can:
#   [c] Continue    - proceed to next task
#   [r] Redo        - run this task again
#   [b] Go back     - return to previous task
#   [q] Quit        - abort the phase
#

set -euo pipefail

PHASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$PHASE_DIR/../.." && pwd)"

# Source libraries
source "$ROOT_DIR/lib/phase.sh"
source "$ROOT_DIR/lib/intro.sh"

# ============================================================================
# GLOBAL STATE (shared across tasks)
# ============================================================================

SETUP_MODE=""           # "guided", "document", or "quick"
SETUP_MODE_OVERRIDE=""  # Set via --mode= CLI flag
SETUP_FILE_PATH=""      # Path to setup.md file (document mode)

# ============================================================================
# LOAD TASKS
# ============================================================================

for task_file in "$PHASE_DIR/tasks/"*.sh; do
    if [[ -f "$task_file" ]]; then
        source "$task_file"
    fi
done

# ============================================================================
# MAIN WORKFLOW
# ============================================================================

main() {
    # Parse CLI flags
    local skip_intro=false
    for arg in "$@"; do
        case "$arg" in
            --skip-intro)
                skip_intro=true
                ;;
            --mode=*)
                SETUP_MODE_OVERRIDE="${arg#*=}"
                ;;
        esac
    done

    # Show the WarGames-style intro
    if ! $skip_intro; then
        wopr_intro
    fi

    phase_start "0-setup" "Setup"

    echo ""
    echo -e "${DIM}Navigation: After each task you can:${NC}"
    echo -e "${DIM}  [c] Continue  [r] Redo  [b] Go back  [q] Quit${NC}"
    echo ""

    # Task 001: Mode Selection
    phase_task_interactive "001" "Mode Selection" task_001_mode_selection
    local result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 002: Config Collection (branches based on mode)
    phase_task_interactive "002" "Config Collection" task_002_config_collection
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 003: Config Review
    phase_task_interactive "003" "Config Review" task_003_config_review
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 004: API Keys
    phase_task_interactive "004" "API Keys" task_004_api_keys
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 005: Material Scan
    phase_task_interactive "005" "Material Scan" task_005_material_scan
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 006: Reference Materials (guide user to gather enriching materials)
    phase_task_interactive "006" "Reference Materials" task_006_reference_materials
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 007: Environment Setup (list dependencies, install instructions)
    phase_task_interactive "007" "Environment Setup" task_007_environment_setup
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 008: Repository Setup (agents + audits + Ollama)
    phase_task_interactive "008" "Repository Setup" task_008_repository_setup
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Task 009: Environment Check (validate installations + agents)
    phase_task_interactive "009" "Environment Check" task_009_environment_check
    result=$?
    [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }

    # Final summary
    echo ""
    atomic_header "Configuration Summary"
    echo ""

    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"
    if [[ -f "$config_file" ]]; then
        local project_name=$(jq -r '.project.name // "unknown"' "$config_file")
        local project_type=$(jq -r '.project.type // "unknown"' "$config_file")
        local pipeline_mode=$(jq -r '.pipeline.mode // "unknown"' "$config_file")
        local llm_provider=$(jq -r '.llm.primary_provider // "unknown"' "$config_file")

        echo -e "  Project:  ${BOLD}$project_name${NC} ($project_type)"
        echo -e "  Pipeline: $pipeline_mode"
        echo -e "  Provider: $llm_provider"
        echo ""
    fi

    phase_complete

    # Chain to Phase 1
    phase_chain "0" "$ROOT_DIR/phases/1-discovery/run.sh" "Discovery"
}

main "$@"
