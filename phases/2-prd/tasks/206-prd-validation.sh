#!/bin/bash
#
# Task 206: PRD Validation
# Validate PRD completeness, testability, and consistency
#
# Checks:
#   - All 15 sections present
#   - Requirements are testable
#   - No internal contradictions
#   - Gherkin scenarios generatable
#

task_206_prd_validation() {
    local prd_file="$ATOMIC_ROOT/docs/prd/PRD.md"
    local validation_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prd-validation.json"
    local prompts_dir="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prompts"

    atomic_step "PRD Validation"

    mkdir -p "$prompts_dir"

    echo ""
    echo -e "${DIM}  ┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${DIM}  │ Validating PRD for completeness and testability.       │${NC}"
    echo -e "${DIM}  └─────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # Check PRD exists
    if [[ ! -f "$prd_file" ]]; then
        atomic_error "PRD file not found: $prd_file"
        return 1
    fi

    # ═══════════════════════════════════════════════════════════════════════════
    # STRUCTURAL VALIDATION
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}STRUCTURAL VALIDATION${NC}                                     ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local sections_found=0
    local sections_missing=()
    local expected_sections=(
        "Vision"
        "Executive Summary"
        "System Architecture"
        "Feature Requirements"
        "Non-Functional"
        "Code Structure"
        "TDD"
        "Integration Testing"
        "Documentation"
        "Operational"
        "Risks"
        "Success Metrics"
        "Task Decomposition"
        "Subtask"
        "Approval"
    )

    for section in "${expected_sections[@]}"; do
        if grep -qi "$section" "$prd_file" 2>/dev/null; then
            echo -e "    ${GREEN}✓${NC} $section"
            ((sections_found++))
        else
            echo -e "    ${YELLOW}○${NC} $section (not found)"
            sections_missing+=("$section")
        fi
    done

    echo ""
    echo -e "  ${DIM}Sections: $sections_found/15 found${NC}"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # CONTENT VALIDATION (LLM)
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}CONTENT VALIDATION${NC}                                        ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local prd_content=$(cat "$prd_file")

    cat > "$prompts_dir/prd-validation.md" << EOF
# Task: PRD Validation

You are a PRD validator checking for completeness, testability, and consistency.

## PRD Content

$prd_content

## Validation Criteria

1. **Completeness**: Are all sections filled with meaningful content (not just placeholders)?
2. **Testability**: Are requirements specific enough to write tests for?
3. **Consistency**: Are there any contradictions between sections?
4. **Clarity**: Is the language clear and unambiguous?
5. **Measurability**: Are success metrics quantifiable?

## Output Format

{
    "overall_status": "PASS|WARN|FAIL",
    "completeness": {
        "status": "PASS|WARN|FAIL",
        "score": 0-100,
        "gaps": ["list of missing/incomplete sections"]
    },
    "testability": {
        "status": "PASS|WARN|FAIL",
        "score": 0-100,
        "issues": ["list of untestable requirements"]
    },
    "consistency": {
        "status": "PASS|WARN|FAIL",
        "contradictions": ["list of any contradictions found"]
    },
    "clarity": {
        "status": "PASS|WARN|FAIL",
        "ambiguous_items": ["list of ambiguous statements"]
    },
    "sample_gherkin": [
        "Feature: ...\n  Scenario: ...\n    Given...\n    When...\n    Then..."
    ],
    "recommendations": ["list of improvement recommendations"]
}

Output ONLY valid JSON.
EOF

    atomic_waiting "prd-validator analyzing..."

    local raw_validation="$prompts_dir/validation-raw.json"
    if atomic_invoke "$prompts_dir/prd-validation.md" "$raw_validation" "PRD validation" --model=sonnet; then
        if jq -e . "$raw_validation" &>/dev/null; then
            cp "$raw_validation" "$validation_file"

            # Display results
            local overall=$(jq -r '.overall_status // "UNKNOWN"' "$validation_file")
            local completeness=$(jq -r '.completeness.score // 0' "$validation_file")
            local testability=$(jq -r '.testability.score // 0' "$validation_file")

            local status_color="${GREEN}"
            [[ "$overall" == "WARN" ]] && status_color="${YELLOW}"
            [[ "$overall" == "FAIL" ]] && status_color="${RED}"

            echo -e "  ${status_color}Overall Status: $overall${NC}"
            echo ""
            echo -e "  Completeness:  ${BOLD}$completeness%${NC}"
            echo -e "  Testability:   ${BOLD}$testability%${NC}"
            echo ""

            # Show recommendations
            local rec_count=$(jq '.recommendations | length' "$validation_file" 2>/dev/null || echo 0)
            if [[ $rec_count -gt 0 ]]; then
                echo -e "  ${CYAN}Recommendations:${NC}"
                jq -r '.recommendations[:5][]' "$validation_file" 2>/dev/null | while read -r rec; do
                    echo -e "    • $rec"
                done
                echo ""
            fi

            # Show sample Gherkin
            local gherkin_count=$(jq '.sample_gherkin | length' "$validation_file" 2>/dev/null || echo 0)
            if [[ $gherkin_count -gt 0 ]]; then
                echo -e "  ${CYAN}Sample Gherkin Scenario:${NC}"
                echo ""
                jq -r '.sample_gherkin[0]' "$validation_file" 2>/dev/null | sed 's/^/    /'
                echo ""
            fi
        else
            atomic_warn "Invalid validation output"
            _206_create_fallback_validation "$validation_file" "$sections_found"
        fi
    else
        atomic_warn "Validation failed - using structural results only"
        _206_create_fallback_validation "$validation_file" "$sections_found"
    fi

    # ═══════════════════════════════════════════════════════════════════════════
    # VALIDATION DECISION
    # ═══════════════════════════════════════════════════════════════════════════

    local overall=$(jq -r '.overall_status // "UNKNOWN"' "$validation_file")

    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    if [[ "$overall" == "FAIL" ]]; then
        echo -e "  ${RED}Validation found critical issues.${NC}"
        echo ""
        echo -e "  ${CYAN}Options:${NC}"
        echo -e "    ${GREEN}[revise]${NC}   Go back and revise PRD"
        echo -e "    ${YELLOW}[continue]${NC} Continue with issues noted"
        echo ""

        read -p "  Choice [revise]: " val_choice
        val_choice=${val_choice:-revise}

        if [[ "$val_choice" == "revise" ]]; then
            return 1
        fi
    fi

    atomic_context_artifact "prd-validation" "$validation_file" "PRD validation results"
    atomic_context_decision "PRD validation: $overall" "validation"

    atomic_success "PRD validation complete"

    return 0
}

# Create fallback validation based on structural checks
_206_create_fallback_validation() {
    local validation_file="$1"
    local sections_found="$2"

    local score=$((sections_found * 100 / 15))
    local status="PASS"
    [[ $score -lt 80 ]] && status="WARN"
    [[ $score -lt 50 ]] && status="FAIL"

    jq -n \
        --arg status "$status" \
        --argjson score "$score" \
        '{
            "overall_status": $status,
            "completeness": {
                "status": $status,
                "score": $score,
                "gaps": []
            },
            "testability": {
                "status": "UNKNOWN",
                "score": 0,
                "issues": ["Automated testability check not performed"]
            },
            "consistency": {
                "status": "UNKNOWN",
                "contradictions": []
            },
            "clarity": {
                "status": "UNKNOWN",
                "ambiguous_items": []
            },
            "sample_gherkin": [],
            "recommendations": ["Manual review recommended"],
            "note": "Fallback validation - LLM validation not performed"
        }' > "$validation_file"
}
