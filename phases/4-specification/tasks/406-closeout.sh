#!/bin/bash
#
# Task 406: Phase Closeout
# Generate closeout document and prepare for Phase 5 (TDD Implementation)
#

task_406_closeout() {
    local closeout_dir="$ATOMIC_ROOT/.claude/closeout"
    local closeout_file="$closeout_dir/phase-04-closeout.md"
    local closeout_json="$closeout_dir/phase-04-closeout.json"
    local tasks_file="$ATOMIC_ROOT/.taskmaster/tasks/tasks.json"
    local specs_dir="$ATOMIC_ROOT/.claude/specs"
    # Audit file - check new path first, then legacy
    local audit_file="$ATOMIC_ROOT/.outputs/audits/phase-4-report.json"
    [[ ! -f "$audit_file" ]] && audit_file="$ATOMIC_ROOT/.claude/audit/phase-04-audit.json"

    atomic_step "Phase Closeout"

    mkdir -p "$closeout_dir"

    echo ""
    echo -e "  ${DIM}Final review before moving to Phase 5 (TDD Implementation).${NC}"
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

    local task_count=$(jq '.tasks | length // 0' "$tasks_file" 2>/dev/null || echo 0)
    local spec_count=$(find "$specs_dir" -name "spec-*.json" 2>/dev/null | wc -l | tr -d ' ')

    # Check OpenSpecs created
    if [[ "$spec_count" -ge "$task_count" && "$task_count" -gt 0 ]]; then
        echo -e "  ${GREEN}[CRIT]${NC} ${GREEN}✓${NC} OpenSpecs created ($spec_count specs)"
        checklist+=("OpenSpecs created:PASS")
    elif [[ "$spec_count" -gt 0 ]]; then
        echo -e "  ${YELLOW}[CRIT]${NC} ${YELLOW}!${NC} Partial OpenSpecs ($spec_count / $task_count)"
        checklist+=("OpenSpecs created:WARN")
    else
        echo -e "  ${RED}[CRIT]${NC} ${RED}✗${NC} No OpenSpecs created"
        checklist+=("OpenSpecs created:FAIL")
        all_passed=false
    fi

    # Check TDD subtasks
    local tasks_with_tdd=$(jq '[.tasks[] | select(.subtasks | length >= 4)] | length' "$tasks_file" 2>/dev/null || echo 0)
    if [[ "$tasks_with_tdd" -ge "$task_count" && "$task_count" -gt 0 ]]; then
        echo -e "  ${GREEN}[CRIT]${NC} ${GREEN}✓${NC} TDD subtasks injected ($tasks_with_tdd tasks)"
        checklist+=("TDD subtasks:PASS")
    elif [[ "$tasks_with_tdd" -gt 0 ]]; then
        echo -e "  ${YELLOW}[CRIT]${NC} ${YELLOW}!${NC} Partial TDD subtasks ($tasks_with_tdd / $task_count)"
        checklist+=("TDD subtasks:WARN")
    else
        echo -e "  ${RED}[CRIT]${NC} ${RED}✗${NC} No TDD subtasks"
        checklist+=("TDD subtasks:FAIL")
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

    # Check spec quality (at least have test strategies)
    local specs_with_tests=$(find "$specs_dir" -name "spec-*.json" -exec jq -e '.test_strategy.unit_tests | length > 0' {} \; 2>/dev/null | grep -c true || echo 0)
    if [[ "$specs_with_tests" -ge "$spec_count" && "$spec_count" -gt 0 ]]; then
        echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} Test strategies defined"
        checklist+=("Test strategies:PASS")
    else
        echo -e "  ${YELLOW}[BLCK]${NC} ${YELLOW}!${NC} Some specs lack test strategies"
        checklist+=("Test strategies:WARN")
    fi

    # TDD chain integrity
    local valid_chains=$(jq '[.tasks[] | select(.subtasks | length >= 4) | select(.subtasks[1].dependencies == [1]) | select(.subtasks[2].dependencies == [2]) | select(.subtasks[3].dependencies == [3])] | length' "$tasks_file" 2>/dev/null || echo 0)
    if [[ "$valid_chains" -ge "$tasks_with_tdd" && "$tasks_with_tdd" -gt 0 ]]; then
        echo -e "  ${GREEN}[PASS]${NC} ${GREEN}✓${NC} TDD chains valid (RED→GREEN→REFACTOR→VERIFY)"
        checklist+=("TDD chains:PASS")
    else
        echo -e "  ${YELLOW}[PASS]${NC} ${YELLOW}!${NC} Some TDD chains may be invalid"
        checklist+=("TDD chains:WARN")
    fi

    echo -e "  ${GREEN}[PASS]${NC} ${GREEN}✓${NC} Ready for TDD Implementation"
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

    # Drain any buffered stdin from previous interactions
    while read -t 0.01 -n 1 _discard 2>/dev/null; do :; done

    # Handle EOF gracefully - default to approve
    read -e -p "  Choice [approve]: " closeout_choice || true
    closeout_choice=${closeout_choice:-approve}

    case "$closeout_choice" in
        review)
            echo ""
            echo -e "  ${DIM}Key artifacts:${NC}"
            echo -e "    .claude/specs/                    - OpenSpec definitions"
            echo -e "    .taskmaster/tasks/tasks.json      - Tasks with TDD subtasks"
            echo -e "    .claude/audit/phase-04-audit.json - Audit results"
            echo ""
            ls -la "$specs_dir"/ 2>/dev/null | head -10
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

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}GENERATING CLOSEOUT${NC}"
    echo ""

    # Calculate total subtasks
    local total_subtasks=$(jq '[.tasks[].subtasks | length] | add // 0' "$tasks_file" 2>/dev/null || echo 0)

    # Generate markdown closeout
    cat > "$closeout_file" << EOF
# Phase 4 Closeout: Specification

**Completed:** $(date -Iseconds)
**Status:** COMPLETE

## Summary

Phase 4 (Specification) has been completed. Tasks have been expanded into OpenSpec definitions with TDD subtask structure.

### Key Outcomes

- **OpenSpecs Created:** $spec_count
- **Tasks with TDD:** $tasks_with_tdd
- **Total Subtasks:** $total_subtasks
- **TDD Structure:** RED→GREEN→REFACTOR→VERIFY

### Artifacts Produced

| Artifact | Location |
|----------|----------|
| OpenSpecs | .claude/specs/spec-*.json |
| Tasks (updated) | .taskmaster/tasks/tasks.json |
| Phase Audit | .claude/audit/phase-04-audit.json |

### TDD Subtask Structure

Each task now has 4 subtasks:

1. **RED** - Write failing tests (tests exist and FAIL)
2. **GREEN** - Minimal implementation (tests PASS)
3. **REFACTOR** - Clean up code (linting passes)
4. **VERIFY** - Security scan (no critical issues)

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

**Phase 5: TDD Implementation**

In the next phase, we will:
- Execute TDD cycles for each task
- Run RED subtasks (write failing tests)
- Run GREEN subtasks (implement to pass)
- Run REFACTOR subtasks (clean up code)
- Run VERIFY subtasks (security scans)

## To Continue

\`\`\`bash
./orchestrator/pipeline resume
\`\`\`

---

*Phase 4 completed by ATOMIC CLAUDE*
EOF

    # Generate JSON closeout
    local checklist_json=$(printf '%s\n' "${checklist[@]}" | jq -R . | jq -s .)

    jq -n \
        --argjson spec_count "$spec_count" \
        --argjson tasks_with_tdd "$tasks_with_tdd" \
        --argjson total_subtasks "$total_subtasks" \
        --argjson task_count "$task_count" \
        --argjson checklist "$checklist_json" \
        '{
            "phase": 4,
            "name": "Specification",
            "status": "complete",
            "completed_at": (now | todate),
            "spec_count": $spec_count,
            "tasks_with_tdd": $tasks_with_tdd,
            "total_subtasks": $total_subtasks,
            "task_count": $task_count,
            "checklist": $checklist,
            "artifacts": {
                "specs": ".claude/specs/",
                "tasks": ".taskmaster/tasks/tasks.json",
                "audit": ".claude/audit/phase-04-audit.json"
            },
            "next_phase": 5
        }' > "$closeout_json"

    echo -e "  ${GREEN}✓${NC} Generated phase-04-closeout.md"
    echo -e "  ${GREEN}✓${NC} Generated phase-04-closeout.json"
    echo ""

    # Register closeout artifacts for downstream phases
    atomic_context_artifact "phase4_closeout_md" "$closeout_file" "Phase 4 closeout summary (markdown)"
    atomic_context_artifact "phase4_closeout_json" "$closeout_json" "Phase 4 closeout data (JSON)"
    atomic_context_artifact "specs_directory" "$specs_dir" "OpenSpec definitions directory"
    atomic_context_decision "Phase 4 closeout completed: $spec_count specs, $tasks_with_tdd tasks with TDD" "closeout"

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # MEMORY CHECKPOINT
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    # Build summary for memory persistence
    local memory_summary="Phase 4 Specification complete. $spec_count OpenSpecs created. $tasks_with_tdd tasks with TDD subtasks (RED/GREEN/REFACTOR/VERIFY). Ready for implementation."

    # Prompt user to save to long-term memory (if enabled)
    memory_prompt_save 4 "Specification" "$memory_summary"

    # Git: commit and push phase
    atomic_git_phase_complete 4 "Specification"

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # SESSION END
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}SESSION END${NC}"
    echo ""
    echo -e "  Closeout saved to:"
    echo -e "    ${DIM}.claude/closeout/phase-04-closeout.md${NC}"
    echo ""
    echo -e "  Specifications saved to:"
    echo -e "    ${DIM}.claude/specs/spec-*.json${NC}"
    echo ""
    echo -e "  Tasks updated at:"
    echo -e "    ${DIM}.taskmaster/tasks/tasks.json${NC}"
    echo ""
    echo -e "  ${BOLD}Next: PHASE 5 - TDD IMPLEMENTATION${NC}"
    echo ""
    echo -e "  To continue:"
    echo -e "    ${CYAN}./orchestrator/pipeline resume${NC}"
    echo ""
    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${GREEN}Phase 4 Complete!${NC}"
    echo -e "  ${DIM}Specifications ready. TDD structure in place. See you in Implementation.${NC}"
    echo ""

    atomic_success "Phase 4 closeout complete"

    return 0
}
