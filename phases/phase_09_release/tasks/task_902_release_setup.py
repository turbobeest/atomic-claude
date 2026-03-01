"""
Task 902: Release Setup

Final confirmation and release notes review before executing release.
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
    Execute Task 902: Release Setup.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory

    Returns:
        True if task completed successfully, False otherwise
    """
    project_root = atomic_root.parent

    deployment_dir = project_root / ".claude" / "deployment"
    setup_file = deployment_dir / "setup.json"
    release_dir = project_root / ".claude" / "release"
    release_setup_file = release_dir / "setup.json"

    step("Release Setup")

    release_dir.mkdir(parents=True, exist_ok=True)

    print()
    print(f"  {DIM}Final confirmation before release.{NC}")
    print()

    # Load configuration
    version = "0.1.0"
    release_type = "minor"
    if setup_file.exists():
        try:
            setup_data = read_json(setup_file)
            version = setup_data.get("release", {}).get("version", "0.1.0")
            release_type = setup_data.get("release", {}).get("type", "minor")
        except Exception as e:
            logger.debug("Failed to read setup file: %s", e)

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # FINAL CONFIRMATION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    print()
    print(f"  {BOLD}- FINAL CONFIRMATION{NC}")
    print()

    print(f"  {'─' * 110}")
    print(f"  {BOLD}RELEASE DETAILS{NC}")
    print()
    print(f"    Version:     {GREEN}{version}{NC}")
    print(f"    Type:        {CYAN}{release_type}{NC}")
    print(f"    Package:     project-{version}.tar.gz")
    print()

    # SIMULATED counts -- replace with CHANGELOG.md parsing
    features_count = 5
    fixes_count = 0
    print(f"    {YELLOW}Note: Feature/fix counts are simulated{NC}")

    print(f"    Changelog:   {GREEN}{features_count} features{NC}, {DIM}{fixes_count} fixes{NC}")
    print(f"  {'─' * 110}")
    print()

    # Get final confirmation
    confirmed = _get_final_confirmation()
    if not confirmed:
        warning("Release aborted")
        return False

    # Review release notes
    notes_feedback = _review_release_notes(version)

    # Save release setup
    setup_payload = {
        "release": {
            "version": version,
            "type": release_type
        },
        "changelog": {
            "features": features_count,
            "fixes": fixes_count,
            "simulated": True
        },
        "confirmed": True,
        "setup_at": datetime.now(timezone.utc).isoformat()
    }
    if notes_feedback:
        setup_payload["feedback"] = notes_feedback

    write_json(release_setup_file, setup_payload)

    # Save decision to context
    decision_file = output_dir / "setup-decision.json"
    decision_file.parent.mkdir(parents=True, exist_ok=True)
    write_json(decision_file, {
        "decision": f"Release v{version} confirmed for execution",
        "type": "setup",
        "artifact": str(release_setup_file)
    })

    success("Release Setup complete")
    return True


def _get_final_confirmation() -> bool:
    """Get user confirmation to proceed with release. Returns False if aborted."""
    print(f"  {DIM}Proceed with release?{NC}")
    print()
    print(f"    {GREEN}[yes]{NC}          Proceed to release")
    print(f"    {CYAN}[review again]{NC} Review artifacts")
    print(f"    {RED}[abort]{NC}        Cancel release")
    print()

    try:
        proceed_choice = input("  Choice (default: yes): ").strip().lower() or "yes"
    except (EOFError, KeyboardInterrupt):
        logger.debug("Non-interactive mode: defaulting to 'yes'")
        proceed_choice = "yes"

    if proceed_choice in ["review again", "review"]:
        print()
        print(f"  {DIM}Key files to review:{NC}")
        print(f"    CHANGELOG.md")
        print(f"    dist/")
        print(f"    docs/")
        print()
        try:
            input("  Press Enter after review...")
        except (EOFError, KeyboardInterrupt):
            logger.debug("Non-interactive mode: skipping review prompt")
        print()
        return True
    elif proceed_choice == "abort":
        print()
        return False

    return True


def _review_release_notes(version: str) -> str:
    """Review release notes and collect feedback. Returns feedback string or empty."""
    print()
    print(f"  {BOLD}- RELEASE NOTES REVIEW{NC}")
    print()

    print(f"  {'─' * 110}")
    print(f"  {BOLD}RELEASE NOTES (v{version}){NC}")
    print()
    print(f"    ## What's New")
    print()
    print(f"    ### Features")
    print(f"    - Core functionality implementation")
    print(f"    - User interface components")
    print(f"    - Data persistence layer")
    print(f"    - External integrations")
    print(f"    - Performance optimizations")
    print()
    print(f"    ### Artifacts")
    print(f"    - Distribution package available in dist/")
    print(f"    - Internal documentation updated")
    print()
    print(f"  {'─' * 110}")
    print()

    print(f"  {DIM}Are the release notes acceptable?{NC}")
    print()

    try:
        notes_confirm = input("  Accept (default: y/n): ").strip().lower() or "y"
    except (EOFError, KeyboardInterrupt):
        logger.debug("Non-interactive mode: defaulting to 'y'")
        notes_confirm = "y"

    notes_feedback = ""
    if notes_confirm not in ["y", "Y"]:
        print()
        try:
            notes_feedback = input("  Notes for modification: ")
        except (EOFError, KeyboardInterrupt):
            logger.debug("Non-interactive mode: skipping notes feedback")
            notes_feedback = ""
        print()

    return notes_feedback


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 902: Release Setup")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    args = parser.parse_args()

    result = execute(args.atomic_root, args.output_dir)
    sys.exit(0 if result else 1)
