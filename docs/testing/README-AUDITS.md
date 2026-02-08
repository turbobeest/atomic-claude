# ATOMIC CLAUDE - Master Audit System

## Overview

The Master Audit Runner orchestrates all audit runners in the ATOMIC CLAUDE test suite, providing comprehensive validation of the system and generating consolidated reports with executive summaries.

## Quick Start

```bash
# Run all audits (comprehensive)
./run_all_audits.py

# Run only critical audits (fast)
./run_all_audits.py --quick

# Run specific audit
./run_all_audits.py --only "Security Audit"

# Skip specific audits
./run_all_audits.py --skip "Performance Audit" --skip "Memory Audit"

# List all available audits
./run_all_audits.py --list
```

## Audit Suite

The master runner executes 12 audit runners in priority order:

### Critical Audits (Must Pass)

1. **Dependency Audit** - Validates all required tools and versions
   - Core dependencies (Python, Bash, git, jq)
   - Python packages
   - Optional tools
   - Version compatibility

2. **Script Quality Audit** - Validates bash script quality and patterns
   - Error handling (set -euo pipefail)
   - Function definitions
   - Variable usage
   - Shellcheck compliance

3. **State Management Audit** - Validates state tracking and persistence
   - Task state machine
   - State file integrity
   - Checkpoint/restore functionality
   - Concurrent access handling

4. **Error Handling Audit** - Validates graceful failure and recovery
   - Missing dependencies detected early
   - Invalid inputs rejected gracefully
   - Partial failures recoverable
   - Error messages actionable

5. **Security Audit** - Validates security practices
   - Secret handling
   - Input sanitization
   - File permissions
   - Command injection prevention

6. **Smoke Tests** - Validates basic end-to-end functionality
   - Core CLI commands
   - Phase initialization
   - Basic workflows

### Non-Critical Audits

7. **Configuration Audit** - Validates configuration files and environment
   - Config file structure
   - Environment variables
   - Provider/model configurations
   - Default values

8. **Output Validation Audit** - Validates output structure and content
   - Output directories created
   - Required files present
   - JSON structure valid
   - Content completeness

9. **Integration Points Audit** - Validates Python-to-bash handoffs
   - Script execution
   - Exit code propagation
   - Output stream capture
   - Timeout handling

10. **Regression Tests** - Validates no regressions from previous versions
    - Previously passing tests still pass
    - Fixed bugs stay fixed
    - Performance hasn't degraded

11. **Performance Audit** - Validates performance and resource usage
    - Startup time
    - Memory usage
    - Task execution speed
    - Concurrent operations

12. **Memory Audit** - Validates memory system functionality
    - Memory initialization
    - Save/recall operations
    - Checkpoint creation
    - Context management

## Grading System

The master audit calculates an overall grade based on pass rate and critical issues:

| Grade | Criteria |
|-------|----------|
| **A** | 95%+ pass rate, 0 critical issues |
| **B** | 85-94% pass rate, 0 critical issues |
| **C** | 75-84% pass rate, <5 critical issues |
| **D** | 65-74% pass rate, <10 critical issues |
| **F** | <65% pass rate or 10+ critical issues |

## Report Structure

### Console Report

Real-time progress with color-coded status:
- ✓ Green = Passed
- ✗ Red = Failed
- ○ Yellow = Skipped

### Master JSON Report

Comprehensive report saved to `test/reports/master-audit-TIMESTAMP.json`:

```json
{
  "timestamp": "2026-02-04T21:30:00",
  "total_duration": 125.3,
  "audits_run": 12,
  "audits_passed": 11,
  "audits_failed": 1,
  "audits_skipped": 0,
  "total_tests": 247,
  "total_passed": 235,
  "total_failed": 12,
  "overall_pass_rate": 95.1,
  "overall_grade": "A",
  "critical_issues_count": 0,
  "audit_results": [...],
  "critical_issues": []
}
```

### Executive Summary

One-page summary including:
- Overall grade and pass rate
- Audit and test summaries
- Critical issues (if any)
- Per-audit results with duration

## Command Line Options

### Basic Usage

```bash
./run_all_audits.py [OPTIONS]
```

### Options

| Option | Description |
|--------|-------------|
| `--quick` | Run only critical audits (6 audits) |
| `--skip AUDIT` | Skip specific audit (can use multiple times) |
| `--only AUDIT` | Run only specific audit |
| `--comprehensive` | Run all audits with verbose output (default) |
| `--list` | List all available audits |

### Examples

```bash
# Quick validation before commit
./run_all_audits.py --quick

# Skip long-running audits
./run_all_audits.py --skip "Performance Audit" --skip "Regression Tests"

# Debug specific audit
./run_all_audits.py --only "State Management Audit"

# Full validation before release
./run_all_audits.py --comprehensive
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All critical audits passed |
| 1 | One or more critical audits failed |
| 130 | Interrupted by user (Ctrl+C) |

## Continuous Execution

The master runner continues executing even if some audits fail, ensuring you get a complete picture of system health. This is critical for:

- Identifying all issues in one run
- Understanding cascading failures
- Prioritizing fixes based on impact

## Integration with CI/CD

### GitHub Actions

```yaml
name: Audit Suite
on: [push, pull_request]
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run audits
        run: |
          cd test
          ./run_all_audits.py --quick
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

cd test
./run_all_audits.py --quick || {
    echo "Critical audits failed - commit blocked"
    exit 1
}
```

### Release Validation

```bash
#!/bin/bash
# Before releasing

cd test
./run_all_audits.py --comprehensive

# Check grade
GRADE=$(jq -r '.overall_grade' reports/master-audit-*.json | tail -1)

if [[ "$GRADE" == "A" ]]; then
    echo "✓ Ready for release"
else
    echo "✗ Grade $GRADE - fix issues before release"
    exit 1
fi
```

## Individual Audit Runners

Each audit can also be run independently:

```bash
# Run individual audits
./dependency_audit_runner.py
./script_audit_runner.py
./state_audit_runner.py
./security_audit_runner.py
./smoke_test_runner.py

# With configuration audit
./config_audit_runner.py

# With integration audit
./integration_audit_runner.py

# With error handling audit
./error_audit_runner.py
```

Each audit generates its own detailed report in `test/reports/`.

## Report Analysis

### Finding Critical Issues

```bash
# Extract critical issues from latest report
jq '.critical_issues[] | "\(.audit): \(.issue)"' \
  reports/master-audit-*.json | tail -1
```

### Comparing Runs

```bash
# Compare pass rates over time
jq '.overall_pass_rate' reports/master-audit-*.json
```

### Identifying Slow Audits

```bash
# List audits by duration
jq '.audit_results | sort_by(.duration) | reverse |
    .[] | "\(.duration)s - \(.name)"' \
  reports/master-audit-*.json | tail -1
```

## Best Practices

### Development Workflow

1. **Before starting work**: `./run_all_audits.py --quick`
2. **During development**: Run relevant individual audits
3. **Before committing**: `./run_all_audits.py --quick`
4. **Before PR**: `./run_all_audits.py --comprehensive`
5. **Before release**: `./run_all_audits.py --comprehensive` + Grade A required

### Debugging Failures

1. Run master audit to identify failing audits
2. Run individual audit for detailed output
3. Check audit report JSON for specific test failures
4. Fix issues and re-run
5. Verify fix doesn't break other audits

### Performance Optimization

If audits are too slow:
1. Use `--quick` for iterative development
2. Skip non-critical audits during dev
3. Run comprehensive audits in CI/CD
4. Optimize slow individual audits

## Audit Development

### Adding New Audits

1. Create audit runner: `test/new_audit_runner.py`
2. Follow structure from existing audits
3. Add to `AUDIT_DEFINITIONS` in `run_all_audits.py`
4. Mark as critical or non-critical
5. Update this documentation

### Audit Runner Requirements

Each audit runner must:
- Accept no arguments for default run
- Generate JSON report in `test/reports/`
- Exit with code 0 on success, non-zero on failure
- Include these fields in report:
  - `total_tests`: Total test count
  - `passed`: Passed test count
  - `failed`: Failed test count
  - `results`: List of test results

### Report Format

```python
{
    "timestamp": "ISO 8601 timestamp",
    "total_tests": int,
    "passed": int,
    "failed": int,
    "duration": float,
    "results": [
        {
            "name": "test name",
            "category": "category",
            "passed": bool,
            "duration": float,
            "error_message": "message if failed"
        }
    ]
}
```

## Troubleshooting

### All Audits Skipped

**Cause**: Audit runners not found

**Solution**:
```bash
# Check test directory
ls -la test/*_audit_runner.py

# Ensure runners are executable
chmod +x test/*_audit_runner.py
```

### Timeouts

**Cause**: Audit taking longer than 10 minutes

**Solution**:
1. Check system resources
2. Run individual audit to debug
3. Optimize slow tests
4. Increase timeout in master runner if needed

### Missing Reports

**Cause**: Audit runner not generating JSON report

**Solution**:
1. Run individual audit
2. Check for errors in output
3. Verify report directory exists and is writable
4. Check report naming matches pattern

### Low Pass Rate

**Cause**: Multiple test failures

**Solution**:
1. Review executive summary for patterns
2. Focus on critical issues first
3. Check if environment issues (missing deps)
4. Run individual audits for details

## Performance Benchmarks

Expected execution times (MacBook Pro M1):

| Mode | Audits | Tests | Duration | Use Case |
|------|--------|-------|----------|----------|
| Quick | 6 | ~120 | 30-60s | Development |
| Comprehensive | 12 | ~250 | 2-3 min | Pre-commit |
| With Performance | 12 | ~300 | 5-10 min | Release |

## Support

For issues or questions:

1. Check individual audit documentation
2. Review audit report JSON for details
3. Run with verbose output: audit runner directly
4. Check system requirements: `./dependency_audit_runner.py`

## Version History

- v1.0.0 (2026-02-04): Initial master audit runner
  - 12 audit runners orchestrated
  - Grading system implemented
  - Executive summary generation
  - Critical issue tracking

## Related Documentation

- [Dependency Audit](./DEPENDENCY-AUDIT.md)
- [Script Audit](./SCRIPT-AUDIT-SUMMARY.md)
- [State Audit](./STATE-AUDIT-README.md)
- [Configuration Audit](./CONFIG-AUDIT-README.md)
- [Smoke Tests](./SMOKE-TEST-GUIDE.md)
- [Output Audit](./README-OUTPUT-AUDIT.md)
- [Integration Audit](./INTEGRATION-AUDIT.md)
