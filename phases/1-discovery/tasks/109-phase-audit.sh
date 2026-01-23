#!/bin/bash
#
# Task 109: Phase Audit - Discovery
# AI-driven audit selection from turbobeest/audits repository
#
# Features:
#   - AI recommends relevant audits based on phase context
#   - User reviews and approves audit selection
#   - Executes selected audits with dependency awareness
#   - Supports air-gapped environments via dependency manifests
#

task_109_phase_audit() {
    local audit_dir="$ATOMIC_ROOT/.claude/audit"
    local prompts_dir="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prompts"

    atomic_step "Phase Audit"

    mkdir -p "$audit_dir" "$prompts_dir"

    echo ""
    echo -e "${DIM}  ┌─────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${DIM}  │ PHASE AUDIT: DISCOVERY                                      │${NC}"
    echo -e "${DIM}  │                                                             │${NC}"
    echo -e "${DIM}  │ An AI-driven audit reviews Phase 1 outputs against the     │${NC}"
    echo -e "${DIM}  │ comprehensive audit library (~2,200 audits).                │${NC}"
    echo -e "${DIM}  └─────────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # AUDIT MODE SELECTION
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}AUDIT MODE SELECTION${NC}                                        ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "  ${CYAN}Select audit mode:${NC}"
    echo ""
    echo -e "    ${GREEN}[1]${NC} AI-Driven ${DIM}(recommended)${NC}"
    echo -e "        ${DIM}AI recommends audits from 2,200+ library based on context${NC}"
    echo ""
    echo -e "    ${GREEN}[2]${NC} Legacy Dimensions"
    echo -e "        ${DIM}Static 9-dimension audit for Phase 1 Discovery${NC}"
    echo ""
    echo -e "    ${GREEN}[3]${NC} Skip Audit"
    echo -e "        ${DIM}Proceed without audit (not recommended)${NC}"
    echo ""

    read -p "  Mode [1]: " mode_choice
    mode_choice=${mode_choice:-1}

    case "$mode_choice" in
        1)
            _109_ai_driven_audit
            ;;
        2)
            _109_legacy_audit
            ;;
        3)
            echo -e "  ${YELLOW}!${NC} Skipping audit for Phase 1"
            atomic_context_decision "Phase 1 audit skipped by user" "audit"
            ;;
    esac

    return 0
}

# ═══════════════════════════════════════════════════════════════════════════════
# AI-DRIVEN AUDIT (from turbobeest/audits)
# ═══════════════════════════════════════════════════════════════════════════════

_109_ai_driven_audit() {
    # Source the audit library
    source "$ATOMIC_ROOT/lib/audit.sh"

    # Run the AI-driven phase audit
    audit_run_phase 1 "Discovery"

    return $?
}

# ═══════════════════════════════════════════════════════════════════════════════
# LEGACY DIMENSION-BASED AUDIT
# ═══════════════════════════════════════════════════════════════════════════════

_109_legacy_audit() {
    local audit_dir="$ATOMIC_ROOT/.claude/audit"
    local audit_file="$audit_dir/phase-01-audit.json"
    local prompts_dir="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prompts"

    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}LEGACY AUDIT (9 Dimensions)${NC}                                 ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Define dimensions
    declare -A dimensions=(
        ["ID-01"]="Corpus Completeness|Are all relevant materials collected?"
        ["ID-02"]="Vision Clarity|Is the project vision clear and actionable?"
        ["ID-03"]="Constraint Definition|Are constraints well-defined and realistic?"
        ["ID-04"]="Approach Viability|Is the selected approach feasible?"
        ["ID-05"]="First Principles Validity|Have assumptions been properly challenged?"
        ["ID-06"]="Stakeholder Coverage|Are all stakeholders identified?"
        ["ID-07"]="Risk Awareness|Are key risks identified and considered?"
        ["ID-08"]="Deliberation Quality|Was the multi-agent discussion productive?"
        ["ID-09"]="Scope Boundaries|Are scope boundaries clear?"
    )

    echo -e "  ${CYAN}Available Dimensions:${NC}"
    echo ""
    for id in $(echo "${!dimensions[@]}" | tr ' ' '\n' | sort); do
        IFS='|' read -r name desc <<< "${dimensions[$id]}"
        echo -e "    ${GREEN}$id${NC}: $name"
        echo -e "         ${DIM}$desc${NC}"
    done
    echo ""

    echo -e "  ${CYAN}Audit Profile:${NC}"
    echo -e "    ${GREEN}[quick]${NC}  Top 5 dimensions (fast)"
    echo -e "    ${GREEN}[custom]${NC} Select specific dimensions"
    echo -e "    ${GREEN}[all]${NC}    All 9 dimensions (thorough)"
    echo ""

    read -p "  Profile [quick]: " audit_profile
    audit_profile=${audit_profile:-quick}

    local selected_dims=()

    case "$audit_profile" in
        quick)
            selected_dims=("ID-01" "ID-02" "ID-04" "ID-07" "ID-09")
            ;;
        custom)
            echo ""
            echo -e "  ${DIM}Enter dimension IDs (space-separated):${NC}"
            read -p "  > " custom_selection
            selected_dims=($custom_selection)
            ;;
        all)
            selected_dims=($(echo "${!dimensions[@]}" | tr ' ' '\n' | sort))
            ;;
    esac

    echo ""
    echo -e "  ${GREEN}✓${NC} Selected ${#selected_dims[@]} dimensions"
    echo ""

    # Execute audit
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}EXECUTING LEGACY AUDIT${NC}                                      ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Gather phase artifacts
    local artifacts=""
    for f in "$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE"/*.json "$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE"/*.md; do
        [[ -f "$f" ]] && artifacts+="$(basename "$f"): $(head -50 "$f" 2>/dev/null)\n\n"
    done

    # Build audit prompt
    cat > "$prompts_dir/phase-audit.md" << EOF
# Task: Phase 1 Discovery Audit (Legacy Mode)

You are an independent auditor reviewing Phase 1 (Discovery) outputs.

## Artifacts to Review

$artifacts

## Dimensions to Audit

$(for dim in "${selected_dims[@]}"; do
    IFS='|' read -r name desc <<< "${dimensions[$dim]}"
    echo "### $dim: $name"
    echo "$desc"
    echo ""
done)

## Output Format

For EACH dimension, provide:
1. **Status**: PASS / WARNING / CRITICAL
2. **Finding**: What you observed
3. **Evidence**: Supporting artifacts/content
4. **Recommendation**: What to do (if not PASS)

Output as JSON:
{
  "audit_timestamp": "$(date -Iseconds)",
  "audit_mode": "legacy",
  "dimensions_audited": ${#selected_dims[@]},
  "findings": {
    "ID-XX": {
      "name": "...",
      "status": "PASS|WARNING|CRITICAL",
      "finding": "...",
      "evidence": "...",
      "recommendation": "..."
    }
  },
  "summary": {
    "passed": N,
    "warnings": N,
    "critical": N
  },
  "overall_status": "PASS|WARNING|CRITICAL",
  "proceed_recommendation": true|false
}

Output ONLY valid JSON.
EOF

    atomic_waiting "auditor analyzing..."

    local audit_raw="$prompts_dir/audit-raw.json"
    if atomic_invoke "$prompts_dir/phase-audit.md" "$audit_raw" "Phase 1 audit" --model=sonnet; then
        if jq -e . "$audit_raw" &>/dev/null; then
            cp "$audit_raw" "$audit_file"
            atomic_success "Audit complete"
        else
            atomic_warn "Invalid audit output"
            echo '{"overall_status": "WARNING", "summary": {"passed": 0, "warnings": 1, "critical": 0}}' > "$audit_file"
        fi
    else
        atomic_error "Audit failed"
        echo '{"overall_status": "WARNING", "summary": {"passed": 0, "warnings": 1, "critical": 0}, "error": "Audit execution failed"}' > "$audit_file"
    fi

    # Display findings
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}AUDIT FINDINGS${NC}                                               ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local passed=$(jq -r '.summary.passed // 0' "$audit_file")
    local warnings=$(jq -r '.summary.warnings // 0' "$audit_file")
    local critical=$(jq -r '.summary.critical // 0' "$audit_file")
    local overall=$(jq -r '.overall_status // "UNKNOWN"' "$audit_file")

    local status_color="${GREEN}"
    [[ "$overall" == "WARNING" ]] && status_color="${YELLOW}"
    [[ "$overall" == "CRITICAL" ]] && status_color="${RED}"

    echo -e "  ${status_color}Overall Status: $overall${NC}"
    echo ""
    echo -e "  ${GREEN}PASSED:${NC}   $passed"
    echo -e "  ${YELLOW}WARNINGS:${NC} $warnings"
    echo -e "  ${RED}CRITICAL:${NC} $critical"
    echo ""

    # Show individual findings
    jq -r '.findings | to_entries[] | "\(.key): \(.value.status) - \(.value.finding)"' "$audit_file" 2>/dev/null | \
    while IFS= read -r finding; do
        if [[ "$finding" == *"PASS"* ]]; then
            echo -e "  ${GREEN}✓${NC} $finding"
        elif [[ "$finding" == *"WARNING"* ]]; then
            echo -e "  ${YELLOW}!${NC} $finding"
        elif [[ "$finding" == *"CRITICAL"* ]]; then
            echo -e "  ${RED}✗${NC} $finding"
        fi
    done

    echo ""

    # Handle warnings/critical
    if [[ $warnings -gt 0 ]] || [[ $critical -gt 0 ]]; then
        echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "  ${CYAN}How would you like to proceed?${NC}"
        echo ""
        echo -e "    ${GREEN}[accept]${NC}    Accept findings and continue"
        echo -e "    ${YELLOW}[address]${NC}   Address issues before continuing"
        echo -e "    ${BLUE}[defer]${NC}     Defer issues to later phases"
        echo ""

        read -p "  Choice [accept]: " review_choice
        review_choice=${review_choice:-accept}

        case "$review_choice" in
            address)
                echo ""
                echo -e "  ${DIM}Please address the issues and run the audit again.${NC}"
                return 1
                ;;
            defer)
                local tmp=$(mktemp)
                jq '.deferred = true | .deferred_by = "human"' "$audit_file" > "$tmp"
                mv "$tmp" "$audit_file"
                echo -e "  ${GREEN}✓${NC} Issues deferred"
                ;;
        esac
    fi

    atomic_context_artifact "phase_audit" "$audit_file" "Phase 1 legacy audit results"
    atomic_context_decision "Legacy audit complete: $passed passed, $warnings warnings, $critical critical" "audit"

    atomic_success "Phase audit complete"

    return 0
}
