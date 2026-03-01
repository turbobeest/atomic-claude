"""
Task 507: Phase Closeout

Generate closeout document and prepare for Phase 6 (Code Review).
Reads real metrics from validation-report.json and tdd-progress.json.
"""

import logging
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user
)
from core.utils.file_ops import ensure_dir, write_file


def _load_json(path: Path) -> Dict[str, Any]:
    """Load JSON file, returning empty dict on failure."""
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception as e:
        logger.debug("Failed to load JSON from %s: %s", path, e)
    return {}


def get_closeout_metrics(
    testing_dir: Path,
    validation_file: Path,
    progress_file: Path,
    audit_file: Path,
    state_dir: Path,
) -> Dict[str, Any]:
    """
    Get metrics for closeout report from real artifacts.

    Reads from:
      - validation-report.json (produced by task 505)
      - tdd-progress.json (produced by task 504)
      - session-tokens.json (LLM token tracking)

    NOTE: Metrics come from two sources — tdd-progress.json (task 504's live
    counters) and validation-report.json (task 505's aggregated analysis).
    Some fields (e.g. tasks_completed, cycle counts) may appear in both;
    tdd-progress.json is the primary source, with validation as fallback.
    """
    validation = _load_json(validation_file)
    progress = _load_json(progress_file)

    # TDD completion from progress file
    tasks_completed = progress.get("tasks_completed", 0)
    tasks_total = progress.get("tasks_total", 0)
    tasks_failed = progress.get("tasks_failed", 0)
    tasks_cascaded = progress.get("tasks_cascaded", 0)

    # Cycle counts from progress
    red_cycles = progress.get("red_cycles", 0)
    green_cycles = progress.get("green_cycles", 0)
    refactor_cycles = progress.get("refactor_cycles", 0)
    verify_cycles = progress.get("verify_cycles", 0)

    # Test suite results from validation
    test_suite = validation.get("test_suite")
    tests_passed = 0
    tests_failed_suite = 0
    total_tests = 0
    if isinstance(test_suite, dict):
        tests_passed = test_suite.get("tests_passed", 0)
        tests_failed_suite = test_suite.get("tests_failed", 0)
        total_tests = tests_passed + tests_failed_suite + test_suite.get("tests_errors", 0)

    # Coverage from validation
    coverage_data = validation.get("coverage")
    unit_coverage = 0
    if isinstance(coverage_data, dict):
        unit_coverage = coverage_data.get("line_coverage_pct", 0)

    # Security from validation
    security = validation.get("security", {})
    critical_issues = security.get("critical", 0)
    security_warnings = security.get("warnings_from_verify", 0)

    # TDD cycles detail from validation
    tdd_cycles = validation.get("tdd_cycles", {})
    green_retries = tdd_cycles.get("green_retries", 0)
    refactor_reverted = tdd_cycles.get("refactor_reverted", 0)

    # TDD record count
    tdd_records = 0
    if testing_dir.exists():
        tdd_records = len(list(testing_dir.glob("tdd-t*.json")))

    # Token spend
    token_spend = 0.0
    tokens_file = state_dir / "session-tokens.json"
    token_data = _load_json(tokens_file)
    if token_data:
        token_spend = token_data.get("estimated_cost_usd", 0.0)

    # Validation passed?
    validation_passed = validation.get("validation_passed", False)

    # Stack info from validation metrics
    stack = validation.get("metrics", {}).get("stack", "unknown")

    return {
        "tasks_completed": tasks_completed,
        "tasks_total": tasks_total,
        "tasks_failed": tasks_failed,
        "tasks_cascaded": tasks_cascaded,
        "total_tests": total_tests,
        "tests_passed": tests_passed,
        "tests_failed_suite": tests_failed_suite,
        "unit_coverage": unit_coverage,
        "critical_issues": critical_issues,
        "security_warnings": security_warnings,
        "green_retries": green_retries,
        "refactor_reverted": refactor_reverted,
        "tdd_records": tdd_records,
        "red_cycles": red_cycles,
        "green_cycles": green_cycles,
        "refactor_cycles": refactor_cycles,
        "verify_cycles": verify_cycles,
        "token_spend": token_spend,
        "validation_passed": validation_passed,
        "stack": stack,
    }


def build_checklist(
    m: Dict[str, Any],
    audit_file: Path,
    output_dir: Path = None,
) -> Tuple[List[str], bool]:
    """
    Build closeout checklist from real metrics.

    NOTE: This function intentionally mixes logic (pass/fail evaluation) with
    presentation (printing colored status lines) because the checklist items
    and their display are tightly coupled.  A future refactor could separate
    them, but the current approach keeps the checklist rendering self-contained.

    Args:
        m: Metrics dict from get_closeout_metrics()
        audit_file: Path to audit report JSON
        output_dir: Phase output directory (used to read tdd-setup.json for coverage target)

    Returns:
        Tuple of (checklist items, all_passed bool)
    """
    checklist = []
    all_passed = True

    # Read configured coverage target from tdd-setup.json (default 80%)
    coverage_target = 80
    if output_dir:
        setup_data = _load_json(output_dir / "tdd-setup.json")
        configured = setup_data.get("coverage_targets", {}).get("unit")
        if isinstance(configured, (int, float)) and configured > 0:
            coverage_target = configured

    # TDD completion
    if m["tasks_completed"] >= m["tasks_total"] and m["tasks_total"] > 0:
        print(print_green(f"  [CRIT] + All TDD cycles complete ({m['tasks_completed']} tasks)"))
        checklist.append("TDD cycles complete:PASS")
    elif m["tasks_completed"] > 0:
        pct = m["tasks_completed"] * 100 // max(m["tasks_total"], 1)
        print(print_yellow(f"  [CRIT] ~ TDD cycles: {pct}% ({m['tasks_completed']} / {m['tasks_total']})"))
        checklist.append("TDD cycles:WARN")
    else:
        print(print_red(f"  [CRIT] X TDD cycles incomplete ({m['tasks_completed']} / {m['tasks_total']})"))
        checklist.append("TDD cycles complete:FAIL")
        all_passed = False

    # Test suite results
    if m["total_tests"] > 0:
        if m["tests_failed_suite"] == 0:
            print(print_green(f"  [CRIT] + All tests passing ({m['tests_passed']} tests)"))
            checklist.append("All tests passing:PASS")
        else:
            print(print_red(f"  [CRIT] X {m['tests_failed_suite']} tests failing out of {m['total_tests']}"))
            checklist.append("All tests passing:FAIL")
            all_passed = False
    else:
        print(print_dim("  [INFO] - Test suite: not available (no build tools)"))
        checklist.append("Test suite:SKIP")

    # Coverage
    coverage_warn = max(coverage_target - 10, 0)
    if m["unit_coverage"] > 0:
        if m["unit_coverage"] >= coverage_target:
            print(print_green(f"  [CRIT] + Coverage >= {coverage_target}% ({m['unit_coverage']}%)"))
            checklist.append("Coverage:PASS")
        elif m["unit_coverage"] >= coverage_warn:
            print(print_yellow(f"  [CRIT] ~ Coverage {m['unit_coverage']}% (target: {coverage_target}%)"))
            checklist.append("Coverage:WARN")
        else:
            print(print_red(f"  [CRIT] X Coverage below {coverage_warn}% ({m['unit_coverage']}%)"))
            checklist.append("Coverage:FAIL")
            all_passed = False
    else:
        print(print_dim("  [INFO] - Coverage: not available"))
        checklist.append("Coverage:SKIP")

    # VERIFY scans
    if m["critical_issues"] == 0:
        print(print_green("  [BLCK] + VERIFY scans clean"))
        checklist.append("VERIFY scans:PASS")
    else:
        print(print_red(f"  [BLCK] X {m['critical_issues']} critical security issues"))
        checklist.append("VERIFY scans:FAIL")
        all_passed = False

    # Audit
    if audit_file.exists():
        audit_data = _load_json(audit_file)

        summary = audit_data.get("summary", {})
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        warnings = summary.get("warnings", 0)
        total = passed + failed + warnings

        if total == 0:
            audit_status = audit_data.get("overall_status", "UNKNOWN")
            if audit_status == "PASS":
                print(print_green("  [BLCK] + Audit passed"))
                checklist.append("Audit:PASS")
            elif audit_status in ("WARNING", "DEFERRED"):
                print(print_yellow(f"  [BLCK] ~ Audit: {audit_status}"))
                checklist.append("Audit:WARN")
            else:
                print(print_red("  [BLCK] X Audit failed"))
                checklist.append("Audit:FAIL")
        elif failed == 0 and warnings == 0:
            print(print_green(f"  [BLCK] + Audit passed ({passed} passed)"))
            checklist.append("Audit:PASS")
        elif failed == 0:
            print(print_yellow(f"  [BLCK] ~ Audit has warnings ({warnings} warnings)"))
            checklist.append("Audit:WARN")
        else:
            print(print_red(f"  [BLCK] X Audit has failures ({failed} failed)"))
            checklist.append("Audit:FAIL")
    else:
        print(print_yellow("  [BLCK] ~ Audit not completed"))
        checklist.append("Audit:SKIP")

    # Quality indicators
    if m["green_retries"] > 0:
        print(print_dim(f"  [INFO] - GREEN retries: {m['green_retries']}"))
    if m["refactor_reverted"] > 0:
        print(print_dim(f"  [INFO] - REFACTOR reverted: {m['refactor_reverted']}"))

    if all_passed:
        print(print_green("  [PASS] + Ready for Code Review"))
    else:
        print(print_red("  [HOLD] X Issues detected — review before proceeding"))

    return checklist, all_passed


def execute(atomic_root: Path, output_dir: Path, mem=None) -> bool:
    """
    Execute Task 507: Phase Closeout.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory

    Returns:
        True if task completed successfully, False otherwise
    """
    project_root = atomic_root.parent
    closeout_dir = project_root / ".claude" / "closeout"
    closeout_file = closeout_dir / "phase-05-closeout.md"
    closeout_json = closeout_dir / "phase-05-closeout.json"
    testing_dir = project_root / ".claude" / "testing"

    # Audit file - check new path first, then legacy
    audit_file = atomic_root.parent / ".outputs" / "audits" / "phase-5" / "report.json"
    if not audit_file.exists():
        audit_file = atomic_root.parent / ".outputs" / "audits" / "phase-5-report.json"
    if not audit_file.exists():
        audit_file = project_root / ".claude" / "audit" / "phase-05-audit.json"

    validation_file = testing_dir / "validation-report.json"
    progress_file = output_dir / "tdd-progress.json"
    state_dir = atomic_root / ".state"

    ensure_dir(closeout_dir)

    print()
    print(print_dim("  Final review before moving to Phase 6 (Code Review)."))
    print()

    # Get real metrics
    m = get_closeout_metrics(
        testing_dir, validation_file, progress_file, audit_file, state_dir,
    )

    # Closeout Checklist
    print(print_dim("─" * 120))
    print()
    print(print_bold("CLOSEOUT CHECKLIST"))
    print()

    checklist, all_passed = build_checklist(m, audit_file, output_dir=output_dir)

    print()

    # Token Spend Summary
    if m["token_spend"] > 0:
        print(print_dim("─" * 120))
        print()
        print(print_bold("TOKEN SPEND"))
        print()
        print(f"    Estimated cost:     ${m['token_spend']:.2f}")
        print(f"    TDD cycles run:     {m['red_cycles'] + m['green_cycles'] + m['refactor_cycles'] + m['verify_cycles']}")
        print()

    # Closeout Approval
    print(print_dim("─" * 120))
    print()

    if not all_passed:
        print(print_yellow("  Some critical items need attention before closeout."))
        print()

    print(print_cyan("  Closeout options:"))
    print()
    print(print_green("    [approve]") + " Approve closeout and proceed")
    print(print_yellow("    [review]") + "  Review specific artifacts")
    print(print_red("    [hold]") + "    Hold closeout for now")
    print()

    closeout_choice = prompt_user("  Choice (default: approve): ").strip()
    closeout_choice = closeout_choice if closeout_choice else "approve"

    if closeout_choice == "review":
        print()
        print(print_dim("  Key artifacts:"))
        print("    .claude/testing/                     - TDD execution records")
        print("    .claude/testing/validation-report.json - Validation report")
        print("    .claude/audit/phase-05-audit.json    - Audit results")
        print("    .taskmaster/tasks/tasks.json         - Task completion status")
        print()
        prompt_user("  Press Enter to continue to closeout...")
    elif closeout_choice == "hold":
        print()
        print(print_yellow("  Closeout held - phase not complete"))
        return False

    # Generate Closeout Document
    print(print_dim("─" * 120))
    print()
    print(print_bold("GENERATING CLOSEOUT"))
    print()

    completion_rate = (m["tasks_completed"] * 100 // max(m["tasks_total"], 1)) if m["tasks_total"] > 0 else 0

    checklist_md = "\n".join([
        f"- [x] {item.split(':')[0]}" if item.endswith(":PASS") else
        f"- [~] {item.split(':')[0]} (warning)" if item.endswith(":WARN") else
        f"- [ ] {item.split(':')[0]} (failed)" if item.endswith(":FAIL") else
        f"- [-] {item.split(':')[0]} (skipped)"
        for item in checklist
    ])

    # Test suite info
    test_info = "Not available (build tools not installed)"
    if m["total_tests"] > 0:
        test_info = f"{m['tests_passed']} passing, {m['tests_failed_suite']} failing (of {m['total_tests']})"

    coverage_info = "Not available (coverage tool not installed)"
    if m["unit_coverage"] > 0:
        coverage_info = f"{m['unit_coverage']}%"

    token_section = ""
    if m["token_spend"] > 0:
        token_section = f"""
### Token Spend

- **Estimated Cost:** ${m['token_spend']:.2f}
- **Total Cycles:** {m['red_cycles'] + m['green_cycles'] + m['refactor_cycles'] + m['verify_cycles']}
"""

    closeout_md = f"""# Phase 5 Closeout: TDD Implementation

**Completed:** {datetime.now(timezone.utc).isoformat()}
**Status:** COMPLETE
**Stack:** {m['stack']}

## Summary

Phase 5 (TDD Implementation) has been completed. Tasks went through RED/GREEN/REFACTOR/VERIFY cycles.

### Key Outcomes

- **Tasks Completed:** {m['tasks_completed']} / {m['tasks_total']} ({completion_rate}%)
- **Tasks Failed:** {m['tasks_failed']}
- **Tasks Cascaded:** {m['tasks_cascaded']}
- **Test Suite:** {test_info}
- **Coverage:** {coverage_info}
- **Critical Issues:** {m['critical_issues']}

### TDD Execution

| Cycle | Count |
|-------|-------|
| RED | {m['red_cycles']} |
| GREEN | {m['green_cycles']} (retries: {m['green_retries']}) |
| REFACTOR | {m['refactor_cycles']} (reverted: {m['refactor_reverted']}) |
| VERIFY | {m['verify_cycles']} |
{token_section}
### Artifacts Produced

| Artifact | Location |
|----------|----------|
| TDD Records | .claude/testing/tdd-t*.json ({m['tdd_records']} files) |
| Validation Report | .claude/testing/validation-report.json |
| TDD Progress | .outputs/5-implementation/tdd-progress.json |
| Phase Audit | .claude/audit/phase-05-audit.json |

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
python main.py run 6
```

---

*Phase 5 completed by ATOMIC CLAUDE*
"""
    write_file(closeout_file, closeout_md)

    closeout_data = {
        "phase": 5,
        "name": "TDD Implementation",
        "status": "complete",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "stack": m["stack"],
        "tasks_completed": m["tasks_completed"],
        "total_tasks": m["tasks_total"],
        "tasks_failed": m["tasks_failed"],
        "tasks_cascaded": m["tasks_cascaded"],
        "tests": {
            "total": m["total_tests"],
            "passing": m["tests_passed"],
            "failing": m["tests_failed_suite"],
        },
        "coverage": {
            "unit": m["unit_coverage"],
        },
        "security": {
            "critical_issues": m["critical_issues"],
            "verify_warnings": m["security_warnings"],
        },
        "tdd_cycles": {
            "red": m["red_cycles"],
            "green": m["green_cycles"],
            "green_retries": m["green_retries"],
            "refactor": m["refactor_cycles"],
            "refactor_reverted": m["refactor_reverted"],
            "verify": m["verify_cycles"],
        },
        "token_spend_usd": m["token_spend"],
        "tdd_records": m["tdd_records"],
        "validation_passed": m["validation_passed"],
        "checklist": checklist,
        "artifacts": {
            "testing": ".claude/testing/",
            "validation": ".claude/testing/validation-report.json",
            "progress": ".outputs/5-implementation/tdd-progress.json",
        },
        "next_phase": 6
    }
    write_file(closeout_json, json.dumps(closeout_data, indent=2))

    print(print_green("  Generated phase-05-closeout.md"))
    print(print_green("  Generated phase-05-closeout.json"))
    print()

    # Session End
    print(print_dim("─" * 120))
    print()
    print(print_bold("SESSION END"))
    print()
    print("  Closeout saved to:")
    print(print_dim("    .claude/closeout/phase-05-closeout.md"))
    print()
    print("  Testing artifacts at:")
    print(print_dim("    .claude/testing/"))
    print()

    if m["token_spend"] > 0:
        print(f"  Token spend: ${m['token_spend']:.2f}")
        print()

    print(print_bold("  Next: PHASE 6 - CODE REVIEW"))
    print()
    print("  To continue:")
    print(print_cyan("    python main.py run 6"))
    print()
    print(print_dim("─" * 120))
    print()
    print(print_green("  Phase 5 Complete!"))
    print(print_dim("  TDD cycles executed. Ready for Code Review."))
    print()

    print(print_green("  Phase 5 closeout complete"))
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 507: Phase Closeout")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir)
    sys.exit(0 if success else 1)
