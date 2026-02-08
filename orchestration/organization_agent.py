"""
Organization Agent Module

Enforces strict file placement rules to maintain clean codebase organization.

Runs after each task to ensure no artifacts are misplaced.
Creates BLOCKERS if files are found in wrong locations.

Allowed locations:
- .outputs/{phase}/prompts/      # LLM prompts
- .outputs/{phase}/outputs/      # LLM responses
- .claude/specs/                 # Specifications
- .state/                        # State files
- .logs/                         # Log files
- reports/                       # Scratch work ONLY
- ../src/                        # Generated project code
- ../tests/                      # Generated project tests
- ../docs/                       # Generated project docs
- core/, phases/, orchestration/ # Tool code
"""

from pathlib import Path
from typing import List, Dict, Any
import json


ALLOWED_LOCATIONS = {
    "prompts": ".outputs/{phase}/prompts/",
    "outputs": ".outputs/{phase}/outputs/",
    "specs": ".claude/specs/",
    "state": ".state/",
    "logs": ".logs/",
    "reports": "reports/",
    "generated_code": "../src/",
    "generated_tests": "../tests/",
    "generated_docs": "../docs/",
}

# Core directories that should never have misplaced files
PROTECTED_DIRS = {"core", "phases", "orchestration", "dashboard", "config", "docs"}


def check_organization(phase_id: str, task_id: str) -> List[Dict[str, Any]]:
    """
    Check for misplaced files after task completion.

    Args:
        phase_id: Current phase (e.g., "2-prd")
        task_id: Current task (e.g., "205")

    Returns:
        List of misplaced files with:
        - path: Relative path to misplaced file
        - correct_location: Where it should be
        - reason: Why it's misplaced
    """
    misplaced = []
    acp_root = Path(__file__).parent.parent

    # Scan atomic-claude2 directory for unexpected files
    for item in acp_root.rglob("*"):
        # Skip directories
        if item.is_dir():
            continue

        # Skip hidden files and __pycache__
        if item.name.startswith(".") or "__pycache__" in str(item):
            continue

        # Skip tool files in protected directories
        if any(part in PROTECTED_DIRS for part in item.relative_to(acp_root).parts):
            continue

        # Check if file is in allowed location
        if not is_allowed_location(item, phase_id, acp_root):
            misplaced.append({
                "path": str(item.relative_to(acp_root)),
                "correct_location": suggest_location(item, phase_id),
                "reason": classify_file(item)
            })

    return misplaced


def is_allowed_location(file_path: Path, phase_id: str, acp_root: Path) -> bool:
    """
    Check if file is in an allowed location.

    Args:
        file_path: Absolute path to file
        phase_id: Current phase
        acp_root: Root of atomic-claude2 directory

    Returns:
        bool: True if file is properly placed
    """
    rel_path = str(file_path.relative_to(acp_root))

    # Check against allowed patterns
    for location_type, pattern in ALLOWED_LOCATIONS.items():
        pattern = pattern.format(phase=phase_id)

        # Handle parent directory references (../)
        if pattern.startswith("../"):
            # These are outside atomic-claude2, skip
            continue

        if rel_path.startswith(pattern):
            return True

    # Check if it's a tool file
    if any(rel_path.startswith(d) for d in ["core/", "phases/", "orchestration/", "dashboard/", "config/", "docs/"]):
        return True

    # Check if it's a package file
    if file_path.name in ["__init__.py", "main.py", "README.md", ".gitignore"]:
        return True

    return False


def suggest_location(file_path: Path, phase_id: str) -> str:
    """
    Suggest correct location for misplaced file.

    Args:
        file_path: Path to misplaced file
        phase_id: Current phase

    Returns:
        str: Suggested location
    """
    name = file_path.name.lower()
    suffix = file_path.suffix.lower()

    # Classify by filename patterns
    if "prompt" in name:
        return f".outputs/{phase_id}/prompts/"
    elif "output" in name or "response" in name:
        return f".outputs/{phase_id}/outputs/"
    elif "spec" in name:
        return ".claude/specs/"
    elif suffix in [".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs"]:
        return "../src/"
    elif "test" in name:
        return "../tests/"
    elif suffix in [".md", ".rst", ".txt"] and "readme" not in name:
        return "../docs/"
    else:
        return "reports/"  # When in doubt, scratch folder


def classify_file(file_path: Path) -> str:
    """
    Classify what type of file this is.

    Args:
        file_path: Path to file

    Returns:
        str: Classification (e.g., "LLM prompt", "Generated code")
    """
    name = file_path.name.lower()
    suffix = file_path.suffix.lower()

    if "prompt" in name:
        return "LLM prompt"
    elif "output" in name or "response" in name:
        return "LLM response"
    elif suffix in [".py", ".js", ".ts", ".jsx", ".tsx"]:
        return "Generated code"
    elif "test" in name:
        return "Test file"
    elif suffix == ".md":
        return "Documentation"
    else:
        return "Unknown artifact"


def fix_organization(misplaced: List[Dict[str, Any]]) -> bool:
    """
    Attempt to automatically fix organization issues.

    Args:
        misplaced: List of misplaced files from check_organization()

    Returns:
        bool: True if all fixes succeeded
    """
    acp_root = Path(__file__).parent.parent

    for file_info in misplaced:
        src = acp_root / file_info["path"]
        dst_dir = acp_root / file_info["correct_location"]

        # Create destination directory
        dst_dir.mkdir(parents=True, exist_ok=True)

        # Move file
        dst = dst_dir / src.name

        try:
            src.rename(dst)
            print(f"   ✓ Moved {file_info['path']} → {file_info['correct_location']}")
        except Exception as e:
            print(f"   ✗ Failed to move {file_info['path']}: {e}")
            return False

    return True
