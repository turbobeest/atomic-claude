#!/usr/bin/env bash
#
# Task 805: Phase Audit - Deployment Prep
# AI-driven audit selection from turbobeest/audits repository
#

# Source required libraries
set -euo pipefail
LIB_DIR="${ATOMIC_LIB_DIR:-$(dirname "$0")/../../lib}"
source "$LIB_DIR/atomic.sh"

task_805_phase_audit() {
    # UAT Mode Bypass
    if [[ "${ATOMIC_UAT_MODE:-false}" == "true" ]]; then
        atomic_step "Phase Audit"
        atomic_substep "UAT Mode: Skipping audit"
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
    audit_phase_wrapper 8 "Deployment Prep"
    return $?
}

# Execute if run directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    task_805_phase_audit
fi
