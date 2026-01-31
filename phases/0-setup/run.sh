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
# BOOTSTRAP
# ============================================================================

# Create required directories and templates for a new project
_bootstrap_project_structure() {
    local dirs=(
        "$ATOMIC_ROOT/.claude"
        "$ATOMIC_ROOT/.outputs"
        "$ATOMIC_ROOT/.state"
        "$ATOMIC_ROOT/.logs"
        "$ATOMIC_ROOT/initialization"
        "$ATOMIC_ROOT/docs"
    )

    for dir in "${dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
        fi
    done

    # Create .gitignore for sensitive directories if not exists
    local gitignore="$ATOMIC_ROOT/.gitignore"
    if [[ ! -f "$gitignore" ]]; then
        cat > "$gitignore" << 'GITIGNORE'
# ATOMIC CLAUDE generated
.outputs/*/secrets.json
.state/
.logs/
*.log
__pycache__/
GITIGNORE
    fi
}

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

    # Bootstrap project structure (creates directories and templates)
    _bootstrap_project_structure

    # Show the WarGames-style intro (only on fresh start)
    if ! $skip_intro; then
        wopr_intro
    fi

    phase_start "0-setup" "Setup"

    echo ""
    echo -e "${DIM}Navigation: After each task you can:${NC}"
    echo -e "${DIM}  [c] Continue  [r] Redo  [b] Go back  [q] Quit${NC}"
    echo ""

    # Task definitions: ID, Name, Function
    local task_ids=("001" "002" "003" "004" "005" "006" "007" "008" "009")
    local task_names=(
        "Mode Selection"
        "Config Collection"
        "Config Review"
        "API Keys"
        "Material Scan"
        "Reference Materials"
        "Environment Setup"
        "Repository Setup"
        "Environment Check"
    )
    local task_funcs=(
        "task_001_mode_selection"
        "task_002_config_collection"
        "task_003_config_review"
        "task_004_api_keys"
        "task_005_material_scan"
        "task_006_reference_materials"
        "task_007_environment_setup"
        "task_008_repository_setup"
        "task_009_environment_check"
    )

    # Determine starting index (for --task= resume)
    local i=0
    if [[ -n "$start_task" ]]; then
        for idx in "${!task_ids[@]}"; do
            if [[ "${task_ids[$idx]}" == "$start_task" ]]; then
                i=$idx
                break
            fi
        done
        # Restore state for skipped tasks
        if [[ $i -gt 0 ]]; then
            local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"
            if [[ -f "$config_file" ]]; then
                SETUP_MODE=$(jq -r '.setup_mode // "document"' "$config_file")
                atomic_info "Restored mode from previous run: $SETUP_MODE"
            fi
        fi
    fi

    local total=${#task_ids[@]}

    # Main task loop with navigation support
    while [[ $i -lt $total ]]; do
        local task_id="${task_ids[$i]}"
        local task_name="${task_names[$i]}"
        local task_func="${task_funcs[$i]}"

        # Ensure SETUP_MODE is set before Task 002+ (restore from config if needed)
        if [[ $i -ge 1 && -z "$SETUP_MODE" ]]; then
            local config_file="$ATOMIC_OUTPUT_DIR/0-setup/project-config.json"
            if [[ -f "$config_file" ]]; then
                SETUP_MODE=$(jq -r '.setup_mode // "document"' "$config_file")
                atomic_info "Restored setup mode: $SETUP_MODE"
            else
                SETUP_MODE="document"
                atomic_warn "No saved config found, defaulting to document mode"
            fi
        fi

        # Run the task with interactive navigation
        phase_task_interactive "$task_id" "$task_name" "$task_func"
        local result=$?

        case $result in
            $TASK_CONTINUE)
                i=$((i + 1))
                ;;
            $TASK_BACK)
                if [[ $i -gt 0 ]]; then
                    i=$((i - 1))
                    # Reset state for the task we're going back to
                    task_state_reset_from "${task_ids[$i]}"
                    # Clear SETUP_MODE if going back to task 001 so it can be re-selected
                    if [[ $i -eq 0 ]]; then
                        SETUP_MODE=""
                    fi
                else
                    atomic_warn "Already at first task"
                fi
                ;;
            $TASK_QUIT)
                atomic_error "Phase aborted"
                exit 1
                ;;
        esac
    done

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
