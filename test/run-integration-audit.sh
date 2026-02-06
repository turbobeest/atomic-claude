#!/usr/bin/env bash
#
# Integration Audit Runner - Convenience Wrapper
# Runs the Python integration audit with proper environment setup
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
echo -e "${BOLD}${CYAN}Atomic Claude - Integration Audit${NC}"
echo ""

# Check Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found. Please install Python 3."
    exit 1
fi

# Run the audit
python3 "$SCRIPT_DIR/integration_audit_runner.py"
exit_code=$?

echo ""
if [[ $exit_code -eq 0 ]]; then
    echo "View detailed report: test/reports/integration_audit.json"
else
    echo "Check test/reports/integration_audit.json for details"
fi
echo ""

exit $exit_code
