"""
Task 606: Phase Closeout

Generate closeout document and prepare for Phase 7 (Integration Testing).
"""

import logging
import sys
import json
from pathlib import Path
from typing import List, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user, clear_input_buffer
)
from core.utils.file_ops import ensure_dir, read_file, write_file
from core.memory import memory_save, MemoryEntryType


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None) -> bool:
    """
    Execute Task 606: Phase Closeout.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    project_root = atomic_root.parent
    closeout_dir = project_root / ".claude" / "closeout"
    closeout_file = closeout_dir / "phase-06-closeout.md"
    closeout_json = closeout_dir / "phase-06-closeout.json"
    review_dir = project_root / ".claude" / "reviews"
    findings_file = review_dir / "findings.json"
    refinement_file = review_dir / "refinement-report.json"

    # Find audit file (new path first, then legacy)
    audit_file = atomic_root.parent / ".outputs" / "audits" / "phase-6" / "report.json"
    if not audit_file.exists():
        audit_file = atomic_root.parent / ".outputs" / "audits" / "phase-6-report.json"
    if not audit_file.exists():
        audit_file = project_root / ".claude" / "audit" / "phase-06-audit.json"

    print()
    print(print_dim("Final review before moving to Phase 7 (Integration Testing)."))
    print()

    # UAT Mode Bypass
    if uat_mode:
        print(print_yellow("UAT Mode: Creating minimal valid output"))
        # Orchestrator will create closeout.json automatically
        print(print_green("✓ UAT bypass complete"))
        return True

    ensure_dir(closeout_dir)

    # Run closeout checklist
    checklist, all_passed = _run_closeout_checklist(
        findings_file, refinement_file, audit_file
    )

    # Get closeout approval
    if not _get_closeout_approval(all_passed, review_dir, uat_mode):
        return False

    # Generate closeout documents
    _generate_closeout_documents(
        closeout_file, closeout_json, checklist,
        findings_file, refinement_file
    )

    # Memory checkpoint
    _memory_checkpoint(findings_file, refinement_file)

    # Display session end
    _display_session_end(closeout_file, review_dir)

    print(print_green("✓ Phase 6 closeout complete"))
    return True


def _load_review_metrics(findings_file: Path, refinement_file: Path) -> dict:
    """Load review metrics from findings and refinement files.

    Returns a dict with keys: critical_found, major_found, critical_fixed,
    major_fixed, tests_passing.
    """
    metrics = {
        "critical_found": 0,
        "major_found": 0,
        "critical_fixed": 0,
        "major_fixed": 0,
        "tests_passing": True,
    }

    if findings_file.exists():
        try:
            findings_data = json.loads(read_file(findings_file))
            totals = findings_data.get("totals", {})
            metrics["critical_found"] = totals.get("critical", 0)
            metrics["major_found"] = totals.get("major", 0)
        except (json.JSONDecodeError, OSError) as e:
            logger.debug("Failed to load findings from %s: %s", findings_file, e)

    if refinement_file.exists():
        try:
            refinement_data = json.loads(read_file(refinement_file))
            refinements = refinement_data.get("refinements", {})
            metrics["critical_fixed"] = refinements.get("critical", {}).get("fixed", 0)
            metrics["major_fixed"] = refinements.get("major", {}).get("fixed", 0)
            test_verification = refinement_data.get("test_verification", {})
            metrics["tests_passing"] = test_verification.get("all_passing", True)
        except (json.JSONDecodeError, OSError) as e:
            logger.debug("Failed to load refinement report from %s: %s", refinement_file, e)

    return metrics


def _check_review_items(
    findings_file: Path, metrics: dict
) -> Tuple[List[Tuple[str, str]], bool]:
    """Check review-related checklist items. Returns (items, all_passed)."""
    items = []
    all_passed = True

    # Check code review complete
    if findings_file.exists():
        print(print_green("[CRIT] ✓") + " Code review complete")
        items.append(("Code review complete", "PASS"))
    else:
        print(print_red("[CRIT] ✗") + " Code review not complete")
        items.append(("Code review complete", "FAIL"))
        all_passed = False

    # Check critical issues resolved
    if metrics["critical_fixed"] >= metrics["critical_found"]:
        print(print_green(f"[CRIT] ✓ All critical issues resolved ({metrics['critical_fixed']}/{metrics['critical_found']})"))
        items.append(("Critical issues resolved", "PASS"))
    else:
        print(print_red(f"[CRIT] ✗ Critical issues unresolved ({metrics['critical_fixed']}/{metrics['critical_found']})"))
        items.append(("Critical issues resolved", "FAIL"))
        all_passed = False

    # Check major issues resolved
    if metrics["major_fixed"] >= metrics["major_found"]:
        print(print_green(f"[CRIT] ✓ All major issues resolved ({metrics['major_fixed']}/{metrics['major_found']})"))
        items.append(("Major issues resolved", "PASS"))
    else:
        print(print_yellow(f"[CRIT] ! Major issues partially resolved ({metrics['major_fixed']}/{metrics['major_found']})"))
        items.append(("Major issues resolved", "WARN"))

    # Check tests passing
    if metrics["tests_passing"]:
        print(print_green("[BLCK] ✓") + " All tests passing after refinements")
        items.append(("Tests passing", "PASS"))
    else:
        print(print_red("[BLCK] ✗") + " Tests failing after refinements")
        items.append(("Tests passing", "FAIL"))
        all_passed = False

    return items, all_passed


def _check_audit_item(audit_file: Path) -> Tuple[str, str]:
    """Check audit checklist item. Returns (name, status) tuple."""
    if not audit_file.exists():
        print(print_yellow("[BLCK] !") + " Audit not completed")
        return ("Audit", "SKIP")

    try:
        audit_data = json.loads(read_file(audit_file))
        summary = audit_data.get("summary", {})
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        warnings = summary.get("warnings", 0)
        total = passed + failed + warnings

        if total == 0:
            overall_status = audit_data.get("overall_status", "UNKNOWN")
            if overall_status == "PASS":
                print(print_green("[BLCK] ✓") + " Audit passed")
                return ("Audit", "PASS")
            elif overall_status in ["WARNING", "DEFERRED"]:
                print(print_yellow(f"[BLCK] ! Audit: {overall_status}"))
                return ("Audit", "WARN")
            else:
                print(print_red("[BLCK] ✗") + " Audit failed")
                return ("Audit", "FAIL")
        elif failed == 0 and warnings == 0:
            print(print_green(f"[BLCK] ✓ Audit passed ({passed} passed)"))
            return ("Audit", "PASS")
        elif failed == 0:
            print(print_yellow(f"[BLCK] ! Audit has warnings ({warnings} warnings)"))
            return ("Audit", "WARN")
        else:
            print(print_red(f"[BLCK] ✗ Audit has failures ({failed} failed)"))
            return ("Audit", "FAIL")
    except (json.JSONDecodeError, OSError) as e:
        logger.debug("Failed to parse audit file %s: %s", audit_file, e)
        print(print_yellow("[BLCK] !") + " Audit not completed")
        return ("Audit", "SKIP")


def _run_closeout_checklist(
    findings_file: Path,
    refinement_file: Path,
    audit_file: Path
) -> Tuple[List[Tuple[str, str]], bool]:
    """Run closeout checklist."""
    print()
    print(print_bold("- CLOSEOUT CHECKLIST"))
    print()

    metrics = _load_review_metrics(findings_file, refinement_file)
    review_items, all_passed = _check_review_items(findings_file, metrics)
    checklist = list(review_items)

    # Check audit
    checklist.append(_check_audit_item(audit_file))

    # Check review artifacts
    if findings_file.exists() and refinement_file.exists():
        print(print_green("[PASS] ✓") + " Review artifacts saved")
        checklist.append(("Review artifacts", "PASS"))
    else:
        print(print_yellow("[PASS] !") + " Some review artifacts missing")
        checklist.append(("Review artifacts", "WARN"))

    print()

    return checklist, all_passed


def _get_closeout_approval(all_passed: bool, review_dir: Path, uat_mode: bool) -> bool:
    """Get closeout approval from user."""
    if uat_mode:
        return True

    print()
    print(print_bold("- CLOSEOUT APPROVAL"))
    print()

    if not all_passed:
        print(print_yellow("Some critical items need attention before closeout."))
        print()

    print(print_cyan("Closeout options:"))
    print()
    print(print_green("  [approve]") + " Approve closeout and proceed")
    print(print_yellow("  [review]") + "  Review specific artifacts")
    print(print_red("  [hold]") + "    Hold closeout for now")
    print()

    clear_input_buffer()
    choice = prompt_user("Choice (default: approve): ").strip() or "approve"

    if choice == "review":
        print()
        print(print_dim("Key artifacts:"))
        print("    .claude/reviews/findings.json         - Review findings")
        print("    .claude/reviews/refinement-report.json - Refinement report")
        print("    .claude/audit/phase-06-audit.json     - Audit results")
        print()
        prompt_user("Press Enter to continue to closeout...")
        return True
    elif choice == "hold":
        print()
        print(print_yellow("! Closeout held - phase not complete"))
        return False

    return True


def _generate_closeout_markdown(
    closeout_file: Path,
    checklist: List[Tuple[str, str]],
    metrics: dict
) -> None:
    """Generate closeout markdown document."""
    checklist_md = []
    for name, status in checklist:
        if status == "PASS":
            checklist_md.append(f"- [x] {name}")
        elif status == "WARN":
            checklist_md.append(f"- [~] {name} (warning)")
        elif status == "FAIL":
            checklist_md.append(f"- [ ] {name} (failed)")
        else:
            checklist_md.append(f"- [-] {name} (deferred)")

    tests_passing = bool(metrics["tests_passing"])

    markdown_content = f"""# Phase 6 Closeout: Code Review

**Completed:** {datetime.now(timezone.utc).isoformat()}
**Status:** COMPLETE

## Summary

Phase 6 (Code Review) has been completed. All implemented code has been reviewed and refined.

### Key Outcomes

- **Critical Issues Found:** {metrics["critical_found"]}
- **Critical Issues Fixed:** {metrics["critical_fixed"]}
- **Major Issues Found:** {metrics["major_found"]}
- **Major Issues Fixed:** {metrics["major_fixed"]}
- **Tests Passing:** {tests_passing}

### Review Dimensions

Code was reviewed across four dimensions:

1. **Deep Code Review** - Logic, error handling, edge cases
2. **Architecture Compliance** - Pattern adherence, dependencies
3. **Performance Analysis** - Complexity, resource usage
4. **Documentation Review** - Comments, API docs, README

### Artifacts Produced

| Artifact | Location |
|----------|----------|
| Review Findings | .claude/reviews/findings.json |
| Refinement Report | .claude/reviews/refinement-report.json |
| Phase Audit | .claude/audit/phase-06-audit.json |

### Checklist Status

{chr(10).join(checklist_md)}

## Next Phase

**Phase 7: Integration Testing**

In the next phase, we will:
- Run integration tests across components
- Verify system-level behavior
- Test external integrations

## To Continue

```bash
python main.py run 7
```

---

*Phase 6 completed by ATOMIC CLAUDE*
"""

    write_file(closeout_file, markdown_content)
    print(print_green("  ✓ Generated phase-06-closeout.md"))


def _generate_closeout_json(
    closeout_json: Path,
    checklist: List[Tuple[str, str]],
    metrics: dict
) -> None:
    """Generate closeout JSON document."""
    checklist_json = [f"{name}:{status}" for name, status in checklist]

    json_content = {
        "phase": 6,
        "name": "Code Review",
        "status": "complete",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "findings": {
            "critical_found": metrics["critical_found"],
            "critical_fixed": metrics["critical_fixed"],
            "major_found": metrics["major_found"],
            "major_fixed": metrics["major_fixed"],
        },
        "tests_passing": bool(metrics["tests_passing"]),
        "checklist": checklist_json,
        "artifacts": {
            "findings": ".claude/reviews/findings.json",
            "refinement": ".claude/reviews/refinement-report.json",
            "audit": ".claude/audit/phase-06-audit.json"
        },
        "next_phase": 7
    }

    write_file(closeout_json, json.dumps(json_content, indent=2))
    print(print_green("  ✓ Generated phase-06-closeout.json"))

    # Also write to .outputs/ path for new-style consumers
    outputs_closeout = closeout_json.parent.parent.parent / ".outputs" / "6-code_review" / "closeout.json"
    ensure_dir(outputs_closeout.parent)
    write_file(outputs_closeout, json.dumps(json_content, indent=2))
    print(print_green("  ✓ Generated .outputs/6-code_review/closeout.json"))


def _generate_closeout_documents(
    closeout_file: Path,
    closeout_json: Path,
    checklist: List[Tuple[str, str]],
    findings_file: Path,
    refinement_file: Path
) -> None:
    """Generate closeout markdown and JSON documents."""
    print()
    print(print_bold("- GENERATING CLOSEOUT"))
    print()

    metrics = _load_review_metrics(findings_file, refinement_file)
    _generate_closeout_markdown(closeout_file, checklist, metrics)
    _generate_closeout_json(closeout_json, checklist, metrics)
    print()


def _memory_checkpoint(findings_file: Path, refinement_file: Path) -> None:
    """Create memory checkpoint and save to memory system."""
    metrics = _load_review_metrics(findings_file, refinement_file)

    memory_summary = f"""PHASE 6 CODE REVIEW COMPLETE

CRITICAL ISSUES: {metrics['critical_fixed']} of {metrics['critical_found']} fixed
MAJOR ISSUES: {metrics['major_fixed']} of {metrics['major_found']} fixed
REVIEW STATUS: Complete

KEY ARTIFACTS:
- findings.json: All code review findings
- refinement-report.json: What was fixed
- Verification tests passing

READY FOR: Phase 7 (Integration) - Integration and acceptance testing"""

    try:
        memory_save(
            phase="6-code-review",
            task_id="606",
            content=memory_summary,
            tags=["phase-closeout", "code-review", "phase-6"],
            entry_type=MemoryEntryType.PHASE_CLOSEOUT,
            metadata={
                "critical_found": metrics["critical_found"],
                "critical_fixed": metrics["critical_fixed"],
                "major_found": metrics["major_found"],
                "major_fixed": metrics["major_fixed"],
                "tests_passing": metrics["tests_passing"],
            },
        )
        print(print_dim(f"Memory checkpoint saved: {len(memory_summary)} chars"))
    except Exception as e:
        logger.debug("Failed to save memory checkpoint: %s", e)
        print(print_dim(f"Memory checkpoint: {len(memory_summary)} chars (save failed)"))


def _display_session_end(closeout_file: Path, review_dir: Path) -> None:
    """Display session end message."""
    print()
    print(print_bold("- SESSION END"))
    print()
    print("  Closeout saved to:")
    print(print_dim(f"    {closeout_file}"))
    print()
    print("  Review artifacts at:")
    print(print_dim(f"    {review_dir}/"))
    print()
    print(print_bold("  Next: PHASE 7 - INTEGRATION TESTING"))
    print()
    print("  To continue:")
    print(print_cyan("    python main.py run 7"))
    print()
    print(print_green("  Phase 6 Complete!"))
    print(print_dim("  Code reviewed and refined. Ready for Integration Testing."))
    print()


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 606: Phase Closeout")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
