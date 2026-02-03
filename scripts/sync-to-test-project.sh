#!/usr/bin/env bash
#
# Sync ATOMIC-CLAUDE to test-project
# Keeps code in sync while preserving test-project state
#

set -euo pipefail

# Parse arguments
QUIET_MODE=false
if [[ "${1:-}" == "--quiet" ]]; then
    QUIET_MODE=true
fi

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

SOURCE_DIR="/Users/jamesterbeest/dev/atomic-claude"
TARGET_DIR="/Users/jamesterbeest/dev/test-project/ATOMIC-CLAUDE"

if [[ "$QUIET_MODE" != "true" ]]; then
    echo ""
    echo -e "${CYAN}${BOLD}Syncing ATOMIC-CLAUDE → test-project${NC}"
    echo ""
fi

# Verify directories exist
if [[ ! -d "$SOURCE_DIR" ]]; then
    echo -e "${RED}✗${NC} Source directory not found: $SOURCE_DIR"
    exit 1
fi

if [[ ! -d "$TARGET_DIR" ]]; then
    echo -e "${RED}✗${NC} Target directory not found: $TARGET_DIR"
    exit 1
fi

# Files/directories to sync (code only, not state)
SYNC_ITEMS=(
    "lib/"
    "phases/"
    "config/"
    "skills/"
    "agents/"
    "audits/"
    "tasks-dashboard/"
    "scripts/"
    "docs/"
    "initialization/"
    "tools/"
    "main.sh"
    "pipeline"
    "README.md"
    "CLAUDE.md"
    "PHASES.md"
    "LICENSE"
)

# Directories to EXCLUDE (state, logs, outputs)
EXCLUDE_PATTERNS=(
    ".claude"
    ".state"
    ".outputs"
    ".logs"
    "node_modules"
    ".git"
    ".DS_Store"
    "*.log"
)

# Build rsync exclude arguments
EXCLUDE_ARGS=""
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    EXCLUDE_ARGS="$EXCLUDE_ARGS --exclude=$pattern"
done

if [[ "$QUIET_MODE" != "true" ]]; then
    echo -e "${DIM}Source: $SOURCE_DIR${NC}"
    echo -e "${DIM}Target: $TARGET_DIR${NC}"
    echo ""
fi

# Sync each item
SYNCED_COUNT=0
FAILED_COUNT=0

for item in "${SYNC_ITEMS[@]}"; do
    SOURCE_PATH="$SOURCE_DIR/$item"

    if [[ ! -e "$SOURCE_PATH" ]]; then
        echo -e "${YELLOW}⊘${NC} Skipping $item (not found)"
        continue
    fi

    if [[ -d "$SOURCE_PATH" ]]; then
        # Directory - use rsync for efficiency
        # Ensure target directory exists
        mkdir -p "$TARGET_DIR/$item"
        if rsync -a --delete $EXCLUDE_ARGS "$SOURCE_PATH" "$TARGET_DIR/$item" 2>/dev/null; then
            echo -e "${GREEN}✓${NC} Synced directory: $item"
            ((SYNCED_COUNT++))
        else
            echo -e "${RED}✗${NC} Failed to sync: $item"
            ((FAILED_COUNT++))
        fi
    else
        # File - direct copy
        if cp "$SOURCE_PATH" "$TARGET_DIR/$item" 2>/dev/null; then
            echo -e "${GREEN}✓${NC} Synced file: $item"
            ((SYNCED_COUNT++))
        else
            echo -e "${RED}✗${NC} Failed to sync: $item"
            ((FAILED_COUNT++))
        fi
    fi
done

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Synced: $SYNCED_COUNT items${NC}"
if [[ $FAILED_COUNT -gt 0 ]]; then
    echo -e "${RED}✗ Failed: $FAILED_COUNT items${NC}"
fi
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Show what was preserved
echo -e "${BOLD}Preserved in test-project:${NC}"
echo -e "${DIM}  • .claude/     (task state)${NC}"
echo -e "${DIM}  • .state/      (runtime state)${NC}"
echo -e "${DIM}  • .outputs/    (phase outputs)${NC}"
echo -e "${DIM}  • .logs/       (invocation logs)${NC}"
echo ""

# Check for uncommitted changes in source
cd "$SOURCE_DIR"
if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
    echo -e "${YELLOW}⚠${NC}  You have uncommitted changes in atomic-claude"
    echo -e "${DIM}  Run 'git status' to see what's changed${NC}"
    echo ""
fi

echo -e "${CYAN}Next step:${NC}"
echo -e "  cd /Users/jamesterbeest/dev/test-project"
echo -e "  ./ATOMIC-CLAUDE/main.sh run 0"
echo ""
