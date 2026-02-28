"""
Task 005: Repository & System Setup

Verifies embedded resources (agents, audits, skills) and assesses system capabilities.

Since v2.0, agents, audits, and skills are embedded in atomic-claude itself.
This task verifies they're available, configures task routing based on provider
inventory, validates git configuration, and performs a full system capability
assessment (CPU, GPU, memory, storage, network).
"""

import logging
import os
import sys
import json
import subprocess
import platform
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user, clear_input_buffer
)
from core.utils.file_ops import ensure_dir, read_file, write_file

try:
    from core.sandbox import generate_sandbox_config
    HAS_SANDBOX = True
except ImportError:
    HAS_SANDBOX = False

logger = logging.getLogger(__name__)


# Global validation state
CHECKS_PASS = 0
CHECKS_FAIL = 0
CHECKS_WARN = 0


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None) -> bool:
    """
    Execute Task 005: Repository & System Setup.

    Verifies embedded resources (agents, audits, skills), configures task
    routing, validates git, and assesses system capabilities.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing
        mem: Optional TaskMemory instance for recording substantive memory

    Returns:
        True if task completed successfully, False otherwise
    """
    global CHECKS_PASS, CHECKS_FAIL, CHECKS_WARN

    config_file = output_dir / "project-config.json"
    report_file = output_dir / "env-validation.json"

    print()
    print(print_cyan("Repository & System Setup"))
    print()

    # Reset counters
    CHECKS_PASS = 0
    CHECKS_FAIL = 0
    CHECKS_WARN = 0

    # Initialize report
    report = {
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "checks": [],
        "capabilities": {}
    }
    write_file(report_file, json.dumps(report, indent=2))

    # Show info box about embedded resources
    _show_info_box()

    # Verify embedded agents
    agents_dir = atomic_root / "agents"
    agents_manifest = agents_dir / "agent-manifest.json"
    total_agents, total_categories = _verify_agents(agents_dir, agents_manifest)

    # Verify embedded audits
    audits_dir = atomic_root / "audits"
    audits_menu = audits_dir / "AUDIT-MENU.md"
    audit_count = _verify_audits(audits_dir, audits_menu)

    # Verify embedded skills
    skills_dir = atomic_root / "skills"
    skill_count, skill_sources = _verify_skills(skills_dir)

    # Load provider inventory to check if ollama is configured
    inventory_file = output_dir / "provider-inventory.json"
    ollama_configured = False
    if inventory_file.exists():
        try:
            inventory = json.loads(read_file(inventory_file))
            providers = inventory.get("providers", {})
            ollama_info = providers.get("ollama", providers.get("Ollama", {}))
            ollama_status = ollama_info.get("status", "unavailable")
            ollama_configured = ollama_status in ("healthy", "degraded")
        except Exception as e:
            logger.debug("Failed to load inventory for Ollama check: %s", e)

    # Task routing configuration
    routing_config = _configure_routing(ollama_configured)

    # Detect OS upfront
    os_type = _detect_os()
    print(print_dim(f"  Platform: {os_type}"))
    print()

    # Git configuration
    _validate_git(report_file, uat_mode)

    # System capabilities
    _assess_cpu(report_file, os_type)
    _assess_gpu(report_file, os_type)
    _assess_memory(report_file, os_type)
    _assess_storage(report_file, os_type)
    _assess_network(report_file)

    # Save configuration
    _save_configuration(
        config_file, report_file,
        agents_dir, agents_manifest,
        audits_dir, audits_menu,
        skills_dir, skill_count, skill_sources,
        routing_config, ollama_configured,
    )

    # Generate sandbox security config for Claude Code invocations
    if HAS_SANDBOX:
        try:
            project_root = atomic_root.parent
            sandbox = generate_sandbox_config(
                project_root=project_root,
                allow_network=False,
            )
            sandbox.write()
            print(print_green("  ✓ Sandbox security config generated"))
        except Exception as e:
            logger.debug("Sandbox config generation failed: %s", e)

    # Show summary
    _show_summary(
        report_file,
        agents_manifest, total_agents,
        audits_menu, audit_count,
        skill_count,
        ollama_configured,
    )

    # Record substantive memory
    if mem:
        mem.finding(f"Agents: {total_agents} | Audits: {audit_count} | Skills: {skill_count}")
        # Read git info from report if available
        if report_file.exists():
            try:
                report = json.loads(report_file.read_text())
                git_info = report.get("git", {})
                user_name = git_info.get("user_name", "")
                branch = git_info.get("branch", "")
                remote_url = git_info.get("remote_url", "")
                if user_name or branch:
                    mem.configuration(f"Git: {user_name} on branch {branch}"
                                      + (f", remote {remote_url}" if remote_url else ""))
                caps = report.get("capabilities", {})
                cpu = caps.get("cpu", {})
                memory_info = caps.get("memory", {})
                arch = cpu.get("architecture", "")
                cores = cpu.get("cores", "")
                ram_mb = memory_info.get("total_mb", 0)
                if arch or cores:
                    mem.finding(f"System: {arch}/{cores} cores"
                                + (f", {ram_mb}MB RAM" if ram_mb else ""))
            except Exception as e:
                logger.debug("Failed to read setup report for memory: %s", e)
        mem.configuration(f"Routing: {'Ollama-enabled' if ollama_configured else 'API-only'}")

    # Handle failures
    if CHECKS_FAIL > 0 and not uat_mode:
        return _handle_validation_failure()

    if CHECKS_WARN > 0:
        print(print_green(f"✓ Repository & system setup complete with {CHECKS_WARN} warnings"))
    else:
        print(print_green("✓ Repository & system setup complete"))

    return True


# ---------------------------------------------------------------------------
# Embedded resource verification (from task_004)
# ---------------------------------------------------------------------------

def _show_info_box() -> None:
    """Show informational box."""
    print(print_dim("  ┌─────────────────────────────────────────────────────────────┐"))
    print(print_dim("  │ ATOMIC CLAUDE includes embedded resources:                  │"))
    print(print_dim("  │   • Agents - Specialized AI agents per phase/domain         │"))
    print(print_dim("  │   • Audits - Quality audits across multiple categories      │"))
    print(print_dim("  │   • Skills - Reusable capability modules                    │"))
    print(print_dim("  └─────────────────────────────────────────────────────────────┘"))
    print()


def _verify_agents(agents_dir: Path, agents_manifest: Path) -> Tuple[int, int]:
    """Verify embedded agents. Returns (total_agents, total_categories)."""
    print(print_cyan("  AGENTS"))
    print()

    if agents_manifest.exists():
        try:
            manifest = json.loads(read_file(agents_manifest))
            agents_list = manifest.get('agents', [])
            total_agents = len(agents_list)
            total_categories = len(set(a.get('category', '') for a in agents_list))
            manifest_version = manifest.get('version', 'unknown')

            print(print_green(f"  ✓ Agents available (v{manifest_version})"))
            print(f"    Total agents:     {total_agents}")
            print(f"    Phase categories: {total_categories}")
        except Exception as e:
            logger.debug("Failed to load agent manifest: %s", e)
            print(print_yellow(f"  ! Agent manifest corrupt: {agents_manifest}"))
            print(print_dim("    Using built-in defaults"))
            total_agents, total_categories = 0, 0
    else:
        print(print_yellow(f"  ! Agent manifest not found at: {agents_manifest}"))
        print(print_dim("    Using built-in defaults"))
        total_agents, total_categories = 0, 0

    print()
    return total_agents, total_categories


def _verify_audits(audits_dir: Path, audits_menu: Path) -> int:
    """Verify embedded audits. Returns total audit count."""
    print(print_cyan("  AUDITS"))
    print()

    if audits_menu.exists():
        # Count audits from AUDIT-INVENTORY.csv (one audit per line, minus header)
        inventory_file = audits_dir / "AUDIT-INVENTORY.csv"
        if inventory_file.exists():
            content = read_file(inventory_file)
            audit_count = max(0, content.count('\n') - 1)  # subtract header
        else:
            audit_count = 0

        # Count category files in categories/
        categories_dir = audits_dir / "categories"
        if categories_dir.exists():
            category_count = len([f for f in categories_dir.iterdir()
                                  if f.is_file() and f.suffix == '.md'])
        else:
            category_count = 0

        print(print_green("  ✓ Audits available"))
        print(f"    Total audits:  {audit_count}")
        print(f"    Categories:    {category_count}")
    else:
        print(print_yellow(f"  ! Audit menu not found at: {audits_menu}"))
        print(print_dim("    AI audits disabled"))
        audit_count = 0

    print()
    return audit_count


def _verify_skills(skills_dir: Path) -> Tuple[int, Dict[str, int]]:
    """
    Verify embedded skills.

    Returns:
        (total_skill_count, sources_dict) where sources_dict maps source name
        to count (e.g. {"tactical": 0, "superpowers": 2, "trailofbits": 25}).
    """
    print(print_cyan("  SKILLS"))
    print()

    sources: Dict[str, int] = {}

    # Tactical skills: skills/tactical/<category>/<skill>/
    tactical_dir = skills_dir / "tactical"
    tactical_count = 0
    if tactical_dir.is_dir():
        for category in tactical_dir.iterdir():
            if category.is_dir() and not category.name.startswith('.'):
                for skill in category.iterdir():
                    if skill.is_dir():
                        tactical_count += 1
    sources["tactical"] = tactical_count

    # Community: superpowers
    superpowers_dir = skills_dir / "community" / "superpowers" / "skills"
    sp_count = 0
    if superpowers_dir.is_dir():
        sp_count = len([d for d in superpowers_dir.iterdir() if d.is_dir()])
    sources["superpowers"] = sp_count

    # Community: Trail of Bits plugins
    tob_dir = skills_dir / "community" / "trailofbits" / "plugins"
    tob_count = 0
    if tob_dir.is_dir():
        tob_count = len([d for d in tob_dir.iterdir() if d.is_dir()])
    sources["trailofbits"] = tob_count

    # Community: ralph
    ralph_dir = skills_dir / "community" / "ralph"
    ralph_count = 0
    if ralph_dir.is_dir() and (ralph_dir / "README.md").exists():
        ralph_count = 1
    sources["ralph"] = ralph_count

    total = sum(sources.values())

    if total > 0:
        print(print_green(f"  ✓ Skills available"))
        print(f"    Total skills:  {total}")
        details = []
        if sources["tactical"]:
            details.append(f"{sources['tactical']} tactical")
        if sources["superpowers"]:
            details.append(f"{sources['superpowers']} superpowers")
        if sources["trailofbits"]:
            details.append(f"{sources['trailofbits']} trail-of-bits")
        if sources["ralph"]:
            details.append(f"{sources['ralph']} ralph")
        if details:
            print(f"    Sources:       {', '.join(details)}")
    else:
        print(print_dim("  ○ No skills found"))

    print()
    return total, sources


# ---------------------------------------------------------------------------
# Task routing (from task_004)
# ---------------------------------------------------------------------------

def _configure_routing(ollama_configured: bool) -> Dict[str, str]:
    """Configure task routing based on Ollama availability."""
    print(print_cyan("  TASK ROUTING"))
    print()

    if ollama_configured:
        print(print_green("  ✓ Ollama hosts configured - hybrid routing available"))
        print()
        print(print_dim("  Task routing determines which provider handles different task types:"))
        print()
        print(print_cyan("    Critical"))
        print("   PRD generation, architecture decisions")
        print(print_dim("              → Uses primary provider (highest quality)"))
        print()
        print(print_cyan("    Bulk"))
        print("       File scanning, audit runs, code analysis")
        print(print_dim("              → Can use Ollama (high volume, parallelizable)"))
        print()
        print(print_cyan("    Background"))
        print(" Indexing, validation, health checks")
        print(print_dim("              → Can use smaller/faster models"))
        print()

        routing_config = {
            "critical": "primary",
            "bulk": "ollama",
            "background": "ollama",
            "background_model": "same"
        }

        print(print_bold("  Current Routing:"))
        print()
        print("    Critical tasks:   primary")
        print("    Bulk tasks:       ollama")
        print("    Background tasks: ollama")
    else:
        print(print_dim("  ○ No Ollama hosts configured - all tasks use primary provider"))
        print(print_dim("    (You can add Ollama hosts in Task 002 for hybrid routing)"))

        routing_config = {
            "critical": "primary",
            "bulk": "primary",
            "background": "primary",
            "background_model": "same"
        }

    print()
    return routing_config


# ---------------------------------------------------------------------------
# Git validation (from task_005)
# ---------------------------------------------------------------------------

def _validate_git(report_file: Path, uat_mode: bool = False) -> None:
    """Validate Git configuration including remote repository."""
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
    except Exception as e:
        logger.debug("Git user check failed: %s", e)
        print(print_yellow("    ! Git user not configured"))
        _add_check(report_file, "git_user", "warn", "recommended", "")
        CHECKS_WARN += 1

    # Check if git repo
    is_git_repo = False
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            is_git_repo = True
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
    except Exception as e:
        logger.debug("Git repo check failed: %s", e)
        print(print_yellow("    ! Not a git repository"))
        _add_check(report_file, "git_repo", "warn", "recommended", "")
        CHECKS_WARN += 1

    # Check remote repository
    if is_git_repo:
        _validate_git_remote(report_file, uat_mode)

    print()


def _validate_git_remote(report_file: Path, uat_mode: bool = False) -> None:
    """Check for git remote and offer to configure one if missing."""
    global CHECKS_PASS, CHECKS_WARN

    # Get current remotes
    try:
        result = subprocess.run(
            ["git", "remote", "-v"],
            capture_output=True, text=True, timeout=5
        )
        remotes = result.stdout.strip() if result.returncode == 0 else ""
    except Exception as e:
        logger.debug("Git remote check failed: %s", e)
        remotes = ""

    if remotes:
        # Parse and display remotes
        seen = set()
        for line in remotes.split('\n'):
            parts = line.split()
            if len(parts) >= 2:
                name, url = parts[0], parts[1]
                key = f"{name}\t{url}"
                if key not in seen:
                    seen.add(key)
                    print(print_green(f"    ✓ Remote '{name}': {url}"))
        _add_check(report_file, "git_remote", "pass", "recommended", "")
        CHECKS_PASS += 1
    else:
        print(print_yellow("    ! No remote repository configured"))
        print(print_dim("      Phase 9 (Release) needs a remote to push to."))

        if uat_mode:
            print(print_dim("      Skipping remote setup (UAT mode)"))
            _add_check(report_file, "git_remote", "warn", "recommended", "")
            CHECKS_WARN += 1
            return

        print()
        print(print_dim("      Enter a remote URL to configure 'origin', or press Enter to skip."))
        print(print_dim("      Examples:"))
        print(print_dim("        git@github.com:user/repo.git"))
        print(print_dim("        https://github.com/user/repo.git"))
        print()

        clear_input_buffer()
        remote_url = prompt_user("    Remote URL (or Enter to skip): ").strip()

        if remote_url:
            if remote_url.lower() == 'q':
                print(print_yellow("    Skipped remote configuration"))
                _add_check(report_file, "git_remote", "warn", "recommended", "")
                CHECKS_WARN += 1
                return

            try:
                add_result = subprocess.run(
                    ["git", "remote", "add", "origin", remote_url],
                    capture_output=True, text=True, timeout=5
                )
                if add_result.returncode == 0:
                    print(print_green(f"    ✓ Remote 'origin' configured: {remote_url}"))
                    _add_check(report_file, "git_remote", "pass", "recommended", "")
                    CHECKS_PASS += 1
                else:
                    # Maybe origin already exists with different URL
                    if "already exists" in add_result.stderr:
                        print(print_yellow(f"    ! Remote 'origin' already exists"))
                        print(print_dim(f"      Use 'git remote set-url origin {remote_url}' to update"))
                    else:
                        print(print_yellow(f"    ! Failed to add remote: {add_result.stderr.strip()}"))
                    _add_check(report_file, "git_remote", "warn", "recommended", "")
                    CHECKS_WARN += 1
            except Exception as e:
                print(print_yellow(f"    ! Failed to add remote: {e}"))
                _add_check(report_file, "git_remote", "warn", "recommended", "")
                CHECKS_WARN += 1
        else:
            print(print_dim("    Skipped remote configuration"))
            _add_check(report_file, "git_remote", "warn", "recommended", "")
            CHECKS_WARN += 1


# ---------------------------------------------------------------------------
# System capability assessment (from task_005)
# ---------------------------------------------------------------------------

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
        except Exception as e:
            logger.debug("CPU brand string detection failed: %s", e)
            cpu_model = "Apple Silicon"
    elif os_type == "linux":
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        cpu_model = line.split(":", 1)[1].strip()
                        break
        except Exception as e:
            logger.debug("CPU model detection from /proc/cpuinfo failed: %s", e)

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
        except Exception as e:
            logger.debug("macOS GPU detection failed: %s", e)
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
            except Exception as e:
                logger.debug("NVIDIA GPU detection failed: %s", e)
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
        except Exception as e:
            logger.debug("macOS memory detection failed: %s", e)
    elif os_type == "linux":
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        total_mb = int(line.split()[1]) // 1024
                    elif line.startswith("MemAvailable:"):
                        avail_mb = int(line.split()[1]) // 1024
        except Exception as e:
            logger.debug("Linux memory detection failed: %s", e)

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
        except Exception as e:
            logger.debug("Disk space detection failed: %s", e)

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
                    "latency_ms": int(latency_ms)
                }
            })
        else:
            print(print_yellow("    ! Network connectivity test failed"))
    except Exception as e:
        logger.debug("Network connectivity test failed: %s", e)
        print(print_yellow("    ! Network connectivity test failed"))

    print()


# ---------------------------------------------------------------------------
# Report helpers (from task_005)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Save configuration and summary
# ---------------------------------------------------------------------------

def _save_configuration(
    config_file: Path,
    report_file: Path,
    agents_dir: Path,
    agents_manifest: Path,
    audits_dir: Path,
    audits_menu: Path,
    skills_dir: Path,
    skill_count: int,
    skill_sources: Dict[str, int],
    routing_config: Dict[str, str],
    ollama_configured: bool,
) -> None:
    """Save repository and system configuration."""
    print(print_dim("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"))
    print()

    # Build repositories configuration
    repos_config = {
        "agents": {
            "path": str(agents_dir),
            "embedded": True,
            "configured": agents_manifest.exists()
        },
        "audits": {
            "path": str(audits_dir),
            "embedded": True,
            "configured": audits_menu.exists()
        },
        "skills": {
            "path": str(skills_dir),
            "embedded": True,
            "configured": skill_count > 0,
            "count": skill_count,
            "sources": skill_sources,
        },
    }

    providers_config = {
        "routing": routing_config,
        "ollama_enabled": ollama_configured,
        "configured_at": datetime.now(timezone.utc).isoformat()
    }

    # Read system capabilities from the report
    report = json.loads(read_file(report_file))
    system_capabilities = report.get('capabilities', {})

    # Write summary to report
    report['summary'] = {
        "passed": CHECKS_PASS,
        "failed": CHECKS_FAIL,
        "warnings": CHECKS_WARN
    }
    write_file(report_file, json.dumps(report, indent=2))

    # Update project config with repositories, providers, and system capabilities
    config = json.loads(read_file(config_file))
    config['repositories'] = repos_config
    # Merge providers_config into existing providers (task_003 wrote effort_level,
    # chain_priority, models, phase_roles, etc. — don't overwrite those)
    if 'providers' not in config:
        config['providers'] = {}
    config['providers'].update(providers_config)
    config['system_capabilities'] = system_capabilities
    write_file(config_file, json.dumps(config, indent=2))

    print(print_green("  ✓ Configuration saved"))
    print()


def _show_summary(
    report_file: Path,
    agents_manifest: Path,
    total_agents: int,
    audits_menu: Path,
    audit_count: int,
    skill_count: int,
    ollama_configured: bool,
) -> None:
    """Show summary of configuration and system assessment."""
    print(print_bold("  Summary:"))
    print()

    # Embedded resources
    if agents_manifest.exists():
        print(print_green(f"    ✓ Agents:  embedded ({total_agents} available)"))
    else:
        print(print_yellow("    ○ Agents:  using defaults"))

    if audits_menu.exists():
        print(print_green(f"    ✓ Audits:  embedded (~{audit_count} available)"))
    else:
        print(print_yellow("    ○ Audits:  disabled"))

    if skill_count > 0:
        print(print_green(f"    ✓ Skills:  embedded ({skill_count} available)"))
    else:
        print(print_dim("    ○ Skills:  none found"))

    if ollama_configured:
        print(print_green(f"    ✓ Routing: hybrid (Ollama + primary)"))
    else:
        print(print_dim("    ○ Routing: primary provider only"))

    # Validation results
    total = CHECKS_PASS + CHECKS_FAIL + CHECKS_WARN
    if total > 0:
        print()
        if CHECKS_FAIL == 0:
            print(print_green(f"    ✓ Checks: {CHECKS_PASS}/{total} passed"))
        else:
            print(print_red(f"    ✗ Checks: {CHECKS_PASS}/{total} passed, {CHECKS_FAIL} failed"))

        if CHECKS_WARN > 0:
            print(print_yellow(f"    ! Warnings: {CHECKS_WARN}"))

    # System capability summary
    report = json.loads(read_file(report_file))
    caps = report.get('capabilities', {})

    cores = caps.get('cpu', {}).get('cores', 0)
    mem_mb = caps.get('memory', {}).get('total_mb', 0)
    mem_gb = mem_mb // 1024

    if cores > 0 or mem_gb > 0:
        gpu_info = ""
        if caps.get('gpu', {}).get('cuda') or caps.get('gpu', {}).get('metal'):
            gpu_info = ", GPU"
        print()
        print(print_dim(f"    System: {cores} cores, {mem_gb}GB RAM{gpu_info}"))

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


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 005: Repository & System Setup")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
