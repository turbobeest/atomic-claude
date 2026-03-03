"""
Task 704: Testing Execution

Execute integration tests against the assembled system.
Runs E2E tests, acceptance validation, and performance benchmarks.
"""

import logging
import sys
from pathlib import Path
from typing import Dict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_green,
    print_red, print_dim, print_yellow
)
from core.utils.file_ops import read_json, write_json


def run_integration_tests(atomic_root: Path, setup_data: Dict) -> Dict:
    """
    Run integration test suites.

    Args:
        atomic_root: Path to atomic-claude root
        setup_data: Integration setup configuration

    Returns:
        Dict with test results (tests_run, tests_passed, tests_failed)
    """
    # STUB: Returns simulated results. Implement actual test execution
    # (pytest, cargo test, etc.) for production use.
    acceptance_criteria = setup_data.get("acceptance_criteria", {})

    total_tests = 0
    passed = 0
    test_details = []

    # E2E test suite
    criteria_count = acceptance_criteria.get("total", 5) if isinstance(acceptance_criteria, dict) else 5
    e2e_tests = max(criteria_count, 5)
    e2e_passed = e2e_tests  # Assume passing in default implementation
    total_tests += e2e_tests
    passed += e2e_passed
    test_details.append({
        "suite": "e2e",
        "total": e2e_tests,
        "passed": e2e_passed,
        "failed": e2e_tests - e2e_passed,
        "simulated": True
    })

    # Acceptance tests
    acceptance_tests = 10
    acceptance_passed = acceptance_tests
    total_tests += acceptance_tests
    passed += acceptance_passed
    test_details.append({
        "suite": "acceptance",
        "total": acceptance_tests,
        "passed": acceptance_passed,
        "failed": acceptance_tests - acceptance_passed,
        "simulated": True
    })

    # Performance benchmarks
    perf_tests = 3
    perf_passed = perf_tests
    total_tests += perf_tests
    passed += perf_passed
    test_details.append({
        "suite": "performance",
        "total": perf_tests,
        "passed": perf_passed,
        "failed": perf_tests - perf_passed,
        "simulated": True
    })

    failed = total_tests - passed

    return {
        "tests_run": total_tests,
        "tests_passed": passed,
        "tests_failed": failed,
        "test_details": test_details,
        "simulated": True
    }


def execute(atomic_root: Path, output_dir: Path, mem=None) -> bool:
    """
    Execute Task 704: Testing Execution.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory

    Returns:
        True if task completed successfully, False otherwise
    """
    results_file = output_dir / "integration-test-results.json"
    setup_file = output_dir / "integration-setup.json"

    print()
    print(print_dim("  Executing integration tests."))
    print()

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run actual integration tests
    print(print_bold("  INTEGRATION TEST EXECUTION"))
    print()

    # Load integration setup
    try:
        setup_data = read_json(setup_file)
    except (FileNotFoundError, ValueError, OSError) as e:
        print(print_red(f"  Integration setup not found: {e}"))
        print(print_red("  Run Task 702 (Integration Setup) first."))
        return False

    # Run tests
    print(print_dim("  Running test suites..."))
    print()

    test_results = run_integration_tests(atomic_root, setup_data)

    if test_results.get("simulated", False):
        print(print_yellow("  ⚠ Integration tests are SIMULATED — no real tests were executed"))
        print()

    tests_run = test_results["tests_run"]
    tests_passed = test_results["tests_passed"]
    tests_failed = test_results["tests_failed"]
    success_rate = round((tests_passed / tests_run * 100), 1) if tests_run > 0 else 0.0

    # Print results
    print(print_dim("  " + "-" * 60))
    print(print_bold("  TEST RESULTS"))
    print()

    for suite in test_results.get("test_details", []):
        suite_name = suite["suite"].upper()
        s_passed = suite["passed"]
        s_total = suite["total"]
        color = print_green if s_passed == s_total else print_red
        print(color(f"    {suite_name}: {s_passed}/{s_total} passed"))

    print()
    print(print_dim("  " + "-" * 60))

    if tests_failed > 0:
        print(print_red(f"  FAILED: {tests_failed} test(s) failed"))
    else:
        print(print_green(f"  PASSED: All {tests_run} tests passed"))

    print(print_dim(f"  Success rate: {success_rate}%"))
    print()

    # Build summary
    if success_rate == 100:
        summary = f"All integration tests passed ({tests_passed}/{tests_run})"
    elif success_rate >= 95:
        summary = f"Integration tests passed ({tests_passed}/{tests_run}, {tests_failed} minor failure(s))"
    elif success_rate >= 80:
        summary = f"Most integration tests passed ({tests_passed}/{tests_run}, {tests_failed} failures)"
    else:
        summary = f"Integration tests have significant failures ({tests_failed}/{tests_run} failed)"

    # Write results
    is_simulated = test_results.get("simulated", False)
    results = {
        "tests_run": tests_run,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "summary": summary,
        "success_rate": success_rate,
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "mode": "normal",
        "simulated": is_simulated,
        "test_suites": test_results.get("test_details", [])
    }

    write_json(results_file, results)

    if tests_failed > 0:
        print(print_red("  Integration test execution complete with failures"))
        return False

    if is_simulated:
        print(print_yellow("  Integration tests are SIMULATED — phase cannot pass without real test execution"))
        return False

    print(print_green("  Integration test execution complete"))
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 704: Testing Execution")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir)
    sys.exit(0 if success else 1)
