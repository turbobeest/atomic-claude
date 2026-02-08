#!/usr/bin/env python3
"""Fix YAML errors caused by improper *.go insertions."""

import re
from pathlib import Path

AUDITS_DIR = Path("/mnt/walnut-drive/dev/audits/audits")

fixed = 0

for yaml_file in AUDITS_DIR.rglob("*.yaml"):
    with open(yaml_file, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # Remove the improperly inserted "*.go" lines
    # These were added as:
    #   file_patterns:
    #     - "*.go"          <-- BAD: this breaks the structure
    #   - glob: '...'       <-- This is the correct format

    # Pattern 1: Remove standalone - "*.go" lines that aren't proper glob objects
    content = re.sub(r'\n  file_patterns:\n    - "\*\.go"\n', '\n  file_patterns:\n', content)

    # Pattern 2: Also check for the pattern in different indentation
    content = re.sub(r'\n    - "\*\.go"\n  -', '\n  -', content)

    # Pattern 3: Remove any stray - "*.go" that's on its own line without proper context
    lines = content.split('\n')
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Check if this is a problematic *.go line
        if line.strip() == '- "*.go"':
            # Look at context - is this properly within a list of globs?
            if i > 0:
                prev_stripped = lines[i-1].strip()
                # If previous line is 'file_patterns:' this is wrong placement
                if prev_stripped == 'file_patterns:':
                    # Skip this line - it's malformed
                    i += 1
                    continue
                # If previous line is a glob entry, this is also wrong
                elif prev_stripped.startswith('- glob:') or prev_stripped.startswith('purpose:'):
                    i += 1
                    continue
            # If next line starts with '- glob:', this was inserted wrongly
            if i < len(lines) - 1:
                next_stripped = lines[i+1].strip()
                if next_stripped.startswith('- glob:'):
                    i += 1
                    continue

        new_lines.append(line)
        i += 1

    content = '\n'.join(new_lines)

    if content != original:
        with open(yaml_file, 'w', encoding='utf-8') as f:
            f.write(content)
        fixed += 1
        print(f"Fixed: {yaml_file.name}")

print(f"\nTotal fixed: {fixed}")
