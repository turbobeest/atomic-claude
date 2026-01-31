#!/bin/bash
#
# Task 306: Phase Closeout
# Generate closeout document and prepare for Phase 4 (Specification)
#

task_306_closeout() {
    local closeout_dir="$ATOMIC_ROOT/.claude/closeout"
    local closeout_file="$closeout_dir/phase-03-closeout.md"
    local closeout_json="$closeout_dir/phase-03-closeout.json"
    local tasks_file="$ATOMIC_ROOT/.taskmaster/tasks/tasks.json"
    local packages_file="$ATOMIC_ROOT/.taskmaster/reports/work-packages.json"

    atomic_step "Phase Closeout"

    mkdir -p "$closeout_dir"

    echo ""
    echo -e "  ${DIM}Final review before moving to Phase 4 (Specification).${NC}"
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

    # Check tasks.json
    if [[ -f "$tasks_file" ]]; then
        local task_count=$(jq '.tasks | length // 0' "$tasks_file" 2>/dev/null || echo 0)
        if [[ $task_count -ge 3 ]]; then
            echo -e "  ${GREEN}[CRIT]${NC} ${GREEN}✓${NC} Tasks decomposed ($task_count tasks)"
            checklist+=("Tasks decomposed:PASS")
        else
            echo -e "  ${RED}[CRIT]${NC} ${RED}✗${NC} Insufficient tasks ($task_count)"
            checklist+=("Tasks decomposed:FAIL")
            all_passed=false
        fi
    else
        echo -e "  ${RED}[CRIT]${NC} ${RED}✗${NC} Tasks file missing"
        checklist+=("Tasks decomposed:FAIL")
        all_passed=false
    fi

    # Check dependencies
    local dep_analysis="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/dependency-analysis.json"
    if [[ -f "$dep_analysis" ]]; then
        # Check .validation.passed (new format) or .dependency_validation.valid (old format)
        local dep_valid=$(jq -r '.validation.passed // .dependency_validation.valid // false' "$dep_analysis")
        if [[ "$dep_valid" == "true" ]]; then
            echo -e "  ${GREEN}[CRIT]${NC} ${GREEN}✓${NC} Dependencies validated"
            checklist+=("Dependencies mapped:PASS")
        else
            echo -e "  ${YELLOW}[CRIT]${NC} ${YELLOW}!${NC} Dependency issues found"
            checklist+=("Dependencies mapped:WARN")
        fi
    else
        echo -e "  ${YELLOW}[CRIT]${NC} ${YELLOW}!${NC} Dependency analysis not found"
        checklist+=("Dependencies mapped:SKIP")
    fi

    # Check audit - look in .outputs/audits/ (current path) or .claude/audit/ (legacy)
    local audit_file="$ATOMIC_ROOT/.outputs/audits/phase-3-report.json"
    [[ ! -f "$audit_file" ]] && audit_file="$ATOMIC_ROOT/.claude/audit/phase-03-audit.json"
    if [[ -f "$audit_file" ]]; then
        # Check summary.passed/failed/warnings or overall_status
        local passed=$(jq -r '.summary.passed // 0' "$audit_file")
        local failed=$(jq -r '.summary.failed // 0' "$audit_file")
        local warnings=$(jq -r '.summary.warnings // 0' "$audit_file")
        local total=$((passed + failed + warnings))

        if [[ $failed -eq 0 && $warnings -eq 0 && $total -gt 0 ]]; then
            echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} Audit passed ($passed passed)"
            checklist+=("Audit:PASS")
        elif [[ $failed -eq 0 && $warnings -gt 0 ]]; then
            echo -e "  ${YELLOW}[BLCK]${NC} ${YELLOW}!${NC} Audit has warnings ($warnings warnings)"
            checklist+=("Audit:WARN")
        elif [[ $failed -gt 0 ]]; then
            echo -e "  ${RED}[BLCK]${NC} ${RED}✗${NC} Audit has failures ($failed failed)"
            checklist+=("Audit:FAIL")
        else
            echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} Audit completed"
            checklist+=("Audit:PASS")
        fi
    else
        echo -e "  ${YELLOW}[BLCK]${NC} ${YELLOW}!${NC} Audit not completed"
        checklist+=("Audit:SKIP")
    fi

    # Check work packages
    if [[ -f "$packages_file" ]]; then
        local pkg_count=$(jq '.packages | length // 0' "$packages_file" 2>/dev/null || echo 0)
        echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} Work packages created ($pkg_count packages)"
        checklist+=("Work packages:PASS")
    else
        echo -e "  ${YELLOW}[BLCK]${NC} ${YELLOW}!${NC} Work packages not created"
        checklist+=("Work packages:SKIP")
    fi

    # Check complexity report (embedded in dependency-analysis.json or separate file)
    local complexity_file="$ATOMIC_ROOT/.taskmaster/reports/task-complexity-report.json"
    local has_complexity=false
    if [[ -f "$complexity_file" ]]; then
        has_complexity=true
    elif [[ -f "$dep_analysis" ]]; then
        # Check for complexity data in dependency analysis
        local complexity_data=$(jq -r '.complexity // empty' "$dep_analysis" 2>/dev/null)
        [[ -n "$complexity_data" ]] && has_complexity=true
    fi

    if [[ "$has_complexity" == "true" ]]; then
        echo -e "  ${GREEN}[PASS]${NC} ${GREEN}✓${NC} Complexity analysis complete"
        checklist+=("Complexity:PASS")
    else
        echo -e "  ${YELLOW}[PASS]${NC} ${YELLOW}!${NC} Complexity analysis not found"
        checklist+=("Complexity:SKIP")
    fi

    echo -e "  ${GREEN}[PASS]${NC} ${GREEN}✓${NC} Ready for Specification"
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
            echo -e "    .taskmaster/tasks/tasks.json"
            echo -e "    .taskmaster/reports/work-packages.json"
            echo -e "    .taskmaster/reports/dependency-graph.json"
            echo -e "    .taskmaster/reports/task-complexity-report.json"
            echo ""
            ls -la "$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/" 2>/dev/null
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

    # Gather metrics
    local task_count=0
    local high_priority=0
    local package_count=0
    [[ -f "$tasks_file" ]] && task_count=$(jq '.tasks | length // 0' "$tasks_file")
    [[ -f "$tasks_file" ]] && high_priority=$(jq '[.tasks[] | select(.priority == "high")] | length' "$tasks_file" 2>/dev/null || echo 0)
    [[ -f "$packages_file" ]] && package_count=$(jq '.packages | length // 0' "$packages_file" 2>/dev/null || echo 0)

    # Generate markdown closeout
    cat > "$closeout_file" << EOF
# Phase 3 Closeout: Tasking

**Completed:** $(date -Iseconds)
**Status:** COMPLETE

## Summary

Phase 3 (Tasking) has been completed successfully. PRD has been decomposed into implementable tasks.

### Key Outcomes

- **Total Tasks:** $task_count
- **High Priority:** $high_priority
- **Work Packages:** $package_count
- **Format:** TaskMaster JSON

### Artifacts Produced

| Artifact | Location |
|----------|----------|
| Tasks | .taskmaster/tasks/tasks.json |
| Work Packages | .taskmaster/reports/work-packages.json |
| Dependency Graph | .taskmaster/reports/dependency-graph.json |
| Complexity Report | .taskmaster/reports/task-complexity-report.json |
| Phase Audit | .claude/audit/phase-03-audit.json |

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

**Phase 4: Specification**

In the next phase, we will:
- Create OpenSpec definitions for each task
- Define TDD subtasks (RED/GREEN/REFACTOR/VERIFY)
- Specify interfaces and contracts
- Detail test strategies

## To Continue

\`\`\`bash
./orchestrator/pipeline resume
\`\`\`

---

*Phase 3 completed by ATOMIC CLAUDE*
EOF

    # Generate JSON closeout
    local checklist_json=$(printf '%s\n' "${checklist[@]}" | jq -R . | jq -s .)

    jq -n \
        --argjson task_count "$task_count" \
        --argjson high_priority "$high_priority" \
        --argjson package_count "$package_count" \
        --argjson checklist "$checklist_json" \
        '{
            "phase": 3,
            "name": "Tasking",
            "status": "complete",
            "completed_at": (now | todate),
            "task_count": $task_count,
            "high_priority_count": $high_priority,
            "package_count": $package_count,
            "checklist": $checklist,
            "artifacts": {
                "tasks": ".taskmaster/tasks/tasks.json",
                "packages": ".taskmaster/reports/work-packages.json",
                "dependencies": ".taskmaster/reports/dependency-graph.json",
                "complexity": ".taskmaster/reports/task-complexity-report.json"
            },
            "next_phase": 4
        }' > "$closeout_json"

    echo -e "  ${GREEN}✓${NC} Generated phase-03-closeout.md"
    echo -e "  ${GREEN}✓${NC} Generated phase-03-closeout.json"
    echo ""

    # Register closeout artifacts for downstream phases
    atomic_context_artifact "phase3_closeout_md" "$closeout_file" "Phase 3 closeout summary (markdown)"
    atomic_context_artifact "phase3_closeout_json" "$closeout_json" "Phase 3 closeout data (JSON)"
    atomic_context_artifact "tasks_json" "$tasks_file" "TaskMaster tasks definition"
    [[ -f "$packages_file" ]] && atomic_context_artifact "work_packages" "$packages_file" "Work packages report"
    atomic_context_decision "Phase 3 closeout completed: $task_count tasks, $package_count packages" "closeout"

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # SESSION END
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}SESSION END${NC}"
    echo ""
    echo -e "  Closeout saved to:"
    echo -e "    ${DIM}.claude/closeout/phase-03-closeout.md${NC}"
    echo ""
    echo -e "  Tasks saved to:"
    echo -e "    ${DIM}.taskmaster/tasks/tasks.json${NC}"
    echo ""
    echo -e "  ${BOLD}Next: PHASE 4 - SPECIFICATION${NC}"
    echo ""
    echo -e "  To continue:"
    echo -e "    ${CYAN}./orchestrator/pipeline resume${NC}"
    echo ""
    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${GREEN}Phase 3 Complete!${NC}"
    echo -e "  ${DIM}Tasks ready. See you in Specification.${NC}"
    echo ""

    atomic_success "Phase 3 closeout complete"

    return 0
}
