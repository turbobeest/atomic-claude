#!/usr/bin/env python3
"""Fix audit IDs in renamed category 21 (ethical-societal -> responsible-design)."""

import os
from pathlib import Path

cat21_dir = Path("/mnt/walnut-drive/dev/audits/audits/21-responsible-design")
fixed_count = 0

for yaml_file in cat21_dir.rglob("*.yaml"):
    with open(yaml_file, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'ethical-societal.' in content:
        new_content = content.replace('ethical-societal.', 'responsible-design.')
        with open(yaml_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        fixed_count += 1
        print(f"Fixed: {yaml_file.name}")

print(f"\nTotal files fixed: {fixed_count}")
