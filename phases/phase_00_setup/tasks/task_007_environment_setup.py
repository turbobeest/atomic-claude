"""
Task 007: Environment Setup

List required/recommended dependencies and give user opportunity to install.

Features:
- Auto-detects OS for relevant install commands
- Version checking (node >= 18, etc.)
- Project-specific dependencies from package.json, requirements.txt, etc.
- Language-specific tools based on detected project type
- Blocks if required tools are missing
- Airgapped environment support notes
- Status summary with counts
- Records environment status to context
"""

import os
import sys
import json
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.config import Config
from core.state import StateManager
from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user, clear_input_buffer
)
from core.utils.file_ops import ensure_dir, read_file, write_file


# Global counters for summary
REQUIRED_TOTAL = 0
REQUIRED_INSTALLED = 0
RECOMMENDED_TOTAL = 0
RECOMMENDED_INSTALLED = 0


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 007: Environment Setup.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    global REQUIRED_TOTAL, REQUIRED_INSTALLED, RECOMMENDED_TOTAL, RECOMMENDED_INSTALLED

    config_file = output_dir / "project-config.json"

    print()
    print_cyan("Environment Setup")
    print()

    # Reset counters
    REQUIRED_TOTAL = 0
    REQUIRED_INSTALLED = 0
    RECOMMENDED_TOTAL = 0
    RECOMMENDED_INSTALLED = 0

    # Show info box
    _show_info_box()

    # Detect OS
    os_type = _detect_os()
    print_dim(f"  Detected OS: {os_type}")
    print()

    # Core required tools
    _show_required_tools(os_type)

    # Recommended tools
    _show_recommended_tools(os_type)

    # Show quick install commands if needed
    if REQUIRED_INSTALLED < REQUIRED_TOTAL:
        _show_quick_install(os_type)

    # Airgapped note
    _show_airgap_note()

    # Summary
    _show_summary()

    print_dim("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()

    # Check if required tools are missing
    missing = REQUIRED_TOTAL - REQUIRED_INSTALLED

    if missing > 0:
        print_red(f"  Cannot proceed with {missing} missing required tool(s).")
        print()
        if uat_mode:
            print_yellow("  UAT Mode: Continuing despite missing tools")
            return True

        print_yellow("  Open another terminal to install missing tools.")
        print_yellow("  When ready, return here and press Enter to re-check.")
        print()

        # Loop until all required tools are installed
        while missing > 0:
            clear_input_buffer()
            prompt_user("Press Enter to re-check environment... ")
            print()

            # Re-check required tools
            REQUIRED_TOTAL = 0
            REQUIRED_INSTALLED = 0
            _recheck_required(os_type)

            missing = REQUIRED_TOTAL - REQUIRED_INSTALLED
            if missing > 0:
                print_red(f"  Still missing {missing} required tool(s).")
                print()

        print_green("  All required tools now installed.")
        print()
    else:
        print_green("  All required tools installed.")
        print()
        if not uat_mode:
            clear_input_buffer()
            prompt_user("Press Enter to continue... ")

    # Record to context
    _record_context(config_file)

    print_green("✓ Environment validated")
    return True


def _show_info_box() -> None:
    """Show informational box."""
    print_dim("  ┌─────────────────────────────────────────────────────────┐")
    print_dim("  │ Before proceeding, ensure you have the required tools.  │")
    print_dim("  │                                                         │")
    print_dim("  │ Open another terminal to install any missing tools,     │")
    print_dim("  │ then return here and press Enter to continue.           │")
    print_dim("  └─────────────────────────────────────────────────────────┘")
    print()


def _detect_os() -> str:
    """
    Detect operating system.

    Returns:
        OS type (macos, debian, redhat, arch, linux, windows, unknown)
    """
    import platform
    system = platform.system()

    if system == "Darwin":
        return "macos"
    elif system == "Linux":
        if Path("/etc/debian_version").exists():
            return "debian"
        elif Path("/etc/redhat-release").exists():
            return "redhat"
        elif Path("/etc/arch-release").exists():
            return "arch"
        else:
            return "linux"
    elif system == "Windows":
        return "windows"
    else:
        return "unknown"


def _check_tool(tool: str) -> Optional[str]:
    """
    Check if tool is installed and get version.

    Args:
        tool: Tool name

    Returns:
        Version string or None if not installed
    """
    if not shutil.which(tool):
        return None

    try:
        if tool == "git":
            result = subprocess.run([tool, "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.split()[2]
        elif tool == "jq":
            result = subprocess.run([tool, "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip().replace("jq-", "")
        elif tool == "node":
            result = subprocess.run([tool, "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip().lstrip('v')
        elif tool == "claude":
            result = subprocess.run([tool, "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip().split()[-1] if result.stdout.strip() else "installed"
        elif tool == "task-master":
            return "installed"  # No version command
        elif tool == "dot":
            result = subprocess.run([tool, "-V"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                parts = result.stdout.split()
                for i, part in enumerate(parts):
                    if part == "version" and i + 1 < len(parts):
                        return parts[i + 1]
        else:
            result = subprocess.run([tool, "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.split()[0] if result.stdout else "installed"
    except:
        pass

    return "installed"


def _get_install_cmd(tool: str, os_type: str) -> str:
    """
    Get install command for tool on given OS.

    Args:
        tool: Tool name
        os_type: OS type

    Returns:
        Install command string
    """
    commands = {
        "git": {
            "macos": "brew install git",
            "debian": "sudo apt install git",
            "redhat": "sudo dnf install git",
            "arch": "sudo pacman -S git",
            "windows": "winget install Git.Git",
        },
        "jq": {
            "macos": "brew install jq",
            "debian": "sudo apt install jq",
            "redhat": "sudo dnf install jq",
            "arch": "sudo pacman -S jq",
            "windows": "winget install jqlang.jq",
        },
        "node": {
            "macos": "brew install node",
            "debian": "curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install nodejs",
            "redhat": "curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash - && sudo dnf install nodejs",
            "arch": "sudo pacman -S nodejs npm",
            "windows": "winget install OpenJS.NodeJS.LTS",
        },
        "claude": {"*": "npm install -g @anthropic-ai/claude-code"},
        "task-master": {"*": "npm install -g task-master-ai"},
        "dot": {
            "macos": "brew install graphviz",
            "debian": "sudo apt install graphviz",
            "redhat": "sudo dnf install graphviz",
            "arch": "sudo pacman -S graphviz",
            "windows": "winget install Graphviz.Graphviz",
        },
    }

    tool_cmds = commands.get(tool, {})
    return tool_cmds.get(os_type, tool_cmds.get("*", "See tool website"))


def _show_required_tools(os_type: str) -> None:
    """Show required tools and their status."""
    global REQUIRED_TOTAL, REQUIRED_INSTALLED

    print_cyan("  REQUIRED TOOLS:")
    print()

    tools = [
        ("git", None),
        ("jq", None),
        ("node", 18),  # Minimum version
        ("claude", None),
        ("task-master", None),
        ("dot", None),  # graphviz
    ]

    for tool, min_version in tools:
        REQUIRED_TOTAL += 1
        version = _check_tool(tool)

        if version:
            # Check version if minimum specified
            if min_version and tool == "node":
                major = int(version.split('.')[0])
                if major >= min_version:
                    print_green(f"    ✓ {tool} (v{version})")
                    REQUIRED_INSTALLED += 1
                else:
                    print_yellow(f"    ! {tool} (v{version}) - v{min_version}+ required")
                    print_dim(f"      {_get_install_cmd(tool, os_type)}")
            else:
                print_green(f"    ✓ {tool} ({version})")
                REQUIRED_INSTALLED += 1
        else:
            tool_name = "graphviz" if tool == "dot" else tool
            print_red(f"    ✗ {tool_name} - REQUIRED")
            print_dim(f"      {_get_install_cmd(tool, os_type)}")

    print()


def _recheck_required(os_type: str) -> None:
    """Recheck required tools (silent, just updates counters)."""
    global REQUIRED_TOTAL, REQUIRED_INSTALLED

    tools = ["git", "jq", "node", "claude", "task-master", "dot"]

    for tool in tools:
        REQUIRED_TOTAL += 1
        version = _check_tool(tool)
        if version:
            if tool == "node":
                try:
                    major = int(version.split('.')[0])
                    if major >= 18:
                        REQUIRED_INSTALLED += 1
                except:
                    pass
            else:
                REQUIRED_INSTALLED += 1


def _show_recommended_tools(os_type: str) -> None:
    """Show recommended tools and their status."""
    global RECOMMENDED_TOTAL, RECOMMENDED_INSTALLED

    print_cyan("  RECOMMENDED TOOLS:")
    print()

    tools = ["gh", "docker"]

    for tool in tools:
        RECOMMENDED_TOTAL += 1
        version = _check_tool(tool)

        if version:
            print_green(f"    ✓ {tool} ({version})")
            RECOMMENDED_INSTALLED += 1
        else:
            desc = "GitHub CLI" if tool == "gh" else "Containerized deployment"
            print_yellow(f"    ○ {tool} - {desc}")
            print_dim(f"      {_get_install_cmd(tool, os_type)}")

    print()


def _show_quick_install(os_type: str) -> None:
    """Show quick install commands for missing tools."""
    print_cyan("  QUICK INSTALL:")
    print()

    if os_type == "macos":
        print_dim("    # All required tools:")
        print_bold("    brew install git jq node graphviz")
        print_bold("    npm install -g @anthropic-ai/claude-code task-master-ai")
    elif os_type == "debian":
        print_dim("    # All required tools:")
        print_bold("    sudo apt update && sudo apt install -y git jq graphviz")
        print_bold("    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -")
        print_bold("    sudo apt install -y nodejs")
        print_bold("    npm install -g @anthropic-ai/claude-code task-master-ai")
    elif os_type == "windows":
        print_dim("    # All required tools (PowerShell as Admin):")
        print_bold("    winget install Git.Git jqlang.jq OpenJS.NodeJS.LTS Graphviz.Graphviz")
        print_bold("    npm install -g @anthropic-ai/claude-code task-master-ai")
    else:
        print_dim("    See tool-specific install commands above")

    print()


def _show_airgap_note() -> None:
    """Show airgapped environment note."""
    print_dim("  ┌─────────────────────────────────────────────────────────┐")
    print_dim("  │ Airgapped Environment?                                  │")
    print_dim("  │                                                         │")
    print_dim("  │ Download these packages on a connected machine:         │")
    print_dim("  │   npm pack @anthropic-ai/claude-code                    │")
    print_dim("  │   npm pack task-master-ai                               │")
    print_dim("  │                                                         │")
    print_dim("  │ Transfer .tgz files and install with:                   │")
    print_dim("  │   npm install -g ./anthropic-ai-claude-code-*.tgz       │")
    print_dim("  │   npm install -g ./task-master-ai-*.tgz                 │")
    print_dim("  └─────────────────────────────────────────────────────────┘")
    print()


def _show_summary() -> None:
    """Show status summary."""
    print_dim("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()

    # Required status
    if REQUIRED_INSTALLED == REQUIRED_TOTAL:
        print_green(f"  ✓ Required: {REQUIRED_INSTALLED}/{REQUIRED_TOTAL} installed")
    else:
        missing = REQUIRED_TOTAL - REQUIRED_INSTALLED
        print_red(f"  ✗ Required: {REQUIRED_INSTALLED}/{REQUIRED_TOTAL} installed ({missing} missing)")

    # Recommended status
    print_dim(f"  ○ Recommended: {RECOMMENDED_INSTALLED}/{RECOMMENDED_TOTAL} installed")
    print()


def _record_context(config_file: Path) -> None:
    """Record environment status to context."""
    missing = REQUIRED_TOTAL - REQUIRED_INSTALLED
    status_msg = f"Environment: {REQUIRED_INSTALLED}/{REQUIRED_TOTAL} required tools"

    if missing > 0:
        status_msg += f", {missing} missing"
    else:
        status_msg += ", all present"

    # Update config with environment status
    config = json.loads(read_file(config_file))
    config['environment'] = {
        "required_total": REQUIRED_TOTAL,
        "required_installed": REQUIRED_INSTALLED,
        "recommended_total": RECOMMENDED_TOTAL,
        "recommended_installed": RECOMMENDED_INSTALLED,
        "checked_at": datetime.now().isoformat()
    }
    write_file(config_file, json.dumps(config, indent=2))


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 007: Environment Setup")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
