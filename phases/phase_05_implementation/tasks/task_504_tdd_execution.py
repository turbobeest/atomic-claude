"""
Task 504: TDD Execution — Stack-Aware Parallel DAG Engine

Execute RED/GREEN/REFACTOR/VERIFY cycles for each task.

Parallel DAG engine that:
  - Loads tasks, OpenSpecs, agents, and TDD setup from prior phases
  - Detects host-project tech stack and uses stack-specific prompts/commands
  - Resolves task dependencies into a DAG and runs independent tasks in parallel
  - Shows Rich Live progress panel (mirrors task 403/404 pattern)
  - Writes test and implementation files to .claude/testing/task-{id}/
  - Tracks per-task records and overall progress with resume support
"""

import os
import re
import sys
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
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
# Stack Profiles — single source of truth for language-specific behaviour
# ---------------------------------------------------------------------------

STACK_PROFILES: Dict[str, Dict[str, Any]] = {
    "python": {
        "language": "python",
        "test_file": "test_task_{id}.py",
        "impl_file": "task_{id}_impl.py",
        "backup_suffix": ".pre_refactor.py",
        "fence_lang": "python",
        "test_framework": "pytest",
        "test_conventions": "Uses pytest conventions (functions named test_*)",
        "import_pattern": "Imports from `task_{id}_impl`",
        "impl_instructions": "Write the implementation module `task_{id}_impl.py`",
        "commands": {
            "test": "python -m pytest -xvs",
            "lint": "python -m py_compile",
            "security": "python -m py_compile",
        },
        "verify_cmd": "python -m py_compile {impl_file}",
    },
    "rust": {
        "language": "rust",
        "test_file": "test_task_{id}.rs",
        "impl_file": "task_{id}_impl.rs",
        "backup_suffix": ".pre_refactor.rs",
        "fence_lang": "rust",
        "test_framework": "cargo test",
        "test_conventions": "Uses Rust #[test] attribute on functions",
        "import_pattern": "Uses `mod task_{id}_impl;` to reference the implementation",
        "impl_instructions": "Write the implementation module `task_{id}_impl.rs`",
        "commands": {
            "test": "cargo test",
            "lint": "cargo clippy -- -D warnings",
            "security": "cargo audit",
        },
        "verify_cmd": "cargo clippy -- -D warnings",
    },
    "node": {
        "language": "javascript",
        "test_file": "test_task_{id}.test.js",
        "impl_file": "task_{id}_impl.js",
        "backup_suffix": ".pre_refactor.js",
        "fence_lang": "javascript",
        "test_framework": "jest",
        "test_conventions": "Uses Jest describe/it blocks",
        "import_pattern": "Requires `./task_{id}_impl`",
        "impl_instructions": "Write the implementation module `task_{id}_impl.js`",
        "commands": {
            "test": "npx jest --no-coverage",
            "lint": "npx eslint",
            "security": "npm audit --audit-level=high",
        },
        "verify_cmd": "npx eslint {impl_file}",
    },
    "go": {
        "language": "go",
        "test_file": "task_{id}_test.go",
        "impl_file": "task_{id}_impl.go",
        "backup_suffix": ".pre_refactor.go",
        "fence_lang": "go",
        "test_framework": "go test",
        "test_conventions": "Uses Go testing.T with TestXxx function names",
        "import_pattern": "Imports from the same package",
        "impl_instructions": "Write the implementation file `task_{id}_impl.go`",
        "commands": {
            "test": "go test -v",
            "lint": "go vet",
            "security": "go vet",
        },
        "verify_cmd": "go vet {impl_file}",
    },
}


def get_stack_profile(stack: str) -> Dict[str, Any]:
    """Return the profile for a stack, falling back to python."""
    return STACK_PROFILES.get(stack, STACK_PROFILES["python"])


# ---------------------------------------------------------------------------
# Helper: safe JSON loader
# ---------------------------------------------------------------------------

def load_json_safe(path: Path) -> Dict[str, Any]:
    """Load JSON file, returning empty dict on any failure.

    Handles OpenSpec files that may be wrapped in markdown code fences.
    """
    try:
        if path.exists():
            text = path.read_text()
            stripped = text.strip()
            # Strip markdown code fences if present
            if stripped.startswith("```"):
                first_nl = stripped.index("\n")
                stripped = stripped[first_nl + 1:]
                if stripped.endswith("```"):
                    stripped = stripped[:-3].strip()
            return json.loads(stripped)
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
    agent_dirs = [
        atomic_root / "agents" / "pipeline-agents" / "06-09-implementation",
        atomic_root / "agents" / "pipeline-agents",
        atomic_root / "agents" / "expert-agents",
    ]

    for base_dir in agent_dirs:
        if not base_dir.exists():
            continue
        candidate = base_dir / f"{name}.md"
        if candidate.exists():
            return _strip_frontmatter(candidate.read_text())
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
    Checks for custom tdd-tools.json first, then falls back to stack profile.
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
    profile = get_stack_profile(stack)
    return dict(profile["commands"])


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

    base = test_cmd.split()[0]

    if base == "python":
        parts = test_cmd.split()
        if len(parts) >= 3 and parts[1] == "-m":
            check_cmd = f"python -m {parts[2]} --version"
        else:
            check_cmd = "python --version"
    elif base == "npx":
        check_cmd = "npx --yes jest --version 2>/dev/null || echo unavailable"
    elif base == "go":
        check_cmd = "go version"
    elif base == "cargo":
        check_cmd = "cargo --version"
    else:
        check_cmd = f"which {base}"

    exit_code, _, _ = run_bash_command(check_cmd, "5-implementation", "504", timeout=15)
    return exit_code == 0


# ---------------------------------------------------------------------------
# Helper: make a command that runs in the project directory
# ---------------------------------------------------------------------------

def _make_project_cmd(cmd: str, project_root: Path) -> str:
    """Prefix a command with cd to the project root.

    So that `cargo test`, `go test`, etc. run in the right directory.
    """
    return f"cd {project_root} && {cmd}"


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

    # Try to find fenced code blocks for the specific language
    pattern = rf"```(?:{re.escape(language)}|{re.escape(language)}\n)?\s*\n(.*?)```"
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
    profile: Dict[str, Any],
) -> None:
    """Display execution plan to user."""
    print()
    print(print_bold("  TDD Execution Overview"))
    print(print_dim("  " + "─" * 56))
    print()
    print(f"    Tasks to execute:   {len(tasks)}")
    print(f"    Specs available:    {len(specs)}")
    print(f"    Stack:              {setup.get('detected_stack', 'unknown')}")
    print(f"    Language:           {profile['language']}")
    print(f"    Test framework:     {profile['test_framework']}")

    # Worker count
    workers = setup.get("execution", {}).get("workers", 4)
    print(f"    Parallel workers:   {workers}")

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
    profile: Dict[str, Any],
    project_root: Path,
    quiet: bool = False,
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

    language = profile["language"]
    fence_lang = profile["fence_lang"]
    test_conventions = profile["test_conventions"]
    import_pattern = profile["import_pattern"].format(id=task_id)

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
Write a test file ({language}) that:
1. {import_pattern} (a module that does NOT exist yet)
2. Tests the expected behavior described in the task and spec
3. {test_conventions}
4. Each test should be focused and test one behavior
5. Include at least 3 test functions covering core functionality

The tests MUST fail when run because the implementation module does not exist yet.

Output ONLY the {language} test code, no explanations. Wrap in ```{fence_lang} fences.
"""

    test_filename = profile["test_file"].format(id=task_id)
    test_file = task_dir / test_filename
    record: Dict[str, Any] = {"status": "failed", "test_file": str(test_file)}

    if not quiet:
        print(print_red(f"    RED  ") + f"Writing tests for task {task_id}...")

    try:
        response = invoke(prompt=prompt, model="sonnet")
    except Exception as e:
        if not quiet:
            print(print_dim(f"         LLM error: {e}"))
        record["error"] = str(e)
        return record

    code = extract_code_from_response(response, fence_lang)
    if not code:
        if not quiet:
            print(print_yellow("         Empty response from LLM, skipping RED"))
        record["error"] = "empty_response"
        return record

    write_file(test_file, code)
    record["test_file"] = str(test_file)

    if skip_execution:
        if not quiet:
            print(print_dim("         (skip_execution) Tests written but not run"))
        record["status"] = "written"
        return record

    # Run tests — expect them to FAIL (ImportError or assertion error)
    test_cmd = f"{commands['test']} {test_file}"
    # For cargo/go, run in project dir
    if commands["test"].startswith(("cargo", "go")):
        test_cmd = _make_project_cmd(f"{commands['test']} -- {test_file.stem}", project_root)

    exit_code, stdout, stderr = run_bash_command(
        test_cmd, "5-implementation", "504", timeout=30
    )

    if exit_code != 0:
        if not quiet:
            print(print_green("         ✓ Tests fail as expected (RED confirmed)"))
        record["status"] = "complete"
    else:
        if not quiet:
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
    profile: Dict[str, Any],
    project_root: Path,
    quiet: bool = False,
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

    language = profile["language"]
    fence_lang = profile["fence_lang"]
    impl_filename = profile["impl_file"].format(id=task_id)
    test_filename = profile["test_file"].format(id=task_id)
    impl_instructions = profile["impl_instructions"].format(id=task_id)

    impl_file = task_dir / impl_filename
    test_file = task_dir / test_filename
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
```{fence_lang}
{test_code}
```
{retry_note}
## Instructions
{impl_instructions} that makes ALL tests pass.
1. Implement only what is needed to pass the tests — no extra features
2. Use clear, readable code
3. Export the functions/classes that the tests import

Output ONLY the {language} implementation code. Wrap in ```{fence_lang} fences.
"""

        attempt_label = f" (retry {attempt})" if attempt > 0 else ""
        if not quiet:
            print(print_green(f"    GREEN") + f" Writing implementation{attempt_label}...")

        try:
            response = invoke(prompt=prompt, model="sonnet")
        except Exception as e:
            if not quiet:
                print(print_dim(f"         LLM error: {e}"))
            record["error"] = str(e)
            continue

        code = extract_code_from_response(response, fence_lang)
        if not code:
            if not quiet:
                print(print_yellow("         Empty response, retrying..."))
            error_context = "LLM returned empty response"
            continue

        write_file(impl_file, code)

        if skip_execution:
            if not quiet:
                print(print_dim("         (skip_execution) Impl written but not tested"))
            record["status"] = "written"
            return record

        # Run tests
        test_cmd = f"{commands['test']} {test_file}"
        if commands["test"].startswith(("cargo", "go")):
            test_cmd = _make_project_cmd(f"{commands['test']} -- {test_file.stem}", project_root)

        exit_code, stdout, stderr = run_bash_command(
            test_cmd, "5-implementation", "504", timeout=60
        )

        if exit_code == 0:
            if not quiet:
                print(print_green("         ✓ All tests pass (GREEN confirmed)"))
            record["status"] = "complete"
            record["attempts"] = attempt + 1
            return record
        else:
            combined_output = (stdout + "\n" + stderr).strip()
            error_context = combined_output
            if attempt < max_retries:
                if not quiet:
                    print(print_yellow(f"         Tests failed, will retry ({attempt + 1}/{max_retries})"))
            else:
                if not quiet:
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
    profile: Dict[str, Any],
    project_root: Path,
    quiet: bool = False,
) -> Dict[str, Any]:
    """
    REFACTOR phase: LLM refactors implementation. If tests break, auto-revert.

    Returns dict with status.
    """
    task_id = task.get("id", "0")
    language = profile["language"]
    fence_lang = profile["fence_lang"]
    impl_filename = profile["impl_file"].format(id=task_id)
    test_filename = profile["test_file"].format(id=task_id)
    backup_suffix = profile["backup_suffix"]

    impl_file = task_dir / impl_filename
    test_file = task_dir / test_filename
    backup_file = task_dir / (impl_file.stem + backup_suffix)

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
```{fence_lang}
{impl_code}
```

## Test Code (must still pass after refactoring)
```{fence_lang}
{test_code}
```

## Instructions
Refactor the implementation for:
1. Readability — clear variable names, logical flow
2. DRY — eliminate duplication
3. Brief documentation for public functions
4. Keep the same public API so all tests still pass

Output ONLY the refactored {language} code. Wrap in ```{fence_lang} fences.
"""

    if not quiet:
        print(print_cyan(f"    REFACTOR") + f" Improving code quality...")

    try:
        response = invoke(prompt=prompt, model="sonnet")
    except Exception as e:
        if not quiet:
            print(print_dim(f"         LLM error: {e} — keeping original"))
        record["status"] = "skipped"
        record["error"] = str(e)
        return record

    code = extract_code_from_response(response, fence_lang)
    if not code:
        if not quiet:
            print(print_dim("         Empty response — keeping original"))
        return record

    write_file(impl_file, code)

    if skip_execution:
        if not quiet:
            print(print_dim("         (skip_execution) Refactored but not verified"))
        record["status"] = "written"
        return record

    # Verify tests still pass
    test_cmd = f"{commands['test']} {test_file}"
    if commands["test"].startswith(("cargo", "go")):
        test_cmd = _make_project_cmd(f"{commands['test']} -- {test_file.stem}", project_root)

    exit_code, _, _ = run_bash_command(
        test_cmd, "5-implementation", "504", timeout=60
    )

    if exit_code == 0:
        if not quiet:
            print(print_green("         ✓ Tests still pass after refactor"))
        record["status"] = "complete"
    else:
        # Revert!
        if not quiet:
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
    profile: Dict[str, Any],
    project_root: Path,
    quiet: bool = False,
) -> Dict[str, Any]:
    """
    VERIFY phase: syntax/lint check + optional haiku security review.
    Non-blocking — warnings logged but don't fail the task.
    """
    task_id = task.get("id", "0")
    language = profile["language"]
    fence_lang = profile["fence_lang"]
    impl_filename = profile["impl_file"].format(id=task_id)
    verify_cmd_template = profile["verify_cmd"]

    impl_file = task_dir / impl_filename
    record: Dict[str, Any] = {"status": "skipped", "warnings": []}

    if not impl_file.exists():
        return record

    if not quiet:
        print(print_magenta(f"    VERIFY") + f" Running verification checks...")

    # 1. Syntax / lint check
    verify_cmd = verify_cmd_template.format(impl_file=impl_file)
    if verify_cmd.startswith(("cargo", "go")):
        verify_cmd = _make_project_cmd(verify_cmd, project_root)

    exit_code, stdout, stderr = run_bash_command(
        verify_cmd, "5-implementation", "504", timeout=15
    )

    if exit_code == 0:
        if not quiet:
            print(print_green("         ✓ Verification check passed"))
    else:
        msg = (stderr or stdout).strip()[:200]
        if not quiet:
            print(print_yellow(f"         ⚠ Verification issue: {msg}"))
        record["warnings"].append(f"verify: {msg}")

    # 2. Optional haiku security review (only for small files, cost control)
    impl_content = impl_file.read_text()
    if len(impl_content) < 5000:
        try:
            security_prompt = f"""Review this {language} code for security issues. Be brief.
Report ONLY actual security concerns (injection, unsafe, eval, exec, etc.).
If the code is safe, respond with just "PASS".

```{fence_lang}
{impl_content}
```"""
            sec_response = invoke(prompt=security_prompt, model="haiku")
            sec_text = sec_response.strip() if isinstance(sec_response, str) else str(sec_response).strip()

            if sec_text.upper().startswith("PASS") or len(sec_text) < 10:
                if not quiet:
                    print(print_green("         ✓ Security review: clean"))
            else:
                if not quiet:
                    print(print_yellow(f"         ⚠ Security note: {sec_text[:120]}"))
                record["warnings"].append(f"security: {sec_text[:300]}")
        except Exception as e:
            if not quiet:
                print(print_dim(f"         Security review skipped: {e}"))
    else:
        if not quiet:
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
# DAGScheduler — thread-safe dependency resolver
# ---------------------------------------------------------------------------

class DAGScheduler:
    """Thread-safe DAG-based task scheduler.

    Resolves dependencies so that tasks whose prerequisites are all met
    can be claimed and executed in parallel.
    """

    def __init__(self, tasks: List[Dict[str, Any]], completed_ids: Set[str]):
        self._lock = threading.Lock()
        self._deps: Dict[str, Set[str]] = {}
        self._rdeps: Dict[str, Set[str]] = {}
        self._all_ids: Set[str] = set()
        self._completed: Set[str] = set(completed_ids)
        self._failed: Set[str] = set()
        self._in_progress: Set[str] = set()

        for task in tasks:
            tid = str(task.get("id", "0"))
            self._all_ids.add(tid)
            deps = set()
            for d in task.get("dependencies", []):
                ds = str(d)
                deps.add(ds)
                self._rdeps.setdefault(ds, set()).add(tid)
            self._deps[tid] = deps

    def _get_ready(self) -> List[str]:
        """Return ready task IDs. MUST be called with self._lock held."""
        ready = []
        for tid in self._all_ids:
            if tid in self._completed or tid in self._in_progress or tid in self._failed:
                continue
            unmet = self._deps[tid] - self._completed
            # Deps outside our task set are assumed already met
            unmet = unmet & self._all_ids
            if not unmet:
                ready.append(tid)
        return ready

    def get_ready(self) -> List[str]:
        """Return task IDs whose dependencies are all met and aren't started/done/failed."""
        with self._lock:
            return self._get_ready()

    def claim(self, task_id: str) -> bool:
        """Mark a task as in-progress. Returns False if already claimed/done."""
        with self._lock:
            if task_id in self._in_progress or task_id in self._completed or task_id in self._failed:
                return False
            self._in_progress.add(task_id)
            return True

    def complete(self, task_id: str) -> None:
        """Mark a task as completed."""
        with self._lock:
            self._in_progress.discard(task_id)
            self._completed.add(task_id)

    def fail(self, task_id: str) -> Set[str]:
        """Mark a task as failed. Returns set of cascade-failed task IDs.

        A downstream task is cascade-failed if ALL of its in-set deps are failed.
        """
        with self._lock:
            self._in_progress.discard(task_id)
            self._failed.add(task_id)

            cascaded: Set[str] = set()
            changed = True
            while changed:
                changed = False
                for tid in self._all_ids:
                    if tid in self._completed or tid in self._failed:
                        continue
                    deps_in_set = self._deps[tid] & self._all_ids
                    if deps_in_set and deps_in_set.issubset(self._failed):
                        self._failed.add(tid)
                        self._in_progress.discard(tid)
                        cascaded.add(tid)
                        changed = True
            return cascaded

    def is_done(self) -> bool:
        """True when no more tasks can possibly run."""
        with self._lock:
            remaining = self._all_ids - self._completed - self._failed
            if not remaining:
                return True
            return len(self._in_progress) == 0 and not self._get_ready()

    @property
    def completed_ids(self) -> Set[str]:
        with self._lock:
            return set(self._completed)

    @property
    def failed_ids(self) -> Set[str]:
        with self._lock:
            return set(self._failed)


# ---------------------------------------------------------------------------
# TDD Cycle Worker — runs full RED→GREEN→REFACTOR→VERIFY for one task
# ---------------------------------------------------------------------------

def _tdd_cycle_worker(
    task: Dict[str, Any],
    spec: Dict[str, Any],
    testing_dir: Path,
    agents: Dict[str, str],
    commands: Dict[str, str],
    skip_execution: bool,
    atomic_root: Path,
    profile: Dict[str, Any],
    project_root: Path,
) -> Tuple[str, str, Dict[str, Any], float, Optional[str]]:
    """Run full TDD cycle for one task. Never raises.

    Returns (task_id, status, record, duration_seconds, error_or_None).
    """
    task_id = str(task.get("id", "0"))
    start = time.monotonic()

    task_dir = testing_dir / f"task-{task_id}"
    ensure_dir(task_dir)

    record: Dict[str, Any] = {"task_id": task_id, "title": task.get("title", "")}

    try:
        # --- RED ---
        red_record = run_red_phase(
            task, spec, task_dir, agents.get("red", ""), commands,
            skip_execution, atomic_root, profile, project_root, quiet=True,
        )
        record["red"] = red_record

        if red_record["status"] == "failed" and "error" in red_record:
            record["status"] = "failed"
            return (task_id, "failed", record, time.monotonic() - start, red_record.get("error"))

        # Load test code for GREEN phase
        test_filename = profile["test_file"].format(id=task_id)
        test_file = task_dir / test_filename
        test_code = test_file.read_text() if test_file.exists() else ""

        # --- GREEN ---
        green_record = run_green_phase(
            task, spec, task_dir, test_code, agents.get("green", ""), commands,
            skip_execution, atomic_root, profile, project_root, quiet=True,
        )
        record["green"] = green_record

        if green_record["status"] == "failed":
            record["status"] = "failed"
            return (task_id, "failed", record, time.monotonic() - start, green_record.get("error"))

        # --- REFACTOR ---
        refactor_record = run_refactor_phase(
            task, task_dir, agents.get("refactor", ""), commands,
            skip_execution, atomic_root, profile, project_root, quiet=True,
        )
        record["refactor"] = refactor_record

        # --- VERIFY ---
        verify_record = run_verify_phase(
            task, task_dir, commands, skip_execution, atomic_root,
            profile, project_root, quiet=True,
        )
        record["verify"] = verify_record

        record["status"] = "complete"
        return (task_id, "complete", record, time.monotonic() - start, None)

    except Exception as e:
        record["status"] = "failed"
        record["error"] = str(e)
        return (task_id, "failed", record, time.monotonic() - start, str(e))


# ---------------------------------------------------------------------------
# Parallel DAG Executor with Rich Live panel
# ---------------------------------------------------------------------------

def _run_dag_parallel(
    tasks: List[Dict[str, Any]],
    specs: Dict[str, Dict[str, Any]],
    completed_ids: Set[str],
    testing_dir: Path,
    agents: Dict[str, str],
    commands: Dict[str, str],
    skip_execution: bool,
    atomic_root: Path,
    profile: Dict[str, Any],
    project_root: Path,
    progress_file: Path,
    max_workers: int = 4,
) -> Dict[str, Any]:
    """Run TDD cycles in parallel respecting DAG dependencies.

    Uses Rich Live panel to show progress. Returns final stats dict.
    """
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel

    console = Console()
    task_map = {str(t.get("id", "0")): t for t in tasks}
    total = len(tasks)

    # Results tracking
    results: Dict[str, Optional[Tuple]] = {}  # task_id -> result tuple
    task_status: Dict[str, str] = {}  # task_id -> display status

    for t in tasks:
        tid = str(t.get("id", "0"))
        if tid in completed_ids:
            task_status[tid] = "done"
        else:
            task_status[tid] = "pending"

    scheduler = DAGScheduler(tasks, completed_ids)

    stats = {
        "tasks_total": total,
        "tasks_completed": len(completed_ids),
        "tasks_failed": 0,
        "tasks_cascaded": 0,
        "red_cycles": 0,
        "green_cycles": 0,
        "refactor_cycles": 0,
        "verify_cycles": 0,
        "completed_ids": list(completed_ids),
        "mode": "live",
        "skip_execution": skip_execution,
        "started_at": datetime.now().isoformat(),
    }

    STATUS_ICON = {
        "pending": "⏳",
        "running": "🔄",
        "done": "✅",
        "failed": "❌",
        "cascaded": "⛔",
    }

    def _build_display() -> Panel:
        done_count = sum(1 for s in task_status.values() if s == "done")
        failed_count = sum(1 for s in task_status.values() if s == "failed")
        cascaded_count = sum(1 for s in task_status.values() if s == "cascaded")
        running_count = sum(1 for s in task_status.values() if s == "running")
        pending_count = sum(1 for s in task_status.values() if s == "pending")

        completed_total = done_count + failed_count + cascaded_count
        pct = int(completed_total / total * 100) if total else 100
        bar_filled = int(pct / 100 * 30)
        bar = "█" * bar_filled + "░" * (30 - bar_filled)

        lines = [""]
        lines.append(f"  {done_count} done  {failed_count} failed  "
                     f"{cascaded_count} cascaded  {running_count} running  "
                     f"{pending_count} pending")

        if completed_total < total:
            lines.append(f"  ⠸ Executing {bar} {pct}%")
        else:
            lines.append(f"  ✓ Complete  {bar} {pct}%")
        lines.append("")

        lines.append(
            f"  {'#':>4}  {'Status':<10} {'Task':>5}  {'Title':<45} {'Time':>8}"
        )

        for i, task in enumerate(tasks):
            tid = str(task.get("id", "0"))
            title = task.get("title", f"Task {tid}")
            if len(title) > 44:
                title = title[:42] + "…"

            status = task_status.get(tid, "pending")
            icon = STATUS_ICON.get(status, "?")

            r = results.get(tid)
            if r is not None:
                time_str = f"{r[3]:.1f}s"
                lines.append(
                    f"  {i+1:>4}  {icon} {status:<8} T{tid:>4}  {title:<45} {time_str:>8}"
                )
            else:
                lines.append(
                    f"  {i+1:>4}  {icon} {status:<8} T{tid:>4}  {title:<45}"
                )

        lines.append("")
        stack = profile["language"]
        return Panel("\n".join(lines),
                     title=f"TDD Execution ({stack}, {max_workers} workers, DAG)")

    with Live(_build_display(), console=console, refresh_per_second=2) as live:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            active_futures: Dict[Future, str] = {}

            while not scheduler.is_done():
                # Submit ready tasks
                ready = scheduler.get_ready()
                for tid in ready:
                    if tid in completed_ids:
                        continue
                    if not scheduler.claim(tid):
                        continue

                    task_status[tid] = "running"
                    live.update(_build_display())

                    task = task_map[tid]
                    spec = specs.get(tid, {})

                    future = executor.submit(
                        _tdd_cycle_worker,
                        task, spec, testing_dir, agents, commands,
                        skip_execution, atomic_root, profile, project_root,
                    )
                    active_futures[future] = tid

                if not active_futures:
                    # Nothing running, nothing ready — might be stuck
                    if scheduler.is_done():
                        break
                    time.sleep(0.2)
                    continue

                # Wait for at least one completion
                done_futures = []
                for future in as_completed(active_futures):
                    done_futures.append(future)
                    break  # Process one at a time to check for newly ready tasks

                for future in done_futures:
                    tid = active_futures.pop(future)
                    result = future.result()
                    results[tid] = result

                    task_id, status, record, duration, error = result

                    # Save per-task record
                    save_tdd_record(testing_dir, task_id, record)

                    if status == "complete":
                        scheduler.complete(tid)
                        task_status[tid] = "done"
                        stats["tasks_completed"] += 1
                        completed_ids.add(tid)

                        # Count cycles from record
                        if "red" in record:
                            stats["red_cycles"] += 1
                        if "green" in record:
                            stats["green_cycles"] += 1
                        if "refactor" in record:
                            stats["refactor_cycles"] += 1
                        if "verify" in record:
                            stats["verify_cycles"] += 1
                    else:
                        cascaded = scheduler.fail(tid)
                        task_status[tid] = "failed"
                        stats["tasks_failed"] += 1

                        # Count partial cycles
                        if "red" in record:
                            stats["red_cycles"] += 1
                        if "green" in record:
                            stats["green_cycles"] += 1

                        for ctid in cascaded:
                            task_status[ctid] = "cascaded"
                            stats["tasks_cascaded"] = stats.get("tasks_cascaded", 0) + 1

                    # Save progress after each completion
                    stats["completed_ids"] = list(completed_ids)
                    save_progress(progress_file, stats)
                    live.update(_build_display())

    return stats


# ---------------------------------------------------------------------------
# Main execute function
# ---------------------------------------------------------------------------

def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None) -> bool:
    """
    Execute Task 504: TDD Execution.

    Runs RED/GREEN/REFACTOR/VERIFY cycles for each TDD-eligible task
    in parallel respecting the DAG from task dependencies.

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

    # UAT Mode Bypass
    if uat_mode:
        print()
        print(print_yellow("⚡ UAT Mode: Creating stub implementation files (no actual TDD cycles)"))
        print()

        ensure_dir(testing_dir)

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
            task_dir = testing_dir / f"task-{task_id}"
            ensure_dir(task_dir)

            impl_file = task_dir / "implementation.py"
            write_file(impl_file, "# Stub Implementation (UAT Mode)\ndef stub_function(): pass\n")

            test_file = task_dir / "test_stub.py"
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

    # --- Stack profile ---
    stack = setup.get("detected_stack", "python")
    profile = get_stack_profile(stack)

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
    agents = {"red": red_agent, "green": green_agent, "refactor": refactor_agent}

    # --- Show overview ---
    show_overview(tasks, specs, agents_data, setup, skip_execution, profile)

    # --- Resume check ---
    existing_progress = load_json_safe(progress_file)
    completed_ids: Set[str] = set()

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

    # --- Check remaining ---
    remaining_tasks = [t for t in tasks if str(t.get("id", "")) not in completed_ids]
    remaining_count = len(remaining_tasks)

    if remaining_count == 0:
        print(print_green("  All tasks already completed."))
        stats = existing_progress
        stats["completed_at"] = datetime.now().isoformat()
        save_progress(progress_file, stats)
        return True

    # --- Worker count ---
    workers = setup.get("execution", {}).get("workers", min(4, os.cpu_count() or 4))
    workers = min(workers, remaining_count)  # Don't spawn more workers than tasks

    print(f"  Ready to execute {remaining_count} TDD cycles.")
    print(print_dim(f"  {workers} parallel workers, DAG-ordered, {profile['language']} stack."))
    print(print_dim(f"  Progress is saved after each task — interrupt with Ctrl+C to pause."))
    print()

    clear_input_buffer()
    choice = prompt_user(f"  Run all {remaining_count} tasks? [Enter] Continue  |  [q] Abort: ").strip().lower()
    if choice == "q":
        print(print_yellow("  Aborted."))
        return False

    # --- LLM warm-up (same pattern as task 404) ---
    print()
    print(print_dim("  Warming up LLM provider..."))
    try:
        from core.llm.invoke import invoke_llm
        invoke_llm(prompt="Reply with OK", model="haiku", timeout=30)
        print(print_green("  ✓ LLM provider ready"))
    except Exception as e:
        print(print_yellow(f"  ⚠ LLM warm-up issue: {e} — continuing anyway"))
    print()

    # --- Execute TDD cycles via DAG parallel executor ---
    stats = _run_dag_parallel(
        tasks=tasks,
        specs=specs,
        completed_ids=completed_ids,
        testing_dir=testing_dir,
        agents=agents,
        commands=commands,
        skip_execution=skip_execution,
        atomic_root=atomic_root,
        profile=profile,
        project_root=project_root,
        progress_file=progress_file,
        max_workers=workers,
    )

    # --- Final summary ---
    print()
    print(print_bold("  TDD Execution Summary"))
    print(print_dim("  " + "─" * 40))
    print(f"    Completed: {stats['tasks_completed']}/{stats['tasks_total']}")
    print(f"    Failed:    {stats['tasks_failed']}")
    cascaded = stats.get('tasks_cascaded', 0)
    if cascaded:
        print(f"    Cascaded:  {cascaded}")
    print(f"    RED:       {stats['red_cycles']} cycles")
    print(f"    GREEN:     {stats['green_cycles']} cycles")
    print(f"    REFACTOR:  {stats['refactor_cycles']} cycles")
    print(f"    VERIFY:    {stats['verify_cycles']} cycles")
    print(f"    Stack:     {profile['language']}")
    print()

    stats["completed_at"] = datetime.now().isoformat()
    save_progress(progress_file, stats)

    success = stats["tasks_completed"] > 0
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
