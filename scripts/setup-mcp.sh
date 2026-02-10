#!/usr/bin/env bash
#
# MCP Server Setup Script
# Installs and configures Model Context Protocol servers for atomic-claude2
#
# Usage:
#   ./scripts/setup-mcp.sh                # Interactive mode
#   ./scripts/setup-mcp.sh --all         # Install all recommended MCPs
#   ./scripts/setup-mcp.sh --minimal     # Install only core MCPs
#

set -euo pipefail

# Color codes
BOLD='\033[1m'
DIM='\033[2m'
GREEN='\033[32m'
CYAN='\033[36m'
YELLOW='\033[33m'
RED='\033[31m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ATOMIC_ROOT="$(dirname "$SCRIPT_DIR")"
MCP_CONFIG="$ATOMIC_ROOT/.mcp.json"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

log_info() {
    echo -e "${CYAN}ℹ${NC}  $1"
}

log_success() {
    echo -e "${GREEN}✓${NC}  $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC}  $1"
}

log_error() {
    echo -e "${RED}✗${NC}  $1"
}

# Check if npm is installed
check_npm() {
    if ! command -v npm &>/dev/null; then
        log_error "npm not found. Please install Node.js 18+ first."
        echo ""
        echo "  macOS:   brew install node"
        echo "  Ubuntu:  curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -"
        echo "           sudo apt-get install -y nodejs"
        echo ""
        exit 1
    fi

    local node_version
    node_version=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
    if [[ $node_version -lt 18 ]]; then
        log_warn "Node.js version $node_version detected. MCP requires Node.js 18+"
        return 1
    fi

    return 0
}

# Install MCP server
install_mcp() {
    local package="$1"
    local name="$2"

    log_info "Installing $name..."

    if npm install -g "$package" >/dev/null 2>&1; then
        log_success "$name installed"
        return 0
    else
        log_error "$name installation failed"
        return 1
    fi
}

# Check if MCP server is installed
is_installed() {
    local command="$1"
    command -v "$command" &>/dev/null
}

# Create .mcp.json configuration
create_mcp_config() {
    local servers="$1"

    cat > "$MCP_CONFIG" <<EOF
{
  "mcpServers": {
$servers
  }
}
EOF

    log_success "Created .mcp.json configuration"
}

# =============================================================================
# MCP SERVER DEFINITIONS
# =============================================================================

# Core servers (required)
install_core_mcps() {
    local installed=0
    local total=2

    echo ""
    echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  Core MCP Servers (Required)${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # GitHub MCP
    if is_installed "mcp-server-github"; then
        log_success "GitHub MCP already installed"
        ((installed++)) || true
    else
        if install_mcp "@modelcontextprotocol/server-github" "GitHub MCP"; then
            ((installed++)) || true
        fi
    fi

    # Filesystem MCP
    if is_installed "mcp-server-filesystem"; then
        log_success "Filesystem MCP already installed"
        ((installed++)) || true
    else
        if install_mcp "@modelcontextprotocol/server-filesystem" "Filesystem MCP"; then
            ((installed++)) || true
        fi
    fi

    echo ""
    echo -e "${BOLD}Core MCPs: $installed/$total installed${NC}"

    return 0
}

# Recommended servers (optional but useful)
install_recommended_mcps() {
    local installed=0
    local total=4

    echo ""
    echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  Recommended MCP Servers (Optional)${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Playwright MCP
    if is_installed "mcp-server-playwright"; then
        log_success "Playwright MCP already installed"
        ((installed++)) || true
    else
        if install_mcp "@modelcontextprotocol/server-playwright" "Playwright MCP"; then
            ((installed++)) || true
        fi
    fi

    # Slack MCP
    if is_installed "mcp-server-slack"; then
        log_success "Slack MCP already installed"
        ((installed++)) || true
    else
        if install_mcp "@modelcontextprotocol/server-slack" "Slack MCP"; then
            ((installed++)) || true
        fi
    fi

    # PostgreSQL MCP
    if is_installed "mcp-server-postgres"; then
        log_success "PostgreSQL MCP already installed"
        ((installed++)) || true
    else
        if install_mcp "@modelcontextprotocol/server-postgres" "PostgreSQL MCP"; then
            ((installed++)) || true
        fi
    fi

    # SQLite MCP
    if is_installed "mcp-server-sqlite"; then
        log_success "SQLite MCP already installed"
        ((installed++)) || true
    else
        if install_mcp "@modelcontextprotocol/server-sqlite" "SQLite MCP"; then
            ((installed++)) || true
        fi
    fi

    echo ""
    echo -e "${BOLD}Recommended MCPs: $installed/$total installed${NC}"

    return 0
}

# Interactive MCP selection
interactive_install() {
    echo ""
    echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  MCP Server Installation${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Select MCP servers to install:"
    echo ""
    echo "  [1] Core only (GitHub + Filesystem) - Required"
    echo "  [2] Core + Recommended (+ Playwright, Slack, PostgreSQL, SQLite)"
    echo "  [3] Custom selection"
    echo "  [4] Skip (I'll install manually later)"
    echo ""

    read -e -p "Select option [1-4]: " choice

    case "$choice" in
        1)
            install_core_mcps
            ;;
        2)
            install_core_mcps
            install_recommended_mcps
            ;;
        3)
            log_info "Custom selection not yet implemented"
            log_info "Please run with --minimal or --all for now"
            exit 1
            ;;
        4)
            log_info "Skipping MCP installation"
            log_warn "You'll need to install MCPs manually for full functionality"
            exit 0
            ;;
        *)
            log_error "Invalid choice"
            exit 1
            ;;
    esac
}

# Generate .mcp.json configuration
generate_config() {
    echo ""
    echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  Generating MCP Configuration${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    local servers=""

    # Add GitHub if installed
    if is_installed "mcp-server-github"; then
        servers+='    "github": {
      "command": "mcp-server-github",
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }'
    fi

    # Add Filesystem if installed
    if is_installed "mcp-server-filesystem"; then
        [[ -n "$servers" ]] && servers+=','
        servers+='
    "filesystem": {
      "command": "mcp-server-filesystem",
      "args": ["--allowed-paths", "${ATOMIC_ROOT}"]
    }'
    fi

    # Add Playwright if installed
    if is_installed "mcp-server-playwright"; then
        [[ -n "$servers" ]] && servers+=','
        servers+='
    "playwright": {
      "command": "mcp-server-playwright"
    }'
    fi

    # Add Slack if installed
    if is_installed "mcp-server-slack"; then
        [[ -n "$servers" ]] && servers+=','
        servers+='
    "slack": {
      "command": "mcp-server-slack",
      "env": {
        "SLACK_BOT_TOKEN": "${SLACK_BOT_TOKEN}",
        "SLACK_CHANNEL": "${SLACK_CHANNEL}"
      }
    }'
    fi

    # Add PostgreSQL if installed
    if is_installed "mcp-server-postgres"; then
        [[ -n "$servers" ]] && servers+=','
        servers+='
    "postgres": {
      "command": "mcp-server-postgres",
      "env": {
        "DATABASE_URL": "${DATABASE_URL}"
      }
    }'
    fi

    # Add SQLite if installed
    if is_installed "mcp-server-sqlite"; then
        [[ -n "$servers" ]] && servers+=','
        servers+='
    "sqlite": {
      "command": "mcp-server-sqlite",
      "args": ["--database", "${ATOMIC_ROOT}/.state/atomic.db"]
    }'
    fi

    if [[ -n "$servers" ]]; then
        create_mcp_config "$servers"
        echo ""
        log_info "Configuration saved to: $MCP_CONFIG"
    else
        log_warn "No MCP servers installed, skipping configuration"
    fi
}

# Show environment variable requirements
show_env_requirements() {
    echo ""
    echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  Environment Variables Required${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Add these to your .env file:"
    echo ""

    if is_installed "mcp-server-github"; then
        echo -e "${DIM}# GitHub MCP${NC}"
        echo "GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxx"
        echo ""
    fi

    if is_installed "mcp-server-slack"; then
        echo -e "${DIM}# Slack MCP${NC}"
        echo "SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxxxxxxx"
        echo "SLACK_CHANNEL=#atomic-builds"
        echo ""
    fi

    if is_installed "mcp-server-postgres"; then
        echo -e "${DIM}# PostgreSQL MCP${NC}"
        echo "DATABASE_URL=postgresql://user:pass@localhost:5432/dbname"
        echo ""
    fi

    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    echo ""
    echo -e "${BOLD}${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}║${NC}   ${BOLD}ATOMIC CLAUDE - MCP Server Setup${NC}                       ${BOLD}${CYAN}║${NC}"
    echo -e "${BOLD}${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Check npm
    if ! check_npm; then
        exit 1
    fi

    log_success "Node.js $(node --version) detected"
    log_success "npm $(npm --version) detected"

    # Parse arguments
    local mode="interactive"
    if [[ $# -gt 0 ]]; then
        case "$1" in
            --all)
                mode="all"
                ;;
            --minimal)
                mode="minimal"
                ;;
            --help|-h)
                echo "Usage: $0 [--all|--minimal|--help]"
                echo ""
                echo "Options:"
                echo "  --all       Install all recommended MCP servers"
                echo "  --minimal   Install only core MCP servers"
                echo "  --help      Show this help message"
                echo ""
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    fi

    # Execute based on mode
    case "$mode" in
        interactive)
            interactive_install
            ;;
        all)
            install_core_mcps
            install_recommended_mcps
            ;;
        minimal)
            install_core_mcps
            ;;
    esac

    # Generate configuration
    generate_config

    # Show environment requirements
    show_env_requirements

    # Summary
    echo ""
    echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  Setup Complete${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    log_success "MCP servers installed and configured"
    log_info "Configuration: $MCP_CONFIG"
    log_info "Documentation: docs/MCP.md"
    echo ""
    log_warn "Don't forget to add required environment variables to .env"
    echo ""
}

# Run main
main "$@"
