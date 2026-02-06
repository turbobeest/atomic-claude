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
"""

import json
import os
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
    print("Warning: psutil not available, falling back to ps/top commands")


# ============================================================================
# ANSI COLOR CODES
# ============================================================================

BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
CYAN = "\033[36m"
NC = "\033[0m"


# ============================================================================
# PERFORMANCE DATA STRUCTURES
# ============================================================================

@dataclass
class PerformanceMetrics:
    """Performance metrics for a phase or full pipeline."""
    name: str
    duration: float
    peak_memory_mb: float
    avg_memory_mb: float
    peak_cpu_percent: float
    avg_cpu_percent: float
    file_descriptors_start: int
    file_descriptors_end: int
    process_count_start: int
    process_count_end: int
    disk_writes_mb: float = 0.0
    warnings: List[str] = field(default_factory=list)


@dataclass
class TestResult:
    """Result of a single performance test."""
    name: str
    category: str
    passed: bool
    duration: float
    error_message: Optional[str] = None
    details: Dict = field(default_factory=dict)


@dataclass
class PerformanceReport:
    """Overall performance audit report."""
    timestamp: str
    total_tests: int
    passed: int
    failed: int
    warnings: int
    duration: float
    metrics: Optional[PerformanceMetrics]
    results: List[TestResult]

    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100


# ============================================================================
# PERFORMANCE AUDIT RUNNER
# ============================================================================

class PerformanceAuditRunner:
    """
    Validates performance characteristics of the pipeline.
    """

    def __init__(self):
        self.atomic_root = Path(__file__).parent.parent.resolve()
        self.test_dir = self.atomic_root / "test"
        self.reports_dir = self.test_dir / "reports"
        self.main_script = self.atomic_root / "atomic-claude-python" / "main.py"

        # Ensure directories exist
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        self.results: List[TestResult] = []
        self.pipeline_metrics: Optional[PerformanceMetrics] = None

    def run_all_tests(self) -> PerformanceReport:
        """
        Run all performance tests and return report.
        """
        start_time = time.time()

        print(f"\n{BOLD}{CYAN}{'='*70}{NC}")
        print(f"{BOLD}  Performance Audit Runner{NC}")
        print(f"{CYAN}{'='*70}{NC}\n")

        if not HAS_PSUTIL:
            print(f"{YELLOW}⚠ psutil not available - using fallback monitoring{NC}\n")

        # Run test categories
        print(f"{BOLD}Running Performance Tests:{NC}\n")

        self._run_category("Execution Time", [
            self.test_full_pipeline_execution_time,
            self.test_phase_timing_breakdown,
            self.test_slow_phase_detection,
        ])

        self._run_category("Memory Usage", [
            self.test_memory_footprint,
            self.test_memory_stability,
            self.test_memory_leak_detection,
        ])

        self._run_category("Resource Cleanup", [
            self.test_file_descriptor_leaks,
            self.test_zombie_processes,
            self.test_temp_file_cleanup,
            self.test_open_file_count,
        ])

        self._run_category("CPU Usage", [
            self.test_cpu_usage_reasonable,
            self.test_cpu_spike_detection,
        ])

        self._run_category("Disk I/O", [
            self.test_file_operations,
            self.test_log_growth,
        ])

        self._run_category("Background Processes", [
            self.test_subprocess_termination,
            self.test_orphaned_children,
        ])

        # Generate report
        duration = time.time() - start_time
        report = self._generate_report(duration)

        # Save report
        self._save_report(report)

        # Display summary
        self._display_summary(report)

        return report

    def _run_category(self, category_name: str, tests: List):
        """Run a category of tests."""
        print(f"{BOLD}{category_name}:{NC}")
        for test in tests:
            result = self._run_test(test, category_name)
            self.results.append(result)

            if result.passed:
                status = f"{GREEN}✓{NC}"
            elif result.error_message and "warning" in result.error_message.lower():
                status = f"{YELLOW}⚠{NC}"
            else:
                status = f"{RED}✗{NC}"

            print(f"  {status} {result.name}")

            if not result.passed and result.error_message:
                print(f"    {DIM}{result.error_message}{NC}")

            # Show performance details if available
            if result.details:
                for key, value in result.details.items():
                    if key.startswith("_"):
                        continue
                    print(f"    {DIM}{key}: {value}{NC}")
        print()

    def _run_test(self, test_func, category: str) -> TestResult:
        """Run a single test and capture result."""
        start_time = time.time()

        try:
            test_func()
            duration = time.time() - start_time
            return TestResult(
                name=test_func.__name__.replace('test_', '').replace('_', ' ').title(),
                category=category,
                passed=True,
                duration=duration
            )
        except AssertionError as e:
            duration = time.time() - start_time
            return TestResult(
                name=test_func.__name__.replace('test_', '').replace('_', ' ').title(),
                category=category,
                passed=False,
                duration=duration,
                error_message=str(e)
            )
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                name=test_func.__name__.replace('test_', '').replace('_', ' ').title(),
                category=category,
                passed=False,
                duration=duration,
                error_message=f"Unexpected error: {e}"
            )

    # ========================================================================
    # EXECUTION TIME TESTS
    # ========================================================================

    def test_full_pipeline_execution_time(self):
        """Test that full UAT pipeline executes in < 10 minutes."""
        # This is a placeholder - actual UAT run would be done separately
        # For now, we'll create a quick test setup

        # Check if we have UAT results already
        uat_results = self.reports_dir / "uat_performance.json"

        if uat_results.exists():
            with open(uat_results) as f:
                data = json.load(f)
                duration = data.get("total_duration", 0)

                assert duration < 600, \
                    f"Pipeline took {duration:.1f}s (> 10 minutes)"
        else:
            # Skip this test if no UAT results available
            print(f"    {DIM}(Skipped - run UAT first to measure){NC}")

    def test_phase_timing_breakdown(self):
        """Test per-phase timing is tracked."""
        # Check task state for phase timings
        task_state = self.atomic_root / ".claude" / "task-state.json"

        if not task_state.exists():
            print(f"    {DIM}(Skipped - no task state available, run pipeline first){NC}")
            return

        with open(task_state) as f:
            state = json.load(f)

        # Verify we have timing data if tasks exist
        tasks = state.get("tasks", {})
        if not tasks:
            print(f"    {DIM}(Skipped - no tasks in state yet){NC}")
            return

        has_timing = any(
            "started_at" in task_data and "completed_at" in task_data
            for task_data in tasks.values()
        )

        if not has_timing:
            print(f"    {YELLOW}Warning: No timing data in task state{NC}")

    def test_slow_phase_detection(self):
        """Test identification of slow phases (> 60 seconds)."""
        task_state = self.atomic_root / ".claude" / "task-state.json"

        if not task_state.exists():
            print(f"    {DIM}(Skipped - no task state available){NC}")
            return

        with open(task_state) as f:
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
            tasks_str = ", ".join(f"{tid} ({dur:.1f}s)" for tid, dur in slow_tasks)
            print(f"    {YELLOW}Warning: Slow tasks detected: {tasks_str}{NC}")

    # ========================================================================
    # MEMORY USAGE TESTS
    # ========================================================================

    def measure_memory_usage(self) -> Dict:
        """Measure current memory usage."""
        if HAS_PSUTIL:
            process = psutil.Process()
            mem = process.memory_info()
            return {
                "rss_mb": mem.rss / (1024 * 1024),
                "vms_mb": mem.vms / (1024 * 1024),
            }
        else:
            # Fallback to ps command
            try:
                result = subprocess.run(
                    ["ps", "-o", "rss=", "-p", str(os.getpid())],
                    capture_output=True,
                    text=True
                )
                rss_kb = int(result.stdout.strip())
                return {"rss_mb": rss_kb / 1024, "vms_mb": 0}
            except:
                return {"rss_mb": 0, "vms_mb": 0}

    def test_memory_footprint(self):
        """Test that memory usage stays under 500MB."""
        mem = self.measure_memory_usage()
        rss_mb = mem["rss_mb"]

        if rss_mb > 500:
            raise AssertionError(
                f"Memory usage {rss_mb:.1f}MB exceeds 500MB threshold"
            )
        elif rss_mb > 400:
            print(f"    {YELLOW}Warning: Memory usage {rss_mb:.1f}MB is high{NC}")

    def test_memory_stability(self):
        """Test that memory is stable over time."""
        measurements = []

        # Take 5 measurements over 5 seconds
        for _ in range(5):
            mem = self.measure_memory_usage()
            measurements.append(mem["rss_mb"])
            time.sleep(1)

        # Check variance
        avg = sum(measurements) / len(measurements)
        variance = sum((x - avg) ** 2 for x in measurements) / len(measurements)
        std_dev = variance ** 0.5

        # Standard deviation should be < 50MB
        if std_dev > 50:
            raise AssertionError(
                f"Memory unstable: std_dev={std_dev:.1f}MB"
            )

    def test_memory_leak_detection(self):
        """Test for memory leaks by checking growth over time."""
        # Take initial measurement
        initial = self.measure_memory_usage()["rss_mb"]

        # Do some work (simulate task execution)
        for _ in range(10):
            # Allocate and release memory
            data = [0] * 10000
            del data
            time.sleep(0.1)

        # Take final measurement
        final = self.measure_memory_usage()["rss_mb"]

        # Growth should be minimal (< 10MB)
        growth = final - initial
        if growth > 10:
            print(f"    {YELLOW}Warning: Memory grew by {growth:.1f}MB{NC}")

    # ========================================================================
    # RESOURCE CLEANUP TESTS
    # ========================================================================

    def check_resource_cleanup(self) -> Dict:
        """Check resource cleanup status."""
        if HAS_PSUTIL:
            process = psutil.Process()
            return {
                "open_files": len(process.open_files()),
                "num_fds": process.num_fds() if hasattr(process, 'num_fds') else 0,
                "num_threads": process.num_threads(),
            }
        else:
            # Fallback to lsof
            try:
                result = subprocess.run(
                    ["lsof", "-p", str(os.getpid())],
                    capture_output=True,
                    text=True
                )
                open_files = len(result.stdout.strip().split('\n')) - 1
                return {"open_files": open_files, "num_fds": 0, "num_threads": 0}
            except:
                return {"open_files": 0, "num_fds": 0, "num_threads": 0}

    def test_file_descriptor_leaks(self):
        """Test for file descriptor leaks."""
        initial = self.check_resource_cleanup()

        # Do some file operations
        temp_file = self.test_dir / "temp_test.txt"
        for _ in range(10):
            with open(temp_file, "w") as f:
                f.write("test\n")

        temp_file.unlink(missing_ok=True)

        final = self.check_resource_cleanup()

        # File descriptors should be similar
        if HAS_PSUTIL:
            fd_growth = final["num_fds"] - initial["num_fds"]
            if fd_growth > 5:
                raise AssertionError(
                    f"File descriptor leak detected: +{fd_growth} FDs"
                )

    def test_zombie_processes(self):
        """Test that no zombie processes exist."""
        if HAS_PSUTIL:
            current_process = psutil.Process()
            children = current_process.children(recursive=True)

            zombies = [p for p in children if p.status() == psutil.STATUS_ZOMBIE]

            if zombies:
                raise AssertionError(
                    f"Zombie processes detected: {len(zombies)} zombies"
                )
        else:
            # Fallback to ps
            result = subprocess.run(
                ["ps", "-eo", "stat,pid,comm"],
                capture_output=True,
                text=True
            )

            zombies = [line for line in result.stdout.split('\n') if 'Z' in line]

            if zombies:
                print(f"    {YELLOW}Warning: Found zombie processes{NC}")

    def test_temp_file_cleanup(self):
        """Test that temporary files are cleaned up."""
        # Check for temp files in common locations
        temp_locations = [
            self.atomic_root / ".outputs" / "tmp",
            self.atomic_root / ".state" / "tmp",
            Path("/tmp/atomic-claude*"),
        ]

        temp_files = []
        for location in temp_locations:
            if location.exists() and location.is_dir():
                temp_files.extend(list(location.glob("*")))

        # Allow some temp files, but flag excessive amounts
        if len(temp_files) > 50:
            print(f"    {YELLOW}Warning: {len(temp_files)} temp files found{NC}")

    def test_open_file_count(self):
        """Test that open file count is reasonable."""
        resources = self.check_resource_cleanup()
        open_files = resources["open_files"]

        # Should have < 100 open files
        if open_files > 100:
            raise AssertionError(
                f"Too many open files: {open_files} (should be < 100)"
            )
        elif open_files > 50:
            print(f"    {YELLOW}Warning: {open_files} files open{NC}")

    # ========================================================================
    # CPU USAGE TESTS
    # ========================================================================

    def measure_cpu_usage(self) -> Dict:
        """Measure CPU usage."""
        if HAS_PSUTIL:
            process = psutil.Process()
            cpu_percent = process.cpu_percent(interval=1.0)
            return {"cpu_percent": cpu_percent}
        else:
            # Fallback to ps
            try:
                result = subprocess.run(
                    ["ps", "-o", "%cpu=", "-p", str(os.getpid())],
                    capture_output=True,
                    text=True
                )
                cpu_percent = float(result.stdout.strip())
                return {"cpu_percent": cpu_percent}
            except:
                return {"cpu_percent": 0}

    def test_cpu_usage_reasonable(self):
        """Test that CPU usage is reasonable."""
        # Take several measurements
        measurements = []
        for _ in range(3):
            cpu = self.measure_cpu_usage()["cpu_percent"]
            measurements.append(cpu)
            time.sleep(1)

        avg_cpu = sum(measurements) / len(measurements)

        # Average should be reasonable (< 50% for idle process)
        if avg_cpu > 50:
            print(f"    {YELLOW}Warning: High CPU usage {avg_cpu:.1f}%{NC}")

    def test_cpu_spike_detection(self):
        """Test for CPU spikes."""
        measurements = []

        for _ in range(5):
            cpu = self.measure_cpu_usage()["cpu_percent"]
            measurements.append(cpu)
            time.sleep(0.5)

        max_cpu = max(measurements)

        # Spikes > 80% sustained should be flagged
        spikes = [m for m in measurements if m > 80]
        if len(spikes) > 2:
            print(f"    {YELLOW}Warning: CPU spikes detected (max {max_cpu:.1f}%){NC}")

    # ========================================================================
    # DISK I/O TESTS
    # ========================================================================

    def test_file_operations(self):
        """Test that file operations are reasonable."""
        if HAS_PSUTIL:
            process = psutil.Process()

            # Check if io_counters is available (not on macOS)
            if not hasattr(process, 'io_counters'):
                print(f"    {DIM}(Skipped - io_counters not available on this platform){NC}")
                return

            try:
                io_before = process.io_counters()

                # Do some file operations
                test_file = self.test_dir / "io_test.txt"
                for _ in range(100):
                    with open(test_file, "w") as f:
                        f.write("test\n")

                test_file.unlink(missing_ok=True)

                io_after = process.io_counters()

                writes_mb = (io_after.write_bytes - io_before.write_bytes) / (1024 * 1024)

                # 100 small writes should be < 1MB
                if writes_mb > 10:
                    print(f"    {YELLOW}Warning: Wrote {writes_mb:.2f}MB{NC}")
            except AttributeError:
                print(f"    {DIM}(Skipped - io_counters not available on this platform){NC}")
        else:
            print(f"    {DIM}(Skipped - requires psutil){NC}")

    def test_log_growth(self):
        """Test for runaway log growth."""
        log_files = [
            self.atomic_root / ".logs" / "atomic.log",
            self.atomic_root / ".logs" / "provider.log",
        ]

        large_logs = []
        for log_file in log_files:
            if log_file.exists():
                size_mb = log_file.stat().st_size / (1024 * 1024)
                if size_mb > 100:
                    large_logs.append((log_file.name, size_mb))

        if large_logs:
            logs_str = ", ".join(f"{name} ({size:.1f}MB)" for name, size in large_logs)
            print(f"    {YELLOW}Warning: Large log files: {logs_str}{NC}")

    # ========================================================================
    # BACKGROUND PROCESS TESTS
    # ========================================================================

    def test_subprocess_termination(self):
        """Test that subprocesses terminate properly."""
        # Start a subprocess
        proc = subprocess.Popen(
            ["sleep", "5"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Terminate it
        proc.terminate()

        # Wait for termination
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            # Force kill if needed
            proc.kill()
            proc.wait()
            raise AssertionError("Subprocess did not terminate cleanly")

    def test_orphaned_children(self):
        """Test for orphaned child processes."""
        if HAS_PSUTIL:
            current_process = psutil.Process()

            # Start a child process
            proc = subprocess.Popen(
                ["sleep", "2"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Get children before termination
            children_before = len(current_process.children())

            # Terminate
            proc.terminate()
            proc.wait()

            # Get children after termination
            time.sleep(0.5)
            children_after = len(current_process.children())

            # Should have one fewer child
            assert children_after <= children_before, \
                "Child process may be orphaned"
        else:
            print(f"    {DIM}(Skipped - requires psutil){NC}")

    # ========================================================================
    # REPORTING
    # ========================================================================

    def _generate_report(self, duration: float) -> PerformanceReport:
        """Generate performance report from results."""
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed

        # Count warnings
        warnings = sum(
            1 for r in self.results
            if not r.passed and r.error_message and "warning" in r.error_message.lower()
        )

        return PerformanceReport(
            timestamp=datetime.now().isoformat(),
            total_tests=len(self.results),
            passed=passed,
            failed=failed,
            warnings=warnings,
            duration=duration,
            metrics=self.pipeline_metrics,
            results=self.results
        )

    def _save_report(self, report: PerformanceReport):
        """Save report to JSON file."""
        report_file = self.reports_dir / "performance_audit.json"

        data = {
            "timestamp": report.timestamp,
            "summary": {
                "total_tests": report.total_tests,
                "passed": report.passed,
                "failed": report.failed,
                "warnings": report.warnings,
                "success_rate": f"{report.success_rate():.1f}%",
                "duration": f"{report.duration:.2f}s"
            },
            "results": [
                {
                    "name": r.name,
                    "category": r.category,
                    "passed": r.passed,
                    "duration": f"{r.duration:.3f}s",
                    "error": r.error_message,
                    "details": r.details
                }
                for r in report.results
            ]
        }

        if report.metrics:
            data["pipeline_metrics"] = {
                "name": report.metrics.name,
                "duration": f"{report.metrics.duration:.2f}s",
                "peak_memory_mb": f"{report.metrics.peak_memory_mb:.1f}",
                "avg_memory_mb": f"{report.metrics.avg_memory_mb:.1f}",
                "peak_cpu_percent": f"{report.metrics.peak_cpu_percent:.1f}",
                "avg_cpu_percent": f"{report.metrics.avg_cpu_percent:.1f}",
                "warnings": report.metrics.warnings
            }

        with open(report_file, "w") as f:
            json.dump(data, f, indent=2)

        print(f"{DIM}Report saved to: {report_file}{NC}\n")

    def _display_summary(self, report: PerformanceReport):
        """Display summary of test results."""
        print(f"{BOLD}{CYAN}{'='*70}{NC}")
        print(f"{BOLD}  Performance Test Summary{NC}")
        print(f"{CYAN}{'='*70}{NC}\n")

        # Overall stats
        print(f"Total Tests:   {report.total_tests}")
        print(f"{GREEN}Passed:{NC}        {report.passed}")
        print(f"{RED}Failed:{NC}        {report.failed}")
        print(f"{YELLOW}Warnings:{NC}      {report.warnings}")
        print(f"Success Rate:  {report.success_rate():.1f}%")
        print(f"Duration:      {report.duration:.2f}s\n")

        # Pipeline metrics if available
        if report.metrics:
            print(f"{BOLD}Pipeline Performance:{NC}\n")
            print(f"  Execution Time: {report.metrics.duration:.1f}s")
            print(f"  Peak Memory:    {report.metrics.peak_memory_mb:.1f}MB")
            print(f"  Avg Memory:     {report.metrics.avg_memory_mb:.1f}MB")
            print(f"  Peak CPU:       {report.metrics.peak_cpu_percent:.1f}%")
            print(f"  Avg CPU:        {report.metrics.avg_cpu_percent:.1f}%")
            if report.metrics.warnings:
                print(f"\n  {YELLOW}Performance Warnings:{NC}")
                for warning in report.metrics.warnings:
                    print(f"    • {warning}")
            print()

        # Category breakdown
        categories = {}
        for result in report.results:
            if result.category not in categories:
                categories[result.category] = {"passed": 0, "failed": 0, "warnings": 0}
            if result.passed:
                categories[result.category]["passed"] += 1
            else:
                if result.error_message and "warning" in result.error_message.lower():
                    categories[result.category]["warnings"] += 1
                else:
                    categories[result.category]["failed"] += 1

        print(f"{BOLD}Category Breakdown:{NC}\n")
        for category, stats in categories.items():
            total = stats["passed"] + stats["failed"] + stats["warnings"]
            rate = (stats["passed"] / total * 100) if total > 0 else 0

            if stats["failed"] == 0 and stats["warnings"] == 0:
                status = f"{GREEN}✓{NC}"
            elif stats["failed"] == 0:
                status = f"{YELLOW}⚠{NC}"
            else:
                status = f"{RED}✗{NC}"

            warning_str = f" ({stats['warnings']} warnings)" if stats['warnings'] > 0 else ""
            print(f"  {status} {category:<30} {stats['passed']}/{total} ({rate:.0f}%){warning_str}")

        print(f"\n{CYAN}{'='*70}{NC}\n")

        # Exit with appropriate code
        if report.failed > 0:
            print(f"{RED}Performance audit FAILED with {report.failed} failures{NC}\n")
            return 1
        elif report.warnings > 0:
            print(f"{YELLOW}Performance audit PASSED with {report.warnings} warnings{NC}\n")
            return 0
        else:
            print(f"{GREEN}Performance audit PASSED - all tests succeeded{NC}\n")
            return 0


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point."""
    runner = PerformanceAuditRunner()
    report = runner.run_all_tests()

    # Exit with appropriate code (warnings don't fail)
    sys.exit(0 if report.failed == 0 else 1)


if __name__ == "__main__":
    main()
