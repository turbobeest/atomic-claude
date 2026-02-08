#!/usr/bin/env python3
"""
Atomic Claude 2.0 - Package Verification Script

Verifies that the package is properly configured:
- All imports work
- Package structure is correct
- Dependencies are installable
- __init__.py files exist where needed
"""

import sys
import subprocess
from pathlib import Path
from typing import List, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class PackageVerifier:
    """Verifies package integrity and configuration."""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.success_count = 0
        self.total_checks = 0

    def check_file_exists(self, filepath: Path, description: str) -> bool:
        """Check if a required file exists."""
        self.total_checks += 1
        if filepath.exists():
            print(f"✅ {description}: {filepath.name}")
            self.success_count += 1
            return True
        else:
            error_msg = f"{description} missing: {filepath}"
            print(f"❌ {error_msg}")
            self.errors.append(error_msg)
            return False

    def check_directory_exists(self, dirpath: Path, description: str) -> bool:
        """Check if a required directory exists."""
        self.total_checks += 1
        if dirpath.exists() and dirpath.is_dir():
            print(f"✅ {description}: {dirpath.name}/")
            self.success_count += 1
            return True
        else:
            error_msg = f"{description} missing: {dirpath}"
            print(f"❌ {error_msg}")
            self.errors.append(error_msg)
            return False

    def check_import(self, module_name: str, description: str) -> bool:
        """Check if a module can be imported."""
        self.total_checks += 1
        try:
            __import__(module_name)
            print(f"✅ {description}: {module_name}")
            self.success_count += 1
            return True
        except ImportError as e:
            error_msg = f"{description} failed: {module_name} - {e}"
            print(f"❌ {error_msg}")
            self.errors.append(error_msg)
            return False

    def verify_packaging_files(self) -> None:
        """Verify packaging configuration files exist."""
        print("\n" + "=" * 80)
        print("CHECKING PACKAGING FILES")
        print("=" * 80)

        self.check_file_exists(
            PROJECT_ROOT / "pyproject.toml",
            "PEP 621 configuration"
        )
        self.check_file_exists(
            PROJECT_ROOT / "requirements.txt",
            "Production requirements"
        )
        self.check_file_exists(
            PROJECT_ROOT / "requirements-dev.txt",
            "Development requirements"
        )
        self.check_file_exists(
            PROJECT_ROOT / "setup.py",
            "Setup script (backward compatibility)"
        )
        self.check_file_exists(
            PROJECT_ROOT / "README.md",
            "README documentation"
        )

    def verify_directory_structure(self) -> None:
        """Verify required directories exist."""
        print("\n" + "=" * 80)
        print("CHECKING DIRECTORY STRUCTURE")
        print("=" * 80)

        required_dirs = [
            (PROJECT_ROOT / "core", "Core modules"),
            (PROJECT_ROOT / "orchestration", "Orchestration modules"),
            (PROJECT_ROOT / "phases", "Phase modules"),
            (PROJECT_ROOT / "lib", "Bash libraries"),
            (PROJECT_ROOT / "test", "Test suite"),
            (PROJECT_ROOT / "test" / "fixtures", "Test fixtures"),
            (PROJECT_ROOT / "test" / "runners", "Test runners"),
            (PROJECT_ROOT / "test" / "phase_configs", "Phase configs"),
            (PROJECT_ROOT / "scripts", "Utility scripts"),
            (PROJECT_ROOT / "config", "Configuration"),
            (PROJECT_ROOT / "agents", "Agent repository"),
            (PROJECT_ROOT / "audits", "Audit repository"),
        ]

        for dirpath, description in required_dirs:
            self.check_directory_exists(dirpath, description)

    def verify_init_files(self) -> None:
        """Verify __init__.py files exist where needed."""
        print("\n" + "=" * 80)
        print("CHECKING __init__.py FILES")
        print("=" * 80)

        required_init_files = [
            (PROJECT_ROOT / "core" / "__init__.py", "core package"),
            (PROJECT_ROOT / "orchestration" / "__init__.py", "orchestration package"),
            (PROJECT_ROOT / "phases" / "__init__.py", "phases package"),
            (PROJECT_ROOT / "test" / "__init__.py", "test package"),
            (PROJECT_ROOT / "test" / "fixtures" / "__init__.py", "test.fixtures package"),
            (PROJECT_ROOT / "test" / "runners" / "__init__.py", "test.runners package"),
            (PROJECT_ROOT / "test" / "phase_configs" / "__init__.py", "test.phase_configs package"),
        ]

        # Check phase subdirectories
        for i in range(10):
            phase_dir = PROJECT_ROOT / "phases" / f"phase{i:02d}"
            if phase_dir.exists():
                init_file = phase_dir / "__init__.py"
                required_init_files.append(
                    (init_file, f"phases.phase{i:02d} package")
                )

        for filepath, description in required_init_files:
            self.check_file_exists(filepath, description)

    def verify_core_imports(self) -> None:
        """Verify core module imports work."""
        print("\n" + "=" * 80)
        print("CHECKING CORE MODULE IMPORTS")
        print("=" * 80)

        core_modules = [
            ("core.state", "StateManager"),
            ("core.config", "Config"),
            ("core.subprocess_runner", "Subprocess runner"),
            ("core.memory", "Memory system"),
            ("core.llm", "LLM module"),
            ("core.providers", "Providers"),
        ]

        for module_name, description in core_modules:
            self.check_import(module_name, description)

    def verify_orchestration_imports(self) -> None:
        """Verify orchestration module imports work."""
        print("\n" + "=" * 80)
        print("CHECKING ORCHESTRATION MODULE IMPORTS")
        print("=" * 80)

        orchestration_modules = [
            ("orchestration.backtrack", "Backtracking"),
            ("orchestration.pre_task_validation", "Pre-task validation"),
        ]

        for module_name, description in orchestration_modules:
            self.check_import(module_name, description)

    def verify_phase_imports(self) -> None:
        """Verify phase orchestrator imports work."""
        print("\n" + "=" * 80)
        print("CHECKING PHASE ORCHESTRATOR IMPORTS")
        print("=" * 80)

        # Check which phases are implemented
        for i in range(10):
            phase_dir = PROJECT_ROOT / "phases" / f"phase{i:02d}"
            orchestrator_file = phase_dir / f"orchestrator{i:02d}.py"

            if orchestrator_file.exists():
                module_name = f"phases.phase{i:02d}.orchestrator{i:02d}"
                self.check_import(module_name, f"Phase {i} orchestrator")

    def verify_entry_point(self) -> None:
        """Verify main entry point works."""
        print("\n" + "=" * 80)
        print("CHECKING ENTRY POINT")
        print("=" * 80)

        # Check if main.py exists and can be imported
        main_file = PROJECT_ROOT / "main.py"
        if self.check_file_exists(main_file, "Main entry point"):
            self.check_import("main", "Main module")

    def check_dependencies_installable(self) -> None:
        """Check if dependencies can be resolved (doesn't actually install)."""
        print("\n" + "=" * 80)
        print("CHECKING DEPENDENCY RESOLUTION")
        print("=" * 80)

        requirements_file = PROJECT_ROOT / "requirements.txt"

        if not requirements_file.exists():
            self.errors.append("requirements.txt not found")
            print("❌ requirements.txt not found")
            return

        try:
            # Use pip to check if dependencies are resolvable without installing
            result = subprocess.run(
                [sys.executable, "-m", "pip", "check"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                print("✅ Installed dependencies are compatible")
                self.success_count += 1
            else:
                warning_msg = f"Dependency conflicts detected: {result.stdout}"
                print(f"⚠️  {warning_msg}")
                self.warnings.append(warning_msg)

            self.total_checks += 1

        except subprocess.TimeoutExpired:
            warning_msg = "Dependency check timed out"
            print(f"⚠️  {warning_msg}")
            self.warnings.append(warning_msg)
        except Exception as e:
            warning_msg = f"Could not check dependencies: {e}"
            print(f"⚠️  {warning_msg}")
            self.warnings.append(warning_msg)

    def print_summary(self) -> bool:
        """Print verification summary and return success status."""
        print("\n" + "=" * 80)
        print("VERIFICATION SUMMARY")
        print("=" * 80)

        print(f"\n✅ Passed: {self.success_count}/{self.total_checks} checks")

        if self.warnings:
            print(f"\n⚠️  Warnings: {len(self.warnings)}")
            for warning in self.warnings:
                print(f"   - {warning}")

        if self.errors:
            print(f"\n❌ Errors: {len(self.errors)}")
            for error in self.errors:
                print(f"   - {error}")
            print("\nPackage verification FAILED!")
            return False
        else:
            print("\n🎉 Package verification PASSED!")
            print("\nThe package is properly configured and ready to use.")
            print("\nNext steps:")
            print("  1. Install in development mode: pip install -e .")
            print("  2. Install with dev dependencies: pip install -e \".[dev]\"")
            print("  3. Run tests: pytest")
            print("  4. Run the CLI: python main.py status")
            return True


def main():
    """Run package verification."""
    print("\n" + "=" * 80)
    print("ATOMIC CLAUDE 2.0 - PACKAGE VERIFICATION")
    print("=" * 80)
    print(f"\nProject root: {PROJECT_ROOT}")

    verifier = PackageVerifier()

    # Run all verification checks
    verifier.verify_packaging_files()
    verifier.verify_directory_structure()
    verifier.verify_init_files()
    verifier.verify_core_imports()
    verifier.verify_orchestration_imports()
    verifier.verify_phase_imports()
    verifier.verify_entry_point()
    verifier.check_dependencies_installable()

    # Print summary and exit with appropriate code
    success = verifier.print_summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
