#!/usr/bin/env python3
"""
ATOMIC CLAUDE - Main Entry Point (Python Implementation)
Orchestrates phase execution for software development pipelines
"""

import sys
import argparse
from pathlib import Path
import json

# Add lib to path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR / "atomic-claude-python"))

from lib.atomic import atomic_h1, atomic_info, atomic_success, atomic_error
from lib.provider import ProviderManager

# Paths
ATOMIC_OUTPUT_DIR = ROOT_DIR / ".outputs"
ATOMIC_STATE_DIR = ROOT_DIR / ".state"
PHASES_DIR = ROOT_DIR / "phases"


def cmd_list():
    """List all available phases."""
    atomic_h1("Available Phases")
    print()

    for phase_dir in sorted(PHASES_DIR.glob("*-*/")):
        if (phase_dir / "run.sh").exists():
            phase_id = phase_dir.name
            status = "pending"

            closeout = ATOMIC_OUTPUT_DIR / phase_id / "closeout.json"
            if closeout.exists():
                status = "completed"

            print(f"  {phase_id:<20} [{status}]")
    print()


def cmd_status():
    """Show current pipeline status."""
    atomic_h1("Pipeline Status")

    session_file = ATOMIC_STATE_DIR / "session.json"

    if not session_file.exists():
        print()
        atomic_info("No active session. Run 'python main.py run 0' to begin.")
        return 0

    with open(session_file) as f:
        session = json.load(f)

    print()
    print(f"Session ID:      {session.get('session_id', 'unknown')}")
    print(f"Started:         {session.get('started_at', 'unknown')}")
    print(f"Current Phase:   {session.get('current_phase', 'none')}")
    print(f"Tasks Completed: {session.get('tasks_completed', 0)}")
    print(f"Tasks Failed:    {session.get('tasks_failed', 0)}")
    print()

    print("Phase Status:")
    for phase_dir in sorted(PHASES_DIR.glob("*-*/")):
        phase_id = phase_dir.name
        closeout = ATOMIC_OUTPUT_DIR / phase_id / "closeout.json"
        if closeout.exists():
            print(f"  ✓ {phase_id}")
        else:
            print(f"  ○ {phase_id}")

    print()
    return 0


def cmd_providers():
    """Check provider availability."""
    atomic_h1("Provider Availability")
    print()

    manager = ProviderManager()
    manager.init()

    providers = {
        "Claude Code (max)": manager.check_claude_code(),
        "Anthropic API": manager.check_anthropic(),
        "AWS Bedrock": manager.check_aws_bedrock(),
        "OpenAI API": manager.check_openai(),
        "Google AI": manager.check_google(),
        "Azure OpenAI": manager.check_azure(),
        "OpenRouter": manager.check_openrouter(),
    }

    for name, available in providers.items():
        status = "✓" if available else "✗"
        print(f"  {status} {name}")

    print()
    return 0


def cmd_reset():
    """Reset pipeline state."""
    print("\n⚠ This will reset all pipeline state!")
    response = input("Type 'yes' to confirm: ")

    if response.lower() != "yes":
        atomic_info("Reset cancelled")
        return 0

    import shutil
    if ATOMIC_STATE_DIR.exists():
        for item in ATOMIC_STATE_DIR.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

    claude_dir = ROOT_DIR / ".claude"
    if claude_dir.exists():
        shutil.rmtree(claude_dir)

    atomic_success("Pipeline state reset complete")
    return 0


def cmd_run(phase: str, **kwargs):
    """Run a specific phase."""
    phase_num = phase.lstrip("0")
    phase_names = {
        "0": "setup", "1": "discovery", "2": "prd",
        "3": "tasking", "4": "specification", "5": "implementation",
        "6": "code-review", "7": "integration",
        "8": "deployment-prep", "9": "release",
    }
    
    phase_name = phase_names.get(phase_num, None)
    if not phase_name:
        atomic_error(f"Invalid phase number: {phase}")
        return 1
        
    phase_id = f"{int(phase_num)}-{phase_name}"
    phase_dir = PHASES_DIR / phase_id

    if not phase_dir.exists():
        atomic_error(f"Phase not found: {phase_id}")
        return 1

    # Call bash for now (Python phase runners TODO)
    import subprocess
    bash_runner = phase_dir / "run.sh"

    if bash_runner.exists():
        atomic_info(f"Running phase: {phase_id}")
        result = subprocess.run([str(bash_runner)], cwd=str(phase_dir))
        return result.returncode

    atomic_error(f"No runner found for phase: {phase_id}")
    return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ATOMIC CLAUDE - Script-controlled LLM development pipeline",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    run_parser = subparsers.add_parser("run", help="Run a specific phase")
    run_parser.add_argument("phase", help="Phase number (e.g., 0, 1, 2)")
    run_parser.add_argument("--resume-at", help="Resume from specific task")
    run_parser.add_argument("--redo", action="store_true", help="Force redo all tasks")

    subparsers.add_parser("status", help="Show pipeline status")
    subparsers.add_parser("list", help="List available phases")
    subparsers.add_parser("providers", help="Check provider availability")
    subparsers.add_parser("reset", help="Reset pipeline state")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "run":
        return cmd_run(args.phase, **vars(args))
    elif args.command == "status":
        return cmd_status()
    elif args.command == "list":
        return cmd_list()
    elif args.command == "providers":
        return cmd_providers()
    elif args.command == "reset":
        return cmd_reset()
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
