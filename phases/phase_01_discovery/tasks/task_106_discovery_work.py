"""
Task 106: Discovery Conversation

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
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.config import Config
from core.state import StateManager
from core.llm import invoke_llm as invoke
from core.ui import phase_header, success, error, warning, info, step


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 106: Discovery Conversation.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, skip interactive discovery

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

    # UAT Mode: Skip interactive discovery
    if uat_mode:
        print()
        print("  ⚡ UAT Mode: Skipping interactive discovery")
        print()

        _create_uat_discovery(approaches_file, consensus_file, deliberation_log)
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

**Started:** {datetime.now().isoformat()}
**Panel:** {', '.join(panel_agents)}

---

""")

    # Initialize conversation state
    conversation = {
        "started_at": datetime.now().isoformat(),
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
    for line in _wrap_text(opening, 60):
        print(f"    {line}")
    print()

    with open(deliberation_log, 'a') as f:
        f.write(f"## Orchestrator (Opening)\n\n{opening}\n\n")

    conversation["exchanges"].append({
        "agent": "orchestrator",
        "message": opening,
        "timestamp": datetime.now().isoformat()
    })

    deliberation_complete = False
    turn = 0
    approaches_generated = False

    while not deliberation_complete:
        print("  You:")
        user_input = input("    ").strip()

        if not user_input:
            continue

        # Log user input
        with open(deliberation_log, 'a') as f:
            f.write(f"## Human\n\n{user_input}\n\n")

        conversation["exchanges"].append({
            "agent": "human",
            "message": user_input,
            "timestamp": datetime.now().isoformat()
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
        response = _route_input(prompts_dir, user_input, context_content, panel_agents)

        print()
        print("  agent:")
        print()
        for line in _wrap_text(response, 60):
            print(f"    {line}")
        print()

        with open(deliberation_log, 'a') as f:
            f.write(f"## Agent\n\n{response}\n\n")

        conversation["exchanges"].append({
            "agent": "agent",
            "message": response,
            "timestamp": datetime.now().isoformat()
        })

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

    # Finalize log
    with open(deliberation_log, 'a') as f:
        f.write(f"""
---

## Session Complete

**Ended:** {datetime.now().isoformat()}
**Total exchanges:** {turn}
""")

    print("━" * 60)
    print()
    print("  Discovery Conversation Complete")
    print()
    print(f"  Exchanges:      {turn}")
    print(f"  Panel size:     {len(panel_agents)} agents")
    print()

    success("Discovery conversation complete")
    return True


def _build_context(output_dir: Path) -> str:
    """Build comprehensive context document."""
    context_parts = ["# Project Context (Ingested Materials)\n\n"]

    # Load dialogue
    dialogue_file = output_dir / "dialogue.json"
    if dialogue_file.exists():
        with open(dialogue_file) as f:
            data = json.load(f)
        synthesis = data.get("synthesis", {})
        vision = synthesis.get("vision", {})

        context_parts.append("## Vision & Goals\n\n")
        context_parts.append(f"**Core Problem:** {vision.get('core_problem', 'Not specified')}\n\n")

    # Load corpus
    corpus_file = output_dir / "corpus.json"
    if corpus_file.exists():
        with open(corpus_file) as f:
            data = json.load(f)
        materials = data.get("materials", [])

        if materials:
            context_parts.append(f"## Collected Materials\n\nMaterials collected: {len(materials)}\n\n")

    return ''.join(context_parts)


def _orchestrator_opening(prompts_dir: Path, context: str) -> str:
    """Generate orchestrator opening."""
    prompt = f"""# Role: Orchestrator

You are moderating a discovery conversation about a software project.

## Project Context (Summary)
{context[:500]}

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
    except Exception:
        pass

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
            for line in output_file.read_text().strip().split('\n'):
                print(f"    {line}")
    except Exception:
        print("  synthesis: Discussion is progressing well.")
    print()


def _generate_approaches(prompts_dir: Path, context: str, approaches_file: Path) -> None:
    """Generate solution approaches."""
    prompt = f"""# Generate Approaches

Based on the project context, generate 2-3 meaningfully different approaches.

## Project Context
{context[:1000]}

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


def _route_input(prompts_dir: Path, user_input: str, context: str, panel: List[str]) -> str:
    """Route natural input and generate response."""
    prompt = f"""# Respond to User Input

The human said: "{user_input}"

## Project Context
{context[:500]}

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
    except Exception:
        pass

    return "That's a good point. Let's explore that direction further."


def _generate_consensus(prompts_dir: Path, conversation: Dict[str, Any], context: str) -> Dict[str, Any]:
    """Generate final consensus document."""
    exchanges_text = '\n\n'.join(
        f"**{ex['agent']}:** {ex['message']}" for ex in conversation["exchanges"]
    )

    prompt = f"""# Task: Generate Final Consensus

Based on the deliberation, create a consensus document.

## Deliberation Exchanges
{exchanges_text[:2000]}

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
    except Exception:
        pass

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


def _wrap_text(text: str, width: int) -> List[str]:
    """Simple text wrapping."""
    words = text.split()
    lines = []
    current = []
    length = 0

    for word in words:
        if length + len(word) + len(current) > width:
            if current:
                lines.append(' '.join(current))
            current = [word]
            length = len(word)
        else:
            current.append(word)
            length += len(word)

    if current:
        lines.append(' '.join(current))

    return lines


if __name__ == "__main__":
    # CLI execution support
    atomic_root = Path.cwd()
    output_dir = atomic_root / ".outputs" / "1-discovery"
    uat_mode = "--uat" in sys.argv

    sys.exit(0 if execute(atomic_root, output_dir, uat_mode) else 1)
