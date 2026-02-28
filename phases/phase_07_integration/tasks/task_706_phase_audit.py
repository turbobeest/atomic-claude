"""
Task 706: Phase Audit - Integration

AI-driven audit selection from audit repository.
This task delegates to the audit system.
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.audit import run_phase_audit
from core.utils.cli_ui import print_yellow


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None, graph=None) -> bool:
    """
    Execute Task 706: Phase Audit.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    # mem available but not used -- audit results are not memory-worthy
    if uat_mode:
        print(print_yellow("UAT Mode: Skipping phase audit"))
        return True

    # Query audit graph for relevant audits
    audit_context = ""
    try:
        from core.graph.audit_loader import get_audit_graph, query_audits_for_task
        audit_graph = get_audit_graph()
        audit_context = query_audits_for_task(
            audit_graph, f"Phase 7: 7-integration", phase="7",
        )
    except Exception as e:
        logger.debug("Audit graph unavailable: %s", e)

    # Delegate to audit system
    return run_phase_audit(
        phase_num=7,
        phase_id="7-integration",
        output_dir=output_dir,
        audit_context=audit_context,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 706: Phase Audit")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip audit)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
