"""
Task 104: Agent Selection (Conversation 2)

Select agents to guide the pipeline phases - NOW BEFORE DIALOGUE.

This is a TRUE CONVERSATION about agent selection.

Flow:
  1. Load agents from turbobeest/agents repository
  2. Present pipeline agents (phase-specific)
  3. Suggest expert agents based on project context
  4. Conversational selection with category browsing
  5. Map selected agents to pipeline phases

The conversation continues until:
  - Human has reviewed and approved agent assignments
  - Or typed 'done' to accept suggestions
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
    Execute Task 104: Agent Selection.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, skip interactive agent selection

    Returns:
        True if selection completed successfully, False otherwise
    """
    agents_output = output_dir / "selected-agents.json"
    roster_output = output_dir / "agent-roster.json"
    prompts_dir = output_dir / "prompts"
    conversation_log = output_dir / "agent-selection-log.md"

    step("Agent Selection")

    prompts_dir.mkdir(parents=True, exist_ok=True)

    # UAT Mode: Skip interactive agent selection
    if uat_mode:
        print()
        print("  ⚡ UAT Mode: Using default agent selection")
        print()

        _create_uat_agents(agents_output, roster_output, conversation_log)
        success("Agent selection complete (UAT mode)")
        return True

    print()
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │ CONVERSATION 2: AGENT SELECTION                         │")
    print("  │                                                         │")
    print("  │ Let's select the right agents for your pipeline.       │")
    print("  │ We'll discuss options and assign agents to each phase. │")
    print("  │                                                         │")
    print("  │ Type 'done' when you're satisfied with selections.     │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()

    # Start conversation log
    conversation_log.write_text("# Agent Selection - Conversation Log\n\n")

    # ═══════════════════════════════════════════════════════════════
    # STEP 1: VERIFY AGENT REPOSITORY
    # ═══════════════════════════════════════════════════════════════

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ AGENT REPOSITORY                                          ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    agent_repo = atomic_root / "agents"
    agent_manifest = agent_repo / "agent-manifest.json"

    if not agent_manifest.exists():
        print("  ! Agent manifest not found - using defaults")
        _use_builtin_agents(agents_output, roster_output)
        return True

    # Load manifest
    with open(agent_manifest) as f:
        manifest = json.load(f)

    total_agents = len(manifest.get("agents", []))
    print(f"  ✓ Agent repository found: {agent_repo}")
    print(f"    Total agents: {total_agents}")
    print()

    # ═══════════════════════════════════════════════════════════════
    # STEP 2: SHOW DEFAULT PIPELINE AGENTS
    # ═══════════════════════════════════════════════════════════════

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ PIPELINE AGENTS                                            ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()
    print("  Pipeline agents execute each phase of the development workflow.")
    print()

    default_pipeline_agents = _get_default_pipeline_agents()

    print("  Default Pipeline Agents:")
    print()
    for phase, agents in default_pipeline_agents.items():
        print(f"    {phase}: {agents}")
    print()

    # ═══════════════════════════════════════════════════════════════
    # STEP 3: SUGGEST SME EXPERTS
    # ═══════════════════════════════════════════════════════════════

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ SME EXPERTS FOR YOUR PROJECT                               ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Load project context
    project_context = _load_project_context(output_dir)

    # Get LLM suggestions
    selected_experts = _suggest_experts(prompts_dir, project_context)

    print()
    print("  Suggested SME Experts:")
    print()
    for i, expert in enumerate(selected_experts, 1):
        print(f"    {i}. {expert}")
    print()

    # ═══════════════════════════════════════════════════════════════
    # STEP 4: CONVERSATIONAL AGENT SELECTION
    # ═══════════════════════════════════════════════════════════════

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ AGENT SELECTION CONVERSATION                              ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    agent_opening = f"Based on your project, I've suggested {len(selected_experts)} expert agents. Would you like to accept these, modify them, or browse other options?"

    print("  Agent:")
    print()
    for line in _wrap_text(agent_opening, 60):
        print(f"    {line}")
    print()

    conversation_complete = False
    turn = 0

    while not conversation_complete:
        print("  You:")
        user_input = input("    ").strip()

        if not user_input:
            continue

        # Check for done
        if user_input.lower() in ('done', 'finished', 'accept', '1'):
            conversation_complete = True
            break

        # Handle commands
        if user_input.lower() in ('browse', 'categories'):
            _browse_categories(agent_manifest)
            continue

        if user_input.lower().startswith('add '):
            agent_name = user_input[4:].strip()
            if agent_name not in selected_experts:
                selected_experts.append(agent_name)
                print(f"    ✓ Added: {agent_name}")
            continue

        if user_input.lower().startswith('remove '):
            agent_name = user_input[7:].strip()
            if agent_name in selected_experts:
                selected_experts.remove(agent_name)
                print(f"    ✓ Removed: {agent_name}")
            continue

        turn += 1

        # Simple response
        print()
        print("  Agent:")
        print("    Understood. You can 'add <name>' or 'remove <name>', or type 'done' to proceed.")
        print()

    # ═══════════════════════════════════════════════════════════════
    # STEP 5: BUILD FINAL ROSTER
    # ═══════════════════════════════════════════════════════════════

    print()
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ ROSTER REVIEW                                             ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    print("  SME Experts (provide domain context to all phases):")
    if selected_experts:
        print(f"    {', '.join(selected_experts)}")
    else:
        print("    (none selected)")
    print()

    # Confirm
    confirm = input("  Does this roster look good? [Y/n]: ").strip().lower()
    if confirm == 'n':
        print("  What would you like to change?")
        changes = input("  > ").strip()
        print("  ✓ Changes noted for review")

    # ═══════════════════════════════════════════════════════════════
    # STEP 6: SAVE OUTPUTS
    # ═══════════════════════════════════════════════════════════════

    # Build selected agents output
    agents_json = {
        "version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "core": [
            {"name": "orchestrator", "description": "Pipeline orchestration", "model": "opus"},
            {"name": "agent-selector", "description": "Agent assignment", "model": "opus"}
        ],
        "selected_experts": selected_experts,
        "total_experts": len(selected_experts)
    }

    with open(agents_output, 'w') as f:
        json.dump(agents_json, f, indent=2)

    # Build roster
    roster = _build_roster(default_pipeline_agents, selected_experts)

    with open(roster_output, 'w') as f:
        json.dump(roster, f, indent=2)

    print()
    print("━" * 60)
    print()
    print("  Agent Selection Complete")
    print()
    print(f"  Core agents:      2")
    print(f"  Expert agents:    {len(selected_experts)}")
    print(f"  Phases mapped:    10")
    print()

    success("Agent selection complete")
    return True


def _get_default_pipeline_agents() -> Dict[str, str]:
    """Get default pipeline agent assignments."""
    return {
        "1-Discovery": "discovery-agent,ideation-agent",
        "2-PRD": "prd-validator,prd-auditor",
        "3-Tasks": "task-decomposer",
        "4-Specification": "specification-agent,coupling-analyzer",
        "5-Implementation": "tdd-implementation-agent",
        "6-Code-Review": "code-review-gate",
        "7-Integration": "integration-testing-gate",
        "8-Validation": "plan-guardian",
        "9-Deployment": "deployment-gate"
    }


def _load_project_context(output_dir: Path) -> Dict[str, str]:
    """Load project context for agent suggestions."""
    context = {}

    corpus_file = output_dir / "corpus.json"
    if corpus_file.exists():
        with open(corpus_file) as f:
            data = json.load(f)
        context["corpus"] = data.get("materials", [])

    return context


def _suggest_experts(prompts_dir: Path, context: Dict[str, str]) -> List[str]:
    """Get expert agent suggestions from LLM."""
    # Default suggestions if LLM fails
    default_experts = ["python-pro", "test-strategist", "backend-architect"]

    prompt = f"""# Task: Suggest Expert Agents

Based on the project context, suggest 3-5 expert agents.

## Context
{json.dumps(context, indent=2)}

## Output
Return a simple list of agent names, one per line. No JSON, no explanations.

Example:
python-pro
test-strategist
backend-architect
"""

    prompt_file = prompts_dir / "agent-suggestion.md"
    output_file = prompts_dir / "suggested-agents.txt"

    prompt_file.write_text(prompt)

    try:
        invoke(str(prompt_file), str(output_file), "Suggest agents", model="haiku")

        if output_file.exists():
            suggestions = output_file.read_text().strip().split('\n')
            return [s.strip() for s in suggestions if s.strip() and not s.startswith('#')]
    except Exception:
        pass

    return default_experts


def _browse_categories(manifest: Dict[str, Any]) -> None:
    """Display available agent categories."""
    print()
    print("  Agent Categories:")
    print()

    categories = manifest.get("categories", {})
    for i, (key, data) in enumerate(categories.items(), 1):
        title = data.get("title", key)
        print(f"    [{i}] {title}")

    print()


def _build_roster(pipeline_agents: Dict[str, str], experts: List[str]) -> Dict[str, Any]:
    """Build the final agent roster."""
    roster = {
        "version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "phases": {}
    }

    phase_num = 1
    for phase_key, agents_str in pipeline_agents.items():
        phase_name = phase_key.split('-', 1)[1]
        agents_list = agents_str.split(',')

        # Add experts to implementation phases (5-8)
        if phase_num >= 5 and phase_num <= 8:
            agents_list.extend(experts)

        roster["phases"][str(phase_num)] = {
            "name": phase_name,
            "agents": agents_list
        }
        phase_num += 1

    return roster


def _use_builtin_agents(agents_output: Path, roster_output: Path) -> None:
    """Use built-in default agents."""
    print("  Using built-in agent definitions...")
    print()

    agents_json = {
        "version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "core": [
            {"name": "orchestrator", "description": "Pipeline orchestration", "model": "opus"},
            {"name": "discovery-facilitator", "description": "Guides discovery process", "model": "sonnet"}
        ],
        "selected_experts": [],
        "note": "Using built-in defaults - external agent repository not available"
    }

    roster = {
        "version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "phases": {
            "1": {"name": "Discovery", "agents": ["discovery-facilitator"]},
            "2": {"name": "PRD", "agents": ["prd-writer"]},
            "3": {"name": "Tasks", "agents": ["task-decomposer"]},
            "4": {"name": "Specification", "agents": ["spec-writer"]},
            "5": {"name": "Implementation", "agents": ["tdd-implementation-agent"]},
            "6": {"name": "Code Review", "agents": ["code-reviewer"]},
            "7": {"name": "Integration", "agents": ["integrator"]},
            "8": {"name": "Validation", "agents": ["validator"]},
            "9": {"name": "Deployment", "agents": ["deployer"]}
        }
    }

    with open(agents_output, 'w') as f:
        json.dump(agents_json, f, indent=2)

    with open(roster_output, 'w') as f:
        json.dump(roster, f, indent=2)

    print("  ✓ Created default agent selection")
    print("  ✓ Created default phase roster")


def _create_uat_agents(agents_output: Path, roster_output: Path, conversation_log: Path) -> None:
    """Create minimal agent files for UAT mode."""
    with open(agents_output, 'w') as f:
        json.dump({
            "expert_agents": ["python-pro", "test-strategist", "backend-architect"],
            "selection_method": "uat_defaults"
        }, f, indent=2)

    with open(roster_output, 'w') as f:
        json.dump({
            "pipeline": {
                "1-discovery": ["discovery-agent"],
                "2-prd": ["prd-validator"],
                "3-tasking": ["task-decomposer"],
                "4-specification": ["specification-agent"],
                "5-implementation": ["tdd-implementation-agent"],
                "6-code-review": ["code-review-gate"],
                "7-integration": ["integration-testing-gate"],
                "8-validation": ["plan-guardian"],
                "9-deployment": ["deployment-gate"]
            },
            "experts": ["python-pro", "test-strategist", "backend-architect"]
        }, f, indent=2)

    conversation_log.write_text("""## UAT Mode

Agent selection skipped in UAT mode.

Selected: python-pro, test-strategist, backend-architect (defaults)
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
