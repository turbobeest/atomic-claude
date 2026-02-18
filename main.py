#!/usr/bin/env python3
"""
Atomic Claude 2.0 - Main Entry Point

Python-based SDLC pipeline orchestrator.
"""

import sys
import argparse
import readline  # Enable arrow keys, history, and line editing in input()
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.state import StateManager
from orchestration.pipeline import PhasePipeline, TransitionMode, PHASE_REGISTRY
from orchestration.backtrack import backtrack_to

# Phase names for display
PHASE_NAMES = {
    0: "Setup",
    1: "Discovery",
    2: "PRD",
    3: "Tasking",
    4: "Specification",
    5: "Implementation",
    6: "Code Review",
    7: "Integration",
    8: "Deployment Prep",
    9: "Release"
}


def run_phase(phase_num: int, resume_at: str = None):
    """Run a specific phase using PhasePipeline for transitions."""
    if phase_num not in PHASE_NAMES:
        print(f"Invalid phase number: {phase_num}")
        print("   Valid phases: 0-9")
        print()
        print("   Available phases:")
        for num, name in sorted(PHASE_NAMES.items()):
            print(f"     {num}: {name}")
        print()
        print("   Usage: python main.py run <phase>")
        print("   Example: python main.py run 0")
        sys.exit(1)

    pipeline = PhasePipeline(atomic_root=Path(__file__).parent)
    success = pipeline.run_phase(
        phase_num,
        resume_at=resume_at,
        transition_mode=TransitionMode.PROMPT,
    )

    if not success:
        print(f"\nTo resume: python main.py run {phase_num} --resume-at=<task>")
        sys.exit(1)


def show_status():
    """Show current pipeline status."""
    state = StateManager()

    print("\n" + "="*80)
    print("  ATOMIC CLAUDE 2.0 - PIPELINE STATUS")
    print("="*80 + "\n")

    state.display_status()


def do_backtrack(phase_num: int, task: str = None):
    """Backtrack to a specific phase/task."""
    if phase_num not in PHASE_NAMES:
        print(f"Invalid phase number: {phase_num}")
        print("   Valid phases: 0-9")
        sys.exit(1)

    backtrack_to(phase_num, task)


def do_reset():
    """Full pipeline reset."""
    import shutil

    print("\n" + "="*80)
    print("  FULL PIPELINE RESET")
    print("="*80)
    print("\n  This will delete ALL state, outputs, and memory.")

    confirm = input("\n  Type 'yes' to confirm: ")
    if confirm.lower() != "yes":
        print("  Cancelled.")
        return

    root = Path(__file__).parent

    # Stop dashboard processes before clearing state (PID files live in .state/)
    try:
        from orchestration.dashboard_sync import stop_dashboard
        print("  Stopping dashboard...")
        stop_dashboard(root)
    except Exception:
        pass

    project_root = root.parent
    for d in [root / ".state", project_root / ".outputs", root / ".logs"]:
        if d.exists():
            shutil.rmtree(d)
            print(f"  Cleared {d.name}/")

    print("\n  Reset complete. Start fresh with: python main.py run 0")


def main():
    parser = argparse.ArgumentParser(
        description="Atomic Claude 2.0 - SDLC Pipeline Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py run 0                   # Run Phase 0 (Setup)
  python main.py run 2 --resume-at=205   # Resume Phase 2 from Task 205
  python main.py status                  # Show pipeline status
  python main.py backtrack 1             # Reset to Phase 1, clear Phase 2+
  python main.py backtrack 0 005         # Reset Phase 0 to Task 005
  python main.py reset                   # Full reset (clears everything)
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run a phase")
    run_parser.add_argument("phase", type=int, help="Phase number (0-9)")
    run_parser.add_argument(
        "--resume-at",
        help="Resume from task (e.g., 205)"
    )

    # Status command
    subparsers.add_parser("status", help="Show pipeline status")

    # Backtrack command
    backtrack_parser = subparsers.add_parser("backtrack", help="Reset to an earlier phase/task")
    backtrack_parser.add_argument("phase", type=int, help="Phase number to reset to (0-9)")
    backtrack_parser.add_argument("task", nargs="?", default=None, help="Optional task ID (e.g., 005)")

    # Reset command
    subparsers.add_parser("reset", help="Full pipeline reset")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "run":
        run_phase(args.phase, args.resume_at)
    elif args.command == "status":
        show_status()
    elif args.command == "backtrack":
        do_backtrack(args.phase, args.task)
    elif args.command == "reset":
        do_reset()


if __name__ == "__main__":
    main()
