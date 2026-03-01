"""
Shared phase orchestration logic.

Eliminates ~150 lines of duplication per orchestrator by extracting the
common task loop, memory handling, and closeout logic into reusable functions.

Usage in orchestrators:
    from orchestration.phase_runner import run_phase_tasks, create_phase_closeout
"""

import inspect
import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from core.memory import memory_save, MemoryEntryType
from core.state import StateManager
from core.ui import phase_header, phase_complete
from core.utils.file_ops import write_json
from core.llm.resolver import get_resolver
from orchestration.dashboard_sync import (
    clear_current_task,
    ensure_dashboard,
    log_error,
    write_current_task,
)
from orchestration.memory_enrichment import enrich_memory_with_llm, summarize_task_artifacts
from orchestration.pre_task_validation import validate_directory_pristine
from orchestration.task_display import display_task_roster, is_infrastructure_task, resolve_agent_roster
from orchestration.task_memory import TaskMemory

logger = logging.getLogger(__name__)

# Type alias for task tuples: (task_id, task_name, task_callable)
TaskEntry = Tuple[str, str, Callable]


def make_flush_fn(phase_id: str, task_id: str) -> Callable:
    """Create a callback for mid-task memory checkpoints."""
    def flush(content, tags, entry_type):
        memory_save(
            phase=phase_id,
            task_id=task_id,
            content=content,
            tags=tags,
            entry_type=MemoryEntryType.TASK_PROGRESS,
        )
    return flush


def run_phase_tasks(
    *,
    phase_num: int,
    phase_name: str,
    phase_id: str,
    tasks: List[TaskEntry],
    task_artifacts: Dict[str, List[str]],
    atomic_root: Path,
    output_dir: Path,
    resume_at: Optional[str] = None,
    pre_header_fn: Optional[Callable] = None,
    graph=None,
) -> bool:
    """
    Execute a phase's task list with full orchestration.

    This is the shared task loop extracted from orchestrators 00-09. It handles:
    - Phase header display
    - Resume-at logic
    - Pre-task validation
    - Agent roster display
    - Task execution with memory tracking
    - Artifact collection
    - Phase closeout

    Args:
        phase_num: Phase number (0-9)
        phase_name: Human-readable phase name (e.g., "Setup", "Discovery")
        phase_id: Phase identifier (e.g., "0-setup", "1-discovery")
        tasks: List of (task_id, task_name, task_callable) tuples
        task_artifacts: Dict mapping task_id to expected artifact filenames
        atomic_root: Path to atomic-claude root
        output_dir: Phase output directory
        resume_at: Optional task ID to resume from
        pre_header_fn: Optional callable to run after header but before task loop
                       (e.g., phase 0's description print)
        graph: Optional FalkorDB graph instance to pass to tasks

    Returns:
        True if all tasks completed successfully
    """
    label = f"Phase {phase_num}: {phase_name}"

    if resume_at:
        phase_header(f"{label} (resuming)")
    else:
        phase_header(label)
        if pre_header_fn:
            pre_header_fn()

    state = StateManager(atomic_root=atomic_root)
    state.set_current_phase(phase_id)

    # Determine starting point
    start_index = 0
    if resume_at:
        valid_ids = {t[0] for t in tasks}
        if resume_at not in valid_ids:
            logger.error(
                "Invalid resume_at task ID '%s'; valid IDs: %s",
                resume_at, sorted(valid_ids),
            )
            print(f"\n  Invalid task ID '{resume_at}'. Valid: {sorted(valid_ids)}")
            return False
        for i, (task_id, _, _) in enumerate(tasks):
            if task_id == resume_at:
                start_index = i
                break

    # Execute tasks
    for task_id, task_name, task_func in tasks[start_index:]:
        if state.is_task_complete(phase_id, task_id):
            print(f"✓ Task {task_id} already complete, skipping")
            continue

        # Pre-task validation
        if not validate_directory_pristine(phase_id, task_id):
            print(f"\n🛑 Cannot proceed to Task {task_id} - fix violations first")
            clear_current_task()
            return False

        # Agent roster & dashboard
        print(f"\n⚡ Running Task {task_id}: {task_name}")
        ensure_dashboard(atomic_root)
        if is_infrastructure_task(task_name):
            print(f"\n  {task_name}\n")
            write_current_task(phase_id, task_id, task_name)
        else:
            roster = resolve_agent_roster(phase_id, task_id, output_dir)
            roster = display_task_roster(task_id, task_name, roster)
            write_current_task(
                phase_id, task_id, task_name,
                resolved=roster[0][1], agent_roster=roster,
            )

        state.mark_task_started(phase_id, task_id, task_name)
        mem = TaskMemory(
            phase_id, task_id, task_name,
            flush_fn=make_flush_fn(phase_id, task_id),
        )

        # Attach graph for decision trail persistence
        if graph is not None:
            mem.set_graph(graph)

        # Pre-task: gravity assessment and skill selection
        gravity_assessment = None
        skill_selection = None
        try:
            from core.skills import GravityClassifier, SkillSelector
            gravity_classifier = GravityClassifier()
            skill_selector = SkillSelector()

            gravity_assessment = gravity_classifier.assess(
                task_prompt=task_name,
                project_id=state.get("project.id", "default")
                if hasattr(state, "get") else "default",
            )
            logger.info(
                "Task %s gravity: %s (confidence=%.2f)",
                task_id, gravity_assessment.gravity.value,
                gravity_assessment.confidence,
            )

            # Resolve active profile
            active_profile = os.environ.get("ATOMIC_ENV_PROFILE", "cloud_full")
            skill_selection = skill_selector.select(
                task_prompt=task_name,
                profile_name=active_profile,
                gravity=gravity_assessment.gravity,
            )
            if skill_selection.skills:
                logger.info(
                    "Task %s skills: %s (method=%s)",
                    task_id,
                    [s.id for s in skill_selection.skills],
                    skill_selection.method,
                )
        except Exception as e:
            logger.debug("Gravity/skill assessment skipped: %s", e)

        # Format skill context and attach to mem + context var
        if skill_selection and skill_selection.skills and gravity_assessment:
            try:
                from core.skills.context_formatter import (
                    format_skill_context, set_active_skill_context,
                )
                skill_ctx = format_skill_context(
                    skill_selection, gravity_assessment.gravity,
                )
                if skill_ctx:
                    mem.set_skill_context(
                        skill_ctx, skill_selection,
                        gravity_assessment.gravity.value,
                    )
                    set_active_skill_context(skill_ctx)
                    logger.info("Skill context attached to mem for task %s", task_id)
            except Exception as e:
                logger.debug("Skill context formatting skipped: %s", e)

        # Format graph context (agents, traceability, memory) and set context var
        if graph is not None and gravity_assessment:
            try:
                from core.graph.context_injector import (
                    build_graph_context, set_active_graph_context,
                )
                graph_ctx = build_graph_context(
                    graph=graph,
                    phase_id=phase_id,
                    task_id=task_id,
                    task_name=task_name,
                    gravity=gravity_assessment.gravity,
                    roster=roster if not is_infrastructure_task(task_name) else None,
                )
                if graph_ctx:
                    set_active_graph_context(graph_ctx)
                    logger.info(
                        "Graph context attached for task %s (%d chars)",
                        task_id, len(graph_ctx),
                    )
            except Exception as e:
                logger.debug("Graph context assembly skipped: %s", e)

        # Resolve retry policy and pattern selection from gravity
        gravity_key = (
            gravity_assessment.gravity.value if gravity_assessment else "standard"
        )
        try:
            from orchestration.retry_policy import get_policy, ConsecutiveFailureTracker
            retry_policy = get_policy(gravity_key)
        except Exception:
            retry_policy = None

        try:
            from orchestration.coordination.selector import select_pattern
            from orchestration.coordination.executors import (
                execute_with_pattern, ExecutionContext,
            )
            pattern_selection = select_pattern(
                gravity=gravity_key,
                roster=roster if not is_infrastructure_task(task_name) else None,
                task_id=task_id,
                task_name=task_name,
                phase_id=phase_id,
            )
            logger.info(
                "Task %s pattern: %s (score=%.2f)",
                task_id, pattern_selection.pattern.value, pattern_selection.score,
            )
        except Exception as e:
            logger.debug("Pattern selection skipped: %s", e)
            pattern_selection = None

        # --- Task execution with retry wrapper ---
        success = None
        last_error = None
        max_attempts = (retry_policy.max_retries + 1) if retry_policy else 1

        for attempt in range(max_attempts):
            if attempt > 0:
                # Cooldown between retries
                if retry_policy:
                    import time as _time
                    cooldown = retry_policy.cooldown_for_attempt(attempt)
                    if cooldown > 0:
                        logger.info(
                            "Task %s retry %d/%d — cooldown %.1fs",
                            task_id, attempt, retry_policy.max_retries, cooldown,
                        )
                        _time.sleep(cooldown)
                    mem.retry_attempt(attempt, gravity_key, last_error)

            try:
                # Execute via coordination pattern or direct call
                if pattern_selection is not None:
                    exec_ctx = ExecutionContext(
                        task_id=task_id,
                        task_name=task_name,
                        task_func=task_func,
                        mem=mem,
                        roster=roster if not is_infrastructure_task(task_name) else None,
                        gravity=gravity_key,
                        graph=graph,
                        phase_id=phase_id,
                    )
                    exec_result = execute_with_pattern(pattern_selection.pattern, exec_ctx)
                    success = exec_result.success
                    if not success:
                        last_error = exec_result.error
                else:
                    # Direct call (legacy path)
                    if graph is not None:
                        try:
                            sig = inspect.signature(task_func)
                            accepts_graph = "graph" in sig.parameters
                        except (ValueError, TypeError):
                            accepts_graph = False
                        if accepts_graph:
                            result = task_func(mem, graph=graph)
                        else:
                            result = task_func(mem)
                    else:
                        result = task_func(mem)
                    # Treat None as success; only explicit False is failure
                    success = result is not False

                if success:
                    break
                last_error = last_error or "returned False"

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "Task %s attempt %d failed: %s", task_id, attempt, e,
                )
                if attempt == max_attempts - 1:
                    # Final attempt — propagate as failure
                    success = False

        # Clear context vars after task execution
        try:
            from core.skills.context_formatter import set_active_skill_context
            set_active_skill_context(None)
        except Exception:
            pass
        try:
            from core.graph.context_injector import set_active_graph_context
            set_active_graph_context(None)
        except Exception:
            pass

        if success is False:
            state.mark_task_failed(phase_id, task_id, task_name, last_error)
            if last_error:
                log_error(phase_id, task_id, last_error, "")
            print(f"\n❌ Task {task_id} failed")
            clear_current_task()
            get_resolver().clear_task_overrides()
            return False

        # Collect artifacts
        artifacts = [
            str(output_dir / f)
            for f in task_artifacts.get(task_id, [])
            if (output_dir / f).exists()
        ]
        state.mark_task_complete(phase_id, task_id, task_name, artifacts=artifacts)
        get_resolver().clear_task_overrides()

        # Shadow audit (non-blocking, STANDARD/INTENSIVE only)
        if graph is not None and gravity_assessment:
            try:
                from core.shadow_agent import ShadowAgent, ShadowContext
                if ShadowAgent.should_activate(gravity_key):
                    shadow = ShadowAgent(graph=graph)
                    shadow_content = mem.build_content() if mem.has_entries() else ""
                    if shadow_content:
                        shadow_ctx = ShadowContext(
                            task_id=task_id,
                            task_name=task_name,
                            phase_id=phase_id,
                            content=shadow_content,
                            artifacts=artifacts,
                        )
                        shadow.evaluate_async(shadow_ctx)
                        logger.info("Shadow audit submitted for task %s", task_id)
            except Exception as e:
                logger.debug("Shadow audit skipped: %s", e)

        # Save task completion to memory
        try:
            if mem.has_entries():
                memory_content = mem.build_content()
                memory_metadata = mem.build_metadata()
            else:
                memory_content = enrich_memory_with_llm(
                    artifacts, task_id, task_name, output_dir=output_dir,
                )
                if not memory_content:
                    memory_content = summarize_task_artifacts(
                        artifacts, task_id, task_name, output_dir=output_dir,
                    )
                memory_metadata = {}
            memory_save(
                phase=phase_id,
                task_id=task_id,
                content=memory_content,
                tags=["task-complete", phase_id, f"task-{task_id}"],
                entry_type=MemoryEntryType.TASK_END,
                metadata=memory_metadata,
            )
        except Exception as e:
            logger.warning("Memory save failed for task %s: %s", task_id, e)

        # Post-task: log skill usage and gravity accuracy
        if gravity_assessment and skill_selection and skill_selection.skills:
            try:
                from core.skills import SkillLearning
                from core.skills.scoring import compute_task_score
                learning = SkillLearning()
                task_score = compute_task_score(
                    success=(success is not False),
                    task_id=task_id,
                    expected_artifacts=task_artifacts.get(task_id, []),
                    actual_artifacts=artifacts,
                    mem_entry_count=len(mem._entries),
                    gravity=gravity_assessment.gravity.value,
                )
                learning.log_usage(
                    task_id=task_id,
                    skill_ids=[s.id for s in skill_selection.skills],
                    success_score=task_score,
                    gravity=gravity_assessment.gravity.value,
                )
                learning.log_gravity_accuracy(
                    task_id=task_id,
                    assessed_gravity=gravity_assessment.gravity,
                    success_score=task_score,
                )
            except Exception as e:
                logger.debug("Post-task skill learning skipped: %s", e)

    # Phase complete
    clear_current_task()
    phase_complete(label)

    # Save phase closeout to memory
    try:
        memory_save(
            phase=phase_id,
            task_id=None,
            content=f"Phase {phase_id} completed. Tasks: {', '.join(t[0] for t in tasks)}",
            tags=["phase-complete", phase_id],
            entry_type=MemoryEntryType.PHASE_CLOSEOUT,
        )
    except Exception as e:
        logger.warning("Phase closeout memory save failed: %s", e)

    # Create closeout file
    try:
        create_phase_closeout(phase_id, tasks)
    except Exception as e:
        logger.warning("Closeout file creation failed: %s", e)

    return True


def create_phase_closeout(phase_id: str, tasks: List[TaskEntry],
                          output_dir: Optional[Path] = None) -> None:
    """
    Create standardized closeout.json for a completed phase.

    Args:
        phase_id: Phase identifier (e.g., "1-discovery")
        tasks: List of (task_id, task_name, task_func) tuples
        output_dir: Phase output directory (defaults to ATOMIC_ROOT/.outputs/<phase_id>)
    """
    if output_dir is None:
        atomic_root = Path(os.environ.get("ATOMIC_ROOT", Path.cwd()))
        output_dir = atomic_root / ".outputs" / phase_id
    output_dir.mkdir(parents=True, exist_ok=True)

    phase_num = int(phase_id.split("-")[0])
    phase_name = phase_id.split("-", 1)[1].replace("_", " ").title()

    closeout_data = {
        "phase": phase_id,
        "phase_num": phase_num,
        "status": "complete",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "tasks_completed": [task_id for task_id, _, _ in tasks],
        "summary": f"Phase {phase_num} ({phase_name}) completed successfully.",
    }

    closeout_file = output_dir / "closeout.json"
    fd, tmp_path = tempfile.mkstemp(dir=str(closeout_file.parent), suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(closeout_data, f, indent=2, default=str)
        os.replace(tmp_path, str(closeout_file))
    except Exception:
        os.unlink(tmp_path)
        raise
    print(f"\n✅ Phase {phase_num} closeout: {closeout_file}")
