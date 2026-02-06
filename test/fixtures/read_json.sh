#!/bin/bash
if command -v jq >/dev/null 2>&1; then
    value=$(jq -r '.key' "/Users/jamesterbeest/dev/atomic-claude/test/fixtures/test_data.json")
    if [[ "$value" == "value" ]]; then
        exit 0
    fi
fi
# Fallback: simple grep
if grep -q '"key": "value"' "/Users/jamesterbeest/dev/atomic-claude/test/fixtures/test_data.json"; then
    exit 0
fi
exit 1
