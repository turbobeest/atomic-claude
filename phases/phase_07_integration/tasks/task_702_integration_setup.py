"""
Task 702: Integration Setup

Configure integration environment and review acceptance criteria.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_green,
    print_dim, print_yellow, prompt_user
)
from core.utils.file_ops import read_json, write_json, ensure_dir


def execute(atomic_root: Path, output_dir: Path, mem=None) -> bool:
    """
    Execute Task 702: Integration Setup.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory

    Returns:
        True if task completed successfully, False otherwise
    """
    project_root = atomic_root.parent

    config_file = atomic_root.parent / ".outputs" / "0-setup" / "project-config.json"
    integration_dir = project_root / ".claude" / "integration"

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
        try:
            config_data = read_json(config_file)
            project_name = config_data.get("project", {}).get("name", "Unknown")
            env_type = config_data.get("environment", {}).get("type", "development")
        except (ValueError, OSError) as e:
            logger.warning("Failed to read project config %s: %s", config_file, e)

    print(print_dim("─" * 118))
    print(print_bold("ENVIRONMENT CONFIGURATION"))
    print()
    print(f"  Project:        {project_name}")
    print(f"  Environment:    {env_type}")
    print(f"  Test Mode:      Full E2E")
    print()
    print(print_dim("─" * 118))
    print()

    env_notes = ""

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

    # SIMULATED: Replace with actual PRD parsing when available
    print(print_yellow("  ⚠ Using simulated acceptance criteria (hardcoded). Real PRD parsing not yet implemented."))
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

    # SIMULATED: Replace with actual NFR targets from PRD when available
    print(print_dim("─" * 118))
    print(print_bold("PERFORMANCE TARGETS"))
    print()
    print("  Response Time:     < 100ms for local operations")
    print("  Startup Time:      < 3s")
    print("  Memory Usage:      < 100MB baseline")
    print("  Error Rate:        < 0.1%")
    print(print_dim("─" * 118))
    print()

    prompt_user("Press Enter to proceed with agent selection...")
    print()

    # Save setup configuration
    env_confirmed = env_confirm.lower() in ["y", "yes"]
    setup_data = {
        "environment": {
            "project": project_name,
            "type": env_type,
            "confirmed": env_confirmed,
            "notes": env_notes,
        },
        "acceptance_criteria": {
            "total": criteria_count,
            "source": "PRD + specs",
            "simulated": True
        },
        "setup_at": datetime.now(timezone.utc).isoformat()
    }

    setup_file = integration_dir / "setup.json"
    write_json(setup_file, setup_data)

    # Also write to output_dir so task_704 can find it (F2 path alignment)
    ensure_dir(output_dir)
    output_setup_file = output_dir / "integration-setup.json"
    write_json(output_setup_file, setup_data)

    print(print_green("✓ Integration Setup complete"))
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 702: Integration Setup")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir)
    sys.exit(0 if success else 1)
