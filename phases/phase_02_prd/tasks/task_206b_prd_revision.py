"""
Task 206b: PRD Revision (LLM-Assisted Q&A)

Invoked from task 206 when user chooses to revise the PRD.

Flow:
  1. Read validation results
  2. Group issues by priority (P0 first)
  3. For each issue: show it, ask user how to resolve
  4. Collect all decisions into a resolution plan
  5. Invoke Opus once with the PRD + all user decisions
  6. Show diff, apply/discard
  7. Return to task 206 for re-validation

Note: This is a helper module invoked by task 206, not a standalone task.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.llm import invoke
from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, print_magenta, prompt_user, clear_input_buffer
)
from core.utils.file_ops import read_file, write_file


def prd_revision_flow(
    validation_file: Path,
    prd_file: Path,
    prompts_dir: Path
) -> bool:
    """
    Execute PRD revision Q&A flow.

    Args:
        validation_file: Path to validation results
        prd_file: Path to PRD file
        prompts_dir: Path to prompts directory

    Returns:
        True if revision completed, False if aborted
    """
    print()
    print_cyan("┌─────────────────────────────────────────────────────────┐")
    print_cyan("│ " + print_bold("PRD REVISION — GUIDED Q&A") + "                               │")
    print_cyan("└─────────────────────────────────────────────────────────┘")
    print()
    print_dim("  Walk through each issue and decide how to resolve it.")
    print_dim("  Your decisions will be applied in one pass by the revision agent.")
    print()

    # Load validation results
    try:
        with open(validation_file, 'r') as f:
            validation_data = json.load(f)
    except Exception as e:
        print_red(f"  ✗ Error loading validation results: {e}")
        return False

    # Collect issues from validation
    issues = collect_issues(validation_data)

    if not issues:
        print_yellow("  No issues found in validation results.")
        print()
        manual_input = prompt_user("  Enter revision instructions manually (or Enter to skip): ").strip()
        if not manual_input:
            return False

        return invoke_revision_agent(prd_file, prompts_dir, manual_input)

    # Q&A session
    resolution_plan = conduct_qa_session(issues)

    if not resolution_plan:
        print_yellow("  No resolutions to apply.")
        return False

    # Apply revisions
    return invoke_revision_agent(prd_file, prompts_dir, resolution_plan)


def collect_issues(validation_data: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Collect issues from validation results.

    Args:
        validation_data: Validation results

    Returns:
        List of issue dictionaries
    """
    issues = []

    # Contradictions (highest priority)
    for item in validation_data.get("consistency", {}).get("contradictions", []):
        issues.append({
            "type": "CONTRADICTION",
            "detail": item,
            "priority": 0
        })

    # Completeness gaps
    for item in validation_data.get("completeness", {}).get("gaps", []):
        issues.append({
            "type": "GAP",
            "detail": item,
            "priority": 1
        })

    # Recommendations
    for item in validation_data.get("recommendations", []):
        priority = 2
        if item.startswith("P0:"):
            priority = 0
        elif item.startswith("P1:"):
            priority = 1

        issues.append({
            "type": "RECOMMENDATION",
            "detail": item,
            "priority": priority
        })

    # Sort by priority
    issues.sort(key=lambda x: x["priority"])

    return issues


def conduct_qa_session(issues: List[Dict[str, str]]) -> str:
    """
    Conduct Q&A session for issue resolution.

    Args:
        issues: List of issues

    Returns:
        Resolution plan string
    """
    total = len(issues)

    print(f"  {print_bold(f'{total} issues to review.')} For each one you can:")
    print("    " + print_green("Enter") + "       Accept the suggested fix (default)")
    print("    " + print_cyan("Type") + "        Provide your own resolution direction")
    print("    " + print_yellow("skip") + "        Skip this issue (don't fix)")
    print("    " + print_red("done") + "        Stop reviewing, apply what you've decided so far")
    print()
    print_dim("─" * 60)

    resolution_plan = ""
    resolved_count = 0
    skipped_count = 0

    for idx, issue in enumerate(issues):
        num = idx + 1
        issue_type = issue["type"]
        detail = issue["detail"]

        # Color by type
        if issue_type == "CONTRADICTION":
            color = print_red
        elif issue_type == "GAP":
            color = print_yellow
        else:
            color = print_cyan

        print()
        print(f"  {color(f'[{issue_type}]')} {print_bold(f'({num}/{total})')}")
        print(f"  {detail}")
        print()

        # Suggest resolution
        suggestion = suggest_resolution(issue_type, detail)
        print_dim(f"  Suggested: {suggestion}")

        user_response = prompt_user("  Resolution (default: accept): ").strip()

        if user_response == "done":
            print()
            print_dim(f"  Stopping review. {total - num} issues remaining.")
            break
        elif user_response in ["skip", "s"]:
            skipped_count += 1
            print_dim("    -> Skipped")
            continue
        elif not user_response or user_response in ["accept", "a"]:
            resolution_plan += f"{resolved_count + 1}. [{issue_type}] {detail}\n   RESOLUTION: {suggestion}\n\n"
            resolved_count += 1
            print_green(f"    -> {suggestion}")
        else:
            resolution_plan += f"{resolved_count + 1}. [{issue_type}] {detail}\n   RESOLUTION: {user_response}\n\n"
            resolved_count += 1
            print_green(f"    -> {user_response}")

    print()
    print_dim("─" * 60)
    print()
    print(f"  {print_bold('Review complete:')} {resolved_count} resolved, {skipped_count} skipped")
    print()

    return resolution_plan if resolved_count > 0 else ""


def suggest_resolution(issue_type: str, detail: str) -> str:
    """Suggest resolution based on issue type."""
    if issue_type == "CONTRADICTION":
        return "Resolve in favor of Phase 1 original requirements"
    elif issue_type == "GAP":
        return "Add the missing content to the appropriate section"
    elif issue_type == "RECOMMENDATION":
        return "Apply this recommendation as described"
    else:
        return "Address this issue appropriately"


def invoke_revision_agent(
    prd_file: Path,
    prompts_dir: Path,
    resolution_plan: str
) -> bool:
    """
    Invoke revision agent to apply changes.

    Args:
        prd_file: Path to PRD file
        prompts_dir: Path to prompts directory
        resolution_plan: Resolution plan from Q&A

    Returns:
        True if revision applied successfully
    """
    print()
    print_cyan("  Invoking revision agent...")

    # Build revision prompt
    prd_content = read_file(prd_file)

    prompt = f"""# Task: Revise PRD Based on User Decisions

You are revising this PRD based on specific user decisions.

## Current PRD

{prd_content}

## User-Directed Resolutions

{resolution_plan}

## Instructions

Apply each resolution exactly as the user specified. Make minimal changes - only what's needed to address each resolution.

Return the complete revised PRD in markdown format.
"""

    # Save prompt
    prompt_file = prompts_dir / "prd-revision-prompt.md"
    write_file(prompt_file, prompt)

    # Invoke LLM
    try:
        output_file = prompts_dir / "prd-revision-output.md"

        success = invoke(
            prompt=prompt,
            output_file=str(output_file),
            model="opus",
            temperature=0.2
        )

        if success and output_file.exists():
            revised_content = read_file(output_file)

            # Show diff and ask to apply
            print()
            print_green("  ✓ Revision generated")
            print()
            print("    " + print_green("[apply]") + "   Apply revision")
            print("    " + print_red("[discard]") + " Discard and keep current PRD")
            print()

            choice = prompt_user("  Choice (default: apply): ").strip().lower() or "apply"

            if choice == "apply":
                # Backup current PRD
                backup_file = prd_file.parent / f"PRD.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                write_file(backup_file, prd_content)

                # Apply revision
                write_file(prd_file, revised_content)
                print_green(f"  ✓ Revision applied (backup: {backup_file.name})")
                return True
            else:
                print_yellow("  Revision discarded")
                return False
        else:
            print_red("  ✗ Revision generation failed")
            return False

    except Exception as e:
        print_red(f"  ✗ Error during revision: {e}")
        return False


if __name__ == "__main__":
    # This module is meant to be imported, not run directly
    print("This module should be imported by task 206, not run directly.")
    sys.exit(1)
