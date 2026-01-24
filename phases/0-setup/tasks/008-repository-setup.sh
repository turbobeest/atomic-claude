#!/bin/bash
#
# Task 008: Repository Setup
# Configure companion repositories (agents + audits) and task routing
#
# Features:
#   - Clones/links agent repository (configurable URL, supports GitHub/GitLab)
#   - Clones/links audits repository (configurable URL, supports GitHub/GitLab)
#   - Offers localhost web UI for browsing agents/audits
#   - Configures task routing (which provider handles which task types)
#   - Supports enterprise repository mirroring
#   - Records configuration to project-config.json
#
# Note: Ollama server credentials are collected in Task 004 (API Keys).
#       This task configures how tasks are ROUTED to those servers.
#

task_008_repository_setup() {
    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"
    local secrets_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/secrets.json"
    local setup_file="$ATOMIC_ROOT/initialization/setup.md"

    # Project-local default paths (portable)
    local default_repo_base="$ATOMIC_ROOT/repos"

    atomic_step "Repository & Provider Setup"

    echo ""
    echo -e "${DIM}  ┌─────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${DIM}  │ ATOMIC CLAUDE uses companion repositories for:              │${NC}"
    echo -e "${DIM}  │   • Agents - Specialized AI agents per phase/domain         │${NC}"
    echo -e "${DIM}  │   • Audits - Quality audits across multiple categories      │${NC}"
    echo -e "${DIM}  │                                                             │${NC}"
    echo -e "${DIM}  │ Both repos include local web UIs for browsing and editing.  │${NC}"
    echo -e "${DIM}  └─────────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 1: REPOSITORY SOURCE CONFIGURATION
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}  REPOSITORY SOURCE${NC}"
    echo ""

    # Check setup.md for custom repo URLs, otherwise prompt
    local agents_url=""
    local audits_url=""

    if [[ -f "$setup_file" ]]; then
        agents_url=$(_008_parse_repo_url "$setup_file" "agents")
        audits_url=$(_008_parse_repo_url "$setup_file" "audits")
    fi

    # Default URLs if not configured
    local default_agents_url="https://github.com/turbobeest/agents"
    local default_audits_url="https://github.com/turbobeest/audits"

    if [[ -z "$agents_url" || -z "$audits_url" ]]; then
        echo -e "  ${DIM}Where should repositories be cloned from?${NC}"
        echo ""
        echo -e "  ${CYAN}1.${NC} Default (github.com/turbobeest)"
        echo -e "  ${CYAN}2.${NC} Custom URLs (enterprise GitHub/GitLab)"
        echo -e "  ${CYAN}3.${NC} Skip repositories (use built-in defaults only)"
        echo ""

        read -p "  Choice [1]: " source_choice
        source_choice=${source_choice:-1}

        case "$source_choice" in
            1)
                agents_url="$default_agents_url"
                audits_url="$default_audits_url"
                ;;
            2)
                echo ""
                echo -e "  ${DIM}Enter full repository URLs (GitHub or GitLab):${NC}"
                read -p "  Agents repo URL: " agents_url
                read -p "  Audits repo URL: " audits_url

                if [[ -z "$agents_url" ]]; then
                    agents_url="$default_agents_url"
                fi
                if [[ -z "$audits_url" ]]; then
                    audits_url="$default_audits_url"
                fi
                ;;
            3)
                echo ""
                echo -e "  ${DIM}Skipping repository setup. Using built-in defaults.${NC}"
                _008_save_config "$config_file" "" "" "" "false"
                atomic_context_decision "Repositories: skipped (using built-in defaults)" "setup"
                atomic_success "Repository setup skipped"
                return 0
                ;;
        esac
    else
        echo -e "  ${GREEN}✓${NC} Repository URLs found in setup.md"
        echo -e "    Agents: ${DIM}$agents_url${NC}"
        echo -e "    Audits: ${DIM}$audits_url${NC}"
    fi
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 2: CLONE LOCATION
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}  CLONE LOCATION${NC}"
    echo ""
    echo -e "  ${DIM}Where should repositories be stored?${NC}"
    echo ""
    echo -e "  ${CYAN}1.${NC} Project-local: ${DIM}$default_repo_base${NC} (recommended)"
    echo -e "  ${CYAN}2.${NC} Home directory: ${DIM}$HOME/atomic-repos${NC}"
    echo -e "  ${CYAN}3.${NC} Custom path"
    echo ""

    read -p "  Choice [1]: " location_choice
    location_choice=${location_choice:-1}

    local repo_base=""
    case "$location_choice" in
        1) repo_base="$default_repo_base" ;;
        2) repo_base="$HOME/atomic-repos" ;;
        3)
            read -p "  Custom path: " repo_base
            repo_base="${repo_base/#\~/$HOME}"  # Expand ~
            ;;
        *) repo_base="$default_repo_base" ;;
    esac

    # Create base directory
    if [[ ! -d "$repo_base" ]]; then
        mkdir -p "$repo_base" 2>/dev/null || {
            atomic_error "Cannot create directory: $repo_base"
            atomic_error "Check permissions and try again."
            return 1
        }
    fi
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 3: AGENTS REPOSITORY
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}AGENTS REPOSITORY${NC}                                            ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local agent_repo=""
    local agent_path="$repo_base/agents"

    agent_repo=$(_008_setup_repository "agents" "agent-manifest.json" "$agent_path" "$agents_url")

    if [[ -n "$agent_repo" && "$agent_repo" != "SKIP" && "$agent_repo" != "FAIL" ]]; then
        # Dynamically count agents from manifest
        local agent_manifest="$agent_repo/agent-manifest.json"
        if [[ -f "$agent_manifest" ]] && jq -e . "$agent_manifest" &>/dev/null; then
            local total_agents=$(jq '[.phases[].agents | length] | add // 0' "$agent_manifest" 2>/dev/null || echo "0")
            local total_categories=$(jq '.phases | length' "$agent_manifest" 2>/dev/null || echo "0")
            local manifest_version=$(jq -r '.version // "unknown"' "$agent_manifest")

            echo -e "  ${GREEN}✓${NC} Valid agent manifest (v$manifest_version)"
            echo -e "    Total agents:    ${BOLD}$total_agents${NC}"
            echo -e "    Phase categories: ${BOLD}$total_categories${NC}"
            echo ""

            # Offer to launch web UI
            _008_offer_web_ui "$agent_repo" "agents"
        else
            atomic_warn "agent-manifest.json is missing or invalid"
        fi
    else
        echo -e "  ${YELLOW}!${NC} Agents repository not configured - using built-in defaults"
        agent_repo=""
    fi
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 4: AUDITS REPOSITORY
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}AUDITS REPOSITORY${NC}                                            ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local audits_repo=""
    local audits_path="$repo_base/audits"

    audits_repo=$(_008_setup_repository "audits" "AUDIT-MENU.md" "$audits_path" "$audits_url")

    if [[ -n "$audits_repo" && "$audits_repo" != "SKIP" && "$audits_repo" != "FAIL" ]]; then
        local audits_menu="$audits_repo/AUDIT-MENU.md"
        if [[ -f "$audits_menu" ]]; then
            # Dynamically count audits
            local audit_count=$(grep -c "^|" "$audits_menu" 2>/dev/null || echo "0")
            local category_count=$(find "$audits_repo/categories" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')

            echo -e "  ${GREEN}✓${NC} Valid audits repository"
            echo -e "    Total audits:    ${BOLD}~$audit_count${NC}"
            echo -e "    Categories:      ${BOLD}$category_count${NC}"
            echo ""

            # Offer to launch web UI
            _008_offer_web_ui "$audits_repo" "audits"
        else
            atomic_warn "AUDIT-MENU.md is missing"
        fi
    else
        echo -e "  ${YELLOW}!${NC} Audits repository not configured - AI audits disabled"
        audits_repo=""
    fi
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 5: TASK ROUTING CONFIGURATION
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}TASK ROUTING${NC}                                                  ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Check if Ollama was configured in Task 004
    local ollama_configured="false"
    if [[ -f "$secrets_file" ]]; then
        local ollama_hosts=$(jq -r '.ollama_hosts // [] | length' "$secrets_file" 2>/dev/null || echo "0")
        if [[ "$ollama_hosts" -gt 0 ]]; then
            ollama_configured="true"
        fi
    fi

    echo -e "  ${DIM}Task routing determines which provider handles different task types.${NC}"
    echo -e "  ${DIM}Ollama servers were configured in Task 004 (API Keys).${NC}"
    echo ""

    if [[ "$ollama_configured" == "true" ]]; then
        echo -e "  ${GREEN}✓${NC} Ollama hosts configured - hybrid routing available"
        echo ""
        echo -e "  ${BOLD}Task Types:${NC}"
        echo ""
        echo -e "    ${CYAN}Critical${NC}   PRD generation, architecture decisions, approvals"
        echo -e "              ${DIM}Requires highest quality - use primary provider${NC}"
        echo ""
        echo -e "    ${CYAN}Bulk${NC}       File scanning, audit runs, code analysis"
        echo -e "              ${DIM}High volume, parallelizable - good for Ollama${NC}"
        echo ""
        echo -e "    ${CYAN}Background${NC} Indexing, validation, health checks"
        echo -e "              ${DIM}Lower priority, can use smaller models${NC}"
        echo ""

        local routing_config=$(_008_configure_routing "$setup_file" "true")

        echo -e "  ${BOLD}Current Routing:${NC}"
        echo ""
        echo -e "    Critical tasks:   $(echo "$routing_config" | jq -r '.critical')"
        echo -e "    Bulk tasks:       $(echo "$routing_config" | jq -r '.bulk')"
        echo -e "    Background tasks: $(echo "$routing_config" | jq -r '.background')"
        echo ""
    else
        echo -e "  ${DIM}○${NC} No Ollama hosts configured - all tasks use primary provider"
        echo -e "    ${DIM}(Configure Ollama in Task 004 for hybrid routing)${NC}"
        echo ""

        local routing_config='{"critical":"primary","bulk":"primary","background":"primary","background_model":"same"}'
    fi

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 6: SAVE CONFIGURATION
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    _008_save_config "$config_file" "$agent_repo" "$audits_repo" "$routing_config" "$ollama_configured"

    echo -e "  ${GREEN}✓${NC} Repository and routing configuration saved"
    echo ""

    # Summary
    echo -e "  ${BOLD}Configuration Summary:${NC}"
    echo ""

    if [[ -n "$agent_repo" ]]; then
        echo -e "    ${GREEN}✓${NC} Agents:  $agent_repo"
    else
        echo -e "    ${YELLOW}○${NC} Agents:  built-in defaults"
    fi

    if [[ -n "$audits_repo" ]]; then
        echo -e "    ${GREEN}✓${NC} Audits:  $audits_repo"
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
    atomic_context_decision "Repositories: agents=$([[ -n "$agent_repo" ]] && echo "configured" || echo "defaults"), audits=$([[ -n "$audits_repo" ]] && echo "configured" || echo "disabled"), routing=$([[ "$ollama_configured" == "true" ]] && echo "hybrid" || echo "primary")" "setup"

    atomic_success "Repository setup complete"

    return 0
}

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

# Parse repository URL from setup.md
_008_parse_repo_url() {
    local setup_file="$1"
    local repo_type="$2"  # "agents" or "audits"

    local section_name=""
    case "$repo_type" in
        agents) section_name="Agents Repository URL" ;;
        audits) section_name="Audits Repository URL" ;;
    esac

    if [[ -f "$setup_file" ]]; then
        local url=$(grep -A1 "## $section_name" "$setup_file" 2>/dev/null | tail -1 | tr -d '[:space:]')
        if [[ "$url" =~ ^https?:// ]]; then
            echo "$url"
            return 0
        fi
    fi

    echo ""
}

# Setup a single repository (agents or audits)
# Returns: repository path, "SKIP", or "FAIL"
_008_setup_repository() {
    local repo_name="$1"          # "agents" or "audits"
    local manifest_file="$2"      # File to check for validity
    local target_path="$3"        # Where to clone
    local repo_url="$4"           # Git URL

    # Check if already exists at target path
    if [[ -f "$target_path/$manifest_file" ]]; then
        echo -e "  ${GREEN}✓${NC} Found existing repository: $target_path"
        echo "$target_path"
        return 0
    fi

    # Check common alternative locations
    local search_paths=(
        "$HOME/$repo_name"
        "$HOME/.$repo_name"
        "$ATOMIC_ROOT/../$repo_name"
    )

    for path in "${search_paths[@]}"; do
        if [[ -f "$path/$manifest_file" ]]; then
            echo -e "  ${GREEN}✓${NC} Found existing repository: $path"
            read -p "  Use this location? [Y/n]: " use_existing
            if [[ ! "$use_existing" =~ ^[Nn] ]]; then
                echo "$path"
                return 0
            fi
        fi
    done

    # Repository not found - offer options
    echo -e "  ${YELLOW}!${NC} No $repo_name repository found."
    echo ""
    echo -e "  ${DIM}Source: $repo_url${NC}"
    echo ""
    echo -e "    ${GREEN}[1]${NC} Clone now ${DIM}(recommended)${NC}"
    echo -e "    ${GREEN}[2]${NC} Specify existing path"
    echo -e "    ${GREEN}[3]${NC} Skip"
    echo ""

    read -p "  Choice [1]: " setup_choice
    setup_choice=${setup_choice:-1}

    case "$setup_choice" in
        1)
            # Clone from configured URL
            echo ""

            # Create parent directory if needed
            local parent_dir=$(dirname "$target_path")
            if [[ ! -d "$parent_dir" ]]; then
                mkdir -p "$parent_dir" 2>/dev/null || {
                    atomic_error "Cannot create directory: $parent_dir"
                    echo "FAIL"
                    return 1
                }
            fi

            echo -e "  ${DIM}Cloning $repo_url...${NC}"
            echo ""

            if git clone --depth 1 "$repo_url" "$target_path" 2>&1; then
                echo ""
                echo -e "  ${GREEN}✓${NC} Successfully cloned $repo_name repository"
                echo "$target_path"
                return 0
            else
                echo ""
                atomic_error "Clone failed. Check URL and network connection."
                atomic_error "URL: $repo_url"
                echo "FAIL"
                return 1
            fi
            ;;

        2)
            # User specifies path
            echo ""
            read -p "  Path to $repo_name repository: " custom_path
            custom_path="${custom_path/#\~/$HOME}"

            if [[ -f "$custom_path/$manifest_file" ]]; then
                echo -e "  ${GREEN}✓${NC} Found $manifest_file"
                echo "$custom_path"
                return 0
            else
                atomic_error "No $manifest_file found at: $custom_path"
                echo "FAIL"
                return 1
            fi
            ;;

        3)
            # Skip
            echo ""
            echo -e "  ${DIM}Skipping $repo_name repository.${NC}"
            echo "SKIP"
            return 0
            ;;
    esac
}

# Offer to launch the local web UI for browsing agents/audits
_008_offer_web_ui() {
    local repo_path="$1"
    local repo_type="$2"  # "agents" or "audits"

    # Check if web UI exists (index.html or serve.sh)
    if [[ ! -f "$repo_path/index.html" && ! -f "$repo_path/serve.sh" ]]; then
        return 0  # No web UI available
    fi

    echo -e "  ${DIM}This repository includes a local web UI for browsing.${NC}"
    read -p "  Launch web UI now? [y/N]: " launch_ui

    if [[ ! "$launch_ui" =~ ^[Yy] ]]; then
        return 0
    fi

    # Find an available port
    local port=$(_008_find_available_port 8080)
    if [[ -z "$port" ]]; then
        atomic_warn "Could not find an available port for web server"
        return 1
    fi

    echo -e "  ${DIM}Starting web server on port $port...${NC}"

    local server_pid=""
    local server_started=false

    # Try custom serve.sh first
    if [[ -f "$repo_path/serve.sh" ]]; then
        bash "$repo_path/serve.sh" "$port" &>/dev/null &
        server_pid=$!
        sleep 1
        if kill -0 "$server_pid" 2>/dev/null; then
            server_started=true
        fi
    fi

    # Try npx serve (Node.js - already required dependency)
    if [[ "$server_started" == "false" ]] && command -v npx &>/dev/null; then
        npx --yes serve -l "$port" "$repo_path" &>/dev/null &
        server_pid=$!
        sleep 2  # npx needs a moment to download if not cached
        if kill -0 "$server_pid" 2>/dev/null; then
            server_started=true
        fi
    fi

    # Fallback to Python http.server
    if [[ "$server_started" == "false" ]] && command -v python3 &>/dev/null; then
        (cd "$repo_path" && python3 -m http.server "$port" &>/dev/null) &
        server_pid=$!
        sleep 1
        if kill -0 "$server_pid" 2>/dev/null; then
            server_started=true
        fi
    fi

    # Last resort: try 'python' (some systems)
    if [[ "$server_started" == "false" ]] && command -v python &>/dev/null; then
        (cd "$repo_path" && python -m http.server "$port" &>/dev/null) &
        server_pid=$!
        sleep 1
        if kill -0 "$server_pid" 2>/dev/null; then
            server_started=true
        fi
    fi

    if [[ "$server_started" == "false" ]]; then
        atomic_warn "Could not start web server. Install Node.js or Python 3."
        return 1
    fi

    # Track PID for later cleanup
    _008_track_server_pid "$server_pid" "$repo_type" "$port"

    local url="http://localhost:$port"
    echo -e "  ${GREEN}✓${NC} Web UI available at: ${BOLD}$url${NC}"
    echo -e "  ${DIM}Use this to browse and select ${repo_type} for your project.${NC}"
    echo -e "  ${DIM}Edits can generate GitHub/GitLab issues for upstream improvements.${NC}"

    # Offer to open browser
    read -p "  Open in browser? [Y/n]: " open_browser
    if [[ ! "$open_browser" =~ ^[Nn] ]]; then
        _008_open_browser "$url"
    fi
}

# Find an available port starting from the given port
_008_find_available_port() {
    local start_port="${1:-8080}"
    local max_attempts=10

    for ((i=0; i<max_attempts; i++)); do
        local port=$((start_port + i))

        # Check if port is in use
        if ! _008_is_port_in_use "$port"; then
            echo "$port"
            return 0
        fi
    done

    # No available port found
    echo ""
    return 1
}

# Check if a port is in use
_008_is_port_in_use() {
    local port="$1"

    # Try multiple methods for cross-platform compatibility
    if command -v lsof &>/dev/null; then
        lsof -i :"$port" &>/dev/null && return 0
    elif command -v ss &>/dev/null; then
        ss -tuln | grep -q ":$port " && return 0
    elif command -v netstat &>/dev/null; then
        netstat -tuln 2>/dev/null | grep -q ":$port " && return 0
    else
        # If no tools available, try to bind (bash /dev/tcp)
        (echo >/dev/tcp/localhost/"$port") 2>/dev/null && return 0
    fi

    return 1
}

# Track server PID for cleanup
_008_track_server_pid() {
    local pid="$1"
    local repo_type="$2"
    local port="$3"

    local pid_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/web-servers.json"

    # Create or update PID tracking file
    if [[ -f "$pid_file" ]]; then
        local tmp=$(atomic_mktemp)
        jq --arg type "$repo_type" --argjson pid "$pid" --argjson port "$port" \
            '.[$type] = {"pid": $pid, "port": $port, "started_at": (now | todate)}' \
            "$pid_file" > "$tmp" && mv "$tmp" "$pid_file"
    else
        cat > "$pid_file" <<EOF
{
    "$repo_type": {
        "pid": $pid,
        "port": $port,
        "started_at": "$(date -Iseconds)"
    }
}
EOF
    fi

    echo -e "  ${DIM}Server PID $pid tracked for cleanup${NC}"
}

# Open URL in default browser (cross-platform)
_008_open_browser() {
    local url="$1"

    case "$(uname -s)" in
        Darwin*)
            # macOS
            open "$url" 2>/dev/null && return 0
            ;;
        Linux*)
            # Linux - try multiple openers
            if command -v xdg-open &>/dev/null; then
                xdg-open "$url" 2>/dev/null && return 0
            elif command -v gnome-open &>/dev/null; then
                gnome-open "$url" 2>/dev/null && return 0
            elif command -v kde-open &>/dev/null; then
                kde-open "$url" 2>/dev/null && return 0
            fi
            ;;
        MINGW*|CYGWIN*|MSYS*)
            # Windows
            start "$url" 2>/dev/null && return 0
            cmd.exe /c start "$url" 2>/dev/null && return 0
            ;;
    esac

    # Fallback: just print the URL
    echo -e "  ${DIM}Could not auto-open browser. Please visit: $url${NC}"
    return 1
}

# Stop tracked web servers (can be called during cleanup)
_008_stop_web_servers() {
    local pid_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/web-servers.json"

    if [[ ! -f "$pid_file" ]]; then
        return 0
    fi

    echo -e "  ${DIM}Stopping web servers...${NC}"

    for repo_type in $(jq -r 'keys[]' "$pid_file" 2>/dev/null); do
        local pid=$(jq -r ".\"$repo_type\".pid // empty" "$pid_file")
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            echo -e "  ${GREEN}✓${NC} Stopped $repo_type server (PID $pid)"
        fi
    done

    rm -f "$pid_file"
}

# Configure task routing
_008_configure_routing() {
    local setup_file="$1"
    local ollama_available="$2"

    local critical="primary"
    local bulk="primary"
    local background="primary"
    local background_model="same"

    # If Ollama is available, check for routing config in setup.md
    if [[ "$ollama_available" == "true" && -f "$setup_file" ]]; then
        # Critical Tasks Provider
        local critical_line=$(grep -A1 "## Critical Tasks Provider" "$setup_file" 2>/dev/null | tail -1 | tr -d '[:space:]')
        if [[ "$critical_line" == "ollama" ]]; then
            critical="ollama"
        elif [[ -n "$critical_line" && "$critical_line" != "default" && "$critical_line" != "primary" ]]; then
            critical="$critical_line"
        fi

        # Bulk Tasks Provider (default to ollama if available)
        local bulk_line=$(grep -A1 "## Bulk Tasks Provider" "$setup_file" 2>/dev/null | tail -1 | tr -d '[:space:]')
        if [[ "$bulk_line" == "ollama" || "$bulk_line" == "default" ]]; then
            bulk="ollama"
        elif [[ -n "$bulk_line" && "$bulk_line" != "primary" ]]; then
            bulk="$bulk_line"
        fi

        # Background Tasks Provider (default to ollama if available)
        local bg_line=$(grep -A1 "## Background Tasks Provider" "$setup_file" 2>/dev/null | tail -1 | tr -d '[:space:]')
        if [[ "$bg_line" == "ollama" || "$bg_line" == "default" ]]; then
            background="ollama"
        elif [[ -n "$bg_line" && "$bg_line" != "primary" ]]; then
            background="$bg_line"
        fi

        # Background Model Override
        local model_line=$(grep -A1 "## Background Model Override" "$setup_file" 2>/dev/null | tail -1 | tr -d '[:space:]')
        if [[ -n "$model_line" && "$model_line" != "default" && "$model_line" != "same" ]]; then
            background_model="$model_line"
        elif [[ "$model_line" == "default" ]]; then
            background_model="qwen3:8b"
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

# Save all configuration to project-config.json
_008_save_config() {
    local config_file="$1"
    local agent_repo="$2"
    local audits_repo="$3"
    local routing_config="$4"
    local ollama_configured="$5"

    # Build repositories config
    local repos_config
    repos_config=$(cat <<EOF
{
    "agents": {
        "repository": $(printf '%s' "$agent_repo" | jq -Rs .),
        "configured": $([[ -n "$agent_repo" ]] && echo "true" || echo "false")
    },
    "audits": {
        "repository": $(printf '%s' "$audits_repo" | jq -Rs .),
        "configured": $([[ -n "$audits_repo" ]] && echo "true" || echo "false")
    }
}
EOF
)

    # Build providers config
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
}
