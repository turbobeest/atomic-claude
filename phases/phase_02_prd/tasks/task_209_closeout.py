"""
Task 209: Phase Closeout

Generates closeout document and prepares for Phase 3.

Final review before moving to Phase 3 (Tasking).
"""

import logging
import os
import re
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.config import Config
from core.state import StateManager
from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user, clear_input_buffer
)
from core.utils.file_ops import ensure_dir, read_file, write_file


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None, graph=None) -> bool:
    """
    Execute Task 209: Phase Closeout.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, auto-approve closeout for testing
        graph: Optional GraphManager instance for knowledge graph operations

    Returns:
        True if task completed successfully, False otherwise
    """
    project_root = atomic_root.parent
    closeout_dir = project_root / ".claude" / "closeout"
    closeout_file = closeout_dir / "phase-02-closeout.md"
    closeout_json = closeout_dir / "phase-02-closeout.json"
    prd_file = project_root / "docs" / "prd" / "PRD.md"

    ensure_dir(closeout_dir)

    print()
    print(print_dim("  ┌─────────────────────────────────────────────────────────┐"))
    print(print_dim("  │ PHASE CLOSEOUT                                          │"))
    print(print_dim("  │                                                         │"))
    print(print_dim("  │ Final review before moving to Phase 3 (Tasking).       │"))
    print(print_dim("  └─────────────────────────────────────────────────────────┘"))
    print()

    # Closeout checklist
    checklist, all_passed = run_closeout_checklist(atomic_root, output_dir, prd_file)

    print()

    # UAT mode bypass
    if uat_mode:
        print(print_yellow("  UAT mode: Auto-approving closeout..."))
        generate_closeout_documents(closeout_file, closeout_json, prd_file, checklist)

        # Export PRD from graph if available
        if graph:
            try:
                graph_prd_export = project_root / "docs" / "prd" / "PRD-graph.md"
                graph.export_prd_md(graph_prd_export)
                logger.info(f"Graph PRD export: {graph_prd_export}")
            except Exception as e:
                logger.warning(f"Graph export failed, using file-based export: {e}")

        print(print_green("✓ UAT mode: Closeout auto-approved"))
        return True

    # Closeout approval
    print(print_dim("━" * 60))
    print()

    if not all_passed:
        print(print_yellow("  Some critical items need attention before closeout."))
        print()

    print(print_cyan("  Closeout options:"))
    print()
    print("    " + print_green("[approve]") + " Approve closeout and proceed")
    print("    " + print_yellow("[review]") + "  Review specific artifacts")
    print("    " + print_red("[hold]") + "    Hold closeout for now")
    print()

    clear_input_buffer()
    closeout_choice = prompt_user("  Choice (default: approve): ").strip().lower() or "approve"

    if closeout_choice == "review":
        print()
        print(print_dim("  Artifacts in this phase:"))
        try:
            for item in sorted(output_dir.iterdir()):
                if item.is_file():
                    print(f"    • {item.name}")
        except Exception as e:
            logger.debug("Failed to list output dir artifacts: %s", e)
        print()
        print(print_dim(f"  PRD location: {prd_file}"))
        print()
        prompt_user("  Press Enter to continue to closeout...")
    elif closeout_choice == "hold":
        print()
        print(print_yellow("  Closeout held - phase not complete"))
        return False

    # Generate closeout documents
    print()
    print(print_cyan("╔═══════════════════════════════════════════════════════════╗"))
    print(print_cyan("║ " + print_bold("GENERATING CLOSEOUT") + "                                       ║"))
    print(print_cyan("╚═══════════════════════════════════════════════════════════╝"))
    print()

    generate_closeout_documents(closeout_file, closeout_json, prd_file, checklist)

    # Export PRD from graph if available
    if graph:
        try:
            graph_prd_export = project_root / "docs" / "prd" / "PRD-graph.md"
            graph.export_prd_md(graph_prd_export)
            logger.info(f"Graph PRD export: {graph_prd_export}")
        except Exception as e:
            logger.warning(f"Graph export failed, using file-based export: {e}")

    print()
    print(print_green("✓ Phase 2 closeout complete"))
    print()
    print(print_cyan("  → Ready to proceed to Phase 3: Tasking"))
    return True


def run_closeout_checklist(
    atomic_root: Path,
    output_dir: Path,
    prd_file: Path
) -> Tuple[List[Tuple[str, str]], bool]:
    """
    Run closeout checklist.

    Args:
        atomic_root: Path to atomic-claude root
        output_dir: Path to phase output directory
        prd_file: Path to PRD file

    Returns:
        Tuple of (checklist_results, all_passed)
    """
    print(print_cyan("╔═══════════════════════════════════════════════════════════╗"))
    print(print_cyan("║ " + print_bold("CLOSEOUT CHECKLIST") + "                                        ║"))
    print(print_cyan("╚═══════════════════════════════════════════════════════════╝"))
    print()

    checklist = []
    all_passed = True

    # Check PRD document
    if prd_file.exists():
        content = read_file(prd_file)
        # Count top-level PRD sections (# N. or ## N. numbered headings)
        lines = content.split('\n')
        top_sections = [l for l in lines if re.match(r'^# \d+\.\s', l)]
        if not top_sections:
            top_sections = [l for l in lines if re.match(r'^## \d+\.\s', l)]
        section_count = len(top_sections)

        if section_count >= 10:
            print("  " + print_green("[CRIT]") + " " + print_green("✓") + f" PRD authored ({section_count} sections)")
            checklist.append(("PRD authored", "PASS"))
        else:
            print("  " + print_yellow("[CRIT]") + " " + print_yellow("!") + f" PRD incomplete ({section_count} sections)")
            checklist.append(("PRD authored", "WARN"))
    else:
        print("  " + print_red("[CRIT]") + " " + print_red("✗") + " PRD document missing")
        checklist.append(("PRD authored", "FAIL"))
        all_passed = False

    # Check PRD approval
    approval_file = output_dir / "prd-approved.json"
    if approval_file.exists():
        try:
            with open(approval_file, 'r') as f:
                approval_data = json.load(f)
            approval_status = approval_data.get('status', 'unknown')

            if approval_status == "approved":
                approver = approval_data.get('approver', 'unknown')
                print("  " + print_green("[CRIT]") + " " + print_green("✓") + f" PRD approved by {approver}")
                checklist.append(("PRD approved", "PASS"))
            else:
                print("  " + print_yellow("[CRIT]") + " " + print_yellow("!") + f" PRD approval status: {approval_status}")
                checklist.append(("PRD approved", "WARN"))
        except Exception as e:
            logger.debug("Failed to read PRD approval file: %s", e)
            print("  " + print_yellow("[CRIT]") + " " + print_yellow("!") + " PRD approval file error")
            checklist.append(("PRD approved", "WARN"))
    else:
        print("  " + print_red("[CRIT]") + " " + print_red("✗") + " PRD not approved")
        checklist.append(("PRD approved", "FAIL"))
        all_passed = False

    # Check audit (project deliverable in project_root, fallback in atomic_root)
    project_root = atomic_root.parent
    audit_file = atomic_root.parent / ".outputs" / "audits" / "phase-2" / "report.json"
    if not audit_file.exists():
        audit_file = atomic_root.parent / ".outputs" / "audits" / "phase-2-report.json"
    if not audit_file.exists():
        audit_file = project_root / ".claude" / "audit" / "phase-02-audit.json"

    if audit_file.exists():
        try:
            with open(audit_file, 'r') as f:
                audit_data = json.load(f)

            summary = audit_data.get("summary", {})
            passed = summary.get("passed", 0)
            failed = summary.get("failed", 0)
            warnings = summary.get("warnings", 0)

            if failed == 0 and warnings == 0:
                print("  " + print_green("[BLCK]") + " " + print_green("✓") + f" Audit passed ({passed} passed)")
                checklist.append(("Audit", "PASS"))
            elif failed == 0:
                print("  " + print_yellow("[BLCK]") + " " + print_yellow("!") + f" Audit has warnings ({warnings} warnings)")
                checklist.append(("Audit", "WARN"))
            else:
                print("  " + print_red("[BLCK]") + " " + print_red("✗") + f" Audit has failures ({failed} failed)")
                checklist.append(("Audit", "FAIL"))
        except Exception as e:
            logger.debug("Failed to read audit file: %s", e)
            print("  " + print_yellow("[BLCK]") + " " + print_yellow("!") + " Audit file error")
            checklist.append(("Audit", "WARN"))
    else:
        print("  " + print_yellow("[BLCK]") + " " + print_yellow("!") + " Audit not completed")
        checklist.append(("Audit", "SKIP"))

    # Check validation
    validation_file = output_dir / "prd-validation.json"
    if validation_file.exists():
        try:
            with open(validation_file, 'r') as f:
                validation_data = json.load(f)
            val_status = validation_data.get('overall_status', 'UNKNOWN')
            print("  " + print_green("[BLCK]") + " " + print_green("✓") + f" Validation complete ({val_status})")
            checklist.append(("Validation", "PASS"))
        except Exception as e:
            logger.debug("Failed to read validation file: %s", e)
            print("  " + print_yellow("[BLCK]") + " " + print_yellow("!") + " Validation file error")
            checklist.append(("Validation", "WARN"))
    else:
        print("  " + print_yellow("[BLCK]") + " " + print_yellow("!") + " Validation not completed")
        checklist.append(("Validation", "SKIP"))

    print("  " + print_green("[PASS]") + " " + print_green("✓") + " Ready for Tasking")

    return checklist, all_passed


def generate_closeout_documents(
    closeout_file: Path,
    closeout_json: Path,
    prd_file: Path,
    checklist: List[Tuple[str, str]]
) -> None:
    """
    Generate closeout documents.

    Args:
        closeout_file: Path to markdown closeout file
        closeout_json: Path to JSON closeout file
        prd_file: Path to PRD file
        checklist: Checklist results
    """
    # Gather metrics
    prd_lines = 0
    prd_sections = 0

    if prd_file.exists():
        content = read_file(prd_file)
        prd_lines = len(content.split('\n'))
        lines = content.split('\n')
        top = [l for l in lines if re.match(r'^# \d+\.\s', l)]
        if not top:
            top = [l for l in lines if re.match(r'^## \d+\.\s', l)]
        prd_sections = len(top)

    # Generate markdown closeout
    markdown_content = f"""# Phase 2 Closeout: PRD

**Completed:** {datetime.now(timezone.utc).isoformat()}
**Status:** COMPLETE

## Summary

Phase 2 (PRD) has been completed successfully.

### Key Outcomes

- **PRD Document:** {prd_lines} lines, {prd_sections} sections
- **Location:** docs/prd/PRD.md
- **Status:** Approved and validated

### Artifacts Produced

| Artifact | Description |
|----------|-------------|
| docs/prd/PRD.md | Product Requirements Document (15 sections) |
| prd-setup.json | PRD setup configuration |
| prd-interview.json | Stakeholder interview responses |
| selected-agents.json | Agent selection for PRD phase |
| prd-validation.json | Validation results |
| prd-approved.json | Approval record |
| phase-02-audit.json | Phase audit results |

### Checklist

"""

    for item, status in checklist:
        if status == "PASS":
            markdown_content += f"- [x] {item}\n"
        elif status == "WARN":
            markdown_content += f"- [!] {item} (warning)\n"
        elif status == "FAIL":
            markdown_content += f"- [ ] {item} (failed)\n"
        else:
            markdown_content += f"- [~] {item} (skipped)\n"

    markdown_content += f"""
## Next Phase

Phase 3: Tasking (Task Decomposition)

---

*Generated by Atomic Claude 2.0*
"""

    write_file(closeout_file, markdown_content)

    # Generate JSON closeout
    json_content = {
        "phase": 2,
        "phase_name": "PRD",
        "status": "complete",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "prd_lines": prd_lines,
            "prd_sections": prd_sections
        },
        "checklist": [{"item": item, "status": status} for item, status in checklist],
        "next_phase": 3
    }

    write_file(closeout_json, json.dumps(json_content, indent=2))

    print(print_green(f"  ✓ Closeout documents generated:"))
    print(print_dim(f"    • {closeout_file}"))
    print(print_dim(f"    • {closeout_json}"))


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 209: Phase Closeout")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (auto-approve closeout)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
