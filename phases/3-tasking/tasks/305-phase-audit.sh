#!/bin/bash
#
# Task 305: Phase Audit - Task Decomposition
# AI-driven audit selection from turbobeest/audits repository
#

task_305_phase_audit() {
    source "$ATOMIC_ROOT/lib/audit.sh"
    audit_phase_wrapper 3 "Task Decomposition"
    return $?
}
