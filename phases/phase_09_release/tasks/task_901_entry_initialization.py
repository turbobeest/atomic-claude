"""
Task 901: Entry & Initialization

Validate prerequisites and present phase objectives for the Release phase.
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

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
    Execute Task 901: Entry & Initialization.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    project_root = atomic_root.parent

    # Display phase header
    print()
    print(f"{DIM}{'━' * 120}{NC}")
    print(f"{CYAN}  PHASE 09 - RELEASE{NC}")
    print(f"{DIM}{'━' * 120}{NC}")
    print()

    step("Entry & Initialization")

    # UAT Mode Bypass
    if uat_mode:
        print(f"  {DIM}UAT Mode: Skipping interactive validation{NC}")
        success("UAT bypass complete")
        return True

    print()
    print(f"  {DIM}Validating prerequisites for Release phase.{NC}")
    print()

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # PREREQUISITE VALIDATION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    print()
    print(f"  {BOLD}- PREREQUISITE VALIDATION{NC}")
    print()

    all_valid = True

    # Find Phase 8 closeout
    closeout_patterns = [
        atomic_root.parent / ".outputs" / "8-deployment-prep" / "closeout.json",
        project_root / ".claude" / "closeout" / "phase-08-closeout.json"
    ]

    closeout_file = None
    for pattern in closeout_patterns:
        if pattern.exists():
            closeout_file = pattern
            break

    # Check Phase 8 closeout
    if closeout_file and closeout_file.exists():
        try:
            closeout_data = read_json(closeout_file)
            phase_8_status = closeout_data.get("status", "unknown")
            if phase_8_status == "complete" or "tasks_completed" in closeout_data:
                print(f"  {GREEN}[CRIT]{NC} {GREEN}✓{NC} Phase 8 (Deployment Prep) complete")
            else:
                print(f"  {RED}[CRIT]{NC} {RED}✗{NC} Phase 8 not complete (status: {phase_8_status})")
                all_valid = False
        except Exception as e:
            logger.debug("Failed to read Phase 8 closeout: %s", e)
            print(f"  {RED}[CRIT]{NC} {RED}✗{NC} Failed to read Phase 8 closeout: {e}")
            all_valid = False
    else:
        print(f"  {RED}[CRIT]{NC} {RED}✗{NC} Phase 8 closeout not found")
        all_valid = False

    # Check changelog
    changelog_file = atomic_root / "CHANGELOG.md"
    if changelog_file.exists():
        print(f"  {GREEN}[BLCK]{NC} {GREEN}✓{NC} CHANGELOG.md present")
    else:
        print(f"  {YELLOW}[BLCK]{NC} {YELLOW}!{NC} CHANGELOG.md not found")

    # Check dist directory
    dist_dir = atomic_root / "dist"
    if dist_dir.exists() and dist_dir.is_dir():
        print(f"  {GREEN}[BLCK]{NC} {GREEN}✓{NC} Distribution artifacts present")
    else:
        print(f"  {YELLOW}[BLCK]{NC} {YELLOW}!{NC} dist/ directory not found")

    # Check project config
    config_file = atomic_root.parent / ".outputs" / "0-setup" / "project-config.json"
    if config_file.exists():
        print(f"  {GREEN}[PASS]{NC} {GREEN}✓{NC} Project configuration found")
    else:
        print(f"  {YELLOW}[PASS]{NC} {YELLOW}!{NC} Project configuration not found")

    print()

    if not all_valid:
        warning("Prerequisites not met - cannot proceed")
        return False

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # PHASE OBJECTIVES
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    print()
    print(f"  {BOLD}- PHASE OBJECTIVES{NC}")
    print()

    print(f"  {DIM}In this phase, we will:{NC}")
    print()
    print(f"    {CYAN}1.{NC} Execute release to distribution channels")
    print(f"    {CYAN}2.{NC} Create GitHub release with notes")
    print(f"    {CYAN}3.{NC} Publish to package registry")
    print(f"    {CYAN}4.{NC} Confirm release success")
    print(f"    {CYAN}5.{NC} Complete project")
    print()

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # RELEASE PROCESS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    print()
    print(f"  {BOLD}- RELEASE PROCESS{NC}")
    print()

    print(f"  {DIM}Release follows a sequential workflow:{NC}")
    print()
    print(f"    Setup  →  GitHub Release  →  Package Publish  →  Confirmation")
    print(f"    {DIM}(final check)    (create tag)       (registry)        (human gate){NC}")
    print()

    try:
        input("  Press Enter to continue...")
    except EOFError:
        logger.debug("Non-interactive mode: skipping Enter prompt")
    print()

    # Save decision to context (future: integrate with memory system)
    decision_file = output_dir / "entry-decision.json"
    decision_file.parent.mkdir(parents=True, exist_ok=True)
    write_json(decision_file, {
        "decision": "Phase 9 entry validated",
        "type": "entry",
        "prerequisites_met": all_valid
    })

    success("Entry & Initialization complete")
    return True


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 901: Entry & Initialization")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    result = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if result else 1)
