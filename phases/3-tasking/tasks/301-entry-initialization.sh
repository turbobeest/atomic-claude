#!/bin/bash
#
# Task 301: Entry & Initialization
# Verify Phase 2 artifacts and initialize TaskMaster structure
#
# Validates:
#   - docs/prd/PRD.md (from Phase 2)
#   - prd-approved.json (PRD approval record)
#   - phase-02-closeout.json (Phase 2 complete)
#
# Initializes:
#   - .taskmaster/ directory structure
#

task_301_entry_initialization() {
    local prd_file="$ATOMIC_ROOT/docs/prd/PRD.md"
    local approval_file="$ATOMIC_OUTPUT_DIR/2-prd/prd-approved.json"
    local closeout_file=$(atomic_find_closeout "2-prd")
    local validation_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/entry-validation.json"
    local taskmaster_dir="$ATOMIC_ROOT/.taskmaster"

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 3 WELCOME
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  PHASE 03 - TASKING${NC}"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}"
    cat << 'EOF'
                          _______ _______ _______ _     _
                             |    |_____| |______ |____/
                             |    |     | ______| |    \_

         ______  _______ _______  _____  _______  _____   _____  _______ _____ _______ _____  _____  __   _
         |     \ |______ |       |     | |  |  | |_____] |     | |______   |      |      |   |     | | \  |
         |_____/ |______ |_____  |_____| |  |  | |       |_____| ______| __|__    |    __|__ |_____| |  \_|
EOF
    echo -e "${NC}"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${DIM}Verifying Phase 2 artifacts and initializing TaskMaster.${NC}"
    echo ""

    local checks_passed=0
    local checks_failed=0
    local checks_warned=0
    local validation_data='{}'

    # ─────────────────────────────────────────────────────────────────────────────
    # PHASE 2 CLOSEOUT
    # ─────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}PHASE 2 CLOSEOUT${NC}"
    echo ""

    if [[ -f "$closeout_file" ]]; then
        local phase2_status=$(jq -r '.status // "unknown"' "$closeout_file")
        if [[ "$phase2_status" == "complete" ]]; then
            echo -e "  ${GREEN}✓${NC} Phase 2 closeout found (status: complete)"
            ((checks_passed++))
            validation_data=$(echo "$validation_data" | jq '.phase2_closeout = "pass"')
        else
            echo -e "  ${YELLOW}!${NC} Phase 2 closeout status: $phase2_status"
            ((checks_warned++))
            validation_data=$(echo "$validation_data" | jq --arg s "$phase2_status" '.phase2_closeout = $s')
        fi
    else
        echo -e "  ${RED}✗${NC} Phase 2 closeout not found"
        echo -e "    ${DIM}Expected: $closeout_file${NC}"
        ((checks_failed++))
        validation_data=$(echo "$validation_data" | jq '.phase2_closeout = "missing"')
    fi
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────
    # PRD DOCUMENT
    # ─────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}PRD DOCUMENT${NC}"
    echo ""

    if [[ -f "$prd_file" ]]; then
        local prd_lines=$(wc -l < "$prd_file")
        echo -e "  ${GREEN}✓${NC} PRD document found ($prd_lines lines)"
        echo -e "    ${DIM}Task decomposition follows PRD-TEMPLATE v3.0 structure${NC}"
        ((checks_passed++))
        validation_data=$(echo "$validation_data" | jq --argjson l "$prd_lines" \
            '.prd_document = {status: "pass", lines: $l}')
    else
        echo -e "  ${RED}✗${NC} PRD document not found"
        echo -e "    ${DIM}Expected: $prd_file${NC}"
        ((checks_failed++))
        validation_data=$(echo "$validation_data" | jq '.prd_document = {status: "missing"}')
    fi
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────
    # PRD APPROVAL
    # ─────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}PRD APPROVAL${NC}"
    echo ""

    if [[ -f "$approval_file" ]]; then
        local approval_status=$(jq -r '.status // "unknown"' "$approval_file")
        local approver=$(jq -r '.approver // "unknown"' "$approval_file")
        local approved_at=$(jq -r '.approved_at // "unknown"' "$approval_file")

        if [[ "$approval_status" == "approved" ]]; then
            echo -e "  ${GREEN}✓${NC} PRD approved"
            echo -e "    ${DIM}Approver: $approver${NC}"
            echo -e "    ${DIM}Date: $approved_at${NC}"
            ((checks_passed++))
            validation_data=$(echo "$validation_data" | jq --arg a "$approver" \
                '.prd_approval = {status: "approved", approver: $a}')
        else
            echo -e "  ${YELLOW}!${NC} PRD approval status: $approval_status"
            ((checks_warned++))
            validation_data=$(echo "$validation_data" | jq --arg s "$approval_status" \
                '.prd_approval = {status: $s}')
        fi
    else
        echo -e "  ${RED}✗${NC} PRD approval record not found"
        echo -e "    ${DIM}Expected: $approval_file${NC}"
        ((checks_failed++))
        validation_data=$(echo "$validation_data" | jq '.prd_approval = {status: "missing"}')
    fi
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────
    # TASKMASTER INITIALIZATION
    # ─────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}TASKMASTER INITIALIZATION${NC}"
    echo ""

    if [[ -d "$taskmaster_dir" ]]; then
        echo -e "  ${GREEN}✓${NC} TaskMaster directory exists"
        echo -e "    ${DIM}$taskmaster_dir${NC}"
    else
        echo -e "  ${DIM}Creating TaskMaster directory structure...${NC}"
        mkdir -p "$taskmaster_dir/tasks"
        mkdir -p "$taskmaster_dir/reports"
        mkdir -p "$taskmaster_dir/history"
        echo -e "  ${GREEN}✓${NC} Created .taskmaster/"
        echo -e "    ${DIM}├── tasks/${NC}"
        echo -e "    ${DIM}├── reports/${NC}"
        echo -e "    ${DIM}└── history/${NC}"
    fi
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────
    # SUMMARY
    # ─────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}SUMMARY${NC}"
    echo ""
    echo -e "    Passed:   ${GREEN}$checks_passed${NC}"
    [[ $checks_warned -gt 0 ]] && echo -e "    Warnings: ${YELLOW}$checks_warned${NC}"
    [[ $checks_failed -gt 0 ]] && echo -e "    Failed:   ${RED}$checks_failed${NC}"
    echo ""

    # Save validation results
    local overall_status="pass"
    [[ $checks_warned -gt 0 ]] && overall_status="warning"
    [[ $checks_failed -gt 0 ]] && overall_status="fail"

    validation_data=$(echo "$validation_data" | jq \
        --arg status "$overall_status" \
        --argjson passed "$checks_passed" \
        --argjson warned "$checks_warned" \
        --argjson failed "$checks_failed" \
        '. + {
            overall_status: $status,
            checks_passed: $passed,
            checks_warned: $warned,
            checks_failed: $failed,
            validated_at: (now | todate)
        }')

    mkdir -p "$(dirname "$validation_file")"
    echo "$validation_data" > "$validation_file"

    atomic_context_artifact "$validation_file" "entry-validation" "Phase 3 entry validation"

    # ─────────────────────────────────────────────────────────────────────────────
    # DECISION POINT
    # ─────────────────────────────────────────────────────────────────────────────

    if [[ $checks_failed -gt 0 ]]; then
        echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
        echo ""
        echo -e "  ${RED}Entry validation failed.${NC}"
        echo ""
        echo -e "    ${YELLOW}continue${NC}  Proceed anyway (not recommended)"
        echo -e "    ${RED}abort${NC}     Return to Phase 2"
        echo ""

    atomic_drain_stdin
        read -e -p "  Choice [abort]: " entry_choice || true
        entry_choice=${entry_choice:-abort}

        if [[ "$entry_choice" != "continue" ]]; then
            atomic_error "Entry validation failed - returning to Phase 2"
            return 1
        fi

        atomic_warn "Proceeding despite failed validation"
        echo ""
    fi

    atomic_success "Entry and initialization complete"

    return 0
}
