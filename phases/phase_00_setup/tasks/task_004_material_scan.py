"""
Task 004: Material Scan & Reference Organization

Scans the project for existing files, collects external reference material,
suggests what's missing, and offers to organize everything into docs/reference/.

Features:
- Comprehensive file type detection
- Key file identification (README, package.json, etc.)
- Project type/framework inference
- External reference path collection
- Material suggestions based on what's missing
- Organization into docs/reference/
"""

import os
import sys
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import subprocess

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.config import Config
from core.state import StateManager
from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user, clear_input_buffer
)
from core.utils.file_ops import ensure_dir, read_file, write_file


# ---------------------------------------------------------------------------
# Constants for reference material scanning
# ---------------------------------------------------------------------------

# Patterns for finding reference materials (docs, images, data files)
REFERENCE_PATTERNS = [
    "*.md", "*.txt", "*.pdf", "*.doc", "*.docx",
    "*.png", "*.jpg", "*.jpeg", "*.gif", "*.svg",
    "*.json", "*.yaml", "*.yml",
    "*.dot", "*.gv", "*.puml", "*.plantuml", "*.mmd",
    "*.drawio", "*.excalidraw",
    "*.csv", "*.tsv", "*.xml", "*.html", "*.htm",
]

# Directories to scan for scattered materials (relative to project root)
REFERENCE_DIRS = [
    ".", "reference", "references", "ref", "docs", "doc",
    "initialization", "init", "specs", "design", "notes",
    "materials", "input", "inputs", "briefs",
]

# Subdirectory name for pipeline-collected material inside docs/reference/
# Keeps user-placed originals separate from pipeline copies.
# Wiped on backtrack so re-runs never create duplicates.
COLLECTED_SUBDIR = "collected"

# Directories to skip during reference scanning
SKIP_DIRS = {
    ".git", ".state", ".outputs", ".logs", "node_modules",
    "__pycache__", "dist", "build", ".venv", "venv",
    COLLECTED_SUBDIR,  # Skip pipeline-collected copies to avoid re-collecting
}


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None) -> bool:
    """
    Execute Task 004: Material Scan & Reference Organization.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, skip interactive prompts
        mem: Optional TaskMemory instance for recording substantive memory

    Returns:
        True if task completed successfully, False otherwise
    """
    config_file = output_dir / "project-config.json"
    manifest_file = output_dir / "material-manifest.json"
    project_root = atomic_root.parent
    reference_dir = project_root / "docs" / "reference"

    print()
    print(print_cyan("Material Scan"))
    print()

    print(print_dim("  Scanning project for existing materials..."))
    print()

    # Initialize manifest
    manifest = {
        "scanned_at": datetime.now().isoformat(),
        "summary": {},
        "key_files": [],
        "project_indicators": [],
        "files": {}
    }

    # Exclude the atomic-claude tool directory from scans — we want project files only
    exclude_dirs = [str(atomic_root)]

    # ── Part 1: Project overview scan ──────────────────────────────────────

    _detect_key_files(manifest, project_root)
    _detect_stack(manifest, project_root)
    _scan_documentation(manifest, project_root, exclude_dirs)
    _scan_configuration(manifest, project_root, exclude_dirs)
    _scan_source_code(manifest, project_root, exclude_dirs)
    _scan_tests(manifest, project_root, exclude_dirs)
    _calculate_totals(manifest)
    _display_summary(manifest)
    _prompt_exclusions(manifest, project_root, uat_mode)

    # ── Part 2: Collect reference materials ────────────────────────────────

    # Scan project for reference-worthy files (docs, images, configs)
    found_files = _scan_for_reference_materials(project_root, atomic_root)

    # Ask for external reference material
    if not uat_mode:
        external_files = _prompt_additional_paths(manifest, project_root, config_file)
        found_files.extend(external_files)

    # ── Part 3: Suggestions ────────────────────────────────────────────────

    _show_suggestions(found_files)

    # ── Part 4: Show found files and organize ──────────────────────────────

    if found_files:
        print(print_green(f"  Found {len(found_files)} reference file(s):"))
        print()
        for _, rel in found_files:
            print(print_dim(f"    {rel}"))
        print()

        if not uat_mode:
            _offer_organization(found_files, reference_dir, project_root)
    else:
        print(print_dim("  No reference materials found."))
        print()

    # Ensure reference dir exists for later phases
    if not reference_dir.exists() and not uat_mode:
        print()
        clear_input_buffer()
        choice = prompt_user("  Create ./docs/reference/ for later? [Y/n]: ").strip().lower()
        if choice in ('', 'y', 'yes'):
            _create_reference_folder(reference_dir)
        else:
            print(print_dim("  Skipped — you can create it anytime."))

    # ── Part 5: Record everything ──────────────────────────────────────────

    write_file(manifest_file, json.dumps(manifest, indent=2))
    _record_context(manifest_file, manifest)
    _record_reference_info(config_file, reference_dir, found_files)

    # Record substantive memory
    if mem:
        summary = manifest.get("summary", {})
        total = summary.get("total", {})
        total_files = total.get("files", 0)
        total_lines = total.get("lines", 0)
        mem.finding(f"Scanned: {total_files} files, {total_lines} lines")
        stack = manifest.get("detected_stack", {})
        langs = stack.get("languages", [])
        frameworks = stack.get("frameworks", [])
        if langs or frameworks:
            parts = []
            if langs:
                parts.append(', '.join(langs))
            if frameworks:
                parts.append(', '.join(frameworks))
            mem.finding(f"Stack: {' + '.join(parts)}")
        docs = summary.get("documentation", {})
        src = summary.get("source_code", {})
        mem.finding(f"Documentation: {docs.get('count', 0)} files | "
                    f"Source: {src.get('count', 0)} files")
        if found_files:
            mem.finding(f"Reference materials: {len(found_files)} files found")
        ext_refs = manifest.get("files", {}).get("external_references", [])
        if ext_refs:
            mem.finding(f"External references: {len(ext_refs)}")

    print()
    print(print_dim("  Tip: Add materials to ./docs/reference/ at any time."))
    print(print_dim("       They'll be used during Discovery and PRD phases."))
    print()
    print(print_green("✓ Material scan complete"))
    return True


# ===========================================================================
# Part 1: Project overview scan functions
# ===========================================================================

def _detect_key_files(manifest: Dict[str, Any], project_root: Path) -> None:
    """Detect key project files."""
    print(print_cyan("  Key Files"))

    key_files = []

    # Documentation
    for fname in ["README.md", "README", "CHANGELOG.md", "LICENSE", "CONTRIBUTING.md"]:
        if (project_root / fname).exists():
            key_files.append(fname)
            print(print_green(f"    ✓ {fname}"))

    # Node.js / JavaScript
    for fname in ["package.json", "tsconfig.json", "vite.config.ts", "next.config.js"]:
        if (project_root / fname).exists():
            key_files.append(fname)
            print(print_green(f"    ✓ {fname}"))

    # Python
    for fname in ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile"]:
        if (project_root / fname).exists():
            key_files.append(fname)
            print(print_green(f"    ✓ {fname}"))

    # Rust
    if (project_root / "Cargo.toml").exists():
        key_files.append("Cargo.toml")
        print(print_green("    ✓ Cargo.toml"))

    # Go
    if (project_root / "go.mod").exists():
        key_files.append("go.mod")
        print(print_green("    ✓ go.mod"))

    # Ruby
    if (project_root / "Gemfile").exists():
        key_files.append("Gemfile")
        print(print_green("    ✓ Gemfile"))

    # Java / Kotlin
    for fname in ["pom.xml", "build.gradle"]:
        if (project_root / fname).exists():
            key_files.append(fname)
            print(print_green(f"    ✓ {fname}"))

    # Docker
    for fname in ["Dockerfile", "docker-compose.yml"]:
        if (project_root / fname).exists():
            key_files.append(fname)
            print(print_green(f"    ✓ {fname}"))

    # CI/CD
    if (project_root / ".github" / "workflows").exists():
        key_files.append(".github/workflows")
        print(print_green("    ✓ .github/workflows"))
    if (project_root / ".gitlab-ci.yml").exists():
        key_files.append(".gitlab-ci.yml")
        print(print_green("    ✓ .gitlab-ci.yml"))

    # Makefile
    if (project_root / "Makefile").exists():
        key_files.append("Makefile")
        print(print_green("    ✓ Makefile"))

    if not key_files:
        print(print_dim("    Greenfield project detected - no standard project files found."))

    manifest['key_files'] = key_files
    print()


def _detect_stack(manifest: Dict[str, Any], project_root: Path) -> None:
    """Detect language/frameworks from key files."""
    languages = []
    frameworks = []

    # Node.js / TypeScript
    package_json = project_root / "package.json"
    if package_json.exists():
        if (project_root / "tsconfig.json").exists():
            languages.append("TypeScript")
        else:
            languages.append("JavaScript")

        # Check for frameworks
        content = read_file(package_json)
        if '"next"' in content:
            frameworks.append("Next.js")
        if '"react"' in content:
            frameworks.append("React")
        if '"vue"' in content:
            frameworks.append("Vue")
        if '"svelte"' in content:
            frameworks.append("Svelte")
        if '"express"' in content:
            frameworks.append("Express")
        if '"fastify"' in content:
            frameworks.append("Fastify")

    # Python
    if (project_root / "pyproject.toml").exists() or \
       (project_root / "setup.py").exists() or \
       (project_root / "requirements.txt").exists():
        languages.append("Python")
        if (project_root / "manage.py").exists():
            frameworks.append("Django")
        # Check for Flask/FastAPI in requirements
        for fname in ["requirements.txt", "pyproject.toml"]:
            fpath = project_root / fname
            if fpath.exists():
                content = read_file(fpath).lower()
                if "flask" in content:
                    frameworks.append("Flask")
                if "fastapi" in content:
                    frameworks.append("FastAPI")

    # Rust
    if (project_root / "Cargo.toml").exists():
        languages.append("Rust")

    # Go
    if (project_root / "go.mod").exists():
        languages.append("Go")

    # Ruby
    if (project_root / "Gemfile").exists():
        languages.append("Ruby")
        gemfile = read_file(project_root / "Gemfile")
        if "rails" in gemfile.lower():
            frameworks.append("Rails")

    # Java/Kotlin
    if (project_root / "pom.xml").exists():
        languages.append("Java")
    if (project_root / "build.gradle").exists():
        languages.append("Java/Kotlin")

    # Update manifest
    manifest['detected_stack'] = {
        "languages": languages,
        "frameworks": frameworks
    }

    # Display if anything detected
    if languages or frameworks:
        print(print_cyan("  Detected Stack"))
        if languages:
            print(print_dim(f"    Languages:  {', '.join(languages)}"))
        if frameworks:
            print(print_dim(f"    Frameworks: {', '.join(frameworks)}"))
        print()


def _scan_documentation(manifest: Dict[str, Any], project_root: Path, exclude_dirs: Optional[List[str]] = None) -> None:
    """Scan documentation files."""
    docs = _find_files(project_root, [
        "**/*.md", "**/*.rst", "**/*.txt", "**/*.adoc", "**/*.org"
    ], max_depth=4, max_files=50, exclude_dirs=exclude_dirs)

    count = len(docs)
    loc = _count_lines(docs[:20]) if docs else 0

    print(print_cyan(f"  Documentation ({count} files)"))
    if count > 0:
        _display_file_tree(docs, project_root)
    print()

    manifest['summary']['documentation'] = {"count": count, "lines": loc}
    manifest['files']['documentation'] = [str(f.relative_to(project_root)) for f in docs]


def _scan_configuration(manifest: Dict[str, Any], project_root: Path, exclude_dirs: Optional[List[str]] = None) -> None:
    """Scan configuration files."""
    configs = _find_files(project_root, [
        "**/*.json", "**/*.yaml", "**/*.yml", "**/*.toml",
        "**/*.ini", "**/*.env*", "**/.*rc", "**/*.config.js", "**/*.config.ts"
    ], max_depth=3, max_files=30, exclude_dirs=exclude_dirs)

    # Filter out lock files
    configs = [f for f in configs if not any(
        lock in f.name.lower() for lock in ["package-lock", "yarn.lock", "pnpm-lock"]
    )]

    count = len(configs)

    print(print_cyan(f"  Configuration ({count} files)"))
    if count > 0:
        _display_file_tree(configs, project_root)
    print()

    manifest['summary']['configuration'] = {"count": count}
    manifest['files']['configuration'] = [str(f.relative_to(project_root)) for f in configs]


def _scan_source_code(manifest: Dict[str, Any], project_root: Path, exclude_dirs: Optional[List[str]] = None) -> None:
    """Scan source code files."""
    code = _find_files(project_root, [
        "**/*.py", "**/*.js", "**/*.ts", "**/*.jsx", "**/*.tsx", "**/*.vue",
        "**/*.go", "**/*.rs", "**/*.rb", "**/*.java", "**/*.kt", "**/*.scala",
        "**/*.c", "**/*.cpp", "**/*.h", "**/*.php", "**/*.swift", "**/*.sh",
        "**/*.sql", "**/*.graphql"
    ], max_depth=5, max_files=100, exclude_dirs=exclude_dirs)

    # Filter out minified files and build artifacts
    code = [f for f in code if not any(
        pattern in str(f) for pattern in [".min.", "node_modules", "dist", "build", "__pycache__"]
    )]

    count = len(code)
    loc = _count_lines(code[:50]) if code else 0

    print(print_cyan(f"  Source Code ({count} files, ~{loc} lines)"))
    if count > 0:
        _display_file_tree(code, project_root)

    # Warn if file count is high
    if count > 100:
        print()
        print(print_yellow(f"    Note: Large codebase detected ({count} files)."))
        print(print_dim("    Consider connecting to external codebases during development"))
        print(print_dim("    rather than embedding all reference material upfront."))
    print()

    manifest['summary']['source_code'] = {"count": count, "lines": loc}
    manifest['files']['source_code'] = [str(f.relative_to(project_root)) for f in code[:50]]


def _scan_tests(manifest: Dict[str, Any], project_root: Path, exclude_dirs: Optional[List[str]] = None) -> None:
    """Scan test files."""
    tests = _find_files(project_root, [
        "**/*_test.py", "**/test_*.py", "**/*.test.js", "**/*.spec.js",
        "**/*.test.ts", "**/*.spec.ts", "**/*_test.go", "**/*_test.rs"
    ], max_depth=5, max_files=30, exclude_dirs=exclude_dirs)

    count = len(tests)

    print(print_cyan(f"  Tests ({count} files)"))
    if count > 0:
        _display_file_tree(tests, project_root)
    else:
        # Check for test directories
        test_dirs = []
        for test_dir in ["test", "tests", "__tests__", "spec"]:
            if (project_root / test_dir).is_dir():
                test_dirs.append(test_dir)
        if test_dirs:
            print(print_dim(f"    Test directories found: {', '.join(test_dirs)}"))
    print()

    manifest['summary']['tests'] = {"count": count}
    manifest['files']['tests'] = [str(f.relative_to(project_root)) for f in tests]


def _calculate_totals(manifest: Dict[str, Any]) -> None:
    """Calculate total files and lines."""
    summary = manifest.get('summary', {})
    total_files = sum(
        summary.get(cat, {}).get('count', 0)
        for cat in ['documentation', 'configuration', 'source_code', 'tests']
    )
    total_loc = sum(
        summary.get(cat, {}).get('lines', 0)
        for cat in ['documentation', 'source_code']
    )

    manifest['summary']['total'] = {
        "files": total_files,
        "lines": total_loc
    }


def _display_summary(manifest: Dict[str, Any]) -> None:
    """Display summary of scan."""
    summary = manifest.get('summary', {})
    total = summary.get('total', {})
    total_files = total.get('files', 0)
    total_loc = total.get('lines', 0)
    key_count = len(manifest.get('key_files', []))

    print(print_dim("  ────────────────────────────────────"))
    print(print_bold(f"  Total: {total_files} files, ~{total_loc} lines"))
    print(print_bold(f"  Key files: {key_count} identified"))
    print()


def _prompt_exclusions(manifest: Dict[str, Any], project_root: Path, uat_mode: bool = False) -> None:
    """
    Prompt the user to exclude directories or files from the material scan.

    Supports commands:
        dir:<path>   — exclude all files under a directory prefix
        file:<path>  — exclude a single file by relative path
        cat:<name>   — exclude an entire category (documentation, configuration, source_code, tests)
        done         — finish excluding
        (Enter)      — skip exclusions entirely

    Stores exclusions in manifest['exclusions'] and preserves originals
    in manifest['files']['all_scanned'].

    Args:
        manifest: The material manifest dict (modified in-place)
        project_root: Project root for display
        uat_mode: If True, skip entirely
    """
    if uat_mode:
        return

    print(print_dim("  Exclude files from context? [Enter to skip]"))
    print(print_dim("  Commands: dir:<path>  file:<path>  cat:<name>  done"))
    print()

    clear_input_buffer()
    first_input = prompt_user("  > ").strip()

    if not first_input:
        # User pressed Enter — no exclusions
        return

    # Preserve originals before any exclusions
    manifest['files']['all_scanned'] = {
        cat: list(files) for cat, files in manifest['files'].items()
        if cat != 'all_scanned' and cat != 'external_references'
    }

    categories = ['documentation', 'configuration', 'source_code', 'tests']
    excluded_files: List[str] = []
    excluded_dirs: List[str] = []
    excluded_cats: List[str] = []

    def _apply_command(cmd: str) -> None:
        """Process a single exclusion command."""
        cmd = cmd.strip()
        if not cmd or cmd == 'done':
            return

        if cmd.startswith('dir:'):
            dir_prefix = cmd[4:].strip().rstrip('/')
            if not dir_prefix:
                print(print_yellow("    Missing directory path"))
                return
            count = 0
            for cat in categories:
                files = manifest['files'].get(cat, [])
                before = len(files)
                manifest['files'][cat] = [
                    f for f in files if not f.startswith(dir_prefix + '/') and f != dir_prefix
                ]
                count += before - len(manifest['files'][cat])
            excluded_dirs.append(dir_prefix)
            if count:
                print(print_dim(f"    Excluded {count} file(s) from {dir_prefix}/"))
            else:
                print(print_yellow(f"    No files matched {dir_prefix}/"))

        elif cmd.startswith('file:'):
            file_path = cmd[5:].strip()
            if not file_path:
                print(print_yellow("    Missing file path"))
                return
            found = False
            for cat in categories:
                files = manifest['files'].get(cat, [])
                if file_path in files:
                    manifest['files'][cat] = [f for f in files if f != file_path]
                    found = True
            excluded_files.append(file_path)
            if found:
                print(print_dim(f"    Excluded {file_path}"))
            else:
                print(print_yellow(f"    Not found: {file_path}"))

        elif cmd.startswith('cat:'):
            cat_name = cmd[4:].strip()
            if cat_name not in categories:
                print(print_yellow(f"    Unknown category: {cat_name}"))
                print(print_dim(f"    Valid: {', '.join(categories)}"))
                return
            count = len(manifest['files'].get(cat_name, []))
            manifest['files'][cat_name] = []
            excluded_cats.append(cat_name)
            print(print_dim(f"    Excluded {count} file(s) from {cat_name}"))

        else:
            print(print_yellow(f"    Unknown command: {cmd}"))
            print(print_dim("    Use dir:<path>, file:<path>, cat:<name>, or done"))

    # Process first input
    _apply_command(first_input)

    # Continue reading commands until 'done' or empty
    if first_input != 'done':
        while True:
            clear_input_buffer()
            cmd = prompt_user("  > ").strip()
            if not cmd or cmd == 'done':
                break
            _apply_command(cmd)

    # Recalculate totals
    _calculate_totals(manifest)

    # Store exclusion metadata
    manifest['exclusions'] = {
        'dirs': excluded_dirs,
        'files': excluded_files,
        'categories': excluded_cats,
    }

    # Show after-exclusion summary
    total_original = sum(
        len(manifest['files']['all_scanned'].get(cat, []))
        for cat in categories
    )
    total_remaining = sum(
        len(manifest['files'].get(cat, []))
        for cat in categories
    )
    total_excluded = total_original - total_remaining

    if total_excluded > 0:
        print()
        summary = manifest.get('summary', {}).get('total', {})
        print(print_bold(
            f"  After exclusions: {total_remaining} files "
            f"(excluded {total_excluded})"
        ))
        print()


# ===========================================================================
# Part 2: Reference material collection
# ===========================================================================

def _scan_for_reference_materials(
    project_root: Path, atomic_root: Path
) -> List[Tuple[Path, str]]:
    """
    Scan project root for existing reference materials (docs, images, etc).
    Skips the atomic-claude directory itself.

    Returns list of (absolute_path, relative_display_path) tuples.
    """
    found: List[Tuple[Path, str]] = []
    atomic_name = atomic_root.name

    for scan_dir_name in REFERENCE_DIRS:
        scan_dir = project_root / scan_dir_name if scan_dir_name != "." else project_root
        if not scan_dir.is_dir():
            continue

        for pattern in REFERENCE_PATTERNS:
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


def _prompt_additional_paths(
    manifest: Dict[str, Any], project_root: Path, config_file: Path
) -> List[Tuple[Path, str]]:
    """
    Ask the user if they have additional reference material outside the project tree.
    Valid directories are scanned recursively; valid files are added directly.

    Returns list of (absolute_path, display_str) tuples for found files.
    Also updates manifest and project-config.json with the paths.
    """
    print(print_bold("  Do you have additional reference material to include?"))
    print(print_dim("  (directories or files outside this project)"))
    print()

    clear_input_buffer()
    choice = prompt_user("  Add external paths? [n]: ").strip().lower()
    if choice not in ('y', 'yes'):
        print()
        return []

    print(print_dim("  One path per line, blank line to finish:"))

    additional_paths: List[str] = []
    found_files: List[Tuple[Path, str]] = []

    while True:
        clear_input_buffer()
        raw = prompt_user("    > ").strip()
        if not raw:
            break

        p = Path(raw).expanduser().resolve()
        if not p.exists():
            print(print_yellow(f"    Warning: path does not exist: {p}"))
            additional_paths.append(str(p))
            continue

        additional_paths.append(str(p))

        if p.is_dir():
            # Scan recursively with reference patterns
            dir_files = _collect_dir_files(p)
            found_files.extend(dir_files)
            print(print_green(f"    ✓ Scanned directory: {len(dir_files)} file(s) found"))
        else:
            found_files.append((p, f"[ext] {p.name}"))
            print(print_green(f"    ✓ Added file: {p.name}"))

    if additional_paths:
        print()

    # Store in manifest
    manifest['additional_reference_paths'] = additional_paths
    if found_files:
        manifest['files'].setdefault('external_references', [])
        manifest['files']['external_references'].extend(
            [str(f) for f, _ in found_files]
        )

    # Write to project-config.json
    if config_file.exists():
        try:
            config = json.loads(read_file(config_file))
        except (json.JSONDecodeError, FileNotFoundError):
            config = {}
    else:
        config = {}

    if additional_paths:
        config['additional_reference_paths'] = additional_paths
        write_file(config_file, json.dumps(config, indent=2))

    return found_files


def _collect_dir_files(directory: Path) -> List[Tuple[Path, str]]:
    """
    Recursively collect reference files from a directory.
    Returns list of (absolute_path, display_str) tuples.
    """
    found: List[Tuple[Path, str]] = []
    for pattern in REFERENCE_PATTERNS:
        for f in sorted(directory.rglob(pattern)):
            if not f.is_file():
                continue
            if any(skip in f.parts for skip in SKIP_DIRS):
                continue
            display = f"[ext] {directory.name}/{f.relative_to(directory)}"
            if not any(r == display for _, r in found):
                found.append((f, display))
    return found


# ===========================================================================
# Part 3: Suggestions
# ===========================================================================

def _show_suggestions(found_files: List[Tuple[Path, str]]) -> None:
    """Show what additional materials would be helpful."""
    found_names = [name.lower() for _, name in found_files]
    has_visuals = any(n.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')) for n in found_names)
    has_specs = any(kw in ' '.join(found_names) for kw in ['prd', 'spec', 'requirement', 'icd'])
    has_vision = any(kw in ' '.join(found_names) for kw in ['vision', 'roadmap', 'brief'])
    has_discovery = any(kw in ' '.join(found_names) for kw in ['chat', 'transcript', 'brainstorm', 'notes'])

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
        print(print_cyan("  ADDITIONAL MATERIALS THAT WOULD HELP:"))
        print()
        for title, desc in suggestions:
            print(f"    {print_bold(title)}")
            print(f"    {print_dim(desc)}")
            print()


# ===========================================================================
# Part 4: Organization
# ===========================================================================

def _offer_organization(
    found_files: List[Tuple[Path, str]],
    reference_dir: Path,
    project_root: Path,
) -> bool:
    """
    Ask the user if they'd like to organize found materials into docs/reference/collected/.

    Pipeline-collected files go into a 'collected/' subdirectory so that:
    - User-placed originals in docs/reference/ are never duplicated
    - Re-runs after backtrack start clean (collected/ is wiped first)

    Returns True if files were organized.
    """
    collected_dir = reference_dir / COLLECTED_SUBDIR

    print(print_bold("  Would you like to organize these into ./docs/reference/collected/?"))
    print(print_dim("  The LLM will use this folder during Discovery and PRD phases."))
    print()
    print(f"    {print_cyan('1.')} Copy files to ./docs/reference/collected/ (originals stay in place)")
    print(f"    {print_cyan('2.')} Move files to ./docs/reference/collected/")
    print(f"    {print_cyan('3.')} Nevermind — don't organize")
    print()

    clear_input_buffer()
    choice = prompt_user("  Choice [1]: ").strip() or "1"

    if choice in ("1", "2"):
        move = (choice == "2")

        # Wipe collected/ for idempotent re-runs (no _1 duplicates)
        if collected_dir.exists():
            shutil.rmtree(collected_dir)
        ensure_dir(collected_dir)

        organized = 0
        for abs_path, rel_path in found_files:
            dest = collected_dir / Path(rel_path).name
            # Avoid overwriting within same batch (two files with same name)
            if dest.exists():
                base = dest.stem
                suffix = dest.suffix
                n = 1
                while dest.exists():
                    dest = collected_dir / f"{base}_{n}{suffix}"
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
        print(print_green(f"  {action} {organized} file(s) to ./docs/reference/collected/"))
        print()
        _show_reference_contents(reference_dir)
        return True

    print(print_dim("  OK — no files organized."))
    return False


# ===========================================================================
# Part 5: Recording and helpers
# ===========================================================================

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
    """Show contents of reference directory, distinguishing user-placed from collected."""
    collected_dir = reference_dir / COLLECTED_SUBDIR

    # Show user-placed files (directly in docs/reference/)
    user_files = sorted(f for f in reference_dir.glob('*.*') if f.name != "README.md")
    if user_files:
        print(print_dim("  User-placed files in ./docs/reference/:"))
        for f in user_files[:10]:
            print(print_dim(f"    {f.name}"))
        if len(user_files) > 10:
            print(print_dim(f"    ... and {len(user_files) - 10} more"))
        print()

    # Show collected files
    if collected_dir.exists():
        collected_files = sorted(collected_dir.rglob('*.*'))
        if collected_files:
            print(print_dim("  Pipeline-collected in ./docs/reference/collected/:"))
            for f in collected_files[:10]:
                print(print_dim(f"    {f.relative_to(collected_dir)}"))
            if len(collected_files) > 10:
                print(print_dim(f"    ... and {len(collected_files) - 10} more"))
            print()


def _record_context(manifest_file: Path, manifest: Dict[str, Any]) -> None:
    """Record findings to context."""
    summary = manifest.get('summary', {})
    total = summary.get('total', {})
    total_files = total.get('files', 0)
    key_count = len(manifest.get('key_files', []))
    languages = manifest.get('detected_stack', {}).get('languages', [])
    ext_count = len(manifest.get('files', {}).get('external_references', []))

    context_msg = f"Material scan: {total_files} project files, {key_count} key files"
    if ext_count:
        context_msg += f", {ext_count} external references"
    if languages:
        context_msg += f", stack: {', '.join(languages)}"

    print(print_dim(f"  Context: {context_msg}"))


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
    collected_files = []
    if reference_dir.exists():
        collected_dir = reference_dir / COLLECTED_SUBDIR
        # User-placed files (directly in docs/reference/)
        ref_files = [
            str(f.relative_to(reference_dir))
            for f in sorted(reference_dir.glob('*.*'))
            if f.name != "README.md"
        ]
        # Pipeline-collected files
        if collected_dir.exists():
            collected_files = [
                str(f.relative_to(reference_dir))
                for f in sorted(collected_dir.rglob('*.*'))
            ]

    all_files = ref_files + collected_files
    config['reference_materials'] = {
        "path": str(reference_dir),
        "file_count": len(all_files),
        "files": all_files[:20],
        "scanned_project_files": len(found_files),
        "collected_dir": str(reference_dir / COLLECTED_SUBDIR),
    }

    write_file(config_file, json.dumps(config, indent=2))


def _find_files(
    root: Path,
    patterns: List[str],
    max_depth: int = 3,
    max_files: int = 100,
    exclude_dirs: Optional[List[str]] = None,
) -> List[Path]:
    """
    Find files matching patterns.

    Args:
        root: Root directory to search
        patterns: List of glob patterns
        max_depth: Maximum directory depth
        max_files: Maximum files to return
        exclude_dirs: Absolute directory paths to skip

    Returns:
        List of matching file paths
    """
    files = []
    exclude_patterns = ["node_modules", ".git", ".outputs", "__pycache__", "dist", "build"]
    # Add explicit directory exclusions (e.g. the atomic-claude tool dir)
    if exclude_dirs:
        exclude_patterns.extend(exclude_dirs)

    for pattern in patterns:
        for f in root.glob(pattern):
            # Check if any exclude pattern is in the path
            if any(excl in str(f) for excl in exclude_patterns):
                continue

            # Check depth
            try:
                rel_path = f.relative_to(root)
                depth = len(rel_path.parts)
                if depth > max_depth:
                    continue
            except ValueError:
                continue

            if f.is_file():
                files.append(f)
                if len(files) >= max_files:
                    break

        if len(files) >= max_files:
            break

    return sorted(files)[:max_files]


def _display_file_tree(files: List[Path], project_root: Path, indent: str = "    ") -> None:
    """
    Display files grouped by parent directory as a compact tree.

    Groups files by their immediate parent directory relative to project_root.
    Root-level files appear under './'. Directories with >15 files are collapsed
    to a count summary.

    Args:
        files: List of absolute file paths
        project_root: Project root for computing relative paths
        indent: Indentation prefix for each line
    """
    from collections import defaultdict

    groups: Dict[str, List[str]] = defaultdict(list)

    for f in files:
        try:
            rel = f.relative_to(project_root)
        except ValueError:
            rel = Path(f.name)

        parent = str(rel.parent) if rel.parent != Path(".") else "."
        groups[parent].append(rel.name)

    # Sort: root first, then alphabetical
    sorted_dirs = sorted(groups.keys(), key=lambda d: ("" if d == "." else d))

    for dir_path in sorted_dirs:
        filenames = sorted(groups[dir_path])
        label = "./" if dir_path == "." else f"{dir_path}/"
        if len(filenames) > 15:
            print(print_dim(f"{indent}{label} ({len(filenames)} files)"))
        else:
            print(print_dim(f"{indent}{label}"))
            for name in filenames:
                print(print_dim(f"{indent}  {name}"))


def _count_lines(files: List[Path]) -> int:
    """Count total lines in files."""
    total = 0
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
                total += sum(1 for _ in fp)
        except:
            pass
    return total


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 004: Material Scan")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir)
    sys.exit(0 if success else 1)
