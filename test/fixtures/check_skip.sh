#!/bin/bash
task_id="001"
if grep -q '"001".*"complete"' "/Users/jamesterbeest/dev/atomic-claude/test/fixtures/skip_state.json"; then
    echo "SKIP"
    exit 0
fi
echo "RUN"
exit 1
