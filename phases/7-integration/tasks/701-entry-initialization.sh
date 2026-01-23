#!/bin/bash
#
# Task 701: Entry & Initialization
# Validate prerequisites and present phase objectives
#

task_701_entry_initialization() {
    local closeout_file="$ATOMIC_ROOT/.claude/closeout/phase-06-closeout.json"
    local config_file="$ATOMIC_ROOT/project-config.json"

    atomic_step "Entry & Initialization"

    echo ""
    echo -e "  ${DIM}Validating prerequisites for Integration phase.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # PREREQUISITE VALIDATION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- PREREQUISITE VALIDATION${NC}"
    echo ""

    local all_valid=true

    # Check Phase 6 closeout
    if [[ -f "$closeout_file" ]]; then
        local phase_6_status=$(jq -r '.status // "unknown"' "$closeout_file")
        if [[ "$phase_6_status" == "complete" ]]; then
            echo -e "  ${GREEN}[CRIT]${NC} ${GREEN}✓${NC} Phase 6 (Code Review) complete"
        else
            echo -e "  ${RED}[CRIT]${NC} ${RED}✗${NC} Phase 6 not complete (status: $phase_6_status)"
            all_valid=false
        fi
    else
        echo -e "  ${RED}[CRIT]${NC} ${RED}✗${NC} Phase 6 closeout not found"
        all_valid=false
    fi

    # Check for review artifacts
    if [[ -d "$ATOMIC_ROOT/.claude/reviews" ]]; then
        echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} Review artifacts present"
    else
        echo -e "  ${YELLOW}[BLCK]${NC} ${YELLOW}!${NC} Review artifacts not found"
    fi

    # Check project config
    if [[ -f "$config_file" ]]; then
        echo -e "  ${GREEN}[PASS]${NC} ${GREEN}✓${NC} Project configuration found"
    else
        echo -e "  ${YELLOW}[PASS]${NC} ${YELLOW}!${NC} Project configuration not found"
    fi

    # Check for test artifacts from implementation
    if [[ -d "$ATOMIC_ROOT/.claude/testing" ]]; then
        echo -e "  ${GREEN}[PASS]${NC} ${GREEN}✓${NC} Testing artifacts present"
    else
        echo -e "  ${YELLOW}[PASS]${NC} ${YELLOW}!${NC} Testing artifacts not found"
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
    echo -e "    ${CYAN}1.${NC} Integrate all components end-to-end"
    echo -e "    ${CYAN}2.${NC} Run full E2E test suite"
    echo -e "    ${CYAN}3.${NC} Validate all acceptance criteria from PRD"
    echo -e "    ${CYAN}4.${NC} Performance testing against NFRs"
    echo -e "    ${CYAN}5.${NC} Generate comprehensive integration report"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # INTEGRATION PROCESS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- INTEGRATION PROCESS${NC}"
    echo ""

    echo -e "  ${DIM}Integration follows a validation-first approach:${NC}"
    echo ""
    echo -e "    E2E Testing  →  Acceptance  →  Performance  →  Approval"
    echo -e "       ${DIM}(flows)       (criteria)    (benchmarks)     (gate)${NC}"
    echo ""

    read -p "  Press Enter to continue..."
    echo ""

    atomic_context_decision "Phase 7 entry validated" "entry"
    atomic_success "Entry & Initialization complete"

    return 0
}
