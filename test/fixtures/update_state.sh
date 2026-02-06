#!/bin/bash
# Read current state
phase=$(grep -o '"phase": "[^"]*"' "/Users/jamesterbeest/dev/atomic-claude/test/fixtures/shared_state.json" | cut -d'"' -f4)

# Update state (increment tasks_complete)
cat > "/Users/jamesterbeest/dev/atomic-claude/test/fixtures/shared_state.json" << 'EOF'
{
  "phase": "$phase",
  "tasks_complete": 1
}
EOF
exit 0
