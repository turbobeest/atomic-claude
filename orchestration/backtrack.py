"""
Backtrack Module

Reset pipeline to any phase/task with clean slate.

Allows users to go back to any point and start fresh by:
1. Clearing state for all phases/tasks after target point
2. Deleting artifacts after target point
3. Optionally clearing generated code
"""

from pathlib import Path
import shutil
import json
from typing import Optional


PHASE_NAMES = {
    0: "setup", 1: "discovery", 2: "prd", 3: "tasking",
    4: "specification", 5: "implementation", 6: "code-review",
    7: "integration", 8: "deployment-prep", 9: "release"
}


def backtrack_to(phase: int, task: Optional[str] = None):
    """
    Reset pipeline to a specific phase/task.

    Args:
        phase: Phase number (0-9)
        task: Optional task ID to reset to (e.g., "205")

    This will:
    1. Reset state to target point
    2. Clear all artifacts after target
    3. Clear all phases after target
    """

    phase_name = PHASE_NAMES.get(phase, f"phase-{phase}")

    print(f"\n🔄 Backtracking to Phase {phase}: {phase_name}" + (f", Task {task}" if task else ""))
    print("\n⚠️  WARNING: This will DELETE all work after this point!")
    print("   - State will be cleared")
    print("   - Artifacts will be deleted")
    print("   - Memory will be cleared")

    confirm = input("\nType 'yes' to confirm: ")

    if confirm.lower() != "yes":
        print("❌ Backtrack cancelled")
        return

    # Load state
    state_file = Path(".state/task-state.json")
    if not state_file.exists():
        print("❌ No state file found")
        return

    with open(state_file) as f:
        state = json.load(f)

    # Determine what to clear
    phases_to_clear = list(range(phase + 1, 10))

    # Clear state for future phases
    print("\n📝 Clearing state...")
    for p in phases_to_clear:
        phase_id = f"{p}-{PHASE_NAMES[p]}"
        if phase_id in state.get("phases", {}):
            del state["phases"][phase_id]
            print(f"   ✓ Cleared {phase_id}")

    # If task specified, clear subsequent tasks in target phase
    if task:
        phase_id = f"{phase}-{phase_name}"
        tasks = state.get("phases", {}).get(phase_id, {}).get("tasks", {})

        # Parse task number
        task_num = int(task) if task.isdigit() else int(task.replace("task", ""))

        # Clear tasks after target
        cleared_count = 0
        for task_id in list(tasks.keys()):
            if int(task_id) > task_num:
                del tasks[task_id]
                cleared_count += 1

        if cleared_count:
            print(f"   ✓ Cleared {cleared_count} tasks in {phase_id}")

    # Save updated state
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)

    # Clear artifacts
    print("\n📁 Clearing artifacts...")
    outputs_dir = Path(".outputs")
    for p in phases_to_clear:
        phase_dir = outputs_dir / f"{p}-{PHASE_NAMES[p]}"
        if phase_dir.exists():
            shutil.rmtree(phase_dir)
            print(f"   ✓ Cleared {phase_dir}")

    # Clear memory for future phases
    memory_dir = Path(".state/memory")
    for p in phases_to_clear:
        phase_mem = memory_dir / f"phase-{p}"
        if phase_mem.exists():
            shutil.rmtree(phase_mem)
            print(f"   ✓ Cleared memory for phase {p}")

    # Prompt to clear generated code
    print("\n🗂️  Generated code...")
    clear_code = input("Clear generated code in ../src/? (y/n): ")
    if clear_code.lower() == "y":
        src_dir = Path("../src")
        if src_dir.exists():
            shutil.rmtree(src_dir)
            src_dir.mkdir()
            print("   ✓ Cleared ../src/")

    clear_tests = input("Clear generated tests in ../tests/? (y/n): ")
    if clear_tests.lower() == "y":
        tests_dir = Path("../tests")
        if tests_dir.exists():
            shutil.rmtree(tests_dir)
            tests_dir.mkdir()
            print("   ✓ Cleared ../tests/")

    # Show resume command
    print(f"\n✅ Backtrack complete!")
    print(f"\nResume with:")
    if task:
        print(f"   python main.py run {phase} --resume-at={task}")
    else:
        print(f"   python main.py run {phase}")
