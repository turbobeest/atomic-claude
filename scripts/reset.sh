#!/usr/bin/env bash
#
# Simple wrapper for reset-task.py
# Makes it easy to call from anywhere in the repo
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 "$SCRIPT_DIR/reset-task.py" "$@"
