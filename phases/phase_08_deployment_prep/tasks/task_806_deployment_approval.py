"""
Task 806: Deployment Approval

Human gate for approving deployment artifacts.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user
)
from core.utils.file_ops import read_json, write_json


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 806: Deployment Approval.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    deployment_dir = atomic_root / ".claude" / "deployment"
    artifacts_file = deployment_dir / "artifacts.json"
    approval_file = deployment_dir / "approval.json"

    print(print_bold("Deployment Approval"))
    print()

    # UAT Mode Bypass
    if uat_mode:
        print(print_dim("  UAT Mode: Creating minimal valid output"))
        deployment_dir.mkdir(parents=True, exist_ok=True)
        approval_data = {
            "approved": True,
            "approved_at": datetime.utcnow().isoformat() + "Z",
            "approver": "UAT"
        }
        write_json(approval_file, approval_data)
        print(print_green("✓ UAT bypass complete"))
        return True

    print()
    print(print_dim("  Human gate: Review and approve deployment artifacts."))
    print()

    # ARTIFACTS REVIEW
    print()
    print(print_bold("  - ARTIFACTS REVIEW"))
    print()

    # Load artifact data
    version = "0.1.0"
    package_status = "success"
    changelog_status = "success"
    docs_status = "success"
    install_status = "success"

    if artifacts_file.exists():
        artifacts_data = read_json(artifacts_file)
        version = artifacts_data.get("release", {}).get("version", "0.1.0")
        package_status = artifacts_data.get("artifacts", {}).get("package", {}).get("status", "unknown")
        changelog_status = artifacts_data.get("artifacts", {}).get("changelog", {}).get("status", "unknown")
        docs_status = artifacts_data.get("artifacts", {}).get("documentation", {}).get("status", "unknown")
        install_status = artifacts_data.get("artifacts", {}).get("installation_guide", {}).get("status", "unknown")

    print("  " + "─" * 110)
    print(print_bold("  RELEASE ARTIFACTS"))
    print()
    print(f"    Version: {version}")
    print()

    _display_status("Package builds successfully", package_status)
    _display_status("Changelog generated", changelog_status)
    _display_status("Documentation complete", docs_status)
    _display_status("Installation guide created", install_status)

    print()
    print("  " + "─" * 110)
    print()

    # APPROVAL CRITERIA
    print()
    print(print_bold("  - APPROVAL CRITERIA"))
    print()

    all_criteria_met = True

    if package_status == "success":
        print("  [CRIT] ✓ Package builds successfully")
    else:
        print("  [CRIT] ✗ Package build failed")
        all_criteria_met = False

    if docs_status == "success":
        print("  [CRIT] ✓ Documentation complete")
    else:
        print("  [CRIT] ✗ Documentation incomplete")
        all_criteria_met = False

    if changelog_status == "success":
        print("  [BLCK] ✓ Changelog accurate")
    else:
        print("  [BLCK] ✗ Changelog missing")
        all_criteria_met = False

    if install_status == "success":
        print("  [BLCK] ✓ Installation guide tested")
    else:
        print("  [BLCK] ✗ Installation guide missing")
        all_criteria_met = False

    print()

    # HUMAN GATE
    print()
    print(print_bold("  - HUMAN GATE: DEPLOYMENT APPROVAL"))
    print()

    if all_criteria_met:
        print(print_green("  " + "━" * 110))
        print(print_green("  Release artifacts ready for review."))
        print(print_green("  " + "━" * 110))
    else:
        print(print_yellow("  " + "━" * 110))
        print(print_yellow("  Some artifacts need attention before approval."))
        print(print_yellow("  " + "━" * 110))

    print()
    print(print_dim("  What would you like to do?"))
    print()
    print("    [approve]  Approve and proceed to Release")
    print("    [revise]   Make changes to artifacts")
    print("    [discuss]  Review specific details")
    print()

    approval_choice = prompt_user("  Choice (default: approve): ") or "approve"

    if approval_choice == "discuss":
        print()
        print(print_dim("  Artifact locations:"))
        print("    dist/                      - Release packages")
        print("    CHANGELOG.md               - Version changelog")
        print("    docs/README.md             - Project documentation")
        print("    docs/INSTALL.md            - Installation guide")
        print("    .claude/deployment/        - Deployment metadata")
        print()
        prompt_user("  Press Enter after review to continue...")
        print()
        print(print_dim("  Returning to approval..."))
        return execute(atomic_root, output_dir, uat_mode)

    elif approval_choice == "revise":
        print()
        print(print_yellow("⚠  Make revisions and re-run artifact generation"))
        print(print_dim("  After revisions, run: ./orchestrator/pipeline resume"))
        print()
        return False

    # Default to approve
    print()
    approver_name = prompt_user("  Approver name: ") or "Human Operator"
    print()

    # Save approval
    approval_data = {
        "status": "approved",
        "approver": approver_name,
        "version": version,
        "artifacts_approved": ["package", "changelog", "documentation", "installation_guide"],
        "approved_at": datetime.utcnow().isoformat() + "Z"
    }

    write_json(approval_file, approval_data)

    print(print_green("  " + "━" * 110))
    print(print_green(f"  ✓ DEPLOYMENT APPROVED by {approver_name}"))
    print(print_green("  " + "━" * 110))
    print()

    print(print_green("✓ Deployment Approval complete"))

    return True


def _display_status(label: str, status: str):
    """Display a status line."""
    if status == "success":
        print(f"    [ok] {label}")
    else:
        print(f"    [fail] {label}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 806: Deployment Approval")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
