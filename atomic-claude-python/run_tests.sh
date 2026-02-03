#!/usr/bin/env bash
#
# ATOMIC CLAUDE Python Tests Runner
# Runs the comprehensive test suite with coverage reporting
#

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC} ${GREEN}ATOMIC CLAUDE Python Test Suite${NC}                          ${BLUE}║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}⚠ pytest not found. Installing test dependencies...${NC}"
    echo
    pip install -r tests/requirements.txt
    echo
fi

# Parse arguments
VERBOSE="-v"
COVERAGE="--cov=lib --cov-report=term-missing"
JUNIT=""
PARALLEL=""
SPECIFIC_TEST=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -vv|--very-verbose)
            VERBOSE="-vv"
            shift
            ;;
        --no-coverage)
            COVERAGE=""
            shift
            ;;
        --html-coverage)
            COVERAGE="--cov=lib --cov-report=html"
            shift
            ;;
        --junit)
            JUNIT="--junit-xml=test-results.xml"
            shift
            ;;
        --parallel)
            PARALLEL="-n auto"
            shift
            ;;
        -k)
            SPECIFIC_TEST="-k $2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo
            echo "Options:"
            echo "  -vv, --very-verbose    Extra verbose output"
            echo "  --no-coverage          Disable coverage reporting"
            echo "  --html-coverage        Generate HTML coverage report"
            echo "  --junit                Generate JUnit XML report"
            echo "  --parallel             Run tests in parallel"
            echo "  -k PATTERN             Run tests matching pattern"
            echo "  -h, --help             Show this help message"
            echo
            echo "Examples:"
            echo "  $0                               # Run all tests with coverage"
            echo "  $0 -vv                           # Run with extra verbose output"
            echo "  $0 -k atomic                     # Run only atomic tests"
            echo "  $0 --parallel --html-coverage    # Parallel with HTML coverage"
            exit 0
            ;;
        *)
            echo -e "${RED}✗ Unknown option: $1${NC}"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Run tests
echo -e "${BLUE}▶${NC} Running tests..."
echo

# Build pytest command
PYTEST_CMD="pytest tests/ $VERBOSE $COVERAGE $JUNIT $PARALLEL $SPECIFIC_TEST"

echo -e "${BLUE}Command:${NC} $PYTEST_CMD"
echo

# Execute tests
if $PYTEST_CMD; then
    echo
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC} ${GREEN}✓ All Tests Passed${NC}                                        ${GREEN}║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo

    # Show coverage report location if HTML was generated
    if [[ "$COVERAGE" == *"html"* ]]; then
        echo -e "${BLUE}▶${NC} HTML coverage report: ${YELLOW}htmlcov/index.html${NC}"
        echo
    fi

    exit 0
else
    EXIT_CODE=$?
    echo
    echo -e "${RED}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║${NC} ${RED}✗ Tests Failed${NC}                                             ${RED}║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo

    exit $EXIT_CODE
fi
