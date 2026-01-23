#!/bin/bash
#
# Task 008: Environment Check
# Validate tools and assess system capabilities
#
# Features:
#   - Tool validation with version checks
#   - API key validation (test actual connectivity)
#   - System capability assessment:
#     - CPU (cores, model, architecture)
#     - GPU (for local LLM inference)
#     - Memory (total/available RAM)
#     - Storage (local + NAS mounts)
#     - Network (LAN + WAN via Cloudflare)
#   - Retry loop on failure
#   - Records results to context
#

# Global validation state
_008_CHECKS_PASS=0
_008_CHECKS_FAIL=0
_008_CHECKS_WARN=0

task_008_environment_check() {
    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"
    local secrets_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/secrets.json"
    local report_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/env-validation.json"

    atomic_step "Environment Validation"

    # Reset counters
    _008_CHECKS_PASS=0
    _008_CHECKS_FAIL=0
    _008_CHECKS_WARN=0

    # Initialize report
    echo '{"validated_at": "'$(date -Iseconds)'", "checks": [], "capabilities": {}}' > "$report_file"

    echo ""

    # Core tool validation
    _008_validate_tools "$report_file"

    # API key validation
    _008_validate_api_keys "$secrets_file" "$report_file"

    # Git configuration
    _008_validate_git "$report_file"

    # Agent repository validation
    _008_validate_agents "$config_file" "$report_file"

    # System capabilities
    _008_assess_cpu "$report_file"
    _008_assess_gpu "$report_file"
    _008_assess_memory "$report_file"
    _008_assess_storage "$report_file"
    _008_assess_network "$report_file"

    # Summary
    _008_show_summary "$report_file"

    # Record to context
    _008_record_context "$config_file" "$report_file"

    # Handle failures
    if [[ $_008_CHECKS_FAIL -gt 0 ]]; then
        echo ""
        echo -e "  ${RED}Validation failed with $_008_CHECKS_FAIL critical issues.${NC}"
        echo ""
        echo -e "  ${YELLOW}Options:${NC}"
        echo -e "    ${DIM}[r]${NC} Retry validation"
        echo -e "    ${DIM}[b]${NC} Go back to install tools"
        echo -e "    ${DIM}[c]${NC} Continue anyway (not recommended)"
        echo ""

        while true; do
            read -p "  Choice [r]: " choice
            choice=${choice:-r}
            case "$choice" in
                r|R)
                    echo ""
                    task_008_environment_check
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

    if [[ $_008_CHECKS_WARN -gt 0 ]]; then
        atomic_success "Environment validated with $_008_CHECKS_WARN warnings"
    else
        atomic_success "Environment validated - all checks passed"
    fi

    # Offer agent repository exploration
    _008_agent_exploration "$config_file"

    return 0
}

# Introduce user to agent repository for familiarization
_008_agent_exploration() {
    local config_file="$1"
    local agent_repo=$(jq -r '.agents.repository // ""' "$config_file" 2>/dev/null)

    # Skip if no agent repo or using builtin
    if [[ -z "$agent_repo" || "$agent_repo" == "null" || "$agent_repo" == "builtin" ]]; then
        return 0
    fi

    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}AGENT REPOSITORY EXPLORATION${NC}                              ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${DIM}Throughout the pipeline, you'll have opportunities to${NC}"
    echo -e "  ${DIM}select which agents guide each phase. Getting familiar${NC}"
    echo -e "  ${DIM}with the available agents now will help you make informed${NC}"
    echo -e "  ${DIM}choices later.${NC}"
    echo ""
    echo -e "  Agent repository: ${BOLD}$agent_repo${NC}"
    echo ""
    echo -e "  ${CYAN}Would you like to explore the agent repository now?${NC}"
    echo ""
    echo -e "    ${GREEN}[browse]${NC}  Open agent repository in a new terminal"
    echo -e "    ${YELLOW}[list]${NC}    Show agent categories here"
    echo -e "    ${DIM}[skip]${NC}    Skip - I'll explore later"
    echo ""

    read -p "  Choice [skip]: " explore_choice
    explore_choice=${explore_choice:-skip}

    case "$explore_choice" in
        browse)
            echo ""
            echo -e "  ${DIM}Opening agent repository...${NC}"
            echo ""
            echo -e "  ${BOLD}In a new terminal, run:${NC}"
            echo ""
            echo -e "    ${CYAN}cd $agent_repo${NC}"
            echo -e "    ${CYAN}ls -la${NC}"
            echo ""
            echo -e "  ${DIM}Key directories:${NC}"
            echo -e "    ${CYAN}pipeline-agents/${NC}  - Phase-specific agents"
            echo -e "    ${CYAN}expert-agents/${NC}    - Domain experts (languages, frameworks)"
            echo -e "    ${CYAN}custom/${NC}           - Your custom agents (create here)"
            echo ""
            echo -e "  ${DIM}Tip: Create custom agents in the repo's custom/ directory.${NC}"
            echo -e "  ${DIM}They'll be available for selection throughout the pipeline.${NC}"
            echo ""
            echo -e "  ${DIM}Press Enter when ready to continue...${NC}"
            read -r
            ;;
        list)
            echo ""
            _008_list_agent_categories "$agent_repo"
            echo ""
            echo -e "  ${DIM}Press Enter when ready to continue...${NC}"
            read -r
            ;;
        skip)
            echo ""
            echo -e "  ${DIM}You can explore the agent repository anytime:${NC}"
            echo -e "    ${CYAN}cd $agent_repo && ls${NC}"
            echo ""
            ;;
    esac

    atomic_context_decision "User offered agent repository exploration" "agent_familiarization"
}

# List agent categories for quick overview
_008_list_agent_categories() {
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
                local group_count=$(find "$group_dir" -name "*.md" -type f 2>/dev/null | wc -l)
                echo -e "    • $group_name: $group_count agents"
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
                local cat_count=$(find "$cat_dir" -name "*.md" -type f 2>/dev/null | wc -l)
                echo -e "    • $cat_name: $cat_count agents"
            fi
        done
        echo ""
    fi

    # Total from manifest
    if [[ -f "$manifest" ]]; then
        local total=$(jq -r '.metadata.totalAgents // 0' "$manifest")
        echo -e "  ${DIM}Total agents available: $total${NC}"
    fi
}

# Validate required tools
_008_validate_tools() {
    local report_file="$1"

    echo -e "${CYAN}  Required Tools:${NC}"

    # git
    if command -v git &>/dev/null; then
        local ver=$(git --version 2>/dev/null | awk '{print $3}')
        echo -e "    ${GREEN}✓${NC} git ($ver)"
        _008_add_check "$report_file" "git" "pass" "critical" "$ver"
        ((_008_CHECKS_PASS++))
    else
        echo -e "    ${RED}✗${NC} git - NOT FOUND"
        _008_add_check "$report_file" "git" "fail" "critical" ""
        ((_008_CHECKS_FAIL++))
    fi

    # jq
    if command -v jq &>/dev/null; then
        local ver=$(jq --version 2>/dev/null | sed 's/jq-//')
        echo -e "    ${GREEN}✓${NC} jq ($ver)"
        _008_add_check "$report_file" "jq" "pass" "critical" "$ver"
        ((_008_CHECKS_PASS++))
    else
        echo -e "    ${RED}✗${NC} jq - NOT FOUND"
        _008_add_check "$report_file" "jq" "fail" "critical" ""
        ((_008_CHECKS_FAIL++))
    fi

    # node (with version check)
    if command -v node &>/dev/null; then
        local ver=$(node --version 2>/dev/null | sed 's/v//')
        local major=$(echo "$ver" | cut -d. -f1)
        if [[ "$major" -ge 18 ]]; then
            echo -e "    ${GREEN}✓${NC} node (v$ver)"
            _008_add_check "$report_file" "node" "pass" "critical" "$ver"
            ((_008_CHECKS_PASS++))
        else
            echo -e "    ${YELLOW}!${NC} node (v$ver) - v18+ required"
            _008_add_check "$report_file" "node" "warn" "critical" "$ver"
            ((_008_CHECKS_WARN++))
        fi
    else
        echo -e "    ${RED}✗${NC} node - NOT FOUND"
        _008_add_check "$report_file" "node" "fail" "critical" ""
        ((_008_CHECKS_FAIL++))
    fi

    # claude CLI
    if command -v claude &>/dev/null; then
        local ver=$(claude --version 2>/dev/null | head -1 | awk '{print $NF}' || echo "installed")
        echo -e "    ${GREEN}✓${NC} claude ($ver)"
        _008_add_check "$report_file" "claude" "pass" "critical" "$ver"
        ((_008_CHECKS_PASS++))
    else
        echo -e "    ${RED}✗${NC} claude CLI - NOT FOUND"
        echo -e "      ${DIM}npm install -g @anthropic-ai/claude-code${NC}"
        _008_add_check "$report_file" "claude" "fail" "critical" ""
        ((_008_CHECKS_FAIL++))
    fi

    echo ""

    # Optional tools
    echo -e "${CYAN}  Optional Tools:${NC}"

    for tool in gh docker curl; do
        if command -v $tool &>/dev/null; then
            local ver=$($tool --version 2>/dev/null | head -1 | grep -oE '[0-9]+\.[0-9]+\.?[0-9]*' | head -1 || echo "")
            echo -e "    ${GREEN}✓${NC} $tool${ver:+ ($ver)}"
            _008_add_check "$report_file" "$tool" "pass" "optional" "$ver"
            ((_008_CHECKS_PASS++))
        else
            echo -e "    ${DIM}○${NC} $tool (not installed)"
            _008_add_check "$report_file" "$tool" "missing" "optional" ""
        fi
    done

    echo ""
}

# Validate API keys
_008_validate_api_keys() {
    local secrets_file="$1"
    local report_file="$2"

    [[ ! -f "$secrets_file" ]] && return

    echo -e "${CYAN}  API Keys:${NC}"

    # Check Anthropic key
    local anthropic_key=$(jq -r '.anthropic_api_key // ""' "$secrets_file" 2>/dev/null)
    if [[ -n "$anthropic_key" && "$anthropic_key" != "null" ]]; then
        echo -e "    ${DIM}Testing Anthropic API...${NC}"
        if _008_test_anthropic_api "$anthropic_key"; then
            echo -e "    ${GREEN}✓${NC} Anthropic API key valid"
            _008_add_check "$report_file" "anthropic_api" "pass" "critical" ""
            ((_008_CHECKS_PASS++))
        else
            echo -e "    ${RED}✗${NC} Anthropic API key invalid or network error"
            _008_add_check "$report_file" "anthropic_api" "fail" "critical" ""
            ((_008_CHECKS_FAIL++))
        fi
    fi

    # Check OpenAI key
    local openai_key=$(jq -r '.openai_api_key // ""' "$secrets_file" 2>/dev/null)
    if [[ -n "$openai_key" && "$openai_key" != "null" ]]; then
        echo -e "    ${DIM}Testing OpenAI API...${NC}"
        if _008_test_openai_api "$openai_key"; then
            echo -e "    ${GREEN}✓${NC} OpenAI API key valid"
            _008_add_check "$report_file" "openai_api" "pass" "optional" ""
            ((_008_CHECKS_PASS++))
        else
            echo -e "    ${YELLOW}!${NC} OpenAI API key invalid"
            _008_add_check "$report_file" "openai_api" "warn" "optional" ""
            ((_008_CHECKS_WARN++))
        fi
    fi

    # Check Ollama
    local ollama_host=$(jq -r '.ollama_host // ""' "$secrets_file" 2>/dev/null)
    if [[ -n "$ollama_host" && "$ollama_host" != "null" ]]; then
        if curl -s "$ollama_host/api/tags" &>/dev/null; then
            echo -e "    ${GREEN}✓${NC} Ollama server reachable"
            _008_add_check "$report_file" "ollama" "pass" "optional" ""
            ((_008_CHECKS_PASS++))
        else
            echo -e "    ${YELLOW}!${NC} Ollama server not responding"
            _008_add_check "$report_file" "ollama" "warn" "optional" ""
            ((_008_CHECKS_WARN++))
        fi
    fi

    echo ""
}

# Test Anthropic API
_008_test_anthropic_api() {
    local key="$1"
    local response=$(curl -s -w "%{http_code}" -o /dev/null \
        -H "x-api-key: $key" \
        -H "anthropic-version: 2023-06-01" \
        "https://api.anthropic.com/v1/models" 2>/dev/null)
    [[ "$response" == "200" ]]
}

# Test OpenAI API
_008_test_openai_api() {
    local key="$1"
    local response=$(curl -s -w "%{http_code}" -o /dev/null \
        -H "Authorization: Bearer $key" \
        "https://api.openai.com/v1/models" 2>/dev/null)
    [[ "$response" == "200" ]]
}

# Validate Git configuration
_008_validate_git() {
    local report_file="$1"

    echo -e "${CYAN}  Git Configuration:${NC}"

    local git_name=$(git config user.name 2>/dev/null || true)
    local git_email=$(git config user.email 2>/dev/null || true)

    if [[ -n "$git_name" && -n "$git_email" ]]; then
        echo -e "    ${GREEN}✓${NC} User: $git_name <$git_email>"
        _008_add_check "$report_file" "git_user" "pass" "recommended" ""
        ((_008_CHECKS_PASS++))
    else
        echo -e "    ${YELLOW}!${NC} Git user not configured"
        echo -e "      ${DIM}git config --global user.name \"Your Name\"${NC}"
        echo -e "      ${DIM}git config --global user.email \"you@example.com\"${NC}"
        _008_add_check "$report_file" "git_user" "warn" "recommended" ""
        ((_008_CHECKS_WARN++))
    fi

    if git rev-parse --git-dir &>/dev/null; then
        local branch=$(git branch --show-current 2>/dev/null || echo "unknown")
        echo -e "    ${GREEN}✓${NC} Git repository (branch: $branch)"
        _008_add_check "$report_file" "git_repo" "pass" "recommended" ""
        ((_008_CHECKS_PASS++))
    else
        echo -e "    ${YELLOW}!${NC} Not a git repository"
        _008_add_check "$report_file" "git_repo" "warn" "recommended" ""
        ((_008_CHECKS_WARN++))
    fi

    echo ""
}

# Validate agent repository
_008_validate_agents() {
    local config_file="$1"
    local report_file="$2"

    echo -e "${CYAN}  Agent Repository:${NC}"

    # Check if agent config exists in project config
    local agent_repo=$(jq -r '.agents.repository // ""' "$config_file" 2>/dev/null)
    local agent_count=$(jq -r '.agents.total_agents // 0' "$config_file" 2>/dev/null)

    if [[ -z "$agent_repo" || "$agent_repo" == "null" ]]; then
        echo -e "    ${YELLOW}!${NC} Agent repository not configured"
        echo -e "      ${DIM}Run Task 007 (Agent Repository) to configure${NC}"
        _008_add_check "$report_file" "agent_repo" "warn" "recommended" ""
        ((_008_CHECKS_WARN++))
        echo ""
        return
    fi

    if [[ "$agent_repo" == "builtin" ]]; then
        echo -e "    ${GREEN}✓${NC} Using built-in agents (default)"
        _008_add_check "$report_file" "agent_repo" "pass" "recommended" "builtin"
        ((_008_CHECKS_PASS++))
        echo ""
        return
    fi

    # Verify the repository path exists
    if [[ -d "$agent_repo" ]]; then
        echo -e "    ${GREEN}✓${NC} Repository: $agent_repo"
        _008_add_check "$report_file" "agent_repo" "pass" "recommended" "$agent_repo"
        ((_008_CHECKS_PASS++))
    else
        echo -e "    ${RED}✗${NC} Repository not found: $agent_repo"
        _008_add_check "$report_file" "agent_repo" "fail" "recommended" "$agent_repo"
        ((_008_CHECKS_FAIL++))
        echo ""
        return
    fi

    # Verify manifest exists and is valid
    local manifest="$agent_repo/agent-manifest.json"
    if [[ -f "$manifest" ]] && jq -e . "$manifest" &>/dev/null; then
        echo -e "    ${GREEN}✓${NC} Manifest valid ($agent_count agents)"
        _008_add_check "$report_file" "agent_manifest" "pass" "recommended" "$agent_count"
        ((_008_CHECKS_PASS++))
    else
        echo -e "    ${YELLOW}!${NC} Manifest missing or invalid"
        _008_add_check "$report_file" "agent_manifest" "warn" "recommended" ""
        ((_008_CHECKS_WARN++))
    fi

    # Check for pipeline agents
    local pipeline_dir="$agent_repo/pipeline-agents"
    if [[ -d "$pipeline_dir" ]]; then
        local pipeline_count=$(find "$pipeline_dir" -name "*.md" -type f 2>/dev/null | wc -l)
        echo -e "    ${GREEN}✓${NC} Pipeline agents: $pipeline_count"
        _008_add_check "$report_file" "pipeline_agents" "pass" "recommended" "$pipeline_count"
        ((_008_CHECKS_PASS++))
    else
        echo -e "    ${YELLOW}!${NC} Pipeline agents directory not found"
        _008_add_check "$report_file" "pipeline_agents" "warn" "recommended" ""
        ((_008_CHECKS_WARN++))
    fi

    echo ""
}

# Assess CPU capabilities
_008_assess_cpu() {
    local report_file="$1"

    echo -e "${CYAN}  CPU:${NC}"

    local cpu_model=""
    local cpu_cores=0
    local cpu_arch=$(uname -m)

    case "$(uname -s)" in
        Darwin)
            cpu_model=$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo "Apple Silicon")
            cpu_cores=$(sysctl -n hw.ncpu 2>/dev/null || echo 0)
            ;;
        Linux)
            cpu_model=$(grep -m1 'model name' /proc/cpuinfo 2>/dev/null | cut -d: -f2 | xargs || echo "Unknown")
            cpu_cores=$(nproc 2>/dev/null || grep -c processor /proc/cpuinfo 2>/dev/null || echo 0)
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
    local tmp=$(mktemp)
    jq --arg model "$cpu_model" --argjson cores "$cpu_cores" --arg arch "$cpu_arch" \
        '.capabilities.cpu = {"model": $model, "cores": $cores, "architecture": $arch}' \
        "$report_file" > "$tmp" && mv "$tmp" "$report_file"

    echo ""
}

# Assess GPU capabilities
_008_assess_gpu() {
    local report_file="$1"

    echo -e "${CYAN}  GPU:${NC}"

    local gpu_name=""
    local gpu_vram=""
    local has_cuda=false
    local has_metal=false

    case "$(uname -s)" in
        Darwin)
            # macOS - check for Metal
            gpu_name=$(system_profiler SPDisplaysDataType 2>/dev/null | grep "Chipset Model" | head -1 | cut -d: -f2 | xargs || echo "")
            if [[ -z "$gpu_name" ]]; then
                gpu_name=$(system_profiler SPDisplaysDataType 2>/dev/null | grep "Chip" | head -1 | cut -d: -f2 | xargs || echo "Integrated")
            fi
            has_metal=true
            echo -e "    ${DIM}GPU:${NC}   $gpu_name"
            echo -e "    ${GREEN}✓${NC} Metal support (Apple Silicon / macOS)"
            ;;
        Linux)
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
            else
                # Check lspci for any GPU
                local pci_gpu=$(lspci 2>/dev/null | grep -i 'vga\|3d\|display' | head -1 || echo "")
                if [[ -n "$pci_gpu" ]]; then
                    gpu_name=$(echo "$pci_gpu" | cut -d: -f3 | xargs)
                    echo -e "    ${DIM}GPU:${NC}   $gpu_name"
                    echo -e "    ${YELLOW}○${NC} No CUDA/ROCm detected"
                else
                    echo -e "    ${DIM}○${NC} No dedicated GPU detected"
                fi
            fi
            ;;
    esac

    # Local LLM recommendation
    if $has_cuda || $has_metal; then
        echo -e "    ${GREEN}✓${NC} Suitable for local LLM inference (ollama)"
    else
        echo -e "    ${DIM}○${NC} CPU-only inference available"
    fi

    # Update report
    local tmp=$(mktemp)
    jq --arg name "$gpu_name" --arg vram "$gpu_vram" --argjson cuda "$has_cuda" --argjson metal "$has_metal" \
        '.capabilities.gpu = {"name": $name, "vram": $vram, "cuda": $cuda, "metal": $metal}' \
        "$report_file" > "$tmp" && mv "$tmp" "$report_file"

    echo ""
}

# Assess memory
_008_assess_memory() {
    local report_file="$1"

    echo -e "${CYAN}  Memory:${NC}"

    local total_mb=0
    local avail_mb=0

    case "$(uname -s)" in
        Darwin)
            total_mb=$(($(sysctl -n hw.memsize 2>/dev/null || echo 0) / 1024 / 1024))
            # macOS doesn't have a simple "available" - use vm_stat
            local pages_free=$(vm_stat 2>/dev/null | grep "Pages free" | awk '{print $3}' | tr -d '.')
            local page_size=$(pagesize 2>/dev/null || echo 4096)
            avail_mb=$(( (pages_free * page_size) / 1024 / 1024 ))
            ;;
        Linux)
            total_mb=$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print int($2/1024)}')
            avail_mb=$(grep MemAvailable /proc/meminfo 2>/dev/null | awk '{print int($2/1024)}')
            ;;
    esac

    local total_gb=$((total_mb / 1024))
    local avail_gb=$((avail_mb / 1024))

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

    # Update report
    local tmp=$(mktemp)
    jq --argjson total "$total_mb" --argjson avail "$avail_mb" \
        '.capabilities.memory = {"total_mb": $total, "available_mb": $avail}' \
        "$report_file" > "$tmp" && mv "$tmp" "$report_file"

    echo ""
}

# Assess storage
_008_assess_storage() {
    local report_file="$1"

    echo -e "${CYAN}  Storage:${NC}"

    # Local storage (current directory)
    local local_avail=$(df -BG . 2>/dev/null | tail -1 | awk '{print $4}' | tr -d 'G' || echo "0")
    local local_total=$(df -BG . 2>/dev/null | tail -1 | awk '{print $2}' | tr -d 'G' || echo "0")
    local local_mount=$(df . 2>/dev/null | tail -1 | awk '{print $NF}' || echo "/")

    echo -e "    ${DIM}Local ($local_mount):${NC}"
    echo -e "      Total: ${local_total} GB, Available: ${local_avail} GB"

    if [[ $local_avail -ge 50 ]]; then
        echo -e "      ${GREEN}✓${NC} Sufficient space"
    elif [[ $local_avail -ge 10 ]]; then
        echo -e "      ${YELLOW}○${NC} Limited space"
    else
        echo -e "      ${YELLOW}!${NC} Low disk space"
    fi

    # Detect NAS mounts
    local nas_mounts=$(mount 2>/dev/null | grep -E 'nfs|cifs|smb|afp' | awk '{print $3}' || true)
    local storage_json
    storage_json=$(jq -n --arg mount "$local_mount" --argjson total "$local_total" --argjson avail "$local_avail" \
        '{"local": {"mount": $mount, "total_gb": $total, "available_gb": $avail}, "nas": []}')

    if [[ -n "$nas_mounts" ]]; then
        echo ""
        echo -e "    ${DIM}NAS Mounts:${NC}"
        while IFS= read -r mount_point; do
            [[ -z "$mount_point" ]] && continue
            local nas_avail=$(df -BG "$mount_point" 2>/dev/null | tail -1 | awk '{print $4}' | tr -d 'G' || echo "0")
            local nas_total=$(df -BG "$mount_point" 2>/dev/null | tail -1 | awk '{print $2}' | tr -d 'G' || echo "0")
            echo -e "      ${GREEN}✓${NC} $mount_point (${nas_avail}G free / ${nas_total}G)"
            storage_json=$(echo "$storage_json" | jq --arg mp "$mount_point" --argjson avail "$nas_avail" --argjson total "$nas_total" \
                '.nas += [{"mount": $mp, "total_gb": $total, "available_gb": $avail}]')
        done <<< "$nas_mounts"
    fi

    # Update report
    local tmp=$(mktemp)
    echo "$storage_json" | jq --slurpfile r "$report_file" '$r[0] | .capabilities.storage = input' - > "$tmp" && mv "$tmp" "$report_file"

    echo ""
}

# Assess network
_008_assess_network() {
    local report_file="$1"

    echo -e "${CYAN}  Network:${NC}"

    local network_json='{"lan": {}, "wan": {}}'

    # LAN - test local network latency
    local gateway=$(ip route 2>/dev/null | grep default | awk '{print $3}' | head -1 || route -n get default 2>/dev/null | grep gateway | awk '{print $2}')
    if [[ -n "$gateway" ]]; then
        local lan_latency=$(ping -c 3 -q "$gateway" 2>/dev/null | grep 'avg' | awk -F'/' '{print $5}' || echo "")
        if [[ -n "$lan_latency" ]]; then
            echo -e "    ${DIM}LAN latency:${NC} ${lan_latency}ms (gateway: $gateway)"
            network_json=$(echo "$network_json" | jq --arg lat "$lan_latency" --arg gw "$gateway" '.lan = {"gateway": $gw, "latency_ms": $lat}')
        fi
    fi

    # WAN - Cloudflare speed test (lightweight)
    echo -e "    ${DIM}Testing WAN speed (Cloudflare)...${NC}"

    # Download test (small file)
    local start_time=$(date +%s%N)
    local dl_result=$(curl -s -w "%{speed_download}" -o /dev/null "https://speed.cloudflare.com/__down?bytes=1000000" 2>/dev/null || echo "0")
    local dl_mbps=$(echo "scale=2; $dl_result / 125000" | bc 2>/dev/null || echo "0")

    # Latency to Cloudflare
    local wan_latency=$(curl -s -w "%{time_connect}" -o /dev/null "https://speed.cloudflare.com/" 2>/dev/null || echo "0")
    local wan_latency_ms=$(echo "scale=0; $wan_latency * 1000" | bc 2>/dev/null || echo "0")

    echo -e "    ${DIM}WAN latency:${NC}  ${wan_latency_ms}ms (Cloudflare)"
    echo -e "    ${DIM}Download:${NC}     ~${dl_mbps} Mbps"

    # API endpoint latency
    local api_latency=$(curl -s -w "%{time_connect}" -o /dev/null "https://api.anthropic.com/" 2>/dev/null || echo "0")
    local api_latency_ms=$(echo "scale=0; $api_latency * 1000" | bc 2>/dev/null || echo "0")
    echo -e "    ${DIM}API latency:${NC}  ${api_latency_ms}ms (Anthropic)"

    # Recommendations
    if [[ "${dl_mbps%.*}" -ge 50 ]]; then
        echo -e "    ${GREEN}✓${NC} Fast connection"
    elif [[ "${dl_mbps%.*}" -ge 10 ]]; then
        echo -e "    ${GREEN}✓${NC} Good connection"
    elif [[ "${dl_mbps%.*}" -ge 1 ]]; then
        echo -e "    ${YELLOW}○${NC} Moderate connection"
    else
        echo -e "    ${YELLOW}!${NC} Slow connection - consider local LLM"
    fi

    network_json=$(echo "$network_json" | jq \
        --arg dl "$dl_mbps" --arg wan_lat "$wan_latency_ms" --arg api_lat "$api_latency_ms" \
        '.wan = {"download_mbps": $dl, "latency_ms": $wan_lat, "api_latency_ms": $api_lat}')

    # Update report
    local tmp=$(mktemp)
    echo "$network_json" | jq --slurpfile r "$report_file" '$r[0] | .capabilities.network = input' - > "$tmp" && mv "$tmp" "$report_file"

    echo ""
}

# Show validation summary
_008_show_summary() {
    local report_file="$1"

    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    local total=$(($_008_CHECKS_PASS + $_008_CHECKS_FAIL + $_008_CHECKS_WARN))

    if [[ $_008_CHECKS_FAIL -eq 0 ]]; then
        echo -e "  ${GREEN}✓${NC} Validation: ${BOLD}$_008_CHECKS_PASS/$total${NC} checks passed"
    else
        echo -e "  ${RED}✗${NC} Validation: ${BOLD}$_008_CHECKS_PASS/$total${NC} passed, ${RED}$_008_CHECKS_FAIL failed${NC}"
    fi

    if [[ $_008_CHECKS_WARN -gt 0 ]]; then
        echo -e "  ${YELLOW}!${NC} Warnings: $_008_CHECKS_WARN"
    fi

    # System capability summary
    local cores=$(jq '.capabilities.cpu.cores // 0' "$report_file")
    local mem_gb=$(jq '.capabilities.memory.total_mb // 0' "$report_file" | awk '{print int($1/1024)}')
    local has_gpu=$(jq '.capabilities.gpu.cuda or .capabilities.gpu.metal' "$report_file")

    echo ""
    echo -e "  ${DIM}System: ${cores} cores, ${mem_gb}GB RAM${has_gpu:+, GPU}${NC}"

    # Update report with summary
    local tmp=$(mktemp)
    jq --argjson pass "$_008_CHECKS_PASS" --argjson fail "$_008_CHECKS_FAIL" --argjson warn "$_008_CHECKS_WARN" \
        '.summary = {"passed": $pass, "failed": $fail, "warnings": $warn}' \
        "$report_file" > "$tmp" && mv "$tmp" "$report_file"

    echo ""
}

# Add a check to the report
_008_add_check() {
    local report_file="$1"
    local name="$2"
    local status="$3"
    local level="$4"
    local version="$5"

    local tmp=$(mktemp)
    jq --arg name "$name" --arg status "$status" --arg level "$level" --arg ver "$version" \
        '.checks += [{"name": $name, "status": $status, "level": $level, "version": $ver}]' \
        "$report_file" > "$tmp" && mv "$tmp" "$report_file"
}

# Record validation results to context
_008_record_context() {
    local config_file="$1"
    local report_file="$2"

    local pass=$_008_CHECKS_PASS
    local fail=$_008_CHECKS_FAIL
    local cores=$(jq '.capabilities.cpu.cores // 0' "$report_file")
    local mem_gb=$(jq '.capabilities.memory.total_mb // 0' "$report_file" | awk '{print int($1/1024)}')

    local msg="Environment validated: $pass passed"
    [[ $fail -gt 0 ]] && msg+=", $fail failed"
    msg+="; System: ${cores} cores, ${mem_gb}GB RAM"

    atomic_context_decision "$msg" "validation"

    # Copy capabilities to main config
    local tmp=$(mktemp)
    jq --slurpfile cap "$report_file" '.system_capabilities = $cap[0].capabilities' "$config_file" > "$tmp" && mv "$tmp" "$config_file"

    # Register report as artifact
    atomic_context_artifact "env-validation" "$report_file" "Environment validation report"
}
