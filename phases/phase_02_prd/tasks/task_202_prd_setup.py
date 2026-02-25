"""
Task 202: PRD Setup

Recaps approach from Phase 1, confirms scope and focus areas for PRD authoring.

Steps:
  1. Display selected approach summary
  2. Confirm/adjust scope
  3. Identify key focus areas for PRD
"""

import logging
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.config import Config
from core.state import StateManager
from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, print_magenta, prompt_user, clear_input_buffer
)
from core.utils.file_ops import ensure_dir, read_file, write_file


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None, graph=None) -> bool:
    """
    Execute Task 202: PRD Setup.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing
        graph: Optional GraphManager instance for knowledge graph operations

    Returns:
        True if task completed successfully, False otherwise
    """
    phase1_dir = output_dir.parent / "1-discovery"
    setup_file = output_dir / "prd-setup.json"

    ensure_dir(setup_file.parent)

    print()
    print(print_dim("  ┌─────────────────────────────────────────────────────────┐"))
    print(print_dim("  │ Before writing the PRD, let's confirm scope and focus. │"))
    print(print_dim("  └─────────────────────────────────────────────────────────┘"))
    print()

    # Recap selected approach
    approach_name, approach_summary, approach_rationale = recap_selected_approach(phase1_dir)

    print()

    # Confirm scope
    scope_type, scope_description = confirm_scope(uat_mode)

    print()

    # Identify focus areas
    focus_areas = identify_focus_areas(uat_mode)

    print()

    # Save setup configuration
    save_setup(
        setup_file,
        approach_name,
        scope_type,
        scope_description,
        focus_areas
    )

    print(print_green("✓ PRD setup complete"))
    return True


def recap_selected_approach(phase1_dir: Path) -> tuple:
    """
    Display selected approach from Phase 1.

    Args:
        phase1_dir: Path to Phase 1 output directory

    Returns:
        Tuple of (approach_name, approach_summary, approach_rationale)
    """
    print(print_cyan("╔═══════════════════════════════════════════════════════════╗"))
    print(print_cyan("║ " + print_bold("SELECTED APPROACH (from Phase 1)") + "                          ║"))
    print(print_cyan("╚═══════════════════════════════════════════════════════════╝"))
    print()

    approach_file = phase1_dir / "selected-approach.json"

    approach_name = "unknown"
    approach_summary = ""
    approach_rationale = ""

    if approach_file.exists():
        try:
            with open(approach_file, 'r') as f:
                approach_data = json.load(f)

            approach_name = approach_data.get('name', 'unnamed')
            approach_summary = approach_data.get('summary', '')
            approach_rationale = approach_data.get('rationale', '')

            print("  " + print_bold(approach_name))
            print()
            if approach_summary:
                print("  " + print_dim(approach_summary))
                print()
            if approach_rationale:
                print("  " + print_dim(f"Rationale: {approach_rationale}"))
        except Exception as e:
            print(print_yellow(f"  ⚠ Error reading approach file: {e}"))
    else:
        print(print_yellow("  No approach file found - proceeding with general PRD"))

    return approach_name, approach_summary, approach_rationale


def confirm_scope(uat_mode: bool) -> tuple:
    """
    Confirm PRD scope with user.

    Args:
        uat_mode: If True, use defaults without prompting

    Returns:
        Tuple of (scope_type, scope_description)
    """
    print(print_cyan("╔═══════════════════════════════════════════════════════════╗"))
    print(print_cyan("║ " + print_bold("CONFIRM SCOPE") + "                                             ║"))
    print(print_cyan("╚═══════════════════════════════════════════════════════════╝"))
    print()

    print(print_dim("  What should this PRD focus on?"))
    print()
    print("    " + print_green("[full]") + "      Full product/feature (comprehensive)")
    print("    " + print_yellow("[mvp]") + "       MVP scope only (minimal viable)")
    print("    " + print_cyan("[component]") + " Single component/module")
    print("    " + print_magenta("[custom]") + "    Define custom scope")
    print()

    # UAT mode bypass
    if uat_mode:
        scope_choice = "mvp"
        print(print_dim(f"  UAT mode: Using default scope '{scope_choice}'"))
    else:
        scope_choice = prompt_user("  Scope (default: mvp): ").strip().lower() or "mvp"

    scope_type = scope_choice
    scope_description = ""

    if scope_choice == "full":
        scope_description = "Comprehensive PRD covering all features and requirements"
    elif scope_choice == "mvp":
        scope_description = "Minimal viable product - core features only"
    elif scope_choice == "component":
        if uat_mode:
            component_name = "core-component"
            print(print_dim(f"  UAT mode: Using default component '{component_name}'"))
        else:
            print()
            component_name = prompt_user("  Component name: ").strip()
        scope_description = f"Single component: {component_name}"
    elif scope_choice == "custom":
        if uat_mode:
            custom_scope = "Custom scope for testing"
            print(print_dim(f"  UAT mode: Using default custom scope"))
        else:
            print()
            custom_scope = prompt_user("  Describe scope: ").strip()
        scope_description = custom_scope
    else:
        # Default to MVP
        scope_description = "Minimal viable product - core features only"

    print()
    print("  " + print_green("✓") + f" Scope: {scope_type}")
    print("    " + print_dim(scope_description))

    return scope_type, scope_description


def identify_focus_areas(uat_mode: bool) -> List[str]:
    """
    Identify PRD focus areas with user.

    Args:
        uat_mode: If True, use defaults without prompting

    Returns:
        List of focus area identifiers
    """
    print(print_cyan("╔═══════════════════════════════════════════════════════════╗"))
    print(print_cyan("║ " + print_bold("FOCUS AREAS") + "                                               ║"))
    print(print_cyan("╚═══════════════════════════════════════════════════════════╝"))
    print()

    print(print_dim("  Which areas need extra attention in the PRD?"))
    print(print_dim("  (Select multiple with spaces, e.g., '1 3 5')"))
    print()
    print("    " + print_dim("1.") + " Technical architecture")
    print("    " + print_dim("2.") + " API/interface design")
    print("    " + print_dim("3.") + " Data models/schemas")
    print("    " + print_dim("4.") + " Security requirements")
    print("    " + print_dim("5.") + " Performance requirements")
    print("    " + print_dim("6.") + " Integration points")
    print("    " + print_dim("7.") + " Testing strategy")
    print("    " + print_dim("8.") + " Deployment/operations")
    print()

    # UAT mode bypass
    if uat_mode:
        focus_input = "1 2 7"
        print(print_dim(f"  UAT mode: Using default focus areas '{focus_input}'"))
    else:
        focus_input = prompt_user("  Focus areas (default: 1 2 7): ").strip() or "1 2 7"

    # Map numbers to focus area identifiers
    focus_map = {
        "1": "architecture",
        "2": "api_design",
        "3": "data_models",
        "4": "security",
        "5": "performance",
        "6": "integrations",
        "7": "testing",
        "8": "deployment"
    }

    focus_areas = []
    for num in focus_input.split():
        if num in focus_map:
            focus_areas.append(focus_map[num])

    # Ensure at least one focus area
    if not focus_areas:
        focus_areas = ["architecture", "api_design", "testing"]

    print()
    print("  " + print_green("✓") + f" Focus areas: {', '.join(focus_areas)}")

    return focus_areas


def save_setup(
    setup_file: Path,
    approach_name: str,
    scope_type: str,
    scope_description: str,
    focus_areas: List[str]
) -> None:
    """
    Save PRD setup configuration.

    Args:
        setup_file: Path to setup file
        approach_name: Name of selected approach
        scope_type: Type of scope (mvp, full, component, custom)
        scope_description: Description of scope
        focus_areas: List of focus area identifiers
    """
    setup_data = {
        "approach": approach_name,
        "scope": {
            "type": scope_type,
            "description": scope_description
        },
        "focus_areas": focus_areas,
        "setup_at": datetime.now(timezone.utc).isoformat()
    }

    write_file(setup_file, json.dumps(setup_data, indent=2))
    print()
    print(print_dim(f"  Setup saved: {setup_file}"))


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 202: PRD Setup")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
