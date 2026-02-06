#!/bin/bash
source "$ATOMIC_ROOT/lib/atomic.sh" || exit 1
atomic_step "Test step" || exit 1
exit 0
