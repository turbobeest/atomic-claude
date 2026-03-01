"""
Task Memory - Accumulates substantive memory entries during task execution.

Instead of generic "Task X completed" messages, tasks use TaskMemory to
record decisions, findings, configuration changes, and conversation summaries.
The orchestrator writes the accumulated content to memory after task completion.

Usage in tasks:
    def execute(atomic_root, output_dir, mem=None):
        # ... task logic ...
        if mem:
            mem.finding("Detected 3 providers")
            mem.decision("Primary provider: claude-code")
        return True

Usage in orchestrators:
    mem = TaskMemory(phase_id, task_id, task_name)
    success = task_func(mem)
    content = mem.build_content() if mem.has_entries() else fallback
    memory_save(phase=phase_id, ..., content=content, metadata=mem.build_metadata())
"""

import logging
from typing import List, Tuple, Dict, Any, Optional

logger = logging.getLogger(__name__)


class TaskMemory:
    """Accumulates substantive memory during task execution."""

    CATEGORIES = ("decision", "finding", "conversation", "configuration", "warning")

    _LABELS_MAP = {
        "finding": "Findings", "decision": "Decisions",
        "configuration": "Configuration",
        "conversation": "Conversation", "warning": "Warnings",
    }

    def __init__(self, phase_id: str, task_id: str, task_name: str, flush_fn=None):
        self._entries: List[Tuple[str, str]] = []
        self.phase_id = phase_id
        self.task_id = task_id
        self.task_name = task_name
        self._flush_fn = flush_fn
        self._flushed_count: int = 0
        # Skill context (set by phase_runner after skill selection)
        self._skill_context: Optional[str] = None
        self._skill_selection = None
        self._gravity: Optional[str] = None
        # Decision trail and graph (set by phase_runner)
        self._trail = None
        self._graph = None

    @staticmethod
    def _format_entries(entries: List[Tuple[str, str]], labels_map: Dict[str, str],
                        categories: tuple) -> List[str]:
        """Format a list of (category, text) entries into labelled sections.

        Args:
            entries: List of (category, text) tuples to format
            labels_map: Mapping from category key to display label
            categories: Ordered tuple of category keys

        Returns:
            List of formatted lines (no leading header — caller adds that)
        """
        grouped: Dict[str, List[str]] = {}
        for category, text in entries:
            grouped.setdefault(category, []).append(text)

        lines: List[str] = []
        for category in categories:
            cat_entries = grouped.get(category, [])
            if not cat_entries:
                continue
            lines.append("")
            lines.append(f"{labels_map[category]}:")
            for entry in cat_entries:
                lines.append(f"- {entry}")
        return lines

    def decision(self, text: str) -> None:
        """Record a user or system choice."""
        self._entries.append(("decision", text))

    def finding(self, text: str) -> None:
        """Record something detected or discovered."""
        self._entries.append(("finding", text))

    def conversation(self, text: str) -> None:
        """Record a summary of an interactive exchange."""
        self._entries.append(("conversation", text))

    def configuration(self, text: str) -> None:
        """Record a config value set or changed."""
        self._entries.append(("configuration", text))

    def warning(self, text: str) -> None:
        """Record an issue or concern."""
        self._entries.append(("warning", text))

    def set_skill_context(self, context: str, skill_selection, gravity: str) -> None:
        """Attach skill context from phase_runner after skill selection.

        Args:
            context: Formatted skill text for LLM prompts.
            skill_selection: Raw SkillSelection object.
            gravity: Gravity level string (e.g. "light", "standard", "intensive").
        """
        self._skill_context = context
        self._skill_selection = skill_selection
        self._gravity = gravity

    def set_graph(self, graph) -> None:
        """Attach graph manager for decision trail persistence.

        Args:
            graph: GraphManager instance.
        """
        self._graph = graph

    @property
    def trail(self):
        """Lazy DecisionTrail for recording decisions with confidence.

        Returns:
            DecisionTrail instance (created on first access).
        """
        if self._trail is None:
            try:
                from core.graph.decision_trail import DecisionTrail
            except ImportError:
                logger.debug("DecisionTrail unavailable (core.graph.decision_trail not installed)")
                return None
            self._trail = DecisionTrail(self.phase_id, self.task_id, self._graph)
        return self._trail

    def retry_attempt(self, attempt: int, model_tier: str, error: Optional[str] = None) -> None:
        """Record a retry attempt in task memory.

        Args:
            attempt: Attempt number (0-indexed).
            model_tier: Model tier used for this attempt.
            error: Error from previous attempt, if any.
        """
        if error:
            self._entries.append((
                "warning",
                f"Retry attempt {attempt} (model: {model_tier}): previous error: {error}",
            ))
        else:
            self._entries.append((
                "finding",
                f"Retry attempt {attempt} (model: {model_tier})",
            ))

    @property
    def skill_context(self) -> Optional[str]:
        """Formatted skill context string, or None if not set."""
        return self._skill_context

    @property
    def skill_selection(self):
        """Raw SkillSelection object, or None if not set."""
        return self._skill_selection

    @property
    def gravity_level(self) -> Optional[str]:
        """Gravity level string, or None if not set."""
        return self._gravity

    def checkpoint(self, label: str = "") -> None:
        """Flush entries accumulated since last checkpoint to persistent memory.

        Writes a TASK_PROGRESS memory entry containing only the entries added
        since the previous checkpoint (or since construction). Does nothing if
        no flush_fn was provided or no new entries exist.
        """
        if not self._flush_fn:
            return
        new_entries = self._entries[self._flushed_count:]
        if not new_entries:
            return

        header = (f"Task {self.task_id} ({self.task_name}) — {label}"
                  if label else f"Task {self.task_id} ({self.task_name}) progress")
        lines = [header]
        lines.extend(self._format_entries(new_entries, self._LABELS_MAP, self.CATEGORIES))

        try:
            self._flush_fn(
                content="\n".join(lines),
                tags=["mid-task", self.phase_id, f"task-{self.task_id}"],
                entry_type="task_progress",
            )
        except Exception as e:
            logger.debug("Mid-task memory checkpoint failed (non-blocking): %s", e)

        self._flushed_count = len(self._entries)

    def has_entries(self) -> bool:
        """Check if any entries have been recorded."""
        return len(self._entries) > 0

    def build_content(self) -> str:
        """
        Build the full memory content string.

        Returns formatted content with task header and categorized entries.
        """
        lines = [f"Task {self.task_id} ({self.task_name}) completed."]
        lines.extend(self._format_entries(self._entries, self._LABELS_MAP, self.CATEGORIES))
        return "\n".join(lines)

    def build_metadata(self) -> Dict[str, Any]:
        """
        Build structured metadata dict for the memory entry's metadata field.

        Returns dict with entries grouped by category.
        """
        if not self._entries:
            return {}

        grouped: Dict[str, List[str]] = {}
        for category, text in self._entries:
            grouped.setdefault(category, []).append(text)

        meta = {
            "task_memory": grouped,
            "phase_id": self.phase_id,
            "task_id": self.task_id,
        }
        if self._skill_selection and self._skill_selection.skills:
            meta["skills_used"] = [s.id for s in self._skill_selection.skills]
        if self._gravity:
            meta["gravity"] = self._gravity
        return meta
