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
# Includes a validate-revise loop: if the user chooses "revise",
# the LLM-assisted revision flow (206b) runs, then validation
# re-runs automatically.
#

task_206_prd_validation() {
    local prd_file="$ATOMIC_ROOT/docs/prd/PRD.md"
    local validation_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prd-validation.json"
    local prompts_dir="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prompts"

    atomic_step "PRD Validation"

    mkdir -p "$prompts_dir"

    echo ""
    echo -e "${DIM}  +----------------------------------------------------------+${NC}"
    echo -e "${DIM}  | Validating PRD for completeness and testability.          |${NC}"
    echo -e "${DIM}  | Revision loop: validate -> review -> revise -> re-validate|${NC}"
    echo -e "${DIM}  +----------------------------------------------------------+${NC}"
    echo ""

    # Check PRD exists
    if [[ ! -f "$prd_file" ]]; then
        atomic_error "PRD file not found: $prd_file"
        return 1
    fi

    # ═══════════════════════════════════════════════════════════════════════════
    # VALIDATE-REVISE LOOP
    # ═══════════════════════════════════════════════════════════════════════════

    local iteration=0

    while true; do
        ((iteration++))

        if [[ $iteration -gt 1 ]]; then
            echo ""
            echo -e "${CYAN}+----------------------------------------------------------+${NC}"
            echo -e "${CYAN}|${NC} ${BOLD}RE-VALIDATION (pass $iteration)${NC}"
            echo -e "${CYAN}+----------------------------------------------------------+${NC}"
            echo ""
        fi

        # ═══════════════════════════════════════════════════════════════════
        # STRUCTURAL VALIDATION
        # ═══════════════════════════════════════════════════════════════════

        echo -e "${CYAN}+----------------------------------------------------------+${NC}"
        echo -e "${CYAN}|${NC} ${BOLD}STRUCTURAL VALIDATION${NC}"
        echo -e "${CYAN}+----------------------------------------------------------+${NC}"
        echo ""

        local sections_found=0
        local sections_missing=()
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
                echo -e "    ${GREEN}v${NC} $section"
                ((sections_found++))
            else
                echo -e "    ${YELLOW}o${NC} $section (not found)"
                sections_missing+=("$section")
            fi
        done

        local prd_lines
        prd_lines=$(wc -l < "$prd_file" 2>/dev/null || echo 0)

        echo ""
        echo -e "  ${DIM}Sections: $sections_found/15 found | PRD: $prd_lines lines${NC}"
        echo ""

        # ═══════════════════════════════════════════════════════════════════
        # STRUCTURAL GATE — blocks LLM validation if PRD is obviously wrong
        # ═══════════════════════════════════════════════════════════════════

        if [[ $sections_found -lt 10 || $prd_lines -lt 100 ]]; then
            echo -e "  ${RED}+----------------------------------------------------------+${NC}"
            echo -e "  ${RED}|${NC} ${BOLD}STRUCTURAL GATE FAILED${NC}"
            echo -e "  ${RED}+----------------------------------------------------------+${NC}"
            echo ""
            echo -e "  ${RED}The PRD does not meet minimum structural requirements.${NC}"
            echo -e "  ${RED}LLM content validation is blocked to avoid wasting resources.${NC}"
            echo ""
            if [[ $prd_lines -lt 100 ]]; then
                echo -e "    ${RED}x${NC} PRD is only $prd_lines lines (expected 200+)"
            fi
            if [[ $sections_found -lt 10 ]]; then
                echo -e "    ${RED}x${NC} Only $sections_found/15 sections found (need at least 10)"
            fi
            if [[ ${#sections_missing[@]} -gt 0 ]]; then
                echo -e ""
                echo -e "  ${YELLOW}Missing sections:${NC}"
                for missing in "${sections_missing[@]}"; do
                    echo -e "    ${YELLOW}o${NC} $missing"
                done
            fi
            echo ""

            # Check if a real PRD exists elsewhere (common authoring error)
            local alt_prd=""
            for candidate in \
                "$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/PRD.md" \
                "$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prompts/prd-output.md" \
                "$ATOMIC_ROOT/../claude-local/PRD.md" \
                "$ATOMIC_ROOT/PRD.md"; do
                if [[ -f "$candidate" ]]; then
                    local cand_lines
                    cand_lines=$(wc -l < "$candidate" 2>/dev/null || echo 0)
                    if [[ $cand_lines -gt $prd_lines ]]; then
                        alt_prd="$candidate ($cand_lines lines)"
                        break
                    fi
                fi
            done

            if [[ -n "$alt_prd" ]]; then
                echo -e "  ${CYAN}Possible real PRD found:${NC}"
                echo -e "    ${GREEN}->  $alt_prd${NC}"
                echo ""
            fi

            echo -e "  ${CYAN}Options:${NC}"
            echo -e "    ${YELLOW}[back]${NC}     Return to PRD authoring (task 205)"
            echo -e "    ${CYAN}[path]${NC}     Provide path to real PRD file"
            echo -e "    ${DIM}[skip]${NC}     Skip gate and run LLM validation anyway"
            echo ""

    atomic_drain_stdin
            read -e -p "  Choice [back]: " gate_choice || true
            gate_choice=${gate_choice:-back}

            case "$gate_choice" in
                back|b)
                    atomic_warn "Returning to PRD authoring"
                    return 1
                    ;;
                path|p)
                    read -e -p "  Path to PRD file: " new_path || true
                    if [[ -f "$new_path" ]]; then
                        local new_lines
                        new_lines=$(wc -l < "$new_path")
                        cp "$prd_file" "${prd_file}.stub"
                        cp "$new_path" "$prd_file"
                        echo -e "  ${GREEN}v${NC} PRD replaced ($new_lines lines). Re-validating..."
                        echo ""
                        continue  # restart the validation loop
                    else
                        echo -e "  ${RED}File not found: $new_path${NC}"
                        return 1
                    fi
                    ;;
                skip|s)
                    echo -e "  ${YELLOW}Skipping structural gate...${NC}"
                    echo ""
                    ;;
                *)
                    atomic_warn "Returning to PRD authoring"
                    return 1
                    ;;
            esac
        fi

        # ═══════════════════════════════════════════════════════════════════
        # CONTENT VALIDATION (LLM)
        # ═══════════════════════════════════════════════════════════════════

        echo -e "${CYAN}+----------------------------------------------------------+${NC}"
        echo -e "${CYAN}|${NC} ${BOLD}CONTENT VALIDATION${NC}"
        echo -e "${CYAN}+----------------------------------------------------------+${NC}"
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

        # Extract key PRD sections
        local prd_vision prd_tech_stack prd_features prd_nfr prd_dependencies prd_metrics
        prd_vision=$(sed -n '/## 0\. Vision/,/## 1\./p' "$prd_file" 2>/dev/null | head -50)
        prd_tech_stack=$(sed -n '/### 2\.1 Tech Stack/,/### 2\.2/p' "$prd_file" 2>/dev/null | head -30)
        prd_features=$(sed -n '/## 3\. Feature Requirements/,/## 4\./p' "$prd_file" 2>/dev/null | head -100)
        prd_nfr=$(sed -n '/## 4\. Non-Functional/,/## 5\./p' "$prd_file" 2>/dev/null | head -50)
        prd_dependencies=$(sed -n '/## 5\. Logical Dependency/,/## 6\./p' "$prd_file" 2>/dev/null | head -50)
        prd_metrics=$(sed -n '/## 13\. Success Metrics/,/## 14\./p' "$prd_file" 2>/dev/null | head -30)

        # Count tool-compatibility indicators
        local shall_count should_count when_then_count scenario_count
        shall_count=$(grep -c -i '\bSHALL\b' "$prd_file" 2>/dev/null || echo 0)
        should_count=$(grep -c -i '\bSHOULD\b' "$prd_file" 2>/dev/null || echo 0)
        when_then_count=$(grep -c -i '\bWHEN\b.*\bTHEN\b' "$prd_file" 2>/dev/null || echo 0)
        scenario_count=$(grep -c -i 'Scenario:' "$prd_file" 2>/dev/null || echo 0)

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

## CRITICAL: Output Format

You MUST output ONLY valid JSON matching the schema below. No prose, no markdown fences, no commentary.
If you cannot complete the full analysis, output the JSON with partial results rather than text.

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
    "recommendations": ["Prioritized list: P0, P1, P2, P3 prefix"],
    "proceed_recommendation": true|false,
    "proceed_rationale": "Explanation of why safe/unsafe to proceed to Phase 3"
}

Output ONLY the JSON object above. No other text.
EOF

        atomic_waiting "prd-validator analyzing..."

        local raw_validation="$prompts_dir/validation-raw.json"
        local saved_turns="${CLAUDE_MAX_TURNS:-10}"
        export CLAUDE_MAX_TURNS=15
        local validation_ok=false

        if atomic_invoke "$prompts_dir/prd-validation.md" "$raw_validation" "PRD validation" --model=opus --timeout=1800; then
            # Attempt JSON recovery pipeline
            if _206_recover_json "$raw_validation" "$prompts_dir"; then
                validation_ok=true
            fi
        fi

        export CLAUDE_MAX_TURNS="$saved_turns"

        if $validation_ok && jq -e . "$raw_validation" &>/dev/null; then
            cp "$raw_validation" "$validation_file"

            # Display results
            local overall overall_score completeness testability taskmaster openspec
            overall=$(jq -r '.overall_status // "UNKNOWN"' "$validation_file")
            overall_score=$(jq -r '.overall_score // 0' "$validation_file")
            completeness=$(jq -r '.completeness.score // 0' "$validation_file")
            testability=$(jq -r '.testability.score // 0' "$validation_file")
            taskmaster=$(jq -r '.taskmaster_compatibility.score // 0' "$validation_file")
            openspec=$(jq -r '.openspec_compatibility.score // 0' "$validation_file")

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

            # Phase 1 alignment
            local phase1_align
            phase1_align=$(jq -r '.completeness.phase1_alignment // "Not checked"' "$validation_file")
            echo -e "  ${CYAN}Phase 1 Alignment:${NC} $phase1_align"
            echo ""

            # Tool readiness
            local has_deps has_tech has_scenarios
            has_deps=$(jq -r '.taskmaster_compatibility.has_dependency_chain // false' "$validation_file")
            has_tech=$(jq -r '.taskmaster_compatibility.has_explicit_tech_stack // false' "$validation_file")
            has_scenarios=$(jq -r '.openspec_compatibility.scenario_format_correct // false' "$validation_file")

            echo -e "  ${CYAN}Tool Readiness:${NC}"
            [[ "$has_deps" == "true" ]] && echo -e "    ${GREEN}v${NC} Logical Dependency Chain" || echo -e "    ${RED}x${NC} Logical Dependency Chain missing"
            [[ "$has_tech" == "true" ]] && echo -e "    ${GREEN}v${NC} Explicit Tech Stack" || echo -e "    ${RED}x${NC} Tech Stack not explicit"
            [[ "$has_scenarios" == "true" ]] && echo -e "    ${GREEN}v${NC} OpenSpec Scenarios" || echo -e "    ${YELLOW}o${NC} Scenario format needs work"
            echo ""

            # Recommendations
            local rec_count
            rec_count=$(jq '.recommendations | length' "$validation_file" 2>/dev/null || echo 0)
            if [[ $rec_count -gt 0 ]]; then
                echo -e "  ${CYAN}Top Recommendations:${NC}"
                jq -r '.recommendations[:5][]' "$validation_file" 2>/dev/null | while read -r rec; do
                    echo -e "    - $rec"
                done
                echo ""
            fi

            # Proceed recommendation
            local proceed proceed_rationale
            proceed=$(jq -r '.proceed_recommendation // true' "$validation_file")
            proceed_rationale=$(jq -r '.proceed_rationale // "No rationale provided"' "$validation_file")
            if [[ "$proceed" == "true" ]]; then
                echo -e "  ${GREEN}Proceed Recommendation: YES${NC}"
            else
                echo -e "  ${RED}Proceed Recommendation: NO${NC}"
            fi
            echo -e "  ${DIM}$proceed_rationale${NC}"
            echo ""

            # Sample Gherkin
            local gherkin_count
            gherkin_count=$(jq '.sample_gherkin | length' "$validation_file" 2>/dev/null || echo 0)
            if [[ $gherkin_count -gt 0 ]]; then
                echo -e "  ${CYAN}Sample Gherkin Scenario:${NC}"
                echo ""
                jq -r '.sample_gherkin[0]' "$validation_file" 2>/dev/null | sed 's/^/    /'
                echo ""
            fi
        else
            atomic_warn "Could not produce valid validation JSON"
            _206_create_fallback_validation "$validation_file" "$sections_found"
        fi

        # ═══════════════════════════════════════════════════════════════════
        # VALIDATION DECISION
        # ═══════════════════════════════════════════════════════════════════

        local overall overall_score proceed
        overall=$(jq -r '.overall_status // "UNKNOWN"' "$validation_file" 2>/dev/null)
        overall_score=$(jq -r '.overall_score // 0' "$validation_file" 2>/dev/null)
        proceed=$(jq -r '.proceed_recommendation // true' "$validation_file" 2>/dev/null)

        echo -e "${DIM}------------------------------------------------------------${NC}"
        echo ""

        # Summary box
        local status_color="${GREEN}"
        [[ "$overall" == "WARN" || "$overall" == "WARNING" ]] && status_color="${YELLOW}"
        [[ "$overall" == "FAIL" ]] && status_color="${RED}"

        echo -e "  ${CYAN}+----------------------------------------------------------+${NC}"
        echo -e "  ${CYAN}|${NC} ${BOLD}VALIDATION SUMMARY${NC}"
        echo -e "  ${CYAN}+----------------------------------------------------------+${NC}"
        echo ""
        echo -e "  ${status_color}*${NC} Status: ${status_color}${BOLD}$overall${NC} ($overall_score%)"
        echo ""

        # Contradictions
        local contradiction_count
        contradiction_count=$(jq '.consistency.contradictions | length' "$validation_file" 2>/dev/null || echo 0)
        if [[ "$contradiction_count" -gt 0 ]]; then
            echo -e "  ${RED}Contradictions found ($contradiction_count):${NC}"
            jq -r '.consistency.contradictions[]' "$validation_file" 2>/dev/null | while IFS= read -r item; do
                echo -e "    ${RED}x${NC} $item"
            done
            echo ""
        fi

        # Recommendations by priority
        local rec_count
        rec_count=$(jq '.recommendations | length' "$validation_file" 2>/dev/null || echo 0)
        if [[ "$rec_count" -gt 0 ]]; then
            echo -e "  ${CYAN}Recommended Actions:${NC}"
            echo ""
            jq -r '.recommendations[]' "$validation_file" 2>/dev/null | while IFS= read -r rec; do
                local priority_color="${DIM}"
                [[ "$rec" == P0:* ]] && priority_color="${RED}"
                [[ "$rec" == P1:* ]] && priority_color="${YELLOW}"
                [[ "$rec" == P2:* ]] && priority_color="${CYAN}"
                echo -e "    ${priority_color}->${NC} $rec"
            done
            echo ""
        fi

        # Proceed rationale
        local proceed_rationale
        proceed_rationale=$(jq -r '.proceed_rationale // ""' "$validation_file" 2>/dev/null)
        if [[ -n "$proceed_rationale" ]]; then
            if [[ "$proceed" == "true" ]]; then
                echo -e "  ${GREEN}v Recommendation: PROCEED${NC}"
            else
                echo -e "  ${RED}x Recommendation: DO NOT PROCEED${NC}"
            fi
            echo -e "  ${DIM}$proceed_rationale${NC}"
            echo ""
        fi

        echo -e "${DIM}------------------------------------------------------------${NC}"
        echo ""

        # Decision: revise or continue (always offer both)
        local val_choice=""

        echo -e "  ${CYAN}Options:${NC}"
        if [[ "$overall" == "FAIL" || "$proceed" == "false" ]]; then
            echo -e "    ${GREEN}[revise]${NC}    Fix validation issues now (targeted LLM revision)"
            echo -e "    ${YELLOW}[continue]${NC}  Proceed to Review & Refinement (collaborative LLM editing before approval)"
            echo ""
    atomic_drain_stdin
            read -e -p "  Choice [revise]: " val_choice || true
            val_choice=${val_choice:-revise}
        else
            echo -e "    ${GREEN}[continue]${NC}  Proceed to Review & Refinement (collaborative LLM editing before approval)"
            echo -e "    ${YELLOW}[revise]${NC}    Fix validation issues now (targeted LLM revision)"
            echo ""
    atomic_drain_stdin
            read -e -p "  Choice [continue]: " val_choice || true
            val_choice=${val_choice:-continue}
        fi

        # Handle choice
        if [[ "$val_choice" == "revise" ]]; then
            # Call the LLM-assisted revision flow
            if prd_revision_flow "$validation_file" "$prd_file"; then
                echo -e "  ${CYAN}Revision complete. Re-validating...${NC}"
                echo ""
            else
                echo -e "  ${YELLOW}Revision did not produce changes. Re-validating anyway...${NC}"
                echo ""
            fi
            continue  # loop back to re-validate
        fi

        # User chose "continue" or PASS auto-continued
        break

    done  # end validate-revise loop

    # ═══════════════════════════════════════════════════════════════════════════
    # FINALIZE
    # ═══════════════════════════════════════════════════════════════════════════

    atomic_context_artifact "prd-validation" "$validation_file" "PRD validation results"
    atomic_context_decision "PRD validation: $overall ($overall_score%)" "validation"

    atomic_success "PRD validation complete"

    return 0
}

# ═══════════════════════════════════════════════════════════════════════════════
# JSON Recovery Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

# Attempt to recover valid JSON from LLM output
# Tries: 1) already valid, 2) atomic_json_fix, 3) Python extraction, 4) Haiku re-parse
# Writes recovered JSON back to the file on success
# Returns: 0 if valid JSON recovered, 1 if all attempts failed
_206_recover_json() {
    local raw_file="$1"
    local prompts_dir="$2"

    # Already valid?
    if jq -e . "$raw_file" &>/dev/null; then
        return 0
    fi

    # Step 1: atomic_json_fix (strips markdown fences, finds leading {)
    local fixed_json
    fixed_json=$(atomic_json_fix "$raw_file")
    if echo "$fixed_json" | jq -e . &>/dev/null; then
        echo "$fixed_json" > "$raw_file"
        return 0
    fi

    # Step 2: Python extraction (find outermost { to last })
    if command -v python3 &>/dev/null; then
        local py_extracted
        py_extracted=$(python3 -c "
import json, sys
content = open(sys.argv[1]).read()
start = content.find('{')
end = content.rfind('}')
if start >= 0 and end > start:
    candidate = content[start:end+1]
    try:
        obj = json.loads(candidate)
        print(json.dumps(obj))
    except json.JSONDecodeError:
        sys.exit(1)
else:
    sys.exit(1)
" "$raw_file" 2>/dev/null)
        if [[ $? -eq 0 ]] && echo "$py_extracted" | jq -e . &>/dev/null; then
            echo "$py_extracted" > "$raw_file"
            return 0
        fi
    fi

    # Step 3: Re-invoke with Haiku to convert text analysis to JSON
    local raw_text
    raw_text=$(cat "$raw_file")
    local reparse_prompt="$prompts_dir/validation-reparse.md"

    cat > "$reparse_prompt" << REPARSE_EOF
# Convert Validation Analysis to JSON

The following text is a PRD validation analysis. Convert it to the exact JSON format below.
Extract scores, issues, and recommendations from the text. Infer scores if not explicitly stated.

## Text to Convert

$raw_text

## Required JSON Format

Output ONLY this JSON structure, no other text:

{
    "overall_status": "PASS or WARN or FAIL",
    "overall_score": 0-100,
    "completeness": {
        "status": "PASS or WARN or FAIL",
        "score": 0-100,
        "gaps": [],
        "phase1_alignment": "explanation"
    },
    "testability": {
        "status": "PASS or WARN or FAIL",
        "score": 0-100,
        "rfc2119_usage": "Adequate or Insufficient",
        "scenario_coverage": "description",
        "issues": []
    },
    "taskmaster_compatibility": {
        "status": "PASS or WARN or FAIL",
        "score": 0-100,
        "has_dependency_chain": true,
        "has_explicit_tech_stack": true,
        "has_scope_based_phases": true,
        "issues": []
    },
    "openspec_compatibility": {
        "status": "PASS or WARN or FAIL",
        "score": 0-100,
        "scenario_format_correct": true,
        "issues": []
    },
    "consistency": {
        "status": "PASS or WARN or FAIL",
        "contradictions": [],
        "ambiguous_items": []
    },
    "sample_gherkin": [],
    "recommendations": [],
    "proceed_recommendation": true,
    "proceed_rationale": "explanation"
}
REPARSE_EOF

    atomic_info "Validation output was not JSON. Re-parsing with LLM..."

    local reparse_output="$prompts_dir/validation-reparsed.json"
    local saved_turns="${CLAUDE_MAX_TURNS:-10}"
    export CLAUDE_MAX_TURNS=5

    if atomic_invoke "$reparse_prompt" "$reparse_output" "JSON re-parse" --timeout=120; then
        export CLAUDE_MAX_TURNS="$saved_turns"

        # Try to extract JSON from re-parse output
        if jq -e . "$reparse_output" &>/dev/null; then
            cp "$reparse_output" "$raw_file"
            return 0
        fi

        # One more try with atomic_json_fix on the re-parse output
        fixed_json=$(atomic_json_fix "$reparse_output")
        if echo "$fixed_json" | jq -e . &>/dev/null; then
            echo "$fixed_json" > "$raw_file"
            return 0
        fi

        # Python extraction on re-parse output
        if command -v python3 &>/dev/null; then
            py_extracted=$(python3 -c "
import json, sys
content = open(sys.argv[1]).read()
start = content.find('{')
end = content.rfind('}')
if start >= 0 and end > start:
    candidate = content[start:end+1]
    try:
        obj = json.loads(candidate)
        print(json.dumps(obj))
    except json.JSONDecodeError:
        sys.exit(1)
else:
    sys.exit(1)
" "$reparse_output" 2>/dev/null)
            if [[ $? -eq 0 ]] && echo "$py_extracted" | jq -e . &>/dev/null; then
                echo "$py_extracted" > "$raw_file"
                return 0
            fi
        fi
    else
        export CLAUDE_MAX_TURNS="$saved_turns"
    fi

    # All recovery attempts failed
    atomic_warn "All JSON recovery attempts failed"
    return 1
}

# Create fallback validation based on structural checks
_206_create_fallback_validation() {
    local validation_file="$1"
    local sections_found="$2"

    local score=$((sections_found * 100 / 15))
    local status="PASS"
    [[ $score -lt 80 ]] && status="WARN"
    [[ $score -lt 50 ]] && status="FAIL"

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
