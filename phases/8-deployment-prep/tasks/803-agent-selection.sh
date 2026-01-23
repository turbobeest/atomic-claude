#!/bin/bash
#
# Task 803: Agent Selection
# Present and select deployment preparation agents
#

task_803_agent_selection() {
    local agents_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/deployment-agents.json"
    local roster_file="$ATOMIC_ROOT/.claude/agent-roster.json"

    atomic_step "Agent Selection"

    echo ""
    echo -e "  ${DIM}Select agents for deployment preparation.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # DEPLOYMENT PREP WORKFLOW
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- DEPLOYMENT PREP WORKFLOW${NC}"
    echo ""

    echo -e "    Release Packager ────────┐"
    echo -e "        ${DIM}(build artifacts)${NC}    │"
    echo -e "    Changelog Writer ────────┤"
    echo -e "        ${DIM}(version notes)${NC}      ├→  Deployment Approval"
    echo -e "    Documentation Gen ───────┤       ${DIM}(human gate)${NC}"
    echo -e "        ${DIM}(user guides)${NC}        │"
    echo -e "    Install Guide Writer ────┘"
    echo -e "        ${DIM}(setup instructions)${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # AVAILABLE AGENTS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- AVAILABLE AGENTS${NC}"
    echo ""

    # Release Packager
    echo -e "  ${CYAN}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "  ${BOLD}RELEASE PACKAGER${NC}"
    echo ""
    echo -e "    Prepares release package (setup.py, pyproject.toml, etc.)."
    echo -e "    Builds distribution artifacts for selected channels."
    echo -e "    ${GREEN}Recommended:${NC} release-packager-phd (sonnet)"
    echo -e "  ${CYAN}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    # Changelog Writer
    echo -e "  ${MAGENTA}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "  ${BOLD}CHANGELOG WRITER${NC}"
    echo ""
    echo -e "    Generates changelog from commits and PRD."
    echo -e "    Follows Keep a Changelog format."
    echo -e "    ${GREEN}Recommended:${NC} changelog-writer-phd (sonnet)"
    echo -e "  ${MAGENTA}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    # Documentation Generator
    echo -e "  ${YELLOW}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "  ${BOLD}DOCUMENTATION GENERATOR${NC}"
    echo ""
    echo -e "    Generates comprehensive user documentation."
    echo -e "    Creates API references and usage guides."
    echo -e "    ${GREEN}Recommended:${NC} documentation-generator-phd (opus)"
    echo -e "  ${YELLOW}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    # Installation Guide Writer
    echo -e "  ${BLUE}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "  ${BOLD}INSTALLATION GUIDE WRITER${NC}"
    echo ""
    echo -e "    Creates installation and quick-start guide."
    echo -e "    Platform-specific instructions and troubleshooting."
    echo -e "    ${GREEN}Recommended:${NC} installation-guide-writer-phd (sonnet)"
    echo -e "  ${BLUE}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # AGENT SELECTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- AGENT SELECTION${NC}"
    echo ""

    echo -e "  ${DIM}Select agents for each role:${NC}"
    echo ""

    local selected_agents=()

    # Release Packager selection
    echo -e "  ${CYAN}Release Packager:${NC}"
    echo -e "    ${GREEN}[1]${NC} release-packager-phd (sonnet) - Recommended"
    echo -e "    ${DIM}[2]${NC} release-packager (haiku) - Fast, standard"
    echo -e "    ${YELLOW}[c]${NC} Custom agent"
    echo ""
    read -p "  Select [1]: " packager_choice
    packager_choice=${packager_choice:-1}

    case "$packager_choice" in
        1) selected_agents+=("release-packager-phd:sonnet") ;;
        2) selected_agents+=("release-packager:haiku") ;;
        c|C)
            read -p "  Custom agent name: " custom_name
            read -p "  Custom agent model [sonnet]: " custom_model
            custom_model=${custom_model:-sonnet}
            selected_agents+=("$custom_name:$custom_model")
            ;;
        *) selected_agents+=("release-packager-phd:sonnet") ;;
    esac
    echo ""

    # Changelog Writer selection
    echo -e "  ${MAGENTA}Changelog Writer:${NC}"
    echo -e "    ${GREEN}[1]${NC} changelog-writer-phd (sonnet) - Recommended"
    echo -e "    ${DIM}[2]${NC} changelog-writer (haiku) - Fast, standard"
    echo -e "    ${YELLOW}[c]${NC} Custom agent"
    echo ""
    read -p "  Select [1]: " changelog_choice
    changelog_choice=${changelog_choice:-1}

    case "$changelog_choice" in
        1) selected_agents+=("changelog-writer-phd:sonnet") ;;
        2) selected_agents+=("changelog-writer:haiku") ;;
        c|C)
            read -p "  Custom agent name: " custom_name
            read -p "  Custom agent model [sonnet]: " custom_model
            custom_model=${custom_model:-sonnet}
            selected_agents+=("$custom_name:$custom_model")
            ;;
        *) selected_agents+=("changelog-writer-phd:sonnet") ;;
    esac
    echo ""

    # Documentation Generator selection
    echo -e "  ${YELLOW}Documentation Generator:${NC}"
    echo -e "    ${GREEN}[1]${NC} documentation-generator-phd (opus) - Recommended"
    echo -e "    ${DIM}[2]${NC} documentation-generator (sonnet) - Standard"
    echo -e "    ${YELLOW}[c]${NC} Custom agent"
    echo ""
    read -p "  Select [1]: " docs_choice
    docs_choice=${docs_choice:-1}

    case "$docs_choice" in
        1) selected_agents+=("documentation-generator-phd:opus") ;;
        2) selected_agents+=("documentation-generator:sonnet") ;;
        c|C)
            read -p "  Custom agent name: " custom_name
            read -p "  Custom agent model [opus]: " custom_model
            custom_model=${custom_model:-opus}
            selected_agents+=("$custom_name:$custom_model")
            ;;
        *) selected_agents+=("documentation-generator-phd:opus") ;;
    esac
    echo ""

    # Installation Guide Writer selection
    echo -e "  ${BLUE}Installation Guide Writer:${NC}"
    echo -e "    ${GREEN}[1]${NC} installation-guide-writer-phd (sonnet) - Recommended"
    echo -e "    ${DIM}[2]${NC} installation-guide-writer (haiku) - Fast, standard"
    echo -e "    ${YELLOW}[c]${NC} Custom agent"
    echo ""
    read -p "  Select [1]: " install_choice
    install_choice=${install_choice:-1}

    case "$install_choice" in
        1) selected_agents+=("installation-guide-writer-phd:sonnet") ;;
        2) selected_agents+=("installation-guide-writer:haiku") ;;
        c|C)
            read -p "  Custom agent name: " custom_name
            read -p "  Custom agent model [sonnet]: " custom_model
            custom_model=${custom_model:-sonnet}
            selected_agents+=("$custom_name:$custom_model")
            ;;
        *) selected_agents+=("installation-guide-writer-phd:sonnet") ;;
    esac
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # SELECTION SUMMARY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- SELECTION SUMMARY${NC}"
    echo ""

    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "  ${BOLD}SELECTED AGENTS${NC}"
    echo ""
    for agent in "${selected_agents[@]}"; do
        IFS=':' read -r name model <<< "$agent"
        echo -e "    ${GREEN}✓${NC} $name ($model)"
    done
    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    # Save agent selection
    local agents_json=$(printf '%s\n' "${selected_agents[@]}" | jq -R . | jq -s .)

    jq -n \
        --argjson agents "$agents_json" \
        '{
            "phase": 8,
            "agents": $agents,
            "selected_at": (now | todate)
        }' > "$agents_file"

    atomic_context_artifact "$agents_file" "deployment-agents" "Selected deployment agents"
    atomic_context_decision "Deployment agents selected: ${#selected_agents[@]} agents" "agents"

    atomic_success "Agent Selection complete"

    return 0
}
