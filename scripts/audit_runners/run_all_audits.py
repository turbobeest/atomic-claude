#!/usr/bin/env python3
"""
Master Audit Runner
Orchestrates all audit runners and generates comprehensive reports

This master runner:
1. Runs all audit runners in priority order
2. Captures and consolidates results
3. Continues execution even if some audits fail
4. Tracks total execution time
5. Generates master report with executive summary
6. Calculates overall grade (A/B/C/D/F)
7. Identifies critical issues across all audits
"""

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


# ============================================================================
# ANSI COLOR CODES
# ============================================================================

BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
NC = "\033[0m"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class AuditResult:
    """Result from a single audit runner."""
    name: str
    runner_path: str
    status: str  # passed, failed, skipped, error
    duration: float
    total_tests: int
    passed_tests: int
    failed_tests: int
    pass_rate: float
    critical_issues: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    report_path: Optional[str] = None


@dataclass
class MasterReport:
    """Consolidated report from all audits."""
    timestamp: str
    total_duration: float
    audits_run: int
    audits_passed: int
    audits_failed: int
    audits_skipped: int
    total_tests: int
    total_passed: int
    total_failed: int
    overall_pass_rate: float
    overall_grade: str
    critical_issues_count: int
    audit_results: List[AuditResult]
    critical_issues: List[Dict[str, Any]] = field(default_factory=list)


# ============================================================================
# AUDIT DEFINITIONS
# ============================================================================

# Priority order for audit execution
AUDIT_DEFINITIONS = [
    {
        'name': 'Dependency Audit',
        'runner': 'dependency_audit_runner.py',
        'critical': True,
        'description': 'Validates all required tools and versions'
    },
    {
        'name': 'Script Quality Audit',
        'runner': 'script_audit_runner.py',
        'critical': True,
        'description': 'Validates bash script quality and patterns'
    },
    {
        'name': 'Configuration Audit',
        'runner': 'config_audit_runner.py',
        'critical': False,
        'description': 'Validates configuration files and environment'
    },
    {
        'name': 'State Management Audit',
        'runner': 'state_audit_runner.py',
        'critical': True,
        'description': 'Validates state tracking and persistence'
    },
    {
        'name': 'Output Validation Audit',
        'runner': 'output_audit_runner.py',
        'critical': False,
        'description': 'Validates output structure and content'
    },
    {
        'name': 'Integration Points Audit',
        'runner': 'integration_audit_runner.py',
        'critical': False,
        'description': 'Validates Python-to-bash handoffs'
    },
    {
        'name': 'Error Handling Audit',
        'runner': 'error_audit_runner.py',
        'critical': True,
        'description': 'Validates graceful failure and recovery'
    },
    {
        'name': 'Security Audit',
        'runner': 'security_audit_runner.py',
        'critical': True,
        'description': 'Validates security practices and vulnerabilities'
    },
    {
        'name': 'Regression Tests',
        'runner': 'regression_test_runner.py',
        'critical': False,
        'description': 'Validates no regressions from previous versions'
    },
    {
        'name': 'Performance Audit',
        'runner': 'performance_audit_runner.py',
        'critical': False,
        'description': 'Validates performance and resource usage'
    },
    {
        'name': 'Memory Audit',
        'runner': 'memory_audit_runner.py',
        'critical': False,
        'description': 'Validates memory system functionality'
    },
    {
        'name': 'Smoke Tests',
        'runner': 'smoke_test_runner.py',
        'critical': True,
        'description': 'Validates basic end-to-end functionality'
    },
]


# ============================================================================
# MASTER AUDIT RUNNER
# ============================================================================

class MasterAuditRunner:
    """
    Orchestrates all audit runners and generates comprehensive reports.
    """

    def __init__(self, test_dir: Optional[Path] = None):
        if test_dir:
            self.test_dir = test_dir
        else:
            self.test_dir = Path(__file__).parent.resolve()

        self.atomic_root = self.test_dir.parent
        self.reports_dir = self.test_dir / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        self.audit_results: List[AuditResult] = []
        self.start_time = 0.0

    def run_audit(self, audit_def: Dict[str, Any]) -> AuditResult:
        """
        Run a single audit runner and capture results.

        Args:
            audit_def: Audit definition with name, runner path, etc.

        Returns:
            AuditResult with execution details
        """
        name = audit_def['name']
        runner_path = self.test_dir / audit_def['runner']

        print(f"\n{BOLD}{CYAN}{'='*70}{NC}")
        print(f"{BOLD}{CYAN}Running: {name}{NC}")
        print(f"{CYAN}{'='*70}{NC}")
        print(f"{DIM}Description: {audit_def['description']}{NC}")
        print(f"{DIM}Critical: {audit_def['critical']}{NC}\n")

        if not runner_path.exists():
            print(f"{YELLOW}⚠ Audit runner not found: {runner_path}{NC}")
            return AuditResult(
                name=name,
                runner_path=str(runner_path),
                status='skipped',
                duration=0.0,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                pass_rate=0.0,
                error_message=f"Runner not found: {runner_path}"
            )

        start = time.time()

        try:
            # Run the audit runner
            result = subprocess.run(
                [sys.executable, str(runner_path)],
                cwd=str(self.test_dir),
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout per audit
            )

            duration = time.time() - start

            # Print output
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(f"{YELLOW}{result.stderr}{NC}", file=sys.stderr)

            # Try to parse the report JSON
            report_path = self._find_latest_report(audit_def['runner'])

            if report_path and report_path.exists():
                with open(report_path) as f:
                    report_data = json.load(f)

                # Extract metrics from report
                total_tests = report_data.get('total_tests', 0)
                passed = report_data.get('passed', 0)
                failed = report_data.get('failed', 0)
                pass_rate = (passed / total_tests * 100) if total_tests > 0 else 0.0

                # Extract critical issues
                critical_issues = []
                if 'results' in report_data:
                    for test in report_data['results']:
                        # Handle different report formats
                        is_failed = False

                        # Check 'passed' field (used by most audits)
                        if 'passed' in test:
                            is_failed = not test.get('passed', False)
                        # Check 'status' field (used by dependency audit)
                        elif 'status' in test:
                            is_failed = test.get('status') not in ['ok', 'passed', 'success']

                        if is_failed:
                            if test.get('category') in ['critical', 'security', 'core']:
                                critical_issues.append(test.get('name', 'Unknown'))

                status = 'passed' if result.returncode == 0 else 'failed'

                return AuditResult(
                    name=name,
                    runner_path=str(runner_path),
                    status=status,
                    duration=duration,
                    total_tests=total_tests,
                    passed_tests=passed,
                    failed_tests=failed,
                    pass_rate=pass_rate,
                    critical_issues=critical_issues,
                    report_path=str(report_path)
                )
            else:
                # No report found, use exit code only
                status = 'passed' if result.returncode == 0 else 'failed'
                return AuditResult(
                    name=name,
                    runner_path=str(runner_path),
                    status=status,
                    duration=duration,
                    total_tests=0,
                    passed_tests=0,
                    failed_tests=0,
                    pass_rate=0.0,
                    error_message='No report generated'
                )

        except subprocess.TimeoutExpired:
            duration = time.time() - start
            print(f"{RED}✗ Audit timed out after 10 minutes{NC}")
            return AuditResult(
                name=name,
                runner_path=str(runner_path),
                status='error',
                duration=duration,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                pass_rate=0.0,
                error_message='Timeout after 10 minutes'
            )

        except Exception as e:
            duration = time.time() - start
            print(f"{RED}✗ Error running audit: {e}{NC}")
            return AuditResult(
                name=name,
                runner_path=str(runner_path),
                status='error',
                duration=duration,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                pass_rate=0.0,
                error_message=str(e)
            )

    def _find_latest_report(self, runner_name: str) -> Optional[Path]:
        """Find the most recent report file for a runner."""
        # Strip .py and _runner suffix
        base_name = runner_name.replace('.py', '').replace('_runner', '').replace('_audit', '')

        # Look for report files
        pattern = f"{base_name}-audit-*.json"
        reports = list(self.reports_dir.glob(pattern))

        if not reports:
            # Try alternate patterns
            pattern = f"{base_name}-*.json"
            reports = list(self.reports_dir.glob(pattern))

        if reports:
            # Return most recent
            return max(reports, key=lambda p: p.stat().st_mtime)

        return None

    def run_all_audits(
        self,
        skip_audits: List[str] = None,
        only_audit: Optional[str] = None,
        quick_mode: bool = False
    ) -> MasterReport:
        """
        Run all configured audits and generate master report.

        Args:
            skip_audits: List of audit names to skip
            only_audit: Run only this specific audit
            quick_mode: Run only critical audits

        Returns:
            MasterReport with consolidated results
        """
        self.start_time = time.time()
        skip_audits = skip_audits or []

        print(f"\n{BOLD}{MAGENTA}{'='*70}{NC}")
        print(f"{BOLD}{MAGENTA}ATOMIC CLAUDE - MASTER AUDIT RUNNER{NC}")
        print(f"{MAGENTA}{'='*70}{NC}")
        print(f"{DIM}Starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{NC}\n")

        if quick_mode:
            print(f"{YELLOW}Running in QUICK mode - critical audits only{NC}\n")

        # Determine which audits to run
        audits_to_run = AUDIT_DEFINITIONS

        if quick_mode:
            audits_to_run = [a for a in audits_to_run if a.get('critical', False)]

        if only_audit:
            audits_to_run = [a for a in audits_to_run if a['name'] == only_audit]
            if not audits_to_run:
                print(f"{RED}✗ Audit not found: {only_audit}{NC}")
                sys.exit(1)

        if skip_audits:
            audits_to_run = [a for a in audits_to_run if a['name'] not in skip_audits]

        # Run each audit
        for audit_def in audits_to_run:
            result = self.run_audit(audit_def)
            self.audit_results.append(result)

        # Generate master report
        return self._generate_master_report()

    def _generate_master_report(self) -> MasterReport:
        """Generate consolidated master report from all audit results."""
        total_duration = time.time() - self.start_time

        # Calculate totals
        audits_passed = sum(1 for r in self.audit_results if r.status == 'passed')
        audits_failed = sum(1 for r in self.audit_results if r.status == 'failed')
        audits_skipped = sum(1 for r in self.audit_results if r.status == 'skipped')

        total_tests = sum(r.total_tests for r in self.audit_results)
        total_passed = sum(r.passed_tests for r in self.audit_results)
        total_failed = sum(r.failed_tests for r in self.audit_results)

        overall_pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0.0

        # Collect all critical issues
        critical_issues = []
        for result in self.audit_results:
            for issue in result.critical_issues:
                critical_issues.append({
                    'audit': result.name,
                    'issue': issue
                })

        # Calculate grade
        grade = self._calculate_grade(overall_pass_rate, len(critical_issues))

        report = MasterReport(
            timestamp=datetime.now().isoformat(),
            total_duration=total_duration,
            audits_run=len(self.audit_results),
            audits_passed=audits_passed,
            audits_failed=audits_failed,
            audits_skipped=audits_skipped,
            total_tests=total_tests,
            total_passed=total_passed,
            total_failed=total_failed,
            overall_pass_rate=overall_pass_rate,
            overall_grade=grade,
            critical_issues_count=len(critical_issues),
            audit_results=self.audit_results,
            critical_issues=critical_issues
        )

        return report

    def _calculate_grade(self, pass_rate: float, critical_count: int) -> str:
        """
        Calculate overall grade based on pass rate and critical issues.

        Grading System:
        - A: 95%+ pass rate, 0 critical issues
        - B: 85-94% pass rate, 0 critical issues
        - C: 75-84% pass rate, <5 critical issues
        - D: 65-74% pass rate, <10 critical issues
        - F: <65% pass rate or 10+ critical issues
        """
        if critical_count >= 10:
            return 'F'

        if pass_rate >= 95 and critical_count == 0:
            return 'A'
        elif pass_rate >= 85 and critical_count == 0:
            return 'B'
        elif pass_rate >= 75 and critical_count < 5:
            return 'C'
        elif pass_rate >= 65 and critical_count < 10:
            return 'D'
        else:
            return 'F'

    def generate_executive_summary(self, report: MasterReport) -> str:
        """Generate a one-page executive summary."""
        lines = []

        lines.append("=" * 70)
        lines.append("ATOMIC CLAUDE - AUDIT EXECUTIVE SUMMARY")
        lines.append("=" * 70)
        lines.append("")

        # Overall verdict
        grade_color = {
            'A': GREEN,
            'B': CYAN,
            'C': YELLOW,
            'D': YELLOW,
            'F': RED
        }.get(report.overall_grade, NC)

        lines.append(f"Overall Grade: {grade_color}{BOLD}{report.overall_grade}{NC}")
        lines.append(f"Overall Pass Rate: {report.overall_pass_rate:.1f}%")
        lines.append(f"Total Duration: {report.total_duration:.1f}s")
        lines.append("")

        # Audit summary
        lines.append("AUDIT SUMMARY")
        lines.append("-" * 70)
        lines.append(f"Total Audits Run: {report.audits_run}")
        lines.append(f"Passed: {GREEN}{report.audits_passed}{NC}")
        lines.append(f"Failed: {RED}{report.audits_failed}{NC}")
        lines.append(f"Skipped: {YELLOW}{report.audits_skipped}{NC}")
        lines.append("")

        # Test summary
        lines.append("TEST SUMMARY")
        lines.append("-" * 70)
        lines.append(f"Total Tests: {report.total_tests}")
        lines.append(f"Passed: {GREEN}{report.total_passed}{NC}")
        lines.append(f"Failed: {RED}{report.total_failed}{NC}")
        lines.append("")

        # Critical issues
        lines.append("CRITICAL ISSUES")
        lines.append("-" * 70)
        if report.critical_issues_count == 0:
            lines.append(f"{GREEN}✓ No critical issues found{NC}")
        else:
            lines.append(f"{RED}✗ {report.critical_issues_count} critical issues found{NC}")
            for issue in report.critical_issues[:10]:  # Show first 10
                lines.append(f"  • [{issue['audit']}] {issue['issue']}")
            if report.critical_issues_count > 10:
                lines.append(f"  ... and {report.critical_issues_count - 10} more")
        lines.append("")

        # Per-audit results
        lines.append("PER-AUDIT RESULTS")
        lines.append("-" * 70)
        for result in report.audit_results:
            status_icon = {
                'passed': f"{GREEN}✓{NC}",
                'failed': f"{RED}✗{NC}",
                'skipped': f"{YELLOW}○{NC}",
                'error': f"{RED}✗{NC}"
            }.get(result.status, "?")

            lines.append(f"{status_icon} {result.name}")
            lines.append(f"   Pass Rate: {result.pass_rate:.1f}% ({result.passed_tests}/{result.total_tests})")
            lines.append(f"   Duration: {result.duration:.1f}s")
            if result.critical_issues:
                lines.append(f"   {RED}Critical Issues: {len(result.critical_issues)}{NC}")

        lines.append("")
        lines.append("=" * 70)

        return "\n".join(lines)

    def save_report(self, report: MasterReport) -> Path:
        """Save master report to JSON file."""
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        report_path = self.reports_dir / f"master-audit-{timestamp}.json"

        # Convert to dict for JSON serialization
        report_dict = asdict(report)

        with open(report_path, 'w') as f:
            json.dump(report_dict, f, indent=2)

        print(f"\n{CYAN}Master report saved: {report_path}{NC}")
        return report_path

    def print_report(self, report: MasterReport):
        """Print formatted report to console."""
        summary = self.generate_executive_summary(report)
        print(f"\n{summary}")


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Master audit runner for ATOMIC CLAUDE',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Run all audits
  %(prog)s --quick                  # Run only critical audits
  %(prog)s --skip "Memory Audit"    # Skip specific audit
  %(prog)s --only "Security Audit"  # Run only one audit
  %(prog)s --comprehensive          # Run all with verbose output
        """
    )

    parser.add_argument(
        '--quick',
        action='store_true',
        help='Run only critical audits'
    )

    parser.add_argument(
        '--skip',
        action='append',
        metavar='AUDIT',
        help='Skip specific audit (can be used multiple times)'
    )

    parser.add_argument(
        '--only',
        metavar='AUDIT',
        help='Run only specific audit'
    )

    parser.add_argument(
        '--comprehensive',
        action='store_true',
        help='Run all audits with verbose output (same as default)'
    )

    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available audits'
    )

    args = parser.parse_args()

    # List audits if requested
    if args.list:
        print(f"\n{BOLD}Available Audits:{NC}\n")
        for i, audit in enumerate(AUDIT_DEFINITIONS, 1):
            critical = f"{RED}[CRITICAL]{NC}" if audit['critical'] else ""
            print(f"{i:2}. {audit['name']} {critical}")
            print(f"    {DIM}{audit['description']}{NC}")
            print(f"    {DIM}Runner: {audit['runner']}{NC}\n")
        return 0

    # Create runner and execute
    runner = MasterAuditRunner()

    try:
        report = runner.run_all_audits(
            skip_audits=args.skip,
            only_audit=args.only,
            quick_mode=args.quick
        )

        # Print and save report
        runner.print_report(report)
        runner.save_report(report)

        # Determine exit code based on critical audits
        critical_audits = [r for r in report.audit_results
                          if any(a['name'] == r.name and a.get('critical', False)
                                for a in AUDIT_DEFINITIONS)]

        critical_failed = any(r.status == 'failed' for r in critical_audits)

        if critical_failed:
            print(f"\n{RED}{BOLD}✗ Critical audits failed{NC}")
            return 1
        else:
            print(f"\n{GREEN}{BOLD}✓ All critical audits passed{NC}")
            return 0

    except KeyboardInterrupt:
        print(f"\n{YELLOW}Audit interrupted by user{NC}")
        return 130
    except Exception as e:
        print(f"\n{RED}Error running master audit: {e}{NC}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
