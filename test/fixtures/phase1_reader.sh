#!/bin/bash
if [[ -f "/Users/jamesterbeest/dev/atomic-claude/test/fixtures/phase0_output/project-config.json" ]]; then
    if grep -q "test-project" "/Users/jamesterbeest/dev/atomic-claude/test/fixtures/phase0_output/project-config.json"; then
        exit 0
    fi
fi
exit 1
