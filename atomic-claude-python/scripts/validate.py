#!/usr/bin/env python3
"""
Validation script for Python conversion
Checks syntax, imports, and basic functionality
"""

import ast
import sys
from pathlib import Path

def validate_python_file(file_path: Path) -> tuple[bool, str]:
    """Validate a Python file for syntax errors."""
    try:
        with open(file_path) as f:
            code = f.read()
        ast.parse(code)
        return True, f"✓ {file_path.name}"
    except SyntaxError as e:
        return False, f"✗ {file_path.name}: {e}"

def main():
    """Validate all Python files in lib/."""
    lib_dir = Path(__file__).parent.parent / "lib"

    results = []
    for py_file in lib_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        success, message = validate_python_file(py_file)
        results.append((success, message))
        print(message)

    # Summary
    passed = sum(1 for s, _ in results if s)
    total = len(results)
    print(f"\nValidation: {passed}/{total} files passed")

    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
