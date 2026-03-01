"""
Task 403: OpenSpec Generation

Generate OpenSpec specification files for each task using parallel LLM analysis.
Each spec defines test strategy, interfaces, edge cases, and security requirements.

Uses ThreadPoolExecutor for concurrent spec generation with Rich live progress.
"""

import json
import logging
import re
import sys
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
    print_red, print_dim
)
from core.utils.file_ops import ensure_dir, read_file, write_file

# Parallel execution settings
MAX_CONCURRENT = 5


def load_tasks(project_root: Path) -> List[Dict]:
    """Load tasks from tasks.json."""
    tasks_file = project_root / ".taskmaster" / "tasks" / "tasks.json"
    if not tasks_file.exists():
        return []

    try:
        data = json.loads(read_file(tasks_file))
        return data.get("tasks", [])
    except (json.JSONDecodeError, Exception):
        return []


def generate_stub_spec(task: Dict) -> Dict:
    """Generate a stub OpenSpec as a fallback when LLM is unavailable."""
    task_id = task.get("id", 0)
    task_title = task.get("title", f"Task {task_id}")

    return {
        "spec_id": f"SPEC-T{task_id}",
        "task_id": task_id,
        "task_title": task_title,
        "stub_mode": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "test_strategy": {
            "unit_tests": [
                {"name": f"test_t{task_id}_basic", "description": f"Basic test for {task_title}"}
            ],
            "integration_tests": [],
            "scenarios": [
                {
                    "given": "System is initialized",
                    "when": f"Task {task_id} executes",
                    "then": "Expected outcome is achieved"
                }
            ]
        },
        "interfaces": {
            "inputs": [{"name": "config", "type": "dict", "required": True}],
            "outputs": [{"name": "result", "type": "bool"}],
            "errors": [{"code": f"ERR_T{task_id}_001", "condition": "Invalid input"}]
        },
        "edge_cases": [
            {"scenario": "Missing input", "expected_behavior": "Return error gracefully"}
        ],
        "security_requirements": [
            {"requirement": "Validate all inputs", "validation": "Schema check"}
        ]
    }


def _load_project_context(atomic_root: Path) -> str:
    """Load project context for LLM prompts to prevent framework confusion."""
    project_root = atomic_root.parent
    context_parts = []

    # Load project config (name, description, type) from Phase 0
    config_file = project_root / ".outputs" / "0-setup" / "project-config.json"
    if config_file.exists():
        try:
            cfg = json.loads(read_file(config_file))
            project = cfg.get("project", {})
            pname = project.get("name", "")
            pdesc = project.get("description", "")
            ptype = project.get("type", "")
            if pname:
                context_parts.append(f"**Project:** {pname}")
            if pdesc:
                context_parts.append(f"**Description:** {pdesc}")
            if ptype:
                context_parts.append(f"**Type:** {ptype}")
            constraints = cfg.get("constraints", {})
            tech = constraints.get("technical", [])
            if tech:
                context_parts.append(f"**Technical Constraints:** {', '.join(str(c) for c in tech[:10])}")
        except Exception as e:
            logger.debug("Could not load project config: %s", e)

    # Load corpus analysis (detailed analysis from Phase 1)
    analysis_file = project_root / ".outputs" / "1-discovery" / "corpus-analysis.md"
    if analysis_file.exists():
        try:
            analysis = read_file(analysis_file).strip()
            if analysis:
                context_parts.append(f"\n**Corpus Analysis:**\n{analysis}")
        except Exception as e:
            logger.debug("Could not load corpus analysis: %s", e)

    # Load PRD content for specification grounding
    prd_file = project_root / "docs" / "prd" / "PRD.md"
    if prd_file.exists():
        try:
            prd_content = read_file(prd_file).strip()
            if prd_content:
                context_parts.append(f"\n**PRD (Product Requirements Document):**\n{prd_content}")
        except Exception as e:
            logger.debug("Could not load PRD content: %s", e)

    # Load task dependency info from tasks.json
    tasks_file = project_root / ".taskmaster" / "tasks" / "tasks.json"
    if tasks_file.exists():
        try:
            tasks_data = json.loads(read_file(tasks_file))
            tasks_list = tasks_data.get("tasks", [])
            if tasks_list:
                dep_summary = []
                for t in tasks_list:
                    tid = t.get("id", "?")
                    title = t.get("title", "")
                    deps = t.get("dependencies", [])
                    dep_summary.append(f"  T{tid}: {title} (depends on: {deps})")
                context_parts.append(f"\n**Task Dependencies:**\n" + "\n".join(dep_summary))
        except Exception as e:
            logger.debug("Could not load task dependencies: %s", e)

    return "\n".join(context_parts) if context_parts else "No project context available."


def _extract_canonical_layout(atomic_root: Path) -> str:
    """Extract the canonical project layout (Section 7) from the approved PRD."""
    project_root = atomic_root.parent
    prd_file = project_root / "docs" / "prd" / "PRD.md"
    if not prd_file.exists():
        # Try prd-approved.json pointer
        approved = project_root / ".outputs" / "2-prd" / "prd-approved.json"
        if approved.exists():
            try:
                data = json.loads(read_file(approved))
                prd_path = data.get("prd_file", "")
                if prd_path:
                    prd_file = Path(prd_path)
            except Exception as e:
                logger.debug("Could not read prd-approved.json: %s", e)

    if not prd_file.exists():
        return ""

    try:
        content = read_file(prd_file)
        match = re.search(r'^#{1,2} 7\. Code (Structure|Organization)(.+?)^#{1,2} 8\.',
                         content, re.MULTILINE | re.DOTALL)
        if match:
            layout = match.group(2).strip()
            return layout[:5000] if len(layout) > 5000 else layout
    except Exception as e:
        logger.debug("Could not extract canonical layout from PRD: %s", e)
    return ""


def _build_spec_prompt(task: Dict, project_context: str, canonical_layout: str = "") -> str:
    """Build the OpenSpec generation prompt for a single task."""
    task_id = task.get("id", 0)
    task_title = task.get("title", f"Task {task_id}")
    task_desc = task.get("description", "")
    acceptance = task.get("acceptance_criteria", "")

    layout_section = ""
    if canonical_layout:
        layout_section = f"""
## Canonical Project Layout

This project uses the following structure (from PRD Section 7).
ALL file paths, module references, and import paths in your spec MUST align with this layout:

{canonical_layout}

"""

    return f"""Generate an OpenSpec specification for the following task.
IMPORTANT: This is for the user's project described below, NOT for the development tool/framework.

## Project Context
{project_context}
{layout_section}
## Task to Specify

Task ID: {task_id}
Title: {task_title}
Description: {task_desc}
Acceptance Criteria: {acceptance}

## Output Format

Generate a JSON specification with the following structure:
{{
    "spec_id": "SPEC-T{task_id}",
    "task_id": {task_id},
    "task_title": {json.dumps(task_title)},
    "test_strategy": {{
        "unit_tests": [...],
        "integration_tests": [...],
        "scenarios": [{{ "given": "...", "when": "...", "then": "..." }}]
    }},
    "interfaces": {{
        "inputs": [...],
        "outputs": [...],
        "errors": [...]
    }},
    "edge_cases": [...],
    "security_requirements": [...]
}}

Return ONLY valid JSON."""


def _spec_worker(
    task: Dict,
    project_context: str,
    openspec_dir: Path,
    invoke_llm,
    canonical_layout: str = "",
) -> tuple[int, str, float, Optional[str]]:
    """Generate spec for a single task. Runs in thread pool. Never raises.

    Returns (task_id, status, duration_seconds, error_or_None).
    """
    task_id = task.get("id", 0)
    start = time.monotonic()
    spec_file = openspec_dir / f"spec-t{task_id}.json"

    try:
        prompt = _build_spec_prompt(task, project_context, canonical_layout)
        invoke_llm(
            prompt=prompt,
            output_file=str(spec_file),
            model="opus",
            timeout=600,
        )

        # Validate the written file is valid JSON
        if spec_file.exists():
            raw = read_file(spec_file).strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                try:
                    first_nl = raw.index("\n")
                except ValueError:
                    first_nl = len(raw)
                raw = raw[first_nl + 1:]
                if raw.endswith("```"):
                    raw = raw[:-3].strip()
            try:
                json.loads(raw)
            except (json.JSONDecodeError, ValueError) as je:
                logger.warning(
                    "Spec file spec-t%s.json is not valid JSON: %s", task_id, je
                )
                spec_file.unlink(missing_ok=True)
                return (task_id, "invalid", time.monotonic() - start, str(je))

        return (task_id, "ok", time.monotonic() - start, None)
    except Exception as e:
        # Fallback to stub spec
        spec = generate_stub_spec(task)
        write_file(spec_file, json.dumps(spec, indent=2))
        return (task_id, "stub", time.monotonic() - start, str(e))


def _run_parallel_specs(
    tasks: List[Dict],
    project_context: str,
    openspec_dir: Path,
    invoke_llm,
    canonical_layout: str = "",
) -> tuple[int, int]:
    """Run spec generation in parallel with Rich live progress.

    Returns (generated_count, failed_count).
    """
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel

    console = Console()
    total = len(tasks)
    results: list[Optional[tuple]] = [None] * total

    STATUS_ICON = {"ok": "✅", "stub": "⚠️ "}

    def _build_display() -> Panel:
        completed = sum(1 for r in results if r is not None)
        ok_count = sum(1 for r in results if r and r[1] == "ok")
        stub_count = sum(1 for r in results if r and r[1] == "stub")

        pct = int(completed / total * 100) if total else 100
        bar_filled = int(pct / 100 * 30)
        bar = "█" * bar_filled + "░" * (30 - bar_filled)

        lines = [""]
        if completed < total:
            lines.append(f"  {completed}/{total} complete   "
                         f"{ok_count} generated   {stub_count} fallback stubs")
            lines.append(f"  ⠸ Generating {bar} {pct}%")
        else:
            lines.append(f"  {completed}/{total} complete   "
                         f"{ok_count} generated   {stub_count} fallback stubs")
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
                time_str = f"{r[2]:.1f}s"
                lines.append(
                    f"  {i+1:>4}  {icon:<8} T{tid:>4}  {title:<50} {time_str:>8}"
                )
            else:
                lines.append(
                    f"  {i+1:>4}  {'...':<8} T{tid:>4}  {title:<50}"
                )

        lines.append("")
        return Panel("\n".join(lines), title="OpenSpec Generation (opus, parallel)")

    with Live(_build_display(), console=console, refresh_per_second=2) as live:
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as executor:
            future_to_idx = {}
            for i, task in enumerate(tasks):
                future = executor.submit(
                    _spec_worker, task, project_context, openspec_dir, invoke_llm,
                    canonical_layout,
                )
                future_to_idx[future] = i

            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                results[idx] = future.result()
                live.update(_build_display())

    generated = sum(1 for r in results if r is not None and r[1] not in ("stub", "invalid"))
    failed = sum(1 for r in results if r and r[1] in ("stub", "invalid"))
    return generated, failed


def execute(atomic_root: Path, output_dir: Path, mem=None, graph=None) -> bool:
    """
    Execute Task 403: OpenSpec Generation.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        graph: Optional GraphManager instance for knowledge graph operations

    Returns:
        True if task completed successfully, False otherwise
    """
    # Determine project root (parent of atomic_root)
    project_root = atomic_root.parent
    openspec_dir = project_root / ".openspec"

    print()
    print(print_dim("  Generating OpenSpec specifications for each task."))
    print()

    # Ensure output directories exist
    ensure_dir(output_dir)
    ensure_dir(openspec_dir)

    # Load tasks
    tasks = load_tasks(project_root)

    if not tasks:
        print(print_yellow("  ! No tasks found in .taskmaster/tasks/tasks.json"))
        # Write empty generation report
        report = {
            "status": "complete",
            "specs_generated": 0,
            "mode": "normal",
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        write_file(output_dir / "openspec-generation.json", json.dumps(report, indent=2))
        return True

    # Use LLM to generate specs in parallel
    print(print_bold("  OPENSPEC GENERATION"))
    print()
    print(print_dim(f"  Generating specifications for {len(tasks)} tasks "
                    f"({MAX_CONCURRENT} parallel workers, opus)..."))
    print()

    # Load project context for LLM prompts
    project_context = _load_project_context(atomic_root)

    # Extract canonical layout from PRD Section 7 for path consistency
    canonical_layout = _extract_canonical_layout(atomic_root)
    if canonical_layout:
        print(print_green("  ✓ Canonical project layout extracted from PRD Section 7"))

    try:
        from core.llm.invoke import invoke_llm

        # Warmup: force router initialization on the main thread before
        # spawning parallel workers (prevents TOCTOU race on singleton init).
        try:
            invoke_llm(prompt="Reply with OK", model="haiku", timeout=30)
        except Exception:
            pass  # Warmup failure is non-fatal; workers will retry

        generated, failed = _run_parallel_specs(
            tasks, project_context, openspec_dir, invoke_llm, canonical_layout
        )

        # Write generated specs to knowledge graph
        if graph:
            graph_written = 0
            for task in tasks:
                task_id = task.get("id", 0)
                spec_file = openspec_dir / f"spec-t{task_id}.json"
                if spec_file.exists():
                    try:
                        raw = read_file(spec_file).strip()
                        # Handle markdown-fenced JSON
                        if raw.startswith("```"):
                            first_nl = raw.index("\n")
                            raw = raw[first_nl + 1:]
                            if raw.endswith("```"):
                                raw = raw[:-3].strip()
                        spec_data = json.loads(raw)
                        graph.add_spec(task_id=task_id, spec_data=spec_data)
                        graph_written += 1
                    except Exception as e:
                        logger.warning("Graph spec write failed for T%s: %s", task_id, e)
            if graph_written > 0:
                print(print_green(f"  ✓ {graph_written} specs written to knowledge graph"))

        # Write generation report
        report = {
            "status": "complete",
            "specs_generated": generated,
            "specs_failed": failed,
            "mode": "parallel",
            "concurrency": MAX_CONCURRENT,
            "model": "opus",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "specs": [f"spec-t{t.get('id', 0)}.json" for t in tasks]
        }
        write_file(output_dir / "openspec-generation.json", json.dumps(report, indent=2))

        print()
        print(print_green(f"  OpenSpec generation complete: "
                          f"{generated}/{len(tasks)} specs created, {failed} failed"))
        return True

    except ImportError:
        print(print_yellow("  ! LLM module not available, falling back to stub specs"))
        for task in tasks:
            task_id = task.get("id", 0)
            spec = generate_stub_spec(task)
            spec_file = openspec_dir / f"spec-t{task_id}.json"
            write_file(spec_file, json.dumps(spec, indent=2))

        report = {
            "status": "complete",
            "specs_generated": len(tasks),
            "mode": "stub-fallback",
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        write_file(output_dir / "openspec-generation.json", json.dumps(report, indent=2))

        print(print_green(f"  OpenSpec generation complete: {len(tasks)} stub specs created"))
        return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 403: OpenSpec Generation")
    parser.add_argument('--atomic-root', type=Path, required=True,
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir)
    sys.exit(0 if success else 1)
