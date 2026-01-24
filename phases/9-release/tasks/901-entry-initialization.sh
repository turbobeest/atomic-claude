#!/bin/bash
#
# Task 901: Entry & Initialization
# Validate prerequisites and present phase objectives
#

task_901_entry_initialization() {
    local closeout_file="$ATOMIC_ROOT/.claude/closeout/phase-08-closeout.json"
    local deployment_dir="$ATOMIC_ROOT/.claude/deployment"
    local config_file="$ATOMIC_ROOT/project-config.json"

    echo ""
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  PHASE 09 - RELEASE${NC}"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    atomic_step "Entry & Initialization"

    echo ""
    echo -e "  ${DIM}Validating prerequisites for Release phase.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # PREREQUISITE VALIDATION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- PREREQUISITE VALIDATION${NC}"
    echo ""

    local all_valid=true

    # Check Phase 8 closeout
    if [[ -f "$closeout_file" ]]; then
        local phase_8_status=$(jq -r '.status // "unknown"' "$closeout_file")
        if [[ "$phase_8_status" == "complete" ]]; then
            echo -e "  ${GREEN}[CRIT]${NC} ${GREEN}✓${NC} Phase 8 (Deployment Prep) complete"
        else
            echo -e "  ${RED}[CRIT]${NC} ${RED}✗${NC} Phase 8 not complete (status: $phase_8_status)"
            all_valid=false
        fi
    else
        echo -e "  ${RED}[CRIT]${NC} ${RED}✗${NC} Phase 8 closeout not found"
        all_valid=false
    fi

    # Check changelog
    if [[ -f "$ATOMIC_ROOT/CHANGELOG.md" ]]; then
        echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} CHANGELOG.md present"
    else
        echo -e "  ${YELLOW}[BLCK]${NC} ${YELLOW}!${NC} CHANGELOG.md not found"
    fi

    # Check dist directory
    if [[ -d "$ATOMIC_ROOT/dist" ]]; then
        echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} Distribution artifacts present"
    else
        echo -e "  ${YELLOW}[BLCK]${NC} ${YELLOW}!${NC} dist/ directory not found"
    fi

    # Check project config
    if [[ -f "$config_file" ]]; then
        echo -e "  ${GREEN}[PASS]${NC} ${GREEN}✓${NC} Project configuration found"
    else
        echo -e "  ${YELLOW}[PASS]${NC} ${YELLOW}!${NC} Project configuration not found"
    fi

    echo ""

    if [[ "$all_valid" == false ]]; then
        atomic_warn "Prerequisites not met - cannot proceed"
        return 1
    fi

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # PHASE OBJECTIVES
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- PHASE OBJECTIVES${NC}"
    echo ""

    echo -e "  ${DIM}In this phase, we will:${NC}"
    echo ""
    echo -e "    ${CYAN}1.${NC} Execute release to distribution channels"
    echo -e "    ${CYAN}2.${NC} Create GitHub release with notes"
    echo -e "    ${CYAN}3.${NC} Publish to package registry"
    echo -e "    ${CYAN}4.${NC} Confirm release success"
    echo -e "    ${CYAN}5.${NC} Complete project"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # RELEASE PROCESS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- RELEASE PROCESS${NC}"
    echo ""

    echo -e "  ${DIM}Release follows a sequential workflow:${NC}"
    echo ""
    echo -e "    Setup  →  GitHub Release  →  Package Publish  →  Confirmation"
    echo -e "    ${DIM}(final check)    (create tag)       (registry)        (human gate)${NC}"
    echo ""

    read -p "  Press Enter to continue..."
    echo ""

    atomic_context_decision "Phase 9 entry validated" "entry"
    atomic_success "Entry & Initialization complete"

    return 0
}
