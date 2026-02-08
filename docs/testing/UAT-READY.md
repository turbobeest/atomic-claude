# UAT Runner - Ready to Use

## ✅ What's Been Created

The User Acceptance Test (UAT) runner is now complete and ready to validate the full Phase 00 and Phase 01 user experience.

### Files Created

1. **test/uat_runner.py** (executable)
   - Automated UAT orchestrator with prescribed inputs
   - Feeds inputs automatically to simulate user interaction
   - Shows full task-to-task UX flow
   - Verifies outputs and displays summary

2. **test/run_uat.sh** (executable)
   - Wrapper script for easy execution
   - Colored output and error handling
   - Usage: `./test/run_uat.sh [options]`

3. **test/fixtures/uat_setup.md**
   - Comprehensive test configuration
   - Project: uat-test-project (simulating atomic-claude2 refactoring)
   - Includes reference materials and success criteria

4. **test/fixtures/reference/** (3 files)
   - `architecture.md`: System architecture documentation
   - `requirements.md`: Functional and non-functional requirements
   - `technical-spec.md`: Detailed technical specifications

5. **UAT-QUICK-START.md**
   - Complete usage guide
   - Troubleshooting section
   - Customization instructions

## 🚀 How to Run

### Option 1: Full UAT (Recommended)

```bash
cd /Users/jamesterbeest/dev/atomic-claude2
./test/run_uat.sh
```

This runs both Phase 00 and Phase 01 with prescribed inputs, showing the full UX flow.

### Option 2: Single Phase

```bash
# Phase 00 only
./test/run_uat.sh --phase 0

# Phase 01 only
./test/run_uat.sh --phase 1
```

### Option 3: With Options

```bash
# Verbose output
./test/run_uat.sh --verbose

# Pause between tasks for review
./test/run_uat.sh --pause

# Combine options
./test/run_uat.sh --phase 0 --verbose
```

## 📋 Prescribed Inputs

The UAT runner automatically feeds these inputs:

### Phase 00 (Setup)
- Task 001: `""` (Press Enter to use setup.md)
- Task 003: `"a"` (Approve configuration)
- Task 004: `""` (Auto-detect API keys)
- Task 006: `"3"` (Skip reference materials)

### Phase 01 (Discovery)
- Task 101: `""` (Entry validation - press Enter)
- Task 102: `"", ""` (No additional materials, press Enter twice)
- Task 103: `"n"` (No existing requirements)
- Task 104: `"a"` (Approve selected agents)
- Task 105: Multi-line vision statement (UAT test description)
- Task 107: `"1"` (Select first approach)
- Task 108: `"y"` (Generate diagrams)
- Task 109: `"y"` (Approve phase audit)
- Task 110: `"y"` (Approve closeout)

## ✅ Expected Output

You'll see:

1. **Setup Phase**
   - Environment cleanup
   - Setup.md copied to initialization/
   - .env validation

2. **Phase 00 Execution**
   - All 6 tasks running with full UX visible
   - Prescribed inputs fed automatically
   - Task-to-task transitions
   - Output files created

3. **Phase 01 Execution**
   - All 10 tasks running with full UX visible
   - Agent selection, vision capture, approach selection
   - Diagram generation (if LLM available)
   - Audit execution
   - Closeout approval

4. **Verification**
   - Output files verified
   - State tracking checked
   - Summary displayed

5. **Final Status**
   ```
   ================================================================================
     ✓ UAT PASSED - All phases completed successfully
   ================================================================================
   ```

## 📦 Output Structure

After successful UAT:

```
.outputs/
├── 0-setup/
│   ├── project-config.json  # Project configuration
│   ├── secrets.json         # API keys and credentials
│   └── closeout.json        # Phase completion marker
└── 1-discovery/
    ├── closeout.json        # Phase completion marker
    ├── selected-agents.json # Agent selections (if LLM available)
    └── vision.md            # Project vision (if LLM available)

.state/
└── task-state.json          # Task completion tracking
```

## 🔍 What Makes This UAT (Not Just Testing)

This is **User Acceptance Testing** because:

1. ✅ **Full UX visible**: You see every prompt, every input, every transition
2. ✅ **Realistic flow**: Prescribed inputs match real user interactions
3. ✅ **Operational**: Actually runs the system, not just mocks
4. ✅ **Acceptance-focused**: Validates user experience, not just exit codes

The previous test_runner.py only checked exit codes - the UAT runner shows you **what users will actually experience**.

## 🎯 Success Criteria

UAT passes when:
- ✅ Phase 00 completes all 6 tasks without errors
- ✅ Phase 01 completes all 10 tasks without errors
- ✅ All expected output files are created
- ✅ State tracking persists correctly
- ✅ Full UX flow is visible and logical

## 🐛 Troubleshooting

### No API Keys
UAT will run but LLM tasks will fail gracefully. For full testing:
```bash
# Add to .env
ANTHROPIC_API_KEY=your-key-here
```

### Missing Initialization Directory
The UAT runner creates this automatically as a sibling to atomic-claude2:
```
/Users/jamesterbeest/dev/initialization/
```

### Permission Denied
```bash
chmod +x test/run_uat.sh
chmod +x test/uat_runner.py
```

## 📖 More Information

See **UAT-QUICK-START.md** for:
- Detailed troubleshooting
- Customization instructions
- Adding more phases
- Modifying prescribed inputs

## 🎉 Ready to Test!

The UAT runner is complete and ready to validate your Phase 00 and Phase 01 implementation.

Run in a separate terminal window as requested:
```bash
cd /Users/jamesterbeest/dev/atomic-claude2
./test/run_uat.sh
```

You'll see the full user journey from initial setup through discovery phase completion!
