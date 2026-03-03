"""
Task 104: Opening Dialogue (Conversation 3)

Deep conversational exchange with human about vision, goals, and constraints.
NOTE: Now runs AFTER agent selection so agents can participate.

This is a TRUE CONVERSATION - not a form to fill out.

Flow:
  1. Agent reviews corpus (if available) and opens with observations
  2. If greenfield: ask for initial vision
  3. Back-and-forth dialogue until mutual understanding
  4. Capture consensus on impact, audience, success criteria
  5. Gather constraints through conversation

The conversation continues until:
  - Human says they're satisfied, OR
  - Agent has gathered all critical information
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.llm import invoke_llm as invoke
from core.ui import success, warning, step, wrap_text

try:
    from core.discovery.canvas import (
        CanvasState, classify_exchange, render_canvas,
        render_canvas_compact, suggest_next_topic,
    )
    HAS_CANVAS = True
except ImportError:
    HAS_CANVAS = False


def execute(atomic_root: Path, output_dir: Path, mem=None, graph=None) -> bool:
    """
    Execute Task 104: Opening Dialogue.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        mem: Optional TaskMemory instance for recording substantive memory

    Returns:
        True if dialogue completed successfully, False otherwise
    """
    corpus_file = output_dir / "corpus.json"
    dialogue_output = output_dir / "dialogue.json"
    conversation_log = output_dir / "conversation-log.md"
    prompts_dir = output_dir / "prompts"

    step("Opening Dialogue")

    prompts_dir.mkdir(parents=True, exist_ok=True)

    print()
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │ CONVERSATION 3: OPENING DIALOGUE                        │")
    print("  │                                                         │")
    print("  │ This is a real conversation, not a form.                │")
    print("  │ We'll talk until we both understand the vision.        │")
    print("  │                                                         │")
    print("  │ Type 'done' when you feel we've covered enough.        │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()

    # Initialize dialogue tracking
    dialogue = {
        "conversation": [],
        "synthesis": {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "turns": 0
    }

    # Start conversation log
    conversation_log.write_text("# Opening Dialogue - Conversation Log\n\n")

    # ═══════════════════════════════════════════════════════════════
    # DETERMINE CONTEXT
    # ═══════════════════════════════════════════════════════════════

    has_corpus = False
    corpus_summary = ""
    project_context = ""

    # Load project config for context
    config_file = output_dir.parent / "0-setup" / "project-config.json"
    if config_file.exists():
        try:
            cfg = json.loads(config_file.read_text())
            project = cfg.get("project", {})
            pname = project.get("name", "")
            pdesc = project.get("description", "")
            ptype = project.get("type", "")
            project_context = f"**Project:** {pname}\n**Description:** {pdesc}\n**Type:** {ptype}\n"
        except Exception as e:
            logger.debug("Failed to load project config: %s", e)

    # Load corpus analysis results (from task 101)
    corpus_analysis_file = output_dir / "corpus-analysis.md"
    if corpus_analysis_file.exists():
        try:
            analysis_text = corpus_analysis_file.read_text().strip()
            if analysis_text:
                project_context += f"\n**Corpus Analysis:**\n{analysis_text}\n"
        except Exception as e:
            logger.debug("Failed to load corpus analysis: %s", e)

    if corpus_file.exists():
        try:
            with open(corpus_file) as f:
                corpus_data = json.load(f)
        except json.JSONDecodeError:
            logger.warning("Failed to parse corpus file: %s", corpus_file)
            corpus_data = {}
        materials = corpus_data.get("materials", [])
        material_count = len(materials)
        if material_count > 0:
            has_corpus = True
            corpus_summary = f"Found {material_count} materials collected"
            # Include material names in project context for informed dialogue
            material_names = [m.get("name", m.get("path", "unknown")) for m in materials[:20]]
            if material_names:
                project_context += f"\n**Materials Found:** {', '.join(material_names)}\n"

    # ═══════════════════════════════════════════════════════════════
    # CONVERSATION LOOP
    # ═══════════════════════════════════════════════════════════════

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ LET'S TALK                                                ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    turn = 0

    # Generate opening based on context
    if has_corpus:
        # Try to get a more informed opening from the corpus analysis
        corpus_analysis_file = output_dir / "corpus-analysis.md"
        pname = ""
        try:
            cfg = json.loads((output_dir.parent / "0-setup" / "project-config.json").read_text())
            pname = cfg.get("project", {}).get("name", "")
        except Exception as e:
            logger.debug("Failed to load project name from config: %s", e)

        if corpus_analysis_file.exists() and pname:
            agent_opening = (f"I've analyzed your {corpus_summary} for {pname}. "
                           f"I have a good picture of the technical landscape. "
                           f"What aspects of the project do you want to make sure we get right?")
        else:
            agent_opening = f"I've reviewed your materials ({corpus_summary}). What's the core problem you're trying to solve?"
    else:
        agent_opening = "This looks like a fresh start! What are you trying to build, and why does it matter to you?"

    print("  Agent:")
    print()
    for line in wrap_text(agent_opening, 60):
        print(line)
    print()

    # Log opening
    with open(conversation_log, 'a') as f:
        f.write(f"## Turn 1\n\n**Agent:** {agent_opening}\n\n")

    dialogue["conversation"].append({"role": "agent", "content": agent_opening})
    turn += 1

    conversation_complete = False
    gathered_vision = False
    gathered_impact = False
    gathered_constraints = False
    canvas = CanvasState() if HAS_CANVAS else None

    while not conversation_complete:
        # Show turn count and hint
        topics_left = []
        if not gathered_vision:
            topics_left.append("vision")
        if not gathered_impact:
            topics_left.append("impact")
        if not gathered_constraints:
            topics_left.append("constraints")

        if canvas and turn > 1:
            print(f"  [{turn} turns]  {render_canvas_compact(canvas)}  │  done to finish")
        elif topics_left:
            print(f"  [{turn} turns]  Topics remaining: {', '.join(topics_left)}  │  done to finish")
        else:
            print(f"  [{turn} turns]  All topics covered  │  done to finish")
        print()

        if canvas and turn > 0 and turn % 5 == 0:
            print(render_canvas(canvas))

        if canvas and turn > 2 and turn % 3 == 0:
            try:
                suggestion = suggest_next_topic(canvas)
                if suggestion:
                    print(f"  Suggested: {suggestion}")
                    print()
            except Exception as e:
                logger.debug("Canvas suggestion failed: %s", e)

        human_response = input("  You: ").strip()

        # Check for canvas command
        input_lower = human_response.lower()
        if input_lower == 'canvas' and canvas:
            print(render_canvas(canvas))
            continue  # Don't count as a dialogue turn

        # Check for exit
        if input_lower in ('done', 'finished', 'exit', 'quit', 'skip'):
            if turn < 3 and input_lower != 'skip':
                print("  (Talk a bit more, or type 'skip' to exit early)")
                continue
            conversation_complete = True
            break

        if not human_response:
            continue

        # Log human response
        with open(conversation_log, 'a') as f:
            f.write(f"**Human:** {human_response}\n\n")

        dialogue["conversation"].append({"role": "human", "content": human_response})
        turn += 1

        # Determine what to probe for next
        probe_focus = ""
        if not gathered_vision:
            probe_focus = "vision and core problem"
            gathered_vision = True
        elif not gathered_impact:
            probe_focus = "desired impact and success metrics"
            gathered_impact = True
        elif not gathered_constraints:
            probe_focus = "constraints (tech, timeline, team, compliance)"
            gathered_constraints = True
        else:
            probe_focus = "anything unclear"

        # Generate agent response
        agent_response = _generate_response(prompts_dir, dialogue, probe_focus, project_context)

        print()
        print("  Agent:")
        print()
        for line in wrap_text(agent_response, 60):
            print(line)
        print()

        # Log agent response
        with open(conversation_log, 'a') as f:
            f.write(f"## Turn {turn + 1}\n\n**Agent:** {agent_response}\n\n")

        dialogue["conversation"].append({"role": "agent", "content": agent_response})
        turn += 1

        # Canvas classification
        if canvas:
            try:
                exchange_text = f"Human: {human_response}\nAgent: {agent_response}"
                classification = classify_exchange(exchange_text, prompts_dir, turn)
                canvas.update(turn, classification, exchange_text)
            except Exception as e:
                logger.debug("Canvas classification failed: %s", e)

        # Record conversation substance and checkpoint periodically
        if mem:
            mem.conversation(f"Turn {turn-1}: User: {human_response[:150]}")
            mem.conversation(f"Turn {turn}: Agent: {agent_response[:200]}")
            if turn % 4 == 0:
                mem.checkpoint(f"Dialogue turns {max(1, turn-3)}-{turn}")

        # Suggest wrapping up after several turns
        if canvas and turn >= 8 and canvas.overall_coverage > 0.3:
            empty_count = len(canvas.empty_sections)
            if empty_count == 0:
                print("    (All PRD sections have some coverage. 'done' to proceed.)")
            else:
                print(f"    ({empty_count} PRD sections still empty. 'done' to proceed anyway, or keep going.)")
            print()
        elif turn >= 10 and gathered_constraints:
            print("    (We've covered a lot. Type 'done' if you're satisfied)")
            print()

    # ═══════════════════════════════════════════════════════════════
    # SYNTHESIZE CONVERSATION
    # ═══════════════════════════════════════════════════════════════

    print()
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ SYNTHESIZING CONVERSATION                                 ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    synthesis = _synthesize_dialogue(prompts_dir, dialogue, project_context)
    dialogue["synthesis"] = synthesis

    # Display synthesis
    print("  ✓ Conversation synthesized")
    print()
    print("  Summary:")
    print()
    print(f"    Vision: {synthesis.get('vision', {}).get('core_problem', 'Not captured')}")
    print(f"    Impact: {synthesis.get('impact', {}).get('primary_impact', 'Not captured')}")
    print(f"    Audience: {synthesis.get('audience', {}).get('primary', 'Not captured')}")
    print()

    # Confirm with human
    confirm = input("  Does this capture our conversation accurately? [Y/n]: ").strip().lower()
    if confirm == 'n':
        print()
        corrections = input("  What should be corrected? ").strip()
        dialogue["synthesis"]["corrections"] = corrections
        print("  ✓ Corrections noted")

    # ═══════════════════════════════════════════════════════════════
    # SAVE DIALOGUE
    # ═══════════════════════════════════════════════════════════════

    dialogue["turns"] = turn

    with open(dialogue_output, 'w') as f:
        json.dump(dialogue, f, indent=2)

    if canvas:
        try:
            canvas_file = output_dir / "canvas.json"
            canvas_file.write_text(json.dumps(canvas.to_dict(), indent=2))
        except Exception as e:
            logger.debug("Failed to save canvas: %s", e)

    print()
    print("━" * 60)
    print()
    print("  Opening Dialogue Complete")
    print(f"  Turns: {turn}")
    print()

    # Record substantive memory
    if mem:
        has_corpus = corpus_file.exists()
        mem.conversation(f"Dialogue: {turn} turns ({'corpus-based' if has_corpus else 'greenfield'})")
        vision = synthesis.get("vision", {})
        if vision.get("core_problem"):
            mem.finding(f"Core problem: {vision['core_problem']}")
        if vision.get("solution_concept"):
            mem.finding(f"Solution concept: {vision['solution_concept']}")
        impact = synthesis.get("impact", {})
        if impact.get("primary_impact"):
            mem.finding(f"Primary impact: {impact['primary_impact']}")
        metrics = impact.get("success_metrics", [])
        if metrics:
            mem.finding(f"Success metrics: {', '.join(str(m) for m in metrics[:5])}")
        constraints = synthesis.get("constraints", "")
        if constraints:
            mem.finding(f"Constraints: {constraints}")
        non_neg = synthesis.get("non_negotiables", [])
        if non_neg:
            mem.decision(f"Non-negotiables: {', '.join(str(n) for n in non_neg[:5])}")
        open_q = synthesis.get("open_questions", [])
        if open_q:
            mem.warning(f"Open questions: {', '.join(str(q) for q in open_q[:5])}")

    # Write to knowledge graph
    if graph:
        # Source node for the dialogue itself
        graph.add_source(
            id="S-104-dialogue",
            type="dialogue",
            title=f"Opening Dialogue ({turn} turns)",
        )
        # Finding nodes from synthesis
        vision = synthesis.get("vision", {})
        if vision.get("core_problem"):
            graph.add_finding(
                id="F-104-core-problem",
                category="vision",
                title="Core Problem",
                content=str(vision["core_problem"]),
                source_id="S-104-dialogue",
            )
        if vision.get("solution_concept"):
            graph.add_finding(
                id="F-104-solution",
                category="vision",
                title="Solution Concept",
                content=str(vision["solution_concept"]),
                source_id="S-104-dialogue",
            )
        impact = synthesis.get("impact", {})
        if impact.get("primary_impact"):
            graph.add_finding(
                id="F-104-impact",
                category="impact",
                title="Primary Impact",
                content=str(impact["primary_impact"]),
                source_id="S-104-dialogue",
            )
        audience = synthesis.get("audience", {})
        if audience.get("primary"):
            graph.add_finding(
                id="F-104-audience",
                category="audience",
                title="Primary Audience",
                content=str(audience["primary"]),
                source_id="S-104-dialogue",
            )
        constraints = synthesis.get("constraints", "")
        if constraints:
            graph.add_finding(
                id="F-104-constraints",
                category="constraint",
                title="Constraints",
                content=str(constraints),
                source_id="S-104-dialogue",
            )
        non_neg = synthesis.get("non_negotiables", [])
        if non_neg:
            graph.add_finding(
                id="F-104-non-negotiables",
                category="non_negotiable",
                title="Non-Negotiables",
                content=", ".join(str(n) for n in non_neg),
                source_id="S-104-dialogue",
            )
        open_q = synthesis.get("open_questions", [])
        if open_q:
            graph.add_finding(
                id="F-104-open-questions",
                category="open_question",
                title="Open Questions",
                content=", ".join(str(q) for q in open_q),
                source_id="S-104-dialogue",
            )

    success("Opening dialogue complete")
    return True


def _generate_response(prompts_dir: Path, dialogue: Dict[str, Any], probe_focus: str,
                       project_context: str = "") -> str:
    """Generate agent response using LLM."""
    conversation_text = '\n\n'.join(
        f"{msg['role']}: {msg['content']}" for msg in dialogue["conversation"]
    )

    context_block = ""
    if project_context:
        context_block = f"""## Project Context
{project_context}

"""

    prompt = f"""# Task: Continue the Discovery Dialogue

You are the discovery-facilitator in an ongoing conversation about a specific project (described below). Stay focused on THIS project — do not confuse it with the development tool/framework being used.

{context_block}## Conversation So Far
{conversation_text}

## Current Focus
{probe_focus}

## Guidelines
- Keep responses to 2-4 sentences
- Ask ONE question per turn
- Be specific, not generic
- Reference details from the project context when relevant
- If they're uncertain, offer concrete examples from the materials

Output ONLY your response, no formatting.
"""

    prompt_file = prompts_dir / "dialogue-continue.md"
    output_file = prompts_dir / "continue-response.txt"

    prompt_file.write_text(prompt)

    try:
        invoke(str(prompt_file), str(output_file), "Continue dialogue", model="sonnet")

        if output_file.exists():
            return output_file.read_text().strip()
    except Exception as e:
        logger.debug("LLM dialogue continuation failed: %s", e)

    # Fallback responses
    fallbacks = {
        "vision": "What would success look like for this project in 6 months?",
        "impact": "Who benefits most from this, and how will we measure that impact?",
        "constraints": "What constraints are we working within - technology, timeline, team size, compliance?"
    }

    for key, fallback in fallbacks.items():
        if key in probe_focus.lower():
            return fallback

    return "That's clear. Is there anything else important I should know?"


def _synthesize_dialogue(prompts_dir: Path, dialogue: Dict[str, Any],
                         project_context: str = "") -> Dict[str, Any]:
    """Synthesize dialogue into structured output."""
    conversation_text = '\n\n'.join(
        f"{msg['role']}: {msg['content']}" for msg in dialogue["conversation"]
    )

    context_block = ""
    if project_context:
        context_block = f"""## Project Context (use to fill gaps in conversation)
{project_context}

"""

    prompt = f"""# Task: Synthesize Dialogue into Structured Output

Extract structured data from this natural conversation about a specific project.

{context_block}## Conversation
{conversation_text}

## Output Format

Return ONLY valid JSON with no additional text:

{{
    "vision": {{
        "core_problem": "What problem are we solving?",
        "solution_concept": "High-level approach",
        "why_now": "Why is this important now?"
    }},
    "impact": {{
        "primary_impact": "Main outcome",
        "success_metrics": ["How we'll measure success"],
        "timeline_to_value": "When will impact be realized?"
    }},
    "audience": {{
        "primary": "Main beneficiary",
        "secondary": ["Other stakeholders"],
        "pain_points": ["What they struggle with today"]
    }},
    "constraints": {{
        "tech_stack": "Required/preferred technologies",
        "timeline": "Key milestones or deadlines",
        "team_size": "Number of people",
        "compliance": ["Regulatory requirements"]
    }},
    "non_negotiables": ["Things that must be true"],
    "open_questions": ["Things still unclear"]
}}
"""

    prompt_file = prompts_dir / "dialogue-synthesis.md"
    output_file = prompts_dir / "synthesis.json"

    prompt_file.write_text(prompt)

    try:
        invoke(str(prompt_file), str(output_file), "Synthesize dialogue", model="sonnet")

        if output_file.exists():
            content = output_file.read_text()
            # Clean JSON (remove markdown fences)
            if '```' in content:
                lines = content.split('\n')
                json_lines = []
                in_fence = False
                for line in lines:
                    if '```' in line:
                        in_fence = not in_fence
                        continue
                    if in_fence:
                        json_lines.append(line)
                content = '\n'.join(json_lines)

            return json.loads(content)
    except Exception as e:
        logger.warning("LLM dialogue synthesis failed (using fallback placeholders): %s", e)

    # Fallback synthesis — placeholder data, not actual synthesis
    warning("Synthesis failed — using placeholder data (not derived from conversation)")
    return {
        "vision": {"core_problem": "Not fully captured", "solution_concept": "", "why_now": ""},
        "impact": {"primary_impact": "Not discussed", "success_metrics": [], "timeline_to_value": ""},
        "audience": {"primary": "Not specified", "secondary": [], "pain_points": []},
        "constraints": {"tech_stack": "Flexible", "timeline": "Not specified", "team_size": "", "compliance": []},
        "non_negotiables": [],
        "open_questions": []
    }




if __name__ == "__main__":
    # CLI execution support
    atomic_root = Path.cwd()
    output_dir = atomic_root.parent / ".outputs" / "1-discovery"

    sys.exit(0 if execute(atomic_root, output_dir) else 1)
