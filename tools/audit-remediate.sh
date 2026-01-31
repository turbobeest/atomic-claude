#!/bin/bash
#
# Standalone audit remediation launcher
# Runs audit_post_execution against an existing report file
#
# Usage:
#   ./tools/audit-remediate.sh [phase_num] [phase_name]
#   ./tools/audit-remediate.sh 2 "PRD Validation"
#   ./tools/audit-remediate.sh                      # defaults to phase 2
#

set -uo pipefail
# NOTE: intentionally no 'set -e' — interactive read loops and jq queries
# return non-zero in normal operation, which would kill the session.

PHASE_NUM="${1:-2}"
PHASE_NAME="${2:-Phase $PHASE_NUM Audit}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

source "$ROOT_DIR/lib/atomic.sh"
source "$ROOT_DIR/lib/audit.sh"

# Disable errexit AFTER both sources — they both set -euo pipefail.
# Interactive read loops, jq queries, and diff return non-zero in normal
# operation, which would kill the session under errexit.
set +e

atomic_state_init

# Resolve actual phase directory name (e.g., "2-prd", "1-discovery")
_phase_dir=$(basename "$(ls -d "$ROOT_DIR/phases/${PHASE_NUM}-"* 2>/dev/null | head -1)" 2>/dev/null)
_phase_dir="${_phase_dir:-${PHASE_NUM}-audit}"
atomic_context_init "$_phase_dir"

audit_init

REPORT="$ATOMIC_OUTPUT_DIR/audits/phase-${PHASE_NUM}-report.json"

if [[ ! -f "$REPORT" ]]; then
    echo -e "${RED}Report not found: $REPORT${NC}" >&2
    echo "  Available reports:" >&2
    ls "$ATOMIC_OUTPUT_DIR/audits"/phase-*-report.json 2>/dev/null | sed 's/^/    /' >&2
    exit 1
fi

echo ""
echo -e "${DIM}Report: $REPORT${NC}"
echo -e "${DIM}Phase:  $PHASE_NUM — $PHASE_NAME${NC}"
echo ""

audit_post_execution "$REPORT" "$PHASE_NUM" "$PHASE_NAME"
