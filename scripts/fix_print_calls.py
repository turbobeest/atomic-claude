#!/usr/bin/env python3
"""
Fix bare print_* calls that silently discard output.

Functions like print_cyan() RETURN strings but don't print them.
Lines like `print_cyan("text")` or `print_cyan("a") + "b"` on their own
silently discard the result. This script wraps them in print().
"""

import re
import sys
from pathlib import Path

# Functions that return strings but don't print
FORMATTERS = [
    'print_bold', 'print_cyan', 'print_yellow', 'print_green',
    'print_red', 'print_dim', 'print_blue', 'print_magenta', 'print_white'
]

# Build pattern: line starts with whitespace, then a formatter call
# NOT already inside print(), NOT an assignment, NOT a return, NOT a comment
FUNC_PATTERN = '|'.join(re.escape(f) for f in FORMATTERS)

# Match lines that start with a bare formatter call (possibly with concatenation)
BARE_CALL_RE = re.compile(
    r'^(\s+)(' + FUNC_PATTERN + r')\('
)

# Lines that are already correctly wrapped
ALREADY_WRAPPED_RE = re.compile(
    r'^\s+print\s*\('
)

# Lines where the result is used (assignment, return, etc.)
RESULT_USED_RE = re.compile(
    r'^\s+(\w+\s*=|return |yield |if |elif |while |assert |raise )'
)

# Lines that are part of function arguments or other expressions
IN_EXPRESSION_RE = re.compile(
    r'^\s+(print|sys\.stdout|logging|logger|log)\s*[\.(]'
)


def fix_file(filepath: Path) -> int:
    """Fix bare print_* calls in a file. Returns count of fixes."""
    lines = filepath.read_text().splitlines(keepends=True)
    fixed = 0
    new_lines = []

    for i, line in enumerate(lines):
        stripped = line.rstrip('\n')

        # Check if this line has a bare formatter call
        match = BARE_CALL_RE.match(stripped)
        if match and not ALREADY_WRAPPED_RE.match(stripped) and not RESULT_USED_RE.match(stripped):
            indent = match.group(1)
            rest = stripped[len(indent):]

            # Wrap the entire expression in print()
            new_line = f"{indent}print({rest})\n"
            new_lines.append(new_line)
            fixed += 1
        else:
            new_lines.append(line)

    if fixed > 0:
        filepath.write_text(''.join(new_lines))

    return fixed


def main():
    phases_dir = Path(__file__).parent.parent / 'phases'

    total_fixed = 0
    files_fixed = 0

    for py_file in sorted(phases_dir.rglob('*.py')):
        # Skip __pycache__, __init__, orchestrator files
        if '__pycache__' in str(py_file):
            continue

        count = fix_file(py_file)
        if count > 0:
            print(f"  Fixed {count:3d} calls in {py_file.relative_to(phases_dir.parent)}")
            total_fixed += count
            files_fixed += 1

    print(f"\nTotal: {total_fixed} fixes across {files_fixed} files")
    return 0


if __name__ == '__main__':
    sys.exit(main())
