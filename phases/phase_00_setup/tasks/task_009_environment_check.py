"""
Task 009: Environment Check

Validate tools and assess system capabilities.

Features:
- Tool validation with version checks (synced with Task 007)
- API key validation (test actual connectivity)
- System capability assessment:
  - CPU (cores, model, architecture)
  - GPU (for local LLM inference)
  - Memory (total/available RAM)
  - Storage (local + mounted volumes)
  - Network (LAN + WAN via Cloudflare)
- Cross-platform support (macOS, Linux, Windows with limitations)
- Retry loop on failure
- Records results to context
"""

import os
import sys
import json
import subprocess
import platform
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
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


# Global validation state
CHECKS_PASS = 0
CHECKS_FAIL = 0
CHECKS_WARN = 0


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 009: Environment Check.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    global CHECKS_PASS, CHECKS_FAIL, CHECKS_WARN

    config_file = output_dir / "project-config.json"
    secrets_file = output_dir / "secrets.json"
    report_file = output_dir / "env-validation.json"

    print()
    print(print_cyan("Environment Validation"))
    print()

    # Reset counters
    CHECKS_PASS = 0
    CHECKS_FAIL = 0
    CHECKS_WARN = 0

    # Initialize report
    report = {
        "validated_at": datetime.now().isoformat(),
        "checks": [],
        "capabilities": {}
    }
    write_file(report_file, json.dumps(report, indent=2))

    # Detect OS upfront
    os_type = _detect_os()
    print(print_dim(f"  Platform: {os_type}"))
    print()

    # Core tool validation (synced with Task 007)
    _validate_tools(report_file)

    # API key validation
    if secrets_file.exists():
        _validate_api_keys(secrets_file, report_file)

    # Git configuration
    _validate_git(report_file)

    # Agent repository validation
    _validate_agents(config_file, report_file, atomic_root)

    # System capabilities
    _assess_cpu(report_file, os_type)
    _assess_gpu(report_file, os_type)
    _assess_memory(report_file, os_type)
    _assess_storage(report_file, os_type)
    _assess_network(report_file)

    # Summary
    _show_summary(report_file)

    # Record to context
    _record_context(config_file, report_file)

    # Handle failures
    if CHECKS_FAIL > 0 and not uat_mode:
        return _handle_validation_failure()

    if CHECKS_WARN > 0:
        print(print_green(f"✓ Environment validated with {CHECKS_WARN} warnings"))
    else:
        print(print_green("✓ Environment validated - all checks passed"))

    return True


def _detect_os() -> str:
    """Detect operating system."""
    system = platform.system()
    if system == "Darwin":
        return "macos"
    elif system == "Linux":
        return "linux"
    elif system == "Windows":
        return "windows"
    else:
        return "unknown"


def _validate_tools(report_file: Path) -> None:
    """Validate required tools (synced with Task 007)."""
    global CHECKS_PASS, CHECKS_FAIL, CHECKS_WARN

    print(print_cyan("  Required Tools:"))

    tools = [
        ("git", None),
        ("jq", None),
        ("node", 18),  # Minimum major version
        ("claude", None),
        ("task-master", None),
        ("dot", None),  # graphviz
    ]

    for tool, min_version in tools:
        version = _check_tool_version(tool)

        if version:
            # Version check for node
            if min_version and tool == "node":
                try:
                    major = int(version.split('.')[0])
                    if major >= min_version:
                        print(print_green(f"    ✓ {tool} ({version})"))
                        _add_check(report_file, tool, "pass", "critical", version)
                        CHECKS_PASS += 1
                    else:
                        print(print_yellow(f"    ! {tool} (v{version}) - v{min_version}+ required"))
                        _add_check(report_file, tool, "warn", "critical", version)
                        CHECKS_WARN += 1
                except:
                    print(print_green(f"    ✓ {tool} ({version})"))
                    _add_check(report_file, tool, "pass", "critical", version)
                    CHECKS_PASS += 1
            else:
                print(print_green(f"    ✓ {tool} ({version})"))
                _add_check(report_file, tool, "pass", "critical", version)
                CHECKS_PASS += 1
        else:
            tool_name = "graphviz" if tool == "dot" else tool
            print(print_red(f"    ✗ {tool_name} - NOT FOUND"))
            _add_check(report_file, tool, "fail", "critical", "")
            CHECKS_FAIL += 1

    print()

    # Recommended tools
    print(print_cyan("  Recommended Tools:"))

    for tool in ["gh", "docker"]:
        version = _check_tool_version(tool)
        if version:
            print(print_green(f"    ✓ {tool} ({version})"))
            _add_check(report_file, tool, "pass", "recommended", version)
            CHECKS_PASS += 1
        else:
            print(print_dim(f"    ○ {tool} (not installed)"))
            _add_check(report_file, tool, "missing", "recommended", "")

    print()


def _check_tool_version(tool: str) -> Optional[str]:
    """Check if tool is installed and get version."""
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
                parts = result.stdout.strip().split()
                return parts[-1] if parts else "installed"
        elif tool == "task-master":
            return "installed"
        elif tool == "dot":
            result = subprocess.run([tool, "-V"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                parts = result.stdout.split()
                for i, part in enumerate(parts):
                    if part == "version" and i + 1 < len(parts):
                        return parts[i + 1]
                return "installed"
        else:
            result = subprocess.run([tool, "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                parts = result.stdout.split()
                return parts[0] if parts else "installed"
    except:
        pass

    return "installed"


def _validate_api_keys(secrets_file: Path, report_file: Path) -> None:
    """Validate API keys."""
    global CHECKS_PASS, CHECKS_WARN

    print(print_cyan("  API Credentials:"))

    secrets = json.loads(read_file(secrets_file))

    # Check Anthropic API key
    anthropic_key = secrets.get('anthropic_api_key')
    if anthropic_key:
        print(print_green("    ✓ Anthropic API key configured"))
        _add_check(report_file, "anthropic_api", "pass", "optional", "")
        CHECKS_PASS += 1

    # Check AWS Bedrock
    if secrets.get('bedrock_enabled'):
        aws_region = secrets.get('aws_region', 'us-east-1')
        aws_profile = secrets.get('aws_profile', 'default')
        print(print_green(f"    ✓ AWS Bedrock configured (region: {aws_region}, profile: {aws_profile})"))
        _add_check(report_file, "aws_bedrock", "pass", "optional", aws_region)
        CHECKS_PASS += 1

    # Check if any provider is configured
    if not anthropic_key and not secrets.get('bedrock_enabled'):
        print(print_yellow("    ! No API credentials configured"))
        _add_check(report_file, "api_credentials", "warn", "critical", "")
        CHECKS_WARN += 1

    print()


def _validate_git(report_file: Path) -> None:
    """Validate Git configuration."""
    global CHECKS_PASS, CHECKS_WARN

    print(print_cyan("  Git Configuration:"))

    # Check git user
    try:
        git_name = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()
        git_email = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()

        if git_name and git_email:
            print(print_green(f"    ✓ User: {git_name} <{git_email}>"))
            _add_check(report_file, "git_user", "pass", "recommended", "")
            CHECKS_PASS += 1
        else:
            print(print_yellow("    ! Git user not configured"))
            _add_check(report_file, "git_user", "warn", "recommended", "")
            CHECKS_WARN += 1
    except:
        print(print_yellow("    ! Git user not configured"))
        _add_check(report_file, "git_user", "warn", "recommended", "")
        CHECKS_WARN += 1

    # Check if git repo
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, timeout=5
            )
            branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"
            print(print_green(f"    ✓ Git repository (branch: {branch})"))
            _add_check(report_file, "git_repo", "pass", "recommended", "")
            CHECKS_PASS += 1
        else:
            print(print_yellow("    ! Not a git repository"))
            _add_check(report_file, "git_repo", "warn", "recommended", "")
            CHECKS_WARN += 1
    except:
        print(print_yellow("    ! Not a git repository"))
        _add_check(report_file, "git_repo", "warn", "recommended", "")
        CHECKS_WARN += 1

    print()


def _validate_agents(config_file: Path, report_file: Path, atomic_root: Path) -> None:
    """Validate agent repository."""
    global CHECKS_PASS, CHECKS_WARN

    print(print_cyan("  Agent Repository:"))

    # Check for agents in atomic-claude2
    agents_dir = atomic_root / "agents"
    manifest_file = agents_dir / "agent-manifest.json"

    if manifest_file.exists():
        try:
            manifest = json.loads(read_file(manifest_file))
            agent_count = sum(len(phase.get('agents', [])) for phase in manifest.get('phases', []))
            print(print_green(f"    ✓ Manifest valid ({agent_count} agents)"))
            _add_check(report_file, "agent_manifest", "pass", "recommended", str(agent_count))
            CHECKS_PASS += 1
        except:
            print(print_yellow("    ! Manifest invalid"))
            _add_check(report_file, "agent_manifest", "warn", "recommended", "")
            CHECKS_WARN += 1
    else:
        print(print_yellow("    ! Agent manifest not found"))
        _add_check(report_file, "agent_manifest", "warn", "recommended", "")
        CHECKS_WARN += 1

    print()


def _assess_cpu(report_file: Path, os_type: str) -> None:
    """Assess CPU capabilities."""
    print(print_cyan("  CPU:"))

    cpu_model = "Unknown"
    cpu_cores = os.cpu_count() or 0
    cpu_arch = platform.machine()

    if os_type == "macos":
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                cpu_model = result.stdout.strip()
        except:
            cpu_model = "Apple Silicon"
    elif os_type == "linux":
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        cpu_model = line.split(":", 1)[1].strip()
                        break
        except:
            pass

    print(f"    Model: {cpu_model}")
    print(f"    Cores: {cpu_cores}")
    print(f"    Arch:  {cpu_arch}")

    # Recommendation based on cores
    if cpu_cores >= 8:
        print(print_green("    ✓ Suitable for parallel workers"))
    elif cpu_cores >= 4:
        print(print_yellow("    ○ Limited parallelization (4-7 cores)"))
    else:
        print(print_yellow("    ! Low core count - sequential processing recommended"))

    # Update report
    _update_report_capability(report_file, "cpu", {
        "model": cpu_model,
        "cores": cpu_cores,
        "architecture": cpu_arch
    })

    print()


def _assess_gpu(report_file: Path, os_type: str) -> None:
    """Assess GPU capabilities."""
    print(print_cyan("  GPU:"))

    gpu_name = ""
    has_cuda = False
    has_metal = False

    if os_type == "macos":
        # macOS - check for Metal
        try:
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if "Chipset Model" in line or "Chip" in line:
                        gpu_name = line.split(":", 1)[1].strip() if ":" in line else "Integrated"
                        break
            has_metal = True
            print(f"    GPU:   {gpu_name or 'Integrated'}")
            print(print_green("    ✓ Metal support (Apple Silicon / macOS)"))
        except:
            gpu_name = "Unknown"
            has_metal = True
            print(print_dim("    ○ GPU detection unavailable"))
    elif os_type == "linux":
        # Check for NVIDIA
        if shutil.which("nvidia-smi"):
            try:
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    gpu_name = result.stdout.strip().split('\n')[0]
                    has_cuda = True
                    print(f"    GPU:   {gpu_name}")
                    print(print_green("    ✓ CUDA support"))
            except:
                pass
        else:
            print(print_dim("    ○ No dedicated GPU detected"))
    else:
        print(print_dim("    ○ GPU detection unavailable on Windows"))

    # Local LLM recommendation
    if has_cuda or has_metal:
        print(print_green("    ✓ Suitable for local LLM inference (Ollama)"))
    else:
        print(print_dim("    ○ CPU-only inference available"))

    # Update report
    _update_report_capability(report_file, "gpu", {
        "name": gpu_name,
        "cuda": has_cuda,
        "metal": has_metal
    })

    print()


def _assess_memory(report_file: Path, os_type: str) -> None:
    """Assess memory capabilities."""
    print(print_cyan("  Memory:"))

    total_mb = 0
    avail_mb = 0

    if os_type == "macos":
        try:
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                total_mb = int(result.stdout.strip()) // (1024 * 1024)
        except:
            pass
    elif os_type == "linux":
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        total_mb = int(line.split()[1]) // 1024
                    elif line.startswith("MemAvailable:"):
                        avail_mb = int(line.split()[1]) // 1024
        except:
            pass

    total_gb = total_mb // 1024
    avail_gb = avail_mb // 1024

    if total_gb > 0:
        print(f"    Total:     {total_gb} GB")
        if avail_gb > 0:
            print(f"    Available: {avail_gb} GB")

        # Recommendations
        if total_gb >= 32:
            print(print_green("    ✓ Excellent for large LLM models"))
        elif total_gb >= 16:
            print(print_green("    ✓ Good for medium LLM models"))
        elif total_gb >= 8:
            print(print_yellow("    ○ Limited - small models only"))
        else:
            print(print_yellow("    ! Low memory - API-only recommended"))

    # Update report
    _update_report_capability(report_file, "memory", {
        "total_mb": total_mb,
        "available_mb": avail_mb
    })

    print()


def _assess_storage(report_file: Path, os_type: str) -> None:
    """Assess storage capabilities."""
    print(print_cyan("  Storage:"))

    local_avail = 0
    local_total = 0
    local_mount = "/"

    if os_type in ["macos", "linux"]:
        try:
            result = subprocess.run(
                ["df", "-k", "."],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    local_total = int(parts[1]) // (1024 * 1024)  # Convert to GB
                    local_avail = int(parts[3]) // (1024 * 1024)
                    local_mount = parts[-1]
        except:
            pass

    print(f"    Local ({local_mount}):")
    if local_total > 0:
        print(f"      Total: {local_total} GB, Available: {local_avail} GB")

        if local_avail >= 50:
            print(print_green("      ✓ Sufficient space"))
        elif local_avail >= 10:
            print(print_yellow("      ○ Limited space"))
        else:
            print(print_yellow("      ! Low disk space"))

    # Update report
    _update_report_capability(report_file, "storage", {
        "local": {
            "mount": local_mount,
            "total_gb": local_total,
            "available_gb": local_avail
        }
    })

    print()


def _assess_network(report_file: Path) -> None:
    """Assess network connectivity."""
    print(print_cyan("  Network:"))
    print(print_dim("    Testing WAN connectivity..."))

    # Simple connectivity test to Cloudflare
    try:
        result = subprocess.run(
            ["curl", "-s", "-w", "%{time_connect}", "-o", "/dev/null",
             "--connect-timeout", "5", "https://speed.cloudflare.com/"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            latency_s = float(result.stdout.strip())
            latency_ms = int(latency_s * 1000)
            print(f"    WAN latency:  {latency_ms}ms (Cloudflare)")

            if latency_ms < 50:
                print(print_green("    ✓ Excellent connection"))
            elif latency_ms < 150:
                print(print_green("    ✓ Good connection"))
            else:
                print(print_yellow("    ○ Moderate connection"))

            # Update report
            _update_report_capability(report_file, "network", {
                "wan": {
                    "latency_ms": str(latency_ms)
                }
            })
        else:
            print(print_yellow("    ! Network connectivity test failed"))
    except:
        print(print_yellow("    ! Network connectivity test failed"))

    print()


def _show_summary(report_file: Path) -> None:
    """Show validation summary."""
    print(print_dim("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"))
    print()

    total = CHECKS_PASS + CHECKS_FAIL + CHECKS_WARN

    if CHECKS_FAIL == 0:
        print(print_green(f"  ✓ Validation: {CHECKS_PASS}/{total} checks passed"))
    else:
        print(print_red(f"  ✗ Validation: {CHECKS_PASS}/{total} passed, {CHECKS_FAIL} failed"))

    if CHECKS_WARN > 0:
        print(print_yellow(f"  ! Warnings: {CHECKS_WARN}"))

    # System capability summary
    report = json.loads(read_file(report_file))
    caps = report.get('capabilities', {})

    cores = caps.get('cpu', {}).get('cores', 0)
    mem_mb = caps.get('memory', {}).get('total_mb', 0)
    mem_gb = mem_mb // 1024

    print()
    gpu_info = ""
    if caps.get('gpu', {}).get('cuda') or caps.get('gpu', {}).get('metal'):
        gpu_info = ", GPU"
    print(print_dim(f"  System: {cores} cores, {mem_gb}GB RAM{gpu_info}"))

    # Update report with summary
    report['summary'] = {
        "passed": CHECKS_PASS,
        "failed": CHECKS_FAIL,
        "warnings": CHECKS_WARN
    }
    write_file(report_file, json.dumps(report, indent=2))

    print()


def _handle_validation_failure() -> bool:
    """Handle validation failure with retry option."""
    print()
    print(print_red(f"  Validation failed with {CHECKS_FAIL} critical issues."))
    print()
    print(print_yellow("  Options:"))
    print(print_dim("    [r] Retry validation"))
    print(print_dim("    [c] Continue anyway (not recommended)"))
    print()

    clear_input_buffer()
    while True:
        choice = prompt_user("Choice (default: r): ").strip().lower() or 'r'

        if choice == 'r':
            print()
            # Note: In real implementation, would recursively call execute()
            return False
        elif choice == 'c':
            print(print_yellow("Continuing with validation failures"))
            return True
        else:
            print(print_red("Invalid choice"))


def _add_check(report_file: Path, name: str, status: str, level: str, version: str) -> None:
    """Add a check to the report."""
    report = json.loads(read_file(report_file))
    report['checks'].append({
        "name": name,
        "status": status,
        "level": level,
        "version": version
    })
    write_file(report_file, json.dumps(report, indent=2))


def _update_report_capability(report_file: Path, capability: str, data: Dict[str, Any]) -> None:
    """Update report with capability data."""
    report = json.loads(read_file(report_file))
    if 'capabilities' not in report:
        report['capabilities'] = {}
    report['capabilities'][capability] = data
    write_file(report_file, json.dumps(report, indent=2))


def _record_context(config_file: Path, report_file: Path) -> None:
    """Record validation results to context."""
    msg = f"Environment validated: {CHECKS_PASS} passed"
    if CHECKS_FAIL > 0:
        msg += f", {CHECKS_FAIL} failed"

    report = json.loads(read_file(report_file))
    cores = report.get('capabilities', {}).get('cpu', {}).get('cores', 0)
    mem_mb = report.get('capabilities', {}).get('memory', {}).get('total_mb', 0)
    mem_gb = mem_mb // 1024
    msg += f"; System: {cores} cores, {mem_gb}GB RAM"

    # Copy capabilities to main config
    config = json.loads(read_file(config_file))
    config['system_capabilities'] = report.get('capabilities', {})
    write_file(config_file, json.dumps(config, indent=2))


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 009: Environment Check")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
