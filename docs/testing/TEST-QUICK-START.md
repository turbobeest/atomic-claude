# Test Quick Start Guide

Run automated tests for Phase 00 & 01 **in a separate terminal window**.

---

## ⚡ Quick Start (Copy-Paste Ready)

### Option 1: Run All Tests

```bash
cd /Users/jamesterbeest/dev/atomic-claude2
./test/run_tests.sh
```

### Option 2: Run with Clean Environment

```bash
cd /Users/jamesterbeest/dev/atomic-claude2
./test/run_tests.sh --clean
```

### Option 3: Verbose Output

```bash
cd /Users/jamesterbeest/dev/atomic-claude2
./test/run_tests.sh --verbose
```

---

## 🎯 What Gets Tested

### Phase 00 (Setup)
- ✅ Task 001: Mode selection
- ✅ Task 002: Config collection
- ✅ Task 003: Config review
- ✅ Task 004: API keys
- ✅ Task 006: Reference materials
- ✅ Task 009: Environment check

### Phase 01 (Discovery)
- ✅ Task 101: Entry validation
- ✅ Phase 00 → 01 transition
- ✅ State tracking across phases

---

## 🚀 Expected Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ATOMIC CLAUDE 2.0 - AUTOMATED TEST SUITE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Python 3.11.8
✓ Repository: /Users/jamesterbeest/dev/atomic-claude2

ℹ Mock Mode Enabled - No LLM tokens will be consumed

Starting test runner...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ATOMIC CLAUDE 2.0 - TEST RUNNER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ℹ Setting up test environment...
  ✓ Copied test setup.md to initialization/setup.md
  ✓ Created minimal .env
  ✓ Test environment ready

  🧪 Testing Phase 00...
  ✓ Phase 00 PASSED

  ℹ Verifying Phase 00 outputs...
  ✓ project-config.json
  ✓ secrets.json
  ✓ closeout.json

  ℹ Verifying Phase 00 state tracking...
  ✓ 6 tasks tracked

  🧪 Testing Phase 01...
  ✓ Phase 01 PASSED

  ℹ Verifying Phase 01 outputs...
  ✓ closeout.json

  ℹ Verifying Phase 01 state tracking...
  ✓ 1 tasks tracked

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  TEST REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Tests:   2
Passed:        2 ✓
Failed:        0
Duration:      45.2s

Detailed report: test/test-report.json

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ALL TESTS PASSED ✓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🔍 Verification

Check test artifacts:

```bash
# View test outputs
ls -la .test-env/.outputs/0-setup/
ls -la .test-env/.outputs/1-discovery/

# View state tracking
cat .test-env/.state/task-state.json | jq .

# View test report
cat test/test-report.json | jq .
```

---

## 🎛️ Options

```bash
# Test specific phase only
./test/run_tests.sh --phase 0        # Phase 00 only
./test/run_tests.sh --phase 1        # Phase 01 only

# Clean test environment before running
./test/run_tests.sh --clean

# Verbose output (see all stdout/stderr)
./test/run_tests.sh --verbose

# Combine options
./test/run_tests.sh --phase 0 --verbose --clean
```

---

## ⏱️ Timing

- **Phase 00:** ~20 seconds (6 tasks)
- **Phase 01:** ~15 seconds (1 task tested)
- **Total:** ~45 seconds

Compare to real execution:
- **Phase 00 (real):** ~5 minutes + user input
- **Phase 01 (real):** ~10 minutes + user input

---

## ✅ Success Criteria

Tests pass if:

1. ✅ All phases return exit code 0
2. ✅ Expected output files created
3. ✅ State tracking updated
4. ✅ No errors in stderr
5. ✅ Mock responses generated

---

## 🛠️ Troubleshooting

### "Permission denied"

```bash
chmod +x test/run_tests.sh
```

### "Python not found"

```bash
# Use python3 explicitly
python3 test/test_runner.py
```

### Tests hang

- Interactive prompts may be blocking
- Use `--verbose` to see where it stops
- Press Ctrl+C to cancel

### Import errors

```bash
# Ensure you're in the repo root
cd /Users/jamesterbeest/dev/atomic-claude2
pwd  # Should show .../atomic-claude2
./test/run_tests.sh
```

---

## 📊 Test Coverage

### Currently Tested

- ✅ Phase 00: All 6 tasks
- ✅ Phase 01: Entry validation (Task 101)
- ✅ Phase transitions (00 → 01)
- ✅ State tracking
- ✅ Output generation
- ✅ Config loading

### Not Yet Tested

- ⏳ Phase 01: Tasks 102-110 (require user interaction)
- ⏳ Phase 02-09 (not yet extracted)
- ⏳ Error scenarios
- ⏳ Network failures
- ⏳ LLM timeouts

---

## 🚀 Next Steps

After successful test run:

1. ✅ Verify all tests passed
2. ✅ Check test report: `cat test/test-report.json`
3. ✅ Review outputs: `ls .test-env/.outputs/`
4. ✅ Continue with Phase 02 extraction

---

## 📝 Notes

- **No LLM tokens consumed** - All responses are mocked
- **Fast execution** - ~45 seconds total
- **Isolated environment** - Uses `.test-env/` directory
- **Reproducible** - Same results every time
- **Safe** - No real API calls

---

**Ready to test?** Open a new terminal and run:

```bash
cd /Users/jamesterbeest/dev/atomic-claude2
./test/run_tests.sh
```

🎉 Happy Testing!
