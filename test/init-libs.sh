#!/usr/bin/env bash
#
# Safe library initialization for manual testing
#

# Set up environment first
export ATOMIC_ROOT="${ATOMIC_ROOT:-$(pwd)}"
export ATOMIC_OUTPUT_DIR="${ATOMIC_OUTPUT_DIR:-$ATOMIC_ROOT/.outputs}"
export ATOMIC_STATE_DIR="${ATOMIC_STATE_DIR:-$ATOMIC_ROOT/.state}"
export ATOMIC_LOG_DIR="${ATOMIC_LOG_DIR:-$ATOMIC_ROOT/.logs}"
export CURRENT_PHASE="${CURRENT_PHASE:-0-setup}"

# Temporarily disable strict error handling for sourcing
set +euo pipefail

# Source libraries
source "$ATOMIC_ROOT/lib/atomic.sh" 2>/dev/null || {
    echo "✗ Failed to source atomic.sh"
    exit 1
}

source "$ATOMIC_ROOT/lib/phase.sh" 2>/dev/null || {
    echo "✗ Failed to source phase.sh"
    exit 1
}

source "$ATOMIC_ROOT/lib/task-state.sh" 2>/dev/null || {
    echo "✗ Failed to source task-state.sh"
    exit 1
}

# Re-enable strict error handling
set -euo pipefail

echo "✓ Libraries loaded successfully"
