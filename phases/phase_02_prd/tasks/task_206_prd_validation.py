"""
Task 206: PRD Validation

Validates PRD completeness, testability, and consistency.

Checks:
  - All 15 sections present
  - Requirements are testable
  - No internal contradictions
  - Gherkin scenarios generatable

Includes a validate-revise loop: if the user chooses "revise",
the LLM-assisted revision flow (206b) runs, then validation re-runs automatically.
"""

import logging
import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.config import Config
from core.llm import invoke
from core.state import StateManager
from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user, clear_input_buffer
)
from core.utils.file_ops import ensure_dir, read_file, write_file
from phases.phase_02_prd.tasks.task_206b_prd_revision import prd_revision_flow


# Expected PRD sections
EXPECTED_SECTIONS = [
    "Vision",
    "Executive Summary",
    "Technical Architecture",
    "Feature Requirements",
    "Non-Functional",
    "Logical Dependency",
    "Development Phases",
    "Code Structure",
    "TDD",
    "Integration Testing",
    "Documentation",
    "Operational",
    "Risks",
    "Success Metrics",
    "Approval"
]


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None, graph=None) -> bool:
    """
    Execute Task 206: PRD Validation.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, auto-pass validation for testing
        graph: Optional GraphManager instance for knowledge graph operations

    Returns:
        True if task completed successfully, False otherwise
    """
    prd_file = atomic_root.parent / "docs" / "prd" / "PRD.md"
    validation_file = output_dir / "prd-validation.json"
    prompts_dir = output_dir / "prompts"

    ensure_dir(prompts_dir)

    # UAT mode bypass
    if uat_mode:
        print(print_yellow("  UAT mode: Auto-passing validation..."))
        create_passing_validation(validation_file, prd_file)
        print(print_green("✓ UAT mode: Validation passed (auto-approved)"))
        return True

    print()
    print(print_dim("  ┌─────────────────────────────────────────────────────────┐"))
    print(print_dim("  │ Validating PRD for completeness and testability.       │"))
    print(print_dim("  │ Revision loop: validate -> review -> revise -> re-validate│"))
    print(print_dim("  └─────────────────────────────────────────────────────────┘"))
    print()

    # Check PRD exists
    if not prd_file.exists():
        print(print_red(f"  ✗ PRD file not found: {prd_file}"))
        return False

    # Query graph for requirement coverage data (supplemental)
    if graph:
        try:
            validation_context = graph.reader.get_nodes("Requirement")
            if validation_context:
                logger.info(f"Loaded {len(validation_context)} requirements from graph for validation")
        except Exception as e:
            logger.warning(f"Graph query failed: {e}")

    # Validate-revise loop
    iteration = 0
    max_iterations = 3

    while iteration < max_iterations:
        iteration += 1

        if iteration > 1:
            print()
            print(print_cyan("┌─────────────────────────────────────────────────────────┐"))
            print(print_cyan("│ " + print_bold(f"RE-VALIDATION (pass {iteration})") + "                                     │"))
            print(print_cyan("└─────────────────────────────────────────────────────────┘"))
            print()

        # Structural validation
        sections_found, sections_missing = validate_structure(prd_file)

        # Structural gate
        if sections_found < 10 or count_lines(prd_file) < 100:
            print()
            print(print_red("  ┌─────────────────────────────────────────────────────────┐"))
            print(print_red("  │ " + print_bold("STRUCTURAL GATE FAILED") + "                                    │"))
            print(print_red("  └─────────────────────────────────────────────────────────┘"))
            print()

            if not handle_structural_failure(prd_file, sections_missing):
                return False

            continue

        # Content validation (LLM)
        validation_result = validate_content(prd_file, prompts_dir, atomic_root, output_dir)

        if not validation_result:
            print(print_red("  ✗ Content validation failed"))
            return False

        # Save validation results
        write_file(validation_file, json.dumps(validation_result, indent=2))

        # Check if validation passed
        overall_status = validation_result.get("overall_status", "UNKNOWN")

        if overall_status == "PASS":
            print()
            print(print_green("✓ PRD validation passed"))
            return True
        elif overall_status == "WARNING":
            print()
            print(print_yellow("  ! PRD validation has warnings"))
            print()
            print("    " + print_green("[approve]") + " Approve despite warnings")
            print("    " + print_yellow("[revise]") + "  Revise PRD to address warnings")
            print()

            clear_input_buffer()
            choice = prompt_user("  Choice (default: approve): ").strip().lower() or "approve"

            if choice == "approve":
                print(print_green("✓ PRD approved with warnings"))
                return True
            else:
                revised = prd_revision_flow(validation_file, prd_file, prompts_dir)
                if revised:
                    continue  # re-validate
                return True  # user discarded revision, approve anyway
        else:
            print()
            print(print_red("  ✗ PRD validation failed with critical issues"))
            print()
            print("    " + print_yellow("[revise]") + " Revise PRD to address issues")
            print("    " + print_red("[abort]") + "  Abort validation")
            print()

            clear_input_buffer()
            choice = prompt_user("  Choice (default: revise): ").strip().lower() or "revise"

            if choice == "abort":
                return False
            else:
                revised = prd_revision_flow(validation_file, prd_file, prompts_dir)
                if revised:
                    continue  # re-validate
                return False  # user discarded revision, abort

    print(print_red("  ✗ Maximum validation iterations reached"))
    return False


def create_passing_validation(validation_file: Path, prd_file: Path) -> None:
    """
    Create passing validation result for UAT.

    Args:
        validation_file: Path to validation file
        prd_file: Path to PRD file
    """
    sections_found = 10
    if prd_file.exists():
        content = read_file(prd_file)
        sections_found = len(re.findall(r'^##\s', content, re.MULTILINE))

    validation_data = {
        "audit_timestamp": datetime.now().isoformat(),
        "overall_status": "PASS",
        "overall_score": 85,
        "completeness": {
            "status": "PASS",
            "score": 85,
            "gaps": [],
            "phase1_alignment": "UAT mode - validation bypassed"
        },
        "testability": {
            "status": "PASS",
            "score": 80,
            "rfc2119_usage": "Adequate",
            "scenario_coverage": "Minimal scenarios present",
            "issues": []
        },
        "taskmaster_compatibility": {
            "status": "PASS",
            "score": 85,
            "has_dependency_chain": True,
            "has_explicit_tech_stack": True,
            "has_scope_based_phases": True,
            "issues": []
        },
        "openspec_compatibility": {
            "status": "PASS",
            "score": 80,
            "scenario_format_correct": True,
            "issues": []
        },
        "consistency": {
            "status": "PASS",
            "contradictions": [],
            "ambiguous_items": []
        },
        "sample_gherkin": [
            "Feature: Core Feature\n  Scenario: Basic test\n    Given system is ready\n    When user acts\n    Then outcome occurs"
        ],
        "recommendations": [],
        "proceed_recommendation": True,
        "proceed_rationale": "UAT mode - automated validation passed with minimal checks",
        "sections_found": sections_found,
        "mode": "uat"
    }

    write_file(validation_file, json.dumps(validation_data, indent=2))


def validate_structure(prd_file: Path) -> Tuple[int, List[str]]:
    """
    Validate PRD structure.

    Args:
        prd_file: Path to PRD file

    Returns:
        Tuple of (sections_found, sections_missing)
    """
    print(print_cyan("┌─────────────────────────────────────────────────────────┐"))
    print(print_cyan("│ " + print_bold("STRUCTURAL VALIDATION") + "                                   │"))
    print(print_cyan("└─────────────────────────────────────────────────────────┘"))
    print()

    content = read_file(prd_file)
    sections_found = 0
    sections_missing = []

    for section in EXPECTED_SECTIONS:
        if re.search(re.escape(section), content, re.IGNORECASE):
            print("    " + print_green("✓") + f" {section}")
            sections_found += 1
        else:
            print("    " + print_yellow("○") + f" {section} (not found)")
            sections_missing.append(section)

    prd_lines = count_lines(prd_file)

    print()
    print(print_dim(f"  Sections: {sections_found}/{len(EXPECTED_SECTIONS)} found | PRD: {prd_lines} lines"))
    print()

    return sections_found, sections_missing


def count_lines(file_path: Path) -> int:
    """Count lines in file."""
    try:
        return len(read_file(file_path).split('\n'))
    except Exception:
        return 0


def handle_structural_failure(prd_file: Path, sections_missing: List[str]) -> bool:
    """
    Handle structural validation failure.

    Args:
        prd_file: Path to PRD file
        sections_missing: List of missing sections

    Returns:
        True to retry validation, False to abort
    """
    print(print_red("  The PRD does not meet minimum structural requirements."))
    print(print_red("  LLM content validation is blocked to avoid wasting resources."))
    print()

    if sections_missing:
        print(print_yellow("  Missing sections:"))
        for section in sections_missing:
            print(f"    {print_yellow('○')} {section}")
        print()

    print(print_cyan("  Options:"))
    print("    " + print_yellow("[back]") + "     Return to PRD authoring (task 205)")
    print("    " + print_cyan("[path]") + "     Provide path to real PRD file")
    print("    " + print_dim("[skip]") + "     Skip gate and run LLM validation anyway")
    print()

    clear_input_buffer()
    choice = prompt_user("  Choice (default: back): ").strip().lower() or "back"

    if choice == "path":
        new_path = prompt_user("  Path to PRD file: ").strip()
        if Path(new_path).exists():
            # Copy to expected location
            content = read_file(Path(new_path))
            write_file(prd_file, content)
            print(print_green(f"  ✓ PRD replaced. Re-validating..."))
            return True
        else:
            print(print_red(f"  ✗ File not found: {new_path}"))
            return False
    elif choice == "skip":
        print(print_yellow("  Skipping structural gate..."))
        return True
    else:
        print(print_yellow("  Returning to PRD authoring"))
        return False


def validate_content(
    prd_file: Path,
    prompts_dir: Path,
    atomic_root: Path,
    output_dir: Path
) -> Optional[Dict[str, Any]]:
    """
    Validate PRD content using LLM.

    Args:
        prd_file: Path to PRD file
        prompts_dir: Path to prompts directory
        atomic_root: Path to atomic-claude root
        output_dir: Path to phase output directory

    Returns:
        Validation result dictionary or None on failure
    """
    print(print_cyan("┌─────────────────────────────────────────────────────────┐"))
    print(print_cyan("│ " + print_bold("CONTENT VALIDATION") + "                                      │"))
    print(print_cyan("└─────────────────────────────────────────────────────────┘"))
    print()

    # Build validation prompt
    prd_content = read_file(prd_file)
    prompt = build_validation_prompt(prd_content)

    # Save prompt
    prompt_file = prompts_dir / "prd-validation-prompt.md"
    write_file(prompt_file, prompt)

    # Invoke LLM
    try:
        output_file = prompts_dir / "prd-validation-output.json"

        success = invoke(
            prompt=prompt,
            output_file=str(output_file),
            model="sonnet",
            temperature=0.2
        )

        if success and output_file.exists():
            content = read_file(output_file)
            # Extract JSON if wrapped in code fence
            content = extract_json(content)
            validation_result = json.loads(content)
            print(print_green("  ✓ Content validation complete"))
            return validation_result
        else:
            return None

    except Exception as e:
        print(print_red(f"  ✗ Error during content validation: {e}"))
        return None


def build_validation_prompt(prd_content: str) -> str:
    """
    Build validation prompt.

    Args:
        prd_content: PRD content

    Returns:
        Prompt string
    """
    prompt = f"""# Task: Validate PRD Quality

You are an independent PRD quality auditor validating this Product Requirements Document.

## PRD Content

{prd_content}

## Validation Criteria

Evaluate the PRD across these dimensions:

### 1. Completeness
- Are all required sections present?
- Are requirements sufficiently detailed?
- Is technical stack explicitly defined?

### 2. Testability
- Are requirements testable and measurable?
- Is RFC 2119 syntax used properly (MUST, SHALL, SHOULD, MAY)?
- Are acceptance criteria clear?

### 3. Consistency
- Are there internal contradictions?
- Are terms used consistently?
- Do sections reference each other correctly?

### 4. Tool Compatibility
- TaskMaster: Can dependency chains be extracted?
- OpenSpec: Can Gherkin scenarios be generated?

## Output Format

Return a JSON object with this structure:

```json
{{
  "overall_status": "PASS|WARNING|FAIL",
  "overall_score": 85,
  "completeness": {{
    "status": "PASS|WARNING|FAIL",
    "score": 85,
    "gaps": ["Missing X", "Needs more detail on Y"]
  }},
  "testability": {{
    "status": "PASS|WARNING|FAIL",
    "score": 80,
    "rfc2119_usage": "Excellent|Good|Poor",
    "issues": ["Issue 1", "Issue 2"]
  }},
  "consistency": {{
    "status": "PASS|WARNING|FAIL",
    "contradictions": ["Item A contradicts Item B"],
    "ambiguous_items": ["Term X is ambiguous"]
  }},
  "taskmaster_compatibility": {{
    "status": "PASS|WARNING|FAIL",
    "has_dependency_chain": true,
    "has_explicit_tech_stack": true,
    "issues": []
  }},
  "openspec_compatibility": {{
    "status": "PASS|WARNING|FAIL",
    "scenario_format_correct": true,
    "issues": []
  }},
  "recommendations": ["P0: Critical fix", "P1: Important", "P2: Nice to have"],
  "proceed_recommendation": true,
  "proceed_rationale": "Brief explanation"
}}
```

Be constructive and specific in your recommendations.
"""

    return prompt


def extract_json(content: str) -> str:
    """Extract JSON from LLM response."""
    if '```json' in content:
        match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
        if match:
            return match.group(1)
    if '```' in content:
        match = re.search(r'```\n(.*?)\n```', content, re.DOTALL)
        if match:
            return match.group(1)
    return content


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 206: PRD Validation")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (auto-pass validation)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
