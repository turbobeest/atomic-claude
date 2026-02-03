#!/usr/bin/env bash
#
# Claude-Mem Troubleshooting Script
#

set -euo pipefail

echo "=== Claude-Mem Troubleshooting ==="
echo

echo "1. Checking for plugin installation files..."
find ~/.config/claude-code -name "*claude-mem*" 2>/dev/null || echo "   No plugin files found in config"
echo

echo "2. Checking Claude Code logs..."
if [ -d ~/.config/claude-code/logs ]; then
    echo "   Recent logs:"
    ls -lt ~/.config/claude-code/logs | head -5
    echo
    echo "   Searching for claude-mem errors..."
    grep -i "claude-mem" ~/.config/claude-code/logs/*.log 2>/dev/null | tail -10 || echo "   No claude-mem entries in logs"
else
    echo "   No logs directory found"
fi
echo

echo "3. Checking for node/bun processes..."
ps aux | grep -E "(node|bun)" | grep -v grep || echo "   No node/bun processes"
echo

echo "4. Checking network listeners..."
lsof -i -P | grep LISTEN | grep -E "(37777|claude)" || echo "   No claude-related services listening"
echo

echo "5. Checking environment..."
env | grep -i claude | sort
echo

echo "6. Attempting to access web UI..."
curl -s --max-time 2 http://localhost:37777 2>&1 | head -5 || echo "   Web UI not accessible"
echo

echo "=== Recommendations ==="
echo
echo "If claude-mem is installed but not running:"
echo "1. Restart Claude Code completely (not just reload)"
echo "2. Check Claude Code version (must be recent)"
echo "3. Try reinstalling: /plugin uninstall claude-mem && /plugin install claude-mem"
echo "4. Check if you're in the same Claude Code instance where you installed"
echo "5. Verify installation: run '/plugin list' in Claude Code"
echo
