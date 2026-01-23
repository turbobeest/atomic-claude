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
    # Updated section list for TaskMaster/OpenSpec compatible PRD
    local expected_sections=(
        "Vision"
        "Executive Summary"
        "Technical Architecture"
        "Feature Requirements"
        "Non-Functional"
        "Logical Dependency"
        "Development Phases"
        "Code Structure"
        "TDD"
        "Integration Testing"
        "Documentation"
        "Operational"
        "Risks"
        "Success Metrics"
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

    # Load original requirements from Phase 1 for comparison
    local phase1_dir="$ATOMIC_OUTPUT_DIR/1-discovery"
    local original_requirements=""
    if [[ -f "$phase1_dir/dialogue.json" ]]; then
        original_requirements=$(jq -r '
            .synthesis // {} |
            "Original Vision: " + (.vision.core_problem // "N/A") + "\n" +
            "Original Impact: " + (.impact.primary_impact // "N/A") + "\n" +
            "Original Audience: " + (.audience.primary // "N/A") + "\n" +
            "Non-negotiables: " + ((.non_negotiables // []) | join("; ")) + "\n" +
            "Constraints: " + (.constraints.tech_stack // "N/A")
        ' "$phase1_dir/dialogue.json" 2>/dev/null || echo "Phase 1 requirements not available")
    fi

    # Extract key PRD sections instead of full dump (smarter context management)
    local prd_vision=$(sed -n '/## 0\. Vision/,/## 1\./p' "$prd_file" 2>/dev/null | head -50)
    local prd_tech_stack=$(sed -n '/### 2\.1 Tech Stack/,/### 2\.2/p' "$prd_file" 2>/dev/null | head -30)
    local prd_features=$(sed -n '/## 3\. Feature Requirements/,/## 4\./p' "$prd_file" 2>/dev/null | head -100)
    local prd_nfr=$(sed -n '/## 4\. Non-Functional/,/## 5\./p' "$prd_file" 2>/dev/null | head -50)
    local prd_dependencies=$(sed -n '/## 5\. Logical Dependency/,/## 6\./p' "$prd_file" 2>/dev/null | head -50)
    local prd_metrics=$(sed -n '/## 13\. Success Metrics/,/## 14\./p' "$prd_file" 2>/dev/null | head -30)

    # Count tool-compatibility indicators
    local shall_count=$(grep -c -i '\bSHALL\b' "$prd_file" 2>/dev/null || echo 0)
    local should_count=$(grep -c -i '\bSHOULD\b' "$prd_file" 2>/dev/null || echo 0)
    local when_then_count=$(grep -c -i '\bWHEN\b.*\bTHEN\b' "$prd_file" 2>/dev/null || echo 0)
    local scenario_count=$(grep -c -i 'Scenario:' "$prd_file" 2>/dev/null || echo 0)

    echo -e "  ${DIM}Tool compatibility indicators:${NC}"
    echo -e "    SHALL/SHOULD keywords: $shall_count / $should_count"
    echo -e "    WHEN/THEN scenarios: $when_then_count"
    echo -e "    Scenario blocks: $scenario_count"
    echo ""

    cat > "$prompts_dir/prd-validation.md" << EOF
# Task: PRD Validation (TaskMaster & OpenSpec Compatibility)

You are a PRD validator checking for completeness, testability, consistency, and tool compatibility.

## Original Requirements (from Phase 1 Discovery)

Use these to verify the PRD captures the original intent:

$original_requirements

## PRD Sections to Validate

### Vision Section
$prd_vision

### Tech Stack Section (CRITICAL for TaskMaster)
$prd_tech_stack

### Feature Requirements (sample)
$prd_features

[TRUNCATED - showing first 100 lines of features]

### Non-Functional Requirements
$prd_nfr

### Logical Dependency Chain (CRITICAL for TaskMaster)
$prd_dependencies

### Success Metrics
$prd_metrics

## Tool Compatibility Indicators (detected)

- SHALL keyword count: $shall_count
- SHOULD keyword count: $should_count
- WHEN/THEN patterns: $when_then_count
- Scenario blocks: $scenario_count

## Score Calibration

Use these thresholds consistently:

| Score | Meaning |
|-------|---------|
| 90-100 | Excellent - Ready for TaskMaster/OpenSpec consumption |
| 70-89 | Good - Minor gaps, can proceed with notes |
| 50-69 | Fair - Significant gaps, should address before Phase 3 |
| 0-49 | Poor - Major revision needed |

## Validation Criteria

### 1. Completeness (weight: 25%)
- All 15 sections present with meaningful content (not placeholders)?
- Vision captures the original problem from Phase 1?
- Tech stack is EXPLICIT (not "TBD")?

### 2. Testability (weight: 25%)
- Requirements use RFC 2119 keywords (SHALL/SHOULD/MAY)?
- Functional requirements have WHEN/THEN scenarios?
- NFRs have specific, measurable metrics (not "fast" but "<200ms")?

### 3. TaskMaster Compatibility (weight: 20%)
- Logical Dependency Chain section exists and is populated?
- Tech stack table with specific technologies?
- Development phases defined by scope (not time)?

### 4. OpenSpec Compatibility (weight: 15%)
- Requirements follow "### Requirement: Name" format?
- Each FR has "#### Scenario:" blocks?
- WHEN/THEN format used in scenarios?

### 5. Consistency & Clarity (weight: 15%)
- No contradictions between sections?
- Language is clear and unambiguous?
- Success metrics align with stated goals?

## Output Format

{
    "overall_status": "PASS|WARN|FAIL",
    "overall_score": 0-100,
    "completeness": {
        "status": "PASS|WARN|FAIL",
        "score": 0-100,
        "gaps": ["Specific missing/incomplete sections"],
        "phase1_alignment": "Does PRD capture original vision? Yes/No/Partial + explanation"
    },
    "testability": {
        "status": "PASS|WARN|FAIL",
        "score": 0-100,
        "rfc2119_usage": "Adequate|Insufficient",
        "scenario_coverage": "X of Y FRs have scenarios",
        "issues": ["Specific untestable requirements"]
    },
    "taskmaster_compatibility": {
        "status": "PASS|WARN|FAIL",
        "score": 0-100,
        "has_dependency_chain": true|false,
        "has_explicit_tech_stack": true|false,
        "has_scope_based_phases": true|false,
        "issues": ["Specific TaskMaster compatibility issues"]
    },
    "openspec_compatibility": {
        "status": "PASS|WARN|FAIL",
        "score": 0-100,
        "scenario_format_correct": true|false,
        "issues": ["Specific OpenSpec compatibility issues"]
    },
    "consistency": {
        "status": "PASS|WARN|FAIL",
        "contradictions": ["Any contradictions found"],
        "ambiguous_items": ["Ambiguous statements"]
    },
    "sample_gherkin": [
        "Feature: [name]\n  Scenario: [name]\n    Given [context]\n    When [action]\n    Then [outcome]"
    ],
    "recommendations": ["Prioritized list of improvements"],
    "proceed_recommendation": true|false,
    "proceed_rationale": "Explanation of why safe/unsafe to proceed to Phase 3"
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
            local overall_score=$(jq -r '.overall_score // 0' "$validation_file")
            local completeness=$(jq -r '.completeness.score // 0' "$validation_file")
            local testability=$(jq -r '.testability.score // 0' "$validation_file")
            local taskmaster=$(jq -r '.taskmaster_compatibility.score // 0' "$validation_file")
            local openspec=$(jq -r '.openspec_compatibility.score // 0' "$validation_file")

            local status_color="${GREEN}"
            [[ "$overall" == "WARN" ]] && status_color="${YELLOW}"
            [[ "$overall" == "FAIL" ]] && status_color="${RED}"

            echo -e "  ${status_color}Overall Status: $overall ($overall_score%)${NC}"
            echo ""
            echo -e "  ${CYAN}Validation Scores:${NC}"
            echo -e "    Completeness:            ${BOLD}$completeness%${NC}"
            echo -e "    Testability:             ${BOLD}$testability%${NC}"
            echo -e "    TaskMaster Compatibility: ${BOLD}$taskmaster%${NC}"
            echo -e "    OpenSpec Compatibility:   ${BOLD}$openspec%${NC}"
            echo ""

            # Show Phase 1 alignment
            local phase1_align=$(jq -r '.completeness.phase1_alignment // "Not checked"' "$validation_file")
            echo -e "  ${CYAN}Phase 1 Alignment:${NC} $phase1_align"
            echo ""

            # Show tool compatibility details
            local has_deps=$(jq -r '.taskmaster_compatibility.has_dependency_chain // false' "$validation_file")
            local has_tech=$(jq -r '.taskmaster_compatibility.has_explicit_tech_stack // false' "$validation_file")
            local has_scenarios=$(jq -r '.openspec_compatibility.scenario_format_correct // false' "$validation_file")

            echo -e "  ${CYAN}Tool Readiness:${NC}"
            [[ "$has_deps" == "true" ]] && echo -e "    ${GREEN}✓${NC} Logical Dependency Chain" || echo -e "    ${RED}✗${NC} Logical Dependency Chain missing"
            [[ "$has_tech" == "true" ]] && echo -e "    ${GREEN}✓${NC} Explicit Tech Stack" || echo -e "    ${RED}✗${NC} Tech Stack not explicit"
            [[ "$has_scenarios" == "true" ]] && echo -e "    ${GREEN}✓${NC} OpenSpec Scenarios" || echo -e "    ${YELLOW}○${NC} Scenario format needs work"
            echo ""

            # Show recommendations
            local rec_count=$(jq '.recommendations | length' "$validation_file" 2>/dev/null || echo 0)
            if [[ $rec_count -gt 0 ]]; then
                echo -e "  ${CYAN}Top Recommendations:${NC}"
                jq -r '.recommendations[:5][]' "$validation_file" 2>/dev/null | while read -r rec; do
                    echo -e "    • $rec"
                done
                echo ""
            fi

            # Show proceed recommendation
            local proceed=$(jq -r '.proceed_recommendation // true' "$validation_file")
            local proceed_rationale=$(jq -r '.proceed_rationale // "No rationale provided"' "$validation_file")
            if [[ "$proceed" == "true" ]]; then
                echo -e "  ${GREEN}Proceed Recommendation: YES${NC}"
            else
                echo -e "  ${RED}Proceed Recommendation: NO${NC}"
            fi
            echo -e "  ${DIM}$proceed_rationale${NC}"
            echo ""

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

    # Determine proceed recommendation based on score
    local proceed="true"
    [[ $score -lt 50 ]] && proceed="false"

    jq -n \
        --arg status "$status" \
        --argjson score "$score" \
        --argjson proceed "$proceed" \
        '{
            "overall_status": $status,
            "overall_score": $score,
            "completeness": {
                "status": $status,
                "score": $score,
                "gaps": [],
                "phase1_alignment": "Not checked - fallback validation"
            },
            "testability": {
                "status": "UNKNOWN",
                "score": 0,
                "rfc2119_usage": "Not checked",
                "scenario_coverage": "Not checked",
                "issues": ["Automated testability check not performed"]
            },
            "taskmaster_compatibility": {
                "status": "UNKNOWN",
                "score": 0,
                "has_dependency_chain": false,
                "has_explicit_tech_stack": false,
                "has_scope_based_phases": false,
                "issues": ["TaskMaster compatibility not checked - fallback validation"]
            },
            "openspec_compatibility": {
                "status": "UNKNOWN",
                "score": 0,
                "scenario_format_correct": false,
                "issues": ["OpenSpec compatibility not checked - fallback validation"]
            },
            "consistency": {
                "status": "UNKNOWN",
                "contradictions": [],
                "ambiguous_items": []
            },
            "sample_gherkin": [],
            "recommendations": ["Manual review recommended", "Run full LLM validation for tool compatibility checks"],
            "proceed_recommendation": $proceed,
            "proceed_rationale": "Fallback validation based on structural checks only. Full LLM validation recommended for tool compatibility assessment.",
            "note": "Fallback validation - LLM validation not performed"
        }' > "$validation_file"
}
