#!/bin/bash
#
# Task 007: Repository Setup
# Configure and validate companion repositories (agents + audits) and Ollama servers
#
# Features:
#   - Detects/clones agent repository (github.com/turbobeest/agents)
#   - Detects/clones audits repository (github.com/turbobeest/audits)
#   - Parses Ollama server configuration from setup.md
#   - Validates Ollama server connectivity
#   - Stores all configuration in project-config.json
#

task_007_repository_setup() {
    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"
    local setup_file="$ATOMIC_ROOT/initialization/setup.md"
    local default_repo_base="/mnt/walnut-drive/dev"

    atomic_step "Repository & Provider Setup"

    echo ""
    echo -e "${DIM}  ┌─────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${DIM}  │ ATOMIC CLAUDE uses companion repositories for:              │${NC}"
    echo -e "${DIM}  │   • Agents - 162+ specialized AI agents per phase/domain    │${NC}"
    echo -e "${DIM}  │   • Audits - 2,200+ quality audits across 43 categories     │${NC}"
    echo -e "${DIM}  │                                                             │${NC}"
    echo -e "${DIM}  │ For hybrid operation, Ollama servers can handle bulk tasks. │${NC}"
    echo -e "${DIM}  └─────────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 1: AGENTS REPOSITORY
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}AGENTS REPOSITORY${NC}                                            ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC} ${DIM}github.com/turbobeest/agents - 162+ specialized agents${NC}       ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local agent_repo=""
    local agent_manifest=""
    local agent_result=$(_007_setup_repository "agents" "agent-manifest.json" "$default_repo_base/agents")

    if [[ "$agent_result" != "SKIP" && "$agent_result" != "FAIL" ]]; then
        agent_repo="$agent_result"
        agent_manifest="$agent_repo/agent-manifest.json"

        # Validate and display agent stats
        if jq -e . "$agent_manifest" &>/dev/null; then
            local total_agents=$(jq -r '.metadata.totalAgents // 0' "$agent_manifest")
            local total_categories=$(jq -r '.metadata.totalCategories // 0' "$agent_manifest")
            local manifest_version=$(jq -r '.version // "unknown"' "$agent_manifest")

            echo -e "  ${GREEN}✓${NC} Valid agent manifest (v$manifest_version)"
            echo -e "    Total agents:    ${BOLD}$total_agents${NC}"
            echo -e "    Categories:      ${BOLD}$total_categories${NC}"
        fi
    else
        echo -e "  ${YELLOW}!${NC} Agents repository not configured - using built-in defaults"
    fi
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 2: AUDITS REPOSITORY
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}AUDITS REPOSITORY${NC}                                            ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC} ${DIM}github.com/turbobeest/audits - 2,200+ quality audits${NC}         ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local audits_repo=""
    local audits_menu=""
    local audits_result=$(_007_setup_repository "audits" "AUDIT-MENU.md" "$default_repo_base/audits")

    if [[ "$audits_result" != "SKIP" && "$audits_result" != "FAIL" ]]; then
        audits_repo="$audits_result"
        audits_menu="$audits_repo/AUDIT-MENU.md"

        # Display audit stats
        if [[ -f "$audits_menu" ]]; then
            local audit_count=$(grep -c "^|" "$audits_menu" 2>/dev/null || echo "0")
            local category_count=$(find "$audits_repo/categories" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)

            echo -e "  ${GREEN}✓${NC} Valid audits repository"
            echo -e "    Menu entries:    ${BOLD}~$audit_count${NC}"
            echo -e "    Categories:      ${BOLD}$category_count${NC}"
        fi
    else
        echo -e "  ${YELLOW}!${NC} Audits repository not configured - AI audits disabled"
    fi
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 3: OLLAMA SERVERS
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}OLLAMA SERVERS${NC}                                                ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC} ${DIM}Local LLM servers for bulk tasks (cost optimization)${NC}         ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local ollama_enabled="false"
    local ollama_servers=()
    local ollama_config=""

    # Parse setup.md for Ollama configuration
    if [[ -f "$setup_file" ]]; then
        ollama_config=$(_007_parse_ollama_config "$setup_file")
        ollama_enabled=$(echo "$ollama_config" | jq -r '.enabled // false')

        if [[ "$ollama_enabled" == "true" ]]; then
            echo -e "  ${DIM}Ollama integration enabled in setup.md${NC}"
            echo ""

            # Parse and validate servers
            local servers_json=$(echo "$ollama_config" | jq -c '.servers // []')
            local server_count=$(echo "$servers_json" | jq 'length')

            if [[ "$server_count" -gt 0 ]]; then
                echo -e "  ${BOLD}Configured Servers:${NC}"
                echo ""

                local healthy_count=0

                echo "$servers_json" | jq -c '.[]' | while read -r server; do
                    local name=$(echo "$server" | jq -r '.name')
                    local host=$(echo "$server" | jq -r '.host')
                    local model=$(echo "$server" | jq -r '.model')
                    local ctx=$(echo "$server" | jq -r '.max_context')
                    local desc=$(echo "$server" | jq -r '.description')

                    # Health check
                    local status="unknown"
                    if _007_check_ollama_health "$host"; then
                        status="healthy"
                        ((healthy_count++)) || true
                        echo -e "    ${GREEN}●${NC} ${BOLD}$name${NC} - $host"
                    else
                        status="unreachable"
                        echo -e "    ${RED}○${NC} ${BOLD}$name${NC} - $host ${DIM}(unreachable)${NC}"
                    fi
                    echo -e "      Model: $model | Context: $ctx | $desc"
                done

                echo ""
                echo -e "  ${DIM}Healthy servers: $healthy_count of $server_count${NC}"
            else
                echo -e "  ${YELLOW}!${NC} No Ollama servers configured in setup.md"
                echo -e "    ${DIM}Add servers in 'Ollama Servers' section${NC}"
            fi
        else
            echo -e "  ${DIM}Ollama integration disabled in setup.md${NC}"
            echo -e "  ${DIM}Set 'Enable Ollama' to 'true' to use local models${NC}"
        fi
    else
        echo -e "  ${YELLOW}!${NC} setup.md not found - skipping Ollama configuration"
    fi
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 4: TASK ROUTING
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}TASK ROUTING CONFIGURATION${NC}                                   ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local routing_config=$(_007_parse_routing_config "$setup_file" "$ollama_enabled")

    echo -e "  ${BOLD}Provider Assignment:${NC}"
    echo ""
    echo -e "    Critical tasks:   $(echo "$routing_config" | jq -r '.critical // "primary"') ${DIM}(PRD, architecture, approvals)${NC}"
    echo -e "    Bulk tasks:       $(echo "$routing_config" | jq -r '.bulk // "primary"') ${DIM}(audits, scanning, analysis)${NC}"
    echo -e "    Background tasks: $(echo "$routing_config" | jq -r '.background // "primary"') ${DIM}(indexing, validation)${NC}"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 5: SAVE CONFIGURATION
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Build repositories config
    local repos_config=$(cat <<EOF
{
    "agents": {
        "repository": $(echo "$agent_repo" | jq -Rs .),
        "manifest": $(echo "$agent_manifest" | jq -Rs .),
        "configured": $([ -n "$agent_repo" ] && echo "true" || echo "false")
    },
    "audits": {
        "repository": $(echo "$audits_repo" | jq -Rs .),
        "menu": $(echo "$audits_menu" | jq -Rs .),
        "configured": $([ -n "$audits_repo" ] && echo "true" || echo "false")
    }
}
EOF
)

    # Build providers config
    local providers_config=$(cat <<EOF
{
    "ollama": $ollama_config,
    "routing": $routing_config,
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

    echo -e "  ${GREEN}✓${NC} Repository and provider configuration saved"
    echo ""

    # Summary
    echo -e "  ${BOLD}Configuration Summary:${NC}"
    echo ""

    if [[ -n "$agent_repo" ]]; then
        echo -e "    ${GREEN}✓${NC} Agents:   $agent_repo"
    else
        echo -e "    ${YELLOW}○${NC} Agents:   built-in defaults"
    fi

    if [[ -n "$audits_repo" ]]; then
        echo -e "    ${GREEN}✓${NC} Audits:   $audits_repo"
    else
        echo -e "    ${YELLOW}○${NC} Audits:   disabled"
    fi

    if [[ "$ollama_enabled" == "true" ]]; then
        echo -e "    ${GREEN}✓${NC} Ollama:   enabled (hybrid routing)"
    else
        echo -e "    ${DIM}○${NC} Ollama:   disabled (API only)"
    fi
    echo ""

    # Record to context
    atomic_context_decision "Repositories configured: agents=$([[ -n "$agent_repo" ]] && echo "yes" || echo "no"), audits=$([[ -n "$audits_repo" ]] && echo "yes" || echo "no"), ollama=$ollama_enabled" "setup"

    atomic_success "Repository setup complete"

    return 0
}

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

# Setup a single repository (agents or audits)
# Returns: repository path, "SKIP", or "FAIL"
_007_setup_repository() {
    local repo_name="$1"          # "agents" or "audits"
    local manifest_file="$2"      # File to check for validity
    local default_path="$3"       # Default location
    local github_url="https://github.com/turbobeest/$repo_name"

    local repo_path=""

    # Check common locations
    local search_paths=(
        "$default_path"
        "$HOME/$repo_name"
        "$HOME/.$repo_name"
        "$ATOMIC_ROOT/$repo_name"
        "$ATOMIC_ROOT/../$repo_name"
    )

    for path in "${search_paths[@]}"; do
        if [[ -f "$path/$manifest_file" ]]; then
            repo_path="$path"
            echo -e "  ${GREEN}✓${NC} Found existing repository: $repo_path"
            echo "$repo_path"
            return 0
        fi
    done

    # Repository not found - offer options
    echo -e "  ${YELLOW}!${NC} No $repo_name repository found in common locations."
    echo ""
    echo -e "  ${CYAN}How would you like to proceed?${NC}"
    echo ""
    echo -e "    ${GREEN}[1]${NC} Clone from GitHub ${DIM}(recommended)${NC}"
    echo -e "    ${GREEN}[2]${NC} Specify existing path"
    echo -e "    ${GREEN}[3]${NC} Skip - continue without $repo_name"
    echo ""

    read -p "  Choice [1]: " setup_choice
    setup_choice=${setup_choice:-1}

    case "$setup_choice" in
        1)
            # Clone from GitHub
            echo ""
            echo -e "  ${DIM}Where should we clone the repository?${NC}"
            read -p "  Path [$default_path]: " clone_path
            clone_path=${clone_path:-$default_path}

            # Create parent directory if needed
            local parent_dir=$(dirname "$clone_path")
            if [[ ! -d "$parent_dir" ]]; then
                echo -e "  ${DIM}Creating directory: $parent_dir${NC}"
                mkdir -p "$parent_dir" 2>/dev/null || {
                    echo -e "  ${RED}✗${NC} Cannot create directory. Check permissions."
                    echo "FAIL"
                    return 1
                }
            fi

            echo ""
            echo -e "  ${DIM}Cloning $github_url...${NC}"
            echo ""

            if git clone "$github_url" "$clone_path" 2>&1; then
                echo ""
                echo -e "  ${GREEN}✓${NC} Successfully cloned $repo_name repository"
                echo "$clone_path"
                return 0
            else
                echo ""
                echo -e "  ${RED}✗${NC} Clone failed. Check network/permissions."
                echo "FAIL"
                return 1
            fi
            ;;

        2)
            # User specifies path
            echo ""
            read -p "  $repo_name repository path: " custom_path

            if [[ -f "$custom_path/$manifest_file" ]]; then
                echo -e "  ${GREEN}✓${NC} Found $manifest_file"
                echo "$custom_path"
                return 0
            else
                echo -e "  ${RED}✗${NC} No $manifest_file found at: $custom_path"
                echo "FAIL"
                return 1
            fi
            ;;

        3)
            # Skip
            echo ""
            echo -e "  ${DIM}Skipping $repo_name repository setup.${NC}"
            echo "SKIP"
            return 0
            ;;
    esac
}

# Parse Ollama configuration from setup.md
_007_parse_ollama_config() {
    local setup_file="$1"
    local enabled="false"
    local servers="[]"
    local failover="true"
    local health_check="true"

    # Parse Enable Ollama
    local enable_line=$(grep -A1 "## Enable Ollama" "$setup_file" | tail -1 | tr -d '[:space:]')
    if [[ "$enable_line" == "true" ]]; then
        enabled="true"
    fi

    # Parse Ollama Servers (lines matching: name | host:port | model | context | description)
    local servers_section=false
    local servers_arr="["
    local first=true

    while IFS= read -r line; do
        # Detect section start
        if [[ "$line" =~ ^##[[:space:]]*Ollama[[:space:]]*Servers ]]; then
            servers_section=true
            continue
        fi

        # Detect next section (stop parsing)
        if [[ "$servers_section" == true && "$line" =~ ^##[[:space:]] && ! "$line" =~ "Ollama Servers" ]]; then
            servers_section=false
            continue
        fi

        # Parse server lines (name | host:port | model | context | description)
        if [[ "$servers_section" == true && "$line" =~ ^[a-zA-Z] && "$line" =~ \| ]]; then
            # Skip example lines (contain "EXAMPLES" or start with #)
            if [[ "$line" =~ ^# || "$line" =~ EXAMPLES ]]; then
                continue
            fi

            IFS='|' read -ra parts <<< "$line"
            if [[ ${#parts[@]} -ge 4 ]]; then
                local name=$(echo "${parts[0]}" | xargs)
                local host=$(echo "${parts[1]}" | xargs)
                local model=$(echo "${parts[2]}" | xargs)
                local ctx=$(echo "${parts[3]}" | xargs)
                local desc=""
                [[ ${#parts[@]} -ge 5 ]] && desc=$(echo "${parts[4]}" | xargs)

                if [[ ! $first ]]; then
                    servers_arr+=","
                fi
                first=false

                servers_arr+="{\"name\":\"$name\",\"host\":\"$host\",\"model\":\"$model\",\"max_context\":$ctx,\"description\":\"$desc\"}"
            fi
        fi
    done < "$setup_file"

    servers_arr+="]"

    # Parse failover setting
    local failover_line=$(grep -A1 "## Ollama Failover" "$setup_file" | tail -1 | tr -d '[:space:]')
    if [[ "$failover_line" == "false" ]]; then
        failover="false"
    fi

    # Parse health check setting
    local health_line=$(grep -A1 "## Ollama Health Check" "$setup_file" | tail -1 | tr -d '[:space:]')
    if [[ "$health_line" == "false" ]]; then
        health_check="false"
    fi

    # Output JSON
    cat <<EOF
{
    "enabled": $enabled,
    "servers": $servers_arr,
    "failover": $failover,
    "health_check": $health_check
}
EOF
}

# Parse task routing configuration from setup.md
_007_parse_routing_config() {
    local setup_file="$1"
    local ollama_enabled="$2"

    local critical="primary"
    local bulk="primary"
    local background="primary"
    local background_model="same"

    # If Ollama is enabled, check for routing overrides
    if [[ -f "$setup_file" ]]; then
        # Critical Tasks Provider
        local critical_line=$(grep -A1 "## Critical Tasks Provider" "$setup_file" | tail -1 | tr -d '[:space:]')
        if [[ "$critical_line" == "ollama" ]]; then
            critical="ollama"
        elif [[ "$critical_line" != "default" && "$critical_line" != "primary" && -n "$critical_line" ]]; then
            critical="$critical_line"
        fi

        # Bulk Tasks Provider
        local bulk_line=$(grep -A1 "## Bulk Tasks Provider" "$setup_file" | tail -1 | tr -d '[:space:]')
        if [[ "$bulk_line" == "ollama" ]]; then
            bulk="ollama"
        elif [[ "$bulk_line" == "default" && "$ollama_enabled" == "true" ]]; then
            bulk="ollama"
        elif [[ "$bulk_line" != "default" && "$bulk_line" != "primary" && -n "$bulk_line" ]]; then
            bulk="$bulk_line"
        fi

        # Background Tasks Provider
        local bg_line=$(grep -A1 "## Background Tasks Provider" "$setup_file" | tail -1 | tr -d '[:space:]')
        if [[ "$bg_line" == "ollama" ]]; then
            background="ollama"
        elif [[ "$bg_line" == "default" && "$ollama_enabled" == "true" ]]; then
            background="ollama"
        elif [[ "$bg_line" != "default" && "$bg_line" != "primary" && -n "$bg_line" ]]; then
            background="$bg_line"
        fi

        # Background Model Override
        local model_line=$(grep -A1 "## Background Model Override" "$setup_file" | tail -1 | tr -d '[:space:]')
        if [[ "$model_line" == "default" && "$ollama_enabled" == "true" ]]; then
            background_model="qwen3:8b"
        elif [[ "$model_line" != "default" && "$model_line" != "same" && -n "$model_line" ]]; then
            background_model="$model_line"
        fi
    fi

    cat <<EOF
{
    "critical": "$critical",
    "bulk": "$bulk",
    "background": "$background",
    "background_model": "$background_model"
}
EOF
}

# Check Ollama server health
_007_check_ollama_health() {
    local host="$1"
    local timeout=3

    # Try to reach Ollama API
    if curl -s --connect-timeout "$timeout" "http://$host/api/tags" &>/dev/null; then
        return 0
    fi
    return 1
}
