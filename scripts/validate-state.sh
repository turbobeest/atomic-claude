#!/usr/bin/env bash
#
# Validate Pipeline State - Quick Health Check
# Run this at any time to see pipeline status and validate correctness
#

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

echo ""
echo -e "${CYAN}${BOLD}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}${BOLD}║  ATOMIC CLAUDE - Pipeline State Validation                ║${NC}"
echo -e "${CYAN}${BOLD}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check prerequisites
echo -e "${BOLD}Prerequisites:${NC}"
[[ -f .env ]] && echo -e "  ${GREEN}✓${NC} .env file exists" || echo -e "  ${RED}✗${NC} .env file missing"
aws sts get-caller-identity --profile bedrock-dev &>/dev/null && echo -e "  ${GREEN}✓${NC} AWS SSO authenticated" || echo -e "  ${YELLOW}⚠${NC} AWS SSO not authenticated"
[[ -f initialization/setup.md ]] && echo -e "  ${GREEN}✓${NC} setup.md exists" || echo -e "  ${YELLOW}⚠${NC} setup.md missing"
echo ""

# Check current state
echo -e "${BOLD}Current State:${NC}"
if [[ -f .state/session.json ]]; then
    current_phase=$(jq -r '.current_phase // "none"' .state/session.json)
    tasks_completed=$(jq -r '.tasks_completed // 0' .state/session.json)
    tasks_failed=$(jq -r '.tasks_failed // 0' .state/session.json)
    echo -e "  Phase: ${CYAN}$current_phase${NC}"
    echo -e "  Tasks completed: ${GREEN}$tasks_completed${NC}"
    [[ $tasks_failed -gt 0 ]] && echo -e "  Tasks failed: ${RED}$tasks_failed${NC}" || echo -e "  Tasks failed: 0"
else
    echo -e "  ${DIM}No active session${NC}"
fi
echo ""

# Check current task
echo -e "${BOLD}Current Task:${NC}"
if [[ -f .state/current-task.json ]]; then
    active=$(jq -r '.active' .state/current-task.json)
    if [[ "$active" == "true" ]]; then
        desc=$(jq -r '.description' .state/current-task.json)
        provider=$(jq -r '.provider' .state/current-task.json)
        model=$(jq -r '.model' .state/current-task.json)
        timestamp=$(jq -r '.timestamp' .state/current-task.json)
        echo -e "  ${YELLOW}⏳${NC} $desc"
        echo -e "  ${DIM}Provider: $provider, Model: $model${NC}"
        echo -e "  ${DIM}Started: $timestamp${NC}"

        # Check how long it's been running
        if command -v gdate &>/dev/null; then
            start_epoch=$(gdate -d "$timestamp" +%s 2>/dev/null || echo "0")
        else
            start_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${timestamp%%[+-]*}" +%s 2>/dev/null || echo "0")
        fi
        now_epoch=$(date +%s)
        duration=$((now_epoch - start_epoch))

        if [[ $duration -gt 300 ]]; then
            echo -e "  ${RED}⚠ WARNING: Task running for ${duration}s (>5min)${NC}"
        elif [[ $duration -gt 120 ]]; then
            echo -e "  ${YELLOW}Duration: ${duration}s${NC}"
        else
            echo -e "  ${DIM}Duration: ${duration}s${NC}"
        fi
    else
        echo -e "  ${DIM}No active task${NC}"
    fi
else
    echo -e "  ${DIM}No task state${NC}"
fi
echo ""

# Check Phase 0 outputs
if [[ -d .outputs/0-setup ]]; then
    echo -e "${BOLD}Phase 0 Outputs:${NC}"

    if [[ -f .outputs/0-setup/project-config.json ]]; then
        echo -e "  ${GREEN}✓${NC} project-config.json"
        project_name=$(jq -r '.project.name // "unknown"' .outputs/0-setup/project-config.json)
        echo -e "    ${DIM}Project: $project_name${NC}"
    fi

    if [[ -f .outputs/0-setup/secrets.json ]]; then
        echo -e "  ${GREEN}✓${NC} secrets.json"
        providers=$(jq -r '.providers | keys | join(", ")' .outputs/0-setup/secrets.json 2>/dev/null || echo "unknown")
        echo -e "    ${DIM}Providers: $providers${NC}"
    fi

    if [[ -f .outputs/0-setup/closeout.json ]]; then
        echo -e "  ${GREEN}✓${NC} closeout.json ${GREEN}(Phase 0 complete!)${NC}"
    else
        echo -e "  ${YELLOW}⚠${NC} closeout.json missing (phase not complete)"
    fi
    echo ""
fi

# Check for errors
echo -e "${BOLD}Recent Errors:${NC}"
if [[ -f .logs/invocations.log ]]; then
    errors=$(grep -i "error\|failed\|timeout" .logs/invocations.log 2>/dev/null | tail -3)
    if [[ -n "$errors" ]]; then
        echo "$errors" | while IFS= read -r line; do
            echo -e "  ${RED}✗${NC} ${DIM}$line${NC}"
        done
    else
        echo -e "  ${GREEN}✓${NC} No recent errors"
    fi
else
    echo -e "  ${DIM}No log file${NC}"
fi
echo ""

# Summary
echo -e "${CYAN}${BOLD}─────────────────────────────────────────────────────────────${NC}"
if [[ -f .outputs/0-setup/closeout.json ]]; then
    echo -e "${GREEN}${BOLD}Status: Phase 0 COMPLETE ✓${NC}"
elif [[ -f .state/current-task.json ]] && [[ "$(jq -r '.active' .state/current-task.json)" == "true" ]]; then
    echo -e "${YELLOW}${BOLD}Status: Task in progress...${NC}"
else
    echo -e "${DIM}Status: Idle${NC}"
fi
echo -e "${CYAN}${BOLD}─────────────────────────────────────────────────────────────${NC}"
echo ""
