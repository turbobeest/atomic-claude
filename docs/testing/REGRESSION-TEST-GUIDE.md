# Regression Test Suite - Quick Reference

## Overview

The regression test suite validates that all bugs documented in `docs/BUG-PATTERNS.md` remain fixed. It scans the codebase for common bug patterns and ensures they don't reappear.

## Quick Start

```bash
# Run full regression suite
./test/run-regression-tests.sh

# Or run directly with Python
python3 test/regression_runner.py --root /path/to/atomic-claude2
```

## Test Coverage

The suite validates **10 critical bug patterns**:

### 1. Arithmetic with set -e (Bug Pattern #1)
**Checks:** All arithmetic operations have `|| true` suffix
**Pattern:** `((var++))` should be `((var++)) || true`
**Why:** Arithmetic returns old value, triggers `set -e` exit when starting from 0

### 2. Bash Syntax Validation (Bug Pattern #2)
**Checks:** All .sh files pass `bash -n` syntax check
**Pattern:** Corrupted conditionals, mismatched brackets
**Why:** Copy-paste errors can corrupt bash syntax

### 3. Closeout Files (Bug Pattern #3)
**Checks:** All orchestrators create `closeout.json`
**Pattern:** Missing `create_closeout()` function
**Why:** Next phase fails without closeout from previous phase

### 4. Library Sourcing (Bug Pattern #4)
**Checks:** All task scripts source `lib/atomic.sh`
**Pattern:** Missing `source "$LIB_DIR/atomic.sh"`
**Why:** Script can't call atomic_invoke(), atomic_step(), etc.

### 5. Execution Blocks (Bug Pattern #5)
**Checks:** All task scripts have execution guard
**Pattern:** Missing `if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then`
**Why:** Script doesn't run when called directly

### 6. UAT Bypasses (Bug Pattern #6)
**Checks:** Interactive tasks have `ATOMIC_UAT_MODE` bypass
**Pattern:** Missing UAT bypass in conversation loops
**Why:** UAT mode hangs waiting for user input

### 7. macOS Command Compatibility (Bug Pattern #7)
**Checks:** Portable command syntax (head, grep, etc.)
**Pattern:** GNU-specific flags like `head -z`
**Why:** macOS doesn't support GNU extensions

### 8. Interactive Prompts (Bug Pattern #8)
**Checks:** UAT logs don't show hanging or timeouts
**Pattern:** Tasks waiting indefinitely for input
**Why:** Automated testing can't provide interactive input

### 9. Dashboard Port (Bug Pattern #9)
**Checks:** Dashboard uses port 5174 consistently
**Pattern:** Hardcoded 5173 instead of 5174
**Why:** Wrong port prevents dashboard from working

### 10. Documentation Completeness
**Checks:**
- Migration docs exist for each phase
- README is complete
- No broken markdown links

## Test Output

### Console Report
Shows real-time results as tests execute:
```
✅ Test Name: PASSED
❌ Test Name: FAILED (with issue count)
⚠️  Test Name: WARNINGS
```

### JSON Report
Detailed results saved to:
```
test/reports/regression-YYYYMMDD-HHMMSS.json
```

### Markdown Report
Human-readable summary saved to:
```
test/reports/regression-YYYYMMDD-HHMMSS.md
```

## Understanding Results

### PASS (✅)
No issues found. Bug pattern is fully fixed.

### FAIL (❌)
Issues detected. Bug pattern has reappeared.
**Action Required:** Review and fix listed issues.

### WARN (⚠️)
Minor issues or non-critical warnings.
**Action Suggested:** Review issues when convenient.

## Common False Positives

### Arithmetic in for loops
**Pattern:** `for ((i=0; i<10; i++))`
**Status:** Usually OK in loop headers
**Fix:** Refine regex to exclude loop constructs

### Comments with arithmetic
**Pattern:** `# Counter: ((var++))`
**Status:** OK, it's a comment
**Fix:** Already filtered by test

### External repos
**Pattern:** Issues in `node_modules/` or `agents/`
**Status:** Ignored by test suite
**Fix:** Already filtered

## Integration with CI/CD

Add to your test pipeline:

```yaml
# .github/workflows/test.yml
- name: Regression Tests
  run: ./test/run-regression-tests.sh
```

## Manual Validation

For complex bug patterns, manual checks may be needed:

### Pattern #1 (Arithmetic)
```bash
# Find potential issues
grep -rn '((' phases/*/task*.sh | grep -v '|| true'

# Quick fix all
sed -i.bak 's/((i++))/((i++)) || true/g' phases/*/task*.sh
```

### Pattern #6 (UAT Bypasses)
```bash
# Find interactive tasks
grep -l "read -e" phases/*/task*.sh

# Check for UAT bypass
grep -L "ATOMIC_UAT_MODE" phases/*/task*.sh
```

## Test Development

To add a new test:

1. Add test method to `RegressionRunner` class:
```python
def test_my_pattern(self) -> Dict:
    """Bug Pattern #N: Description"""
    issues = []

    # Your validation logic here

    return {
        "status": "PASS" if len(issues) == 0 else "FAIL",
        "issues": issues,
        "expected": "Description of expected state"
    }
```

2. Add to `run_all()` test list:
```python
tests = [
    # ...
    ("My Pattern", self.test_my_pattern),
]
```

3. Document in BUG-PATTERNS.md

## Performance

- **Fast:** Tests complete in 5-15 seconds
- **Lightweight:** No LLM calls, pure static analysis
- **Scalable:** Linear with number of .sh files

## Troubleshooting

### Test fails but code looks correct
**Solution:** Check for whitespace issues, line endings

### Too many false positives
**Solution:** Refine regex patterns in test method

### Test skips files
**Solution:** Check file glob patterns and filters

## Related Documentation

- `docs/BUG-PATTERNS.md` - Full bug pattern catalog
- `test/UAT-QUICK-START.md` - User acceptance testing
- `test/SMOKE-TEST-GUIDE.md` - Smoke testing

## Maintenance

Run regression tests:
- ✅ Before committing new phases
- ✅ After refactoring bash scripts
- ✅ Before merging PRs
- ✅ In CI/CD pipeline
- ✅ Weekly as part of health checks

---

**Last Updated:** 2026-02-04
**Test Version:** 1.0.0
