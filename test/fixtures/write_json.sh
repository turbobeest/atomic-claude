#!/bin/bash
cat > "/Users/jamesterbeest/dev/atomic-claude/test/fixtures/bash_output.json" << 'EOF'
{
  "status": "success",
  "task_id": "001",
  "result": "completed"
}
EOF
exit 0
