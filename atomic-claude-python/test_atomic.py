#!/usr/bin/env python3
"""
Quick test suite for atomic.py

Validates core functionality without requiring actual Claude invocations.
"""

import sys
import json
import tempfile
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from lib.atomic import (
    atomic_json_escape,
    atomic_get_primary_model,
    atomic_get_fast_model,
    atomic_state_init,
    atomic_state_get,
    atomic_state_set,
    atomic_state_increment,
    atomic_extract_json,
    atomic_validate_files,
    atomic_mktemp,
    atomic_step,
    atomic_success,
    atomic_error,
    atomic_warn,
    atomic_info,
    atomic_h1,
    atomic_h2,
    C,  # Colors
)


def test_json_escape():
    """Test JSON string escaping."""
    print("\n" + "="*60)
    atomic_h2("Test: JSON Escaping")

    tests = [
        ('simple', 'simple'),
        ('with "quotes"', 'with \\"quotes\\"'),
        ('with\nnewlines', 'with\\nnewlines'),
        ('with\ttabs', 'with\\ttabs'),
        ('with\\backslashes', 'with\\\\backslashes'),
    ]

    for input_str, expected in tests:
        result = atomic_json_escape(input_str)
        if result == expected:
            atomic_success(f"✓ Escaped: {repr(input_str)}")
        else:
            atomic_error(f"✗ Failed: {repr(input_str)} -> {repr(result)} (expected {repr(expected)})")
            return False

    return True


def test_state_management():
    """Test state get/set/increment."""
    print("\n" + "="*60)
    atomic_h2("Test: State Management")

    # Initialize state
    atomic_state_init()

    # Test set and get
    atomic_state_set("test_key", "test_value")
    value = atomic_state_get("test_key")

    if value == "test_value":
        atomic_success("✓ State set/get works")
    else:
        atomic_error(f"✗ State get failed: got {value}")
        return False

    # Test increment
    atomic_state_set("counter", 0)
    atomic_state_increment("counter")
    atomic_state_increment("counter")
    counter = atomic_state_get("counter")

    if counter == 2:
        atomic_success("✓ State increment works")
    else:
        atomic_error(f"✗ State increment failed: got {counter}")
        return False

    return True


def test_json_extraction():
    """Test JSON extraction from mixed output."""
    print("\n" + "="*60)
    atomic_h2("Test: JSON Extraction")

    # Create test file with mixed content
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("""
Here is some text before the JSON.

```json
{
  "status": "success",
  "count": 42,
  "items": ["a", "b", "c"]
}
```

And some text after.
""")
        input_file = f.name

    # Extract JSON
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        output_file = f.name

    success = atomic_extract_json(input_file, output_file)

    if success:
        with open(output_file) as f:
            data = json.load(f)
        if data.get("count") == 42:
            atomic_success("✓ JSON extraction works")
        else:
            atomic_error(f"✗ JSON content wrong: {data}")
            return False
    else:
        atomic_error("✗ JSON extraction failed")
        return False

    # Cleanup
    Path(input_file).unlink(missing_ok=True)
    Path(output_file).unlink(missing_ok=True)

    return True


def test_file_validation():
    """Test file validation."""
    print("\n" + "="*60)
    atomic_h2("Test: File Validation")

    # Create temp files
    temp_files = []
    for i in range(3):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_files.append(f.name)

    # All files exist
    if atomic_validate_files(*temp_files):
        atomic_success("✓ File validation works (all exist)")
    else:
        atomic_error("✗ File validation failed (false negative)")
        return False

    # One file missing
    Path(temp_files[1]).unlink()
    if not atomic_validate_files(*temp_files):
        atomic_success("✓ File validation works (missing detected)")
    else:
        atomic_error("✗ File validation failed (false positive)")
        return False

    # Cleanup
    for f in temp_files:
        Path(f).unlink(missing_ok=True)

    return True


def test_output_functions():
    """Test output formatting functions."""
    print("\n" + "="*60)
    atomic_h2("Test: Output Functions")

    # Just verify they don't crash
    atomic_h1("Test Header 1")
    atomic_h2("Test Header 2")
    atomic_step("Test Step")
    atomic_success("Test Success")
    atomic_error("Test Error")
    atomic_warn("Test Warning")
    atomic_info("Test Info")

    atomic_success("✓ All output functions work")
    return True


def test_temp_file_management():
    """Test temporary file tracking."""
    print("\n" + "="*60)
    atomic_h2("Test: Temp File Management")

    temp_path = atomic_mktemp()

    if Path(temp_path).exists():
        atomic_success(f"✓ Temp file created: {temp_path}")
        # Note: Cleanup happens via atexit
        return True
    else:
        atomic_error("✗ Temp file not created")
        return False


def test_model_getters():
    """Test model getter functions."""
    print("\n" + "="*60)
    atomic_h2("Test: Model Getters")

    primary = atomic_get_primary_model()
    fast = atomic_get_fast_model()

    if primary and fast:
        atomic_success(f"✓ Primary model: {primary}")
        atomic_success(f"✓ Fast model: {fast}")
        return True
    else:
        atomic_error("✗ Model getters failed")
        return False


def main():
    """Run all tests."""
    atomic_h1("ATOMIC.PY TEST SUITE")

    print(f"\n{C.CYAN}Running unit tests for core functionality...{C.NC}\n")

    tests = [
        ("JSON Escaping", test_json_escape),
        ("State Management", test_state_management),
        ("JSON Extraction", test_json_extraction),
        ("File Validation", test_file_validation),
        ("Output Functions", test_output_functions),
        ("Temp File Management", test_temp_file_management),
        ("Model Getters", test_model_getters),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            atomic_error(f"Test '{name}' crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "="*60)
    atomic_h1("TEST RESULTS")

    for name, success in results:
        status = f"{C.GREEN}✓ PASS{C.NC}" if success else f"{C.RED}✗ FAIL{C.NC}"
        print(f"  {status}  {name}")

    total = len(results)
    passed = sum(1 for _, s in results if s)

    print()
    if passed == total:
        atomic_success(f"All tests passed ({passed}/{total})")
        return 0
    else:
        atomic_error(f"Some tests failed ({passed}/{total} passed)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
