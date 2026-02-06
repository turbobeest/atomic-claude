# Quick Recovery Cheatsheet

Common error scenarios and how to recover using the reset tool.

## AWS Token Expired

**Error:**
```
API Error: Token is expired. To refresh this SSO session run 'aws sso login'
```

**Fix:**
```bash
# 1. Refresh token
aws sso login --profile bedrock-dev

# 2. Reset failed task
./scripts/reset.sh 205

# 3. Continue
./run-atomic.sh run 2 --resume-at=205
```

## Task Failed Mid-Execution

**Scenario:** Task 205 crashed, partial outputs created

**Fix:**
```bash
# Reset the failed task
./scripts/reset.sh 205

# Fix the underlying issue (code bug, missing file, etc.)

# Retry
./run-atomic.sh run 2 --resume-at=205
```

## Want to Redo Earlier Work

**Scenario:** Realized during task 207 that requirements in task 203 were wrong

**Fix:**
```bash
# Reset from task 203 onward (203, 204, 205, 206, 207)
./scripts/reset.sh 203 --and-after

# Redo the work
./run-atomic.sh run 2 --resume-at=203
```

## Phase Quality Poor - Restart Entire Phase

**Scenario:** Finished Phase 2 but PRD quality is unacceptable

**Fix:**
```bash
# Reset entire Phase 2
./scripts/reset.sh --phase 2

# Restart from beginning
./run-atomic.sh run 2
```

## Agent Selection Was Wrong

**Scenario:** Picked wrong agents in task 204, need different ones

**Fix:**
```bash
# Reset task 204 onward
./scripts/reset.sh 204 --and-after

# Select different agents
./run-atomic.sh run 2 --resume-at=204
```

## Network Error During LLM Call

**Scenario:** Network hiccup caused task 106 to fail

**Fix:**
```bash
# Check network is stable
ping anthropic.com

# Reset task
./scripts/reset.sh 106

# Retry
./run-atomic.sh run 1 --resume-at=106
```

## Memory System Corrupted

**Scenario:** Weird memory-related errors, suspect corruption

**Fix:**
```bash
# Nuclear option - clear all memory for the phase
rm -rf .state/memory/phase-2/*

# Reset phase
./scripts/reset.sh --phase 2

# Restart
./run-atomic.sh run 2
```

## Accidental Early Continue

**Scenario:** Hit Enter at prompt, skipped important review

**Fix:**
```bash
# Reset the task you skipped
./scripts/reset.sh 206

# Resume with proper review
./run-atomic.sh run 2 --resume-at=206
```

## Testing New Code Changes

**Scenario:** Modified task 205 code, want to test it

**Fix:**
```bash
# Reset task to test
./scripts/reset.sh 205

# Run with new code
./run-atomic.sh run 2 --resume-at=205
```

## Dashboard Shows Wrong State

**Scenario:** Dashboard task counts don't match reality

**Fix:**
```bash
# Restart dashboard
./scripts/start-dashboard.sh

# If still wrong, validate state file
./scripts/validate-state.sh

# Last resort - rebuild state by resuming from last good task
./scripts/reset.sh 205 --and-after
./run-atomic.sh run 2 --resume-at=205
```

## Tips

1. **Always check what will be reset:**
   - Single task: just that task
   - `--and-after`: that task + everything after in the phase
   - `--phase N`: entire phase N

2. **No undo** - reset is immediate and permanent

3. **Backup important files** before risky resets:
   ```bash
   cp docs/prd/PRD.md docs/prd/PRD.md.backup
   ```

4. **Resume from reset point:**
   ```bash
   # After reset, always use --resume-at
   ./run-atomic.sh run 2 --resume-at=205
   ```

5. **Check dependencies:**
   - Resetting task 203 preserves 201-202
   - Phase boundaries are respected
   - Memory checkpoints may need manual cleanup

## Getting Help

If none of these work:
1. Check `.logs/` for detailed error logs
2. Review `.claude/task-state.json` for state issues
3. Look at dashboard for visual state check
4. Check ISSUES-TRACKER.md for known bugs
