"""
Task 905: Release Confirmation

Human gate for confirming release success.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.ui import success, warning, step
from core.utils.cli_ui import CYAN, DIM, BOLD, GREEN, RED, YELLOW, NC
from core.utils.file_ops import read_json, write_json

logger = logging.getLogger(__name__)


def execute(atomic_root: Path, output_dir: Path, mem=None) -> bool:
    """
    Execute Task 905: Release Confirmation.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory

    Returns:
        True if task completed successfully, False otherwise
    """
    project_root = atomic_root.parent

    release_dir = project_root / ".claude" / "release"
    execution_file = release_dir / "execution.json"
    confirmation_file = release_dir / "confirmation.json"

    step("Release Confirmation")

    print()
    print(f"  {DIM}Human gate: Confirm release was successful.{NC}")
    print()

    # Load release status
    version, channel, announcement_status = _load_release_status(execution_file)

    # Display approval criteria
    all_criteria_met = _display_approval_criteria(version, announcement_status, project_root)

    # Handle confirmation interaction (loop replaces recursion)
    result = _handle_confirmation(all_criteria_met, version, channel, confirmation_file, output_dir, mem=mem)

    if result:
        success("Release Confirmation complete")
    return result


def _load_release_status(execution_file: Path) -> tuple:
    """Load release status from execution file. Returns (version, channel, announcement_status)."""
    print()
    print(f"  {BOLD}- RELEASE STATUS{NC}")
    print()

    version = "0.1.0"
    channel = "internal"
    announcement_status = "success"

    if execution_file.exists():
        try:
            execution_data = read_json(execution_file)
            version = execution_data.get("release", {}).get("version", "0.1.0")
            channel = execution_data.get("release", {}).get("channel", "internal")
            announcement_status = execution_data.get("announcement", {}).get("status", "unknown")
        except Exception as e:
            logger.debug("Failed to read execution file: %s", e)

    print(f"  {DIM}Internal release completed. Please verify:{NC}")
    print()

    print(f"  {'─' * 110}")
    print(f"  {BOLD}VERIFICATION CHECKLIST{NC}")
    print()
    print(f"    1. Release Notes:  {DIM}.claude/release/announcement.md{NC}")
    print(f"    2. Version:        v{version}")
    print(f"    3. Channel:        {channel}")
    print(f"  {'─' * 110}")
    print()

    return version, channel, announcement_status


def _display_approval_criteria(version: str, announcement_status: str, project_root: Path = None) -> bool:
    """Display approval criteria. Returns True if all criteria met."""
    print()
    print(f"  {BOLD}- APPROVAL CRITERIA{NC}")
    print()

    all_criteria_met = True

    if announcement_status == "success":
        print(f"  {GREEN}[CRIT]{NC} {GREEN}✓{NC} Internal release notes created")
    else:
        print(f"  {RED}[CRIT]{NC} {RED}✗{NC} Internal release notes failed")
        all_criteria_met = False

    if version and version != "0.0.0":
        print(f"  {GREEN}[CRIT]{NC} {GREEN}✓{NC} Version number confirmed")
    else:
        print(f"  {RED}[CRIT]{NC} {RED}✗{NC} Version number not set")
        all_criteria_met = False

    dist_ready = project_root is not None and (project_root / "dist").exists()
    if dist_ready:
        print(f"  {GREEN}[BLCK]{NC} {GREEN}✓{NC} Distribution artifacts ready")
    else:
        print(f"  {RED}[BLCK]{NC} {RED}✗{NC} Distribution artifacts not found (dist/ missing)")
        all_criteria_met = False
    print()

    return all_criteria_met


def _handle_confirmation(
    all_criteria_met: bool, version: str, channel: str,
    confirmation_file: Path, output_dir: Path, mem=None
) -> bool:
    """Handle the confirmation interaction loop. Returns True if confirmed."""
    while True:
        print()
        print(f"  {BOLD}- HUMAN GATE: RELEASE CONFIRMATION{NC}")
        print()

        if all_criteria_met:
            print(f"  {GREEN}{'━' * 110}{NC}")
            print(f"  {GREEN}Internal release completed successfully.{NC}")
            print(f"  {GREEN}{'━' * 110}{NC}")
        else:
            print(f"  {RED}{'━' * 110}{NC}")
            print(f"  {RED}Some release steps failed. Review before confirming.{NC}")
            print(f"  {RED}{'━' * 110}{NC}")

        print()
        print(f"  {DIM}Confirm internal release is complete?{NC}")
        print()
        print(f"    {GREEN}[confirm]{NC}     Release verified, proceed to closeout")
        print(f"    {RED}[rollback]{NC}    Rollback the release")
        print(f"    {YELLOW}[investigate]{NC} Investigate issues")
        print()

        try:
            confirm_choice = input("  Choice (default: confirm): ").strip().lower() or "confirm"
        except (EOFError, KeyboardInterrupt):
            logger.debug("Non-interactive mode: defaulting to 'confirm'")
            confirm_choice = "confirm"

        if confirm_choice == "investigate":
            print()
            print(f"  {DIM}Investigation steps:{NC}")
            print(f"    1. Review release notes: .claude/release/announcement.md")
            print(f"    2. Check distribution artifacts in dist/")
            print(f"    3. Verify version in execution log")
            print()
            print(f"  {DIM}Execution log: .claude/release/execution.json{NC}")
            print()
            try:
                input("  Press Enter after investigation...")
            except (EOFError, KeyboardInterrupt):
                logger.debug("Non-interactive mode: skipping investigation prompt")
            print()
            print(f"  {DIM}Returning to confirmation...{NC}")
            continue
        elif confirm_choice == "rollback":
            print()
            warning("Rollback initiated")
            print(f"  {DIM}Manual rollback steps:{NC}")
            print(f"    1. Remove release notes from .claude/release/")
            print(f"    2. Revert version changes (if any)")
            print()
            return False
        else:
            # confirm (or any other input)
            break

    # Get confirmer name
    confirmer_name = "Human Operator"
    print()
    try:
        confirmer_input = input("  Confirmer name: ").strip()
        if confirmer_input:
            confirmer_name = confirmer_input
    except (EOFError, KeyboardInterrupt):
        logger.debug("Non-interactive mode: using default confirmer name")
    print()

    # Save confirmation
    write_json(confirmation_file, {
        "status": "confirmed",
        "confirmer": confirmer_name,
        "version": version,
        "channel": channel,
        "confirmed_at": datetime.now(timezone.utc).isoformat()
    })

    print(f"  {GREEN}{'━' * 110}{NC}")
    print(f"  {GREEN}✓ RELEASE CONFIRMED{NC} by {confirmer_name}")
    print(f"  {GREEN}{'━' * 110}{NC}")
    print()

    # Save decision to context
    decision_file = output_dir / "confirmation-decision.json"
    decision_file.parent.mkdir(parents=True, exist_ok=True)
    write_json(decision_file, {
        "decision": f"Release v{version} confirmed by {confirmer_name}",
        "type": "confirmation",
        "artifact": str(confirmation_file)
    })

    return True


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 905: Release Confirmation")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    args = parser.parse_args()

    result = execute(args.atomic_root, args.output_dir)
    sys.exit(0 if result else 1)
