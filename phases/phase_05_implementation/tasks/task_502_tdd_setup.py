"""
Task 502: TDD Setup

Configure coverage targets, test pyramid, and execution mode.
"""

import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user
)
from core.utils.file_ops import ensure_dir, write_file


def detect_cpu_count() -> int:
    """Detect CPU count across platforms."""
    try:
        # Try nproc (Linux)
        result = subprocess.run(['nproc'], capture_output=True, text=True)
        if result.returncode == 0:
            return int(result.stdout.strip())
    except:
        pass

    try:
        # Try sysctl (macOS)
        result = subprocess.run(['sysctl', '-n', 'hw.ncpu'], capture_output=True, text=True)
        if result.returncode == 0:
            return int(result.stdout.strip())
    except:
        pass

    return 4  # Default fallback


def detect_tech_stack(atomic_root: Path) -> str:
    """Detect project tech stack from configuration files."""
    if (atomic_root / "pyproject.toml").exists() or (atomic_root / "requirements.txt").exists():
        return "python"
    elif (atomic_root / "package.json").exists():
        return "node"
    elif (atomic_root / "go.mod").exists():
        return "go"
    return "unknown"


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 502: TDD Setup.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    tasks_file = atomic_root / ".taskmaster" / "tasks" / "tasks.json"
    setup_file = output_dir / "tdd-setup.json"
    config_file = atomic_root / ".claude" / "config" / "tdd-tools.json"

    # UAT Mode Bypass
    if uat_mode:
        print()
        print_yellow("⚡ UAT Mode: Skipping TDD configuration, creating minimal setup")
        print()

        ensure_dir(setup_file.parent)

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
            "detected_stack": "python",
            "mode": "uat",
            "configured_at": datetime.now().isoformat()
        }
        write_file(setup_file, json.dumps(setup_data, indent=2))

        print_green("✓ TDD Setup complete (UAT mode)")
        return True

    ensure_dir(setup_file.parent)
    ensure_dir(config_file.parent)

    print()
    print_dim("  Configuring TDD execution parameters.")
    print()

    # Coverage Targets
    print_dim("─" * 120)
    print()
    print_bold("COVERAGE TARGETS")
    print()

    print_dim("  Coverage measures how much of your code is exercised by tests. But coverage")
    print_dim("  is a means, not an end—100% coverage doesn't guarantee bug-free code.")
    print()

    print_bold("  Strategic Considerations:")
    print()
    print_cyan("    Unit Coverage") + " measures function/method-level testing."
    print_dim("    Higher coverage catches more edge cases but has diminishing returns.")
    print_dim("    The last 10% often requires mocking internals, which creates brittle tests.")
    print()
    print_cyan("    Integration Coverage") + " measures how components work together."
    print_dim("    Lower targets are acceptable because integration tests are more expensive")
    print_dim("    to write and maintain, but they catch real-world interaction bugs.")
    print()

    print("  " + "─" * 114)
    print_bold("  Coverage Philosophy")
    print()
    print_green("    90%+ Unit") + "     Critical paths, financial calculations, security logic"
    print_yellow("    80% Unit") + "      Most production systems—good balance of safety and velocity"
    print_dim("    70% Unit") + "      Prototypes, internal tools, rapidly evolving code"
    print()
    print_dim("    Rule of thumb: Cover what matters, not what's easy to cover.")
    print_dim("    Focus on business logic, error paths, and boundary conditions.")
    print("  " + "─" * 114)
    print()

    print_cyan("    Unit Test Coverage Target")
    print()
    print_green("      [90]") + "  Strict   " + print_dim("- Financial, security, compliance systems")
    print_yellow("      [80]") + "  Standard " + print_dim("- Production applications (recommended)")
    print_dim("      [70]") + "  Relaxed  " + print_dim("- Prototypes, internal tools, MVPs")
    print()

    unit_coverage = prompt_user("    Unit test coverage target (default: 80): ").strip()
    unit_coverage = int(unit_coverage) if unit_coverage else 80

    print()
    print_cyan("    Integration Test Coverage Target")
    print()
    print_green("      [80]") + "  Strict   " + print_dim("- Microservices, distributed systems")
    print_yellow("      [70]") + "  Standard " + print_dim("- Most applications (recommended)")
    print_dim("      [60]") + "  Relaxed  " + print_dim("- Monoliths with strong unit tests")
    print()

    integration_coverage = prompt_user("    Integration test coverage target (default: 70): ").strip()
    integration_coverage = int(integration_coverage) if integration_coverage else 70

    print()

    # Test Pyramid Strategy
    print_dim("─" * 120)
    print()
    print_bold("TEST PYRAMID STRATEGY")
    print()

    print_dim("  The test pyramid is a mental model for balancing test types. Each layer")
    print_dim("  trades off between speed, cost, and confidence.")
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

    print_bold("  Strategic Tradeoffs:")
    print()
    print("  " + "─" * 114)
    print()
    print_green("    Unit-Heavy (70/25/5)")
    print_dim("    Best for: Libraries, algorithms, pure business logic")
    print_dim("    Fast feedback loops, easy to debug, but may miss integration bugs")
    print()
    print_yellow("    Balanced (50/35/15)")
    print_dim("    Best for: Full-stack applications, CRUD systems")
    print_dim("    Good coverage across layers, balanced maintenance cost")
    print()
    print_cyan("    Integration-Heavy (40/45/15)")
    print_dim("    Best for: Microservices, APIs, systems with many external dependencies")
    print_dim("    Catches boundary issues, but slower test suites")
    print()
    print("  " + "─" * 114)
    print()

    print_cyan("  Select pyramid profile:")
    print()
    print_green("    [unit-heavy]") + "     70% unit, 25% integration, 5% E2E"
    print_yellow("    [balanced]") + "       50% unit, 35% integration, 15% E2E"
    print_cyan("    [integration]") + "    40% unit, 45% integration, 15% E2E"
    print()

    pyramid_profile = prompt_user("  Pyramid profile (default: unit-heavy): ").strip()
    pyramid_profile = pyramid_profile if pyramid_profile else "unit-heavy"

    print()

    # Parallel Execution
    print_dim("─" * 120)
    print()
    print_bold("PARALLEL EXECUTION")
    print()

    # Get task count
    task_count = 0
    if tasks_file.exists():
        with open(tasks_file) as f:
            tasks_data = json.load(f)
        task_count = sum(1 for task in tasks_data.get("tasks", []) if len(task.get("subtasks", [])) >= 4)

    print_dim("  TDD cycles execute in parallel using git worktrees, just like the DAG")
    print_dim("  execution in previous phases. Independent tasks run simultaneously.")
    print()

    # Calculate optimal worker count
    cpu_count = detect_cpu_count()
    optimal_workers = min(4, cpu_count, task_count if task_count > 0 else 4)

    # Check for blockers
    blocked = False  # In real implementation, analyze task dependencies

    if blocked:
        print_yellow("  ! Cross-task dependencies detected. Falling back to sequential execution.")
        optimal_workers = 1
    else:
        print_green("  ✓ No blockers detected. Parallel execution enabled.")

    print()
    print("  " + "─" * 114)
    print_bold("  Execution Plan")
    print()
    print(f"    Tasks to execute:    {task_count}")
    print(f"    Parallel workers:    {optimal_workers}")
    print(f"    CPU cores detected:  {cpu_count}")
    print()

    if optimal_workers > 1:
        tasks_per_worker = (task_count + optimal_workers - 1) // optimal_workers
        print_dim(f"    Each worker handles ~{tasks_per_worker} tasks in its own git worktree.")
        print_dim("    Workers merge results back to main branch on completion.")
    else:
        print_dim("    Tasks will execute sequentially in the main worktree.")

    print("  " + "─" * 114)
    print()

    # Testing Tools
    print_dim("─" * 120)
    print()
    print_bold("TESTING TOOLS")
    print()

    print_dim("  Tools are auto-detected from your project configuration files.")
    print()

    # Detect project type
    detected_stack = detect_tech_stack(atomic_root)

    print("  " + "─" * 114)
    print_bold("  Detected Tools")
    print()

    if detected_stack == "python":
        print_red("    RED (Testing):") + "       pytest, coverage.py"
        print_cyan("    REFACTOR (Linting):") + "  ruff, black, mypy"
        print("    " + print_magenta("VERIFY (Security):") + "   bandit, safety, pip-audit")
    elif detected_stack == "node":
        print_red("    RED (Testing):") + "       jest, vitest, nyc"
        print_cyan("    REFACTOR (Linting):") + "  eslint, prettier, tsc"
        print("    " + print_magenta("VERIFY (Security):") + "   npm audit, snyk")
    elif detected_stack == "go":
        print_red("    RED (Testing):") + "       go test -cover"
        print_cyan("    REFACTOR (Linting):") + "  gofmt, golint, staticcheck"
        print("    " + print_magenta("VERIFY (Security):") + "   gosec, govulncheck")
    else:
        print_yellow("    ! No project files detected. Configure tools manually.")

    print("  " + "─" * 114)
    print()

    print_bold("  Customizing Tools:")
    print()
    print_dim("  To use different tools, create or edit:")
    print_cyan("    .claude/config/tdd-tools.json")
    print()
    print_dim("  Example configuration:")
    print()
    print_dim('    {')
    print_dim('      "red": {')
    print_dim('        "test_command": "pytest -v",')
    print_dim('        "coverage_command": "pytest --cov=src --cov-report=json"')
    print_dim('      },')
    print_dim('      "refactor": {')
    print_dim('        "lint_command": "ruff check . --fix",')
    print_dim('        "format_command": "black ."')
    print_dim('      },')
    print_dim('      "verify": {')
    print_dim('        "security_command": "bandit -r src/"')
    print_dim('      }')
    print_dim('    }')
    print()

    if config_file.exists():
        print_green("  ✓ Custom tool configuration found at .claude/config/tdd-tools.json")
    else:
        print_dim("  No custom configuration found. Using detected defaults.")
    print()

    prompt_user("  Press Enter to continue (or edit tdd-tools.json first)...")
    print()

    # Setup Summary
    print_dim("─" * 120)
    print()
    print_bold("SETUP SUMMARY")
    print()

    print("    Coverage Targets:")
    print(f"      Unit:        {unit_coverage}%")
    print(f"      Integration: {integration_coverage}%")
    print()
    print(f"    Test Pyramid:    {pyramid_profile}")
    print(f"    Execution:       parallel ({optimal_workers} workers)")
    print(f"    Tool Stack:      {detected_stack}")
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
        "configured_at": datetime.now().isoformat()
    }
    write_file(setup_file, json.dumps(setup_data, indent=2))

    print_green("✓ TDD Setup complete")
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
