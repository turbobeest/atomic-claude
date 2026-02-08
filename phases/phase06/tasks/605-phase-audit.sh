#!/usr/bin/env bash
#
# Task 605: Phase Audit - Code Review
# AI-driven audit selection from turbobeest/audits repository
#

# Source required libraries
set -euo pipefail
LIB_DIR="${ATOMIC_LIB_DIR:-$(dirname "$0")/../../../lib}"
source "$LIB_DIR/atomic.sh"

task_605_phase_audit() {
    # UAT Mode Bypass
    if [[ "${ATOMIC_UAT_MODE:-false}" == "true" ]]; then
        atomic_step "Phase Audit"
        atomic_substep "UAT Mode: Creating minimal valid output"

        # Create minimal output that satisfies downstream tasks
        local audit_report="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/audit-report.json"
        mkdir -p "$(dirname "$audit_report")"
        jq -n '{
            "audits_run": 0,
            "status": "complete",
            "summary": {
                "passed": 0,
                "failed": 0,
                "warnings": 0
            },
            "overall_status": "PASS",
            "completed_at": (now | todate)
        }' > "$audit_report"

        atomic_success "UAT bypass complete"
        return 0
    fi

    # Source the audit library (with fallback to library root)
    local audit_lib="$ATOMIC_ROOT/lib/audit.sh"
    if [[ ! -f "$audit_lib" && -n "${ATOMIC_LIB_ROOT:-}" ]]; then
        audit_lib="$ATOMIC_LIB_ROOT/lib/audit.sh"
    fi

    if [[ ! -f "$audit_lib" ]]; then
        atomic_error "audit.sh not found at $ATOMIC_ROOT/lib/ or $ATOMIC_LIB_ROOT/lib/"
        return 1
    fi

    source "$audit_lib"
    audit_phase_wrapper 6 "Code Review"
    return $?
}

# Execute if run directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    task_605_phase_audit
fi
