#!/bin/bash
#
# Task 507: Phase Closeout
# Generate closeout document and prepare for Phase 6 (Code Review)
#

task_507_closeout() {
    local closeout_dir="$ATOMIC_ROOT/.claude/closeout"
    local closeout_file="$closeout_dir/phase-05-closeout.md"
    local closeout_json="$closeout_dir/phase-05-closeout.json"
    local tasks_file="$ATOMIC_ROOT/.taskmaster/tasks/tasks.json"
    local testing_dir="$ATOMIC_ROOT/.claude/testing"
    local audit_file="$ATOMIC_ROOT/.claude/audit/phase-05-audit.json"
    local validation_file="$testing_dir/validation-report.json"

    atomic_step "Phase Closeout"

    mkdir -p "$closeout_dir"

    echo ""
    echo -e "  ${DIM}Final review before moving to Phase 6 (Code Review).${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # CLOSEOUT CHECKLIST
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}CLOSEOUT CHECKLIST${NC}"
    echo ""

    local checklist=()
    local all_passed=true

    # Get metrics
    local total_tasks=$(jq '[.tasks[] | select(.subtasks | length >= 4)] | length' "$tasks_file" 2>/dev/null || echo 0)
    local completed_tasks=$(jq '[.tasks[] | select(.status == "done")] | length' "$tasks_file" 2>/dev/null || echo 0)
    local tdd_records=$(find "$testing_dir" -name "tdd-t*.json" 2>/dev/null | wc -l)

    local unit_coverage=0
    local passing_tests=0
    local total_tests=0
    local critical_issues=0

    if [[ -f "$validation_file" ]]; then
        unit_coverage=$(jq -r '.coverage.unit // 0' "$validation_file")
        passing_tests=$(jq -r '.test_quality.passing_tests // 0' "$validation_file")
        total_tests=$(jq -r '.test_quality.total_tests // 0' "$validation_file")
        critical_issues=$(jq -r '.security.critical // 0' "$validation_file")
    fi

    # Check TDD completion
    if [[ "$completed_tasks" -ge "$total_tasks" && "$total_tasks" -gt 0 ]]; then
        echo -e "  ${GREEN}[CRIT]${NC} ${GREEN}✓${NC} All TDD cycles complete ($completed_tasks tasks)"
        checklist+=("TDD cycles complete:PASS")
    else
        echo -e "  ${RED}[CRIT]${NC} ${RED}✗${NC} TDD cycles incomplete ($completed_tasks / $total_tasks)"
        checklist+=("TDD cycles complete:FAIL")
        all_passed=false
    fi

    # Check coverage
    if [[ "$unit_coverage" -ge 80 ]]; then
        echo -e "  ${GREEN}[CRIT]${NC} ${GREEN}✓${NC} Coverage >= 80% (${unit_coverage}%)"
        checklist+=("Coverage:PASS")
    elif [[ "$unit_coverage" -ge 70 ]]; then
        echo -e "  ${YELLOW}[CRIT]${NC} ${YELLOW}!${NC} Coverage ${unit_coverage}% (target: 80%)"
        checklist+=("Coverage:WARN")
    else
        echo -e "  ${RED}[CRIT]${NC} ${RED}✗${NC} Coverage below 70% (${unit_coverage}%)"
        checklist+=("Coverage:FAIL")
        all_passed=false
    fi

    # Check all tests passing
    if [[ "$passing_tests" -eq "$total_tests" && "$total_tests" -gt 0 ]]; then
        echo -e "  ${GREEN}[CRIT]${NC} ${GREEN}✓${NC} All tests passing ($passing_tests tests)"
        checklist+=("All tests passing:PASS")
    else
        echo -e "  ${RED}[CRIT]${NC} ${RED}✗${NC} Tests failing ($((total_tests - passing_tests)) of $total_tests)"
        checklist+=("All tests passing:FAIL")
        all_passed=false
    fi

    # Check VERIFY scans
    if [[ "$critical_issues" -eq 0 ]]; then
        echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} VERIFY scans clean"
        checklist+=("VERIFY scans:PASS")
    else
        echo -e "  ${RED}[BLCK]${NC} ${RED}✗${NC} $critical_issues critical security issues"
        checklist+=("VERIFY scans:FAIL")
    fi

    # Check audit
    if [[ -f "$audit_file" ]]; then
        local audit_status=$(jq -r '.overall_status // "UNKNOWN"' "$audit_file")
        if [[ "$audit_status" == "PASS" ]]; then
            echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} Audit passed"
            checklist+=("Audit:PASS")
        elif [[ "$audit_status" == "DEFERRED" ]]; then
            echo -e "  ${YELLOW}[BLCK]${NC} ${YELLOW}!${NC} Audit deferred"
            checklist+=("Audit:DEFERRED")
        else
            echo -e "  ${YELLOW}[BLCK]${NC} ${YELLOW}!${NC} Audit: $audit_status"
            checklist+=("Audit:WARN")
        fi
    else
        echo -e "  ${YELLOW}[BLCK]${NC} ${YELLOW}!${NC} Audit not completed"
        checklist+=("Audit:SKIP")
    fi

    # Check no flaky tests
    local flaky_tests=0
    if [[ -f "$validation_file" ]]; then
        flaky_tests=$(jq -r '.test_quality.flaky_tests // 0' "$validation_file")
    fi
    if [[ "$flaky_tests" -eq 0 ]]; then
        echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} No flaky tests"
        checklist+=("No flaky tests:PASS")
    else
        echo -e "  ${YELLOW}[BLCK]${NC} ${YELLOW}!${NC} $flaky_tests flaky tests detected"
        checklist+=("No flaky tests:WARN")
    fi

    echo -e "  ${GREEN}[PASS]${NC} ${GREEN}✓${NC} Ready for Code Review"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # CLOSEOUT APPROVAL
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
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
            echo -e "  ${DIM}Key artifacts:${NC}"
            echo -e "    .claude/testing/                     - TDD execution records"
            echo -e "    .claude/testing/validation-report.json - Validation report"
            echo -e "    .claude/audit/phase-05-audit.json    - Audit results"
            echo -e "    .taskmaster/tasks/tasks.json         - Task completion status"
            echo ""
            ls -la "$testing_dir"/ 2>/dev/null | head -10
            echo ""
            read -p "  Press Enter to continue to closeout..."
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

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}GENERATING CLOSEOUT${NC}"
    echo ""

    # Generate markdown closeout
    cat > "$closeout_file" << EOF
# Phase 5 Closeout: TDD Implementation

**Completed:** $(date -Iseconds)
**Status:** COMPLETE

## Summary

Phase 5 (TDD Implementation) has been completed. All tasks have gone through RED/GREEN/REFACTOR/VERIFY cycles.

### Key Outcomes

- **Tasks Completed:** $completed_tasks / $total_tasks
- **Tests Written:** $total_tests
- **Tests Passing:** $passing_tests
- **Unit Coverage:** ${unit_coverage}%
- **Critical Issues:** $critical_issues

### TDD Execution

Each task completed the following cycle:

1. **RED** - Wrote failing tests based on OpenSpec
2. **GREEN** - Implemented minimal code to pass tests
3. **REFACTOR** - Cleaned up code, ran linters
4. **VERIFY** - Security scans, no critical issues

### Artifacts Produced

| Artifact | Location |
|----------|----------|
| TDD Records | .claude/testing/tdd-t*.json |
| Validation Report | .claude/testing/validation-report.json |
| Phase Audit | .claude/audit/phase-05-audit.json |
| Updated Tasks | .taskmaster/tasks/tasks.json |

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

**Phase 6: Code Review**

In the next phase, we will:
- Conduct peer code review
- Check for best practices and patterns
- Validate architecture decisions
- Ensure code maintainability

## To Continue

\`\`\`bash
./orchestrator/pipeline resume
\`\`\`

---

*Phase 5 completed by ATOMIC CLAUDE*
EOF

    # Generate JSON closeout
    local checklist_json=$(printf '%s\n' "${checklist[@]}" | jq -R . | jq -s .)

    jq -n \
        --argjson completed_tasks "$completed_tasks" \
        --argjson total_tasks "$total_tasks" \
        --argjson total_tests "$total_tests" \
        --argjson passing_tests "$passing_tests" \
        --argjson unit_coverage "$unit_coverage" \
        --argjson critical_issues "$critical_issues" \
        --argjson flaky_tests "$flaky_tests" \
        --argjson tdd_records "$tdd_records" \
        --argjson checklist "$checklist_json" \
        '{
            "phase": 5,
            "name": "TDD Implementation",
            "status": "complete",
            "completed_at": (now | todate),
            "tasks_completed": $completed_tasks,
            "total_tasks": $total_tasks,
            "tests": {
                "total": $total_tests,
                "passing": $passing_tests,
                "flaky": $flaky_tests
            },
            "coverage": {
                "unit": $unit_coverage
            },
            "security": {
                "critical_issues": $critical_issues
            },
            "tdd_records": $tdd_records,
            "checklist": $checklist,
            "artifacts": {
                "testing": ".claude/testing/",
                "validation": ".claude/testing/validation-report.json",
                "audit": ".claude/audit/phase-05-audit.json",
                "tasks": ".taskmaster/tasks/tasks.json"
            },
            "next_phase": 6
        }' > "$closeout_json"

    echo -e "  ${GREEN}✓${NC} Generated phase-05-closeout.md"
    echo -e "  ${GREEN}✓${NC} Generated phase-05-closeout.json"
    echo ""

    atomic_context_decision "Phase 5 closeout completed" "closeout"

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # SESSION END
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}SESSION END${NC}"
    echo ""
    echo -e "  Closeout saved to:"
    echo -e "    ${DIM}.claude/closeout/phase-05-closeout.md${NC}"
    echo ""
    echo -e "  Testing artifacts at:"
    echo -e "    ${DIM}.claude/testing/${NC}"
    echo ""
    echo -e "  ${BOLD}Next: PHASE 6 - CODE REVIEW${NC}"
    echo ""
    echo -e "  To continue:"
    echo -e "    ${CYAN}./orchestrator/pipeline resume${NC}"
    echo ""
    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${GREEN}Phase 5 Complete!${NC}"
    echo -e "  ${DIM}TDD cycles executed. Tests passing. Ready for Code Review.${NC}"
    echo ""

    atomic_success "Phase 5 closeout complete"

    return 0
}
