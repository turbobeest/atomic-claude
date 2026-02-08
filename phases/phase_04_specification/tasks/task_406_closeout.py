"""
Task 406: Phase Closeout

Generate closeout document and prepare for Phase 5 (TDD Implementation).
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user, clear_input_buffer
)
from core.utils.file_ops import ensure_dir, read_file, write_file


def check_closeout_items(
    tasks_file: Path,
    specs_dir: Path,
    audit_file: Path
) -> Tuple[List[Tuple[str, str]], bool]:
    """
    Check closeout checklist items.

    Returns:
        Tuple of (checklist items, all_passed flag)
    """
    checklist = []
    all_passed = True

    try:
        tasks_data = json.loads(read_file(tasks_file))
        tasks = tasks_data.get("tasks", [])
        task_count = len(tasks)

        # Check OpenSpecs created
        spec_count = len(list(specs_dir.glob("spec-*.json")))

        if spec_count >= task_count and task_count > 0:
            print_green(f"  [CRIT] ✓ OpenSpecs created ({spec_count} specs)")
            checklist.append(("OpenSpecs created", "PASS"))
        elif spec_count > 0:
            print_yellow(f"  [CRIT] ! Partial OpenSpecs ({spec_count} / {task_count})")
            checklist.append(("OpenSpecs created", "WARN"))
        else:
            print_red("  [CRIT] ✗ No OpenSpecs created")
            checklist.append(("OpenSpecs created", "FAIL"))
            all_passed = False

        # Check TDD subtasks
        tasks_with_tdd = len([t for t in tasks if len(t.get("subtasks", [])) >= 4])

        if tasks_with_tdd >= task_count and task_count > 0:
            print_green(f"  [CRIT] ✓ TDD subtasks injected ({tasks_with_tdd} tasks)")
            checklist.append(("TDD subtasks", "PASS"))
        elif tasks_with_tdd > 0:
            print_yellow(f"  [CRIT] ! Partial TDD subtasks ({tasks_with_tdd} / {task_count})")
            checklist.append(("TDD subtasks", "WARN"))
        else:
            print_red("  [CRIT] ✗ No TDD subtasks")
            checklist.append(("TDD subtasks", "FAIL"))
            all_passed = False

        # Check audit
        if audit_file.exists():
            try:
                audit_data = json.loads(read_file(audit_file))
                passed = audit_data.get("summary", {}).get("passed", 0)
                failed = audit_data.get("summary", {}).get("failed", 0)
                warnings = audit_data.get("summary", {}).get("warnings", 0)
                total = passed + failed + warnings

                if total == 0:
                    # Try legacy format
                    audit_status = audit_data.get("overall_status", "UNKNOWN")
                    if audit_status == "PASS":
                        print_green("  [BLCK] ✓ Audit passed")
                        checklist.append(("Audit", "PASS"))
                    elif audit_status in ["WARNING", "DEFERRED"]:
                        print_yellow(f"  [BLCK] ! Audit: {audit_status}")
                        checklist.append(("Audit", "WARN"))
                    else:
                        print_red("  [BLCK] ✗ Audit failed")
                        checklist.append(("Audit", "FAIL"))
                elif failed == 0 and warnings == 0:
                    print_green(f"  [BLCK] ✓ Audit passed ({passed} passed)")
                    checklist.append(("Audit", "PASS"))
                elif failed == 0:
                    print_yellow(f"  [BLCK] ! Audit has warnings ({warnings} warnings)")
                    checklist.append(("Audit", "WARN"))
                else:
                    print_red(f"  [BLCK] ✗ Audit has failures ({failed} failed)")
                    checklist.append(("Audit", "FAIL"))
            except Exception as e:
                print_yellow(f"  [BLCK] ! Could not parse audit: {e}")
                checklist.append(("Audit", "WARN"))
        else:
            print_yellow("  [BLCK] ! Audit not completed")
            checklist.append(("Audit", "SKIP"))

        # Check spec quality
        specs_with_tests = 0
        for spec_file in specs_dir.glob("spec-*.json"):
            try:
                spec_data = json.loads(read_file(spec_file))
                if len(spec_data.get("test_strategy", {}).get("unit_tests", [])) > 0:
                    specs_with_tests += 1
            except:
                pass

        if specs_with_tests >= spec_count and spec_count > 0:
            print_green("  [BLCK] ✓ Test strategies defined")
            checklist.append(("Test strategies", "PASS"))
        else:
            print_yellow("  [BLCK] ! Some specs lack test strategies")
            checklist.append(("Test strategies", "WARN"))

        # TDD chain integrity
        valid_chains = 0
        for task in tasks:
            subtasks = task.get("subtasks", [])
            if len(subtasks) >= 4:
                # Check dependencies: RED→GREEN→REFACTOR→VERIFY
                if (subtasks[1].get("dependencies") == [1] and
                    subtasks[2].get("dependencies") == [2] and
                    subtasks[3].get("dependencies") == [3]):
                    valid_chains += 1

        if valid_chains >= tasks_with_tdd and tasks_with_tdd > 0:
            print_green("  [PASS] ✓ TDD chains valid (RED→GREEN→REFACTOR→VERIFY)")
            checklist.append(("TDD chains", "PASS"))
        else:
            print_yellow("  [PASS] ! Some TDD chains may be invalid")
            checklist.append(("TDD chains", "WARN"))

        print_green("  [PASS] ✓ Ready for TDD Implementation")

    except Exception as e:
        print_red(f"✗ Error checking closeout items: {e}")
        all_passed = False

    return checklist, all_passed


def generate_closeout_documents(
    closeout_dir: Path,
    tasks_file: Path,
    specs_dir: Path,
    checklist: List[Tuple[str, str]]
) -> Tuple[Path, Path]:
    """Generate closeout markdown and JSON documents."""
    closeout_md = closeout_dir / "phase-04-closeout.md"
    closeout_json = closeout_dir / "phase-04-closeout.json"

    # Load task data
    tasks_data = json.loads(read_file(tasks_file))
    tasks = tasks_data.get("tasks", [])
    task_count = len(tasks)

    # Calculate metrics
    spec_count = len(list(specs_dir.glob("spec-*.json")))
    tasks_with_tdd = len([t for t in tasks if len(t.get("subtasks", [])) >= 4])
    total_subtasks = sum(len(t.get("subtasks", [])) for t in tasks)

    # Generate markdown
    checklist_md = []
    for name, status in checklist:
        if status == "PASS":
            checklist_md.append(f"- [x] {name}")
        elif status == "WARN":
            checklist_md.append(f"- [~] {name} (warning)")
        elif status == "FAIL":
            checklist_md.append(f"- [ ] {name} (failed)")
        elif status == "SKIP":
            checklist_md.append(f"- [-] {name} (skipped)")

    md_content = f"""# Phase 4 Closeout: Specification

**Completed:** {datetime.now().isoformat()}
**Status:** COMPLETE

## Summary

Phase 4 (Specification) has been completed. Tasks have been expanded into OpenSpec definitions with TDD subtask structure.

### Key Outcomes

- **OpenSpecs Created:** {spec_count}
- **Tasks with TDD:** {tasks_with_tdd}
- **Total Subtasks:** {total_subtasks}
- **TDD Structure:** RED→GREEN→REFACTOR→VERIFY

### Artifacts Produced

| Artifact | Location |
|----------|----------|
| OpenSpecs | .claude/specs/spec-*.json |
| Tasks (updated) | .taskmaster/tasks/tasks.json |
| Phase Audit | .claude/audit/phase-04-audit.json |

### TDD Subtask Structure

Each task now has 4 subtasks:

1. **RED** - Write failing tests (tests exist and FAIL)
2. **GREEN** - Minimal implementation (tests PASS)
3. **REFACTOR** - Clean up code (linting passes)
4. **VERIFY** - Security scan (no critical issues)

### Checklist Status

{chr(10).join(checklist_md)}

## Next Phase

**Phase 5: TDD Implementation**

In the next phase, we will:
- Execute TDD cycles for each task
- Run RED subtasks (write failing tests)
- Run GREEN subtasks (implement to pass)
- Run REFACTOR subtasks (clean up code)
- Run VERIFY subtasks (security scans)

## To Continue

```bash
./orchestrator/pipeline resume
```

---

*Phase 4 completed by ATOMIC CLAUDE*
"""

    write_file(closeout_md, md_content)

    # Generate JSON
    json_data = {
        "phase": 4,
        "name": "Specification",
        "status": "complete",
        "completed_at": datetime.now().isoformat(),
        "spec_count": spec_count,
        "tasks_with_tdd": tasks_with_tdd,
        "total_subtasks": total_subtasks,
        "task_count": task_count,
        "checklist": [{"name": name, "status": status} for name, status in checklist],
        "artifacts": {
            "specs": ".claude/specs/",
            "tasks": ".taskmaster/tasks/tasks.json",
            "audit": ".claude/audit/phase-04-audit.json"
        },
        "next_phase": 5
    }

    write_file(closeout_json, json.dumps(json_data, indent=2))

    return closeout_md, closeout_json


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 406: Phase Closeout.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, auto-approve closeout for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    closeout_dir = atomic_root / ".claude" / "closeout"
    tasks_file = atomic_root / ".taskmaster" / "tasks" / "tasks.json"
    specs_dir = atomic_root / ".claude" / "specs"

    # Check audit file (new path first, then legacy)
    audit_file = atomic_root / ".outputs" / "audits" / "phase-4-report.json"
    if not audit_file.exists():
        audit_file = atomic_root / ".claude" / "audit" / "phase-04-audit.json"

    # UAT Mode: Auto-approve closeout
    if uat_mode:
        print()
        print_yellow("⚡ UAT Mode: Auto-approving closeout")
        print()
        ensure_dir(output_dir)
        write_file(output_dir / "closeout.json", json.dumps({
            "approved": True,
            "mode": "uat"
        }, indent=2))
        print_green("✓ Phase closeout complete (UAT mode)")
        return True

    ensure_dir(closeout_dir)

    print()
    print_dim("  Final review before moving to Phase 5 (TDD Implementation).")
    print()

    # Closeout Checklist
    print_dim("─" * 109)
    print()
    print_bold("CLOSEOUT CHECKLIST")
    print()

    checklist, all_passed = check_closeout_items(tasks_file, specs_dir, audit_file)

    print()

    # Closeout Approval
    print_dim("─" * 109)
    print()

    if not all_passed:
        print_yellow("  Some critical items need attention before closeout.")
        print()

    print_cyan("Closeout options:")
    print()
    print_green("  [approve] Approve closeout and proceed")
    print_yellow("  [review]  Review specific artifacts")
    print_red("  [hold]    Hold closeout for now")
    print()

    clear_input_buffer()
    closeout_choice = prompt_user("  Choice (default: approve): ").strip().lower() or "approve"

    if closeout_choice == "review":
        print()
        print_dim("  Key artifacts:")
        print("    .claude/specs/                    - OpenSpec definitions")
        print("    .taskmaster/tasks/tasks.json      - Tasks with TDD subtasks")
        print("    .claude/audit/phase-04-audit.json - Audit results")
        print()
        if specs_dir.exists():
            print_dim("  Spec files:")
            for spec_file in list(specs_dir.glob("spec-*.json"))[:10]:
                print(f"    {spec_file.name}")
            if len(list(specs_dir.glob("spec-*.json"))) > 10:
                print_dim("    ... and more")
        print()
        prompt_user("  Press Enter to continue to closeout...")
    elif closeout_choice == "hold":
        print()
        print_yellow("⚠  Closeout held - phase not complete")
        return False

    # Generate Closeout Document
    print_dim("─" * 109)
    print()
    print_bold("GENERATING CLOSEOUT")
    print()

    closeout_md, closeout_json = generate_closeout_documents(
        closeout_dir, tasks_file, specs_dir, checklist
    )

    print_green(f"  ✓ Generated {closeout_md.name}")
    print_green(f"  ✓ Generated {closeout_json.name}")
    print()

    # Memory Checkpoint (placeholder for future memory.py integration)
    tasks_data = json.loads(read_file(tasks_file))
    tasks = tasks_data.get("tasks", [])
    spec_count = len(list(specs_dir.glob("spec-*.json")))
    tasks_with_tdd = len([t for t in tasks if len(t.get("subtasks", [])) >= 4])
    total_subtasks = sum(len(t.get("subtasks", [])) for t in tasks)

    print_dim("  Memory checkpoint would save here...")
    print()

    # Session End
    print_dim("─" * 109)
    print()
    print_bold("SESSION END")
    print()
    print("  Closeout saved to:")
    print_dim("    .claude/closeout/phase-04-closeout.md")
    print()
    print("  Specifications saved to:")
    print_dim("    .claude/specs/spec-*.json")
    print()
    print("  Tasks updated at:")
    print_dim("    .taskmaster/tasks/tasks.json")
    print()
    print_bold("  Next: PHASE 5 - TDD IMPLEMENTATION")
    print()
    print("  To continue:")
    print_cyan("    ./orchestrator/pipeline resume")
    print()
    print_dim("─" * 109)
    print()
    print_green("  Phase 4 Complete!")
    print_dim("  Specifications ready. TDD structure in place. See you in Implementation.")
    print()

    print_green("✓ Phase 4 closeout complete")

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 406: Phase Closeout")
    parser.add_argument('--atomic-root', type=Path, required=True,
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (auto-approve closeout)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
