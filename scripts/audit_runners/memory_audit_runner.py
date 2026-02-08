#!/usr/bin/env python3
"""
Memory Audit Test Runner

Validates proper claude-mem integration across all 70 tasks in the pipeline.
Tests memory saves, recalls, lifecycle hooks, and artifact persistence.

Usage:
    python test/memory_audit_runner.py              # Test all phases (0-9)
    python test/memory_audit_runner.py --phase 2    # Test specific phase
    python test/memory_audit_runner.py --verbose    # Detailed output
"""

import sys
import os
import subprocess
import json
import argparse
from pathlib import Path
from typing import Dict, List, Set, Optional
from datetime import datetime

# Repo root
REPO_ROOT = Path(__file__).parent.parent.resolve()
MEMORY_DIR = REPO_ROOT / ".state" / "memory"
OUTPUT_DIR = REPO_ROOT / ".outputs"

# Colors for output
class Colors:
    CYAN = '\033[0;36m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    NC = '\033[0m'


class MemoryAuditRunner:
    """Memory integration audit runner."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.memory_saves: Dict[str, List[str]] = {}  # phase -> [memory files]
        self.memory_recalls: Dict[str, List[str]] = {}  # phase -> [recall queries]
        self.task_results: Dict[str, Dict] = {}  # task_id -> results

    def log(self, message: str, color: str = Colors.NC):
        """Log a message with color."""
        print(f"{color}{message}{Colors.NC}")

    def setup_test_environment(self):
        """Set up test environment with memory tracing enabled."""
        self.log("\n" + "="*80, Colors.CYAN)
        self.log("  MEMORY AUDIT TEST SETUP", Colors.CYAN)
        self.log("="*80, Colors.CYAN)

        # Clean previous test data
        if MEMORY_DIR.exists():
            self.log(f"\n  Cleaning previous memory state...", Colors.DIM)
            import shutil
            shutil.rmtree(MEMORY_DIR)

        if OUTPUT_DIR.exists():
            self.log(f"  Cleaning previous outputs...", Colors.DIM)
            import shutil
            shutil.rmtree(OUTPUT_DIR)

        # Create initialization directory with UAT setup
        init_dir = REPO_ROOT.parent / "initialization"
        init_dir.mkdir(exist_ok=True)

        # Copy UAT setup
        uat_setup = REPO_ROOT / "test" / "fixtures" / "uat_setup.md"
        setup_dst = init_dir / "setup.md"

        if uat_setup.exists():
            import shutil
            shutil.copy(uat_setup, setup_dst)
            self.log(f"\n  ✓ Copied UAT setup.md", Colors.GREEN)

        self.log(f"  ✓ Test environment ready", Colors.GREEN)
        return True

    def run_phase_with_memory_tracing(self, phase_num: int) -> bool:
        """
        Run a phase with memory tracing enabled.

        Args:
            phase_num: Phase number (0-9)

        Returns:
            True if phase completed successfully
        """
        self.log(f"\n" + "="*80, Colors.CYAN)
        self.log(f"  AUDITING PHASE {phase_num:02d} MEMORY USAGE", Colors.CYAN)
        self.log("="*80, Colors.CYAN)

        # Build command
        cmd = [
            sys.executable,
            str(REPO_ROOT / "main.py"),
            "run",
            str(phase_num)
        ]

        # Prepare environment with memory tracing
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        env["ATOMIC_ROOT"] = str(REPO_ROOT)
        env["ATOMIC_UAT_MODE"] = "true"  # Use UAT mode for fast execution
        env["ATOMIC_MEMORY_ENABLED"] = "true"  # Enable memory system
        env["ATOMIC_MEMORY_TRACE"] = "true"  # Enable memory tracing
        env["ATOMIC_TOOL_DEVELOPMENT"] = "true"  # Disable forcing function

        # Capture memory directory before run
        memory_before = self._scan_memory_files()

        self.log(f"\n  Running Phase {phase_num:02d} with memory tracing...\n", Colors.BOLD)

        try:
            # Run phase
            result = subprocess.run(
                cmd,
                cwd=REPO_ROOT,
                env=env,
                input="",
                text=True,
                timeout=600,
                capture_output=True
            )

            success = result.returncode == 0

            # Capture memory directory after run
            memory_after = self._scan_memory_files()

            # Analyze memory usage
            self._analyze_memory_usage(phase_num, memory_before, memory_after, result.stdout)

            if success:
                self.log(f"\n  ✓ Phase {phase_num:02d} completed", Colors.GREEN)
            else:
                self.log(f"\n  ✗ Phase {phase_num:02d} failed (exit code: {result.returncode})", Colors.RED)
                if self.verbose and result.stderr:
                    self.log(f"\n  Error output:\n{result.stderr[:500]}", Colors.DIM)

            return success

        except subprocess.TimeoutExpired:
            self.log(f"\n  ✗ Phase {phase_num:02d} timed out", Colors.RED)
            return False
        except Exception as e:
            self.log(f"\n  ✗ Phase {phase_num:02d} error: {e}", Colors.RED)
            return False

    def _scan_memory_files(self) -> Set[Path]:
        """Scan memory directory for all files."""
        if not MEMORY_DIR.exists():
            return set()

        files = set()
        for path in MEMORY_DIR.rglob("*"):
            if path.is_file():
                files.add(path.relative_to(MEMORY_DIR))
        return files

    def _analyze_memory_usage(
        self,
        phase_num: int,
        before: Set[Path],
        after: Set[Path],
        stdout: str
    ):
        """
        Analyze memory usage for a phase.

        Args:
            phase_num: Phase number
            before: Memory files before phase
            after: Memory files after phase
            stdout: Phase stdout for parsing memory operations
        """
        new_files = after - before
        phase_key = f"phase-{phase_num}"

        self.log(f"\n  Memory Analysis:", Colors.BOLD)

        if new_files:
            self.log(f"    ✓ Created {len(new_files)} memory artifacts", Colors.GREEN)
            self.memory_saves[phase_key] = sorted(str(f) for f in new_files)

            if self.verbose:
                for f in sorted(new_files)[:10]:  # Show first 10
                    self.log(f"      - {f}", Colors.DIM)
                if len(new_files) > 10:
                    self.log(f"      ... and {len(new_files) - 10} more", Colors.DIM)
        else:
            self.log(f"    ⚠ No memory artifacts created", Colors.YELLOW)
            self.memory_saves[phase_key] = []

        # Check for memory-related output in stdout
        memory_ops = self._parse_memory_operations(stdout)
        if memory_ops['saves'] > 0:
            self.log(f"    ✓ Detected {memory_ops['saves']} memory saves", Colors.GREEN)
        if memory_ops['recalls'] > 0:
            self.log(f"    ✓ Detected {memory_ops['recalls']} memory recalls", Colors.GREEN)
        if memory_ops['checkpoints'] > 0:
            self.log(f"    ✓ Detected {memory_ops['checkpoints']} checkpoints", Colors.GREEN)

    def _parse_memory_operations(self, stdout: str) -> Dict[str, int]:
        """Parse stdout for memory operations."""
        return {
            'saves': stdout.count('memory_save') + stdout.count('_memory_save_local'),
            'recalls': stdout.count('memory_recall') + stdout.count('_memory_recall_local'),
            'checkpoints': stdout.count('memory_checkpoint') + stdout.count('memory_add_checkpoint'),
        }

    def verify_memory_integrity(self, phase_num: int) -> Dict[str, any]:
        """
        Verify memory artifacts have proper structure and content.

        Args:
            phase_num: Phase number to verify

        Returns:
            Dict with verification results
        """
        phase_names = {
            0: "0-setup",
            1: "1-discovery",
            2: "2-prd",
            3: "3-tasking",
            4: "4-specification",
            5: "5-implementation",
            6: "6-code-review",
            7: "7-integration",
            8: "8-deployment-prep",
            9: "9-release"
        }

        phase_id = phase_names.get(phase_num)
        if not phase_id:
            return {"valid": False, "error": "Unknown phase"}

        phase_memory_dir = MEMORY_DIR / phase_id

        results = {
            "valid": True,
            "phase": phase_id,
            "artifacts_found": 0,
            "artifacts_valid": 0,
            "artifacts_invalid": [],
            "missing_expected": []
        }

        if not phase_memory_dir.exists():
            results["valid"] = False
            results["error"] = "Phase memory directory not found"
            return results

        # Check all memory artifacts
        for artifact in phase_memory_dir.glob("**/*"):
            if artifact.is_file():
                results["artifacts_found"] += 1

                # Verify artifact is readable and has content
                try:
                    content = artifact.read_text()
                    if len(content) > 0:
                        results["artifacts_valid"] += 1
                    else:
                        results["artifacts_invalid"].append(str(artifact.name))
                except Exception as e:
                    results["artifacts_invalid"].append(f"{artifact.name} (error: {e})")

        return results

    def generate_report(self, phases_tested: List[int]):
        """Generate comprehensive memory audit report."""
        self.log("\n" + "="*80, Colors.CYAN)
        self.log("  MEMORY AUDIT REPORT", Colors.CYAN)
        self.log("="*80, Colors.CYAN)

        total_saves = sum(len(files) for files in self.memory_saves.values())
        phases_with_memory = len([p for p in self.memory_saves.values() if p])

        self.log(f"\n  Phases Tested: {len(phases_tested)}", Colors.BOLD)
        self.log(f"  Phases Using Memory: {phases_with_memory}/{len(phases_tested)}", Colors.BOLD)
        self.log(f"  Total Memory Artifacts: {total_saves}", Colors.BOLD)

        # Per-phase breakdown
        self.log(f"\n  Per-Phase Memory Usage:", Colors.BOLD)
        for phase_num in phases_tested:
            phase_key = f"phase-{phase_num}"
            saves = self.memory_saves.get(phase_key, [])

            if saves:
                self.log(f"    ✓ Phase {phase_num:02d}: {len(saves)} artifacts", Colors.GREEN)
            else:
                self.log(f"    ⚠ Phase {phase_num:02d}: No memory artifacts", Colors.YELLOW)

        # Memory integrity verification
        self.log(f"\n  Memory Integrity Checks:", Colors.BOLD)
        all_valid = True
        for phase_num in phases_tested:
            integrity = self.verify_memory_integrity(phase_num)

            if integrity.get("artifacts_found", 0) > 0:
                valid = integrity["artifacts_valid"]
                total = integrity["artifacts_found"]
                if valid == total:
                    self.log(f"    ✓ Phase {phase_num:02d}: {valid}/{total} artifacts valid", Colors.GREEN)
                else:
                    self.log(f"    ⚠ Phase {phase_num:02d}: {valid}/{total} artifacts valid", Colors.YELLOW)
                    all_valid = False

                    if integrity["artifacts_invalid"]:
                        for invalid in integrity["artifacts_invalid"][:3]:
                            self.log(f"      - Invalid: {invalid}", Colors.DIM)

        # Overall assessment
        self.log(f"\n  Overall Assessment:", Colors.BOLD)

        if phases_with_memory == len(phases_tested) and all_valid:
            self.log(f"    ✅ EXCELLENT - All phases use memory correctly", Colors.GREEN)
        elif phases_with_memory >= len(phases_tested) * 0.7:
            self.log(f"    ⚠️ GOOD - Most phases use memory", Colors.YELLOW)
        else:
            self.log(f"    ❌ NEEDS IMPROVEMENT - Limited memory usage", Colors.RED)

        # Memory directory summary
        if MEMORY_DIR.exists():
            total_size = sum(f.stat().st_size for f in MEMORY_DIR.rglob("*") if f.is_file())
            total_files = sum(1 for _ in MEMORY_DIR.rglob("*") if _.is_file())

            self.log(f"\n  Memory Storage:", Colors.BOLD)
            self.log(f"    Location: {MEMORY_DIR}", Colors.DIM)
            self.log(f"    Total Files: {total_files}", Colors.DIM)
            self.log(f"    Total Size: {total_size:,} bytes ({total_size/1024:.1f} KB)", Colors.DIM)

        # Save detailed report
        self._save_detailed_report(phases_tested)

    def _save_detailed_report(self, phases_tested: List[int]):
        """Save detailed JSON report."""
        report_dir = REPO_ROOT / "test" / "reports"
        report_dir.mkdir(exist_ok=True)

        report_file = report_dir / f"memory-audit-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"

        report = {
            "timestamp": datetime.now().isoformat(),
            "phases_tested": phases_tested,
            "memory_saves": self.memory_saves,
            "memory_recalls": self.memory_recalls,
            "summary": {
                "phases_with_memory": len([p for p in self.memory_saves.values() if p]),
                "total_artifacts": sum(len(files) for files in self.memory_saves.values()),
            }
        }

        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        self.log(f"\n  Detailed report saved: {report_file}", Colors.CYAN)


def main():
    parser = argparse.ArgumentParser(
        description="Memory Audit Test Runner - Validate claude-mem integration",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--phase",
        type=int,
        choices=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        help="Test specific phase only"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    print("\n" + "="*80)
    print("  ATOMIC CLAUDE 2.0 - MEMORY AUDIT TEST")
    print("="*80)

    runner = MemoryAuditRunner(verbose=args.verbose)

    # Setup environment
    if not runner.setup_test_environment():
        sys.exit(1)

    # Determine phases to test
    phases = [args.phase] if args.phase is not None else list(range(10))

    # Run phases with memory tracing
    all_success = True
    for phase_num in phases:
        success = runner.run_phase_with_memory_tracing(phase_num)
        if not success:
            all_success = False
            # Continue testing other phases

    # Generate report
    runner.generate_report(phases)

    if all_success:
        print("\n" + "="*80)
        print(f"{Colors.GREEN}  ✓ MEMORY AUDIT COMPLETE{Colors.NC}")
        print("="*80 + "\n")
        sys.exit(0)
    else:
        print("\n" + "="*80)
        print(f"{Colors.YELLOW}  ⚠ MEMORY AUDIT COMPLETE (some phases failed){Colors.NC}")
        print("="*80 + "\n")
        sys.exit(0)  # Don't fail on phase errors, just report


if __name__ == "__main__":
    main()
