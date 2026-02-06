#!/usr/bin/env bash
#
# Task 605: Phase Audit - Code Review
# AI-driven audit selection from turbobeest/audits repository
#

task_605_phase_audit() {
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
