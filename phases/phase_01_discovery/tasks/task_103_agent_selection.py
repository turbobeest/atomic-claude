"""
Task 103: Agent Selection (Conversation 2)

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
import logging
import re
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.config import Config
from core.state import StateManager
from core.llm import invoke_llm as invoke
from core.ui import phase_header, success, error, warning, info, step, wrap_text
from core.utils.file_ops import write_json


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None, graph=None) -> bool:
    """
    Execute Task 103: Agent Selection.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, skip interactive agent selection
        mem: Optional TaskMemory instance for recording substantive memory

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

    # Load agents into knowledge graph (idempotent)
    if graph:
        loaded = graph.load_agents_from_manifest(agent_manifest)
        if loaded:
            print(f"  ✓ Loaded {loaded} agents into knowledge graph")
        else:
            print(f"  ✓ Agent catalog already in knowledge graph")

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

    # Get LLM suggestions (catalog-backed: graph preferred, manifest fallback)
    selected_experts = _suggest_experts(prompts_dir, project_context,
                                        manifest=manifest, graph=graph)

    print()
    print("  Suggested SMEs:")
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

    agent_opening = f"Based on your project, I've suggested {len(selected_experts)} expert agents. Review the list below and modify as needed."

    print("  Agent:")
    print()
    for line in wrap_text(agent_opening, 60):
        print(line)
    print()

    conversation_complete = False
    turn = 0

    while not conversation_complete:
        # Show current selections
        print("  ┌─ Current Experts ─────────────────────────────────────┐")
        if selected_experts:
            for i, expert in enumerate(selected_experts, 1):
                print(f"  │  {i}. {expert:<51s} │")
        else:
            print(f"  │  {'(none selected)':<51s} │")
        print("  └───────────────────────────────────────────────────────┘")
        print()
        print("  Commands:  add <name>  │  remove <name>  │  browse  │  done")
        print()
        user_input = input("  > ").strip()

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
                print(f"  ✓ Added: {agent_name}")
            else:
                print(f"  ℹ Already selected: {agent_name}")
            print()
            continue

        if user_input.lower().startswith('remove '):
            agent_name = user_input[7:].strip()
            if agent_name in selected_experts:
                selected_experts.remove(agent_name)
                print(f"  ✓ Removed: {agent_name}")
            else:
                print(f"  ℹ Not in list: {agent_name}")
            print()
            continue

        turn += 1

        # Unrecognized input — help
        print()
        print("  Try: add <name>, remove <name>, browse, or done")
        print()

    # ═══════════════════════════════════════════════════════════════
    # STEP 5: BUILD FINAL ROSTER
    # ═══════════════════════════════════════════════════════════════

    print()
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ ROSTER REVIEW                                             ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    print("  SMEs (provide domain context to all phases):")
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
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "core": [
            {"name": "orchestrator", "description": "Pipeline orchestration", "model": "opus"},
            {"name": "agent-selector", "description": "Agent assignment", "model": "opus"}
        ],
        "selected_experts": selected_experts,
        "total_experts": len(selected_experts)
    }

    write_json(agents_output, agents_json)

    # Build roster
    roster = _build_roster(default_pipeline_agents, selected_experts)

    write_json(roster_output, roster)

    print()
    print("━" * 60)
    print()
    print("  Agent Selection Complete")
    print()
    print(f"  Core agents:      2")
    print(f"  Expert agents:    {len(selected_experts)}")
    print(f"  Phases mapped:    10")
    print()

    # Record substantive memory
    if mem:
        mem.finding(f"Expert agents selected: {len(selected_experts)}")
        if selected_experts:
            mem.decision(f"Final experts: {', '.join(selected_experts)}")

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

    # Load project config (name, description, type) from Phase 0
    config_file = output_dir.parent / "0-setup" / "project-config.json"
    if config_file.exists():
        try:
            cfg = json.loads(config_file.read_text())
            project = cfg.get("project", {})
            context["project_name"] = project.get("name", "")
            context["project_description"] = project.get("description", "")
            context["project_type"] = project.get("type", "")
            constraints = cfg.get("constraints", {})
            tech = constraints.get("technical", [])
            if tech:
                context["technical_constraints"] = tech
        except Exception as e:
            logger.debug("Failed to load project config for context: %s", e)

    # Load corpus analysis (the detailed analysis from task 101)
    analysis_file = output_dir / "corpus-analysis.md"
    if analysis_file.exists():
        try:
            context["corpus_analysis"] = analysis_file.read_text().strip()
        except Exception as e:
            logger.debug("Failed to read corpus analysis: %s", e)

    corpus_file = output_dir / "corpus.json"
    if corpus_file.exists():
        try:
            with open(corpus_file) as f:
                data = json.load(f)
            context["corpus"] = data.get("materials", [])
        except Exception as e:
            logger.debug("Failed to read corpus.json: %s", e)

    # Load dialogue synthesis if available (from task 104)
    dialogue_file = output_dir / "dialogue.json"
    if dialogue_file.exists():
        try:
            with open(dialogue_file) as f:
                dialogue_data = json.load(f)
            synthesis = dialogue_data.get("synthesis", {})
            if synthesis:
                context["dialogue_synthesis"] = synthesis
        except Exception as e:
            logger.debug("Failed to read dialogue synthesis: %s", e)

    return context


def _suggest_experts(prompts_dir: Path, context: Dict[str, str],
                     manifest: Dict = None, graph=None) -> List[str]:
    """Get expert agent suggestions from LLM.

    Always includes the real agent catalog in the prompt (from graph or
    manifest) and validates suggestions against known names — eliminating
    hallucinated agent names.
    """
    # Default suggestions if LLM fails
    default_experts = ["python-pro", "test-strategist", "backend-architect"]

    # Build the set of valid agent names and a catalog string for the prompt
    valid_names = set()
    catalog = ""

    if graph:
        # Prefer graph-backed catalog
        catalog = graph.query_agent_catalog(tier="expert")
        try:
            valid_agents = graph.reader.get_nodes("Agent")
            valid_names = {a["id"] for a in valid_agents}
        except Exception as e:
            logger.debug("Failed to query agent nodes from graph: %s", e)

    if not catalog and manifest:
        # Fallback: build catalog directly from manifest JSON
        catalog, valid_names = _build_catalog_from_manifest(manifest)

    # Build a focused context summary (avoid dumping raw corpus file list)
    context_summary = ""
    if context.get("project_name"):
        context_summary += f"**Project:** {context['project_name']}\n"
    if context.get("project_description"):
        context_summary += f"**Description:** {context['project_description']}\n"
    if context.get("project_type"):
        context_summary += f"**Type:** {context['project_type']}\n"
    if context.get("technical_constraints"):
        context_summary += f"**Constraints:** {', '.join(context['technical_constraints'][:10])}\n"
    if context.get("corpus_analysis"):
        # Include the full corpus analysis for informed agent suggestions
        context_summary += f"\n**Corpus Analysis:**\n{context['corpus_analysis']}\n"
    if context.get("dialogue_synthesis"):
        synthesis = context["dialogue_synthesis"]
        vision = synthesis.get("vision", {})
        constraints = synthesis.get("constraints", {})
        if vision.get("core_problem"):
            context_summary += f"\n**Vision:** {vision['core_problem']}\n"
        if vision.get("solution_concept"):
            context_summary += f"**Solution Concept:** {vision['solution_concept']}\n"
        if constraints:
            context_summary += f"**Constraints:** {json.dumps(constraints)}\n"

    prompt = f"""# Task: Suggest Expert Agents

Based on the project context below, suggest 3-5 expert agents from the available roster. Focus on the project's domain, NOT on the development framework/tool being used.

## Project Context
{context_summary}
"""

    # Include real agent catalog in prompt
    if catalog:
        prompt += f"\n## Available Agents\n\n{catalog}\n"
        prompt += "\nIMPORTANT: You MUST only suggest agents from the list above. Use exact agent names as shown. Do NOT invent agent names.\n"

    prompt += """
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
            # Filter: agent names are short lowercase-hyphenated tokens.
            # Skip comments, blank lines, and LLM preamble (prose sentences).
            parsed = []
            for s in suggestions:
                s = s.strip().lstrip('- ').strip()
                if not s or s.startswith('#'):
                    continue
                # Skip prose lines (contain spaces and are long = LLM preamble)
                if ' ' in s and len(s) > 40:
                    continue
                # Strip leading numbers like "1. " or "2) "
                s = re.sub(r'^\d+[\.\)]\s*', '', s).strip()
                if s:
                    parsed.append(s)

            # Validate against known agents — drop hallucinated names
            if valid_names and parsed:
                validated = [s for s in parsed if s in valid_names]
                if validated:
                    return validated
                # All suggestions were hallucinated — fall through to defaults

            return parsed if parsed else default_experts
    except Exception as e:
        logger.debug("LLM agent suggestion failed, using defaults: %s", e)

    return default_experts


def _build_catalog_from_manifest(manifest: Dict) -> tuple:
    """Build agent catalog string and valid name set from manifest JSON.

    Returns:
        (catalog_string, valid_names_set)
    """
    from collections import defaultdict

    agents = manifest.get("agents", [])
    if not agents:
        return "", set()

    # Only include expert-tier agents in suggestions
    experts = [a for a in agents if a.get("tier") == "expert"]
    valid_names = {a["name"] for a in agents}  # All tiers for validation

    by_category = defaultdict(list)
    for a in experts:
        by_category[a.get("category", "uncategorized")].append(a)

    parts = []
    for cat in sorted(by_category.keys()):
        cat_agents = by_category[cat]
        parts.append(f"### {cat} ({len(cat_agents)} agents)")
        for a in sorted(cat_agents, key=lambda x: x.get("name", "")):
            desc = a.get("description", "")
            if len(desc) > 120:
                desc = desc[:117] + "..."
            parts.append(f"- {a['name']}: {desc}")
        parts.append("")

    return "\n".join(parts), valid_names


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
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "core": [
            {"name": "orchestrator", "description": "Pipeline orchestration", "model": "opus"},
            {"name": "discovery-facilitator", "description": "Guides discovery process", "model": "sonnet"}
        ],
        "selected_experts": [],
        "note": "Using built-in defaults - external agent repository not available"
    }

    roster = {
        "version": "1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
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

    write_json(agents_output, agents_json)

    write_json(roster_output, roster)

    print("  ✓ Created default agent selection")
    print("  ✓ Created default phase roster")


def _create_uat_agents(agents_output: Path, roster_output: Path, conversation_log: Path) -> None:
    """Create minimal agent files for UAT mode."""
    write_json(agents_output, {
        "expert_agents": ["python-pro", "test-strategist", "backend-architect"],
        "selection_method": "uat_defaults"
    })

    write_json(roster_output, {
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
    })

    conversation_log.write_text("""## UAT Mode

Agent selection skipped in UAT mode.

Selected: python-pro, test-strategist, backend-architect (defaults)
""")




if __name__ == "__main__":
    # CLI execution support
    atomic_root = Path.cwd()
    output_dir = atomic_root.parent / ".outputs" / "1-discovery"
    uat_mode = "--uat" in sys.argv

    sys.exit(0 if execute(atomic_root, output_dir, uat_mode) else 1)
