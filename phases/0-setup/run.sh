#!/usr/bin/env bash
#
# PHASE 0: SETUP
# Configuration via initialization/setup.md (single path forward)
#
# Tasks: 001-009 (0xx range)
#
# Setup Process:
#   1. Validates that initialization/setup.md exists (creates template if not)
#   2. Parses setup.md with Claude to extract configuration
#   3. Collects API keys and configures environment
#   4. Scans reference materials and validates repository
#
# Required file:
#   initialization/setup.md - Project configuration (ground truth for all settings)
#
# Optional files:
#   initialization/agent-plan.md  - Agent assignments per phase
#   initialization/audit-plan.md  - Audit profiles and overrides
#
# CLI Flags:
#   --task=NNN       Resume from a specific task (skips intro)
#   --skip-intro     Skip the WarGames intro animation
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

SETUP_FILE_PATH=""      # Path to setup.md file

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

    # Auto-start tasks dashboard (silent mode)
    
    atomic_start_dashboard true

    echo ""
    echo -e "${DIM}Navigation: After each task you can:${NC}"
    echo -e "${DIM}  [c] Continue  [r] Redo  [b] Go back  [q] Quit${NC}"
    echo ""

    # Task definitions: ID, Name, Function
    local task_ids=("001" "002" "003" "004" "005" "006" "007" "008" "009")
    local task_names=(
        "Setup File Validation"
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
        "task_001_setup_validation"
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
        # Restore setup file path for skipped tasks
        if [[ $i -gt 0 ]]; then
            local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"
            if [[ -f "$config_file" ]]; then
                SETUP_FILE_PATH=$(jq -r '.setup_file // ""' "$config_file")
                if [[ -n "$SETUP_FILE_PATH" ]]; then
                    atomic_info "Restored setup file path: $SETUP_FILE_PATH"
                fi
            fi
        fi
    fi

    local total=${#task_ids[@]}

    # Main task loop with navigation support
    while [[ $i -lt $total ]]; do
        local task_id="${task_ids[$i]}"
        local task_name="${task_names[$i]}"
        local task_func="${task_funcs[$i]}"

        # Ensure SETUP_FILE_PATH is set before Task 002+ (restore from config if needed)
        if [[ $i -ge 1 && -z "$SETUP_FILE_PATH" ]]; then
            local config_file="$ATOMIC_OUTPUT_DIR/0-setup/project-config.json"
            if [[ -f "$config_file" ]]; then
                SETUP_FILE_PATH=$(jq -r '.setup_file // ""' "$config_file")
                if [[ -n "$SETUP_FILE_PATH" ]]; then
                    atomic_info "Restored setup file path: $SETUP_FILE_PATH"
                fi
            fi
        fi

        # Run the task with interactive navigation
        # Note: Must capture exit code without triggering set -e on non-zero returns
        local result=0
        phase_task_interactive "$task_id" "$task_name" "$task_func" || result=$?

        case $result in
            $TASK_CONTINUE)
                i=$((i + 1))
                ;;
            $TASK_BACK)
                if [[ $i -gt 0 ]]; then
                    i=$((i - 1))
                    # Reset state for the task we're going back to
                    task_state_reset_from "${task_ids[$i]}"
                    # Clear SETUP_FILE_PATH if going back to task 001 so it can be re-validated
                    if [[ $i -eq 0 ]]; then
                        SETUP_FILE_PATH=""
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
