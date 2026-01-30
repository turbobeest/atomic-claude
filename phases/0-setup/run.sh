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
#   --task=NNN                     Resume from a specific task (skips intro)
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
    local start_task=""
    for arg in "$@"; do
        case "$arg" in
            --skip-intro)
                skip_intro=true
                ;;
            --mode=*)
                SETUP_MODE_OVERRIDE="${arg#*=}"
                ;;
            --task=*)
                start_task="${arg#*=}"
                # Resuming from a specific task implies skip intro
                skip_intro=true
                ;;
        esac
    done

    # Show the WarGames-style intro (only on fresh start)
    if ! $skip_intro; then
        wopr_intro
    fi

    phase_start "0-setup" "Setup"

    echo ""
    echo -e "${DIM}Navigation: After each task you can:${NC}"
    echo -e "${DIM}  [c] Continue  [r] Redo  [b] Go back  [q] Quit${NC}"
    echo ""

    # When resuming, skip tasks before the requested start task
    local skipping=false
    [[ -n "$start_task" ]] && skipping=true

    # Task 001: Mode Selection
    if $skipping && [[ "$start_task" != "001" ]]; then
        atomic_info "Skipping Task 001 (Mode Selection)"
        # Restore state from previous run
        local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"
        if [[ -f "$config_file" ]]; then
            SETUP_MODE=$(jq -r '.setup_mode // "document"' "$config_file")
            atomic_info "Restored mode: $SETUP_MODE"
        fi
    else
        skipping=false
        phase_task_interactive "001" "Mode Selection" task_001_mode_selection
        local result=$?
        [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }
    fi

    # Ensure SETUP_MODE is set before Task 002 (restores from config if skipped/resumed)
    if [[ -z "$SETUP_MODE" ]]; then
        local config_file="$ATOMIC_OUTPUT_DIR/0-setup/project-config.json"
        if [[ -f "$config_file" ]]; then
            SETUP_MODE=$(jq -r '.setup_mode // "document"' "$config_file")
            atomic_info "Restored setup mode: $SETUP_MODE"
        else
            SETUP_MODE="document"
            atomic_warn "No saved config found, defaulting to document mode"
        fi
    fi

    # Task 002: Config Collection (branches based on mode)
    if $skipping && [[ "$start_task" != "002" ]]; then
        atomic_info "Skipping Task 002 (Config Collection)"
    else
        skipping=false
        phase_task_interactive "002" "Config Collection" task_002_config_collection
        local result=$?
        [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }
    fi

    # Task 003: Config Review
    if $skipping && [[ "$start_task" != "003" ]]; then
        atomic_info "Skipping Task 003 (Config Review)"
    else
        skipping=false
        phase_task_interactive "003" "Config Review" task_003_config_review
        local result=$?
        [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }
    fi

    # Task 004: API Keys
    if $skipping && [[ "$start_task" != "004" ]]; then
        atomic_info "Skipping Task 004 (API Keys)"
    else
        skipping=false
        phase_task_interactive "004" "API Keys" task_004_api_keys
        local result=$?
        [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }
    fi

    # Task 005: Material Scan
    if $skipping && [[ "$start_task" != "005" ]]; then
        atomic_info "Skipping Task 005 (Material Scan)"
    else
        skipping=false
        phase_task_interactive "005" "Material Scan" task_005_material_scan
        local result=$?
        [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }
    fi

    # Task 006: Reference Materials (guide user to gather enriching materials)
    if $skipping && [[ "$start_task" != "006" ]]; then
        atomic_info "Skipping Task 006 (Reference Materials)"
    else
        skipping=false
        phase_task_interactive "006" "Reference Materials" task_006_reference_materials
        local result=$?
        [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }
    fi

    # Task 007: Environment Setup (list dependencies, install instructions)
    if $skipping && [[ "$start_task" != "007" ]]; then
        atomic_info "Skipping Task 007 (Environment Setup)"
    else
        skipping=false
        phase_task_interactive "007" "Environment Setup" task_007_environment_setup
        local result=$?
        [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }
    fi

    # Task 008: Repository Setup (agents + audits + Ollama)
    if $skipping && [[ "$start_task" != "008" ]]; then
        atomic_info "Skipping Task 008 (Repository Setup)"
    else
        skipping=false
        phase_task_interactive "008" "Repository Setup" task_008_repository_setup
        local result=$?
        [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }
    fi

    # Task 009: Environment Check (validate installations + agents)
    if $skipping && [[ "$start_task" != "009" ]]; then
        atomic_info "Skipping Task 009 (Environment Check)"
    else
        skipping=false
        phase_task_interactive "009" "Environment Check" task_009_environment_check
        local result=$?
        [[ $result -eq $TASK_QUIT ]] && { atomic_error "Phase aborted"; exit 1; }
    fi

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
