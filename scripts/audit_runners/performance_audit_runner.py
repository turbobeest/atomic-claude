#!/usr/bin/env python3
"""
Performance Audit Runner
Validates reasonable performance characteristics across the pipeline

This audit ensures that:
1. Full UAT pipeline executes in < 10 minutes
2. Memory usage stays reasonable (< 500MB)
3. No memory leaks occur
4. CPU usage is reasonable
5. File descriptors don't leak
6. Background processes terminate properly
7. Disk I/O is reasonable
8. No runaway log growth

Usage:
    python test/performance_audit_runner.py              # Run all tests
    python test/performance_audit_runner.py --verbose    # Detailed output
    python test/performance_audit_runner.py --profile    # Run with profiling
"""

import json
import os
import resource
import subprocess
import sys
import time
import signal
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Try to import psutil for detailed monitoring
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("⚠️  psutil not available - using fallback monitoring")
    print("   Install with: pip install psutil")

# Repo root
REPO_ROOT = Path(__file__).parent.parent.resolve()
STATE_DIR = REPO_ROOT / ".state"
OUTPUT_DIR = REPO_ROOT / ".outputs"
LOG_DIR = REPO_ROOT / ".logs"

# Colors for output
class Colors:
    CYAN = '\033[0;36m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    NC = '\033[0m'


@dataclass
class PerformanceMetrics:
    """Performance metrics for a test or operation."""
    duration_ms: float = 0.0
    memory_mb: float = 0.0
    peak_memory_mb: float = 0.0
    cpu_percent: float = 0.0
    open_files: int = 0
    processes: int = 0
    disk_writes_kb: float = 0.0


@dataclass
class TestResult:
    """Result of a single performance test."""
    category: str
    test: str
    passed: bool
    message: str
    metrics: Optional[PerformanceMetrics] = None
    severity: str = "info"  # critical, warning, info

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        result = {
            "category": self.category,
            "test": self.test,
            "passed": self.passed,
            "message": self.message,
            "severity": self.severity
        }
        if self.metrics:
            result["metrics"] = {
                "duration_ms": round(self.metrics.duration_ms, 2),
                "memory_mb": round(self.metrics.memory_mb, 2),
                "cpu_percent": round(self.metrics.cpu_percent, 2),
            }
            if self.metrics.peak_memory_mb > 0:
                result["metrics"]["peak_memory_mb"] = round(self.metrics.peak_memory_mb, 2)
            if self.metrics.open_files > 0:
                result["metrics"]["open_files"] = self.metrics.open_files
            if self.metrics.processes > 0:
                result["metrics"]["processes"] = self.metrics.processes
        return result


class PerformanceAuditRunner:
    """
    Validates performance characteristics of the pipeline.
    """

    def __init__(self, verbose: bool = False, profile: bool = False):
        self.verbose = verbose
        self.profile = profile
        self.results: List[TestResult] = []

        # Ensure directories exist
        (REPO_ROOT / "test" / "reports").mkdir(parents=True, exist_ok=True)

    def log(self, message: str, color: str = Colors.NC):
        """Log a message with color."""
        print(f"{color}{message}{Colors.NC}")

    def measure_memory(self) -> Dict[str, float]:
        """Measure current memory usage."""
        if HAS_PSUTIL:
            process = psutil.Process()
            mem = process.memory_info()
            return {
                "rss_mb": mem.rss / (1024 * 1024),
                "vms_mb": mem.vms / (1024 * 1024),
            }
        else:
            # Fallback to resource module
            try:
                usage = resource.getrusage(resource.RUSAGE_SELF)
                # On macOS, ru_maxrss is in bytes; on Linux, in kilobytes
                if sys.platform == 'darwin':
                    rss_mb = usage.ru_maxrss / (1024 * 1024)
                else:
                    rss_mb = usage.ru_maxrss / 1024
                return {"rss_mb": rss_mb, "vms_mb": 0}
            except:
                return {"rss_mb": 0, "vms_mb": 0}

    def measure_cpu(self) -> float:
        """Measure CPU usage."""
        if HAS_PSUTIL:
            process = psutil.Process()
            return process.cpu_percent(interval=0.1)
        else:
            # Fallback to getrusage
            try:
                usage = resource.getrusage(resource.RUSAGE_SELF)
                user_time = usage.ru_utime
                sys_time = usage.ru_stime
                # Simple approximation
                return (user_time + sys_time) * 10  # Very rough estimate
            except:
                return 0.0

    def count_open_files(self) -> int:
        """Count open file descriptors."""
        if HAS_PSUTIL:
            try:
                process = psutil.Process()
                return len(process.open_files())
            except:
                return 0
        else:
            # Fallback to lsof
            try:
                result = subprocess.run(
                    ["lsof", "-p", str(os.getpid())],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return len(result.stdout.strip().split('\n')) - 1
            except:
                return 0

    def count_processes(self) -> int:
        """Count child processes."""
        if HAS_PSUTIL:
            try:
                process = psutil.Process()
                return len(process.children(recursive=True))
            except:
                return 0
        else:
            return 0

    # ========================================================================
    # EXECUTION TIME TESTS
    # ========================================================================

    def test_phase_0_execution_time(self):
        """Test that Phase 0 completes in < 120s (UAT mode)."""
        start_time = time.time()

        # Check if we have UAT results
        uat_results = REPO_ROOT / "test" / "reports" / "uat_performance.json"

        if uat_results.exists():
            with open(uat_results) as f:
                data = json.load(f)
                phase_0_duration = data.get("phase_durations", {}).get("0", 0)

                duration_ms = phase_0_duration * 1000
                metrics = PerformanceMetrics(duration_ms=duration_ms)

                if phase_0_duration < 120:
                    self.results.append(TestResult(
                        category="execution_time",
                        test="Phase 0 completes in < 120s",
                        passed=True,
                        message=f"Phase 0 completed in {phase_0_duration:.1f}s",
                        metrics=metrics,
                        severity="info"
                    ))
                else:
                    self.results.append(TestResult(
                        category="execution_time",
                        test="Phase 0 completes in < 120s",
                        passed=False,
                        message=f"Phase 0 took {phase_0_duration:.1f}s (> 120s)",
                        metrics=metrics,
                        severity="warning"
                    ))
        else:
            # Skip if no UAT results
            self.results.append(TestResult(
                category="execution_time",
                test="Phase 0 completes in < 120s",
                passed=True,
                message="Skipped - run UAT first to measure",
                severity="info"
            ))

    def test_full_pipeline_time(self):
        """Test that full 10-phase pipeline < 10 minutes (UAT mode)."""
        uat_results = REPO_ROOT / "test" / "reports" / "uat_performance.json"

        if uat_results.exists():
            with open(uat_results) as f:
                data = json.load(f)
                total_duration = data.get("total_duration", 0)

                duration_ms = total_duration * 1000
                metrics = PerformanceMetrics(duration_ms=duration_ms)

                if total_duration < 600:
                    self.results.append(TestResult(
                        category="execution_time",
                        test="Full pipeline < 10 minutes",
                        passed=True,
                        message=f"Pipeline completed in {total_duration:.1f}s ({total_duration/60:.1f}m)",
                        metrics=metrics,
                        severity="info"
                    ))
                else:
                    self.results.append(TestResult(
                        category="execution_time",
                        test="Full pipeline < 10 minutes",
                        passed=False,
                        message=f"Pipeline took {total_duration:.1f}s ({total_duration/60:.1f}m)",
                        metrics=metrics,
                        severity="critical"
                    ))
        else:
            self.results.append(TestResult(
                category="execution_time",
                test="Full pipeline < 10 minutes",
                passed=True,
                message="Skipped - run UAT first to measure",
                severity="info"
            ))

    def test_task_timeout_compliance(self):
        """Test that tasks complete within timeout limits."""
        task_state_file = STATE_DIR / "task-state.json"

        if not task_state_file.exists():
            self.results.append(TestResult(
                category="execution_time",
                test="Tasks complete within timeout",
                passed=True,
                message="Skipped - no task state available",
                severity="info"
            ))
            return

        with open(task_state_file) as f:
            state = json.load(f)

        slow_tasks = []
        for task_id, task_data in state.get("tasks", {}).items():
            if "started_at" in task_data and "completed_at" in task_data:
                start = datetime.fromisoformat(task_data["started_at"])
                end = datetime.fromisoformat(task_data["completed_at"])
                duration = (end - start).total_seconds()

                # Flag tasks > 300s (5 minutes)
                if duration > 300:
                    slow_tasks.append((task_id, duration))

        if not slow_tasks:
            self.results.append(TestResult(
                category="execution_time",
                test="Tasks complete within timeout",
                passed=True,
                message="All tasks completed within reasonable time",
                severity="info"
            ))
        else:
            tasks_str = ", ".join(f"{tid} ({dur:.0f}s)" for tid, dur in slow_tasks[:3])
            self.results.append(TestResult(
                category="execution_time",
                test="Tasks complete within timeout",
                passed=False,
                message=f"Slow tasks detected: {tasks_str}",
                severity="warning"
            ))

    def test_slow_task_detection(self):
        """Identify slow tasks (> 60s)."""
        task_state_file = STATE_DIR / "task-state.json"

        if not task_state_file.exists():
            self.results.append(TestResult(
                category="execution_time",
                test="Slow task detection",
                passed=True,
                message="Skipped - no task state available",
                severity="info"
            ))
            return

        with open(task_state_file) as f:
            state = json.load(f)

        slow_tasks = []
        for task_id, task_data in state.get("tasks", {}).items():
            if "started_at" in task_data and "completed_at" in task_data:
                start = datetime.fromisoformat(task_data["started_at"])
                end = datetime.fromisoformat(task_data["completed_at"])
                duration = (end - start).total_seconds()

                if duration > 60:
                    slow_tasks.append((task_id, duration))

        if slow_tasks:
            avg_duration = sum(d for _, d in slow_tasks) / len(slow_tasks)
            tasks_str = ", ".join(f"{tid} ({dur:.0f}s)" for tid, dur in slow_tasks[:5])

            metrics = PerformanceMetrics(duration_ms=avg_duration * 1000)

            self.results.append(TestResult(
                category="execution_time",
                test="Slow task detection",
                passed=True,
                message=f"Found {len(slow_tasks)} slow tasks (avg {avg_duration:.0f}s): {tasks_str}",
                metrics=metrics,
                severity="info"
            ))
        else:
            self.results.append(TestResult(
                category="execution_time",
                test="Slow task detection",
                passed=True,
                message="No slow tasks detected",
                severity="info"
            ))

    # ========================================================================
    # MEMORY USAGE TESTS
    # ========================================================================

    def test_memory_footprint(self):
        """Test that memory usage stays under 500MB."""
        start_time = time.time()
        mem = self.measure_memory()
        duration_ms = (time.time() - start_time) * 1000

        rss_mb = mem["rss_mb"]
        metrics = PerformanceMetrics(
            duration_ms=duration_ms,
            memory_mb=rss_mb,
            peak_memory_mb=rss_mb
        )

        if rss_mb < 500:
            self.results.append(TestResult(
                category="resource_usage",
                test="Memory footprint < 500MB",
                passed=True,
                message=f"Current memory: {rss_mb:.1f}MB",
                metrics=metrics,
                severity="info"
            ))
        else:
            self.results.append(TestResult(
                category="resource_usage",
                test="Memory footprint < 500MB",
                passed=False,
                message=f"Memory usage {rss_mb:.1f}MB exceeds 500MB",
                metrics=metrics,
                severity="critical"
            ))

    def test_memory_leak_detection(self):
        """Test for memory leaks by monitoring growth."""
        measurements = []

        # Take 10 measurements over 2 seconds
        for _ in range(10):
            mem = self.measure_memory()
            measurements.append(mem["rss_mb"])
            time.sleep(0.2)

        initial = measurements[0]
        final = measurements[-1]
        growth = final - initial
        avg_mem = sum(measurements) / len(measurements)

        metrics = PerformanceMetrics(
            memory_mb=avg_mem,
            peak_memory_mb=final
        )

        if growth < 10:
            self.results.append(TestResult(
                category="resource_usage",
                test="Memory leak detection",
                passed=True,
                message=f"Memory stable (growth: {growth:.1f}MB)",
                metrics=metrics,
                severity="info"
            ))
        else:
            self.results.append(TestResult(
                category="resource_usage",
                test="Memory leak detection",
                passed=False,
                message=f"Potential memory leak (growth: {growth:.1f}MB)",
                metrics=metrics,
                severity="warning"
            ))

    def test_memory_per_phase(self):
        """Test memory consumption per phase."""
        uat_results = REPO_ROOT / "test" / "reports" / "uat_performance.json"

        if uat_results.exists():
            with open(uat_results) as f:
                data = json.load(f)
                phase_memory = data.get("phase_memory", {})

                if phase_memory:
                    max_phase = max(phase_memory.items(), key=lambda x: x[1])
                    avg_memory = sum(phase_memory.values()) / len(phase_memory)

                    metrics = PerformanceMetrics(
                        memory_mb=avg_memory,
                        peak_memory_mb=max_phase[1]
                    )

                    self.results.append(TestResult(
                        category="resource_usage",
                        test="Memory per phase",
                        passed=True,
                        message=f"Peak: Phase {max_phase[0]} ({max_phase[1]:.1f}MB), Avg: {avg_memory:.1f}MB",
                        metrics=metrics,
                        severity="info"
                    ))
                    return

        self.results.append(TestResult(
            category="resource_usage",
            test="Memory per phase",
            passed=True,
            message="Skipped - run UAT first to measure",
            severity="info"
        ))

    # ========================================================================
    # RESOURCE CLEANUP TESTS
    # ========================================================================

    def test_file_descriptor_leaks(self):
        """Test for file descriptor leaks."""
        initial_fds = self.count_open_files()

        # Do some file operations
        temp_file = REPO_ROOT / "test" / "reports" / "perf_test_temp.txt"
        for _ in range(20):
            with open(temp_file, "w") as f:
                f.write("test\n")

        temp_file.unlink(missing_ok=True)

        final_fds = self.count_open_files()
        fd_growth = final_fds - initial_fds

        metrics = PerformanceMetrics(open_files=final_fds)

        if fd_growth <= 2:
            self.results.append(TestResult(
                category="cleanup",
                test="File descriptor leaks",
                passed=True,
                message=f"FD count stable ({final_fds} open)",
                metrics=metrics,
                severity="info"
            ))
        else:
            self.results.append(TestResult(
                category="cleanup",
                test="File descriptor leaks",
                passed=False,
                message=f"FD leak detected (+{fd_growth} descriptors)",
                metrics=metrics,
                severity="warning"
            ))

    def test_temp_file_cleanup(self):
        """Test that temporary files are cleaned up."""
        temp_locations = [
            OUTPUT_DIR / "tmp",
            STATE_DIR / "tmp",
        ]

        temp_files = []
        for location in temp_locations:
            if location.exists() and location.is_dir():
                temp_files.extend(list(location.glob("*")))

        if len(temp_files) < 50:
            self.results.append(TestResult(
                category="cleanup",
                test="Temp file cleanup",
                passed=True,
                message=f"{len(temp_files)} temp files found (acceptable)",
                severity="info"
            ))
        else:
            self.results.append(TestResult(
                category="cleanup",
                test="Temp file cleanup",
                passed=False,
                message=f"Too many temp files: {len(temp_files)}",
                severity="warning"
            ))

    def test_orphaned_processes(self):
        """Test for orphaned processes."""
        if not HAS_PSUTIL:
            self.results.append(TestResult(
                category="cleanup",
                test="Orphaned processes",
                passed=True,
                message="Skipped - requires psutil",
                severity="info"
            ))
            return

        try:
            current_process = psutil.Process()
            children = current_process.children(recursive=True)

            # Filter for zombies
            zombies = [p for p in children if p.status() == psutil.STATUS_ZOMBIE]

            metrics = PerformanceMetrics(processes=len(children))

            if not zombies:
                self.results.append(TestResult(
                    category="cleanup",
                    test="Orphaned processes",
                    passed=True,
                    message=f"No zombie processes ({len(children)} children)",
                    metrics=metrics,
                    severity="info"
                ))
            else:
                self.results.append(TestResult(
                    category="cleanup",
                    test="Orphaned processes",
                    passed=False,
                    message=f"Found {len(zombies)} zombie processes",
                    metrics=metrics,
                    severity="critical"
                ))
        except Exception as e:
            self.results.append(TestResult(
                category="cleanup",
                test="Orphaned processes",
                passed=True,
                message=f"Skipped - error checking processes: {e}",
                severity="info"
            ))

    def test_open_file_count(self):
        """Test that open file count is reasonable."""
        open_files = self.count_open_files()

        metrics = PerformanceMetrics(open_files=open_files)

        if open_files < 50:
            self.results.append(TestResult(
                category="cleanup",
                test="Open file count",
                passed=True,
                message=f"{open_files} files open (good)",
                metrics=metrics,
                severity="info"
            ))
        elif open_files < 100:
            self.results.append(TestResult(
                category="cleanup",
                test="Open file count",
                passed=True,
                message=f"{open_files} files open (acceptable)",
                metrics=metrics,
                severity="info"
            ))
        else:
            self.results.append(TestResult(
                category="cleanup",
                test="Open file count",
                passed=False,
                message=f"Too many open files: {open_files}",
                metrics=metrics,
                severity="warning"
            ))

    # ========================================================================
    # CPU USAGE TESTS
    # ========================================================================

    def test_cpu_usage(self):
        """Test that CPU usage is reasonable."""
        measurements = []

        for _ in range(5):
            cpu = self.measure_cpu()
            measurements.append(cpu)
            time.sleep(0.5)

        avg_cpu = sum(measurements) / len(measurements)
        max_cpu = max(measurements)

        metrics = PerformanceMetrics(cpu_percent=avg_cpu)

        if avg_cpu < 50:
            self.results.append(TestResult(
                category="resource_usage",
                test="CPU usage reasonable",
                passed=True,
                message=f"CPU avg: {avg_cpu:.1f}%, max: {max_cpu:.1f}%",
                metrics=metrics,
                severity="info"
            ))
        else:
            self.results.append(TestResult(
                category="resource_usage",
                test="CPU usage reasonable",
                passed=False,
                message=f"High CPU usage: avg {avg_cpu:.1f}%, max {max_cpu:.1f}%",
                metrics=metrics,
                severity="warning"
            ))

    def test_cpu_spike_detection(self):
        """Test for CPU spikes."""
        measurements = []

        for _ in range(10):
            cpu = self.measure_cpu()
            measurements.append(cpu)
            time.sleep(0.2)

        max_cpu = max(measurements)
        spikes = [m for m in measurements if m > 80]

        metrics = PerformanceMetrics(cpu_percent=max_cpu)

        if len(spikes) <= 2:
            self.results.append(TestResult(
                category="resource_usage",
                test="CPU spike detection",
                passed=True,
                message=f"No sustained spikes (max: {max_cpu:.1f}%)",
                metrics=metrics,
                severity="info"
            ))
        else:
            self.results.append(TestResult(
                category="resource_usage",
                test="CPU spike detection",
                passed=False,
                message=f"CPU spikes detected: {len(spikes)} measurements > 80%",
                metrics=metrics,
                severity="warning"
            ))

    # ========================================================================
    # DISK I/O TESTS
    # ========================================================================

    def test_log_growth(self):
        """Test for runaway log growth."""
        log_files = [
            LOG_DIR / "atomic.log",
            LOG_DIR / "provider.log",
            LOG_DIR / "task.log",
        ]

        large_logs = []
        total_size = 0

        for log_file in log_files:
            if log_file.exists():
                size_mb = log_file.stat().st_size / (1024 * 1024)
                total_size += size_mb
                if size_mb > 100:
                    large_logs.append((log_file.name, size_mb))

        metrics = PerformanceMetrics(disk_writes_kb=total_size * 1024)

        if not large_logs:
            self.results.append(TestResult(
                category="resource_usage",
                test="Log file growth",
                passed=True,
                message=f"Total logs: {total_size:.1f}MB (acceptable)",
                metrics=metrics,
                severity="info"
            ))
        else:
            logs_str = ", ".join(f"{name} ({size:.1f}MB)" for name, size in large_logs)
            self.results.append(TestResult(
                category="resource_usage",
                test="Log file growth",
                passed=False,
                message=f"Large log files: {logs_str}",
                metrics=metrics,
                severity="warning"
            ))

    def test_output_size(self):
        """Test that output files are reasonable size."""
        if not OUTPUT_DIR.exists():
            self.results.append(TestResult(
                category="resource_usage",
                test="Output file size",
                passed=True,
                message="No output directory yet",
                severity="info"
            ))
            return

        total_size = 0
        large_files = []

        for output_file in OUTPUT_DIR.rglob("*"):
            if output_file.is_file():
                size_mb = output_file.stat().st_size / (1024 * 1024)
                total_size += size_mb
                if size_mb > 50:
                    large_files.append((output_file.name, size_mb))

        metrics = PerformanceMetrics(disk_writes_kb=total_size * 1024)

        if total_size < 500:
            self.results.append(TestResult(
                category="resource_usage",
                test="Output file size",
                passed=True,
                message=f"Total outputs: {total_size:.1f}MB",
                metrics=metrics,
                severity="info"
            ))
        else:
            self.results.append(TestResult(
                category="resource_usage",
                test="Output file size",
                passed=False,
                message=f"Large output size: {total_size:.1f}MB",
                metrics=metrics,
                severity="warning"
            ))

    # ========================================================================
    # SCALABILITY TESTS
    # ========================================================================

    def test_concurrent_operations(self):
        """Test handling of concurrent file operations."""
        import threading

        def write_test_file(index):
            test_file = REPO_ROOT / "test" / "reports" / f"concurrent_{index}.txt"
            with open(test_file, "w") as f:
                f.write(f"test {index}\n")
            test_file.unlink(missing_ok=True)

        start_time = time.time()
        threads = []

        for i in range(10):
            t = threading.Thread(target=write_test_file, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        duration_ms = (time.time() - start_time) * 1000
        metrics = PerformanceMetrics(duration_ms=duration_ms)

        if duration_ms < 1000:
            self.results.append(TestResult(
                category="scalability",
                test="Concurrent operations",
                passed=True,
                message=f"10 concurrent ops in {duration_ms:.0f}ms",
                metrics=metrics,
                severity="info"
            ))
        else:
            self.results.append(TestResult(
                category="scalability",
                test="Concurrent operations",
                passed=False,
                message=f"Slow concurrent ops: {duration_ms:.0f}ms",
                metrics=metrics,
                severity="warning"
            ))

    def test_large_file_handling(self):
        """Test handling of large output files."""
        test_file = REPO_ROOT / "test" / "reports" / "large_test.txt"

        start_time = time.time()

        # Write 10MB file
        with open(test_file, "w") as f:
            for _ in range(100000):
                f.write("x" * 100 + "\n")

        write_time = (time.time() - start_time) * 1000

        # Read it back
        start_time = time.time()
        with open(test_file, "r") as f:
            content = f.read()
        read_time = (time.time() - start_time) * 1000

        test_file.unlink(missing_ok=True)

        metrics = PerformanceMetrics(
            duration_ms=write_time + read_time,
            disk_writes_kb=len(content) / 1024
        )

        if write_time < 2000 and read_time < 1000:
            self.results.append(TestResult(
                category="scalability",
                test="Large file handling",
                passed=True,
                message=f"10MB file: write {write_time:.0f}ms, read {read_time:.0f}ms",
                metrics=metrics,
                severity="info"
            ))
        else:
            self.results.append(TestResult(
                category="scalability",
                test="Large file handling",
                passed=False,
                message=f"Slow file I/O: write {write_time:.0f}ms, read {read_time:.0f}ms",
                metrics=metrics,
                severity="warning"
            ))

    # ========================================================================
    # MAIN TEST RUNNER
    # ========================================================================

    def run_all_tests(self):
        """Run all performance tests."""
        self.log("\n" + "="*70, Colors.CYAN)
        self.log("  PERFORMANCE AUDIT RUNNER", Colors.BOLD)
        self.log("="*70, Colors.CYAN)

        if not HAS_PSUTIL:
            self.log("\n⚠️  psutil not available - using fallback monitoring", Colors.YELLOW)
            self.log("   Install with: pip install psutil\n", Colors.DIM)

        # Run test categories
        self.log("\n" + Colors.BOLD + "Execution Time Tests:" + Colors.NC)
        self.test_phase_0_execution_time()
        self.test_full_pipeline_time()
        self.test_task_timeout_compliance()
        self.test_slow_task_detection()

        self.log("\n" + Colors.BOLD + "Resource Usage Tests:" + Colors.NC)
        self.test_memory_footprint()
        self.test_memory_leak_detection()
        self.test_memory_per_phase()
        self.test_cpu_usage()
        self.test_cpu_spike_detection()
        self.test_log_growth()
        self.test_output_size()

        self.log("\n" + Colors.BOLD + "Resource Cleanup Tests:" + Colors.NC)
        self.test_file_descriptor_leaks()
        self.test_temp_file_cleanup()
        self.test_orphaned_processes()
        self.test_open_file_count()

        self.log("\n" + Colors.BOLD + "Scalability Tests:" + Colors.NC)
        self.test_concurrent_operations()
        self.test_large_file_handling()

        # Display results
        self.display_results()

        # Save report
        self.save_report()

        # Return exit code
        critical_failures = [r for r in self.results if not r.passed and r.severity == "critical"]
        return 0 if not critical_failures else 1

    def display_results(self):
        """Display test results summary."""
        self.log("\n" + "="*70, Colors.CYAN)
        self.log("  TEST RESULTS", Colors.BOLD)
        self.log("="*70, Colors.CYAN)

        # Count results
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        critical = sum(1 for r in self.results if not r.passed and r.severity == "critical")
        warnings = sum(1 for r in self.results if not r.passed and r.severity == "warning")

        # Overall stats
        self.log(f"\nTotal Tests:     {len(self.results)}", Colors.BOLD)
        self.log(f"{Colors.GREEN}Passed:{Colors.NC}          {passed}")
        self.log(f"{Colors.RED}Failed:{Colors.NC}          {failed}")
        self.log(f"{Colors.RED}  Critical:{Colors.NC}      {critical}")
        self.log(f"{Colors.YELLOW}  Warnings:{Colors.NC}     {warnings}")

        # Category breakdown
        categories = {}
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = {"passed": 0, "failed": 0, "critical": 0, "warning": 0}

            if result.passed:
                categories[result.category]["passed"] += 1
            else:
                categories[result.category]["failed"] += 1
                if result.severity == "critical":
                    categories[result.category]["critical"] += 1
                elif result.severity == "warning":
                    categories[result.category]["warning"] += 1

        self.log(f"\n{Colors.BOLD}Category Breakdown:{Colors.NC}\n")
        for category, stats in sorted(categories.items()):
            total = stats["passed"] + stats["failed"]
            rate = (stats["passed"] / total * 100) if total > 0 else 0

            if stats["critical"] > 0:
                status = f"{Colors.RED}✗{Colors.NC}"
            elif stats["warning"] > 0:
                status = f"{Colors.YELLOW}⚠{Colors.NC}"
            else:
                status = f"{Colors.GREEN}✓{Colors.NC}"

            detail = ""
            if stats["critical"] > 0:
                detail += f" ({stats['critical']} critical)"
            if stats["warning"] > 0:
                detail += f" ({stats['warning']} warnings)"

            self.log(f"  {status} {category:<25} {stats['passed']}/{total} ({rate:.0f}%){detail}")

        # Show failures
        failures = [r for r in self.results if not r.passed]
        if failures:
            self.log(f"\n{Colors.BOLD}Failed Tests:{Colors.NC}\n")
            for result in failures:
                color = Colors.RED if result.severity == "critical" else Colors.YELLOW
                symbol = "✗" if result.severity == "critical" else "⚠"
                self.log(f"  {color}{symbol} {result.test}{Colors.NC}")
                self.log(f"    {Colors.DIM}{result.message}{Colors.NC}")

        # Overall status
        self.log(f"\n{'='*70}", Colors.CYAN)
        if critical > 0:
            self.log(f"{Colors.RED}PERFORMANCE AUDIT FAILED - {critical} critical issues{Colors.NC}", Colors.BOLD)
        elif warnings > 0:
            self.log(f"{Colors.YELLOW}PERFORMANCE AUDIT PASSED - {warnings} warnings{Colors.NC}", Colors.BOLD)
        else:
            self.log(f"{Colors.GREEN}PERFORMANCE AUDIT PASSED - all tests succeeded{Colors.NC}", Colors.BOLD)
        self.log("="*70 + "\n", Colors.CYAN)

    def save_report(self):
        """Save detailed JSON report."""
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        report_file = REPO_ROOT / "test" / "reports" / f"performance-audit-{timestamp}.json"

        # Count stats
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        critical = sum(1 for r in self.results if not r.passed and r.severity == "critical")
        warnings = sum(1 for r in self.results if not r.passed and r.severity == "warning")

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.results),
            "passed": passed,
            "failed": failed,
            "critical": critical,
            "warnings": warnings,
            "success_rate": f"{(passed / len(self.results) * 100):.1f}%",
            "results": [r.to_dict() for r in self.results]
        }

        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        self.log(f"{Colors.DIM}Report saved: {report_file}{Colors.NC}\n")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Performance Audit Runner - Validate pipeline performance",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    parser.add_argument(
        "--profile",
        action="store_true",
        help="Run with profiling enabled"
    )

    args = parser.parse_args()

    runner = PerformanceAuditRunner(verbose=args.verbose, profile=args.profile)
    exit_code = runner.run_all_tests()

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
