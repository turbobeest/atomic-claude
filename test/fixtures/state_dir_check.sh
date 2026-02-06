#!/bin/bash
if [[ -d "$ATOMIC_ROOT/.state" ]]; then
    exit 0
else
    echo ".state not found" >&2
    exit 1
fi
