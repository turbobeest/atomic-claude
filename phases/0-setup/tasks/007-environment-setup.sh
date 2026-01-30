#!/bin/bash
#
# Task 007: Environment Setup
# List required/recommended dependencies and give user opportunity to install
#
# Features:
#   - Auto-detects OS for relevant install commands
#   - Version checking (node >= 18, etc.)
#   - Project-specific dependencies from package.json, requirements.txt, etc.
#   - Language-specific tools based on detected project type
#   - Blocks if required tools are missing
#   - Airgapped environment support notes
#   - Status summary with counts
#   - Records environment status to context
#

# Global counters for summary
_007_REQUIRED_TOTAL=0
_007_REQUIRED_INSTALLED=0
_007_RECOMMENDED_TOTAL=0
_007_RECOMMENDED_INSTALLED=0

task_007_environment_setup() {
    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"
    local manifest_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/material-manifest.json"

    atomic_step "Environment Setup"

    # Reset counters
    _007_REQUIRED_TOTAL=0
    _007_REQUIRED_INSTALLED=0
    _007_RECOMMENDED_TOTAL=0
    _007_RECOMMENDED_INSTALLED=0

    echo ""
    echo -e "${DIM}  ┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${DIM}  │ Before proceeding, ensure you have the required tools.  │${NC}"
    echo -e "${DIM}  │                                                         │${NC}"
    echo -e "${DIM}  │ Open another terminal to install any missing tools,     │${NC}"
    echo -e "${DIM}  │ then return here and press Enter to continue.           │${NC}"
    echo -e "${DIM}  └─────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # Detect OS
    local os_type=$(_007_detect_os)
    echo -e "  ${DIM}Detected OS: $os_type${NC}"
    echo ""

    # Core required tools
    _007_show_required_tools "$os_type"

    # Recommended tools
    _007_show_recommended_tools "$os_type"

    # Project-specific dependencies
    local project_lang=$(jq -r '.project.language // "unknown"' "$config_file" 2>/dev/null)
    _007_show_language_tools "$project_lang" "$os_type"

    # Project dependencies from manifest files
    _007_show_project_dependencies

    # Quick install commands
    _007_show_quick_install "$os_type"

    # Airgapped environment note
    _007_show_airgap_note

    # Status summary
    _007_show_summary

    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Check if required tools are missing
    local missing=$(($_007_REQUIRED_TOTAL - $_007_REQUIRED_INSTALLED))
    if [[ $missing -gt 0 ]]; then
        echo -e "  ${RED}Cannot proceed with $missing missing required tool(s).${NC}"
        echo ""
        echo -e "  ${YELLOW}Open another terminal to install missing tools.${NC}"
        echo -e "  ${YELLOW}When ready, return here and press Enter to re-check.${NC}"
        echo ""

        # Loop until all required tools are installed
        while [[ $missing -gt 0 ]]; do
            read -e -p "  Press Enter to re-check environment... " _ || true
            echo ""

            # Re-check required tools
            _007_REQUIRED_TOTAL=0
            _007_REQUIRED_INSTALLED=0
            _007_recheck_required "$os_type"

            missing=$(($_007_REQUIRED_TOTAL - $_007_REQUIRED_INSTALLED))
            if [[ $missing -gt 0 ]]; then
                echo -e "  ${RED}Still missing $missing required tool(s).${NC}"
                echo ""
            fi
        done

        echo -e "  ${GREEN}All required tools now installed.${NC}"
        echo ""
    else
        echo -e "  ${GREEN}All required tools installed.${NC}"
        echo ""
        read -e -p "  Press Enter to continue... " _ || true
    fi

    # Record to context
    _007_record_context "$config_file"

    atomic_success "Environment validated"
    return 0
}

# Detect operating system
_007_detect_os() {
    case "$(uname -s)" in
        Darwin*)
            echo "macos"
            ;;
        Linux*)
            if [[ -f /etc/debian_version ]]; then
                echo "debian"
            elif [[ -f /etc/redhat-release ]]; then
                echo "redhat"
            elif [[ -f /etc/arch-release ]]; then
                echo "arch"
            else
                echo "linux"
            fi
            ;;
        MINGW*|CYGWIN*|MSYS*)
            echo "windows"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

# Get install command for OS
_007_install_cmd() {
    local tool="$1"
    local os_type="$2"

    case "$tool" in
        git)
            case "$os_type" in
                macos) echo "brew install git" ;;
                debian) echo "sudo apt install git" ;;
                redhat) echo "sudo dnf install git" ;;
                arch) echo "sudo pacman -S git" ;;
                windows) echo "winget install Git.Git" ;;
                *) echo "https://git-scm.com/downloads" ;;
            esac
            ;;
        jq)
            case "$os_type" in
                macos) echo "brew install jq" ;;
                debian) echo "sudo apt install jq" ;;
                redhat) echo "sudo dnf install jq" ;;
                arch) echo "sudo pacman -S jq" ;;
                windows) echo "winget install jqlang.jq" ;;
                *) echo "https://jqlang.github.io/jq/download/" ;;
            esac
            ;;
        node)
            case "$os_type" in
                macos) echo "brew install node" ;;
                debian) echo "curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install nodejs" ;;
                redhat) echo "curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash - && sudo dnf install nodejs" ;;
                arch) echo "sudo pacman -S nodejs npm" ;;
                windows) echo "winget install OpenJS.NodeJS.LTS" ;;
                *) echo "https://nodejs.org/" ;;
            esac
            ;;
        claude)
            echo "npm install -g @anthropic-ai/claude-code"
            ;;
        task-master)
            echo "npm install -g task-master-ai"
            ;;
        gh)
            case "$os_type" in
                macos) echo "brew install gh" ;;
                debian) echo "sudo apt install gh" ;;
                redhat) echo "sudo dnf install gh" ;;
                arch) echo "sudo pacman -S github-cli" ;;
                windows) echo "winget install GitHub.cli" ;;
                *) echo "https://cli.github.com/" ;;
            esac
            ;;
        docker)
            case "$os_type" in
                macos) echo "brew install --cask docker" ;;
                debian) echo "sudo apt install docker.io" ;;
                windows) echo "winget install Docker.DockerDesktop" ;;
                *) echo "https://docs.docker.com/get-docker/" ;;
            esac
            ;;
        graphviz)
            case "$os_type" in
                macos) echo "brew install graphviz" ;;
                debian) echo "sudo apt install graphviz" ;;
                redhat) echo "sudo dnf install graphviz" ;;
                arch) echo "sudo pacman -S graphviz" ;;
                windows) echo "winget install Graphviz.Graphviz" ;;
                *) echo "https://graphviz.org/download/" ;;
            esac
            ;;
        python)
            case "$os_type" in
                macos) echo "brew install python" ;;
                debian) echo "sudo apt install python3 python3-pip python3-venv" ;;
                redhat) echo "sudo dnf install python3 python3-pip" ;;
                arch) echo "sudo pacman -S python python-pip" ;;
                windows) echo "winget install Python.Python.3.12" ;;
                *) echo "https://python.org/" ;;
            esac
            ;;
        rust)
            echo "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
            ;;
        go)
            case "$os_type" in
                macos) echo "brew install go" ;;
                debian) echo "sudo apt install golang" ;;
                windows) echo "winget install GoLang.Go" ;;
                *) echo "https://go.dev/dl/" ;;
            esac
            ;;
        *)
            echo ""
            ;;
    esac
}

# Check version meets minimum
_007_check_version() {
    local tool="$1"
    local min_version="$2"
    local current_version="$3"

    # Simple version comparison (works for semver)
    if [[ "$(printf '%s\n' "$min_version" "$current_version" | sort -V | head -n1)" == "$min_version" ]]; then
        return 0  # Current >= minimum
    else
        return 1  # Current < minimum
    fi
}

# Show required tools
_007_show_required_tools() {
    local os_type="$1"

    echo -e "${CYAN}  REQUIRED TOOLS:${NC}"
    echo ""

    # git
    ((_007_REQUIRED_TOTAL++))
    if command -v git &>/dev/null; then
        local ver=$(git --version 2>/dev/null | awk '{print $3}')
        echo -e "    ${GREEN}✓${NC} git ($ver)"
        ((_007_REQUIRED_INSTALLED++))
    else
        echo -e "    ${RED}✗${NC} git - ${BOLD}REQUIRED${NC}"
        echo -e "      ${DIM}$(_007_install_cmd git "$os_type")${NC}"
    fi

    # jq
    ((_007_REQUIRED_TOTAL++))
    if command -v jq &>/dev/null; then
        local ver=$(jq --version 2>/dev/null | sed 's/jq-//')
        echo -e "    ${GREEN}✓${NC} jq ($ver)"
        ((_007_REQUIRED_INSTALLED++))
    else
        echo -e "    ${RED}✗${NC} jq - ${BOLD}REQUIRED${NC}"
        echo -e "      ${DIM}$(_007_install_cmd jq "$os_type")${NC}"
    fi

    # node (with version check)
    ((_007_REQUIRED_TOTAL++))
    if command -v node &>/dev/null; then
        local ver=$(node --version 2>/dev/null | sed 's/v//')
        local major_ver=$(echo "$ver" | cut -d. -f1)
        if [[ "$major_ver" -ge 18 ]]; then
            echo -e "    ${GREEN}✓${NC} node (v$ver)"
            ((_007_REQUIRED_INSTALLED++))
        else
            echo -e "    ${YELLOW}!${NC} node (v$ver) - ${BOLD}v18+ required${NC}"
            echo -e "      ${DIM}$(_007_install_cmd node "$os_type")${NC}"
        fi
    else
        echo -e "    ${RED}✗${NC} node - ${BOLD}REQUIRED${NC} (v18+)"
        echo -e "      ${DIM}$(_007_install_cmd node "$os_type")${NC}"
    fi

    # claude CLI
    ((_007_REQUIRED_TOTAL++))
    if command -v claude &>/dev/null; then
        local ver=$(claude --version 2>/dev/null | head -1 || echo "installed")
        echo -e "    ${GREEN}✓${NC} claude CLI ($ver)"
        ((_007_REQUIRED_INSTALLED++))
    else
        echo -e "    ${RED}✗${NC} claude CLI - ${BOLD}REQUIRED${NC}"
        echo -e "      ${DIM}$(_007_install_cmd claude "$os_type")${NC}"
    fi

    # task-master-ai (check global install only - npx fallback is slow)
    ((_007_REQUIRED_TOTAL++))
    if command -v task-master &>/dev/null; then
        echo -e "    ${GREEN}✓${NC} task-master-ai"
        ((_007_REQUIRED_INSTALLED++))
    else
        echo -e "    ${RED}✗${NC} task-master-ai - ${BOLD}REQUIRED${NC} (task decomposition)"
        echo -e "      ${DIM}$(_007_install_cmd task-master "$os_type")${NC}"
        echo -e "      ${DIM}Note: Install globally for faster startup${NC}"
    fi

    # graphviz (for DOT → SVG diagram rendering)
    ((_007_REQUIRED_TOTAL++))
    if command -v dot &>/dev/null; then
        local ver=$(dot -V 2>&1 | head -1 | awk '{print $5}')
        echo -e "    ${GREEN}✓${NC} graphviz ($ver)"
        ((_007_REQUIRED_INSTALLED++))
    else
        echo -e "    ${RED}✗${NC} graphviz - ${BOLD}REQUIRED${NC} (diagram rendering)"
        echo -e "      ${DIM}$(_007_install_cmd graphviz "$os_type")${NC}"
    fi

    echo ""
}

# Re-check required tools (silent, just updates counters)
_007_recheck_required() {
    local os_type="$1"

    # git
    ((_007_REQUIRED_TOTAL++))
    command -v git &>/dev/null && ((_007_REQUIRED_INSTALLED++))

    # jq
    ((_007_REQUIRED_TOTAL++))
    command -v jq &>/dev/null && ((_007_REQUIRED_INSTALLED++))

    # node (with version check)
    ((_007_REQUIRED_TOTAL++))
    if command -v node &>/dev/null; then
        local major_ver=$(node --version 2>/dev/null | sed 's/v//' | cut -d. -f1)
        [[ "$major_ver" -ge 18 ]] && ((_007_REQUIRED_INSTALLED++))
    fi

    # claude CLI
    ((_007_REQUIRED_TOTAL++))
    command -v claude &>/dev/null && ((_007_REQUIRED_INSTALLED++))

    # task-master-ai
    ((_007_REQUIRED_TOTAL++))
    command -v task-master &>/dev/null && ((_007_REQUIRED_INSTALLED++))

    # graphviz
    ((_007_REQUIRED_TOTAL++))
    command -v dot &>/dev/null && ((_007_REQUIRED_INSTALLED++))
}

# Show recommended tools
_007_show_recommended_tools() {
    local os_type="$1"

    echo -e "${CYAN}  RECOMMENDED TOOLS:${NC}"
    echo ""

    # gh
    ((_007_RECOMMENDED_TOTAL++))
    if command -v gh &>/dev/null; then
        local ver=$(gh --version 2>/dev/null | head -1 | awk '{print $3}')
        echo -e "    ${GREEN}✓${NC} gh ($ver)"
        ((_007_RECOMMENDED_INSTALLED++))
    else
        echo -e "    ${YELLOW}○${NC} gh (GitHub CLI) - PR/issue management"
        echo -e "      ${DIM}$(_007_install_cmd gh "$os_type")${NC}"
    fi

    # docker
    ((_007_RECOMMENDED_TOTAL++))
    if command -v docker &>/dev/null; then
        local ver=$(docker --version 2>/dev/null | awk '{print $3}' | sed 's/,//')
        echo -e "    ${GREEN}✓${NC} docker ($ver)"
        ((_007_RECOMMENDED_INSTALLED++))
    else
        echo -e "    ${YELLOW}○${NC} docker - Containerized deployment"
        echo -e "      ${DIM}$(_007_install_cmd docker "$os_type")${NC}"
    fi

    echo ""
}

# Show language-specific tools
_007_show_language_tools() {
    local lang="$1"
    local os_type="$2"

    [[ "$lang" == "unknown" || "$lang" == "null" ]] && return

    echo -e "${CYAN}  PROJECT LANGUAGE TOOLS ($lang):${NC}"
    echo ""

    case "$lang" in
        python)
            if command -v python3 &>/dev/null; then
                local ver=$(python3 --version 2>/dev/null | awk '{print $2}')
                echo -e "    ${GREEN}✓${NC} python3 ($ver)"
            else
                echo -e "    ${YELLOW}○${NC} python3"
                echo -e "      ${DIM}$(_007_install_cmd python "$os_type")${NC}"
            fi

            if command -v pip3 &>/dev/null || command -v pip &>/dev/null; then
                echo -e "    ${GREEN}✓${NC} pip"
            else
                echo -e "    ${YELLOW}○${NC} pip"
            fi

            if command -v poetry &>/dev/null; then
                echo -e "    ${GREEN}✓${NC} poetry"
            elif [[ -f "pyproject.toml" ]] && grep -q 'poetry' pyproject.toml 2>/dev/null; then
                echo -e "    ${YELLOW}○${NC} poetry - Detected in pyproject.toml"
                echo -e "      ${DIM}pip install poetry${NC}"
            fi
            ;;

        typescript|javascript)
            if command -v npm &>/dev/null; then
                local ver=$(npm --version 2>/dev/null)
                echo -e "    ${GREEN}✓${NC} npm ($ver)"
            else
                echo -e "    ${YELLOW}○${NC} npm"
            fi

            if command -v yarn &>/dev/null; then
                echo -e "    ${GREEN}✓${NC} yarn"
            elif [[ -f "yarn.lock" ]]; then
                echo -e "    ${YELLOW}○${NC} yarn - Detected yarn.lock"
                echo -e "      ${DIM}npm install -g yarn${NC}"
            fi

            if command -v pnpm &>/dev/null; then
                echo -e "    ${GREEN}✓${NC} pnpm"
            elif [[ -f "pnpm-lock.yaml" ]]; then
                echo -e "    ${YELLOW}○${NC} pnpm - Detected pnpm-lock.yaml"
                echo -e "      ${DIM}npm install -g pnpm${NC}"
            fi
            ;;

        rust)
            if command -v rustc &>/dev/null; then
                local ver=$(rustc --version 2>/dev/null | awk '{print $2}')
                echo -e "    ${GREEN}✓${NC} rustc ($ver)"
            else
                echo -e "    ${YELLOW}○${NC} rust"
                echo -e "      ${DIM}$(_007_install_cmd rust "$os_type")${NC}"
            fi

            if command -v cargo &>/dev/null; then
                echo -e "    ${GREEN}✓${NC} cargo"
            else
                echo -e "    ${YELLOW}○${NC} cargo (installed with rust)"
            fi
            ;;

        go)
            if command -v go &>/dev/null; then
                local ver=$(go version 2>/dev/null | awk '{print $3}' | sed 's/go//')
                echo -e "    ${GREEN}✓${NC} go ($ver)"
            else
                echo -e "    ${YELLOW}○${NC} go"
                echo -e "      ${DIM}$(_007_install_cmd go "$os_type")${NC}"
            fi
            ;;

        ruby)
            if command -v ruby &>/dev/null; then
                local ver=$(ruby --version 2>/dev/null | awk '{print $2}')
                echo -e "    ${GREEN}✓${NC} ruby ($ver)"
            else
                echo -e "    ${YELLOW}○${NC} ruby"
            fi

            if command -v bundler &>/dev/null; then
                echo -e "    ${GREEN}✓${NC} bundler"
            elif [[ -f "Gemfile" ]]; then
                echo -e "    ${YELLOW}○${NC} bundler"
                echo -e "      ${DIM}gem install bundler${NC}"
            fi
            ;;
    esac

    echo ""
}

# Show project-specific dependencies (header printed only once)
_007_show_project_dependencies() {
    local deps_found=()

    # Collect all dependency info first
    if [[ -f "package.json" ]]; then
        local dep_count=$(jq '(.dependencies // {}) | keys | length' package.json 2>/dev/null || echo 0)
        local dev_count=$(jq '(.devDependencies // {}) | keys | length' package.json 2>/dev/null || echo 0)
        if [[ "$dep_count" -gt 0 || "$dev_count" -gt 0 ]]; then
            deps_found+=("package.json:$dep_count:$dev_count:node_modules")
        fi
    fi

    if [[ -f "requirements.txt" ]]; then
        local dep_count=$(grep -v '^#' requirements.txt 2>/dev/null | grep -c -v '^$' || echo 0)
        deps_found+=("requirements.txt:$dep_count:0:venv")
    fi

    if [[ -f "Cargo.toml" ]]; then
        deps_found+=("Cargo.toml:rust:0:Cargo.lock")
    fi

    if [[ -f "go.mod" ]]; then
        deps_found+=("go.mod:go:0:go.sum")
    fi

    # Only print if we found dependencies
    [[ ${#deps_found[@]} -eq 0 ]] && return

    echo -e "${CYAN}  PROJECT DEPENDENCIES:${NC}"
    echo ""

    for dep_info in "${deps_found[@]}"; do
        IFS=':' read -r file count1 count2 check_target <<< "$dep_info"

        case "$file" in
            package.json)
                echo -e "    ${DIM}package.json:${NC} $count1 dependencies, $count2 devDependencies"
                if [[ -d "node_modules" ]]; then
                    echo -e "    ${GREEN}✓${NC} node_modules exists"
                else
                    echo -e "    ${YELLOW}○${NC} Run: ${BOLD}npm install${NC}"
                fi
                ;;
            requirements.txt)
                echo -e "    ${DIM}requirements.txt:${NC} ~$count1 packages"
                if [[ -d "venv" ]] || [[ -d ".venv" ]]; then
                    echo -e "    ${GREEN}✓${NC} Virtual environment exists"
                else
                    echo -e "    ${YELLOW}○${NC} Run: ${BOLD}python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt${NC}"
                fi
                ;;
            Cargo.toml)
                echo -e "    ${DIM}Cargo.toml:${NC} Rust project"
                if [[ -f "Cargo.lock" ]]; then
                    echo -e "    ${GREEN}✓${NC} Cargo.lock exists"
                else
                    echo -e "    ${YELLOW}○${NC} Run: ${BOLD}cargo build${NC}"
                fi
                ;;
            go.mod)
                echo -e "    ${DIM}go.mod:${NC} Go project"
                if [[ -f "go.sum" ]]; then
                    echo -e "    ${GREEN}✓${NC} go.sum exists"
                else
                    echo -e "    ${YELLOW}○${NC} Run: ${BOLD}go mod tidy${NC}"
                fi
                ;;
        esac
    done

    echo ""
}

# Show quick install commands
_007_show_quick_install() {
    local os_type="$1"

    # Only show if something is missing
    if [[ $_007_REQUIRED_INSTALLED -eq $_007_REQUIRED_TOTAL ]]; then
        return
    fi

    echo -e "${CYAN}  QUICK INSTALL:${NC}"
    echo ""

    case "$os_type" in
        macos)
            echo -e "    ${DIM}# All required tools:${NC}"
            echo -e "    ${BOLD}brew install git jq node${NC}"
            echo -e "    ${BOLD}npm install -g @anthropic-ai/claude-code task-master-ai${NC}"
            ;;
        debian)
            echo -e "    ${DIM}# All required tools:${NC}"
            echo -e "    ${BOLD}sudo apt update && sudo apt install -y git jq${NC}"
            echo -e "    ${BOLD}curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -${NC}"
            echo -e "    ${BOLD}sudo apt install -y nodejs${NC}"
            echo -e "    ${BOLD}npm install -g @anthropic-ai/claude-code task-master-ai${NC}"
            ;;
        arch)
            echo -e "    ${DIM}# All required tools:${NC}"
            echo -e "    ${BOLD}sudo pacman -S git jq nodejs npm${NC}"
            echo -e "    ${BOLD}npm install -g @anthropic-ai/claude-code task-master-ai${NC}"
            ;;
        windows)
            echo -e "    ${DIM}# All required tools (PowerShell as Admin):${NC}"
            echo -e "    ${BOLD}winget install Git.Git jqlang.jq OpenJS.NodeJS.LTS${NC}"
            echo -e "    ${BOLD}npm install -g @anthropic-ai/claude-code task-master-ai${NC}"
            ;;
        *)
            echo -e "    ${DIM}See tool-specific install commands above${NC}"
            ;;
    esac

    echo ""
}

# Show airgapped environment note
_007_show_airgap_note() {
    echo -e "${DIM}  ┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${DIM}  │ ${NC}${YELLOW}Airgapped Environment?${NC}${DIM}                                  │${NC}"
    echo -e "${DIM}  │                                                         │${NC}"
    echo -e "${DIM}  │ Download these packages on a connected machine:         │${NC}"
    echo -e "${DIM}  │   npm pack @anthropic-ai/claude-code                    │${NC}"
    echo -e "${DIM}  │   npm pack task-master-ai                               │${NC}"
    echo -e "${DIM}  │                                                         │${NC}"
    echo -e "${DIM}  │ Transfer .tgz files and install with:                   │${NC}"
    echo -e "${DIM}  │   npm install -g ./anthropic-ai-claude-code-*.tgz       │${NC}"
    echo -e "${DIM}  │   npm install -g ./task-master-ai-*.tgz                 │${NC}"
    echo -e "${DIM}  └─────────────────────────────────────────────────────────┘${NC}"
    echo ""
}

# Show status summary
_007_show_summary() {
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Required status
    if [[ $_007_REQUIRED_INSTALLED -eq $_007_REQUIRED_TOTAL ]]; then
        echo -e "  ${GREEN}✓${NC} Required: ${BOLD}$_007_REQUIRED_INSTALLED/$_007_REQUIRED_TOTAL${NC} installed"
    else
        local missing=$(($_007_REQUIRED_TOTAL - $_007_REQUIRED_INSTALLED))
        echo -e "  ${RED}✗${NC} Required: ${BOLD}$_007_REQUIRED_INSTALLED/$_007_REQUIRED_TOTAL${NC} installed (${RED}$missing missing${NC})"
    fi

    # Recommended status
    echo -e "  ${DIM}○${NC} Recommended: ${BOLD}$_007_RECOMMENDED_INSTALLED/$_007_RECOMMENDED_TOTAL${NC} installed"
    echo ""
}

# Record environment status to context
_007_record_context() {
    local config_file="$1"

    local missing=$(($_007_REQUIRED_TOTAL - $_007_REQUIRED_INSTALLED))
    local status_msg="Environment: $_007_REQUIRED_INSTALLED/$_007_REQUIRED_TOTAL required tools"

    if [[ $missing -gt 0 ]]; then
        status_msg+=", $missing missing"
    else
        status_msg+=", all present"
    fi

    atomic_context_decision "$status_msg" "environment"

    # Update config with environment status
    local tmp=$(atomic_mktemp)
    jq --argjson req_total "$_007_REQUIRED_TOTAL" \
       --argjson req_installed "$_007_REQUIRED_INSTALLED" \
       --argjson rec_total "$_007_RECOMMENDED_TOTAL" \
       --argjson rec_installed "$_007_RECOMMENDED_INSTALLED" \
       '.environment = {
           "required_total": $req_total,
           "required_installed": $req_installed,
           "recommended_total": $rec_total,
           "recommended_installed": $rec_installed,
           "checked_at": (now | todate)
       }' "$config_file" > "$tmp" && mv "$tmp" "$config_file"
}
