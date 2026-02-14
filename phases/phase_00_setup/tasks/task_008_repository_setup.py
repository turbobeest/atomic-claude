"""
Task 008: Repository Setup

Validates embedded agents/audits and configures task routing.

Since v2.0, agents and audits are embedded in atomic-claude2 itself.
This task verifies they're available and configures task routing.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
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


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 008: Repository Setup.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    config_file = output_dir / "project-config.json"
    secrets_file = output_dir / "secrets.json"

    print()
    print(print_cyan("Repository & Provider Setup"))
    print()

    # Show info box
    _show_info_box()

    # Verify embedded agents
    agents_dir = atomic_root / "agents"
    agents_manifest = agents_dir / "agent-manifest.json"
    total_agents, total_categories = _verify_agents(agents_dir, agents_manifest)

    # Verify embedded audits
    audits_dir = atomic_root / "audits"
    audits_menu = audits_dir / "AUDIT-MENU.md"
    audit_count = _verify_audits(audits_dir, audits_menu)

    # Task routing configuration
    ollama_configured = _check_ollama_config(secrets_file)
    routing_config = _configure_routing(ollama_configured)

    # Save configuration
    _save_configuration(
        config_file, agents_dir, agents_manifest, audits_dir,
        audits_menu, routing_config, ollama_configured
    )

    # Show summary
    _show_summary(
        agents_manifest, total_agents, audits_menu,
        audit_count, ollama_configured
    )

    print(print_green("✓ Repository setup complete"))
    return True


def _show_info_box() -> None:
    """Show informational box."""
    print(print_dim("  ┌─────────────────────────────────────────────────────────────┐"))
    print(print_dim("  │ ATOMIC CLAUDE includes embedded resources:                  │"))
    print(print_dim("  │   • Agents - Specialized AI agents per phase/domain         │"))
    print(print_dim("  │   • Audits - Quality audits across multiple categories      │"))
    print(print_dim("  └─────────────────────────────────────────────────────────────┘"))
    print()


def _verify_agents(agents_dir: Path, agents_manifest: Path) -> tuple[int, int]:
    """
    Verify embedded agents.

    Args:
        agents_dir: Path to agents directory
        agents_manifest: Path to agent manifest file

    Returns:
        Tuple of (total_agents, total_categories)
    """
    print(print_cyan("  AGENTS"))
    print()

    if agents_manifest.exists():
        try:
            manifest = json.loads(read_file(agents_manifest))
            total_agents = sum(len(phase.get('agents', [])) for phase in manifest.get('phases', []))
            total_categories = len(manifest.get('phases', []))
            manifest_version = manifest.get('version', 'unknown')

            print(print_green(f"  ✓ Agents available (v{manifest_version})"))
            print(f"    Total agents:     {total_agents}")
            print(f"    Phase categories: {total_categories}")
        except:
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
    """
    Verify embedded audits.

    Args:
        audits_dir: Path to audits directory
        audits_menu: Path to audits menu file

    Returns:
        Total audit count
    """
    print(print_cyan("  AUDITS"))
    print()

    if audits_menu.exists():
        # Count lines with '|' (table rows)
        content = read_file(audits_menu)
        audit_count = content.count('\n|')

        # Count categories
        categories_dir = audits_dir / "categories"
        if categories_dir.exists():
            category_count = len([d for d in categories_dir.iterdir() if d.is_dir()])
        else:
            category_count = 0

        print(print_green("  ✓ Audits available"))
        print(f"    Total audits:  ~{audit_count}")
        print(f"    Categories:    {category_count}")
    else:
        print(print_yellow(f"  ! Audit menu not found at: {audits_menu}"))
        print(print_dim("    AI audits disabled"))
        audit_count = 0

    print()
    return audit_count


def _check_ollama_config(secrets_file: Path) -> bool:
    """
    Check if Ollama was configured in Task 004.

    Args:
        secrets_file: Path to secrets file

    Returns:
        True if Ollama is configured
    """
    if not secrets_file.exists():
        return False

    try:
        secrets = json.loads(read_file(secrets_file))
        ollama_hosts = secrets.get('ollama_hosts', [])
        return len(ollama_hosts) > 0
    except:
        return False


def _configure_routing(ollama_configured: bool) -> Dict[str, str]:
    """
    Configure task routing based on Ollama availability.

    Args:
        ollama_configured: Whether Ollama is configured

    Returns:
        Routing configuration dictionary
    """
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
        print(print_dim("    (Configure Ollama in Task 004 for hybrid routing)"))

        routing_config = {
            "critical": "primary",
            "bulk": "primary",
            "background": "primary",
            "background_model": "same"
        }

    print()
    return routing_config


def _save_configuration(
    config_file: Path,
    agents_dir: Path,
    agents_manifest: Path,
    audits_dir: Path,
    audits_menu: Path,
    routing_config: Dict[str, str],
    ollama_configured: bool
) -> None:
    """
    Save repository and provider configuration.

    Args:
        config_file: Path to project config file
        agents_dir: Path to agents directory
        agents_manifest: Path to agent manifest
        audits_dir: Path to audits directory
        audits_menu: Path to audits menu
        routing_config: Routing configuration
        ollama_configured: Whether Ollama is configured
    """
    print(print_dim("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"))
    print()

    # Build configuration
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
        }
    }

    providers_config = {
        "routing": routing_config,
        "ollama_enabled": ollama_configured,
        "configured_at": datetime.now().isoformat()
    }

    # Update project config
    config = json.loads(read_file(config_file))
    config['repositories'] = repos_config
    config['providers'] = providers_config
    write_file(config_file, json.dumps(config, indent=2))

    print(print_green("  ✓ Configuration saved"))
    print()


def _show_summary(
    agents_manifest: Path,
    total_agents: int,
    audits_menu: Path,
    audit_count: int,
    ollama_configured: bool
) -> None:
    """Show summary of configuration."""
    print(print_bold("  Summary:"))
    print()

    if agents_manifest.exists():
        print(print_green(f"    ✓ Agents:  embedded ({total_agents} available)"))
    else:
        print(print_yellow("    ○ Agents:  using defaults"))

    if audits_menu.exists():
        print(print_green(f"    ✓ Audits:  embedded (~{audit_count} available)"))
    else:
        print(print_yellow("    ○ Audits:  disabled"))

    if ollama_configured:
        print(print_green("    ✓ Routing: hybrid (Ollama + primary)"))
    else:
        print(print_dim("    ○ Routing: primary provider only"))

    print()


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 008: Repository Setup")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
