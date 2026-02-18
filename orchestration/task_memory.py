"""
Task Memory - Accumulates substantive memory entries during task execution.

Instead of generic "Task X completed" messages, tasks use TaskMemory to
record decisions, findings, configuration changes, and conversation summaries.
The orchestrator writes the accumulated content to memory after task completion.

Usage in tasks:
    def execute(atomic_root, output_dir, uat_mode=False, mem=None):
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

from typing import List, Tuple, Dict, Any, Optional


class TaskMemory:
    """Accumulates substantive memory during task execution."""

    CATEGORIES = ("decision", "finding", "conversation", "configuration", "warning")

    def __init__(self, phase_id: str, task_id: str, task_name: str, flush_fn=None):
        self._entries: List[Tuple[str, str]] = []
        self.phase_id = phase_id
        self.task_id = task_id
        self.task_name = task_name
        self._flush_fn = flush_fn
        self._flushed_count: int = 0

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

        grouped: Dict[str, List[str]] = {}
        for category, text in new_entries:
            grouped.setdefault(category, []).append(text)

        labels_map = {
            "finding": "Findings", "decision": "Decisions",
            "configuration": "Configuration",
            "conversation": "Conversation", "warning": "Warnings",
        }

        for category in self.CATEGORIES:
            entries = grouped.get(category, [])
            if not entries:
                continue
            lines.append("")
            lines.append(f"{labels_map[category]}:")
            for entry in entries:
                lines.append(f"- {entry}")

        try:
            self._flush_fn(
                content="\n".join(lines),
                tags=["mid-task", self.phase_id, f"task-{self.task_id}"],
                entry_type="task_progress",
            )
        except Exception:
            pass  # Checkpoint failure is non-blocking

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

        # Group entries by category, preserving order within each
        grouped: Dict[str, List[str]] = {}
        for category, text in self._entries:
            grouped.setdefault(category, []).append(text)

        # Category display names (plural)
        labels = {
            "finding": "Findings",
            "decision": "Decisions",
            "configuration": "Configuration",
            "conversation": "Conversation",
            "warning": "Warnings",
        }

        # Emit in a stable order
        for category in self.CATEGORIES:
            entries = grouped.get(category, [])
            if not entries:
                continue
            lines.append("")
            lines.append(f"{labels[category]}:")
            for entry in entries:
                lines.append(f"- {entry}")

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

        return {
            "task_memory": grouped,
            "phase_id": self.phase_id,
            "task_id": self.task_id,
        }
