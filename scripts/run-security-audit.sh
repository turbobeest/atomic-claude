#!/bin/bash
# Security Audit Runner - Convenience Script
# Runs comprehensive security validation

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT_DIR"

echo "Running Security Audit..."
echo

python3 test/security_audit_runner.py

EXIT_CODE=$?

echo
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ Security audit passed (no critical issues)"
else
    echo "✗ Security audit failed (critical issues found)"
fi

echo
echo "Report saved to: test/reports/security-audit.json"

exit $EXIT_CODE
