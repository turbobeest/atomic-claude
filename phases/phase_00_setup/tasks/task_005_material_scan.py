"""
Task 005: Material Scan

Index existing project files (docs, configs, source code).

Features:
- Comprehensive file type detection
- Key file identification (README, package.json, etc.)
- Project type/framework inference
- Sample file display per category
- Size and LOC awareness
- Records findings to context
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
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


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 005: Material Scan.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    config_file = output_dir / "project-config.json"
    manifest_file = output_dir / "material-manifest.json"
    project_root = atomic_root.parent

    print()
    print_cyan("Material Scan")
    print()

    print_dim("  Scanning project for existing materials...")
    print()

    # Initialize manifest
    manifest = {
        "scanned_at": datetime.now().isoformat(),
        "summary": {},
        "key_files": [],
        "project_indicators": [],
        "files": {}
    }

    # Scan for key files first
    _detect_key_files(manifest, project_root)

    # Detect language/frameworks from key files
    _detect_stack(manifest, project_root)

    # Scan different categories
    _scan_documentation(manifest, project_root)
    _scan_configuration(manifest, project_root)
    _scan_source_code(manifest, project_root)
    _scan_tests(manifest, project_root)

    # Calculate totals
    _calculate_totals(manifest)

    # Display summary
    _display_summary(manifest)

    # Save manifest
    write_file(manifest_file, json.dumps(manifest, indent=2))

    # Record to context
    _record_context(manifest_file, manifest)

    print_green("✓ Material manifest created")
    return True


def _detect_key_files(manifest: Dict[str, Any], project_root: Path) -> None:
    """Detect key project files."""
    print_cyan("  Key Files")

    key_files = []

    # Documentation
    for fname in ["README.md", "README", "CHANGELOG.md", "LICENSE", "CONTRIBUTING.md"]:
        if (project_root / fname).exists():
            key_files.append(fname)
            print_green(f"    ✓ {fname}")

    # Node.js / JavaScript
    for fname in ["package.json", "tsconfig.json", "vite.config.ts", "next.config.js"]:
        if (project_root / fname).exists():
            key_files.append(fname)
            print_green(f"    ✓ {fname}")

    # Python
    for fname in ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile"]:
        if (project_root / fname).exists():
            key_files.append(fname)
            print_green(f"    ✓ {fname}")

    # Rust
    if (project_root / "Cargo.toml").exists():
        key_files.append("Cargo.toml")
        print_green("    ✓ Cargo.toml")

    # Go
    if (project_root / "go.mod").exists():
        key_files.append("go.mod")
        print_green("    ✓ go.mod")

    # Ruby
    if (project_root / "Gemfile").exists():
        key_files.append("Gemfile")
        print_green("    ✓ Gemfile")

    # Java / Kotlin
    for fname in ["pom.xml", "build.gradle"]:
        if (project_root / fname).exists():
            key_files.append(fname)
            print_green(f"    ✓ {fname}")

    # Docker
    for fname in ["Dockerfile", "docker-compose.yml"]:
        if (project_root / fname).exists():
            key_files.append(fname)
            print_green(f"    ✓ {fname}")

    # CI/CD
    if (project_root / ".github" / "workflows").exists():
        key_files.append(".github/workflows")
        print_green("    ✓ .github/workflows")
    if (project_root / ".gitlab-ci.yml").exists():
        key_files.append(".gitlab-ci.yml")
        print_green("    ✓ .gitlab-ci.yml")

    # Makefile
    if (project_root / "Makefile").exists():
        key_files.append("Makefile")
        print_green("    ✓ Makefile")

    if not key_files:
        print_dim("    Greenfield project detected - no standard project files found.")

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
        print_cyan("  Detected Stack")
        if languages:
            print_dim(f"    Languages:  {', '.join(languages)}")
        if frameworks:
            print_dim(f"    Frameworks: {', '.join(frameworks)}")
        print()


def _scan_documentation(manifest: Dict[str, Any], project_root: Path) -> None:
    """Scan documentation files."""
    docs = _find_files(project_root, [
        "**/*.md", "**/*.rst", "**/*.txt", "**/*.adoc", "**/*.org"
    ], max_depth=4, max_files=50)

    count = len(docs)
    sample = docs[:5]
    loc = _count_lines(docs[:20]) if docs else 0

    print_cyan("  Documentation")
    print_dim(f"  {count} files")
    if count > 0:
        for f in sample:
            print_dim(f"    {f.relative_to(project_root)}")
        if count > 5:
            print_dim(f"    ... and {count - 5} more")
    print()

    manifest['summary']['documentation'] = {"count": count, "lines": loc}
    manifest['files']['documentation'] = [str(f.relative_to(project_root)) for f in docs]


def _scan_configuration(manifest: Dict[str, Any], project_root: Path) -> None:
    """Scan configuration files."""
    configs = _find_files(project_root, [
        "**/*.json", "**/*.yaml", "**/*.yml", "**/*.toml",
        "**/*.ini", "**/*.env*", "**/.*rc", "**/*.config.js", "**/*.config.ts"
    ], max_depth=3, max_files=30)

    # Filter out lock files
    configs = [f for f in configs if not any(
        lock in f.name.lower() for lock in ["package-lock", "yarn.lock", "pnpm-lock"]
    )]

    count = len(configs)
    sample = configs[:5]

    print_cyan("  Configuration")
    print_dim(f"  {count} files")
    if count > 0:
        for f in sample:
            print_dim(f"    {f.relative_to(project_root)}")
        if count > 5:
            print_dim(f"    ... and {count - 5} more")
    print()

    manifest['summary']['configuration'] = {"count": count}
    manifest['files']['configuration'] = [str(f.relative_to(project_root)) for f in configs]


def _scan_source_code(manifest: Dict[str, Any], project_root: Path) -> None:
    """Scan source code files."""
    code = _find_files(project_root, [
        "**/*.py", "**/*.js", "**/*.ts", "**/*.jsx", "**/*.tsx", "**/*.vue",
        "**/*.go", "**/*.rs", "**/*.rb", "**/*.java", "**/*.kt", "**/*.scala",
        "**/*.c", "**/*.cpp", "**/*.h", "**/*.php", "**/*.swift", "**/*.sh",
        "**/*.sql", "**/*.graphql"
    ], max_depth=5, max_files=100)

    # Filter out minified files and build artifacts
    code = [f for f in code if not any(
        pattern in str(f) for pattern in [".min.", "node_modules", "dist", "build", "__pycache__"]
    )]

    count = len(code)
    sample = code[:5]
    loc = _count_lines(code[:50]) if code else 0

    print_cyan("  Source Code")
    print_dim(f"  {count} files (~{loc} lines)")
    if count > 0:
        for f in sample:
            print_dim(f"    {f.relative_to(project_root)}")
        if count > 5:
            print_dim(f"    ... and {count - 5} more")

    # Warn if file count is high
    if count > 100:
        print()
        print_yellow(f"    Note: Large codebase detected ({count} files).")
        print_dim("    Consider connecting to external codebases during development")
        print_dim("    rather than embedding all reference material upfront.")
    print()

    manifest['summary']['source_code'] = {"count": count, "lines": loc}
    manifest['files']['source_code'] = [str(f.relative_to(project_root)) for f in code[:50]]


def _scan_tests(manifest: Dict[str, Any], project_root: Path) -> None:
    """Scan test files."""
    tests = _find_files(project_root, [
        "**/*_test.py", "**/test_*.py", "**/*.test.js", "**/*.spec.js",
        "**/*.test.ts", "**/*.spec.ts", "**/*_test.go", "**/*_test.rs"
    ], max_depth=5, max_files=30)

    count = len(tests)
    sample = tests[:3]

    print_cyan("  Tests")
    print_dim(f"  {count} files")
    if count > 0:
        for f in sample:
            print_dim(f"    {f.relative_to(project_root)}")
        if count > 3:
            print_dim(f"    ... and {count - 3} more")
    else:
        # Check for test directories
        test_dirs = []
        for test_dir in ["test", "tests", "__tests__", "spec"]:
            if (project_root / test_dir).is_dir():
                test_dirs.append(test_dir)
        if test_dirs:
            print_dim(f"    Test directories found: {', '.join(test_dirs)}")
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

    print_dim("  ────────────────────────────────────")
    print_bold(f"  Total: {total_files} files, ~{total_loc} lines")
    print_bold(f"  Key files: {key_count} identified")
    print()


def _find_files(
    root: Path,
    patterns: List[str],
    max_depth: int = 3,
    max_files: int = 100
) -> List[Path]:
    """
    Find files matching patterns.

    Args:
        root: Root directory to search
        patterns: List of glob patterns
        max_depth: Maximum directory depth
        max_files: Maximum files to return

    Returns:
        List of matching file paths
    """
    files = []
    exclude_patterns = ["node_modules", ".git", ".outputs", "__pycache__", "dist", "build"]

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


def _count_lines(files: List[Path]) -> int:
    """
    Count total lines in files.

    Args:
        files: List of file paths

    Returns:
        Total line count
    """
    total = 0
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
                total += sum(1 for _ in fp)
        except:
            pass
    return total


def _record_context(manifest_file: Path, manifest: Dict[str, Any]) -> None:
    """Record findings to context."""
    summary = manifest.get('summary', {})
    total = summary.get('total', {})
    total_files = total.get('files', 0)
    key_count = len(manifest.get('key_files', []))
    languages = manifest.get('detected_stack', {}).get('languages', [])

    context_msg = f"Material scan: {total_files} files, {key_count} key files"
    if languages:
        context_msg += f", stack: {', '.join(languages)}"

    # Record to context (in real implementation)
    print_dim(f"  Context: {context_msg}")


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 005: Material Scan")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
