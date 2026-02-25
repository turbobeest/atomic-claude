"""
Task 203: PRD Interview (Confirmatory) - OPTIONAL

Gathers/confirms key PRD inputs: stakeholders, success criteria, non-goals, MVP.

This is a confirmatory interview - we PROPOSE values based on Phase 1
and the user confirms or adjusts them.

This task is OPTIONAL - can be skipped if no stakeholders are available
or if defaults are acceptable.
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
    print_red, print_dim, prompt_user, clear_input_buffer
)
from core.utils.file_ops import ensure_dir, read_file, write_file


# Default interview values
DEFAULT_STAKEHOLDERS = [
    "End users (primary)",
    "Development team",
    "Product owner"
]

DEFAULT_SUCCESS_CRITERIA = [
    "Core functionality works as specified",
    "Passes all acceptance tests",
    "Documentation complete"
]

DEFAULT_NON_GOALS = [
    "Performance optimization (defer to later)",
    "Full production deployment",
    "Comprehensive error handling for edge cases"
]

DEFAULT_MVP_SCOPE = [
    "Core feature implementation",
    "Basic error handling",
    "Unit tests for critical paths"
]


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None, graph=None) -> bool:
    """
    Execute Task 203: PRD Interview (Optional).

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing
        graph: Optional GraphManager instance for knowledge graph operations

    Returns:
        True if task completed successfully, False otherwise
    """
    phase1_dir = output_dir.parent / "1-discovery"
    interview_file = output_dir / "prd-interview.json"

    print()
    print(print_dim("  ┌─────────────────────────────────────────────────────────┐"))
    print(print_dim("  │ Confirmatory interview to refine PRD inputs.           │"))
    print(print_dim("  │                                                         │"))
    print(print_dim("  │ You may answer as yourself, on behalf of stakeholders, │"))
    print(print_dim("  │ or use sensible defaults to proceed quickly.           │"))
    print(print_dim("  └─────────────────────────────────────────────────────────┘"))
    print()

    # Optional skip
    skip_choice = handle_optional_skip(uat_mode)

    if skip_choice == "defaults":
        save_defaults(interview_file)
        print()
        print(print_green("✓ PRD interview complete (defaults)"))
        return True
    elif skip_choice == "skip":
        print()
        print(print_yellow("  ! Interview skipped - no interview data will be available"))
        return True

    # Conduct interview
    print()

    stakeholders = collect_stakeholders(uat_mode)
    print()

    success_criteria = collect_success_criteria(uat_mode)
    print()

    non_goals = collect_non_goals(uat_mode)
    print()

    mvp_scope = collect_mvp_scope(uat_mode)
    print()

    # Save interview results
    save_interview(
        interview_file,
        stakeholders,
        success_criteria,
        non_goals,
        mvp_scope
    )

    print(print_green("✓ PRD interview complete"))
    return True


def handle_optional_skip(uat_mode: bool) -> str:
    """
    Handle optional skip decision.

    Args:
        uat_mode: If True, use defaults

    Returns:
        Choice: "continue", "defaults", or "skip"
    """
    print(print_cyan("  This task is optional."))
    print()
    print("    " + print_green("[continue]") + "  Conduct stakeholder interview")
    print("    " + print_yellow("[defaults]") + "  Use default values (skip interview)")
    print("    " + print_dim("[skip]") + "      Skip entirely (no interview data)")
    print()

    if uat_mode:
        choice = "defaults"
        print(print_dim(f"  UAT mode: Using '{choice}'"))
        return choice

    clear_input_buffer()
    choice = prompt_user("  Choice (default: continue): ").strip().lower() or "continue"

    return choice


def collect_stakeholders(uat_mode: bool) -> List[str]:
    """
    Collect stakeholder information.

    Args:
        uat_mode: If True, use defaults

    Returns:
        List of stakeholder descriptions
    """
    print(print_cyan("╔═══════════════════════════════════════════════════════════╗"))
    print(print_cyan("║ " + print_bold("1. STAKEHOLDERS") + "                                           ║"))
    print(print_cyan("╚═══════════════════════════════════════════════════════════╝"))
    print()

    # Propose default stakeholders
    print(print_dim("  PROPOSED stakeholders:"))
    for stakeholder in DEFAULT_STAKEHOLDERS:
        print(f"    • {stakeholder}")
    print()
    print(print_cyan("  Options:"))
    print("    " + print_green("[confirm]") + "  Accept proposed stakeholders")
    print("    " + print_yellow("[adjust]") + "   Add or modify stakeholders")
    print()

    if uat_mode:
        choice = "confirm"
        print(print_dim(f"  UAT mode: Using '{choice}'"))
        return DEFAULT_STAKEHOLDERS

    clear_input_buffer()
    choice = prompt_user("  Choice (default: confirm): ").strip().lower() or "confirm"

    if choice == "adjust":
        print()
        print(print_dim("  Enter stakeholders (one per line, empty line to finish):"))
        stakeholders = []
        while True:
            stakeholder = prompt_user("    > ").strip()
            if not stakeholder:
                break
            stakeholders.append(stakeholder)

        if not stakeholders:
            stakeholders = DEFAULT_STAKEHOLDERS
    else:
        stakeholders = DEFAULT_STAKEHOLDERS

    print("  " + print_green("✓") + " Stakeholders confirmed")
    return stakeholders


def collect_success_criteria(uat_mode: bool) -> List[str]:
    """
    Collect success criteria.

    Args:
        uat_mode: If True, use defaults

    Returns:
        List of success criteria
    """
    print(print_cyan("╔═══════════════════════════════════════════════════════════╗"))
    print(print_cyan("║ " + print_bold("2. SUCCESS CRITERIA") + "                                       ║"))
    print(print_cyan("╚═══════════════════════════════════════════════════════════╝"))
    print()

    print(print_dim("  PROPOSED success criteria:"))
    for criterion in DEFAULT_SUCCESS_CRITERIA:
        print(f"    • {criterion}")
    print()
    print(print_cyan("  Options:"))
    print("    " + print_green("[confirm]") + "  Accept proposed criteria")
    print("    " + print_yellow("[adjust]") + "   Define specific metrics")
    print()

    if uat_mode:
        choice = "confirm"
        print(print_dim(f"  UAT mode: Using '{choice}'"))
        return DEFAULT_SUCCESS_CRITERIA

    clear_input_buffer()
    choice = prompt_user("  Choice (default: confirm): ").strip().lower() or "confirm"

    if choice == "adjust":
        print()
        print(print_dim("  Enter success criteria (one per line, empty line to finish):"))
        criteria = []
        while True:
            criterion = prompt_user("    > ").strip()
            if not criterion:
                break
            criteria.append(criterion)

        if not criteria:
            criteria = DEFAULT_SUCCESS_CRITERIA
    else:
        criteria = DEFAULT_SUCCESS_CRITERIA

    print("  " + print_green("✓") + " Success criteria confirmed")
    return criteria


def collect_non_goals(uat_mode: bool) -> List[str]:
    """
    Collect non-goals (explicitly out of scope).

    Args:
        uat_mode: If True, use defaults

    Returns:
        List of non-goals
    """
    print(print_cyan("╔═══════════════════════════════════════════════════════════╗"))
    print(print_cyan("║ " + print_bold("3. NON-GOALS (Out of Scope)") + "                               ║"))
    print(print_cyan("╚═══════════════════════════════════════════════════════════╝"))
    print()

    print(print_dim("  PROPOSED non-goals (explicitly out of scope):"))
    for non_goal in DEFAULT_NON_GOALS:
        print(f"    • {non_goal}")
    print()
    print(print_cyan("  Options:"))
    print("    " + print_green("[confirm]") + "  Accept proposed non-goals")
    print("    " + print_yellow("[adjust]") + "   Define specific non-goals")
    print()

    if uat_mode:
        choice = "confirm"
        print(print_dim(f"  UAT mode: Using '{choice}'"))
        return DEFAULT_NON_GOALS

    clear_input_buffer()
    choice = prompt_user("  Choice (default: confirm): ").strip().lower() or "confirm"

    if choice == "adjust":
        print()
        print(print_dim("  Enter non-goals (one per line, empty line to finish):"))
        non_goals = []
        while True:
            non_goal = prompt_user("    > ").strip()
            if not non_goal:
                break
            non_goals.append(non_goal)

        if not non_goals:
            non_goals = DEFAULT_NON_GOALS
    else:
        non_goals = DEFAULT_NON_GOALS

    print("  " + print_green("✓") + " Non-goals confirmed")
    return non_goals


def collect_mvp_scope(uat_mode: bool) -> List[str]:
    """
    Collect MVP scope definition.

    Args:
        uat_mode: If True, use defaults

    Returns:
        List of MVP features/components
    """
    print(print_cyan("╔═══════════════════════════════════════════════════════════╗"))
    print(print_cyan("║ " + print_bold("4. MVP SCOPE") + "                                              ║"))
    print(print_cyan("╚═══════════════════════════════════════════════════════════╝"))
    print()

    if uat_mode:
        print(print_dim("  UAT mode: Using default MVP scope"))
        return DEFAULT_MVP_SCOPE

    print(print_dim("  What's the minimum viable scope for Phase 1 delivery?"))
    print()
    print(print_dim("  Enter MVP features (one per line, empty line to finish):"))

    mvp_scope = []
    while True:
        mvp_item = prompt_user("    > ").strip()
        if not mvp_item:
            break
        mvp_scope.append(mvp_item)

    if not mvp_scope:
        mvp_scope = DEFAULT_MVP_SCOPE

    print()
    print("  " + print_green("✓") + " MVP scope defined")
    return mvp_scope


def save_defaults(interview_file: Path) -> None:
    """
    Save default interview values.

    Args:
        interview_file: Path to interview file
    """
    interview_data = {
        "stakeholders": DEFAULT_STAKEHOLDERS,
        "success_criteria": DEFAULT_SUCCESS_CRITERIA,
        "non_goals": DEFAULT_NON_GOALS,
        "mvp_scope": DEFAULT_MVP_SCOPE,
        "interview_at": datetime.now(timezone.utc).isoformat(),
        "source": "defaults"
    }

    write_file(interview_file, json.dumps(interview_data, indent=2))
    print()
    print("  " + print_green("✓") + " Using default interview values")


def save_interview(
    interview_file: Path,
    stakeholders: List[str],
    success_criteria: List[str],
    non_goals: List[str],
    mvp_scope: List[str]
) -> None:
    """
    Save interview results.

    Args:
        interview_file: Path to interview file
        stakeholders: List of stakeholders
        success_criteria: List of success criteria
        non_goals: List of non-goals
        mvp_scope: List of MVP features
    """
    interview_data = {
        "stakeholders": stakeholders,
        "success_criteria": success_criteria,
        "non_goals": non_goals,
        "mvp_scope": mvp_scope,
        "interview_at": datetime.now(timezone.utc).isoformat()
    }

    write_file(interview_file, json.dumps(interview_data, indent=2))
    print(print_dim(f"  Interview saved: {interview_file}"))


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 203: PRD Interview (Optional)")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
