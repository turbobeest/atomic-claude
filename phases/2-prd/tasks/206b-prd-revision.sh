#!/bin/bash
#
# Task 206b: PRD Revision (LLM-Assisted Q&A)
# Invoked from task 206 when user chooses to revise the PRD
#
# Flow:
#   1. Read validation results
#   2. Group issues by priority (P0 first)
#   3. For each issue: show it, ask user how to resolve
#   4. Collect all decisions into a resolution plan
#   5. Invoke Opus once with the PRD + all user decisions
#   6. Show diff, apply/discard
#   7. Return to task 206 for re-validation
#

prd_revision_flow() {
    local validation_file="$1"
    local prd_file="$2"
    local prompts_dir="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prompts"

    mkdir -p "$prompts_dir"

    echo ""
    echo -e "${CYAN}+----------------------------------------------------------+${NC}"
    echo -e "${CYAN}|${NC} ${BOLD}PRD REVISION — GUIDED Q&A${NC}"
    echo -e "${CYAN}+----------------------------------------------------------+${NC}"
    echo ""
    echo -e "  ${DIM}Walk through each issue and decide how to resolve it.${NC}"
    echo -e "  ${DIM}Your decisions will be applied in one pass by the revision agent.${NC}"
    echo ""

    # ══════════════════════════════════════════════════════════════════════════
    # COLLECT ISSUES
    # ══════════════════════════════════════════════════════════════════════════

    local issue_labels=()
    local issue_details=()

    # Contradictions first (highest priority)
    while IFS= read -r item; do
        [[ -z "$item" ]] && continue
        issue_labels+=("CONTRADICTION")
        issue_details+=("$item")
    done < <(jq -r '.consistency.contradictions[]?' "$validation_file" 2>/dev/null)

    # Completeness gaps
    while IFS= read -r item; do
        [[ -z "$item" ]] && continue
        issue_labels+=("GAP")
        issue_details+=("$item")
    done < <(jq -r '.completeness.gaps[]?' "$validation_file" 2>/dev/null)

    # P0/P1 recommendations
    while IFS= read -r item; do
        [[ -z "$item" ]] && continue
        issue_labels+=("RECOMMENDATION")
        issue_details+=("$item")
    done < <(jq -r '[.recommendations[]? | select(startswith("P0:") or startswith("P1:"))] | .[]' "$validation_file" 2>/dev/null)

    # P2+ recommendations
    while IFS= read -r item; do
        [[ -z "$item" ]] && continue
        issue_labels+=("RECOMMENDATION")
        issue_details+=("$item")
    done < <(jq -r '[.recommendations[]? | select(startswith("P2:") or startswith("P3:"))] | .[]' "$validation_file" 2>/dev/null)

    # Ambiguities
    while IFS= read -r item; do
        [[ -z "$item" ]] && continue
        issue_labels+=("AMBIGUITY")
        issue_details+=("$item")
    done < <(jq -r '.consistency.ambiguous_items[]?' "$validation_file" 2>/dev/null)

    # Testability issues
    while IFS= read -r item; do
        [[ -z "$item" ]] && continue
        issue_labels+=("TESTABILITY")
        issue_details+=("$item")
    done < <(jq -r '.testability.issues[]?' "$validation_file" 2>/dev/null)

    local total_issues=${#issue_details[@]}

    if [[ $total_issues -eq 0 ]]; then
        echo -e "  ${YELLOW}No issues found in validation results.${NC}"
        echo ""
        read -e -p "  Enter revision instructions manually (or Enter to skip): " manual_input || true
        if [[ -z "$manual_input" ]]; then
            return 0
        fi
        _prd_revision_invoke "$prd_file" "$prompts_dir" "1. $manual_input"
        return $?
    fi

    echo -e "  ${BOLD}$total_issues issues to review.${NC} For each one you can:"
    echo -e "    ${GREEN}Enter${NC}       Accept the suggested fix (default)"
    echo -e "    ${CYAN}Type${NC}        Provide your own resolution direction"
    echo -e "    ${YELLOW}skip${NC}        Skip this issue (don't fix)"
    echo -e "    ${RED}done${NC}        Stop reviewing, apply what you've decided so far"
    echo ""
    echo -e "${DIM}------------------------------------------------------------${NC}"

    # ══════════════════════════════════════════════════════════════════════════
    # Q&A SESSION — walk through each issue
    # ══════════════════════════════════════════════════════════════════════════

    local resolution_plan=""
    local resolved_count=0
    local skipped_count=0

    for i in "${!issue_details[@]}"; do
        local num=$((i + 1))
        local label="${issue_labels[$i]}"
        local detail="${issue_details[$i]}"

        # Color by type
        local label_color="${DIM}"
        case "$label" in
            CONTRADICTION) label_color="${RED}" ;;
            GAP)           label_color="${YELLOW}" ;;
            RECOMMENDATION)
                [[ "$detail" == P0:* ]] && label_color="${RED}"
                [[ "$detail" == P1:* ]] && label_color="${YELLOW}"
                [[ "$detail" == P2:* ]] && label_color="${CYAN}"
                [[ "$detail" == P3:* ]] && label_color="${DIM}"
                ;;
            AMBIGUITY)     label_color="${MAGENTA}" ;;
            TESTABILITY)   label_color="${BLUE}" ;;
        esac

        echo ""
        echo -e "  ${label_color}[$label]${NC} ${BOLD}($num/$total_issues)${NC}"
        echo -e "  $detail"
        echo ""

        # Suggest a default resolution based on type
        local suggestion=""
        case "$label" in
            CONTRADICTION)
                suggestion="Resolve in favor of Phase 1 original requirements"
                ;;
            GAP)
                suggestion="Add the missing content to the appropriate section"
                ;;
            RECOMMENDATION)
                suggestion="Apply this recommendation as described"
                ;;
            AMBIGUITY)
                suggestion="Add explicit definition or clarification"
                ;;
            TESTABILITY)
                suggestion="Add measurable criteria and concrete thresholds"
                ;;
        esac

        echo -e "  ${DIM}Suggested: $suggestion${NC}"
        read -e -p "  Resolution [accept]: " user_response || true

        if [[ "$user_response" == "done" ]]; then
            echo ""
            echo -e "  ${DIM}Stopping review. $((total_issues - num)) issues remaining.${NC}"
            break
        elif [[ "$user_response" == "skip" || "$user_response" == "s" ]]; then
            ((skipped_count++))
            echo -e "  ${DIM}  -> Skipped${NC}"
            continue
        elif [[ -z "$user_response" || "$user_response" == "accept" || "$user_response" == "a" ]]; then
            # Use the default suggestion
            resolution_plan+="$((resolved_count + 1)). [$label] $detail\n   RESOLUTION: $suggestion\n\n"
            ((resolved_count++))
            echo -e "  ${GREEN}  -> $suggestion${NC}"
        else
            # User provided custom direction
            resolution_plan+="$((resolved_count + 1)). [$label] $detail\n   RESOLUTION: $user_response\n\n"
            ((resolved_count++))
            echo -e "  ${GREEN}  -> $user_response${NC}"
        fi
    done

    echo ""
    echo -e "${DIM}------------------------------------------------------------${NC}"
    echo ""
    echo -e "  ${BOLD}Review complete:${NC} $resolved_count resolved, $skipped_count skipped"
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

    # ══════════════════════════════════════════════════════════════════════════
    # INVOKE REVISION AGENT
    # ══════════════════════════════════════════════════════════════════════════

    _prd_revision_invoke "$prd_file" "$prompts_dir" "$resolution_plan"
    return $?
}

# Internal: Build prompt, invoke LLM, handle diff/apply
_prd_revision_invoke() {
    local prd_file="$1"
    local prompts_dir="$2"
    local resolution_plan="$3"

    local revision_prompt="$prompts_dir/prd-revision.md"
    local revision_output="$prompts_dir/prd-revision-output.md"

    cat > "$revision_prompt" << 'PROMPT_HEADER'
# PRD Revision — Applying User Decisions

You are revising a PRD to implement the resolution plan below. Each item has been reviewed
by the user, who provided specific direction on how to resolve it.

## Rules

1. Implement EACH resolution exactly as the user directed.
2. Do NOT modify sections unrelated to the resolutions.
3. Preserve all existing formatting and structure.
4. When resolving contradictions, update ALL occurrences in the document.
5. When adding new content, place it in the most appropriate existing section.
6. Use RFC 2119 keywords (SHALL/SHOULD/MAY) for any new requirements.
7. Output the COMPLETE revised PRD — every section, even if unchanged.
8. Do NOT wrap output in markdown fences. Start with the first heading.

PROMPT_HEADER

    {
        echo "## Resolution Plan"
        echo ""
        echo -e "$resolution_plan"
        echo ""
        echo "## Current PRD"
        echo ""
        cat "$prd_file"
    } >> "$revision_prompt"

    local saved_turns="${CLAUDE_MAX_TURNS:-10}"
    export CLAUDE_MAX_TURNS=25

    echo ""
    atomic_waiting "Applying $resolved_count resolutions to PRD..."

    if ! atomic_invoke "$revision_prompt" "$revision_output" "PRD revision" --model=opus --timeout=3600; then
        export CLAUDE_MAX_TURNS="$saved_turns"
        echo -e "  ${RED}Revision failed. PRD unchanged.${NC}"
        return 1
    fi
    export CLAUDE_MAX_TURNS="$saved_turns"

    # ── Verify output ──

    if [[ ! -f "$revision_output" ]]; then
        echo -e "  ${RED}No output. PRD unchanged.${NC}"
        return 1
    fi

    local output_lines orig_lines
    output_lines=$(wc -l < "$revision_output" 2>/dev/null || echo 0)
    orig_lines=$(wc -l < "$prd_file" 2>/dev/null || echo 0)

    if [[ $output_lines -lt $((orig_lines / 2)) ]]; then
        echo -e "  ${RED}Output too short ($output_lines vs $orig_lines lines). PRD unchanged.${NC}"
        echo -e "  ${DIM}Saved to: $revision_output${NC}"
        return 1
    fi

    # Strip fences if wrapped
    if head -1 "$revision_output" | grep -q '```'; then
        sed -i '1d' "$revision_output"
        tail -1 "$revision_output" | grep -q '```' && sed -i '$d' "$revision_output"
    fi

    # ── Diff & Apply ──

    if diff -q "$prd_file" "$revision_output" &>/dev/null; then
        echo -e "  ${YELLOW}No changes detected.${NC}"
        return 0
    fi

    local added removed
    added=$(diff "$prd_file" "$revision_output" 2>/dev/null | grep -c '^>' || echo 0)
    removed=$(diff "$prd_file" "$revision_output" 2>/dev/null | grep -c '^<' || echo 0)

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
                cp "$revision_output" "$prd_file"
                echo ""
                echo -e "  ${GREEN}v PRD updated.${NC} ${DIM}Backup: PRD.md.bak${NC}"
                echo -e "  ${DIM}  Re-validation will follow...${NC}"
                echo ""

                local refine_log="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prd-refinements.log"
                {
                    echo "---"
                    echo "timestamp: $(date -Iseconds 2>/dev/null || date)"
                    echo "source: 206b-revision-qa"
                    echo "lines_added: $added"
                    echo "lines_removed: $removed"
                    echo "---"
                } >> "$refine_log"

                atomic_context_decision "PRD revised via Q&A (+$added/-$removed lines)" "revision"
                return 0
                ;;
            diff|d)
                echo ""
                echo -e "${DIM}------- DIFF (original -> revised) -------${NC}"
                diff --color=always -u "$prd_file" "$revision_output" 2>/dev/null | head -200 \
                    || diff -u "$prd_file" "$revision_output" 2>/dev/null | head -200
                echo ""
                echo -e "${DIM}  (first 200 lines)${NC}"
                echo -e "${DIM}------------------------------------------${NC}"
                echo ""
                ;;
            discard|x)
                echo ""
                echo -e "  ${YELLOW}Revision discarded. PRD unchanged.${NC}"
                echo -e "  ${DIM}Output preserved at: $revision_output${NC}"
                echo ""
                return 0
                ;;
            *)
                echo -e "  ${RED}Enter apply, diff, or discard.${NC}"
                ;;
        esac
    done
}
