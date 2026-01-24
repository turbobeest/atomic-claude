#!/bin/bash
#
# Task 001: Mode Selection
# Choose between DOCUMENT, GUIDED, or QUICK setup mode
#
# Modes:
#   DOCUMENT - Parse initialization/ files, Claude extracts config (1 LLM call)
#   GUIDED   - Interactive Q&A, step by step (deterministic)
#   QUICK    - All defaults for greenfield projects (fastest)
#
# CLI Override:
#   Accepts SETUP_MODE_OVERRIDE from run.sh (set via --mode=X flag)
#

task_001_mode_selection() {
    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"

    atomic_step "Setup Mode Selection"

    # Check for CLI override (set by run.sh from --mode= flag)
    if [[ -n "${SETUP_MODE_OVERRIDE:-}" ]]; then
        case "$SETUP_MODE_OVERRIDE" in
            document|guided|quick)
                SETUP_MODE="$SETUP_MODE_OVERRIDE"
                atomic_info "Mode set via CLI: $SETUP_MODE"
                _001_save_config "$config_file"
                return 0
                ;;
            *)
                atomic_warn "Invalid --mode value: $SETUP_MODE_OVERRIDE (ignoring)"
                ;;
        esac
    fi

    # Auto-detect setup files
    local detected_setup=""
    local init_dir="$ATOMIC_ROOT/initialization"
    local setup_locations=("$init_dir/setup.md" "./initialization/setup.md" "./setup.md" "./manifest.md")
    for loc in "${setup_locations[@]}"; do
        if [[ -f "$loc" ]]; then
            detected_setup="$loc"
            break
        fi
    done

    # Detect if this looks like a greenfield project
    local is_greenfield=false
    local file_count=0
    while IFS= read -r -d ''; do
        ((file_count++))
    done < <(find . -maxdepth 1 -type f -print0 2>/dev/null)
    [[ $file_count -lt 5 ]] && is_greenfield=true

    # Determine smart default
    local default_choice="2"  # Guided by default
    if [[ -n "$detected_setup" ]]; then
        default_choice="1"
    elif $is_greenfield; then
        default_choice="3"
    fi

    # Display consolidated mode selection
    echo ""
    echo -e "  ${BOLD}How do you want to configure this project?${NC}"
    echo ""
    echo -e "  ${CYAN}1.${NC} ${BOLD}DOCUMENT${NC}  - Parse initialization files (1 LLM call)"
    if [[ -n "$detected_setup" ]]; then
        echo -e "     ${DIM}Found: $detected_setup${NC}"
    fi
    echo -e "  ${CYAN}2.${NC} ${BOLD}GUIDED${NC}    - Interactive Q&A, step by step"
    echo -e "  ${CYAN}3.${NC} ${BOLD}QUICK${NC}     - Sensible defaults, minimal input"
    echo ""

    while true; do
        read -p "  Select mode [$default_choice]: " choice
        choice=${choice:-$default_choice}

        case "$choice" in
            1|d|D|document|Document|DOCUMENT)
                SETUP_MODE="document"
                if [[ -z "$detected_setup" ]]; then
                    echo ""
                    atomic_warn "No setup.md detected. You'll be prompted for the path."
                fi
                break
                ;;
            2|g|G|guided|Guided|GUIDED)
                SETUP_MODE="guided"
                break
                ;;
            3|q|Q|quick|Quick|QUICK)
                SETUP_MODE="quick"
                break
                ;;
            *)
                atomic_error "Invalid selection. Enter 1, 2, or 3."
                echo ""
                ;;
        esac
    done

    _001_save_config "$config_file"
    return 0
}

# Helper: Save config and record decision
_001_save_config() {
    local config_file="$1"

    # Initialize config file
    mkdir -p "$(dirname "$config_file")"
    cat > "$config_file" << EOF
{
  "setup_mode": "$SETUP_MODE",
  "created_at": "$(date -Iseconds)"
}
EOF

    # Record decision to context
    atomic_context_decision "Setup mode selected: $SETUP_MODE" "configuration"

    # Store setup file path if detected (for Task 002)
    if [[ -n "${detected_setup:-}" ]]; then
        SETUP_FILE_PATH="$detected_setup"
        atomic_context_decision "Setup file auto-detected: $SETUP_FILE_PATH" "detection"
    fi

    atomic_success "Setup mode: $SETUP_MODE"
}
