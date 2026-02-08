#!/usr/bin/env python3
"""
Fix context management issues:
1. Upgrade oversized "focused" (>150 lines) to "expert"
2. Upgrade oversized "expert" (>400 lines) to "phd"
3. Standardize non-standard tier values
"""

import yaml
import os
from pathlib import Path
from collections import defaultdict

# Custom YAML representer to preserve multiline strings
def str_representer(dumper, data):
    if '\n' in data:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

yaml.add_representer(str, str_representer)

AUDITS_DIR = Path("/mnt/walnut-drive/dev/audits/audits")

# Tier thresholds (lines)
THRESHOLDS = {
    'focused': 150,
    'expert': 400,
    'phd': 800,
}

# Tier standardization mapping
TIER_MAPPING = {
    'standard': 'focused',
    'intermediate': 'focused',
    'advanced': 'expert',
    'comprehensive': 'phd',
}

def count_lines(filepath):
    """Count lines in a file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return sum(1 for _ in f)

def load_yaml(filepath):
    """Load YAML file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_yaml(filepath, data):
    """Save YAML file with proper formatting."""
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True,
                  sort_keys=False, width=100)

def main():
    print("Fixing context management issues...")

    stats = defaultdict(int)
    fixes = {
        'tier_standardized': [],
        'focused_to_expert': [],
        'expert_to_phd': [],
    }

    # Find all audit files
    audit_files = list(AUDITS_DIR.rglob('*.yaml'))
    print(f"Found {len(audit_files)} audit files")

    for filepath in audit_files:
        try:
            data = load_yaml(filepath)
            if not data or 'audit' not in data:
                continue

            audit = data.get('audit', {})
            current_tier = audit.get('tier', '')
            line_count = count_lines(filepath)
            modified = False

            # 1. Standardize non-standard tiers
            if current_tier in TIER_MAPPING:
                new_tier = TIER_MAPPING[current_tier]
                audit['tier'] = new_tier
                stats['tier_standardized'] += 1
                fixes['tier_standardized'].append({
                    'file': str(filepath.relative_to(AUDITS_DIR)),
                    'old': current_tier,
                    'new': new_tier,
                })
                current_tier = new_tier
                modified = True

            # 2. Check if tier is undersized for content
            if current_tier == 'focused' and line_count > THRESHOLDS['focused']:
                audit['tier'] = 'expert'
                stats['focused_to_expert'] += 1
                fixes['focused_to_expert'].append({
                    'file': str(filepath.relative_to(AUDITS_DIR)),
                    'lines': line_count,
                })
                modified = True
            elif current_tier == 'expert' and line_count > THRESHOLDS['expert']:
                audit['tier'] = 'phd'
                stats['expert_to_phd'] += 1
                fixes['expert_to_phd'].append({
                    'file': str(filepath.relative_to(AUDITS_DIR)),
                    'lines': line_count,
                })
                modified = True

            if modified:
                save_yaml(filepath, data)

        except Exception as e:
            print(f"  ERROR: {filepath}: {e}")

    # Print summary
    print(f"\n=== Summary ===")
    print(f"Tier standardizations: {stats['tier_standardized']}")
    print(f"  - standard → focused: {sum(1 for f in fixes['tier_standardized'] if f['old'] == 'standard')}")
    print(f"  - advanced → expert: {sum(1 for f in fixes['tier_standardized'] if f['old'] == 'advanced')}")
    print(f"  - comprehensive → phd: {sum(1 for f in fixes['tier_standardized'] if f['old'] == 'comprehensive')}")
    print(f"  - intermediate → focused: {sum(1 for f in fixes['tier_standardized'] if f['old'] == 'intermediate')}")
    print(f"\nSize-based upgrades:")
    print(f"  - focused → expert (>150 lines): {stats['focused_to_expert']}")
    print(f"  - expert → phd (>400 lines): {stats['expert_to_phd']}")
    print(f"\nTotal files modified: {stats['tier_standardized'] + stats['focused_to_expert'] + stats['expert_to_phd']}")

    # Save detailed report
    report = {
        'summary': dict(stats),
        'fixes': fixes,
    }

    report_path = AUDITS_DIR.parent / 'meta-audit' / 'context-fixes-report.yaml'
    with open(report_path, 'w') as f:
        yaml.dump(report, f, default_flow_style=False)
    print(f"\nDetailed report saved to: {report_path}")

if __name__ == '__main__':
    main()
