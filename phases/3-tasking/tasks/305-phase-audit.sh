#!/usr/bin/env bash
#
# Task 305: Phase Audit - Task Decomposition
# AI-driven audit selection from turbobeest/audits repository
#

task_305_phase_audit() {
    # =========================================================================
    # UAT MODE BYPASS
    # =========================================================================
    if [[ "${ATOMIC_UAT_MODE:-false}" == "true" ]]; then
        atomic_info "UAT mode: Skipping audit..."

        local audit_dir="$ATOMIC_ROOT/.claude/audit"
        mkdir -p "$audit_dir"

        # Create minimal audit report
        cat > "$audit_dir/phase-03-audit.json" << EOF
{
  "audit_timestamp": "$(date -Iseconds)",
  "audit_mode": "uat",
  "phase": 3,
  "phase_name": "Task Decomposition",
  "findings": {},
  "summary": {
    "passed": 5,
    "warnings": 0,
    "critical": 0
  },
  "overall_status": "PASS",
  "proceed_recommendation": true,
  "proceed_rationale": "UAT mode - audit bypassed for testing"
}
EOF

        atomic_success "UAT mode: Audit bypassed"
        return 0
    fi

    # -------------------------------------------------------------------------
    # NORMAL MODE - Continue with full audit
    # -------------------------------------------------------------------------

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
    audit_phase_wrapper 3 "Task Decomposition"
    return $?
}
