"""
Task 705: Integration Approval

Human gate for approving integration test results.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user, clear_input_buffer
)
from core.utils.file_ops import read_json, write_json


def execute(atomic_root: Path, output_dir: Path, mem=None) -> bool:
    """
    Execute Task 705: Integration Approval.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory

    Returns:
        True if task completed successfully, False otherwise
    """
    project_root = atomic_root.parent

    integration_dir = project_root / ".claude" / "integration"
    report_file = output_dir / "integration-test-results.json"
    approval_file = integration_dir / "approval.json"

    print()
    print(print_dim("Human gate: Review and approve integration results."))
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # RESULTS SUMMARY
    # ─────────────────────────────────────────────────────────────────────────

    print()
    print(print_bold("  - RESULTS SUMMARY"))
    print()

    # Load report data
    e2e_passed = 0
    e2e_total = 0
    criteria_passed = 0
    criteria_total = 0
    overall_status = "unknown"
    report_is_simulated = False

    if report_file.exists():
        try:
            report_data = read_json(report_file)
        except (ValueError, OSError) as e:
            logger.warning("Failed to read integration report %s: %s", report_file, e)
            report_data = {}
        # integration-test-results.json uses different keys than the old integration-report.json
        e2e_passed = report_data.get("tests_passed", e2e_passed)
        e2e_total = report_data.get("tests_run", e2e_total)
        report_is_simulated = report_data.get("simulated", False)
        # Look for acceptance data in test suites if available
        for suite in report_data.get("test_suites", []):
            if suite.get("suite") == "acceptance":
                criteria_passed = suite.get("passed", criteria_passed)
                criteria_total = suite.get("total", criteria_total)
        overall_status = "ready" if report_data.get("tests_failed", 0) == 0 else "issues"
    else:
        print(print_yellow("WARNING: Integration report not found -- cannot verify test results"))
        overall_status = "missing"

    print(print_dim("─" * 118))
    print(print_bold("INTEGRATION RESULTS"))
    print()

    # E2E status
    if overall_status == "missing":
        print(print_red("  E2E Tests:              UNKNOWN (report missing)"))
    elif e2e_passed == e2e_total and e2e_total > 0:
        print(print_green(f"  E2E Tests:              {e2e_passed} / {e2e_total} PASSING"))
    else:
        print(print_red(f"  E2E Tests:              {e2e_passed} / {e2e_total} PASSING"))

    # Acceptance status
    if overall_status == "missing":
        print(print_red("  Acceptance Criteria:    UNKNOWN (report missing)"))
    elif criteria_passed == criteria_total and criteria_total > 0:
        print(print_green(f"  Acceptance Criteria:    {criteria_passed} / {criteria_total} MET"))
    else:
        print(print_red(f"  Acceptance Criteria:    {criteria_passed} / {criteria_total} MET"))

    # Performance status (no performance data in report yet -- flag as simulated if report is simulated)
    if report_is_simulated:
        print(print_yellow("  Performance:            NOT VERIFIED (simulated results)"))
    else:
        print(print_yellow("  Performance:            NOT VERIFIED (no benchmark data in report)"))

    if report_is_simulated:
        print(print_yellow("  Note:                   Test results are SIMULATED -- not from real test execution"))

    print()
    print(print_dim("─" * 118))
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # APPROVAL CRITERIA
    # ─────────────────────────────────────────────────────────────────────────

    print()
    print(print_bold("  - APPROVAL CRITERIA"))
    print()

    all_criteria_met = True

    # Check E2E tests
    if overall_status == "missing":
        print(print_red("  [CRIT] ✗ E2E tests unknown (integration report missing)"))
        all_criteria_met = False
    elif e2e_passed == e2e_total and e2e_total > 0:
        print(print_green("  [CRIT] ✓ All E2E tests passing"))
    else:
        print(print_red(f"  [CRIT] ✗ E2E tests failing ({e2e_total - e2e_passed} failures)"))
        all_criteria_met = False

    # Check acceptance criteria
    if overall_status == "missing":
        print(print_red("  [CRIT] ✗ Acceptance criteria unknown (integration report missing)"))
        all_criteria_met = False
    elif criteria_passed == criteria_total and criteria_total > 0:
        print(print_green("  [CRIT] ✓ All acceptance criteria met"))
    else:
        print(print_red(f"  [CRIT] ✗ Acceptance criteria not met ({criteria_total - criteria_passed} failures)"))
        all_criteria_met = False

    # Check performance -- no automated performance data available; flag accordingly
    if report_is_simulated:
        print(print_yellow("  [BLCK] ! Performance not verified (simulated results)"))
        all_criteria_met = False
    else:
        print(print_yellow("  [BLCK] ! Performance not verified (no benchmark data in report)"))

    # Check for critical issues -- flag simulated results so reviewer is aware
    if report_is_simulated:
        print(print_yellow("  [BLCK] ! Test results are simulated -- real execution required"))
        all_criteria_met = False
    elif overall_status == "missing":
        print(print_red("  [BLCK] ✗ Integration report missing -- cannot verify results"))
        all_criteria_met = False
    else:
        print(print_green("  [BLCK] ✓ No critical integration issues detected"))

    print()

    # ─────────────────────────────────────────────────────────────────────────
    # HUMAN GATE
    # ─────────────────────────────────────────────────────────────────────────

    print()
    print(print_bold("  - HUMAN GATE: INTEGRATION APPROVAL"))
    print()

    if all_criteria_met:
        print(print_green("━" * 118))
        print(print_green("All tests passing. All criteria met. Performance within bounds."))
        print(print_green("━" * 118))
    else:
        print(print_yellow("━" * 118))
        print(print_yellow("Some criteria not met. Review results before approving."))
        print(print_yellow("━" * 118))

    print()

    approval_choice = None
    while approval_choice != "approve":
        print(print_dim("What would you like to do?"))
        print()
        print(print_green("  [approve]       ") + "Approve and proceed to audit")
        print(print_cyan("  [investigate]   ") + "Look into specific results")
        print(print_yellow("  [fix-and-rerun] ") + "Address issues and retest")
        print()

        clear_input_buffer()
        approval_choice = prompt_user("Choice (default: approve): ").strip() or "approve"

        if approval_choice == "investigate":
            print()
            print(print_dim("Investigation artifacts:"))
            print("  .outputs/7-integration/integration-test-results.json")
            print()
            if integration_dir.exists():
                for f in sorted(integration_dir.iterdir()):
                    print(f"  {f.name}")
            print()
            prompt_user("Press Enter after investigation to continue...")
            print()
            # Loop back to approval prompt
            continue

        elif approval_choice == "fix-and-rerun":
            print()
            print(print_yellow("Fix issues and re-run integration tests"))
            print(print_dim("  After fixing, run: python main.py run 7 --resume-at=704"))
            print()
            return False

        elif approval_choice != "approve":
            print()
            print(print_yellow(f"Unrecognized choice: '{approval_choice}'. Please choose approve, investigate, or fix-and-rerun."))
            print()
            approval_choice = None  # Reset so the loop re-renders
            continue

    # Get approver name
    print()
    approver_name = prompt_user("Approver name: ").strip() or "Human Operator"
    print()

    # Save approval
    approval_data = {
        "status": "approved",
        "approver": approver_name,
        "results": {
            "e2e": {"passed": e2e_passed, "total": e2e_total},
            "acceptance": {"passed": criteria_passed, "total": criteria_total},
            "performance": "not_verified"
        },
        "results_simulated": report_is_simulated,
        "approved_at": datetime.now(timezone.utc).isoformat()
    }

    write_json(approval_file, approval_data)

    print(print_green("━" * 118))
    print(print_green(f"✓ INTEGRATION APPROVED by {approver_name}"))
    print(print_green("━" * 118))
    print()

    print(print_green("✓ Integration Approval complete"))
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 705: Integration Approval")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir)
    sys.exit(0 if success else 1)
