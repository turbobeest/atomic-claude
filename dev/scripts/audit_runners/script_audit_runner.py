#!/usr/bin/env python3
"""
Script Quality Audit Runner

Comprehensive validation of bash scripts and Python code quality across the repository.

Usage:
    ./test/script_audit_runner.py [--bash-only | --python-only] [--json-report]

Exit Codes:
    0: All scripts valid
    1: Critical issues found
"""

import os
import sys
import json
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import importlib.util


@dataclass
class IssueReport:
    """Single issue found during audit"""
    file_path: str
    line_number: Optional[int]
    severity: str  # 'critical', 'warning', 'info'
    category: str  # 'syntax', 'antipattern', 'style', etc.
    message: str
    suggestion: Optional[str] = None


@dataclass
class FileAuditResult:
    """Audit result for a single file"""
    file_path: str
    file_type: str  # 'bash', 'python'
    passed: bool
    issues: List[IssueReport]
    execution_time_ms: float


@dataclass
class AuditSummary:
    """Overall audit summary"""
    total_files: int
    files_passed: int
    files_failed: int
    total_issues: int
    critical_issues: int
    warnings: int
    bash_files_checked: int
    python_files_checked: int
    execution_time_seconds: float
    timestamp: str


class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


class ScriptAuditRunner:
    """Main audit runner for bash and Python scripts"""

    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root)
        self.results: List[FileAuditResult] = []
        self.start_time = datetime.now()

        # Check for shellcheck availability
        self.has_shellcheck = self._check_shellcheck()

    def _check_shellcheck(self) -> bool:
        """Check if shellcheck is available"""
        try:
            subprocess.run(['shellcheck', '--version'],
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def audit_bash_scripts(self) -> List[FileAuditResult]:
        """Audit all bash scripts in the repository"""
        bash_files = self._find_bash_scripts()

        print(f"\n{Colors.CYAN}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}BASH SCRIPT AUDIT{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*80}{Colors.RESET}\n")
        print(f"Found {len(bash_files)} bash scripts to audit\n")

        if not self.has_shellcheck:
            print(f"{Colors.YELLOW}⚠ ShellCheck not found. Install with: brew install shellcheck{Colors.RESET}\n")

        results = []
        for script_path in bash_files:
            result = self._audit_single_bash_script(script_path)
            results.append(result)
            self._print_file_result(result)

        return results

    def audit_python_scripts(self) -> List[FileAuditResult]:
        """Audit all Python scripts in the repository"""
        python_files = self._find_python_scripts()

        print(f"\n{Colors.MAGENTA}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.MAGENTA}PYTHON SCRIPT AUDIT{Colors.RESET}")
        print(f"{Colors.MAGENTA}{'='*80}{Colors.RESET}\n")
        print(f"Found {len(python_files)} Python files to audit\n")

        results = []
        for script_path in python_files:
            result = self._audit_single_python_script(script_path)
            results.append(result)
            self._print_file_result(result)

        return results

    def _find_bash_scripts(self) -> List[Path]:
        """Find all bash scripts in the repository"""
        bash_scripts = []

        # Primary directories to check
        check_dirs = [
            self.repo_root / 'phases',
            self.repo_root / 'lib',
            self.repo_root / 'test',
            self.repo_root / 'agents',
            self.repo_root / 'audits',
            self.repo_root / 'dashboard',
        ]

        for directory in check_dirs:
            if directory.exists():
                bash_scripts.extend(directory.rglob('*.sh'))

        return sorted(bash_scripts)

    def _find_python_scripts(self) -> List[Path]:
        """Find all Python scripts in the repository"""
        python_scripts = []

        # Primary directories to check
        check_dirs = [
            self.repo_root / 'phases',
            self.repo_root / 'core',
            self.repo_root / 'orchestration',
            self.repo_root / 'test',
            self.repo_root / 'agents' / 'scripts',
            self.repo_root / 'audits' / 'scripts',
            self.repo_root / 'audits' / 'meta-audit',
        ]

        # Add main.py
        main_py = self.repo_root / 'main.py'
        if main_py.exists():
            python_scripts.append(main_py)

        for directory in check_dirs:
            if directory.exists():
                python_scripts.extend(directory.rglob('*.py'))

        return sorted(python_scripts)

    def _audit_single_bash_script(self, script_path: Path) -> FileAuditResult:
        """Audit a single bash script"""
        start_time = datetime.now()
        issues = []

        # Read script content
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            issues.append(IssueReport(
                file_path=str(script_path),
                line_number=None,
                severity='critical',
                category='read_error',
                message=f"Failed to read file: {str(e)}",
                suggestion=None
            ))
            exec_time = (datetime.now() - start_time).total_seconds() * 1000
            return FileAuditResult(
                file_path=str(script_path.relative_to(self.repo_root)),
                file_type='bash',
                passed=False,
                issues=issues,
                execution_time_ms=exec_time
            )

        # 1. Check shebang
        issues.extend(self._check_bash_shebang(script_path, lines))

        # 2. Check execute permissions
        issues.extend(self._check_execute_permissions(script_path))

        # 3. Bash syntax check
        issues.extend(self._check_bash_syntax(script_path))

        # 4. ShellCheck (if available)
        if self.has_shellcheck:
            issues.extend(self._run_shellcheck(script_path))

        # 5. Detect antipatterns
        issues.extend(self._detect_bash_antipatterns(script_path, lines))

        exec_time = (datetime.now() - start_time).total_seconds() * 1000
        has_critical = any(issue.severity == 'critical' for issue in issues)

        return FileAuditResult(
            file_path=str(script_path.relative_to(self.repo_root)),
            file_type='bash',
            passed=not has_critical,
            issues=issues,
            execution_time_ms=exec_time
        )

    def _audit_single_python_script(self, script_path: Path) -> FileAuditResult:
        """Audit a single Python script"""
        start_time = datetime.now()
        issues = []

        # Read script content
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            issues.append(IssueReport(
                file_path=str(script_path),
                line_number=None,
                severity='critical',
                category='read_error',
                message=f"Failed to read file: {str(e)}",
                suggestion=None
            ))
            exec_time = (datetime.now() - start_time).total_seconds() * 1000
            return FileAuditResult(
                file_path=str(script_path.relative_to(self.repo_root)),
                file_type='python',
                passed=False,
                issues=issues,
                execution_time_ms=exec_time
            )

        # 1. Check shebang for executable scripts
        if os.access(script_path, os.X_OK):
            issues.extend(self._check_python_shebang(script_path, lines))

        # 2. Python syntax check
        issues.extend(self._check_python_syntax(script_path))

        # 3. Import validation
        issues.extend(self._check_python_imports(script_path, lines))

        # 4. Detect debugging statements
        issues.extend(self._detect_python_debug_statements(script_path, lines))

        # 5. Check for TODO/FIXME
        issues.extend(self._detect_todo_fixme(script_path, lines))

        exec_time = (datetime.now() - start_time).total_seconds() * 1000
        has_critical = any(issue.severity == 'critical' for issue in issues)

        return FileAuditResult(
            file_path=str(script_path.relative_to(self.repo_root)),
            file_type='python',
            passed=not has_critical,
            issues=issues,
            execution_time_ms=exec_time
        )

    def _check_bash_shebang(self, script_path: Path, lines: List[str]) -> List[IssueReport]:
        """Check for proper bash shebang"""
        issues = []

        if not lines or not lines[0].startswith('#!'):
            issues.append(IssueReport(
                file_path=str(script_path),
                line_number=1,
                severity='warning',
                category='shebang',
                message='Missing shebang line',
                suggestion='Add: #!/usr/bin/env bash'
            ))
        elif lines[0].strip() not in ['#!/usr/bin/env bash', '#!/bin/bash']:
            issues.append(IssueReport(
                file_path=str(script_path),
                line_number=1,
                severity='warning',
                category='shebang',
                message=f'Non-standard shebang: {lines[0]}',
                suggestion='Use: #!/usr/bin/env bash'
            ))

        return issues

    def _check_python_shebang(self, script_path: Path, lines: List[str]) -> List[IssueReport]:
        """Check for proper Python shebang in executable scripts"""
        issues = []

        if not lines or not lines[0].startswith('#!'):
            issues.append(IssueReport(
                file_path=str(script_path),
                line_number=1,
                severity='warning',
                category='shebang',
                message='Executable script missing shebang line',
                suggestion='Add: #!/usr/bin/env python3'
            ))
        elif 'python' not in lines[0].lower():
            issues.append(IssueReport(
                file_path=str(script_path),
                line_number=1,
                severity='warning',
                category='shebang',
                message=f'Non-Python shebang for .py file: {lines[0]}',
                suggestion='Use: #!/usr/bin/env python3'
            ))

        return issues

    def _check_execute_permissions(self, script_path: Path) -> List[IssueReport]:
        """Check if bash script has execute permissions"""
        issues = []

        # Skip scripts in certain directories that are typically sourced
        skip_dirs = ['lib', 'mocks']
        if any(part in script_path.parts for part in skip_dirs):
            return issues

        if not os.access(script_path, os.X_OK):
            issues.append(IssueReport(
                file_path=str(script_path),
                line_number=None,
                severity='warning',
                category='permissions',
                message='Script is not executable',
                suggestion=f'Run: chmod +x {script_path.name}'
            ))

        return issues

    def _check_bash_syntax(self, script_path: Path) -> List[IssueReport]:
        """Run bash -n syntax check"""
        issues = []

        try:
            result = subprocess.run(
                ['bash', '-n', str(script_path)],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                # Parse error message for line number
                line_match = re.search(r'line (\d+):', result.stderr)
                line_number = int(line_match.group(1)) if line_match else None

                issues.append(IssueReport(
                    file_path=str(script_path),
                    line_number=line_number,
                    severity='critical',
                    category='syntax',
                    message=f'Bash syntax error: {result.stderr.strip()}',
                    suggestion=None
                ))
        except subprocess.TimeoutExpired:
            issues.append(IssueReport(
                file_path=str(script_path),
                line_number=None,
                severity='warning',
                category='syntax',
                message='Syntax check timed out',
                suggestion=None
            ))
        except Exception as e:
            issues.append(IssueReport(
                file_path=str(script_path),
                line_number=None,
                severity='warning',
                category='syntax',
                message=f'Failed to run syntax check: {str(e)}',
                suggestion=None
            ))

        return issues

    def _check_python_syntax(self, script_path: Path) -> List[IssueReport]:
        """Run python -m py_compile syntax check"""
        issues = []

        try:
            result = subprocess.run(
                [sys.executable, '-m', 'py_compile', str(script_path)],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                # Parse error message for line number
                line_match = re.search(r'line (\d+)', result.stderr)
                line_number = int(line_match.group(1)) if line_match else None

                issues.append(IssueReport(
                    file_path=str(script_path),
                    line_number=line_number,
                    severity='critical',
                    category='syntax',
                    message=f'Python syntax error: {result.stderr.strip()}',
                    suggestion=None
                ))
        except subprocess.TimeoutExpired:
            issues.append(IssueReport(
                file_path=str(script_path),
                line_number=None,
                severity='warning',
                category='syntax',
                message='Syntax check timed out',
                suggestion=None
            ))
        except Exception as e:
            issues.append(IssueReport(
                file_path=str(script_path),
                line_number=None,
                severity='warning',
                category='syntax',
                message=f'Failed to run syntax check: {str(e)}',
                suggestion=None
            ))

        return issues

    def _run_shellcheck(self, script_path: Path) -> List[IssueReport]:
        """Run shellcheck if available"""
        issues = []

        try:
            result = subprocess.run(
                ['shellcheck', '-f', 'json', str(script_path)],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.stdout:
                shellcheck_issues = json.loads(result.stdout)
                for sc_issue in shellcheck_issues:
                    severity_map = {
                        'error': 'critical',
                        'warning': 'warning',
                        'info': 'info',
                        'style': 'info'
                    }

                    issues.append(IssueReport(
                        file_path=str(script_path),
                        line_number=sc_issue.get('line'),
                        severity=severity_map.get(sc_issue.get('level', 'info'), 'info'),
                        category='shellcheck',
                        message=f"SC{sc_issue.get('code')}: {sc_issue.get('message')}",
                        suggestion=None
                    ))
        except subprocess.TimeoutExpired:
            pass  # Skip shellcheck if it times out
        except Exception:
            pass  # Skip shellcheck if it fails

        return issues

    def _detect_bash_antipatterns(self, script_path: Path, lines: List[str]) -> List[IssueReport]:
        """Detect common bash antipatterns"""
        issues = []

        # Check for set -euo pipefail (skip sourced libraries)
        skip_dirs = ['lib', 'mocks']
        if not any(part in script_path.parts for part in skip_dirs):
            has_errexit = any('set -e' in line or 'set -o errexit' in line for line in lines[:20])
            if not has_errexit:
                issues.append(IssueReport(
                    file_path=str(script_path),
                    line_number=None,
                    severity='warning',
                    category='antipattern',
                    message='Missing error handling (set -e or set -euo pipefail)',
                    suggestion='Add near top of script: set -euo pipefail'
                ))

        # Check for dangerous patterns
        for i, line in enumerate(lines, 1):
            # Skip comments
            if line.strip().startswith('#'):
                continue

            # Check for rm -rf with variables
            if re.search(r'\brm\s+-[rf]+.*\$', line):
                issues.append(IssueReport(
                    file_path=str(script_path),
                    line_number=i,
                    severity='critical',
                    category='antipattern',
                    message='Dangerous: rm -rf with variable - could delete everything',
                    suggestion='Add safety checks or quote variables'
                ))

            # Check for unquoted variables (common cases)
            # Look for $VAR that's not in quotes and not in special contexts
            if re.search(r'(?<!")(\$\w+|\$\{\w+\})(?!")', line):
                # Exclude some false positives
                if not any(pattern in line for pattern in ['[[', 'case', '$(', '${#', 'for ']):
                    issues.append(IssueReport(
                        file_path=str(script_path),
                        line_number=i,
                        severity='warning',
                        category='antipattern',
                        message='Potentially unquoted variable',
                        suggestion='Quote variables: "$var" instead of $var'
                    ))

            # Check for cd without error checking
            if re.match(r'^\s*cd\s+', line) and not any(pattern in line for pattern in ['||', '&&', 'if']):
                issues.append(IssueReport(
                    file_path=str(script_path),
                    line_number=i,
                    severity='warning',
                    category='antipattern',
                    message='cd without error checking',
                    suggestion='Use: cd dir || exit 1'
                ))

        return issues

    def _check_python_imports(self, script_path: Path, lines: List[str]) -> List[IssueReport]:
        """Check if Python imports can resolve"""
        issues = []

        # Extract import statements
        import_lines = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith('import ') or stripped.startswith('from '):
                import_lines.append((i, stripped))

        # Try to validate imports (basic check only)
        for line_num, import_stmt in import_lines:
            # Skip relative imports and standard library
            if import_stmt.startswith('from .'):
                continue

            # Extract module name
            match = re.match(r'(?:from|import)\s+(\w+)', import_stmt)
            if not match:
                continue

            module_name = match.group(1)

            # Skip known standard library modules
            stdlib_modules = {
                'os', 'sys', 'json', 'datetime', 'pathlib', 'subprocess',
                're', 'time', 'typing', 'dataclasses', 'collections',
                'argparse', 'logging', 'shutil', 'tempfile', 'importlib'
            }

            if module_name in stdlib_modules:
                continue

            # Try to find the module
            try:
                spec = importlib.util.find_spec(module_name)
                if spec is None:
                    issues.append(IssueReport(
                        file_path=str(script_path),
                        line_number=line_num,
                        severity='warning',
                        category='import',
                        message=f'Cannot resolve import: {module_name}',
                        suggestion='Ensure module is installed or in PYTHONPATH'
                    ))
            except (ModuleNotFoundError, ValueError, ImportError):
                # Module might be project-specific, only warn if suspicious
                pass

        return issues

    def _detect_python_debug_statements(self, script_path: Path, lines: List[str]) -> List[IssueReport]:
        """Detect debugging statements in Python code"""
        issues = []

        debug_patterns = [
            (r'\bprint\s*\(', 'print statement (consider using logging)'),
            (r'\bpdb\.set_trace\s*\(', 'pdb.set_trace() debugging statement'),
            (r'\bbreakpoint\s*\(', 'breakpoint() debugging statement'),
            (r'\bimport\s+pdb\b', 'pdb import (debugging)'),
        ]

        for i, line in enumerate(lines, 1):
            # Skip comments and docstrings
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                continue

            for pattern, description in debug_patterns:
                if re.search(pattern, line):
                    issues.append(IssueReport(
                        file_path=str(script_path),
                        line_number=i,
                        severity='info',
                        category='debug',
                        message=f'Debug statement found: {description}',
                        suggestion='Remove before production'
                    ))

        return issues

    def _detect_todo_fixme(self, script_path: Path, lines: List[str]) -> List[IssueReport]:
        """Detect TODO and FIXME comments"""
        issues = []

        for i, line in enumerate(lines, 1):
            if 'TODO' in line or 'FIXME' in line:
                issues.append(IssueReport(
                    file_path=str(script_path),
                    line_number=i,
                    severity='info',
                    category='todo',
                    message='TODO/FIXME comment found',
                    suggestion='Address or track in issue tracker'
                ))

        return issues

    def _print_file_result(self, result: FileAuditResult):
        """Print result for a single file"""
        status_color = Colors.GREEN if result.passed else Colors.RED
        status_symbol = '✓' if result.passed else '✗'

        # Only print files with issues or in verbose mode
        if result.issues:
            print(f"{status_color}{status_symbol} {result.file_path}{Colors.RESET}")

            for issue in result.issues:
                severity_colors = {
                    'critical': Colors.RED,
                    'warning': Colors.YELLOW,
                    'info': Colors.BLUE
                }
                color = severity_colors.get(issue.severity, Colors.WHITE)

                line_info = f":{issue.line_number}" if issue.line_number else ""
                print(f"  {color}[{issue.severity.upper()}]{Colors.RESET} {issue.category}{line_info}")
                print(f"    {issue.message}")
                if issue.suggestion:
                    print(f"    💡 {issue.suggestion}")

    def generate_report(self) -> AuditSummary:
        """Generate audit summary report"""
        end_time = datetime.now()
        execution_time = (end_time - self.start_time).total_seconds()

        total_files = len(self.results)
        files_passed = sum(1 for r in self.results if r.passed)
        files_failed = total_files - files_passed

        all_issues = [issue for result in self.results for issue in result.issues]
        total_issues = len(all_issues)
        critical_issues = sum(1 for issue in all_issues if issue.severity == 'critical')
        warnings = sum(1 for issue in all_issues if issue.severity == 'warning')

        bash_files = sum(1 for r in self.results if r.file_type == 'bash')
        python_files = sum(1 for r in self.results if r.file_type == 'python')

        summary = AuditSummary(
            total_files=total_files,
            files_passed=files_passed,
            files_failed=files_failed,
            total_issues=total_issues,
            critical_issues=critical_issues,
            warnings=warnings,
            bash_files_checked=bash_files,
            python_files_checked=python_files,
            execution_time_seconds=round(execution_time, 2),
            timestamp=self.start_time.isoformat()
        )

        return summary

    def print_summary(self, summary: AuditSummary):
        """Print audit summary to console"""
        print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}AUDIT SUMMARY{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")

        # Overall status
        if summary.critical_issues == 0:
            status_color = Colors.GREEN
            status = "PASSED"
        else:
            status_color = Colors.RED
            status = "FAILED"

        print(f"Status: {status_color}{Colors.BOLD}{status}{Colors.RESET}\n")

        # File statistics
        print(f"Files Checked:")
        print(f"  Total:  {summary.total_files}")
        print(f"  Bash:   {summary.bash_files_checked}")
        print(f"  Python: {summary.python_files_checked}")
        print(f"  {Colors.GREEN}Passed: {summary.files_passed}{Colors.RESET}")
        if summary.files_failed > 0:
            print(f"  {Colors.RED}Failed: {summary.files_failed}{Colors.RESET}")
        print()

        # Issue statistics
        print(f"Issues Found:")
        print(f"  Total:    {summary.total_issues}")
        if summary.critical_issues > 0:
            print(f"  {Colors.RED}Critical: {summary.critical_issues}{Colors.RESET}")
        if summary.warnings > 0:
            print(f"  {Colors.YELLOW}Warnings: {summary.warnings}{Colors.RESET}")
        print()

        # Execution time
        print(f"Execution Time: {summary.execution_time_seconds}s")
        print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")

    def save_json_report(self, summary: AuditSummary, output_path: Path):
        """Save detailed JSON report"""
        report = {
            'summary': asdict(summary),
            'files': [
                {
                    'file_path': result.file_path,
                    'file_type': result.file_type,
                    'passed': result.passed,
                    'execution_time_ms': result.execution_time_ms,
                    'issues': [asdict(issue) for issue in result.issues]
                }
                for result in self.results
            ]
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"Detailed JSON report saved to: {output_path}")

    def run_full_audit(self, bash_only: bool = False, python_only: bool = False):
        """Run complete audit of both bash and Python scripts"""
        if not python_only:
            bash_results = self.audit_bash_scripts()
            self.results.extend(bash_results)

        if not bash_only:
            python_results = self.audit_python_scripts()
            self.results.extend(python_results)

        summary = self.generate_report()
        self.print_summary(summary)

        return summary


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Audit bash and Python scripts for quality issues'
    )
    parser.add_argument(
        '--bash-only',
        action='store_true',
        help='Only audit bash scripts'
    )
    parser.add_argument(
        '--python-only',
        action='store_true',
        help='Only audit Python scripts'
    )
    parser.add_argument(
        '--json-report',
        action='store_true',
        help='Generate JSON report in test/reports/'
    )
    parser.add_argument(
        '--repo-root',
        type=str,
        default=None,
        help='Repository root directory (default: auto-detect)'
    )

    args = parser.parse_args()

    # Determine repository root
    if args.repo_root:
        repo_root = Path(args.repo_root).resolve()
    else:
        # Auto-detect: go up from script location
        script_dir = Path(__file__).parent
        repo_root = script_dir.parent

    if not repo_root.exists():
        print(f"{Colors.RED}Error: Repository root not found: {repo_root}{Colors.RESET}")
        sys.exit(1)

    print(f"{Colors.CYAN}Repository root: {repo_root}{Colors.RESET}")

    # Run audit
    runner = ScriptAuditRunner(str(repo_root))
    summary = runner.run_full_audit(
        bash_only=args.bash_only,
        python_only=args.python_only
    )

    # Save JSON report if requested
    if args.json_report:
        report_path = repo_root / 'test' / 'reports' / f'script-audit-{datetime.now().strftime("%Y%m%d-%H%M%S")}.json'
        runner.save_json_report(summary, report_path)

    # Exit with appropriate code
    if summary.critical_issues > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
