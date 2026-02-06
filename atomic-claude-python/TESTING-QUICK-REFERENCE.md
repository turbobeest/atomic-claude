# Testing Quick Reference Card

**Last Updated:** February 3, 2026

---

## 🚀 Quick Commands

### Run All Tests (Automated)
```bash
# Full test suite (~100 minutes)
./run_attack_tests.sh

# Quick validation (~5 minutes)
./run_attack_tests.sh --quick

# Skip LLM tests (saves API calls)
./run_attack_tests.sh --skip-llm

# Skip integration tests (if pytest not installed)
./run_attack_tests.sh --skip-integration
```

### Manual Test Commands

#### 1. Basic Validation (30 seconds)
```bash
# Smoke tests
python3 tests/test_basic.py

# CLI check
python3 main.py list
python3 main.py providers
```

#### 2. Integration Tests (with pytest)
```bash
# Install pytest first
pip install -r tests/requirements.txt

# Run all integration tests
pytest tests/test_integration.py -v

# Run specific module tests
pytest tests/test_integration.py::TestAtomicModule -v
pytest tests/test_integration.py::TestProviderModule -v

# With coverage
./run_tests.sh --html-coverage
```

#### 3. Real LLM Test
```bash
cat > /tmp/quick_test.md << 'EOF'
Respond with: {"test": "pass"}
EOF

python3 << 'PYEOF'
from lib.atomic import atomic_invoke
result = atomic_invoke(
    "/tmp/quick_test.md",
    "/tmp/quick_out.json",
    "Quick LLM test",
    model="haiku",
    format_type="json"
)
print(f"✅ Result: {result}")
PYEOF
```

#### 4. Provider Check
```bash
python3 << 'EOF'
from lib.provider import ProviderManager
pm = ProviderManager()
print("Available Providers:")
print(f"  Max: {pm.is_max_available()}")
print(f"  Bedrock: {pm.is_bedrock_available()}")
print(f"  API: {pm.is_api_available()}")
EOF
```

---

## 📊 Test Phases Overview

| Phase | Focus | Time | Command |
|-------|-------|------|---------|
| 1 | Foundation | 5 min | `python3 tests/test_basic.py` |
| 2 | Integration | 15 min | `pytest tests/ -v` |
| 3 | Real LLM | 10 min | Manual invocations |
| 4 | Hybrid Mode | 20 min | `python3 main.py run 0` |
| 5 | Provider Fallback | 15 min | Provider tests |
| 6 | Error Handling | 20 min | Edge cases |
| 7 | Performance | 15 min | Benchmarks |

---

## 🎯 Test Tier Recommendations

### Tier 1: Essential (5 min)
**Run before any deployment**
```bash
python3 tests/test_basic.py
python3 main.py list
python3 main.py providers
```

### Tier 2: Important (30 min)
**Run before major changes**
```bash
./run_attack_tests.sh --quick
pytest tests/test_integration.py::TestAtomicModule -v
pytest tests/test_integration.py::TestProviderModule -v
```

### Tier 3: Comprehensive (100 min)
**Run before releases**
```bash
./run_attack_tests.sh
```

---

## 🔍 Debugging Test Failures

### Check Logs
```bash
# Test logs are in /tmp/
ls -lt /tmp/test_*.log | head -10

# View specific log
cat /tmp/test_basic.log
cat /tmp/test_integration.log
```

### Common Issues

#### 1. Import Errors
```bash
# Check Python path
python3 -c "import sys; print('\n'.join(sys.path))"

# Verify lib/ directory
ls -la lib/*.py
```

#### 2. Provider Not Available
```bash
# Check provider status
python3 main.py providers

# Check environment
env | grep -E "CLAUDE|AWS|BEDROCK"

# Check .env file
cat .env
```

#### 3. pytest Not Found
```bash
# Install testing dependencies
pip install -r tests/requirements.txt

# Or install pytest directly
pip install pytest pytest-cov
```

#### 4. LLM Invocation Fails
```bash
# Check logs
tail -f .logs/atomic.log

# Test provider directly
python3 << 'EOF'
from lib.provider import ProviderManager
pm = ProviderManager()
print(f"Max available: {pm.is_max_available()}")
print(f"Bedrock available: {pm.is_bedrock_available()}")
EOF

# Check credentials
env | grep -E "AWS_|ANTHROPIC_"
```

---

## 📈 Test Output Interpretation

### Smoke Tests Output
```
🧪 Running basic smoke tests...
✅ All imports successful       # Good: No import errors
✅ All atomic functions exist   # Good: Functions present
✅ ProviderManager works        # Good: Provider module OK
✅ Memory functions exist       # Good: Memory module OK
✅ Phase functions exist        # Good: Phase module OK
✅ Task state functions exist   # Good: Task state OK
✅ All basic tests passed!      # SUCCESS
```

### pytest Output
```
tests/test_integration.py::TestAtomicModule::test_output_functions PASSED [ 2%]
tests/test_integration.py::TestAtomicModule::test_json_escape PASSED [ 4%]
...
===================== 49 passed in 5.23s =====================

49 passed = ALL GOOD ✅
X failed = NEEDS ATTENTION ⚠️
```

### LLM Invocation Output
```
  ▶ Test simple invocation (bedrock/haiku)
⏳ Invoking Claude...
✓ Claude completed task (4s)
  → Output written to: /tmp/test_output.json

This means: SUCCESS ✅
- Provider: bedrock
- Model: haiku
- Time: 4 seconds
- Output: Written to file
```

---

## 🛠️ Custom Test Scenarios

### Test Specific Provider
```bash
python3 << 'EOF'
from lib.atomic import atomic_invoke

# Force bedrock
result = atomic_invoke(
    "/tmp/test.md",
    "/tmp/out.json",
    "Test bedrock",
    provider="bedrock",
    model="haiku"
)
print(f"Bedrock: {result}")
EOF
```

### Test Provider Fallback
```bash
python3 << 'EOF'
from lib.provider import ProviderManager

pm = ProviderManager()

# Get fallback chain
chain = pm.get_provider_chain("primary", "sonnet")
print(f"Fallback chain: {chain}")

# Simulate primary failure, should fallback
for provider in chain:
    print(f"Trying: {provider}")
EOF
```

### Test Memory System
```bash
python3 << 'EOF'
from lib.memory import memory_init, memory_should_persist

memory_init()
should_persist = memory_should_persist()
print(f"Memory enabled: {should_persist}")
EOF
```

### Test State Management
```bash
python3 << 'EOF'
from lib.task_state import TaskStateManager

tsm = TaskStateManager("test-phase")
tsm.task_start("001", "Test Task")
tsm.task_complete("001", "Test Task")
print("✅ State operations work")
EOF
```

---

## 📋 Test Results Checklist

After running tests, verify:

- [ ] All smoke tests pass
- [ ] No import warnings
- [ ] CLI commands work
- [ ] At least one provider available
- [ ] Real LLM invocation succeeds
- [ ] Integration tests pass (if pytest installed)
- [ ] No critical errors in logs
- [ ] Provider detection accurate
- [ ] State files created correctly

---

## 🚨 Emergency Quick Test

If something is broken and you need fast validation:

```bash
# 1. Can Python find the modules?
python3 -c "from lib import atomic; print('OK')"

# 2. Can we list phases?
python3 main.py list

# 3. Can we detect providers?
python3 main.py providers

# 4. Can we invoke LLM?
echo 'Say: OK' > /tmp/t.md
python3 -c "from lib.atomic import atomic_invoke; print(atomic_invoke('/tmp/t.md', '/tmp/o.md', 'test', model='haiku'))"
```

If all 4 pass → System is functional!

---

## 📞 Help Commands

```bash
# Test script help
./run_attack_tests.sh --help

# pytest help
pytest --help

# View test plan
cat TEST-ATTACK-PLAN.md

# View test implementation
cat TEST_IMPLEMENTATION_SUMMARY.md

# View testing guide
cat tests/README.md
```

---

## 🎯 Success Indicators

| Indicator | Meaning |
|-----------|---------|
| ✅ All tests pass | Ready for production |
| ✅ Most tests pass, some skipped | OK if missing optional deps |
| ⚠️ Some tests fail | Review logs, fix issues |
| ❌ Many tests fail | Check environment, dependencies |

---

**Remember:**
- Run `./run_attack_tests.sh --quick` before commits
- Run full test suite before releases
- Check logs in /tmp/test_*.log for details
- Results saved to /tmp/atomic_test_results_*.md

**Quick Start:** `./run_attack_tests.sh --quick` (5 minutes)
