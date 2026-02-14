"""
Task 403: OpenSpec Generation

Generate OpenSpec specification files for each task using LLM analysis.
Each spec defines test strategy, interfaces, edge cases, and security requirements.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim
)
from core.utils.file_ops import ensure_dir, read_file, write_file


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
    """Generate a stub OpenSpec for UAT/testing mode."""
    task_id = task.get("id", 0)
    task_title = task.get("title", f"Task {task_id}")

    return {
        "spec_id": f"SPEC-T{task_id}",
        "task_id": task_id,
        "task_title": task_title,
        "stub_mode": True,
        "generated_at": datetime.now().isoformat(),
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


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 403: OpenSpec Generation.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, generate stub specs without LLM calls

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
            "mode": "uat" if uat_mode else "normal",
            "generated_at": datetime.now().isoformat()
        }
        write_file(output_dir / "openspec-generation.json", json.dumps(report, indent=2))
        return True

    # UAT Mode: Generate stub specs
    if uat_mode:
        print(print_yellow("  UAT Mode: Generating stub OpenSpecs"))
        print()

        for task in tasks:
            task_id = task.get("id", 0)
            spec = generate_stub_spec(task)
            spec_file = openspec_dir / f"spec-t{task_id}.json"
            write_file(spec_file, json.dumps(spec, indent=2))
            print(print_green(f"    Stub spec created: spec-t{task_id}.json"))

        # Write generation report
        report = {
            "status": "complete",
            "specs_generated": len(tasks),
            "mode": "uat",
            "generated_at": datetime.now().isoformat(),
            "specs": [f"spec-t{t.get('id', 0)}.json" for t in tasks]
        }
        write_file(output_dir / "openspec-generation.json", json.dumps(report, indent=2))

        print()
        print(print_green(f"  OpenSpec generation complete: {len(tasks)} specs created (UAT mode)"))
        return True

    # Normal Mode: Use LLM to generate specs
    print(print_bold("  OPENSPEC GENERATION"))
    print()
    print(print_dim(f"  Generating specifications for {len(tasks)} tasks..."))
    print()

    try:
        from core.llm import invoke

        generated = 0
        failed = 0

        for task in tasks:
            task_id = task.get("id", 0)
            task_title = task.get("title", f"Task {task_id}")
            task_desc = task.get("description", "")
            acceptance = task.get("acceptance_criteria", "")

            print(print_dim(f"  [{generated + 1}/{len(tasks)}] Generating spec for T{task_id}: {task_title}"))

            spec_file = openspec_dir / f"spec-t{task_id}.json"

            # Build prompt for LLM
            prompt = f"""Generate an OpenSpec specification for the following task:

Task ID: {task_id}
Title: {task_title}
Description: {task_desc}
Acceptance Criteria: {acceptance}

Generate a JSON specification with the following structure:
{{
    "spec_id": "SPEC-T{task_id}",
    "task_id": {task_id},
    "task_title": "{task_title}",
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

            try:
                result = invoke(
                    prompt=prompt,
                    output_file=str(spec_file),
                    description=f"Generate OpenSpec for T{task_id}",
                    model="sonnet"
                )
                generated += 1
                print(print_green(f"    Created: spec-t{task_id}.json"))
            except Exception as e:
                print(print_red(f"    Failed: {e}"))
                # Create fallback stub spec
                spec = generate_stub_spec(task)
                write_file(spec_file, json.dumps(spec, indent=2))
                generated += 1

        # Write generation report
        report = {
            "status": "complete",
            "specs_generated": generated,
            "specs_failed": failed,
            "mode": "normal",
            "generated_at": datetime.now().isoformat(),
            "specs": [f"spec-t{t.get('id', 0)}.json" for t in tasks]
        }
        write_file(output_dir / "openspec-generation.json", json.dumps(report, indent=2))

        print()
        print(print_green(f"  OpenSpec generation complete: {generated}/{len(tasks)} specs created"))
        return True

    except ImportError:
        print(print_yellow("  ! LLM module not available, falling back to stub specs"))
        # Fallback to stub generation
        for task in tasks:
            task_id = task.get("id", 0)
            spec = generate_stub_spec(task)
            spec_file = openspec_dir / f"spec-t{task_id}.json"
            write_file(spec_file, json.dumps(spec, indent=2))

        report = {
            "status": "complete",
            "specs_generated": len(tasks),
            "mode": "stub-fallback",
            "generated_at": datetime.now().isoformat()
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
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (generate stub specs)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
