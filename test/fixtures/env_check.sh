#!/bin/bash
if [[ -z "$ATOMIC_ROOT" ]]; then
    echo "ATOMIC_ROOT not set" >&2
    exit 1
fi
echo "ATOMIC_ROOT=$ATOMIC_ROOT"
exit 0
