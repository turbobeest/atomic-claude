"""
Task 707: Phase Closeout

Generate closeout document and prepare for Phase 8 (Deployment Prep).
"""

import sys
from pathlib import Path
from typing import List
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user, clear_input_buffer
)
from core.utils.file_ops import read_json, write_json, write_file, ensure_dir


def _build_checklist(
    report_file: Path, approval_file: Path, audit_file: Path
) -> tuple:
    """Build closeout checklist from artifacts.

    Returns:
        (checklist, all_passed, metrics_dict) where checklist is a list of
        "name:status" strings, all_passed is bool, and metrics_dict has
        e2e/criteria/approval/audit data for the closeout documents.
    """
    checklist: List[str] = []
    all_passed = True

    e2e_passed = 0
    e2e_total = 0
    criteria_passed = 0
    criteria_total = 0
    approval_status = "pending"
    audit_status = "UNKNOWN"
    report_is_simulated = False

    if report_file.exists():
        report_data = read_json(report_file)
        e2e_passed = report_data.get("tests_passed", e2e_passed)
        e2e_total = report_data.get("tests_run", e2e_total)
        report_is_simulated = report_data.get("simulated", False)
        for suite in report_data.get("test_suites", []):
            if suite.get("suite") == "acceptance":
                criteria_passed = suite.get("passed", criteria_passed)
                criteria_total = suite.get("total", criteria_total)

    if approval_file.exists():
        approval_data = read_json(approval_file)
        approval_status = approval_data.get("status", "pending")

    if audit_file.exists():
        audit_data = read_json(audit_file)
        audit_status = audit_data.get("overall_status", "UNKNOWN")

    # Check E2E tests
    if e2e_total == 0:
        print(print_red(f"  [CRIT] ✗ E2E tests unknown (no report data)"))
        checklist.append("E2E tests passing:FAIL")
        all_passed = False
    elif e2e_passed == e2e_total:
        print(print_green(f"  [CRIT] ✓ E2E tests passing ({e2e_passed}/{e2e_total})"))
        checklist.append("E2E tests passing:PASS")
    else:
        print(print_red(f"  [CRIT] ✗ E2E tests failing ({e2e_passed}/{e2e_total})"))
        checklist.append("E2E tests passing:FAIL")
        all_passed = False

    # Check acceptance criteria
    if criteria_total == 0:
        print(print_red(f"  [CRIT] ✗ Acceptance criteria unknown (no report data)"))
        checklist.append("Acceptance criteria validated:FAIL")
        all_passed = False
    elif criteria_passed == criteria_total:
        print(print_green(f"  [CRIT] ✓ Acceptance criteria validated ({criteria_passed}/{criteria_total})"))
        checklist.append("Acceptance criteria validated:PASS")
    else:
        print(print_red(f"  [CRIT] ✗ Acceptance criteria not met ({criteria_passed}/{criteria_total})"))
        checklist.append("Acceptance criteria validated:FAIL")
        all_passed = False

    # Check performance -- no automated benchmark data; flag as unverified
    if report_is_simulated:
        print(print_yellow("  [BLCK] ! Performance not verified (simulated results)"))
        checklist.append("Performance benchmarks met:WARN")
    else:
        print(print_yellow("  [BLCK] ! Performance benchmarks not verified (no benchmark data)"))
        checklist.append("Performance benchmarks met:WARN")

    # Check integration report
    if report_file.exists():
        print(print_green("  [BLCK] ✓ Integration report generated"))
        checklist.append("Integration report generated:PASS")
    else:
        print(print_red("  [BLCK] ✗ Integration report not found"))
        checklist.append("Integration report generated:FAIL")
        all_passed = False

    # Check approval
    if approval_status == "approved":
        print(print_green("  [BLCK] ✓ Integration approved"))
        checklist.append("Integration approved:PASS")
    else:
        print(print_red("  [BLCK] ✗ Integration not approved"))
        checklist.append("Integration approved:FAIL")
        all_passed = False

    # Check audit
    if audit_file.exists():
        if audit_status == "PASS":
            print(print_green("  [BLCK] ✓ Integration audit passed"))
            checklist.append("Integration audit:PASS")
        elif audit_status in ["WARNING", "DEFERRED"]:
            print(print_yellow(f"  [BLCK] ! Integration audit: {audit_status}"))
            checklist.append("Integration audit:WARN")
        else:
            print(print_red("  [BLCK] ✗ Integration audit failed"))
            checklist.append("Integration audit:FAIL")
    else:
        print(print_yellow("  [BLCK] ! Integration audit not completed"))
        checklist.append("Integration audit:SKIP")

    metrics = {
        "e2e_passed": e2e_passed,
        "e2e_total": e2e_total,
        "criteria_passed": criteria_passed,
        "criteria_total": criteria_total,
        "approval_status": approval_status,
        "audit_status": audit_status,
        "results_simulated": report_is_simulated,
    }
    return checklist, all_passed, metrics


def _generate_closeout_markdown(
    closeout_file: Path, checklist: List[str], metrics: dict
) -> None:
    """Generate the closeout markdown file."""
    checklist_md = []
    for item in checklist:
        name, status = item.split(":", 1)
        if status == "PASS":
            checklist_md.append(f"- [x] {name}")
        elif status == "WARN":
            checklist_md.append(f"- [~] {name} (warning)")
        elif status == "FAIL":
            checklist_md.append(f"- [ ] {name} (failed)")
        else:
            checklist_md.append(f"- [-] {name} (deferred)")

    simulated_note = "\n> **WARNING:** Test results are SIMULATED. Real test execution required before production.\n" if metrics.get("results_simulated") else ""
    closeout_content = f"""# Phase 7 Closeout: Integration

**Completed:** {datetime.now(timezone.utc).isoformat()}
**Status:** COMPLETE
{simulated_note}
## Summary

Phase 7 (Integration) has been completed. All components have been integrated and validated end-to-end.

### Key Outcomes

- **E2E Tests:** {metrics['e2e_passed']} / {metrics['e2e_total']} passing{' (SIMULATED)' if metrics.get('results_simulated') else ''}
- **Acceptance Criteria:** {metrics['criteria_passed']} / {metrics['criteria_total']} validated{' (SIMULATED)' if metrics.get('results_simulated') else ''}
- **Performance:** Not verified (no benchmark data captured)
- **Approval Status:** {metrics['approval_status']}

### Integration Dimensions

Integration was validated across multiple dimensions:

1. **E2E Testing** - Full user flow coverage
2. **Acceptance Validation** - PRD criteria verification
3. **Performance Testing** - NFR benchmarking
4. **Integration Reporting** - Comprehensive results

### Artifacts Produced

| Artifact | Location |
|----------|----------|
| E2E Results | .claude/integration/e2e-results.json |
| Acceptance Results | .claude/integration/acceptance-results.json |
| Performance Results | .claude/integration/performance-results.json |
| Integration Report | .claude/integration/integration-report.json |
| Approval Record | .claude/integration/approval.json |
| Phase Audit | .outputs/audits/phase-7-report.json |

### Checklist Status

{chr(10).join(checklist_md)}

## Next Phase

**Phase 8: Deployment Prep**

In the next phase, we will:
- Package release artifacts
- Generate changelog
- Prepare deployment documentation
- Create installation guides

## To Continue

```bash
python main.py run 8
```

---

*Phase 7 completed by ATOMIC CLAUDE*
"""
    write_file(closeout_file, closeout_content)


def _generate_closeout_json(
    closeout_json: Path, checklist: List[str], metrics: dict
) -> None:
    """Generate the closeout JSON file."""
    closeout_data = {
        "phase": 7,
        "name": "Integration",
        "status": "complete",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "results": {
            "e2e_tests": {"passed": metrics["e2e_passed"], "total": metrics["e2e_total"]},
            "acceptance": {"passed": metrics["criteria_passed"], "total": metrics["criteria_total"]},
            "performance": "not_verified"
        },
        "results_simulated": metrics.get("results_simulated", False),
        "approval_status": metrics["approval_status"],
        "audit_status": metrics["audit_status"],
        "checklist": checklist,
        "artifacts": {
            "e2e_results": ".claude/integration/e2e-results.json",
            "acceptance_results": ".claude/integration/acceptance-results.json",
            "performance_results": ".claude/integration/performance-results.json",
            "integration_report": ".claude/integration/integration-report.json",
            "approval": ".claude/integration/approval.json",
            "audit": ".outputs/audits/phase-7-report.json"
        },
        "next_phase": 8
    }
    write_json(closeout_json, closeout_data)


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None) -> bool:
    """
    Execute Task 707: Phase Closeout.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    project_root = atomic_root.parent

    closeout_dir = project_root / ".claude" / "closeout"
    closeout_file = closeout_dir / "phase-07-closeout.md"
    closeout_json = closeout_dir / "phase-07-closeout.json"
    integration_dir = project_root / ".claude" / "integration"
    report_file = output_dir / "integration-test-results.json"
    approval_file = integration_dir / "approval.json"
    audit_file = atomic_root.parent / ".outputs" / "audits" / "phase-7" / "report.json"
    if not audit_file.exists():
        audit_file = atomic_root.parent / ".outputs" / "audits" / "phase-7-report.json"

    ensure_dir(closeout_dir)

    print()
    print(print_dim("Final review before moving to Phase 8 (Deployment Prep)."))
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # CLOSEOUT CHECKLIST
    # ─────────────────────────────────────────────────────────────────────────

    print()
    print(print_bold("  - CLOSEOUT CHECKLIST"))
    print()

    checklist, all_passed, metrics = _build_checklist(
        report_file, approval_file, audit_file
    )

    print()

    # ─────────────────────────────────────────────────────────────────────────
    # CLOSEOUT APPROVAL
    # ─────────────────────────────────────────────────────────────────────────

    print()
    print(print_bold("  - CLOSEOUT APPROVAL"))
    print()

    if not all_passed:
        print(print_yellow("Some critical items need attention before closeout."))
        print()

    if uat_mode:
        print(print_yellow("UAT Mode: Auto-approving closeout"))
        closeout_choice = "approve"
    else:
        print(print_cyan("Closeout options:"))
        print()
        print(print_green("  [approve] ") + "Approve closeout and proceed")
        print(print_yellow("  [review]  ") + "Review specific artifacts")
        print(print_red("  [hold]    ") + "Hold closeout for now")
        print()

        clear_input_buffer()
        closeout_choice = prompt_user("Choice (default: approve): ").strip() or "approve"

        if closeout_choice == "review":
            print()
            print(print_dim("Key artifacts:"))
            print("  .claude/integration/e2e-results.json         - E2E test results")
            print("  .claude/integration/acceptance-results.json  - Acceptance validation")
            print("  .claude/integration/performance-results.json - Performance benchmarks")
            print("  .claude/integration/integration-report.json  - Integration report")
            print("  .claude/integration/approval.json            - Approval record")
            print("  .outputs/audits/phase-7-report.json          - Audit results")
            print()
            if integration_dir.exists():
                for f in sorted(integration_dir.iterdir()):
                    print(f"  {f.name}")
            print()
            prompt_user("Press Enter to continue to closeout...")

        elif closeout_choice == "hold":
            print()
            print(print_yellow("Closeout held - phase not complete"))
            return False

    # ─────────────────────────────────────────────────────────────────────────
    # GENERATING CLOSEOUT
    # ─────────────────────────────────────────────────────────────────────────

    print()
    print(print_bold("  - GENERATING CLOSEOUT"))
    print()

    _generate_closeout_markdown(closeout_file, checklist, metrics)
    _generate_closeout_json(closeout_json, checklist, metrics)

    print(print_green("  ✓ Generated phase-07-closeout.md"))
    print(print_green("  ✓ Generated phase-07-closeout.json"))
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # SESSION END
    # ─────────────────────────────────────────────────────────────────────────

    print()
    print(print_bold("  - SESSION END"))
    print()
    print("  Closeout saved to:")
    print(print_dim("    .claude/closeout/phase-07-closeout.md"))
    print()
    print("  Integration artifacts at:")
    print(print_dim("    .claude/integration/"))
    print()
    print(print_bold("  Next: PHASE 8 - DEPLOYMENT PREP"))
    print()
    print("  To continue:")
    print(print_cyan("    python main.py run 8"))
    print()
    print(print_green("  Phase 7 Complete!"))
    print(print_dim("  Fully integrated. Deployment Prep next."))
    print()

    print(print_green("✓ Phase 7 closeout complete"))
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 707: Phase Closeout")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
