#!/usr/bin/env bash
#
# Atomic Claude Installer
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/turbobeest/atomic-claude/python/install.sh | bash
#   curl -fsSL ... | bash -s -- --full          # Full clone (dev tools, tests, docs)
#   curl -fsSL ... | bash -s -- --no-dashboard  # Skip dashboard (no Node.js needed)
#   curl -fsSL ... | bash -s -- --dir=myproject  # Custom install directory
#
set -euo pipefail

# ─── Configuration ────────────────────────────────────────────────────────────
REPO="https://github.com/turbobeest/atomic-claude.git"
BRANCH="python"
INSTALL_DIR="./atomic-claude"
FULL_CLONE=false
INCLUDE_DASHBOARD=true
CREATE_VENV=true

# ─── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
DIM='\033[2m'
NC='\033[0m'

info()  { echo -e "${CYAN}[info]${NC}  $*"; }
ok()    { echo -e "${GREEN}[ok]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[warn]${NC}  $*"; }
fail()  { echo -e "${RED}[fail]${NC}  $*"; exit 1; }

# ─── Parse Arguments ──────────────────────────────────────────────────────────
for arg in "$@"; do
    case "$arg" in
        --full)           FULL_CLONE=true ;;
        --no-dashboard)   INCLUDE_DASHBOARD=false ;;
        --no-venv)        CREATE_VENV=false ;;
        --dir=*)          INSTALL_DIR="${arg#*=}" ;;
        --branch=*)       BRANCH="${arg#*=}" ;;
        --help|-h)
            echo "Atomic Claude Installer"
            echo ""
            echo "Usage: curl -fsSL .../install.sh | bash -s -- [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --full            Full clone with dev tools, tests, docs (~160MB)"
            echo "  --no-dashboard    Skip dashboard (Node.js not required)"
            echo "  --no-venv         Skip Python venv creation"
            echo "  --dir=<path>      Install directory (default: ./atomic-claude)"
            echo "  --branch=<name>   Git branch (default: python)"
            echo "  --help            Show this help"
            exit 0
            ;;
        *)
            warn "Unknown option: $arg (ignored)"
            ;;
    esac
done

# ─── Banner ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}╔══════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       Atomic Claude Installer        ║${NC}"
echo -e "${CYAN}║   Python SDLC Pipeline Framework     ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════╝${NC}"
echo ""

# ─── Check Prerequisites ─────────────────────────────────────────────────────

# Git >= 2.25 (required for sparse-checkout cone mode)
if ! command -v git &>/dev/null; then
    fail "git is required but not found. Install git and try again."
fi

GIT_VERSION=$(git --version | grep -oP '\d+\.\d+' | head -1)
GIT_MAJOR=$(echo "$GIT_VERSION" | cut -d. -f1)
GIT_MINOR=$(echo "$GIT_VERSION" | cut -d. -f2)
if [[ "$GIT_MAJOR" -lt 2 ]] || { [[ "$GIT_MAJOR" -eq 2 ]] && [[ "$GIT_MINOR" -lt 25 ]]; }; then
    fail "git >= 2.25 required (found $GIT_VERSION). Sparse-checkout needs git 2.25+."
fi
ok "git $GIT_VERSION"

# Python >= 3.9
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PY_VERSION=$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
        PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
        PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
        if [[ "$PY_MAJOR" -ge 3 ]] && [[ "$PY_MINOR" -ge 9 ]]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    fail "Python >= 3.9 required but not found. Install Python 3.9+ and try again."
fi
ok "$PYTHON $PY_VERSION"

# Node.js (optional, for dashboard)
if $INCLUDE_DASHBOARD; then
    if command -v node &>/dev/null && command -v npm &>/dev/null; then
        NODE_VERSION=$(node --version 2>/dev/null || echo "unknown")
        ok "node $NODE_VERSION (dashboard enabled)"
    else
        warn "Node.js not found. Dashboard will be skipped."
        warn "Install Node.js 18+ to enable the web dashboard."
        INCLUDE_DASHBOARD=false
    fi
fi

# ─── Check Install Directory ─────────────────────────────────────────────────
if [[ -d "$INSTALL_DIR" ]]; then
    fail "Directory '$INSTALL_DIR' already exists. Remove it or use --dir=<path>."
fi

# ─── Clone Repository ────────────────────────────────────────────────────────
echo ""

if $FULL_CLONE; then
    info "Full clone (all files including dev tools, tests, docs)..."
    git clone --branch "$BRANCH" "$REPO" "$INSTALL_DIR"
    ok "Cloned full repository"
else
    info "Runtime install (sparse-checkout, pipeline essentials only)..."

    # Blobless partial clone + no checkout (fast — only downloads tree objects)
    git clone --filter=blob:none --no-checkout --branch "$BRANCH" "$REPO" "$INSTALL_DIR"

    cd "$INSTALL_DIR"

    # Configure sparse-checkout in cone mode
    git sparse-checkout init --cone

    # Runtime-essential directories
    # Cone mode: listing agents/expert-agents also includes all root files in agents/
    # (gets agent-manifest.json for free). Same for audits/ root files.
    CONES=(
        core
        phases
        orchestration
        config
        initialization
        agents/expert-agents
        agents/pipeline-agents
        audits/categories
        audits/data
    )

    if $INCLUDE_DASHBOARD; then
        CONES+=( dashboard )
    fi

    git sparse-checkout set "${CONES[@]}"

    # Now checkout — only fetches blobs for sparse-checked-out paths
    git checkout "$BRANCH"

    cd - > /dev/null
    ok "Cloned runtime files (~23MB)"
fi

# ─── Python Environment ──────────────────────────────────────────────────────
cd "$INSTALL_DIR"
echo ""

if $CREATE_VENV; then
    info "Creating Python virtual environment..."
    $PYTHON -m venv .venv

    # Activate venv
    if [[ -f .venv/bin/activate ]]; then
        source .venv/bin/activate
    elif [[ -f .venv/Scripts/activate ]]; then
        source .venv/Scripts/activate
    fi
    ok "Virtual environment created (.venv/)"
fi

info "Installing Python dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
if [[ -f requirements-llm.txt ]]; then
    pip install --quiet -r requirements-llm.txt
fi
ok "Python dependencies installed"

# ─── Environment Configuration ────────────────────────────────────────────────
if [[ ! -f .env ]] && [[ -f .env.example ]]; then
    cp .env.example .env
    ok "Created .env from .env.example"
    warn "Edit .env to configure your LLM provider (API key, etc.)"
fi

# ─── Dashboard Dependencies ──────────────────────────────────────────────────
if $INCLUDE_DASHBOARD && [[ -d dashboard ]]; then
    echo ""
    info "Installing dashboard dependencies..."
    (cd dashboard && npm install --silent 2>/dev/null) && ok "Dashboard dependencies installed" || warn "Dashboard npm install failed (non-critical)"
fi

# ─── Success ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Installation Complete!            ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""
echo "Next steps:"
echo ""
echo "  1. Configure your LLM provider:"
echo -e "     ${DIM}Edit .env and set ANTHROPIC_API_KEY or AWS_PROFILE${NC}"
echo ""
echo "  2. Run the pipeline:"
echo -e "     ${CYAN}cd $INSTALL_DIR${NC}"
if $CREATE_VENV; then
echo -e "     ${CYAN}source .venv/bin/activate${NC}"
fi
echo -e "     ${CYAN}python main.py run 0${NC}"
echo ""
echo "  3. Check status:"
echo -e "     ${CYAN}python main.py status${NC}"
echo ""
if $INCLUDE_DASHBOARD && [[ -d dashboard ]]; then
echo "  4. Start the dashboard:"
echo -e "     ${CYAN}bash dashboard/start-dashboard.sh${NC}"
echo ""
fi
echo "  Update later with: cd $INSTALL_DIR && git pull"
echo ""
