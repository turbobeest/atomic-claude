"""
Task 603: Comprehensive Review

Execute parallel code review across all dimensions:
- Deep Code Review (logic, error handling, security)
- Architecture Compliance (patterns, layer separation, dependencies)
- Performance Analysis (efficiency, resource usage, bottlenecks)
- Documentation Review (comments, docstrings, API docs)
"""

import logging
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, print_magenta, print_blue
)
from core.utils.file_ops import ensure_dir, read_file, write_file
from core.llm import invoke_llm


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None) -> bool:
    """
    Execute Task 603: Comprehensive Review.

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
    prompts_dir = output_dir / "prompts"

    print()
    print(print_dim("Executing parallel code review across all dimensions."))
    print()

    # UAT Mode Bypass
    if uat_mode:
        print(print_yellow("UAT Mode: Creating minimal valid output"))
        ensure_dir(review_dir)
        ensure_dir(prompts_dir)

        review_report = output_dir / "review-report.md"
        write_file(review_report, """# Code Review Report (UAT Mode)

## Summary
UAT mode - stub review complete

## Critical Issues
None (UAT stub)

## Major Issues
None (UAT stub)

## Minor Issues
None (UAT stub)
""")

        write_file(findings_file, json.dumps({
            "deep_code": {"critical": 0, "major": 0, "minor": 0, "suggestions": 0, "findings": []},
            "architecture": {"critical": 0, "major": 0, "minor": 0, "suggestions": 0, "findings": []},
            "performance": {"critical": 0, "major": 0, "minor": 0, "suggestions": 0, "findings": []},
            "documentation": {"critical": 0, "major": 0, "minor": 0, "suggestions": 0, "findings": []},
            "totals": {"critical": 0, "major": 0, "minor": 0, "suggestions": 0},
            "reviewed_at": datetime.now().isoformat()
        }, indent=2))

        print(print_green("✓ UAT bypass complete"))
        return True

    ensure_dir(review_dir)
    ensure_dir(prompts_dir)

    # Load review agents
    agents_file = output_dir / "review-agents.json"
    agents = _load_agents(agents_file, atomic_root)

    # Discover review scope (host project, not atomic-claude)
    source_files, test_files = _discover_review_scope(project_root, atomic_root)
    print()
    print(print_dim(f"Review scope: {len(source_files)} source files, {len(test_files)} test files"))
    print()

    # Gather code context
    code_sample = _gather_code_sample(source_files, project_root, prompts_dir)
    test_sample = _gather_test_sample(test_files, prompts_dir)

    # Load project context for review grounding
    project_context = _load_project_context(atomic_root)

    # Execute parallel review
    print()
    print(print_bold("- PARALLEL REVIEW EXECUTION"))
    print()
    print(print_dim("Launching review agents..."))
    print()

    results = {}
    results["code"] = _deep_code_review(code_sample, prompts_dir, agents.get("deep"), project_context)
    results["arch"] = _architecture_review(code_sample, prompts_dir, agents.get("arch"), project_context)
    results["perf"] = _performance_review(code_sample, prompts_dir, agents.get("perf"), project_context)
    results["doc"] = _documentation_review(code_sample, test_sample, prompts_dir, agents.get("doc"), project_context)

    # Display and save results
    _display_and_save_results(results, findings_file)

    print(print_green("✓ Comprehensive Review complete"))
    return True


def _load_agents(agents_file: Path, atomic_root: Path) -> Dict[str, str]:
    """Load agent names from selection file."""
    agents = {}
    if not agents_file.exists():
        return agents

    try:
        data = json.loads(read_file(agents_file))
        review_agents = data.get("review_agents", {})
        agents["deep"] = review_agents.get("deep_code", {}).get("name", "")
        agents["arch"] = review_agents.get("architecture", {}).get("name", "")
        agents["perf"] = review_agents.get("performance", {}).get("name", "")
        agents["doc"] = review_agents.get("documentation", {}).get("name", "")
    except Exception as e:
        logger.debug("Failed to load review agents from %s: %s", agents_file, e)

    return agents


def _discover_review_scope(project_root: Path, atomic_root: Path) -> Tuple[List[Path], List[Path]]:
    """Discover source and test files for review.

    Searches the HOST project (project_root) for source code, plus any
    TDD-generated code in .claude/testing/. Also checks the host project's
    src/ directory and common Rust/Go/Node/Python source locations.
    """
    source_files = []
    test_files = []
    seen = set()

    # Common source directories in the host project
    source_dirs = [
        project_root / "src",
        project_root / "lib",
        project_root / "app",
        project_root / "pkg",
        project_root / "cmd",
    ]

    # TDD-generated code
    tdd_dir = project_root / ".claude" / "testing"
    if tdd_dir.exists():
        source_dirs.append(tdd_dir)

    source_exts = ["*.rs", "*.py", "*.ts", "*.js", "*.go", "*.java"]

    for src_dir in source_dirs:
        if not src_dir.exists():
            continue
        for ext in source_exts:
            for f in src_dir.rglob(ext):
                if f not in seen and len(source_files) < 50:
                    # Skip test files from source list
                    if "test" in f.stem.lower() and src_dir != tdd_dir:
                        continue
                    source_files.append(f)
                    seen.add(f)

    # Also check for top-level Rust files (common in small crates)
    for ext in source_exts:
        for f in project_root.glob(ext):
            if f not in seen and len(source_files) < 50:
                source_files.append(f)
                seen.add(f)

    # Find test files in host project
    test_patterns = ["*.test.*", "*_test.*", "test_*"]
    test_dirs = [
        project_root / "tests",
        project_root / "test",
        project_root / "src",  # Rust inline tests
    ]
    # Also include TDD test files
    if tdd_dir.exists():
        test_dirs.append(tdd_dir)

    for td in test_dirs:
        if not td.exists():
            continue
        for pattern in test_patterns:
            for f in td.rglob(pattern):
                if f not in seen and len(test_files) < 30:
                    test_files.append(f)
                    seen.add(f)

    return source_files, test_files


def _gather_code_sample(files: List[Path], project_root: Path, prompts_dir: Path) -> Path:
    """Gather code sample for review."""
    sample_file = prompts_dir / "code-sample.txt"
    max_lines = 100

    content = ["# Source Code Sample for Review\n"]

    for file in files[:20]:  # Limit to 20 files
        if not file.exists():
            continue

        try:
            rel = file.relative_to(project_root)
        except ValueError:
            rel = file.name

        content.append(f"\n## File: {rel}\n")
        content.append("```\n")
        try:
            lines = read_file(file).splitlines()
            content.append("\n".join(lines[:max_lines]))
        except Exception as e:
            logger.debug("Failed to read source file %s: %s", file, e)
            content.append("(Unable to read file)")
        content.append("\n```\n")

    write_file(sample_file, "\n".join(content))
    return sample_file


def _gather_test_sample(files: List[Path], prompts_dir: Path) -> Path:
    """Gather test code sample for review."""
    sample_file = prompts_dir / "test-sample.txt"
    max_lines = 100

    content = ["# Test Code Sample for Review\n"]

    for file in files[:10]:  # Limit to 10 files
        if not file.exists():
            continue

        content.append(f"\n## File: {file.name}\n")
        content.append("```\n")
        try:
            lines = read_file(file).splitlines()
            content.append("\n".join(lines[:max_lines]))
        except Exception as e:
            logger.debug("Failed to read test file %s: %s", file, e)
            content.append("(Unable to read file)")
        content.append("\n```\n")

    write_file(sample_file, "\n".join(content))
    return sample_file


def _load_project_context(atomic_root: Path) -> str:
    """Load project context for review prompts."""
    project_root = atomic_root.parent
    context_parts = []

    # Load project config
    config_file = project_root / ".outputs" / "0-setup" / "project-config.json"
    if config_file.exists():
        try:
            cfg = json.loads(read_file(config_file))
            project = cfg.get("project", {})
            if project.get("name"):
                context_parts.append(f"**Project:** {project['name']}")
            if project.get("description"):
                context_parts.append(f"**Description:** {project['description']}")
            if project.get("type"):
                context_parts.append(f"**Type:** {project['type']}")
        except Exception as e:
            logger.debug("Failed to load project config from %s: %s", config_file, e)

    # Load corpus analysis from discovery phase
    analysis_file = project_root / ".outputs" / "1-discovery" / "corpus-analysis.md"
    if analysis_file.exists():
        try:
            analysis = read_file(analysis_file).strip()
            if analysis:
                context_parts.append(f"\n**Technical Landscape:**\n{analysis}")
        except Exception as e:
            logger.debug("Failed to load corpus analysis from %s: %s", analysis_file, e)

    # Load OpenSpec constraints if available
    openspec_dir = project_root / ".openspec"
    if openspec_dir.exists():
        spec_files = list(openspec_dir.glob("spec-t*.json"))
        if spec_files:
            spec_summary = []
            for sf in spec_files[:10]:
                try:
                    raw = read_file(sf)
                    stripped = raw.strip()
                    # Strip markdown code fences if present
                    if stripped.startswith("```"):
                        first_nl = stripped.index("\n")
                        stripped = stripped[first_nl + 1:]
                        if stripped.endswith("```"):
                            stripped = stripped[:-3].strip()
                    spec = json.loads(stripped)
                    title = spec.get("task_title", sf.stem)
                    spec_summary.append(f"  - {title}")
                except Exception as e:
                    logger.debug("Failed to parse OpenSpec %s: %s", sf, e)
            if spec_summary:
                context_parts.append(f"\n**OpenSpec Tasks:**\n" + "\n".join(spec_summary))

    return "\n".join(context_parts) if context_parts else ""


def _deep_code_review(code_file: Path, prompts_dir: Path, agent_name: str,
                      project_context: str = "") -> Dict[str, Any]:
    """Execute deep code review."""
    print(print_cyan("    Worker 1: Deep Code Review         "))

    output_file = prompts_dir / "review-code.json"
    prompt = _build_code_review_prompt(code_file, agent_name, project_context)

    return _execute_review(prompt, output_file, "sonnet")


def _architecture_review(code_file: Path, prompts_dir: Path, agent_name: str,
                          project_context: str = "") -> Dict[str, Any]:
    """Execute architecture review."""
    print(print_magenta("    Worker 2: Architecture Compliance  "))

    output_file = prompts_dir / "review-arch.json"
    prompt = _build_architecture_prompt(code_file, agent_name, project_context)

    return _execute_review(prompt, output_file, "sonnet")


def _performance_review(code_file: Path, prompts_dir: Path, agent_name: str,
                         project_context: str = "") -> Dict[str, Any]:
    """Execute performance review."""
    print(print_yellow("    Worker 3: Performance Analysis     "))

    output_file = prompts_dir / "review-perf.json"
    prompt = _build_performance_prompt(code_file, agent_name, project_context)

    return _execute_review(prompt, output_file, "haiku")


def _documentation_review(code_file: Path, test_file: Path, prompts_dir: Path,
                           agent_name: str, project_context: str = "") -> Dict[str, Any]:
    """Execute documentation review."""
    print(print_blue("    Worker 4: Documentation Review     "))

    output_file = prompts_dir / "review-doc.json"
    prompt = _build_documentation_prompt(code_file, test_file, agent_name, project_context)

    return _execute_review(prompt, output_file, "haiku")


def _build_code_review_prompt(code_file: Path, agent_name: str,
                               project_context: str = "") -> str:
    """Build deep code review prompt."""
    code_content = read_file(code_file) if code_file.exists() else ""

    context_section = ""
    if project_context:
        context_section = f"""## Project Context

{project_context}

"""

    return f"""# Deep Code Review

You are a senior code reviewer performing thorough code analysis.

{context_section}## Review Focus Areas

1. **Logic Errors**: Incorrect conditions, off-by-one errors, null checks
2. **Error Handling**: Missing try/catch, unhandled edge cases, error propagation
3. **Security**: Input validation, injection vulnerabilities, auth checks, data exposure
4. **Code Quality**: DRY violations, unclear naming, excessive complexity

## Severity Definitions

- **critical**: Security vulnerability, data loss risk, crash in normal use
- **major**: Incorrect behavior, poor error handling, significant maintainability issue
- **minor**: Style issues, minor inefficiencies, small improvements
- **suggestion**: Nice-to-have improvements, alternative approaches

## Code to Review

{code_content}

## Output Format

Respond with ONLY valid JSON (no markdown wrapper):

{{
  "critical": <number>,
  "major": <number>,
  "minor": <number>,
  "suggestions": <number>,
  "findings": [
    {{
      "severity": "critical|major|minor|suggestion",
      "category": "logic|error_handling|security|code_quality",
      "file": "filename.ext",
      "line": 42,
      "description": "Brief description of the issue",
      "recommendation": "How to fix it"
    }}
  ]
}}

Be specific. If no issues found in a category, return 0 for that count.
"""


def _build_architecture_prompt(code_file: Path, agent_name: str,
                                project_context: str = "") -> str:
    """Build architecture review prompt."""
    code_content = read_file(code_file) if code_file.exists() else ""

    context_section = ""
    if project_context:
        context_section = f"""## Project Context

{project_context}

"""

    return f"""# Architecture Compliance Review

You are a software architect reviewing code for architectural compliance.

{context_section}## Review Focus Areas

1. **Layer Separation**: Presentation/business/data layer boundaries
2. **Dependency Direction**: Dependencies should point inward (to domain)
3. **Pattern Compliance**: Consistent use of chosen patterns
4. **Module Boundaries**: Clear interfaces, no circular dependencies
5. **Coupling**: Avoid tight coupling between unrelated modules

## Code to Review

{code_content}

## Output Format

Respond with ONLY valid JSON (no markdown wrapper):

{{
  "critical": <number>,
  "major": <number>,
  "minor": <number>,
  "suggestions": <number>,
  "findings": [
    {{
      "severity": "critical|major|minor|suggestion",
      "category": "layer_separation|dependency|pattern|module_boundary|coupling",
      "file": "filename.ext",
      "description": "Brief description of the architectural issue",
      "recommendation": "How to improve the architecture"
    }}
  ]
}}
"""


def _build_performance_prompt(code_file: Path, agent_name: str,
                               project_context: str = "") -> str:
    """Build performance review prompt."""
    code_content = read_file(code_file) if code_file.exists() else ""

    context_section = ""
    if project_context:
        context_section = f"""## Project Context

{project_context}

"""

    return f"""# Performance Analysis Review

You are a performance engineer reviewing code for efficiency issues.

{context_section}## Review Focus Areas

1. **Algorithm Complexity**: O(n^2) where O(n) is possible
2. **Memory Usage**: Large allocations, memory leaks
3. **I/O Operations**: Blocking calls, N+1 queries
4. **Caching**: Missing cache opportunities
5. **Concurrency**: Race conditions, deadlock potential

## Code to Review

{code_content}

## Output Format

Respond with ONLY valid JSON (no markdown wrapper):

{{
  "critical": <number>,
  "major": <number>,
  "minor": <number>,
  "suggestions": <number>,
  "findings": [
    {{
      "severity": "critical|major|minor|suggestion",
      "category": "algorithm|memory|io|caching|concurrency",
      "file": "filename.ext",
      "line": 42,
      "description": "Brief description of the performance issue",
      "impact": "Estimated impact",
      "recommendation": "How to improve performance"
    }}
  ]
}}
"""


def _build_documentation_prompt(code_file: Path, test_file: Path, agent_name: str,
                                 project_context: str = "") -> str:
    """Build documentation review prompt."""
    code_content = read_file(code_file) if code_file.exists() else ""
    test_content = read_file(test_file) if test_file.exists() else ""

    context_section = ""
    if project_context:
        context_section = f"""## Project Context

{project_context}

"""

    return f"""# Documentation Review

You are a technical writer reviewing code documentation quality.

{context_section}## Review Focus Areas

1. **Public API Docs**: All public functions have clear documentation
2. **Complex Logic Comments**: Non-obvious code has explanatory comments
3. **Type Annotations**: Parameters and return types are documented
4. **Examples**: Complex APIs have usage examples
5. **Accuracy**: Documentation matches actual behavior

## Source Code

{code_content}

## Test Code

{test_content}

## Output Format

Respond with ONLY valid JSON (no markdown wrapper):

{{
  "critical": <number>,
  "major": <number>,
  "minor": <number>,
  "suggestions": <number>,
  "findings": [
    {{
      "severity": "critical|major|minor|suggestion",
      "category": "api_docs|comments|types|examples|accuracy",
      "file": "filename.ext",
      "function": "functionName",
      "description": "Brief description of the documentation issue",
      "recommendation": "What documentation to add/fix"
    }}
  ]
}}
"""


def _execute_review(prompt: str, output_file: Path, model: str) -> Dict[str, Any]:
    """Execute a review by calling LLM."""
    try:
        response = invoke_llm(prompt=prompt, model=model)

        # Parse JSON from response
        # Try to extract JSON from markdown if present
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            response = response[start:end].strip()

        result = json.loads(response)
        write_file(output_file, json.dumps(result, indent=2))

        print(print_green("████████████████████████████████████████  Complete"))
        return result
    except Exception as e:
        print(print_yellow(f"████████████████████████████████████████  Fallback ({e})"))
        # Return empty result on error
        empty = {"critical": 0, "major": 0, "minor": 0, "suggestions": 0, "findings": []}
        write_file(output_file, json.dumps(empty, indent=2))
        return empty


def _display_and_save_results(results: Dict[str, Dict], findings_file: Path) -> None:
    """Display and save review results."""
    code_result = results.get("code", {})
    arch_result = results.get("arch", {})
    perf_result = results.get("perf", {})
    doc_result = results.get("doc", {})

    # Calculate totals
    total_critical = sum([
        code_result.get("critical", 0),
        arch_result.get("critical", 0),
        perf_result.get("critical", 0),
        doc_result.get("critical", 0)
    ])
    total_major = sum([
        code_result.get("major", 0),
        arch_result.get("major", 0),
        perf_result.get("major", 0),
        doc_result.get("major", 0)
    ])
    total_minor = sum([
        code_result.get("minor", 0),
        arch_result.get("minor", 0),
        perf_result.get("minor", 0),
        doc_result.get("minor", 0)
    ])
    total_suggestions = sum([
        code_result.get("suggestions", 0),
        arch_result.get("suggestions", 0),
        perf_result.get("suggestions", 0),
        doc_result.get("suggestions", 0)
    ])

    # Display summary
    print()
    print(print_bold("- REVIEW SUMMARY"))
    print()
    print("  ─" * 50)
    print(print_bold("TOTAL FINDINGS"))
    print()

    if total_critical == 0:
        print(print_green(f"  Critical:     {total_critical}") + "      Must fix before release")
    else:
        print(print_red(f"  Critical:     {total_critical}") + "      Must fix before release")

    if total_major == 0:
        print(print_green(f"  Major:        {total_major}") + "      Should fix before release")
    else:
        print(print_yellow(f"  Major:        {total_major}") + "      Should fix before release")

    print(print_dim(f"  Minor:        {total_minor}") + "      Consider fixing")
    print(print_dim(f"  Suggestions:  {total_suggestions}") + "      Nice to have improvements")
    print("  ─" * 50)
    print()

    # Save findings
    findings_data = {
        "deep_code": code_result,
        "architecture": arch_result,
        "performance": perf_result,
        "documentation": doc_result,
        "totals": {
            "critical": total_critical,
            "major": total_major,
            "minor": total_minor,
            "suggestions": total_suggestions
        },
        "reviewed_at": datetime.now().isoformat()
    }

    write_file(findings_file, json.dumps(findings_data, indent=2))


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 603: Comprehensive Review")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
