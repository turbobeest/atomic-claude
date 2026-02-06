#!/usr/bin/env bash
#
# Performance Audit Runner - Convenience Wrapper
# Runs the Python performance audit with proper environment setup
#

set -euo pipefail

# Find script directory and repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

# Colors
BOLD="\033[1m"
CYAN="\033[36m"
NC="\033[0m"

echo ""
echo -e "${BOLD}${CYAN}Atomic Claude - Performance Audit${NC}"
echo ""

# Check Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found. Please install Python 3."
    exit 1
fi

# Check for psutil (optional but recommended)
if ! python3 -c "import psutil" &> /dev/null; then
    echo "NOTE: psutil not installed - some metrics will use fallback methods"
    echo "      Install with: pip3 install psutil"
    echo ""
fi

# Run the audit
python3 "$SCRIPT_DIR/performance_audit_runner.py"
exit_code=$?

echo ""
if [[ $exit_code -eq 0 ]]; then
    echo "View detailed report: test/reports/performance_audit.json"
else
    echo "Check test/reports/performance_audit.json for details"
fi
echo ""

exit $exit_code
