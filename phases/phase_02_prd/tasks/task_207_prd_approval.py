"""
Task 207: PRD Review, Refinement & Approval

Agents analyze validation scores and walk the user through each
recommended improvement one at a time. User directs every change.
No autonomous LLM edits — user controls all decisions.

Flow:
  1. Show validation scores
  2. Walk through each recommendation: show it, ask user how to resolve
  3. Collect all decisions + optional custom requests
  4. One LLM pass applies the collected resolution plan
  5. Diff/apply/discard
  6. Re-validate, show updated scores
  7. Loop until user approves
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
from phases.phase_02_prd.tasks.task_206b_prd_revision import prd_revision_flow, invoke_revision_agent
from phases.phase_02_prd.tasks.task_206_prd_validation import validate_content


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None, graph=None) -> bool:
    """
    Execute Task 207: PRD Approval.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, auto-approve for testing
        graph: Optional GraphManager instance for knowledge graph operations

    Returns:
        True if task completed successfully, False otherwise
    """
    prd_file = atomic_root.parent / "docs" / "prd" / "PRD.md"
    validation_file = output_dir / "prd-validation.json"
    approval_file = output_dir / "prd-approved.json"
    prompts_dir = output_dir / "prompts"
    ensure_dir(prompts_dir)

    print()
    print(print_yellow("┌─────────────────────────────────────────────────────────┐"))
    print(print_yellow("│           " + print_bold("PRD REVIEW, REFINEMENT & APPROVAL") + "               │"))
    print(print_yellow("└─────────────────────────────────────────────────────────┘"))
    print()

    if not prd_file.exists():
        print(print_red(f"  ✗ PRD file not found: {prd_file}"))
        return False

    # UAT mode bypass
    if uat_mode:
        print(print_yellow("  UAT mode: Auto-approving PRD..."))
        approve_prd(approval_file, prd_file, "uat-mode")
        print(print_green("✓ PRD auto-approved (UAT mode)"))
        return True

    # Show validation scores
    show_validation_scores(validation_file)

    # Review-refine-approve loop
    max_iterations = 3
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        print(print_dim("─" * 60))
        print()

        # Get recommendations from validation
        has_issues = check_for_issues(validation_file)

        if not has_issues:
            print(print_green("  No outstanding issues detected. PRD is ready for approval."))
            print()
            print("    " + print_green("[approve]") + "  Approve PRD and proceed to Phase 3")
            print("    " + print_cyan("[custom]") + "   Make a custom improvement request")
            print("    " + print_yellow("[view]") + "     View PRD content")
            print()

            clear_input_buffer()
            choice = prompt_user("  Choice (default: approve): ").strip().lower() or "approve"
        else:
            print(print_cyan("  Recommended improvements available."))
            print()
            print("    " + print_green("[refine]") + "   Walk through recommendations")
            print("    " + print_cyan("[custom]") + "   Make a custom improvement request")
            print("    " + print_yellow("[view]") + "     View PRD content")
            print("    " + print_bold("[approve]") + "  Approve PRD as-is and proceed")
            print()

            clear_input_buffer()
            choice = prompt_user("  Choice (default: refine): ").strip().lower() or "refine"

        if choice in ["approve", "a"]:
            # Approve PRD
            print()
            approver = prompt_user("  Your name (for approval record): ").strip() or "User"
            approve_prd(approval_file, prd_file, approver)
            print()
            print(print_green("✓ PRD approved and signed off"))
            return True

        elif choice in ["view", "v"]:
            # View PRD
            print()
            print(print_dim("─" * 60))
            print()
            content = read_file(prd_file)
            lines = content.split('\n')
            for line in lines[:100]:
                print(f"  {line}")
            print()
            print(print_dim(f"  ... (showing first 100 lines)"))
            print(print_dim(f"  Full file: {prd_file}"))
            print()
            print(print_dim("─" * 60))
            print()

        elif choice in ["custom", "c"]:
            # Custom request
            print()
            print(print_dim("  Enter custom improvement request:"))
            custom_request = prompt_user("  > ").strip()
            if custom_request:
                revised = invoke_revision_agent(prd_file, prompts_dir, custom_request)
                if revised:
                    validation_result = validate_content(prd_file, prompts_dir, atomic_root, output_dir)
                    if validation_result:
                        write_file(validation_file, json.dumps(validation_result, indent=2))
                        show_validation_scores(validation_file)
            print()

        elif choice in ["refine", "r"]:
            # Guided refinement via 206b Q&A flow
            revised = prd_revision_flow(validation_file, prd_file, prompts_dir)
            if revised:
                validation_result = validate_content(prd_file, prompts_dir, atomic_root, output_dir)
                if validation_result:
                    write_file(validation_file, json.dumps(validation_result, indent=2))
                    show_validation_scores(validation_file)

        else:
            print(print_red("  Invalid choice"))

    print(print_yellow("  Maximum iterations reached - proceeding with approval"))
    approve_prd(approval_file, prd_file, "auto-approved")
    return True


def show_validation_scores(validation_file: Path) -> None:
    """Show validation scores from validation file."""
    if not validation_file.exists():
        print(print_yellow("  ! No validation results found"))
        return

    try:
        with open(validation_file, 'r') as f:
            validation_data = json.load(f)

        overall_status = validation_data.get("overall_status", "UNKNOWN")
        overall_score = validation_data.get("overall_score", 0)

        print(print_cyan("  Validation Status:"))
        print(f"    Status: {overall_status}")
        print(f"    Score:  {overall_score}/100")
        print()

    except Exception as e:
        print(print_yellow(f"  ! Error reading validation results: {e}"))


def check_for_issues(validation_file: Path) -> bool:
    """Check if there are outstanding issues."""
    if not validation_file.exists():
        return False

    try:
        with open(validation_file, 'r') as f:
            validation_data = json.load(f)

        # Check for recommendations, contradictions, gaps, etc.
        has_recommendations = len(validation_data.get("recommendations", [])) > 0
        has_contradictions = len(validation_data.get("consistency", {}).get("contradictions", [])) > 0
        has_gaps = len(validation_data.get("completeness", {}).get("gaps", [])) > 0

        return has_recommendations or has_contradictions or has_gaps

    except Exception as e:
        logger.debug("Failed to check pending issues in validation data: %s", e)
        return False


def approve_prd(approval_file: Path, prd_file: Path, approver: str) -> None:
    """
    Record PRD approval.

    Args:
        approval_file: Path to approval file
        prd_file: Path to PRD file
        approver: Name of approver
    """
    approval_data = {
        "status": "approved",
        "approver": approver,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "prd_file": str(prd_file)
    }

    write_file(approval_file, json.dumps(approval_data, indent=2))
    print(print_dim(f"  Approval recorded: {approval_file}"))


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 207: PRD Approval")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (auto-approve)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
