#!/bin/bash
#
# Task 001: Mode Selection
# Choose between DOCUMENT, GUIDED, or QUICK setup mode
#
# Modes:
#   DOCUMENT - Parse initialization/setup.md, Claude extracts config (1 LLM call)
#   GUIDED   - Interactive Q&A, step by step (deterministic)
#   QUICK    - All defaults for greenfield projects (fastest)
#
# CLI Override:
#   Accepts SETUP_MODE_OVERRIDE from run.sh (set via --mode=X flag)
#

task_001_mode_selection() {
    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"
    local init_dir="$ATOMIC_ROOT/initialization"
    local setup_file="$init_dir/setup.md"
    local orchestrator_template="$ROOT_DIR/initialization/setup.md"

    atomic_step "Setup Mode Selection"

    # Check for CLI override (set by run.sh from --mode= flag)
    if [[ -n "${SETUP_MODE_OVERRIDE:-}" ]]; then
        case "$SETUP_MODE_OVERRIDE" in
            document|guided|quick)
                SETUP_MODE="$SETUP_MODE_OVERRIDE"
                atomic_info "Mode set via CLI: $SETUP_MODE"
                [[ "$SETUP_MODE" == "document" ]] && _001_ensure_setup_template "$setup_file" "$orchestrator_template"
                _001_save_config "$config_file" "$setup_file"
                return 0
                ;;
            *)
                atomic_warn "Invalid --mode value: $SETUP_MODE_OVERRIDE (ignoring)"
                ;;
        esac
    fi

    # Check if setup.md already exists
    local has_setup=false
    [[ -f "$setup_file" ]] && has_setup=true

    # Detect if this looks like a greenfield project
    local is_greenfield=false
    local file_count=0
    while IFS= read -r -d ''; do
        ((file_count++))
    done < <(find "$ATOMIC_ROOT" -maxdepth 1 -type f -print0 2>/dev/null)
    [[ $file_count -lt 5 ]] && is_greenfield=true

    # Determine smart default
    local default_choice="2"  # Guided by default
    if $has_setup; then
        default_choice="1"
    elif $is_greenfield; then
        default_choice="3"
    fi

    # Single consolidated prompt - no separate detection phase
    echo ""
    echo -e "  ${BOLD}How do you want to configure this project?${NC}"
    echo ""
    echo -e "  ${CYAN}1.${NC} ${BOLD}DOCUMENT${NC}  - Fill out initialization/setup.md, then parse"
    if $has_setup; then
        echo -e "     ${GREEN}✓ setup.md exists${NC}"
    else
        echo -e "     ${DIM}Template will be created${NC}"
    fi
    echo -e "  ${CYAN}2.${NC} ${BOLD}GUIDED${NC}    - Interactive Q&A, step by step"
    echo -e "  ${CYAN}3.${NC} ${BOLD}QUICK${NC}     - Sensible defaults, minimal input"
    echo ""

    # Drain any buffered stdin
    while read -t 0.01 -n 1 _discard 2>/dev/null; do :; done

    while true; do
        read -e -p "  Select mode [$default_choice]: " choice || true
        choice=${choice:-$default_choice}

        case "$choice" in
            1|d|D|document|Document|DOCUMENT)
                SETUP_MODE="document"

                # Ensure setup.md template exists
                _001_ensure_setup_template "$setup_file" "$orchestrator_template"

                # Tell user to fill it out
                echo ""
                echo -e "  ${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                echo -e "  ${BOLD}  Fill out your setup file:${NC}"
                echo -e "  ${CYAN}  $setup_file${NC}"
                echo ""
                echo -e "  ${DIM}  This file defines your project configuration.${NC}"
                echo -e "  ${DIM}  Fields marked 'infer' will be extracted from${NC}"
                echo -e "  ${DIM}  your reference materials. Use 'default' for${NC}"
                echo -e "  ${DIM}  recommended values.${NC}"
                echo -e "  ${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                echo ""

                # Drain stdin before prompt
                while read -t 0.01 -n 1 _discard 2>/dev/null; do :; done
                read -e -p "  Press Enter when setup.md is ready... " || true
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
                echo -e "  ${RED}Invalid selection. Enter 1, 2, or 3.${NC}"
                ;;
        esac
    done

    _001_save_config "$config_file" "$setup_file"
    return 0
}

# Ensure setup.md template exists, create from orchestrator template if not
_001_ensure_setup_template() {
    local target_file="$1"
    local template_file="$2"

    if [[ -f "$target_file" ]]; then
        return 0
    fi

    mkdir -p "$(dirname "$target_file")"

    if [[ -f "$template_file" ]]; then
        cp "$template_file" "$target_file"
        echo -e "  ${GREEN}✓${NC} Created setup template: $target_file"
    else
        # Fallback minimal template if orchestrator template missing
        cat > "$target_file" << 'TEMPLATE'
# Project Setup
# =============
# Fill in the fields below. Use "infer" to let Claude extract from reference
# materials, "default" for recommended values, or enter a specific value.

## Project Name
infer

## Description
infer

## Project Type
# Options: new-component | new-api | new-cli | new-library | existing | migration
default

## Primary Goal
infer

## Technical Constraints
infer

## Infrastructure Context
infer

# See the full template at:
# https://github.com/turbobeest/atomic-claude/blob/main/initialization/setup.md
TEMPLATE
        echo -e "  ${GREEN}✓${NC} Created minimal setup template: $target_file"
    fi
}

# Helper: Save config and record decision
_001_save_config() {
    local config_file="$1"
    local setup_file="$2"

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

    # Store setup file path if it exists (for Task 002)
    if [[ -f "$setup_file" ]]; then
        SETUP_FILE_PATH="$setup_file"
        atomic_context_decision "Setup file: $SETUP_FILE_PATH" "detection"
    fi

    atomic_success "Setup mode: $SETUP_MODE"
}
