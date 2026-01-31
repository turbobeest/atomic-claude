#!/usr/bin/env python3
"""Fix YAML errors caused by improper *.go additions."""

import re
from pathlib import Path

AUDITS_DIR = Path("/mnt/walnut-drive/dev/audits/audits")

fixed = 0
for yaml_file in AUDITS_DIR.rglob("*.yaml"):
    with open(yaml_file, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # Remove improperly added "*.go" lines that aren't in a list context
    # Pattern: line starting with spaces followed by - "*.go" that's not in file_patterns
    lines = content.split('\n')
    new_lines = []
    skip_next = False

    for i, line in enumerate(lines):
        # Check if this line is a problematic *.go addition
        if '- "*.go"' in line:
            # Check if previous line contains file_patterns or is a list item
            if i > 0:
                prev_line = lines[i-1].strip()
                # If previous line is file_patterns: or another list item, keep it
                if prev_line == 'file_patterns:' or prev_line.startswith('- '):
                    new_lines.append(line)
                else:
                    # Skip this improperly placed line
                    continue
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    content = '\n'.join(new_lines)

    # Also fix any pattern additions that broke YAML
    # Remove lines like "# Python logging" etc that were added incorrectly
    bad_patterns = [
        r'\n    # Python logging\n',
        r'\n    # JavaScript/Node console\n',
        r'\n    # Go logging\n',
        r'\n    # Java logging\n',
        r'\n    # Ruby logging\n',
        r'\n    # DynamoDB patterns\n',
        r'\n    # Cassandra patterns\n',
        r'\n    # MongoDB patterns\n',
        r'\n    # Redis patterns\n',
        r'\n    - pattern:.*\n      description:.*\n',
    ]

    # Remove the problematic pattern expansions that broke YAML
    content = re.sub(r'\n  # Additional patterns for comprehensive coverage:.*?(?=\n[a-z]|\Z)', '', content, flags=re.DOTALL)

    if content != original:
        with open(yaml_file, 'w', encoding='utf-8') as f:
            f.write(content)
        fixed += 1

print(f"Fixed {fixed} files")
