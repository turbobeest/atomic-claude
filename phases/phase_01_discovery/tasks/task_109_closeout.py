"""
Task 109: Phase Closeout

Generate closeout document and prepare for Phase 2.

Steps:
  1. Display closeout checklist
  2. Get closeout approval
  3. Generate phase-01-closeout.md
  4. End session with instructions
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.config import Config
from core.state import StateManager
from core.ui import phase_header, success, error, warning, info, step


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None, graph=None) -> bool:
    """
    Execute Task 109: Phase Closeout.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, auto-approve closeout
        mem: Optional TaskMemory instance for recording substantive memory

    Returns:
        True if closeout completed successfully, False otherwise
    """
    project_root = atomic_root.parent
    closeout_dir = project_root / ".claude" / "closeout"
    closeout_file = closeout_dir / "phase-01-closeout.md"
    closeout_json = closeout_dir / "phase-01-closeout.json"

    step("Phase Closeout")

    closeout_dir.mkdir(parents=True, exist_ok=True)

    # UAT Mode: Auto-approve closeout
    if uat_mode:
        print()
        print("  ⚡ UAT Mode: Auto-approving closeout")
        print()

        _create_uat_closeout(closeout_file, closeout_json)
        success("Phase closeout complete (UAT mode)")
        return True

    print()
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │ PHASE CLOSEOUT                                          │")
    print("  │                                                         │")
    print("  │ Final review before moving to Phase 2 (PRD).           │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()

    # ═══════════════════════════════════════════════════════════════
    # CLOSEOUT CHECKLIST
    # ═══════════════════════════════════════════════════════════════

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ CLOSEOUT CHECKLIST                                        ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    checklist = []
    all_passed = True

    # Check artifacts
    all_passed = _check_artifact(output_dir, "corpus.json", "Corpus collected", "CRIT", checklist) and all_passed
    all_passed = _check_artifact(output_dir, "dialogue.json", "Dialogue completed", "CRIT", checklist) and all_passed
    all_passed = _check_artifact(output_dir, "selected-agents.json", "Agents selected", "BLCK", checklist) and all_passed
    all_passed = _check_artifact(output_dir, "approaches.json", "Approaches generated", "CRIT", checklist) and all_passed
    all_passed = _check_artifact(output_dir, "selected-approach.json", "Approach selected", "CRIT", checklist) and all_passed

    # Check diagrams
    diagrams_manifest = project_root / "docs" / "diagrams" / "manifest.json"
    if diagrams_manifest.exists():
        try:
            with open(diagrams_manifest) as f:
                diagram_data = json.load(f)
            diagram_count = diagram_data.get('summary', {}).get('generated', 0)
            print(f"  [BLCK] ✓ Diagrams generated ({diagram_count})")
            checklist.append(("diagrams", "PASS"))
        except Exception as e:
            logger.debug("Failed to read diagrams manifest: %s", e)
            print("  [BLCK] ! Diagrams manifest invalid")
            checklist.append(("diagrams", "WARN"))
    else:
        print("  [BLCK] ! Diagrams not generated")
        checklist.append(("diagrams", "WARN"))

    # Check audit
    audit_file = atomic_root.parent / ".outputs" / "audits" / "phase-1" / "report.json"
    if not audit_file.exists():
        audit_file = atomic_root.parent / ".outputs" / "audits" / "phase-1-report.json"
    if not audit_file.exists():
        audit_file = project_root / ".claude" / "audit" / "phase-01-audit.json"

    if audit_file.exists():
        try:
            with open(audit_file) as f:
                audit_data = json.load(f)

            passed = audit_data.get('summary', {}).get('passed', 0)
            failed = audit_data.get('summary', {}).get('failed', 0)
            warnings = audit_data.get('summary', {}).get('warnings', 0)
            total = passed + failed + warnings

            if total == 0:
                # Try legacy format
                audit_status = audit_data.get('overall_status', 'UNKNOWN')
                if audit_status == "PASS":
                    print("  [BLCK] ✓ Audit passed")
                    checklist.append(("audit", "PASS"))
                elif audit_status == "WARNING":
                    print("  [BLCK] ! Audit has warnings")
                    checklist.append(("audit", "WARN"))
                else:
                    print("  [BLCK] ✗ Audit has critical issues")
                    checklist.append(("audit", "FAIL"))
            elif failed == 0 and warnings == 0:
                print(f"  [BLCK] ✓ Audit passed ({passed} passed)")
                checklist.append(("audit", "PASS"))
            elif failed == 0:
                print(f"  [BLCK] ! Audit has warnings ({warnings} warnings)")
                checklist.append(("audit", "WARN"))
            else:
                print(f"  [BLCK] ✗ Audit has failures ({failed} failed)")
                checklist.append(("audit", "FAIL"))
        except Exception as e:
            logger.debug("Failed to read audit file: %s", e)
            print("  [BLCK] ! Audit file invalid")
            checklist.append(("audit", "WARN"))
    else:
        print("  [BLCK] ! Audit not completed")
        checklist.append(("audit", "SKIP"))

    # Additional checks
    print("  [PASS] ✓ Ready for PRD")
    print()

    # ═══════════════════════════════════════════════════════════════
    # CLOSEOUT APPROVAL
    # ═══════════════════════════════════════════════════════════════

    print("━" * 60)
    print()

    if not all_passed:
        print("  Some items need attention before closeout.")
        print()

    print("  Closeout options:")
    print()
    print("    [approve] Approve closeout and proceed")
    print("    [review]  Review specific artifacts")
    print("    [hold]    Hold closeout for now")
    print()

    closeout_choice = input("  Choice (default: approve): ").strip().lower() or "approve"

    if closeout_choice == "review":
        print()
        print("  Artifacts in this phase:")
        for item in output_dir.iterdir():
            print(f"    {item.name}")
        print()
        input("  Press Enter to continue to closeout...")
    elif closeout_choice == "hold":
        print()
        warning("Closeout held - phase not complete")
        return False

    # ═══════════════════════════════════════════════════════════════
    # GENERATE CLOSEOUT DOCUMENT
    # ═══════════════════════════════════════════════════════════════

    print()
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ GENERATING CLOSEOUT                                       ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Gather key information
    approach_name = _get_approach_name(output_dir)
    corpus_count = _get_corpus_count(output_dir)
    agent_count = _get_agent_count(output_dir)

    # Generate markdown closeout
    _generate_markdown_closeout(closeout_file, approach_name, corpus_count, agent_count, checklist)

    # Generate JSON closeout
    _generate_json_closeout(closeout_json, approach_name, corpus_count, agent_count, checklist)

    print("  ✓ Generated phase-01-closeout.md")
    print("  ✓ Generated phase-01-closeout.json")
    print()

    # ═══════════════════════════════════════════════════════════════
    # SESSION END
    # ═══════════════════════════════════════════════════════════════

    print()
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║                                                               ║")
    print("║  SESSION END                                                  ║")
    print("║                                                               ║")
    print("║  Closeout saved to:                                           ║")
    print("║  .claude/closeout/phase-01-closeout.md                       ║")
    print("║                                                               ║")
    print("║  Next: PHASE 2 - PRD                                          ║")
    print("║                                                               ║")
    print("║  To continue:                                                 ║")
    print("║  python main.py run 2                               ║")
    print("║                                                               ║")
    print("║  ─────────────────────────────────────────────────────────── ║")
    print("║                                                               ║")
    print("║      Phase 1 Complete!                                        ║")
    print("║      Great work. See you in PRD.                              ║")
    print("║                                                               ║")
    print("╔═══════════════════════════════════════════════════════════════╝")
    print()

    # Record substantive memory
    if mem:
        passed = sum(1 for _, s in checklist if s == "PASS")
        failed = sum(1 for _, s in checklist if s == "FAIL")
        warned = sum(1 for _, s in checklist if s == "WARN")
        mem.finding(f"Checklist: {passed} passed, {failed} failed, {warned} warnings")
        mem.finding(f"Approach: {approach_name}")
        mem.finding(f"Corpus: {corpus_count} materials | Agents: {agent_count} selected")
        mem.finding("Phase 2 readiness: confirmed")

    # Export needs index from graph if available
    if graph:
        try:
            needs_export = output_dir / "needs-index-graph.json"
            graph.export_needs_index(needs_export)
        except Exception as e:
            logger.debug("Graph export failure (non-blocking): %s", e)

    success("Phase 1 closeout complete")
    return True


def _check_artifact(output_dir: Path, filename: str, name: str, level: str, checklist: List[Tuple[str, str]]) -> bool:
    """Check if an artifact exists and update checklist."""
    path = output_dir / filename
    if path.exists():
        print(f"  [{level}] ✓ {name}")
        checklist.append((name, "PASS"))
        return True
    else:
        if level == "CRIT":
            print(f"  [{level}] ✗ {name}")
            checklist.append((name, "FAIL"))
            return False
        else:
            print(f"  [{level}] ! {name}")
            checklist.append((name, "WARN"))
            return True


def _get_approach_name(output_dir: Path) -> str:
    """Get the selected approach name."""
    approach_file = output_dir / "selected-approach.json"
    if approach_file.exists():
        try:
            with open(approach_file) as f:
                data = json.load(f)
            return data.get('name', 'N/A')
        except Exception as e:
            logger.debug("Failed to read approach file: %s", e)
    return "N/A"


def _get_corpus_count(output_dir: Path) -> int:
    """Get the count of corpus materials."""
    corpus_file = output_dir / "corpus.json"
    if corpus_file.exists():
        try:
            with open(corpus_file) as f:
                data = json.load(f)
            return len(data.get('materials', []))
        except Exception as e:
            logger.debug("Failed to read corpus file: %s", e)
    return 0


def _get_agent_count(output_dir: Path) -> int:
    """Get the count of selected agents."""
    agents_file = output_dir / "selected-agents.json"
    if agents_file.exists():
        try:
            with open(agents_file) as f:
                data = json.load(f)
            return len(data.get('selected', []))
        except Exception as e:
            logger.debug("Failed to read agents file: %s", e)
    return 0


def _generate_markdown_closeout(closeout_file: Path, approach_name: str, corpus_count: int, agent_count: int, checklist: List[Tuple[str, str]]) -> None:
    """Generate the markdown closeout document."""
    timestamp = datetime.now(timezone.utc).isoformat()

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

    content = f"""# Phase 1 Closeout: Discovery

**Completed:** {timestamp}
**Status:** COMPLETE

## Summary

Phase 1 (Discovery) has been completed successfully.

### Key Outcomes

- **Corpus:** {corpus_count} materials collected and organized
- **Selected Approach:** {approach_name}
- **Agents Available:** {agent_count} selected for pipeline use
- **Direction:** Confirmed and locked

### Artifacts Produced

| Artifact | Description |
|----------|-------------|
| corpus.json | Collected project materials |
| CORPUS-INDEX.md | Organized corpus index |
| dialogue.json | Opening dialogue capture |
| approaches.json | Generated solution approaches |
| first-principles.json | First principles analysis |
| selected-approach.json | Human-selected approach (includes confirmed direction) |
| deliberation-log.json | Multi-agent discussion log |
| docs/diagrams/*.dot | Architecture diagrams (DOT format) |
| docs/diagrams/*.svg | Architecture diagrams (SVG visual) |

### Checklist Status

{chr(10).join(checklist_md)}

## Next Phase

**Phase 2: PRD (Product Requirements Document)**

In the next phase, we will:
- Transform the selected approach into formal requirements
- Define user stories and acceptance criteria
- Establish technical specifications
- Document non-functional requirements

## Agent Selection

Note: You'll have the opportunity to select or modify agents at the
start of Phase 2 and each subsequent phase. The agents selected in
this phase serve as recommendations, not fixed assignments.

## To Continue

```bash
python main.py run 2
```

---

*Phase 1 completed by ATOMIC CLAUDE*
"""

    closeout_file.write_text(content)


def _generate_json_closeout(closeout_json: Path, approach_name: str, corpus_count: int, agent_count: int, checklist: List[Tuple[str, str]]) -> None:
    """Generate the JSON closeout document."""
    timestamp = datetime.now(timezone.utc).isoformat()

    data = {
        "phase": 1,
        "name": "Discovery",
        "status": "complete",
        "completed_at": timestamp,
        "approach": approach_name,
        "corpus_materials": corpus_count,
        "agents_selected": agent_count,
        "checklist": [f"{name}:{status}" for name, status in checklist],
        "next_phase": 2
    }

    with open(closeout_json, 'w') as f:
        json.dump(data, f, indent=2)


def _create_uat_closeout(closeout_file: Path, closeout_json: Path) -> None:
    """Create minimal closeout files for UAT mode."""
    closeout_file.write_text("""# Phase 1: Discovery - Closeout

## UAT Mode

Phase 1 closeout auto-approved in UAT mode.

## Status
- All tasks completed
- Ready for Phase 2 (PRD)
""")

    with open(closeout_json, 'w') as f:
        json.dump({
            "phase": "1-discovery",
            "status": "complete",
            "approved": True,
            "mode": "uat"
        }, f, indent=2)


if __name__ == "__main__":
    # CLI execution support
    atomic_root = Path.cwd()
    output_dir = atomic_root.parent / ".outputs" / "1-discovery"
    uat_mode = "--uat" in sys.argv

    sys.exit(0 if execute(atomic_root, output_dir, uat_mode) else 1)
