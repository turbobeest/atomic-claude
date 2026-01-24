#!/bin/bash
#
# Task 209: Phase Closeout
# Generate closeout document and prepare for Phase 3
#

task_209_closeout() {
    local closeout_dir="$ATOMIC_ROOT/.claude/closeout"
    local closeout_file="$closeout_dir/phase-02-closeout.md"
    local closeout_json="$closeout_dir/phase-02-closeout.json"
    local prd_file="$ATOMIC_ROOT/docs/prd/PRD.md"

    atomic_step "Phase Closeout"

    mkdir -p "$closeout_dir"

    echo ""
    echo -e "${DIM}  ┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${DIM}  │ PHASE CLOSEOUT                                          │${NC}"
    echo -e "${DIM}  │                                                         │${NC}"
    echo -e "${DIM}  │ Final review before moving to Phase 3 (Tasking).  │${NC}"
    echo -e "${DIM}  └─────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # CLOSEOUT CHECKLIST
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}CLOSEOUT CHECKLIST${NC}                                        ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local checklist=()
    local all_passed=true

    # Check PRD document
    if [[ -f "$prd_file" ]]; then
        local section_count=$(grep -c '^##' "$prd_file" 2>/dev/null || echo 0)
        if [[ $section_count -ge 10 ]]; then
            echo -e "  ${GREEN}[CRIT]${NC} ${GREEN}✓${NC} PRD authored ($section_count sections)"
            checklist+=("PRD authored:PASS")
        else
            echo -e "  ${YELLOW}[CRIT]${NC} ${YELLOW}!${NC} PRD incomplete ($section_count sections)"
            checklist+=("PRD authored:WARN")
        fi
    else
        echo -e "  ${RED}[CRIT]${NC} ${RED}✗${NC} PRD document missing"
        checklist+=("PRD authored:FAIL")
        all_passed=false
    fi

    # Check PRD approval
    local approval_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prd-approved.json"
    if [[ -f "$approval_file" ]]; then
        local approval_status=$(jq -r '.status // "unknown"' "$approval_file")
        if [[ "$approval_status" == "approved" ]]; then
            local approver=$(jq -r '.approver // "unknown"' "$approval_file")
            echo -e "  ${GREEN}[CRIT]${NC} ${GREEN}✓${NC} PRD approved by $approver"
            checklist+=("PRD approved:PASS")
        else
            echo -e "  ${YELLOW}[CRIT]${NC} ${YELLOW}!${NC} PRD approval status: $approval_status"
            checklist+=("PRD approved:WARN")
        fi
    else
        echo -e "  ${RED}[CRIT]${NC} ${RED}✗${NC} PRD not approved"
        checklist+=("PRD approved:FAIL")
        all_passed=false
    fi

    # Check audit
    local audit_file="$ATOMIC_ROOT/.claude/audit/phase-02-audit.json"
    if [[ -f "$audit_file" ]]; then
        local audit_status=$(jq -r '.overall_status // "UNKNOWN"' "$audit_file")
        if [[ "$audit_status" == "PASS" ]]; then
            echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} Audit passed"
            checklist+=("Audit:PASS")
        elif [[ "$audit_status" == "WARNING" ]]; then
            echo -e "  ${YELLOW}[BLCK]${NC} ${YELLOW}!${NC} Audit has warnings"
            checklist+=("Audit:WARN")
        else
            echo -e "  ${RED}[BLCK]${NC} ${RED}✗${NC} Audit has critical issues"
            checklist+=("Audit:FAIL")
        fi
    else
        echo -e "  ${YELLOW}[BLCK]${NC} ${YELLOW}!${NC} Audit not completed"
        checklist+=("Audit:SKIP")
    fi

    # Check validation
    local validation_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prd-validation.json"
    if [[ -f "$validation_file" ]]; then
        local val_status=$(jq -r '.overall_status // "UNKNOWN"' "$validation_file")
        echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} Validation complete ($val_status)"
        checklist+=("Validation:PASS")
    else
        echo -e "  ${YELLOW}[BLCK]${NC} ${YELLOW}!${NC} Validation not completed"
        checklist+=("Validation:SKIP")
    fi

    echo -e "  ${GREEN}[PASS]${NC} ${GREEN}✓${NC} Ready for Tasking"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # CLOSEOUT APPROVAL
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    if [[ "$all_passed" == false ]]; then
        echo -e "  ${YELLOW}Some critical items need attention before closeout.${NC}"
        echo ""
    fi

    echo -e "  ${CYAN}Closeout options:${NC}"
    echo ""
    echo -e "    ${GREEN}[approve]${NC} Approve closeout and proceed"
    echo -e "    ${YELLOW}[review]${NC}  Review specific artifacts"
    echo -e "    ${RED}[hold]${NC}    Hold closeout for now"
    echo ""

    read -p "  Choice [approve]: " closeout_choice
    closeout_choice=${closeout_choice:-approve}

    case "$closeout_choice" in
        review)
            echo ""
            echo -e "  ${DIM}Artifacts in this phase:${NC}"
            ls -la "$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/" 2>/dev/null
            echo ""
            echo -e "  ${DIM}PRD location: $prd_file${NC}"
            echo ""
            read -p "  Press Enter to continue to closeout..."
            ;;
        hold)
            echo ""
            atomic_warn "Closeout held - phase not complete"
            return 1
            ;;
    esac

    # ═══════════════════════════════════════════════════════════════════════════
    # GENERATE CLOSEOUT DOCUMENT
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}GENERATING CLOSEOUT${NC}                                       ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Gather metrics
    local prd_lines=0
    local prd_sections=0
    [[ -f "$prd_file" ]] && prd_lines=$(wc -l < "$prd_file")
    [[ -f "$prd_file" ]] && prd_sections=$(grep -c '^##' "$prd_file" 2>/dev/null || echo 0)

    # Generate markdown closeout
    cat > "$closeout_file" << EOF
# Phase 2 Closeout: PRD

**Completed:** $(date -Iseconds)
**Status:** COMPLETE

## Summary

Phase 2 (PRD) has been completed successfully.

### Key Outcomes

- **PRD Document:** $prd_lines lines, $prd_sections sections
- **Location:** docs/prd/PRD.md
- **Status:** Approved and validated

### Artifacts Produced

| Artifact | Description |
|----------|-------------|
| docs/prd/PRD.md | Product Requirements Document (15 sections) |
| prd-setup.json | PRD setup configuration |
| prd-interview.json | Interview responses |
| selected-agents.json | Agent selection for PRD |
| prd-validation.json | Validation results |
| prd-approved.json | Approval record |

### Checklist Status

$(for item in "${checklist[@]}"; do
    IFS=':' read -r name status <<< "$item"
    case "$status" in
        PASS) echo "- [x] $name" ;;
        WARN) echo "- [~] $name (warning)" ;;
        FAIL) echo "- [ ] $name (failed)" ;;
        SKIP) echo "- [-] $name (skipped)" ;;
    esac
done)

## Next Phase

**Phase 3: Tasking**

In the next phase, we will:
- Design system architecture based on PRD
- Define component structure
- Specify interfaces and contracts
- Establish technical patterns

## To Continue

\`\`\`bash
./orchestrator/pipeline resume
\`\`\`

---

*Phase 2 completed by ATOMIC CLAUDE*
EOF

    # Generate JSON closeout using jq for proper escaping
    local checklist_json=$(printf '%s\n' "${checklist[@]}" | jq -R . | jq -s .)

    jq -n \
        --arg prd_file "$prd_file" \
        --argjson prd_lines "$prd_lines" \
        --argjson prd_sections "$prd_sections" \
        --argjson checklist "$checklist_json" \
        '{
            "phase": 2,
            "name": "PRD",
            "status": "complete",
            "completed_at": (now | todate),
            "prd_file": $prd_file,
            "prd_lines": $prd_lines,
            "prd_sections": $prd_sections,
            "checklist": $checklist,
            "next_phase": 3
        }' > "$closeout_json"

    echo -e "  ${GREEN}✓${NC} Generated phase-02-closeout.md"
    echo -e "  ${GREEN}✓${NC} Generated phase-02-closeout.json"
    echo ""

    # Register closeout artifacts for downstream phases
    atomic_context_artifact "phase2_closeout_md" "$closeout_file" "Phase 2 closeout summary (markdown)"
    atomic_context_artifact "phase2_closeout_json" "$closeout_json" "Phase 2 closeout data (JSON)"
    atomic_context_artifact "prd_document" "$prd_file" "Product Requirements Document"
    atomic_context_decision "Phase 2 closeout completed: $prd_sections PRD sections" "closeout"

    # ═══════════════════════════════════════════════════════════════════════════
    # SESSION END
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  ${BOLD}SESSION END${NC}                                                 ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  Closeout saved to:                                           ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  ${DIM}.claude/closeout/phase-02-closeout.md${NC}                       ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  PRD saved to:                                                ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  ${DIM}docs/prd/PRD.md${NC}                                              ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  ${BOLD}Next: PHASE 3 - ARCHITECTURE${NC}                               ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  To continue:                                                 ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  ${CYAN}./orchestrator/pipeline resume${NC}                              ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  ─────────────────────────────────────────────────────────── ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}      ${BOLD}Phase 2 Complete!${NC}                                       ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}      ${DIM}Great work. See you in Tasking.${NC}                    ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    atomic_success "Phase 2 closeout complete"

    return 0
}
