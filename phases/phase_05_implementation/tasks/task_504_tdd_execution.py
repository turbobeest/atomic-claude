"""
Task 504: TDD Execution

Execute RED/GREEN/REFACTOR/VERIFY cycles for each task.

Sequential TDD engine that:
  - Loads tasks, OpenSpecs, agents, and TDD setup from prior phases
  - For each TDD-eligible task, runs RED → GREEN → REFACTOR → VERIFY
  - Writes test and implementation files to .claude/testing/task-{id}/
  - Tracks per-task records and overall progress with resume support
"""

import re
import sys
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.llm import invoke
from core.subprocess_runner import run_bash_command
from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, print_magenta, prompt_user, clear_input_buffer
)
from core.utils.file_ops import ensure_dir, read_file, write_file


# ---------------------------------------------------------------------------
# Helper: safe JSON loader
# ---------------------------------------------------------------------------

def load_json_safe(path: Path) -> Dict[str, Any]:
    """Load JSON file, returning empty dict on any failure."""
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        pass
    return {}


# ---------------------------------------------------------------------------
# Helper: load tasks eligible for TDD
# ---------------------------------------------------------------------------

def load_tasks(project_root: Path) -> List[Dict[str, Any]]:
    """
    Load tasks.json and return tasks that have >= 4 subtasks
    (the threshold from Phase 4 task decomposition).
    """
    tasks_file = project_root / ".taskmaster" / "tasks" / "tasks.json"
    if not tasks_file.exists():
        return []

    data = load_json_safe(tasks_file)
    tasks = data.get("tasks", [])
    return [t for t in tasks if len(t.get("subtasks", [])) >= 4]


# ---------------------------------------------------------------------------
# Helper: load OpenSpecs
# ---------------------------------------------------------------------------

def load_specs(project_root: Path) -> Dict[str, Dict[str, Any]]:
    """
    Load OpenSpec files from .openspec/ and .claude/specs/.
    Returns dict keyed by task id string.
    """
    specs: Dict[str, Dict[str, Any]] = {}

    for specs_dir in [project_root / ".openspec", project_root / ".claude" / "specs"]:
        if not specs_dir.exists():
            continue
        for spec_file in specs_dir.glob("spec-t*.json"):
            spec_data = load_json_safe(spec_file)
            # Extract task id from filename: spec-t3.json -> "3"
            match = re.search(r"spec-t(\d+)", spec_file.stem)
            if match:
                specs[match.group(1)] = spec_data
        # Also check spec-*.json (non-t prefix)
        for spec_file in specs_dir.glob("spec-*.json"):
            if "spec-t" in spec_file.name:
                continue  # already handled
            spec_data = load_json_safe(spec_file)
            task_id = spec_data.get("task_id")
            if task_id:
                specs[str(task_id)] = spec_data

    return specs


# ---------------------------------------------------------------------------
# Helper: load agent markdown as prompt prefix
# ---------------------------------------------------------------------------

def load_agent_prompt(name: str, atomic_root: Path) -> str:
    """
    Read an agent .md file from the agents directory.
    Strips YAML frontmatter (between --- delimiters) and returns body text.
    """
    # Search in pipeline-agents/06-09-implementation/ first
    agent_dirs = [
        atomic_root / "agents" / "pipeline-agents" / "06-09-implementation",
        atomic_root / "agents" / "pipeline-agents",
        atomic_root / "agents" / "expert-agents",
    ]

    for base_dir in agent_dirs:
        if not base_dir.exists():
            continue
        # Direct match
        candidate = base_dir / f"{name}.md"
        if candidate.exists():
            return _strip_frontmatter(candidate.read_text())
        # Recursive search
        for md_file in base_dir.rglob(f"{name}.md"):
            return _strip_frontmatter(md_file.read_text())

    return ""


def _strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter (--- ... ---) from markdown."""
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            return text[end + 3:].strip()
    return text.strip()


# ---------------------------------------------------------------------------
# Helper: map tech stack to test/lint/security commands
# ---------------------------------------------------------------------------

def get_tool_commands(setup: Dict[str, Any], project_root: Path) -> Dict[str, str]:
    """
    Map detected_stack to test/lint/security commands.
    Checks for custom tdd-tools.json first, then falls back to defaults.
    """
    # Check for custom config
    config_file = project_root / ".claude" / "config" / "tdd-tools.json"
    if config_file.exists():
        custom = load_json_safe(config_file)
        if custom:
            return {
                "test": custom.get("red", {}).get("test_command", ""),
                "lint": custom.get("refactor", {}).get("lint_command", ""),
                "security": custom.get("verify", {}).get("security_command", ""),
            }

    stack = setup.get("detected_stack", "python")

    if stack == "python":
        return {
            "test": "python -m pytest -xvs",
            "lint": "python -m py_compile",
            "security": "python -m py_compile",  # fallback if bandit unavailable
        }
    elif stack == "node":
        return {
            "test": "npx jest --no-coverage",
            "lint": "npx eslint",
            "security": "npm audit --audit-level=high",
        }
    elif stack == "go":
        return {
            "test": "go test -v",
            "lint": "go vet",
            "security": "go vet",
        }

    return {"test": "", "lint": "", "security": ""}


# ---------------------------------------------------------------------------
# Helper: verify test runner availability
# ---------------------------------------------------------------------------

def verify_test_runner(commands: Dict[str, str], project_root: Path) -> bool:
    """
    Check if the test runner command is actually available.
    Returns True if available, False otherwise.
    """
    test_cmd = commands.get("test", "")
    if not test_cmd:
        return False

    # Extract the base command (first word)
    base = test_cmd.split()[0]

    # Check if it's a python -m style command
    if base == "python":
        # Check the module
        parts = test_cmd.split()
        if len(parts) >= 3 and parts[1] == "-m":
            check_cmd = f"python -m {parts[2]} --version"
        else:
            check_cmd = "python --version"
    elif base == "npx":
        check_cmd = "npx --yes jest --version 2>/dev/null || echo unavailable"
    elif base == "go":
        check_cmd = "go version"
    else:
        check_cmd = f"which {base}"

    exit_code, _, _ = run_bash_command(check_cmd, "5-implementation", "504", timeout=15)
    return exit_code == 0


# ---------------------------------------------------------------------------
# Helper: extract code blocks from LLM response
# ---------------------------------------------------------------------------

def extract_code_from_response(response: str, language: str = "python") -> str:
    """
    Extract code from an LLM response, stripping markdown fences.
    If multiple code blocks exist, joins them. If none, returns raw text.
    """
    if not response:
        return ""

    # Try to find fenced code blocks
    pattern = rf"```(?:{language}|{language}\n)?\s*\n(.*?)```"
    blocks = re.findall(pattern, response, re.DOTALL)

    if blocks:
        return "\n\n".join(block.strip() for block in blocks)

    # Try generic fenced blocks
    generic_blocks = re.findall(r"```\w*\s*\n(.*?)```", response, re.DOTALL)
    if generic_blocks:
        return "\n\n".join(block.strip() for block in generic_blocks)

    # No fences found — return the whole response stripped of obvious non-code
    return response.strip()


# ---------------------------------------------------------------------------
# Helper: show execution overview
# ---------------------------------------------------------------------------

def show_overview(
    tasks: List[Dict],
    specs: Dict,
    agents: Dict,
    setup: Dict,
    skip_execution: bool,
) -> None:
    """Display execution plan to user."""
    print()
    print(print_bold("  TDD Execution Overview"))
    print(print_dim("  " + "─" * 56))
    print()
    print(f"    Tasks to execute:   {len(tasks)}")
    print(f"    Specs available:    {len(specs)}")
    print(f"    Stack:              {setup.get('detected_stack', 'unknown')}")

    # Show agent summary
    agent_names = []
    for role in ["red_agents", "green_agents", "refactor_agents", "verify_agents"]:
        agent_names.extend(agents.get(role, []))
    if agent_names:
        print(f"    Agents loaded:      {len(set(agent_names))}")
    else:
        print(f"    Agents loaded:      (defaults)")

    if skip_execution:
        print()
        print(print_yellow("    ⚠ Test runner not available — code generation only"))

    print()
    print(print_dim("  " + "─" * 56))
    print()


# ---------------------------------------------------------------------------
# TDD Phase: RED — write failing tests
# ---------------------------------------------------------------------------

def run_red_phase(
    task: Dict,
    spec: Dict,
    task_dir: Path,
    agent_prompt: str,
    commands: Dict[str, str],
    skip_execution: bool,
    atomic_root: Path,
) -> Dict[str, Any]:
    """
    RED phase: LLM writes failing tests. Run them and verify they fail.

    Returns dict with status, test_file path, and any notes.
    """
    task_id = task.get("id", "0")
    title = task.get("title", "untitled")
    description = task.get("description", "")

    # Build spec context
    spec_tests = spec.get("test_strategy", spec.get("tests", ""))
    spec_interfaces = spec.get("interfaces", spec.get("api", ""))
    if isinstance(spec_tests, dict):
        spec_tests = json.dumps(spec_tests, indent=2)
    if isinstance(spec_interfaces, dict):
        spec_interfaces = json.dumps(spec_interfaces, indent=2)

    language = "python"  # determined from setup, but default python

    prompt = f"""{agent_prompt}

You are writing FAILING tests for a TDD RED phase.

## Task
ID: {task_id}
Title: {title}
Description: {description}

## Spec Test Strategy
{spec_tests}

## Spec Interfaces
{spec_interfaces}

## Instructions
Write a test file that:
1. Imports from `task_{task_id}_impl` (a module that does NOT exist yet)
2. Tests the expected behavior described in the task and spec
3. Uses pytest conventions (functions named test_*)
4. Each test should be focused and test one behavior
5. Include at least 3 test functions covering core functionality

The tests MUST fail when run because task_{task_id}_impl does not exist yet.

Output ONLY the Python test code, no explanations. Wrap in ```python fences.
"""

    print(print_red(f"    RED  ") + f"Writing tests for task {task_id}...")

    test_file = task_dir / f"test_task_{task_id}.py"
    record: Dict[str, Any] = {"status": "failed", "test_file": str(test_file)}

    try:
        response = invoke(prompt=prompt, model="sonnet")
    except Exception as e:
        print(print_dim(f"         LLM error: {e}"))
        record["error"] = str(e)
        return record

    code = extract_code_from_response(response, language)
    if not code:
        print(print_yellow("         Empty response from LLM, skipping RED"))
        record["error"] = "empty_response"
        return record

    write_file(test_file, code)
    record["test_file"] = str(test_file)

    if skip_execution:
        print(print_dim("         (skip_execution) Tests written but not run"))
        record["status"] = "written"
        return record

    # Run tests — expect them to FAIL (ImportError or assertion error)
    test_cmd = f"{commands['test']} {test_file}"
    exit_code, stdout, stderr = run_bash_command(
        test_cmd, "5-implementation", "504", timeout=30
    )

    if exit_code != 0:
        # Expected! Tests should fail in RED phase
        print(print_green("         ✓ Tests fail as expected (RED confirmed)"))
        record["status"] = "complete"
    else:
        # Tests passed — this is unexpected but not fatal
        print(print_yellow("         ⚠ Tests passed unexpectedly (no impl exists?)"))
        record["status"] = "complete"
        record["note"] = "tests_passed_unexpectedly"

    return record


# ---------------------------------------------------------------------------
# TDD Phase: GREEN — write implementation to make tests pass
# ---------------------------------------------------------------------------

def run_green_phase(
    task: Dict,
    spec: Dict,
    task_dir: Path,
    test_code: str,
    agent_prompt: str,
    commands: Dict[str, str],
    skip_execution: bool,
    atomic_root: Path,
    max_retries: int = 2,
) -> Dict[str, Any]:
    """
    GREEN phase: LLM writes minimal implementation. Run tests, retry on failure.

    Returns dict with status and impl_file path.
    """
    task_id = task.get("id", "0")
    title = task.get("title", "untitled")
    description = task.get("description", "")

    spec_interfaces = spec.get("interfaces", spec.get("api", ""))
    if isinstance(spec_interfaces, dict):
        spec_interfaces = json.dumps(spec_interfaces, indent=2)

    impl_file = task_dir / f"task_{task_id}_impl.py"
    test_file = task_dir / f"test_task_{task_id}.py"
    record: Dict[str, Any] = {"status": "failed", "impl_file": str(impl_file)}

    error_context = ""

    for attempt in range(max_retries + 1):
        retry_note = ""
        if attempt > 0:
            retry_note = f"""

## Previous Attempt Failed
The previous implementation did not pass the tests. Here is the error output
(last 2000 chars):

{error_context[-2000:]}

Fix the implementation to make the tests pass.
"""

        prompt = f"""{agent_prompt}

You are writing a MINIMAL implementation for a TDD GREEN phase.

## Task
ID: {task_id}
Title: {title}
Description: {description}

## Spec Interfaces
{spec_interfaces}

## Test Code (must pass)
```python
{test_code}
```
{retry_note}
## Instructions
Write the implementation module `task_{task_id}_impl.py` that makes ALL tests pass.
1. Implement only what is needed to pass the tests — no extra features
2. Use clear, readable code
3. Export the functions/classes that the tests import

Output ONLY the Python implementation code. Wrap in ```python fences.
"""

        attempt_label = f" (retry {attempt})" if attempt > 0 else ""
        print(print_green(f"    GREEN") + f" Writing implementation{attempt_label}...")

        try:
            response = invoke(prompt=prompt, model="sonnet")
        except Exception as e:
            print(print_dim(f"         LLM error: {e}"))
            record["error"] = str(e)
            continue

        code = extract_code_from_response(response, "python")
        if not code:
            print(print_yellow("         Empty response, retrying..."))
            error_context = "LLM returned empty response"
            continue

        write_file(impl_file, code)

        if skip_execution:
            print(print_dim("         (skip_execution) Impl written but not tested"))
            record["status"] = "written"
            return record

        # Run tests
        test_cmd = f"{commands['test']} {test_file}"
        exit_code, stdout, stderr = run_bash_command(
            test_cmd, "5-implementation", "504", timeout=60
        )

        if exit_code == 0:
            print(print_green("         ✓ All tests pass (GREEN confirmed)"))
            record["status"] = "complete"
            record["attempts"] = attempt + 1
            return record
        else:
            combined_output = (stdout + "\n" + stderr).strip()
            error_context = combined_output
            if attempt < max_retries:
                print(print_yellow(f"         Tests failed, will retry ({attempt + 1}/{max_retries})"))
            else:
                print(print_red(f"         ✗ Tests failed after {max_retries + 1} attempts"))
                record["error"] = error_context[-500:]

    record["attempts"] = max_retries + 1
    return record


# ---------------------------------------------------------------------------
# TDD Phase: REFACTOR — improve code quality
# ---------------------------------------------------------------------------

def run_refactor_phase(
    task: Dict,
    task_dir: Path,
    agent_prompt: str,
    commands: Dict[str, str],
    skip_execution: bool,
    atomic_root: Path,
) -> Dict[str, Any]:
    """
    REFACTOR phase: LLM refactors implementation. If tests break, auto-revert.

    Returns dict with status.
    """
    task_id = task.get("id", "0")
    impl_file = task_dir / f"task_{task_id}_impl.py"
    test_file = task_dir / f"test_task_{task_id}.py"
    backup_file = task_dir / f"task_{task_id}_impl.pre_refactor.py"

    record: Dict[str, Any] = {"status": "skipped"}

    if not impl_file.exists():
        return record

    impl_code = impl_file.read_text()
    test_code = test_file.read_text() if test_file.exists() else ""

    # Backup before refactor
    write_file(backup_file, impl_code)

    prompt = f"""{agent_prompt}

You are REFACTORING an implementation that already passes its tests.

## Implementation Code
```python
{impl_code}
```

## Test Code (must still pass after refactoring)
```python
{test_code}
```

## Instructions
Refactor the implementation for:
1. Readability — clear variable names, logical flow
2. DRY — eliminate duplication
3. Docstrings — add brief docstrings to public functions
4. Keep the same public API so all tests still pass

Output ONLY the refactored Python code. Wrap in ```python fences.
"""

    print(print_cyan(f"    REFACTOR") + f" Improving code quality...")

    try:
        response = invoke(prompt=prompt, model="sonnet")
    except Exception as e:
        print(print_dim(f"         LLM error: {e} — keeping original"))
        record["status"] = "skipped"
        record["error"] = str(e)
        return record

    code = extract_code_from_response(response, "python")
    if not code:
        print(print_dim("         Empty response — keeping original"))
        return record

    write_file(impl_file, code)

    if skip_execution:
        print(print_dim("         (skip_execution) Refactored but not verified"))
        record["status"] = "written"
        return record

    # Verify tests still pass
    test_cmd = f"{commands['test']} {test_file}"
    exit_code, _, _ = run_bash_command(
        test_cmd, "5-implementation", "504", timeout=60
    )

    if exit_code == 0:
        print(print_green("         ✓ Tests still pass after refactor"))
        record["status"] = "complete"
    else:
        # Revert!
        print(print_yellow("         ⚠ Refactor broke tests — reverting to backup"))
        write_file(impl_file, backup_file.read_text())
        record["status"] = "reverted"

    return record


# ---------------------------------------------------------------------------
# TDD Phase: VERIFY — syntax check + optional security review
# ---------------------------------------------------------------------------

def run_verify_phase(
    task: Dict,
    task_dir: Path,
    commands: Dict[str, str],
    skip_execution: bool,
    atomic_root: Path,
) -> Dict[str, Any]:
    """
    VERIFY phase: syntax check + optional haiku security review.
    Non-blocking — warnings logged but don't fail the task.
    """
    task_id = task.get("id", "0")
    impl_file = task_dir / f"task_{task_id}_impl.py"
    record: Dict[str, Any] = {"status": "skipped", "warnings": []}

    if not impl_file.exists():
        return record

    print(print_magenta(f"    VERIFY") + f" Running verification checks...")

    # 1. Syntax check with py_compile
    compile_cmd = f"python -m py_compile {impl_file}"
    exit_code, stdout, stderr = run_bash_command(
        compile_cmd, "5-implementation", "504", timeout=15
    )

    if exit_code == 0:
        print(print_green("         ✓ Syntax check passed"))
    else:
        msg = (stderr or stdout).strip()[:200]
        print(print_yellow(f"         ⚠ Syntax issue: {msg}"))
        record["warnings"].append(f"syntax: {msg}")

    # 2. Optional haiku security review (only for small files, cost control)
    impl_content = impl_file.read_text()
    if len(impl_content) < 5000:
        try:
            security_prompt = f"""Review this Python code for security issues. Be brief.
Report ONLY actual security concerns (injection, eval, exec, pickle, etc.).
If the code is safe, respond with just "PASS".

```python
{impl_content}
```"""
            sec_response = invoke(prompt=security_prompt, model="haiku")
            sec_text = sec_response.strip() if isinstance(sec_response, str) else str(sec_response).strip()

            if sec_text.upper().startswith("PASS") or len(sec_text) < 10:
                print(print_green("         ✓ Security review: clean"))
            else:
                print(print_yellow(f"         ⚠ Security note: {sec_text[:120]}"))
                record["warnings"].append(f"security: {sec_text[:300]}")
        except Exception as e:
            print(print_dim(f"         Security review skipped: {e}"))
    else:
        print(print_dim("         Security review skipped (file > 5000 chars)"))

    record["status"] = "complete"
    return record


# ---------------------------------------------------------------------------
# Helper: save per-task TDD record
# ---------------------------------------------------------------------------

def save_tdd_record(testing_dir: Path, task_id: str, record: Dict[str, Any]) -> None:
    """Write per-task JSON record to .claude/testing/tdd-t{id}.json."""
    record_file = testing_dir / f"tdd-t{task_id}.json"
    record["saved_at"] = datetime.now().isoformat()
    write_file(record_file, json.dumps(record, indent=2))


# ---------------------------------------------------------------------------
# Helper: save overall progress
# ---------------------------------------------------------------------------

def save_progress(progress_file: Path, stats: Dict[str, Any]) -> None:
    """Write overall progress JSON."""
    stats["updated_at"] = datetime.now().isoformat()
    write_file(progress_file, json.dumps(stats, indent=2))


# ---------------------------------------------------------------------------
# Main execute function
# ---------------------------------------------------------------------------

def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None) -> bool:
    """
    Execute Task 504: TDD Execution.

    Runs RED/GREEN/REFACTOR/VERIFY cycles for each TDD-eligible task.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    project_root = atomic_root.parent
    testing_dir = project_root / ".claude" / "testing"
    progress_file = output_dir / "tdd-progress.json"
    src_dir = atomic_root / "src"

    # UAT Mode Bypass
    if uat_mode:
        print()
        print(print_yellow("⚡ UAT Mode: Creating stub implementation files (no actual TDD cycles)"))
        print()

        ensure_dir(testing_dir)
        ensure_dir(src_dir)

        # Create minimal TDD progress file
        progress_data = {
            "tasks_completed": 3,
            "tasks_total": 3,
            "subtasks_completed": 12,
            "subtasks_total": 12,
            "red_cycles": 3,
            "green_cycles": 3,
            "refactor_cycles": 3,
            "verify_cycles": 3,
            "mode": "uat",
            "completed_at": datetime.now().isoformat()
        }
        write_file(progress_file, json.dumps(progress_data, indent=2))

        # Create stub test and implementation files for 3 tasks
        for task_id in range(1, 4):
            task_dir = src_dir / f"task-{task_id}"
            ensure_dir(task_dir)
            ensure_dir(testing_dir / f"task-{task_id}")

            impl_file = task_dir / "implementation.py"
            write_file(impl_file, "# Stub Implementation (UAT Mode)\ndef stub_function(): pass\n")

            test_file = testing_dir / f"task-{task_id}" / "test_stub.py"
            write_file(test_file, "# Stub Test (UAT Mode)\ndef test_stub(): assert True\n")

            # Create minimal TDD record
            tdd_record = {
                "task_id": task_id,
                "red": {"status": "complete"},
                "green": {"status": "complete"},
                "refactor": {"status": "complete"},
                "verify": {"status": "complete"},
                "mode": "uat"
            }
            write_file(testing_dir / f"tdd-t{task_id}.json", json.dumps(tdd_record, indent=2))

        print(print_green("✓ Created stub files for 3 tasks"))
        print()

        print(print_green("✓ TDD Execution complete (UAT mode)"))
        return True

    # =======================================================================
    # LIVE PATH: Full TDD Execution
    # =======================================================================

    # --- Load inputs ---
    tasks = load_tasks(project_root)
    specs = load_specs(project_root)
    agents_data = load_json_safe(output_dir / "selected-agents.json")
    setup = load_json_safe(output_dir / "tdd-setup.json")

    if not tasks:
        print()
        print(print_red("✗ No TDD-eligible tasks found in .taskmaster/tasks/tasks.json"))
        print(print_dim("  Tasks need >= 4 subtasks to qualify for TDD execution."))
        print()
        return False

    if not specs:
        print()
        print(print_yellow("⚠ No OpenSpec files found — proceeding with task descriptions only"))
        print()

    # --- Tool commands ---
    commands = get_tool_commands(setup, project_root)

    # --- Verify test runner ---
    skip_execution = False
    if not commands.get("test"):
        skip_execution = True
    elif not verify_test_runner(commands, project_root):
        print()
        print(print_yellow("⚠ Test runner not available on this system"))
        print(print_dim(f"  Command: {commands['test']}"))
        print()

        clear_input_buffer()
        choice = prompt_user("  Continue with code generation only? (y/n, default y): ").strip().lower()
        skip_execution = choice != "n"

        if not skip_execution:
            print(print_red("  Aborting — install the test runner and retry."))
            return False

    # --- Load agent prompts ---
    red_agent = load_agent_prompt("test-strategist", atomic_root)
    green_agent = load_agent_prompt("tdd-implementation-agent", atomic_root)
    refactor_agent = load_agent_prompt("code-review-gate", atomic_root)

    # --- Show overview ---
    show_overview(tasks, specs, agents_data, setup, skip_execution)

    # --- Resume check ---
    existing_progress = load_json_safe(progress_file)
    completed_ids: set = set()

    if existing_progress.get("completed_ids"):
        completed_ids = set(str(i) for i in existing_progress["completed_ids"])
        remaining = len(tasks) - len(completed_ids)
        if remaining > 0 and completed_ids:
            print(print_cyan(f"  Found previous progress: {len(completed_ids)} of {len(tasks)} tasks done"))
            clear_input_buffer()
            choice = prompt_user("  Resume from where you left off? (y/n, default y): ").strip().lower()
            if choice == "n":
                completed_ids = set()
                print(print_dim("  Starting fresh."))
            else:
                print(print_dim(f"  Resuming — {remaining} tasks remaining."))
            print()

    # --- Prepare directories ---
    ensure_dir(testing_dir)
    ensure_dir(output_dir)

    # --- Execution stats ---
    stats = {
        "tasks_total": len(tasks),
        "tasks_completed": len(completed_ids),
        "tasks_failed": 0,
        "tasks_skipped": 0,
        "red_cycles": 0,
        "green_cycles": 0,
        "refactor_cycles": 0,
        "verify_cycles": 0,
        "completed_ids": list(completed_ids),
        "mode": "live",
        "skip_execution": skip_execution,
        "started_at": datetime.now().isoformat(),
    }

    # --- Execute TDD cycles ---
    for idx, task in enumerate(tasks):
        task_id = str(task.get("id", idx))
        title = task.get("title", "untitled")

        if task_id in completed_ids:
            continue

        print()
        print(print_bold(f"  ━━━ Task {task_id}: {title} ━━━"))
        print()

        # Interactive prompt
        clear_input_buffer()
        print(print_dim(f"    [Enter] Execute  |  [s] Skip  |  [q] Abort"))
        choice = prompt_user("    > ").strip().lower()

        if choice == "q":
            print()
            print(print_yellow("  Aborting TDD execution. Progress saved."))
            save_progress(progress_file, stats)
            return stats["tasks_completed"] > 0

        if choice == "s":
            print(print_dim(f"    Skipping task {task_id}"))
            stats["tasks_skipped"] += 1
            continue

        # Setup task directory
        task_dir = testing_dir / f"task-{task_id}"
        ensure_dir(task_dir)

        # Get spec for this task
        spec = specs.get(task_id, {})

        # --- RED ---
        red_record = run_red_phase(
            task, spec, task_dir, red_agent, commands, skip_execution, atomic_root
        )
        stats["red_cycles"] += 1

        if red_record["status"] in ("failed",) and not red_record.get("error", "").startswith("empty"):
            # If RED itself failed catastrophically (LLM error), mark failed and continue
            if "error" in red_record and "LLM" in str(red_record.get("error", "")):
                print(print_red(f"    ✗ RED phase failed — skipping task {task_id}"))
                stats["tasks_failed"] += 1
                tdd_record = {"task_id": task_id, "red": red_record, "status": "failed"}
                save_tdd_record(testing_dir, task_id, tdd_record)
                continue

        # Load test code for GREEN phase
        test_file = task_dir / f"test_task_{task_id}.py"
        test_code = test_file.read_text() if test_file.exists() else ""

        # --- GREEN ---
        green_record = run_green_phase(
            task, spec, task_dir, test_code, green_agent, commands,
            skip_execution, atomic_root
        )
        stats["green_cycles"] += 1

        if green_record["status"] == "failed":
            print(print_red(f"    ✗ GREEN phase failed — marking task {task_id} as failed"))
            stats["tasks_failed"] += 1
            tdd_record = {
                "task_id": task_id,
                "red": red_record,
                "green": green_record,
                "status": "failed",
            }
            save_tdd_record(testing_dir, task_id, tdd_record)
            save_progress(progress_file, stats)
            continue

        # --- REFACTOR ---
        refactor_record = run_refactor_phase(
            task, task_dir, refactor_agent, commands, skip_execution, atomic_root
        )
        stats["refactor_cycles"] += 1

        # --- VERIFY ---
        verify_record = run_verify_phase(
            task, task_dir, commands, skip_execution, atomic_root
        )
        stats["verify_cycles"] += 1

        # --- Save per-task record ---
        tdd_record = {
            "task_id": task_id,
            "title": title,
            "red": red_record,
            "green": green_record,
            "refactor": refactor_record,
            "verify": verify_record,
            "status": "complete",
        }
        save_tdd_record(testing_dir, task_id, tdd_record)

        # --- Update progress ---
        completed_ids.add(task_id)
        stats["tasks_completed"] = len(completed_ids)
        stats["completed_ids"] = list(completed_ids)
        save_progress(progress_file, stats)

        print()
        print(print_green(f"    ✓ Task {task_id} complete"))

    # --- Final summary ---
    print()
    print(print_bold("  TDD Execution Summary"))
    print(print_dim("  " + "─" * 40))
    print(f"    Completed: {stats['tasks_completed']}/{stats['tasks_total']}")
    print(f"    Failed:    {stats['tasks_failed']}")
    print(f"    Skipped:   {stats['tasks_skipped']}")
    print(f"    RED:       {stats['red_cycles']} cycles")
    print(f"    GREEN:     {stats['green_cycles']} cycles")
    print(f"    REFACTOR:  {stats['refactor_cycles']} cycles")
    print(f"    VERIFY:    {stats['verify_cycles']} cycles")
    print()

    stats["completed_at"] = datetime.now().isoformat()
    save_progress(progress_file, stats)

    success = stats["tasks_completed"] > 0 or stats["tasks_skipped"] > 0
    if success:
        print(print_green("✓ TDD Execution complete"))
    else:
        print(print_red("✗ No tasks completed"))

    return success


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 504: TDD Execution")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
