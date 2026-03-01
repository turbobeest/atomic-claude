"""
Phase Audit Task

AI-driven audit selection from audit repository.
Wrapper around the Python audit system.
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.audit import run_phase_audit
from core.utils.cli_ui import print_green, print_yellow


def execute(atomic_root: Path, output_dir: Path, mem=None, graph=None) -> bool:
    """
    Execute phase audit task.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        mem: Optional TaskMemory instance for recording substantive memory

    Returns:
        True if audit completed or skipped (non-blocking)
    """
    # Extract phase number from output_dir
    # e.g., ".outputs/3-tasking" -> 3
    phase_name = output_dir.name
    if '-' in phase_name:
        try:
            phase_num = int(phase_name.split('-')[0])
        except (ValueError, IndexError):
            phase_num = 0
        phase_id = phase_name
    else:
        print(print_yellow("⚠️  Could not determine phase number from output directory"))
        return True  # Non-blocking

    # Query audit graph for relevant audits
    audit_context = ""
    try:
        from core.graph.audit_loader import get_audit_graph, query_audits_for_task
        audit_graph = get_audit_graph()
        audit_context = query_audits_for_task(
            audit_graph, f"Phase {phase_num}: {phase_id}", phase=str(phase_num),
        )
    except Exception as e:
        logger.debug("Audit graph unavailable: %s", e)

    # Run audit (non-blocking - returns True even if audit fails)
    result = run_phase_audit(phase_num, phase_id, output_dir,
                             audit_context=audit_context)

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
            except Exception as e:
                logger.debug("Failed to parse audit report for memory: %s", e)
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

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir)
    sys.exit(0 if success else 1)
