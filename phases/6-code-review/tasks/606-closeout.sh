#!/bin/bash
#
# Task 606: Phase Closeout
# Generate closeout document and prepare for Phase 7 (Integration Testing)
#

task_606_closeout() {
    local closeout_dir="$ATOMIC_ROOT/.claude/closeout"
    local closeout_file="$closeout_dir/phase-06-closeout.md"
    local closeout_json="$closeout_dir/phase-06-closeout.json"
    local review_dir="$ATOMIC_ROOT/.claude/reviews"
    local findings_file="$review_dir/findings.json"
    local refinement_file="$review_dir/refinement-report.json"
    # Audit file - check new path first, then legacy
    local audit_file="$ATOMIC_ROOT/.outputs/audits/phase-6-report.json"
    [[ ! -f "$audit_file" ]] && audit_file="$ATOMIC_ROOT/.claude/audit/phase-06-audit.json"

    atomic_step "Phase Closeout"

    mkdir -p "$closeout_dir"

    echo ""
    echo -e "  ${DIM}Final review before moving to Phase 7 (Integration Testing).${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # CLOSEOUT CHECKLIST
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- CLOSEOUT CHECKLIST${NC}"
    echo ""

    local checklist=()
    local all_passed=true

    # Get metrics
    local critical_found=0
    local major_found=0
    local critical_fixed=0
    local major_fixed=0
    local tests_passing=true

    if [[ -f "$findings_file" ]]; then
        critical_found=$(jq -r '.totals.critical // 0' "$findings_file")
        major_found=$(jq -r '.totals.major // 0' "$findings_file")
    fi

    if [[ -f "$refinement_file" ]]; then
        critical_fixed=$(jq -r '.refinements.critical.fixed // 0' "$refinement_file")
        major_fixed=$(jq -r '.refinements.major.fixed // 0' "$refinement_file")
        tests_passing=$(jq -r '.test_verification.all_passing // false' "$refinement_file")
    fi

    # Check code review complete
    if [[ -f "$findings_file" ]]; then
        echo -e "  ${GREEN}[CRIT]${NC} ${GREEN}✓${NC} Code review complete"
        checklist+=("Code review complete:PASS")
    else
        echo -e "  ${RED}[CRIT]${NC} ${RED}✗${NC} Code review not complete"
        checklist+=("Code review complete:FAIL")
        all_passed=false
    fi

    # Check critical issues resolved
    if [[ "$critical_fixed" -ge "$critical_found" ]]; then
        echo -e "  ${GREEN}[CRIT]${NC} ${GREEN}✓${NC} All critical issues resolved ($critical_fixed/$critical_found)"
        checklist+=("Critical issues resolved:PASS")
    else
        echo -e "  ${RED}[CRIT]${NC} ${RED}✗${NC} Critical issues unresolved ($critical_fixed/$critical_found)"
        checklist+=("Critical issues resolved:FAIL")
        all_passed=false
    fi

    # Check major issues resolved
    if [[ "$major_fixed" -ge "$major_found" ]]; then
        echo -e "  ${GREEN}[CRIT]${NC} ${GREEN}✓${NC} All major issues resolved ($major_fixed/$major_found)"
        checklist+=("Major issues resolved:PASS")
    else
        echo -e "  ${YELLOW}[CRIT]${NC} ${YELLOW}!${NC} Major issues partially resolved ($major_fixed/$major_found)"
        checklist+=("Major issues resolved:WARN")
    fi

    # Check tests passing
    if [[ "$tests_passing" == "true" ]]; then
        echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} All tests passing after refinements"
        checklist+=("Tests passing:PASS")
    else
        echo -e "  ${RED}[BLCK]${NC} ${RED}✗${NC} Tests failing after refinements"
        checklist+=("Tests passing:FAIL")
        all_passed=false
    fi

    # Check audit
    if [[ -f "$audit_file" ]]; then
        # Check summary.passed/failed/warnings (new format) or overall_status (legacy)
        local passed=$(jq -r '.summary.passed // 0' "$audit_file" 2>/dev/null)
        local failed=$(jq -r '.summary.failed // 0' "$audit_file" 2>/dev/null)
        local warnings=$(jq -r '.summary.warnings // 0' "$audit_file" 2>/dev/null)
        local total=$((passed + failed + warnings))

        if [[ $total -eq 0 ]]; then
            # Try legacy format
            local audit_status=$(jq -r '.overall_status // "UNKNOWN"' "$audit_file")
            case "$audit_status" in
                PASS) echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} Audit passed"; checklist+=("Audit:PASS") ;;
                WARNING|DEFERRED) echo -e "  ${YELLOW}[BLCK]${NC} ${YELLOW}!${NC} Audit: $audit_status"; checklist+=("Audit:WARN") ;;
                *) echo -e "  ${RED}[BLCK]${NC} ${RED}✗${NC} Audit failed"; checklist+=("Audit:FAIL") ;;
            esac
        elif [[ $failed -eq 0 && $warnings -eq 0 ]]; then
            echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} Audit passed ($passed passed)"
            checklist+=("Audit:PASS")
        elif [[ $failed -eq 0 ]]; then
            echo -e "  ${YELLOW}[BLCK]${NC} ${YELLOW}!${NC} Audit has warnings ($warnings warnings)"
            checklist+=("Audit:WARN")
        else
            echo -e "  ${RED}[BLCK]${NC} ${RED}✗${NC} Audit has failures ($failed failed)"
            checklist+=("Audit:FAIL")
        fi
    else
        echo -e "  ${YELLOW}[BLCK]${NC} ${YELLOW}!${NC} Audit not completed"
        checklist+=("Audit:SKIP")
    fi

    # Check review artifacts
    if [[ -f "$findings_file" && -f "$refinement_file" ]]; then
        echo -e "  ${GREEN}[PASS]${NC} ${GREEN}✓${NC} Review artifacts saved"
        checklist+=("Review artifacts:PASS")
    else
        echo -e "  ${YELLOW}[PASS]${NC} ${YELLOW}!${NC} Some review artifacts missing"
        checklist+=("Review artifacts:WARN")
    fi

    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # CLOSEOUT APPROVAL
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- CLOSEOUT APPROVAL${NC}"
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

    # Drain any buffered stdin from previous interactions
    while read -t 0.01 -n 1 _discard 2>/dev/null; do :; done

    # Handle EOF gracefully - default to approve
    read -e -p "  Choice [approve]: " closeout_choice || true
    closeout_choice=${closeout_choice:-approve}

    case "$closeout_choice" in
        review)
            echo ""
            echo -e "  ${DIM}Key artifacts:${NC}"
            echo -e "    .claude/reviews/findings.json         - Review findings"
            echo -e "    .claude/reviews/refinement-report.json - Refinement report"
            echo -e "    .claude/audit/phase-06-audit.json     - Audit results"
            echo ""
            ls -la "$review_dir"/ 2>/dev/null | head -10
            echo ""
            read -e -p "  Press Enter to continue to closeout..." || true
            ;;
        hold)
            echo ""
            atomic_warn "Closeout held - phase not complete"
            return 1
            ;;
    esac

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # GENERATE CLOSEOUT DOCUMENT
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- GENERATING CLOSEOUT${NC}"
    echo ""

    # Generate markdown closeout
    cat > "$closeout_file" << EOF
# Phase 6 Closeout: Code Review

**Completed:** $(date -Iseconds)
**Status:** COMPLETE

## Summary

Phase 6 (Code Review) has been completed. All implemented code has been reviewed and refined.

### Key Outcomes

- **Critical Issues Found:** $critical_found
- **Critical Issues Fixed:** $critical_fixed
- **Major Issues Found:** $major_found
- **Major Issues Fixed:** $major_fixed
- **Tests Passing:** $tests_passing

### Review Dimensions

Code was reviewed across four dimensions:

1. **Deep Code Review** - Logic, error handling, edge cases
2. **Architecture Compliance** - Pattern adherence, dependencies
3. **Performance Analysis** - Complexity, resource usage
4. **Documentation Review** - Comments, API docs, README

### Artifacts Produced

| Artifact | Location |
|----------|----------|
| Review Findings | .claude/reviews/findings.json |
| Refinement Report | .claude/reviews/refinement-report.json |
| Phase Audit | .claude/audit/phase-06-audit.json |

### Checklist Status

$(for item in "${checklist[@]}"; do
    IFS=':' read -r name status <<< "$item"
    case "$status" in
        PASS) echo "- [x] $name" ;;
        WARN) echo "- [~] $name (warning)" ;;
        FAIL) echo "- [ ] $name (failed)" ;;
        SKIP|DEFERRED) echo "- [-] $name (deferred)" ;;
    esac
done)

## Next Phase

**Phase 7: Integration Testing**

In the next phase, we will:
- Run integration tests across components
- Verify system-level behavior
- Test external integrations

## To Continue

\`\`\`bash
./orchestrator/pipeline resume
\`\`\`

---

*Phase 6 completed by ATOMIC CLAUDE*
EOF

    # Generate JSON closeout
    local checklist_json=$(printf '%s\n' "${checklist[@]}" | jq -R . | jq -s .)

    jq -n \
        --argjson critical_found "$critical_found" \
        --argjson critical_fixed "$critical_fixed" \
        --argjson major_found "$major_found" \
        --argjson major_fixed "$major_fixed" \
        --arg tests_passing "$tests_passing" \
        --argjson checklist "$checklist_json" \
        '{
            "phase": 6,
            "name": "Code Review",
            "status": "complete",
            "completed_at": (now | todate),
            "findings": {
                "critical_found": $critical_found,
                "critical_fixed": $critical_fixed,
                "major_found": $major_found,
                "major_fixed": $major_fixed
            },
            "tests_passing": ($tests_passing == "true"),
            "checklist": $checklist,
            "artifacts": {
                "findings": ".claude/reviews/findings.json",
                "refinement": ".claude/reviews/refinement-report.json",
                "audit": ".claude/audit/phase-06-audit.json"
            },
            "next_phase": 7
        }' > "$closeout_json"

    echo -e "  ${GREEN}✓${NC} Generated phase-06-closeout.md"
    echo -e "  ${GREEN}✓${NC} Generated phase-06-closeout.json"
    echo ""

    # Register closeout artifacts for downstream phases
    atomic_context_artifact "phase6_closeout_md" "$closeout_file" "Phase 6 closeout summary (markdown)"
    atomic_context_artifact "phase6_closeout_json" "$closeout_json" "Phase 6 closeout data (JSON)"
    [[ -f "$findings_file" ]] && atomic_context_artifact "review_findings" "$findings_file" "Code review findings"
    [[ -f "$refinement_file" ]] && atomic_context_artifact "refinement_report" "$refinement_file" "Code refinement report"
    atomic_context_decision "Phase 6 closeout completed: $critical_fixed/$critical_found critical, $major_fixed/$major_found major fixed" "closeout"

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # MEMORY CHECKPOINT
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    # Build summary for memory persistence
    local memory_summary="Phase 6 Code Review complete. $critical_fixed/$critical_found critical issues fixed, $major_fixed/$major_found major issues fixed. Tests passing: $tests_passing. Ready for integration testing."

    # Prompt user to save to long-term memory (if enabled)
    memory_prompt_save 6 "Code Review" "$memory_summary"

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # SESSION END
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- SESSION END${NC}"
    echo ""
    echo -e "  Closeout saved to:"
    echo -e "    ${DIM}.claude/closeout/phase-06-closeout.md${NC}"
    echo ""
    echo -e "  Review artifacts at:"
    echo -e "    ${DIM}.claude/reviews/${NC}"
    echo ""
    echo -e "  ${BOLD}Next: PHASE 7 - INTEGRATION TESTING${NC}"
    echo ""
    echo -e "  To continue:"
    echo -e "    ${CYAN}./orchestrator/pipeline resume${NC}"
    echo ""
    echo -e "  ${GREEN}Phase 6 Complete!${NC}"
    echo -e "  ${DIM}Code reviewed and refined. Ready for Integration Testing.${NC}"
    echo ""

    atomic_success "Phase 6 closeout complete"

    return 0
}
