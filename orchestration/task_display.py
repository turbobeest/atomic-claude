"""
Per-Task Agent Model Roster Display

Shows users which agents will run for each task and what models they'll use.
Offers interactive override of model assignments before task execution.

This replaces the upfront LLM Configuration Mode from task_001 with a
contextual display right before each task runs.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.llm.resolver import ResolvedModel, get_resolver, resolve_model
from core.utils.cli_ui import (
    print_bold, print_cyan, print_dim, print_green,
    print_yellow, print_red, prompt_user, clear_input_buffer,
)


# ---------------------------------------------------------------------------
# Agent entry type
# ---------------------------------------------------------------------------

@dataclass
class AgentEntry:
    """Normalized agent info extracted from phase-specific JSON files."""
    name: str
    label: Optional[str] = None       # Role label (e.g. "RED", "deep_code")
    manifest_model: Optional[str] = None  # Model preference from agent file


# ---------------------------------------------------------------------------
# Agent file discovery
# ---------------------------------------------------------------------------

AGENT_FILE_CANDIDATES = [
    "selected-agents.json",
    "review-agents.json",
    "integration-agents.json",
    "deployment-agents.json",
    "release-agents.json",
    "agent-roster.json",
]

# All known keys that contain agent lists across phase formats
_AGENT_LIST_KEYS = [
    "selected", "agents", "expert_agents", "selected_experts",
    "decomposition_agents", "validation_agents", "additional_agents",
    "additional", "core", "specialists",
]

# Keys that contain nested dicts with agent info (Phase 5/6 style)
_AGENT_DICT_KEYS = [
    "tdd_agents", "review_agents",
]


def discover_agents(output_dir: Path) -> List[AgentEntry]:
    """Find and normalize agents from any phase's agent selection output.

    Tries each candidate file, then walks the JSON to extract agent names
    from all known key patterns. Handles all phase-specific structures.
    """
    agents: List[AgentEntry] = []
    seen_names: set = set()

    for candidate in AGENT_FILE_CANDIDATES:
        agent_file = output_dir / candidate
        if not agent_file.exists():
            continue

        try:
            data = json.loads(agent_file.read_text())
        except (OSError, json.JSONDecodeError):
            continue

        # Extract from flat list keys
        for key in _AGENT_LIST_KEYS:
            items = data.get(key)
            if not items:
                continue
            if isinstance(items, list):
                for item in items:
                    entry = _parse_agent_item(item)
                    if entry and entry.name not in seen_names:
                        agents.append(entry)
                        seen_names.add(entry.name)

        # Extract from nested dict keys (Phase 5/6 style)
        for key in _AGENT_DICT_KEYS:
            items = data.get(key)
            if not items or not isinstance(items, dict):
                continue
            for label, value in items.items():
                if isinstance(value, dict):
                    name = value.get("name", label)
                    model = value.get("model")
                    if name not in seen_names:
                        agents.append(AgentEntry(name=name, label=label, manifest_model=model))
                        seen_names.add(name)
                elif isinstance(value, str):
                    entry = _parse_agent_item(value, label=label)
                    if entry and entry.name not in seen_names:
                        agents.append(entry)
                        seen_names.add(entry.name)

        # If we found agents in this file, stop looking
        if agents:
            break

    return agents


def _parse_agent_item(item: Any, label: str = None) -> Optional[AgentEntry]:
    """Parse a single agent item from JSON (string, dict, etc.)."""
    if isinstance(item, str):
        # Handle "agent-name:model" format
        if ":" in item:
            parts = item.split(":", 1)
            return AgentEntry(name=parts[0], label=label, manifest_model=parts[1])
        return AgentEntry(name=item, label=label)
    elif isinstance(item, dict):
        name = item.get("name") or item.get("agent_name")
        if name:
            return AgentEntry(
                name=name,
                label=item.get("label") or item.get("role") or label,
                manifest_model=item.get("model"),
            )
    return None


# ---------------------------------------------------------------------------
# Roster resolution
# ---------------------------------------------------------------------------

def resolve_agent_roster(
    phase_id: str,
    task_id: str,
    output_dir: Path,
) -> List[Tuple[AgentEntry, ResolvedModel]]:
    """Resolve model for each discovered agent.

    Uses resolver with agent_name to get per-agent model resolution.
    Falls back to phase-level resolution if no agents found.
    """
    agents = discover_agents(output_dir)
    if not agents:
        # No agent file yet (pre-selection task, phase 0, etc.)
        resolved = resolve_model(phase_id, task_id)
        return [(AgentEntry(name="\u2014"), resolved)]

    roster = []
    for agent in agents:
        resolved = resolve_model(phase_id, task_id, agent_name=agent.name)
        roster.append((agent, resolved))
    return roster


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

PROVIDER_LABELS = {
    "claude-code": "Subscription",
    "anthropic": "Anthropic API",
    "aws-bedrock": "AWS Bedrock",
    "ollama": "Ollama",
    None: "Detecting...",
}


def _fmt_context(ctx: int) -> str:
    """Format context window: 1M, 200K, 128K."""
    if ctx >= 1_000_000:
        return f"{ctx // 1_000_000}M"
    return f"{ctx // 1_000}K"


EFFORT_LABELS = {
    "high": "Max",
    "medium": "Med",
    "low": "Low",
}


def _fmt_effort(effort: Optional[str], provider: Optional[str]) -> str:
    """Format effort level, dash for providers that don't support it."""
    if provider == "ollama":
        return "\u2014"
    if not effort:
        return "\u2014"
    return EFFORT_LABELS.get(effort, effort.capitalize())


def display_task_roster(
    task_id: str,
    task_name: str,
    roster: List[Tuple[AgentEntry, ResolvedModel]],
    uat_mode: bool = False,
) -> List[Tuple[AgentEntry, ResolvedModel]]:
    """Display agent model table and offer override prompt.

    Returns the (possibly modified) roster.
    In UAT mode, skips the interactive prompt.
    """
    print()

    if len(roster) == 1 and roster[0][0].name == "\u2014":
        # Single-row display for tasks without agents
        _, rm = roster[0]
        prov_label = PROVIDER_LABELS.get(rm.provider, rm.provider or "Unknown")
        ctx = _fmt_context(rm.context_window)
        effort = _fmt_effort(rm.effort_level, rm.provider)
        print(f"  {print_bold(f'Task {task_id}: {task_name}')}")
        print(f"  Provider: {prov_label}  \u2502  Model: {rm.model_id}  \u2502  Context: {ctx}  \u2502  Effort: {effort}")
    else:
        # Multi-agent table
        _print_roster_table(task_id, task_name, roster)

    print()

    if uat_mode:
        return roster

    # Interactive prompt
    if len(roster) > 1 or roster[0][0].name != "\u2014":
        clear_input_buffer()
        choice = prompt_user("  Enter to continue, [m] to change model assignments: ").strip().lower()
        if choice == "m":
            roster = _handle_override(roster)
    else:
        clear_input_buffer()
        prompt_user("  Enter to continue: ")

    return roster


def _print_roster_table(
    task_id: str,
    task_name: str,
    roster: List[Tuple[AgentEntry, ResolvedModel]],
) -> None:
    """Render the agent roster as a box-drawing table."""
    print(f"  {print_bold(f'Task {task_id}: {task_name}')}")
    print()

    # Calculate column widths
    agent_col = max(len(_agent_display(e)) for e, _ in roster)
    agent_col = max(agent_col, 5)  # minimum "Agent"
    prov_col = max(len(PROVIDER_LABELS.get(rm.provider, rm.provider or "")) for _, rm in roster)
    prov_col = max(prov_col, 8)  # minimum "Provider"
    model_col = max(len(rm.model_id) for _, rm in roster)
    model_col = max(model_col, 5)  # minimum "Model"
    ctx_col = 7   # "Context"
    eff_col = 6   # "Effort"

    # Header
    hdr = (
        f"  \u250c\u2500{'Agent':\u2500<{agent_col}}\u2500\u252c\u2500{'Provider':\u2500<{prov_col}}\u2500"
        f"\u252c\u2500{'Model':\u2500<{model_col}}\u2500\u252c\u2500{'Context':\u2500<{ctx_col}}\u2500"
        f"\u252c\u2500{'Effort':\u2500<{eff_col}}\u2500\u2510"
    )
    # The top border
    top = (
        f"  \u250c{'─' * (agent_col + 2)}\u252c{'─' * (prov_col + 2)}"
        f"\u252c{'─' * (model_col + 2)}\u252c{'─' * (ctx_col + 2)}"
        f"\u252c{'─' * (eff_col + 2)}\u2510"
    )
    print(print_dim(top))

    # Column headers
    hdr_line = (
        f"  \u2502 {'Agent':<{agent_col}} \u2502 {'Provider':<{prov_col}} "
        f"\u2502 {'Model':<{model_col}} \u2502 {'Context':<{ctx_col}} "
        f"\u2502 {'Effort':<{eff_col}} \u2502"
    )
    print(print_bold(hdr_line))

    # Separator
    sep = (
        f"  \u251c{'─' * (agent_col + 2)}\u253c{'─' * (prov_col + 2)}"
        f"\u253c{'─' * (model_col + 2)}\u253c{'─' * (ctx_col + 2)}"
        f"\u253c{'─' * (eff_col + 2)}\u2524"
    )
    print(print_dim(sep))

    # Data rows
    for entry, rm in roster:
        agent_display = _agent_display(entry)
        prov_label = PROVIDER_LABELS.get(rm.provider, rm.provider or "")
        ctx = _fmt_context(rm.context_window)
        effort = _fmt_effort(rm.effort_level, rm.provider)
        row = (
            f"  \u2502 {agent_display:<{agent_col}} \u2502 {prov_label:<{prov_col}} "
            f"\u2502 {rm.model_id:<{model_col}} \u2502 {ctx:<{ctx_col}} "
            f"\u2502 {effort:<{eff_col}} \u2502"
        )
        print(row)

    # Bottom border
    bot = (
        f"  \u2514{'─' * (agent_col + 2)}\u2534{'─' * (prov_col + 2)}"
        f"\u2534{'─' * (model_col + 2)}\u2534{'─' * (ctx_col + 2)}"
        f"\u2534{'─' * (eff_col + 2)}\u2518"
    )
    print(print_dim(bot))


def _agent_display(entry: AgentEntry) -> str:
    """Format agent name with optional label."""
    if entry.label:
        return f"{entry.name} ({entry.label})"
    return entry.name


# ---------------------------------------------------------------------------
# Override prompt
# ---------------------------------------------------------------------------

def _handle_override(
    roster: List[Tuple[AgentEntry, ResolvedModel]],
) -> List[Tuple[AgentEntry, ResolvedModel]]:
    """Interactive override for agent model assignments.

    1. Show numbered agent list
    2. User picks agent (or 'all' for bulk)
    3. Pick new tier
    4. Pick scope (all tasks or this task only)
    5. Re-resolve and redisplay
    """
    resolver = get_resolver()

    # Load available providers from project config
    try:
        config_path = resolver._atomic_root / ".outputs" / "0-setup" / "project-config.json"
        config_data = json.loads(config_path.read_text())
        chain = config_data.get("extracted", {}).get("providers", {}).get("chain_priority", [])
    except (OSError, json.JSONDecodeError):
        chain = []

    while True:
        print()
        print(print_bold("  SELECT AGENT TO OVERRIDE"))
        print()
        for i, (entry, rm) in enumerate(roster):
            display = _agent_display(entry)
            print(f"    {i + 1}. {display:<30} {print_dim(rm.model_id)}")
        print(f"    a. All agents")
        print()

        clear_input_buffer()
        raw = prompt_user("  Agent [cancel]: ").strip().lower()
        if not raw or raw in ("c", "cancel"):
            break

        # Parse selection
        targets: List[int] = []
        if raw == "a" or raw == "all":
            targets = list(range(len(roster)))
        else:
            try:
                idx = int(raw) - 1
                if 0 <= idx < len(roster):
                    targets = [idx]
            except ValueError:
                print(print_red("    Invalid selection"))
                continue

        if not targets:
            print(print_red("    Invalid selection"))
            continue

        # Pick new tier
        print()
        print(print_bold("  SELECT MODEL TIER"))
        print()
        tiers = [
            ("opus",   "Most capable, 200K context"),
            ("sonnet", "Balanced, 200K context"),
            ("haiku",  "Fast, 200K context"),
        ]
        for i, (tier, desc) in enumerate(tiers):
            print(f"    {i + 1}. {tier:<10} {print_dim(desc)}")

        # Add Ollama models if available
        ollama_models = _get_ollama_models(resolver)
        if ollama_models:
            print()
            print(f"    {print_dim('Ollama models:')}")
            for i, model_name in enumerate(ollama_models):
                print(f"    {len(tiers) + i + 1}. {model_name}")

        print()
        clear_input_buffer()
        tier_raw = prompt_user("  Tier [cancel]: ").strip()
        if not tier_raw or tier_raw.lower() in ("c", "cancel"):
            continue

        new_tier = None
        new_provider = None
        new_model_id = None

        try:
            tier_idx = int(tier_raw) - 1
            if 0 <= tier_idx < len(tiers):
                new_tier = tiers[tier_idx][0]
            elif ollama_models and tier_idx < len(tiers) + len(ollama_models):
                ollama_idx = tier_idx - len(tiers)
                new_provider = "ollama"
                new_model_id = ollama_models[ollama_idx]
                new_tier = "sonnet"  # placeholder tier for Ollama
        except ValueError:
            # Try as tier name
            if tier_raw.lower() in ("opus", "sonnet", "haiku"):
                new_tier = tier_raw.lower()
            else:
                print(print_red("    Invalid selection"))
                continue

        if new_tier is None and new_model_id is None:
            print(print_red("    Invalid selection"))
            continue

        # Pick scope
        print()
        print(print_bold("  APPLY TO"))
        print(f"    1. All tasks using this agent {print_dim('(recommended)')}")
        print(f"    2. This task only")
        print()
        clear_input_buffer()
        scope_raw = prompt_user("  Choice [1]: ").strip() or "1"
        task_only = scope_raw == "2"

        # Apply overrides
        for idx in targets:
            entry, _ = roster[idx]
            if entry.name == "\u2014":
                continue
            resolver.set_override(
                agent_name=entry.name,
                tier=new_tier,
                provider=new_provider,
                model_id=new_model_id,
                task_only=task_only,
            )

        # Re-resolve roster
        new_roster = []
        for entry, old_rm in roster:
            if entry.name == "\u2014":
                new_roster.append((entry, old_rm))
            else:
                rm = resolve_model(old_rm.phase_id, old_rm.task_id, agent_name=entry.name)
                new_roster.append((entry, rm))
        roster = new_roster

        # Redisplay
        print()
        print(print_green("  Override applied"))
        _print_roster_table("", "Updated", roster)
        print()

        clear_input_buffer()
        choice = prompt_user("  Enter to continue, [m] for more changes: ").strip().lower()
        if choice != "m":
            break

    return roster


def _get_ollama_models(resolver) -> List[str]:
    """Get available Ollama model names from project config."""
    try:
        config = resolver._config
        ollama_cfg = config.get("providers", {}).get("ollama", {})
        if not ollama_cfg.get("enabled"):
            return []
        models = ollama_cfg.get("models", {})
        return list(models.keys())
    except Exception:
        return []
