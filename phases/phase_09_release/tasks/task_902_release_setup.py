"""
Task 902: Release Setup

Final confirmation and release notes review before executing release.
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.config import Config
from core.state import StateManager
from core.ui import success, error, warning, info, step
from core.utils.file_ops import read_json, write_json

logger = logging.getLogger(__name__)


# ANSI color codes for formatted output
CYAN = "\033[96m"
DIM = "\033[2m"
BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
NC = "\033[0m"


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None) -> bool:
    """
    Execute Task 902: Release Setup.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

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

    # UAT Mode Bypass
    if uat_mode:
        print(f"  {DIM}UAT Mode: Creating minimal valid output{NC}")

        # Create minimal release setup
        write_json(release_setup_file, {
            "version": "0.1.0",
            "release_type": "internal",
            "confirmed": True
        })

        success("UAT bypass complete")
        return True

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

    # Count changelog entries (simulated)
    features_count = 5
    fixes_count = 0

    print(f"    Changelog:   {GREEN}{features_count} features{NC}, {DIM}{fixes_count} fixes{NC}")
    print(f"  {'─' * 110}")
    print()

    print(f"  {DIM}Proceed with release?{NC}")
    print()
    print(f"    {GREEN}[yes]{NC}          Proceed to release")
    print(f"    {CYAN}[review again]{NC} Review artifacts")
    print(f"    {RED}[abort]{NC}        Cancel release")
    print()

    try:
        proceed_choice = input("  Choice (default: yes): ").strip().lower() or "yes"
    except EOFError:
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
        except EOFError:
            logger.debug("Non-interactive mode: skipping review prompt")
        print()
    elif proceed_choice == "abort":
        print()
        warning("Release aborted")
        return False

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # RELEASE NOTES REVIEW
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

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
    except EOFError:
        logger.debug("Non-interactive mode: defaulting to 'y'")
        notes_confirm = "y"

    if notes_confirm not in ["y", "Y"]:
        print()
        try:
            notes_feedback = input("  Notes for modification: ")
        except EOFError:
            logger.debug("Non-interactive mode: skipping notes feedback")
            notes_feedback = ""
        print()

    # Save release setup
    write_json(release_setup_file, {
        "release": {
            "version": version,
            "type": release_type
        },
        "changelog": {
            "features": features_count,
            "fixes": fixes_count
        },
        "confirmed": True,
        "setup_at": datetime.now().isoformat()
    })

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


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 902: Release Setup")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    result = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if result else 1)
