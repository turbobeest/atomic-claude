"""
Backtrack Module

Reset pipeline to any phase/task with clean slate.

Allows users to go back to any point and start fresh by:
1. Clearing state for all phases/tasks after target point
2. Deleting artifacts after target point
3. Optionally clearing generated code
"""

import logging
from pathlib import Path
import shutil
import json
from typing import Optional

from core.memory import memory_init, memory_handle_backtrack
from core.utils.file_ops import write_json

logger = logging.getLogger(__name__)

# Compute atomic-claude root directory (parent of orchestration/)
atomic_root = Path(__file__).resolve().parent.parent


from orchestration.pipeline import PHASE_REGISTRY

# Derive PHASE_NAMES from the canonical PHASE_REGISTRY to avoid duplication
PHASE_NAMES = {
    meta.phase_num: meta.phase_id.split("-", 1)[1]
    for meta in PHASE_REGISTRY.values()
}

# Deliverable directories written to project_root (outside atomic-claude)
# These are cleaned during backtrack alongside .outputs/
PROJECT_DELIVERABLES = {
    1: ["docs/diagrams", ".claude/needs"],
    2: ["docs/prd"],
    4: [".openspec", ".claude/specs"],
    5: [".claude/testing", ".claude/config"],
    6: [".claude/reviews"],
    7: [".claude/integration"],
    8: [".claude/deployment"],
    9: [".claude/release"],
}


def _clear_directory_for_phases(base_dir: Path, phases: list, pattern_fn, label: str = "") -> None:
    """Clear directories or files matching a pattern for a list of phases.

    Args:
        base_dir: Base directory to search in
        phases: List of phase numbers to clear
        pattern_fn: Callable(phase_num) -> list of (Path, is_glob) tuples to clear
        label: Label for log messages
    """
    if not base_dir.exists():
        return
    for p in phases:
        targets = pattern_fn(p)
        for target, is_glob in targets:
            if is_glob:
                for f in base_dir.glob(str(target)):
                    if f.is_dir():
                        shutil.rmtree(f)
                    else:
                        f.unlink()
                    print(f"   ✓ Cleared {f.name if not f.is_dir() else f}" +
                          (f" ({label})" if label else ""))
            else:
                full_path = base_dir / target if not target.is_absolute() else target
                if full_path.exists():
                    if full_path.is_dir():
                        shutil.rmtree(full_path)
                    else:
                        full_path.unlink()
                    print(f"   ✓ Cleared {full_path}" +
                          (f" ({label})" if label else ""))


def _clear_state(state: dict, state_file: Path, phase: int, phase_name: str,
                 task: Optional[str], task_num: Optional[int],
                 phases_to_clear: list) -> None:
    """Clear state entries for rolled-back phases and update pointers.

    Modifies `state` dict in place. Does NOT write to disk (caller does that
    after all cleanup is complete).
    """
    print("\n📝 Clearing state...")
    for p in phases_to_clear:
        phase_id = f"{p}-{PHASE_NAMES[p]}"
        if phase_id in state.get("phases", {}):
            del state["phases"][phase_id]
            print(f"   ✓ Cleared {phase_id}")

    target_phase_id = f"{phase}-{phase_name}"
    if task:
        # Task specified: clear tasks >= target, reset phase status
        phase_data = state.get("phases", {}).get(target_phase_id, {})
        tasks = phase_data.get("tasks", {})

        cleared_count = 0
        for task_id in list(tasks.keys()):
            if int(task_id) >= task_num:
                del tasks[task_id]
                cleared_count += 1

        if cleared_count:
            print(f"   ✓ Cleared {cleared_count} tasks in {target_phase_id}")

        # Reset phase-level completion (tasks were removed, phase is no longer complete)
        if target_phase_id in state.get("phases", {}):
            state["phases"][target_phase_id].pop("completed_at", None)
            state["phases"][target_phase_id].pop("status", None)
            print(f"   ✓ Reset {target_phase_id} phase status")
    else:
        # No task: clear entire target phase state
        if target_phase_id in state.get("phases", {}):
            del state["phases"][target_phase_id]
            print(f"   ✓ Cleared {target_phase_id}")

    # Update current_phase pointer to the target
    state["current_phase"] = target_phase_id
    state["current_task"] = None


def _clear_artifacts(phases_to_clear: list, phase: int, phase_name: str,
                     task: Optional[str], task_num: Optional[int]) -> None:
    """Clear output artifacts, deliverables, audit/closeout reports for rolled-back phases."""
    project_root = atomic_root.parent
    outputs_dir = atomic_root / ".outputs"
    first_task = not task or (task_num is not None and task_num % 100 == 1)

    print("\n📁 Clearing artifacts...")

    # Always wipe subsequent phases entirely
    for p in phases_to_clear:
        phase_dir = outputs_dir / f"{p}-{PHASE_NAMES[p]}"
        if phase_dir.exists():
            shutil.rmtree(phase_dir)
            print(f"   ✓ Cleared {phase_dir}")

    # Target phase: wipe entirely if no task specified OR if the target
    # task is the first task in the phase (nothing before it to preserve).
    target_phase_dir = outputs_dir / f"{phase}-{phase_name}"
    if first_task:
        if target_phase_dir.exists():
            shutil.rmtree(target_phase_dir)
            print(f"   ✓ Cleared {target_phase_dir}")
    else:
        print(f"   ℹ Preserved {target_phase_dir} (earlier task artifacts needed)")

    # Clear project-root deliverables (written outside atomic-claude)
    print("\n📁 Clearing project deliverables...")

    # Clear pipeline-collected reference material if backtracking to/before task 004
    if phase == 0 and (not task or (task_num is not None and task_num <= 4)):
        collected_dir = project_root / "docs" / "reference" / "collected"
        if collected_dir.exists():
            shutil.rmtree(collected_dir)
            print("   ✓ Cleared docs/reference/collected/ (pipeline-collected material)")

    # Clear deliverable dirs for rolled-back phases
    for p in phases_to_clear:
        for rel_dir in PROJECT_DELIVERABLES.get(p, []):
            d = project_root / rel_dir
            if d.exists():
                shutil.rmtree(d)
                print(f"   ✓ Cleared {rel_dir}/ (Phase %s deliverable)" % p)

    # Clear target phase deliverables if resetting from the start
    if first_task:
        for rel_dir in PROJECT_DELIVERABLES.get(phase, []):
            d = project_root / rel_dir
            if d.exists():
                shutil.rmtree(d)
                print(f"   ✓ Cleared {rel_dir}/ (Phase %s deliverable)" % phase)

    # Clear audit evaluation reports (.outputs/audits/phase-N/)
    audits_dir = outputs_dir / "audits"
    if audits_dir.exists():
        for p in phases_to_clear:
            phase_audit_dir = audits_dir / f"phase-{p}"
            if phase_audit_dir.exists():
                shutil.rmtree(phase_audit_dir)
                print(f"   ✓ Cleared {phase_audit_dir}")
        if first_task:
            target_audit_dir = audits_dir / f"phase-{phase}"
            if target_audit_dir.exists():
                shutil.rmtree(target_audit_dir)
                print(f"   ✓ Cleared {target_audit_dir}")

    # Clear closeout reports for rolled-back phases
    closeout_dir = project_root / ".claude" / "closeout"
    if closeout_dir.exists():
        for p in phases_to_clear:
            for pattern in [f"phase-{p:02d}-closeout.*", f"phase-{p}-closeout.*"]:
                for f in closeout_dir.glob(pattern):
                    f.unlink()
                    print(f"   ✓ Cleared {f.name}")
        if first_task:
            for pattern in [f"phase-{phase:02d}-closeout.*", f"phase-{phase}-closeout.*"]:
                for f in closeout_dir.glob(pattern):
                    f.unlink()
                    print(f"   ✓ Cleared {f.name}")

    # Clear audit reports for rolled-back phases
    audit_dir = project_root / ".claude" / "audit"
    if audit_dir.exists():
        for p in phases_to_clear:
            for pattern in [f"phase-{p:02d}-audit.*", f"phase-{p}-audit.*"]:
                for f in audit_dir.glob(pattern):
                    f.unlink()
                    print(f"   ✓ Cleared {f.name}")
        if first_task:
            for pattern in [f"phase-{phase:02d}-audit.*", f"phase-{phase}-audit.*"]:
                for f in audit_dir.glob(pattern):
                    f.unlink()
                    print(f"   ✓ Cleared {f.name}")

    # Clear dashboard status file (no active task after backtrack)
    current_task_file = atomic_root / ".state" / "current-task.json"
    if current_task_file.exists():
        current_task_file.unlink()
        print("   ✓ Cleared dashboard current-task status")

    # Clear error log (prevents stale error cards in dashboard)
    errors_file = atomic_root / ".logs" / "errors.json"
    if errors_file.exists():
        errors_file.write_text('{"errors": []}')
        print("   ✓ Cleared error log")

    # Signal dashboard to clear error state
    try:
        from orchestration.dashboard_sync import clear_current_task
        clear_current_task()
    except Exception as e:
        logger.debug("Failed to signal dashboard during backtrack: %s", e)

    # Clear memory debug logs for affected phases
    debug_dir = atomic_root / ".state" / "memory-debug"
    if debug_dir.exists():
        for p in phases_to_clear:
            phase_id = f"{p}-{PHASE_NAMES[p]}"
            for f in debug_dir.glob(f"*{phase_id}*"):
                f.unlink()
        if not task:
            target_id = f"{phase}-{phase_name}"
            for f in debug_dir.glob(f"*{target_id}*"):
                f.unlink()
        remaining = list(debug_dir.iterdir())
        if not remaining:
            print("   ✓ Cleared all memory debug logs")
        else:
            print("   ✓ Cleared memory debug logs for rolled-back phases")

    # Clear model overrides (user may want fresh selections)
    overrides_file = atomic_root / ".state" / "model-overrides.json"
    if overrides_file.exists():
        overrides_file.unlink()
        print("   ✓ Cleared model overrides")

    # Clear LLM response cache (prevents stale cached responses on re-run)
    llm_cache_dir = atomic_root / ".state" / "llm_cache"
    if llm_cache_dir.exists():
        shutil.rmtree(llm_cache_dir)
        print("   ✓ Cleared LLM response cache")


def _clear_memory(phases_to_clear: list, phase: int, phase_name: str,
                  task: Optional[str], task_num: Optional[int]) -> None:
    """Clear memory entries and invalidate checkpoints for rolled-back phases."""
    first_task = not task or (task_num is not None and task_num % 100 == 1)

    # Clear memory entries and invalidate checkpoints
    try:
        memory_init()
        memory_handle_backtrack(phase)
    except Exception as e:
        logger.warning("Memory cleanup during backtrack failed: %s", e)

    # Clear memory file directories
    memory_dir = atomic_root / ".state" / "memory"
    for p in phases_to_clear:
        phase_mem = memory_dir / f"phase-{p}"
        if phase_mem.exists():
            shutil.rmtree(phase_mem)
            print(f"   ✓ Cleared memory for phase {p}")

    if first_task:
        target_mem = memory_dir / f"phase-{phase}"
        if target_mem.exists():
            shutil.rmtree(target_mem)
            print(f"   ✓ Cleared memory for phase %s" % phase)


def _clear_graph(phases_to_clear: list, phase: int, phase_name: str,
                 task: Optional[str], task_num: Optional[int]) -> None:
    """Clear FalkorDB graph data for rolled-back phases."""
    first_task = not task or (task_num is not None and task_num % 100 == 1)
    target_phase_id = f"{phase}-{phase_name}"

    try:
        from core.graph import get_graph
        from core.graph.exceptions import GraphUnavailableError
    except ImportError:
        logger.debug("Graph module not available for backtrack cleanup")
        return

    try:
        graph_cleaned = False
        for p in phases_to_clear:
            p_id = f"{p}-{PHASE_NAMES[p]}"
            graph = get_graph(phase_id=p_id)
            try:
                deleted = graph.delete_phase_data(p_id)
                logger.info("Deleted %s graph nodes/edges for phase %s", deleted, p_id)
                if deleted:
                    print(f"   ✓ Cleared {deleted} graph nodes/edges for {p_id}")
                    graph_cleaned = True
            except Exception as e:
                logger.warning("Graph cleanup failed for phase %s: %s", p_id, e)
        if first_task:
            graph = get_graph(phase_id=target_phase_id)
            try:
                deleted = graph.delete_phase_data(target_phase_id)
                logger.info("Deleted %s graph nodes/edges for phase %s", deleted, target_phase_id)
                if deleted:
                    print(f"   ✓ Cleared {deleted} graph nodes/edges for {target_phase_id}")
                    graph_cleaned = True
            except Exception as e:
                logger.warning("Graph cleanup failed for phase %s: %s", target_phase_id, e)
        if not graph_cleaned:
            print("   ℹ No graph data to clear (graph empty)")
    except GraphUnavailableError:
        logger.debug("FalkorDB unavailable for backtrack graph cleanup")


def _prompt_code_cleanup(project_root: Path, force: bool) -> None:
    """Prompt user to optionally clear generated code and tests."""
    print("\n🗂️  Generated code...")
    if force:
        clear_code = "n"
    else:
        clear_code = input("Clear generated code in ../src/? (y/n): ")
    if clear_code.lower() == "y":
        src_dir = project_root / "src"
        if src_dir.exists():
            shutil.rmtree(src_dir)
            src_dir.mkdir()
            print("   ✓ Cleared ../src/")

    if force:
        clear_tests = "n"
    else:
        clear_tests = input("Clear generated tests in ../tests/? (y/n): ")
    if clear_tests.lower() == "y":
        tests_dir = project_root / "tests"
        if tests_dir.exists():
            shutil.rmtree(tests_dir)
            tests_dir.mkdir()
            print("   ✓ Cleared ../tests/")


def backtrack_to(phase: int, task: Optional[str] = None, force: bool = False):
    """
    Reset pipeline to a specific phase/task.

    Args:
        phase: Phase number (0-9)
        task: Optional task ID to reset to (e.g., "205")
        force: If True, skip confirmation prompts (for programmatic use)

    This will:
    1. Clear memory entries and graph data for rolled-back phases
    2. Clear all artifacts after target
    3. Write updated state (last, so a crash mid-cleanup is safe)
    """
    # Validate phase number
    if not isinstance(phase, int) or phase < 0 or phase > 9:
        print(f"\n❌ Invalid phase number: {phase}. Must be 0-9.")
        return

    # Safety check: ensure we're in the right directory
    if not (atomic_root / "main.py").exists():
        raise RuntimeError(f"Safety check failed: {atomic_root} does not look like atomic-claude root")

    phase_name = PHASE_NAMES.get(phase, f"phase-{phase}")

    print(f"\n🔄 Backtracking to Phase {phase}: {phase_name}" + (f", Task {task}" if task else ""))
    print("\n⚠️  WARNING: This will DELETE all work after this point!")
    print("   - State will be cleared")
    print("   - Artifacts will be deleted")
    print("   - Memory will be cleared")

    if not force:
        confirm = input("\nType 'yes' to confirm: ")

        if confirm.lower() != "yes":
            print("❌ Backtrack cancelled")
            return

    # Load state
    state_file = atomic_root / ".state" / "task-state.json"
    if not state_file.exists():
        print("❌ No state file found")
        return

    with open(state_file) as f:
        state = json.load(f)

    # Determine what to clear
    phases_to_clear = list(range(phase + 1, 10))

    # Parse task number early (needed for artifact cleanup logic too)
    task_num = None
    if task:
        task_num = int(task) if task.isdigit() else int(task.replace("task", ""))

        # Validate task belongs to the target phase (e.g., Phase 1 tasks are 1xx)
        expected_prefix = phase * 100
        if not (expected_prefix < task_num <= expected_prefix + 99):
            print(f"\n❌ Task {task} doesn't belong to Phase {phase}.")
            print(f"   Phase {phase} tasks are numbered {expected_prefix + 1:03d}–{expected_prefix + 99:03d}")
            print(f"   Example: python main.py backtrack {phase} {expected_prefix + 1:03d}")
            return

    # Step 1: Clear memory and graph (safe — these are supplementary data)
    _clear_memory(phases_to_clear, phase, phase_name, task, task_num)
    _clear_graph(phases_to_clear, phase, phase_name, task, task_num)

    # Step 2: Clear artifacts (file deletions)
    _clear_artifacts(phases_to_clear, phase, phase_name, task, task_num)

    # Step 3: Update state in memory (modify dict but don't write yet)
    _clear_state(state, state_file, phase, phase_name, task, task_num, phases_to_clear)

    # Step 4: Write state LAST so crash during cleanup doesn't leave
    # state marked as backtracked while artifacts still exist (Finding #10, #11)
    write_json(state_file, state)

    # Step 5: Prompt for optional code cleanup
    project_root = atomic_root.parent
    _prompt_code_cleanup(project_root, force)

    # Show resume command
    print(f"\n✅ Backtrack complete!")
    print(f"\nResume with:")
    if task:
        print(f"   python main.py run {phase} --resume-at={task}")
    else:
        print(f"   python main.py run {phase}")
