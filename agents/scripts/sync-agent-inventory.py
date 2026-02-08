#!/usr/bin/env python3
"""
Sync agent-inventory.csv from agent markdown files.

Scans all agent .md files, extracts YAML frontmatter metadata,
and updates the CSV inventory. Run by GitHub Action nightly.

Usage: python3 scripts/sync-agent-inventory.py
"""

import csv
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("PyYAML not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml", "-q"])
    import yaml


def parse_frontmatter(content: str) -> dict[str, Any] | None:
    """Extract YAML frontmatter from markdown content."""
    # Match --- at start, then content, then ---
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return None

    try:
        return yaml.safe_load(match.group(1))
    except yaml.YAMLError as e:
        print(f"  YAML parse error: {e}")
        return None


def extract_agent_metadata(file_path: Path, repo_root: Path) -> dict[str, str] | None:
    """Extract agent metadata from a markdown file."""
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"  Error reading {file_path}: {e}")
        return None

    frontmatter = parse_frontmatter(content)
    if not frontmatter:
        return None

    # Skip files without required agent fields
    if 'name' not in frontmatter or 'tier' not in frontmatter:
        return None

    # Derive path, category, subcategory from file location
    rel_path = file_path.relative_to(repo_root)
    parts = rel_path.parts

    # expert-agents/category/subcategory/agent.md
    # pipeline-agents/phase/agent.md
    if len(parts) >= 3:
        category = parts[1]
        subcategory = parts[2] if len(parts) > 3 else ''
    else:
        category = ''
        subcategory = ''

    # Extract model fallbacks
    model_fallbacks = frontmatter.get('model_fallbacks', [])
    if isinstance(model_fallbacks, list):
        model_fallbacks_str = ';'.join(model_fallbacks)
    else:
        model_fallbacks_str = ''

    # Extract audit data
    audit = frontmatter.get('audit', {})
    grade = audit.get('grade', frontmatter.get('grade', ''))
    composite_score = audit.get('composite_score', frontmatter.get('composite_score', ''))

    return {
        'name': frontmatter.get('name', ''),
        'path': str(rel_path),
        'tier': frontmatter.get('tier', ''),
        'model': frontmatter.get('model', 'sonnet'),
        'model_fallbacks': model_fallbacks_str,
        'category': category,
        'subcategory': subcategory,
        'description': frontmatter.get('description', ''),
        'grade': str(grade),
        'composite_score': str(composite_score) if composite_score else '',
        'role': frontmatter.get('role', 'executor'),
        'rationale': '',  # Preserved from existing CSV if present
    }


def load_existing_csv(csv_path: Path) -> dict[str, dict[str, str]]:
    """Load existing CSV as dict keyed by agent name."""
    if not csv_path.exists():
        return {}

    existing = {}
    with open(csv_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing[row['name']] = dict(row)
    return existing


def scan_agents(repo_root: Path) -> list[dict[str, str]]:
    """Scan all agent directories and extract metadata."""
    agents = []
    agent_dirs = [
        repo_root / 'expert-agents',
        repo_root / 'pipeline-agents',
    ]

    for agent_dir in agent_dirs:
        if not agent_dir.exists():
            continue

        for md_file in agent_dir.rglob('*.md'):
            # Skip READMEs and templates
            if md_file.name.lower() in ('readme.md', 'template.md'):
                continue

            metadata = extract_agent_metadata(md_file, repo_root)
            if metadata:
                agents.append(metadata)

    return agents


def merge_agents(scanned: list[dict[str, str]], existing: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    """Merge scanned agents with existing CSV data (preserve rationale)."""
    merged = []

    for agent in scanned:
        name = agent['name']
        if name in existing:
            # Preserve rationale from existing entry
            agent['rationale'] = existing[name].get('rationale', '')
        merged.append(agent)

    # Sort by name
    merged.sort(key=lambda x: x['name'])
    return merged


def write_csv(agents: list[dict[str, str]], csv_path: Path):
    """Write agents to CSV file."""
    fieldnames = [
        'name', 'path', 'tier', 'model', 'model_fallbacks',
        'category', 'subcategory', 'description', 'grade',
        'composite_score', 'role', 'rationale'
    ]

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(agents)


def main():
    repo_root = Path(__file__).parent.parent.resolve()
    csv_path = repo_root / 'agent-inventory.csv'

    print(f"Syncing agent inventory from markdown files...")
    print(f"  Repository: {repo_root}")

    # Load existing CSV to preserve rationale
    existing = load_existing_csv(csv_path)
    print(f"  Existing agents in CSV: {len(existing)}")

    # Scan agent files
    scanned = scan_agents(repo_root)
    print(f"  Agents found in files: {len(scanned)}")

    # Merge (preserve rationale)
    merged = merge_agents(scanned, existing)

    # Detect changes
    added = set(a['name'] for a in merged) - set(existing.keys())
    removed = set(existing.keys()) - set(a['name'] for a in merged)

    if added:
        print(f"\n  Added agents: {', '.join(sorted(added))}")
    if removed:
        print(f"\n  Removed agents: {', '.join(sorted(removed))}")

    # Write updated CSV
    write_csv(merged, csv_path)
    print(f"\n  Updated {csv_path} with {len(merged)} agents")

    # Report if changes were made
    if added or removed or len(merged) != len(existing):
        print("\n[CHANGES DETECTED]")
        return 0
    else:
        print("\n[NO CHANGES]")
        return 0


if __name__ == '__main__':
    sys.exit(main())
