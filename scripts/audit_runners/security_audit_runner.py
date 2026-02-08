#!/usr/bin/env python3
"""
Security Audit Runner
Validates security best practices across the codebase

This audit ensures that:
1. No hardcoded secrets (API keys, passwords, credentials)
2. File permissions are secure (600 for secrets, no world-writable)
3. Git safety (.gitignore protects secrets, no secrets in history)
4. Input validation (no injection vulnerabilities)
5. Network security (sandbox enforcement, network mode restrictions)
6. Dashboard security (XSS prevention, CORS config, no exposed secrets)
"""

import json
import os
import re
import stat
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set


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
MAGENTA = "\033[35m"
NC = "\033[0m"


# ============================================================================
# SECURITY FINDING DATA STRUCTURE
# ============================================================================

@dataclass
class SecurityFinding:
    """A single security finding."""
    category: str
    severity: str  # critical, high, medium, low
    title: str
    description: str
    location: Optional[str] = None
    remediation: Optional[str] = None
    details: Dict = field(default_factory=dict)


@dataclass
class SecurityReport:
    """Overall security audit report."""
    timestamp: str
    total_checks: int
    findings: List[SecurityFinding]
    duration: float

    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "critical")

    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "high")

    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "medium")

    def low_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "low")

    def has_critical_issues(self) -> bool:
        return self.critical_count() > 0


# ============================================================================
# SECURITY AUDIT RUNNER
# ============================================================================

class SecurityAuditRunner:
    """
    Validates security best practices across the Atomic Claude codebase.
    """

    # Secret patterns to detect
    SECRET_PATTERNS = [
        (r'sk-ant-[a-zA-Z0-9_-]{95,}', 'Anthropic API Key'),
        (r'ANTHROPIC_API_KEY\s*=\s*["\']?(sk-ant-[^"\'\s]+)', 'Hardcoded Anthropic API Key'),
        (r'AWS_ACCESS_KEY_ID\s*=\s*["\']?([A-Z0-9]{20})', 'AWS Access Key ID'),
        (r'AWS_SECRET_ACCESS_KEY\s*=\s*["\']?([A-Za-z0-9/+=]{40})', 'AWS Secret Access Key'),
        (r'password\s*=\s*["\']([^"\'\s]+)["\']', 'Hardcoded Password'),
        (r'api_key\s*=\s*["\']([^"\'\s]+)["\']', 'Hardcoded API Key'),
        (r'token\s*=\s*["\']([^"\'\s]+)["\']', 'Hardcoded Token'),
        (r'secret\s*=\s*["\']([^"\'\s]+)["\']', 'Hardcoded Secret'),
        (r'-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----', 'Private Key'),
    ]

    # Shell metacharacters that could indicate injection vulnerabilities
    SHELL_METACHARACTERS = ['$', '`', ';', '|', '&', '>', '<', '(', ')', '{', '}', '[', ']', '*', '?', '~', '!']

    def __init__(self):
        self.atomic_root = Path(__file__).parent.parent.resolve()
        self.test_dir = self.atomic_root / "test"
        self.reports_dir = self.test_dir / "reports"

        # Ensure directories exist
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        self.findings: List[SecurityFinding] = []
        self.checks_run = 0

    # ========================================================================
    # TEST ORCHESTRATION
    # ========================================================================

    def run_all_checks(self) -> SecurityReport:
        """Run all security checks and return consolidated report."""
        start_time = time.time()

        self.print_header("SECURITY AUDIT")
        print()

        # Run all security checks
        self.run_secret_detection()
        self.run_file_permission_checks()
        self.run_git_safety_checks()
        self.run_input_validation_checks()
        self.run_network_security_checks()
        self.run_dashboard_security_checks()

        duration = time.time() - start_time

        # Create report
        report = SecurityReport(
            timestamp=datetime.now().isoformat(),
            total_checks=self.checks_run,
            findings=self.findings,
            duration=duration
        )

        # Print summary
        self.print_summary(report)

        # Save report
        self.save_report(report)

        return report

    # ========================================================================
    # 1. SECRET DETECTION
    # ========================================================================

    def run_secret_detection(self):
        """Scan for hardcoded secrets in code."""
        self.print_section("Secret Detection")

        # Scan Python files
        self.scan_files_for_secrets("*.py", "Python files")

        # Scan shell scripts
        self.scan_files_for_secrets("*.sh", "Shell scripts")

        # Scan JavaScript files
        self.scan_files_for_secrets("*.js", "JavaScript files")

        # Check for .env file exposure
        self.check_env_file_security()

        # Check secrets.json files
        self.check_secrets_json_files()

        print()

    def scan_files_for_secrets(self, pattern: str, description: str):
        """Scan files matching pattern for secret patterns."""
        self.checks_run += 1

        files = list(self.atomic_root.rglob(pattern))

        # Exclude test fixtures and node_modules
        files = [f for f in files if 'node_modules' not in str(f) and 'test/fixtures' not in str(f)]

        secrets_found = []

        for file_path in files:
            try:
                content = file_path.read_text()

                for pattern_re, secret_type in self.SECRET_PATTERNS:
                    matches = re.finditer(pattern_re, content, re.IGNORECASE)
                    for match in matches:
                        # Exclude comments and examples
                        line = content[:match.start()].split('\n')[-1]
                        if '#' in line or 'example' in line.lower():
                            continue

                        secrets_found.append({
                            'file': str(file_path.relative_to(self.atomic_root)),
                            'type': secret_type,
                            'line_num': content[:match.start()].count('\n') + 1
                        })
            except Exception as e:
                # Skip binary or unreadable files
                continue

        if secrets_found:
            for secret in secrets_found:
                self.findings.append(SecurityFinding(
                    category="Secret Detection",
                    severity="critical",
                    title=f"Hardcoded {secret['type']} detected",
                    description=f"Found {secret['type']} in source code",
                    location=f"{secret['file']}:{secret['line_num']}",
                    remediation="Move secret to .env file or environment variables. Add file to .gitignore.",
                    details=secret
                ))
            print(f"  {RED}✗{NC} {description}: {len(secrets_found)} secret(s) found")
        else:
            print(f"  {GREEN}✓{NC} {description}: No hardcoded secrets")

    def check_env_file_security(self):
        """Check .env file security."""
        self.checks_run += 1

        env_file = self.atomic_root / ".env"

        if env_file.exists():
            # Check permissions
            mode = env_file.stat().st_mode
            perms = stat.filemode(mode)

            if mode & stat.S_IRWXO:  # World readable/writable/executable
                self.findings.append(SecurityFinding(
                    category="Secret Detection",
                    severity="high",
                    title=".env file has insecure permissions",
                    description=f".env file permissions are {perms}, should be 600",
                    location=str(env_file.relative_to(self.atomic_root)),
                    remediation="Run: chmod 600 .env"
                ))
                print(f"  {YELLOW}⚠{NC}  .env file permissions: {perms} (should be 600)")
            elif mode & stat.S_IRWXG:  # Group readable/writable/executable
                self.findings.append(SecurityFinding(
                    category="Secret Detection",
                    severity="medium",
                    title=".env file has group permissions",
                    description=f".env file permissions are {perms}, should be 600",
                    location=str(env_file.relative_to(self.atomic_root)),
                    remediation="Run: chmod 600 .env"
                ))
                print(f"  {YELLOW}⚠{NC}  .env file permissions: {perms} (should be 600)")
            else:
                print(f"  {GREEN}✓{NC} .env file permissions: {perms}")
        else:
            print(f"  {DIM}−{NC} .env file not present")

    def check_secrets_json_files(self):
        """Check secrets.json files security."""
        self.checks_run += 1

        secrets_files = list(self.atomic_root.rglob("*secrets.json"))

        for secrets_file in secrets_files:
            # Check permissions
            mode = secrets_file.stat().st_mode
            perms = stat.filemode(mode)

            if mode & stat.S_IRWXO:  # World readable/writable/executable
                self.findings.append(SecurityFinding(
                    category="Secret Detection",
                    severity="high",
                    title="secrets.json has insecure permissions",
                    description=f"File permissions are {perms}, should be 600",
                    location=str(secrets_file.relative_to(self.atomic_root)),
                    remediation=f"Run: chmod 600 {secrets_file}"
                ))
                print(f"  {YELLOW}⚠{NC}  {secrets_file.name} permissions: {perms} (should be 600)")
            elif mode & stat.S_IRWXG:  # Group readable/writable/executable
                self.findings.append(SecurityFinding(
                    category="Secret Detection",
                    severity="medium",
                    title="secrets.json has group permissions",
                    description=f"File permissions are {perms}, should be 600",
                    location=str(secrets_file.relative_to(self.atomic_root)),
                    remediation=f"Run: chmod 600 {secrets_file}"
                ))
                print(f"  {YELLOW}⚠{NC}  {secrets_file.name} permissions: {perms} (should be 600)")
            else:
                print(f"  {GREEN}✓{NC} {secrets_file.name} permissions: {perms}")

        if not secrets_files:
            print(f"  {DIM}−{NC} No secrets.json files found")

    # ========================================================================
    # 2. FILE PERMISSIONS
    # ========================================================================

    def run_file_permission_checks(self):
        """Check file permissions for security issues."""
        self.print_section("File Permissions")

        self.check_world_writable_files()
        self.check_executable_permissions()
        self.check_sensitive_directory_permissions()

        print()

    def check_world_writable_files(self):
        """Check for world-writable files in sensitive directories."""
        self.checks_run += 1

        sensitive_dirs = ['.state', '.outputs', '.logs', '.claude', 'config']
        world_writable = []

        for dir_name in sensitive_dirs:
            dir_path = self.atomic_root / dir_name
            if not dir_path.exists():
                continue

            for file_path in dir_path.rglob('*'):
                if file_path.is_file():
                    mode = file_path.stat().st_mode
                    if mode & stat.S_IWOTH:  # World writable
                        world_writable.append(str(file_path.relative_to(self.atomic_root)))

        if world_writable:
            for file_path in world_writable:
                self.findings.append(SecurityFinding(
                    category="File Permissions",
                    severity="high",
                    title="World-writable file in sensitive directory",
                    description="File can be modified by any user",
                    location=file_path,
                    remediation=f"Run: chmod 644 {file_path}"
                ))
            print(f"  {RED}✗{NC} World-writable files: {len(world_writable)} found")
        else:
            print(f"  {GREEN}✓{NC} No world-writable files in sensitive directories")

    def check_executable_permissions(self):
        """Check that executable permissions are appropriate."""
        self.checks_run += 1

        # Check that Python scripts in lib/ are not executable (they're imported, not run)
        lib_dir = self.atomic_root / "lib"
        if lib_dir.exists():
            incorrect_perms = []
            for py_file in lib_dir.glob("*.py"):
                mode = py_file.stat().st_mode
                if mode & stat.S_IXUSR:  # User executable
                    incorrect_perms.append(str(py_file.relative_to(self.atomic_root)))

            if incorrect_perms:
                for file_path in incorrect_perms:
                    self.findings.append(SecurityFinding(
                        category="File Permissions",
                        severity="low",
                        title="Library file marked as executable",
                        description="Library files should not be executable",
                        location=file_path,
                        remediation=f"Run: chmod 644 {file_path}"
                    ))
                print(f"  {YELLOW}⚠{NC}  Executable lib files: {len(incorrect_perms)} found")
            else:
                print(f"  {GREEN}✓{NC} Library file permissions appropriate")

        # Check that main.py and test runners are executable
        main_py = self.atomic_root / "main.py"
        if main_py.exists():
            mode = main_py.stat().st_mode
            if not (mode & stat.S_IXUSR):
                self.findings.append(SecurityFinding(
                    category="File Permissions",
                    severity="low",
                    title="main.py not executable",
                    description="Entry point should be executable",
                    location="main.py",
                    remediation="Run: chmod +x main.py"
                ))
                print(f"  {YELLOW}⚠{NC}  main.py not executable")
            else:
                print(f"  {GREEN}✓{NC} main.py is executable")

    def check_sensitive_directory_permissions(self):
        """Check permissions on sensitive directories."""
        self.checks_run += 1

        git_dir = self.atomic_root / ".git"
        if git_dir.exists():
            mode = git_dir.stat().st_mode
            if mode & stat.S_IRWXO:  # World accessible
                self.findings.append(SecurityFinding(
                    category="File Permissions",
                    severity="medium",
                    title=".git directory has world permissions",
                    description="Git metadata should not be world-accessible",
                    location=".git/",
                    remediation="Run: chmod 700 .git"
                ))
                print(f"  {YELLOW}⚠{NC}  .git directory has world permissions")
            else:
                print(f"  {GREEN}✓{NC} .git directory permissions secure")

    # ========================================================================
    # 3. GIT SAFETY
    # ========================================================================

    def run_git_safety_checks(self):
        """Check git configuration for security issues."""
        self.print_section("Git Safety")

        self.check_gitignore_coverage()
        self.check_git_history_for_secrets()

        print()

    def check_gitignore_coverage(self):
        """Check that sensitive files are in .gitignore."""
        self.checks_run += 1

        gitignore = self.atomic_root / ".gitignore"

        if not gitignore.exists():
            self.findings.append(SecurityFinding(
                category="Git Safety",
                severity="high",
                title="Missing .gitignore file",
                description="No .gitignore file found",
                location=".",
                remediation="Create .gitignore with appropriate entries"
            ))
            print(f"  {RED}✗{NC} .gitignore file missing")
            return

        gitignore_content = gitignore.read_text()

        # Check for required entries
        required_patterns = [
            ('.env', 'Environment variables'),
            ('secrets.json', 'Secrets files'),
            ('*.key', 'Key files'),
            ('*.pem', 'PEM files'),
        ]

        missing = []
        for pattern, description in required_patterns:
            if pattern not in gitignore_content:
                missing.append((pattern, description))

        if missing:
            for pattern, description in missing:
                self.findings.append(SecurityFinding(
                    category="Git Safety",
                    severity="high",
                    title=f"{pattern} not in .gitignore",
                    description=f"{description} should be excluded from version control",
                    location=".gitignore",
                    remediation=f"Add '{pattern}' to .gitignore"
                ))
            print(f"  {YELLOW}⚠{NC}  .gitignore missing {len(missing)} required patterns")
        else:
            print(f"  {GREEN}✓{NC} .gitignore covers sensitive files")

    def check_git_history_for_secrets(self):
        """Check if secrets have been committed to git history."""
        self.checks_run += 1

        git_dir = self.atomic_root / ".git"
        if not git_dir.exists():
            print(f"  {DIM}−{NC} Not a git repository")
            return

        # Check if any secrets.json files are tracked
        try:
            result = subprocess.run(
                ['git', 'ls-files', '*secrets.json'],
                cwd=self.atomic_root,
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.stdout.strip():
                tracked_files = result.stdout.strip().split('\n')
                for file_path in tracked_files:
                    self.findings.append(SecurityFinding(
                        category="Git Safety",
                        severity="critical",
                        title="Secrets file tracked in git",
                        description="Secrets file is tracked by git and may be in history",
                        location=file_path,
                        remediation=f"Run: git rm --cached {file_path} && git commit -m 'Remove secrets'"
                    ))
                print(f"  {RED}✗{NC} Secrets files tracked in git: {len(tracked_files)}")
            else:
                print(f"  {GREEN}✓{NC} No secrets files tracked in git")

        except subprocess.TimeoutExpired:
            print(f"  {YELLOW}⚠{NC}  Git check timed out")
        except Exception as e:
            print(f"  {YELLOW}⚠{NC}  Could not check git history: {e}")

    # ========================================================================
    # 4. INPUT VALIDATION
    # ========================================================================

    def run_input_validation_checks(self):
        """Check for input validation vulnerabilities."""
        self.print_section("Input Validation")

        self.check_command_injection_risks()
        self.check_path_traversal_risks()
        self.check_prompt_injection_risks()

        print()

    def check_command_injection_risks(self):
        """Check for potential command injection vulnerabilities."""
        self.checks_run += 1

        risky_patterns = [
            (r'subprocess\.(run|call|check_output)\([^)]*f["\']', 'Subprocess with f-string'),
            (r'os\.system\([^)]*\+', 'os.system with concatenation'),
            (r'subprocess\.(run|call)\([^)]*shell=True', 'Shell=True without proper escaping'),
        ]

        vulnerabilities = []

        for py_file in self.atomic_root.rglob("*.py"):
            # Skip test files
            if 'test' in str(py_file):
                continue

            try:
                content = py_file.read_text()

                for pattern, risk_type in risky_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        line = content.split('\n')[line_num - 1].strip()

                        # Check if input validation is present nearby
                        context_start = max(0, match.start() - 500)
                        context_end = min(len(content), match.end() + 500)
                        context = content[context_start:context_end]

                        has_validation = any(keyword in context.lower() for keyword in [
                            'shlex.quote', 'quote(', 'sanitize', 'validate', 'escape'
                        ])

                        if not has_validation:
                            vulnerabilities.append({
                                'file': str(py_file.relative_to(self.atomic_root)),
                                'line': line_num,
                                'type': risk_type,
                                'code': line
                            })

            except Exception:
                continue

        if vulnerabilities:
            for vuln in vulnerabilities:
                self.findings.append(SecurityFinding(
                    category="Input Validation",
                    severity="high",
                    title=f"Potential command injection: {vuln['type']}",
                    description="User input may be passed to shell without validation",
                    location=f"{vuln['file']}:{vuln['line']}",
                    remediation="Use shlex.quote() or avoid shell=True. Validate all user input.",
                    details=vuln
                ))
            print(f"  {YELLOW}⚠{NC}  Command injection risks: {len(vulnerabilities)} found")
        else:
            print(f"  {GREEN}✓{NC} No obvious command injection risks")

    def check_path_traversal_risks(self):
        """Check for path traversal vulnerabilities."""
        self.checks_run += 1

        risky_patterns = [
            (r'open\([^)]*\+', 'File open with concatenation'),
            (r'Path\([^)]*\+', 'Path with concatenation'),
            (r'\.read_text\(\)', 'Direct file read'),
        ]

        vulnerabilities = []

        for py_file in self.atomic_root.rglob("*.py"):
            # Skip test files
            if 'test' in str(py_file):
                continue

            try:
                content = py_file.read_text()

                # Look for file operations with user input
                if 'input(' in content or 'args.' in content:
                    for pattern, risk_type in risky_patterns:
                        matches = re.finditer(pattern, content)
                        for match in matches:
                            line_num = content[:match.start()].count('\n') + 1

                            # Check for path validation
                            context_start = max(0, match.start() - 500)
                            context_end = min(len(content), match.end() + 500)
                            context = content[context_start:context_end]

                            has_validation = any(keyword in context for keyword in [
                                'resolve()', 'is_relative_to', 'absolute()', 'normpath'
                            ])

                            if not has_validation:
                                vulnerabilities.append({
                                    'file': str(py_file.relative_to(self.atomic_root)),
                                    'line': line_num,
                                    'type': risk_type
                                })

            except Exception:
                continue

        if vulnerabilities:
            for vuln in vulnerabilities:
                self.findings.append(SecurityFinding(
                    category="Input Validation",
                    severity="medium",
                    title=f"Potential path traversal: {vuln['type']}",
                    description="File path may not be validated",
                    location=f"{vuln['file']}:{vuln['line']}",
                    remediation="Use Path.resolve() and validate paths are within expected directories",
                    details=vuln
                ))
            print(f"  {YELLOW}⚠{NC}  Path traversal risks: {len(vulnerabilities)} found")
        else:
            print(f"  {GREEN}✓{NC} No obvious path traversal risks")

    def check_prompt_injection_risks(self):
        """Check for prompt injection vulnerabilities."""
        self.checks_run += 1

        # Look for prompts that include user input without sanitization
        risky_files = []

        for py_file in self.atomic_root.rglob("*.py"):
            # Skip test files
            if 'test' in str(py_file):
                continue

            try:
                content = py_file.read_text()

                # Look for prompt construction with user input
                if 'prompt' in content.lower() and ('input(' in content or 'args.' in content):
                    # Check if sanitization is present
                    has_sanitization = any(keyword in content for keyword in [
                        'escape', 'sanitize', 'validate', 'strip_tags', 'html.escape'
                    ])

                    if not has_sanitization:
                        risky_files.append(str(py_file.relative_to(self.atomic_root)))

            except Exception:
                continue

        if risky_files:
            for file_path in risky_files:
                self.findings.append(SecurityFinding(
                    category="Input Validation",
                    severity="low",
                    title="Potential prompt injection risk",
                    description="User input included in prompts without visible sanitization",
                    location=file_path,
                    remediation="Validate and escape user input before including in prompts"
                ))
            print(f"  {YELLOW}⚠{NC}  Prompt injection risks: {len(risky_files)} files")
        else:
            print(f"  {GREEN}✓{NC} No obvious prompt injection risks")

    # ========================================================================
    # 5. NETWORK SECURITY
    # ========================================================================

    def run_network_security_checks(self):
        """Check network security configuration."""
        self.print_section("Network Security")

        self.check_network_mode_enforcement()
        self.check_sandbox_configuration()
        self.check_fetch_restrictions()

        print()

    def check_network_mode_enforcement(self):
        """Check that network mode is properly enforced."""
        self.checks_run += 1

        # Check if network mode is checked before making requests
        provider_file = self.atomic_root / "lib" / "provider.py"

        if provider_file.exists():
            content = provider_file.read_text()

            has_network_check = 'ATOMIC_NETWORK_MODE' in content or 'ATOMIC_OFFLINE_MODE' in content

            if has_network_check:
                print(f"  {GREEN}✓{NC} Network mode enforcement present")
            else:
                self.findings.append(SecurityFinding(
                    category="Network Security",
                    severity="medium",
                    title="Network mode not enforced",
                    description="Code may not check network mode before making requests",
                    location="lib/provider.py",
                    remediation="Check ATOMIC_NETWORK_MODE or ATOMIC_OFFLINE_MODE before network requests"
                ))
                print(f"  {YELLOW}⚠{NC}  Network mode enforcement not found")
        else:
            print(f"  {DIM}−{NC} provider.py not found")

    def check_sandbox_configuration(self):
        """Check sandbox configuration."""
        self.checks_run += 1

        # Check for sandbox bypass attempts
        bypass_patterns = [
            (r'dangerouslyDisableSandbox.*=.*True', 'Sandbox disabled'),
            (r'SANDBOX_ENABLED.*=.*False', 'Sandbox disabled'),
        ]

        bypasses = []

        for py_file in self.atomic_root.rglob("*.py"):
            try:
                content = py_file.read_text()

                for pattern, description in bypass_patterns:
                    if re.search(pattern, content):
                        bypasses.append(str(py_file.relative_to(self.atomic_root)))

            except Exception:
                continue

        if bypasses:
            for file_path in bypasses:
                self.findings.append(SecurityFinding(
                    category="Network Security",
                    severity="high",
                    title="Sandbox may be disabled",
                    description="Code contains sandbox bypass configuration",
                    location=file_path,
                    remediation="Review sandbox configuration and ensure it's enabled in production"
                ))
            print(f"  {YELLOW}⚠{NC}  Potential sandbox bypasses: {len(bypasses)}")
        else:
            print(f"  {GREEN}✓{NC} No sandbox bypasses detected")

    def check_fetch_restrictions(self):
        """Check that fetch operations are restricted."""
        self.checks_run += 1

        # Check for unrestricted URL fetching
        atomic_file = self.atomic_root / "lib" / "atomic.py"

        if atomic_file.exists():
            content = atomic_file.read_text()

            # Look for URL validation
            has_url_validation = 'allowed_domains' in content.lower() or 'validate_url' in content.lower()

            if not has_url_validation:
                self.findings.append(SecurityFinding(
                    category="Network Security",
                    severity="low",
                    title="URL fetching may not be restricted",
                    description="No obvious URL validation found",
                    location="lib/atomic.py",
                    remediation="Implement whitelist of allowed domains for fetching"
                ))
                print(f"  {YELLOW}⚠{NC}  URL validation not found")
            else:
                print(f"  {GREEN}✓{NC} URL validation present")
        else:
            print(f"  {DIM}−{NC} atomic.py not found")

    # ========================================================================
    # 6. DASHBOARD SECURITY
    # ========================================================================

    def run_dashboard_security_checks(self):
        """Check dashboard security."""
        self.print_section("Dashboard Security")

        self.check_xss_vulnerabilities()
        self.check_sensitive_data_exposure()
        self.check_cors_configuration()

        print()

    def check_xss_vulnerabilities(self):
        """Check for XSS vulnerabilities in dashboard."""
        self.checks_run += 1

        dashboard_files = list((self.atomic_root / "dashboard").rglob("*.html")) + \
                          list((self.atomic_root / "dashboard").rglob("*.js"))

        vulnerabilities = []

        for file_path in dashboard_files:
            try:
                content = file_path.read_text()

                # Look for innerHTML without sanitization
                if 'innerHTML' in content:
                    # Check for sanitization
                    has_sanitization = any(keyword in content for keyword in [
                        'DOMPurify', 'textContent', 'innerText', 'escape', 'sanitize'
                    ])

                    if not has_sanitization:
                        vulnerabilities.append(str(file_path.relative_to(self.atomic_root)))

            except Exception:
                continue

        if vulnerabilities:
            for file_path in vulnerabilities:
                self.findings.append(SecurityFinding(
                    category="Dashboard Security",
                    severity="high",
                    title="Potential XSS vulnerability",
                    description="innerHTML used without visible sanitization",
                    location=file_path,
                    remediation="Use textContent or sanitize HTML with DOMPurify"
                ))
            print(f"  {YELLOW}⚠{NC}  Potential XSS vulnerabilities: {len(vulnerabilities)}")
        else:
            print(f"  {GREEN}✓{NC} No obvious XSS vulnerabilities")

    def check_sensitive_data_exposure(self):
        """Check that sensitive data is not exposed in dashboard."""
        self.checks_run += 1

        server_file = self.atomic_root / "dashboard" / "server.js"

        if server_file.exists():
            content = server_file.read_text()

            # Check if API keys or secrets are exposed
            exposes_secrets = any(keyword in content for keyword in [
                'ANTHROPIC_API_KEY', 'AWS_SECRET', 'secrets.json', 'api_key'
            ])

            if exposes_secrets:
                self.findings.append(SecurityFinding(
                    category="Dashboard Security",
                    severity="critical",
                    title="Sensitive data may be exposed",
                    description="Dashboard code references sensitive data",
                    location="dashboard/server.js",
                    remediation="Never expose API keys or secrets through dashboard API"
                ))
                print(f"  {RED}✗{NC} Sensitive data may be exposed")
            else:
                print(f"  {GREEN}✓{NC} No sensitive data exposure detected")
        else:
            print(f"  {DIM}−{NC} Dashboard server not found")

    def check_cors_configuration(self):
        """Check CORS configuration."""
        self.checks_run += 1

        server_file = self.atomic_root / "dashboard" / "server.js"

        if server_file.exists():
            content = server_file.read_text()

            # Check for overly permissive CORS
            if "Access-Control-Allow-Origin" in content:
                if "'*'" in content or '"*"' in content:
                    self.findings.append(SecurityFinding(
                        category="Dashboard Security",
                        severity="medium",
                        title="Overly permissive CORS",
                        description="CORS allows all origins (*)",
                        location="dashboard/server.js",
                        remediation="Restrict CORS to specific origins or localhost"
                    ))
                    print(f"  {YELLOW}⚠{NC}  CORS allows all origins")
                else:
                    print(f"  {GREEN}✓{NC} CORS configured with restrictions")
            else:
                print(f"  {GREEN}✓{NC} No CORS configuration (default same-origin)")
        else:
            print(f"  {DIM}−{NC} Dashboard server not found")

    # ========================================================================
    # REPORTING
    # ========================================================================

    def save_report(self, report: SecurityReport):
        """Save report to JSON file."""
        report_file = self.reports_dir / "security-audit.json"

        report_data = {
            'timestamp': report.timestamp,
            'total_checks': report.total_checks,
            'findings': {
                'critical': report.critical_count(),
                'high': report.high_count(),
                'medium': report.medium_count(),
                'low': report.low_count(),
                'total': len(report.findings)
            },
            'duration': f"{report.duration:.2f}s",
            'details': [
                {
                    'category': f.category,
                    'severity': f.severity,
                    'title': f.title,
                    'description': f.description,
                    'location': f.location,
                    'remediation': f.remediation,
                    'details': f.details
                }
                for f in report.findings
            ]
        }

        report_file.write_text(json.dumps(report_data, indent=2))
        print(f"\n{DIM}Report saved: {report_file}{NC}")

    def print_summary(self, report: SecurityReport):
        """Print audit summary."""
        print()
        self.print_header("SECURITY AUDIT SUMMARY")
        print()

        # Statistics
        print(f"  Total Checks:    {report.total_checks}")
        print(f"  Duration:        {report.duration:.2f}s")
        print()

        # Findings by severity
        print(f"  {RED}Critical:{NC}  {report.critical_count():3d}")
        print(f"  {YELLOW}High:{NC}      {report.high_count():3d}")
        print(f"  {YELLOW}Medium:{NC}    {report.medium_count():3d}")
        print(f"  {CYAN}Low:{NC}       {report.low_count():3d}")
        print(f"  {DIM}━{NC * 18}")
        print(f"  Total:      {len(report.findings):3d}")
        print()

        # Show findings by category
        if report.findings:
            categories = {}
            for finding in report.findings:
                if finding.category not in categories:
                    categories[finding.category] = []
                categories[finding.category].append(finding)

            print(f"{BOLD}Findings by Category:{NC}")
            print()

            for category, findings in sorted(categories.items()):
                print(f"  {BOLD}{category}{NC}")
                for finding in findings[:5]:  # Show first 5 per category
                    severity_color = {
                        'critical': RED,
                        'high': YELLOW,
                        'medium': YELLOW,
                        'low': CYAN
                    }.get(finding.severity, NC)

                    print(f"    {severity_color}[{finding.severity.upper()}]{NC} {finding.title}")
                    if finding.location:
                        print(f"    {DIM}Location: {finding.location}{NC}")
                    if finding.remediation:
                        print(f"    {DIM}Fix: {finding.remediation}{NC}")
                    print()

                if len(findings) > 5:
                    print(f"    {DIM}... and {len(findings) - 5} more{NC}")
                    print()
        else:
            print(f"{GREEN}✓ No security issues found!{NC}")
            print()

        # Final status
        if report.has_critical_issues():
            print(f"{RED}{BOLD}CRITICAL ISSUES FOUND - IMMEDIATE ACTION REQUIRED{NC}")
        elif report.findings:
            print(f"{YELLOW}Security issues found - review and remediate{NC}")
        else:
            print(f"{GREEN}{BOLD}Security audit passed!{NC}")

        print()

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def print_header(self, text: str):
        """Print section header."""
        print(f"\n{BOLD}{BLUE}{'=' * 70}{NC}")
        print(f"{BOLD}{BLUE}{text.center(70)}{NC}")
        print(f"{BOLD}{BLUE}{'=' * 70}{NC}\n")

    def print_section(self, text: str):
        """Print section title."""
        print(f"{BOLD}{CYAN}{text}{NC}")
        print(f"{DIM}{'-' * len(text)}{NC}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Run security audit."""
    runner = SecurityAuditRunner()
    report = runner.run_all_checks()

    # Exit with error if critical issues found
    if report.has_critical_issues():
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
