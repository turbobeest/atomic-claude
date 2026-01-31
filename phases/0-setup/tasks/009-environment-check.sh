#!/bin/bash
#
# Task 009: Environment Check
# Validate tools and assess system capabilities
#
# Features:
#   - Tool validation with version checks (synced with Task 007)
#   - API key validation (test actual connectivity)
#   - Ollama hosts validation (array support for LAN clusters)
#   - System capability assessment:
#     - CPU (cores, model, architecture)
#     - GPU (for local LLM inference)
#     - Memory (total/available RAM)
#     - Storage (local + mounted volumes)
#     - Network (LAN + WAN via Cloudflare)
#   - Cross-platform support (macOS, Linux, Windows with limitations)
#   - Retry loop on failure
#   - Records results to context
#

# Global validation state
_009_CHECKS_PASS=0
_009_CHECKS_FAIL=0
_009_CHECKS_WARN=0

task_009_environment_check() {
    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"
    local secrets_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/secrets.json"
    local report_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/env-validation.json"

    atomic_step "Environment Validation"

    # Reset counters
    _009_CHECKS_PASS=0
    _009_CHECKS_FAIL=0
    _009_CHECKS_WARN=0

    # Initialize report
    echo '{"validated_at": "'$(date -Iseconds)'", "checks": [], "capabilities": {}}' > "$report_file"

    echo ""

    # Detect OS upfront
    local os_type=$(_009_detect_os)
    echo -e "  ${DIM}Platform: $os_type${NC}"
    echo ""

    # Core tool validation (synced with Task 007)
    _009_validate_tools "$report_file"

    # API key validation
    _009_validate_api_keys "$secrets_file" "$report_file"

    # Ollama hosts validation
    _009_validate_ollama_hosts "$secrets_file" "$report_file"

    # Git configuration
    _009_validate_git "$report_file"

    # Agent repository validation
    _009_validate_agents "$config_file" "$report_file"

    # System capabilities
    _009_assess_cpu "$report_file" "$os_type"
    _009_assess_gpu "$report_file" "$os_type"
    _009_assess_memory "$report_file" "$os_type"
    _009_assess_storage "$report_file" "$os_type"
    _009_assess_network "$report_file"

    # Summary
    _009_show_summary "$report_file"

    # Record to context
    _009_record_context "$config_file" "$report_file"

    # Handle failures
    if [[ $_009_CHECKS_FAIL -gt 0 ]]; then
        echo ""
        echo -e "  ${RED}Validation failed with $_009_CHECKS_FAIL critical issues.${NC}"
        echo ""
        echo -e "  ${YELLOW}Options:${NC}"
        echo -e "    ${DIM}[r]${NC} Retry validation"
        echo -e "    ${DIM}[b]${NC} Go back to install tools"
        echo -e "    ${DIM}[c]${NC} Continue anyway (not recommended)"
        echo ""

        # Drain any buffered stdin
    while read -t 0.01 -n 1 _discard 2>/dev/null; do :; done

    while true; do
    atomic_drain_stdin
            read -e -p "  Choice [r]: " choice || true
            choice=${choice:-r}
            case "$choice" in
                r|R)
                    echo ""
                    task_009_environment_check
                    return $?
                    ;;
                b|B)
                    return 1  # Signal to go back
                    ;;
                c|C)
                    atomic_warn "Continuing with validation failures"
                    return 0
                    ;;
                *)
                    atomic_error "Invalid choice"
                    ;;
            esac
        done
    fi

    if [[ $_009_CHECKS_WARN -gt 0 ]]; then
        atomic_success "Environment validated with $_009_CHECKS_WARN warnings"
    else
        atomic_success "Environment validated - all checks passed"
    fi

    # Offer agent repository exploration (complements web UI from Task 008)
    _009_agent_exploration "$config_file"

    # ═══════════════════════════════════════════════════════════════════════════
    # MEMORY CHECKPOINT (Phase 0 Complete)
    # ═══════════════════════════════════════════════════════════════════════════

    # Build summary for memory persistence
    local project_name
    project_name=$(jq -r '.project_name // "unknown"' "$config_file" 2>/dev/null)
    local mode
    mode=$(jq -r '.mode // "guided"' "$config_file" 2>/dev/null)
    local cores
    cores=$(jq '.capabilities.cpu.cores // 0' "$report_file" 2>/dev/null || echo "0")
    local mem_gb
    mem_gb=$(jq '.capabilities.memory.total_mb // 0' "$report_file" 2>/dev/null | awk '{printf "%.0f", $1/1024}')

    local memory_summary="Phase 0 Setup complete. Project: $project_name. Mode: $mode. Environment validated: $_009_CHECKS_PASS passed, $_009_CHECKS_FAIL failed. System: ${cores} cores, ${mem_gb}GB RAM."

    # Prompt user to save to long-term memory (if enabled)
    memory_prompt_save 0 "Setup" "$memory_summary"

    # Git: commit and push phase
    atomic_git_phase_complete 0 "Setup"

    return 0
}

# Detect operating system
_009_detect_os() {
    case "$(uname -s)" in
        Darwin*)  echo "macos" ;;
        Linux*)   echo "linux" ;;
        MINGW*|CYGWIN*|MSYS*) echo "windows" ;;
        *)        echo "unknown" ;;
    esac
}

# Agent repository exploration (complements web UI from Task 008)
_009_agent_exploration() {
    local config_file="$1"
    local agent_repo=$(jq -r '.repositories.agents.repository // ""' "$config_file" 2>/dev/null)

    # Skip if no agent repo configured
    if [[ -z "$agent_repo" || "$agent_repo" == "null" || "$agent_repo" == "" ]]; then
        return 0
    fi

    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}AGENT REPOSITORY EXPLORATION${NC}                              ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${DIM}Throughout the pipeline, you'll have opportunities to${NC}"
    echo -e "  ${DIM}select which agents guide each phase.${NC}"
    echo ""
    echo -e "  Agent repository: ${BOLD}$agent_repo${NC}"
    echo ""

    # Check if web server is already running (from Task 008)
    local web_servers_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/web-servers.json"
    local web_ui_running=false
    local web_ui_port=""

    if [[ -f "$web_servers_file" ]]; then
        local agents_pid=$(jq -r '.agents.pid // empty' "$web_servers_file" 2>/dev/null)
        web_ui_port=$(jq -r '.agents.port // empty' "$web_servers_file" 2>/dev/null)
        if [[ -n "$agents_pid" ]] && kill -0 "$agents_pid" 2>/dev/null; then
            web_ui_running=true
        fi
    fi

    if [[ "$web_ui_running" == "true" ]]; then
        echo -e "  ${GREEN}✓${NC} Web UI already running at: ${BOLD}http://localhost:$web_ui_port${NC}"
        echo ""
        echo -e "  ${CYAN}Would you like to explore further?${NC}"
        echo ""
        echo -e "    ${GREEN}[open]${NC}   Open web UI in browser"
        echo -e "    ${YELLOW}[list]${NC}   Show agent categories in terminal"
        echo -e "    ${DIM}[skip]${NC}   Continue to next phase"
    else
        echo -e "  ${DIM}Web UI not running. You can explore via terminal or launch web UI.${NC}"
        echo ""
        echo -e "  ${CYAN}How would you like to explore?${NC}"
        echo ""
        echo -e "    ${GREEN}[web]${NC}    Launch web UI (recommended)"
        echo -e "    ${YELLOW}[list]${NC}   Show agent categories in terminal"
        echo -e "    ${DIM}[skip]${NC}   Continue to next phase"
    fi
    echo ""

    atomic_drain_stdin
    read -e -p "  Choice [skip]: " explore_choice || true
    explore_choice=${explore_choice:-skip}

    case "$explore_choice" in
        open)
            if [[ "$web_ui_running" == "true" ]]; then
                _009_open_browser "http://localhost:$web_ui_port"
            fi
            ;;
        web)
            # Launch web UI (reuse function from Task 008 if available, or simple fallback)
            _009_launch_web_ui "$agent_repo"
            ;;
        list)
            echo ""
            _009_list_agent_categories "$agent_repo"
            echo ""
            read -e -p "  Press Enter to continue... " _ || true
            ;;
        skip)
            echo ""
            echo -e "  ${DIM}You can explore agents anytime:${NC}"
            echo -e "    ${CYAN}cd $agent_repo && ls${NC}"
            echo ""
            ;;
    esac

    atomic_context_decision "Agent exploration offered" "agent_familiarization"
}

# Launch web UI for agent browsing
_009_launch_web_ui() {
    local repo_path="$1"

    if [[ ! -f "$repo_path/index.html" && ! -f "$repo_path/serve.sh" ]]; then
        echo -e "  ${YELLOW}!${NC} No web UI found in repository"
        echo -e "  ${DIM}Falling back to terminal exploration...${NC}"
        echo ""
        _009_list_agent_categories "$repo_path"
        return
    fi

    # Find available port
    local port=8080
    for ((i=0; i<10; i++)); do
        if ! _009_is_port_in_use "$((port + i))"; then
            port=$((port + i))
            break
        fi
    done

    echo -e "  ${DIM}Starting web server on port $port...${NC}"

    # Try npx serve first (Node.js required), then python
    local server_pid=""
    if command -v npx &>/dev/null; then
        npx --yes serve -l "$port" "$repo_path" &>/dev/null &
        server_pid=$!
        sleep 2
    elif command -v python3 &>/dev/null; then
        (cd "$repo_path" && python3 -m http.server "$port" &>/dev/null) &
        server_pid=$!
        sleep 1
    elif command -v python &>/dev/null; then
        (cd "$repo_path" && python -m http.server "$port" &>/dev/null) &
        server_pid=$!
        sleep 1
    fi

    if [[ -n "$server_pid" ]] && kill -0 "$server_pid" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Web UI available at: ${BOLD}http://localhost:$port${NC}"
        _009_open_browser "http://localhost:$port"
    else
        echo -e "  ${YELLOW}!${NC} Could not start web server"
        echo -e "  ${DIM}Showing terminal listing instead...${NC}"
        echo ""
        _009_list_agent_categories "$repo_path"
    fi
}

# Check if port is in use
_009_is_port_in_use() {
    local port="$1"
    if command -v lsof &>/dev/null; then
        lsof -i :"$port" &>/dev/null && return 0
    elif command -v ss &>/dev/null; then
        ss -tuln | grep -q ":$port " && return 0
    elif command -v netstat &>/dev/null; then
        netstat -tuln 2>/dev/null | grep -q ":$port " && return 0
    fi
    return 1
}

# Open URL in browser (cross-platform)
_009_open_browser() {
    local url="$1"
    case "$(uname -s)" in
        Darwin*)  open "$url" 2>/dev/null ;;
        Linux*)   xdg-open "$url" 2>/dev/null || gnome-open "$url" 2>/dev/null ;;
        MINGW*|CYGWIN*|MSYS*) start "$url" 2>/dev/null || cmd.exe /c start "$url" 2>/dev/null ;;
    esac
}

# List agent categories for quick overview
_009_list_agent_categories() {
    local agent_repo="$1"
    local manifest="$agent_repo/agent-manifest.json"

    echo -e "  ${BOLD}Agent Categories:${NC}"
    echo ""

    # Pipeline agents
    local pipeline_dir="$agent_repo/pipeline-agents"
    if [[ -d "$pipeline_dir" ]]; then
        echo -e "  ${CYAN}Pipeline Agents${NC} (phase-specific guidance)"
        for group_dir in "$pipeline_dir"/*/; do
            if [[ -d "$group_dir" ]]; then
                local group_name=$(basename "$group_dir")
                local group_count=$(find "$group_dir" -name "*.md" -type f 2>/dev/null | wc -l | tr -d ' ')
                echo -e "    - $group_name: $group_count agents"
            fi
        done
        echo ""
    fi

    # Expert agents
    local expert_dir="$agent_repo/expert-agents"
    if [[ -d "$expert_dir" ]]; then
        echo -e "  ${CYAN}Expert Agents${NC} (domain expertise)"
        for cat_dir in "$expert_dir"/*/; do
            if [[ -d "$cat_dir" ]]; then
                local cat_name=$(basename "$cat_dir")
                local cat_count=$(find "$cat_dir" -name "*.md" -type f 2>/dev/null | wc -l | tr -d ' ')
                echo -e "    - $cat_name: $cat_count agents"
            fi
        done
        echo ""
    fi

    # Total from manifest
    if [[ -f "$manifest" ]]; then
        local total=$(jq '[.phases[].agents | length] | add // 0' "$manifest" 2>/dev/null || echo "0")
        echo -e "  ${DIM}Total agents available: $total${NC}"
    fi
}

# Validate required tools (synced with Task 007)
_009_validate_tools() {
    local report_file="$1"

    echo -e "${CYAN}  Required Tools:${NC}"

    # git
    if command -v git &>/dev/null; then
        local ver=$(git --version 2>/dev/null | awk '{print $3}')
        echo -e "    ${GREEN}✓${NC} git ($ver)"
        _009_add_check "$report_file" "git" "pass" "critical" "$ver"
        ((_009_CHECKS_PASS++))
    else
        echo -e "    ${RED}✗${NC} git - NOT FOUND"
        _009_add_check "$report_file" "git" "fail" "critical" ""
        ((_009_CHECKS_FAIL++))
    fi

    # jq
    if command -v jq &>/dev/null; then
        local ver=$(jq --version 2>/dev/null | sed 's/jq-//')
        echo -e "    ${GREEN}✓${NC} jq ($ver)"
        _009_add_check "$report_file" "jq" "pass" "critical" "$ver"
        ((_009_CHECKS_PASS++))
    else
        echo -e "    ${RED}✗${NC} jq - NOT FOUND"
        _009_add_check "$report_file" "jq" "fail" "critical" ""
        ((_009_CHECKS_FAIL++))
    fi

    # node (with version check)
    if command -v node &>/dev/null; then
        local ver=$(node --version 2>/dev/null | sed 's/v//')
        local major=$(echo "$ver" | cut -d. -f1)
        if [[ "$major" -ge 18 ]]; then
            echo -e "    ${GREEN}✓${NC} node (v$ver)"
            _009_add_check "$report_file" "node" "pass" "critical" "$ver"
            ((_009_CHECKS_PASS++))
        else
            echo -e "    ${YELLOW}!${NC} node (v$ver) - v18+ required"
            _009_add_check "$report_file" "node" "warn" "critical" "$ver"
            ((_009_CHECKS_WARN++))
        fi
    else
        echo -e "    ${RED}✗${NC} node - NOT FOUND"
        _009_add_check "$report_file" "node" "fail" "critical" ""
        ((_009_CHECKS_FAIL++))
    fi

    # claude CLI
    if command -v claude &>/dev/null; then
        local ver=$(claude --version 2>/dev/null | head -1 | awk '{print $NF}' || echo "installed")
        echo -e "    ${GREEN}✓${NC} claude ($ver)"
        _009_add_check "$report_file" "claude" "pass" "critical" "$ver"
        ((_009_CHECKS_PASS++))
    else
        echo -e "    ${RED}✗${NC} claude CLI - NOT FOUND"
        echo -e "      ${DIM}npm install -g @anthropic-ai/claude-code${NC}"
        _009_add_check "$report_file" "claude" "fail" "critical" ""
        ((_009_CHECKS_FAIL++))
    fi

    # task-master-ai (synced with Task 007 - now required)
    if command -v task-master &>/dev/null; then
        echo -e "    ${GREEN}✓${NC} task-master-ai"
        _009_add_check "$report_file" "task-master" "pass" "critical" ""
        ((_009_CHECKS_PASS++))
    else
        echo -e "    ${RED}✗${NC} task-master-ai - NOT FOUND"
        echo -e "      ${DIM}npm install -g task-master-ai${NC}"
        _009_add_check "$report_file" "task-master" "fail" "critical" ""
        ((_009_CHECKS_FAIL++))
    fi

    echo ""

    # Recommended tools
    echo -e "${CYAN}  Recommended Tools:${NC}"

    for tool in gh docker curl; do
        if command -v $tool &>/dev/null; then
            local ver=$($tool --version 2>/dev/null | head -1 | grep -oE '[0-9]+\.[0-9]+\.?[0-9]*' | head -1 || echo "")
            echo -e "    ${GREEN}✓${NC} $tool${ver:+ ($ver)}"
            _009_add_check "$report_file" "$tool" "pass" "recommended" "$ver"
            ((_009_CHECKS_PASS++))
        else
            echo -e "    ${DIM}○${NC} $tool (not installed)"
            _009_add_check "$report_file" "$tool" "missing" "recommended" ""
        fi
    done

    echo ""
}

# Validate API keys
_009_validate_api_keys() {
    local secrets_file="$1"
    local report_file="$2"

    [[ ! -f "$secrets_file" ]] && return

    echo -e "${CYAN}  API Credentials:${NC}"

    # Check Claude Max login
    local max_enabled=$(jq -r '.max_enabled // false' "$secrets_file" 2>/dev/null)
    if [[ "$max_enabled" == "true" ]]; then
        echo -e "    ${GREEN}✓${NC} Claude Max (subscription login)"
        _009_add_check "$report_file" "claude_max" "pass" "optional" ""
        ((_009_CHECKS_PASS++))
    fi

    # Check Anthropic API key
    local anthropic_key=$(jq -r '.anthropic_api_key // ""' "$secrets_file" 2>/dev/null)
    if [[ -n "$anthropic_key" && "$anthropic_key" != "null" ]]; then
        echo -e "    ${DIM}Testing Anthropic API...${NC}"
        if _009_test_anthropic_api "$anthropic_key"; then
            echo -e "    ${GREEN}✓${NC} Anthropic API key valid"
            _009_add_check "$report_file" "anthropic_api" "pass" "optional" ""
            ((_009_CHECKS_PASS++))
        else
            echo -e "    ${RED}✗${NC} Anthropic API key invalid or network error"
            _009_add_check "$report_file" "anthropic_api" "fail" "optional" ""
            ((_009_CHECKS_WARN++))
        fi
    fi

    # Check AWS Bedrock configuration
    local aws_region=$(jq -r '.aws_region // ""' "$secrets_file" 2>/dev/null)
    if [[ -n "$aws_region" && "$aws_region" != "null" ]]; then
        local aws_profile=$(jq -r '.aws_profile // "default"' "$secrets_file" 2>/dev/null)
        echo -e "    ${GREEN}✓${NC} AWS Bedrock configured (region: $aws_region, profile: $aws_profile)"
        _009_add_check "$report_file" "aws_bedrock" "pass" "optional" "$aws_region"
        ((_009_CHECKS_PASS++))
    fi

    # Check if any provider is configured
    if [[ "$max_enabled" != "true" && -z "$anthropic_key" && -z "$aws_region" ]]; then
        echo -e "    ${YELLOW}!${NC} No API credentials configured"
        echo -e "      ${DIM}Run Task 004 (API Keys) to configure${NC}"
        _009_add_check "$report_file" "api_credentials" "warn" "critical" ""
        ((_009_CHECKS_WARN++))
    fi

    echo ""
}

# Validate Ollama hosts (array support for LAN clusters)
_009_validate_ollama_hosts() {
    local secrets_file="$1"
    local report_file="$2"

    [[ ! -f "$secrets_file" ]] && return

    local ollama_hosts=$(jq -r '.ollama_hosts // []' "$secrets_file" 2>/dev/null)
    local host_count=$(echo "$ollama_hosts" | jq 'length' 2>/dev/null || echo "0")

    if [[ "$host_count" -eq 0 ]]; then
        return
    fi

    echo -e "${CYAN}  Ollama Hosts:${NC}"

    local healthy_count=0
    local total_count=0

    # Use process substitution to avoid subshell
    while IFS= read -r host; do
        [[ -z "$host" || "$host" == "null" ]] && continue
        ((total_count++))

        # Clean host URL
        local clean_host="${host#http://}"
        clean_host="${clean_host#https://}"

        echo -n "    Testing $host... "
        if curl -s --connect-timeout 3 "http://$clean_host/api/tags" &>/dev/null; then
            echo -e "${GREEN}✓${NC} reachable"
            ((healthy_count++))
        else
            echo -e "${YELLOW}○${NC} unreachable"
        fi
    done < <(echo "$ollama_hosts" | jq -r '.[]' 2>/dev/null)

    if [[ $healthy_count -eq $total_count ]]; then
        echo -e "    ${GREEN}✓${NC} All $total_count Ollama host(s) healthy"
        _009_add_check "$report_file" "ollama_hosts" "pass" "optional" "$healthy_count/$total_count"
        ((_009_CHECKS_PASS++))
    elif [[ $healthy_count -gt 0 ]]; then
        echo -e "    ${YELLOW}!${NC} $healthy_count of $total_count Ollama hosts reachable"
        _009_add_check "$report_file" "ollama_hosts" "warn" "optional" "$healthy_count/$total_count"
        ((_009_CHECKS_WARN++))
    else
        echo -e "    ${RED}✗${NC} No Ollama hosts reachable"
        _009_add_check "$report_file" "ollama_hosts" "fail" "optional" "0/$total_count"
        ((_009_CHECKS_WARN++))
    fi

    echo ""
}

# Test Anthropic API
_009_test_anthropic_api() {
    local key="$1"
    local response=$(curl -s -w "%{http_code}" -o /dev/null \
        -H "x-api-key: $key" \
        -H "anthropic-version: 2023-06-01" \
        "https://api.anthropic.com/v1/models" 2>/dev/null)
    [[ "$response" == "200" ]]
}

# Validate Git configuration
_009_validate_git() {
    local report_file="$1"

    echo -e "${CYAN}  Git Configuration:${NC}"

    local git_name=$(git config user.name 2>/dev/null || true)
    local git_email=$(git config user.email 2>/dev/null || true)

    if [[ -n "$git_name" && -n "$git_email" ]]; then
        echo -e "    ${GREEN}✓${NC} User: $git_name <$git_email>"
        _009_add_check "$report_file" "git_user" "pass" "recommended" ""
        ((_009_CHECKS_PASS++))
    else
        echo -e "    ${YELLOW}!${NC} Git user not configured"
        echo -e "      ${DIM}git config --global user.name \"Your Name\"${NC}"
        echo -e "      ${DIM}git config --global user.email \"you@example.com\"${NC}"
        _009_add_check "$report_file" "git_user" "warn" "recommended" ""
        ((_009_CHECKS_WARN++))
    fi

    if git rev-parse --git-dir &>/dev/null; then
        local branch=$(git branch --show-current 2>/dev/null || echo "unknown")
        echo -e "    ${GREEN}✓${NC} Git repository (branch: $branch)"
        _009_add_check "$report_file" "git_repo" "pass" "recommended" ""
        ((_009_CHECKS_PASS++))
    else
        echo -e "    ${YELLOW}!${NC} Not a git repository"
        _009_add_check "$report_file" "git_repo" "warn" "recommended" ""
        ((_009_CHECKS_WARN++))
    fi

    echo ""
}

# Validate agent repository
_009_validate_agents() {
    local config_file="$1"
    local report_file="$2"

    echo -e "${CYAN}  Agent Repository:${NC}"

    # Check if agent config exists in project config
    local agent_repo=$(jq -r '.repositories.agents.repository // ""' "$config_file" 2>/dev/null)

    if [[ -z "$agent_repo" || "$agent_repo" == "null" || "$agent_repo" == "" ]]; then
        echo -e "    ${YELLOW}!${NC} Agent repository not configured"
        echo -e "      ${DIM}Run Task 008 (Repository Setup) to configure${NC}"
        _009_add_check "$report_file" "agent_repo" "warn" "recommended" ""
        ((_009_CHECKS_WARN++))
        echo ""
        return
    fi

    # Verify the repository path exists
    if [[ -d "$agent_repo" ]]; then
        echo -e "    ${GREEN}✓${NC} Repository: $agent_repo"
        _009_add_check "$report_file" "agent_repo" "pass" "recommended" "$agent_repo"
        ((_009_CHECKS_PASS++))
    else
        echo -e "    ${RED}✗${NC} Repository not found: $agent_repo"
        _009_add_check "$report_file" "agent_repo" "fail" "recommended" "$agent_repo"
        ((_009_CHECKS_FAIL++))
        echo ""
        return
    fi

    # Verify manifest exists and is valid
    local manifest="$agent_repo/agent-manifest.json"
    if [[ -f "$manifest" ]] && jq -e . "$manifest" &>/dev/null; then
        local agent_count=$(jq '[.phases[].agents | length] | add // 0' "$manifest" 2>/dev/null || echo "0")
        echo -e "    ${GREEN}✓${NC} Manifest valid ($agent_count agents)"
        _009_add_check "$report_file" "agent_manifest" "pass" "recommended" "$agent_count"
        ((_009_CHECKS_PASS++))
    else
        echo -e "    ${YELLOW}!${NC} Manifest missing or invalid"
        _009_add_check "$report_file" "agent_manifest" "warn" "recommended" ""
        ((_009_CHECKS_WARN++))
    fi

    echo ""
}

# Assess CPU capabilities
_009_assess_cpu() {
    local report_file="$1"
    local os_type="$2"

    echo -e "${CYAN}  CPU:${NC}"

    local cpu_model="Unknown"
    local cpu_cores=0
    local cpu_arch=$(uname -m)

    case "$os_type" in
        macos)
            cpu_model=$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo "Apple Silicon")
            cpu_cores=$(sysctl -n hw.ncpu 2>/dev/null || echo 0)
            ;;
        linux)
            cpu_model=$(grep -m1 'model name' /proc/cpuinfo 2>/dev/null | cut -d: -f2 | xargs || echo "Unknown")
            cpu_cores=$(nproc 2>/dev/null || grep -c processor /proc/cpuinfo 2>/dev/null || echo 0)
            ;;
        windows)
            echo -e "    ${DIM}○${NC} Detailed CPU info unavailable on Windows"
            cpu_cores=$(echo "$NUMBER_OF_PROCESSORS" 2>/dev/null || echo 0)
            cpu_model="Windows CPU"
            ;;
    esac

    echo -e "    ${DIM}Model:${NC} $cpu_model"
    echo -e "    ${DIM}Cores:${NC} $cpu_cores"
    echo -e "    ${DIM}Arch:${NC}  $cpu_arch"

    # Recommendation based on cores
    if [[ $cpu_cores -ge 8 ]]; then
        echo -e "    ${GREEN}✓${NC} Suitable for parallel workers"
    elif [[ $cpu_cores -ge 4 ]]; then
        echo -e "    ${YELLOW}○${NC} Limited parallelization (4-7 cores)"
    else
        echo -e "    ${YELLOW}!${NC} Low core count - sequential processing recommended"
    fi

    # Update report
    local tmp=$(atomic_mktemp)
    jq --arg model "$cpu_model" --argjson cores "$cpu_cores" --arg arch "$cpu_arch" \
        '.capabilities.cpu = {"model": $model, "cores": $cores, "architecture": $arch}' \
        "$report_file" > "$tmp" && mv "$tmp" "$report_file"

    echo ""
}

# Assess GPU capabilities
_009_assess_gpu() {
    local report_file="$1"
    local os_type="$2"

    echo -e "${CYAN}  GPU:${NC}"

    local gpu_name=""
    local gpu_vram=""
    local has_cuda=false
    local has_metal=false

    case "$os_type" in
        macos)
            # macOS - check for Metal
            gpu_name=$(system_profiler SPDisplaysDataType 2>/dev/null | grep "Chipset Model" | head -1 | cut -d: -f2 | xargs || echo "")
            if [[ -z "$gpu_name" ]]; then
                gpu_name=$(system_profiler SPDisplaysDataType 2>/dev/null | grep "Chip" | head -1 | cut -d: -f2 | xargs || echo "Integrated")
            fi
            has_metal=true
            echo -e "    ${DIM}GPU:${NC}   $gpu_name"
            echo -e "    ${GREEN}✓${NC} Metal support (Apple Silicon / macOS)"
            ;;
        linux)
            # Check for NVIDIA
            if command -v nvidia-smi &>/dev/null; then
                gpu_name=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 || echo "NVIDIA GPU")
                gpu_vram=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>/dev/null | head -1 || echo "")
                has_cuda=true
                echo -e "    ${DIM}GPU:${NC}   $gpu_name"
                [[ -n "$gpu_vram" ]] && echo -e "    ${DIM}VRAM:${NC}  $gpu_vram"
                echo -e "    ${GREEN}✓${NC} CUDA support"
            elif command -v rocm-smi &>/dev/null; then
                gpu_name=$(rocm-smi --showproductname 2>/dev/null | grep "Card" | head -1 || echo "AMD GPU")
                echo -e "    ${DIM}GPU:${NC}   $gpu_name"
                echo -e "    ${GREEN}✓${NC} ROCm support (AMD)"
            elif command -v lspci &>/dev/null; then
                # Check lspci for any GPU
                local pci_gpu=$(lspci 2>/dev/null | grep -i 'vga\|3d\|display' | head -1 || echo "")
                if [[ -n "$pci_gpu" ]]; then
                    gpu_name=$(echo "$pci_gpu" | cut -d: -f3 | xargs)
                    echo -e "    ${DIM}GPU:${NC}   $gpu_name"
                    echo -e "    ${YELLOW}○${NC} No CUDA/ROCm detected"
                else
                    echo -e "    ${DIM}○${NC} No dedicated GPU detected"
                fi
            else
                echo -e "    ${DIM}○${NC} GPU detection unavailable"
            fi
            ;;
        windows)
            echo -e "    ${DIM}○${NC} GPU detection unavailable on Windows (use Device Manager)"
            gpu_name="Unknown (Windows)"
            ;;
    esac

    # Local LLM recommendation
    if $has_cuda || $has_metal; then
        echo -e "    ${GREEN}✓${NC} Suitable for local LLM inference (Ollama)"
    else
        echo -e "    ${DIM}○${NC} CPU-only inference available"
    fi

    # Update report
    local tmp=$(atomic_mktemp)
    jq --arg name "$gpu_name" --arg vram "$gpu_vram" --argjson cuda "$has_cuda" --argjson metal "$has_metal" \
        '.capabilities.gpu = {"name": $name, "vram": $vram, "cuda": $cuda, "metal": $metal}' \
        "$report_file" > "$tmp" && mv "$tmp" "$report_file"

    echo ""
}

# Assess memory
_009_assess_memory() {
    local report_file="$1"
    local os_type="$2"

    echo -e "${CYAN}  Memory:${NC}"

    local total_mb=0
    local avail_mb=0

    case "$os_type" in
        macos)
            total_mb=$(($(sysctl -n hw.memsize 2>/dev/null || echo 0) / 1024 / 1024))
            # macOS doesn't have a simple "available" - use vm_stat
            local pages_free=$(vm_stat 2>/dev/null | grep "Pages free" | awk '{print $3}' | tr -d '.')
            local page_size=$(sysctl -n hw.pagesize 2>/dev/null || echo 4096)
            avail_mb=$(awk "BEGIN {printf \"%.0f\", ($pages_free * $page_size) / 1024 / 1024}")
            ;;
        linux)
            total_mb=$(awk '/MemTotal/ {printf "%.0f", $2/1024}' /proc/meminfo 2>/dev/null || echo 0)
            avail_mb=$(awk '/MemAvailable/ {printf "%.0f", $2/1024}' /proc/meminfo 2>/dev/null || echo 0)
            ;;
        windows)
            echo -e "    ${DIM}○${NC} Memory detection limited on Windows"
            # Try to get from wmic if available
            total_mb=0
            avail_mb=0
            ;;
    esac

    local total_gb=$((total_mb / 1024))
    local avail_gb=$((avail_mb / 1024))

    if [[ $total_gb -gt 0 ]]; then
        echo -e "    ${DIM}Total:${NC}     ${total_gb} GB"
        echo -e "    ${DIM}Available:${NC} ${avail_gb} GB"

        # Recommendations
        if [[ $total_gb -ge 32 ]]; then
            echo -e "    ${GREEN}✓${NC} Excellent for large LLM models"
        elif [[ $total_gb -ge 16 ]]; then
            echo -e "    ${GREEN}✓${NC} Good for medium LLM models"
        elif [[ $total_gb -ge 8 ]]; then
            echo -e "    ${YELLOW}○${NC} Limited - small models only"
        else
            echo -e "    ${YELLOW}!${NC} Low memory - API-only recommended"
        fi
    fi

    # Update report
    local tmp=$(atomic_mktemp)
    jq --argjson total "$total_mb" --argjson avail "$avail_mb" \
        '.capabilities.memory = {"total_mb": $total, "available_mb": $avail}' \
        "$report_file" > "$tmp" && mv "$tmp" "$report_file"

    echo ""
}

# Assess storage (cross-platform)
_009_assess_storage() {
    local report_file="$1"
    local os_type="$2"

    echo -e "${CYAN}  Storage:${NC}"

    local local_avail=0
    local local_total=0
    local local_mount="/"

    case "$os_type" in
        macos|linux)
            # Use portable df output and parse with awk
            local df_output=$(df -k . 2>/dev/null | tail -1)
            local_total=$(echo "$df_output" | awk '{printf "%.0f", $2/1024/1024}')
            local_avail=$(echo "$df_output" | awk '{printf "%.0f", $4/1024/1024}')
            local_mount=$(echo "$df_output" | awk '{print $NF}')
            ;;
        windows)
            echo -e "    ${DIM}○${NC} Storage detection limited on Windows"
            local_total=0
            local_avail=0
            local_mount="C:"
            ;;
    esac

    echo -e "    ${DIM}Local ($local_mount):${NC}"
    if [[ $local_total -gt 0 ]]; then
        echo -e "      Total: ${local_total} GB, Available: ${local_avail} GB"

        if [[ $local_avail -ge 50 ]]; then
            echo -e "      ${GREEN}✓${NC} Sufficient space"
        elif [[ $local_avail -ge 10 ]]; then
            echo -e "      ${YELLOW}○${NC} Limited space"
        else
            echo -e "      ${YELLOW}!${NC} Low disk space"
        fi
    fi

    # Detect mounted volumes (renamed from NAS Mounts)
    local storage_json
    storage_json=$(jq -n --arg mount "$local_mount" --argjson total "$local_total" --argjson avail "$local_avail" \
        '{"local": {"mount": $mount, "total_gb": $total, "available_gb": $avail}, "mounts": []}')

    if [[ "$os_type" != "windows" ]]; then
        local mounted_vols=$(mount 2>/dev/null | grep -E 'nfs|cifs|smb|afp|fuse' | awk '{print $3}' || true)

        if [[ -n "$mounted_vols" ]]; then
            echo ""
            echo -e "    ${DIM}Storage Mounts:${NC}"
            while IFS= read -r mount_point; do
                [[ -z "$mount_point" ]] && continue
                local df_mount=$(df -k "$mount_point" 2>/dev/null | tail -1)
                local mount_total=$(echo "$df_mount" | awk '{printf "%.0f", $2/1024/1024}')
                local mount_avail=$(echo "$df_mount" | awk '{printf "%.0f", $4/1024/1024}')
                echo -e "      ${GREEN}✓${NC} $mount_point (${mount_avail}G free / ${mount_total}G)"
                storage_json=$(echo "$storage_json" | jq --arg mp "$mount_point" --argjson avail "$mount_avail" --argjson total "$mount_total" \
                    '.mounts += [{"mount": $mp, "total_gb": $total, "available_gb": $avail}]')
            done <<< "$mounted_vols"
        fi
    fi

    # Update report
    local tmp=$(atomic_mktemp)
    jq --argjson storage "$storage_json" '.capabilities.storage = $storage' "$report_file" > "$tmp" && mv "$tmp" "$report_file"

    echo ""
}

# Assess network
_009_assess_network() {
    local report_file="$1"

    echo -e "${CYAN}  Network:${NC}"

    local network_json='{"lan": {}, "wan": {}}'

    # LAN - test local network latency
    local gateway=""
    if command -v ip &>/dev/null; then
        gateway=$(ip route 2>/dev/null | grep default | awk '{print $3}' | head -1)
    elif command -v route &>/dev/null; then
        gateway=$(route -n get default 2>/dev/null | grep gateway | awk '{print $2}')
    fi

    if [[ -n "$gateway" ]]; then
        local lan_latency=$(ping -c 3 -q "$gateway" 2>/dev/null | grep -oE 'avg[^=]*=[^/]*/([0-9.]+)' | grep -oE '[0-9.]+$' || echo "")
        if [[ -n "$lan_latency" ]]; then
            echo -e "    ${DIM}LAN latency:${NC} ${lan_latency}ms (gateway: $gateway)"
            network_json=$(echo "$network_json" | jq --arg lat "$lan_latency" --arg gw "$gateway" '.lan = {"gateway": $gw, "latency_ms": $lat}')
        fi
    fi

    # WAN - Cloudflare speed test (lightweight)
    echo -e "    ${DIM}Testing WAN connectivity...${NC}"

    # Download test (small file) - use awk instead of bc for portability
    local dl_result=$(curl -s -w "%{speed_download}" -o /dev/null --connect-timeout 5 "https://speed.cloudflare.com/__down?bytes=500000" 2>/dev/null || echo "0")
    local dl_mbps=$(awk "BEGIN {printf \"%.2f\", $dl_result / 125000}")

    # Latency to Cloudflare - use awk instead of bc
    local wan_latency=$(curl -s -w "%{time_connect}" -o /dev/null --connect-timeout 5 "https://speed.cloudflare.com/" 2>/dev/null || echo "0")
    local wan_latency_ms=$(awk "BEGIN {printf \"%.0f\", $wan_latency * 1000}")

    echo -e "    ${DIM}WAN latency:${NC}  ${wan_latency_ms}ms (Cloudflare)"
    echo -e "    ${DIM}Download:${NC}     ~${dl_mbps} Mbps"

    # API endpoint latency
    local api_latency=$(curl -s -w "%{time_connect}" -o /dev/null --connect-timeout 5 "https://api.anthropic.com/" 2>/dev/null || echo "0")
    local api_latency_ms=$(awk "BEGIN {printf \"%.0f\", $api_latency * 1000}")
    echo -e "    ${DIM}API latency:${NC}  ${api_latency_ms}ms (Anthropic)"

    # Recommendations - use awk for comparison
    local dl_int=$(awk "BEGIN {printf \"%.0f\", $dl_mbps}")
    if [[ "$dl_int" -ge 50 ]]; then
        echo -e "    ${GREEN}✓${NC} Fast connection"
    elif [[ "$dl_int" -ge 10 ]]; then
        echo -e "    ${GREEN}✓${NC} Good connection"
    elif [[ "$dl_int" -ge 1 ]]; then
        echo -e "    ${YELLOW}○${NC} Moderate connection"
    else
        echo -e "    ${YELLOW}!${NC} Slow connection - consider local LLM"
    fi

    network_json=$(echo "$network_json" | jq \
        --arg dl "$dl_mbps" --arg wan_lat "$wan_latency_ms" --arg api_lat "$api_latency_ms" \
        '.wan = {"download_mbps": $dl, "latency_ms": $wan_lat, "api_latency_ms": $api_lat}')

    # Update report
    local tmp=$(atomic_mktemp)
    jq --argjson network "$network_json" '.capabilities.network = $network' "$report_file" > "$tmp" && mv "$tmp" "$report_file"

    echo ""
}

# Show validation summary
_009_show_summary() {
    local report_file="$1"

    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    local total=$(($_009_CHECKS_PASS + $_009_CHECKS_FAIL + $_009_CHECKS_WARN))

    if [[ $_009_CHECKS_FAIL -eq 0 ]]; then
        echo -e "  ${GREEN}✓${NC} Validation: ${BOLD}$_009_CHECKS_PASS/$total${NC} checks passed"
    else
        echo -e "  ${RED}✗${NC} Validation: ${BOLD}$_009_CHECKS_PASS/$total${NC} passed, ${RED}$_009_CHECKS_FAIL failed${NC}"
    fi

    if [[ $_009_CHECKS_WARN -gt 0 ]]; then
        echo -e "  ${YELLOW}!${NC} Warnings: $_009_CHECKS_WARN"
    fi

    # System capability summary
    local cores=$(jq '.capabilities.cpu.cores // 0' "$report_file" 2>/dev/null || echo "0")
    local mem_gb=$(jq '.capabilities.memory.total_mb // 0' "$report_file" 2>/dev/null | awk '{printf "%.0f", $1/1024}')
    local has_gpu=$(jq '.capabilities.gpu.cuda or .capabilities.gpu.metal' "$report_file" 2>/dev/null || echo "false")

    echo ""
    local gpu_str=""
    [[ "$has_gpu" == "true" ]] && gpu_str=", GPU"
    echo -e "  ${DIM}System: ${cores} cores, ${mem_gb}GB RAM${gpu_str}${NC}"

    # Update report with summary
    local tmp=$(atomic_mktemp)
    jq --argjson pass "$_009_CHECKS_PASS" --argjson fail "$_009_CHECKS_FAIL" --argjson warn "$_009_CHECKS_WARN" \
        '.summary = {"passed": $pass, "failed": $fail, "warnings": $warn}' \
        "$report_file" > "$tmp" && mv "$tmp" "$report_file"

    echo ""
}

# Add a check to the report
_009_add_check() {
    local report_file="$1"
    local name="$2"
    local status="$3"
    local level="$4"
    local version="$5"

    local tmp=$(atomic_mktemp)
    jq --arg name "$name" --arg status "$status" --arg level "$level" --arg ver "$version" \
        '.checks += [{"name": $name, "status": $status, "level": $level, "version": $ver}]' \
        "$report_file" > "$tmp" && mv "$tmp" "$report_file"
}

# Record validation results to context
_009_record_context() {
    local config_file="$1"
    local report_file="$2"

    local pass=$_009_CHECKS_PASS
    local fail=$_009_CHECKS_FAIL
    local cores=$(jq '.capabilities.cpu.cores // 0' "$report_file" 2>/dev/null || echo "0")
    local mem_gb=$(jq '.capabilities.memory.total_mb // 0' "$report_file" 2>/dev/null | awk '{printf "%.0f", $1/1024}')

    local msg="Environment validated: $pass passed"
    [[ $fail -gt 0 ]] && msg+=", $fail failed"
    msg+="; System: ${cores} cores, ${mem_gb}GB RAM"

    atomic_context_decision "$msg" "validation"

    # Copy capabilities to main config
    local cap_json=$(cat "$report_file")
    local tmp=$(atomic_mktemp)
    jq --argjson cap "$cap_json" '.system_capabilities = $cap.capabilities' "$config_file" > "$tmp" && mv "$tmp" "$config_file"

    # Register report as artifact
    atomic_context_artifact "env-validation" "$report_file" "Environment validation report"
}
