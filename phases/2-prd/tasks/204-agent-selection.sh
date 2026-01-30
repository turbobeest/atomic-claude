#!/bin/bash
#
# Task 204: Agent Selection
# Select agents for PRD authoring and validation
#
# Core agents:
#   - requirements-engineer (opus) - Synthesize requirements
#   - prd-writer (opus) - Author PRD document
#   - prd-validator (sonnet) - Validate completeness
#

task_204_agent_selection() {
    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/../0-setup/project-config.json"
    local agents_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/selected-agents.json"

    atomic_step "Agent Selection"

    echo ""
    echo -e "${DIM}  ┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${DIM}  │ Select agents for PRD authoring and validation.        │${NC}"
    echo -e "${DIM}  │                                                         │${NC}"
    echo -e "${DIM}  │ Tip: Custom agents can be created in the agent repo's  │${NC}"
    echo -e "${DIM}  │ custom/ directory for project-specific needs.          │${NC}"
    echo -e "${DIM}  └─────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # CORE AGENTS
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}CORE PRD AGENTS${NC}                                           ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "  ${BOLD}Authoring Agents:${NC}"
    echo -e "    ${GREEN}requirements-engineer${NC} (opus)"
    echo -e "      ${DIM}Synthesizes requirements into structured format${NC}"
    echo -e "      ${DIM}Uses RFC 2119 + EARS syntax${NC}"
    echo ""
    echo -e "    ${GREEN}prd-writer${NC} (opus)"
    echo -e "      ${DIM}Authors formal PRD using 15-section template${NC}"
    echo ""
    echo -e "  ${BOLD}Validation Agents:${NC}"
    echo -e "    ${GREEN}prd-validator${NC} (sonnet)"
    echo -e "      ${DIM}Validates completeness, clarity, consistency${NC}"
    echo -e "      ${DIM}Generates Gherkin scenarios${NC}"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # SUGGESTED ADDITIONAL AGENTS
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}SUGGESTED ADDITIONAL AGENTS${NC}                               ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "  ${DIM}Based on your project, consider adding:${NC}"
    echo ""
    echo -e "    ${YELLOW}security-requirements-analyst${NC} (sonnet)"
    echo -e "      ${DIM}For projects with security requirements${NC}"
    echo ""
    echo -e "    ${YELLOW}api-requirements-engineer${NC} (sonnet)"
    echo -e "      ${DIM}For API-heavy projects${NC}"
    echo ""
    echo -e "    ${YELLOW}ux-requirements-analyst${NC} (haiku)"
    echo -e "      ${DIM}For user-facing applications${NC}"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # SELECTION
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${CYAN}How would you like to proceed?${NC}"
    echo ""
    echo -e "    ${GREEN}[approve]${NC}   Use core agents only (recommended)"
    echo -e "    ${YELLOW}[add]${NC}       Add suggested agents"
    echo -e "    ${CYAN}[custom]${NC}    Specify custom agent selection"
    echo -e "    ${MAGENTA}[list]${NC}      Browse available agents"
    echo ""

    atomic_drain_stdin
    read -e -p "  Choice [approve]: " agent_choice || true
    agent_choice=${agent_choice:-approve}

    local selected_agents='["requirements-engineer", "prd-writer", "prd-validator"]'
    local additional_agents='[]'

    case "$agent_choice" in
        add)
            echo ""
            echo -e "  ${DIM}Select additional agents (space-separated numbers):${NC}"
            echo -e "    1. security-requirements-analyst"
            echo -e "    2. api-requirements-engineer"
            echo -e "    3. ux-requirements-analyst"
            echo ""
            read -e -p "  > " add_selection || true

            for num in $add_selection; do
                case "$num" in
                    1) additional_agents=$(echo "$additional_agents" | jq '. += ["security-requirements-analyst"]') ;;
                    2) additional_agents=$(echo "$additional_agents" | jq '. += ["api-requirements-engineer"]') ;;
                    3) additional_agents=$(echo "$additional_agents" | jq '. += ["ux-requirements-analyst"]') ;;
                esac
            done
            ;;
        custom)
            echo ""
            echo -e "  ${DIM}Enter agent names (one per line, empty to finish):${NC}"
            selected_agents='[]'
            while true; do
                read -e -p "    > " agent_name || true
                [[ -z "$agent_name" ]] && break
                selected_agents=$(echo "$selected_agents" | jq --arg a "$agent_name" '. += [$a]')
            done
            ;;
        list)
            _204_list_agents
            echo ""
            read -e -p "  Press Enter to continue with core agents..." _ || true
            ;;
    esac

    # Merge core and additional agents
    local all_agents=$(echo "$selected_agents" "$additional_agents" | jq -s 'add | unique')

    echo ""
    echo -e "  ${GREEN}✓${NC} Selected agents:"
    echo "$all_agents" | jq -r '.[]' | while read -r agent; do
        echo -e "    • $agent"
    done
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # SAVE SELECTION
    # ═══════════════════════════════════════════════════════════════════════════

    jq -n \
        --argjson selected "$all_agents" \
        --argjson additional "$additional_agents" \
        '{
            "phase": 2,
            "phase_name": "PRD",
            "selected": $selected,
            "core": ["requirements-engineer", "prd-writer", "prd-validator"],
            "additional": $additional,
            "selected_at": (now | todate)
        }' > "$agents_file"

    atomic_context_artifact "selected-agents" "$agents_file" "Phase 2 agent selection"
    atomic_context_decision "Agents selected for PRD: $(echo "$all_agents" | jq -r 'join(", ")')" "agents"

    atomic_success "Agent selection complete"

    return 0
}

# List available agents from repository
_204_list_agents() {
    local config_file="$ATOMIC_OUTPUT_DIR/0-setup/project-config.json"
    local agent_repo=$(jq -r '.agents.repository // ""' "$config_file" 2>/dev/null)

    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}AVAILABLE AGENTS${NC}                                          ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if [[ -z "$agent_repo" || "$agent_repo" == "null" || "$agent_repo" == "builtin" ]]; then
        echo -e "  ${DIM}Using built-in agents (external repository not configured)${NC}"
        echo ""
        echo -e "  ${BOLD}PRD-related built-in agents:${NC}"
        echo -e "    • requirements-engineer"
        echo -e "    • prd-writer"
        echo -e "    • prd-validator"
        echo -e "    • security-requirements-analyst"
        echo -e "    • api-requirements-engineer"
        return
    fi

    # List from pipeline-agents directory
    local pipeline_dir="$agent_repo/pipeline-agents"
    if [[ -d "$pipeline_dir" ]]; then
        echo -e "  ${BOLD}Pipeline Agents:${NC}"
        find "$pipeline_dir" -name "*.md" -type f 2>/dev/null | head -20 | while read -r f; do
            local name=$(basename "$f" .md)
            echo -e "    • $name"
        done
    fi

    echo ""
}
