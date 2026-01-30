#!/bin/bash
#
# Task 207: PRD Review, Refinement & Approval
#
# Agents analyze validation scores and walk the user through each
# recommended improvement one at a time. User directs every change.
# No autonomous LLM edits — user controls all decisions.
#
# Flow:
#   1. Show validation scores
#   2. Walk through each recommendation: show it, ask user how to resolve
#   3. Collect all decisions + optional custom requests
#   4. One LLM pass applies the collected resolution plan
#   5. Diff/apply/discard
#   6. Re-validate, show updated scores
#   7. Loop until user approves
#

task_207_prd_approval() {
    local prd_file="$ATOMIC_ROOT/docs/prd/PRD.md"
    local validation_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prd-validation.json"
    local approval_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prd-approved.json"
    local prompts_dir="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prompts"
    # Check embedded repo first (monorepo deployment), then env var, then default
    local agent_repo="$ATOMIC_ROOT/repos/agents"
    [[ -d "$ATOMIC_ROOT/external/agents" ]] && agent_repo="$ATOMIC_ROOT/external/agents"
    [[ -n "$AGENT_REPO" ]] && agent_repo="$AGENT_REPO"

    atomic_step "PRD Review, Refinement & Approval"
    mkdir -p "$prompts_dir"

    echo ""
    echo -e "${YELLOW}+----------------------------------------------------------+${NC}"
    echo -e "${YELLOW}|${NC}           ${BOLD}PRD REVIEW, REFINEMENT & APPROVAL${NC}               ${YELLOW}|${NC}"
    echo -e "${YELLOW}+----------------------------------------------------------+${NC}"
    echo ""

    if [[ ! -f "$prd_file" ]]; then
        atomic_error "PRD file not found: $prd_file"
        return 1
    fi

    # ═══════════════════════════════════════════════════════════════════════════
    # REVIEW-REFINE-APPROVE LOOP
    # ═══════════════════════════════════════════════════════════════════════════

    local iteration=0

    while true; do
        ((iteration++))

        # ── Show current scores ──
        _207_show_scores "$prd_file" "$validation_file"

        # ── Build improvement recommendations from validation data ──
        local suggestions=()
        local suggestion_agents=()
        local suggestion_prompts=()
        local suggestion_details=()

        _207_build_suggestions "$validation_file" suggestions suggestion_agents suggestion_prompts suggestion_details

        local num_suggestions=${#suggestions[@]}

        # ── Decision point: refine or approve ──
        echo -e "${DIM}------------------------------------------------------------${NC}"
        echo ""

        if [[ $num_suggestions -eq 0 ]]; then
            echo -e "  ${GREEN}No outstanding issues detected. PRD is ready for approval.${NC}"
            echo ""
            echo -e "    ${GREEN}[approve]${NC}  Approve PRD and proceed to Phase 3"
            echo -e "    ${CYAN}[custom]${NC}   Make a custom improvement request"
            echo -e "    ${YELLOW}[view]${NC}     View PRD content"
            echo ""
    atomic_drain_stdin
            read -e -p "  Choice [approve]: " top_choice || true
            top_choice=${top_choice:-approve}
        else
            echo -e "  ${CYAN}${num_suggestions} recommended improvements available.${NC}"
            echo ""
            echo -e "    ${GREEN}[refine]${NC}   Walk through recommendations one by one"
            echo -e "    ${CYAN}[custom]${NC}   Make a custom improvement request"
            echo -e "    ${YELLOW}[view]${NC}     View PRD content"
            echo -e "    ${BOLD}[approve]${NC}  Approve PRD as-is and proceed to Phase 3"
            echo ""
    atomic_drain_stdin
            read -e -p "  Choice [refine]: " top_choice || true
            top_choice=${top_choice:-refine}
        fi

        case "$top_choice" in

            # ── APPROVE ──
            approve|a)
                _207_do_approve "$prd_file" "$approval_file"
                return 0
                ;;

            # ── VIEW ──
            view|v)
                echo ""
                echo -e "${DIM}-------------- PRD CONTENT ----------------${NC}"
                echo ""
                head -100 "$prd_file" | sed 's/^/  /'
                echo ""
                echo -e "${DIM}  ... (showing first 100 lines)${NC}"
                echo -e "${DIM}  Full file: $prd_file${NC}"
                echo ""
                echo -e "${DIM}-------------------------------------------${NC}"
                echo ""
                ;;

            # ── CUSTOM REQUEST ──
            custom|c)
                _207_custom_request "$prd_file" "$validation_file" "$prompts_dir" "$agent_repo" "$iteration"
                _207_revalidate "$prd_file" "$validation_file" "$prompts_dir"
                ;;

            # ── GUIDED REFINEMENT Q&A ──
            refine|r)
                if [[ $num_suggestions -eq 0 ]]; then
                    echo -e "  ${YELLOW}No recommendations to review. Use 'custom' instead.${NC}"
                    continue
                fi

                _207_guided_walkthrough "$prd_file" "$validation_file" "$prompts_dir" \
                    "$agent_repo" "$iteration" \
                    suggestions suggestion_agents suggestion_prompts suggestion_details
                _207_revalidate "$prd_file" "$validation_file" "$prompts_dir"
                ;;

            *)
                echo -e "  ${RED}Enter refine, custom, view, or approve.${NC}"
                ;;
        esac
    done
}

# ═══════════════════════════════════════════════════════════════════════════════
# GUIDED WALKTHROUGH — one recommendation at a time
# ═══════════════════════════════════════════════════════════════════════════════

_207_guided_walkthrough() {
    local prd_file="$1"
    local validation_file="$2"
    local prompts_dir="$3"
    local agent_repo="$4"
    local iteration="$5"
    local -n _sug_list=$6
    local -n _sug_agents=$7
    local -n _sug_prompts=$8
    local -n _sug_details=$9

    local total=${#_sug_list[@]}

    echo ""
    echo -e "${CYAN}+----------------------------------------------------------+${NC}"
    echo -e "${CYAN}|${NC} ${BOLD}GUIDED REFINEMENT — $total recommendations${NC}"
    echo -e "${CYAN}+----------------------------------------------------------+${NC}"
    echo ""
    echo -e "  ${DIM}For each recommendation you can:${NC}"
    echo -e "    ${GREEN}Enter${NC}       Accept the recommended revision (default)"
    echo -e "    ${CYAN}Type${NC}        Provide your own revision direction"
    echo -e "    ${YELLOW}skip${NC}        Skip this recommendation"
    echo -e "    ${RED}done${NC}        Stop reviewing, apply what you've decided so far"
    echo ""
    echo -e "${DIM}------------------------------------------------------------${NC}"

    local resolution_plan=""
    local resolved_count=0
    local skipped_count=0

    local i
    for i in "${!_sug_list[@]}"; do
        local num=$((i + 1))
        local agent="${_sug_agents[$i]}"
        local suggestion="${_sug_list[$i]}"
        local default_prompt="${_sug_prompts[$i]}"
        local details="${_sug_details[$i]}"

        # Color by agent
        local agent_color="${DIM}"
        [[ "$agent" == "prd-writer" ]] && agent_color="${GREEN}"
        [[ "$agent" == "requirements-engineer" ]] && agent_color="${CYAN}"

        echo ""
        echo -e "  ${agent_color}[$agent]${NC} ${BOLD}($num/$total)${NC}  $suggestion"
        echo ""

        # Show the specific issues and recommended action
        echo -e "$details" | sed 's/^/  /'
        echo ""

        read -e -p "  Resolution [accept]: " user_response || true

        if [[ "$user_response" == "done" ]]; then
            echo ""
            echo -e "  ${DIM}Stopping review. $((total - num)) recommendations remaining.${NC}"
            break
        elif [[ "$user_response" == "skip" || "$user_response" == "s" ]]; then
            ((skipped_count++))
            echo -e "  ${DIM}  -> Skipped${NC}"
            continue
        elif [[ -z "$user_response" || "$user_response" == "accept" || "$user_response" == "a" ]]; then
            # Use the full default prompt for this suggestion
            resolution_plan+="$((resolved_count + 1)). [$agent] $suggestion\n   RESOLUTION:\n$(echo -e "$default_prompt")\n\n"
            ((resolved_count++))
            echo -e "  ${GREEN}  -> Accepted${NC}"
        else
            # User provided custom direction
            resolution_plan+="$((resolved_count + 1)). [$agent] $suggestion\n   RESOLUTION: $user_response\n\n"
            ((resolved_count++))
            echo -e "  ${GREEN}  -> $user_response${NC}"
        fi
    done

    echo ""
    echo -e "${DIM}------------------------------------------------------------${NC}"
    echo ""
    echo -e "  ${BOLD}Review complete:${NC} $resolved_count accepted, $skipped_count skipped"
    echo ""

    if [[ $resolved_count -eq 0 ]]; then
        echo -e "  ${YELLOW}No resolutions to apply.${NC}"
        return 0
    fi

    # Ask for any additional global instructions
    echo -e "  ${DIM}Any additional instructions for the revision agent? (Enter to skip):${NC}"
    read -e -p "  > " additional_context || true

    if [[ -n "$additional_context" ]]; then
        resolution_plan+="\nADDITIONAL INSTRUCTIONS FROM USER:\n$additional_context\n"
    fi

    # ── Apply the collected resolution plan ──
    _207_apply_plan "$prd_file" "$prompts_dir" "$agent_repo" "$resolution_plan" "$resolved_count" "$iteration"
    return $?
}

# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOM REQUEST — user describes their own improvement
# ═══════════════════════════════════════════════════════════════════════════════

_207_custom_request() {
    local prd_file="$1"
    local validation_file="$2"
    local prompts_dir="$3"
    local agent_repo="$4"
    local iteration="$5"

    echo ""
    echo -e "  ${CYAN}What would you like to improve?${NC}"
    echo -e "  ${DIM}(Multi-line. Empty line when done.)${NC}"
    echo ""
    local custom_text=""
    while true; do
        read -e -p "    > " line || true
        [[ -z "$line" ]] && break
        custom_text+="$line\n"
    done
    if [[ -z "$custom_text" ]]; then
        echo -e "  ${YELLOW}No instructions provided.${NC}"
        return 0
    fi

    local resolution_plan="1. [user-request] Custom improvement\n   RESOLUTION: $(echo -e "$custom_text")\n"

    _207_apply_plan "$prd_file" "$prompts_dir" "$agent_repo" "$resolution_plan" 1 "$iteration"
    return $?
}

# ═══════════════════════════════════════════════════════════════════════════════
# APPLY PLAN — single LLM invocation with collected resolutions
# ═══════════════════════════════════════════════════════════════════════════════

_207_apply_plan() {
    local prd_file="$1"
    local prompts_dir="$2"
    local agent_repo="$3"
    local resolution_plan="$4"
    local resolved_count="$5"
    local iteration="$6"

    local refine_prompt="$prompts_dir/prd-refine-207.md"
    local refine_output="$prompts_dir/prd-refine-207-output.md"

    # Load prd-writer agent profile if available
    local agent_context=""
    if [[ -d "$agent_repo" ]]; then
        local agent_file
        agent_file=$(find "$agent_repo/pipeline-agents" -name "prd-writer.md" -type f 2>/dev/null | head -1)
        if [[ -f "$agent_file" ]]; then
            agent_context=$(cat "$agent_file" | atomic_strip_frontmatter)
        fi
    fi

    cat > "$refine_prompt" << 'PROMPT_HEADER'
# PRD Refinement — Applying User-Directed Revisions

You are revising a PRD to implement the resolution plan below. Each item has been
reviewed and directed by the user.

## CRITICAL OUTPUT RULES

1. Your ENTIRE response must be the revised PRD text. Nothing else.
2. Do NOT write to any files. Do NOT use any tools. Just output the text.
3. Do NOT wrap output in markdown fences. Start directly with the first heading.
4. Do NOT include any preamble, summary, or commentary before or after the PRD.
5. Output the COMPLETE PRD — every section, even those not affected by revisions.

## Revision Rules

1. Implement EACH resolution exactly as the user directed.
2. Do NOT modify sections unrelated to the resolutions.
3. Preserve all existing formatting and structure.
4. When resolving contradictions, update ALL occurrences in the document.
5. When adding new content, place it in the most appropriate existing section.
6. Use RFC 2119 keywords (SHALL/SHOULD/MAY) for any new requirements.

PROMPT_HEADER

    {
        if [[ -n "$agent_context" ]]; then
            echo "## Agent Profile"
            echo ""
            echo "$agent_context"
            echo ""
        fi
        echo "## Resolution Plan"
        echo ""
        echo -e "$resolution_plan"
        echo ""
        echo "## Current PRD"
        echo ""
        cat "$prd_file"
    } >> "$refine_prompt"

    local saved_turns="${CLAUDE_MAX_TURNS:-10}"
    export CLAUDE_MAX_TURNS=25

    echo ""
    atomic_waiting "Applying $resolved_count resolutions to PRD..."

    if ! atomic_invoke "$refine_prompt" "$refine_output" "PRD refinement (207)" --model=opus --timeout=3600; then
        export CLAUDE_MAX_TURNS="$saved_turns"
        echo -e "  ${RED}Refinement failed. PRD unchanged.${NC}"
        return 1
    fi
    export CLAUDE_MAX_TURNS="$saved_turns"

    # ── Verify output ──

    if [[ ! -f "$refine_output" ]]; then
        echo -e "  ${RED}No output. PRD unchanged.${NC}"
        return 1
    fi

    local output_lines orig_lines
    output_lines=$(wc -l < "$refine_output" 2>/dev/null || echo 0)
    orig_lines=$(wc -l < "$prd_file" 2>/dev/null || echo 0)

    if [[ $output_lines -lt $((orig_lines / 2)) ]]; then
        echo -e "  ${RED}Output too short ($output_lines vs $orig_lines lines). PRD unchanged.${NC}"
        echo -e "  ${DIM}Saved to: $refine_output${NC}"
        echo ""
        echo -e "  ${DIM}The LLM may have used file tools instead of text output.${NC}"
        echo -e "  ${DIM}Checking if it wrote the PRD directly...${NC}"

        # Fallback: check if the LLM wrote to PRD.md directly
        local current_lines
        current_lines=$(wc -l < "$prd_file" 2>/dev/null || echo 0)
        if [[ $current_lines -gt $orig_lines ]]; then
            echo -e "  ${YELLOW}LLM appears to have modified PRD.md directly (+$((current_lines - orig_lines)) lines).${NC}"
            echo -e "  ${DIM}Changes are already applied. Re-validating...${NC}"
            return 0
        fi
        return 1
    fi

    # Strip fences if wrapped
    if head -1 "$refine_output" | grep -q '```'; then
        sed -i '1d' "$refine_output"
        tail -1 "$refine_output" | grep -q '```' && sed -i '$d' "$refine_output"
    fi

    # ── Diff & Apply ──

    if diff -q "$prd_file" "$refine_output" &>/dev/null; then
        echo -e "  ${YELLOW}No changes detected.${NC}"
        return 0
    fi

    local added removed
    added=$(diff "$prd_file" "$refine_output" 2>/dev/null | grep -c '^>' || echo 0)
    removed=$(diff "$prd_file" "$refine_output" 2>/dev/null | grep -c '^<' || echo 0)

    echo ""
    echo -e "  ${CYAN}Revision Summary:${NC}"
    echo -e "    Original:  $orig_lines lines"
    echo -e "    Revised:   $output_lines lines"
    echo -e "    Added:     ${GREEN}+$added lines${NC}"
    echo -e "    Removed:   ${RED}-$removed lines${NC}"
    echo ""
    echo -e "    ${GREEN}[apply]${NC}  Accept    ${CYAN}[diff]${NC}  View diff    ${RED}[discard]${NC}  Reject"
    echo ""

    while true; do
    atomic_drain_stdin
        read -e -p "  Choice [apply]: " ref_choice || true
        ref_choice=${ref_choice:-apply}

        case "$ref_choice" in
            apply|a)
                cp "$prd_file" "${prd_file}.bak"
                cp "$refine_output" "$prd_file"
                echo ""
                echo -e "  ${GREEN}v PRD updated.${NC} ${DIM}Backup: PRD.md.bak${NC}"
                echo ""

                # Log refinement
                {
                    echo "---"
                    echo "timestamp: $(date -Iseconds 2>/dev/null || date)"
                    echo "source: 207-guided-refinement"
                    echo "iteration: $iteration"
                    echo "resolutions: $resolved_count"
                    echo "lines_added: $added"
                    echo "lines_removed: $removed"
                    echo "---"
                } >> "$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prd-refinements.log"

                atomic_context_decision "PRD refined via guided review (+$added/-$removed lines, $resolved_count items)" "refinement"
                return 0
                ;;
            diff|d)
                echo ""
                echo -e "${DIM}------- DIFF (original -> revised) -------${NC}"
                diff --color=always -u "$prd_file" "$refine_output" 2>/dev/null | head -200 \
                    || diff -u "$prd_file" "$refine_output" 2>/dev/null | head -200
                echo ""
                echo -e "${DIM}  (first 200 lines)${NC}"
                echo -e "${DIM}------------------------------------------${NC}"
                echo ""
                ;;
            discard|x)
                echo ""
                echo -e "  ${YELLOW}Revision discarded. PRD unchanged.${NC}"
                echo -e "  ${DIM}Output preserved at: $refine_output${NC}"
                echo ""
                return 0
                ;;
            *)
                echo -e "  ${RED}Enter apply, diff, or discard.${NC}"
                ;;
        esac
    done
}

# ═══════════════════════════════════════════════════════════════════════════════
# SHOW SCORES
# ═══════════════════════════════════════════════════════════════════════════════

_207_show_scores() {
    local prd_file="$1"
    local validation_file="$2"

    local line_count word_count
    line_count=$(wc -l < "$prd_file")
    word_count=$(wc -w < "$prd_file")

    echo -e "  ${DIM}PRD: $line_count lines, $word_count words${NC}"
    echo ""

    if [[ ! -f "$validation_file" ]]; then
        echo -e "  ${YELLOW}No validation data available.${NC}"
        echo ""
        return
    fi

    local val_status overall_score completeness testability taskmaster openspec
    val_status=$(jq -r '.overall_status // "UNKNOWN"' "$validation_file" 2>/dev/null)
    overall_score=$(jq -r '.overall_score // 0' "$validation_file" 2>/dev/null)
    completeness=$(jq -r '.completeness.score // 0' "$validation_file" 2>/dev/null)
    testability=$(jq -r '.testability.score // 0' "$validation_file" 2>/dev/null)
    taskmaster=$(jq -r '.taskmaster_compatibility.score // 0' "$validation_file" 2>/dev/null)
    openspec=$(jq -r '.openspec_compatibility.score // 0' "$validation_file" 2>/dev/null)

    local status_color="${GREEN}"
    [[ "$val_status" == "WARN" || "$val_status" == "WARNING" ]] && status_color="${YELLOW}"
    [[ "$val_status" == "FAIL" ]] && status_color="${RED}"

    # Score bar helper
    _score_bar() {
        local score=$1
        local color="${GREEN}"
        [[ $score -lt 80 ]] && color="${YELLOW}"
        [[ $score -lt 60 ]] && color="${RED}"
        local filled=$((score / 5))
        local empty=$((20 - filled))
        printf "${color}"
        printf '%0.s#' $(seq 1 $filled) 2>/dev/null
        printf "${DIM}"
        printf '%0.s-' $(seq 1 $empty) 2>/dev/null
        printf "${NC} %3d%%" "$score"
    }

    echo -e "  ${BOLD}Overall: ${status_color}$val_status ($overall_score%)${NC}"
    echo ""
    printf "    Completeness:  "; _score_bar "$completeness"; echo ""
    printf "    Testability:   "; _score_bar "$testability"; echo ""
    printf "    TaskMaster:    "; _score_bar "$taskmaster"; echo ""
    printf "    OpenSpec:      "; _score_bar "$openspec"; echo ""
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════════
# BUILD SUGGESTIONS FROM VALIDATION DATA
# ═══════════════════════════════════════════════════════════════════════════════

_207_build_suggestions() {
    local validation_file="$1"
    local -n _suggestions=$2
    local -n _agents=$3
    local -n _prompts=$4
    local -n _details=$5

    [[ ! -f "$validation_file" ]] && return

    local completeness testability taskmaster openspec
    completeness=$(jq -r '.completeness.score // 100' "$validation_file" 2>/dev/null)
    testability=$(jq -r '.testability.score // 100' "$validation_file" 2>/dev/null)
    taskmaster=$(jq -r '.taskmaster_compatibility.score // 100' "$validation_file" 2>/dev/null)
    openspec=$(jq -r '.openspec_compatibility.score // 100' "$validation_file" 2>/dev/null)

    # P0 contradictions
    local contradiction_count
    contradiction_count=$(jq '.consistency.contradictions | length' "$validation_file" 2>/dev/null || echo 0)
    if [[ $contradiction_count -gt 0 ]]; then
        local contradictions_text
        contradictions_text=$(jq -r '.consistency.contradictions[]' "$validation_file" 2>/dev/null | sed 's/^/    - /')
        _suggestions+=("Fix $contradiction_count contradictions (P0 issues)")
        _agents+=("prd-writer")
        _prompts+=("Resolve these contradictions in the PRD:\n$contradictions_text\nFor each contradiction, pick the option most consistent with the Phase 1 original requirements and update the PRD accordingly.")
        _details+=("${YELLOW}Issues found:${NC}\n$contradictions_text\n\n${DIM}Recommended action: Resolve each contradiction in favor of Phase 1\noriginal requirements. Update all occurrences in the document.${NC}")
    fi

    # Completeness gaps
    local gap_count
    gap_count=$(jq '.completeness.gaps | length' "$validation_file" 2>/dev/null || echo 0)
    if [[ $gap_count -gt 0 || $completeness -lt 85 ]]; then
        local gaps_text
        gaps_text=$(jq -r '.completeness.gaps[]' "$validation_file" 2>/dev/null | sed 's/^/    - /')
        _suggestions+=("Improve completeness ($completeness% -> 90%+): fill $gap_count gaps")
        _agents+=("prd-writer")
        _prompts+=("Improve PRD completeness by addressing these gaps:\n$gaps_text\nAdd missing content in the appropriate sections. Ensure all Phase 1 requirements are represented.")
        _details+=("${YELLOW}Missing content:${NC}\n$gaps_text\n\n${DIM}Recommended action: Add the missing content to the appropriate PRD\nsections. Ensure all Phase 1 requirements are represented.${NC}")
    fi

    # OpenSpec format
    if [[ $openspec -lt 80 ]]; then
        local openspec_issues
        openspec_issues=$(jq -r '.openspec_compatibility.issues[]' "$validation_file" 2>/dev/null | sed 's/^/    - /')
        _suggestions+=("Improve OpenSpec compatibility ($openspec% -> 85%+): Gherkin conversion")
        _agents+=("requirements-engineer")
        _prompts+=("Improve OpenSpec compatibility by making these changes:\n$openspec_issues\nConvert all WHEN/THEN scenarios to proper Given/When/Then Gherkin format. Add '#### Scenario: [Name]' headers. Wrap related requirements in Feature blocks where appropriate.")
        _details+=("${YELLOW}Format issues:${NC}\n$openspec_issues\n\n${DIM}Recommended action: Convert WHEN/THEN to Given/When/Then Gherkin format.\nAdd Scenario headers and Feature blocks for requirement groups.${NC}")
    fi

    # Testability
    if [[ $testability -lt 85 ]]; then
        local test_issues
        test_issues=$(jq -r '.testability.issues[]' "$validation_file" 2>/dev/null | sed 's/^/    - /')
        _suggestions+=("Strengthen testability ($testability% -> 90%+): tighten requirements")
        _agents+=("requirements-engineer")
        _prompts+=("Improve requirement testability:\n$test_issues\nEnsure all FRs use RFC 2119 keywords (SHALL/SHOULD/MAY). Add specific measurable thresholds to any vague NFRs. Add acceptance criteria where missing.")
        _details+=("${YELLOW}Testability gaps:${NC}\n$test_issues\n\n${DIM}Recommended action: Add RFC 2119 keywords (SHALL/SHOULD/MAY) to all FRs.\nAdd measurable thresholds to vague NFRs. Add acceptance criteria where missing.${NC}")
    fi

    # TaskMaster compatibility
    if [[ $taskmaster -lt 85 ]]; then
        local tm_issues
        tm_issues=$(jq -r '.taskmaster_compatibility.issues[]' "$validation_file" 2>/dev/null | sed 's/^/    - /')
        _suggestions+=("Improve TaskMaster compatibility ($taskmaster% -> 90%+)")
        _agents+=("prd-writer")
        _prompts+=("Improve TaskMaster compatibility:\n$tm_issues\nEnsure the dependency chain has explicit references. Add FR numbers for infrastructure items. Ensure development phases are scope-defined with exit criteria.")
        _details+=("${YELLOW}Compatibility issues:${NC}\n$tm_issues\n\n${DIM}Recommended action: Add explicit dependency references between FRs.\nAdd FR numbers for infrastructure items. Add exit criteria to dev phases.${NC}")
    fi

    # P1+ recommendations not already covered
    local rec_count
    rec_count=$(jq '.recommendations | length' "$validation_file" 2>/dev/null || echo 0)
    if [[ $rec_count -gt 5 ]]; then
        local p1_recs
        p1_recs=$(jq -r '[.recommendations[] | select(startswith("P1:") or startswith("P2:"))] | .[0:3] | .[]' "$validation_file" 2>/dev/null | sed 's/^/    - /')
        if [[ -n "$p1_recs" ]]; then
            _suggestions+=("Address P1/P2 recommendations (${rec_count} total)")
            _agents+=("prd-writer")
            _prompts+=("Address these priority recommendations:\n$p1_recs\nMake targeted edits to resolve each item.")
            _details+=("${YELLOW}Priority recommendations:${NC}\n$p1_recs\n\n${DIM}Recommended action: Apply each recommendation as described above.${NC}")
        fi
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# RE-VALIDATE (reuses the LLM validation prompt from task 206)
# ═══════════════════════════════════════════════════════════════════════════════

_207_revalidate() {
    local prd_file="$1"
    local validation_file="$2"
    local prompts_dir="$3"

    echo ""
    echo -e "  ${DIM}Re-validating PRD...${NC}"

    # Quick structural check
    local sections_found=0
    local expected_sections=(
        "Vision" "Executive Summary" "Technical Architecture"
        "Feature Requirements" "Non-Functional" "Logical Dependency"
        "Development Phases" "Code Structure" "TDD" "Integration Testing"
        "Documentation" "Operational" "Risks" "Success Metrics" "Approval"
    )
    for section in "${expected_sections[@]}"; do
        grep -qi "$section" "$prd_file" 2>/dev/null && ((sections_found++))
    done

    # Re-run LLM validation
    local raw_validation="$prompts_dir/validation-raw.json"

    # Reuse the validation prompt from task 206 if it exists
    local val_prompt="$prompts_dir/prd-validation.md"
    if [[ ! -f "$val_prompt" ]]; then
        echo -e "  ${YELLOW}Validation prompt not found — using structural check only.${NC}"
        local score=$((sections_found * 100 / 15))
        jq -n --argjson score "$score" '{"overall_status":"WARN","overall_score":$score,"completeness":{"score":$score,"gaps":[]},"testability":{"score":0},"taskmaster_compatibility":{"score":0},"openspec_compatibility":{"score":0},"consistency":{"contradictions":[],"ambiguous_items":[]},"recommendations":[],"proceed_recommendation":true,"proceed_rationale":"Structural re-check only"}' > "$validation_file"
        echo ""
        return
    fi

    local saved_turns="${CLAUDE_MAX_TURNS:-10}"
    export CLAUDE_MAX_TURNS=15

    atomic_waiting "Re-validating with prd-validator..."

    if atomic_invoke "$val_prompt" "$raw_validation" "PRD re-validation" --model=opus --timeout=1800; then
        # JSON recovery pipeline (same as 206)
        if _206_recover_json "$raw_validation" "$prompts_dir" 2>/dev/null; then
            cp "$raw_validation" "$validation_file"
            echo -e "  ${GREEN}v Validation updated.${NC}"
        else
            echo -e "  ${YELLOW}Could not parse re-validation output.${NC}"
        fi
    else
        echo -e "  ${YELLOW}Re-validation invocation failed. Scores unchanged.${NC}"
    fi

    export CLAUDE_MAX_TURNS="$saved_turns"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════════
# APPROVAL
# ═══════════════════════════════════════════════════════════════════════════════

_207_do_approve() {
    local prd_file="$1"
    local approval_file="$2"

    echo ""
    read -e -p "  Approver name: " approver_name || true
    approver_name=${approver_name:-"Anonymous"}
    read -e -p "  Any notes? (optional): " approval_notes || true

    jq -n \
        --arg approver "$approver_name" \
        --arg notes "$approval_notes" \
        --arg prd "$prd_file" \
        '{
            "status": "approved",
            "approver": $approver,
            "notes": $notes,
            "prd_file": $prd,
            "approved_at": (now | todate)
        }' > "$approval_file"

    echo ""
    echo -e "  ${GREEN}+----------------------------------------------------------+${NC}"
    echo -e "  ${GREEN}|${NC}                   ${BOLD}PRD APPROVED${NC}                           ${GREEN}|${NC}"
    echo -e "  ${GREEN}+----------------------------------------------------------+${NC}"
    echo ""

    atomic_context_artifact "prd_approval" "$approval_file" "PRD approval record"
    atomic_context_decision "PRD approved by $approver_name" "approval"
    atomic_success "PRD approved - ready for Phase 3"
}
