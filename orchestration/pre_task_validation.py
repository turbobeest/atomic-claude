"""
Pre-Task Validation Module

FORCING FUNCTION: Ensures atomic-claude2 directory is pristine before each task runs.

This is a BLOCKER - tasks cannot proceed if project artifacts are found in the tool directory.

Philosophy:
- atomic-claude2 is a TOOL, not a project
- ALL project code must live in parent directory (../src/, ../tests/, ../docs/)
- ONLY tool code and runtime artifacts allowed in atomic-claude2/

Violations are HARD ERRORS - the pipeline stops until they're fixed.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any
import sys

logger = logging.getLogger(__name__)


# Allowed patterns in atomic-claude2 directory
ALLOWED_PATTERNS = {
    # Tool code
    "core/**/*.py",
    "phases/**/*.py",
    "phases/**/*.sh",  # Task scripts (initially bash, then Python)
    "orchestration/**/*.py",
    "dashboard/**/*.js",
    "dashboard/**/*.html",
    "dashboard/**/*.css",
    "main.py",

    # Tool docs
    "README.md",
    "PROJECT-STRUCTURE.md",
    "REFACTORING-PLAN*.md",
    "docs/**/*.md",

    # Tool config
    "config/**/*.yaml",
    "config/**/*.yml",
    "dashboard/package.json",

    # Runtime artifacts (OK)
    ".outputs/**/*",
    ".state/**/*",
    ".logs/**/*",
    "reports/**/*",  # Scratch work

    # Python package files
    "**/__init__.py",
    "**/__pycache__/**",
    "**/*.pyc",

    # Git, IDE, OS files
    ".git/**/*",
    ".gitignore",
    ".vscode/**/*",
    ".idea/**/*",
    ".DS_Store",
}

# Forbidden file types (project artifacts that should NEVER be in tool directory)
FORBIDDEN_TYPES = {
    # Generated project code
    ".js": "../src/ (unless it's dashboard/server.js)",
    ".ts": "../src/",
    ".tsx": "../src/",
    ".jsx": "../src/",
    ".java": "../src/",
    ".go": "../src/",
    ".rs": "../src/",
    ".cpp": "../src/",
    ".c": "../src/",
    ".h": "../src/",

    # Test files (unless they're tool tests)
    "_test.py": "../tests/",
    "_spec.py": "../tests/",
    ".test.js": "../tests/",
    ".spec.js": "../tests/",

    # Data files
    ".csv": "parent directory or ../data/",
    ".db": "parent directory or ../data/",
    ".sqlite": "parent directory or ../data/",
    ".sql": "parent directory or ../migrations/",

    # Notebooks
    ".ipynb": "../notebooks/ or parent directory",

    # Binaries
    ".exe": "should never exist",
    ".dll": "should never exist",
    ".dylib": "should never exist",

    # Archives
    ".zip": "should never exist",
    ".tar": "should never exist",
}


def validate_directory_pristine(phase_id: str, task_id: str) -> bool:
    """
    BLOCKING validation: Ensure atomic-claude2 contains ONLY tool files.

    Args:
        phase_id: Current phase (e.g., "2-prd")
        task_id: Current task (e.g., "205")

    Returns:
        bool: True if directory is pristine, False if violations found
    """
    # Skip validation when developing the tool itself
    import os
    if os.environ.get("ATOMIC_TOOL_DEVELOPMENT") == "true":
        return True

    violations = find_violations()

    if not violations:
        return True

    # BLOCKER: Print violations and abort
    print("\n" + "="*80)
    print("  🚨 PRE-TASK VALIDATION FAILED 🚨")
    print("="*80)
    print(f"\nFound {len(violations)} project artifact(s) in atomic-claude2 directory!")
    print("\n⚠️  atomic-claude2 is a TOOL, not a project.")
    print("   ALL project code must live in the parent directory.\n")

    for violation in violations:
        print(f"❌ {violation['path']}")
        print(f"   → Should be in: {violation['correct_location']}")
        print(f"   → Reason: {violation['reason']}\n")

    print("="*80)
    print("  TASK BLOCKED - FIX VIOLATIONS FIRST")
    print("="*80)
    print("\nOptions:")
    print("  1. Move files to correct locations manually")
    print("  2. Run: python main.py cleanup (auto-fix)")
    print("  3. Delete files if they're mistakes\n")

    return False


def find_violations() -> List[Dict[str, Any]]:
    """
    Scan atomic-claude2 for project artifacts.

    Returns:
        List of violations with path, correct location, and reason
    """
    import os as _os

    violations = []
    acp_root = Path(__file__).parent.parent

    # Prune directories we never need to scan (fast: avoids traversing them at all)
    _PRUNE_DIRS = {".git", ".venv", ".outputs", ".state", ".logs", ".claude",
                   ".vscode", ".idea", "__pycache__", "node_modules", "htmlcov"}

    for dirpath, dirnames, filenames in _os.walk(acp_root):
        # Prune in-place so os.walk won't descend into them
        dirnames[:] = [d for d in dirnames if d not in _PRUNE_DIRS and not d.startswith(".")]

        for fname in filenames:
            item = Path(dirpath) / fname

            # Skip dotfiles (except .gitignore, .DS_Store)
            if fname.startswith(".") and fname not in (".gitignore", ".DS_Store"):
                continue

            # Check if file is allowed
            if not is_allowed_file(item, acp_root):
                violation = classify_violation(item, acp_root)
                if violation:
                    violations.append(violation)

    return violations


def is_allowed_file(file_path: Path, acp_root: Path) -> bool:
    """
    Check if file is an allowed tool file.

    Args:
        file_path: Absolute path to file
        acp_root: Root of atomic-claude2 directory

    Returns:
        bool: True if file is allowed in tool directory
    """
    rel_path = file_path.relative_to(acp_root)

    # Check against allowed patterns
    allowed_dirs = {
        # Tool source code
        "core", "phases", "orchestration", "dashboard", "lib",
        # Tool assets
        "agents", "audits", "skills", "scripts", "examples",
        # Tool testing
        "tests", "test",
        # Tool config and docs
        "config", "docs", "initialization",
        # Runtime artifacts
        ".outputs", ".state", ".logs", "reports",
        # Environment and IDE
        ".git", ".venv", ".claude", ".vscode", ".idea",
    }

    # Check if in allowed top-level directory
    if rel_path.parts[0] in allowed_dirs:
        return True

    # Check if it's a root-level allowed file
    allowed_root_files = {
        "main.py", "README.md", "CLAUDE.md", "OPERATIONAL.md",
        ".gitignore", ".DS_Store",
        ".claudeignore", ".env.example", ".env",
        "setup.py", "MANIFEST.in",
        "pytest.ini", "coverage.xml",
        "requirements.txt", "requirements-dev.txt", "requirements-llm.txt",
        "docker-compose.yml", "docker-compose.yaml",
    }
    if str(rel_path) in allowed_root_files:
        return True

    # Allow root-level tool planning/config files by prefix
    if len(rel_path.parts) == 1 and (
        file_path.name.startswith("PLAN-")
        or file_path.name.startswith("REFACTORING-")
        or file_path.name == "PROJECT-STRUCTURE.md"
    ):
        return True

    # Allow log files at root (e.g., excalidraw.log)
    if len(rel_path.parts) == 1 and file_path.suffix == ".log":
        return True

    # Check for __init__.py anywhere
    if file_path.name == "__init__.py":
        return True

    return False


def classify_violation(file_path: Path, acp_root: Path) -> Dict[str, Any]:
    """
    Classify what kind of violation this is and where it should go.

    Args:
        file_path: Path to violating file
        acp_root: Root of atomic-claude2 directory

    Returns:
        dict: Violation info (path, correct_location, reason)
    """
    rel_path = file_path.relative_to(acp_root)
    suffix = file_path.suffix.lower()
    name = file_path.name.lower()

    # Check against forbidden types
    for forbidden_suffix, correct_loc in FORBIDDEN_TYPES.items():
        if suffix == forbidden_suffix or name.endswith(forbidden_suffix):
            return {
                "path": str(rel_path),
                "correct_location": correct_loc,
                "reason": f"Project artifact ({forbidden_suffix} file)"
            }

    # Check for project code patterns
    if suffix in [".js", ".ts", ".jsx", ".tsx"] and "dashboard" not in str(rel_path):
        return {
            "path": str(rel_path),
            "correct_location": "../src/",
            "reason": "Generated project code"
        }

    if suffix == ".py" and ("test" in name or "spec" in name):
        if not str(rel_path).startswith("tests/"):  # Allow tests/ directory for tool tests
            return {
                "path": str(rel_path),
                "correct_location": "../tests/",
                "reason": "Project test file"
            }

    if suffix == ".md" and not any(allowed in str(rel_path) for allowed in [
        "README.md", "CLAUDE.md", "OPERATIONAL.md", "PROJECT-STRUCTURE.md",
        "docs/", "reports/"
    ]) and not file_path.name.startswith("PLAN-") and not file_path.name.startswith("REFACTORING-"):
        return {
            "path": str(rel_path),
            "correct_location": "../docs/ or reports/ (if scratch work)",
            "reason": "Project documentation"
        }

    # Generic violation
    return {
        "path": str(rel_path),
        "correct_location": "parent directory or reports/ (if scratch work)",
        "reason": "Unexpected file in tool directory"
    }


def auto_cleanup() -> bool:
    """
    Automatically move violations to correct locations.

    Returns:
        bool: True if cleanup succeeded
    """
    violations = find_violations()

    if not violations:
        print("✅ Directory is pristine - no cleanup needed")
        return True

    print(f"\n🧹 Cleaning up {len(violations)} violation(s)...\n")

    acp_root = Path(__file__).parent.parent

    for violation in violations:
        src = acp_root / violation["path"]

        # Determine destination
        if violation["correct_location"] == "parent directory or reports/ (if scratch work)":
            # Move to reports as safe default
            dst_dir = acp_root / "reports"
        elif violation["correct_location"].startswith("../"):
            # Move to parent directory
            dst_dir = acp_root.parent / violation["correct_location"].replace("../", "")
        else:
            # Other location
            dst_dir = acp_root.parent / violation["correct_location"]

        # Create destination directory
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / src.name

        try:
            src.rename(dst)
            print(f"✓ Moved {violation['path']} → {dst}")
        except Exception as e:
            print(f"✗ Failed to move {violation['path']}: {e}")
            return False

    print("\n✅ Cleanup complete!")
    return True


if __name__ == "__main__":
    # Can be run standalone for manual validation
    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        success = auto_cleanup()
        sys.exit(0 if success else 1)
    else:
        violations = find_violations()
        if violations:
            print(f"Found {len(violations)} violations")
            for v in violations:
                print(f"  - {v['path']}")
            sys.exit(1)
        else:
            print("✅ Directory pristine")
            sys.exit(0)
