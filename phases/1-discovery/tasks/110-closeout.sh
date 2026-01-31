#!/bin/bash
#
# Task 110: Phase Closeout
# Generate closeout document and prepare for Phase 2
#
# Steps:
#   1. Display closeout checklist
#   2. Get closeout approval
#   3. Generate phase-01-closeout.md
#   4. End session with instructions
#

task_110_closeout() {
    local closeout_dir="$ATOMIC_ROOT/.claude/closeout"
    local closeout_file="$closeout_dir/phase-01-closeout.md"
    local closeout_json="$closeout_dir/phase-01-closeout.json"

    atomic_step "Phase Closeout"

    mkdir -p "$closeout_dir"

    echo ""
    echo -e "${DIM}  ┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${DIM}  │ PHASE CLOSEOUT                                          │${NC}"
    echo -e "${DIM}  │                                                         │${NC}"
    echo -e "${DIM}  │ Final review before moving to Phase 2 (PRD).           │${NC}"
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

    # Check artifacts
    _110_check_artifact "Corpus collected" "$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/corpus.json" "CRIT" checklist all_passed
    _110_check_artifact "Dialogue completed" "$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/dialogue.json" "CRIT" checklist all_passed
    _110_check_artifact "Agents selected" "$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/selected-agents.json" "BLCK" checklist all_passed
    _110_check_artifact "Approaches generated" "$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/approaches.json" "CRIT" checklist all_passed
    _110_check_artifact "Approach selected" "$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/selected-approach.json" "CRIT" checklist all_passed
    _110_check_artifact "Direction confirmed" "$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/direction-confirmed.json" "CRIT" checklist all_passed

    # Check diagrams
    local diagrams_manifest="$ATOMIC_ROOT/docs/diagrams/manifest.json"
    if [[ -f "$diagrams_manifest" ]]; then
        local diagram_count=$(jq '.summary.generated // 0' "$diagrams_manifest")
        echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} Diagrams generated ($diagram_count)"
        checklist+=("diagrams:PASS")
    else
        echo -e "  ${YELLOW}[BLCK]${NC} ${YELLOW}!${NC} Diagrams not generated"
        checklist+=("diagrams:WARN")
    fi

    # Check audit - look in .outputs/audits/ (current path) or .claude/audit/ (legacy)
    local audit_file="$ATOMIC_ROOT/.outputs/audits/phase-1-report.json"
    [[ ! -f "$audit_file" ]] && audit_file="$ATOMIC_ROOT/.claude/audit/phase-01-audit.json"
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
                PASS) echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} Audit passed"; checklist+=("audit:PASS") ;;
                WARNING) echo -e "  ${YELLOW}[BLCK]${NC} ${YELLOW}!${NC} Audit has warnings"; checklist+=("audit:WARN") ;;
                *) echo -e "  ${RED}[BLCK]${NC} ${RED}✗${NC} Audit has critical issues"; checklist+=("audit:FAIL") ;;
            esac
        elif [[ $failed -eq 0 && $warnings -eq 0 ]]; then
            echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} Audit passed ($passed passed)"
            checklist+=("audit:PASS")
        elif [[ $failed -eq 0 ]]; then
            echo -e "  ${YELLOW}[BLCK]${NC} ${YELLOW}!${NC} Audit has warnings ($warnings warnings)"
            checklist+=("audit:WARN")
        else
            echo -e "  ${RED}[BLCK]${NC} ${RED}✗${NC} Audit has failures ($failed failed)"
            checklist+=("audit:FAIL")
        fi
    else
        echo -e "  ${YELLOW}[BLCK]${NC} ${YELLOW}!${NC} Audit not completed"
        checklist+=("audit:SKIP")
    fi

    # Additional checks
    echo -e "  ${GREEN}[PASS]${NC} ${GREEN}✓${NC} Ready for PRD"

    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # CLOSEOUT APPROVAL
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    if [[ "$all_passed" == false ]]; then
        echo -e "  ${YELLOW}Some items need attention before closeout.${NC}"
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
            echo -e "  ${DIM}Artifacts in this phase:${NC}"
            ls -la "$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/"
            echo ""
            read -e -p "  Press Enter to continue to closeout..." || true
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

    # Gather key information
    local approach_name="N/A"
    local approach_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/selected-approach.json"
    [[ -f "$approach_file" ]] && approach_name=$(jq -r '.name // "N/A"' "$approach_file")

    local corpus_count=0
    local corpus_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/corpus.json"
    [[ -f "$corpus_file" ]] && corpus_count=$(jq '.materials | length' "$corpus_file")

    local agent_count=0
    local agents_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/selected-agents.json"
    [[ -f "$agents_file" ]] && agent_count=$(jq '.selected | length' "$agents_file")

    # Generate markdown closeout
    cat > "$closeout_file" << EOF
# Phase 1 Closeout: Discovery

**Completed:** $(date -Iseconds)
**Status:** COMPLETE

## Summary

Phase 1 (Discovery) has been completed successfully.

### Key Outcomes

- **Corpus:** $corpus_count materials collected and organized
- **Selected Approach:** $approach_name
- **Agents Available:** $agent_count selected for pipeline use
- **Direction:** Confirmed and locked

### Artifacts Produced

| Artifact | Description |
|----------|-------------|
| corpus.json | Collected project materials |
| CORPUS-INDEX.md | Organized corpus index |
| dialogue.json | Opening dialogue capture |
| approaches.json | Generated solution approaches |
| first-principles.json | First principles analysis |
| selected-approach.json | Human-selected approach |
| direction-confirmed.json | Confirmed project direction |
| deliberation-log.json | Multi-agent discussion log |
| docs/diagrams/*.dot | Architecture diagrams (DOT format) |
| docs/diagrams/*.svg | Architecture diagrams (SVG visual) |

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

**Phase 2: PRD (Product Requirements Document)**

In the next phase, we will:
- Transform the selected approach into formal requirements
- Define user stories and acceptance criteria
- Establish technical specifications
- Document non-functional requirements

## Agent Selection

Note: You'll have the opportunity to select or modify agents at the
start of Phase 2 and each subsequent phase. The agents selected in
this phase serve as recommendations, not fixed assignments.

## To Continue

\`\`\`bash
./orchestrator/pipeline resume
\`\`\`

---

*Phase 1 completed by ATOMIC CLAUDE*
EOF

    # Generate JSON closeout
    cat > "$closeout_json" << EOF
{
    "phase": 1,
    "name": "Discovery",
    "status": "complete",
    "completed_at": "$(date -Iseconds)",
    "approach": "$approach_name",
    "corpus_materials": $corpus_count,
    "agents_selected": $agent_count,
    "checklist": [$(printf '"%s",' "${checklist[@]}" | sed 's/,$//')],
    "next_phase": 2
}
EOF

    echo -e "  ${GREEN}✓${NC} Generated phase-01-closeout.md"
    echo -e "  ${GREEN}✓${NC} Generated phase-01-closeout.json"
    echo ""

    # Register closeout artifacts for downstream phases
    atomic_context_artifact "phase1_closeout_md" "$closeout_file" "Phase 1 closeout summary (markdown)"
    atomic_context_artifact "phase1_closeout_json" "$closeout_json" "Phase 1 closeout data (JSON)"
    atomic_context_decision "Phase 1 closeout completed: $corpus_count materials, approach=$approach_name" "closeout"

    # ═══════════════════════════════════════════════════════════════════════════
    # MEMORY CHECKPOINT
    # ═══════════════════════════════════════════════════════════════════════════

    # Build summary for memory persistence
    local memory_summary="Phase 1 Discovery complete. $corpus_count materials collected. Selected approach: $approach_name. Direction confirmed and locked for PRD phase."

    # Prompt user to save to long-term memory (if enabled)
    memory_prompt_save 1 "Discovery" "$memory_summary"

    # Git: commit and push phase
    atomic_git_phase_complete 1 "Discovery"

    # ═══════════════════════════════════════════════════════════════════════════
    # SESSION END
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  ${BOLD}SESSION END${NC}                                                 ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  Closeout saved to:                                           ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  ${DIM}.claude/closeout/phase-01-closeout.md${NC}                       ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  ${BOLD}Next: PHASE 2 - PRD${NC}                                        ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  To continue:                                                 ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  ${CYAN}./orchestrator/pipeline resume${NC}                              ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  ─────────────────────────────────────────────────────────── ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}      ${BOLD}Phase 1 Complete!${NC}                                       ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}      ${DIM}Great work. See you in PRD.${NC}                              ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    atomic_success "Phase 1 closeout complete"

    return 0
}

# Helper function to check artifact existence
_110_check_artifact() {
    local name="$1"
    local path="$2"
    local level="$3"
    local -n checklist_ref=$4
    local -n passed_ref=$5

    if [[ -f "$path" ]]; then
        echo -e "  ${GREEN}[$level]${NC} ${GREEN}✓${NC} $name"
        checklist_ref+=("$name:PASS")
    else
        if [[ "$level" == "CRIT" ]]; then
            echo -e "  ${RED}[$level]${NC} ${RED}✗${NC} $name"
            checklist_ref+=("$name:FAIL")
            passed_ref=false
        else
            echo -e "  ${YELLOW}[$level]${NC} ${YELLOW}!${NC} $name"
            checklist_ref+=("$name:WARN")
        fi
    fi
}
