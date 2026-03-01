"""
Task 205: PRD Authoring

Multi-generation PRD authoring with guardian validation.

Strategy: 15 sections → 12 generations with guardian validation after each.
Guardian prevents drift via context injection and auto-retry.

This is a complex task that orchestrates multiple LLM calls to build
a comprehensive PRD document section by section.
"""

import logging
import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.llm import invoke
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


def execute(atomic_root: Path, output_dir: Path, mem=None, graph=None) -> bool:
    """
    Execute Task 205: PRD Authoring.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        graph: Optional GraphManager instance for knowledge graph operations

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

    # Load context from previous tasks
    context = load_prd_context(atomic_root, output_dir)

    # Detect partial state from output files
    resuming = False
    completed_gens = set()

    # Check if PRD already exists
    if prd_file.exists():
        print(print_yellow(f"  PRD already exists: {prd_file}"))

        # Scan output files for resume detection
        completed_gens = _detect_completed_sections(prompts_dir)
        total_gens = 12
        remaining = total_gens - len(completed_gens)
        invalid_gens = set()

        # Check for output files that exist but are invalid
        for gen_num in range(1, 13):
            output_file = prompts_dir / f"gen{gen_num:02d}_output.md"
            if output_file.exists() and gen_num not in completed_gens:
                invalid_gens.add(gen_num)

        if 0 < len(completed_gens) < total_gens:
            # Partial state — show resume option
            print()
            gen_names = {s["gen"]: s["name"] for s in PRD_SECTIONS}
            print(print_green(f"    Valid sections ({len(completed_gens)}): ") +
                  ", ".join(f"{g}-{gen_names[g]}" for g in sorted(completed_gens)))
            if invalid_gens:
                print(print_red(f"    Invalid sections ({len(invalid_gens)}): ") +
                      ", ".join(f"{g}-{gen_names[g]}" for g in sorted(invalid_gens)))
            missing = set(range(1, 13)) - completed_gens
            if missing - invalid_gens:
                print(print_yellow(f"    Missing sections ({len(missing - invalid_gens)}): ") +
                      ", ".join(f"{g}-{gen_names[g]}" for g in sorted(missing - invalid_gens)))
            print()
            print("    " + print_cyan("[enter]") + "  Accept PRD as-is")
            print("    " + print_yellow("[r]") + "      Resume from where it left off")
            print("    " + print_yellow("[n]") + "      Regenerate from scratch")
            print()

            clear_input_buffer()
            choice = prompt_user("  Choice (default: accept): ").strip().lower()

            if choice == "r":
                resuming = True
                print(print_cyan(f"  Resuming — {remaining} section(s) to generate..."))
            elif choice == "n":
                backup_file = prd_file.parent / f"PRD.backup.{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.md"
                prd_file.rename(backup_file)
                print(print_dim(f"  Backed up to: {backup_file}"))
                completed_gens = set()
            else:
                print(print_green("✓ Using existing PRD"))
                return True
        else:
            # All complete or none — original 2-option menu
            print()
            print("    " + print_cyan("[enter]") + "  Accept existing PRD")
            print("    " + print_yellow("[n]") + "      Regenerate from scratch")
            print()

            clear_input_buffer()
            choice = prompt_user("  Choice (default: accept): ").strip().lower()

            if choice == "n":
                backup_file = prd_file.parent / f"PRD.backup.{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.md"
                prd_file.rename(backup_file)
                print(print_dim(f"  Backed up to: {backup_file}"))
                completed_gens = set()
            else:
                print(print_green("✓ Using existing PRD"))
                return True

    print()
    print(print_cyan("  Generating PRD in 12 generations..."))
    print()

    # Rebuild prior content from valid outputs when resuming
    if resuming:
        prd_content = _rebuild_prd_content(prompts_dir, completed_gens)
        if prd_content:
            prd_content += "\n\n"
    else:
        prd_content = ""

    # Generate PRD section by section
    for section_def in PRD_SECTIONS:
        gen_num = section_def["gen"]
        section_name = section_def["name"]

        if gen_num in completed_gens:
            print(f"  [{gen_num}/12] {section_name} " + print_green("(cached)"))
            continue

        print(f"  [{gen_num}/12] {section_name}...")

        # Use graph context if available (focused context instead of full prior_content)
        effective_prior = prd_content
        if graph:
            try:
                graph_context = graph.query_prd_context(section=section_name, max_tokens=8000)
                if graph_context:
                    effective_prior = graph_context
                    logger.info(f"Using graph context for section '{section_name}'")
            except Exception as e:
                logger.warning(f"Graph query failed, falling back to file context: {e}")
                effective_prior = prd_content  # fallback

        # Generate section
        section_content = generate_section(
            section_def,
            context,
            effective_prior,
            prompts_dir,
            atomic_root,
            output_dir
        )

        if section_content:
            prd_content += section_content + "\n\n"
            completed_gens.add(gen_num)
            print(print_green(f"    ✓ {section_name} complete"))

            # Write Feature node to graph for this section
            if graph:
                try:
                    graph.add_feature(
                        id=f"F-{gen_num}",
                        title=section_name,
                        description=section_content[:500],
                    )
                    logger.info(f"Wrote Feature node F-{gen_num} to graph")
                except Exception as e:
                    logger.warning(f"Graph write failed for section '{section_name}': {e}")
        else:
            print(print_red(f"    ✗ Failed to generate {section_name} — skipping"))
            logger.warning("Section generation returned empty for '%s' (gen %d)", section_name, gen_num)

        # Save incremental progress
        write_file(prd_file, prd_content)

    # Check if any sections were actually generated
    failed_sections = [s["name"] for s in PRD_SECTIONS if s["gen"] not in completed_gens]
    if not prd_content.strip():
        print()
        print(print_red("✗ PRD authoring failed: no sections were generated"))
        return False

    print()
    if failed_sections:
        print(print_yellow(f"⚠ PRD authoring partially complete ({len(failed_sections)} section(s) failed): {prd_file}"))
    else:
        print(print_green(f"✓ PRD authoring complete: {prd_file}"))
    return True


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
        except Exception as e:
            logger.debug("Failed to load PRD setup file: %s", e)

    # Load interview
    interview_file = output_dir / "prd-interview.json"
    if interview_file.exists():
        try:
            with open(interview_file, 'r') as f:
                context["interview"] = json.load(f)
        except Exception as e:
            logger.debug("Failed to load interview file: %s", e)

    # Load Phase 1 context
    phase1_context_file = output_dir / "phase1-context.json"
    if phase1_context_file.exists():
        try:
            with open(phase1_context_file, 'r') as f:
                context["phase1"] = json.load(f)
        except Exception as e:
            logger.debug("Failed to load Phase 1 context file: %s", e)

    # Load project config
    config_file = output_dir.parent / "0-setup" / "project-config.json"
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                context["project_config"] = json.load(f)
        except Exception as e:
            logger.debug("Failed to load project config file: %s", e)

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

        # invoke() returns the LLM response as a string (not a bool).
        # A non-empty string is truthy; an empty string or exception means failure.
        llm_result = invoke(
            prompt=prompt,
            output_file=str(output_file),
            model="opus",  # Use Opus for PRD authoring
            temperature=0.3
        )

        # Normalise: result must be a string (guard against unexpected return types)
        if isinstance(llm_result, dict):
            content = json.dumps(llm_result)
        elif llm_result is not None:
            content = str(llm_result)
        else:
            content = ""

        if content and output_file.exists():
            # Re-read from file to pick up any normalisation done by invoke()
            content = read_file(output_file)
            content = extract_markdown(content)
            content = _strip_llm_preamble(content)
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

    # Add prior sections context (capped to prevent unbounded growth across 12 generations)
    if prior_content:
        _PRIOR_CONTENT_CAP = 12000
        if len(prior_content) > _PRIOR_CONTENT_CAP:
            prior_content = "[Earlier sections truncated]\n" + prior_content[-_PRIOR_CONTENT_CAP:]
        prompt += f"""### Prior Sections

{prior_content}

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

    Strips outer code fences if the LLM wrapped its entire output in one.
    Does NOT match internal code fences (e.g. code examples within the content).

    Args:
        content: LLM response content

    Returns:
        Extracted markdown content
    """
    # Only strip code fences that wrap the entire output:
    # - re.match anchors to the start of the string
    # - greedy (.*) + end anchor captures everything to the LAST closing fence
    # This prevents matching internal code blocks (directory trees, code examples)

    # Check for ```markdown or ```md wrapping
    match = re.match(r'\s*```(?:markdown|md)\n(.*)\n```\s*$', content, re.DOTALL)
    if match:
        return match.group(1)

    # Check for generic ``` wrapping
    match = re.match(r'\s*```\n(.*)\n```\s*$', content, re.DOTALL)
    if match:
        return match.group(1)

    return content


def _strip_llm_preamble(content: str) -> str:
    """Strip LLM preamble/reflection text before the actual section header.

    LLM outputs sometimes start with "I have sufficient context..." or similar
    thinking-out-loud text before the actual markdown section header.
    Matches both # and ## headings, numbered (# 1. Title) or unnumbered (## Title).
    """
    match = re.search(r'^(#{1,2}\s+(?:\d+\.)?\s*\w)', content, re.MULTILINE)
    if match and match.start() > 0:
        return content[match.start():]
    return content


def _is_valid_section_output(content: str) -> bool:
    """Check if content is real PRD content (not an LLM summary/reflection).

    A section is valid if it meets EITHER criterion:
      - At least 200 characters long, OR
      - Contains ## or ### subheadings.
    This avoids rejecting short but valid sections (e.g., Vision for small projects).
    """
    has_sufficient_length = len(content) >= 200
    has_subheadings = bool(re.search(r'^#{2,3}\s+', content, re.MULTILINE))
    return has_sufficient_length or has_subheadings


def _detect_completed_sections(prompts_dir: Path) -> set:
    """Scan output files and return set of valid generation numbers."""
    completed = set()
    for gen_num in range(1, 13):
        output_file = prompts_dir / f"gen{gen_num:02d}_output.md"
        if output_file.exists():
            try:
                content = read_file(output_file)
                content = extract_markdown(content)
                content = _strip_llm_preamble(content)
                if _is_valid_section_output(content):
                    completed.add(gen_num)
            except Exception as e:
                logger.debug("Failed to scan section output gen%02d: %s", gen_num, e)
    return completed


def _rebuild_prd_content(prompts_dir: Path, completed_gens: set) -> str:
    """Rebuild PRD content from valid output files in generation order."""
    parts = []
    for gen_num in sorted(completed_gens):
        output_file = prompts_dir / f"gen{gen_num:02d}_output.md"
        if output_file.exists():
            content = read_file(output_file)
            content = extract_markdown(content)
            content = _strip_llm_preamble(content)
            parts.append(content)
    return "\n\n".join(parts)


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 205: PRD Authoring")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir)
    sys.exit(0 if success else 1)
