#!/usr/bin/env python3
"""Fix cross-references to renamed category 21 audits."""

import os
from pathlib import Path

# These subcategories were in category 21 (now responsible-design)
CAT21_SUBCATEGORIES = [
    "addiction-manipulation",
    "dark-pattern-avoidance",
    "content-harm",
    "consent-transparency",
    "algorithmic-fairness",
    "economic-fairness",
    "environmental-impact",
]

audits_dir = Path("/mnt/walnut-drive/dev/audits/audits")
fixed_count = 0

for yaml_file in audits_dir.rglob("*.yaml"):
    with open(yaml_file, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    modified = False

    for subcat in CAT21_SUBCATEGORIES:
        old_ref = f"ethical-societal.{subcat}."
        new_ref = f"responsible-design.{subcat}."
        if old_ref in content:
            content = content.replace(old_ref, new_ref)
            modified = True

    if modified and content != original_content:
        with open(yaml_file, 'w', encoding='utf-8') as f:
            f.write(content)
        fixed_count += 1
        print(f"Fixed: {yaml_file.relative_to(audits_dir)}")

print(f"\nTotal cross-reference files fixed: {fixed_count}")
