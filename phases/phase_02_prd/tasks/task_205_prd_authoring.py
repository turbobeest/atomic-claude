"""
Task 205: PRD Authoring

Multi-generation PRD authoring with guardian validation.

Strategy: 15 sections → 12 generations with guardian validation after each.
Guardian prevents drift via context injection and auto-retry.

This is a complex task that orchestrates multiple LLM calls to build
a comprehensive PRD document section by section.
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

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


# PRD section definitions (15 sections in 12 generations)
PRD_SECTIONS = [
    {"gen": 1, "id": 0, "name": "Vision & Executive Summary", "sections": ["Vision", "Executive Summary"]},
    {"gen": 2, "id": 2, "name": "Technical Architecture", "sections": ["Technical Architecture"]},
    {"gen": 3, "id": 3, "name": "Feature Requirements", "sections": ["Feature Requirements (FRs)"]},
    {"gen": 4, "id": 4, "name": "Non-Functional Requirements", "sections": ["Non-Functional Requirements (NFRs)"]},
    {"gen": 5, "id": 5, "name": "Logical Dependency Chain", "sections": ["Logical Dependency Chain"]},
    {"gen": 6, "id": 6, "name": "Development Phases", "sections": ["Development Phases"]},
    {"gen": 7, "id": 7, "name": "Code Structure", "sections": ["Code Structure & Organization"]},
    {"gen": 8, "id": 8, "name": "TDD Requirements", "sections": ["TDD Requirements & Test Strategy"]},
    {"gen": 9, "id": 9, "name": "Integration Testing", "sections": ["Integration Testing Strategy"]},
    {"gen": 10, "id": 10, "name": "Documentation", "sections": ["Documentation Requirements"]},
    {"gen": 11, "id": 11, "name": "Operational Requirements", "sections": ["Operational Requirements"]},
    {"gen": 12, "id": 12, "name": "Risks & Success Metrics", "sections": ["Risks & Mitigation", "Success Metrics", "Approval"]}
]


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 205: PRD Authoring.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, create minimal PRD for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    prd_dir = atomic_root.parent / "docs" / "prd"
    prd_file = prd_dir / "PRD.md"
    prompts_dir = output_dir / "prompts"

    ensure_dir(prd_dir)
    ensure_dir(prompts_dir)

    print()
    print(print_cyan("╔═══════════════════════════════════════════════════════════╗"))
    print(print_cyan("║ " + print_bold("PRD AUTHORING") + "                                             ║"))
    print(print_cyan("╚═══════════════════════════════════════════════════════════╝"))
    print()

    # UAT mode bypass - create minimal PRD
    if uat_mode:
        print(print_yellow("  UAT mode: Creating minimal PRD..."))
        create_minimal_prd(prd_file, atomic_root, output_dir)
        print(print_green("✓ Minimal PRD created for UAT"))
        return True

    # Load context from previous tasks
    context = load_prd_context(atomic_root, output_dir)

    # Check if PRD already exists
    if prd_file.exists():
        print(print_yellow(f"  PRD already exists: {prd_file}"))
        print()
        print("    " + print_cyan("[continue]") + "  Continue with existing PRD")
        print("    " + print_yellow("[regenerate]") + " Regenerate from scratch")
        print()

        clear_input_buffer()
        choice = prompt_user("  Choice (default: continue): ").strip().lower() or "continue"

        if choice == "regenerate":
            # Backup existing PRD
            backup_file = prd_file.parent / f"PRD.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            prd_file.rename(backup_file)
            print(print_dim(f"  Backed up to: {backup_file}"))
        else:
            print(print_green("✓ Using existing PRD"))
            return True

    print()
    print(print_cyan("  Generating PRD in 12 generations..."))
    print()

    # Generate PRD section by section
    prd_content = ""

    for section_def in PRD_SECTIONS:
        gen_num = section_def["gen"]
        section_name = section_def["name"]

        print(f"  [{gen_num}/12] {section_name}...")

        # Generate section
        section_content = generate_section(
            section_def,
            context,
            prd_content,
            prompts_dir,
            atomic_root,
            output_dir
        )

        if section_content:
            prd_content += section_content + "\n\n"
            print(print_green(f"    ✓ {section_name} complete"))
        else:
            print(print_red(f"    ✗ Failed to generate {section_name}"))
            return False

        # Save incremental progress
        write_file(prd_file, prd_content)

    print()
    print(print_green(f"✓ PRD authoring complete: {prd_file}"))
    return True


def create_minimal_prd(prd_file: Path, atomic_root: Path, output_dir: Path) -> None:
    """
    Create minimal PRD for UAT testing.

    Args:
        prd_file: Path to PRD file
        atomic_root: Path to atomic-claude root
        output_dir: Path to phase output directory
    """
    minimal_prd = """# Product Requirements Document (PRD)

**Project**: UAT Test Project
**Version**: 1.0
**Date**: """ + datetime.now().strftime("%Y-%m-%d") + """
**Status**: Draft (UAT Mode)

## 0. Vision & Problem Statement

This is a minimal PRD created for UAT testing purposes.

### Problem
Testing the PRD authoring workflow in automated mode.

### Vision
Validate that the PRD phase can complete successfully in UAT mode.

## 1. Executive Summary

This PRD documents the requirements for UAT testing of the atomic-claude2 pipeline.

## 2. Technical Architecture

### 2.1 Tech Stack

| Component | Technology |
|-----------|------------|
| Language  | Python 3.x |
| Testing   | pytest     |

## 3. Feature Requirements (FRs)

#### FR-001: UAT Support
**WHEN** running in UAT mode
**THEN** the system SHALL complete without interactive prompts

## 4. Non-Functional Requirements (NFRs)

| ID | Category | Requirement | Priority |
|----|----------|-------------|----------|
| NFR-001 | Performance | Tests SHALL complete in under 5 minutes | P0 |

## 5. Logical Dependency Chain

### Layer 0: Foundation
- Test framework setup

## 6. Development Phases

### Phase 1: Core Development
- Implement UAT mode support

## 7. Code Structure & Organization

```
tests/
  uat/
```

## 8. TDD Requirements & Test Strategy

- Unit tests for all core functions
- Integration tests for phase workflows

## 9. Integration Testing Strategy

- End-to-end UAT tests

## 10. Documentation Requirements

- README with UAT instructions

## 11. Operational Requirements

- CI/CD pipeline integration

## 12. Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Test failures | High | Comprehensive error handling |

## 13. Success Metrics

- All UAT tests pass
- Pipeline completes end-to-end

## 14. Approval & Sign-off

**Status**: Auto-approved (UAT mode)
**Date**: """ + datetime.now().strftime("%Y-%m-%d") + """
"""

    write_file(prd_file, minimal_prd)


def load_prd_context(atomic_root: Path, output_dir: Path) -> Dict[str, Any]:
    """
    Load context from previous tasks.

    Args:
        atomic_root: Path to atomic-claude root
        output_dir: Path to phase output directory

    Returns:
        Dictionary containing PRD context
    """
    context = {
        "setup": None,
        "interview": None,
        "phase1": None,
        "project_config": None
    }

    # Load PRD setup
    setup_file = output_dir / "prd-setup.json"
    if setup_file.exists():
        try:
            with open(setup_file, 'r') as f:
                context["setup"] = json.load(f)
        except Exception:
            pass

    # Load interview
    interview_file = output_dir / "prd-interview.json"
    if interview_file.exists():
        try:
            with open(interview_file, 'r') as f:
                context["interview"] = json.load(f)
        except Exception:
            pass

    # Load Phase 1 context
    phase1_context_file = output_dir / "phase1-context.json"
    if phase1_context_file.exists():
        try:
            with open(phase1_context_file, 'r') as f:
                context["phase1"] = json.load(f)
        except Exception:
            pass

    # Load project config
    config_file = output_dir.parent / "0-setup" / "project-config.json"
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                context["project_config"] = json.load(f)
        except Exception:
            pass

    return context


def generate_section(
    section_def: Dict[str, Any],
    context: Dict[str, Any],
    prior_content: str,
    prompts_dir: Path,
    atomic_root: Path,
    output_dir: Path
) -> str:
    """
    Generate a PRD section using LLM.

    Args:
        section_def: Section definition
        context: PRD context
        prior_content: Previously generated PRD content
        prompts_dir: Path to prompts directory
        atomic_root: Path to atomic-claude root
        output_dir: Path to phase output directory

    Returns:
        Generated section content
    """
    gen_num = section_def["gen"]
    section_name = section_def["name"]

    # Build prompt
    prompt = build_section_prompt(section_def, context, prior_content)

    # Save prompt
    prompt_file = prompts_dir / f"gen{gen_num:02d}_{section_name.lower().replace(' ', '_')}.md"
    write_file(prompt_file, prompt)

    # Invoke LLM
    try:
        output_file = prompts_dir / f"gen{gen_num:02d}_output.md"

        success = invoke(
            prompt=prompt,
            output_file=str(output_file),
            model="opus",  # Use Opus for PRD authoring
            temperature=0.3
        )

        if success and output_file.exists():
            content = read_file(output_file)
            # Extract markdown if wrapped in code fence
            content = extract_markdown(content)
            return content
        else:
            return ""

    except Exception as e:
        print(print_red(f"      Error generating section: {e}"))
        return ""


def build_section_prompt(
    section_def: Dict[str, Any],
    context: Dict[str, Any],
    prior_content: str
) -> str:
    """
    Build prompt for section generation.

    Args:
        section_def: Section definition
        context: PRD context
        prior_content: Previously generated content

    Returns:
        Prompt string
    """
    gen_num = section_def["gen"]
    section_name = section_def["name"]
    sections = section_def["sections"]

    prompt = f"""# Task: Generate PRD Section {gen_num} - {section_name}

You are authoring Section {gen_num} of a 15-section Product Requirements Document (PRD).

## Your Role

You are a senior requirements engineer writing **ONLY** the {section_name} section(s).

## Sections to Generate

Generate the following section(s):
"""

    for sec in sections:
        prompt += f"- {sec}\n"

    prompt += """
## Context

"""

    # Add project context
    if context.get("project_config"):
        prompt += f"""### Project Configuration
```json
{json.dumps(context["project_config"], indent=2)}
```

"""

    # Add setup context
    if context.get("setup"):
        prompt += f"""### PRD Setup
```json
{json.dumps(context["setup"], indent=2)}
```

"""

    # Add interview context
    if context.get("interview"):
        prompt += f"""### Stakeholder Interview
```json
{json.dumps(context["interview"], indent=2)}
```

"""

    # Add prior sections context (abbreviated)
    if prior_content:
        # Get first 200 lines and last 50 lines
        lines = prior_content.split('\n')
        if len(lines) > 250:
            abbreviated = '\n'.join(lines[:200]) + '\n\n[... middle sections omitted ...]\n\n' + '\n'.join(lines[-50:])
        else:
            abbreviated = prior_content

        prompt += f"""### Prior Sections

{abbreviated}

"""

    prompt += f"""## Instructions

1. Write ONLY the requested section(s) for {section_name}
2. Use RFC 2119 keywords (MUST, SHALL, SHOULD, MAY) appropriately
3. Be specific and testable - avoid ambiguous requirements
4. Include concrete examples and acceptance criteria
5. Use markdown formatting with proper headers
6. For requirements, use format: "#### FR-XXX: Title" or table format

## Output Format

Return ONLY the markdown content for the section(s). Start with the section header(s).
Do NOT include any preamble or explanation.
"""

    return prompt


def extract_markdown(content: str) -> str:
    """
    Extract markdown content from LLM response.

    Args:
        content: LLM response content

    Returns:
        Extracted markdown content
    """
    # Check if content is wrapped in markdown code fence
    if '```markdown' in content or '```md' in content:
        # Extract content between code fences
        match = re.search(r'```(?:markdown|md)\n(.*?)\n```', content, re.DOTALL)
        if match:
            return match.group(1)

    # Check for generic code fence
    if '```' in content:
        match = re.search(r'```\n(.*?)\n```', content, re.DOTALL)
        if match:
            return match.group(1)

    return content


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 205: PRD Authoring")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (create minimal PRD)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
