# E2E Testing System for ATOMIC CLAUDE

Automated end-to-end testing system for rapid UI inspection and functionality validation.

## Quick Start

### 1. Automated Testing (Fastest)

Run Phase 0 with simulated user inputs:

```bash
cd /Users/jamesterbeest/dev/test-project
./test-e2e-phase0.sh minimal
```

This will:
- Clean previous test state
- Run Phase 0 with automated inputs
- Generate test log
- Report results

### 2. Interactive Testing (UI Inspection)

Run Phase 0 normally while monitoring execution:

**Terminal 1 - Run Test:**
```bash
cd /Users/jamesterbeest/dev/test-project
./test-e2e-phase0.sh interactive
```

**Terminal 2 - Monitor Execution:**
```bash
cd /Users/jamesterbeest/dev/test-project
./monitor-e2e-test.sh
```

The monitor shows:
- Current task and duration
- Provider/model being used
- Real-time error detection
- UI feature checks (dashboard, navigation, etc.)
- Performance evaluation
- Task completion statistics

### 3. Custom Testing (Specific Tasks)

Start from a specific task:

```bash
./test-e2e-phase0.sh custom 003
```

## Test Modes

### Minimal (Automated)
```bash
./test-e2e-phase0.sh minimal
```
- Automatically answers all prompts
- Minimal inputs for rapid testing
- Ideal for regression testing
- Completes in ~2-5 minutes

### Interactive (Manual)
```bash
./test-e2e-phase0.sh interactive
```
- Normal Phase 0 execution
- Manual input at each prompt
- Best for UI polish and inspection
- Run monitor in separate terminal

### Custom (Partial)
```bash
./test-e2e-phase0.sh custom 005
```
- Starts from specific task
- Resume testing after fixing issues
- Skips earlier tasks

## Monitoring Features

The `monitor-e2e-test.sh` script provides real-time evaluation:

### What It Checks

**Task Execution:**
- Task duration tracking
- Performance evaluation (<30s excellent, 30-60s acceptable, >60s slow)
- Error detection in real-time
- Provider/model selection verification

**UI Features:**
- Dashboard availability (port 5173)
- Task state tracking
- Output file generation
- Navigation prompts presence

**Statistics:**
- Total tasks monitored
- Error count
- Warning count
- Phase duration
- Per-task durations

### Monitor Output Example

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Task: Extract configuration from setup
Duration: 23s
Provider: aws-bedrock
Model: claude-sonnet-4-5
Active: true
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

UI Feature Checks:
  ✓ Dashboard running on port 5173
  ✓ Task state tracking active
  ✓ Output directory created (5 files)
  ✓ Navigation prompts present

Statistics:
  Tasks Monitored: 3
  Errors: 0
  Warnings: 0
  Phase Duration: 145s
```

## Workflow for Polishing UI

### Step 1: Run Automated Test

```bash
# Terminal 1
./test-e2e-phase0.sh minimal

# Check log for issues
cat e2e-test.log
```

### Step 2: Interactive Testing with Monitoring

```bash
# Terminal 1 - Monitor
./monitor-e2e-test.sh

# Terminal 2 - Run test
./test-e2e-phase0.sh interactive
```

**Inspect each task:**
- Verify prompt formatting
- Check color codes rendering
- Test navigation (c/r/b/q)
- Validate error messages
- Confirm success indicators

### Step 3: Fix Issues and Re-test

If you find UI issues:

1. Make changes to relevant files
2. Sync to test-project:
   ```bash
   cd /Users/jamesterbeest/dev/atomic-claude
   make sync  # or rsync manually
   ```
3. Re-run specific task:
   ```bash
   ./test-e2e-phase0.sh custom 003
   ```

## Test Inputs Reference

The automated test provides these inputs:

```
Task 001: [Enter]           - Confirm setup.md ready
Task 002: [auto]            - Uses pre-detected setup file
Task 003: a                 - Approve configuration
Task 004: skip, skip, skip  - Skip API key setup
Task 005: [Enter]           - Continue with defaults
Task 006: [Enter]           - Accept reference materials
Task 007: y                 - Confirm environment
Task 008: [Enter]           - Repository defaults
Task 009: c                 - Continue through remaining
```

## Customization

### Modify Test Inputs

Edit `/tmp/phase0-inputs.txt` section in `test-e2e-phase0.sh`:

```bash
cat > /tmp/phase0-inputs.txt << 'INPUTS'

a            # Task 003: approve
my-key       # Task 004: custom API key
skip         # Task 004: skip additional keys
c            # Continue
INPUTS
```

### Add Custom Checks

Edit `monitor-e2e-test.sh` and add to `check_ui_features()`:

```bash
# Check for custom feature
if [[ condition ]]; then
    echo -e "  ${GREEN}✓${NC} My feature working"
else
    echo -e "  ${RED}✗${NC} My feature broken"
fi
```

## Logs and Artifacts

**Test Log:**
- Location: `e2e-test.log`
- Contains: Full execution output, timestamps, results

**Task State:**
- Location: `ATOMIC-CLAUDE/.state/current-task.json`
- Contains: Active task info, provider, model

**Outputs:**
- Location: `ATOMIC-CLAUDE/.outputs/0-setup/`
- Contains: project-config.json, extracted-config.json, etc.

**Invocation Logs:**
- Location: `ATOMIC-CLAUDE/.logs/invocations.log`
- Contains: LLM call details, responses

## Cleanup

After testing:

```bash
# Remove test artifacts
rm -f e2e-test.log

# Clean test state (preserves backup)
rm -rf ATOMIC-CLAUDE/.claude
rm -rf ATOMIC-CLAUDE/.state
rm -rf ATOMIC-CLAUDE/.outputs
rm -rf ATOMIC-CLAUDE/.logs

# Restore original setup.md (automatic on test end)
cp ATOMIC-CLAUDE/initialization/setup.md.backup ATOMIC-CLAUDE/initialization/setup.md
```

## Troubleshooting

### Test hangs
- Check if dashboard is blocking (PID state 'T')
- Kill suspended processes: `pkill -9 node`
- Re-run test

### Monitor shows no activity
- Verify Phase 0 is actually running
- Check `.state/current-task.json` exists
- Ensure both scripts have execute permissions

### Automated inputs don't work
- Verify `/tmp/phase0-inputs.txt` was created
- Check for prompt format changes
- Add debug echo statements to test script

## Example Testing Session

```bash
# 1. Quick regression test
./test-e2e-phase0.sh minimal

# 2. If issues found, run with monitor
tmux new-session -d -s e2e './monitor-e2e-test.sh'
tmux split-window -h './test-e2e-phase0.sh interactive'
tmux attach -t e2e

# 3. Fix issues in main repo
cd /Users/jamesterbeest/dev/atomic-claude
# Make changes...

# 4. Sync and re-test specific task
make sync
cd /Users/jamesterbeest/dev/test-project
./test-e2e-phase0.sh custom 005

# 5. Final full test
./test-e2e-phase0.sh minimal
cat e2e-test.log | grep -i error
```

## Next Steps

**Expand to Other Phases:**
- Create `test-e2e-phase1.sh`, `test-e2e-phase2.sh`, etc.
- Reuse monitoring infrastructure
- Build full pipeline E2E suite

**Add Assertions:**
- Validate output file structure
- Check config values extracted correctly
- Verify agent selection logic

**Performance Benchmarking:**
- Track task durations over time
- Compare provider performance
- Identify slow operations
