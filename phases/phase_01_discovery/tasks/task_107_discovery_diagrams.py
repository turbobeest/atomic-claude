"""
Task 107: Discovery Diagrams

Generate standard software architecture diagrams in DOT format.

Diagram types:
  - System Context (C4 Level 1)
  - Container/Component View (C4 Level 2)
  - Data Flow Diagram
  - Sequence Diagrams (key flows)
  - State Diagram (if applicable)
  - Deployment/Operational View
  - Entity Relationship Diagram

Output: docs/diagrams/*.dot + *.svg
"""

import json
import logging
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.llm import invoke_llm as invoke
from core.ui import phase_header, success, error, warning, info, step


# Diagram type definitions
DIAGRAM_TYPES = {
    "1": ("system-context", "System Context", "C4 Level 1: System + external actors"),
    "2": ("container", "Container View", "C4 Level 2: High-level components"),
    "3": ("component", "Component View", "C4 Level 3: Internal structure"),
    "4": ("data-flow", "Data Flow", "How data moves through system"),
    "5": ("sequence", "Sequence Diagram", "Key interaction flows"),
    "6": ("state", "State Diagram", "State machine for key entities"),
    "7": ("deployment", "Deployment View", "Infrastructure/operational"),
    "8": ("er-diagram", "ER Diagram", "Entity relationships/data model"),
}


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None, graph=None) -> bool:
    """
    Execute Task 107: Discovery Diagrams.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, skip diagram generation
        mem: Optional TaskMemory instance for recording substantive memory

    Returns:
        True if diagrams generated successfully, False otherwise
    """
    project_root = atomic_root.parent
    diagrams_dir = project_root / "docs" / "diagrams"
    prompts_dir = output_dir / "prompts"

    step("Discovery Diagrams")

    diagrams_dir.mkdir(parents=True, exist_ok=True)
    prompts_dir.mkdir(parents=True, exist_ok=True)

    # UAT Mode: Skip diagram generation
    if uat_mode:
        print()
        print("  ⚡ UAT Mode: Skipping diagram generation")
        print()

        _create_uat_manifest(diagrams_dir)
        success("Diagram generation skipped (UAT mode)")
        return True

    print()
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │ DISCOVERY DIAGRAMS                                      │")
    print("  │                                                         │")
    print("  │ Generate standard architecture diagrams based on the   │")
    print("  │ selected approach. DOT files will be converted to SVG  │")
    print("  │ for human review.                                       │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()

    # Check for graphviz
    has_graphviz = _check_graphviz()

    # Load approach context
    approach_context = _load_approach_context(output_dir)

    # ═══════════════════════════════════════════════════════════════
    # DIAGRAM TYPE SELECTION
    # ═══════════════════════════════════════════════════════════════

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ DIAGRAM TYPE SELECTION                                    ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    print("  Select diagrams to generate (space-separated numbers):")
    print()
    for num, (_, name, desc) in DIAGRAM_TYPES.items():
        print(f"    {num}. {name:20s} - {desc}")
    print()
    print("    [all]      Generate all applicable diagrams")
    print("    [minimal]  System Context + Container only")
    print("    [standard] Context + Container + Data Flow + Deployment")
    print()

    diagram_selection = input("  Selection (default: standard): ").strip().lower() or "standard"

    selected_diagrams = _parse_diagram_selection(diagram_selection)

    print()
    print(f"  ✓ Selected: {', '.join(selected_diagrams)}")
    print()

    # ═══════════════════════════════════════════════════════════════
    # GENERATE DIAGRAMS
    # ═══════════════════════════════════════════════════════════════

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ GENERATING DIAGRAMS                                       ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    generated_count = 0
    failed_count = 0

    for diagram_type in selected_diagrams:
        print(f"  [{diagram_type}]")

        # Generate DOT file
        dot_file = diagrams_dir / f"{diagram_type}.dot"
        if _generate_diagram(diagram_type, dot_file, prompts_dir, approach_context):
            print(f"    ✓ Generated {diagram_type}.dot")
            generated_count += 1

            # Convert to SVG if graphviz available
            if has_graphviz:
                svg_file = diagrams_dir / f"{diagram_type}.svg"
                if _convert_to_svg(dot_file, svg_file):
                    print(f"    ✓ Generated {diagram_type}.svg")
                else:
                    print(f"    ! SVG conversion failed")
        else:
            print(f"    ✗ Generation failed")
            failed_count += 1

        print()

    # ═══════════════════════════════════════════════════════════════
    # DIAGRAM MANIFEST
    # ═══════════════════════════════════════════════════════════════

    _create_manifest(diagrams_dir, selected_diagrams, generated_count, failed_count, approach_context)

    # ═══════════════════════════════════════════════════════════════
    # HUMAN REVIEW
    # ═══════════════════════════════════════════════════════════════

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ DIAGRAM REVIEW                                            ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    print(f"  Generated: {generated_count} diagrams")
    if failed_count > 0:
        print(f"  Failed: {failed_count}")
    print()
    print(f"  Location: {diagrams_dir}")
    print()

    # List generated files
    print("  Files:")
    for diagram_type in selected_diagrams:
        dot_file = diagrams_dir / f"{diagram_type}.dot"
        svg_file = diagrams_dir / f"{diagram_type}.svg"

        if dot_file.exists():
            dot_lines = len(dot_file.read_text().splitlines())
            if svg_file.exists():
                print(f"    ● {diagram_type}.dot ({dot_lines} lines) + .svg")
            else:
                print(f"    ● {diagram_type}.dot ({dot_lines} lines) (no SVG)")

    print()
    print("━" * 60)
    print()

    # Approval loop
    while True:
        approval = input("  Approve diagrams? [Y/n]: ").strip().lower()
        if approval == 'n':
            print()
            print(f"  Review diagrams at: {diagrams_dir}")
            print()
            print("  Options:")
            print("    [retry]    Regenerate all diagrams")
            print("    [continue] Approve and continue")
            print("    [abort]    Abort diagram task")
            print()
            choice = input("  Choice (default: continue): ").strip().lower() or "continue"

            if choice == "retry":
                print()
                print("  Regenerating diagrams...")
                print()
                generated_count = 0
                failed_count = 0
                for diagram_type in selected_diagrams:
                    print(f"  [{diagram_type}]")
                    dot_file = diagrams_dir / f"{diagram_type}.dot"
                    if _generate_diagram(diagram_type, dot_file, prompts_dir, approach_context):
                        print(f"    ✓ Generated {diagram_type}.dot")
                        generated_count += 1
                        if has_graphviz:
                            svg_file = diagrams_dir / f"{diagram_type}.svg"
                            if _convert_to_svg(dot_file, svg_file):
                                print(f"    ✓ Generated {diagram_type}.svg")
                            else:
                                print(f"    ! SVG conversion failed")
                    else:
                        print(f"    ✗ Generation failed")
                        failed_count += 1
                    print()
                _create_manifest(diagrams_dir, selected_diagrams, generated_count, failed_count, approach_context)
                continue  # Loop back to approval prompt
            elif choice == "abort":
                warning("Diagram task aborted by user")
                return False
            else:
                break  # "continue" — accept and move on
        else:
            break  # "Y" or Enter — accept and move on

    print()

    # Record substantive memory
    if mem:
        mem.finding(f"Diagrams generated: {generated_count} ({', '.join(selected_diagrams)})")
        mem.finding(f"Graphviz: {'available (SVG output)' if has_graphviz else 'not installed (DOT only)'}")

    success("Discovery diagrams complete")
    return True


def _check_graphviz() -> bool:
    """Check if graphviz is installed."""
    try:
        result = subprocess.run(['dot', '-V'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✓ graphviz available")
            return True
    except FileNotFoundError:
        pass

    print("  ! graphviz not installed - SVG generation will be skipped")
    print("    Install with: apt install graphviz / brew install graphviz")
    return False


def _load_approach_context(output_dir: Path) -> Dict[str, str]:
    """Load approach and project context."""
    context = {
        "approach_name": "unknown",
        "approach_summary": "",
        "tech_stack": "",
        "vision": "",
        "project_name": "",
        "project_description": "",
        "project_type": ""
    }

    # Load project config (name, description, type) from Phase 0
    config_file = output_dir.parent / "0-setup" / "project-config.json"
    if config_file.exists():
        try:
            with open(config_file) as f:
                cfg = json.load(f)
            project = cfg.get("project", {})
            context["project_name"] = project.get("name", "")
            context["project_description"] = project.get("description", "")
            context["project_type"] = project.get("type", "")
        except Exception as e:
            logger.debug("Failed to load project config for diagrams: %s", e)

    # Load approach
    approach_file = output_dir / "selected-approach.json"
    if approach_file.exists():
        with open(approach_file) as f:
            data = json.load(f)
        context["approach_name"] = data.get("name", "unknown")
        context["approach_summary"] = data.get("summary", "")

    # Load dialogue synthesis (full vision, constraints, impact)
    dialogue_file = output_dir / "dialogue.json"
    if dialogue_file.exists():
        with open(dialogue_file) as f:
            data = json.load(f)
        synthesis = data.get("synthesis", {})
        vision = synthesis.get("vision", {})
        context["vision"] = vision.get("core_problem", "")
        if vision.get("solution_concept"):
            context["solution_concept"] = vision["solution_concept"]
        impact = synthesis.get("impact", {})
        if impact.get("primary_impact"):
            context["impact"] = impact["primary_impact"]
        audience = synthesis.get("audience", {})
        if audience.get("primary"):
            context["audience"] = audience["primary"]
        constraints = synthesis.get("constraints", {})
        if constraints.get("tech_stack"):
            context["tech_stack"] = constraints["tech_stack"]
        non_neg = synthesis.get("non_negotiables", [])
        if non_neg:
            context["non_negotiables"] = non_neg

    # Load corpus analysis for technical context
    corpus_analysis_file = output_dir / "corpus-analysis.md"
    if corpus_analysis_file.exists():
        try:
            analysis_text = corpus_analysis_file.read_text().strip()
            if analysis_text:
                context["corpus_analysis"] = analysis_text
        except Exception as e:
            logger.debug("Failed to load corpus analysis for diagrams: %s", e)

    return context


def _parse_diagram_selection(selection: str) -> List[str]:
    """Parse user diagram selection."""
    if selection == "all":
        return [dt for dt, _, _ in DIAGRAM_TYPES.values()]
    elif selection == "minimal":
        return ["system-context", "container"]
    elif selection == "standard":
        return ["system-context", "container", "data-flow", "deployment"]
    else:
        # Parse space-separated numbers
        selected = []
        for num in selection.split():
            if num in DIAGRAM_TYPES:
                diagram_type, _, _ = DIAGRAM_TYPES[num]
                selected.append(diagram_type)
        return selected or ["system-context", "container", "data-flow", "deployment"]


def _generate_diagram(diagram_type: str, output_file: Path, prompts_dir: Path,
                      context: Dict[str, str]) -> bool:
    """Generate a diagram DOT file using LLM."""
    prompt_file = prompts_dir / f"diagram-{diagram_type}.md"

    # Build prompt
    project_identity = ""
    if context.get('project_name'):
        project_identity += f"**Project:** {context['project_name']}\n"
    if context.get('project_description'):
        project_identity += f"**Description:** {context['project_description']}\n"
    if context.get('project_type'):
        project_identity += f"**Type:** {context['project_type']}\n"

    extra_context = ""
    if context.get('solution_concept'):
        extra_context += f"**Solution Concept:** {context['solution_concept']}\n"
    if context.get('impact'):
        extra_context += f"**Impact:** {context['impact']}\n"
    if context.get('audience'):
        extra_context += f"**Primary Audience:** {context['audience']}\n"
    if context.get('non_negotiables'):
        extra_context += f"**Non-Negotiables:** {', '.join(str(n) for n in context['non_negotiables'])}\n"
    if context.get('corpus_analysis'):
        extra_context += f"\n**Technical Landscape (from corpus analysis):**\n{context['corpus_analysis']}\n"

    context_section = f"""{project_identity}
**Approach:** {context['approach_name']}
{context['approach_summary']}

**Vision:** {context['vision']}
{extra_context}
**Tech Stack:** {context.get('tech_stack', 'Not specified')}
"""

    diagram_instructions = _get_diagram_instructions(diagram_type)

    prompt_content = f"""# Task: Generate {diagram_type} Diagram

You are a software architect creating a DOT (Graphviz) diagram.
IMPORTANT: This diagram is for the user's project described below, NOT for the development tool/framework.
Stay focused on THIS project — do not confuse it with the development tool/framework.

## Project Context

{context_section}

## Diagram Type: {diagram_type}

{diagram_instructions}

## Output

Output ONLY valid DOT code. No markdown fences, no explanation.
Start directly with the digraph line.

digraph {diagram_type.replace('-', '_')} {{
    // Your diagram here
}}
"""

    prompt_file.write_text(prompt_content)

    # Invoke LLM
    try:
        invoke(str(prompt_file), str(output_file), f"Generate {diagram_type} diagram", model="sonnet")

        # Clean output (remove markdown fences if present)
        if output_file.exists():
            content = output_file.read_text()
            # Extract DOT content
            if '```' in content:
                lines = content.split('\n')
                dot_lines = []
                in_code = False
                for line in lines:
                    if line.startswith('```'):
                        in_code = not in_code
                        continue
                    if in_code or line.startswith('digraph') or line.startswith('graph'):
                        dot_lines.append(line)
                content = '\n'.join(dot_lines)
            output_file.write_text(content)

        return output_file.exists()
    except Exception as e:
        print(f"    Error: {e}")
        return False


def _get_diagram_instructions(diagram_type: str) -> str:
    """Get instructions for a specific diagram type."""
    instructions = {
        "system-context": "Create a C4 System Context diagram showing the main system, external users/actors, and external systems.",
        "container": "Create a C4 Container diagram showing major containers/services within the system boundary.",
        "component": "Create a C4 Component diagram showing internal components within a key container.",
        "data-flow": "Create a Data Flow Diagram (DFD) showing data sources, processes, stores, and flows.",
        "sequence": "Create a sequence diagram showing key actors/components and messages between them.",
        "state": "Create a State Diagram showing states, transitions with event labels, and guard conditions.",
        "deployment": "Create a Deployment diagram showing physical/cloud infrastructure, servers, and deployment artifacts.",
        "er-diagram": "Create an Entity-Relationship diagram showing entities with attributes and relationships.",
    }
    return instructions.get(diagram_type, "Create a diagram representing the system architecture.")


def _convert_to_svg(dot_file: Path, svg_file: Path) -> bool:
    """Convert DOT file to SVG using graphviz."""
    try:
        result = subprocess.run(
            ['dot', '-Tsvg', str(dot_file), '-o', str(svg_file)],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0
    except Exception as e:
        logger.debug("DOT to SVG compilation failed: %s", e)
        return False


def _create_manifest(diagrams_dir: Path, selected_diagrams: List[str],
                     generated: int, failed: int, context: Dict[str, str]) -> None:
    """Create diagram manifest."""
    diagrams_json = []
    for diagram_type in selected_diagrams:
        dot_file = diagrams_dir / f"{diagram_type}.dot"
        svg_file = diagrams_dir / f"{diagram_type}.svg"

        if dot_file.exists():
            diagrams_json.append({
                "type": diagram_type,
                "dot_file": str(dot_file),
                "svg_file": str(svg_file),
                "has_svg": svg_file.exists()
            })

    manifest = {
        "approach": context["approach_name"],
        "diagrams": diagrams_json,
        "summary": {
            "generated": generated,
            "failed": failed
        },
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

    manifest_file = diagrams_dir / "manifest.json"
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)


def _create_uat_manifest(diagrams_dir: Path) -> None:
    """Create minimal manifest for UAT mode."""
    manifest = {
        "summary": {
            "generated": 0,
            "successful": 0,
            "mode": "uat"
        },
        "diagrams": []
    }

    with open(diagrams_dir / "manifest.json", 'w') as f:
        json.dump(manifest, f, indent=2)


if __name__ == "__main__":
    # CLI execution support
    atomic_root = Path.cwd()
    output_dir = atomic_root.parent / ".outputs" / "1-discovery"
    uat_mode = "--uat" in sys.argv

    sys.exit(0 if execute(atomic_root, output_dir, uat_mode) else 1)
