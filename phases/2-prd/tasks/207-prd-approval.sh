#!/bin/bash
#
# Task 207: PRD Approval (Human Gate)
# Human reviews and approves the PRD document
#
# This is a REQUIRED human gate - the PRD must be approved
# before proceeding to Phase 3.
#

task_207_prd_approval() {
    local prd_file="$ATOMIC_ROOT/docs/prd/PRD.md"
    local validation_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prd-validation.json"
    local approval_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prd-approved.json"

    atomic_step "PRD Approval (Human Gate)"

    echo ""
    echo -e "${YELLOW}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║${NC}                    ${BOLD}HUMAN GATE${NC}                              ${YELLOW}║${NC}"
    echo -e "${YELLOW}║${NC}                  ${BOLD}PRD APPROVAL${NC}                             ${YELLOW}║${NC}"
    echo -e "${YELLOW}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # PRD SUMMARY
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}  PRD Summary:${NC}"
    echo ""

    if [[ -f "$prd_file" ]]; then
        local line_count=$(wc -l < "$prd_file")
        local word_count=$(wc -w < "$prd_file")
        local section_count=$(grep -c '^##' "$prd_file" 2>/dev/null || echo 0)

        echo -e "    Location:    ${BOLD}$prd_file${NC}"
        echo -e "    Lines:       $line_count"
        echo -e "    Words:       $word_count"
        echo -e "    Sections:    $section_count"
    else
        echo -e "    ${RED}PRD file not found!${NC}"
        return 1
    fi

    echo ""

    # Show validation summary
    if [[ -f "$validation_file" ]]; then
        local val_status=$(jq -r '.overall_status // "UNKNOWN"' "$validation_file")
        local completeness=$(jq -r '.completeness.score // 0' "$validation_file")

        local status_color="${GREEN}"
        [[ "$val_status" == "WARN" ]] && status_color="${YELLOW}"
        [[ "$val_status" == "FAIL" ]] && status_color="${RED}"

        echo -e "${CYAN}  Validation Status:${NC}"
        echo -e "    Overall:      ${status_color}$val_status${NC}"
        echo -e "    Completeness: $completeness%"
        echo ""
    fi

    # ═══════════════════════════════════════════════════════════════════════════
    # APPROVAL OPTIONS
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${CYAN}Please review the PRD and select an option:${NC}"
    echo ""
    echo -e "    ${GREEN}[approve]${NC}   Approve PRD and proceed to Phase 3"
    echo -e "    ${YELLOW}[revise]${NC}    Request revisions (returns to authoring)"
    echo -e "    ${CYAN}[view]${NC}      View PRD content"
    echo -e "    ${MAGENTA}[discuss]${NC}   Add notes for discussion"
    echo ""

    while true; do
        read -p "  Choice: " approval_choice

        case "$approval_choice" in
            approve|a)
                echo ""
                read -p "  Approver name: " approver_name
                approver_name=${approver_name:-"Anonymous"}

                read -p "  Any notes? (optional): " approval_notes

                # Save approval
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
                echo -e "  ${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
                echo -e "  ${GREEN}║${NC}                   ${BOLD}PRD APPROVED${NC}                           ${GREEN}║${NC}"
                echo -e "  ${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
                echo ""

                # Register approval artifact for downstream phases
                atomic_context_artifact "prd_approval" "$approval_file" "PRD approval record"
                atomic_context_decision "PRD approved by $approver_name" "approval"
                atomic_success "PRD approved - ready for Phase 3"

                return 0
                ;;

            revise|r)
                echo ""
                read -p "  Revision notes: " revision_notes

                # Save revision request
                jq -n \
                    --arg notes "$revision_notes" \
                    '{
                        "status": "revision_requested",
                        "notes": $notes,
                        "requested_at": (now | todate)
                    }' > "$approval_file"

                # Register revision request artifact
                atomic_context_artifact "prd_revision_request" "$approval_file" "PRD revision request"
                atomic_context_decision "PRD revision requested: $revision_notes" "revision"
                atomic_warn "Revision requested - returning to authoring"

                return 1
                ;;

            view|v)
                echo ""
                echo -e "${DIM}━━━━━━━━━━━━━━━ PRD CONTENT ━━━━━━━━━━━━━━━${NC}"
                echo ""
                head -100 "$prd_file" | sed 's/^/  /'
                echo ""
                echo -e "${DIM}  ... (showing first 100 lines)${NC}"
                echo -e "${DIM}  Full file: $prd_file${NC}"
                echo ""
                echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                echo ""
                ;;

            discuss|d)
                echo ""
                echo -e "  ${DIM}Enter discussion notes (empty line to finish):${NC}"
                local discussion=""
                while true; do
                    read -p "    > " note_line
                    [[ -z "$note_line" ]] && break
                    discussion+="$note_line\n"
                done

                if [[ -n "$discussion" ]]; then
                    # Append to discussion file
                    local discuss_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prd-discussion.md"
                    echo -e "\n## Discussion $(date -Iseconds)\n" >> "$discuss_file"
                    echo -e "$discussion" >> "$discuss_file"
                    echo -e "  ${GREEN}✓${NC} Notes saved to prd-discussion.md"
                fi
                echo ""
                ;;

            *)
                echo -e "  ${RED}Invalid choice. Enter approve, revise, view, or discuss.${NC}"
                echo ""
                ;;
        esac
    done
}
