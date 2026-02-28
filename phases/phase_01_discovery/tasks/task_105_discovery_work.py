"""
Task 105: Discovery Conversation

Multi-agent deliberation to establish project direction.

This is a CONFERENCE TABLE conversation where:
  - Multiple agents deliberate on approaches
  - Agents can disagree (healthy!)
  - Human orchestrates and directs
  - Haiku provides fast synthesis
  - Consensus emerges through dialogue

Outputs:
  - approaches.json        - Generated approaches with agent attributions
  - deliberation-log.md    - Full conversation transcript
  - consensus.json         - Agreed positions and next steps
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.llm import invoke_llm as invoke
from core.ui import success, warning, info, step, wrap_text

try:
    from core.discovery.canvas import (
        CanvasState, classify_exchange, render_canvas,
        render_canvas_compact, suggest_next_topic, PRD_SECTIONS,
    )
    HAS_CANVAS = True
except ImportError:
    HAS_CANVAS = False


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None, graph=None) -> bool:
    """
    Execute Task 105: Discovery Conversation.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, skip interactive discovery
        mem: Optional TaskMemory instance for recording substantive memory

    Returns:
        True if discovery completed successfully, False otherwise
    """
    approaches_file = output_dir / "approaches.json"
    consensus_file = output_dir / "consensus.json"
    deliberation_log = output_dir / "deliberation-log.md"
    context_file = output_dir / "ingested-context.md"
    prompts_dir = output_dir / "prompts"

    step("Discovery Conversation")

    prompts_dir.mkdir(parents=True, exist_ok=True)

    # Load canvas from task 104 (or create fresh)
    canvas = None
    if HAS_CANVAS:
        canvas_file = output_dir / "canvas.json"
        if canvas_file.exists():
            try:
                canvas = CanvasState.from_dict(json.loads(canvas_file.read_text()))
            except Exception as e:
                logger.debug("Failed to load canvas: %s", e)
        if canvas is None:
            canvas = CanvasState()

    # UAT Mode: Skip interactive discovery
    if uat_mode:
        print()
        print("  ⚡ UAT Mode: Skipping interactive discovery")
        print()

        _create_uat_discovery(approaches_file, consensus_file, deliberation_log)

        if HAS_CANVAS:
            canvas_file = output_dir / "canvas.json"
            if not canvas_file.exists():
                try:
                    uat_canvas = CanvasState()
                    uat_canvas.scores["vision"] = 0.6
                    uat_canvas.scores["architecture"] = 0.3
                    canvas_file.write_text(json.dumps(uat_canvas.to_dict(), indent=2))
                except Exception as e:
                    logger.debug("Failed to save UAT canvas: %s", e)

        success("Discovery conversation complete (UAT mode)")
        return True

    # ═══════════════════════════════════════════════════════════════
    # INTRODUCTION
    # ═══════════════════════════════════════════════════════════════

    print()
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║                                                           ║")
    print("║  DISCOVERY CONVERSATION                                   ║")
    print("║                                                           ║")
    print("║  This is where your project takes shape.                  ║")
    print("║                                                           ║")
    print("║  You're about to sit at a conference table with           ║")
    print("║  specialized agents. They'll deliberate on approaches,    ║")
    print("║  challenge assumptions, and work toward consensus.        ║")
    print("║                                                           ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # ═══════════════════════════════════════════════════════════════
    # AGENT ROSTER
    # ═══════════════════════════════════════════════════════════════

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ YOUR PANEL                                                 ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    panel_agents = [
        "orchestrator",
        "discovery-facilitator",
        "first-principles-analyst"
    ]

    # Load expert agents
    agents_file = output_dir / "selected-agents.json"
    if agents_file.exists():
        with open(agents_file) as f:
            data = json.load(f)
        experts = data.get("selected_experts", [])
        panel_agents.extend(experts[:3])  # Limit to 3 experts for focus

    print("  These agents will join the conversation:")
    print()
    for i, agent in enumerate(panel_agents, 1):
        print(f"    {i}. {agent}")
    print()

    # ═══════════════════════════════════════════════════════════════
    # DEEP INGESTION
    # ═══════════════════════════════════════════════════════════════

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ INGESTING PROJECT CONTEXT                                 ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    print("  Deep reading project materials...")

    # Build comprehensive context document
    context_content = _build_context(output_dir)
    context_file.write_text(context_content)

    print("  ✓ Project context ingested")
    print()

    # Initialize deliberation log
    deliberation_log.write_text(f"""# Discovery Deliberation Log

**Started:** {datetime.now(timezone.utc).isoformat()}
**Panel:** {', '.join(panel_agents)}

---

""")

    # Initialize conversation state
    conversation = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "panel": panel_agents,
        "exchanges": []
    }

    # ═══════════════════════════════════════════════════════════════
    # CONVERSATION LOOP
    # ═══════════════════════════════════════════════════════════════

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ CONFERENCE TABLE                                          ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    print("  Commands:")
    print("    canvas      Show PRD coverage map")
    print("    generate    Generate/refine approaches")
    print("    synthesize  Get quick summary of discussion")
    print("    done        Conclude deliberation")
    print()
    print("  Or just type naturally - the orchestrator will route your input.")
    print()
    print("━" * 60)
    print()

    # Orchestrator opens
    opening = _orchestrator_opening(prompts_dir, context_content)
    print("  orchestrator:")
    print()
    for line in wrap_text(opening, 60):
        print(line)
    print()

    with open(deliberation_log, 'a') as f:
        f.write(f"## Orchestrator (Opening)\n\n{opening}\n\n")

    conversation["exchanges"].append({
        "agent": "orchestrator",
        "message": opening,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    deliberation_complete = False
    turn = 0
    approaches_generated = False

    while not deliberation_complete:
        # Show status bar with available commands
        status_parts = [f"Turn {turn}"]
        if canvas:
            try:
                pct = int(canvas.overall_coverage * 100)
                status_parts.append(f"Canvas: {pct}%")
            except Exception:
                pass
        if approaches_generated:
            status_parts.append("approaches ready")
        else:
            status_parts.append("no approaches yet")

        # Show gaps in status
        if canvas:
            try:
                empty = canvas.empty_sections
                if empty:
                    names = []
                    for eid in empty[:3]:
                        for s in PRD_SECTIONS:
                            if s["id"] == eid:
                                names.append(s["name"].split(" ")[0])
                                break
                    suffix = f" +{len(empty) - 3}" if len(empty) > 3 else ""
                    status_parts.append(f"Gaps: {', '.join(names)}{suffix}")
            except Exception:
                pass

        print(f"  [{' │ '.join(status_parts)}]")
        print(f"  Commands:  canvas  │  generate  │  synthesize  │  done")
        print(f"  Or speak naturally to the panel.")

        if canvas and turn > 1 and turn % 3 == 0:
            try:
                suggestion = suggest_next_topic(canvas)
                if suggestion:
                    print(f"  Suggested: {suggestion}")
            except Exception:
                pass

        print()
        user_input = input("  You: ").strip()

        if not user_input:
            continue

        # Canvas command: show coverage map (not a deliberation turn)
        if user_input.lower() == 'canvas' and canvas:
            try:
                print(render_canvas(canvas))
            except Exception as e:
                logger.debug("Canvas render failed: %s", e)
            continue

        # Log user input
        with open(deliberation_log, 'a') as f:
            f.write(f"## Human\n\n{user_input}\n\n")

        conversation["exchanges"].append({
            "agent": "human",
            "message": user_input,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        turn += 1

        # Parse command
        input_lower = user_input.lower()

        # Detect closure intent
        if any(phrase in input_lower for phrase in ['done', 'proceed', 'move on', 'wrap up', 'finish', 'ready']):
            print()
            print("  Detected closure intent. Closing deliberation...")
            deliberation_complete = True
            break

        if input_lower in ('synthesize', 'summary'):
            _synthesize(prompts_dir, conversation)
            continue

        if input_lower in ('generate', 'approaches'):
            _generate_approaches(prompts_dir, context_content, approaches_file)
            approaches_generated = True
            continue

        # Route natural input
        response = _route_input(prompts_dir, user_input, context_content, panel_agents, conversation)

        print()
        print("  Agent:")
        print()
        for line in wrap_text(response, 60):
            print(line)
        print()

        with open(deliberation_log, 'a') as f:
            f.write(f"## Agent\n\n{response}\n\n")

        conversation["exchanges"].append({
            "agent": "agent",
            "message": response,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # Canvas classification
        if canvas:
            try:
                exchange_text = f"Human: {user_input}\nAgent: {response}"
                classification = classify_exchange(exchange_text, prompts_dir, turn)
                canvas.update(turn, classification, exchange_text)
            except Exception as e:
                logger.debug("Canvas classification failed: %s", e)

        # Record exchange substance and checkpoint periodically
        if mem:
            mem.conversation(f"Exchange {turn}: User: {user_input[:150]}")
            mem.conversation(f"Exchange {turn}: Panel: {response[:200]}")
            if turn % 3 == 0:
                mem.checkpoint(f"Deliberation exchanges {max(1, turn-2)}-{turn}")

    # ═══════════════════════════════════════════════════════════════
    # FINAL CONSENSUS
    # ═══════════════════════════════════════════════════════════════

    print()
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ CONCLUDING DELIBERATION                                   ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    print("  Generating consensus...")

    consensus = _generate_consensus(prompts_dir, conversation, context_content)

    with open(consensus_file, 'w') as f:
        json.dump(consensus, f, indent=2)

    print("  ✓ Consensus captured")
    print()

    # Display consensus
    direction = consensus.get("agreed_direction", {}).get("approach", "No clear direction")
    print(f"  Agreed Direction: {direction}")
    print()

    # Save canvas state
    if canvas:
        try:
            canvas_file = output_dir / "canvas.json"
            canvas_file.write_text(json.dumps(canvas.to_dict(), indent=2))
        except Exception as e:
            logger.debug("Failed to save canvas: %s", e)

    # Finalize log
    with open(deliberation_log, 'a') as f:
        f.write(f"""
---

## Session Complete

**Ended:** {datetime.now(timezone.utc).isoformat()}
**Total exchanges:** {turn}
""")

    print("━" * 60)
    print()
    print("  Discovery Conversation Complete")
    print()
    print(f"  Exchanges:      {turn}")
    print(f"  Panel size:     {len(panel_agents)} agents")
    print()

    # Record substantive memory
    if mem:
        mem.finding(f"Panel: {', '.join(str(a) for a in panel_agents)}")
        # Count approaches from file if available
        if approaches_file.exists():
            try:
                approaches_data = json.loads(approaches_file.read_text())
                approach_count = len(approaches_data.get("approaches", []))
                mem.finding(f"Approaches generated: {approach_count}")
            except Exception as e:
                logger.debug("Failed to read approaches file: %s", e)
        mem.decision(f"Consensus direction: {direction}")
        key_decisions = consensus.get("key_decisions", [])
        if key_decisions:
            mem.decision(f"Key decisions: {', '.join(str(d) for d in key_decisions[:5])}")
        open_items = consensus.get("open_items", [])
        if open_items:
            mem.warning(f"Open items: {', '.join(str(i) for i in open_items[:5])}")

    # Write to knowledge graph
    if graph:
        graph.add_source(
            id="S-105-deliberation",
            type="meeting",
            title=f"Discovery Deliberation ({turn} exchanges)",
        )
        direction = consensus.get("agreed_direction", {}).get("approach", "")
        if direction:
            graph.add_finding(
                id="F-105-direction",
                category="vision",
                title="Agreed Direction",
                content=str(direction),
                source_id="S-105-deliberation",
            )
        for i, decision in enumerate(consensus.get("key_decisions", [])[:10]):
            graph.add_decision(
                id=f"DEC-105-{i+1}",
                title=f"Key Decision {i+1}",
                rationale=str(decision),
                status="proposed",
            )
        for i, item in enumerate(consensus.get("open_items", [])[:10]):
            graph.add_finding(
                id=f"F-105-open-{i+1}",
                category="open_question",
                title=f"Open Item {i+1}",
                content=str(item),
                source_id="S-105-deliberation",
            )

    success("Discovery conversation complete")
    return True


def _build_context(output_dir: Path) -> str:
    """Build comprehensive context from all prior task outputs."""
    parts = ["# Project Context\n"]

    # 1. Full dialogue synthesis (Task 104)
    dialogue_file = output_dir / "dialogue.json"
    if dialogue_file.exists():
        try:
            data = json.loads(dialogue_file.read_text())
            synthesis = data.get("synthesis", {})

            vision = synthesis.get("vision", {})
            parts.append("\n## Vision & Goals\n")
            if vision.get("core_problem"):
                parts.append(f"**Core Problem:** {vision['core_problem']}\n")
            if vision.get("solution_concept"):
                parts.append(f"**Solution:** {vision['solution_concept']}\n")
            if vision.get("why_now"):
                parts.append(f"**Why Now:** {vision['why_now']}\n")

            impact = synthesis.get("impact", {})
            if impact:
                parts.append("\n## Impact & Success\n")
                if impact.get("primary_impact"):
                    parts.append(f"**Primary Impact:** {impact['primary_impact']}\n")
                metrics = impact.get("success_metrics", [])
                if metrics:
                    parts.append("**Success Metrics:**\n")
                    for m in metrics:
                        parts.append(f"- {m}\n")

            constraints = synthesis.get("constraints", {})
            if constraints and isinstance(constraints, dict):
                parts.append("\n## Constraints\n")
                for key, val in constraints.items():
                    if val:
                        label = key.replace("_", " ").title()
                        if isinstance(val, list):
                            parts.append(f"**{label}:** {', '.join(str(v) for v in val)}\n")
                        else:
                            parts.append(f"**{label}:** {val}\n")

            non_neg = synthesis.get("non_negotiables", [])
            if non_neg:
                parts.append("\n## Non-Negotiables\n")
                for n in non_neg:
                    parts.append(f"- {n}\n")

            open_q = synthesis.get("open_questions", [])
            if open_q:
                parts.append("\n## Open Questions (from Task 104)\n")
                for q in open_q:
                    parts.append(f"- {q}\n")

            audience = synthesis.get("audience", {})
            if audience and isinstance(audience, dict):
                parts.append("\n## Audience\n")
                if audience.get("primary"):
                    parts.append(f"**Primary:** {audience['primary']}\n")
                pain = audience.get("pain_points", [])
                if pain:
                    parts.append("**Pain Points:**\n")
                    for p in pain:
                        parts.append(f"- {p}\n")
        except Exception as e:
            logger.debug("Failed to load dialogue synthesis: %s", e)

    # 2. Corpus analysis (Task 102) — the full detailed analysis
    corpus_analysis = output_dir / "corpus-analysis.md"
    if corpus_analysis.exists():
        try:
            analysis_text = corpus_analysis.read_text().strip()
            if analysis_text:
                parts.append(f"\n## Corpus Analysis\n\n{analysis_text}\n")
        except Exception as e:
            logger.debug("Failed to load corpus analysis: %s", e)

    # 3. Needs index (Task 102) — if it exists
    needs_file = output_dir / "needs-index.json"
    if needs_file.exists():
        try:
            needs_data = json.loads(needs_file.read_text())
            needs = needs_data.get("needs", [])
            if needs:
                parts.append(f"\n## Imported Requirements ({len(needs)} items)\n")
                for need in needs[:20]:  # Cap at 20
                    nid = need.get("id", "")
                    title = need.get("title", "")
                    parts.append(f"- [{nid}] {title}\n")
        except Exception as e:
            logger.debug("Failed to load needs index: %s", e)

    return ''.join(parts)


def _orchestrator_opening(prompts_dir: Path, context: str) -> str:
    """Generate orchestrator opening."""
    prompt = f"""# Role: Orchestrator

You are moderating a discovery conversation about a software project.

## Project Context
{context}

## Your Task

Open the deliberation with:
1. A brief acknowledgment of the project's core problem (1 sentence)
2. A framing question to start discussion

Keep it concise - 2-3 sentences max.
"""

    prompt_file = prompts_dir / "opening.md"
    output_file = prompts_dir / "opening-response.txt"

    prompt_file.write_text(prompt)

    try:
        invoke(str(prompt_file), str(output_file), "Orchestrator opening", model="sonnet")

        if output_file.exists():
            return output_file.read_text().strip()
    except Exception as e:
        logger.debug("LLM orchestrator opening failed: %s", e)

    return "Let's discuss the best approach for this project. What directions should we consider?"


def _synthesize(prompts_dir: Path, conversation: Dict[str, Any]) -> None:
    """Quick synthesis of discussion."""
    recent = conversation["exchanges"][-10:]
    recent_text = '\n'.join(f"{ex['agent']}: {ex['message']}" for ex in recent)

    prompt = f"""# Quick Synthesis

Summarize the discussion in 2-3 bullet points.

## Recent Exchanges
{recent_text}

Be extremely concise. Output plain text, no JSON.
"""

    prompt_file = prompts_dir / "synthesize.md"
    output_file = prompts_dir / "synthesis.txt"

    prompt_file.write_text(prompt)

    print()
    try:
        invoke(str(prompt_file), str(output_file), "Synthesis", model="haiku")

        if output_file.exists():
            print("  synthesis:")
            print()
            for line in wrap_text(output_file.read_text().strip(), 60):
                print(line)
    except Exception as e:
        logger.debug("LLM synthesis failed: %s", e)
        print("  synthesis: Discussion is progressing well.")
    print()


def _generate_approaches(prompts_dir: Path, context: str, approaches_file: Path) -> None:
    """Generate solution approaches."""
    prompt = f"""# Generate Approaches

Based on the project context, generate 2-3 meaningfully different approaches.

## Project Context
{context}

## Output Format

Return ONLY valid JSON:

{{
    "approaches": [
        {{
            "id": "A",
            "name": "Approach Name",
            "summary": "Brief description",
            "key_decisions": ["Decision 1", "Decision 2"],
            "complexity": "simple|moderate|complex"
        }}
    ]
}}
"""

    prompt_file = prompts_dir / "generate-approaches.md"

    prompt_file.write_text(prompt)

    print()
    print("  Generating approaches...")

    try:
        invoke(str(prompt_file), str(approaches_file), "Generate approaches", model="sonnet")

        if approaches_file.exists():
            with open(approaches_file) as f:
                data = json.load(f)

            print("  ✓ Approaches generated")
            print()
            for approach in data.get("approaches", []):
                print(f"    [{approach['id']}] {approach['name']} ({approach.get('complexity', 'unknown')})")
                print(f"        {approach['summary']}")
    except Exception as e:
        print(f"  ! Generation failed: {e}")
    print()


def _route_input(prompts_dir: Path, user_input: str, context: str, panel: List[str],
                  conversation: Dict[str, Any] = None) -> str:
    """Route natural input and generate response."""
    # Build recent exchange context from current session
    recent_text = ""
    if conversation and conversation.get("exchanges"):
        recent = conversation["exchanges"][-6:]
        recent_text = '\n'.join(
            f"{ex['agent']}: {ex['message']}" for ex in recent
        )

    prompt = f"""# Respond to User Input

The human said: "{user_input}"

## Recent Discussion
{recent_text}

## Full Project Context
{context}

## Panel Members
{', '.join(panel)}

Respond helpfully as one of the panel members. Keep it to 2-4 sentences.
Output plain text, no JSON.
"""

    prompt_file = prompts_dir / "route.md"
    output_file = prompts_dir / "route-response.txt"

    prompt_file.write_text(prompt)

    try:
        invoke(str(prompt_file), str(output_file), "Route input", model="sonnet")

        if output_file.exists():
            return output_file.read_text().strip()
    except Exception as e:
        logger.debug("LLM route input failed: %s", e)

    return "That's a good point. Let's explore that direction further."


def _generate_consensus(prompts_dir: Path, conversation: Dict[str, Any], context: str) -> Dict[str, Any]:
    """Generate final consensus document."""
    exchanges_text = '\n\n'.join(
        f"**{ex['agent']}:** {ex['message']}" for ex in conversation["exchanges"]
    )

    prompt = f"""# Task: Generate Final Consensus

Based on the deliberation, create a consensus document.

## Deliberation Exchanges
{exchanges_text[:4000]}

## Output

Return ONLY valid JSON:

{{
    "agreed_direction": {{
        "approach": "What approach emerged?",
        "rationale": "Why this direction?"
    }},
    "key_decisions": ["Decision 1", "Decision 2"],
    "open_items": ["What needs resolution?"],
    "next_steps": ["What to do next?"],
    "dissenting_views": []
}}
"""

    prompt_file = prompts_dir / "final-consensus.md"
    output_file = prompts_dir / "consensus.json"

    prompt_file.write_text(prompt)

    try:
        invoke(str(prompt_file), str(output_file), "Final consensus", model="sonnet")

        if output_file.exists():
            with open(output_file) as f:
                return json.load(f)
    except Exception as e:
        logger.debug("LLM consensus generation failed: %s", e)

    # Fallback consensus
    return {
        "agreed_direction": {
            "approach": "Phased Implementation",
            "rationale": "Allows iterative development with validation at each stage"
        },
        "key_decisions": ["Start with MVP", "Validate early"],
        "open_items": [],
        "next_steps": ["Define Phase 1 scope"],
        "dissenting_views": []
    }


def _create_uat_discovery(approaches_file: Path, consensus_file: Path, deliberation_log: Path) -> None:
    """Create minimal discovery files for UAT mode."""
    with open(approaches_file, 'w') as f:
        json.dump({
            "approaches": [
                {
                    "name": "Phased Implementation",
                    "description": "UAT mode: Minimal approach for testing",
                    "pros": ["Systematic validation"],
                    "cons": ["Simplified for testing"],
                    "recommended": True
                }
            ]
        }, f, indent=2)

    with open(consensus_file, 'w') as f:
        json.dump({
            "consensus": {
                "approach": "Phased Implementation",
                "key_decisions": ["UAT mode testing"],
                "next_steps": ["Proceed to approach selection"]
            }
        }, f, indent=2)

    deliberation_log.write_text("""## UAT Mode

Discovery conversation skipped in UAT mode.

Approach: Phased Implementation (testing)
""")




if __name__ == "__main__":
    # CLI execution support
    atomic_root = Path.cwd()
    output_dir = atomic_root.parent / ".outputs" / "1-discovery"
    uat_mode = "--uat" in sys.argv

    sys.exit(0 if execute(atomic_root, output_dir, uat_mode) else 1)
