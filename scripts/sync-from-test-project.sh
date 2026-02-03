#!/usr/bin/env bash
#
# Sync changes FROM test-project back to ATOMIC-CLAUDE
# Use this if you made fixes/changes during testing
#

set -euo pipefail

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

SOURCE_DIR="/Users/jamesterbeest/dev/test-project/ATOMIC-CLAUDE"
TARGET_DIR="/Users/jamesterbeest/dev/atomic-claude"

echo ""
echo -e "${CYAN}${BOLD}Syncing test-project → ATOMIC-CLAUDE${NC}"
echo ""
echo -e "${YELLOW}⚠  WARNING: This will overwrite the main ATOMIC-CLAUDE repo!${NC}"
echo ""

# Show git status in target
cd "$TARGET_DIR"
if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
    echo -e "${RED}✗${NC} You have uncommitted changes in atomic-claude"
    echo ""
    git status --short
    echo ""
    read -e -p "Continue anyway? [y/N]: " confirm
    if [[ "${confirm,,}" != "y" ]]; then
        echo "Aborted."
        exit 1
    fi
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

# Files/directories to sync back
SYNC_ITEMS=(
    "lib/"
    "phases/"
    "config/"
    "skills/"
    "tasks-dashboard/"
    "scripts/"
    "main.sh"
)

echo -e "${DIM}Source: $SOURCE_DIR${NC}"
echo -e "${DIM}Target: $TARGET_DIR${NC}"
echo ""

# Sync each item
SYNCED_COUNT=0

for item in "${SYNC_ITEMS[@]}"; do
    SOURCE_PATH="$SOURCE_DIR/$item"

    if [[ ! -e "$SOURCE_PATH" ]]; then
        echo -e "${YELLOW}⊘${NC} Skipping $item (not found)"
        continue
    fi

    if [[ -d "$SOURCE_PATH" ]]; then
        # Directory - use rsync
        rsync -a --delete --exclude=".git" --exclude="node_modules" "$SOURCE_PATH" "$TARGET_DIR/$(dirname "$item")"
        echo -e "${GREEN}✓${NC} Synced directory: $item"
    else
        # File
        cp "$SOURCE_PATH" "$TARGET_DIR/$item"
        echo -e "${GREEN}✓${NC} Synced file: $item"
    fi
    ((SYNCED_COUNT++))
done

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Synced: $SYNCED_COUNT items${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cd "$TARGET_DIR"
echo -e "${BOLD}Changed files in atomic-claude:${NC}"
echo ""
git status --short
echo ""

echo -e "${CYAN}Next steps:${NC}"
echo -e "  cd $TARGET_DIR"
echo -e "  git diff           # Review changes"
echo -e "  git add -A         # Stage changes"
echo -e "  git commit -m '...'  # Commit"
echo ""
