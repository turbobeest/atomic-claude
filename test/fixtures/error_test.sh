#!/bin/bash
cat > "/Users/jamesterbeest/dev/atomic-claude/test/fixtures/error.json" << 'EOF'
{
  "error": true,
  "message": "Task validation failed",
  "code": 100
}
EOF
exit 100
