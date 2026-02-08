# Master Audit Runner - Quick Reference

## One-Liners

```bash
# Run all audits
./run-all-audits.sh

# Run critical audits only (30-60s)
./run-all-audits.sh quick

# Run specific audit
./run-all-audits.sh security

# List available audits
./run-all-audits.sh list

# Skip specific audits
./run_all_audits.py --skip "Performance Audit" --skip "Memory Audit"
```

## Common Workflows

### Before Committing
```bash
./run-all-audits.sh quick
```

### Before Pull Request
```bash
./run_all_audits.py
```

### Before Release
```bash
./run_all_audits.py --comprehensive
# Check grade is A
jq -r '.overall_grade' reports/master-audit-*.json | tail -1
```

### Debug Specific Issue
```bash
# Run just one audit
./run-all-audits.sh state

# Or directly
./state_audit_runner.py
```

## Individual Audit Commands

| Command | Audit | Duration |
|---------|-------|----------|
| `./run-all-audits.sh dependency` | Dependency Audit | ~5s |
| `./run-all-audits.sh script` | Script Quality Audit | ~10s |
| `./run-all-audits.sh config` | Configuration Audit | ~8s |
| `./run-all-audits.sh state` | State Management Audit | ~15s |
| `./run-all-audits.sh output` | Output Validation Audit | ~10s |
| `./run-all-audits.sh integration` | Integration Points Audit | ~12s |
| `./run-all-audits.sh error` | Error Handling Audit | ~10s |
| `./run-all-audits.sh security` | Security Audit | ~15s |
| `./run-all-audits.sh regression` | Regression Tests | ~30s |
| `./run-all-audits.sh performance` | Performance Audit | ~60s |
| `./run-all-audits.sh memory` | Memory Audit | ~8s |
| `./run-all-audits.sh smoke` | Smoke Tests | ~20s |

## Report Analysis

### View Latest Grade
```bash
jq -r '.overall_grade' reports/master-audit-*.json | tail -1
```

### View Pass Rate
```bash
jq -r '.overall_pass_rate' reports/master-audit-*.json | tail -1
```

### List Critical Issues
```bash
jq -r '.critical_issues[] | "\(.audit): \(.issue)"' \
  reports/master-audit-*.json | tail -1
```

### View Failed Tests
```bash
jq -r '.audit_results[] | select(.failed_tests > 0) |
  "\(.name): \(.failed_tests) failures"' \
  reports/master-audit-*.json | tail -1
```

### Compare Runs
```bash
# Show pass rates over time
jq -r '"\(.timestamp | split("T")[0]): \(.overall_pass_rate)%"' \
  reports/master-audit-*.json
```

## Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | All critical audits passed | Safe to proceed |
| 1 | Critical audit(s) failed | Fix issues before proceeding |
| 130 | Interrupted (Ctrl+C) | Re-run when ready |

## Grading Scale

| Grade | Pass Rate | Critical Issues | Quality |
|-------|-----------|-----------------|---------|
| A | 95%+ | 0 | Production ready |
| B | 85-94% | 0 | Good, minor fixes |
| C | 75-84% | <5 | Needs improvement |
| D | 65-74% | <10 | Significant issues |
| F | <65% | Any | Not ready |

## Critical Audits (Must Pass)

1. Dependency Audit - All tools installed
2. Script Quality Audit - Code quality standards
3. State Management Audit - State integrity
4. Error Handling Audit - Graceful failures
5. Security Audit - Security practices
6. Smoke Tests - Basic functionality

## Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| Audit skipped | Runner not found, check `ls test/*_audit_runner.py` |
| Timeout | System too slow, run individual audit to debug |
| Missing report | Check audit runner for errors |
| Low pass rate | Run failed audits individually for details |

## Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit
cd test
./run-all-audits.sh quick || {
    echo "Critical audits failed"
    exit 1
}
```

## CI/CD Integration

```yaml
# GitHub Actions
- name: Audit
  run: cd test && ./run-all-audits.sh quick
```

## Time Estimates

| Mode | Duration | Tests | Use Case |
|------|----------|-------|----------|
| Quick | 30-60s | ~120 | Development iteration |
| Full | 2-3 min | ~250 | Pre-commit validation |
| Comprehensive | 5-10 min | ~300 | Release validation |

## Aliases

Add to `.bashrc` or `.zshrc`:

```bash
# ATOMIC CLAUDE audit aliases
alias audit='cd ~/dev/atomic-claude2/test && ./run-all-audits.sh'
alias audit-quick='cd ~/dev/atomic-claude2/test && ./run-all-audits.sh quick'
alias audit-list='cd ~/dev/atomic-claude2/test && ./run-all-audits.sh list'
alias audit-report='jq . ~/dev/atomic-claude2/test/reports/master-audit-*.json | tail -1'
```

## Python API

```python
from run_all_audits import MasterAuditRunner
from pathlib import Path

# Create runner
runner = MasterAuditRunner(test_dir=Path("test"))

# Run audits
report = runner.run_all_audits(quick_mode=True)

# Check results
print(f"Grade: {report.overall_grade}")
print(f"Pass Rate: {report.overall_pass_rate:.1f}%")

# Save report
runner.save_report(report)
```

## Files Created

| File | Purpose |
|------|---------|
| `run_all_audits.py` | Master audit runner (Python) |
| `run-all-audits.sh` | Shell wrapper with shortcuts |
| `README-AUDITS.md` | Full documentation |
| `AUDIT-QUICKREF.md` | This quick reference |
| `reports/master-audit-*.json` | Audit reports |

## Getting Help

```bash
# Show command help
./run-all-audits.sh help
./run_all_audits.py --help

# List all audits
./run-all-audits.sh list

# Read full docs
cat README-AUDITS.md
```
