"""
Task 802: Deployment Setup

Configure release type, version, and distribution channels.
"""

import sys
import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user
)
from core.utils.file_ops import write_json


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None) -> bool:
    """
    Execute Task 802: Deployment Setup.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    project_root = atomic_root.parent

    deployment_dir = project_root / ".claude" / "deployment"
    setup_file = deployment_dir / "setup.json"

    print(print_bold("Deployment Setup"))
    print()

    deployment_dir.mkdir(parents=True, exist_ok=True)

    # UAT Mode Bypass
    if uat_mode:
        print(print_dim("  UAT Mode: Creating minimal valid output"))
        setup_data = {
            "release_type": "internal",
            "version": "0.1.0",
            "channels": ["internal"],
            "config_confirmed": True
        }
        write_json(setup_file, setup_data)
        print(print_green("✓ UAT bypass complete"))
        return True

    print()
    print(print_dim("  Configuring release type and distribution channels."))
    print()

    # RELEASE TYPE
    print()
    print(print_bold("  - RELEASE TYPE"))
    print()

    print(print_dim("  Select the type of release:"))
    print()
    print("    [1] Major (x.0.0) - Breaking changes, new architecture")
    print("    [2] Minor (0.x.0) - New features, backward compatible")
    print("    [3] Patch (0.0.x) - Bug fixes, minor improvements")
    print()

    release_type_choice = prompt_user("  Select (default: 2): ") or "2"

    release_type_map = {"1": "major", "2": "minor", "3": "patch"}
    release_type = release_type_map.get(release_type_choice, "minor")

    print()

    # VERSION NUMBER
    print()
    print(print_bold("  - VERSION NUMBER"))
    print()

    version_map = {"major": "1.0.0", "minor": "0.1.0", "patch": "0.0.1"}
    default_version = version_map.get(release_type, "0.1.0")

    print(print_dim("  Enter version number (SemVer format):"))
    print()
    version_number = prompt_user(f"  Version (default: {default_version}): ") or default_version

    print()

    # DISTRIBUTION CHANNELS
    print()
    print(print_bold("  - DISTRIBUTION CHANNELS"))
    print()

    print(print_dim("  Select distribution channel:"))
    print()
    print("    [1] Internal only")
    print()

    channel_choice = prompt_user("  Select channel (default: 1): ") or "1"

    channels = []
    if "1" in channel_choice:
        channels.append("internal")

    print()

    # RELEASE CONFIGURATION SUMMARY
    print()
    print(print_bold("  - RELEASE CONFIGURATION"))
    print()

    print("  " + "─" * 110)
    print(print_bold("  RELEASE SETTINGS"))
    print()
    print(f"    Release Type:    {release_type}")
    print(f"    Version:         {version_number}")
    print(f"    Channels:        {', '.join(channels)}")
    print("  " + "─" * 110)
    print()

    print(print_dim("  Confirm this configuration?"))
    print()
    config_confirm = prompt_user("  Confirm (default: y/n): ") or "y"

    if config_confirm.lower() not in ["y", "yes"]:
        print()
        print(print_dim("  Re-running setup..."))
        return execute(atomic_root, output_dir, uat_mode)

    print()

    # Save setup configuration
    setup_data = {
        "release": {
            "type": release_type,
            "version": version_number
        },
        "distribution": {
            "channels": channels
        },
        "configured_at": datetime.now(timezone.utc).isoformat() + "Z"
    }

    write_json(setup_file, setup_data)

    print(print_green("✓ Deployment Setup complete"))

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 802: Deployment Setup")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
