#!/bin/bash
# Quick Start Script for Regression Tests
# Validates all bug patterns from BUG-PATTERNS.md

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Regression Test Suite${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Run the regression tests
cd "$ROOT_DIR"
python3 "$SCRIPT_DIR/regression_runner.py" --root "$ROOT_DIR"

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ All regression tests passed!${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}❌ Some regression tests failed. See reports above.${NC}"
    echo ""
fi

exit $exit_code
