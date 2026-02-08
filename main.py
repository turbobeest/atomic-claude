#!/usr/bin/env python3
"""
Atomic Claude 2.0 - Main Entry Point

Python-based SDLC pipeline orchestrator.
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.state import StateManager

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
    """Run a specific phase."""
    if phase_num not in PHASE_NAMES:
        print(f"❌ Invalid phase number: {phase_num}")
        print("   Valid phases: 0-9")
        print()
        print("   Available phases:")
        for num, name in sorted(PHASE_NAMES.items()):
            print(f"     {num}: {name}")
        print()
        print("   Usage: python main.py run <phase>")
        print("   Example: python main.py run 0")
        sys.exit(1)

    phase_name = PHASE_NAMES[phase_num]
    print(f"\n{'='*80}")
    print(f"  ATOMIC CLAUDE 2.0 - Phase {phase_num}: {phase_name.upper()}")
    print(f"{'='*80}\n")

    try:
        # Import phase orchestrator dynamically
        phase_module = __import__(
            f"phases.phase{phase_num:02d}.orchestrator{phase_num:02d}",
            fromlist=["run_phase"]
        )

        # Execute
        success = phase_module.run_phase(resume_at=resume_at)

        if not success:
            print(f"\n⚠️  Phase {phase_num} stopped.")
            print(f"To resume:")
            print(f"   python main.py run {phase_num} --resume-at=<task>")
            sys.exit(1)

        print(f"\n✅ Phase {phase_num} complete!")

    except ImportError as e:
        print(f"❌ Could not load Phase {phase_num} orchestrator")
        print(f"   Error: {e}")
        print(f"   Expected: phases/phase{phase_num:02d}/orchestrator{phase_num:02d}.py")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Phase {phase_num} error: {e}")
        sys.exit(1)


def show_status():
    """Show current pipeline status."""
    state = StateManager()

    print("\n" + "="*80)
    print("  ATOMIC CLAUDE 2.0 - PIPELINE STATUS")
    print("="*80 + "\n")

    state.display_status()


def main():
    parser = argparse.ArgumentParser(
        description="Atomic Claude 2.0 - SDLC Pipeline Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py run 0              # Run Phase 0 (Setup)
  python main.py run 2 --resume-at=205  # Resume Phase 2 from Task 205
  python main.py status             # Show pipeline status
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

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "run":
        run_phase(args.phase, args.resume_at)
    elif args.command == "status":
        show_status()


if __name__ == "__main__":
    main()
