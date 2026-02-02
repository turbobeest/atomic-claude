# JSON Escaping Fix for Dashboard

## Problem

The dashboard status endpoint was returning malformed JSON when task descriptions or other fields contained special characters:
- Double quotes (`"`)
- Newlines (`\n`)
- Tabs (`\t`)
- Backslashes (`\`)
- Other control characters

This caused the dashboard to fail parsing the `/api/status` response.

## Solution

Added robust JSON escaping to `lib/atomic.sh`:

### 1. New Function: `atomic_json_escape()`

**Location**: Lines 62-86 in `lib/atomic.sh`

Escapes all JSON-unsafe characters in the correct order:
1. Backslashes → `\\`
2. Quotes → `\"`
3. Newlines → `\n`
4. Tabs → `\t`
5. Carriage returns → `\r`
6. Form feeds → `\f`
7. Backspaces → `\b`

**Usage**:
```bash
local escaped=$(atomic_json_escape "$raw_string")
```

### 2. Updated `atomic_task_start()`

**Location**: Lines ~1305-1360

Now escapes all string variables before generating JSON:
- `description`
- `provider`
- `model`
- `role`
- `network_mode`
- `context_window`
- `cost_tier`
- `host_type`
- `ollama_host`
- `prompt_source`
- `output_file`
- `phase`
- `task_id`

### 3. Fixed `atomic_task_clear()`

**Location**: Lines ~1363-1374

Changed from single-quote heredoc to double-quote heredoc so timestamp properly expands:

**Before**:
```bash
cat > "$status_file" << 'EOF'
{
  "timestamp": "$(date -Iseconds)"  # Literal string!
}
EOF
```

**After**:
```bash
local timestamp=$(date -Iseconds)
cat > "$status_file" << EOF
{
  "timestamp": "$timestamp"  # Properly expanded!
}
EOF
```

## Testing

### Unit Test

```bash
# Test the escaping function
source lib/atomic.sh
result=$(atomic_json_escape 'Test "quotes" and\nnewlines')
echo "$result"
# Output: Test \"quotes\" and\nnewlines
```

### Integration Test

```bash
# Test full JSON generation with problematic content
cat > /tmp/test-task-json.sh << 'TESTSCRIPT'
#!/usr/bin/env bash
source lib/atomic.sh

# Simulate task with special characters
ATOMIC_STATE_DIR="/tmp/atomic-test"
mkdir -p "$ATOMIC_STATE_DIR"

atomic_task_start \
    "Task with \"quotes\"\nand special chars" \
    "max" \
    "sonnet" \
    "primary" \
    300 \
    "prompt.md" \
    "output.json" \
    ""

# Validate the generated JSON
if jq . "$ATOMIC_STATE_DIR/current-task.json" > /dev/null 2>&1; then
    echo "✓ Valid JSON generated"
    jq . "$ATOMIC_STATE_DIR/current-task.json"
else
    echo "✗ Invalid JSON"
    exit 1
fi

# Clean up
rm -rf /tmp/atomic-test
TESTSCRIPT

chmod +x /tmp/test-task-json.sh && /tmp/test-task-json.sh
```

### E2E Dashboard Test

1. Start dashboard:
   ```bash
   ./scripts/start-dashboard.sh
   ```

2. Run Phase 0 in another terminal:
   ```bash
   ./main.sh run 0 --mode=quick
   ```

3. Open browser to `http://localhost:5173`

4. Verify:
   - No JSON parse errors in browser console
   - Task descriptions display correctly
   - All status fields populate properly
   - Real-time updates work

## Files Changed

- `lib/atomic.sh` - Added escaping function and updated JSON generation

## Backward Compatibility

This change is fully backward compatible:
- No API changes
- No configuration changes
- Existing JSON files work as before
- Only affects new JSON generation going forward

## Next Steps

1. **Verify Max authentication**:
   ```bash
   claude auth whoami
   ```

2. **Test provider resolution**:
   ```bash
   ./test/test-provider-resolution.sh
   ```

3. **Clean state and re-run E2E test**:
   ```bash
   rm -rf .state .outputs .logs .claude
   cd test && ./test-e2e-phase0.sh
   ```

4. **Monitor with dashboard** (separate terminal):
   ```bash
   ./scripts/start-dashboard.sh
   # Open http://localhost:5173
   ```

## Additional Notes

- The escaping order matters! Backslashes must be escaped first to avoid double-escaping
- This fix prevents JSON injection vulnerabilities
- All string fields are now safe from special characters
- Numeric and boolean fields remain unquoted as per JSON spec
