#!/usr/bin/env python3
"""
Add rationale column to agent-inventory.csv from TIER-CLASSIFICATION.md
"""

import csv
import re
from pathlib import Path

def parse_tier_classification(md_path: Path) -> dict[str, str]:
    """Extract agent -> rationale mappings from TIER-CLASSIFICATION.md"""
    rationales = {}
    content = md_path.read_text()

    # Match table rows: | `agent-name` | Category | Rationale |
    # or: | `agent-name` | Rationale |
    patterns = [
        # 3-column: | `name` | category | rationale |
        r'\|\s*`([^`]+)`\s*\|[^|]+\|\s*([^|]+)\s*\|',
        # 2-column: | `name` | rationale |
        r'\|\s*`([^`]+)`\s*\|\s*([^|]+)\s*\|',
    ]

    for line in content.split('\n'):
        if '|' in line and '`' in line:
            # Skip header rows
            if 'Agent' in line or '---' in line:
                continue

            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    agent_name = match.group(1).strip()
                    # Get last captured group as rationale
                    rationale = match.groups()[-1].strip()
                    if rationale and not rationale.startswith('-'):
                        rationales[agent_name] = rationale
                    break

    return rationales

def update_csv(csv_path: Path, rationales: dict[str, str]):
    """Add rationale column to CSV"""
    # Read existing CSV
    with open(csv_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    # Add rationale column if not present
    if 'rationale' not in fieldnames:
        fieldnames.append('rationale')

    # Update rows with rationale
    matched = 0
    for row in rows:
        agent_name = row['name']
        if agent_name in rationales:
            row['rationale'] = rationales[agent_name]
            matched += 1
        else:
            row['rationale'] = row.get('rationale', '')

    # Write updated CSV
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Updated {csv_path}")
    print(f"  - Added rationale column")
    print(f"  - Matched {matched}/{len(rows)} agents with rationales")
    print(f"  - {len(rationales)} rationales found in TIER-CLASSIFICATION.md")

def main():
    repo_root = Path(__file__).parent.parent
    tier_md = repo_root / 'TIER-CLASSIFICATION.md'
    csv_path = repo_root / 'agent-inventory.csv'

    print(f"Parsing {tier_md}...")
    rationales = parse_tier_classification(tier_md)

    print(f"\nFound {len(rationales)} agent rationales:")
    for name, rationale in list(rationales.items())[:5]:
        print(f"  - {name}: {rationale[:50]}...")

    print(f"\nUpdating {csv_path}...")
    update_csv(csv_path, rationales)

if __name__ == '__main__':
    main()
