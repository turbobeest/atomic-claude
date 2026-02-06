#!/usr/bin/env python3
"""
Simple Task Reset Tool

Does exactly what we do manually:
1. Remove task(s) from task-state.json
2. Delete their output files
3. That's it.

Usage:
  ./scripts/reset-task.py 109              # Reset task 109
  ./scripts/reset-task.py 109 --and-after  # Reset 109 and all after it
  ./scripts/reset-task.py --phase 1        # Reset entire phase 1
"""

import sys
import json
import argparse
from pathlib import Path
import shutil

def get_atomic_root():
    """Find ATOMIC_ROOT (current dir or parent with .claude dir)."""
    current = Path.cwd()
    if (current / ".claude").exists():
        return current
    if (current.parent / ".claude").exists():
        return current.parent
    raise RuntimeError("Not in ATOMIC project (no .claude directory found)")

def get_phase_id(task_id: str) -> str:
    """Get phase ID from task ID (e.g., '109' -> '1-discovery')."""
    phase_num = task_id[0]
    phase_names = {
        '0': 'setup', '1': 'discovery', '2': 'prd', '3': 'tasking',
        '4': 'specification', '5': 'implementation', '6': 'code-review',
        '7': 'integration', '8': 'deployment-prep', '9': 'release'
    }
    return f"{phase_num}-{phase_names.get(phase_num, 'unknown')}"

def reset_task(task_id: str, and_after: bool = False):
    """Reset task(s) - removes from state and deletes files."""
    atomic_root = get_atomic_root()
    task_state_file = atomic_root / ".claude" / "task-state.json"

    if not task_state_file.exists():
        print(f"✗ Task state file not found: {task_state_file}")
        return False

    # Load task state
    with open(task_state_file) as f:
        state = json.load(f)

    phase_id = get_phase_id(task_id)

    if phase_id not in state.get('phases', {}):
        print(f"✗ Phase {phase_id} not found in task state")
        return False

    phase = state['phases'][phase_id]
    tasks = phase.get('tasks', {})

    # Determine which tasks to reset
    if and_after:
        tasks_to_reset = [tid for tid in tasks.keys() if tid >= task_id]
    else:
        tasks_to_reset = [task_id] if task_id in tasks else []

    if not tasks_to_reset:
        print(f"✗ Task {task_id} not found in phase {phase_id}")
        return False

    print(f"\nResetting {len(tasks_to_reset)} task(s) in phase {phase_id}:")

    # Remove tasks from state
    for tid in tasks_to_reset:
        task_name = tasks[tid].get('name', 'Unknown')
        print(f"  ✓ {tid}  {task_name}")
        del state['phases'][phase_id]['tasks'][tid]

    # Save updated state
    with open(task_state_file, 'w') as f:
        json.dump(state, f, indent=2)

    # Delete output files
    outputs_dir = atomic_root / ".outputs" / phase_id
    if outputs_dir.exists():
        deleted_files = []

        # Delete prompt files for these tasks
        prompts_dir = outputs_dir / "prompts"
        if prompts_dir.exists():
            for tid in tasks_to_reset:
                for pattern in [f"*{tid}*", f"task-{tid}*"]:
                    for file in prompts_dir.glob(pattern):
                        file.unlink()
                        deleted_files.append(file)

        # Delete any task-specific output files
        for tid in tasks_to_reset:
            for pattern in [f"*{tid}*", f"task-{tid}*"]:
                for file in outputs_dir.glob(pattern):
                    if file.is_file():
                        file.unlink()
                        deleted_files.append(file)

        if deleted_files:
            print(f"\nDeleted {len(deleted_files)} file(s):")
            for f in deleted_files[:5]:  # Show first 5
                print(f"  • {f.name}")
            if len(deleted_files) > 5:
                print(f"  ... and {len(deleted_files) - 5} more")

    print(f"\n✅ Reset complete. Run phase {phase_id.split('-')[0]} to continue.")
    return True

def reset_phase(phase_num: str):
    """Reset entire phase."""
    atomic_root = get_atomic_root()
    task_state_file = atomic_root / ".claude" / "task-state.json"

    if not task_state_file.exists():
        print(f"✗ Task state file not found")
        return False

    with open(task_state_file) as f:
        state = json.load(f)

    # Find phase by number
    phase_id = None
    for pid in state.get('phases', {}).keys():
        if pid.startswith(f"{phase_num}-"):
            phase_id = pid
            break

    if not phase_id:
        print(f"✗ Phase {phase_num} not found")
        return False

    task_count = len(state['phases'][phase_id].get('tasks', {}))
    print(f"\nResetting entire phase {phase_id} ({task_count} tasks)")

    # Delete phase from state
    del state['phases'][phase_id]

    with open(task_state_file, 'w') as f:
        json.dump(state, f, indent=2)

    # Delete output directory
    outputs_dir = atomic_root / ".outputs" / phase_id
    if outputs_dir.exists():
        shutil.rmtree(outputs_dir)
        print(f"  ✓ Deleted: .outputs/{phase_id}/")

    print(f"\n✅ Phase reset complete. Run phase {phase_num} to start fresh.")
    return True

def main():
    parser = argparse.ArgumentParser(description='Reset pipeline tasks')
    parser.add_argument('task_id', nargs='?', help='Task ID to reset (e.g., 109)')
    parser.add_argument('--and-after', action='store_true',
                       help='Reset this task and all after it in the same phase')
    parser.add_argument('--phase', type=str,
                       help='Reset entire phase (e.g., --phase 1)')

    args = parser.parse_args()

    if args.phase:
        return 0 if reset_phase(args.phase) else 1
    elif args.task_id:
        return 0 if reset_task(args.task_id, args.and_after) else 1
    else:
        parser.print_help()
        return 1

if __name__ == '__main__':
    sys.exit(main())
