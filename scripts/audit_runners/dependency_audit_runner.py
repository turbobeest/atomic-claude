#!/usr/bin/env python3
"""
Dependency Audit Runner
Validates all required tools and versions are available for ATOMIC CLAUDE

This audit ensures that:
1. Core dependencies are installed (Python, Bash, git, jq)
2. Python packages are available
3. Optional tools are detected
4. Version compatibility is checked
5. Installation guidance is provided for missing tools
"""

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


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
# VERSION DATA STRUCTURES
# ============================================================================

@dataclass
class VersionInfo:
    """Version information for a dependency."""
    installed: bool
    version: Optional[str] = None
    meets_requirements: bool = True
    required_version: Optional[str] = None
    warning: Optional[str] = None


@dataclass
class DependencyResult:
    """Result of checking a single dependency."""
    name: str
    category: str  # core, python, optional
    status: str  # ok, warning, missing, error
    version_info: VersionInfo
    install_command: Optional[str] = None
    documentation_url: Optional[str] = None


@dataclass
class AuditReport:
    """Overall dependency audit report."""
    timestamp: str
    platform: str
    python_version: str
    total_dependencies: int
    ok_count: int
    warning_count: int
    missing_count: int
    error_count: int
    results: List[DependencyResult]

    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_dependencies == 0:
            return 0.0
        return (self.ok_count / self.total_dependencies) * 100


# ============================================================================
# DEPENDENCY AUDIT RUNNER
# ============================================================================

class DependencyAuditRunner:
    """
    Validates all required tools and versions for ATOMIC CLAUDE.
    """

    def __init__(self):
        self.atomic_root = Path(__file__).parent.parent.resolve()
        self.test_dir = self.atomic_root / "test"
        self.reports_dir = self.test_dir / "reports"

        # Ensure directories exist
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        self.results: List[DependencyResult] = []
        self.platform = platform.system()
        self.is_macos = self.platform == "Darwin"
        self.is_linux = self.platform == "Linux"

    # ========================================================================
    # CORE DEPENDENCIES
    # ========================================================================

    def check_core_dependencies(self) -> Dict[str, DependencyResult]:
        """
        Check core system dependencies required for ATOMIC CLAUDE.
        Returns dict of dependency_name -> DependencyResult
        """
        results = {}

        print(f"\n{BOLD}{BLUE}Checking Core Dependencies...{NC}")

        # Python
        results["python"] = self._check_python()

        # Bash
        results["bash"] = self._check_bash()

        # Git
        results["git"] = self._check_git()

        # jq
        results["jq"] = self._check_jq()

        # Node/npm (optional for dashboard)
        results["node"] = self._check_node()

        return results

    def _check_python(self) -> DependencyResult:
        """Check Python version."""
        print(f"  Checking Python...", end=" ")

        version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        major, minor = sys.version_info.major, sys.version_info.minor

        meets_req = major == 3 and minor >= 8

        if meets_req:
            status = "ok"
            warning = None
            if minor < 9:
                status = "warning"
                warning = "Python 3.9+ recommended for best compatibility"

            version_info = VersionInfo(
                installed=True,
                version=version,
                meets_requirements=meets_req,
                required_version="3.8+",
                warning=warning
            )

            print(f"{GREEN}✓{NC} {version}")

            return DependencyResult(
                name="Python",
                category="core",
                status=status,
                version_info=version_info,
                install_command=self._get_python_install_cmd(),
                documentation_url="https://www.python.org/downloads/"
            )
        else:
            print(f"{RED}✗{NC} {version} (requires 3.8+)")

            version_info = VersionInfo(
                installed=True,
                version=version,
                meets_requirements=False,
                required_version="3.8+",
                warning="Python version too old"
            )

            return DependencyResult(
                name="Python",
                category="core",
                status="error",
                version_info=version_info,
                install_command=self._get_python_install_cmd(),
                documentation_url="https://www.python.org/downloads/"
            )

    def _check_bash(self) -> DependencyResult:
        """Check Bash version."""
        print(f"  Checking Bash...", end=" ")

        try:
            result = subprocess.run(
                ["bash", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # Parse version from first line: "GNU bash, version 5.2.26(1)-release"
                version_line = result.stdout.split('\n')[0]
                version_match = re.search(r'version\s+(\d+\.\d+)', version_line)

                if version_match:
                    version = version_match.group(1)
                    major, minor = map(int, version.split('.'))

                    # macOS ships with bash 3.2, Linux typically has 4.0+
                    if self.is_macos:
                        meets_req = major >= 3 and minor >= 2
                        required = "3.2+"
                    else:
                        meets_req = major >= 4
                        required = "4.0+"

                    if meets_req:
                        status = "ok"
                        warning = None
                        if self.is_macos and major == 3:
                            status = "warning"
                            warning = "Consider upgrading to Bash 5+ via Homebrew"

                        print(f"{GREEN}✓{NC} {version}")

                        return DependencyResult(
                            name="Bash",
                            category="core",
                            status=status,
                            version_info=VersionInfo(
                                installed=True,
                                version=version,
                                meets_requirements=True,
                                required_version=required,
                                warning=warning
                            ),
                            install_command=self._get_bash_install_cmd(),
                            documentation_url="https://www.gnu.org/software/bash/"
                        )
                    else:
                        print(f"{RED}✗{NC} {version} (requires {required})")

                        return DependencyResult(
                            name="Bash",
                            category="core",
                            status="error",
                            version_info=VersionInfo(
                                installed=True,
                                version=version,
                                meets_requirements=False,
                                required_version=required
                            ),
                            install_command=self._get_bash_install_cmd(),
                            documentation_url="https://www.gnu.org/software/bash/"
                        )

                print(f"{YELLOW}?{NC} (unknown version)")
                return self._missing_result("Bash", "core", "Could not parse version")

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            print(f"{RED}✗{NC} Not found")
            return self._missing_result("Bash", "core", str(e))

        return self._missing_result("Bash", "core", "Unknown error")

    def _check_git(self) -> DependencyResult:
        """Check git availability."""
        print(f"  Checking git...", end=" ")

        git_path = shutil.which("git")

        if git_path:
            try:
                result = subprocess.run(
                    ["git", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0:
                    # Parse: "git version 2.39.3"
                    version_match = re.search(r'version\s+(\d+\.\d+\.\d+)', result.stdout)
                    version = version_match.group(1) if version_match else "unknown"

                    print(f"{GREEN}✓{NC} {version}")

                    return DependencyResult(
                        name="git",
                        category="core",
                        status="ok",
                        version_info=VersionInfo(
                            installed=True,
                            version=version,
                            meets_requirements=True,
                            required_version="any recent version"
                        ),
                        install_command=self._get_git_install_cmd(),
                        documentation_url="https://git-scm.com/"
                    )

            except Exception as e:
                pass

        print(f"{RED}✗{NC} Not found")
        return self._missing_result("git", "core")

    def _check_jq(self) -> DependencyResult:
        """Check jq availability."""
        print(f"  Checking jq...", end=" ")

        jq_path = shutil.which("jq")

        if jq_path:
            try:
                result = subprocess.run(
                    ["jq", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0:
                    # Parse: "jq-1.6"
                    version = result.stdout.strip().replace("jq-", "")

                    print(f"{GREEN}✓{NC} {version}")

                    return DependencyResult(
                        name="jq",
                        category="core",
                        status="ok",
                        version_info=VersionInfo(
                            installed=True,
                            version=version,
                            meets_requirements=True,
                            required_version="any recent version"
                        ),
                        install_command=self._get_jq_install_cmd(),
                        documentation_url="https://stedolan.github.io/jq/"
                    )

            except Exception as e:
                pass

        print(f"{RED}✗{NC} Not found")
        return self._missing_result("jq", "core")

    def _check_node(self) -> DependencyResult:
        """Check Node.js availability (optional for dashboard)."""
        print(f"  Checking Node.js (optional)...", end=" ")

        node_path = shutil.which("node")

        if node_path:
            try:
                result = subprocess.run(
                    ["node", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0:
                    version = result.stdout.strip().lstrip('v')

                    print(f"{GREEN}✓{NC} {version}")

                    return DependencyResult(
                        name="Node.js",
                        category="optional",
                        status="ok",
                        version_info=VersionInfo(
                            installed=True,
                            version=version,
                            meets_requirements=True,
                            required_version="14+"
                        ),
                        install_command=self._get_node_install_cmd(),
                        documentation_url="https://nodejs.org/"
                    )

            except Exception as e:
                pass

        print(f"{YELLOW}✗{NC} Not found (dashboard won't work)")

        return DependencyResult(
            name="Node.js",
            category="optional",
            status="warning",
            version_info=VersionInfo(
                installed=False,
                meets_requirements=False,
                required_version="14+",
                warning="Tasks dashboard requires Node.js"
            ),
            install_command=self._get_node_install_cmd(),
            documentation_url="https://nodejs.org/"
        )

    # ========================================================================
    # PYTHON PACKAGES
    # ========================================================================

    def check_python_packages(self) -> Dict[str, DependencyResult]:
        """
        Check Python package dependencies.
        Returns dict of package_name -> DependencyResult
        """
        results = {}

        print(f"\n{BOLD}{BLUE}Checking Python Packages...{NC}")

        # Core packages (stdlib only currently)
        stdlib_packages = [
            "json", "subprocess", "pathlib", "argparse", "typing"
        ]

        for package in stdlib_packages:
            results[package] = self._check_python_package(package, stdlib=True)

        # Optional packages
        optional_packages = [
            ("anthropic", "Anthropic SDK for API access"),
            ("pytest", "Testing framework"),
            ("pyyaml", "YAML config support"),
            ("rich", "Enhanced terminal output")
        ]

        for package, description in optional_packages:
            results[package] = self._check_python_package(
                package,
                stdlib=False,
                optional=True,
                description=description
            )

        return results

    def _check_python_package(
        self,
        package: str,
        stdlib: bool = False,
        optional: bool = False,
        description: str = None
    ) -> DependencyResult:
        """Check if a Python package is available."""
        status_str = "(stdlib)" if stdlib else "(optional)" if optional else ""
        print(f"  Checking {package} {status_str}...", end=" ")

        try:
            __import__(package)
            print(f"{GREEN}✓{NC}")

            # Try to get version for non-stdlib packages
            version = None
            if not stdlib:
                try:
                    import importlib.metadata
                    version = importlib.metadata.version(package)
                except:
                    pass

            return DependencyResult(
                name=package,
                category="python",
                status="ok",
                version_info=VersionInfo(
                    installed=True,
                    version=version,
                    meets_requirements=True
                ),
                install_command=f"pip install {package}" if not stdlib else None,
                documentation_url=f"https://pypi.org/project/{package}/" if not stdlib else None
            )

        except ImportError:
            if stdlib:
                # Stdlib package missing is serious
                print(f"{RED}✗{NC} Missing (stdlib)")
                return DependencyResult(
                    name=package,
                    category="python",
                    status="error",
                    version_info=VersionInfo(
                        installed=False,
                        meets_requirements=False,
                        warning="Standard library package missing - Python installation may be corrupted"
                    )
                )
            elif optional:
                print(f"{YELLOW}✗{NC} Not installed")
                return DependencyResult(
                    name=package,
                    category="python",
                    status="warning",
                    version_info=VersionInfo(
                        installed=False,
                        meets_requirements=False,
                        warning=description
                    ),
                    install_command=f"pip install {package}",
                    documentation_url=f"https://pypi.org/project/{package}/"
                )
            else:
                print(f"{RED}✗{NC} Not installed")
                return DependencyResult(
                    name=package,
                    category="python",
                    status="missing",
                    version_info=VersionInfo(
                        installed=False,
                        meets_requirements=False
                    ),
                    install_command=f"pip install {package}",
                    documentation_url=f"https://pypi.org/project/{package}/"
                )

    # ========================================================================
    # OPTIONAL TOOLS
    # ========================================================================

    def check_optional_tools(self) -> Dict[str, DependencyResult]:
        """
        Check optional tool dependencies.
        Returns dict of tool_name -> DependencyResult
        """
        results = {}

        print(f"\n{BOLD}{BLUE}Checking Optional Tools...{NC}")

        # Claude CLI
        results["claude"] = self._check_claude_cli()

        # shellcheck
        results["shellcheck"] = self._check_shellcheck()

        return results

    def _check_claude_cli(self) -> DependencyResult:
        """Check Claude CLI availability."""
        print(f"  Checking claude CLI...", end=" ")

        claude_path = shutil.which("claude")

        if claude_path:
            try:
                result = subprocess.run(
                    ["claude", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                # claude CLI might not have --version, check if it exists
                if result.returncode == 0 or "claude" in result.stdout.lower():
                    print(f"{GREEN}✓{NC} Found")

                    return DependencyResult(
                        name="claude",
                        category="optional",
                        status="ok",
                        version_info=VersionInfo(
                            installed=True,
                            meets_requirements=True
                        ),
                        documentation_url="https://claude.ai/code"
                    )

            except Exception:
                pass

        print(f"{YELLOW}✗{NC} Not found")

        return DependencyResult(
            name="claude",
            category="optional",
            status="warning",
            version_info=VersionInfo(
                installed=False,
                meets_requirements=False,
                warning="Claude CLI provides max provider support"
            ),
            install_command="See https://claude.ai/code for installation",
            documentation_url="https://claude.ai/code"
        )

    def _check_shellcheck(self) -> DependencyResult:
        """Check shellcheck availability."""
        print(f"  Checking shellcheck...", end=" ")

        shellcheck_path = shutil.which("shellcheck")

        if shellcheck_path:
            try:
                result = subprocess.run(
                    ["shellcheck", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0:
                    # Parse version
                    version_match = re.search(r'version:\s+(\S+)', result.stdout)
                    version = version_match.group(1) if version_match else "unknown"

                    print(f"{GREEN}✓{NC} {version}")

                    return DependencyResult(
                        name="shellcheck",
                        category="optional",
                        status="ok",
                        version_info=VersionInfo(
                            installed=True,
                            version=version,
                            meets_requirements=True
                        ),
                        install_command=self._get_shellcheck_install_cmd(),
                        documentation_url="https://www.shellcheck.net/"
                    )

            except Exception:
                pass

        print(f"{YELLOW}✗{NC} Not found")

        return DependencyResult(
            name="shellcheck",
            category="optional",
            status="warning",
            version_info=VersionInfo(
                installed=False,
                meets_requirements=False,
                warning="shellcheck provides enhanced bash validation"
            ),
            install_command=self._get_shellcheck_install_cmd(),
            documentation_url="https://www.shellcheck.net/"
        )

    # ========================================================================
    # VERSION COMPATIBILITY
    # ========================================================================

    def check_versions(self) -> Dict[str, bool]:
        """
        Check version compatibility across Python versions.
        Returns dict of version -> compatible (bool)
        """
        print(f"\n{BOLD}{BLUE}Version Compatibility...{NC}")

        current_version = f"{sys.version_info.major}.{sys.version_info.minor}"

        # Test Python 3.8-3.12 compatibility
        versions_to_test = ["3.8", "3.9", "3.10", "3.11", "3.12"]

        compatibility = {}

        for version in versions_to_test:
            if version == current_version:
                print(f"  Python {version}: {GREEN}✓{NC} (current)")
                compatibility[version] = True
            else:
                # We can't actually test other versions, just mark as compatible
                print(f"  Python {version}: {CYAN}~{NC} (not tested)")
                compatibility[version] = None

        # Check for deprecated versions
        major, minor = sys.version_info.major, sys.version_info.minor

        if major == 3 and minor < 9:
            print(f"\n  {YELLOW}⚠{NC}  Python {current_version} will reach EOL soon")
            print(f"      Consider upgrading to Python 3.11+")

        return compatibility

    # ========================================================================
    # INSTALLATION COMMANDS
    # ========================================================================

    def _get_python_install_cmd(self) -> str:
        """Get Python installation command for current platform."""
        if self.is_macos:
            return "brew install python@3.11"
        elif self.is_linux:
            return "sudo apt install python3.11  # or: sudo yum install python311"
        else:
            return "See https://www.python.org/downloads/"

    def _get_bash_install_cmd(self) -> str:
        """Get Bash installation command for current platform."""
        if self.is_macos:
            return "brew install bash"
        elif self.is_linux:
            return "sudo apt install bash  # or: sudo yum install bash"
        else:
            return "See https://www.gnu.org/software/bash/"

    def _get_git_install_cmd(self) -> str:
        """Get git installation command for current platform."""
        if self.is_macos:
            return "brew install git  # or: xcode-select --install"
        elif self.is_linux:
            return "sudo apt install git  # or: sudo yum install git"
        else:
            return "See https://git-scm.com/downloads"

    def _get_jq_install_cmd(self) -> str:
        """Get jq installation command for current platform."""
        if self.is_macos:
            return "brew install jq"
        elif self.is_linux:
            return "sudo apt install jq  # or: sudo yum install jq"
        else:
            return "See https://stedolan.github.io/jq/download/"

    def _get_node_install_cmd(self) -> str:
        """Get Node.js installation command for current platform."""
        if self.is_macos:
            return "brew install node"
        elif self.is_linux:
            return "sudo apt install nodejs npm  # or use nvm: https://github.com/nvm-sh/nvm"
        else:
            return "See https://nodejs.org/en/download/"

    def _get_shellcheck_install_cmd(self) -> str:
        """Get shellcheck installation command for current platform."""
        if self.is_macos:
            return "brew install shellcheck"
        elif self.is_linux:
            return "sudo apt install shellcheck  # or: sudo yum install ShellCheck"
        else:
            return "See https://github.com/koalaman/shellcheck#installing"

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _missing_result(
        self,
        name: str,
        category: str,
        error: str = None
    ) -> DependencyResult:
        """Create a result for missing dependency."""
        install_cmd = None
        doc_url = None

        if name == "Bash":
            install_cmd = self._get_bash_install_cmd()
            doc_url = "https://www.gnu.org/software/bash/"
        elif name == "git":
            install_cmd = self._get_git_install_cmd()
            doc_url = "https://git-scm.com/"
        elif name == "jq":
            install_cmd = self._get_jq_install_cmd()
            doc_url = "https://stedolan.github.io/jq/"

        return DependencyResult(
            name=name,
            category=category,
            status="missing",
            version_info=VersionInfo(
                installed=False,
                meets_requirements=False,
                warning=error
            ),
            install_command=install_cmd,
            documentation_url=doc_url
        )

    # ========================================================================
    # MAIN RUN METHOD
    # ========================================================================

    def run_all_checks(self) -> AuditReport:
        """
        Run all dependency checks and generate report.
        """
        start_time = time.time()

        print(f"\n{BOLD}{CYAN}{'='*70}{NC}")
        print(f"{BOLD}{CYAN}ATOMIC CLAUDE - Dependency Audit{NC}")
        print(f"{BOLD}{CYAN}{'='*70}{NC}")

        print(f"\n{DIM}Platform: {self.platform}{NC}")
        print(f"{DIM}Python:   {sys.version.split()[0]}{NC}")

        # Run all checks
        core_results = self.check_core_dependencies()
        python_results = self.check_python_packages()
        optional_results = self.check_optional_tools()
        self.check_versions()

        # Combine all results
        all_results = {**core_results, **python_results, **optional_results}
        self.results = list(all_results.values())

        # Count by status
        ok_count = sum(1 for r in self.results if r.status == "ok")
        warning_count = sum(1 for r in self.results if r.status == "warning")
        missing_count = sum(1 for r in self.results if r.status == "missing")
        error_count = sum(1 for r in self.results if r.status == "error")

        duration = time.time() - start_time

        # Create report
        report = AuditReport(
            timestamp=datetime.now().isoformat(),
            platform=self.platform,
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            total_dependencies=len(self.results),
            ok_count=ok_count,
            warning_count=warning_count,
            missing_count=missing_count,
            error_count=error_count,
            results=self.results
        )

        # Display summary
        self._display_summary(report, duration)

        # Display installation guidance
        self._display_installation_guidance(report)

        # Save report
        self._save_report(report)

        return report

    def _display_summary(self, report: AuditReport, duration: float):
        """Display audit summary."""
        print(f"\n{BOLD}{CYAN}{'='*70}{NC}")
        print(f"{BOLD}{CYAN}Summary{NC}")
        print(f"{BOLD}{CYAN}{'='*70}{NC}\n")

        print(f"  Total Dependencies:  {report.total_dependencies}")
        print(f"  {GREEN}✓{NC} OK:                  {report.ok_count}")
        print(f"  {YELLOW}⚠{NC}  Warnings:            {report.warning_count}")
        print(f"  {YELLOW}✗{NC} Missing (optional):  {report.missing_count}")
        print(f"  {RED}✗{NC} Errors (required):   {report.error_count}")
        print(f"\n  Success Rate:        {report.success_rate():.1f}%")
        print(f"  Duration:            {duration:.2f}s")

        # Overall status
        if report.error_count > 0:
            print(f"\n  {RED}✗ FAILED{NC} - Required dependencies missing")
        elif report.missing_count > 0 or report.warning_count > 0:
            print(f"\n  {YELLOW}⚠ PASSED WITH WARNINGS{NC} - Optional dependencies missing")
        else:
            print(f"\n  {GREEN}✓ PASSED{NC} - All dependencies satisfied")

    def _display_installation_guidance(self, report: AuditReport):
        """Display installation guidance for missing dependencies."""
        missing = [r for r in report.results if r.status in ["missing", "error"]]
        warnings = [r for r in report.results if r.status == "warning"]

        if missing:
            print(f"\n{BOLD}{RED}Required Dependencies Missing:{NC}\n")

            for result in missing:
                print(f"  {BOLD}{result.name}{NC}")
                if result.install_command:
                    print(f"    Install: {CYAN}{result.install_command}{NC}")
                if result.documentation_url:
                    print(f"    Docs:    {DIM}{result.documentation_url}{NC}")
                print()

        if warnings:
            print(f"\n{BOLD}{YELLOW}Optional Dependencies (Recommended):{NC}\n")

            for result in warnings:
                print(f"  {BOLD}{result.name}{NC}")
                if result.version_info.warning:
                    print(f"    Note:    {result.version_info.warning}")
                if result.install_command:
                    print(f"    Install: {CYAN}{result.install_command}{NC}")
                if result.documentation_url:
                    print(f"    Docs:    {DIM}{result.documentation_url}{NC}")
                print()

    def _save_report(self, report: AuditReport):
        """Save report to JSON file."""
        report_file = self.reports_dir / f"dependency-audit-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"

        # Convert to dict
        report_dict = {
            "timestamp": report.timestamp,
            "platform": report.platform,
            "python_version": report.python_version,
            "total_dependencies": report.total_dependencies,
            "ok_count": report.ok_count,
            "warning_count": report.warning_count,
            "missing_count": report.missing_count,
            "error_count": report.error_count,
            "success_rate": report.success_rate(),
            "results": [
                {
                    "name": r.name,
                    "category": r.category,
                    "status": r.status,
                    "version": r.version_info.version,
                    "meets_requirements": r.version_info.meets_requirements,
                    "required_version": r.version_info.required_version,
                    "warning": r.version_info.warning,
                    "install_command": r.install_command,
                    "documentation_url": r.documentation_url
                }
                for r in report.results
            ]
        }

        with open(report_file, 'w') as f:
            json.dump(report_dict, f, indent=2)

        print(f"\n{DIM}Report saved: {report_file}{NC}\n")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point."""
    runner = DependencyAuditRunner()
    report = runner.run_all_checks()

    # Exit with error if required dependencies missing
    if report.error_count > 0:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
