# Performance Audit Quick Start

The **Performance Audit Runner** validates pipeline performance characteristics including execution time, memory usage, CPU utilization, resource cleanup, and scalability.

## Quick Run

```bash
# Run all performance tests
python test/performance_audit_runner.py

# With verbose output
python test/performance_audit_runner.py --verbose

# With profiling enabled
python test/performance_audit_runner.py --profile
```

## What It Tests

### Execution Time (4 tests)
- **Phase 0 execution**: < 120s in UAT mode
- **Full pipeline**: < 10 minutes (UAT mode)
- **Task timeout compliance**: All tasks complete within limits
- **Slow task detection**: Identify tasks > 60s

### Resource Usage (7 tests)
- **Memory footprint**: < 500MB usage
- **Memory leak detection**: Monitor growth over time
- **Memory per phase**: Track peak usage per phase
- **CPU usage**: Average < 50% for idle process
- **CPU spike detection**: Flag sustained > 80% usage
- **Log growth**: Monitor for runaway logs
- **Output size**: Track total output file size

### Resource Cleanup (4 tests)
- **File descriptor leaks**: Monitor FD growth
- **Temp file cleanup**: Check temp file accumulation
- **Orphaned processes**: Detect zombie processes
- **Open file count**: Reasonable file handle usage

### Scalability (2 tests)
- **Concurrent operations**: Handle parallel file ops
- **Large file handling**: Process 10MB+ files efficiently

## Exit Codes

- **0**: All tests passed (warnings OK)
- **1**: Critical performance issues detected

## Output Format

### Console Output
```
======================================================================
  PERFORMANCE AUDIT RUNNER
======================================================================

Execution Time Tests:
Resource Usage Tests:
Resource Cleanup Tests:
Scalability Tests:

======================================================================
  TEST RESULTS
======================================================================

Total Tests:     17
Passed:          17
Failed:          0
  Critical:      0
  Warnings:      0

Category Breakdown:

  ✓ cleanup                   4/4 (100%)
  ✓ execution_time            4/4 (100%)
  ✓ resource_usage            7/7 (100%)
  ✓ scalability               2/2 (100%)

======================================================================
PERFORMANCE AUDIT PASSED - all tests succeeded
======================================================================
```

### JSON Report
Generated at: `test/reports/performance-audit-TIMESTAMP.json`

```json
{
  "timestamp": "2026-02-05T07:00:52.138406",
  "total_tests": 17,
  "passed": 17,
  "failed": 0,
  "critical": 0,
  "warnings": 0,
  "success_rate": "100.0%",
  "results": [
    {
      "category": "execution_time",
      "test": "Phase 0 completes in < 120s",
      "passed": true,
      "message": "Phase 0 completed in 45.2s",
      "severity": "info",
      "metrics": {
        "duration_ms": 45200.0,
        "memory_mb": 0.0,
        "cpu_percent": 0.0
      }
    }
  ]
}
```

## Dependencies

**Recommended**: `psutil` for detailed monitoring
```bash
pip install psutil
```

**Fallback**: Uses `resource` module and shell commands if psutil unavailable

## Integration with UAT

The performance audit reads UAT execution data from:
```
test/reports/uat_performance.json
```

UAT runner should generate this file with:
```json
{
  "total_duration": 580.5,
  "phase_durations": {
    "0": 45.2,
    "1": 67.8,
    ...
  },
  "phase_memory": {
    "0": 142.5,
    "1": 178.3,
    ...
  }
}
```

## Performance Thresholds

| Metric | Threshold | Severity |
|--------|-----------|----------|
| Phase 0 time | < 120s | warning |
| Full pipeline | < 10m | critical |
| Task time | < 5m | warning |
| Memory usage | < 500MB | critical |
| Memory growth | < 10MB | warning |
| Open files | < 100 | warning |
| Log files | < 100MB | warning |
| Zombie processes | 0 | critical |

## Example: Failed Test

```
======================================================================
  TEST RESULTS
======================================================================

Total Tests:     17
Passed:          15
Failed:          2
  Critical:      1
  Warnings:      1

Category Breakdown:

  ✗ execution_time            3/4 (75%) (1 critical)
  ⚠ resource_usage            6/7 (86%) (1 warnings)
  ✓ cleanup                   4/4 (100%)
  ✓ scalability               2/2 (100%)

Failed Tests:

  ✗ Full pipeline < 10 minutes
    Pipeline took 720.5s (12.0m)
  ⚠ Memory leak detection
    Potential memory leak (growth: 15.3MB)

======================================================================
PERFORMANCE AUDIT FAILED - 1 critical issues
======================================================================
```

## Troubleshooting

### High Memory Usage
- Check for unclosed file handles
- Review memory cleanup in tasks
- Look for large data structures in memory

### Slow Execution
- Profile with `--profile` flag
- Check for blocking I/O operations
- Review LLM provider response times

### File Descriptor Leaks
- Ensure `with` statements for file operations
- Check subprocess cleanup
- Review temp file handling

### CPU Spikes
- Check for tight loops
- Review JSON parsing of large files
- Monitor background processes

## Advanced Usage

### Custom Thresholds
Edit the test methods to adjust thresholds:

```python
# In test_memory_footprint():
if rss_mb < 500:  # Change threshold here
    ...
```

### Add New Tests
Create test methods following the pattern:

```python
def test_new_metric(self):
    """Test description."""
    # Measure
    metric = self.measure_something()

    # Evaluate
    passed = metric < threshold

    # Record
    self.results.append(TestResult(
        category="your_category",
        test="Test name",
        passed=passed,
        message="Description",
        metrics=PerformanceMetrics(...),
        severity="info|warning|critical"
    ))
```

### Integration with CI/CD

```yaml
# .github/workflows/performance.yml
- name: Run Performance Audit
  run: |
    python test/performance_audit_runner.py

- name: Upload Performance Report
  uses: actions/upload-artifact@v3
  with:
    name: performance-report
    path: test/reports/performance-audit-*.json
```

## See Also

- [UAT Quick Start](UAT-QUICK-START.md) - User acceptance testing
- [Memory Audit](MEMORY-AUDIT.md) - Memory system validation
- [State Audit](STATE-AUDIT-README.md) - State management validation
- [Master Audit](MASTER-AUDIT-SUMMARY.md) - Comprehensive audit suite
