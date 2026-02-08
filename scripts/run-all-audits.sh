#!/bin/bash
# Shell wrapper for master audit runner
# Provides convenient shortcuts and presets

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
BOLD="\033[1m"
CYAN="\033[36m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
NC="\033[0m"

# Show usage
usage() {
    cat << EOF
${BOLD}ATOMIC CLAUDE - Master Audit Runner${NC}

Usage: $0 [COMMAND] [OPTIONS]

${BOLD}Commands:${NC}
  all           Run all audits (default)
  quick         Run only critical audits
  critical      Same as quick
  list          List all available audits

${BOLD}Individual Audits:${NC}
  dependency    Run dependency audit
  script        Run script quality audit
  config        Run configuration audit
  state         Run state management audit
  output        Run output validation audit
  integration   Run integration points audit
  error         Run error handling audit
  security      Run security audit
  regression    Run regression tests
  performance   Run performance audit
  memory        Run memory audit
  smoke         Run smoke tests

${BOLD}Options:${NC}
  --skip AUDIT  Skip specific audit
  --help        Show this help

${BOLD}Examples:${NC}
  $0                      # Run all audits
  $0 quick                # Run critical audits only
  $0 security             # Run security audit
  $0 all --skip memory    # Run all except memory audit

EOF
    exit 0
}

# Parse command
COMMAND="${1:-all}"
shift || true

case "$COMMAND" in
    help|--help|-h)
        usage
        ;;

    all|comprehensive)
        echo -e "${CYAN}Running comprehensive audit suite...${NC}"
        ./run_all_audits.py "$@"
        ;;

    quick|critical|fast)
        echo -e "${CYAN}Running critical audits only...${NC}"
        ./run_all_audits.py --quick "$@"
        ;;

    list|ls)
        ./run_all_audits.py --list
        ;;

    dependency|deps)
        echo -e "${CYAN}Running dependency audit...${NC}"
        ./run_all_audits.py --only "Dependency Audit" "$@"
        ;;

    script|scripts)
        echo -e "${CYAN}Running script quality audit...${NC}"
        ./run_all_audits.py --only "Script Quality Audit" "$@"
        ;;

    config|configuration)
        echo -e "${CYAN}Running configuration audit...${NC}"
        ./run_all_audits.py --only "Configuration Audit" "$@"
        ;;

    state)
        echo -e "${CYAN}Running state management audit...${NC}"
        ./run_all_audits.py --only "State Management Audit" "$@"
        ;;

    output)
        echo -e "${CYAN}Running output validation audit...${NC}"
        ./run_all_audits.py --only "Output Validation Audit" "$@"
        ;;

    integration|handoff)
        echo -e "${CYAN}Running integration points audit...${NC}"
        ./run_all_audits.py --only "Integration Points Audit" "$@"
        ;;

    error|errors)
        echo -e "${CYAN}Running error handling audit...${NC}"
        ./run_all_audits.py --only "Error Handling Audit" "$@"
        ;;

    security|sec)
        echo -e "${CYAN}Running security audit...${NC}"
        ./run_all_audits.py --only "Security Audit" "$@"
        ;;

    regression)
        echo -e "${CYAN}Running regression tests...${NC}"
        ./run_all_audits.py --only "Regression Tests" "$@"
        ;;

    performance|perf)
        echo -e "${CYAN}Running performance audit...${NC}"
        ./run_all_audits.py --only "Performance Audit" "$@"
        ;;

    memory|mem)
        echo -e "${CYAN}Running memory audit...${NC}"
        ./run_all_audits.py --only "Memory Audit" "$@"
        ;;

    smoke)
        echo -e "${CYAN}Running smoke tests...${NC}"
        ./run_all_audits.py --only "Smoke Tests" "$@"
        ;;

    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        echo "Run '$0 help' for usage"
        exit 1
        ;;
esac

EXIT_CODE=$?

# Show final status
if [[ $EXIT_CODE -eq 0 ]]; then
    echo -e "\n${GREEN}${BOLD}✓ Audit completed successfully${NC}"
else
    echo -e "\n${RED}${BOLD}✗ Audit failed${NC}"
fi

exit $EXIT_CODE
