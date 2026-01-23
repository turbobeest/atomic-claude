#!/bin/bash
#
# Task 101: Entry Validation
# Validate Phase 0 completion and load prerequisites
#
# Checks:
#   - phase-00-closeout.md exists
#   - project-config.json is valid
#   - pipeline-state.json shows Phase 0 complete
#

task_101_entry_validation() {
    local setup_dir="$ATOMIC_OUTPUT_DIR/0-setup"
    local closeout_dir="$ATOMIC_ROOT/.claude/closeout"

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 1 WELCOME
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}"
    cat << 'EOF'
 ______  _____ _______ _______  _____  _    _ _______  ______ __   __
 |     \   |   |______ |       |     |  \  /  |______ |_____/   \_/
 |_____/ __|__ ______| |_____  |_____|   \/   |______ |    \_    |
EOF
    echo -e "${NC}"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "                       ${BOLD}[ PHASE 1 OF 10 ]${NC}"
    echo ""

    atomic_step "Entry Validation"

    echo ""
    echo -e "${DIM}  Validating Phase 0 completion...${NC}"
    echo ""

    local validation_passed=true
    local issues=()

    # ═══════════════════════════════════════════════════════════════════════════
    # CHECK 1: Phase 0 Closeout
    # ═══════════════════════════════════════════════════════════════════════════

    local closeout_file="$closeout_dir/phase-00-closeout.md"
    if [[ -f "$closeout_file" ]]; then
        echo -e "  ${GREEN}✓${NC} phase-00-closeout.md found"
    else
        # Try JSON format
        closeout_file="$closeout_dir/phase-00-closeout.json"
        if [[ -f "$closeout_file" ]]; then
            echo -e "  ${GREEN}✓${NC} phase-00-closeout.json found"
        else
            echo -e "  ${RED}✗${NC} Phase 0 closeout not found"
            issues+=("Phase 0 closeout missing - run Phase 0 first")
            validation_passed=false
        fi
    fi

    # ═══════════════════════════════════════════════════════════════════════════
    # CHECK 2: Project Config
    # ═══════════════════════════════════════════════════════════════════════════

    local config_file="$setup_dir/project-config.json"
    if [[ -f "$config_file" ]]; then
        # Validate JSON
        if jq -e . "$config_file" &>/dev/null; then
            echo -e "  ${GREEN}✓${NC} project-config.json valid"

            # Check required fields
            local project_name=$(jq -r '.project.name // empty' "$config_file")
            local project_type=$(jq -r '.project.type // empty' "$config_file")

            if [[ -z "$project_name" ]]; then
                echo -e "  ${YELLOW}!${NC} project.name not set"
                issues+=("Project name not configured")
            fi
        else
            echo -e "  ${RED}✗${NC} project-config.json invalid JSON"
            issues+=("Project config is invalid JSON")
            validation_passed=false
        fi
    else
        echo -e "  ${RED}✗${NC} project-config.json not found"
        issues+=("Project config missing")
        validation_passed=false
    fi

    # ═══════════════════════════════════════════════════════════════════════════
    # CHECK 3: Pipeline State
    # ═══════════════════════════════════════════════════════════════════════════

    local state_file="$ATOMIC_ROOT/.claude/pipeline-state.json"
    if [[ -f "$state_file" ]]; then
        local current_phase=$(jq -r '.current_phase // 0' "$state_file")
        local phase_0_status=$(jq -r '.phases["0"].status // "unknown"' "$state_file")

        if [[ "$phase_0_status" == "completed" ]] || [[ "$current_phase" -ge 1 ]]; then
            echo -e "  ${GREEN}✓${NC} Pipeline state: Phase 0 complete"
        else
            echo -e "  ${YELLOW}!${NC} Pipeline state shows Phase 0 incomplete"
            issues+=("Phase 0 not marked complete in pipeline state")
        fi
    else
        echo -e "  ${YELLOW}!${NC} pipeline-state.json not found (will create)"
    fi

    # ═══════════════════════════════════════════════════════════════════════════
    # VALIDATION RESULT
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""

    if [[ "$validation_passed" == false ]]; then
        echo -e "${RED}╔═══════════════════════════════════════════════════════════╗${NC}"
        echo -e "${RED}║${NC} ${BOLD}VALIDATION FAILED${NC}                                        ${RED}║${NC}"
        echo -e "${RED}╚═══════════════════════════════════════════════════════════╝${NC}"
        echo ""
        for issue in "${issues[@]}"; do
            echo -e "  ${RED}•${NC} $issue"
        done
        echo ""
        atomic_error "Cannot proceed - complete Phase 0 first"
        return 1
    fi

    if [[ ${#issues[@]} -gt 0 ]]; then
        echo -e "${YELLOW}  Warnings:${NC}"
        for issue in "${issues[@]}"; do
            echo -e "  ${YELLOW}•${NC} $issue"
        done
        echo ""
    fi

    # ═══════════════════════════════════════════════════════════════════════════
    # WELCOME MESSAGE
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}    ╔╦╗ ╦ ╔═╗ ╔═╗ ╔═╗ ╦  ╦ ╔═╗ ╦═╗ ╦ ╦${NC}"
    echo -e "${CYAN}     ║║ ║ ╚═╗ ║   ║ ║ ╚╗╔╝ ║╣  ╠╦╝ ╚╦╝${NC}"
    echo -e "${CYAN}    ═╩╝ ╩ ╚═╝ ╚═╝ ╚═╝  ╚╝  ╚═╝ ╩╚═  ╩ ${NC}"
    echo -e "${DIM}    ─────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${DIM}Phase 1${NC}"
    echo ""
    echo -e "  Welcome. This is where your project takes shape."
    echo -e "  We'll explore your vision, gather context, and"
    echo -e "  assemble the right team of agents for the journey."
    echo ""

    # Initialize phase output directory
    mkdir -p "$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE"

    atomic_context_decision "Phase 1 entry validated, starting discovery" "phase_start"
    atomic_success "Entry validation passed"

    return 0
}
