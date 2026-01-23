#!/bin/bash
#
# Task 006: Environment Setup
# List required/recommended dependencies and give user opportunity to install
#
# Features:
#   - Auto-detects OS for relevant install commands
#   - Version checking (node >= 18, etc.)
#   - Project-specific dependencies from package.json, requirements.txt, etc.
#   - Language-specific tools based on inferred project type
#   - Status summary with counts
#   - Records environment status to context
#

# Global counters for summary
_006_REQUIRED_TOTAL=0
_006_REQUIRED_INSTALLED=0
_006_RECOMMENDED_TOTAL=0
_006_RECOMMENDED_INSTALLED=0

task_006_environment_setup() {
    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"
    local manifest_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/material-manifest.json"

    atomic_step "Environment Setup"

    # Reset counters
    _006_REQUIRED_TOTAL=0
    _006_REQUIRED_INSTALLED=0
    _006_RECOMMENDED_TOTAL=0
    _006_RECOMMENDED_INSTALLED=0

    echo ""
    echo -e "${DIM}  ┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${DIM}  │ Before proceeding, ensure you have the required tools.  │${NC}"
    echo -e "${DIM}  │                                                         │${NC}"
    echo -e "${DIM}  │ Open another terminal to install any missing tools,     │${NC}"
    echo -e "${DIM}  │ then return here and press Enter to continue.           │${NC}"
    echo -e "${DIM}  └─────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # Detect OS
    local os_type=$(_006_detect_os)
    echo -e "  ${DIM}Detected OS: $os_type${NC}"
    echo ""

    # Core required tools
    _006_show_required_tools "$os_type"

    # Recommended tools
    _006_show_recommended_tools "$os_type"

    # Project-specific dependencies
    local project_lang=$(jq -r '.project.language // "unknown"' "$config_file" 2>/dev/null)
    _006_show_language_tools "$project_lang" "$os_type"

    # Project dependencies from manifest files
    _006_show_project_dependencies

    # Quick install commands
    _006_show_quick_install "$os_type"

    # Status summary
    _006_show_summary

    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${YELLOW}Open another terminal to install missing tools.${NC}"
    echo -e "  ${YELLOW}When ready, return here and press Enter to validate.${NC}"
    echo ""

    read -p "  Press Enter when ready to continue... " _

    # Record to context
    _006_record_context "$config_file"

    atomic_success "Ready for environment validation"
    return 0
}

# Detect operating system
_006_detect_os() {
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
_006_install_cmd() {
    local tool="$1"
    local os_type="$2"

    case "$tool" in
        git)
            case "$os_type" in
                macos) echo "brew install git" ;;
                debian) echo "sudo apt install git" ;;
                redhat) echo "sudo dnf install git" ;;
                arch) echo "sudo pacman -S git" ;;
                *) echo "https://git-scm.com/downloads" ;;
            esac
            ;;
        jq)
            case "$os_type" in
                macos) echo "brew install jq" ;;
                debian) echo "sudo apt install jq" ;;
                redhat) echo "sudo dnf install jq" ;;
                arch) echo "sudo pacman -S jq" ;;
                *) echo "https://jqlang.github.io/jq/download/" ;;
            esac
            ;;
        node)
            case "$os_type" in
                macos) echo "brew install node" ;;
                debian) echo "curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install nodejs" ;;
                redhat) echo "curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash - && sudo dnf install nodejs" ;;
                arch) echo "sudo pacman -S nodejs npm" ;;
                *) echo "https://nodejs.org/" ;;
            esac
            ;;
        claude)
            echo "npm install -g @anthropic-ai/claude-code"
            ;;
        gh)
            case "$os_type" in
                macos) echo "brew install gh" ;;
                debian) echo "sudo apt install gh" ;;
                redhat) echo "sudo dnf install gh" ;;
                arch) echo "sudo pacman -S github-cli" ;;
                *) echo "https://cli.github.com/" ;;
            esac
            ;;
        docker)
            case "$os_type" in
                macos) echo "brew install --cask docker" ;;
                debian) echo "sudo apt install docker.io" ;;
                *) echo "https://docs.docker.com/get-docker/" ;;
            esac
            ;;
        python)
            case "$os_type" in
                macos) echo "brew install python" ;;
                debian) echo "sudo apt install python3 python3-pip python3-venv" ;;
                redhat) echo "sudo dnf install python3 python3-pip" ;;
                arch) echo "sudo pacman -S python python-pip" ;;
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
                *) echo "https://go.dev/dl/" ;;
            esac
            ;;
        *)
            echo ""
            ;;
    esac
}

# Check version meets minimum
_006_check_version() {
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
_006_show_required_tools() {
    local os_type="$1"

    echo -e "${CYAN}  REQUIRED TOOLS:${NC}"
    echo ""

    # git
    ((_006_REQUIRED_TOTAL++))
    if command -v git &>/dev/null; then
        local ver=$(git --version 2>/dev/null | awk '{print $3}')
        echo -e "    ${GREEN}✓${NC} git ($ver)"
        ((_006_REQUIRED_INSTALLED++))
    else
        echo -e "    ${RED}✗${NC} git - ${BOLD}REQUIRED${NC}"
        echo -e "      ${DIM}$(_006_install_cmd git "$os_type")${NC}"
    fi

    # jq
    ((_006_REQUIRED_TOTAL++))
    if command -v jq &>/dev/null; then
        local ver=$(jq --version 2>/dev/null | sed 's/jq-//')
        echo -e "    ${GREEN}✓${NC} jq ($ver)"
        ((_006_REQUIRED_INSTALLED++))
    else
        echo -e "    ${RED}✗${NC} jq - ${BOLD}REQUIRED${NC}"
        echo -e "      ${DIM}$(_006_install_cmd jq "$os_type")${NC}"
    fi

    # node (with version check)
    ((_006_REQUIRED_TOTAL++))
    if command -v node &>/dev/null; then
        local ver=$(node --version 2>/dev/null | sed 's/v//')
        local major_ver=$(echo "$ver" | cut -d. -f1)
        if [[ "$major_ver" -ge 18 ]]; then
            echo -e "    ${GREEN}✓${NC} node (v$ver)"
            ((_006_REQUIRED_INSTALLED++))
        else
            echo -e "    ${YELLOW}!${NC} node (v$ver) - ${BOLD}v18+ required${NC}"
            echo -e "      ${DIM}$(_006_install_cmd node "$os_type")${NC}"
        fi
    else
        echo -e "    ${RED}✗${NC} node - ${BOLD}REQUIRED${NC} (v18+)"
        echo -e "      ${DIM}$(_006_install_cmd node "$os_type")${NC}"
    fi

    # claude CLI
    ((_006_REQUIRED_TOTAL++))
    if command -v claude &>/dev/null; then
        local ver=$(claude --version 2>/dev/null | head -1 || echo "installed")
        echo -e "    ${GREEN}✓${NC} claude CLI ($ver)"
        ((_006_REQUIRED_INSTALLED++))
    else
        echo -e "    ${RED}✗${NC} claude CLI - ${BOLD}REQUIRED${NC}"
        echo -e "      ${DIM}$(_006_install_cmd claude "$os_type")${NC}"
    fi

    echo ""
}

# Show recommended tools
_006_show_recommended_tools() {
    local os_type="$1"

    echo -e "${CYAN}  RECOMMENDED TOOLS:${NC}"
    echo ""

    # task-master-ai
    ((_006_RECOMMENDED_TOTAL++))
    if command -v task-master &>/dev/null || npx task-master-ai --version &>/dev/null 2>&1; then
        echo -e "    ${GREEN}✓${NC} task-master-ai"
        ((_006_RECOMMENDED_INSTALLED++))
    else
        echo -e "    ${YELLOW}○${NC} task-master-ai - Task decomposition"
        echo -e "      ${DIM}npm install -g task-master-ai${NC}"
    fi

    # gh
    ((_006_RECOMMENDED_TOTAL++))
    if command -v gh &>/dev/null; then
        local ver=$(gh --version 2>/dev/null | head -1 | awk '{print $3}')
        echo -e "    ${GREEN}✓${NC} gh ($ver)"
        ((_006_RECOMMENDED_INSTALLED++))
    else
        echo -e "    ${YELLOW}○${NC} gh (GitHub CLI) - PR/issue management"
        echo -e "      ${DIM}$(_006_install_cmd gh "$os_type")${NC}"
    fi

    # docker
    ((_006_RECOMMENDED_TOTAL++))
    if command -v docker &>/dev/null; then
        local ver=$(docker --version 2>/dev/null | awk '{print $3}' | sed 's/,//')
        echo -e "    ${GREEN}✓${NC} docker ($ver)"
        ((_006_RECOMMENDED_INSTALLED++))
    else
        echo -e "    ${YELLOW}○${NC} docker - Containerized deployment"
        echo -e "      ${DIM}$(_006_install_cmd docker "$os_type")${NC}"
    fi

    echo ""
}

# Show language-specific tools
_006_show_language_tools() {
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
                echo -e "      ${DIM}$(_006_install_cmd python "$os_type")${NC}"
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
                echo -e "      ${DIM}$(_006_install_cmd rust "$os_type")${NC}"
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
                echo -e "      ${DIM}$(_006_install_cmd go "$os_type")${NC}"
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

# Show project-specific dependencies
_006_show_project_dependencies() {
    local has_deps=false

    # Check package.json
    if [[ -f "package.json" ]]; then
        local dep_count=$(jq '(.dependencies // {}) | keys | length' package.json 2>/dev/null || echo 0)
        local dev_count=$(jq '(.devDependencies // {}) | keys | length' package.json 2>/dev/null || echo 0)
        if [[ "$dep_count" -gt 0 || "$dev_count" -gt 0 ]]; then
            has_deps=true
            echo -e "${CYAN}  PROJECT DEPENDENCIES:${NC}"
            echo ""
            echo -e "    ${DIM}package.json:${NC} $dep_count dependencies, $dev_count devDependencies"
            if [[ -d "node_modules" ]]; then
                echo -e "    ${GREEN}✓${NC} node_modules exists"
            else
                echo -e "    ${YELLOW}○${NC} Run: ${BOLD}npm install${NC}"
            fi
            echo ""
        fi
    fi

    # Check requirements.txt
    if [[ -f "requirements.txt" ]]; then
        local dep_count=$(grep -v '^#' requirements.txt 2>/dev/null | grep -c -v '^$' || echo 0)
        has_deps=true
        echo -e "${CYAN}  PROJECT DEPENDENCIES:${NC}"
        echo ""
        echo -e "    ${DIM}requirements.txt:${NC} ~$dep_count packages"
        if [[ -d "venv" ]] || [[ -d ".venv" ]]; then
            echo -e "    ${GREEN}✓${NC} Virtual environment exists"
        else
            echo -e "    ${YELLOW}○${NC} Run: ${BOLD}python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt${NC}"
        fi
        echo ""
    fi

    # Check Cargo.toml
    if [[ -f "Cargo.toml" ]]; then
        local dep_count=$(grep -c '^\[' Cargo.toml 2>/dev/null || echo 0)
        has_deps=true
        echo -e "${CYAN}  PROJECT DEPENDENCIES:${NC}"
        echo ""
        echo -e "    ${DIM}Cargo.toml:${NC} Rust project"
        if [[ -f "Cargo.lock" ]]; then
            echo -e "    ${GREEN}✓${NC} Cargo.lock exists"
        else
            echo -e "    ${YELLOW}○${NC} Run: ${BOLD}cargo build${NC}"
        fi
        echo ""
    fi

    # Check go.mod
    if [[ -f "go.mod" ]]; then
        has_deps=true
        echo -e "${CYAN}  PROJECT DEPENDENCIES:${NC}"
        echo ""
        echo -e "    ${DIM}go.mod:${NC} Go project"
        if [[ -f "go.sum" ]]; then
            echo -e "    ${GREEN}✓${NC} go.sum exists"
        else
            echo -e "    ${YELLOW}○${NC} Run: ${BOLD}go mod tidy${NC}"
        fi
        echo ""
    fi
}

# Show quick install commands
_006_show_quick_install() {
    local os_type="$1"

    # Only show if something is missing
    if [[ $_006_REQUIRED_INSTALLED -eq $_006_REQUIRED_TOTAL ]]; then
        return
    fi

    echo -e "${CYAN}  QUICK INSTALL:${NC}"
    echo ""

    case "$os_type" in
        macos)
            echo -e "    ${DIM}# All required tools:${NC}"
            echo -e "    ${BOLD}brew install git jq node && npm install -g @anthropic-ai/claude-code${NC}"
            echo ""
            echo -e "    ${DIM}# Recommended extras:${NC}"
            echo -e "    ${BOLD}npm install -g task-master-ai && brew install gh${NC}"
            ;;
        debian)
            echo -e "    ${DIM}# All required tools:${NC}"
            echo -e "    ${BOLD}sudo apt update && sudo apt install -y git jq${NC}"
            echo -e "    ${BOLD}curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -${NC}"
            echo -e "    ${BOLD}sudo apt install -y nodejs && npm install -g @anthropic-ai/claude-code${NC}"
            ;;
        arch)
            echo -e "    ${DIM}# All required tools:${NC}"
            echo -e "    ${BOLD}sudo pacman -S git jq nodejs npm && npm install -g @anthropic-ai/claude-code${NC}"
            ;;
        *)
            echo -e "    ${DIM}See tool-specific install commands above${NC}"
            ;;
    esac

    echo ""
}

# Show status summary
_006_show_summary() {
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Required status
    if [[ $_006_REQUIRED_INSTALLED -eq $_006_REQUIRED_TOTAL ]]; then
        echo -e "  ${GREEN}✓${NC} Required: ${BOLD}$_006_REQUIRED_INSTALLED/$_006_REQUIRED_TOTAL${NC} installed"
    else
        local missing=$(($_006_REQUIRED_TOTAL - $_006_REQUIRED_INSTALLED))
        echo -e "  ${RED}✗${NC} Required: ${BOLD}$_006_REQUIRED_INSTALLED/$_006_REQUIRED_TOTAL${NC} installed (${RED}$missing missing${NC})"
    fi

    # Recommended status
    echo -e "  ${DIM}○${NC} Recommended: ${BOLD}$_006_RECOMMENDED_INSTALLED/$_006_RECOMMENDED_TOTAL${NC} installed"
    echo ""
}

# Record environment status to context
_006_record_context() {
    local config_file="$1"

    local missing=$(($_006_REQUIRED_TOTAL - $_006_REQUIRED_INSTALLED))
    local status_msg="Environment: $_006_REQUIRED_INSTALLED/$_006_REQUIRED_TOTAL required tools"

    if [[ $missing -gt 0 ]]; then
        status_msg+=", $missing missing"
    else
        status_msg+=", all present"
    fi

    atomic_context_decision "$status_msg" "environment"

    # Update config with environment status
    local tmp=$(mktemp)
    jq --argjson req_total "$_006_REQUIRED_TOTAL" \
       --argjson req_installed "$_006_REQUIRED_INSTALLED" \
       --argjson rec_total "$_006_RECOMMENDED_TOTAL" \
       --argjson rec_installed "$_006_RECOMMENDED_INSTALLED" \
       '.environment = {
           "required_total": $req_total,
           "required_installed": $req_installed,
           "recommended_total": $rec_total,
           "recommended_installed": $rec_installed,
           "checked_at": (now | todate)
       }' "$config_file" > "$tmp" && mv "$tmp" "$config_file"
}
