"""
Task 602: Agent Selection

Select agents for code review: deep-code-reviewer, arch-compliance,
perf-analyzer, doc-reviewer, code-refiner.
"""

import logging
import sys
import json
from pathlib import Path
from typing import Dict, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Model tier constants
TIER_OPUS = "opus"
TIER_SONNET = "sonnet"
TIER_HAIKU = "haiku"

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, print_magenta, print_blue,
    prompt_user, clear_input_buffer
)
from core.utils.file_ops import ensure_dir, read_file, write_file


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None) -> bool:
    """
    Execute Task 602: Agent Selection.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    agents_file = output_dir / "review-agents.json"
    ensure_dir(agents_file.parent)

    print()
    print(print_dim("Selecting specialized agents for code review."))
    print()

    # UAT Mode Bypass
    if uat_mode:
        print(print_yellow("UAT Mode: Creating minimal valid output"))
        # NOTE: Agent names here are display labels, not manifest IDs
        # TODO: validate against agent-manifest.json
        write_file(agents_file, json.dumps({
            "agents": ["code-reviewer"],
            "count": 1,
            "review_agents": {
                "deep_code": {"name": "code-reviewer", "model": TIER_SONNET, "dimension": "code_quality"},
                "architecture": {"name": "code-reviewer", "model": TIER_SONNET, "dimension": "architecture"},
                "performance": {"name": "code-reviewer", "model": TIER_SONNET, "dimension": "performance"},
                "documentation": {"name": "code-reviewer", "model": TIER_SONNET, "dimension": "documentation"},
                "refiner": {"name": "code-reviewer", "model": TIER_SONNET, "dimension": "refinement"}
            },
            "selected_at": datetime.now(timezone.utc).isoformat()
        }, indent=2))
        print(print_green("✓ UAT bypass complete"))
        return True

    # Display agent roles
    _display_agent_roles()

    # Select agents
    print(print_dim("─" * 100))
    print()
    print(print_bold("SELECT AGENTS"))
    print()

    clear_input_buffer()

    agents = _select_all_agents()

    # Display summary
    _display_selection_summary(agents)

    # Save agent selection
    # NOTE: Agent names here are display labels, not manifest IDs
    # TODO: validate against agent-manifest.json
    agent_data = {
        "review_agents": {
            "deep_code": {"name": agents["deep"], "model": TIER_OPUS, "dimension": "code_quality"},
            "architecture": {"name": agents["arch"], "model": TIER_SONNET, "dimension": "architecture"},
            "performance": {"name": agents["perf"], "model": TIER_SONNET, "dimension": "performance"},
            "documentation": {"name": agents["doc"], "model": TIER_HAIKU, "dimension": "documentation"},
            "refiner": {"name": agents["refiner"], "model": TIER_OPUS, "dimension": "refinement"}
        },
        "selected_at": datetime.now(timezone.utc).isoformat()
    }

    write_file(agents_file, json.dumps(agent_data, indent=2))

    print(print_green("✓ Agent Selection complete"))
    return True


def _display_agent_roles() -> None:
    """Display code review agent roles."""
    print(print_dim("─" * 100))
    print()
    print(print_bold("CODE REVIEW AGENT ROLES"))
    print()

    print(print_dim("Five agents work together for comprehensive code review:"))
    print()

    # Deep Code Reviewer
    print(print_cyan("─" * 100))
    print(print_bold("DEEP CODE REVIEWER"))
    print()
    print("  Reviews code for correctness, clarity, and maintainability.")
    print("  Checks logic, error handling, edge cases, and code smells.")
    print()
    print(print_green("  Recommended:") + " deep-code-reviewer-phd (opus)")
    print(print_dim("  Alternative:") + " senior-engineer, code-quality-expert")
    print(print_cyan("─" * 100))
    print()

    # Architecture Compliance
    print(print_magenta("─" * 100))
    print(print_bold("ARCHITECTURE COMPLIANCE"))
    print()
    print("  Verifies adherence to architectural patterns and design decisions.")
    print("  Checks dependency direction, layer separation, coupling.")
    print()
    print(print_green("  Recommended:") + " arch-compliance-phd (sonnet)")
    print(print_dim("  Alternative:") + " system-architect, design-pattern-expert")
    print(print_magenta("─" * 100))
    print()

    # Performance Analyzer
    print(print_yellow("─" * 100))
    print(print_bold("PERFORMANCE ANALYZER"))
    print()
    print("  Identifies performance bottlenecks and optimization opportunities.")
    print("  Reviews algorithmic complexity, memory usage, I/O patterns.")
    print()
    print(print_green("  Recommended:") + " perf-analyzer-phd (sonnet)")
    print(print_dim("  Alternative:") + " performance-engineer, optimization-specialist")
    print(print_yellow("─" * 100))
    print()

    # Documentation Reviewer
    print(print_blue("─" * 100))
    print(print_bold("DOCUMENTATION REVIEWER"))
    print()
    print("  Reviews code comments, API documentation, and README files.")
    print("  Ensures documentation matches implementation.")
    print()
    print(print_green("  Recommended:") + " doc-reviewer-phd (haiku)")
    print(print_dim("  Alternative:") + " technical-writer, api-doc-specialist")
    print(print_blue("─" * 100))
    print()

    # Code Refiner
    print(print_green("─" * 100))
    print(print_bold("CODE REFINER"))
    print()
    print("  Applies refinements based on review findings.")
    print("  Ensures tests continue to pass after changes.")
    print()
    print(print_green("  Recommended:") + " code-refiner-phd (opus)")
    print(print_dim("  Alternative:") + " refactoring-specialist, clean-code-expert")
    print(print_green("─" * 100))
    print()


def _select_agent(role_name: str, color_func, recommended: str, alternatives: list) -> str:
    """Select a single agent."""
    print(color_func(role_name))
    print(print_green("  [1]") + f" {recommended} (recommended)")
    for i, alt in enumerate(alternatives, 2):
        print(print_dim(f"  [{i}]") + f" {alt}")
    print(print_dim("  [c]") + " Custom agent name")
    print()

    choice = prompt_user("  Selection (default: 1): ").strip() or "1"

    if choice.lower() == 'c':
        agent_name = prompt_user("  Enter custom agent name: ").strip()
        if not agent_name.strip():
            agent_name = "code-reviewer"
        return agent_name

    try:
        idx = int(choice)
        if idx == 1:
            return recommended
        elif 2 <= idx <= len(alternatives) + 1:
            return alternatives[idx - 2]
    except ValueError:
        pass

    return recommended


def _select_all_agents() -> Dict[str, str]:
    """Select all review agents interactively."""
    agents = {}

    # Deep Code Reviewer
    agents["deep"] = _select_agent(
        "Deep Code Reviewer",
        print_cyan,
        "deep-code-reviewer-phd",
        ["senior-engineer", "code-quality-expert"]
    )
    print()

    # Architecture Compliance
    agents["arch"] = _select_agent(
        "Architecture Compliance",
        print_magenta,
        "arch-compliance-phd",
        ["system-architect", "design-pattern-expert"]
    )
    print()

    # Performance Analyzer
    agents["perf"] = _select_agent(
        "Performance Analyzer",
        print_yellow,
        "perf-analyzer-phd",
        ["performance-engineer", "optimization-specialist"]
    )
    print()

    # Documentation Reviewer
    agents["doc"] = _select_agent(
        "Documentation Reviewer",
        print_blue,
        "doc-reviewer-phd",
        ["technical-writer", "api-doc-specialist"]
    )
    print()

    # Code Refiner
    agents["refiner"] = _select_agent(
        "Code Refiner",
        print_green,
        "code-refiner-phd",
        ["refactoring-specialist", "clean-code-expert"]
    )
    print()

    return agents


def _display_selection_summary(agents: Dict[str, str]) -> None:
    """Display agent selection summary."""
    print(print_dim("─" * 100))
    print()
    print(print_bold("AGENT SELECTION SUMMARY"))
    print()

    print(print_cyan("  Deep Code:    ") + agents["deep"])
    print(print_magenta("  Architecture: ") + agents["arch"])
    print(print_yellow("  Performance:  ") + agents["perf"])
    print(print_blue("  Documentation: ") + agents["doc"])
    print(print_green("  Refiner:      ") + agents["refiner"])
    print()


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 602: Agent Selection")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
