#!/bin/bash
#
# Task 903: Agent Selection
# Present and select release agents
#

task_903_agent_selection() {
    local agents_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/release-agents.json"
    local roster_file="$ATOMIC_ROOT/.claude/agent-roster.json"

    atomic_step "Agent Selection"

    echo ""
    echo -e "  ${DIM}Select agents for release execution.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # RELEASE WORKFLOW
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- RELEASE WORKFLOW${NC}"
    echo ""

    echo -e "    Announcement Writer ────→  Release Confirmation"
    echo -e "        ${DIM}(internal notes)${NC}          ${DIM}(human gate)${NC}"
    echo ""

    # Future workflow with external channels (hidden for now):
    # echo -e "    GitHub Releaser ─────────┐"
    # echo -e "        ${DIM}(create tag)${NC}         │"
    # echo -e "    Package Publisher ───────┼→  Release Confirmation"
    # echo -e "        ${DIM}(registry upload)${NC}    │       ${DIM}(human gate)${NC}"
    # echo -e "    Announcement Writer ─────┘"
    # echo -e "        ${DIM}(stakeholder comms)${NC}"

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # AVAILABLE AGENTS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- AVAILABLE AGENTS${NC}"
    echo ""

    # Future agents (hidden for now):
    # # GitHub Releaser
    # echo -e "  ${CYAN}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    # echo -e "  ${BOLD}GITHUB RELEASER${NC}"
    # echo ""
    # echo -e "    Creates GitHub release with tag and release notes."
    # echo -e "    Uploads distribution artifacts to release."
    # echo -e "    ${GREEN}Recommended:${NC} github-releaser-phd (sonnet)"
    # echo -e "  ${CYAN}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    # echo ""
    #
    # # Package Publisher
    # echo -e "  ${MAGENTA}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    # echo -e "  ${BOLD}PACKAGE PUBLISHER${NC}"
    # echo ""
    # echo -e "    Publishes package to PyPI/npm/registry."
    # echo -e "    Handles authentication and upload."
    # echo -e "    ${GREEN}Recommended:${NC} package-publisher-phd (haiku)"
    # echo -e "  ${MAGENTA}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    # echo ""

    # Announcement Writer
    echo -e "  ${YELLOW}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "  ${BOLD}ANNOUNCEMENT WRITER${NC}"
    echo ""
    echo -e "    Drafts internal release notes for stakeholders."
    echo -e "    Documents version changes and highlights."
    echo -e "    ${GREEN}Recommended:${NC} announcement-writer-phd (haiku)"
    echo -e "  ${YELLOW}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # AGENT SELECTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- AGENT SELECTION${NC}"
    echo ""

    echo -e "  ${DIM}Select agents for each role:${NC}"
    echo ""

    # Drain any buffered stdin before agent selection
    atomic_drain_stdin

    local selected_agents=()

    # Future agent selections (hidden for now):
    # # GitHub Releaser selection
    # echo -e "  ${CYAN}GitHub Releaser:${NC}"
    # echo -e "    ${GREEN}[1]${NC} github-releaser-phd (sonnet) - Recommended"
    # echo -e "    ${DIM}[2]${NC} github-releaser (haiku) - Fast, standard"
    # echo -e "    ${YELLOW}[c]${NC} Custom agent"
    # echo ""
    # read -e -p "  Select [1]: " gh_choice || true
    # gh_choice=${gh_choice:-1}
    #
    # case "$gh_choice" in
    #     1) selected_agents+=("github-releaser-phd:sonnet") ;;
    #     2) selected_agents+=("github-releaser:haiku") ;;
    #     c|C)
    #         read -e -p "  Custom agent name: " custom_name || true
    #         read -e -p "  Custom agent model [sonnet]: " custom_model || true
    #         custom_model=${custom_model:-sonnet}
    #         selected_agents+=("$custom_name:$custom_model")
    #         ;;
    #     *) selected_agents+=("github-releaser-phd:sonnet") ;;
    # esac
    # echo ""
    #
    # # Package Publisher selection
    # echo -e "  ${MAGENTA}Package Publisher:${NC}"
    # echo -e "    ${GREEN}[1]${NC} package-publisher-phd (haiku) - Recommended"
    # echo -e "    ${DIM}[2]${NC} package-publisher-careful (sonnet) - Thorough"
    # echo -e "    ${YELLOW}[c]${NC} Custom agent"
    # echo ""
    # read -e -p "  Select [1]: " pub_choice || true
    # pub_choice=${pub_choice:-1}
    #
    # case "$pub_choice" in
    #     1) selected_agents+=("package-publisher-phd:haiku") ;;
    #     2) selected_agents+=("package-publisher-careful:sonnet") ;;
    #     c|C)
    #         read -e -p "  Custom agent name: " custom_name || true
    #         read -e -p "  Custom agent model [haiku]: " custom_model || true
    #         custom_model=${custom_model:-haiku}
    #         selected_agents+=("$custom_name:$custom_model")
    #         ;;
    #     *) selected_agents+=("package-publisher-phd:haiku") ;;
    # esac
    # echo ""

    # Announcement Writer selection
    echo -e "  ${YELLOW}Announcement Writer:${NC}"
    echo -e "    ${GREEN}[1]${NC} announcement-writer-phd (haiku) - Recommended"
    echo -e "    ${DIM}[2]${NC} announcement-writer-detailed (sonnet) - Comprehensive"
    echo -e "    ${YELLOW}[c]${NC} Custom agent"
    echo ""
    read -e -p "  Select [1]: " ann_choice || true
    ann_choice=${ann_choice:-1}

    case "$ann_choice" in
        1) selected_agents+=("announcement-writer-phd:haiku") ;;
        2) selected_agents+=("announcement-writer-detailed:sonnet") ;;
        c|C)
            read -e -p "  Custom agent name: " custom_name || true
            read -e -p "  Custom agent model [haiku]: " custom_model || true
            custom_model=${custom_model:-haiku}
            selected_agents+=("$custom_name:$custom_model")
            ;;
        *) selected_agents+=("announcement-writer-phd:haiku") ;;
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
            "phase": 9,
            "agents": $agents,
            "selected_at": (now | todate)
        }' > "$agents_file"

    atomic_context_artifact "$agents_file" "release-agents" "Selected release agents"
    atomic_context_decision "Release agents selected: ${#selected_agents[@]} agents" "agents"

    atomic_success "Agent Selection complete"

    return 0
}
