#!/usr/bin/env bash
#
# UAT Pre-flight Check
# Verifies environment before running UAT
#

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "\n${CYAN}════════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  UAT PRE-FLIGHT CHECK${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════════════════════════${NC}\n"

CHECKS_PASSED=0
CHECKS_FAILED=0
WARNINGS=0

# Check Python
echo -n "Checking Python 3... "
if command -v python3 &> /dev/null; then
    VERSION=$(python3 --version | awk '{print $2}')
    echo -e "${GREEN}✓ Found Python $VERSION${NC}"
    ((CHECKS_PASSED++)) || true || true
else
    echo -e "${RED}✗ Python 3 not found${NC}"
    ((CHECKS_FAILED++)) || true || true
fi

# Check Bash version
echo -n "Checking Bash version... "
if [[ "${BASH_VERSINFO[0]}" -ge 4 ]]; then
    echo -e "${GREEN}✓ Bash ${BASH_VERSION}${NC}"
    ((CHECKS_PASSED++)) || true
else
    echo -e "${RED}✗ Bash 4.0+ required (found ${BASH_VERSION})${NC}"
    ((CHECKS_FAILED++)) || true
fi

# Check jq
echo -n "Checking jq... "
if command -v jq &> /dev/null; then
    VERSION=$(jq --version)
    echo -e "${GREEN}✓ Found $VERSION${NC}"
    ((CHECKS_PASSED++)) || true
else
    echo -e "${RED}✗ jq not found (required for JSON processing)${NC}"
    ((CHECKS_FAILED++)) || true
fi

# Check UAT files
echo -n "Checking UAT runner... "
if [[ -x "$SCRIPT_DIR/uat_runner.py" ]]; then
    echo -e "${GREEN}✓ uat_runner.py (executable)${NC}"
    ((CHECKS_PASSED++)) || true
else
    echo -e "${RED}✗ uat_runner.py missing or not executable${NC}"
    ((CHECKS_FAILED++)) || true
fi

echo -n "Checking run_uat.sh... "
if [[ -x "$SCRIPT_DIR/run_uat.sh" ]]; then
    echo -e "${GREEN}✓ run_uat.sh (executable)${NC}"
    ((CHECKS_PASSED++)) || true
else
    echo -e "${RED}✗ run_uat.sh missing or not executable${NC}"
    ((CHECKS_FAILED++)) || true
fi

# Check fixtures
echo -n "Checking test fixtures... "
FIXTURE_COUNT=$(find "$SCRIPT_DIR/fixtures" -type f 2>/dev/null | wc -l | tr -d ' ')
if [[ "$FIXTURE_COUNT" -ge 5 ]]; then
    echo -e "${GREEN}✓ Found $FIXTURE_COUNT fixture files${NC}"
    ((CHECKS_PASSED++)) || true
else
    echo -e "${RED}✗ Missing fixture files (found $FIXTURE_COUNT, expected 5+)${NC}"
    ((CHECKS_FAILED++)) || true
fi

# Check main.py
echo -n "Checking main.py... "
if [[ -f "$REPO_ROOT/main.py" ]]; then
    echo -e "${GREEN}✓ main.py exists${NC}"
    ((CHECKS_PASSED++)) || true
else
    echo -e "${RED}✗ main.py not found in $REPO_ROOT${NC}"
    ((CHECKS_FAILED++)) || true
fi

# Check core modules
echo -n "Checking core modules... "
CORE_COUNT=0
[[ -f "$REPO_ROOT/core/state.py" ]] && ((CORE_COUNT++)) || true
[[ -f "$REPO_ROOT/core/config.py" ]] && ((CORE_COUNT++)) || true
[[ -f "$REPO_ROOT/core/subprocess_runner.py" ]] && ((CORE_COUNT++)) || true
if [[ $CORE_COUNT -eq 3 ]]; then
    echo -e "${GREEN}✓ All core modules found${NC}"
    ((CHECKS_PASSED++)) || true
else
    echo -e "${RED}✗ Missing core modules (found $CORE_COUNT/3)${NC}"
    ((CHECKS_FAILED++)) || true
fi

# Check phase orchestrators
echo -n "Checking phase orchestrators... "
ORCHESTRATOR_COUNT=0
[[ -f "$REPO_ROOT/phases/phase00/orchestrator00.py" ]] && ((ORCHESTRATOR_COUNT++)) || true
[[ -f "$REPO_ROOT/phases/phase01/orchestrator01.py" ]] && ((ORCHESTRATOR_COUNT++)) || true
if [[ $ORCHESTRATOR_COUNT -eq 2 ]]; then
    echo -e "${GREEN}✓ Phase 00 & 01 orchestrators found${NC}"
    ((CHECKS_PASSED++)) || true
else
    echo -e "${RED}✗ Missing orchestrators (found $ORCHESTRATOR_COUNT/2)${NC}"
    ((CHECKS_FAILED++)) || true
fi

# Check .env (optional)
echo -n "Checking .env file... "
if [[ -f "$REPO_ROOT/.env" ]]; then
    echo -e "${GREEN}✓ .env found (API calls enabled)${NC}"
    ((CHECKS_PASSED++)) || true
else
    echo -e "${YELLOW}⚠ .env not found (UAT will run but LLM tasks may fail)${NC}"
    ((WARNINGS++)) || true
fi

# Summary
echo -e "\n${CYAN}────────────────────────────────────────────────────────────────────────────────${NC}"
echo -e "  Checks passed:  ${GREEN}$CHECKS_PASSED${NC}"
echo -e "  Checks failed:  ${RED}$CHECKS_FAILED${NC}"
echo -e "  Warnings:       ${YELLOW}$WARNINGS${NC}"
echo -e "${CYAN}────────────────────────────────────────────────────────────────────────────────${NC}\n"

if [[ $CHECKS_FAILED -eq 0 ]]; then
    echo -e "${GREEN}✓ Pre-flight check passed!${NC}"
    echo -e "${GREEN}  Ready to run: ./test/run_uat.sh${NC}\n"
    exit 0
else
    echo -e "${RED}✗ Pre-flight check failed!${NC}"
    echo -e "${RED}  Please resolve issues before running UAT${NC}\n"
    exit 1
fi
