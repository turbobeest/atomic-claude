#!/usr/bin/env bash
#
# Quick launcher for dependency audit runner
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ATOMIC_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ATOMIC_ROOT"

echo "Running ATOMIC CLAUDE Dependency Audit..."
echo ""

python3 "$SCRIPT_DIR/dependency_audit_runner.py" "$@"
