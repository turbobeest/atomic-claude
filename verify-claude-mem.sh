#!/usr/bin/env bash
#
# Claude-Mem Verification Script
# Checks if claude-mem is properly installed and configured for atomic-claude
#

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Status tracking
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNED=0

print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((CHECKS_PASSED++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((CHECKS_FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((CHECKS_WARNED++))
}

print_summary() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  Summary"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  ${GREEN}Passed:${NC}  $CHECKS_PASSED"
    echo -e "  ${RED}Failed:${NC}  $CHECKS_FAILED"
    echo -e "  ${YELLOW}Warnings:${NC} $CHECKS_WARNED"
    echo ""

    if [[ $CHECKS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}✓ Claude-mem is properly installed and configured!${NC}"
        echo ""
        echo "Next steps:"
        echo "  1. Run: ./main.sh run 0"
        echo "  2. Enable memory when prompted"
        echo "  3. Check web UI: http://localhost:37777"
        echo ""
        return 0
    else
        echo -e "${RED}✗ Claude-mem installation incomplete${NC}"
        echo ""
        echo "Please review the failed checks above and follow:"
        echo "  CLAUDE-MEM-INSTALLATION.md"
        echo ""
        return 1
    fi
}

# ============================================================================
# CHECK 1: Claude Code Environment
# ============================================================================

print_header "Check 1: Claude Code Environment"

if [[ -n "${CLAUDECODE:-}" ]]; then
    check_pass "Running inside Claude Code (CLAUDECODE=$CLAUDECODE)"
else
    check_fail "Not running inside Claude Code"
    echo "         This script should be run from within a Claude Code session"
fi

if [[ -n "${CLAUDE_CODE_ENTRYPOINT:-}" ]]; then
    check_pass "Claude Code entrypoint: $CLAUDE_CODE_ENTRYPOINT"
fi

# ============================================================================
# CHECK 2: Claude-Mem Command
# ============================================================================

print_header "Check 2: Claude-Mem Command Availability"

if command -v claude-mem &>/dev/null; then
    check_pass "claude-mem command found in PATH"
    CLAUDE_MEM_VERSION=$(claude-mem --version 2>&1 || echo "unknown")
    echo "         Version: $CLAUDE_MEM_VERSION"
else
    check_fail "claude-mem command not found"
    echo "         Install via: Claude Code Marketplace → claude-mem"
fi

# ============================================================================
# CHECK 3: MCP Skills
# ============================================================================

print_header "Check 3: MCP Skills Availability"

if command -v mem-search &>/dev/null; then
    check_pass "mem-search skill available"
else
    check_fail "mem-search skill not available"
    echo "         Claude-mem MCP server may not be running"
fi

if command -v mem-search-project &>/dev/null; then
    check_pass "mem-search-project skill available"
else
    check_warn "mem-search-project skill not available (optional)"
fi

# ============================================================================
# CHECK 4: Database Files
# ============================================================================

print_header "Check 4: Claude-Mem Database"

DB_SEARCH_PATHS=(
    "$HOME/Library/Application Support/claude-code/claude-mem/"
    "$HOME/.local/share/claude-code/claude-mem/"
    "$HOME/.claude-mem/"
    "$HOME/.config/claude-code/claude-mem/"
    ".//.claude-mem/"
)

DB_FOUND=false
for search_path in "${DB_SEARCH_PATHS[@]}"; do
    if [[ -d "$search_path" ]]; then
        DB_FILES=$(find "$search_path" -name "*.db" 2>/dev/null || true)
        if [[ -n "$DB_FILES" ]]; then
            check_pass "Database found: $search_path"
            echo "$DB_FILES" | while read -r db; do
                SIZE=$(du -h "$db" 2>/dev/null | cut -f1)
                echo "         $db ($SIZE)"
            done
            DB_FOUND=true
            break
        fi
    fi
done

if [[ "$DB_FOUND" == "false" ]]; then
    check_warn "No claude-mem database found yet"
    echo "         Database will be created on first use"
fi

# ============================================================================
# CHECK 5: Web UI
# ============================================================================

print_header "Check 5: Claude-Mem Web UI"

if curl -s --connect-timeout 3 http://localhost:37777 >/dev/null 2>&1; then
    check_pass "Web UI accessible at http://localhost:37777"
    echo "         Open in browser to view memories"
else
    check_fail "Web UI not accessible at http://localhost:37777"
    echo "         Claude-mem MCP server may not be running"

    # Check if something else is using the port
    if lsof -i :37777 2>/dev/null | grep -q LISTEN; then
        echo "         Port 37777 is in use by another process"
    fi
fi

# ============================================================================
# CHECK 6: Atomic-Claude Memory Configuration
# ============================================================================

print_header "Check 6: Atomic-Claude Memory Configuration"

# Check local memory directory
if [[ -d ".state/memory" ]]; then
    check_pass "Local memory directory exists: .state/memory/"
    FILE_COUNT=$(find .state/memory -type f 2>/dev/null | wc -l | tr -d ' ')
    echo "         Contains $FILE_COUNT memory files"
else
    check_warn "Local memory directory not created yet"
    echo "         Will be created when memory is enabled"
fi

# Check memory enabled flag
SECRETS_FILE=".outputs/0-setup/secrets.json"
if [[ -f "$SECRETS_FILE" ]]; then
    MEM_ENABLED=$(jq -r '.memory_enabled // false' "$SECRETS_FILE" 2>/dev/null)
    if [[ "$MEM_ENABLED" == "true" ]]; then
        check_pass "Memory enabled in secrets.json"
    else
        check_warn "Memory not enabled in secrets.json"
        echo "         Run Phase 0 and select memory option"
    fi
else
    check_warn "No secrets.json found (Phase 0 not run yet)"
fi

# Check environment variable
if [[ "${ATOMIC_MEMORY_ENABLED:-}" == "true" ]]; then
    check_pass "ATOMIC_MEMORY_ENABLED=true in environment"
else
    check_warn "ATOMIC_MEMORY_ENABLED not set in environment"
    echo "         Can be enabled in initialization/setup.md"
fi

# ============================================================================
# CHECK 7: MCP Server Configuration
# ============================================================================

print_header "Check 7: MCP Server Configuration"

MCP_CONFIG_PATHS=(
    "$HOME/.config/claude-code/mcp_servers.json"
    "$HOME/.config/claudecode/mcp_servers.json"
    "$HOME/Library/Application Support/claude-code/mcp_servers.json"
)

MCP_FOUND=false
for config_path in "${MCP_CONFIG_PATHS[@]}"; do
    if [[ -f "$config_path" ]]; then
        if grep -q "claude-mem" "$config_path" 2>/dev/null; then
            check_pass "Claude-mem configured in: $config_path"
            MCP_FOUND=true
            break
        fi
    fi
done

if [[ "$MCP_FOUND" == "false" ]]; then
    check_warn "No MCP server configuration found for claude-mem"
    echo "         May auto-configure on first use"
fi

# ============================================================================
# CHECK 8: Dependencies
# ============================================================================

print_header "Check 8: System Dependencies"

if command -v sqlite3 &>/dev/null; then
    check_pass "sqlite3 available"
    SQLITE_VERSION=$(sqlite3 --version | cut -d' ' -f1)
    echo "         Version: $SQLITE_VERSION"
else
    check_warn "sqlite3 not found (optional for manual queries)"
fi

if command -v curl &>/dev/null; then
    check_pass "curl available"
else
    check_fail "curl not found (required for web UI checks)"
fi

if command -v jq &>/dev/null; then
    check_pass "jq available"
else
    check_fail "jq not found (required for atomic-claude)"
fi

# ============================================================================
# CHECK 9: Atomic-Claude Integration
# ============================================================================

print_header "Check 9: Atomic-Claude Integration"

if [[ -f "lib/memory.sh" ]]; then
    check_pass "lib/memory.sh present"

    # Check for claude-mem references
    if grep -q "claude-mem" lib/memory.sh 2>/dev/null; then
        check_pass "lib/memory.sh references claude-mem"
    else
        check_warn "lib/memory.sh may need claude-mem integration"
    fi
else
    check_fail "lib/memory.sh not found"
fi

if [[ -f "lib/task-memory-defs.sh" ]]; then
    check_pass "lib/task-memory-defs.sh present"
else
    check_warn "lib/task-memory-defs.sh not found"
fi

# ============================================================================
# SUMMARY
# ============================================================================

print_summary
