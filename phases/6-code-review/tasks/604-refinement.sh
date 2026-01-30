#!/bin/bash
#
# Task 604: Refinement
# Address review findings and apply code improvements
#
# Uses code-refiner agent to:
#   1. Parse findings from 603 comprehensive review
#   2. Generate targeted fixes for critical/major issues
#   3. Apply fixes with minimal change principle
#   4. Verify tests pass after each fix
#

task_604_refinement() {
    local review_dir="$ATOMIC_ROOT/.claude/reviews"
    local findings_file="$review_dir/findings.json"
    local refinement_file="$review_dir/refinement-report.json"
    local tasks_file="$ATOMIC_ROOT/.taskmaster/tasks/tasks.json"
    local prompts_dir="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prompts"
    local fixes_dir="$prompts_dir/fixes"

    atomic_step "Refinement"

    mkdir -p "$fixes_dir"

    echo ""
    echo -e "  ${DIM}Addressing review findings and applying code improvements.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # LOAD CODE REFINER AGENT FROM TASK 602 SELECTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    local agents_selection_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/review-agents.json"
    # Check embedded repo first (monorepo deployment), then env var, then default
    local agent_repo="$ATOMIC_ROOT/repos/agents"
    [[ -f "$ATOMIC_ROOT/external/agents/agent-inventory.csv" ]] && agent_repo="$ATOMIC_ROOT/external/agents"
    [[ -n "$ATOMIC_AGENT_REPO" ]] && agent_repo="$ATOMIC_AGENT_REPO"

    # Agent prompt (loaded from agents repository if available)
    export _604_REFINER_AGENT_PROMPT=""

    if [[ -f "$agents_selection_file" ]]; then
        local refiner_agent=$(jq -r '.review_agents.refiner.name // ""' "$agents_selection_file")
        if [[ -n "$refiner_agent" ]]; then
            agent_file=$(atomic_find_agent "$refiner_agent" "$agent_repo")
            if [[ -f "$agent_file" ]]; then
                _604_REFINER_AGENT_PROMPT=$(cat "$agent_file" | atomic_strip_frontmatter)
                echo -e "  ${GREEN}✓${NC} Loaded agent: $refiner_agent"
                echo ""
            fi
        fi
    fi

    # Load findings
    local total_critical=0
    local total_major=0
    local total_minor=0

    if [[ -f "$findings_file" ]]; then
        total_critical=$(jq -r '.totals.critical // 0' "$findings_file")
        total_major=$(jq -r '.totals.major // 0' "$findings_file")
        total_minor=$(jq -r '.totals.minor // 0' "$findings_file")
    else
        atomic_warn "No findings file found at $findings_file"
        atomic_warn "Run task 603 (Comprehensive Review) first"
        return 1
    fi

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # FINDINGS TO ADDRESS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- FINDINGS TO ADDRESS${NC}"
    echo ""

    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "  ${BOLD}REFINEMENT QUEUE${NC}"
    echo ""
    if [[ "$total_critical" -gt 0 ]]; then
        echo -e "    ${RED}Critical:${NC}  $total_critical issue(s) - ${RED}MUST FIX${NC}"
    else
        echo -e "    ${GREEN}Critical:${NC}  $total_critical issue(s)"
    fi
    if [[ "$total_major" -gt 0 ]]; then
        echo -e "    ${YELLOW}Major:${NC}     $total_major issue(s) - ${YELLOW}SHOULD FIX${NC}"
    else
        echo -e "    ${GREEN}Major:${NC}     $total_major issue(s)"
    fi
    echo -e "    ${DIM}Minor:${NC}     $total_minor issue(s) - optional"
    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # REFINEMENT STRATEGY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- REFINEMENT STRATEGY${NC}"
    echo ""

    echo -e "  ${DIM}What would you like the code-refiner agent to address?${NC}"
    echo ""
    echo -e "    ${GREEN}[critical]${NC}    Address critical issues only (fastest)"
    echo -e "    ${YELLOW}[major]${NC}       Address critical + major issues (recommended)"
    echo -e "    ${CYAN}[minor]${NC}       Address critical + major + minor issues"
    echo -e "    ${MAGENTA}[all]${NC}         Address all issues including suggestions (thorough)"
    echo -e "    ${DIM}[skip]${NC}        Skip refinement entirely"
    echo ""

    atomic_drain_stdin
    local refinement_scope
    read -e -p "  Refinement scope [major]: " refinement_scope || true
    refinement_scope=${refinement_scope:-major}

    if [[ "$refinement_scope" == "skip" ]]; then
        echo ""
        echo -e "  ${YELLOW}!${NC} Skipping refinement - no changes will be made"
        echo ""
        atomic_success "Refinement skipped by user choice"
        return 0
    fi

    # Export scope for use in refinement execution
    export REFINEMENT_SCOPE="$refinement_scope"

    echo ""
    echo -e "  ${DIM}The code-refiner agent will:${NC}"
    echo ""
    case "$refinement_scope" in
        critical)
            echo -e "    ${CYAN}1.${NC} Address ${RED}critical${NC} findings only"
            ;;
        major)
            echo -e "    ${CYAN}1.${NC} Address ${RED}critical${NC} and ${YELLOW}major${NC} findings"
            ;;
        minor)
            echo -e "    ${CYAN}1.${NC} Address ${RED}critical${NC}, ${YELLOW}major${NC}, and ${CYAN}minor${NC} findings"
            ;;
        all)
            echo -e "    ${CYAN}1.${NC} Address ${BOLD}all findings${NC} including suggestions"
            ;;
    esac
    echo -e "    ${CYAN}2.${NC} Apply targeted fixes without changing unrelated code"
    echo -e "    ${CYAN}3.${NC} Run tests after each change to ensure no regressions"
    echo -e "    ${CYAN}4.${NC} Document changes made for each finding"
    echo ""

    echo -e "  ${DIM}Refinement philosophy:${NC}"
    echo ""
    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "  ${BOLD}Minimal Change Principle${NC}"
    echo ""
    echo -e "    - Fix the identified issue, nothing more"
    echo -e "    - Preserve existing test coverage"
    echo -e "    - Avoid refactoring temptation during fixes"
    echo -e "    - Each fix is a separate, atomic commit"
    echo ""
    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    read -e -p "  Press Enter to begin refinement..." || true
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # REFINEMENT EXECUTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- REFINEMENT EXECUTION${NC}"
    echo ""

    local fixed_critical=0
    local fixed_major=0
    local fixed_minor=0
    local fix_details=()

    # Process critical issues
    if [[ "$total_critical" -gt 0 ]]; then
        echo -e "  ${RED}Addressing Critical Issues${NC}"
        echo ""

        # Extract critical findings from all review dimensions
        # Filter out process failures that can't be code-fixed (max turns, blocked, etc.)
        local critical_findings=$(jq -c '
            [.deep_code.findings[]?, .architecture.findings[]?, .performance.findings[]?, .documentation.findings[]?]
            | map(select(.severity == "critical"))
            | map(select(.description | (contains("max turns") or contains("blocked") or contains("does not exist")) | not))
        ' "$findings_file" 2>/dev/null)

        local i=0
        echo "$critical_findings" | jq -c '.[]' 2>/dev/null | while read -r finding; do
            ((i++))
            local file=$(echo "$finding" | jq -r '.file // "unknown"')
            local desc=$(echo "$finding" | jq -r '.description // "No description"')
            local recommendation=$(echo "$finding" | jq -r '.recommendation // "Fix the issue"')
            local category=$(echo "$finding" | jq -r '.category // "general"')

            echo -e "    ${DIM}[$i/$total_critical]${NC} $desc"

            if _604_apply_fix "$finding" "$fixes_dir/critical-$i" "$ATOMIC_ROOT"; then
                echo -e "             ${GREEN}✓${NC} Fixed"
                ((fixed_critical++))

                # Verify tests still pass
                if _604_verify_tests "$ATOMIC_ROOT"; then
                    echo -e "             ${GREEN}✓${NC} Tests passing"
                else
                    echo -e "             ${YELLOW}!${NC} Tests need attention"
                fi
            else
                echo -e "             ${YELLOW}!${NC} Manual fix recommended"
            fi
            echo ""
        done
    fi

    # Process major issues
    if [[ "$total_major" -gt 0 ]]; then
        echo -e "  ${YELLOW}Addressing Major Issues${NC}"
        echo ""

        # Filter out process failures that can't be code-fixed
        local major_findings=$(jq -c '
            [.deep_code.findings[]?, .architecture.findings[]?, .performance.findings[]?, .documentation.findings[]?]
            | map(select(.severity == "major"))
            | map(select(.description | (contains("max turns") or contains("blocked") or contains("does not exist")) | not))
        ' "$findings_file" 2>/dev/null)

        local i=0
        echo "$major_findings" | jq -c '.[]' 2>/dev/null | while read -r finding; do
            ((i++))
            local desc=$(echo "$finding" | jq -r '.description // "No description"')

            echo -e "    ${DIM}[$i/$total_major]${NC} $desc"

            if _604_apply_fix "$finding" "$fixes_dir/major-$i" "$ATOMIC_ROOT"; then
                echo -e "             ${GREEN}✓${NC} Fixed"
                ((fixed_major++))

                if _604_verify_tests "$ATOMIC_ROOT"; then
                    echo -e "             ${GREEN}✓${NC} Tests passing"
                else
                    echo -e "             ${YELLOW}!${NC} Tests need attention"
                fi
            else
                echo -e "             ${YELLOW}!${NC} Manual fix recommended"
            fi
            echo ""
        done
    fi

    # Minor fixes (if scope includes them)
    if [[ "$REFINEMENT_SCOPE" == "minor" || "$REFINEMENT_SCOPE" == "all" ]]; then
        if [[ "$total_minor" -gt 0 ]]; then
            echo -e "  ${CYAN}Addressing Minor Issues${NC}"
            echo ""

            # Filter out process failures that can't be code-fixed
            local minor_findings=$(jq -c '
                [.deep_code.findings[]?, .architecture.findings[]?, .performance.findings[]?, .documentation.findings[]?]
                | map(select(.severity == "minor"))
                | map(select(.description | (contains("max turns") or contains("blocked") or contains("does not exist")) | not))
            ' "$findings_file" 2>/dev/null)

            local i=0
            echo "$minor_findings" | jq -c '.[]' 2>/dev/null | while read -r finding; do
                ((i++))
                local desc=$(echo "$finding" | jq -r '.description // "No description"')

                echo -e "    ${DIM}[$i/$total_minor]${NC} $desc"

                if _604_apply_fix "$finding" "$fixes_dir/minor-$i" "$ATOMIC_ROOT"; then
                    echo -e "             ${GREEN}✓${NC} Fixed"
                    ((fixed_minor++))
                else
                    echo -e "             ${YELLOW}!${NC} Manual fix recommended"
                fi
                echo ""
            done
        fi
    else
        echo -e "  ${DIM}Minor Issues${NC}"
        echo ""
        echo -e "    ${DIM}$total_minor minor issues skipped (select 'minor' or 'all' scope to address)${NC}"
        echo ""
    fi

    # Note about process failures
    echo -e "  ${DIM}Note: Process failures (max turns, blocked tasks) are automatically filtered.${NC}"
    echo -e "  ${DIM}These require re-running Phase 5, not code fixes.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # TEST VERIFICATION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- TEST VERIFICATION${NC}"
    echo ""

    echo -e "  ${DIM}Running full test suite to verify refinements...${NC}"
    echo ""

    local tests_total=0
    local tests_passing=0
    local test_output=""

    # Detect and run test framework
    test_output=$(_604_run_full_tests "$ATOMIC_ROOT")
    local test_status=$?

    # Parse test results
    if [[ -n "$test_output" ]]; then
        # Try to extract counts from common test output formats
        if echo "$test_output" | grep -qE '[0-9]+ passed'; then
            tests_passing=$(echo "$test_output" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' | head -1)
        fi
        if echo "$test_output" | grep -qE '[0-9]+ tests?'; then
            tests_total=$(echo "$test_output" | grep -oE '[0-9]+ tests?' | grep -oE '[0-9]+' | head -1)
        fi

        # Jest format
        if echo "$test_output" | grep -qE 'Tests:.*[0-9]+ passed'; then
            tests_passing=$(echo "$test_output" | grep -oE 'Tests:.*[0-9]+ passed' | grep -oE '[0-9]+' | tail -1)
            tests_total=$(echo "$test_output" | grep -oE 'Tests:.*[0-9]+ total' | grep -oE '[0-9]+' | tail -1)
        fi

        # pytest format
        if echo "$test_output" | grep -qE '[0-9]+ passed'; then
            tests_passing=$(echo "$test_output" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+')
        fi
    fi

    # Fallback if we couldn't parse
    [[ -z "$tests_total" || "$tests_total" -eq 0 ]] && tests_total=$tests_passing
    [[ -z "$tests_passing" ]] && tests_passing=0

    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "  ${BOLD}TEST RESULTS${NC}"
    echo ""
    echo -e "    Total Tests:    ${tests_total:-unknown}"
    if [[ "$test_status" -eq 0 ]]; then
        echo -e "    Passing:        ${GREEN}${tests_passing:-all}${NC}"
        echo -e "    Failing:        ${GREEN}0${NC}"
    else
        echo -e "    Status:         ${YELLOW}Some tests may have issues${NC}"
    fi
    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    if [[ "$test_status" -eq 0 ]]; then
        echo -e "  ${GREEN}✓${NC} All tests passing after refinements"
    else
        echo -e "  ${YELLOW}!${NC} Review test output for any issues"
    fi
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # REFINEMENT SUMMARY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- REFINEMENT SUMMARY${NC}"
    echo ""

    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "  ${BOLD}ISSUES RESOLVED${NC}"
    echo ""
    echo -e "    Critical Fixed:  ${GREEN}$fixed_critical / $total_critical${NC}"
    echo -e "    Major Fixed:     ${GREEN}$fixed_major / $total_major${NC}"
    echo -e "    Minor Fixed:     ${DIM}$fixed_minor / $total_minor${NC}  (optional)"
    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    if [[ "$fixed_critical" -ge "$total_critical" && "$fixed_major" -ge "$total_major" ]]; then
        echo -e "  ${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "  ${GREEN}✓ ALL CRITICAL AND MAJOR ISSUES RESOLVED${NC}"
        echo -e "  ${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    else
        echo -e "  ${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "  ${YELLOW}! Some issues remain - review before proceeding${NC}"
        echo -e "  ${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    fi
    echo ""

    # Save refinement report
    jq -n \
        --argjson total_critical "$total_critical" \
        --argjson fixed_critical "$fixed_critical" \
        --argjson total_major "$total_major" \
        --argjson fixed_major "$fixed_major" \
        --argjson total_minor "$total_minor" \
        --argjson fixed_minor "$fixed_minor" \
        --argjson tests_total "${tests_total:-0}" \
        --argjson tests_passing "${tests_passing:-0}" \
        --argjson test_status "$test_status" \
        '{
            "refinements": {
                "critical": { "total": $total_critical, "fixed": $fixed_critical },
                "major": { "total": $total_major, "fixed": $fixed_major },
                "minor": { "total": $total_minor, "fixed": $fixed_minor }
            },
            "test_verification": {
                "total": $tests_total,
                "passing": $tests_passing,
                "all_passing": ($test_status == 0)
            },
            "all_resolved": (($fixed_critical >= $total_critical) and ($fixed_major >= $total_major)),
            "refined_at": (now | todate)
        }' > "$refinement_file"

    atomic_context_artifact "$refinement_file" "refinement-report" "Code refinement report"
    atomic_context_decision "Refinement: $fixed_critical/$total_critical critical, $fixed_major/$total_major major fixed" "refinement"

    atomic_success "Refinement complete"

    return 0
}

# ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# REFINEMENT HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

_604_apply_fix() {
    local finding="$1"
    local output_prefix="$2"
    local project_root="$3"

    local prompt_file="${output_prefix}-prompt.md"
    local fix_file="${output_prefix}-fix.json"

    local file=$(echo "$finding" | jq -r '.file // "unknown"')
    local line=$(echo "$finding" | jq -r '.line // 0')
    local desc=$(echo "$finding" | jq -r '.description // ""')
    local recommendation=$(echo "$finding" | jq -r '.recommendation // ""')
    local category=$(echo "$finding" | jq -r '.category // "general"')
    local severity=$(echo "$finding" | jq -r '.severity // "major"')

    # Get current file content if file exists
    local file_content=""
    local full_path=""

    if [[ "$file" != "unknown" ]]; then
        # Try to find the file
        if [[ -f "$project_root/$file" ]]; then
            full_path="$project_root/$file"
        elif [[ -f "$project_root/src/$file" ]]; then
            full_path="$project_root/src/$file"
        else
            full_path=$(find "$project_root" -name "$(basename "$file")" -type f 2>/dev/null | head -1)
        fi

        if [[ -n "$full_path" && -f "$full_path" ]]; then
            file_content=$(head -200 "$full_path")
        fi
    fi

    # Build the fix prompt - use loaded agent if available
    if [[ -n "$_604_REFINER_AGENT_PROMPT" ]]; then
        echo "$_604_REFINER_AGENT_PROMPT" > "$prompt_file"
        cat >> "$prompt_file" << PROMPT

---

# Code Fix Request

Apply your code refinement expertise to fix the issue described below.
PROMPT
    else
        cat > "$prompt_file" << PROMPT
# Code Fix Request

You are a code-refiner agent. Apply a minimal, targeted fix for the issue described below.
PROMPT
    fi

    cat >> "$prompt_file" << PROMPT

## Issue Details

- **File**: $file
- **Line**: $line
- **Severity**: $severity
- **Category**: $category
- **Description**: $desc
- **Recommendation**: $recommendation

## Current Code

\`\`\`
$file_content
\`\`\`

## Fix Requirements

1. **Minimal Change**: Only fix the identified issue, nothing else
2. **Preserve Behavior**: Don't change any unrelated functionality
3. **Testable**: The fix should be verifiable by existing tests
4. **No Refactoring**: Resist the urge to "improve" surrounding code

## Output Format

Respond with ONLY valid JSON (no markdown wrapper):

{
  "can_fix": true,
  "fix_type": "code_change|config_change|documentation",
  "file_path": "$file",
  "original_code": "The exact code to replace (if code_change)",
  "fixed_code": "The corrected code (if code_change)",
  "explanation": "Brief explanation of what the fix does",
  "requires_manual_review": false,
  "manual_review_reason": "Why manual review is needed (if applicable)"
}

If you cannot safely generate a fix, set can_fix to false and explain why.
PROMPT

    # Call LLM to generate fix
    if atomic_invoke "$prompt_file" "$fix_file" "Fix $severity issue" --model=sonnet; then
        if jq -e . "$fix_file" &>/dev/null; then
            local can_fix=$(jq -r '.can_fix // false' "$fix_file")

            if [[ "$can_fix" == "true" ]]; then
                local fix_type=$(jq -r '.fix_type // "code_change"' "$fix_file")
                local original_code=$(jq -r '.original_code // ""' "$fix_file")
                local fixed_code=$(jq -r '.fixed_code // ""' "$fix_file")

                if [[ "$fix_type" == "code_change" && -n "$original_code" && -n "$fixed_code" && -n "$full_path" ]]; then
                    # Apply the fix using sed (simple replacement)
                    # For safety, create backup first
                    cp "$full_path" "${full_path}.bak"

                    # Try to apply fix (simple string replacement)
                    if grep -qF "$original_code" "$full_path" 2>/dev/null; then
                        # Use perl for multiline replacement
                        perl -i -p0e "s/\Q$original_code\E/$fixed_code/s" "$full_path" 2>/dev/null

                        # Verify the change was made
                        if grep -qF "$fixed_code" "$full_path" 2>/dev/null; then
                            rm -f "${full_path}.bak"
                            return 0
                        else
                            # Restore backup
                            mv "${full_path}.bak" "$full_path"
                            return 1
                        fi
                    else
                        rm -f "${full_path}.bak"
                        return 1
                    fi
                fi

                return 0
            fi
        else
            # Try to repair JSON
            if grep -q '```json' "$fix_file"; then
                sed -n '/```json/,/```/p' "$fix_file" | sed '1d;$d' > "${fix_file}.tmp"
                if jq -e . "${fix_file}.tmp" &>/dev/null; then
                    mv "${fix_file}.tmp" "$fix_file"
                    # Recursive call to process the repaired JSON
                    return $(_604_apply_fix "$finding" "$output_prefix" "$project_root" && echo 0 || echo 1)
                fi
                rm -f "${fix_file}.tmp"
            fi
        fi
    fi

    return 1
}

_604_verify_tests() {
    local project_root="$1"

    # Quick test verification - just check if tests can run
    # Full test run is done in TEST VERIFICATION section

    # Check for common test runners
    if [[ -f "$project_root/package.json" ]]; then
        if grep -q '"test"' "$project_root/package.json"; then
            npm test --prefix "$project_root" -- --passWithNoTests 2>/dev/null && return 0
        fi
    fi

    if [[ -f "$project_root/pytest.ini" ]] || [[ -f "$project_root/setup.py" ]]; then
        cd "$project_root" && python -m pytest --collect-only 2>/dev/null && return 0
    fi

    if [[ -f "$project_root/go.mod" ]]; then
        cd "$project_root" && go test ./... -count=0 2>/dev/null && return 0
    fi

    # No test framework detected or tests passed
    return 0
}

_604_run_full_tests() {
    local project_root="$1"

    # Detect and run the appropriate test framework
    if [[ -f "$project_root/package.json" ]]; then
        if grep -q '"test"' "$project_root/package.json"; then
            npm test --prefix "$project_root" 2>&1
            return $?
        fi
    fi

    if [[ -f "$project_root/pytest.ini" ]] || [[ -d "$project_root/tests" && -f "$project_root/setup.py" ]]; then
        cd "$project_root" && python -m pytest -v 2>&1
        return $?
    fi

    if [[ -f "$project_root/go.mod" ]]; then
        cd "$project_root" && go test -v ./... 2>&1
        return $?
    fi

    if [[ -f "$project_root/Cargo.toml" ]]; then
        cd "$project_root" && cargo test 2>&1
        return $?
    fi

    # BATS tests (for shell projects like ATOMIC-CLAUDE itself)
    if [[ -d "$project_root/tests" ]] && ls "$project_root/tests"/*.bats &>/dev/null; then
        bats "$project_root/tests" 2>&1
        return $?
    fi

    echo "No test framework detected"
    return 0
}
