#!/bin/bash
#
# Copy Test Fixtures
# Copies sample outputs to .outputs directory for testing
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ATOMIC_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=========================================="
echo "Copy Test Fixtures"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "$ATOMIC_ROOT/main.py" ]; then
    echo "✗ Error: Not in atomic-claude2 root directory"
    echo "  Expected: main.py in $ATOMIC_ROOT"
    exit 1
fi

cd "$ATOMIC_ROOT"

# Phase 0 fixtures
echo "==> Copying Phase 0 fixtures..."
mkdir -p .outputs/0-setup
cp -v "$SCRIPT_DIR/phase00-outputs/"* .outputs/0-setup/
echo "✓ Phase 0 fixtures copied"
echo ""

# Verify
echo "==> Verifying fixtures..."
for file in project-config.json secrets.json closeout.json; do
    if [ -f ".outputs/0-setup/$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file missing"
        exit 1
    fi
done

echo ""
echo "=========================================="
echo "Fixtures Ready"
echo "=========================================="
echo ""
echo "You can now run Phase 1:"
echo "  python main.py run 1"
echo ""
echo "Or continue with continuity tests:"
echo "  ./test/continuity-test-scenario1.sh"
echo ""
