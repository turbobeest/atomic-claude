#!/usr/bin/env bash
#
# UAT Runner Wrapper
# Runs User Acceptance Tests for Phase 00 and Phase 01
#
# Usage:
#   ./run_uat.sh              # Run full UAT (both phases)
#   ./run_uat.sh --phase 0    # Phase 00 only
#   ./run_uat.sh --phase 1    # Phase 01 only
#   ./run_uat.sh --pause      # Pause between tasks
#   ./run_uat.sh --verbose    # Verbose output
#

set -euo pipefail

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "\n${CYAN}════════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  ATOMIC CLAUDE 2.0 - USER ACCEPTANCE TEST${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════════════════════════${NC}\n"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 not found${NC}"
    exit 1
fi

# Check PYTHONPATH
export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"
export ATOMIC_ROOT="$REPO_ROOT"

# Disable forcing function for tool development
export ATOMIC_TOOL_DEVELOPMENT="true"

# Enable UAT mode to skip interactive tasks
export ATOMIC_UAT_MODE="true"

# Check for .env file
if [[ ! -f "$REPO_ROOT/.env" ]]; then
    echo -e "${YELLOW}⚠  Warning: .env file not found (API calls may fail)${NC}"
    echo -e "${YELLOW}   Expected location: $REPO_ROOT/.env${NC}\n"
fi

# Run UAT runner
echo -e "${BOLD}Starting UAT runner...${NC}\n"

cd "$REPO_ROOT"

if python3 "$SCRIPT_DIR/uat_runner.py" "$@"; then
    echo -e "\n${GREEN}════════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ✓ UAT PASSED${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════════════════════════${NC}\n"
    exit 0
else
    echo -e "\n${RED}════════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}  ✗ UAT FAILED${NC}"
    echo -e "${RED}════════════════════════════════════════════════════════════════════════════════${NC}\n"
    exit 1
fi
