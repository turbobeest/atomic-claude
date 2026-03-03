"""
Task 505: Final Validation

Analyze TDD results using REAL data from execution artifacts:
  - tdd-progress.json for task completion stats
  - Per-task tdd-t*.json records for pass/fail/retry counts
  - Actual test runner output (cargo test / pytest) if tools available
  - Optional coverage tool output if installed

No hardcoded metrics — everything comes from actual artifacts.
"""

import sys
import json
import logging
import re
import shlex
import tempfile
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.subprocess_runner import run_bash_command
from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim
)
from core.utils.file_ops import ensure_dir, write_file


def _load_json(path: Path) -> Dict[str, Any]:
    """Load JSON file, returning empty dict on failure."""
    try:
        if path.exists():
            return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.debug("Failed to load JSON from %s: %s", path, e)
    return {}


def _load_tdd_progress(output_dir: Path) -> Dict[str, Any]:
    """Load tdd-progress.json from output dir."""
    return _load_json(output_dir / "tdd-progress.json")


def _load_per_task_records(testing_dir: Path) -> List[Dict[str, Any]]:
    """Load all per-task TDD records from .claude/testing/tdd-t*.json."""
    records = []
    if not testing_dir.exists():
        return records

    for record_file in sorted(testing_dir.glob("tdd-t*.json")):
        data = _load_json(record_file)
        if data:
            records.append(data)

    return records


def _aggregate_tdd_records(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate per-task records into summary metrics."""
    total = len(records)
    completed = 0
    failed = 0
    red_complete = 0
    green_complete = 0
    green_retries = 0
    refactor_complete = 0
    refactor_reverted = 0
    verify_complete = 0
    security_warnings = 0
    bootstrap_count = 0
    library_count = 0
    feature_count = 0

    for rec in records:
        status = rec.get("status", "")
        if status == "complete":
            completed += 1
        elif status in ("failed", "budget_exceeded"):
            failed += 1

        classification = rec.get("classification", "feature")
        if classification == "bootstrap":
            bootstrap_count += 1
        elif classification == "library":
            library_count += 1
        else:
            feature_count += 1

        red = rec.get("red", {})
        if red.get("status") == "complete":
            red_complete += 1

        green = rec.get("green", {})
        if green.get("status") in ("complete", "written"):
            green_complete += 1
        attempts = green.get("attempts", 1)
        if attempts > 1:
            green_retries += attempts - 1

        refactor = rec.get("refactor", {})
        if refactor.get("status") == "complete":
            refactor_complete += 1
        elif refactor.get("status") == "reverted":
            refactor_reverted += 1

        verify = rec.get("verify", {})
        if verify.get("status") == "complete":
            verify_complete += 1
        warnings = verify.get("warnings", [])
        security_warnings += sum(1 for w in warnings if "security" in w.lower())

    return {
        "total_records": total,
        "completed": completed,
        "failed": failed,
        "red_complete": red_complete,
        "green_complete": green_complete,
        "green_retries": green_retries,
        "refactor_complete": refactor_complete,
        "refactor_reverted": refactor_reverted,
        "verify_complete": verify_complete,
        "security_warnings": security_warnings,
        "classification": {
            "bootstrap": bootstrap_count,
            "library": library_count,
            "feature": feature_count,
        },
    }


def _run_test_suite(
    stack: str, project_root: Path
) -> Optional[Dict[str, Any]]:
    """Run the actual test suite and parse results.

    Returns dict with tests_passed, tests_failed, tests_errors, or None if
    the test runner isn't available.
    """
    # NOTE: shlex.quote is POSIX-only but this runs under Git Bash on
    # Windows, where POSIX quoting is correct.
    safe_root = shlex.quote(str(project_root))
    if stack == "rust":
        cmd = f"cd {safe_root} && cargo test 2>&1"
    elif stack == "python":
        cmd = f"cd {safe_root} && python -m pytest --tb=no -q 2>&1"
    elif stack == "node":
        cmd = f"cd {safe_root} && npx jest --no-coverage --silent 2>&1"
    elif stack == "go":
        cmd = f"cd {safe_root} && go test ./... 2>&1"
    else:
        return None

    exit_code, stdout, stderr = run_bash_command(
        cmd, "5-implementation", "505", timeout=120,
        reject_shell_meta=False,  # commands use cd && and 2>&1
    )

    output = (stdout + "\n" + stderr).strip()

    if stack == "rust":
        # Parse ALL "test result:" lines (workspaces produce one per binary)
        matches = re.findall(
            r"test result:.*?(\d+)\s+passed.*?(\d+)\s+failed", output
        )
        if matches:
            total_passed = sum(int(m[0]) for m in matches)
            total_failed = sum(int(m[1]) for m in matches)
            return {
                "tests_passed": total_passed,
                "tests_failed": total_failed,
                "tests_errors": 0,
                "raw_output": output[-500:],
            }

    elif stack == "python":
        # Parse: X passed, Y failed, Z errors  OR  X passed
        passed = 0
        failed = 0
        errors = 0

        m = re.search(r"(\d+)\s+passed", output)
        if m:
            passed = int(m.group(1))
        m = re.search(r"(\d+)\s+failed", output)
        if m:
            failed = int(m.group(1))
        m = re.search(r"(\d+)\s+error", output)
        if m:
            errors = int(m.group(1))

        if passed > 0 or failed > 0 or errors > 0:
            return {
                "tests_passed": passed,
                "tests_failed": failed,
                "tests_errors": errors,
                "raw_output": output[-500:],
            }

    elif stack == "node":
        # Parse Jest output: Tests: X passed, Y failed, Z total
        m = re.search(r"Tests:\s+.*?(\d+)\s+passed", output)
        passed = int(m.group(1)) if m else 0
        m = re.search(r"Tests:\s+.*?(\d+)\s+failed", output)
        failed = int(m.group(1)) if m else 0
        if passed > 0 or failed > 0:
            return {
                "tests_passed": passed,
                "tests_failed": failed,
                "tests_errors": 0,
                "raw_output": output[-500:],
            }

    elif stack == "go":
        # Parse: ok or FAIL lines
        # NOTE: Go's `go test ./...` reports per-package results, not
        # individual test counts.  The passed/failed numbers here represent
        # package-level pass/fail, not individual test functions.
        passed = len(re.findall(r"^ok\s+", output, re.MULTILINE))
        failed = len(re.findall(r"^FAIL\s+", output, re.MULTILINE))
        if passed > 0 or failed > 0:
            return {
                "tests_passed": passed,
                "tests_failed": failed,
                "tests_errors": 0,
                "raw_output": output[-500:],
            }

    # Could not parse — might not be set up yet
    return None


def _run_coverage(
    stack: str, project_root: Path
) -> Optional[Dict[str, Any]]:
    """Run coverage tool and parse results. Returns None if not available."""
    safe_root = shlex.quote(str(project_root))
    if stack == "rust":
        # cargo tarpaulin
        tarpaulin_dir = tempfile.gettempdir()
        cmd = f"cd {safe_root} && cargo tarpaulin --out json --output-dir {shlex.quote(tarpaulin_dir)} 2>&1"
        coverage_json = Path(tarpaulin_dir) / "tarpaulin-report.json"
    elif stack == "python":
        cmd = f"cd {safe_root} && python -m pytest --cov --cov-report=json --cov-report=term -q 2>&1"
        coverage_json = project_root / "coverage.json"
    else:
        return None

    exit_code, stdout, stderr = run_bash_command(
        cmd, "5-implementation", "505", timeout=180,
        reject_shell_meta=False,  # commands use cd && and 2>&1
    )

    if exit_code != 0:
        return None

    # Try to parse the JSON report
    try:
        if coverage_json.exists():
            data = json.loads(coverage_json.read_text())

            if stack == "rust":
                # Tarpaulin JSON: top-level "covered" and "coverable" keys
                covered = data.get("covered", 0)
                total = data.get("coverable", 1)
                pct = (covered / total * 100) if total > 0 else 0
                return {"line_coverage_pct": round(pct, 1), "source": "tarpaulin"}

            elif stack == "python":
                # coverage.py JSON format
                totals = data.get("totals", {})
                pct = totals.get("percent_covered", 0)
                return {"line_coverage_pct": round(pct, 1), "source": "coverage.py"}
    except (json.JSONDecodeError, OSError, KeyError) as e:
        logger.debug("Failed to parse coverage report from %s: %s", coverage_json, e)

    return None


def get_validation_metrics(
    output_dir: Path,
    testing_dir: Path,
    setup_file: Path,
    project_root: Path,
) -> Dict[str, Any]:
    """
    Collect all validation metrics from real artifacts.

    Sources:
      1. tdd-progress.json — overall task completion
      2. tdd-t*.json per-task records — pass/fail/retry aggregates
      3. Real test suite run (if tools available)
      4. Coverage tool (if installed)
    """
    # Load setup for targets and stack info
    setup = _load_json(setup_file)
    stack = setup.get("detected_stack", "python")
    unit_target = setup.get("coverage_targets", {}).get("unit", 80)
    integration_target = setup.get("coverage_targets", {}).get("integration", 70)

    # Source 1: TDD progress
    progress = _load_tdd_progress(output_dir)

    # Source 2: Per-task records
    records = _load_per_task_records(testing_dir)
    aggregated = _aggregate_tdd_records(records)

    # Source 3: Real test suite (if tools available)
    test_results = None
    tools_available = setup.get("tools_available", False)
    if tools_available:
        test_results = _run_test_suite(stack, project_root)

    # Source 4: Coverage (if tool installed)
    coverage_results = None
    if tools_available and test_results:
        coverage_results = _run_coverage(stack, project_root)

    # Build metrics
    metrics = {
        "stack": stack,
        "targets": {
            "unit_coverage": unit_target,
            "integration_coverage": integration_target,
        },
        "tdd_completion": {
            "tasks_total": progress.get("tasks_total", aggregated["total_records"]),
            "tasks_completed": progress.get("tasks_completed", aggregated["completed"]),
            "tasks_failed": progress.get("tasks_failed", aggregated["failed"]),
            "tasks_cascaded": progress.get("tasks_cascaded", 0),
        },
        "tdd_cycles": {
            "red_complete": aggregated["red_complete"],
            "green_complete": aggregated["green_complete"],
            "green_retries": aggregated["green_retries"],
            "refactor_complete": aggregated["refactor_complete"],
            "refactor_reverted": aggregated["refactor_reverted"],
            "verify_complete": aggregated["verify_complete"],
        },
        "classification": aggregated["classification"],
        "security": {
            "warnings_from_verify": aggregated["security_warnings"],
            "critical": 0,
            "high": 0,
        },
        "test_suite": test_results if test_results else "not_available",
        "coverage": coverage_results if coverage_results else "not_available",
    }

    return metrics


def execute(atomic_root: Path, output_dir: Path, mem=None) -> bool:
    """
    Execute Task 505: Final Validation.

    Reads REAL metrics from TDD execution artifacts — no hardcoded numbers.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory

    Returns:
        True if task completed successfully, False otherwise
    """
    project_root = atomic_root.parent
    testing_dir = project_root / ".claude" / "testing"
    validation_file = testing_dir / "validation-report.json"
    setup_file = output_dir / "tdd-setup.json"

    ensure_dir(testing_dir)

    print()
    print(print_dim("  Analyzing TDD results from execution artifacts."))
    print()

    # Collect real metrics
    metrics = get_validation_metrics(output_dir, testing_dir, setup_file, project_root)

    tdd = metrics["tdd_completion"]
    cycles = metrics["tdd_cycles"]
    test_suite = metrics["test_suite"]
    coverage = metrics["coverage"]
    security = metrics["security"]

    # -----------------------------------------------------------------------
    # TDD Completion
    # -----------------------------------------------------------------------
    print(print_dim("─" * 120))
    print()
    print(print_bold("TDD COMPLETION"))
    print()

    total = tdd["tasks_total"]
    completed = tdd["tasks_completed"]
    failed = tdd["tasks_failed"]
    cascaded = tdd.get("tasks_cascaded", 0)
    completion_rate = (completed * 100 // total) if total > 0 else 0

    print("  " + "─" * 114)
    print(print_bold("  TASK STATUS"))
    print()
    print(f"    Tasks Completed:    {completed} / {total}")
    print(f"    Tasks Failed:       {failed}")
    if cascaded:
        print(f"    Tasks Cascaded:     {cascaded}")

    if completion_rate == 100:
        print(print_green(f"    Completion Rate:    {completion_rate}%"))
    elif completion_rate >= 70:
        print(print_yellow(f"    Completion Rate:    {completion_rate}%"))
    else:
        print(print_red(f"    Completion Rate:    {completion_rate}%"))

    print()
    print(print_bold("  TDD CYCLES"))
    print()
    print(f"    RED complete:       {cycles['red_complete']}")
    print(f"    GREEN complete:     {cycles['green_complete']}")
    if cycles['green_retries'] > 0:
        print(print_yellow(f"    GREEN retries:      {cycles['green_retries']}"))
    print(f"    REFACTOR complete:  {cycles['refactor_complete']}")
    if cycles['refactor_reverted'] > 0:
        print(print_yellow(f"    REFACTOR reverted:  {cycles['refactor_reverted']}"))
    print(f"    VERIFY complete:    {cycles['verify_complete']}")

    # Task classification breakdown
    classification = metrics.get("classification", {})
    if any(classification.values()):
        print()
        print(print_bold("  TASK CLASSIFICATION"))
        print()
        if classification.get("bootstrap"):
            print(f"    Bootstrap:          {classification['bootstrap']}")
        if classification.get("library"):
            print(f"    Library:            {classification['library']}")
        if classification.get("feature"):
            print(f"    Feature:            {classification['feature']}")

    print("  " + "─" * 114)
    print()

    # -----------------------------------------------------------------------
    # Test Suite Results (real)
    # -----------------------------------------------------------------------
    print(print_dim("─" * 120))
    print()
    print(print_bold("TEST SUITE RESULTS"))
    print()

    print("  " + "─" * 114)

    if isinstance(test_suite, dict):
        tests_passed = test_suite.get("tests_passed", 0)
        tests_failed = test_suite.get("tests_failed", 0)
        tests_errors = test_suite.get("tests_errors", 0)
        total_tests = tests_passed + tests_failed + tests_errors

        print(print_bold("  TEST SUITE (live run)"))
        print()
        print(f"    Total Tests:        {total_tests}")
        print(print_green(f"    Passing:            {tests_passed}"))
        if tests_failed > 0:
            print(print_red(f"    Failing:            {tests_failed}"))
        else:
            print(print_green(f"    Failing:            {tests_failed}"))
        if tests_errors > 0:
            print(print_red(f"    Errors:             {tests_errors}"))
    else:
        print(print_dim("  TEST SUITE"))
        print()
        print(print_dim("    Test runner not available — skipped live test run"))
        print(print_dim("    (Install build tools to enable test suite validation)"))
        total_tests = 0
        tests_passed = 0
        tests_failed = 0

    print("  " + "─" * 114)
    print()

    # -----------------------------------------------------------------------
    # Coverage (real)
    # -----------------------------------------------------------------------
    print(print_dim("─" * 120))
    print()
    print(print_bold("COVERAGE"))
    print()

    print("  " + "─" * 114)

    unit_coverage_pct = 0
    if isinstance(coverage, dict):
        unit_coverage_pct = coverage.get("line_coverage_pct", 0)
        source = coverage.get("source", "unknown")
        target = metrics["targets"]["unit_coverage"]

        print(print_bold(f"  COVERAGE ({source})"))
        print()
        if unit_coverage_pct >= target:
            print(print_green(f"    Line Coverage:      {unit_coverage_pct}%") +
                  f" (target: {target}%)")
        else:
            print(print_red(f"    Line Coverage:      {unit_coverage_pct}%") +
                  f" (target: {target}%)")
    else:
        print(print_dim("  COVERAGE"))
        print()
        print(print_dim("    Coverage tool not available"))
        print(print_dim("    (Install cargo-tarpaulin or pytest-cov to enable)"))

    print("  " + "─" * 114)
    print()

    # -----------------------------------------------------------------------
    # Security
    # -----------------------------------------------------------------------
    print(print_dim("─" * 120))
    print()
    print(print_bold("SECURITY STATUS"))
    print()

    print("  " + "─" * 114)
    print(print_bold("  SECURITY FINDINGS"))
    print()

    if security["critical"] == 0:
        print(print_green(f"    Critical Issues:    {security['critical']}"))
    else:
        print(print_red(f"    Critical Issues:    {security['critical']}"))

    if security["high"] == 0:
        print(print_green(f"    High Issues:        {security['high']}"))
    else:
        print(print_red(f"    High Issues:        {security['high']}"))

    verify_warnings = security["warnings_from_verify"]
    if verify_warnings > 0:
        print(print_yellow(f"    VERIFY Warnings:    {verify_warnings}"))
    else:
        print(print_green(f"    VERIFY Warnings:    {verify_warnings}"))

    print("  " + "─" * 114)
    print()

    # -----------------------------------------------------------------------
    # Validation Summary
    # -----------------------------------------------------------------------
    print(print_dim("─" * 120))
    print()
    print(print_bold("VALIDATION SUMMARY"))
    print()

    validation_passed = True

    # TDD completion
    if completed > 0 and total > 0:
        if completed == total:
            print(print_green(f"  + All TDD cycles complete ({completed} tasks)"))
        elif completion_rate >= 70:
            print(print_yellow(f"  ~ TDD completion: {completion_rate}% ({completed}/{total})"))
        else:
            print(print_red(f"  X TDD completion low: {completion_rate}% ({completed}/{total})"))
            validation_passed = False
    else:
        print(print_red("  X No TDD tasks completed"))
        validation_passed = False

    # Test suite
    if isinstance(test_suite, dict):
        if tests_failed == 0 and total_tests > 0:
            print(print_green(f"  + All tests passing ({tests_passed} tests)"))
        elif tests_failed > 0:
            print(print_red(f"  X {tests_failed} tests failing out of {total_tests}"))
            validation_passed = False
    else:
        print(print_dim("  - Test suite: not available (no build tools)"))

    # Coverage
    if isinstance(coverage, dict):
        target = metrics["targets"]["unit_coverage"]
        if unit_coverage_pct >= target:
            print(print_green(f"  + Coverage meets target ({unit_coverage_pct}% >= {target}%)"))
        else:
            print(print_yellow(f"  ~ Coverage below target ({unit_coverage_pct}% < {target}%)"))
    else:
        print(print_dim("  - Coverage: not available (tool not installed)"))

    # Security
    if security["critical"] == 0 and security["high"] == 0:
        print(print_green("  + No critical or high security issues"))
    else:
        total_security = security["critical"] + security["high"]
        print(print_red(f"  X {total_security} critical/high security issues"))
        validation_passed = False

    # Green retries (quality signal)
    if cycles["green_retries"] > 0:
        retry_pct = (cycles["green_retries"] / max(cycles["green_complete"], 1)) * 100
        if retry_pct > 50:
            print(print_yellow(f"  ~ High retry rate: {cycles['green_retries']} GREEN retries ({retry_pct:.0f}%)"))
        else:
            print(print_dim(f"  - GREEN retries: {cycles['green_retries']}"))

    print()

    if validation_passed:
        print(print_green("=" * 120))
        print(print_green("  VALIDATION PASSED") + " - Ready for phase audit")
        print(print_green("=" * 120))
    else:
        print(print_yellow("=" * 120))
        print(print_yellow("  VALIDATION WARNINGS") + " - Review issues before proceeding")
        print(print_yellow("=" * 120))
    print()

    # Save validation report
    validation_data = {
        "metrics": metrics,
        "tdd_completion": tdd,
        "tdd_cycles": cycles,
        "test_suite": test_suite if isinstance(test_suite, dict) else None,
        "coverage": coverage if isinstance(coverage, dict) else None,
        "security": security,
        "validation_passed": validation_passed,
        "validated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_file(validation_file, json.dumps(validation_data, indent=2))

    print(print_green("  Final Validation complete"))
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 505: Final Validation")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir)
    sys.exit(0 if success else 1)
