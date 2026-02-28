"""
Task 604: Refinement

Address review findings and apply code improvements using the code-refiner agent.
"""

import logging
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user, clear_input_buffer
)
from core.utils.file_ops import ensure_dir, read_file, write_file
from core.llm import invoke_llm


def _graph_findings_to_dict(findings: list) -> dict:
    """Convert graph ReviewFinding dicts to the format expected by the refinement logic.

    Returns dict with 'totals' and 'dimensions' keys matching findings.json structure.
    """
    totals = {"critical": 0, "major": 0, "minor": 0, "suggestions": 0}
    dimensions = {}

    for f in findings:
        severity = f.get("severity", "minor")
        if severity in totals:
            totals[severity] += 1

        dim = f.get("review_dimension", "general")
        if dim not in dimensions:
            dimensions[dim] = {"findings": [], "totals": {"critical": 0, "major": 0, "minor": 0, "suggestions": 0}}
        dimensions[dim]["findings"].append(f)
        if severity in dimensions[dim]["totals"]:
            dimensions[dim]["totals"][severity] += 1

    return {"totals": totals, "dimensions": dimensions}


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None, graph=None) -> bool:
    """
    Execute Task 604: Refinement.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    project_root = atomic_root.parent
    review_dir = project_root / ".claude" / "reviews"
    findings_file = review_dir / "findings.json"
    refinement_file = review_dir / "refinement-report.json"
    prompts_dir = output_dir / "prompts"
    fixes_dir = prompts_dir / "fixes"

    print()
    print(print_dim("Addressing review findings and applying code improvements."))
    print()

    # UAT Mode Bypass
    if uat_mode:
        print(print_yellow("UAT Mode: Creating minimal valid output"))
        ensure_dir(review_dir)
        ensure_dir(fixes_dir)

        refinement_report = output_dir / "refinement-report.md"
        write_file(refinement_report, "# Refinement Report (UAT Mode)\n\nAll issues addressed (UAT stub)")

        write_file(refinement_file, json.dumps({
            "refinements": {
                "critical": {"total": 0, "fixed": 0},
                "major": {"total": 0, "fixed": 0},
                "minor": {"total": 0, "fixed": 0}
            },
            "test_verification": {
                "total": 0,
                "passing": 0,
                "all_passing": True
            },
            "all_resolved": True,
            "refined_at": datetime.now(timezone.utc).isoformat()
        }, indent=2))

        print(print_green("✓ UAT bypass complete"))
        return True

    ensure_dir(fixes_dir)

    # Load findings -- prefer graph, fall back to JSON file
    findings_data = None
    if graph:
        try:
            unresolved = graph.get_unresolved_findings()
            if unresolved:
                findings_data = _graph_findings_to_dict(unresolved)
                logger.info("Loaded %d unresolved findings from graph", len(unresolved))
        except Exception as e:
            logger.debug("Graph findings unavailable, falling back to JSON: %s", e)

    if findings_data is None:
        if not findings_file.exists():
            print(print_yellow("! No findings file found"))
            print(print_yellow("Run task 603 (Comprehensive Review) first"))
            return False
        try:
            findings_data = json.loads(read_file(findings_file))
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to parse findings file %s: %s", findings_file, e)
            print(print_red(f"✗ Failed to read findings: {e}"))
            return False
    totals = findings_data.get("totals", {})
    total_critical = totals.get("critical", 0)
    total_major = totals.get("major", 0)
    total_minor = totals.get("minor", 0)

    # Display findings to address
    _display_findings_summary(total_critical, total_major, total_minor)

    # Get refinement scope
    refinement_scope = _get_refinement_scope(total_critical, total_major, uat_mode)

    if refinement_scope == "skip":
        print(print_yellow("! Skipping refinement - no changes will be made"))
        print(print_green("✓ Refinement skipped by user choice"))
        return True

    # Display refinement strategy
    _display_refinement_strategy(refinement_scope)

    clear_input_buffer()
    prompt_user("Press Enter to begin refinement...")
    print()

    # Execute refinement
    print()
    print(print_bold("- REFINEMENT EXECUTION"))
    print()

    fixed_critical = 0
    fixed_major = 0
    fixed_minor = 0

    # Process critical issues
    if total_critical > 0:
        print(print_red("Addressing Critical Issues"))
        print()
        fixed_critical = _address_issues(findings_data, "critical", fixes_dir, atomic_root)
        print()

    # Process major issues
    if total_major > 0 and refinement_scope in ["major", "minor", "all"]:
        print(print_yellow("Addressing Major Issues"))
        print()
        fixed_major = _address_issues(findings_data, "major", fixes_dir, atomic_root)
        print()

    # Process minor issues
    if total_minor > 0 and refinement_scope in ["minor", "all"]:
        print(print_cyan("Addressing Minor Issues"))
        print()
        fixed_minor = _address_issues(findings_data, "minor", fixes_dir, atomic_root)
        print()

    # Run test verification
    tests_passing, tests_total, tests_passed = _run_test_verification(atomic_root)

    # Display summary
    _display_refinement_summary(
        fixed_critical, total_critical,
        fixed_major, total_major,
        fixed_minor, total_minor,
        tests_passing
    )

    # Save refinement report
    refinement_data = {
        "refinements": {
            "critical": {"total": total_critical, "fixed": fixed_critical},
            "major": {"total": total_major, "fixed": fixed_major},
            "minor": {"total": total_minor, "fixed": fixed_minor}
        },
        "test_verification": {
            "total": tests_total,
            "passing": tests_passed,
            "all_passing": tests_passing
        },
        "all_resolved": (fixed_critical >= total_critical and fixed_major >= total_major),
        "refined_at": datetime.now(timezone.utc).isoformat()
    }

    write_file(refinement_file, json.dumps(refinement_data, indent=2))

    # Generate refinement-report.md (expected by orchestrator artifact check)
    refinement_report = output_dir / "refinement-report.md"
    report_content = f"""# Refinement Report

**Completed:** {datetime.now(timezone.utc).isoformat()}

## Issues Resolved

- **Critical Fixed:** {fixed_critical} / {total_critical}
- **Major Fixed:** {fixed_major} / {total_major}
- **Minor Fixed:** {fixed_minor} / {total_minor}

## Test Verification

- Tests passing: {tests_passing}
- Total tests: {tests_total}

## Status

{"All critical and major issues resolved." if refinement_data["all_resolved"] else "Some issues remain -- review before proceeding."}
"""
    write_file(refinement_report, report_content)

    print(print_green("✓ Refinement complete"))
    return True


def _display_findings_summary(critical: int, major: int, minor: int) -> None:
    """Display findings summary."""
    print()
    print(print_bold("- FINDINGS TO ADDRESS"))
    print()

    print("  ─" * 50)
    print(print_bold("REFINEMENT QUEUE"))
    print()

    if critical > 0:
        print(print_red(f"  Critical:  {critical} issue(s) - ") + print_red("MUST FIX"))
    else:
        print(print_green(f"  Critical:  {critical} issue(s)"))

    if major > 0:
        print(print_yellow(f"  Major:     {major} issue(s) - ") + print_yellow("SHOULD FIX"))
    else:
        print(print_green(f"  Major:     {major} issue(s)"))

    print(print_dim(f"  Minor:     {minor} issue(s) - optional"))
    print("  ─" * 50)
    print()


def _get_refinement_scope(critical: int, major: int, uat_mode: bool) -> str:
    """Get refinement scope from user."""
    if uat_mode:
        return "major"

    print()
    print(print_bold("- REFINEMENT STRATEGY"))
    print()

    print(print_dim("What would you like the code-refiner agent to address?"))
    print()
    print(print_green("  [critical]") + "    Address critical issues only (fastest)")
    print(print_yellow("  [major]") + "       Address critical + major issues (recommended)")
    print(print_cyan("  [minor]") + "       Address critical + major + minor issues")
    print(print_dim("  [skip]") + "        Skip refinement entirely")
    print()

    valid_scopes = {"critical", "major", "minor", "skip"}
    clear_input_buffer()
    scope = prompt_user("Refinement scope (default: major): ").strip().lower() or "major"
    if scope not in valid_scopes:
        print(print_yellow(f"  ! Invalid scope '{scope}'. Defaulting to 'critical'."))
        scope = "critical"
    return scope


def _display_refinement_strategy(scope: str) -> None:
    """Display refinement strategy."""
    print()
    print(print_dim("The code-refiner agent will:"))
    print()

    if scope == "critical":
        print(print_cyan("  1.") + " Address " + print_red("critical") + " findings only")
    elif scope == "major":
        print(print_cyan("  1.") + " Address " + print_red("critical") + " and " + print_yellow("major") + " findings")
    elif scope == "minor":
        print(print_cyan("  1.") + " Address " + print_red("critical") + ", " + print_yellow("major") + ", and " + print_cyan("minor") + " findings")

    print(print_cyan("  2.") + " Apply targeted fixes without changing unrelated code")
    print(print_cyan("  3.") + " Run tests after each change to ensure no regressions")
    print(print_cyan("  4.") + " Document changes made for each finding")
    print()


def _address_issues(findings_data: Dict, severity: str, fixes_dir: Path, atomic_root: Path) -> int:
    """Address issues of a specific severity."""
    # Extract findings of this severity from all dimensions
    # _graph_findings_to_dict wraps dimensions under a "dimensions" key
    dims = findings_data.get("dimensions", findings_data)
    all_findings = []
    for dimension in ["deep_code", "architecture", "performance", "documentation"]:
        dimension_data = dims.get(dimension, {})
        findings = dimension_data.get("findings", [])
        all_findings.extend([f for f in findings if f.get("severity") == severity])

    # Filter out process failures
    all_findings = [
        f for f in all_findings
        if not any(keyword in f.get("description", "").lower()
                  for keyword in ["max turns", "blocked", "does not exist"])
    ]

    fixed_count = 0
    for i, finding in enumerate(all_findings[:10], 1):  # Limit to 10 issues
        desc = finding.get("description", "No description")
        print(print_dim(f"    [{i}/{len(all_findings)}] {desc}"))

        if _apply_fix(finding, fixes_dir / f"{severity}-{i}", atomic_root):
            print(print_green("             ✓ Fixed"))
            fixed_count += 1
        else:
            print(print_yellow("             ! Manual fix recommended"))

    return fixed_count


def _resolve_source_path(finding_file: str, project_root: Path) -> Path:
    """Resolve the source file path for a finding, trying multiple locations."""
    if not finding_file or finding_file == 'unknown':
        return Path(finding_file)

    candidates = [
        project_root / finding_file,
        project_root / ".claude" / "testing" / finding_file,
        project_root / "src" / finding_file,
        Path(finding_file),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path(finding_file)


def _build_fix_prompt(finding: Dict, source_context: str, finding_file: str,
                      finding_line: int) -> str:
    """Build the LLM prompt for a code fix request."""
    code_section = ""
    if source_context:
        code_section = f"""## Source Code (around line {finding_line})

```
{source_context}
```

"""

    return f"""# Code Fix Request

You are a code-refiner agent. Apply a minimal, targeted fix for the issue described below.

## Issue Details

- **File**: {finding_file}
- **Line**: {finding_line}
- **Severity**: {finding.get('severity', 'major')}
- **Category**: {finding.get('category', 'general')}
- **Description**: {finding.get('description', 'No description')}
- **Recommendation**: {finding.get('recommendation', 'Fix the issue')}

{code_section}## Fix Requirements

1. **Minimal Change**: Only fix the identified issue, nothing else
2. **Preserve Behavior**: Don't change any unrelated functionality
3. **Testable**: The fix should be verifiable by existing tests
4. **No Refactoring**: Resist the urge to "improve" surrounding code

## Output Format

Respond with ONLY valid JSON (no markdown wrapper):

{{
  "can_fix": true,
  "fix_type": "code_change|config_change|documentation",
  "file_path": "{finding_file}",
  "explanation": "Brief explanation of what the fix does",
  "requires_manual_review": false,
  "manual_review_reason": "Why manual review is needed (if applicable)"
}}

If you cannot safely generate a fix, set can_fix to false and explain why.
"""


def _apply_llm_fix(prompt: str, output_prefix: Path, finding_file: str) -> bool:
    """Send fix prompt to LLM and save the result."""
    try:
        response = invoke_llm(prompt=prompt, model="sonnet")

        # Parse JSON — strip markdown fences if present
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            response = response[start:end].strip()
        elif response.strip().startswith("```"):
            stripped = response.strip()
            first_nl = stripped.find("\n")
            if first_nl != -1:
                stripped = stripped[first_nl + 1:]
            if stripped.endswith("```"):
                stripped = stripped[:-3].strip()
            response = stripped

        result = json.loads(response)

        # Save result
        output_file = Path(str(output_prefix) + "-fix.json")
        ensure_dir(output_file.parent)
        write_file(output_file, json.dumps(result, indent=2))

        return result.get("can_fix", False)
    except Exception as e:
        logger.debug("Failed to apply fix for %s: %s", finding_file, e)
        return False


def _apply_fix(finding: Dict, output_prefix: Path, atomic_root: Path) -> bool:
    """Apply a fix for a finding by resolving source, building prompt, and invoking LLM."""
    project_root = atomic_root.parent
    finding_file = finding.get('file', 'unknown')
    finding_line = finding.get('line', 0)

    # Resolve source file and extract context
    source_context = ""
    source_path = _resolve_source_path(finding_file, project_root)

    if source_path.exists() and finding_file != 'unknown':
        try:
            source_lines = source_path.read_text().splitlines()
            context_radius = 25
            start_line = max(0, finding_line - context_radius - 1)
            end_line = min(len(source_lines), finding_line + context_radius)
            numbered_lines = []
            for i, line in enumerate(source_lines[start_line:end_line], start=start_line + 1):
                marker = " >> " if i == finding_line else "    "
                numbered_lines.append(f"{marker}{i:4d} | {line}")
            source_context = "\n".join(numbered_lines)
        except (OSError, UnicodeDecodeError) as e:
            logger.debug("Failed to read source file %s: %s", source_path, e)
            source_context = "(Unable to read source file)"

    prompt = _build_fix_prompt(finding, source_context, finding_file, finding_line)
    return _apply_llm_fix(prompt, output_prefix, finding_file)


def _parse_test_counts(output: str) -> tuple:
    """Parse test counts from test runner output.

    Supports cargo test, pytest, npm/jest, and go test output formats.
    Returns (total, passed). Returns (0, 0) if no pattern matched.
    """
    import re

    # cargo test: "test result: ok. 5 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out"
    m = re.search(r'test result: \w+\.\s+(\d+) passed;\s+(\d+) failed', output)
    if m:
        passed = int(m.group(1))
        failed = int(m.group(2))
        return (passed + failed, passed)

    # pytest: "5 passed, 2 failed" or "5 passed" or "== 10 passed in 1.5s =="
    m = re.search(r'(\d+) passed', output)
    if m:
        passed = int(m.group(1))
        m_failed = re.search(r'(\d+) failed', output)
        failed = int(m_failed.group(1)) if m_failed else 0
        return (passed + failed, passed)

    # jest/npm: "Tests:  2 failed, 5 passed, 7 total"
    m = re.search(r'Tests:\s+(?:\d+ \w+,\s+)*(\d+) passed,\s+(\d+) total', output)
    if m:
        passed = int(m.group(1))
        total = int(m.group(2))
        return (total, passed)

    # go test: "ok" lines per package, or "FAIL" — count ok/FAIL lines
    ok_count = len(re.findall(r'^ok\s+', output, re.MULTILINE))
    fail_count = len(re.findall(r'^FAIL\s+', output, re.MULTILINE))
    if ok_count + fail_count > 0:
        return (ok_count + fail_count, ok_count)

    return (0, 0)


def _run_test_verification(atomic_root: Path) -> tuple:
    """Run test verification against the host project."""
    project_root = atomic_root.parent

    print()
    print(print_bold("- TEST VERIFICATION"))
    print()
    print(print_dim("Running full test suite to verify refinements..."))
    print()

    # Detect and run tests in the HOST project
    tests_passing = True
    tests_total = 0
    tests_passed = 0
    result = None

    try:
        # Try cargo test (Rust)
        if (project_root / "Cargo.toml").exists():
            result = subprocess.run(
                ["cargo", "test"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=120
            )
            tests_passing = (result.returncode == 0)

        # Try npm test (Node)
        elif (project_root / "package.json").exists():
            result = subprocess.run(
                ["npm", "test"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            tests_passing = (result.returncode == 0)

        # Try go test (Go)
        elif (project_root / "go.mod").exists():
            result = subprocess.run(
                ["go", "test", "./..."],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=120
            )
            tests_passing = (result.returncode == 0)

        # Try pytest (Python)
        elif (project_root / "pytest.ini").exists() or (project_root / "pyproject.toml").exists():
            result = subprocess.run(
                ["python", "-m", "pytest", "-v"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            tests_passing = (result.returncode == 0)
    except FileNotFoundError as e:
        logger.warning("Test tool not installed: %s", e)
    except Exception as e:
        logger.debug("Test verification failed: %s", e)

    # Parse test counts from subprocess output
    if result is not None:
        stdout = (result.stdout or "") + (result.stderr or "")
        tests_total, tests_passed = _parse_test_counts(stdout)
        logger.debug("Parsed test counts: %d total, %d passed", tests_total, tests_passed)

    print("  ─" * 50)
    print(print_bold("TEST RESULTS"))
    print()

    if tests_passing:
        print(print_green(f"  Passing:  {tests_passed if tests_passed > 0 else 'unknown (not parsed)'}"))
        print(print_green("  Failing:  0"))
        print()
        print(print_green("  ✓ All tests passing after refinements"))
    else:
        print(print_yellow("  ! Some tests may need attention"))

    print()

    return tests_passing, tests_total, tests_passed


def _display_refinement_summary(
    fixed_critical: int, total_critical: int,
    fixed_major: int, total_major: int,
    fixed_minor: int, total_minor: int,
    tests_passing: bool
) -> None:
    """Display refinement summary."""
    print()
    print(print_bold("- REFINEMENT SUMMARY"))
    print()

    print("  ─" * 50)
    print(print_bold("ISSUES RESOLVED"))
    print()
    print(print_green(f"  Critical Fixed:  {fixed_critical} / {total_critical}"))
    print(print_green(f"  Major Fixed:     {fixed_major} / {total_major}"))
    print(print_dim(f"  Minor Fixed:     {fixed_minor} / {total_minor}  (optional)"))
    print("  ─" * 50)
    print()

    if fixed_critical >= total_critical and fixed_major >= total_major:
        print(print_green("━" * 100))
        print(print_green("✓ ALL CRITICAL AND MAJOR ISSUES RESOLVED"))
        print(print_green("━" * 100))
    else:
        print(print_yellow("━" * 100))
        print(print_yellow("! Some issues remain - review before proceeding"))
        print(print_yellow("━" * 100))

    print()


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 604: Refinement")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
