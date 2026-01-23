#!/bin/bash
#
# ATOMIC CLAUDE Test Runner
# Runs all BATS tests and produces summary
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ============================================================================
# DEPENDENCY CHECKS
# ============================================================================

check_dependencies() {
    echo -e "${CYAN}Checking dependencies...${NC}"

    # Check for BATS
    if ! command -v bats &> /dev/null; then
        echo -e "${YELLOW}BATS not found. Installing...${NC}"

        # Try to install BATS
        if command -v brew &> /dev/null; then
            brew install bats-core
        elif command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y bats
        elif command -v npm &> /dev/null; then
            npm install -g bats
        else
            echo -e "${RED}Error: Cannot install BATS. Please install manually:${NC}"
            echo "  https://bats-core.readthedocs.io/en/stable/installation.html"
            exit 1
        fi
    fi

    # Check for jq
    if ! command -v jq &> /dev/null; then
        echo -e "${RED}Error: jq is required but not installed.${NC}"
        echo "  Install with: apt-get install jq OR brew install jq"
        exit 1
    fi

    echo -e "${GREEN}All dependencies satisfied.${NC}"
    echo ""
}

# ============================================================================
# USAGE
# ============================================================================

show_usage() {
    echo ""
    echo -e "${BOLD}ATOMIC CLAUDE Test Runner${NC}"
    echo ""
    echo "Usage: $0 [OPTIONS] [PATTERN]"
    echo ""
    echo "Options:"
    echo "  -u, --unit         Run only unit tests"
    echo "  -i, --integration  Run only integration tests"
    echo "  -v, --verbose      Show verbose output"
    echo "  -t, --tap          Output in TAP format"
    echo "  -j, --junit        Output JUnit XML (for CI)"
    echo "  -h, --help         Show this help"
    echo ""
    echo "Pattern:"
    echo "  Optionally specify a pattern to filter tests"
    echo "  e.g., $0 'atomic' runs tests matching 'atomic'"
    echo ""
    echo "Examples:"
    echo "  $0                    # Run all tests"
    echo "  $0 --unit             # Run unit tests only"
    echo "  $0 --verbose          # Run with verbose output"
    echo "  $0 'state'            # Run tests matching 'state'"
    echo ""
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    local test_type="all"
    local output_format=""
    local verbose=""
    local filter=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -u|--unit)
                test_type="unit"
                shift
                ;;
            -i|--integration)
                test_type="integration"
                shift
                ;;
            -v|--verbose)
                verbose="--verbose-run"
                shift
                ;;
            -t|--tap)
                output_format="--tap"
                shift
                ;;
            -j|--junit)
                output_format="--formatter junit"
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                filter="$1"
                shift
                ;;
        esac
    done

    check_dependencies

    # Build test file list
    local test_files=()

    case "$test_type" in
        unit)
            test_files=("$SCRIPT_DIR/unit/"*.bats)
            ;;
        integration)
            test_files=("$SCRIPT_DIR/integration/"*.bats)
            ;;
        all)
            test_files=("$SCRIPT_DIR/unit/"*.bats "$SCRIPT_DIR/integration/"*.bats)
            ;;
    esac

    # Header
    echo ""
    echo -e "${BOLD}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║        ATOMIC CLAUDE TEST SUITE                           ║${NC}"
    echo -e "${BOLD}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  Test type:    ${CYAN}$test_type${NC}"
    echo -e "  Test files:   ${CYAN}${#test_files[@]}${NC}"
    [[ -n "$filter" ]] && echo -e "  Filter:       ${CYAN}$filter${NC}"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Run tests
    local bats_cmd="bats"
    local bats_args=""

    [[ -n "$verbose" ]] && bats_args+=" $verbose"
    [[ -n "$output_format" ]] && bats_args+=" $output_format"
    [[ -n "$filter" ]] && bats_args+=" --filter '$filter'"

    local start_time=$(date +%s)

    # Run BATS
    if eval "$bats_cmd $bats_args ${test_files[*]}"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))

        echo ""
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}  ALL TESTS PASSED${NC} (${duration}s)"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        exit 0
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))

        echo ""
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${RED}  SOME TESTS FAILED${NC} (${duration}s)"
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        exit 1
    fi
}

main "$@"
