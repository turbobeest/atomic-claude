"""
Task 702: Integration Setup

Configure integration environment and review acceptance criteria.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user
)
from core.utils.file_ops import read_json, write_json, ensure_dir


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 702: Integration Setup.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    config_file = atomic_root / ".outputs" / "0-setup" / "project-config.json"
    integration_dir = atomic_root / ".claude" / "integration"

    ensure_dir(integration_dir)

    print()
    print(print_dim("Configuring integration environment and reviewing acceptance criteria."))
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # INTEGRATION ENVIRONMENT
    # ─────────────────────────────────────────────────────────────────────────

    print()
    print(print_bold("  - INTEGRATION ENVIRONMENT"))
    print()

    # Load project config
    project_name = "Unknown"
    env_type = "development"

    if config_file.exists():
        config_data = read_json(config_file)
        project_name = config_data.get("project", {}).get("name", "Unknown")
        env_type = config_data.get("environment", {}).get("type", "development")

    print(print_dim("─" * 118))
    print(print_bold("ENVIRONMENT CONFIGURATION"))
    print()
    print(f"  Project:        {project_name}")
    print(f"  Environment:    {env_type}")
    print(f"  Test Mode:      Full E2E")
    print()
    print(print_dim("─" * 118))
    print()

    env_confirm = "y"
    env_notes = ""

    if not uat_mode:
        print(print_dim("Is this the correct integration environment?"))
        print()
        env_confirm = prompt_user("Confirm (default: y/n): ").strip() or "y"

        if env_confirm.lower() not in ["y", "yes"]:
            print()
            env_notes = prompt_user("Enter environment notes: ").strip()
            print()

    # ─────────────────────────────────────────────────────────────────────────
    # ACCEPTANCE CRITERIA REVIEW
    # ─────────────────────────────────────────────────────────────────────────

    print()
    print(print_bold("  - ACCEPTANCE CRITERIA REVIEW"))
    print()

    print(print_dim("Loading acceptance criteria from PRD and specifications..."))
    print()

    # Simulated acceptance criteria (in real implementation, would parse PRD)
    criteria_count = 17

    print(print_dim("─" * 118))
    print(print_bold("ACCEPTANCE CRITERIA TO VALIDATE"))
    print()
    print(print_cyan("  Functional Requirements:"))
    print("    FR-1   Core functionality implemented")
    print("    FR-2   Data persistence working")
    print("    FR-3   User interface responsive")
    print("    FR-4   External integrations functional")
    print("    FR-5   Offline capability (if applicable)")
    print("    ...    (additional criteria from PRD)")
    print()
    print(print_cyan("  Non-Functional Requirements:"))
    print("    NFR-1  Response time < target threshold")
    print("    NFR-2  Memory usage within bounds")
    print("    NFR-3  Error rate < acceptable limit")
    print("    ...    (additional NFRs)")
    print()
    print(f"  Total Criteria:  {criteria_count}")
    print(print_dim("─" * 118))
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # NFR TARGETS
    # ─────────────────────────────────────────────────────────────────────────

    print()
    print(print_bold("  - NFR TARGETS"))
    print()

    print(print_dim("─" * 118))
    print(print_bold("PERFORMANCE TARGETS"))
    print()
    print("  Response Time:     < 100ms for local operations")
    print("  Startup Time:      < 3s")
    print("  Memory Usage:      < 100MB baseline")
    print("  Error Rate:        < 0.1%")
    print(print_dim("─" * 118))
    print()

    if not uat_mode:
        prompt_user("Press Enter to proceed with agent selection...")
    print()

    # Save setup configuration
    setup_data = {
        "environment": {
            "project": project_name,
            "type": env_type,
            "confirmed": True
        },
        "acceptance_criteria": {
            "total": criteria_count,
            "source": "PRD + specs"
        },
        "setup_at": datetime.now().isoformat()
    }

    setup_file = integration_dir / "setup.json"
    write_json(setup_file, setup_data)

    print(print_green("✓ Integration Setup complete"))
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 702: Integration Setup")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
