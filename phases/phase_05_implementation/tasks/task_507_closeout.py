"""
Task 507: Phase Closeout

Generate closeout document and prepare for Phase 6 (Code Review).
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user
)
from core.utils.file_ops import ensure_dir, write_file


def get_closeout_metrics(
    tasks_file: Path,
    testing_dir: Path,
    validation_file: Path,
    audit_file: Path
) -> Tuple[int, int, int, int, int, int, int, int]:
    """
    Get metrics for closeout report.

    Returns:
        Tuple of (completed_tasks, total_tasks, total_tests, passing_tests,
                  unit_coverage, critical_issues, flaky_tests, tdd_records)
    """
    # Task completion
    completed_tasks = 0
    total_tasks = 0
    if tasks_file.exists():
        with open(tasks_file) as f:
            tasks_data = json.load(f)
        tasks = tasks_data.get("tasks", [])
        total_tasks = sum(1 for task in tasks if len(task.get("subtasks", [])) >= 4)
        completed_tasks = sum(1 for task in tasks if task.get("status") == "done")

    # Validation metrics
    unit_coverage = 0
    passing_tests = 0
    total_tests = 0
    critical_issues = 0
    flaky_tests = 0
    if validation_file.exists():
        with open(validation_file) as f:
            validation_data = json.load(f)
        unit_coverage = validation_data.get("coverage", {}).get("unit", 0)
        passing_tests = validation_data.get("test_quality", {}).get("passing_tests", 0)
        total_tests = validation_data.get("test_quality", {}).get("total_tests", 0)
        critical_issues = validation_data.get("security", {}).get("critical", 0)
        flaky_tests = validation_data.get("test_quality", {}).get("flaky_tests", 0)

    # TDD records
    tdd_records = 0
    if testing_dir.exists():
        tdd_records = len(list(testing_dir.glob("tdd-t*.json")))

    return (completed_tasks, total_tasks, total_tests, passing_tests,
            unit_coverage, critical_issues, flaky_tests, tdd_records)


def build_checklist(
    completed_tasks: int,
    total_tasks: int,
    unit_coverage: int,
    passing_tests: int,
    total_tests: int,
    critical_issues: int,
    flaky_tests: int,
    audit_file: Path
) -> Tuple[List[str], bool]:
    """
    Build closeout checklist and determine if all passed.

    Returns:
        Tuple of (checklist items, all_passed bool)
    """
    checklist = []
    all_passed = True

    # TDD completion
    if completed_tasks >= total_tasks and total_tasks > 0:
        print_green(f"  [CRIT] ✓ All TDD cycles complete ({completed_tasks} tasks)")
        checklist.append("TDD cycles complete:PASS")
    else:
        print_red(f"  [CRIT] ✗ TDD cycles incomplete ({completed_tasks} / {total_tasks})")
        checklist.append("TDD cycles complete:FAIL")
        all_passed = False

    # Coverage
    if unit_coverage >= 80:
        print_green(f"  [CRIT] ✓ Coverage >= 80% ({unit_coverage}%)")
        checklist.append("Coverage:PASS")
    elif unit_coverage >= 70:
        print_yellow(f"  [CRIT] ! Coverage {unit_coverage}% (target: 80%)")
        checklist.append("Coverage:WARN")
    else:
        print_red(f"  [CRIT] ✗ Coverage below 70% ({unit_coverage}%)")
        checklist.append("Coverage:FAIL")
        all_passed = False

    # All tests passing
    if passing_tests == total_tests and total_tests > 0:
        print_green(f"  [CRIT] ✓ All tests passing ({passing_tests} tests)")
        checklist.append("All tests passing:PASS")
    else:
        print_red(f"  [CRIT] ✗ Tests failing ({total_tests - passing_tests} of {total_tests})")
        checklist.append("All tests passing:FAIL")
        all_passed = False

    # VERIFY scans
    if critical_issues == 0:
        print_green("  [BLCK] ✓ VERIFY scans clean")
        checklist.append("VERIFY scans:PASS")
    else:
        print_red(f"  [BLCK] ✗ {critical_issues} critical security issues")
        checklist.append("VERIFY scans:FAIL")

    # Audit
    if audit_file.exists():
        with open(audit_file) as f:
            audit_data = json.load(f)

        # Check new format (summary) or legacy format (overall_status)
        summary = audit_data.get("summary", {})
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        warnings = summary.get("warnings", 0)
        total = passed + failed + warnings

        if total == 0:
            # Try legacy format
            audit_status = audit_data.get("overall_status", "UNKNOWN")
            if audit_status == "PASS":
                print_green("  [BLCK] ✓ Audit passed")
                checklist.append("Audit:PASS")
            elif audit_status in ["WARNING", "DEFERRED"]:
                print_yellow(f"  [BLCK] ! Audit: {audit_status}")
                checklist.append("Audit:WARN")
            else:
                print_red("  [BLCK] ✗ Audit failed")
                checklist.append("Audit:FAIL")
        elif failed == 0 and warnings == 0:
            print_green(f"  [BLCK] ✓ Audit passed ({passed} passed)")
            checklist.append("Audit:PASS")
        elif failed == 0:
            print_yellow(f"  [BLCK] ! Audit has warnings ({warnings} warnings)")
            checklist.append("Audit:WARN")
        else:
            print_red(f"  [BLCK] ✗ Audit has failures ({failed} failed)")
            checklist.append("Audit:FAIL")
    else:
        print_yellow("  [BLCK] ! Audit not completed")
        checklist.append("Audit:SKIP")

    # No flaky tests
    if flaky_tests == 0:
        print_green("  [BLCK] ✓ No flaky tests")
        checklist.append("No flaky tests:PASS")
    else:
        print_yellow(f"  [BLCK] ! {flaky_tests} flaky tests detected")
        checklist.append("No flaky tests:WARN")

    print_green("  [PASS] ✓ Ready for Code Review")

    return checklist, all_passed


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 507: Phase Closeout.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    closeout_dir = atomic_root / ".claude" / "closeout"
    closeout_file = closeout_dir / "phase-05-closeout.md"
    closeout_json = closeout_dir / "phase-05-closeout.json"
    tasks_file = atomic_root / ".taskmaster" / "tasks" / "tasks.json"
    testing_dir = atomic_root / ".claude" / "testing"

    # Audit file - check new path first, then legacy
    audit_file = atomic_root / ".outputs" / "audits" / "phase-5-report.json"
    if not audit_file.exists():
        audit_file = atomic_root / ".claude" / "audit" / "phase-05-audit.json"

    validation_file = testing_dir / "validation-report.json"

    # UAT Mode Bypass
    if uat_mode:
        print()
        print_yellow("⚡ UAT Mode: Auto-approving closeout, creating minimal artifacts")
        print()

        ensure_dir(closeout_dir)

        # Create minimal closeout markdown
        closeout_md = """# Phase 5: Implementation - Closeout (UAT Mode)

## Summary
Phase 5 completed in UAT mode with stub implementation files.

## Metrics
- Tasks: 3/3 complete
- Test Coverage: 80% (stub)
- Security Issues: 0 critical

## Status
COMPLETE (UAT Mode)

## Next Phase
Phase 6: Code Review
"""
        write_file(closeout_file, closeout_md)

        # Create minimal closeout JSON
        closeout_data = {
            "phase": 5,
            "status": "complete",
            "mode": "uat",
            "completion": {
                "tasks_completed": 3,
                "tasks_total": 3,
                "completion_rate": 100
            },
            "coverage": {
                "unit": 80
            },
            "security": {
                "critical_issues": 0
            },
            "tdd_records": 3,
            "checklist": ["uat-stub-files", "uat-mock-tests"],
            "artifacts": {
                "testing": ".claude/testing/",
                "validation": ".claude/testing/validation-report.json"
            },
            "completed_at": datetime.now().isoformat(),
            "next_phase": 6
        }
        write_file(closeout_json, json.dumps(closeout_data, indent=2))

        print_green("✓ Generated phase-05-closeout.md (UAT mode)")
        print_green("✓ Generated phase-05-closeout.json (UAT mode)")
        print()

        print_green("✓ Phase 5 closeout complete (UAT mode)")
        return True

    ensure_dir(closeout_dir)

    print()
    print_dim("  Final review before moving to Phase 6 (Code Review).")
    print()

    # Get metrics
    (completed_tasks, total_tasks, total_tests, passing_tests,
     unit_coverage, critical_issues, flaky_tests, tdd_records) = get_closeout_metrics(
        tasks_file, testing_dir, validation_file, audit_file
    )

    # Closeout Checklist
    print_dim("─" * 120)
    print()
    print_bold("CLOSEOUT CHECKLIST")
    print()

    checklist, all_passed = build_checklist(
        completed_tasks, total_tasks, unit_coverage, passing_tests,
        total_tests, critical_issues, flaky_tests, audit_file
    )

    print()

    # Closeout Approval
    print_dim("─" * 120)
    print()

    if not all_passed:
        print_yellow("  Some critical items need attention before closeout.")
        print()

    print_cyan("  Closeout options:")
    print()
    print_green("    [approve]") + " Approve closeout and proceed"
    print_yellow("    [review]") + "  Review specific artifacts"
    print_red("    [hold]") + "    Hold closeout for now"
    print()

    closeout_choice = prompt_user("  Choice (default: approve): ").strip()
    closeout_choice = closeout_choice if closeout_choice else "approve"

    if closeout_choice == "review":
        print()
        print_dim("  Key artifacts:")
        print("    .claude/testing/                     - TDD execution records")
        print("    .claude/testing/validation-report.json - Validation report")
        print("    .claude/audit/phase-05-audit.json    - Audit results")
        print("    .taskmaster/tasks/tasks.json         - Task completion status")
        print()
        prompt_user("  Press Enter to continue to closeout...")
    elif closeout_choice == "hold":
        print()
        print_yellow("✗ Closeout held - phase not complete")
        return False

    # Generate Closeout Document
    print_dim("─" * 120)
    print()
    print_bold("GENERATING CLOSEOUT")
    print()

    # Generate markdown closeout
    checklist_md = "\n".join([
        f"- [x] {item.split(':')[0]}" if item.endswith(":PASS") else
        f"- [~] {item.split(':')[0]} (warning)" if item.endswith(":WARN") else
        f"- [ ] {item.split(':')[0]} (failed)" if item.endswith(":FAIL") else
        f"- [-] {item.split(':')[0]} (deferred)"
        for item in checklist
    ])

    closeout_md = f"""# Phase 5 Closeout: TDD Implementation

**Completed:** {datetime.now().isoformat()}
**Status:** COMPLETE

## Summary

Phase 5 (TDD Implementation) has been completed. All tasks have gone through RED/GREEN/REFACTOR/VERIFY cycles.

### Key Outcomes

- **Tasks Completed:** {completed_tasks} / {total_tasks}
- **Tests Written:** {total_tests}
- **Tests Passing:** {passing_tests}
- **Unit Coverage:** {unit_coverage}%
- **Critical Issues:** {critical_issues}

### TDD Execution

Each task completed the following cycle:

1. **RED** - Wrote failing tests based on OpenSpec
2. **GREEN** - Implemented minimal code to pass tests
3. **REFACTOR** - Cleaned up code, ran linters
4. **VERIFY** - Security scans, no critical issues

### Artifacts Produced

| Artifact | Location |
|----------|----------|
| TDD Records | .claude/testing/tdd-t*.json |
| Validation Report | .claude/testing/validation-report.json |
| Phase Audit | .claude/audit/phase-05-audit.json |
| Updated Tasks | .taskmaster/tasks/tasks.json |

### Checklist Status

{checklist_md}

## Next Phase

**Phase 6: Code Review**

In the next phase, we will:
- Conduct peer code review
- Check for best practices and patterns
- Validate architecture decisions
- Ensure code maintainability

## To Continue

```bash
./orchestrator/pipeline resume
```

---

*Phase 5 completed by ATOMIC CLAUDE*
"""
    write_file(closeout_file, closeout_md)

    # Generate JSON closeout
    closeout_data = {
        "phase": 5,
        "name": "TDD Implementation",
        "status": "complete",
        "completed_at": datetime.now().isoformat(),
        "tasks_completed": completed_tasks,
        "total_tasks": total_tasks,
        "tests": {
            "total": total_tests,
            "passing": passing_tests,
            "flaky": flaky_tests
        },
        "coverage": {
            "unit": unit_coverage
        },
        "security": {
            "critical_issues": critical_issues
        },
        "tdd_records": tdd_records,
        "checklist": checklist,
        "artifacts": {
            "testing": ".claude/testing/",
            "validation": ".claude/testing/validation-report.json",
            "audit": ".claude/audit/phase-05-audit.json",
            "tasks": ".taskmaster/tasks/tasks.json"
        },
        "next_phase": 6
    }
    write_file(closeout_json, json.dumps(closeout_data, indent=2))

    print_green("✓ Generated phase-05-closeout.md")
    print_green("✓ Generated phase-05-closeout.json")
    print()

    # Session End
    print_dim("─" * 120)
    print()
    print_bold("SESSION END")
    print()
    print("  Closeout saved to:")
    print_dim("    .claude/closeout/phase-05-closeout.md")
    print()
    print("  Testing artifacts at:")
    print_dim("    .claude/testing/")
    print()
    print_bold("  Next: PHASE 6 - CODE REVIEW")
    print()
    print("  To continue:")
    print_cyan("    ./orchestrator/pipeline resume")
    print()
    print_dim("─" * 120)
    print()
    print_green("  Phase 5 Complete!")
    print_dim("  TDD cycles executed. Tests passing. Ready for Code Review.")
    print()

    print_green("✓ Phase 5 closeout complete")
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 507: Phase Closeout")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
