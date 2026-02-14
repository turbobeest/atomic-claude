"""
Task 006: Reference Materials

Finds existing project materials scattered in the project root,
offers to organize them into ./docs/reference/, and suggests
what additional materials would help.
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user, clear_input_buffer
)
from core.utils.file_ops import ensure_dir, read_file, write_file


# ---------------------------------------------------------------------------
# Material categories for suggestions
# ---------------------------------------------------------------------------

MATERIAL_CATEGORIES = [
    ("Visual References", "Screenshots, wireframes, mockups, UI inspiration"),
    ("Analogous Systems", "Links or docs describing similar products to emulate"),
    ("Prior Discovery Work", "Chat transcripts, brainstorming notes, LLM conversations"),
    ("Requirements & Specs", "PRDs, ICDs, API specs, technical requirements"),
    ("Vision Documents", "Product vision, roadmaps, strategic goals"),
]

# Patterns for finding existing materials in the project root
# (filename pattern, description for display)
SCAN_PATTERNS = [
    "*.md", "*.txt", "*.pdf", "*.doc", "*.docx",
    "*.png", "*.jpg", "*.jpeg", "*.gif", "*.svg",
    "*.json", "*.yaml", "*.yml",
]

# Directories to scan for scattered materials (relative to project root)
SCAN_DIRS = [
    ".", "reference", "references", "ref", "docs", "doc",
    "initialization", "init", "specs", "design", "notes",
    "materials", "input", "inputs", "briefs",
]

# Directories to skip
SKIP_DIRS = {
    ".git", ".state", ".outputs", ".logs", "node_modules",
    "__pycache__", "dist", "build", ".venv", "venv",
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 006: Reference Materials.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, skip interactive prompts

    Returns:
        True if task completed successfully, False otherwise
    """
    project_root = atomic_root.parent
    reference_dir = project_root / "docs" / "reference"
    config_file = output_dir / "project-config.json"

    print()
    print(print_cyan("Reference Materials"))
    print()

    # Step 1: Scan project root for existing materials
    found_files = _scan_for_materials(project_root, atomic_root)

    if found_files:
        # Step 2: Show what was found
        print(print_green(f"  Found {len(found_files)} file(s) in your project:"))
        print()
        for f, rel in found_files:
            print(print_dim(f"    {rel}"))
        print()

        # Step 3: Offer to organize into docs/reference/
        organized = _offer_organization(found_files, reference_dir, project_root)
    else:
        print(print_dim("  No existing materials found in project root."))
        print()
        organized = False

    # Step 4: Show what additional materials would help
    _show_suggestions(reference_dir, found_files, organized)

    # Step 5: Ensure reference dir exists for later phases
    if not reference_dir.exists():
        print()
        clear_input_buffer()
        choice = prompt_user("  Create ./docs/reference/ for later? [Y/n]: ").strip().lower()
        if choice in ('', 'y', 'yes'):
            _create_reference_folder(reference_dir)
        else:
            print(print_dim("  Skipped — you can create it anytime."))

    # Step 6: Record to config
    _record_reference_info(config_file, reference_dir, found_files)

    print()
    print(print_dim("  Tip: Add materials to ./docs/reference/ at any time."))
    print(print_dim("       They'll be used during Discovery and PRD phases."))
    print()

    return True


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------

def _scan_for_materials(
    project_root: Path, atomic_root: Path
) -> List[Tuple[Path, str]]:
    """
    Scan project root for existing materials (docs, images, etc).
    Skips the atomic-claude directory itself.

    Returns list of (absolute_path, relative_display_path) tuples.
    """
    found: List[Tuple[Path, str]] = []
    atomic_name = atomic_root.name

    for scan_dir_name in SCAN_DIRS:
        scan_dir = project_root / scan_dir_name if scan_dir_name != "." else project_root
        if not scan_dir.is_dir():
            continue

        for pattern in SCAN_PATTERNS:
            for f in sorted(scan_dir.glob(pattern)):
                if not f.is_file():
                    continue
                # Skip atomic-claude directory
                try:
                    rel = f.relative_to(project_root)
                    parts = rel.parts
                    if parts and parts[0] == atomic_name:
                        continue
                    if any(p in SKIP_DIRS for p in parts):
                        continue
                except ValueError:
                    continue

                rel_str = str(rel)
                # Deduplicate
                if not any(r == rel_str for _, r in found):
                    found.append((f, rel_str))

    return found


# ---------------------------------------------------------------------------
# Organization offer
# ---------------------------------------------------------------------------

def _offer_organization(
    found_files: List[Tuple[Path, str]],
    reference_dir: Path,
    project_root: Path,
) -> bool:
    """
    Ask the user if they'd like to organize found materials into docs/reference/.
    Returns True if files were organized.
    """
    print(print_bold("  Would you like to organize these into ./docs/reference/?"))
    print(print_dim("  The LLM will use this folder during Discovery and PRD phases."))
    print()
    print(f"    {print_cyan('1.')} Move files to ./docs/reference/")
    print(f"    {print_cyan('2.')} Copy files to ./docs/reference/ (originals stay in place)")
    print(f"    {print_cyan('3.')} Skip — leave files where they are")
    print()

    clear_input_buffer()
    choice = prompt_user("  Choice [1]: ").strip() or "1"

    if choice in ("1", "2"):
        move = (choice == "1")
        ensure_dir(reference_dir)
        organized = 0

        for abs_path, rel_path in found_files:
            dest = reference_dir / Path(rel_path).name
            # Avoid overwriting
            if dest.exists():
                base = dest.stem
                suffix = dest.suffix
                n = 1
                while dest.exists():
                    dest = reference_dir / f"{base}_{n}{suffix}"
                    n += 1

            try:
                if move:
                    shutil.move(str(abs_path), str(dest))
                else:
                    shutil.copy2(str(abs_path), str(dest))
                organized += 1
            except Exception as e:
                print(print_yellow(f"    Warning: Could not {'move' if move else 'copy'} {rel_path}: {e}"))

        action = "Moved" if move else "Copied"
        print()
        print(print_green(f"  {action} {organized} file(s) to ./docs/reference/"))
        print()
        _show_reference_contents(reference_dir)
        return True

    print(print_dim("  Skipped — files left in place."))
    return False


# ---------------------------------------------------------------------------
# Suggestions
# ---------------------------------------------------------------------------

def _show_suggestions(
    reference_dir: Path,
    found_files: List[Tuple[Path, str]],
    organized: bool,
) -> None:
    """Show what additional materials would be helpful."""
    # Categorize what we have
    found_names = [name.lower() for _, name in found_files]
    has_visuals = any(n.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')) for n in found_names)
    has_specs = any(kw in ' '.join(found_names) for kw in ['prd', 'spec', 'requirement', 'icd'])
    has_vision = any(kw in ' '.join(found_names) for kw in ['vision', 'roadmap', 'brief'])
    has_discovery = any(kw in ' '.join(found_names) for kw in ['chat', 'transcript', 'brainstorm', 'notes'])

    # Build suggestions for what's missing
    suggestions = []
    if not has_visuals:
        suggestions.append(("Visual References", "Screenshots, wireframes, mockups, UI inspiration"))
    suggestions.append(("Analogous Systems", "Links or docs describing similar products to emulate"))
    if not has_discovery:
        suggestions.append(("Prior Discovery Work", "Chat transcripts, brainstorming notes, LLM conversations"))
    if not has_specs:
        suggestions.append(("Requirements & Specs", "PRDs, ICDs, API specs, technical requirements"))
    if not has_vision:
        suggestions.append(("Vision Documents", "Product vision, roadmaps, strategic goals"))

    if suggestions:
        print()
        print(print_cyan("  ADDITIONAL MATERIALS THAT WOULD HELP:"))
        print()
        for title, desc in suggestions:
            print(f"    {print_bold(title)}")
            print(f"    {print_dim(desc)}")
            print()


# ---------------------------------------------------------------------------
# Reference folder helpers
# ---------------------------------------------------------------------------

def _create_reference_folder(reference_dir: Path) -> None:
    """Create reference folder with suggested structure."""
    ensure_dir(reference_dir)

    readme_content = """# Reference Materials

Place materials here to enrich Discovery and PRD phases.

## What Goes Here

- **Screenshots, wireframes, mockups** — visual references for UI/UX
- **Requirements docs** — PRDs, ICDs, API specs
- **Vision documents** — product vision, roadmaps
- **Similar systems** — docs or links to analogous products
- **Prior work** — chat transcripts, brainstorming notes

## Tips

- Images (PNG, JPG) will be analyzed visually
- Text files (MD, TXT) will be read directly
- PDFs will be processed for content
- Keep file names descriptive
"""
    write_file(reference_dir / "README.md", readme_content)
    print(print_green("  Created ./docs/reference/"))


def _show_reference_contents(reference_dir: Path) -> None:
    """Show contents of reference directory."""
    files = sorted(reference_dir.rglob('*.*'))
    # Exclude README
    files = [f for f in files if f.name != "README.md"]

    if not files:
        return

    print(print_dim("  Contents of ./docs/reference/:"))
    for f in files[:10]:
        fname = f.relative_to(reference_dir)
        print(print_dim(f"    {fname}"))
    if len(files) > 10:
        print(print_dim(f"    ... and {len(files) - 10} more"))
    print()


# ---------------------------------------------------------------------------
# Config recording
# ---------------------------------------------------------------------------

def _record_reference_info(
    config_file: Path,
    reference_dir: Path,
    found_files: List[Tuple[Path, str]],
) -> None:
    """Record reference material info into project config."""
    if not config_file.exists():
        return

    try:
        config = json.loads(read_file(config_file))
    except (json.JSONDecodeError, FileNotFoundError):
        return

    ref_files = []
    if reference_dir.exists():
        ref_files = [
            str(f.relative_to(reference_dir))
            for f in sorted(reference_dir.rglob('*.*'))
            if f.name != "README.md"
        ]

    config['reference_materials'] = {
        "path": str(reference_dir),
        "file_count": len(ref_files),
        "files": ref_files[:20],
        "scanned_project_files": len(found_files),
    }

    write_file(config_file, json.dumps(config, indent=2))


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 006: Reference Materials")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir)
    sys.exit(0 if success else 1)
