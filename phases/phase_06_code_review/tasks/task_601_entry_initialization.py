"""
Task 601: Entry & Initialization

Welcome to Phase 6, verify Phase 5 completion, display review overview.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, print_magenta, prompt_user, clear_input_buffer
)
from core.utils.file_ops import ensure_dir, read_file, write_file


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None) -> bool:
    """
    Execute Task 601: Entry & Initialization.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    project_root = atomic_root.parent

    # Find Phase 5 closeout
    closeout_file = _find_closeout(atomic_root, project_root, "5-implementation")

    # Display phase header
    _display_phase_header()

    # UAT Mode Bypass
    if uat_mode:
        print(print_yellow("UAT Mode: Creating minimal valid output"))
        entry_context = output_dir / "entry-context.json"
        ensure_dir(entry_context.parent)
        write_file(entry_context, json.dumps({
            "status": "initialized",
            "phase": "6-code-review",
            "timestamp": datetime.now().isoformat()
        }, indent=2))
        print(print_green("✓ UAT bypass complete"))
        return True

    # Phase 5 Verification
    if not _verify_phase_5(closeout_file):
        return False

    # Display Code Review Overview
    _display_code_review_overview()

    # Display Review Dimensions
    _display_review_dimensions()

    # Display Phase 6 Tasks
    _display_phase_tasks()

    # Wait for user
    print()
    clear_input_buffer()
    prompt_user("Press Enter to begin Code Review...")
    print()

    print(print_green("✓ Entry & Initialization complete"))
    return True


def _find_closeout(atomic_root: Path, project_root: Path, phase_name: str) -> Path:
    """Find closeout file for a phase."""
    # Try new format first
    closeout_file = atomic_root.parent / ".outputs" / phase_name / "closeout.json"
    if closeout_file.exists():
        return closeout_file

    # Try legacy format
    closeout_file = project_root / ".claude" / "closeout" / f"{phase_name}-closeout.json"
    if closeout_file.exists():
        return closeout_file

    return atomic_root.parent / ".outputs" / phase_name / "closeout.json"


def _display_phase_header() -> None:
    """Display the Phase 6 header."""
    print()
    print(print_dim("━" * 110))
    print(print_cyan("  PHASE 06 - CODE REVIEW"))
    print(print_dim("━" * 110))
    print()
    print(print_bold(print_cyan("""
   ██████╗ ██████╗ ██████╗ ███████╗    ██████╗ ███████╗██╗   ██╗██╗███████╗██╗    ██╗
  ██╔════╝██╔═══██╗██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║██║██╔════╝██║    ██║
  ██║     ██║   ██║██║  ██║█████╗      ██████╔╝█████╗  ██║   ██║██║█████╗  ██║ █╗ ██║
  ██║     ██║   ██║██║  ██║██╔══╝      ██╔══██╗██╔══╝  ╚██╗ ██╔╝██║██╔══╝  ██║███╗██║
  ╚██████╗╚██████╔╝██████╔╝███████╗    ██║  ██║███████╗ ╚████╔╝ ██║███████╗╚███╔███╔╝
   ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝    ╚═╝  ╚═╝╚══════╝  ╚═══╝  ╚═╝╚══════╝ ╚══╝╚══╝
    """)))

    print()
    print(print_dim("━" * 110))
    print()


def _verify_phase_5(closeout_file: Path) -> bool:
    """Verify Phase 5 completion."""
    print(print_dim("─" * 100))
    print()
    print(print_bold("PHASE 5 VERIFICATION"))
    print()

    if not closeout_file.exists():
        print(print_red("✗ Phase 5 closeout not found"))
        print()
        print(print_red("Phase 5 must be completed before starting Phase 6"))
        return False

    # Load closeout data
    try:
        closeout_data = json.loads(read_file(closeout_file))
    except:
        print(print_red("✗ Failed to read Phase 5 closeout"))
        return False

    phase5_status = closeout_data.get("status", "unknown")
    tasks_completed = closeout_data.get("tasks_completed", 0)
    total_tasks = closeout_data.get("total_tasks", 0)
    tests = closeout_data.get("tests", {})
    tests_passing = tests.get("passing", 0)
    total_tests = tests.get("total", 0)
    coverage = closeout_data.get("coverage", {})
    unit_coverage = coverage.get("unit", 0)

    if phase5_status != "complete" and "tasks_completed" not in closeout_data:
        print(print_red(f"✗ Phase 5 status: {phase5_status}"))
        print()
        print(print_red("Phase 5 must be complete before starting Phase 6"))
        return False

    print(print_green("✓ Phase 5 complete"))
    print(print_green(f"✓ TDD cycles completed: {tasks_completed} / {total_tasks}"))
    print(print_green(f"✓ Tests passing: {tests_passing} / {total_tests}"))
    print(print_green(f"✓ Unit coverage: {unit_coverage}%"))
    print()

    return True


def _display_code_review_overview() -> None:
    """Display the code review overview."""
    print(print_dim("─" * 100))
    print()
    print(print_bold("CODE REVIEW OVERVIEW"))
    print()

    print(print_dim("Phase 6 performs comprehensive code review across multiple dimensions:"))
    print()

    print("  ─" * 50)
    print(print_bold("CODE REVIEW PROCESS"))
    print()
    print(print_cyan("    Deep Code Review") + "  ───►")
    print("                            ╲")
    print(print_cyan("    Architecture") + "      ───►  ╲")
    print(print_cyan("    Compliance") + "               ╲")
    print("                              ────►  " + print_green("Code Refiner"))
    print(print_cyan("    Performance") + "       ───►  ╱        " + print_green("(Refinement)"))
    print(print_cyan("    Analysis") + "               ╱")
    print("                            ╱")
    print(print_cyan("    Documentation") + "     ───►")
    print(print_cyan("    Review"))
    print()
    print("  ─" * 50)
    print()


def _display_review_dimensions() -> None:
    """Display review dimensions."""
    print(print_dim("─" * 100))
    print()
    print(print_bold("REVIEW DIMENSIONS"))
    print()

    print(print_cyan("1. Deep Code Review"))
    print(print_dim("   Logic correctness, error handling, edge cases, code clarity"))
    print()
    print(print_cyan("2. Architecture Compliance"))
    print(print_dim("   Pattern adherence, dependency management, separation of concerns"))
    print()
    print(print_cyan("3. Performance Analysis"))
    print(print_dim("   Algorithmic complexity, resource usage, potential bottlenecks"))
    print()
    print(print_cyan("4. Documentation Review"))
    print(print_dim("   Code comments, API docs, README completeness"))
    print()
    print(print_cyan("5. Code Refinement"))
    print(print_dim("   Address findings, apply improvements, maintain test coverage"))
    print()


def _display_phase_tasks() -> None:
    """Display Phase 6 tasks."""
    print(print_dim("─" * 100))
    print()
    print(print_bold("PHASE 6 TASKS"))
    print()

    print(print_dim("    601") + " Entry & Initialization      " + print_green("◄ current"))
    print(print_dim("    602") + " Agent Selection")
    print(print_dim("    603") + " Comprehensive Review")
    print(print_dim("    604") + " Refinement")
    print(print_dim("    605") + " Phase Audit")
    print(print_dim("    606") + " Closeout")
    print()


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 601: Entry & Initialization")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
