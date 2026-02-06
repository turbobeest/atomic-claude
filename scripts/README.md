# Pipeline Scripts

Utility scripts for managing the ATOMIC CLAUDE pipeline.

## reset-task.py / reset.sh

Reset pipeline state by removing tasks and deleting their output files.

### Usage

**Reset single task:**
```bash
./scripts/reset.sh 109
```

**Reset task and all after it:**
```bash
./scripts/reset.sh 109 --and-after
```

**Reset entire phase:**
```bash
./scripts/reset.sh --phase 1
```

### What It Does

1. Removes task(s) from `.claude/task-state.json`
2. Deletes output files from `.outputs/{phase}/`
3. Deletes prompt files from `.outputs/{phase}/prompts/`

### Examples

**Scenario: Task 205 failed, need to retry**
```bash
# Reset task 205
./scripts/reset.sh 205

# Continue pipeline
./run-atomic.sh run 2 --resume-at=205
```

**Scenario: Want to redo tasks 203-207**
```bash
# Reset from 203 onward
./scripts/reset.sh 203 --and-after

# Continue pipeline
./run-atomic.sh run 2 --resume-at=203
```

**Scenario: Restart entire Phase 1**
```bash
# Reset all Phase 1 tasks
./scripts/reset.sh --phase 1

# Restart Phase 1
./run-atomic.sh run 1
```

### Safety Notes

- **No confirmation prompt** - resets immediately
- **No undo** - changes are permanent
- **No backup** - deleted files are gone
- Use with care in production

For safer interactive reset with impact analysis, use the full recovery tool (when implemented).

## Other Scripts

- `start-dashboard.sh` - Start the web dashboard
- `sync-to-test-project.sh` - Sync code to test project
- `validate-state.sh` - Validate pipeline state files
