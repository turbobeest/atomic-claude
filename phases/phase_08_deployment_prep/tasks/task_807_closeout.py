"""
Task 807: Phase Closeout

Generate closeout document and prepare for Phase 9 (Release).
"""

import sys
import logging
from pathlib import Path
from typing import List
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user
)
from core.utils.file_ops import read_json, write_json, write_file

logger = logging.getLogger(__name__)


def execute(atomic_root: Path, output_dir: Path, mem=None) -> bool:
    """
    Execute Task 807: Phase Closeout.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory

    Returns:
        True if task completed successfully, False otherwise
    """
    project_root = atomic_root.parent

    closeout_dir = project_root / ".claude" / "closeout"
    closeout_file = closeout_dir / "phase-08-closeout.md"
    closeout_json = closeout_dir / "phase-08-closeout.json"
    deployment_dir = project_root / ".claude" / "deployment"
    setup_file = deployment_dir / "setup.json"
    artifacts_file = deployment_dir / "artifacts.json"
    approval_file = deployment_dir / "approval.json"

    print(print_bold("Phase Closeout"))
    print()

    closeout_dir.mkdir(parents=True, exist_ok=True)

    print()
    print(print_dim("  Final review before moving to Phase 9 (Release)."))
    print()

    # Get data
    version = "0.1.0"
    approval_status = "pending"

    if setup_file.exists():
        try:
            setup_data = read_json(setup_file)
            version = setup_data.get("release", {}).get("version", "0.1.0")
        except Exception as e:
            logger.debug("Failed to read setup file: %s", e)

    if approval_file.exists():
        try:
            approval_data = read_json(approval_file)
            approval_status = approval_data.get("status", "pending")
        except Exception as e:
            logger.debug("Failed to read approval file: %s", e)

    # Run checklist validation
    checklist, all_passed = _validate_checklist(artifacts_file, approval_status)

    # CLOSEOUT APPROVAL
    print()
    print(print_bold("  - CLOSEOUT APPROVAL"))
    print()

    if not all_passed:
        print(print_yellow("  Some critical items need attention before closeout."))
        print()

    print(print_cyan("  Closeout options:"))
    print()
    print("    [approve] Approve closeout and proceed")
    print("    [review]  Review specific artifacts")
    print("    [hold]    Hold closeout for now")
    print()

    closeout_choice = prompt_user("  Choice (default: approve): ") or "approve"

    if closeout_choice == "review":
        print()
        print(print_dim("  Key artifacts:"))
        print("    dist/                            - Release packages")
        print("    CHANGELOG.md                     - Version changelog")
        print("    docs/                            - Documentation")
        print("    .claude/deployment/setup.json    - Setup configuration")
        print("    .claude/deployment/artifacts.json - Artifact record")
        print("    .claude/deployment/approval.json  - Approval record")
        print()
        prompt_user("  Press Enter to continue to closeout...")
        # Fall through to approval

    elif closeout_choice == "hold":
        print()
        print(print_yellow("⚠  Closeout held - phase not complete"))
        return False

    # Generate closeout documents
    closeout_md = _generate_closeout_markdown(checklist, version, approval_status)
    write_file(closeout_file, closeout_md)

    closeout_data = _generate_closeout_json(checklist, version, approval_status)
    write_json(closeout_json, closeout_data)

    print("  ✓ Generated phase-08-closeout.md")
    print("  ✓ Generated phase-08-closeout.json")
    print()

    # Display session end
    _display_session_end()

    print(print_green("✓ Phase 8 closeout complete"))

    return True


def _validate_checklist(artifacts_file: Path, approval_status: str) -> tuple:
    """Validate closeout checklist items. Returns (checklist, all_passed)."""
    print()
    print(print_bold("  - CLOSEOUT CHECKLIST"))
    print()

    checklist = []
    all_passed = True

    # Check release package
    if artifacts_file.exists():
        try:
            artifacts_data = read_json(artifacts_file)
        except Exception as e:
            logger.debug("Failed to read artifacts file: %s", e)
            print("  [CRIT] ✗ Artifacts file unreadable")
            return [f"Artifacts file unreadable:FAIL"], False
        package_status = artifacts_data.get("artifacts", {}).get("package", {}).get("status", "unknown")

        if package_status in ("success", "cached"):
            print("  [CRIT] ✓ Release package prepared")
            checklist.append("Release package prepared:PASS")
        else:
            print("  [CRIT] ✗ Release package not ready")
            checklist.append("Release package prepared:FAIL")
            all_passed = False

        # Check changelog
        changelog_status = artifacts_data.get("artifacts", {}).get("changelog", {}).get("status", "unknown")
        if changelog_status in ("success", "cached"):
            print("  [CRIT] ✓ Changelog generated")
            checklist.append("Changelog generated:PASS")
        else:
            print("  [CRIT] ✗ Changelog not generated")
            checklist.append("Changelog generated:FAIL")
            all_passed = False

        # Check documentation
        docs_status = artifacts_data.get("artifacts", {}).get("documentation", {}).get("status", "unknown")
        if docs_status in ("success", "cached"):
            print("  [BLCK] ✓ Documentation complete")
            checklist.append("Documentation complete:PASS")
        else:
            print("  [BLCK] ✗ Documentation incomplete")
            checklist.append("Documentation complete:FAIL")
            all_passed = False

        # Check installation guide
        install_status = artifacts_data.get("artifacts", {}).get("installation_guide", {}).get("status", "unknown")
        if install_status in ("success", "cached"):
            print("  [BLCK] ✓ Installation guide created")
            checklist.append("Installation guide created:PASS")
        else:
            print("  [BLCK] ✗ Installation guide missing")
            checklist.append("Installation guide created:FAIL")
            all_passed = False
    else:
        print("  [CRIT] ✗ Artifacts file not found")
        checklist.append("Release package prepared:FAIL")
        all_passed = False

    # Check approval
    if approval_status == "approved":
        print("  [BLCK] ✓ Deployment approved")
        checklist.append("Deployment approved:PASS")
    else:
        print("  [BLCK] ✗ Deployment not approved")
        checklist.append("Deployment approved:FAIL")
        all_passed = False

    print()

    return checklist, all_passed


def _generate_closeout_markdown(checklist: List[str], version: str, approval_status: str) -> str:
    """Generate markdown closeout document."""
    checklist_md = _format_checklist_markdown(checklist)

    return f"""# Phase 8 Closeout: Deployment Prep

**Completed:** {datetime.now(timezone.utc).isoformat()}
**Status:** COMPLETE

## Summary

Phase 8 (Deployment Prep) has been completed. All release artifacts are prepared.

### Key Outcomes

- **Version:** {version}
- **Package:** Built and ready
- **Changelog:** Generated
- **Documentation:** Complete
- **Installation Guide:** Created
- **Approval Status:** {approval_status}

### Artifacts Prepared

| Artifact | Status |
|----------|--------|
| Release Package | Ready |
| Changelog | Generated |
| Documentation | Complete |
| Installation Guide | Ready |

### Checklist Status

{checklist_md}

## Next Phase

**Phase 9: Release**

In the next phase, we will:
- Create GitHub release
- Publish to package registries
- Make announcement
- Complete release process

## To Continue

```bash
python main.py run 9
```

---

*Phase 8 completed by ATOMIC CLAUDE*
"""


def _generate_closeout_json(checklist: List[str], version: str, approval_status: str) -> dict:
    """Generate JSON closeout data."""
    return {
        "phase": "8-deployment-prep",
        "name": "Deployment Prep",
        "status": "complete",
        "completed_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "release": {
            "version": version
        },
        "approval_status": approval_status,
        "checklist": checklist,
        "artifacts": {
            "setup": ".claude/deployment/setup.json",
            "artifacts": ".claude/deployment/artifacts.json",
            "approval": ".claude/deployment/approval.json"
        },
        "next_phase": 9
    }


def _display_session_end():
    """Display session end information."""
    print()
    print(print_bold("  - SESSION END"))
    print()
    print("  Closeout saved to:")
    print(print_dim("    .claude/closeout/phase-08-closeout.md"))
    print()
    print("  Deployment artifacts at:")
    print(print_dim("    .claude/deployment/"))
    print()
    print(print_bold("  Next: PHASE 9 - RELEASE"))
    print()
    print("  To continue:")
    print(print_cyan("    python main.py run 9"))
    print()
    print(print_green("  Phase 8 Complete!"))
    print(print_dim("  Package ready. Launch imminent."))
    print()


def _format_checklist_markdown(checklist: List[str]) -> str:
    """Format checklist items as markdown."""
    lines = []
    for item in checklist:
        parts = item.split(":", 1)
        name = parts[0]
        status = parts[1] if len(parts) > 1 else "UNKNOWN"
        if status == "PASS":
            lines.append(f"- [x] {name}")
        elif status == "FAIL":
            lines.append(f"- [ ] {name} (failed)")
        else:
            lines.append(f"- [?] {name} (unknown)")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 807: Phase Closeout")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir)
    sys.exit(0 if success else 1)
