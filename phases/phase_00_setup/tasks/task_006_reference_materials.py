"""
Task 006: Reference Materials

Guide user to gather enriching materials for Discovery and PRD phases.

Features:
- Explains what kinds of materials help the LLM
- Suggests folder structure for reference docs
- Optionally creates reference folder
- Records what materials are available to context
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
    Execute Task 006: Reference Materials.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    config_file = output_dir / "project-config.json"
    reference_dir = atomic_root / "docs" / "reference"

    print()
    print_cyan("Reference Materials")
    print()

    # Show info box
    _show_info_box()

    # Show helpful reference materials
    _show_reference_types()

    # Check if reference folder already exists
    has_reference, reference_count = _check_existing_reference(reference_dir)

    print_dim("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()

    if has_reference:
        print_green(f"  ✓ Found ./docs/reference/ with {reference_count} file(s)")
        print()
        _show_reference_contents(reference_dir, reference_count)
    else:
        print_dim("  No reference folder found.")
        print()

    # UAT mode - skip creation
    if uat_mode:
        print_yellow("UAT Mode: Skipping reference materials")
        return True

    # Prompt for action
    return _prompt_action(reference_dir, config_file)


def _show_info_box() -> None:
    """Show informational box about reference materials."""
    print_dim("  ┌─────────────────────────────────────────────────────────┐")
    print_dim("  │ Better inputs = better outputs.                         │")
    print_dim("  │                                                         │")
    print_dim("  │ Reference materials help the LLM understand your vision │")
    print_dim("  │ during Discovery and PRD phases.                        │")
    print_dim("  └─────────────────────────────────────────────────────────┘")
    print()


def _show_reference_types() -> None:
    """Show types of helpful reference materials."""
    print_cyan("  HELPFUL REFERENCE MATERIALS:")
    print()
    print_bold("    Visual References")
    print_dim("    Screenshots, wireframes, mockups, UI inspiration")
    print()
    print_bold("    Analogous Systems")
    print_dim("    Links or docs describing similar products to emulate")
    print()
    print_bold("    Prior Discovery Work")
    print_dim("    Chat transcripts, brainstorming notes, LLM conversations")
    print()
    print_bold("    Requirements & Specs")
    print_dim("    PRDs, ICDs, API specs, technical requirements")
    print()
    print_bold("    Vision Documents")
    print_dim("    Product vision, roadmaps, strategic goals")
    print()


def _check_existing_reference(reference_dir: Path) -> tuple[bool, int]:
    """
    Check if reference folder exists and count files.

    Args:
        reference_dir: Path to reference directory

    Returns:
        Tuple of (has_reference, file_count)
    """
    if not reference_dir.exists():
        return False, 0

    # Count files recursively
    file_count = len(list(reference_dir.rglob('*.*')))
    return file_count > 0, file_count


def _show_reference_contents(reference_dir: Path, reference_count: int) -> None:
    """
    Show contents of reference directory.

    Args:
        reference_dir: Path to reference directory
        reference_count: Total number of files
    """
    print_dim("  Contents:")
    files = list(reference_dir.rglob('*.*'))[:10]  # Show first 10
    for f in files:
        fname = f.relative_to(reference_dir)
        print_dim(f"    {fname}")

    if reference_count > 10:
        print_dim(f"    ... and {reference_count - 10} more")
    print()


def _prompt_action(reference_dir: Path, config_file: Path) -> bool:
    """
    Prompt user for action on reference materials.

    Args:
        reference_dir: Path to reference directory
        config_file: Path to project config file

    Returns:
        True if successful
    """
    print_bold("  What would you like to do?")
    print()
    print_cyan("  1. Create ./docs/reference/ folder (I'll add materials)")
    print_cyan("  2. Point to existing folder")
    print_cyan("  3. Skip for now (can add later)")
    print()

    clear_input_buffer()
    ref_choice = prompt_user("Choice (default: 3): ").strip() or '3'

    if ref_choice == '1':
        _create_reference_folder(reference_dir)
    elif ref_choice == '2':
        _link_existing_folder(config_file)
    else:
        print_dim("Skipping reference materials")

    print()
    print_dim("  Tip: You can add materials to ./docs/reference/ at any time.")
    print_dim("       They'll be available during Discovery and PRD phases.")
    print()

    return True


def _create_reference_folder(reference_dir: Path) -> None:
    """
    Create reference folder with suggested structure.

    Args:
        reference_dir: Path to reference directory
    """
    # Create subdirectories
    ensure_dir(reference_dir / "visuals")
    ensure_dir(reference_dir / "docs")
    ensure_dir(reference_dir / "examples")

    # Create README
    readme_content = """# Reference Materials

Place materials here to enrich Discovery and PRD phases.

## Suggested Organization

- **visuals/** - Screenshots, wireframes, mockups, UI inspiration
- **docs/** - Requirements, specs, ICDs, vision documents
- **examples/** - Links or descriptions of analogous systems

## Tips

- Images (PNG, JPG) will be analyzed visually
- Text files (MD, TXT) will be read directly
- PDFs will be processed for content
- Keep file names descriptive

## Adding Materials Later

You can add materials at any time before or during Discovery.
"""
    write_file(reference_dir / "README.md", readme_content)

    print_green("✓ Created ./docs/reference/ with suggested structure")
    print()
    print_dim("  Folders created:")
    print_dim("    ./docs/reference/visuals/   - Screenshots, mockups")
    print_dim("    ./docs/reference/docs/      - Requirements, specs")
    print_dim("    ./docs/reference/examples/  - Analogous systems")
    print()


def _link_existing_folder(config_file: Path) -> None:
    """
    Link to an existing folder.

    Args:
        config_file: Path to project config file
    """
    print()
    existing_path = prompt_user("Path to existing folder: ").strip()

    if not existing_path:
        print_yellow("No path provided")
        return

    # Expand ~ if used
    existing_path = os.path.expanduser(existing_path)
    existing_path_obj = Path(existing_path)

    if not existing_path_obj.exists():
        print_red(f"Folder not found: {existing_path}")
        return

    # Count files
    file_count = len(list(existing_path_obj.rglob('*.*')))

    # Store path in config
    config = json.loads(read_file(config_file))
    config['reference_path'] = existing_path
    write_file(config_file, json.dumps(config, indent=2))

    print_green(f"✓ Linked to {existing_path} ({file_count} files)")


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 006: Reference Materials")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
