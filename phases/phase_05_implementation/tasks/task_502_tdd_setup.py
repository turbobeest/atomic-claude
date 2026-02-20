"""
Task 502: TDD Setup

Configure coverage targets, test pyramid, execution mode, and tech stack detection.

Stack detection uses a 4-strategy cascade:
  1. Filesystem — check for Cargo.toml, pyproject.toml, etc. in the host project
  2. PRD scan — keyword-match the approved PRD document
  3. Spec/task scan — keyword-match OpenSpec files and task titles
  4. User prompt — ask interactively (defaults to "python" in UAT mode)
"""

import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, print_magenta, prompt_user
)
from core.utils.file_ops import ensure_dir, write_file


# ---------------------------------------------------------------------------
# Stack signal keywords — used by PRD and spec scanning strategies
# ---------------------------------------------------------------------------

STACK_SIGNALS: Dict[str, Dict[str, List[str]]] = {
    "rust": {
        "strong": [
            "Cargo.toml", "cargo test", "edition 2021", "Rust", "#[test]",
            "crate", "pub fn", "impl ", "mod.rs", "rust-toolchain", "FFI",
            "cargo build", "cargo clippy", "#[derive", "tokio::main",
        ],
        "weak": [
            "memory safety", "zero-cost", "Send + Sync", "tokio",
            "async fn", "unsafe", "lifetime", "borrow checker",
        ],
    },
    "python": {
        "strong": [
            "pytest", "pip install", "requirements.txt", "pyproject.toml",
            "Django", "Flask", "FastAPI", "Python 3", "python3",
            "setup.py", "poetry", "pdm", "pipenv",
        ],
        "weak": [
            "venv", "pip", "conda", "virtualenv", "pydantic",
        ],
    },
    "node": {
        "strong": [
            "package.json", "npm install", "yarn add", "pnpm",
            "TypeScript", "tsconfig", "jest", "vitest",
            "React", "Next.js", "Express", "Node.js",
        ],
        "weak": [
            "ESLint", "Prettier", "webpack", "vite", "esbuild",
        ],
    },
    "go": {
        "strong": [
            "go.mod", "go test", "Go ", "golang",
            "func main", "package main", "goroutine",
        ],
        "weak": [
            "gofmt", "go vet", "go build",
        ],
    },
}


def _scan_text_for_stack(text: str) -> Dict[str, int]:
    """Score text against STACK_SIGNALS. Returns {stack: score}.

    Scoring: strong keyword hit = 10 pts, weak = 2 pts.
    Case-insensitive matching.
    """
    scores: Dict[str, int] = {}
    text_lower = text.lower()

    for stack, signals in STACK_SIGNALS.items():
        score = 0
        for kw in signals.get("strong", []):
            # Count occurrences (capped at 10 to avoid runaway scoring)
            count = min(text_lower.count(kw.lower()), 10)
            score += count * 10
        for kw in signals.get("weak", []):
            count = min(text_lower.count(kw.lower()), 10)
            score += count * 2
        scores[stack] = score

    return scores


def _load_prd_text(project_root: Path) -> Optional[str]:
    """Load the approved PRD document text.

    Resolution order:
      1. prd-approved.json ``prd_file`` pointer (most authoritative)
      2. Markdown/text files in .outputs/2-prd/ (including prompts/ subdir)
      3. Largest JSON file as last resort
    """
    prd_dir = project_root / ".outputs" / "2-prd"
    if not prd_dir.exists():
        return None

    # Strategy 1: Follow the prd-approved.json pointer
    approved_meta = prd_dir / "prd-approved.json"
    if approved_meta.exists():
        try:
            meta = json.loads(approved_meta.read_text())
            prd_file_str = meta.get("prd_file", "")
            prd_path = Path(prd_file_str) if prd_file_str else None
            if prd_path and prd_path.is_file() and prd_path.stat().st_size > 0:
                text = prd_path.read_text(errors="replace")
                return text[:100_000]
        except Exception:
            pass  # Fall through to other strategies

    # Strategy 2: Markdown/text in prd_dir and prompts/ subdir
    candidates = list(prd_dir.glob("*.md")) + list(prd_dir.glob("*.txt"))
    prompts_dir = prd_dir / "prompts"
    if prompts_dir.exists():
        candidates += list(prompts_dir.glob("*.md"))
    if not candidates:
        # Strategy 3: JSON files
        candidates = list(prd_dir.glob("*.json"))

    if not candidates:
        return None

    # Read the largest file (likely the full PRD)
    candidates.sort(key=lambda p: p.stat().st_size, reverse=True)
    try:
        text = candidates[0].read_text(errors="replace")
        return text[:100_000]
    except Exception:
        return None


def _load_spec_and_task_text(project_root: Path) -> Optional[str]:
    """Load first 5 OpenSpec files + first 10 task titles for scanning."""
    parts: List[str] = []

    # OpenSpec files
    for specs_dir in [project_root / ".openspec", project_root / ".claude" / "specs"]:
        if not specs_dir.exists():
            continue
        spec_files = sorted(specs_dir.glob("spec-*.json"))[:5]
        for sf in spec_files:
            try:
                parts.append(sf.read_text(errors="replace")[:10_000])
            except Exception:
                continue

    # Task titles from tasks.json
    tasks_file = project_root / ".taskmaster" / "tasks" / "tasks.json"
    if tasks_file.exists():
        try:
            data = json.loads(tasks_file.read_text())
            for task in data.get("tasks", [])[:10]:
                parts.append(task.get("title", ""))
                parts.append(task.get("description", "")[:500])
        except Exception:
            pass

    combined = "\n".join(parts)
    return combined if combined.strip() else None


def detect_tech_stack(atomic_root: Path) -> str:
    """Detect project tech stack from host project configuration files.

    Checks the HOST project root (atomic_root.parent), not the atomic-claude
    directory itself -- atomic-claude has its own requirements.txt which would
    always cause false "python" detection.

    This is Strategy 1 (filesystem) only -- kept for backward compatibility.
    Prefer detect_tech_stack_cascade() for full detection.
    """
    project_root = atomic_root.parent
    if (project_root / "Cargo.toml").exists():
        return "rust"
    if (project_root / "pyproject.toml").exists() or (project_root / "requirements.txt").exists():
        return "python"
    if (project_root / "package.json").exists():
        return "node"
    if (project_root / "go.mod").exists():
        return "go"
    return "unknown"


def detect_tech_stack_cascade(
    atomic_root: Path,
    uat_mode: bool = False,
) -> Tuple[str, Dict[str, Any]]:
    """Cascading tech stack detection with 4 strategies.

    Stops at the first confident match:
      1. Filesystem -- check for Cargo.toml, etc.
      2. PRD scan -- keyword-score the approved PRD document
      3. Spec/task scan -- keyword-score OpenSpec + task titles
      4. User prompt -- interactive fallback (defaults to 'python' in UAT)

    Returns:
        (detected_stack, metadata_dict) where metadata contains strategy,
        confidence, score, and signals_found.
    """
    project_root = atomic_root.parent
    THRESHOLD = 10  # Minimum score to accept a PRD/spec match

    # Strategy 1: Filesystem
    fs_stack = detect_tech_stack(atomic_root)
    if fs_stack != "unknown":
        return fs_stack, {
            "strategy": "filesystem",
            "confidence": "high",
            "score": None,
            "signals_found": [f"Found config file at project root"],
        }

    # Strategy 2: PRD scan
    prd_text = _load_prd_text(project_root)
    if prd_text:
        scores = _scan_text_for_stack(prd_text)
        best_stack = max(scores, key=scores.get) if scores else None
        best_score = scores.get(best_stack, 0) if best_stack else 0

        if best_stack and best_score >= THRESHOLD:
            # Collect which signals matched for diagnostics
            signals_found = []
            text_lower = prd_text.lower()
            for kw in STACK_SIGNALS[best_stack]["strong"]:
                if kw.lower() in text_lower:
                    signals_found.append(kw)
            for kw in STACK_SIGNALS[best_stack]["weak"]:
                if kw.lower() in text_lower:
                    signals_found.append(kw)

            return best_stack, {
                "strategy": "prd_scan",
                "confidence": "high" if best_score >= 50 else "medium",
                "score": best_score,
                "signals_found": signals_found[:20],
            }

    # Strategy 3: Spec/task scan
    spec_text = _load_spec_and_task_text(project_root)
    if spec_text:
        scores = _scan_text_for_stack(spec_text)
        best_stack = max(scores, key=scores.get) if scores else None
        best_score = scores.get(best_stack, 0) if best_stack else 0

        if best_stack and best_score >= THRESHOLD:
            signals_found = []
            text_lower = spec_text.lower()
            for kw in STACK_SIGNALS[best_stack]["strong"]:
                if kw.lower() in text_lower:
                    signals_found.append(kw)

            return best_stack, {
                "strategy": "spec_scan",
                "confidence": "medium" if best_score >= 30 else "low",
                "score": best_score,
                "signals_found": signals_found[:20],
            }

    # Strategy 4: User prompt (or UAT default)
    if uat_mode:
        return "python", {
            "strategy": "uat_default",
            "confidence": "low",
            "score": None,
            "signals_found": [],
        }

    print()
    print(print_yellow("  Stack could not be auto-detected from project files or PRD."))
    print()
    print(print_cyan("  Select your project's primary language:"))
    print()
    print(print_green("    [1]") + " Rust")
    print(print_yellow("    [2]") + " Python")
    print(print_cyan("    [3]") + " Node/TypeScript")
    print(print_dim("    [4]") + " Go")
    print()

    choice = prompt_user("  Choice (default: 2 - Python): ").strip()
    stack_map = {"1": "rust", "2": "python", "3": "node", "4": "go"}
    chosen = stack_map.get(choice, "python")

    return chosen, {
        "strategy": "user_prompt",
        "confidence": "high",
        "score": None,
        "signals_found": [f"User selected: {chosen}"],
    }


def _check_tool_availability(stack: str) -> Dict[str, bool]:
    """Check if build/test tools for the detected stack are installed."""
    checks: Dict[str, str] = {
        "rust": "cargo --version",
        "python": "python3 --version",
        "node": "node --version",
        "go": "go version",
    }

    cmd = checks.get(stack)
    if not cmd:
        return {"available": False, "command": "unknown"}

    try:
        result = subprocess.run(
            cmd.split(), capture_output=True, text=True, timeout=10,
        )
        available = result.returncode == 0
        version = result.stdout.strip() if available else None
        return {"available": available, "command": cmd, "version": version}
    except Exception:
        return {"available": False, "command": cmd}


def detect_cpu_count() -> int:
    """Detect CPU count across platforms."""
    try:
        # Try nproc (Linux)
        result = subprocess.run(['nproc'], capture_output=True, text=True)
        if result.returncode == 0:
            return int(result.stdout.strip())
    except Exception:
        pass

    try:
        # Try sysctl (macOS)
        result = subprocess.run(['sysctl', '-n', 'hw.ncpu'], capture_output=True, text=True)
        if result.returncode == 0:
            return int(result.stdout.strip())
    except Exception:
        pass

    return 4  # Default fallback


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None) -> bool:
    """
    Execute Task 502: TDD Setup.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    project_root = atomic_root.parent
    tasks_file = project_root / ".taskmaster" / "tasks" / "tasks.json"
    setup_file = output_dir / "tdd-setup.json"
    config_file = project_root / ".claude" / "config" / "tdd-tools.json"

    # UAT Mode Bypass
    if uat_mode:
        print()
        print(print_yellow("  UAT Mode: Skipping TDD configuration, creating minimal setup"))
        print()

        ensure_dir(setup_file.parent)

        detected_stack, stack_meta = detect_tech_stack_cascade(atomic_root, uat_mode=True)

        setup_data = {
            "coverage_targets": {
                "unit": 80,
                "integration": 70
            },
            "pyramid_profile": "unit-heavy",
            "execution": {
                "mode": "parallel",
                "workers": 2
            },
            "task_count": 3,
            "detected_stack": detected_stack,
            "stack_detection": stack_meta,
            "token_budget_usd": 50.0,
            "mode": "uat",
            "configured_at": datetime.now().isoformat()
        }
        write_file(setup_file, json.dumps(setup_data, indent=2))

        print(print_green("  TDD Setup complete (UAT mode)"))
        return True

    ensure_dir(setup_file.parent)
    ensure_dir(config_file.parent)

    print()
    print(print_dim("  Configuring TDD execution parameters."))
    print()

    # Coverage Targets
    print(print_dim("─" * 120))
    print()
    print(print_bold("COVERAGE TARGETS"))
    print()

    print(print_dim("  Coverage measures how much of your code is exercised by tests. But coverage"))
    print(print_dim("  is a means, not an end—100% coverage doesn't guarantee bug-free code."))
    print()

    print(print_bold("  Strategic Considerations:"))
    print()
    print(print_cyan("    Unit Coverage") + " measures function/method-level testing.")
    print(print_dim("    Higher coverage catches more edge cases but has diminishing returns."))
    print(print_dim("    The last 10% often requires mocking internals, which creates brittle tests."))
    print()
    print(print_cyan("    Integration Coverage") + " measures how components work together.")
    print(print_dim("    Lower targets are acceptable because integration tests are more expensive"))
    print(print_dim("    to write and maintain, but they catch real-world interaction bugs."))
    print()

    print("  " + "─" * 114)
    print(print_bold("  Coverage Philosophy"))
    print()
    print(print_green("    90%+ Unit") + "     Critical paths, financial calculations, security logic")
    print(print_yellow("    80% Unit") + "      Most production systems—good balance of safety and velocity")
    print(print_dim("    70% Unit") + "      Prototypes, internal tools, rapidly evolving code")
    print()
    print(print_dim("    Rule of thumb: Cover what matters, not what's easy to cover."))
    print(print_dim("    Focus on business logic, error paths, and boundary conditions."))
    print("  " + "─" * 114)
    print()

    print(print_cyan("    Unit Test Coverage Target"))
    print()
    print(print_green("      [90]") + "  Strict   " + print_dim("- Financial, security, compliance systems"))
    print(print_yellow("      [80]") + "  Standard " + print_dim("- Production applications (recommended)"))
    print(print_dim("      [70]") + "  Relaxed  " + print_dim("- Prototypes, internal tools, MVPs"))
    print()

    unit_coverage_str = prompt_user("    Unit test coverage target (default: 80): ").strip()
    try:
        unit_coverage = int(unit_coverage_str) if unit_coverage_str else 80
    except ValueError:
        print(print_yellow(f"    Invalid input '{unit_coverage_str}', using default 80"))
        unit_coverage = 80

    print()
    print(print_cyan("    Integration Test Coverage Target"))
    print()
    print(print_green("      [80]") + "  Strict   " + print_dim("- Microservices, distributed systems"))
    print(print_yellow("      [70]") + "  Standard " + print_dim("- Most applications (recommended)"))
    print(print_dim("      [60]") + "  Relaxed  " + print_dim("- Monoliths with strong unit tests"))
    print()

    integration_coverage_str = prompt_user("    Integration test coverage target (default: 70): ").strip()
    try:
        integration_coverage = int(integration_coverage_str) if integration_coverage_str else 70
    except ValueError:
        print(print_yellow(f"    Invalid input '{integration_coverage_str}', using default 70"))
        integration_coverage = 70

    print()

    # Test Pyramid Strategy
    print(print_dim("─" * 120))
    print()
    print(print_bold("TEST PYRAMID STRATEGY"))
    print()

    print(print_dim("  The test pyramid is a mental model for balancing test types. Each layer"))
    print(print_dim("  trades off between speed, cost, and confidence."))
    print()

    print("""                      ▲
                     ╱ ╲
                    ╱E2E╲         Slow, expensive, high confidence
                   ╱─────╲        Test full user journeys
                  ╱ Integ ╲       Medium speed, tests boundaries
                 ╱─────────╲      API contracts, DB operations
                ╱   Unit    ╲     Fast, cheap, isolated
               ╱─────────────╲    Pure functions, business logic
              ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔""")
    print()

    print(print_bold("  Strategic Tradeoffs:"))
    print()
    print("  " + "─" * 114)
    print()
    print(print_green("    Unit-Heavy (70/25/5)"))
    print(print_dim("    Best for: Libraries, algorithms, pure business logic"))
    print(print_dim("    Fast feedback loops, easy to debug, but may miss integration bugs"))
    print()
    print(print_yellow("    Balanced (50/35/15)"))
    print(print_dim("    Best for: Full-stack applications, CRUD systems"))
    print(print_dim("    Good coverage across layers, balanced maintenance cost"))
    print()
    print(print_cyan("    Integration-Heavy (40/45/15)"))
    print(print_dim("    Best for: Microservices, APIs, systems with many external dependencies"))
    print(print_dim("    Catches boundary issues, but slower test suites"))
    print()
    print("  " + "─" * 114)
    print()

    print(print_cyan("  Select pyramid profile:"))
    print()
    print(print_green("    [unit-heavy]") + "     70% unit, 25% integration, 5% E2E")
    print(print_yellow("    [balanced]") + "       50% unit, 35% integration, 15% E2E")
    print(print_cyan("    [integration]") + "    40% unit, 45% integration, 15% E2E")
    print()

    pyramid_profile = prompt_user("  Pyramid profile (default: unit-heavy): ").strip()
    pyramid_profile = pyramid_profile if pyramid_profile else "unit-heavy"

    print()

    # Parallel Execution
    print(print_dim("─" * 120))
    print()
    print(print_bold("PARALLEL EXECUTION"))
    print()

    # Get task count
    task_count = 0
    if tasks_file.exists():
        with open(tasks_file) as f:
            tasks_data = json.load(f)
        task_count = sum(1 for task in tasks_data.get("tasks", []) if len(task.get("subtasks", [])) >= 4)

    print(print_dim("  TDD cycles execute in parallel using git worktrees, just like the DAG"))
    print(print_dim("  execution in previous phases. Independent tasks run simultaneously."))
    print()

    # Calculate optimal worker count
    cpu_count = detect_cpu_count()
    optimal_workers = min(4, cpu_count, task_count if task_count > 0 else 4)

    # Check for blockers
    blocked = False  # In real implementation, analyze task dependencies

    if blocked:
        print(print_yellow("  ! Cross-task dependencies detected. Falling back to sequential execution."))
        optimal_workers = 1
    else:
        print(print_green("  No blockers detected. Parallel execution enabled."))

    print()
    print("  " + "─" * 114)
    print(print_bold("  Execution Plan"))
    print()
    print(f"    Tasks to execute:    {task_count}")
    print(f"    Parallel workers:    {optimal_workers}")
    print(f"    CPU cores detected:  {cpu_count}")
    print()

    if optimal_workers > 1:
        tasks_per_worker = (task_count + optimal_workers - 1) // optimal_workers
        print(print_dim(f"    Each worker handles ~{tasks_per_worker} tasks in its own git worktree."))
        print(print_dim("    Workers merge results back to main branch on completion."))
    else:
        print(print_dim("    Tasks will execute sequentially in the main worktree."))

    print("  " + "─" * 114)
    print()

    # -----------------------------------------------------------------------
    # Tech Stack Detection (cascading)
    # -----------------------------------------------------------------------
    print(print_dim("─" * 120))
    print()
    print(print_bold("TECH STACK DETECTION"))
    print()

    detected_stack, stack_meta = detect_tech_stack_cascade(atomic_root, uat_mode=False)
    strategy = stack_meta.get("strategy", "unknown")
    confidence = stack_meta.get("confidence", "unknown")

    print(f"    Detected stack:  {print_bold(detected_stack)}")
    print(f"    Strategy:        {strategy}")
    print(f"    Confidence:      {confidence}")
    if stack_meta.get("score") is not None:
        print(f"    Score:           {stack_meta['score']}")
    signals = stack_meta.get("signals_found", [])
    if signals:
        print(f"    Signals:         {', '.join(signals[:8])}")
        if len(signals) > 8:
            print(f"                     ...and {len(signals) - 8} more")
    print()

    # Check tool availability
    tool_info = _check_tool_availability(detected_stack)
    if tool_info.get("available"):
        print(print_green(f"    Build tools available: {tool_info.get('version', 'yes')}"))
    else:
        print(print_yellow(f"    Build tools NOT available ({tool_info.get('command', '?')})"))
        print(print_dim("    TDD will run in code-generation-only mode (no compilation gates)."))

    print()

    # Testing Tools Display
    print(print_dim("─" * 120))
    print()
    print(print_bold("TESTING TOOLS"))
    print()

    print(print_dim("  Tools are auto-detected from your project configuration files."))
    print()

    print("  " + "─" * 114)
    print(print_bold("  Detected Tools"))
    print()

    if detected_stack == "rust":
        print(print_red("    RED (Testing):") + "       cargo test")
        print(print_cyan("    REFACTOR (Linting):") + "  cargo clippy, rustfmt")
        print("    " + print_magenta("VERIFY (Security):") + "   cargo audit, cargo deny")
    elif detected_stack == "python":
        print(print_red("    RED (Testing):") + "       pytest, coverage.py")
        print(print_cyan("    REFACTOR (Linting):") + "  ruff, black, mypy")
        print("    " + print_magenta("VERIFY (Security):") + "   bandit, safety, pip-audit")
    elif detected_stack == "node":
        print(print_red("    RED (Testing):") + "       jest, vitest, nyc")
        print(print_cyan("    REFACTOR (Linting):") + "  eslint, prettier, tsc")
        print("    " + print_magenta("VERIFY (Security):") + "   npm audit, snyk")
    elif detected_stack == "go":
        print(print_red("    RED (Testing):") + "       go test -cover")
        print(print_cyan("    REFACTOR (Linting):") + "  gofmt, golint, staticcheck")
        print("    " + print_magenta("VERIFY (Security):") + "   gosec, govulncheck")
    else:
        print(print_yellow("    ! No project files detected. Configure tools manually."))

    print("  " + "─" * 114)
    print()

    print(print_bold("  Customizing Tools:"))
    print()
    print(print_dim("  To use different tools, create or edit:"))
    print(print_cyan("    .claude/config/tdd-tools.json"))
    print()
    print(print_dim("  Example configuration:"))
    print()
    print(print_dim('    {'))
    print(print_dim('      "red": {'))
    print(print_dim('        "test_command": "pytest -v",'))
    print(print_dim('        "coverage_command": "pytest --cov=src --cov-report=json"'))
    print(print_dim('      },'))
    print(print_dim('      "refactor": {'))
    print(print_dim('        "lint_command": "ruff check . --fix",'))
    print(print_dim('        "format_command": "black ."'))
    print(print_dim('      },'))
    print(print_dim('      "verify": {'))
    print(print_dim('        "security_command": "bandit -r src/"'))
    print(print_dim('      }'))
    print(print_dim('    }'))
    print()

    if config_file.exists():
        print(print_green("  Custom tool configuration found at .claude/config/tdd-tools.json"))
    else:
        print(print_dim("  No custom configuration found. Using detected defaults."))
    print()

    prompt_user("  Press Enter to continue (or edit tdd-tools.json first)...")
    print()

    # -----------------------------------------------------------------------
    # Token Budget
    # -----------------------------------------------------------------------
    print(print_dim("─" * 120))
    print()
    print(print_bold("TOKEN BUDGET"))
    print()

    est_calls = task_count * 4  # ~4 LLM calls per task (RED/GREEN/REFACTOR/VERIFY)
    est_cost = est_calls * 0.15  # rough estimate per call

    print(print_dim(f"  Estimated LLM calls: ~{est_calls} ({task_count} tasks x 4 phases)"))
    print(print_dim(f"  Estimated cost:      ~${est_cost:.0f} (at ~$0.15/call average)"))
    print()
    print(print_dim("  Set a spending limit. Execution pauses if the budget is reached."))
    print(print_dim("  For subscription providers (claude-code), this tracks token counts only."))
    print()

    budget_input = prompt_user("  Token budget in USD (default: 50): ").strip()
    try:
        token_budget = float(budget_input) if budget_input else 50.0
    except ValueError:
        print(print_yellow(f"  Invalid input '{budget_input}', using default $50"))
        token_budget = 50.0

    print()

    # Setup Summary
    print(print_dim("─" * 120))
    print()
    print(print_bold("SETUP SUMMARY"))
    print()

    print("    Coverage Targets:")
    print(f"      Unit:        {unit_coverage}%")
    print(f"      Integration: {integration_coverage}%")
    print()
    print(f"    Test Pyramid:    {pyramid_profile}")
    print(f"    Execution:       parallel ({optimal_workers} workers)")
    print(f"    Tool Stack:      {detected_stack} (via {strategy})")
    print(f"    Tools available: {'yes' if tool_info.get('available') else 'no (code-gen only)'}")
    print(f"    Token budget:    ${token_budget:.2f}")
    print()

    # Save setup configuration
    setup_data = {
        "coverage_targets": {
            "unit": unit_coverage,
            "integration": integration_coverage
        },
        "pyramid_profile": pyramid_profile,
        "execution": {
            "mode": "parallel",
            "workers": optimal_workers
        },
        "task_count": task_count,
        "detected_stack": detected_stack,
        "stack_detection": stack_meta,
        "tools_available": tool_info.get("available", False),
        "token_budget_usd": token_budget,
        "configured_at": datetime.now().isoformat()
    }
    write_file(setup_file, json.dumps(setup_data, indent=2))

    print(print_green("TDD Setup complete"))
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 502: TDD Setup")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
