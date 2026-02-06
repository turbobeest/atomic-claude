#!/bin/bash
if [[ -d "$ATOMIC_ROOT/.outputs" ]]; then
    exit 0
else
    echo ".outputs not found" >&2
    exit 1
fi
