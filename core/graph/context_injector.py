"""Graph context auto-injection for LLM prompts.

Builds gravity-tiered context from the knowledge graph (agents, traceability,
memory) and manages a ContextVar for automatic injection into every LLM call.

Token budgets by gravity:
- LIGHT:     ~250 tokens (agent names, decision count, 1 memory entry)
- STANDARD:  ~1000 tokens (agent descriptions, decisions+requirements, 3 memory entries)
- INTENSIVE: ~3000 tokens (full catalog subset, ContextCompiler preset, 5 memory entries)
"""

import logging
from contextvars import ContextVar
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Context var for auto-injection into LLM system prompts.
# Set by phase_runner before task execution, read by FeatureAwareLLMInvoker.invoke().
_active_graph_context: ContextVar[Optional[str]] = ContextVar(
    "_active_graph_context", default=None,
)

# Token budgets per gravity tier, split across sections.
_BUDGETS = {
    "light":     {"agents": 100, "trace": 50,  "memory": 100},
    "standard":  {"agents": 300, "trace": 400, "memory": 300},
    "intensive": {"agents": 800, "trace": 1200, "memory": 1000},
}


def set_active_graph_context(ctx: Optional[str]) -> None:
    """Set the active graph context for the current task execution."""
    _active_graph_context.set(ctx)


def get_active_graph_context() -> Optional[str]:
    """Get the active graph context, or None if not set."""
    return _active_graph_context.get()


def build_graph_context(
    graph,
    phase_id: str,
    task_id: str,
    task_name: str,
    gravity,
    roster: Optional[List[Tuple]] = None,
) -> Optional[str]:
    """Build unified graph context for LLM injection, tiered by gravity.

    Args:
        graph: GraphManager instance (or None).
        phase_id: Current phase identifier (e.g. "2-prd").
        task_id: Current task identifier (e.g. "205").
        task_name: Human-readable task name.
        gravity: GravityLevel enum value.
        roster: Agent roster from resolve_agent_roster(), list of
                (AgentEntry, ResolvedModel) tuples. None for infrastructure tasks.

    Returns:
        Formatted context string, or None if no context available.
    """
    if graph is None:
        return None

    gravity_key = gravity.value if hasattr(gravity, "value") else str(gravity)
    budget = _BUDGETS.get(gravity_key, _BUDGETS["standard"])

    sections = []

    agent_section = _format_agent_context(graph, roster, budget["agents"])
    if agent_section:
        sections.append(agent_section)

    trace_section = _format_traceability_context(
        graph, phase_id, task_id, budget["trace"],
    )
    if trace_section:
        sections.append(trace_section)

    memory_section = _format_memory_context(
        graph, phase_id, task_name, budget["memory"],
    )
    if memory_section:
        sections.append(memory_section)

    if not sections:
        return None

    return "\n\n".join(sections)


def _format_agent_context(
    graph, roster: Optional[List[Tuple]], budget_tokens: int,
) -> str:
    """Format assigned agent context from the roster.

    For small budgets (<=100), just agent names.
    For larger budgets, query graph for full descriptions.
    """
    if not roster:
        return ""

    try:
        agent_names = []
        for entry in roster:
            # entry is (AgentEntry, ResolvedModel)
            agent_entry = entry[0] if isinstance(entry, (list, tuple)) else entry
            name = getattr(agent_entry, "name", None) or str(agent_entry)
            if name:
                agent_names.append(name)

        if not agent_names:
            return ""

        if budget_tokens <= 100:
            # LIGHT: names only
            names_str = ", ".join(agent_names[:3])
            return f"[Assigned Experts] {names_str}"

        # STANDARD/INTENSIVE: query graph for descriptions
        lines = ["[Assigned Experts]"]
        budget_chars = budget_tokens * 4
        chars_used = len(lines[0]) + 1

        for name in agent_names:
            try:
                nodes = graph.reader.get_nodes(
                    "Agent", filters={"id": name}, limit=1,
                )
                if nodes:
                    desc = nodes[0].get("description", "")
                    if len(desc) > 120:
                        desc = desc[:117] + "..."
                    line = f"- {name}: {desc}" if desc else f"- {name}"
                else:
                    line = f"- {name}"
            except Exception:
                line = f"- {name}"

            if chars_used + len(line) + 1 > budget_chars:
                break
            lines.append(line)
            chars_used += len(line) + 1

        return "\n".join(lines) if len(lines) > 1 else ""

    except Exception as e:
        logger.debug("Agent context formatting failed: %s", e)
        return ""


def _format_traceability_context(
    graph, phase_id: str, task_id: str, budget_tokens: int,
) -> str:
    """Format traceability context (decisions, requirements) via ContextCompiler.

    LIGHT: accepted decisions only, limit 3.
    STANDARD: decisions + phase requirements.
    INTENSIVE: full task_context() preset from ContextCompiler.
    """
    if budget_tokens <= 0:
        return ""

    try:
        from .context_compiler import ContextCompiler, Traversal

        compiler = ContextCompiler(graph.reader)

        if budget_tokens <= 100:
            # LIGHT: just a few accepted decisions
            traversals = [
                Traversal(
                    label="Decision",
                    heading="[Key Decisions]",
                    filters={"status": "accepted"},
                    limit=3,
                    format_fn=lambda d: f"{d.get('title', '')}",
                ),
            ]
            return compiler.compile(traversals, max_tokens=budget_tokens)

        elif budget_tokens <= 500:
            # STANDARD: decisions (with confidence) + requirements
            traversals = [
                Traversal(
                    label="Decision",
                    heading="[Key Decisions]",
                    filters={"status": "accepted"},
                    limit=5,
                    format_fn=lambda d: (
                        f"{d.get('title', '')}: {d.get('rationale', '')} "
                        f"(confidence: {d.get('confidence', 'N/A')})"
                    ),
                    token_budget=budget_tokens // 2,
                ),
                Traversal(
                    label="Requirement",
                    heading="[Requirements]",
                    limit=8,
                    format_fn=lambda r: (
                        f"[{r.get('type', '')}] {r.get('title', '')}"
                    ),
                    token_budget=budget_tokens // 2,
                ),
            ]
            return compiler.compile(traversals, max_tokens=budget_tokens)

        else:
            # INTENSIVE: full task context preset
            return compiler.task_context(task_id=None, max_tokens=budget_tokens)

    except Exception as e:
        logger.debug("Traceability context formatting failed: %s", e)
        return ""


def _format_memory_context(
    graph, phase_id: str, task_name: str, budget_tokens: int,
) -> str:
    """Format memory recall results for LLM context.

    Queries graph-backed memory recall for relevant prior entries.
    """
    if budget_tokens <= 0:
        return ""

    try:
        # Scale limit by budget
        if budget_tokens <= 100:
            limit = 1
        elif budget_tokens <= 300:
            limit = 3
        else:
            limit = 5

        entries = graph.recall_memory(
            query=task_name, phase=phase_id, limit=limit,
        )

        if not entries:
            return ""

        # Priority-based budget reservation: reserve a portion for P0/P1 entries
        # LIGHT: 25%, STANDARD: 20%, INTENSIVE: 15%
        if budget_tokens <= 100:
            reserved_pct = 0.25
        elif budget_tokens <= 300:
            reserved_pct = 0.20
        else:
            reserved_pct = 0.15
        reserved_chars = int(budget_tokens * 4 * reserved_pct)

        # Separate high-priority and normal entries
        high_priority = [e for e in entries if e.get("priority", "P2") in ("P0", "P1")]
        normal = [e for e in entries if e.get("priority", "P2") not in ("P0", "P1")]

        lines = ["[Prior Context]"]
        budget_chars = budget_tokens * 4
        chars_used = len(lines[0]) + 1

        # Fill reserved budget with high-priority entries first
        for entry in high_priority:
            content = entry.get("content", "")
            if not content:
                continue
            if len(content) > 200:
                content = content[:197] + "..."
            line = f"- {content}"
            if chars_used + len(line) + 1 > budget_chars:
                break
            lines.append(line)
            chars_used += len(line) + 1

        # Fill remaining with normal entries
        for entry in normal:
            content = entry.get("content", "")
            if not content:
                continue
            if len(content) > 200:
                content = content[:197] + "..."
            line = f"- {content}"
            if chars_used + len(line) + 1 > budget_chars:
                break
            lines.append(line)
            chars_used += len(line) + 1

        return "\n".join(lines) if len(lines) > 1 else ""

    except Exception as e:
        logger.debug("Memory context formatting failed: %s", e)
        return ""
