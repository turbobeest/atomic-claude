#!/usr/bin/env python3
"""
ATOMIC CLAUDE - Output Validation Audit Runner
Validates all output files have correct structure and content after a UAT run.

This audit checks:
1. File existence across all phases
2. JSON validation and schema compliance
3. Markdown structure validation
4. File size sanity checks
5. Closeout validation
6. Phase-specific output validation

Usage:
    python test/output_audit_runner.py [--outputs-dir PATH] [--report-dir PATH]
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ============================================================================
# COLOR CODES
# ============================================================================

class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ValidationIssue:
    """Represents a validation issue found during audit."""
    severity: str  # 'critical', 'error', 'warning', 'info'
    category: str  # 'file_existence', 'json_validation', 'markdown', 'size', 'closeout'
    message: str
    file_path: Optional[str] = None
    details: Optional[Dict] = None


@dataclass
class ValidationResult:
    """Result of a validation check."""
    passed: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    checked: int = 0

    def add_issue(self, severity: str, category: str, message: str,
                  file_path: Optional[str] = None, details: Optional[Dict] = None):
        """Add a validation issue."""
        self.issues.append(ValidationIssue(
            severity=severity,
            category=category,
            message=message,
            file_path=file_path,
            details=details
        ))
        if severity in ['critical', 'error']:
            self.passed = False


@dataclass
class AuditReport:
    """Complete audit report."""
    timestamp: str
    outputs_dir: str
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    issues: List[ValidationIssue] = field(default_factory=list)
    results: Dict[str, ValidationResult] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert report to dictionary."""
        return {
            'timestamp': self.timestamp,
            'outputs_dir': self.outputs_dir,
            'summary': {
                'total_checks': self.total_checks,
                'passed_checks': self.passed_checks,
                'failed_checks': self.failed_checks,
                'pass_rate': f"{(self.passed_checks / self.total_checks * 100) if self.total_checks > 0 else 0:.1f}%"
            },
            'issues_by_severity': {
                'critical': len([i for i in self.issues if i.severity == 'critical']),
                'error': len([i for i in self.issues if i.severity == 'error']),
                'warning': len([i for i in self.issues if i.severity == 'warning']),
                'info': len([i for i in self.issues if i.severity == 'info'])
            },
            'issues_by_category': {
                'file_existence': len([i for i in self.issues if i.category == 'file_existence']),
                'json_validation': len([i for i in self.issues if i.category == 'json_validation']),
                'markdown': len([i for i in self.issues if i.category == 'markdown']),
                'size': len([i for i in self.issues if i.category == 'size']),
                'closeout': len([i for i in self.issues if i.category == 'closeout'])
            },
            'issues': [
                {
                    'severity': issue.severity,
                    'category': issue.category,
                    'message': issue.message,
                    'file_path': issue.file_path,
                    'details': issue.details
                }
                for issue in self.issues
            ]
        }


# ============================================================================
# OUTPUT AUDIT RUNNER
# ============================================================================

class OutputAuditRunner:
    """Validates all output files after UAT run."""

    # Phase-specific file expectations
    PHASE_FILES = {
        '0-setup': {
            'required': ['project-config.json', 'secrets.json'],
            'optional': ['closeout.json', 'extracted-config.json']
        },
        '1-discovery': {
            'required': ['closeout.json'],
            'optional': ['selected-agents.json', 'discovery-report.json']
        },
        '2-prd': {
            'required': ['closeout.json'],
            'optional': ['PRD.md', 'prd-interview.json']
        },
        '3-tasking': {
            'required': ['closeout.json'],
            'optional': ['tasks.json']
        },
        '4-specification': {
            'required': ['closeout.json'],
            'optional': ['openspec.json']
        },
        '5-implementation': {
            'required': ['closeout.json'],
            'optional': []
        },
        '6-code-review': {
            'required': ['closeout.json'],
            'optional': ['review-report.md']
        },
        '7-integration': {
            'required': ['closeout.json'],
            'optional': ['test-results.json']
        },
        '8-deployment-prep': {
            'required': ['closeout.json'],
            'optional': ['deployment-plan.md']
        },
        '9-release': {
            'required': ['closeout.json'],
            'optional': ['release-notes.md']
        }
    }

    # File size limits (in bytes)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MIN_JSON_SIZE = 10  # Minimum 10 bytes for valid JSON
    MIN_MD_SIZE = 50  # Minimum 50 bytes for meaningful markdown

    # PRD sections expected
    PRD_SECTIONS = [
        "## 0.",  # Executive Summary
        "## 1.",  # Problem Statement
        "## 2.",  # Goals & Success Metrics
        "## 3.",  # User Stories
        "## 4.",  # Functional Requirements
        "## 5.",  # Non-Functional Requirements
        "## 6.",  # System Architecture
        "## 7.",  # Data Model
        "## 8.",  # API Specifications
        "## 9.",  # User Interface
        "## 10.", # Security & Privacy
        "## 11.", # Testing Strategy
        "## 12.", # Deployment
        "## 13.", # Timeline & Milestones
        "## 14."  # Appendix
    ]

    def __init__(self, outputs_dir: str, report_dir: str):
        """Initialize the audit runner."""
        self.outputs_dir = Path(outputs_dir)
        self.report_dir = Path(report_dir)
        self.report = AuditReport(
            timestamp=datetime.now().isoformat(),
            outputs_dir=str(self.outputs_dir)
        )

        # Ensure report directory exists
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> AuditReport:
        """Run all validation checks."""
        print(f"{Colors.BOLD}{Colors.HEADER}╔═══════════════════════════════════════════════════════════╗{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}║  ATOMIC CLAUDE - Output Validation Audit Runner          ║{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}╚═══════════════════════════════════════════════════════════╝{Colors.ENDC}\n")

        print(f"{Colors.OKCYAN}Outputs Directory: {Colors.ENDC}{self.outputs_dir}")
        print(f"{Colors.OKCYAN}Report Directory:  {Colors.ENDC}{self.report_dir}\n")

        # Run validation checks
        checks = [
            ('File Existence', self.check_file_existence),
            ('JSON Validation', self.validate_json_files),
            ('Markdown Validation', self.validate_markdown_files),
            ('File Sizes', self.check_file_sizes),
            ('Closeout Validation', self.validate_closeouts)
        ]

        for check_name, check_func in checks:
            print(f"{Colors.BOLD}▶ {check_name}{Colors.ENDC}")
            result = check_func()
            self.report.results[check_name] = result
            self.report.total_checks += result.checked

            if result.passed:
                self.report.passed_checks += result.checked
                print(f"  {Colors.OKGREEN}✓ Passed ({result.checked} checks){Colors.ENDC}\n")
            else:
                failed_count = len([i for i in result.issues if i.severity in ['critical', 'error']])
                self.report.failed_checks += failed_count
                print(f"  {Colors.FAIL}✗ Failed ({failed_count} issues found){Colors.ENDC}\n")

            # Add issues to report
            self.report.issues.extend(result.issues)

        # Print summary
        self._print_summary()

        # Save report
        self._save_report()

        return self.report

    def check_file_existence(self) -> ValidationResult:
        """Check that expected files exist for each phase."""
        result = ValidationResult(passed=True)

        for phase_id, files in self.PHASE_FILES.items():
            phase_dir = self.outputs_dir / phase_id

            # Check if phase directory exists
            if not phase_dir.exists():
                result.add_issue(
                    'warning',
                    'file_existence',
                    f"Phase directory not found: {phase_id}",
                    str(phase_dir)
                )
                result.checked += 1
                continue

            result.checked += 1

            # Check required files
            for required_file in files['required']:
                file_path = phase_dir / required_file
                result.checked += 1

                if not file_path.exists():
                    result.add_issue(
                        'error',
                        'file_existence',
                        f"Required file missing: {required_file}",
                        str(file_path)
                    )

            # Check optional files (info only if missing)
            for optional_file in files['optional']:
                file_path = phase_dir / optional_file
                result.checked += 1

                if not file_path.exists():
                    result.add_issue(
                        'info',
                        'file_existence',
                        f"Optional file missing: {optional_file}",
                        str(file_path)
                    )

        # Check for PRD.md in docs/prd/
        docs_prd_path = Path(self.outputs_dir).parent / 'docs' / 'prd' / 'PRD.md'
        result.checked += 1

        if not docs_prd_path.exists():
            # Also check in phase 2 output
            phase2_prd = self.outputs_dir / '2-prd' / 'PRD.md'
            if not phase2_prd.exists():
                result.add_issue(
                    'warning',
                    'file_existence',
                    "PRD.md not found in docs/prd/ or .outputs/2-prd/",
                    str(docs_prd_path)
                )

        return result

    def validate_json_files(self) -> ValidationResult:
        """Validate all JSON files are parseable and have correct schema."""
        result = ValidationResult(passed=True)

        # Find all JSON files
        json_files = list(self.outputs_dir.rglob('*.json'))

        for json_file in json_files:
            result.checked += 1

            # Check file is not empty
            if json_file.stat().st_size == 0:
                result.add_issue(
                    'error',
                    'json_validation',
                    "Empty JSON file",
                    str(json_file)
                )
                continue

            # Try to parse JSON
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)

                # Validate specific file types
                file_name = json_file.name

                if file_name == 'project-config.json':
                    self._validate_project_config(json_file, data, result)
                elif file_name == 'closeout.json':
                    self._validate_closeout(json_file, data, result)
                elif file_name == 'secrets.json':
                    self._validate_secrets(json_file, data, result)
                elif file_name == 'tasks.json':
                    self._validate_tasks(json_file, data, result)

            except json.JSONDecodeError as e:
                result.add_issue(
                    'critical',
                    'json_validation',
                    f"Invalid JSON: {str(e)}",
                    str(json_file),
                    {'error': str(e)}
                )
            except Exception as e:
                result.add_issue(
                    'error',
                    'json_validation',
                    f"Error reading file: {str(e)}",
                    str(json_file),
                    {'error': str(e)}
                )

        return result

    def _validate_project_config(self, file_path: Path, data: Dict, result: ValidationResult):
        """Validate project-config.json schema."""
        required_keys = ['name', 'type', 'tech_stack']

        for key in required_keys:
            if key not in data:
                result.add_issue(
                    'error',
                    'json_validation',
                    f"Missing required key: {key}",
                    str(file_path),
                    {'missing_key': key}
                )

    def _validate_closeout(self, file_path: Path, data: Dict, result: ValidationResult):
        """Validate closeout.json schema."""
        required_keys = ['phase_id', 'phase_name', 'status']

        for key in required_keys:
            if key not in data:
                result.add_issue(
                    'error',
                    'json_validation',
                    f"Missing required closeout key: {key}",
                    str(file_path),
                    {'missing_key': key}
                )

        # Check completed_at timestamp exists
        if 'completed_at' not in data and data.get('status') == 'complete':
            result.add_issue(
                'warning',
                'json_validation',
                "Completed phase missing completed_at timestamp",
                str(file_path)
            )

    def _validate_secrets(self, file_path: Path, data: Dict, result: ValidationResult):
        """Validate secrets.json has provider configs."""
        # Just check it's not empty
        if not data:
            result.add_issue(
                'warning',
                'json_validation',
                "Empty secrets.json",
                str(file_path)
            )

    def _validate_tasks(self, file_path: Path, data: Dict, result: ValidationResult):
        """Validate tasks.json structure."""
        if not isinstance(data, (dict, list)):
            result.add_issue(
                'error',
                'json_validation',
                "tasks.json should be a dict or list",
                str(file_path)
            )

    def validate_markdown_files(self) -> ValidationResult:
        """Validate markdown files structure."""
        result = ValidationResult(passed=True)

        # Find all markdown files
        md_files = list(self.outputs_dir.rglob('*.md'))

        # Also check docs/prd/PRD.md
        docs_prd = Path(self.outputs_dir).parent / 'docs' / 'prd' / 'PRD.md'
        if docs_prd.exists():
            md_files.append(docs_prd)

        for md_file in md_files:
            result.checked += 1

            # Check file is not empty
            if md_file.stat().st_size == 0:
                result.add_issue(
                    'warning',
                    'markdown',
                    "Empty markdown file",
                    str(md_file)
                )
                continue

            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Special validation for PRD.md
                if md_file.name == 'PRD.md':
                    self._validate_prd_structure(md_file, content, result)

                # Check for basic markdown issues
                if not content.strip():
                    result.add_issue(
                        'warning',
                        'markdown',
                        "Markdown file is empty or whitespace only",
                        str(md_file)
                    )

                # Check for basic markdown syntax
                if not re.search(r'#+\s+\w+', content):
                    result.add_issue(
                        'info',
                        'markdown',
                        "No markdown headers found",
                        str(md_file)
                    )

            except Exception as e:
                result.add_issue(
                    'error',
                    'markdown',
                    f"Error reading markdown file: {str(e)}",
                    str(md_file),
                    {'error': str(e)}
                )

        return result

    def _validate_prd_structure(self, file_path: Path, content: str, result: ValidationResult):
        """Validate PRD.md has all 15 sections."""
        missing_sections = []

        for section in self.PRD_SECTIONS:
            if section not in content:
                missing_sections.append(section)

        if missing_sections:
            result.add_issue(
                'warning',
                'markdown',
                f"PRD missing {len(missing_sections)} section(s): {', '.join(missing_sections)}",
                str(file_path),
                {'missing_sections': missing_sections}
            )

    def check_file_sizes(self) -> ValidationResult:
        """Check file sizes are within reasonable bounds."""
        result = ValidationResult(passed=True)

        # Check all files in outputs directory
        for file_path in self.outputs_dir.rglob('*'):
            if not file_path.is_file():
                continue

            result.checked += 1
            file_size = file_path.stat().st_size

            # Check for 0-byte files
            if file_size == 0:
                result.add_issue(
                    'warning',
                    'size',
                    "0-byte file found",
                    str(file_path),
                    {'size': 0}
                )
                continue

            # Check for files > 10MB
            if file_size > self.MAX_FILE_SIZE:
                result.add_issue(
                    'warning',
                    'size',
                    f"File exceeds size limit ({file_size / 1024 / 1024:.1f}MB > 10MB)",
                    str(file_path),
                    {'size': file_size}
                )

            # Check JSON files are at least MIN_JSON_SIZE
            if file_path.suffix == '.json' and file_size < self.MIN_JSON_SIZE:
                result.add_issue(
                    'warning',
                    'size',
                    f"JSON file suspiciously small ({file_size} bytes)",
                    str(file_path),
                    {'size': file_size}
                )

            # Check markdown files are at least MIN_MD_SIZE
            if file_path.suffix == '.md' and file_size < self.MIN_MD_SIZE:
                result.add_issue(
                    'info',
                    'size',
                    f"Markdown file very small ({file_size} bytes)",
                    str(file_path),
                    {'size': file_size}
                )

        return result

    def validate_closeouts(self) -> ValidationResult:
        """Validate all closeout files."""
        result = ValidationResult(passed=True)

        for phase_id in self.PHASE_FILES.keys():
            result.checked += 1

            phase_dir = self.outputs_dir / phase_id
            closeout_file = phase_dir / 'closeout.json'

            if not closeout_file.exists():
                result.add_issue(
                    'warning',
                    'closeout',
                    f"Closeout file missing for phase {phase_id}",
                    str(closeout_file)
                )
                continue

            try:
                with open(closeout_file, 'r') as f:
                    closeout = json.load(f)

                # Validate closeout structure
                if 'phase_id' not in closeout:
                    result.add_issue(
                        'error',
                        'closeout',
                        f"Closeout missing phase_id for {phase_id}",
                        str(closeout_file)
                    )

                if 'completed_at' not in closeout:
                    result.add_issue(
                        'error',
                        'closeout',
                        f"Closeout missing completed_at timestamp for {phase_id}",
                        str(closeout_file)
                    )

                if 'status' not in closeout:
                    result.add_issue(
                        'error',
                        'closeout',
                        f"Closeout missing status for {phase_id}",
                        str(closeout_file)
                    )

                # Validate completed_at is a valid timestamp
                if 'completed_at' in closeout:
                    try:
                        datetime.fromisoformat(closeout['completed_at'].replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        result.add_issue(
                            'warning',
                            'closeout',
                            f"Invalid timestamp format in closeout for {phase_id}",
                            str(closeout_file),
                            {'timestamp': closeout.get('completed_at')}
                        )

            except json.JSONDecodeError as e:
                result.add_issue(
                    'critical',
                    'closeout',
                    f"Invalid JSON in closeout for {phase_id}: {str(e)}",
                    str(closeout_file),
                    {'error': str(e)}
                )
            except Exception as e:
                result.add_issue(
                    'error',
                    'closeout',
                    f"Error reading closeout for {phase_id}: {str(e)}",
                    str(closeout_file),
                    {'error': str(e)}
                )

        return result

    def _print_summary(self):
        """Print audit summary to console."""
        print(f"\n{Colors.BOLD}{Colors.HEADER}═══════════════════════════════════════════════════════════{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}AUDIT SUMMARY{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}═══════════════════════════════════════════════════════════{Colors.ENDC}\n")

        # Overall statistics
        pass_rate = (self.report.passed_checks / self.report.total_checks * 100) if self.report.total_checks > 0 else 0

        print(f"{Colors.BOLD}Total Checks:{Colors.ENDC} {self.report.total_checks}")
        print(f"{Colors.OKGREEN}Passed:{Colors.ENDC} {self.report.passed_checks}")
        print(f"{Colors.FAIL}Failed:{Colors.ENDC} {self.report.failed_checks}")
        print(f"{Colors.BOLD}Pass Rate:{Colors.ENDC} {pass_rate:.1f}%\n")

        # Issues by severity
        critical_count = len([i for i in self.report.issues if i.severity == 'critical'])
        error_count = len([i for i in self.report.issues if i.severity == 'error'])
        warning_count = len([i for i in self.report.issues if i.severity == 'warning'])
        info_count = len([i for i in self.report.issues if i.severity == 'info'])

        print(f"{Colors.BOLD}Issues by Severity:{Colors.ENDC}")
        if critical_count > 0:
            print(f"  {Colors.FAIL}Critical: {critical_count}{Colors.ENDC}")
        if error_count > 0:
            print(f"  {Colors.FAIL}Error:    {error_count}{Colors.ENDC}")
        if warning_count > 0:
            print(f"  {Colors.WARNING}Warning:  {warning_count}{Colors.ENDC}")
        if info_count > 0:
            print(f"  {Colors.OKCYAN}Info:     {info_count}{Colors.ENDC}")

        if critical_count == 0 and error_count == 0 and warning_count == 0 and info_count == 0:
            print(f"  {Colors.OKGREEN}No issues found!{Colors.ENDC}")

        print()

        # Print critical and error issues
        if critical_count > 0 or error_count > 0:
            print(f"{Colors.BOLD}Critical & Error Issues:{Colors.ENDC}\n")

            for issue in self.report.issues:
                if issue.severity in ['critical', 'error']:
                    color = Colors.FAIL
                    icon = "✗"

                    print(f"  {color}{icon} [{issue.severity.upper()}] {issue.message}{Colors.ENDC}")
                    if issue.file_path:
                        print(f"    File: {issue.file_path}")
                    if issue.details:
                        print(f"    Details: {issue.details}")
                    print()

        # Overall result
        if critical_count == 0 and error_count == 0:
            print(f"\n{Colors.OKGREEN}{Colors.BOLD}✓ OUTPUT VALIDATION PASSED{Colors.ENDC}")
        else:
            print(f"\n{Colors.FAIL}{Colors.BOLD}✗ OUTPUT VALIDATION FAILED{Colors.ENDC}")

    def _save_report(self):
        """Save detailed report to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        report_file = self.report_dir / f"output-audit-{timestamp}.json"

        try:
            with open(report_file, 'w') as f:
                json.dump(self.report.to_dict(), f, indent=2)

            print(f"\n{Colors.OKCYAN}Report saved to: {report_file}{Colors.ENDC}\n")
        except Exception as e:
            print(f"\n{Colors.FAIL}Error saving report: {str(e)}{Colors.ENDC}\n")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Validate ATOMIC CLAUDE output files after UAT run'
    )
    parser.add_argument(
        '--outputs-dir',
        type=str,
        default='.outputs',
        help='Path to outputs directory (default: .outputs)'
    )
    parser.add_argument(
        '--report-dir',
        type=str,
        default='test/reports',
        help='Path to report directory (default: test/reports)'
    )

    args = parser.parse_args()

    # Resolve paths
    outputs_dir = Path(args.outputs_dir).resolve()
    report_dir = Path(args.report_dir).resolve()

    # Check outputs directory exists
    if not outputs_dir.exists():
        print(f"{Colors.FAIL}Error: Outputs directory not found: {outputs_dir}{Colors.ENDC}")
        sys.exit(1)

    # Run audit
    runner = OutputAuditRunner(str(outputs_dir), str(report_dir))
    report = runner.run()

    # Exit with appropriate code
    critical_count = len([i for i in report.issues if i.severity == 'critical'])
    error_count = len([i for i in report.issues if i.severity == 'error'])

    if critical_count > 0 or error_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
