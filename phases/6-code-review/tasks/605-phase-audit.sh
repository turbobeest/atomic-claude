#!/bin/bash
#
# Task 605: Phase Audit - Code Review
# AI-driven audit selection from turbobeest/audits repository
#

task_605_phase_audit() {
    source "$ATOMIC_ROOT/lib/audit.sh"
    audit_phase_wrapper 6 "Code Review"
    return $?
}
