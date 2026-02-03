#!/usr/bin/env bash
#
# Install Git hooks for automatic syncing
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOKS_DIR="$ROOT_DIR/.git/hooks"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${CYAN}Installing Git hooks...${NC}"
echo ""

# Ensure hooks directory exists
mkdir -p "$HOOKS_DIR"

# Post-commit hook - auto-sync to test-project
cat > "$HOOKS_DIR/post-commit" << 'HOOK'
#!/bin/bash
#
# Post-commit hook: Auto-sync to test-project
#

SCRIPT_DIR="$(git rev-parse --show-toplevel)/scripts"

if [[ -f "$SCRIPT_DIR/sync-to-test-project.sh" ]]; then
    echo ""
    echo "🔄 Auto-syncing to test-project..."
    "$SCRIPT_DIR/sync-to-test-project.sh" --quiet 2>/dev/null || true
fi
HOOK

chmod +x "$HOOKS_DIR/post-commit"
echo -e "${GREEN}✓${NC} Installed post-commit hook (auto-sync after commit)"

# Post-merge hook - auto-sync after pull
cat > "$HOOKS_DIR/post-merge" << 'HOOK'
#!/bin/bash
#
# Post-merge hook: Auto-sync to test-project after git pull
#

SCRIPT_DIR="$(git rev-parse --show-toplevel)/scripts"

if [[ -f "$SCRIPT_DIR/sync-to-test-project.sh" ]]; then
    echo ""
    echo "🔄 Auto-syncing to test-project..."
    "$SCRIPT_DIR/sync-to-test-project.sh" --quiet 2>/dev/null || true
fi
HOOK

chmod +x "$HOOKS_DIR/post-merge"
echo -e "${GREEN}✓${NC} Installed post-merge hook (auto-sync after git pull)"

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}Hooks installed successfully!${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Git will now automatically sync to test-project:"
echo "  • After every commit"
echo "  • After every git pull"
echo ""
echo "To disable: rm .git/hooks/post-commit .git/hooks/post-merge"
echo ""
