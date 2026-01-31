#!/bin/bash
#
# Task 008: Repository Setup
# Validates embedded agents/audits and configures task routing
#
# Since v2.0, agents and audits are embedded in ATOMIC-CLAUDE itself.
# This task verifies they're available and configures task routing.
#

task_008_repository_setup() {
    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"
    local secrets_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/secrets.json"

    # Get orchestrator directory (where ATOMIC-CLAUDE lives)
    local orchestrator_dir="${ATOMIC_ORCHESTRATOR:-$(dirname "$(dirname "$(dirname "$PHASE_DIR")")")}"

    atomic_step "Repository & Provider Setup"

    echo ""
    echo -e "${DIM}  ┌─────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${DIM}  │ ATOMIC CLAUDE includes embedded resources:                  │${NC}"
    echo -e "${DIM}  │   • Agents - Specialized AI agents per phase/domain         │${NC}"
    echo -e "${DIM}  │   • Audits - Quality audits across multiple categories      │${NC}"
    echo -e "${DIM}  └─────────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 1: VERIFY EMBEDDED AGENTS
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}  AGENTS${NC}"
    echo ""

    local agents_dir="$orchestrator_dir/agents"
    local agents_manifest="$agents_dir/agent-manifest.json"

    if [[ -f "$agents_manifest" ]] && jq -e . "$agents_manifest" &>/dev/null; then
        local total_agents=$(jq '[.phases[].agents | length] | add // 0' "$agents_manifest" 2>/dev/null || echo "0")
        local total_categories=$(jq '.phases | length' "$agents_manifest" 2>/dev/null || echo "0")
        local manifest_version=$(jq -r '.version // "unknown"' "$agents_manifest")

        echo -e "  ${GREEN}✓${NC} Agents available (v$manifest_version)"
        echo -e "    Total agents:     ${BOLD}$total_agents${NC}"
        echo -e "    Phase categories: ${BOLD}$total_categories${NC}"
    else
        echo -e "  ${YELLOW}!${NC} Agent manifest not found at: $agents_manifest"
        echo -e "    ${DIM}Using built-in defaults${NC}"
    fi
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 2: VERIFY EMBEDDED AUDITS
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}  AUDITS${NC}"
    echo ""

    local audits_dir="$orchestrator_dir/audits"
    local audits_menu="$audits_dir/AUDIT-MENU.md"

    if [[ -f "$audits_menu" ]]; then
        local audit_count=$(grep -c "^|" "$audits_menu" 2>/dev/null || echo "0")
        local category_count=$(find "$audits_dir/categories" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')

        echo -e "  ${GREEN}✓${NC} Audits available"
        echo -e "    Total audits:  ${BOLD}~$audit_count${NC}"
        echo -e "    Categories:    ${BOLD}$category_count${NC}"
    else
        echo -e "  ${YELLOW}!${NC} Audit menu not found at: $audits_menu"
        echo -e "    ${DIM}AI audits disabled${NC}"
    fi
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 3: TASK ROUTING CONFIGURATION
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}  TASK ROUTING${NC}"
    echo ""

    # Check if Ollama was configured in Task 004
    local ollama_configured="false"
    if [[ -f "$secrets_file" ]]; then
        local ollama_hosts=$(jq -r '.ollama_hosts // [] | length' "$secrets_file" 2>/dev/null || echo "0")
        if [[ "$ollama_hosts" -gt 0 ]]; then
            ollama_configured="true"
        fi
    fi

    local routing_config=""

    if [[ "$ollama_configured" == "true" ]]; then
        echo -e "  ${GREEN}✓${NC} Ollama hosts configured - hybrid routing available"
        echo ""
        echo -e "  ${DIM}Task routing determines which provider handles different task types:${NC}"
        echo ""
        echo -e "    ${CYAN}Critical${NC}   PRD generation, architecture decisions"
        echo -e "              ${DIM}→ Uses primary provider (highest quality)${NC}"
        echo ""
        echo -e "    ${CYAN}Bulk${NC}       File scanning, audit runs, code analysis"
        echo -e "              ${DIM}→ Can use Ollama (high volume, parallelizable)${NC}"
        echo ""
        echo -e "    ${CYAN}Background${NC} Indexing, validation, health checks"
        echo -e "              ${DIM}→ Can use smaller/faster models${NC}"
        echo ""

        # Default hybrid routing when Ollama is available
        routing_config='{"critical":"primary","bulk":"ollama","background":"ollama","background_model":"same"}'

        echo -e "  ${BOLD}Current Routing:${NC}"
        echo ""
        echo -e "    Critical tasks:   primary"
        echo -e "    Bulk tasks:       ollama"
        echo -e "    Background tasks: ollama"
    else
        echo -e "  ${DIM}○${NC} No Ollama hosts configured - all tasks use primary provider"
        echo -e "    ${DIM}(Configure Ollama in Task 004 for hybrid routing)${NC}"

        routing_config='{"critical":"primary","bulk":"primary","background":"primary","background_model":"same"}'
    fi
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 4: SAVE CONFIGURATION
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Build configuration
    local repos_config
    repos_config=$(cat <<EOF
{
    "agents": {
        "path": "$agents_dir",
        "embedded": true,
        "configured": $([[ -f "$agents_manifest" ]] && echo "true" || echo "false")
    },
    "audits": {
        "path": "$audits_dir",
        "embedded": true,
        "configured": $([[ -f "$audits_menu" ]] && echo "true" || echo "false")
    }
}
EOF
)

    local providers_config
    providers_config=$(cat <<EOF
{
    "routing": $routing_config,
    "ollama_enabled": $ollama_configured,
    "configured_at": "$(date -Iseconds)"
}
EOF
)

    # Update project config
    local tmp=$(atomic_mktemp)
    jq --argjson repos "$repos_config" \
       --argjson providers "$providers_config" \
       '.repositories = $repos | .providers = $providers' \
       "$config_file" > "$tmp" && mv "$tmp" "$config_file"

    echo -e "  ${GREEN}✓${NC} Configuration saved"
    echo ""

    # Summary
    echo -e "  ${BOLD}Summary:${NC}"
    echo ""

    if [[ -f "$agents_manifest" ]]; then
        echo -e "    ${GREEN}✓${NC} Agents:  embedded ($total_agents available)"
    else
        echo -e "    ${YELLOW}○${NC} Agents:  using defaults"
    fi

    if [[ -f "$audits_menu" ]]; then
        echo -e "    ${GREEN}✓${NC} Audits:  embedded (~$audit_count available)"
    else
        echo -e "    ${YELLOW}○${NC} Audits:  disabled"
    fi

    if [[ "$ollama_configured" == "true" ]]; then
        echo -e "    ${GREEN}✓${NC} Routing: hybrid (Ollama + primary)"
    else
        echo -e "    ${DIM}○${NC} Routing: primary provider only"
    fi
    echo ""

    # Record to context
    atomic_context_decision "Repositories: agents=embedded, audits=embedded, routing=$([[ "$ollama_configured" == "true" ]] && echo "hybrid" || echo "primary")" "setup"

    atomic_success "Repository setup complete"

    return 0
}
