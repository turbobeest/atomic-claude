# Performance Audit Runner

Validates reasonable performance characteristics across the Atomic Claude pipeline.

## Overview

The Performance Audit Runner is a comprehensive testing tool that validates:

1. **Execution Time** - Full UAT pipeline completes in < 10 minutes
2. **Memory Usage** - Stable memory footprint under 500MB
3. **Resource Cleanup** - No file descriptor leaks or zombie processes
4. **CPU Usage** - Reasonable CPU consumption without sustained spikes
5. **Disk I/O** - Reasonable file operations and log growth
6. **Background Processes** - All subprocesses terminate cleanly

## Quick Start

```bash
# Run performance audit
./test/run_performance_audit.sh

# Or run directly with Python
python3 test/performance_audit_runner.py
```

## Test Categories

### 1. Execution Time (3 tests)

**Full Pipeline Execution Time**
- Validates UAT pipeline completes in < 10 minutes
- Requires UAT results in `test/reports/uat_performance.json`
- Skipped if no prior UAT run exists

**Phase Timing Breakdown**
- Tracks execution time per phase
- Reads from `.claude/task-state.json`
- Identifies timing patterns

**Slow Phase Detection**
- Flags phases taking > 60 seconds
- Warns about performance bottlenecks
- Helps identify optimization targets

### 2. Memory Usage (3 tests)

**Memory Footprint**
- Verifies memory usage < 500MB
- Warns if memory exceeds 400MB
- Measures RSS (Resident Set Size)

**Memory Stability**
- Takes 5 measurements over 5 seconds
- Checks variance (should be < 50MB std dev)
- Detects memory thrashing

**Memory Leak Detection**
- Allocates and releases memory in loop
- Verifies growth < 10MB
- Ensures proper garbage collection

### 3. Resource Cleanup (4 tests)

**File Descriptor Leaks**
- Performs file operations
- Verifies FD count returns to baseline
- Flags growth > 5 file descriptors

**Zombie Processes**
- Checks for zombie child processes
- Uses psutil or ps command fallback
- Ensures process cleanup

**Temp File Cleanup**
- Checks common temp locations
- Flags > 50 temporary files
- Verifies cleanup routines work

**Open File Count**
- Verifies < 100 open files
- Warns if > 50 files open
- Detects file handle leaks

### 4. CPU Usage (2 tests)

**CPU Usage Reasonable**
- Takes 3 measurements over 3 seconds
- Average should be < 50% for idle
- Flags excessive CPU consumption

**CPU Spike Detection**
- Takes 5 measurements over 2.5 seconds
- Flags sustained spikes > 80%
- Detects runaway processes

### 5. Disk I/O (2 tests)

**File Operations**
- Performs 100 small writes
- Should consume < 10MB
- Platform-specific (requires psutil.io_counters)

**Log Growth**
- Checks log files in `.logs/`
- Flags files > 100MB
- Prevents runaway logging

### 6. Background Processes (2 tests)

**Subprocess Termination**
- Starts test subprocess
- Verifies clean termination
- Checks timeout handling

**Orphaned Children**
- Tracks child process count
- Verifies children terminate with parent
- Ensures no orphaned processes

## Requirements

### Required
- Python 3.8+
- Standard library modules (json, os, subprocess, time, pathlib)

### Optional (Highly Recommended)
- `psutil` - Enhanced monitoring capabilities

Install psutil for detailed metrics:
```bash
pip3 install psutil
```

### Without psutil
- Falls back to `ps`, `top`, `lsof` commands
- Some tests skip (marked as "(Skipped - requires psutil)")
- macOS: `io_counters` unavailable (falls back gracefully)

## Output

### Console Output
```
======================================================================
  Performance Audit Runner
======================================================================

Running Performance Tests:

Execution Time:
  ✓ Full Pipeline Execution Time
  ✓ Phase Timing Breakdown
  ✓ Slow Phase Detection

Memory Usage:
  ✓ Memory Footprint
  ✓ Memory Stability
  ✓ Memory Leak Detection

...

======================================================================
  Performance Test Summary
======================================================================

Total Tests:   16
Passed:        16
Failed:        0
Warnings:      0
Success Rate:  100.0%
Duration:      20.18s

Category Breakdown:

  ✓ Execution Time                 3/3 (100%)
  ✓ Memory Usage                   3/3 (100%)
  ✓ Resource Cleanup               4/4 (100%)
  ✓ CPU Usage                      2/2 (100%)
  ✓ Disk I/O                       2/2 (100%)
  ✓ Background Processes           2/2 (100%)

Performance audit PASSED - all tests succeeded
```

### JSON Report

Located at `test/reports/performance_audit.json`:

```json
{
  "timestamp": "2026-02-04T21:30:51.359667",
  "summary": {
    "total_tests": 16,
    "passed": 16,
    "failed": 0,
    "warnings": 0,
    "success_rate": "100.0%",
    "duration": "20.19s"
  },
  "results": [
    {
      "name": "Full Pipeline Execution Time",
      "category": "Execution Time",
      "passed": true,
      "duration": "0.000s",
      "error": null,
      "details": {}
    },
    ...
  ]
}
```

## Performance Thresholds

| Metric | Threshold | Warning | Failure |
|--------|-----------|---------|---------|
| Pipeline execution | < 10 min | - | > 10 min |
| Memory usage (RSS) | < 500MB | > 400MB | > 500MB |
| Memory std dev | < 50MB | - | > 50MB |
| Memory growth | < 10MB | - | > 10MB |
| File descriptors | - | - | +5 FDs |
| Open files | < 100 | > 50 | > 100 |
| Avg CPU (idle) | < 50% | - | > 50% |
| CPU spikes (sustained) | - | > 80% (3+) | - |
| Disk writes | < 10MB | - | - |
| Log file size | - | > 100MB | - |

## Integration with CI/CD

Add to your test suite:

```bash
#!/bin/bash
# Run full test suite

# Integration tests
./test/run-integration-audit.sh || exit 1

# Configuration tests
python3 test/config_audit_runner.py || exit 1

# Error handling tests
python3 test/error_audit_runner.py || exit 1

# Performance tests
./test/run_performance_audit.sh || exit 1

echo "All audits passed!"
```

## Troubleshooting

### "psutil not available"
- Install with: `pip3 install psutil`
- Or continue with fallback monitoring (reduced metrics)

### "No task state available"
- Run pipeline first: `./main.sh run 0`
- Or skip execution time tests (they'll auto-skip)

### "io_counters not available on this platform"
- Normal on macOS - this method not supported
- Test automatically skips, no action needed

### High Memory Warnings
- Check for memory leaks in recent changes
- Review log file sizes (`.logs/`)
- Check temp file accumulation (`.outputs/tmp/`, `.state/tmp/`)

### CPU Spike Warnings
- Normal during LLM invocations
- Investigate if occurring during idle periods
- Check background processes

### File Descriptor Leaks
- Review file operations in recent changes
- Ensure files are closed with `with` statements
- Check subprocess cleanup

## Performance Baseline

Typical performance on development machine:

- **Execution time**: 15-20 seconds (for audit itself)
- **Memory usage**: 40-80MB RSS
- **CPU usage**: < 10% average (spikes during tests)
- **File descriptors**: 20-40 typical
- **Open files**: 10-30 typical

Full UAT pipeline (when run):
- **Execution time**: 5-8 minutes
- **Peak memory**: 200-300MB
- **CPU usage**: Variable during LLM calls

## Future Enhancements

Potential additions:

1. **Network monitoring** - Track API calls and bandwidth
2. **Database metrics** - If persistent storage added
3. **Thread analysis** - Concurrent operation monitoring
4. **Regression detection** - Compare against baselines
5. **Profiling integration** - cProfile/pstats integration
6. **Real-time monitoring** - WebSocket-based live metrics
7. **Alert thresholds** - Configurable warning/error levels

## Related Documentation

- [Integration Audit](./run-integration-audit.sh) - Validates Python/Bash integration
- [Config Audit](./config_audit_runner.py) - Validates configuration handling
- [Error Audit](./error_audit_runner.py) - Validates error propagation

## Architecture

```python
class PerformanceAuditRunner:
    def measure_execution_time(self) -> Dict
        # Reads task-state.json for timing data
        # Validates < 10 minute threshold

    def measure_memory_usage(self) -> Dict
        # Uses psutil.Process().memory_info()
        # Fallback to ps command

    def check_resource_cleanup(self) -> Dict
        # Tracks file descriptors, open files
        # Detects zombies and orphans

    def measure_cpu_usage(self) -> Dict
        # Uses psutil.Process().cpu_percent()
        # Fallback to ps command

    def run_all_tests(self) -> PerformanceReport
        # Orchestrates all test categories
        # Generates report
```

## Exit Codes

- `0` - All tests passed (warnings OK)
- `1` - One or more tests failed

Warnings don't cause failure - they're informational only.
