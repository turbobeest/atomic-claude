#!/bin/bash
#
# Task 203: PRD Interview (Confirmatory) - OPTIONAL
# Gather/confirm key PRD inputs: stakeholders, success criteria, non-goals, MVP
#
# This is a confirmatory interview - we PROPOSE values based on Phase 1
# and the user confirms or adjusts them.
#
# This task is OPTIONAL - can be skipped if no stakeholders are available
# or if defaults are acceptable.
#

task_203_prd_interview() {
    local phase1_dir="$ATOMIC_OUTPUT_DIR/1-discovery"
    local interview_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prd-interview.json"

    atomic_step "PRD Interview (Optional)"

    echo ""
    echo -e "${DIM}  ┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${DIM}  │ Confirmatory interview to refine PRD inputs.           │${NC}"
    echo -e "${DIM}  │                                                         │${NC}"
    echo -e "${DIM}  │ You may answer as yourself, on behalf of stakeholders, │${NC}"
    echo -e "${DIM}  │ or use sensible defaults to proceed quickly.           │${NC}"
    echo -e "${DIM}  └─────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # OPTIONAL SKIP
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "  ${CYAN}This task is optional.${NC}"
    echo ""
    echo -e "    ${GREEN}[continue]${NC}  Conduct stakeholder interview"
    echo -e "    ${YELLOW}[defaults]${NC}  Use default values (skip interview)"
    echo -e "    ${DIM}[skip]${NC}      Skip entirely (no interview data)"
    echo ""

    read -p "  Choice [continue]: " skip_choice
    skip_choice=${skip_choice:-continue}

    case "$skip_choice" in
        defaults|d)
            echo ""
            echo -e "  ${GREEN}✓${NC} Using default interview values"
            _203_save_defaults "$interview_file"
            atomic_context_artifact "prd-interview" "$interview_file" "PRD interview (defaults)"
            atomic_context_decision "PRD interview skipped - using defaults" "interview"
            atomic_success "PRD interview complete (defaults)"
            return 0
            ;;
        skip|s)
            echo ""
            echo -e "  ${YELLOW}!${NC} Interview skipped - no interview data will be available"
            atomic_context_decision "PRD interview skipped entirely" "interview"
            atomic_warn "PRD interview skipped"
            return 0
            ;;
    esac

    echo ""

    # Initialize interview data as arrays
    local stakeholders=()
    local success_criteria=()
    local non_goals=()
    local mvp_scope=()

    # ═══════════════════════════════════════════════════════════════════════════
    # STAKEHOLDERS
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}1. STAKEHOLDERS${NC}                                           ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Propose default stakeholders
    echo -e "  ${DIM}PROPOSED stakeholders:${NC}"
    echo -e "    • End users (primary)"
    echo -e "    • Development team"
    echo -e "    • Product owner"
    echo ""
    echo -e "  ${CYAN}Options:${NC}"
    echo -e "    ${GREEN}[confirm]${NC}  Accept proposed stakeholders"
    echo -e "    ${YELLOW}[adjust]${NC}   Add or modify stakeholders"
    echo ""

    read -p "  Choice [confirm]: " stake_choice
    stake_choice=${stake_choice:-confirm}

    if [[ "$stake_choice" == "adjust" ]]; then
        echo ""
        echo -e "  ${DIM}Enter stakeholders (one per line, empty line to finish):${NC}"
        stakeholders=()
        while true; do
            read -p "    > " stakeholder
            [[ -z "$stakeholder" ]] && break
            stakeholders+=("$stakeholder")
        done
    else
        stakeholders=("End users (primary)" "Development team" "Product owner")
    fi

    echo -e "  ${GREEN}✓${NC} Stakeholders confirmed"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # SUCCESS CRITERIA
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}2. SUCCESS CRITERIA${NC}                                       ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "  ${DIM}PROPOSED success criteria:${NC}"
    echo -e "    • Core functionality works as specified"
    echo -e "    • Passes all acceptance tests"
    echo -e "    • Documentation complete"
    echo ""
    echo -e "  ${CYAN}Options:${NC}"
    echo -e "    ${GREEN}[confirm]${NC}  Accept proposed criteria"
    echo -e "    ${YELLOW}[adjust]${NC}   Define specific metrics"
    echo ""

    read -p "  Choice [confirm]: " success_choice
    success_choice=${success_choice:-confirm}

    if [[ "$success_choice" == "adjust" ]]; then
        echo ""
        echo -e "  ${DIM}Enter success criteria (one per line, empty line to finish):${NC}"
        success_criteria=()
        while true; do
            read -p "    > " criterion
            [[ -z "$criterion" ]] && break
            success_criteria+=("$criterion")
        done
    else
        success_criteria=("Core functionality works as specified" "Passes all acceptance tests" "Documentation complete")
    fi

    echo -e "  ${GREEN}✓${NC} Success criteria confirmed"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # NON-GOALS
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}3. NON-GOALS (Out of Scope)${NC}                               ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "  ${DIM}PROPOSED non-goals (explicitly out of scope):${NC}"
    echo -e "    • Performance optimization (defer to later)"
    echo -e "    • Full production deployment"
    echo -e "    • Comprehensive error handling for edge cases"
    echo ""
    echo -e "  ${CYAN}Options:${NC}"
    echo -e "    ${GREEN}[confirm]${NC}  Accept proposed non-goals"
    echo -e "    ${YELLOW}[adjust]${NC}   Define specific non-goals"
    echo ""

    read -p "  Choice [confirm]: " nongoal_choice
    nongoal_choice=${nongoal_choice:-confirm}

    if [[ "$nongoal_choice" == "adjust" ]]; then
        echo ""
        echo -e "  ${DIM}Enter non-goals (one per line, empty line to finish):${NC}"
        non_goals=()
        while true; do
            read -p "    > " nongoal
            [[ -z "$nongoal" ]] && break
            non_goals+=("$nongoal")
        done
    else
        non_goals=("Performance optimization (defer to later)" "Full production deployment" "Comprehensive error handling for edge cases")
    fi

    echo -e "  ${GREEN}✓${NC} Non-goals confirmed"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # MVP SCOPE
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}4. MVP SCOPE${NC}                                              ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "  ${DIM}What's the minimum viable scope for Phase 1 delivery?${NC}"
    echo ""
    echo -e "  ${DIM}Enter MVP features (one per line, empty line to finish):${NC}"

    mvp_scope=()
    while true; do
        read -p "    > " mvp_item
        [[ -z "$mvp_item" ]] && break
        mvp_scope+=("$mvp_item")
    done

    if [[ ${#mvp_scope[@]} -eq 0 ]]; then
        mvp_scope=("Core feature implementation" "Basic error handling" "Unit tests for critical paths")
    fi

    echo ""
    echo -e "  ${GREEN}✓${NC} MVP scope defined"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # SAVE INTERVIEW
    # ═══════════════════════════════════════════════════════════════════════════

    # Convert arrays to JSON arrays
    local stakeholders_json=$(printf '%s\n' "${stakeholders[@]}" | jq -R 'select(length > 0)' | jq -s '.')
    local success_json=$(printf '%s\n' "${success_criteria[@]}" | jq -R 'select(length > 0)' | jq -s '.')
    local nongoals_json=$(printf '%s\n' "${non_goals[@]}" | jq -R 'select(length > 0)' | jq -s '.')
    local mvp_json=$(printf '%s\n' "${mvp_scope[@]}" | jq -R 'select(length > 0)' | jq -s '.')

    jq -n \
        --argjson stakeholders "$stakeholders_json" \
        --argjson success "$success_json" \
        --argjson nongoals "$nongoals_json" \
        --argjson mvp "$mvp_json" \
        '{
            "stakeholders": $stakeholders,
            "success_criteria": $success,
            "non_goals": $nongoals,
            "mvp_scope": $mvp,
            "interview_at": (now | todate)
        }' > "$interview_file"

    atomic_context_artifact "prd-interview" "$interview_file" "PRD interview responses"
    atomic_context_decision "PRD interview completed" "interview"

    atomic_success "PRD interview complete"

    return 0
}

# Save default interview values
_203_save_defaults() {
    local interview_file="$1"

    jq -n '{
        "stakeholders": ["End users (primary)", "Development team", "Product owner"],
        "success_criteria": ["Core functionality works as specified", "Passes all acceptance tests", "Documentation complete"],
        "non_goals": ["Performance optimization (defer to later)", "Full production deployment", "Comprehensive error handling for edge cases"],
        "mvp_scope": ["Core feature implementation", "Basic error handling", "Unit tests for critical paths"],
        "interview_at": (now | todate),
        "source": "defaults"
    }' > "$interview_file"
}
