#!/bin/bash
cat > "/Users/jamesterbeest/dev/atomic-claude/test/fixtures/failure_state.json" << 'EOF'
{
  "tasks": {
    "003": {
      "status": "failed",
      "error": "Validation error",
      "timestamp": "2024-01-01T00:00:00"
    }
  }
}
EOF
exit 1
