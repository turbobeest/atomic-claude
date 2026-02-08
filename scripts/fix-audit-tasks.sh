#!/bin/bash
#
# Fix All Audit Tasks - Replace bash script calls with Python audit module
#

set -e

echo "=========================================="
echo "Fixing Audit Tasks"
echo "=========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# List of audit tasks that need fixing
AUDIT_TASKS=(
    "phases/phase_01_discovery/tasks/task_109_phase_audit.py"
    "phases/phase_03_tasking/tasks/task_305_phase_audit.py"
    "phases/phase_04_specification/tasks/task_405_phase_audit.py"
    "phases/phase_05_implementation/tasks/task_506_phase_audit.py"
    "phases/phase_06_code_review/tasks/task_605_phase_audit.py"
)

for task_file in "${AUDIT_TASKS[@]}"; do
    if [ ! -f "$task_file" ]; then
        echo "⚠️  File not found: $task_file"
        continue
    fi

    echo "Fixing: $task_file"

    # Check if already fixed (uses core.audit)
    if grep -q "from core.audit import" "$task_file"; then
        echo "  ✓ Already uses core.audit"
        continue
    fi

    # Replace the execute function with a simple call to core.audit
    cat > "${task_file}.new" << 'EOFPYTHON'
"""
Phase Audit Task

AI-driven audit selection from audit repository.
Wrapper around the Python audit system.
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.audit import run_phase_audit
from core.utils.cli_ui import print_green, print_yellow


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute phase audit task.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, skip audit for testing

    Returns:
        True if audit completed or skipped (non-blocking)
    """
    # Extract phase number from output_dir
    # e.g., ".outputs/3-tasking" -> 3
    phase_name = output_dir.name
    if '-' in phase_name:
        phase_num = int(phase_name.split('-')[0])
        phase_id = phase_name
    else:
        print_yellow("⚠️  Could not determine phase number from output directory")
        return True  # Non-blocking

    # Run audit (non-blocking - returns True even if audit fails)
    result = run_phase_audit(phase_num, phase_id, output_dir, uat_mode)

    if result:
        print_green("✓ Phase audit complete")
    else:
        print_yellow("⚠️  Phase audit had issues (non-blocking)")

    return True  # Always return True - audits are non-blocking


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Phase Audit Task")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
EOFPYTHON

    # Backup original
    cp "$task_file" "${task_file}.backup"

    # Replace with fixed version
    mv "${task_file}.new" "$task_file"

    echo "  ✓ Fixed"
done

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo ""
echo "Fixed ${#AUDIT_TASKS[@]} audit tasks"
echo "Backups created with .backup extension"
echo ""
echo "All audit tasks now use core.audit module"
echo "instead of calling bash scripts directly."
echo ""
