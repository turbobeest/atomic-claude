# UAT Quick Start Guide

## What is UAT?

User Acceptance Testing (UAT) validates the full user experience flow through Phase 00 (Setup) and Phase 01 (Discovery) with **prescribed inputs** automatically fed to each task.

This is NOT just exit code validation - you will see the **actual UX flow** from task to task, including all prompts, responses, and transitions.

## Prerequisites

1. **Environment setup**:
   ```bash
   cd /Users/jamesterbeest/dev/atomic-claude2
   ```

2. **API keys** (optional but recommended):
   - Create `.env` file in atomic-claude2 root
   - Add your API keys:
     ```bash
     ANTHROPIC_API_KEY=your-key-here
     # OR for Bedrock:
     AWS_PROFILE=your-profile
     AWS_REGION=us-east-1
     ```
   - UAT can run without API keys (will use mock mode)

3. **Dependencies**:
   - Python 3.8+
   - Bash 4.0+
   - jq (for JSON processing)

## Quick Start

### Run Full UAT (Phase 00 + Phase 01)

```bash
cd /Users/jamesterbeest/dev/atomic-claude2
./test/run_uat.sh
```

This will:
1. Clean previous UAT state
2. Copy test setup.md to ../initialization/
3. Run Phase 00 with prescribed inputs:
   - Task 001: Press Enter (use setup.md)
   - Task 003: 'a' (approve config)
   - Task 004: Press Enter (auto-detect API keys)
   - Task 006: '3' (skip reference materials)
4. Run Phase 01 with prescribed inputs:
   - Task 101: Press Enter (entry validation)
   - Task 102: Press Enter twice (no additional materials)
   - Task 103: 'n' (no existing requirements)
   - Task 104: 'a' (approve agents)
   - Task 105: Multi-line vision statement
   - Task 107: '1' (select first approach)
   - Task 108: 'y' (generate diagrams)
   - Task 109: 'y' (approve audit)
   - Task 110: 'y' (approve closeout)
5. Verify all outputs created
6. Show summary

### Run Single Phase

```bash
# Phase 00 only
./test/run_uat.sh --phase 0

# Phase 01 only
./test/run_uat.sh --phase 1
```

### Verbose Mode

```bash
./test/run_uat.sh --verbose
```

### Pause Between Tasks

```bash
./test/run_uat.sh --pause
```

## What You'll See

### During Execution

You'll see **real task execution** with:
- Task headers and descriptions
- All prompts as they appear to users
- Prescribed inputs being fed
- LLM responses (or mock responses if no API keys)
- Task transitions
- State tracking updates
- Output file creation

### Example Output

```
================================================================================
  SETTING UP UAT ENVIRONMENT
================================================================================

  Cleaning previous outputs...
  Cleaning previous state...

  ✓ Copied UAT setup.md to: /Users/jamesterbeest/dev/initialization/setup.md
  ✓ .env file found

  ✓ UAT environment ready

================================================================================
  RUNNING PHASE 00 (USER ACCEPTANCE TEST)
================================================================================

  Starting Phase 00...

┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 0: SETUP                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

Task 001: Setup Validation
[... full task execution visible ...]

  ✓ Phase 00 completed successfully

  Verifying Phase 00 outputs...
  ✓ project-config.json (2431 bytes)
  ✓ secrets.json (156 bytes)
  ✓ closeout.json (234 bytes)

================================================================================
  RUNNING PHASE 01 (USER ACCEPTANCE TEST)
================================================================================

  Starting Phase 01...

┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: DISCOVERY                                                          │
└─────────────────────────────────────────────────────────────────────────────┘

Task 101: Entry Validation
[... full task execution visible ...]

================================================================================
  UAT SUMMARY
================================================================================

  Outputs created:

  📁 0-setup/
     ✓ project-config.json (2431 bytes)
     ✓ secrets.json (156 bytes)
     ✓ closeout.json (234 bytes)

  📁 1-discovery/
     ✓ closeout.json (312 bytes)
     ✓ selected-agents.json (1847 bytes)
     ✓ vision.md (456 bytes)

  State tracking: .state/task-state.json
    0-setup: 6 tasks completed
    1-discovery: 10 tasks completed

================================================================================
  ✓ UAT PASSED - All phases completed successfully
================================================================================
```

## Test Data

The UAT uses realistic test data from:

- **test/fixtures/uat_setup.md**: Comprehensive project setup
  - Project: uat-test-project
  - Type: new-component
  - Tech stack: Python 3.11+, Click, subprocess, JSON
  - Reference materials: architecture, requirements, technical specs

- **test/fixtures/reference/**: Reference documentation
  - architecture.md: System architecture
  - requirements.md: Functional and non-functional requirements
  - technical-spec.md: Detailed technical specifications

## Success Criteria

UAT passes when:
1. ✅ Phase 00 completes all 6 tasks
2. ✅ Phase 01 completes all 10 tasks
3. ✅ All expected output files created:
   - .outputs/0-setup/project-config.json
   - .outputs/0-setup/secrets.json
   - .outputs/0-setup/closeout.json
   - .outputs/1-discovery/closeout.json
4. ✅ State tracking persists correctly (.state/task-state.json)
5. ✅ Full UX flow visible from task to task

## Troubleshooting

### "UAT setup.md not found"

```bash
# Check if fixture exists
ls -la test/fixtures/uat_setup.md

# If missing, it should have been created in the previous session
```

### ".env file not found" warning

This is normal if you don't have API keys configured. UAT can still run in mock mode (though LLM responses will be simulated).

To add API keys:
```bash
cat > .env << EOF
ANTHROPIC_API_KEY=your-key-here
EOF
```

### "Phase 01 failed"

Check that Phase 00 completed successfully first. Phase 01 requires:
- .outputs/0-setup/closeout.json
- .outputs/0-setup/project-config.json

### See full logs

```bash
# Check atomic logs
tail -f .logs/atomic.log

# Check task state
cat .state/task-state.json | jq .
```

## Customizing UAT

### Modify Prescribed Inputs

Edit `test/uat_runner.py` and update the `auto_input` strings in `run_phase_interactive()`:

```python
if phase_num == 0:
    auto_input = "\n".join([
        "",        # Task 001: Your custom input
        "a",       # Task 003: Your custom input
        # ...
    ])
```

### Change Test Setup

Edit `test/fixtures/uat_setup.md` to customize:
- Project name, type, description
- Tech stack
- LLM models
- Reference materials

### Add More Phases

Extend `phases` list in `main()` to include Phase 02+:
```python
phases = [args.phase] if args.phase is not None else [0, 1, 2]  # Add phase 2
```

## Next Steps

After UAT passes:
1. Continue implementing remaining phases (Phase 02-09)
2. Add UAT scenarios for each new phase
3. Extend test coverage with integration tests
4. Document any deviations from expected behavior

## Questions?

If UAT fails or behaves unexpectedly:
1. Check logs: `.logs/atomic.log`
2. Check state: `.state/task-state.json`
3. Check outputs: `.outputs/*/`
4. Run with --verbose for more details

The UAT runner is designed to show you **exactly what users will experience** - if something looks wrong in the flow, it probably is!
