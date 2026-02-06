# Integration Audit - Quick Start

## Run the Audit

```bash
# Option 1: Using wrapper (recommended)
./test/run-integration-audit.sh

# Option 2: Direct Python
python3 test/integration_audit_runner.py

# Option 3: From test directory
cd test && python3 integration_audit_runner.py
```

## What It Tests

| Category | Tests | What It Validates |
|----------|-------|-------------------|
| **Orchestrator Execution** | 3 | Python can execute bash scripts |
| **Exit Code Propagation** | 3 | Exit codes (0, 1, custom) are captured |
| **Output Capture** | 3 | stdout and stderr are captured separately |
| **Timeout Handling** | 3 | Scripts terminate at specified timeouts |
| **Environment Passing** | 3 | Env vars reach bash scripts |
| **Library Function Access** | 4 | Bash can use lib/atomic.sh functions |
| **Error Propagation** | 4 | Errors are detected and reported |
| **Working Directory** | 3 | Scripts run in correct directory |

**Total: 26 tests**

## Expected Output

```
======================================================================
  Integration Audit Runner
======================================================================

Running Integration Tests:

Orchestrator Execution:
  ✓ Simple Execution
  ✓ Script With Output
  ✓ Script With Stderr

...

======================================================================
  Test Summary
======================================================================

Total Tests:   26
Passed:        26
Failed:        0
Success Rate:  100.0%
Duration:      3.42s

Integration audit PASSED - all tests succeeded
```

## Success Criteria

- **All 26 tests pass**: Exit code 0
- **Any test fails**: Exit code 1, see error messages
- **Report saved**: `test/reports/integration_audit.json`

## When to Run

Run the integration audit:

1. **Before committing** changes to orchestration code
2. **After modifying** lib/atomic.sh or lib/phase.py
3. **When adding** new bash-python integration points
4. **In CI/CD** pipeline (required check)
5. **When troubleshooting** orchestrator issues

## Troubleshooting

### All Tests Fail

**Problem**: "command not found: python3"

**Solution**: Install Python 3.7+

### Library Tests Fail

**Problem**: "lib/atomic.sh not found"

**Solution**: Run from repository root, not test/ subdirectory

### Timeout Tests Fail

**Problem**: Tests time out or hang

**Solution**: System may be under heavy load. Timeout tests have ±0.1s variance.

### Permission Test Fails

**Problem**: "Permission denied"

**Solution**: Normal - test validates permission errors are caught

## Quick Validation

Want to quickly check if integration is working?

```bash
# Run just one category
python3 -c "
from test.integration_audit_runner import IntegrationAuditRunner
runner = IntegrationAuditRunner()
runner._create_test_fixtures()
runner.test_simple_execution()
print('✓ Basic integration working')
"
```

## Files Created

| Path | Purpose |
|------|---------|
| `test/integration_audit_runner.py` | Main audit script (772 lines) |
| `test/run-integration-audit.sh` | Bash wrapper for convenience |
| `test/fixtures/*.sh` | 21 test fixture scripts (auto-created) |
| `test/reports/integration_audit.json` | JSON report output |
| `test/INTEGRATION-AUDIT.md` | Full documentation |

## CI/CD Integration

### GitHub Actions

```yaml
- name: Integration Audit
  run: ./test/run-integration-audit.sh
```

### GitLab CI

```yaml
integration-audit:
  script:
    - python3 test/integration_audit_runner.py
```

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
if [[ -f test/integration_audit_runner.py ]]; then
  python3 test/integration_audit_runner.py || {
    echo "Integration audit failed"
    exit 1
  }
fi
```

## Full Documentation

See `test/INTEGRATION-AUDIT.md` for:
- Detailed test descriptions
- Architecture notes
- Development guidelines
- Complete API reference
