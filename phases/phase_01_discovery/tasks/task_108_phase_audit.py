"""
Phase Audit Task

AI-driven audit selection from audit repository.
Wrapper around the Python audit system.
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.audit import run_phase_audit
from core.utils.cli_ui import print_green, print_yellow


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None, graph=None) -> bool:
    """
    Execute phase audit task.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, skip audit for testing
        mem: Optional TaskMemory instance for recording substantive memory

    Returns:
        True if audit completed or skipped (non-blocking)
    """
    # Extract phase number from output_dir
    # e.g., ".outputs/3-tasking" -> 3
    phase_name = output_dir.name
    if '-' in phase_name:
        phase_num = int(phase_name.split('-')[0])
        phase_id = phase_name
    else:
        print(print_yellow("⚠️  Could not determine phase number from output directory"))
        return True  # Non-blocking

    # Run audit (non-blocking - returns True even if audit fails)
    result = run_phase_audit(phase_num, phase_id, output_dir, uat_mode)

    if result:
        print(print_green("✓ Phase audit complete"))
    else:
        print(print_yellow("⚠️  Phase audit had issues (non-blocking)"))

    # Record substantive memory
    if mem:
        # Try to read audit results
        import json
        audit_file = atomic_root.parent / ".outputs" / "audits" / f"phase-{phase_num}-report.json"
        if audit_file.exists():
            try:
                audit_data = json.loads(audit_file.read_text())
                summary = audit_data.get("summary", {})
                passed = summary.get("passed", 0)
                failed = summary.get("failed", 0)
                warnings = summary.get("warnings", 0)
                mem.finding(f"Audit results: {passed} passed, {failed} failed, {warnings} warnings")
            except Exception:
                mem.finding(f"Audit: {'passed' if result else 'had issues'}")
        else:
            mem.finding(f"Audit: {'passed' if result else 'had issues'}")

    return True  # Always return True - audits are non-blocking


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Phase Audit Task")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
