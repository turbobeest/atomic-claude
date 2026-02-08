"""
Git Manager Module

Handles commit/push prompts after task completion.
Generates contextual commit messages based on task context.
"""

import subprocess
from pathlib import Path
from typing import Optional


def prompt_git_actions(phase_id: str, task_id: str) -> str:
    """
    Prompt user for git actions after task completion.

    Args:
        phase_id: Phase identifier (e.g., "2-prd")
        task_id: Task identifier (e.g., "205")

    Returns:
        str: Action chosen ("commit", "commit_push", or "skip")
    """
    print("\n📦 Git Actions")
    print("   [1] Commit changes")
    print("   [2] Commit & push")
    print("   [3] Skip")

    choice = input("\nChoice (default: skip): ").strip()

    if choice == "1":
        return "commit"
    elif choice == "2":
        return "commit_push"
    else:
        return "skip"


def commit_changes(phase_id: str, task_id: str, custom_message: Optional[str] = None) -> bool:
    """
    Commit changes with auto-generated or custom message.

    Args:
        phase_id: Phase identifier
        task_id: Task identifier
        custom_message: Optional custom commit message

    Returns:
        bool: True if commit succeeded
    """
    # Generate commit message if not provided
    if not custom_message:
        message = generate_commit_message(phase_id, task_id)

        print(f"\n💬 Commit message:")
        print("-" * 60)
        print(message)
        print("-" * 60)

        confirm = input("\nCommit with this message? (y/n): ").lower()

        if confirm != "y":
            custom_message = input("Enter custom message: ")
            if not custom_message:
                print("❌ Commit cancelled")
                return False
            message = custom_message
    else:
        message = custom_message

    # Stage and commit
    try:
        subprocess.run(["git", "add", "."], check=True, cwd="..")
        subprocess.run(["git", "commit", "-m", message], check=True, cwd="..")
        print("✅ Changes committed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Commit failed: {e}")
        return False


def push_changes() -> bool:
    """
    Push changes to remote.

    Returns:
        bool: True if push succeeded
    """
    try:
        subprocess.run(["git", "push"], check=True, cwd="..")
        print("✅ Changes pushed to remote")
        return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Push failed: {e}")
        print("   Check git status and try manually")
        return False


def generate_commit_message(phase_id: str, task_id: str) -> str:
    """
    Generate contextual commit message based on phase and task.

    Args:
        phase_id: Phase identifier (e.g., "2-prd")
        task_id: Task identifier (e.g., "205")

    Returns:
        str: Generated commit message
    """
    # Map of task-specific commit messages
    messages = {
        "0-setup": {
            "001": "chore(setup): Configure pipeline mode",
            "002": "chore(setup): Collect project configuration",
            "004": "chore(setup): Configure API keys",
            "009": "chore(setup): Complete environment check",
        },
        "2-prd": {
            "201": "docs(prd): Initialize PRD phase",
            "203": "docs(prd): Complete PRD interview",
            "204": "docs(prd): Select agents for PRD authoring",
            "205": "docs(prd): Generate comprehensive PRD\n\nCompleted 8-stage PRD generation with:\n- Vision & executive summary\n- Technical architecture\n- Feature requirements (FR-001 through FR-NNN)\n- Non-functional requirements\n- Logical dependency chain\n- Development phases",
            "206": "docs(prd): Validate PRD structure and content",
            "207": "docs(prd): PRD approved by stakeholders",
            "209": "docs(prd): Complete PRD phase closeout",
        },
        "3-tasking": {
            "301": "feat(tasking): Initialize task decomposition",
            "304": "feat(tasking): Complete dependency analysis",
            "306": "feat(tasking): Complete tasking phase closeout",
        },
        "5-implementation": {
            "504": "feat(impl): Complete TDD implementation cycle",
            "507": "feat(impl): Complete implementation phase closeout",
        },
        "6-code-review": {
            "604": "refactor(review): Complete code refinement",
            "606": "refactor(review): Complete code review phase closeout",
        },
    }

    # Try to find specific message
    if phase_id in messages and task_id in messages[phase_id]:
        return messages[phase_id][task_id]

    # Generate generic message
    phase_name = phase_id.split("-", 1)[1] if "-" in phase_id else phase_id
    return f"feat({phase_name}): Complete task {task_id}"


def check_git_status() -> dict:
    """
    Check current git status.

    Returns:
        dict: Git status info (has_changes, branch, etc.)
    """
    try:
        # Check if we're in a git repo
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            check=True,
            capture_output=True,
            cwd=".."
        )

        # Get branch name
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            check=True,
            capture_output=True,
            text=True,
            cwd=".."
        )
        branch = result.stdout.strip()

        # Check for changes
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
            cwd=".."
        )
        has_changes = bool(result.stdout.strip())

        return {
            "in_git_repo": True,
            "branch": branch,
            "has_changes": has_changes,
        }

    except subprocess.CalledProcessError:
        return {"in_git_repo": False}
