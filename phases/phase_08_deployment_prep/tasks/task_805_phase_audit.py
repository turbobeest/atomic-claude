"""
Task 805: Phase Audit - Deployment Prep

AI-driven audit selection from turbobeest/audits repository.
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import print_bold
from core.audit import run_phase_audit


def execute(atomic_root: Path, output_dir: Path, mem=None, graph=None) -> bool:
    """
    Execute Task 805: Phase Audit.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory

    Returns:
        True if task completed successfully, False otherwise
    """
    print(print_bold("Phase Audit"))
    print()

    # Query audit graph for relevant audits
    audit_context = ""
    try:
        from core.graph.audit_loader import get_audit_graph, query_audits_for_task
        audit_graph = get_audit_graph()
        audit_context = query_audits_for_task(
            audit_graph, f"Phase 8: 8-deployment-prep", phase="8",
        )
    except Exception as e:
        logger.debug("Audit graph unavailable: %s", e)

    # Run phase audit
    return run_phase_audit(
        phase_num=8,
        phase_id="8-deployment-prep",
        output_dir=output_dir,
        audit_context=audit_context,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 805: Phase Audit")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir)
    sys.exit(0 if success else 1)
