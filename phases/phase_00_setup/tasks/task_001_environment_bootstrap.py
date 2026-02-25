"""
Task 001: Environment Bootstrap

Detect OS, verify required/recommended tools, install dashboard dependencies,
and launch the web companion dashboard.

Features:
- Auto-detects OS for relevant install commands (macOS, Debian, RedHat, Arch, Windows)
- Version checking (node >= 18, etc.)
- Blocks if required tools are missing (loop until installed)
- Installs npm deps for Dashboard, Agent Browser, Audit Browser, Skills Browser
- Runs svelte-kit sync for SvelteKit apps
- Launches the Express dashboard server
- Writes environment section to project-config.json
"""

import logging
import os
import sys
import json
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user, clear_input_buffer
)
from core.utils.file_ops import ensure_dir, write_file


# Global counters for summary
REQUIRED_TOTAL = 0
REQUIRED_INSTALLED = 0
RECOMMENDED_TOTAL = 0
RECOMMENDED_INSTALLED = 0


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None) -> bool:
    """
    Execute Task 001: Environment Bootstrap.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing
        mem: Optional TaskMemory instance for recording substantive memory

    Returns:
        True if task completed successfully, False otherwise
    """
    global REQUIRED_TOTAL, REQUIRED_INSTALLED, RECOMMENDED_TOTAL, RECOMMENDED_INSTALLED

    config_file = output_dir / "project-config.json"

    print()
    print(print_cyan("Environment Bootstrap"))
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
    print(print_dim(f"  Detected OS: {os_type}"))
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

    print(print_dim("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"))
    print()

    # Check if required tools are missing
    missing = REQUIRED_TOTAL - REQUIRED_INSTALLED

    if missing > 0:
        print(print_red(f"  Cannot proceed with {missing} missing required tool(s)."))
        print()
        if uat_mode:
            print(print_yellow("  UAT Mode: Continuing despite missing tools"))
        else:
            print(print_yellow("  Open another terminal to install missing tools."))
            print(print_yellow("  When ready, return here and press Enter to re-check."))
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
                    print(print_red(f"  Still missing {missing} required tool(s)."))
                    print()

            print(print_green("  All required tools now installed."))
            print()
    else:
        print(print_green("  All required tools installed."))
        print()
        if not uat_mode:
            clear_input_buffer()
            prompt_user("Press Enter to continue... ")

    # Install dashboard sub-app dependencies (requires node)
    _install_dashboard_deps(atomic_root)

    # Launch web companion dashboard
    _launch_dashboard(atomic_root)

    # Start FalkorDB knowledge graph
    _start_falkordb(atomic_root, uat_mode)

    # Record environment to config
    _record_environment(config_file, os_type)

    # Record substantive memory
    if mem:
        import platform
        hostname = platform.node()
        mem.finding(f"Platform: {os_type} ({hostname})")
        mem.finding(f"Required tools: {REQUIRED_INSTALLED}/{REQUIRED_TOTAL} verified")
        mem.finding(f"Recommended tools: {RECOMMENDED_INSTALLED}/{RECOMMENDED_TOTAL} available")
        mem.configuration(f"Dashboard launched from {atomic_root / 'dashboard'}")
        mem.configuration("FalkorDB knowledge graph started via docker compose")

    print(print_green("✓ Environment bootstrap complete"))
    return True


# ---------------------------------------------------------------------------
# Info box
# ---------------------------------------------------------------------------

def _show_info_box() -> None:
    """Show informational box."""
    print(print_dim("  ┌─────────────────────────────────────────────────────────┐"))
    print(print_dim("  │ Before proceeding, ensure you have the required tools.  │"))
    print(print_dim("  │                                                         │"))
    print(print_dim("  │ Open another terminal to install any missing tools,     │"))
    print(print_dim("  │ then return here and press Enter to continue.           │"))
    print(print_dim("  └─────────────────────────────────────────────────────────┘"))
    print()


# ---------------------------------------------------------------------------
# OS detection
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Tool checking
# ---------------------------------------------------------------------------

def _check_tool(tool: str) -> Optional[str]:
    """
    Check if tool is installed and get version.

    Args:
        tool: Tool name

    Returns:
        Version string or None if not installed
    """
    # For cargo/rustup, also check $HOME/.cargo/bin (not always on PATH)
    tool_path = shutil.which(tool)
    if not tool_path and tool in ("cargo", "rustup"):
        cargo_bin = Path.home() / ".cargo" / "bin" / tool
        if cargo_bin.exists():
            tool_path = str(cargo_bin)

    if not tool_path:
        return None

    try:
        if tool == "git":
            result = subprocess.run([tool_path, "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.split()[2]
        elif tool == "jq":
            result = subprocess.run([tool_path, "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip().replace("jq-", "")
        elif tool == "node":
            result = subprocess.run([tool_path, "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip().lstrip('v')
        elif tool == "claude":
            result = subprocess.run([tool_path, "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip().split()[-1] if result.stdout.strip() else "installed"
        elif tool == "task-master":
            return "installed"  # Legacy — no longer required
        elif tool == "dot":
            result = subprocess.run([tool_path, "-V"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                parts = result.stdout.split()
                for i, part in enumerate(parts):
                    if part == "version" and i + 1 < len(parts):
                        return parts[i + 1]
        elif tool in ("cargo", "rustup"):
            result = subprocess.run([tool_path, "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # "cargo 1.93.1 (...)" or "rustup 1.27.1 (...)"
                parts = result.stdout.strip().split()
                return parts[1] if len(parts) >= 2 else "installed"
        else:
            result = subprocess.run([tool_path, "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.split()[0] if result.stdout else "installed"
    except (subprocess.SubprocessError, OSError, ValueError):
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
        "rustup": {
            "macos": "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh",
            "debian": "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh",
            "redhat": "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh",
            "arch": "sudo pacman -S rustup && rustup default stable",
            "windows": "winget install Rustlang.Rustup",
            "*": "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh",
        },
        "cargo": {
            "*": "Install via rustup: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh",
        },
        "tmux": {
            "macos": "brew install tmux",
            "debian": "sudo apt install tmux",
            "redhat": "sudo dnf install tmux",
            "arch": "sudo pacman -S tmux",
            "windows": "See https://github.com/tmux/tmux/wiki/Installing",
        },
    }

    tool_cmds = commands.get(tool, {})
    return tool_cmds.get(os_type, tool_cmds.get("*", "See tool website"))


def _show_required_tools(os_type: str) -> None:
    """Show required tools and their status."""
    global REQUIRED_TOTAL, REQUIRED_INSTALLED

    print(print_cyan("  REQUIRED TOOLS:"))
    print()

    tools = [
        ("git", None),
        ("jq", None),
        ("node", 18),  # Minimum version
        ("claude", None),
        ("docker", None),  # Required for FalkorDB knowledge graph
        ("tmux", None),
        ("dot", None),  # graphviz
        ("cargo", None),  # Rust toolchain (installed via rustup)
    ]

    for tool, min_version in tools:
        REQUIRED_TOTAL += 1
        version = _check_tool(tool)

        if version:
            # Check version if minimum specified
            if min_version and tool == "node":
                major = int(version.split('.')[0])
                if major >= min_version:
                    print(print_green(f"    ✓ {tool} (v{version})"))
                    REQUIRED_INSTALLED += 1
                else:
                    print(print_yellow(f"    ! {tool} (v{version}) - v{min_version}+ required"))
                    print(print_dim(f"      {_get_install_cmd(tool, os_type)}"))
            else:
                if tool == "cargo":
                    # Show PATH hint if cargo found in ~/.cargo/bin but not on PATH
                    if not shutil.which("cargo"):
                        print(print_green(f"    ✓ {tool} ({version})") + print_dim("  — found in ~/.cargo/bin"))
                        print(print_dim("      Add to PATH: source \"$HOME/.cargo/env\""))
                    else:
                        print(print_green(f"    ✓ {tool} ({version})"))
                    REQUIRED_INSTALLED += 1
                else:
                    print(print_green(f"    ✓ {tool} ({version})"))
                    REQUIRED_INSTALLED += 1
        else:
            tool_name = "graphviz" if tool == "dot" else tool
            if tool == "cargo":
                tool_name = "cargo (Rust toolchain)"
            print(print_red(f"    ✗ {tool_name} - REQUIRED"))
            print(print_dim(f"      {_get_install_cmd(tool, os_type)}"))

    print()


def _recheck_required(os_type: str) -> None:
    """Recheck required tools (silent, just updates counters)."""
    global REQUIRED_TOTAL, REQUIRED_INSTALLED

    tools = ["git", "jq", "node", "claude", "docker", "tmux", "dot", "cargo"]

    for tool in tools:
        REQUIRED_TOTAL += 1
        version = _check_tool(tool)
        if version:
            if tool == "node":
                try:
                    major = int(version.split('.')[0])
                    if major >= 18:
                        REQUIRED_INSTALLED += 1
                except Exception as e:
                    logger.debug("Failed to parse node version: %s", e)
            else:
                REQUIRED_INSTALLED += 1


def _show_recommended_tools(os_type: str) -> None:
    """Show recommended tools and their status."""
    global RECOMMENDED_TOTAL, RECOMMENDED_INSTALLED

    print(print_cyan("  RECOMMENDED TOOLS:"))
    print()

    tools = ["gh"]

    for tool in tools:
        RECOMMENDED_TOTAL += 1
        version = _check_tool(tool)

        if version:
            print(print_green(f"    ✓ {tool} ({version})"))
            RECOMMENDED_INSTALLED += 1
        else:
            descs = {
                "gh": "GitHub CLI",
                "docker": "Required for FalkorDB knowledge graph",
            }
            desc = descs.get(tool, tool)
            print(print_yellow(f"    ○ {tool} - {desc}"))
            print(print_dim(f"      {_get_install_cmd(tool, os_type)}"))

    print()


def _show_quick_install(os_type: str) -> None:
    """Show quick install commands for missing tools."""
    print(print_cyan("  QUICK INSTALL:"))
    print()

    if os_type == "macos":
        print(print_dim("    # All required tools:"))
        print(print_bold("    brew install git jq node graphviz"))
        print(print_bold("    npm install -g @anthropic-ai/claude-code"))
        print(print_bold("    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"))
    elif os_type == "debian":
        print(print_dim("    # All required tools:"))
        print(print_bold("    sudo apt update && sudo apt install -y git jq graphviz"))
        print(print_bold("    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -"))
        print(print_bold("    sudo apt install -y nodejs"))
        print(print_bold("    npm install -g @anthropic-ai/claude-code"))
        print(print_bold("    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"))
    elif os_type == "windows":
        print(print_dim("    # All required tools (PowerShell as Admin):"))
        print(print_bold("    winget install Git.Git jqlang.jq OpenJS.NodeJS.LTS Graphviz.Graphviz Rustlang.Rustup"))
        print(print_bold("    npm install -g @anthropic-ai/claude-code"))
    else:
        print(print_dim("    See tool-specific install commands above"))

    print()


def _show_airgap_note() -> None:
    """Show airgapped environment note."""
    print(print_dim("  ┌─────────────────────────────────────────────────────────┐"))
    print(print_dim("  │ Airgapped Environment?                                  │"))
    print(print_dim("  │                                                         │"))
    print(print_dim("  │ Download these packages on a connected machine:         │"))
    print(print_dim("  │   npm pack @anthropic-ai/claude-code                    │"))
    print(print_dim("  │                                                         │"))
    print(print_dim("  │ Transfer .tgz files and install with:                   │"))
    print(print_dim("  │   npm install -g ./anthropic-ai-claude-code-*.tgz       │"))
    print(print_dim("  └─────────────────────────────────────────────────────────┘"))
    print()


def _show_summary() -> None:
    """Show status summary."""
    print(print_dim("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"))
    print()

    # Required status
    if REQUIRED_INSTALLED == REQUIRED_TOTAL:
        print(print_green(f"  ✓ Required: {REQUIRED_INSTALLED}/{REQUIRED_TOTAL} installed"))
    else:
        missing = REQUIRED_TOTAL - REQUIRED_INSTALLED
        print(print_red(f"  ✗ Required: {REQUIRED_INSTALLED}/{REQUIRED_TOTAL} installed ({missing} missing)"))

    # Recommended status
    print(print_dim(f"  ○ Recommended: {RECOMMENDED_INSTALLED}/{RECOMMENDED_TOTAL} installed"))
    print()


# ---------------------------------------------------------------------------
# Dashboard dependencies
# ---------------------------------------------------------------------------

def _install_dashboard_deps(atomic_root: Path) -> None:
    """Install npm dependencies for the dashboard and browser sub-apps."""
    print()
    print(print_cyan("  DASHBOARD COMPONENTS:"))
    print()

    subapps = [
        ("Dashboard",       atomic_root / "dashboard"),
        ("Agent Browser",   atomic_root / "agents"  / "agent-manager"),
        ("Audit Browser",   atomic_root / "audits"  / "audit-browser"),
        ("Skills Browser",  atomic_root / "skills"  / "skills-browser"),
    ]

    for name, app_dir in subapps:
        pkg = app_dir / "package.json"
        if not pkg.exists():
            print(print_dim(f"    ○ {name} — no package.json, skipped"))
            continue

        node_modules = app_dir / "node_modules"
        if node_modules.exists():
            print(print_green(f"    ✓ {name} — dependencies installed"))
            continue

        # Install
        print(print_dim(f"    ⚙ {name} — installing dependencies..."), end="", flush=True)
        try:
            result = subprocess.run(
                ["npm", "install", "--silent"],
                cwd=str(app_dir),
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                print(f"\r" + print_green(f"    ✓ {name} — dependencies installed"))
            else:
                print(f"\r" + print_yellow(f"    ! {name} — npm install failed"))
        except subprocess.TimeoutExpired:
            print(f"\r" + print_yellow(f"    ! {name} — npm install timed out"))
        except Exception as e:
            print(f"\r" + print_yellow(f"    ! {name} — {e}"))

    # Run svelte-kit sync for SvelteKit apps (generates .svelte-kit/)
    for name, app_dir in subapps[1:]:  # skip Dashboard (not SvelteKit)
        svelte_kit_dir = app_dir / ".svelte-kit"
        if svelte_kit_dir.exists() or not (app_dir / "node_modules").exists():
            continue
        try:
            subprocess.run(
                ["npx", "svelte-kit", "sync"],
                cwd=str(app_dir),
                capture_output=True, text=True, timeout=30,
            )
        except Exception as e:
            logger.debug("svelte-kit sync failed (non-critical): %s", e)

    print()


# ---------------------------------------------------------------------------
# Dashboard launcher
# ---------------------------------------------------------------------------

def _launch_dashboard(atomic_root: Path) -> None:
    """Launch the web companion dashboard server and display URL."""
    import time
    import urllib.request

    dashboard_script = atomic_root / "dashboard" / "start-dashboard.sh"
    if not dashboard_script.exists():
        return

    port = os.environ.get("ATOMIC_TASKS_PORT", "5174")

    try:
        env = os.environ.copy()
        env["ATOMIC_ROOT"] = str(atomic_root)
        subprocess.Popen(
            ["bash", str(dashboard_script)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        # Wait for dashboard to be ready (up to 10s)
        ready = False
        for _ in range(20):
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{port}/api/root")
                with urllib.request.urlopen(req, timeout=1):
                    ready = True
                    break
            except Exception as e:
                logger.debug("Dashboard not yet responding: %s", e)
                time.sleep(0.5)

        # Detect hostname/IP for remote access
        hostname = _get_hostname()
        url = f"http://{hostname}:{port}"

        title = "Web Companion Dashboard"
        inner = max(len(title), len(url)) + 4
        print(print_cyan(f"  ┌{'─' * inner}┐"))
        print(print_cyan("  │") + print_bold(f"  {title}") + " " * (inner - len(title) - 2) + print_cyan("│"))
        print(print_cyan("  │") + f"  {url}" + " " * (inner - len(url) - 2) + print_cyan("│"))
        print(print_cyan(f"  └{'─' * inner}┘"))
        if not ready:
            print(print_yellow("  ! Dashboard may still be starting..."))
        print()
    except Exception as e:
        logger.debug("Dashboard launch failed: %s", e)


def _get_hostname() -> str:
    """Get the best hostname/IP for dashboard access."""
    import socket
    # Try to get a routable IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        logger.debug("Failed to detect routable IP: %s", e)
    # Fallback to hostname
    try:
        return socket.gethostname()
    except Exception as e:
        logger.debug("Failed to get hostname: %s", e)
        return "localhost"


# ---------------------------------------------------------------------------
# FalkorDB knowledge graph
# ---------------------------------------------------------------------------

def _start_falkordb(atomic_root: Path, uat_mode: bool = False) -> None:
    """Start FalkorDB via docker compose and verify it's healthy."""
    import time

    compose_file = atomic_root / "docker-compose.yml"
    if not compose_file.exists():
        print(print_red("  ✗ docker-compose.yml not found — cannot start FalkorDB"))
        return

    graph_port = os.environ.get("ATOMIC_GRAPH_PORT", "6379")
    browser_port = os.environ.get("ATOMIC_GRAPH_BROWSER_PORT", "3001")

    print(print_cyan("  Starting FalkorDB knowledge graph..."))
    print()

    try:
        # Start FalkorDB container
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "up", "-d", "falkordb"],
            capture_output=True, text=True, timeout=60,
            cwd=str(atomic_root),
        )

        if result.returncode != 0:
            print(print_red(f"  ✗ docker compose up failed: {result.stderr.strip()}"))
            if uat_mode:
                print(print_yellow("  UAT Mode: Continuing without FalkorDB"))
                return
            print(print_yellow("  Ensure Docker is running and try again."))
            return

        # Wait for FalkorDB to be healthy (up to 15s)
        ready = False
        for attempt in range(15):
            try:
                check = subprocess.run(
                    ["docker", "compose", "-f", str(compose_file),
                     "exec", "-T", "falkordb", "redis-cli", "ping"],
                    capture_output=True, text=True, timeout=5,
                    cwd=str(atomic_root),
                )
                if check.returncode == 0 and "PONG" in check.stdout:
                    ready = True
                    break
            except Exception as e:
                logger.debug("FalkorDB ping check failed: %s", e)
            time.sleep(1)

        if ready:
            print(print_green(f"  ✓ FalkorDB running (Redis: {graph_port}, Browser: {browser_port})"))
            hostname = _get_hostname()
            print(print_dim(f"    Graph browser: http://{hostname}:{browser_port}"))
        else:
            print(print_yellow(f"  ! FalkorDB started but not yet responding on port {graph_port}"))
            print(print_dim("    It may need a few more seconds. The pipeline will retry on first use."))

        print()

    except FileNotFoundError:
        print(print_red("  ✗ docker not found — install Docker to use the knowledge graph"))
        print()
    except subprocess.TimeoutExpired:
        print(print_yellow("  ! docker compose timed out — FalkorDB may still be starting"))
        print()
    except Exception as e:
        print(print_yellow(f"  ! FalkorDB startup error: {e}"))
        print()


# ---------------------------------------------------------------------------
# Record to config
# ---------------------------------------------------------------------------

def _record_environment(config_file: Path, os_type: str) -> None:
    """Record environment status to project-config.json."""
    ensure_dir(config_file.parent)

    config: Dict[str, Any] = {}
    if config_file.exists():
        try:
            config = json.loads(config_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    # Record cargo/rustup availability and PATH status
    cargo_version = _check_tool("cargo")
    cargo_on_path = shutil.which("cargo") is not None
    cargo_in_home = (Path.home() / ".cargo" / "bin" / "cargo").exists()

    config['environment'] = {
        "os_type": os_type,
        "required_total": REQUIRED_TOTAL,
        "required_installed": REQUIRED_INSTALLED,
        "recommended_total": RECOMMENDED_TOTAL,
        "recommended_installed": RECOMMENDED_INSTALLED,
        "cargo_available": cargo_version is not None,
        "cargo_version": cargo_version,
        "cargo_on_path": cargo_on_path,
        "cargo_env_source_needed": cargo_in_home and not cargo_on_path,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    write_file(config_file, json.dumps(config, indent=2))


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 001: Environment Bootstrap")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                        help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                        help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                        help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
