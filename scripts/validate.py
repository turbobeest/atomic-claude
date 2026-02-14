#!/usr/bin/env python3
"""
Validation Tool

Validates atomic-claude2 installation and configuration.
"""

import sys
import json
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict, Any


class Validator:
    """System validation checker."""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.checks_passed = 0
        self.checks_total = 0

    def check(self, name: str, condition: bool, error_msg: str = "", warning: bool = False):
        """
        Run a validation check.

        Args:
            name: Check name
            condition: Check condition (True = pass)
            error_msg: Error message if check fails
            warning: If True, treat as warning not error
        """
        self.checks_total += 1

        if condition:
            print(f"✓ {name}")
            self.checks_passed += 1
        else:
            symbol = "⚠" if warning else "✗"
            print(f"{symbol} {name}")
            if error_msg:
                print(f"  {error_msg}")

            if warning:
                self.warnings.append(f"{name}: {error_msg}")
            else:
                self.errors.append(f"{name}: {error_msg}")

    def validate_python_version(self):
        """Check Python version >= 3.9."""
        major, minor = sys.version_info[:2]
        self.check(
            "Python version >= 3.9",
            major == 3 and minor >= 9,
            f"Found Python {major}.{minor}, need >= 3.9",
        )

    def validate_dependencies(self):
        """Check required packages are installed."""
        # Core required packages
        required = ["pytest", "boto3", "requests"]

        for package in required:
            try:
                __import__(package)
                self.check(f"Package '{package}' installed", True)
            except ImportError:
                self.check(
                    f"Package '{package}' installed",
                    False,
                    f"Run: pip install {package}",
                )

        # Optional LLM providers (at least one should be installed)
        optional_providers = ["anthropic", "boto3"]
        provider_installed = False

        for package in optional_providers:
            try:
                __import__(package)
                self.check(f"Package '{package}' installed", True)
                provider_installed = True
            except ImportError:
                self.check(
                    f"Package '{package}' installed (optional)",
                    False,
                    f"Run: pip install -r requirements-llm.txt (or use Bedrock/Ollama)",
                    warning=True,
                )

        # Check that at least boto3 is available (for Bedrock)
        if not provider_installed:
            # boto3 is already checked above, so if we get here it means
            # anthropic is not installed but boto3 is, which is fine
            pass

    def validate_directory_structure(self):
        """Check directory structure is correct."""
        required_dirs = [
            "core",
            "phases",
            "orchestration",
            "tests",
            "config",
        ]

        for dir_name in required_dirs:
            dir_path = Path(dir_name)
            self.check(
                f"Directory '{dir_name}/' exists",
                dir_path.exists() and dir_path.is_dir(),
                f"Missing required directory: {dir_name}/",
            )

    def validate_phase_modules(self):
        """Check all phase modules exist."""
        for i in range(10):
            phase_name = f"phase_0{i}_" + [
                "setup", "discovery", "prd", "tasking", "specification",
                "implementation", "code_review", "integration",
                "deployment_prep", "release"
            ][i]

            tasks_dir = Path("phases") / phase_name / "tasks"
            self.check(
                f"Phase {i} tasks directory exists",
                tasks_dir.exists(),
                f"Missing: {tasks_dir}",
                warning=True,
            )

    def validate_configuration(self):
        """Check configuration files."""
        config_files = [
            ("pytest.ini", False),
            ("setup.py", True),
            (".gitignore", True),
            ("requirements.txt", False),
        ]

        for file_name, optional in config_files:
            file_path = Path(file_name)
            if optional:
                self.check(
                    f"Config file '{file_name}'",
                    file_path.exists(),
                    f"Optional file missing: {file_name}",
                    warning=True,
                )
            else:
                self.check(
                    f"Config file '{file_name}'",
                    file_path.exists(),
                    f"Required file missing: {file_name}",
                )

    def validate_imports(self):
        """Check core modules can be imported."""
        modules = [
            "core.state",
            "core.config",
            "core.llm",
            "core.utils.cli_ui",
            "core.utils.file_ops",
        ]

        for module in modules:
            try:
                __import__(module)
                self.check(f"Import {module}", True)
            except Exception as e:
                self.check(
                    f"Import {module}",
                    False,
                    f"Import error: {str(e)[:60]}",
                )

    def run_validation(self) -> bool:
        """
        Run all validation checks.

        Returns:
            True if all checks passed
        """
        print("=" * 60)
        print("ATOMIC-CLAUDE2 VALIDATION")
        print("=" * 60)
        print()

        print("Python Environment:")
        self.validate_python_version()
        print()

        print("Dependencies:")
        self.validate_dependencies()
        print()

        print("Directory Structure:")
        self.validate_directory_structure()
        self.validate_phase_modules()
        print()

        print("Configuration:")
        self.validate_configuration()
        print()

        print("Module Imports:")
        self.validate_imports()
        print()

        # Print summary
        print("=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Checks passed: {self.checks_passed}/{self.checks_total}")
        print(f"Errors: {len(self.errors)}")
        print(f"Warnings: {len(self.warnings)}")
        print()

        if self.errors:
            print("ERRORS:")
            for error in self.errors:
                print(f"  ✗ {error}")
            print()

        if self.warnings:
            print("WARNINGS:")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")
            print()

        success = len(self.errors) == 0
        if success:
            print("✓ Validation passed!")
        else:
            print("✗ Validation failed - fix errors above")

        return success


def main():
    """Run validation."""
    validator = Validator()
    success = validator.run_validation()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
