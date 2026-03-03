"""
Task 404: TDD Subtask Injection (LLM-Enriched)

Reads each task's OpenSpec (spec-tN.json) and uses the LLM to generate
task-specific RED/GREEN/REFACTOR/VERIFY subtasks with concrete test names,
file paths, assertions, and acceptance criteria derived from the spec.

Uses ThreadPoolExecutor for concurrent generation with Rich live progress
(mirrors task 403's _spec_worker + _run_parallel_specs pattern).
"""

import copy
import json
import logging
import os
import re
import sys
import shutil
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user, clear_input_buffer
)
from core.utils.file_ops import ensure_dir, read_file, write_file

# Parallel execution settings
MAX_CONCURRENT = 5
SPEC_TRUNCATE_CHARS = 50_000


def create_generic_subtasks(task_id: int) -> List[Dict]:
    """Create generic TDD subtasks (fallback when LLM/spec unavailable)."""
    return [
        {
            "id": 1,
            "title": f"RED: Write failing tests for T{task_id}",
            "phase": "RED",
            "status": "pending",
            "dependencies": [],
            "description": "Write unit tests and/or integration tests based on the OpenSpec. Tests must fail initially (no implementation yet).",
            "acceptance_criteria": "Tests exist and FAIL when run",
            "spec_references": []
        },
        {
            "id": 2,
            "title": f"GREEN: Implement T{task_id} to pass tests",
            "phase": "GREEN",
            "status": "pending",
            "dependencies": [1],
            "description": "Write the minimal implementation code to make all tests pass. Focus on correctness, not optimization.",
            "acceptance_criteria": "All tests PASS",
            "spec_references": []
        },
        {
            "id": 3,
            "title": f"REFACTOR: Clean up T{task_id} code",
            "phase": "REFACTOR",
            "status": "pending",
            "dependencies": [2],
            "description": "Refactor the code for clarity, maintainability, and style compliance. Run linters. Ensure tests still pass.",
            "acceptance_criteria": "Linting passes, tests still PASS",
            "spec_references": []
        },
        {
            "id": 4,
            "title": f"VERIFY: Security scan T{task_id}",
            "phase": "VERIFY",
            "status": "pending",
            "dependencies": [3],
            "description": "Run security scanners. Address any critical or high severity issues.",
            "acceptance_criteria": "No critical or high security issues",
            "spec_references": []
        }
    ]


def _load_openspec(task_id: int, openspec_dir: Path) -> Optional[Dict]:
    """Load spec-tN.json for a task. Returns parsed dict or None.

    Handles raw JSON and markdown-fenced JSON (```json ... ```) since
    task 403 writes raw LLM output which often includes code fences.
    """
    spec_file = openspec_dir / f"spec-t{task_id}.json"
    if not spec_file.exists():
        return None
    try:
        content = read_file(spec_file).strip()
        # Try direct parse first
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.debug("Direct JSON parse failed for spec-t%s.json: %s", task_id, e)
        # Strip markdown code fences
        fenced = _extract_json_block(content)
        if fenced:
            try:
                return json.loads(fenced)
            except json.JSONDecodeError as e:
                logger.debug("Fenced JSON parse failed for spec-t%s.json: %s", task_id, e)
        # Last resort: use JSONDecoder to find first valid JSON object
        decoder = json.JSONDecoder()
        idx = content.find('{')
        while idx != -1:
            try:
                parsed, _ = decoder.raw_decode(content, idx)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
            idx = content.find('{', idx + 1)
        return None
    except Exception as e:
        logger.debug("Could not load openspec for task %s: %s", task_id, e)
        return None


def _build_tdd_prompt(task: Dict, spec: Dict) -> str:
    """Build the LLM prompt with task context + full OpenSpec."""
    task_id = task.get("id", 0)
    task_title = task.get("title", f"Task {task_id}")
    task_desc = task.get("description", "")
    acceptance = task.get("acceptance_criteria", "")

    spec_json = json.dumps(spec, indent=2)
    if len(spec_json) > SPEC_TRUNCATE_CHARS:
        spec_json = spec_json[:SPEC_TRUNCATE_CHARS] + "\n... [truncated]"

    return f"""You are generating TDD subtasks for a software development task. You have the task's
OpenSpec specification which contains detailed test strategies, interfaces, edge cases,
and security requirements.

## Task
ID: {task_id}
Title: {task_title}
Description: {task_desc}
Acceptance Criteria: {acceptance}

## OpenSpec (spec-t{task_id}.json)
{spec_json}

## Instructions

Generate exactly 4 TDD subtasks as a JSON array. Each subtask must be SPECIFIC to this
task — reference actual test IDs, file paths, module names, and assertions from the spec.

### Subtask 1: RED (Write Failing Tests)
- Reference specific unit test IDs (UT-xxx) and integration test IDs (IT-xxx) from the spec
- Name specific test files to create and test functions to write
- Include edge cases (EDGE-xxx) that must be covered
- Acceptance: tests exist AND fail (no implementation yet)

### Subtask 2: GREEN (Minimal Implementation)
- Reference the functional requirements and interfaces from the spec
- Name specific source files, modules, structs/classes to create
- Describe the minimal code to make all RED tests pass
- Acceptance: all tests pass

### Subtask 3: REFACTOR (Code Quality)
- Reference coding standards relevant to this task's language/framework
- Identify specific areas to clean up based on the spec's implementation notes
- Acceptance: linting passes, tests still pass, code meets project style

### Subtask 4: VERIFY (Security & Compliance)
- Reference specific security requirements from the spec
- Name specific security tools to run for this task's tech stack
- Include any compliance checks from the spec
- Acceptance: no critical/high security issues

Return ONLY a JSON array of 4 objects with these fields:
- id (1-4)
- title (string, format: "PHASE: Description for T{task_id}")
- phase ("RED" | "GREEN" | "REFACTOR" | "VERIFY")
- status ("pending")
- dependencies (array: [] for RED, [1] for GREEN, [2] for REFACTOR, [3] for VERIFY)
- description (string, 3-8 sentences, SPECIFIC to this task)
- acceptance_criteria (string, 2-4 specific criteria from the spec)
- spec_references (array of spec IDs referenced: UT-xxx, IT-xxx, EDGE-xxx, etc.)"""


def _parse_tdd_response(response: str, task_id: int) -> Optional[List[Dict]]:
    """Extract and validate the JSON subtask array from LLM response.

    Tries multiple extraction strategies. Returns list of 4 subtask dicts
    or None on failure.
    """
    # Strategy 1: raw JSON parse (response is just the array)
    text = response.strip()
    for candidate in [text, _extract_json_block(text)]:
        if candidate is None:
            continue
        try:
            parsed = json.loads(candidate)
            parsed = copy.deepcopy(parsed)
            if _validate_subtasks(parsed, task_id):
                return parsed
        except (json.JSONDecodeError, ValueError):
            continue

    # Strategy 2: use json.JSONDecoder to find the first valid JSON array
    decoder = json.JSONDecoder()
    idx = text.find('[')
    while idx != -1:
        try:
            parsed, end_idx = decoder.raw_decode(text, idx)
            parsed = copy.deepcopy(parsed)
            if isinstance(parsed, list) and _validate_subtasks(parsed, task_id):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass
        # Try next '[' occurrence
        idx = text.find('[', idx + 1)

    return None


def _extract_json_block(text: str) -> Optional[str]:
    """Extract content from ```json ... ``` fenced block."""
    match = re.search(r'```(?:json)?\s*\n([\s\S]*?)\n```', text)
    return match.group(1).strip() if match else None


def _validate_subtasks(parsed, task_id: int) -> bool:
    """Check that parsed value is a list of 4 subtask dicts with required fields.

    Note: This function may add missing 'spec_references' keys to items.
    Callers should pass a deep copy if mutation of the original is undesirable.
    """
    if not isinstance(parsed, list) or len(parsed) != 4:
        return False

    required_fields = {"id", "title", "phase", "status", "dependencies", "description", "acceptance_criteria"}
    expected_phases = ["RED", "GREEN", "REFACTOR", "VERIFY"]

    for i, st in enumerate(parsed):
        if not isinstance(st, dict):
            return False
        if not required_fields.issubset(st.keys()):
            return False
        if st.get("phase") != expected_phases[i]:
            return False
        # Ensure spec_references exists (add empty if missing)
        if "spec_references" not in st:
            st["spec_references"] = []

    return True


def _tdd_worker(
    task: Dict,
    openspec_dir: Path,
    invoke_llm,
) -> tuple:
    """Generate TDD subtasks for a single task. Runs in thread pool. Never raises.

    Returns (task_id, status, subtasks, duration_seconds, error_or_None).
    Status: "ok" | "parsed" | "fallback" | "no-spec"
    """
    task_id = task.get("id", 0)
    start = time.monotonic()

    # Load OpenSpec
    spec = _load_openspec(task_id, openspec_dir)
    if spec is None:
        subtasks = create_generic_subtasks(task_id)
        return (task_id, "no-spec", subtasks, time.monotonic() - start, None)

    try:
        prompt = _build_tdd_prompt(task, spec)
        response = invoke_llm(
            prompt=prompt,
            model="opus",
            timeout=600,
        )
        # response may be str or LLMResponse
        if hasattr(response, 'content'):
            response_text = response.content
        else:
            response_text = str(response)

        subtasks = _parse_tdd_response(response_text, task_id)
        if subtasks is not None:
            return (task_id, "ok", subtasks, time.monotonic() - start, None)

        # Parse failed — fallback
        subtasks = create_generic_subtasks(task_id)
        return (task_id, "fallback", subtasks, time.monotonic() - start,
                "JSON parse failed")

    except Exception as e:
        subtasks = create_generic_subtasks(task_id)
        return (task_id, "fallback", subtasks, time.monotonic() - start, str(e))


def _run_parallel_tdd(
    tasks: List[Dict],
    openspec_dir: Path,
    invoke_llm,
) -> List[tuple]:
    """Run TDD subtask generation in parallel with Rich live progress.

    Returns list of (task_id, status, subtasks, duration, error) tuples.
    """
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel

    console = Console()
    total = len(tasks)
    results: list[Optional[tuple]] = [None] * total

    STATUS_ICON = {"ok": "✅", "parsed": "✅", "fallback": "⚠️ ", "no-spec": "📭"}

    def _build_display() -> Panel:
        completed = sum(1 for r in results if r is not None)
        ok_count = sum(1 for r in results if r and r[1] in ("ok", "parsed"))
        fallback_count = sum(1 for r in results if r and r[1] == "fallback")
        nospec_count = sum(1 for r in results if r and r[1] == "no-spec")

        pct = int(completed / total * 100) if total else 100
        bar_filled = int(pct / 100 * 30)
        bar = "█" * bar_filled + "░" * (30 - bar_filled)

        lines = [""]
        if completed < total:
            lines.append(f"  {completed}/{total} complete   "
                         f"{ok_count} spec-aware   {fallback_count} fallback   "
                         f"{nospec_count} no-spec")
            lines.append(f"  ⠸ Generating {bar} {pct}%")
        else:
            lines.append(f"  {completed}/{total} complete   "
                         f"{ok_count} spec-aware   {fallback_count} fallback   "
                         f"{nospec_count} no-spec")
            lines.append(f"  ✓ Complete {bar} {pct}%")
        lines.append("")

        lines.append(
            f"  {'#':>4}  {'Status':<8} {'Task':>5}  {'Title':<50} {'Time':>8}"
        )

        for i, task in enumerate(tasks):
            tid = task.get("id", 0)
            title = task.get("title", f"Task {tid}")
            if len(title) > 49:
                title = title[:47] + "…"

            r = results[i]
            if r is not None:
                icon = STATUS_ICON.get(r[1], "?")
                time_str = f"{r[3]:.1f}s"
                lines.append(
                    f"  {i+1:>4}  {icon:<8} T{tid:>4}  {title:<50} {time_str:>8}"
                )
            else:
                lines.append(
                    f"  {i+1:>4}  {'...':<8} T{tid:>4}  {title:<50}"
                )

        lines.append("")
        return Panel("\n".join(lines), title="TDD Subtask Generation (opus, parallel)")

    with Live(_build_display(), console=console, refresh_per_second=2) as live:
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as executor:
            future_to_idx = {}
            for i, task in enumerate(tasks):
                future = executor.submit(
                    _tdd_worker, task, openspec_dir, invoke_llm
                )
                future_to_idx[future] = i

            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                results[idx] = future.result()
                live.update(_build_display())

    return [r for r in results if r is not None]


def execute(atomic_root: Path, output_dir: Path, mem=None, graph=None) -> bool:
    """
    Execute Task 404: TDD Subtask Injection.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        graph: Optional GraphManager instance for knowledge graph operations

    Returns:
        True if task completed successfully, False otherwise
    """
    project_root = atomic_root.parent
    tasks_file = project_root / ".taskmaster" / "tasks" / "tasks.json"
    backup_file = project_root / ".taskmaster" / "tasks" / "tasks.json.pre-tdd-backup"
    openspec_dir = project_root / ".openspec"
    injection_report = output_dir / "tdd-injection.json"

    ensure_dir(output_dir)

    print()
    print(print_dim("  Injecting TDD subtasks (RED/GREEN/REFACTOR/VERIFY) into tasks.json."))
    print()

    # Validate tasks.json exists
    if not tasks_file.exists():
        print(print_red("✗ tasks.json not found"))
        return False

    # Pre-injection backup
    print(print_dim("─" * 109))
    print()
    print(print_bold("PRE-INJECTION BACKUP"))
    print()

    # Validate JSON before making backup (avoid backing up corrupt data)
    try:
        tasks_data = json.loads(read_file(tasks_file))
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Cannot parse %s: %s — aborting TDD injection", tasks_file, e)
        print(print_red(f"✗ tasks.json is corrupt or unreadable: {e}"))
        return False
    shutil.copy(tasks_file, backup_file)
    print(print_green("  ✓ Backed up tasks.json → tasks.json.pre-tdd-backup"))
    print()

    # Load tasks (already parsed above)
    tasks = tasks_data.get("tasks", [])
    total_tasks = len(tasks)

    if total_tasks == 0:
        print(print_yellow("  ! No tasks found in tasks.json"))
        write_file(injection_report, json.dumps({
            "injection_mode": "llm-enriched",
            "tasks_injected": 0,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }, indent=2))
        return True

    # Handle existing subtasks
    tasks_with_subtasks = len([t for t in tasks if len(t.get("subtasks", [])) > 0])

    print(print_dim("─" * 109))
    print()
    print(print_bold("INJECTION MODE"))
    print()
    print(print_dim("  Current state:"))
    print(f"    Tasks with subtasks: {tasks_with_subtasks} / {total_tasks}")
    print()

    inject_mode = "inject"

    if tasks_with_subtasks > 0:
        print(print_yellow("  ! Some tasks already have subtasks."))
        print()
        print(print_cyan("Options:"))
        print()
        print(print_green("  [skip]       Skip tasks that already have subtasks"))
        print(print_yellow("  [replace]   Replace existing subtasks"))
        print(print_red("  [abort]     Abort and review manually"))
        print()

        clear_input_buffer()
        inject_mode = prompt_user("  Choice (default: skip): ").strip().lower() or "skip"

        if inject_mode == "abort":
            print(print_red("✗ Aborted by user"))
            return False

    # Filter tasks to process
    if inject_mode == "skip":
        tasks_to_process = [t for t in tasks if len(t.get("subtasks", [])) == 0]
    else:
        tasks_to_process = list(tasks)

    if not tasks_to_process:
        print(print_yellow("  ! All tasks already have subtasks, nothing to inject"))
        write_file(injection_report, json.dumps({
            "injection_mode": "llm-enriched",
            "model": "opus",
            "tasks_injected": 0,
            "tasks_skipped": total_tasks,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }, indent=2))
        return True

    # Check OpenSpec availability (supplement from graph if available)
    if graph:
        for t in tasks_to_process:
            task_id = t.get("id", 0)
            spec_file = openspec_dir / f"spec-t{task_id}.json"
            if not spec_file.exists():
                try:
                    get_node = getattr(graph, 'get_node', None) or graph.reader.get_node
                    spec_node = get_node("Spec", task_id)
                    if spec_node:
                        logger.info("Loaded spec for T%s from graph", task_id)
                        write_file(spec_file, json.dumps(spec_node, indent=2))
                except Exception as e:
                    logger.warning("Graph spec query failed for T%s: %s", task_id, e)

    spec_count = sum(1 for t in tasks_to_process
                     if (openspec_dir / f"spec-t{t.get('id', 0)}.json").exists())

    print()
    print(print_dim("─" * 109))
    print()
    print(print_bold("LLM-ENRICHED TDD SUBTASK GENERATION"))
    print()
    print(print_dim(f"  Tasks to process: {len(tasks_to_process)}"))
    print(print_dim(f"  OpenSpecs available: {spec_count}/{len(tasks_to_process)}"))
    print(print_dim(f"  Model: opus  |  Workers: {MAX_CONCURRENT}  |  Timeout: 600s/task"))
    print()

    prompt_user("  Press Enter to begin generation...")
    print()

    # Run parallel LLM generation
    try:
        from core.llm.invoke import invoke_llm

        # Warm up the LLM router singleton on the main thread.
        # _get_default_router() has a race condition: it sets the global
        # before registering providers, so threads see an empty router.
        # A single main-thread call forces full initialization.
        print(print_dim("  Warming up LLM provider..."))
        invoke_llm(prompt="Reply with OK", model="haiku", timeout=30)
        print(print_green("  ✓ LLM provider ready"))
        print()

        gen_start = time.monotonic()
        results = _run_parallel_tdd(tasks_to_process, openspec_dir, invoke_llm)
        gen_duration = time.monotonic() - gen_start

    except ImportError:
        print(print_yellow("  ! LLM module not available, using generic subtasks"))
        results = []
        gen_start = time.monotonic()
        for task in tasks_to_process:
            tid = task.get("id", 0)
            subtasks = create_generic_subtasks(tid)
            results.append((tid, "fallback", subtasks, 0.0, "LLM unavailable"))
        gen_duration = time.monotonic() - gen_start

    # Apply subtasks to tasks
    result_map = {r[0]: r for r in results}
    for task in tasks:
        tid = task.get("id", 0)
        if tid in result_map:
            task["subtasks"] = result_map[tid][2]

    # Write updated tasks (atomic: temp file + os.replace to avoid corruption on crash)
    tasks_dir = tasks_file.parent
    fd, tmp_path = tempfile.mkstemp(dir=tasks_dir, suffix=".tmp", prefix="tasks_")
    try:
        with os.fdopen(fd, 'w') as tmp_f:
            tmp_f.write(json.dumps(tasks_data, indent=2))
        os.replace(tmp_path, tasks_file)
    except Exception:
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except OSError:
            logger.debug("Failed to clean up temp file: %s", tmp_path)
        raise

    # Compute stats
    ok_count = sum(1 for r in results if r[1] in ("ok", "parsed"))
    fallback_count = sum(1 for r in results if r[1] == "fallback")
    nospec_count = sum(1 for r in results if r[1] == "no-spec")
    skipped_count = total_tasks - len(tasks_to_process)
    total_subtasks = len(results) * 4
    durations = [r[3] for r in results]
    avg_duration = sum(durations) / len(durations) if durations else 0

    print()
    print(print_dim("─" * 109))
    print()
    print(print_bold("INJECTION SUMMARY"))
    print()
    print(print_green(f"    Tasks injected:     {len(results)}"))
    print(print_green(f"      Spec-aware (LLM): {ok_count}"))
    print(print_yellow(f"      Fallback:         {fallback_count}"))
    print(print_dim(f"      No spec:          {nospec_count}"))
    if skipped_count > 0:
        print(print_dim(f"    Tasks skipped:      {skipped_count}"))
    print()
    print(print_bold(f"    Total subtasks created: {total_subtasks}"))
    print(print_dim(f"    Avg generation time:    {avg_duration:.1f}s"))
    print(print_dim(f"    Total wall time:        {gen_duration:.1f}s"))
    print()

    # Verify
    tasks_data = json.loads(read_file(tasks_file))
    tasks = tasks_data.get("tasks", [])
    final_with_subtasks = len([t for t in tasks if len(t.get("subtasks", [])) >= 4])

    print(print_dim("  Verification:"))
    print(f"    Tasks with TDD subtasks: {final_with_subtasks} / {total_tasks}")
    print()

    # Sample output
    print(print_dim("─" * 109))
    print()
    print(print_bold("SAMPLE TASK STRUCTURE"))
    print()

    # Show a spec-aware sample if available
    sample_task = None
    for r in results:
        if r[1] in ("ok", "parsed"):
            for t in tasks:
                if t.get("id") == r[0]:
                    sample_task = t
                    break
            if sample_task:
                break
    if sample_task is None and tasks:
        sample_task = tasks[0]

    if sample_task:
        sample_output = {
            "id": sample_task.get("id"),
            "title": sample_task.get("title"),
            "subtasks": [
                {
                    "id": st.get("id"),
                    "title": st.get("title"),
                    "phase": st.get("phase"),
                    "dependencies": st.get("dependencies"),
                    "spec_references": st.get("spec_references", []),
                    "description": st.get("description", "")[:120] + "..."
                        if len(st.get("description", "")) > 120
                        else st.get("description", "")
                }
                for st in sample_task.get("subtasks", [])
            ]
        }
        print(json.dumps(sample_output, indent=2))
    print()

    # Save injection report
    per_task = [
        {
            "task_id": r[0],
            "status": r[1],
            "duration_s": round(r[3], 1),
            **({"error": r[4]} if r[4] else {})
        }
        for r in results
    ]

    injection_data = {
        "injection_mode": "llm-enriched",
        "model": "opus",
        "tasks_injected": len(results),
        "spec_aware": ok_count,
        "fallback": fallback_count,
        "no_spec": nospec_count,
        "tasks_skipped": skipped_count,
        "total_subtasks_created": total_subtasks,
        "avg_generation_time_s": round(avg_duration, 1),
        "total_wall_time_s": round(gen_duration, 1),
        "backup_file": "tasks.json.pre-tdd-backup",
        "per_task": per_task,
        "completed_at": datetime.now(timezone.utc).isoformat()
    }

    write_file(injection_report, json.dumps(injection_data, indent=2))

    print(print_green("✓ TDD Subtask Injection complete"))

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 404: TDD Subtask Injection")
    parser.add_argument('--atomic-root', type=Path, required=True,
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir)
    sys.exit(0 if success else 1)
