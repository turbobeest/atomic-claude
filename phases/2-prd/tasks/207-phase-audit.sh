#!/bin/bash
#
# Task 207: Phase Audit - PRD Validation
# AI-driven audit selection from turbobeest/audits repository
#
# Features:
#   - AI recommends relevant audits based on PRD content
#   - User reviews and approves audit selection
#   - Supports legacy 94-dimension mode for backward compatibility
#

task_207_phase_audit() {
    source "$ATOMIC_ROOT/lib/audit.sh"
    audit_phase_wrapper 2 "PRD Validation" "_207_legacy_audit"
    return $?
}

# Legacy dimension-based audit for PRD phase
_207_legacy_audit() {
    local audit_dir="$ATOMIC_ROOT/.claude/audit"
    local audit_file="$audit_dir/phase-02-audit.json"
    local prd_file="$ATOMIC_ROOT/docs/prd/PRD.md"
    local prompts_dir="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prompts"

    mkdir -p "$audit_dir" "$prompts_dir"

    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}LEGACY PRD AUDIT (94 Dimensions Available)${NC}                  ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Audit profiles
    echo -e "  ${CYAN}Select audit profile:${NC}"
    echo ""
    echo -e "    ${GREEN}[minimal]${NC}    15 dimensions - Quick check"
    echo -e "    ${GREEN}[standard]${NC}   30 dimensions - Balanced review"
    echo -e "    ${GREEN}[thorough]${NC}   50 dimensions - Detailed audit"
    echo -e "    ${GREEN}[exhaustive]${NC} 94 dimensions - Full audit"
    echo ""

    read -p "  Profile [standard]: " profile
    profile=${profile:-standard}

    local dim_count=30
    case "$profile" in
        minimal) dim_count=15 ;;
        standard) dim_count=30 ;;
        thorough) dim_count=50 ;;
        exhaustive) dim_count=94 ;;
    esac

    echo ""
    echo -e "  ${GREEN}✓${NC} Selected $profile profile ($dim_count dimensions)"
    echo ""

    # Build audit prompt
    local prd_content=""
    [[ -f "$prd_file" ]] && prd_content=$(cat "$prd_file")

    cat > "$prompts_dir/prd-audit.md" << EOF
# Task: Phase 2 PRD Audit (Legacy - $dim_count Dimensions)

You are an independent auditor reviewing the PRD (Product Requirements Document).

## PRD Content

$prd_content

## Audit Dimensions ($profile profile)

Audit the PRD across these categories:
- Requirements completeness
- Acceptance criteria quality
- Non-functional requirements
- Risk identification
- Stakeholder coverage
- Technical feasibility
- Scope clarity

Select $dim_count specific dimensions and audit each.

## Output Format

Output as JSON:
{
  "audit_timestamp": "$(date -Iseconds)",
  "audit_mode": "legacy",
  "profile": "$profile",
  "dimensions_audited": $dim_count,
  "findings": {
    "PRD-XX": {
      "name": "...",
      "status": "PASS|WARNING|CRITICAL",
      "finding": "...",
      "recommendation": "..."
    }
  },
  "summary": {
    "passed": N,
    "warnings": N,
    "critical": N
  },
  "overall_status": "PASS|WARNING|CRITICAL"
}

Output ONLY valid JSON.
EOF

    atomic_waiting "PRD auditor analyzing..."

    local audit_raw="$prompts_dir/audit-raw.json"
    if atomic_invoke "$prompts_dir/prd-audit.md" "$audit_raw" "PRD audit" --model=sonnet; then
        if jq -e . "$audit_raw" &>/dev/null; then
            cp "$audit_raw" "$audit_file"
            atomic_success "Audit complete"
        else
            atomic_warn "Invalid audit output"
            echo '{"overall_status": "WARNING", "summary": {"passed": 0, "warnings": 1, "critical": 0}}' > "$audit_file"
        fi
    else
        atomic_error "Audit failed"
        return 1
    fi

    # Display results
    _audit_display_results "$audit_file"

    return 0
}

# Shared results display function
_audit_display_results() {
    local audit_file="$1"

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

    atomic_context_artifact "phase_audit" "$audit_file" "Phase 2 audit results"
    atomic_success "Phase audit complete"
}
