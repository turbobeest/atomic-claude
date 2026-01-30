#!/bin/bash
#
# Task 801: Entry & Initialization
# Validate prerequisites and present phase objectives
#

task_801_entry_initialization() {
    local closeout_file=$(atomic_find_closeout "7-integration")
    local integration_dir="$ATOMIC_ROOT/.claude/integration"
    local config_file="$ATOMIC_OUTPUT_DIR/0-setup/project-config.json"

    echo ""
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  PHASE 08 - DEPLOYMENT PREP${NC}"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    atomic_step "Entry & Initialization"

    echo ""
    echo -e "  ${DIM}Validating prerequisites for Deployment Prep phase.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # PREREQUISITE VALIDATION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- PREREQUISITE VALIDATION${NC}"
    echo ""

    local all_valid=true

    # Check Phase 7 closeout
    if [[ -f "$closeout_file" ]]; then
        local phase_7_status=$(jq -r '.status // "unknown"' "$closeout_file")
        if [[ "$phase_7_status" == "complete" ]]; then
            echo -e "  ${GREEN}[CRIT]${NC} ${GREEN}✓${NC} Phase 7 (Integration) complete"
        else
            echo -e "  ${RED}[CRIT]${NC} ${RED}✗${NC} Phase 7 not complete (status: $phase_7_status)"
            all_valid=false
        fi
    else
        echo -e "  ${RED}[CRIT]${NC} ${RED}✗${NC} Phase 7 closeout not found"
        all_valid=false
    fi

    # Check integration report
    if [[ -f "$integration_dir/integration-report.json" ]]; then
        echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} Integration report present"
    else
        echo -e "  ${YELLOW}[BLCK]${NC} ${YELLOW}!${NC} Integration report not found"
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
    echo -e "    ${CYAN}1.${NC} Prepare deployment artifacts"
    echo -e "    ${CYAN}2.${NC} Generate release documentation"
    echo -e "    ${CYAN}3.${NC} Create installation guides"
    echo -e "    ${CYAN}4.${NC} Prepare changelog"
    echo -e "    ${CYAN}5.${NC} Ready for Release phase"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # DEPLOYMENT PREP PROCESS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- DEPLOYMENT PREP PROCESS${NC}"
    echo ""

    echo -e "  ${DIM}Preparation follows a parallel workflow:${NC}"
    echo ""
    echo -e "    Packaging  →  Changelog  →  Documentation  →  Approval"
    echo -e "      ${DIM}(build)      (version)       (guides)        (gate)${NC}"
    echo ""

    read -e -p "  Press Enter to continue..." || true
    echo ""

    atomic_context_decision "Phase 8 entry validated" "entry"
    atomic_success "Entry & Initialization complete"

    return 0
}
