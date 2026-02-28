"""Format skill selections for LLM system prompt injection.

Uses a ContextVar for async-safe, thread-safe auto-injection into every
LLM call without modifying individual task files.

Gravity tiers control verbosity:
- LIGHT:     max 2 skills, name + one-line imperative (<200 tokens)
- STANDARD:  max 8 skills, name + category + description (<600 tokens)
- INTENSIVE: max 15 skills, full detail with risk notes (<1500 tokens)
"""

import logging
from contextvars import ContextVar
from typing import Optional

from core.skills.models import GravityLevel, SkillMetadata, SkillSelection

logger = logging.getLogger(__name__)

# Context var for auto-injection into LLM system prompts.
# Set by phase_runner before task execution, read by FeatureAwareLLMInvoker.invoke().
_active_skill_context: ContextVar[Optional[str]] = ContextVar(
    "_active_skill_context", default=None,
)


def set_active_skill_context(ctx: Optional[str]) -> None:
    """Set the active skill context for the current task execution."""
    _active_skill_context.set(ctx)


def get_active_skill_context() -> Optional[str]:
    """Get the active skill context, or None if not set."""
    return _active_skill_context.get()


def format_skill_context(
    selection: SkillSelection,
    gravity: GravityLevel,
) -> Optional[str]:
    """Format a skill selection for LLM consumption, tiered by gravity.

    Args:
        selection: The skill selection result from SkillSelector.
        gravity: The gravity level determining verbosity.

    Returns:
        Formatted string for prepending to system_prompt, or None if no skills.
    """
    if not selection or not selection.skills:
        return None

    if gravity == GravityLevel.LIGHT:
        return _format_light(selection.skills[:2])
    elif gravity == GravityLevel.INTENSIVE:
        return _format_intensive(selection)
    else:
        return _format_standard(selection.skills[:8])


def _format_light(skills: list[SkillMetadata]) -> str:
    """LIGHT: name + one-line imperative. Under 200 tokens."""
    lines = ["[Active Skills]"]
    for skill in skills:
        # Use first sentence of description as imperative
        imperative = _first_sentence(skill.description)
        lines.append(f"- {skill.name}: {imperative}")
    return "\n".join(lines)


def _format_standard(skills: list[SkillMetadata]) -> str:
    """STANDARD: name, category, description. Under 600 tokens."""
    lines = ["[Active Skills]"]
    for skill in skills:
        cat = f" [{skill.category}]" if skill.category else ""
        lines.append(f"- {skill.name}{cat}: {skill.description}")
    return "\n".join(lines)


def _format_intensive(selection: SkillSelection) -> str:
    """INTENSIVE: full detail with risk notes, workflow header. Under 1500 tokens."""
    lines = ["[Active Skills]"]

    if selection.workflow:
        lines.append(f"Workflow: {selection.workflow}")
        lines.append("")

    for skill in selection.skills[:15]:
        cat = f" [{skill.category}]" if skill.category else ""
        lines.append(f"- {skill.name}{cat}")
        lines.append(f"  {skill.description}")
        if skill.risk_level and skill.risk_level.value not in ("None", "Low"):
            risk_note = f"  Risk: {skill.risk_level.value}"
            if skill.risk_notes:
                risk_note += f" - {skill.risk_notes}"
            lines.append(risk_note)
    return "\n".join(lines)


def _first_sentence(text: str) -> str:
    """Extract the first sentence from a description."""
    if not text:
        return ""
    # Split on period followed by space or end of string
    idx = text.find(". ")
    if idx > 0:
        return text[:idx + 1]
    return text.rstrip(".")  + "." if text and not text.endswith(".") else text
