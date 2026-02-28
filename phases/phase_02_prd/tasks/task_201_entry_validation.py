"""
Task 201: Entry Validation

Validates Phase 1 artifacts exist and loads context before proceeding.

Required artifacts from Phase 1:
  - phase-01-closeout.json
  - selected-approach.json (includes confirmed direction)
  - corpus.json (optional but recommended)
"""

import logging
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user, clear_input_buffer
)
from core.utils.file_ops import write_file


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None, graph=None) -> bool:
    """
    Execute Task 201: Entry Validation.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing
        graph: Optional GraphManager instance for knowledge graph operations

    Returns:
        True if task completed successfully, False otherwise
    """
    project_root = atomic_root.parent
    phase1_dir = output_dir.parent / "1-discovery"

    # Display Phase 2 welcome banner
    _show_phase_welcome()

    print()
    print(print_dim("  ┌─────────────────────────────────────────────────────────┐"))
    print(print_dim("  │ Validating Phase 1 artifacts before proceeding...      │"))
    print(print_dim("  └─────────────────────────────────────────────────────────┘"))
    print()

    # Validate artifacts
    all_valid, missing = validate_phase1_artifacts(phase1_dir, project_root)

    # Handle missing artifacts
    if not all_valid:
        print()
        print(print_red("  Missing required artifacts:"))
        for item in missing:
            print(f"    • {item}")
        print()

        # UAT mode bypass
        if uat_mode:
            print(print_yellow("  UAT mode: Continuing with missing artifacts"))
        else:
            print(print_yellow("  Options:"))
            print("    " + print_dim("[b]") + " Go back to Phase 1")
            print("    " + print_dim("[c]") + " Continue anyway (not recommended)")
            print()

            clear_input_buffer()
            choice = prompt_user("  Choice (default: b): ").strip().lower() or "b"

            if choice in ["c"]:
                print(print_yellow("  ⚠ Continuing with missing artifacts"))
            else:
                print(print_cyan("  → Returning to complete Phase 1 first"))
                return False

    # Load context from Phase 1
    context = load_phase1_context(phase1_dir)

    # Supplement with graph data from Phase 1 (if available)
    if graph:
        try:
            # Query Phase 1 findings and decisions from graph
            phase1_graph_context = graph.query_prd_context(section="vision", max_tokens=4000)
            if phase1_graph_context:
                context["graph_context"] = phase1_graph_context
                logger.info("Loaded Phase 1 context from knowledge graph")
        except Exception as e:
            logger.warning(f"Graph query failed, using file-based context: {e}")

    # Save context summary
    context_file = output_dir / "phase1-context.json"
    write_file(context_file, json.dumps(context, indent=2))

    print(print_green("✓ Entry validation passed"))
    return True


def _show_phase_welcome() -> None:
    """Display Phase 2 welcome banner."""
    print()
    print(print_dim("━" * 90))
    print(print_cyan(r"""
                    _____   ______  _____  ______  _     _ _______ _______
                   |_____] |_____/ |     | |     \ |     | |          |
                   |       |    \_ |_____| |_____/ |_____| |_____     |

 ______ _______  _____  _     _ _____  ______ _______ _______ _______ __   _ _______ _______
|_____/ |______ |   __| |     |   |   |_____/ |______ |  |  | |______ | \  |    |    |______
|    \_ |______ |____\| |_____| __|__ |    \_ |______ |  |  | |______ |  \_|    |    ______|

                  ______   _____  _______ _     _ _______ _______ __   _ _______
                 |     \ |     | |       |     | |  |  | |______ | \  |    |
                 |_____/ |_____| |_____  |_____| |  |  | |______ |  \_|    |
    """))
    print(print_dim("━" * 90))
    print("                                   " + print_bold("[ PHASE 02 - PRD ]"))
    print()


def validate_phase1_artifacts(phase1_dir: Path, project_root: Path = None) -> Tuple[bool, List[str]]:
    """
    Validate Phase 1 artifacts exist.

    Args:
        phase1_dir: Path to Phase 1 output directory
        project_root: Path to the project root (parent of atomic-claude)

    Returns:
        Tuple of (all_valid, missing_items)
    """
    all_valid = True
    missing = []

    print("  " + print_cyan("Phase 1 Closeout:"))

    # Check Phase 1 closeout
    closeout_file = find_closeout(phase1_dir, project_root)
    if closeout_file:
        try:
            with open(closeout_file, 'r') as f:
                closeout_data = json.load(f)
            # Accept multiple indicators of completion:
            #   - "status": "complete" (task_109 format)
            #   - "tasks_completed" key present (orchestrator format)
            #   - valid JSON file exists (minimum bar)
            status = closeout_data.get('status', '')
            has_tasks = 'tasks_completed' in closeout_data
            if status == 'complete' or has_tasks:
                print("    " + print_green("✓") + " Phase 1 closeout found")
            else:
                # File exists with valid JSON — warn but don't block
                print("    " + print_yellow("!") + f" Phase 1 closeout found (status: {status or 'unset'})")
        except Exception as e:
            print("    " + print_red("✗") + f" Phase 1 closeout - error reading: {e}")
            missing.append("Phase 1 closeout (unreadable)")
            all_valid = False
    else:
        print("    " + print_red("✗") + " Phase 1 closeout - NOT FOUND")
        missing.append("Phase 1 closeout")
        all_valid = False

    print()
    print("  " + print_cyan("Phase 1 Artifacts:"))

    # Check selected approach
    approach_file = phase1_dir / "selected-approach.json"
    if approach_file.exists():
        try:
            with open(approach_file, 'r') as f:
                approach_data = json.load(f)
            approach_name = approach_data.get('name', 'unnamed')
            print("    " + print_green("✓") + f" selected-approach.json ({approach_name})")
        except Exception as e:
            logger.debug("Error reading selected-approach.json: %s", e)
            print("    " + print_yellow("!") + " selected-approach.json (error reading)")
    else:
        print("    " + print_red("✗") + " selected-approach.json - NOT FOUND")
        missing.append("selected-approach.json")
        all_valid = False

    # Check corpus (optional)
    corpus_file = phase1_dir / "corpus.json"
    if corpus_file.exists():
        try:
            with open(corpus_file, 'r') as f:
                corpus_data = json.load(f)
            material_count = len(corpus_data.get('materials', []))
            print("    " + print_green("✓") + f" corpus.json ({material_count} materials)")
        except Exception as e:
            logger.debug("Error reading corpus.json: %s", e)
            print("    " + print_yellow("○") + " corpus.json - error reading")
    else:
        print("    " + print_yellow("○") + " corpus.json - not found (optional)")

    # Check dialogue
    dialogue_file = phase1_dir / "dialogue.json"
    if dialogue_file.exists():
        print("    " + print_green("✓") + " dialogue.json")
    else:
        print("    " + print_yellow("○") + " dialogue.json - not found (optional)")

    print()

    return all_valid, missing


def find_closeout(phase_dir: Path, project_root: Path = None) -> Optional[Path]:
    """
    Find closeout file in phase directory.

    Args:
        phase_dir: Path to phase output directory
        project_root: Path to the project root (parent of atomic-claude)

    Returns:
        Path to closeout file if found, None otherwise
    """
    # Try common closeout file patterns
    patterns = [
        "phase-01-closeout.json",
        "phase-1-closeout.json",
        "closeout.json"
    ]

    for pattern in patterns:
        closeout_file = phase_dir / pattern
        if closeout_file.exists():
            return closeout_file

    # Also check in .claude/closeout directory (in project root)
    closeout_base = project_root if project_root else phase_dir.parent.parent.parent
    closeout_dir = closeout_base / ".claude" / "closeout"
    for pattern in patterns:
        closeout_file = closeout_dir / pattern
        if closeout_file.exists():
            return closeout_file

    return None


def load_phase1_context(phase1_dir: Path) -> Dict[str, Any]:
    """
    Load context from Phase 1 artifacts.

    Args:
        phase1_dir: Path to Phase 1 output directory

    Returns:
        Dictionary containing Phase 1 context
    """
    print(print_dim("  Loading context from Phase 1..."))

    context = {
        "loaded_at": datetime.now(timezone.utc).isoformat(),
        "approach": None,
        "vision": None,
        "constraints": [],
        "corpus_materials": 0
    }

    # Extract approach and direction information from selected-approach.json
    # (Task 106 stores the confirmed direction here)
    approach_file = phase1_dir / "selected-approach.json"
    if approach_file.exists():
        try:
            with open(approach_file, 'r') as f:
                approach_data = json.load(f)

            # Extract approach name (varies by mode)
            approach_name = (
                approach_data.get('name')
                or approach_data.get('direction', {}).get('summary', 'unnamed')
            )
            context["approach"] = {
                "name": approach_name,
                "summary": approach_data.get('summary', approach_data.get('direction', {}).get('summary', '')),
                "rationale": approach_data.get('rationale', approach_data.get('direction', {}).get('rationale', ''))
            }
            print("    • Selected approach: " + approach_name)

            # Extract direction/vision (stored in the same file)
            direction = approach_data.get('direction', {})
            if direction:
                context["vision"] = direction.get('summary', '')
                context["constraints"] = approach_data.get('open_items', [])
                key_decisions = approach_data.get('key_decisions', [])
                print(f"    • Direction confirmed ({len(key_decisions)} key decisions)")
        except Exception as e:
            print(print_yellow(f"    ⚠ Error loading approach: {e}"))

    # Extract corpus information
    corpus_file = phase1_dir / "corpus.json"
    if corpus_file.exists():
        try:
            with open(corpus_file, 'r') as f:
                corpus_data = json.load(f)
            context["corpus_materials"] = len(corpus_data.get('materials', []))
        except Exception as e:
            logger.debug("Failed to load corpus data: %s", e)

    print("  " + print_green("✓") + " Context loaded")
    print()

    return context


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 201: Entry Validation")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
