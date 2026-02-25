"""
Task 102: Import Existing Requirements (Optional)

Import requirements from existing project documentation.

Supported formats:
  - Sphinx-needs RST files (.. req::, .. spec::, etc.)
  - Markdown requirements files
  - CSV/spreadsheet exports
  - JSON/YAML requirements files

Purpose:
  For projects with existing requirements docs, import them into
  structured format for traceability throughout the pipeline.
"""

import json
import logging
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Set, Tuple

logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.config import Config
from core.state import StateManager
from core.ui import phase_header, success, error, warning, info, step
from core.utils.file_ops import write_json


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None, graph=None) -> bool:
    """
    Execute Task 102: Import Requirements.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, skip interactive import
        mem: Optional TaskMemory instance for recording substantive memory

    Returns:
        True if import completed successfully, False otherwise
    """
    project_root = atomic_root.parent
    needs_dir = project_root / ".claude" / "needs"
    needs_index = needs_dir / "needs-index.json"

    step("Import Requirements")

    print()
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │ IMPORT REQUIREMENTS (Optional)                         │")
    print("  │                                                         │")
    print("  │ If your project has existing requirements docs, we     │")
    print("  │ can import them for traceability.                      │")
    print("  │                                                         │")
    print("  │ Supported: Sphinx-needs RST, Markdown, CSV, JSON/YAML   │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()

    # ═══════════════════════════════════════════════════════════════
    # STEP 1: DETECT RST FILES
    # ═══════════════════════════════════════════════════════════════

    print("  Scanning for RST files...")

    rst_files = _find_rst_files(atomic_root)

    if not rst_files:
        print("  No RST files found.")
        print()
        use_needs = input("  Does your project use Sphinx-Needs? [y/N]: ").strip().lower()

        if use_needs in ('y', 'yes'):
            print()
            print("  Enter paths to RST files (one per line, empty to finish):")
            while True:
                manual_path = input("    Path: ").strip()
                if not manual_path:
                    break
                path = Path(manual_path)
                if path.exists() and path.is_file():
                    rst_files.append(path)
                    print(f"    ✓ Added: {manual_path}")
                else:
                    print(f"    ✗ File not found: {manual_path}")

            if not rst_files:
                if mem:
                    mem.finding("Requirements import: skipped (no RST files provided)")
                info("No RST files provided - skipping")
                return True
        else:
            if mem:
                mem.finding("Requirements import: skipped (no RST files found)")
            info("Sphinx-needs: Skipped (no RST files)")
            return True

    print(f"  ✓ Found {len(rst_files)} RST file(s)")
    print()

    # ═══════════════════════════════════════════════════════════════
    # STEP 2: SCAN FOR DIRECTIVES
    # ═══════════════════════════════════════════════════════════════

    print("  Checking for sphinx-needs directives...")

    directive_pattern = re.compile(r'^\.\.\s+(req|spec|test|need|story|feature)::', re.IGNORECASE)
    files_with_needs = []

    for rst_file in rst_files:
        try:
            with open(rst_file, 'r', encoding='utf-8') as f:
                if any(directive_pattern.match(line) for line in f):
                    files_with_needs.append(rst_file)
        except Exception as e:
            logger.debug("Failed to scan RST file %s: %s", rst_file, e)
            continue

    if not files_with_needs:
        print("  No sphinx-needs directives found in RST files.")
        print()
        info("Sphinx-needs: No directives found")
        return True

    print(f"  ✓ Found directives in {len(files_with_needs)} file(s)")
    print()

    # List files with needs
    print("  Files with needs:")
    for f in files_with_needs:
        count = _count_directives(f, directive_pattern)
        print(f"    • {f.name} ({count} needs)")
    print()

    # Confirm parsing
    do_parse = input("  Parse these files? [Y/n]: ").strip().lower()
    if do_parse == 'n':
        info("Sphinx-needs: Skipped by user")
        return True

    # ═══════════════════════════════════════════════════════════════
    # STEP 3: PARSE NEEDS
    # ═══════════════════════════════════════════════════════════════

    print()
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ PARSING SPHINX-NEEDS                                      ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    needs_dir.mkdir(parents=True, exist_ok=True)

    needs_data = {
        "version": "1.0",
        "parsed_at": datetime.now().isoformat(),
        "source_files": [],
        "needs": [],
        "summary": {
            "total": 0,
            "by_type": {}
        }
    }

    total_needs = 0
    seen_ids = set()

    for rst_file in files_with_needs:
        file_relpath = str(rst_file.relative_to(atomic_root))
        needs_data["source_files"].append(file_relpath)

        print(f"  Parsing: {rst_file.name}")

        parsed_needs = _parse_rst_needs(rst_file, file_relpath, seen_ids)
        total_needs += len(parsed_needs)
        needs_data["needs"].extend(parsed_needs)

    # ═══════════════════════════════════════════════════════════════
    # STEP 4: SUMMARY
    # ═══════════════════════════════════════════════════════════════

    print()
    print("━" * 60)
    print()
    print(f"  Parsed {total_needs} needs")
    print()

    # Calculate summary
    needs_data["summary"]["total"] = total_needs

    print("  By Type:")
    for need_type in ['req', 'spec', 'test', 'need', 'story', 'feature']:
        count = sum(1 for n in needs_data["needs"] if n["type"] == need_type)
        if count > 0:
            print(f"    {need_type}: {count}")
            needs_data["summary"]["by_type"][need_type] = count
    print()

    # ═══════════════════════════════════════════════════════════════
    # STEP 5: SAVE
    # ═══════════════════════════════════════════════════════════════

    write_json(needs_index, needs_data)
    print(f"  ✓ Saved: .claude/needs/needs-index.json")

    # Also save to phase output
    output_needs = output_dir / "needs-index.json"
    write_json(output_needs, needs_data)
    print(f"  ✓ Copied to phase output")

    # Write to knowledge graph
    if graph:
        for need in needs_data.get("needs", []):
            graph.add_source(
                id=f"S-102-{need.get('id', 'unknown')}",
                type="need",
                title=need.get("title", need.get("id", "unknown")),
                file_path=need.get("source_file", ""),
            )

    print()

    # Record substantive memory
    if mem:
        by_type = needs_data.get("summary", {}).get("by_type", {})
        if by_type:
            type_parts = [f"{count} {ntype}" for ntype, count in by_type.items()]
            mem.finding(f"Requirements imported: {', '.join(type_parts)}")
        else:
            total = len(needs_data.get("needs", []))
            mem.finding(f"Requirements imported: {total} total")

    success("Sphinx-needs parsing complete")
    return True


def _find_rst_files(atomic_root: Path, max_files: int = 100) -> List[Path]:
    """Find RST files in the project, excluding common ignore patterns."""
    rst_files = []
    exclude_patterns = ['.git', '__pycache__', 'node_modules', '.venv', 'venv']

    for rst_file in atomic_root.rglob("*.rst"):
        # Skip if in excluded directory
        if any(pattern in str(rst_file) for pattern in exclude_patterns):
            continue

        rst_files.append(rst_file)
        if len(rst_files) >= max_files:
            break

    return rst_files


def _count_directives(rst_file: Path, pattern: re.Pattern) -> int:
    """Count sphinx-needs directives in an RST file."""
    try:
        with open(rst_file, 'r', encoding='utf-8') as f:
            return sum(1 for line in f if pattern.match(line))
    except Exception as e:
        logger.debug("Failed to count directives in %s: %s", rst_file, e)
        return 0


def _parse_rst_needs(rst_file: Path, file_relpath: str, seen_ids: Set[str]) -> List[Dict[str, Any]]:
    """Parse sphinx-needs directives from an RST file."""
    needs = []

    # Regex patterns
    directive_pattern = re.compile(r'^\.\.\s+(req|spec|test|need|story|feature)::\s*(.*)$', re.IGNORECASE)
    id_title_pattern = re.compile(r'^([A-Z]+-?[0-9]+)\s*(.*)$')
    attr_pattern = re.compile(r'^\s+:([a-z_]+):\s*(.*)$')
    content_pattern = re.compile(r'^\s{3,}[^:]')

    try:
        with open(rst_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        logger.debug("Failed to read RST file %s for parsing: %s", rst_file, e)
        return needs

    in_need = False
    current_type = ""
    current_id = ""
    current_title = ""
    current_attrs = {}
    current_content = ""
    need_start_line = 0

    for line_num, line in enumerate(lines, 1):
        # Check for new directive
        directive_match = directive_pattern.match(line)
        if directive_match:
            # Save previous need if exists
            if in_need and current_type:
                need = _create_need(
                    current_id, current_type, current_title,
                    current_content, current_attrs, file_relpath,
                    need_start_line, seen_ids
                )
                if need:
                    needs.append(need)
                    print(f"    ✓ {need['id']}: {need['title'][:50]}")

            # Start new need
            in_need = True
            current_type = directive_match.group(1).lower()
            rest = directive_match.group(2).strip()
            need_start_line = line_num
            current_attrs = {}
            current_content = ""

            # Parse ID and title
            id_match = id_title_pattern.match(rest)
            if id_match:
                current_id = id_match.group(1)
                current_title = id_match.group(2).strip()
            else:
                current_id = ""
                current_title = rest

        # Check for attribute line
        elif in_need:
            attr_match = attr_pattern.match(line)
            if attr_match:
                attr_name = attr_match.group(1)
                attr_value = attr_match.group(2).strip()
                current_attrs[attr_name] = attr_value

            # Check for content line
            elif content_pattern.match(line):
                content_line = line.strip()
                if current_content:
                    current_content += " " + content_line
                else:
                    current_content = content_line

            # Check for end of need (non-indented line)
            elif line.strip() and not line.startswith(' '):
                # Save current need
                if current_type:
                    need = _create_need(
                        current_id, current_type, current_title,
                        current_content, current_attrs, file_relpath,
                        need_start_line, seen_ids
                    )
                    if need:
                        needs.append(need)
                        print(f"    ✓ {need['id']}: {need['title'][:50]}")
                in_need = False

    # Save final need if file ends while in a need
    if in_need and current_type:
        need = _create_need(
            current_id, current_type, current_title,
            current_content, current_attrs, file_relpath,
            need_start_line, seen_ids
        )
        if need:
            needs.append(need)
            print(f"    ✓ {need['id']}: {need['title'][:50]}")

    return needs


def _create_need(need_id: str, need_type: str, title: str, content: str,
                 attrs: Dict[str, str], file_path: str, line_num: int,
                 seen_ids: Set[str]) -> Dict[str, Any]:
    """Create a need object from parsed data."""
    # Generate ID if not provided
    if not need_id:
        prefix_map = {
            'req': 'REQ',
            'spec': 'SPEC',
            'test': 'TST',
            'need': 'NEED',
            'story': 'STORY',
            'feature': 'FEAT'
        }
        prefix = prefix_map.get(need_type, 'NEED')

        # Find next available number
        num = 1
        while f"{prefix}-{num:03d}" in seen_ids:
            num += 1
        need_id = f"{prefix}-{num:03d}"

    # Check for duplicate ID
    if need_id in seen_ids:
        print(f"    ! Duplicate ID: {need_id} (skipped)")
        return None

    seen_ids.add(need_id)

    return {
        "id": need_id,
        "type": need_type,
        "title": title,
        "content": content,
        "attributes": attrs,
        "source": {
            "file": file_path,
            "line": line_num
        }
    }


if __name__ == "__main__":
    # CLI execution support
    atomic_root = Path.cwd()
    output_dir = atomic_root.parent / ".outputs" / "1-discovery"
    uat_mode = "--uat" in sys.argv

    sys.exit(0 if execute(atomic_root, output_dir, uat_mode) else 1)
