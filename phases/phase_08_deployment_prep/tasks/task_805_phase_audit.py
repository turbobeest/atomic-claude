"""
Task 805: Phase Audit - Deployment Prep

AI-driven audit selection from turbobeest/audits repository.
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import print_bold, print_dim, print_green
from core.audit import run_phase_audit


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 805: Phase Audit.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass audit for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    print(print_bold("Phase Audit"))
    print()

    # UAT Mode Bypass
    if uat_mode:
        print(print_dim("  UAT Mode: Skipping audit"))
        print(print_green("✓ UAT bypass complete"))
        return True

    # Run phase audit
    return run_phase_audit(
        phase_num=8,
        phase_name="Deployment Prep",
        atomic_root=atomic_root,
        output_dir=output_dir
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 805: Phase Audit")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip audit)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
