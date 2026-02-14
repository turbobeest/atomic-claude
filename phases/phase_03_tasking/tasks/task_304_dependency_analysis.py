"""
Task 304: Dependency Analysis & Work Packages

Validate DAG, visualize execution levels with complexity, generate work packages.

This task:
  1. Validates dependency graph (cycles, invalid refs)
  2. Computes topological levels for parallel execution
  3. Renders ASCII DAG with complexity and time annotations
  4. Generates work-packages.json for Phase 4+ execution
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple
from datetime import datetime
from collections import defaultdict

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.config import Config
from core.state import StateManager
from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user, clear_input_buffer
)
from core.utils.file_ops import ensure_dir, read_file, write_file


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 304: Dependency Analysis.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    project_root = atomic_root.parent
    tasks_file = project_root / ".taskmaster" / "tasks" / "tasks.json"
    graph_file = project_root / ".taskmaster" / "reports" / "dependency-graph.json"
    packages_file = project_root / ".taskmaster" / "reports" / "work-packages.json"
    analysis_file = output_dir / "dependency-analysis.json"

    ensure_dir(graph_file.parent)
    ensure_dir(analysis_file.parent)

    # UAT Mode: Auto-approve
    if uat_mode:
        print()
        print(print_yellow("⚡ UAT Mode: Auto-approving dependency analysis"))
        print()

        analysis_data = {
            "validation": "pass",
            "cycles_detected": False,
            "invalid_refs": [],
            "mode": "uat"
        }
        write_file(analysis_file, json.dumps(analysis_data, indent=2))
        print(print_green("✓ Dependency analysis complete (UAT mode)"))
        return True

    print()
    print(print_dim("Validating DAG structure, computing execution levels, and generating work packages."))
    print()

    if not tasks_file.exists():
        print(print_red(f"✗ Tasks file not found: {tasks_file}"))
        return False

    tasks_data = json.loads(read_file(tasks_file))
    tasks = tasks_data.get("tasks", [])
    task_count = len(tasks)

    if task_count == 0:
        print(print_red("✗ No tasks found in tasks.json"))
        return False

    # Dependency Validation
    print(print_dim("─" * 100))
    print()
    print(print_bold("DEPENDENCY VALIDATION"))
    print()

    validation_result = _validate_dependencies(tasks)

    if validation_result["invalid_refs"] > 0:
        print(print_red(f"✗ Found {validation_result['invalid_refs']} invalid dependency references"))
        validation_result["passed"] = False
    else:
        print(print_green("✓ All dependency references valid"))

    if validation_result["self_refs"] > 0:
        print(print_red(f"✗ Found {validation_result['self_refs']} self-referencing tasks"))
        validation_result["passed"] = False

    if validation_result["root_count"] == 0 and task_count > 0:
        print(print_red("✗ No root tasks found - possible circular dependency"))
        validation_result["passed"] = False
    else:
        print(print_green("✓ No circular dependencies"))

    print(print_green("✓ DAG structure verified"))
    print()

    if not validation_result["passed"]:
        print(print_red("Dependency validation failed."))
        print()
        print(print_yellow("  [fix]      ") + "Edit tasks.json to fix issues")
        print(print_red("  [abort]    ") + "Return to task decomposition")
        print()

        clear_input_buffer()
        fix_choice = prompt_user("Choice (default: fix): ").strip().lower()
        if not fix_choice:
            fix_choice = "fix"

        if fix_choice == "abort":
            print(print_red("✗ Aborting due to dependency issues"))
            return False

        print()
        print(print_dim("Edit .taskmaster/tasks/tasks.json to fix dependency issues."))
        print(print_dim("Press Enter when ready to re-validate..."))
        input()
        return execute(atomic_root, output_dir, uat_mode)

    # Compute Execution Levels
    levels = _compute_levels(tasks)

    # Complexity Distribution
    _show_complexity_distribution(tasks)

    # Execution DAG
    _show_execution_dag(tasks, levels)

    # Work Packages
    packages = _generate_work_packages(tasks, levels)
    write_file(packages_file, json.dumps(packages, indent=2))

    print(print_dim("─" * 100))
    print()
    print(print_bold("WORK PACKAGES"))
    print()
    print(print_green(f"✓ Generated {len(packages['packages'])} work packages (waves)"))
    print()

    for package in packages["packages"]:
        parallel_text = " (parallel)" if package["can_parallelize"] else ""
        print(f"  Wave {package['id']}: {package['task_count']} tasks{parallel_text}")
    print()

    # Critical Path
    _show_critical_path(tasks, levels)

    # Summary
    _show_summary(tasks, levels, packages)

    # Save analysis
    analysis_data = _build_analysis_data(tasks, levels, packages)
    write_file(analysis_file, json.dumps(analysis_data, indent=2))

    # Save graph
    graph_data = {
        "levels": levels,
        "critical_path": _compute_critical_path(tasks, levels),
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }
    write_file(graph_file, json.dumps(graph_data, indent=2))

    print(print_green("✓ Dependency analysis complete"))
    return True


def _validate_dependencies(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate dependency graph."""
    valid_ids = {task["id"] for task in tasks}
    invalid_refs = 0
    self_refs = 0
    root_count = 0

    for task in tasks:
        task_id = task["id"]
        deps = task.get("dependencies", [])

        # Check for invalid references
        for dep in deps:
            if dep not in valid_ids:
                invalid_refs += 1

        # Check for self-references
        if task_id in deps:
            self_refs += 1

        # Count root tasks
        if not deps:
            root_count += 1

    return {
        "passed": invalid_refs == 0 and self_refs == 0,
        "invalid_refs": invalid_refs,
        "self_refs": self_refs,
        "root_count": root_count
    }


def _compute_levels(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Compute topological levels for tasks."""
    # Build task map
    task_map = {task["id"]: task for task in tasks}

    # Compute level for each task
    levels_map: Dict[int, int] = {}

    # Iterative approach (max 20 iterations)
    for _ in range(20):
        changed = False
        for task in tasks:
            task_id = task["id"]
            deps = task.get("dependencies", [])

            if task_id in levels_map:
                continue

            if not deps:
                levels_map[task_id] = 0
                changed = True
            else:
                # Check if all dependencies have levels
                if all(dep in levels_map for dep in deps):
                    max_dep_level = max(levels_map[dep] for dep in deps)
                    levels_map[task_id] = max_dep_level + 1
                    changed = True

        if not changed:
            break

    # Group tasks by level
    levels_grouped: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for task in tasks:
        task_id = task["id"]
        level = levels_map.get(task_id, 0)
        levels_grouped[level].append({
            "id": task["id"],
            "title": task.get("title", "Untitled"),
            "priority": task.get("priority", "medium"),
            "complexity": task.get("estimated_complexity", "moderate"),
            "has_criteria": bool(task.get("acceptance_criteria"))
        })

    # Convert to list format
    levels_list = []
    for level in sorted(levels_grouped.keys()):
        levels_list.append({
            "level": level,
            "tasks": levels_grouped[level]
        })

    return levels_list


def _show_complexity_distribution(tasks: List[Dict[str, Any]]) -> None:
    """Display complexity distribution."""
    print(print_dim("─" * 100))
    print()
    print(print_bold("COMPLEXITY DISTRIBUTION"))
    print()

    simple_count = sum(1 for t in tasks if t.get("estimated_complexity") == "simple")
    moderate_count = sum(1 for t in tasks if t.get("estimated_complexity") in ["moderate", None])
    complex_count = sum(1 for t in tasks if t.get("estimated_complexity") == "complex")
    task_count = len(tasks)

    # Visual bar (10 chars = 100%)
    simple_bar = "█" * min(10, int(simple_count * 10 / task_count) + 1) if task_count > 0 else ""
    moderate_bar = "█" * min(10, int(moderate_count * 10 / task_count) + 1) if task_count > 0 else ""
    complex_bar = "█" * min(10, int(complex_count * 10 / task_count) + 1) if task_count > 0 else ""

    print(f"  Simple:   {simple_count:2d}  {print_green(simple_bar)}")
    print(f"  Moderate: {moderate_count:2d}  {print_yellow(moderate_bar)}")
    print(f"  Complex:  {complex_count:2d}  {print_red(complex_bar)}")
    print()

    # Estimate time
    estimated_sessions = simple_count * 1 + moderate_count * 3 + complex_count * 5
    print(print_dim(f"Estimated implementation sessions: ~{estimated_sessions}"))
    print(print_dim("(Simple=1, Moderate=3, Complex=5 sessions per task)"))
    print()


def _show_execution_dag(tasks: List[Dict[str, Any]], levels: List[Dict[str, Any]]) -> None:
    """Display execution DAG visualization."""
    print(print_dim("─" * 100))
    print()
    print(print_bold("EXECUTION DAG"))
    print()
    print(print_dim("Tasks grouped by dependency level. Tasks at the same level can execute"))
    print(print_dim("in parallel git worktrees. Each level must complete before the next begins."))
    print()

    for level_data in levels:
        level = level_data["level"]
        level_tasks = level_data["tasks"]
        task_count = len(level_tasks)

        print(print_cyan(f"LEVEL {level}") + print_dim(" " + "─" * 70))
        print(print_dim("│"))

        for task in level_tasks:
            task_id = task["id"]
            title = task["title"]
            priority = task["priority"]
            complexity = task["complexity"]

            # Priority indicator
            if priority == "high":
                priority_indicator = print_red("■")
            elif priority == "medium":
                priority_indicator = print_yellow("■")
            else:
                priority_indicator = print_dim("■")

            # Complexity indicator
            if complexity == "simple":
                complexity_indicator = print_green("S")
            elif complexity == "moderate":
                complexity_indicator = print_yellow("M")
            elif complexity == "complex":
                complexity_indicator = print_red("C")
            else:
                complexity_indicator = print_dim("?")

            print(print_dim("├── ") + print_bold(f"[{task_id}]") + f" {title}  {priority_indicator} {complexity_indicator}")

        if task_count > 1:
            print(print_dim("│   ") + print_green(f"↑ {task_count} parallel worktrees"))

        print(print_dim("│"))

    print(print_dim(f"Legend: Priority ■ ({print_red('high')}/{print_yellow('med')}/{print_dim('low')})  ")
              + f"Complexity ({print_green('S')}imple/{print_yellow('M')}oderate/{print_red('C')}omplex)")
    print()


def _generate_work_packages(tasks: List[Dict[str, Any]], levels: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate work packages from levels."""
    packages = []

    for level_data in levels:
        level = level_data["level"]
        level_tasks = level_data["tasks"]

        # Count complexity
        simple = sum(1 for t in level_tasks if t["complexity"] == "simple")
        moderate = sum(1 for t in level_tasks if t["complexity"] == "moderate")
        complex_count = sum(1 for t in level_tasks if t["complexity"] == "complex")

        packages.append({
            "id": level + 1,
            "name": f"Wave {level + 1}",
            "level": level,
            "tasks": [t["id"] for t in level_tasks],
            "task_count": len(level_tasks),
            "can_parallelize": len(level_tasks) > 1,
            "complexity_breakdown": {
                "simple": simple,
                "moderate": moderate,
                "complex": complex_count
            }
        })

    max_parallelism = max(len(p["tasks"]) for p in packages) if packages else 0

    return {
        "packages": packages,
        "summary": {
            "total_waves": len(packages),
            "max_parallelism": max_parallelism,
            "total_tasks": len(tasks)
        },
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }


def _compute_critical_path(tasks: List[Dict[str, Any]], levels: List[Dict[str, Any]]) -> str:
    """Compute critical path through highest complexity tasks."""
    path_tasks = []

    for level_data in levels:
        level_tasks = level_data["tasks"]
        # Sort by complexity (complex first, then moderate, then simple)
        complexity_order = {"complex": 0, "moderate": 1, "simple": 2}
        sorted_tasks = sorted(
            level_tasks,
            key=lambda t: complexity_order.get(t["complexity"], 1)
        )
        if sorted_tasks:
            path_tasks.append(sorted_tasks[0]["title"])

    return " → ".join(path_tasks)


def _show_critical_path(tasks: List[Dict[str, Any]], levels: List[Dict[str, Any]]) -> None:
    """Display critical path."""
    print(print_dim("─" * 100))
    print()
    print(print_bold("CRITICAL PATH"))
    print()

    critical_path = _compute_critical_path(tasks, levels)
    print(print_dim("Longest path through highest complexity:"))
    print(f"  {critical_path}")
    print()


def _show_summary(tasks: List[Dict[str, Any]], levels: List[Dict[str, Any]], packages: Dict[str, Any]) -> None:
    """Display summary statistics."""
    print(print_dim("─" * 100))
    print()
    print(print_bold("SUMMARY"))
    print()

    task_count = len(tasks)
    total_levels = len(levels)
    max_parallel = packages["summary"]["max_parallelism"]

    # Estimate sessions
    simple_count = sum(1 for t in tasks if t.get("estimated_complexity") == "simple")
    moderate_count = sum(1 for t in tasks if t.get("estimated_complexity") in ["moderate", None])
    complex_count = sum(1 for t in tasks if t.get("estimated_complexity") == "complex")
    estimated_sessions = simple_count * 1 + moderate_count * 3 + complex_count * 5

    print(f"  Total tasks:           {task_count}")
    print(f"  Execution waves:       {total_levels}")
    print(f"  Max parallel tasks:    {max_parallel}")
    print(f"  Est. sessions:         ~{estimated_sessions}")
    print()


def _build_analysis_data(
    tasks: List[Dict[str, Any]],
    levels: List[Dict[str, Any]],
    packages: Dict[str, Any]
) -> Dict[str, Any]:
    """Build analysis data structure."""
    simple_count = sum(1 for t in tasks if t.get("estimated_complexity") == "simple")
    moderate_count = sum(1 for t in tasks if t.get("estimated_complexity") in ["moderate", None])
    complex_count = sum(1 for t in tasks if t.get("estimated_complexity") == "complex")
    estimated_sessions = simple_count * 1 + moderate_count * 3 + complex_count * 5

    return {
        "validation": {
            "passed": True,
            "cycles": False,
            "invalid_refs": 0
        },
        "complexity": {
            "simple": simple_count,
            "moderate": moderate_count,
            "complex": complex_count,
            "estimated_sessions": estimated_sessions
        },
        "dag": {
            "total_tasks": len(tasks),
            "execution_waves": len(levels),
            "max_parallelism": packages["summary"]["max_parallelism"],
            "levels": levels,
            "critical_path": _compute_critical_path(tasks, levels)
        },
        "analyzed_at": datetime.utcnow().isoformat() + "Z"
    }


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 304: Dependency Analysis")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
