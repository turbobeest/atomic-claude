#!/bin/bash
#
# Task 202: PRD Setup
# Recap approach from Phase 1, confirm scope and focus areas
#
# Steps:
#   1. Display selected approach summary
#   2. Confirm/adjust scope
#   3. Identify key focus areas for PRD
#

task_202_prd_setup() {
    local phase1_dir="$ATOMIC_OUTPUT_DIR/1-discovery"
    local setup_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prd-setup.json"

    atomic_step "PRD Setup"

    mkdir -p "$(dirname "$setup_file")"

    echo ""
    echo -e "${DIM}  ┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${DIM}  │ Before writing the PRD, let's confirm scope and focus. │${NC}"
    echo -e "${DIM}  └─────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # RECAP SELECTED APPROACH
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}SELECTED APPROACH (from Phase 1)${NC}                          ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local approach_name="unknown"
    local approach_summary=""
    local approach_rationale=""

    if [[ -f "$phase1_dir/selected-approach.json" ]]; then
        approach_name=$(jq -r '.name // "unnamed"' "$phase1_dir/selected-approach.json")
        approach_summary=$(jq -r '.summary // ""' "$phase1_dir/selected-approach.json")
        approach_rationale=$(jq -r '.rationale // ""' "$phase1_dir/selected-approach.json")

        echo -e "  ${BOLD}$approach_name${NC}"
        echo ""
        [[ -n "$approach_summary" ]] && echo -e "  ${DIM}$approach_summary${NC}"
        echo ""
        [[ -n "$approach_rationale" ]] && echo -e "  ${DIM}Rationale: $approach_rationale${NC}"
    else
        echo -e "  ${YELLOW}No approach file found - proceeding with general PRD${NC}"
    fi

    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # CONFIRM SCOPE
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}CONFIRM SCOPE${NC}                                             ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "  ${DIM}What should this PRD focus on?${NC}"
    echo ""
    echo -e "    ${GREEN}[full]${NC}      Full product/feature (comprehensive)"
    echo -e "    ${YELLOW}[mvp]${NC}       MVP scope only (minimal viable)"
    echo -e "    ${CYAN}[component]${NC} Single component/module"
    echo -e "    ${MAGENTA}[custom]${NC}    Define custom scope"
    echo ""

    read -e -p "  Scope [mvp]: " scope_choice || true
    scope_choice=${scope_choice:-mvp}

    local scope_type="$scope_choice"
    local scope_description=""

    case "$scope_choice" in
        full)
            scope_description="Comprehensive PRD covering all features and requirements"
            ;;
        mvp)
            scope_description="Minimal viable product - core features only"
            ;;
        component)
            echo ""
            read -e -p "  Component name: " component_name || true
            scope_description="Single component: $component_name"
            ;;
        custom)
            echo ""
            read -e -p "  Describe scope: " custom_scope || true
            scope_description="$custom_scope"
            ;;
    esac

    echo ""
    echo -e "  ${GREEN}✓${NC} Scope: $scope_type"
    echo -e "    ${DIM}$scope_description${NC}"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # FOCUS AREAS
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}FOCUS AREAS${NC}                                               ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "  ${DIM}Which areas need extra attention in the PRD?${NC}"
    echo -e "  ${DIM}(Select multiple with spaces, e.g., '1 3 5')${NC}"
    echo ""
    echo -e "    ${DIM}1.${NC} Technical architecture"
    echo -e "    ${DIM}2.${NC} API/interface design"
    echo -e "    ${DIM}3.${NC} Data models/schemas"
    echo -e "    ${DIM}4.${NC} Security requirements"
    echo -e "    ${DIM}5.${NC} Performance requirements"
    echo -e "    ${DIM}6.${NC} Integration points"
    echo -e "    ${DIM}7.${NC} Testing strategy"
    echo -e "    ${DIM}8.${NC} Deployment/operations"
    echo ""

    read -e -p "  Focus areas [1 2 7]: " focus_input || true
    focus_input=${focus_input:-"1 2 7"}

    local focus_areas=()
    for num in $focus_input; do
        case "$num" in
            1) focus_areas+=("architecture") ;;
            2) focus_areas+=("api_design") ;;
            3) focus_areas+=("data_models") ;;
            4) focus_areas+=("security") ;;
            5) focus_areas+=("performance") ;;
            6) focus_areas+=("integrations") ;;
            7) focus_areas+=("testing") ;;
            8) focus_areas+=("deployment") ;;
        esac
    done

    echo ""
    echo -e "  ${GREEN}✓${NC} Focus areas: ${focus_areas[*]}"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # SAVE SETUP
    # ═══════════════════════════════════════════════════════════════════════════

    # Build focus areas JSON array
    local focus_json="[]"
    for area in "${focus_areas[@]}"; do
        focus_json=$(echo "$focus_json" | jq --arg a "$area" '. += [$a]')
    done

    jq -n \
        --arg approach "$approach_name" \
        --arg scope_type "$scope_type" \
        --arg scope_desc "$scope_description" \
        --argjson focus "$focus_json" \
        '{
            "approach": $approach,
            "scope": {
                "type": $scope_type,
                "description": $scope_desc
            },
            "focus_areas": $focus,
            "setup_at": (now | todate)
        }' > "$setup_file"

    atomic_context_artifact "prd-setup" "$setup_file" "PRD setup configuration"
    atomic_context_decision "PRD scope: $scope_type, focus: ${focus_areas[*]}" "setup"

    atomic_success "PRD setup complete"

    return 0
}
