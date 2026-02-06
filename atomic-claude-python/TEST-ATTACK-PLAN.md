# Multi-Pronged Test Attack Plan

**Date:** February 3, 2026
**Target:** ATOMIC CLAUDE Python Implementation
**Objective:** Comprehensive validation of all systems

---

## 🎯 Test Strategy Overview

We'll attack testing from 7 different angles to ensure bulletproof validation:

```
Layer 7: Performance & Benchmarks
Layer 6: Error Handling & Edge Cases
Layer 5: Provider Fallback & Recovery
Layer 4: Hybrid Mode (Python CLI → Bash Phases)
Layer 3: End-to-End Workflows
Layer 2: Integration Tests (49 tests)
Layer 1: Unit Tests (smoke tests)
```

Each layer builds confidence in the layer above it.

---

## 📋 Test Execution Plan

### Phase 1: Foundation (5 minutes)
**Goal:** Verify core functionality works

#### 1.1 Unit Tests (Smoke Tests) ✅
```bash
python3 tests/test_basic.py
```
**Expected:** All pass, no warnings
**Status:** Already verified passing

#### 1.2 Import Validation
```bash
python3 << 'EOF'
# Test all imports
from lib import atomic, provider, memory, phase, task_state
from lib.atomic import atomic_invoke
from lib.provider import ProviderManager
print("✅ All imports successful")
EOF
```
**Expected:** No errors, clean output

#### 1.3 CLI Commands
```bash
python3 main.py list
python3 main.py status
python3 main.py providers
```
**Expected:** Clean formatted output, no errors

---

### Phase 2: Integration Testing (15 minutes)
**Goal:** Verify modules work together

#### 2.1 Install pytest
```bash
pip install -r tests/requirements.txt
```

#### 2.2 Run Integration Test Suite
```bash
# Run all 49 tests
pytest tests/test_integration.py -v

# Or use test runner
./run_tests.sh
```
**Expected:** 49 tests pass (or identify failures for fixing)

#### 2.3 Module-Specific Tests
```bash
# Test each module individually
pytest tests/test_integration.py::TestAtomicModule -v
pytest tests/test_integration.py::TestProviderModule -v
pytest tests/test_integration.py::TestMemoryModule -v
pytest tests/test_integration.py::TestPhaseModule -v
pytest tests/test_integration.py::TestTaskStateModule -v
pytest tests/test_integration.py::TestIntegration -v
```
**Expected:** Each test class passes independently

#### 2.4 Coverage Report
```bash
./run_tests.sh --html-coverage
```
**Expected:** Coverage report generated in htmlcov/index.html

---

### Phase 3: Real LLM Invocations (10 minutes)
**Goal:** Verify actual Claude API integration works

#### 3.1 Simple Invocation (Haiku)
```bash
cat > /tmp/test_simple.md << 'EOF'
Respond with exactly: {"test": "success"}
EOF

python3 << 'EOF'
from lib.atomic import atomic_invoke
result = atomic_invoke(
    "/tmp/test_simple.md",
    "/tmp/test_output.json",
    "Test simple invocation",
    model="haiku",
    format_type="json",
    timeout=30
)
print(f"✅ Result: {result}")
with open("/tmp/test_output.json") as f:
    print(f"Output: {f.read()}")
EOF
```
**Expected:** Success, valid JSON output

#### 3.2 Complex Invocation (Sonnet)
```bash
cat > /tmp/test_complex.md << 'EOF'
Analyze this code and respond with JSON:
```python
def add(a, b):
    return a + b
```
Return: {"language": "python", "function": "add", "complexity": "simple"}
EOF

python3 << 'EOF'
from lib.atomic import atomic_invoke
result = atomic_invoke(
    "/tmp/test_complex.md",
    "/tmp/test_complex_output.json",
    "Test complex analysis",
    model="sonnet",
    format_type="json",
    timeout=60
)
print(f"✅ Result: {result}")
EOF
```
**Expected:** Success, complex analysis completed

#### 3.3 Markdown Output (No JSON)
```bash
cat > /tmp/test_markdown.md << 'EOF'
Write a brief haiku about Python.
EOF

python3 << 'EOF'
from lib.atomic import atomic_invoke
result = atomic_invoke(
    "/tmp/test_markdown.md",
    "/tmp/test_haiku.md",
    "Test markdown output",
    model="haiku",
    timeout=30
)
print(f"✅ Result: {result}")
with open("/tmp/test_haiku.md") as f:
    print(f"Haiku:\n{f.read()}")
EOF
```
**Expected:** Success, markdown output generated

#### 3.4 Timeout Test
```bash
cat > /tmp/test_timeout.md << 'EOF'
This is a test. Respond with: OK
EOF

python3 << 'EOF'
from lib.atomic import atomic_invoke
result = atomic_invoke(
    "/tmp/test_timeout.md",
    "/tmp/test_timeout.json",
    "Test timeout handling",
    model="haiku",
    timeout=1  # Very short timeout
)
print(f"Result: {result}")
EOF
```
**Expected:** Either success (if fast) or graceful timeout handling

---

### Phase 4: Hybrid Mode Testing (20 minutes)
**Goal:** Verify Python CLI can orchestrate bash phase runners

#### 4.1 List Phases
```bash
python3 main.py list
```
**Expected:** Shows all 10 phases with status

#### 4.2 Check Provider Availability
```bash
python3 main.py providers
```
**Expected:** Shows which providers are available

#### 4.3 Check Pipeline Status
```bash
python3 main.py status
```
**Expected:** Shows current phase and task status

#### 4.4 Reset Pipeline (Dry Run)
```bash
# Check what would be reset
ls -la .state/ .outputs/ .claude/
python3 main.py reset
# Verify state is clean
```
**Expected:** State directories cleaned

#### 4.5 Run Phase 0 (Setup)
```bash
# This is the critical test - Python CLI calling bash phase runner
python3 main.py run 0

# Or with mode flag
python3 main.py run 0 --mode=quick
```
**Expected:** Phase 0 executes via bash runner, no errors
**Note:** This tests the hybrid architecture end-to-end

---

### Phase 5: Provider Fallback Testing (15 minutes)
**Goal:** Verify provider routing and fallback chains work

#### 5.1 Test Provider Detection
```bash
python3 << 'EOF'
from lib.provider import ProviderManager

pm = ProviderManager()
print("Provider Availability:")
print(f"  Max: {pm.is_max_available()}")
print(f"  API: {pm.is_api_available()}")
print(f"  Bedrock: {pm.is_bedrock_available()}")
print(f"  Ollama: {pm.is_ollama_available()}")
EOF
```
**Expected:** Correct detection of available providers

#### 5.2 Test Provider Chain
```bash
python3 << 'EOF'
from lib.provider import ProviderManager

pm = ProviderManager()
chain = pm.get_provider_chain("primary", "sonnet")
print(f"Primary provider chain: {chain}")
EOF
```
**Expected:** Returns fallback chain (e.g., ["max", "api", "bedrock"])

#### 5.3 Test Provider for Task Type
```bash
python3 << 'EOF'
from lib.provider import ProviderManager

pm = ProviderManager()
tasks = ["primary", "fast", "gardener", "heavyweight"]
for task in tasks:
    provider = pm.get_provider_for_task(task)
    print(f"{task}: {provider}")
EOF
```
**Expected:** Correct provider selection per task type

#### 5.4 Test Forced Provider Override
```bash
python3 << 'EOF'
from lib.atomic import atomic_invoke

# Force specific provider
result = atomic_invoke(
    "/tmp/test_simple.md",
    "/tmp/test_forced.json",
    "Test forced provider",
    provider="bedrock",
    model="haiku"
)
print(f"✅ Forced provider test: {result}")
EOF
```
**Expected:** Uses specified provider, ignores fallback chain

---

### Phase 6: Error Handling & Edge Cases (20 minutes)
**Goal:** Verify graceful failure and recovery

#### 6.1 Missing Prompt File
```bash
python3 << 'EOF'
from lib.atomic import atomic_invoke

result = atomic_invoke(
    "/tmp/nonexistent_prompt.md",
    "/tmp/output.json",
    "Test missing prompt",
    model="haiku"
)
print(f"Result (should be False): {result}")
EOF
```
**Expected:** Returns False, clear error message

#### 6.2 Invalid JSON Format Request
```bash
cat > /tmp/test_invalid_json.md << 'EOF'
Just respond with plain text, not JSON.
EOF

python3 << 'EOF'
from lib.atomic import atomic_invoke

result = atomic_invoke(
    "/tmp/test_invalid_json.md",
    "/tmp/test_invalid_output.json",
    "Test invalid JSON",
    model="haiku",
    format_type="json"  # Expects JSON but won't get it
)
print(f"Result: {result}")
EOF
```
**Expected:** Handles invalid JSON gracefully

#### 6.3 Missing Dependencies
```bash
python3 << 'EOF'
from lib.atomic import atomic_validate_deps

# Test non-strict mode (should pass even with missing optional deps)
result = atomic_validate_deps(strict=False)
print(f"Non-strict: {result}")

# Test strict mode (might fail if optional deps missing)
result = atomic_validate_deps(strict=True)
print(f"Strict: {result}")
EOF
```
**Expected:** Non-strict passes, strict may fail with clear message

#### 6.4 State Corruption Recovery
```bash
# Corrupt state file
echo "invalid json" > .state/task-state.json

python3 << 'EOF'
from lib.task_state import TaskStateManager

try:
    tsm = TaskStateManager("test-phase")
    print("State manager initialized despite corruption")
except Exception as e:
    print(f"Handled corruption: {e}")
EOF

# Clean up
rm .state/task-state.json
```
**Expected:** Graceful handling or recovery

#### 6.5 Concurrent State Access
```bash
python3 << 'EOF'
from lib.task_state import TaskStateManager
import threading

def access_state(n):
    tsm = TaskStateManager("test-phase")
    tsm.task_start(f"task-{n}", f"Test Task {n}")
    tsm.task_complete(f"task-{n}", f"Test Task {n}")

threads = [threading.Thread(target=access_state, args=(i,)) for i in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()

print("✅ Concurrent access completed")
EOF
```
**Expected:** No race conditions, all tasks recorded

#### 6.6 Memory Module Disabled
```bash
# Test with memory disabled
unset ATOMIC_MEMORY_ENABLED

python3 << 'EOF'
from lib.memory import memory_init, memory_should_persist

memory_init()
should_persist = memory_should_persist()
print(f"Memory persistence (should be False): {should_persist}")
EOF
```
**Expected:** Memory functions gracefully when disabled

---

### Phase 7: Performance & Benchmarks (15 minutes)
**Goal:** Compare Python vs Bash performance

#### 7.1 Startup Time Comparison
```bash
# Bash startup
time bash -c "source ../lib/atomic.sh; echo ok" > /dev/null

# Python startup
time python3 -c "from lib import atomic; print('ok')" > /dev/null
```
**Expected:** Python startup ~50% faster

#### 7.2 JSON Parsing Benchmark
```bash
# Create test JSON
cat > /tmp/test_large.json << 'EOF'
{"data": [1,2,3,4,5,6,7,8,9,10], "nested": {"key1": "value1", "key2": "value2"}}
EOF

# Bash (jq)
time bash -c "cat /tmp/test_large.json | jq -r '.data[0]'" > /dev/null

# Python (native)
time python3 -c "import json; data=json.load(open('/tmp/test_large.json')); print(data['data'][0])" > /dev/null
```
**Expected:** Python JSON parsing significantly faster

#### 7.3 State File Operations
```bash
# Benchmark state read/write
python3 << 'EOF'
import time
from lib.task_state import TaskStateManager

# Write benchmark
start = time.time()
tsm = TaskStateManager("perf-test")
for i in range(100):
    tsm.task_start(f"task-{i}", f"Task {i}")
    tsm.task_complete(f"task-{i}", f"Task {i}")
write_time = time.time() - start

print(f"100 state operations: {write_time:.3f}s ({100/write_time:.1f} ops/sec)")
EOF
```
**Expected:** Fast state operations (>100 ops/sec)

#### 7.4 Provider Check Performance
```bash
python3 << 'EOF'
import time
from lib.provider import ProviderManager

start = time.time()
pm = ProviderManager()
for i in range(10):
    pm.is_max_available()
    pm.is_api_available()
    pm.is_bedrock_available()
check_time = time.time() - start

print(f"30 provider checks: {check_time:.3f}s")
EOF
```
**Expected:** Provider checks cached, fast repeated calls

---

## 🎯 Test Execution Checklist

### Pre-Flight Checks
- [ ] In atomic-claude-python directory
- [ ] Python 3.7+ available (`python3 --version`)
- [ ] pip installed (`pip --version`)
- [ ] Git status clean (optional)

### Phase 1: Foundation (5 min)
- [ ] 1.1 Unit tests passing
- [ ] 1.2 All imports successful
- [ ] 1.3 CLI commands working

### Phase 2: Integration (15 min)
- [ ] 2.1 pytest installed
- [ ] 2.2 49 integration tests passing
- [ ] 2.3 Module-specific tests passing
- [ ] 2.4 Coverage report generated

### Phase 3: Real LLM (10 min)
- [ ] 3.1 Simple invocation works
- [ ] 3.2 Complex invocation works
- [ ] 3.3 Markdown output works
- [ ] 3.4 Timeout handling works

### Phase 4: Hybrid Mode (20 min)
- [ ] 4.1 List phases works
- [ ] 4.2 Provider check works
- [ ] 4.3 Status check works
- [ ] 4.4 Reset works
- [ ] 4.5 Phase 0 execution works

### Phase 5: Provider Fallback (15 min)
- [ ] 5.1 Provider detection accurate
- [ ] 5.2 Provider chain correct
- [ ] 5.3 Task type routing correct
- [ ] 5.4 Forced provider works

### Phase 6: Error Handling (20 min)
- [ ] 6.1 Missing file handled
- [ ] 6.2 Invalid JSON handled
- [ ] 6.3 Dependencies checked
- [ ] 6.4 State corruption handled
- [ ] 6.5 Concurrent access safe
- [ ] 6.6 Disabled memory works

### Phase 7: Performance (15 min)
- [ ] 7.1 Startup time faster
- [ ] 7.2 JSON parsing faster
- [ ] 7.3 State operations fast
- [ ] 7.4 Provider checks cached

---

## 📊 Success Criteria

### Must Pass (Blocking)
- ✅ All unit tests pass
- ✅ Integration tests pass (can have some skipped for missing deps)
- ✅ At least one real LLM invocation succeeds
- ✅ CLI commands work
- ✅ Hybrid mode Phase 0 executes

### Should Pass (Important)
- ✅ Provider detection accurate
- ✅ Error handling graceful
- ✅ No state corruption
- ✅ Performance better than bash

### Nice to Have (Optional)
- ✅ 100% test coverage
- ✅ All edge cases handled
- ✅ Benchmark results documented

---

## 🚨 Failure Response Plan

### If Unit Tests Fail
1. Check import errors
2. Verify Python version (3.7+)
3. Review missing dependencies
4. Fix and re-run

### If Integration Tests Fail
1. Run with `-v` for verbose output
2. Check specific test class failing
3. Review mocking issues
4. Fix and re-run specific tests

### If LLM Invocation Fails
1. Check provider availability (`main.py providers`)
2. Verify network connectivity
3. Check API keys in .env
4. Try different provider
5. Check logs in .logs/

### If Hybrid Mode Fails
1. Verify bash phases exist (`ls ../phases/`)
2. Check subprocess execution
3. Review phase runner logs
4. Test bash phase directly first
5. Check file permissions

---

## 📝 Test Results Template

Use this to track results:

```markdown
## Test Results - [Date]

### Phase 1: Foundation ✅/❌
- Unit tests: ✅/❌
- Imports: ✅/❌
- CLI: ✅/❌

### Phase 2: Integration ✅/❌
- Test suite: ✅/❌ (X/49 passed)
- Coverage: X%

### Phase 3: Real LLM ✅/❌
- Simple: ✅/❌
- Complex: ✅/❌
- Markdown: ✅/❌
- Timeout: ✅/❌

### Phase 4: Hybrid Mode ✅/❌
- List: ✅/❌
- Providers: ✅/❌
- Status: ✅/❌
- Reset: ✅/❌
- Phase 0: ✅/❌

### Phase 5: Provider Fallback ✅/❌
- Detection: ✅/❌
- Chain: ✅/❌
- Routing: ✅/❌
- Override: ✅/❌

### Phase 6: Error Handling ✅/❌
- Missing file: ✅/❌
- Invalid JSON: ✅/❌
- Dependencies: ✅/❌
- State corruption: ✅/❌
- Concurrent: ✅/❌
- Disabled memory: ✅/❌

### Phase 7: Performance ✅/❌
- Startup: X% faster
- JSON: X% faster
- State ops: X ops/sec
- Provider cache: Working

### Overall Status: ✅/❌
- Critical issues: X
- Warnings: X
- Recommendations: [list]
```

---

## 🚀 Quick Start Test Run

For a fast validation (5 minutes):

```bash
# 1. Unit tests
python3 tests/test_basic.py

# 2. One integration test
pytest tests/test_integration.py::TestAtomicModule -v

# 3. Real LLM invocation
cat > /tmp/quick_test.md << 'EOF'
Say: {"status": "ok"}
EOF
python3 << 'PYEOF'
from lib.atomic import atomic_invoke
result = atomic_invoke("/tmp/quick_test.md", "/tmp/quick_out.json", "Quick test", model="haiku", format_type="json")
print(f"✅ Quick test: {result}")
PYEOF

# 4. CLI
python3 main.py list

# 5. Providers
python3 main.py providers
```

If all 5 pass → System is working!

---

## 📚 Documentation References

- `tests/README.md` - Complete testing guide
- `TESTING_QUICKSTART.md` - Quick commands
- `TEST_IMPLEMENTATION_SUMMARY.md` - Test details
- `COMPLETION-STATUS.md` - Current status

---

**Total Estimated Time:** 100 minutes (1h 40min)
**Minimum Time (Quick):** 5 minutes
**Recommended Time:** 30-45 minutes (Phases 1-4)

Ready to execute! 🎯
