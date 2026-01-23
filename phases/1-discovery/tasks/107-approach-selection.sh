#!/bin/bash
#
# Task 107: Direction Confirmation (Human Gate)
# Review and confirm the consensus from deliberation
#
# This is a HUMAN GATE where:
#   - The consensus from Task 106 is presented
#   - Human can approve as-is or modify any section
#   - Final direction is locked in for downstream phases
#
# Outputs:
#   - selected-approach.json   - Finalized direction (structured)
#   - selected-approach.md     - Human-readable documentation
#

task_107_approach_selection() {
    local consensus_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/consensus.json"
    local approaches_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/approaches.json"
    local selected_json="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/selected-approach.json"
    local selected_md="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/selected-approach.md"

    # Check for jq dependency
    if ! command -v jq &>/dev/null; then
        atomic_error "jq is required for direction confirmation"
        echo -e "  ${DIM}Install with: apt install jq / brew install jq${NC}"
        return 1
    fi

    atomic_step "Direction Confirmation"

    # ═══════════════════════════════════════════════════════════════════════════
    # CHECK PREREQUISITES
    # ═══════════════════════════════════════════════════════════════════════════

    if [[ ! -f "$consensus_file" ]]; then
        atomic_error "No consensus found. Run Discovery Conversation first."
        return 1
    fi

    # Load consensus
    local direction=$(jq -r '.agreed_direction.approach // "No direction specified"' "$consensus_file")
    local rationale=$(jq -r '.agreed_direction.rationale // ""' "$consensus_file")
    local key_decisions=$(jq -r '.key_decisions // []' "$consensus_file")
    local open_items=$(jq -r '.open_items // []' "$consensus_file")
    local next_steps=$(jq -r '.next_steps // []' "$consensus_file")
    local dissenting_views=$(jq -r '.dissenting_views // []' "$consensus_file")

    # ═══════════════════════════════════════════════════════════════════════════
    # PRESENT CONSENSUS
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${YELLOW}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║${NC}                                                           ${YELLOW}║${NC}"
    echo -e "${YELLOW}║${NC}  ${BOLD}HUMAN GATE: CONFIRM DIRECTION${NC}                            ${YELLOW}║${NC}"
    echo -e "${YELLOW}║${NC}                                                           ${YELLOW}║${NC}"
    echo -e "${YELLOW}║${NC}  ${DIM}Review the consensus from deliberation.${NC}                  ${YELLOW}║${NC}"
    echo -e "${YELLOW}║${NC}  ${DIM}Approve as-is, or modify any section.${NC}                    ${YELLOW}║${NC}"
    echo -e "${YELLOW}║${NC}                                                           ${YELLOW}║${NC}"
    echo -e "${YELLOW}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 1: DIRECTION
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}1. DIRECTION${NC}                                               ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${BOLD}$direction${NC}"
    echo ""
    if [[ -n "$rationale" ]]; then
        echo "$rationale" | fold -s -w 60 | while IFS= read -r line; do
            echo -e "  ${DIM}$line${NC}"
        done
        echo ""
    fi

    echo -e "  ${GREEN}[enter]${NC} Accept  ${YELLOW}[edit]${NC} Modify"
    read -p "  > " section1_action

    if [[ "${section1_action,,}" == "edit" ]]; then
        echo ""
        echo -e "  ${DIM}Enter new direction (or press enter to keep current):${NC}"
        read -p "  Direction: " new_direction
        [[ -n "$new_direction" ]] && direction="$new_direction"

        echo -e "  ${DIM}Enter new rationale (or press enter to keep current):${NC}"
        read -p "  Rationale: " new_rationale
        [[ -n "$new_rationale" ]] && rationale="$new_rationale"

        echo -e "  ${GREEN}✓${NC} Direction updated"
    fi
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 2: KEY DECISIONS
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}2. KEY DECISIONS${NC}                                           ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local decisions_count=$(echo "$key_decisions" | jq 'length')
    if [[ "$decisions_count" -gt 0 ]]; then
        echo "$key_decisions" | jq -r '.[] | "  • " + .'
    else
        echo -e "  ${DIM}No key decisions recorded${NC}"
    fi
    echo ""

    echo -e "  ${GREEN}[enter]${NC} Accept  ${YELLOW}[add]${NC} Add decision  ${RED}[clear]${NC} Start fresh"
    read -p "  > " section2_action

    case "${section2_action,,}" in
        add)
            echo ""
            echo -e "  ${DIM}Add decisions (one per line, empty to finish):${NC}"
            local new_decisions=()
            # Keep existing
            while IFS= read -r existing; do
                new_decisions+=("$existing")
            done < <(echo "$key_decisions" | jq -r '.[]' 2>/dev/null)
            # Add new
            while true; do
                read -p "  + " decision
                [[ -z "$decision" ]] && break
                new_decisions+=("$decision")
            done
            key_decisions=$(printf '%s\n' "${new_decisions[@]}" | jq -R . | jq -s .)
            echo -e "  ${GREEN}✓${NC} Decisions updated"
            ;;
        clear)
            echo ""
            echo -e "  ${DIM}Enter decisions (one per line, empty to finish):${NC}"
            local fresh_decisions=()
            while true; do
                read -p "  + " decision
                [[ -z "$decision" ]] && break
                fresh_decisions+=("$decision")
            done
            key_decisions=$(printf '%s\n' "${fresh_decisions[@]}" | jq -R . | jq -s .)
            echo -e "  ${GREEN}✓${NC} Decisions replaced"
            ;;
    esac
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 3: NEXT STEPS
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}3. NEXT STEPS${NC}                                              ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local steps_count=$(echo "$next_steps" | jq 'length')
    if [[ "$steps_count" -gt 0 ]]; then
        local i=1
        echo "$next_steps" | jq -r '.[]' | while IFS= read -r step; do
            echo -e "  ${GREEN}$i.${NC} $step"
            ((i++))
        done
    else
        echo -e "  ${DIM}No next steps recorded${NC}"
    fi
    echo ""

    echo -e "  ${GREEN}[enter]${NC} Accept  ${YELLOW}[add]${NC} Add step  ${YELLOW}[reorder]${NC} Reprioritize  ${RED}[clear]${NC} Start fresh"
    read -p "  > " section3_action

    case "${section3_action,,}" in
        add)
            echo ""
            echo -e "  ${DIM}Add steps (one per line, empty to finish):${NC}"
            local new_steps=()
            while IFS= read -r existing; do
                new_steps+=("$existing")
            done < <(echo "$next_steps" | jq -r '.[]' 2>/dev/null)
            while true; do
                read -p "  + " step
                [[ -z "$step" ]] && break
                new_steps+=("$step")
            done
            next_steps=$(printf '%s\n' "${new_steps[@]}" | jq -R . | jq -s .)
            echo -e "  ${GREEN}✓${NC} Steps updated"
            ;;
        reorder)
            echo ""
            echo -e "  ${DIM}Enter step numbers in new order (e.g., '3 1 2'):${NC}"
            read -p "  Order: " new_order
            if [[ -n "$new_order" ]]; then
                local reordered=()
                local old_steps=()
                while IFS= read -r s; do
                    old_steps+=("$s")
                done < <(echo "$next_steps" | jq -r '.[]')
                for num in $new_order; do
                    if [[ "$num" =~ ^[0-9]+$ ]] && [[ $num -ge 1 ]] && [[ $num -le ${#old_steps[@]} ]]; then
                        reordered+=("${old_steps[$((num-1))]}")
                    fi
                done
                next_steps=$(printf '%s\n' "${reordered[@]}" | jq -R . | jq -s .)
                echo -e "  ${GREEN}✓${NC} Steps reordered"
            fi
            ;;
        clear)
            echo ""
            echo -e "  ${DIM}Enter steps in priority order (one per line, empty to finish):${NC}"
            local fresh_steps=()
            while true; do
                read -p "  + " step
                [[ -z "$step" ]] && break
                fresh_steps+=("$step")
            done
            next_steps=$(printf '%s\n' "${fresh_steps[@]}" | jq -R . | jq -s .)
            echo -e "  ${GREEN}✓${NC} Steps replaced"
            ;;
    esac
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 4: OPEN ITEMS
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}4. OPEN ITEMS${NC}                                              ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local open_count=$(echo "$open_items" | jq 'length')
    if [[ "$open_count" -gt 0 ]]; then
        echo "$open_items" | jq -r '.[] | "  ⚠ " + .'
    else
        echo -e "  ${DIM}No open items${NC}"
    fi
    echo ""

    echo -e "  ${GREEN}[enter]${NC} Accept  ${YELLOW}[add]${NC} Add item  ${YELLOW}[resolve]${NC} Mark resolved"
    read -p "  > " section4_action

    case "${section4_action,,}" in
        add)
            echo ""
            echo -e "  ${DIM}Add open items (one per line, empty to finish):${NC}"
            local new_open=()
            while IFS= read -r existing; do
                new_open+=("$existing")
            done < <(echo "$open_items" | jq -r '.[]' 2>/dev/null)
            while true; do
                read -p "  + " item
                [[ -z "$item" ]] && break
                new_open+=("$item")
            done
            open_items=$(printf '%s\n' "${new_open[@]}" | jq -R . | jq -s .)
            echo -e "  ${GREEN}✓${NC} Open items updated"
            ;;
        resolve)
            echo ""
            echo -e "  ${DIM}Which items are resolved? (numbers, e.g., '1 3'):${NC}"
            local j=1
            echo "$open_items" | jq -r '.[]' | while IFS= read -r item; do
                echo -e "    $j. $item"
                ((j++))
            done
            read -p "  Resolved: " resolved_nums
            if [[ -n "$resolved_nums" ]]; then
                local kept=()
                local old_items=()
                while IFS= read -r item; do
                    old_items+=("$item")
                done < <(echo "$open_items" | jq -r '.[]')
                for k in "${!old_items[@]}"; do
                    local num=$((k+1))
                    if [[ ! " $resolved_nums " =~ " $num " ]]; then
                        kept+=("${old_items[$k]}")
                    fi
                done
                open_items=$(printf '%s\n' "${kept[@]}" | jq -R . | jq -s .)
                echo -e "  ${GREEN}✓${NC} Items resolved"
            fi
            ;;
    esac
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 5: DISSENTING VIEWS (Read-only acknowledgment)
    # ═══════════════════════════════════════════════════════════════════════════

    local dissent_count=$(echo "$dissenting_views" | jq 'length')
    if [[ "$dissent_count" -gt 0 ]]; then
        echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║${NC} ${BOLD}5. DISSENTING VIEWS${NC}                                        ${CYAN}║${NC}"
        echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo "$dissenting_views" | jq -r '.[] | "  💭 " + .'
        echo ""
        echo -e "  ${DIM}(Noted for the record - these concerns may resurface)${NC}"
        echo ""
    fi

    # ═══════════════════════════════════════════════════════════════════════════
    # FINAL CONFIRMATION
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${BOLD}Ready to lock in this direction?${NC}"
    echo ""
    echo -e "    ${GREEN}[approve]${NC}   Lock in and proceed"
    echo -e "    ${YELLOW}[review]${NC}    See full summary first"
    echo -e "    ${RED}[reopen]${NC}    Go back to deliberation"
    echo ""

    while true; do
        read -p "  > " final_action

        case "${final_action,,}" in
            approve|yes|y)
                break
                ;;
            review)
                echo ""
                echo -e "  ${CYAN}Direction:${NC} $direction"
                echo -e "  ${CYAN}Rationale:${NC} $rationale"
                echo -e "  ${CYAN}Decisions:${NC} $(echo "$key_decisions" | jq -r 'join(", ")')"
                echo -e "  ${CYAN}Next Steps:${NC} $(echo "$next_steps" | jq -r 'join(", ")')"
                echo -e "  ${CYAN}Open Items:${NC} $(echo "$open_items" | jq -r 'join(", ")')"
                echo ""
                ;;
            reopen)
                echo ""
                echo -e "  ${YELLOW}!${NC} Returning to deliberation..."
                atomic_info "Direction not confirmed - reopen deliberation"
                return 1
                ;;
            *)
                echo -e "  ${DIM}Type 'approve', 'review', or 'reopen'${NC}"
                ;;
        esac
    done

    # ═══════════════════════════════════════════════════════════════════════════
    # SAVE FINALIZED DIRECTION
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    atomic_waiting "Locking in direction..."

    # Build final JSON
    jq -n \
        --arg direction "$direction" \
        --arg rationale "$rationale" \
        --argjson decisions "$key_decisions" \
        --argjson next_steps "$next_steps" \
        --argjson open_items "$open_items" \
        --argjson dissenting "$dissenting_views" \
        --arg confirmed_at "$(date -Iseconds)" \
        '{
            direction: {
                summary: $direction,
                rationale: $rationale
            },
            key_decisions: $decisions,
            next_steps: $next_steps,
            open_items: $open_items,
            dissenting_views: $dissenting,
            confirmed_at: $confirmed_at,
            confirmed_by: "human"
        }' > "$selected_json"

    # Build markdown documentation
    cat > "$selected_md" << EOF
# Selected Direction

**Confirmed:** $(date -Iseconds)

---

## Direction

**$direction**

$rationale

---

## Key Decisions

$(echo "$key_decisions" | jq -r '.[] | "- " + .')

---

## Next Steps

$(echo "$next_steps" | jq -r 'to_entries | .[] | "\(.key + 1). " + .value')

---

## Open Items

$(echo "$open_items" | jq -r 'if length > 0 then .[] | "- ⚠ " + . else "None" end')

---

## Dissenting Views

$(echo "$dissenting_views" | jq -r 'if length > 0 then .[] | "- 💭 " + . else "None recorded" end')

---

*This direction was confirmed through Discovery Conversation deliberation.*
EOF

    echo -e "  ${GREEN}✓${NC} Direction locked in"
    echo ""

    # Summary
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${BOLD}Direction Confirmed${NC}"
    echo ""
    echo -e "  ${CYAN}$direction${NC}"
    echo ""
    echo -e "  Next steps: $(echo "$next_steps" | jq 'length')"
    echo -e "  Open items: $(echo "$open_items" | jq 'length')"
    echo ""

    atomic_context_artifact "selected_approach" "$selected_json" "Confirmed direction"
    atomic_context_artifact "selected_approach_doc" "$selected_md" "Direction documentation"
    atomic_context_decision "Direction confirmed: $direction" "human_gate"

    atomic_success "Direction confirmed"

    return 0
}
