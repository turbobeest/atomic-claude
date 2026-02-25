"""
ATOMIC CLAUDE - Context Compiler

Generic graph context assembler for LLM prompts.
Builds context strings from configurable graph traversals with token budgets.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


def _estimate_tokens(text: str) -> int:
    """Estimate token count using chars/4 heuristic."""
    return len(text) // 4


@dataclass
class Traversal:
    """A single graph traversal step that contributes context.

    Attributes:
        label: Node label to query (e.g., "Finding", "Task")
        heading: Section heading in output (e.g., "## Relevant Findings")
        filters: Property filters for get_nodes (exact match)
        rel_from: If set, traverse relationships FROM this (label, id) pair
        rel_type: Relationship type filter for traversal
        direction: Traversal direction ("out", "in", "both")
        order_by: Property to sort results by
        limit: Max nodes to retrieve
        format_fn: Custom formatter (node_dict -> str). Default: title + content
        token_budget: Max tokens for this traversal's output (0 = unlimited)
        include_empty: If False (default), skip section when no results
    """
    label: str
    heading: str = ""
    filters: Optional[Dict[str, Any]] = None
    rel_from: Optional[tuple] = None  # (label, node_id)
    rel_type: Optional[str] = None
    direction: str = "out"
    order_by: Optional[str] = None
    limit: Optional[int] = None
    format_fn: Optional[Callable] = None
    token_budget: int = 0
    include_empty: bool = False


def _default_format(node: Dict[str, Any]) -> str:
    """Default node formatter: [category/type] title: content."""
    parts = []
    cat = node.get("category") or node.get("type") or ""
    if cat:
        parts.append(f"[{cat}]")
    title = node.get("title") or node.get("name") or node.get("id", "")
    parts.append(str(title))
    content = node.get("content") or node.get("description") or ""
    if content:
        parts.append(f": {content}")
    return " ".join(parts)


class ContextCompiler:
    """Assembles graph context from configurable traversals.

    Usage:
        compiler = ContextCompiler(reader)
        context = compiler.compile([
            Traversal(label="Finding", heading="## Findings",
                      filters={"category": "technical"}, limit=20),
            Traversal(label="Decision", heading="## Decisions",
                      filters={"status": "accepted"}),
        ], max_tokens=4000)

    Or use presets:
        context = compiler.prd_context("features", max_tokens=8000)
    """

    def __init__(self, reader):
        """
        Args:
            reader: GraphReader instance
        """
        self.reader = reader

    def compile(self, traversals: List[Traversal],
                max_tokens: int = 8000) -> str:
        """Execute traversals and assemble context within token budget.

        Args:
            traversals: Ordered list of Traversal steps
            max_tokens: Total token budget for assembled output

        Returns:
            Assembled context string
        """
        sections = []
        tokens_used = 0

        for t in traversals:
            remaining = max_tokens - tokens_used
            if remaining <= 0:
                break

            section_budget = t.token_budget if t.token_budget > 0 else remaining

            # Query nodes
            nodes = self._execute_traversal(t)
            if not nodes and not t.include_empty:
                continue

            # Format section
            section_text = self._format_section(t, nodes, min(section_budget, remaining))
            if not section_text:
                continue

            section_tokens = _estimate_tokens(section_text)
            if tokens_used + section_tokens > max_tokens:
                # Truncate this section to fit
                available_chars = (max_tokens - tokens_used) * 4
                if available_chars > 100:  # Don't add tiny fragments
                    section_text = section_text[:available_chars] + "\n... [truncated]"
                    sections.append(section_text)
                break

            sections.append(section_text)
            tokens_used += section_tokens

        return "\n".join(sections)

    def _execute_traversal(self, t: Traversal) -> List[Dict[str, Any]]:
        """Execute a single traversal and return matching nodes."""
        try:
            if t.rel_from:
                from_label, from_id = t.rel_from
                return self.reader.get_neighbors(
                    from_label, from_id,
                    rel_type=t.rel_type,
                    direction=t.direction,
                )
            else:
                return self.reader.get_nodes(
                    t.label,
                    filters=t.filters,
                    order_by=t.order_by,
                    limit=t.limit,
                )
        except Exception as e:
            logger.debug("Traversal failed for %s: %s", t.label, e)
            return []

    def _format_section(self, t: Traversal, nodes: List[Dict],
                        budget_tokens: int) -> str:
        """Format a section's nodes within its token budget."""
        formatter = t.format_fn or _default_format
        lines = []

        if t.heading:
            lines.append(t.heading)
            lines.append("")

        budget_chars = budget_tokens * 4
        chars_used = sum(len(line) + 1 for line in lines)

        for node in nodes:
            line = f"- {formatter(node)}"
            if chars_used + len(line) + 1 > budget_chars:
                break
            lines.append(line)
            chars_used += len(line) + 1

        if len(lines) <= (2 if t.heading else 0):
            # No content lines added
            return "" if not t.include_empty else t.heading + "\n(none)\n"

        lines.append("")  # trailing newline
        return "\n".join(lines)

    # ====================================================================
    # PRESETS
    # ====================================================================

    def prd_context(self, section: str, max_tokens: int = 8000) -> str:
        """Assemble context for a PRD section.

        Equivalent to reader.query_prd_context() but configurable.
        """
        section_category_map = {
            "vision": ["vision", "impact"],
            "audience": ["audience"],
            "features": ["technical", "non_negotiable"],
            "nfr": ["constraint", "non_negotiable"],
            "architecture": ["technical"],
            "constraints": ["constraint"],
            "open_questions": ["open_question"],
        }

        traversals = []
        categories = section_category_map.get(section.lower(), [])
        for cat in categories:
            traversals.append(Traversal(
                label="Finding",
                heading=f"## Findings ({cat})",
                filters={"category": cat},
                limit=30,
            ))

        if not traversals:
            traversals.append(Traversal(
                label="Finding",
                heading="## Findings",
                limit=30,
            ))

        traversals.extend([
            Traversal(
                label="Decision",
                heading="## Decisions",
                filters={"status": "accepted"},
                format_fn=lambda d: f"[{d.get('status', 'proposed')}] "
                                    f"{d.get('title', '')}: {d.get('rationale', '')}",
            ),
            Traversal(
                label="Requirement",
                heading="## Requirements",
                filters={"section": section},
                limit=50,
            ),
            Traversal(
                label="Source",
                heading="## Sources",
                limit=20,
                format_fn=lambda s: f"[{s.get('type', '')}] {s.get('title', '')}",
            ),
        ])

        return self.compile(traversals, max_tokens=max_tokens)

    def task_context(self, task_id: Any = None, max_tokens: int = 8000) -> str:
        """Assemble context for a specific task or all tasks."""
        traversals = []

        if task_id is not None:
            # Specific task details
            traversals.extend([
                Traversal(
                    label="Task",
                    heading=f"## Task {task_id}",
                    filters={"id": task_id},
                    limit=1,
                    format_fn=lambda t: f"{t.get('title', '')}\n  {t.get('description', '')}",
                ),
                Traversal(
                    label="Requirement",
                    heading="## Requirements",
                    rel_from=("Task", task_id),
                    rel_type="IMPLEMENTS",
                    direction="out",
                    format_fn=lambda r: f"[{r.get('type', '')}] {r.get('title', '')}: "
                                        f"{r.get('content', '')}",
                ),
                Traversal(
                    label="Finding",
                    heading="## Research",
                    rel_from=("Task", task_id),
                    rel_type="INFORMED_BY",
                    direction="out",
                ),
                Traversal(
                    label="Task",
                    heading="## Dependencies",
                    rel_from=("Task", task_id),
                    rel_type="TASK_DEPENDS_ON",
                    direction="out",
                    format_fn=lambda t: f"Task {t.get('id')}: {t.get('title', '')} "
                                        f"[{t.get('status', 'pending')}]",
                ),
            ])
        else:
            traversals.extend([
                Traversal(
                    label="Task",
                    heading="## Tasks",
                    order_by="id",
                    format_fn=lambda t: f"Task {t.get('id')}: {t.get('title', '')} "
                                        f"[{t.get('status', 'pending')}]",
                ),
                Traversal(
                    label="Decision",
                    heading="## Decisions",
                    filters={"status": "accepted"},
                    format_fn=lambda d: f"{d.get('title', '')}: {d.get('rationale', '')}",
                ),
            ])

        return self.compile(traversals, max_tokens=max_tokens)

    def review_context(self, severity: str = None,
                       review_dimension: str = None,
                       max_tokens: int = 4000) -> str:
        """Assemble context from review findings.

        Args:
            severity: Filter by severity (optional)
            review_dimension: Filter by dimension (optional)
            max_tokens: Token budget
        """
        filters = {"status": "open"}
        if severity:
            filters["severity"] = severity
        if review_dimension:
            filters["review_dimension"] = review_dimension

        heading = "## Review Findings"
        if severity:
            heading += f" ({severity})"
        if review_dimension:
            heading += f" [{review_dimension}]"

        traversals = [
            Traversal(
                label="ReviewFinding",
                heading=heading,
                filters=filters,
                format_fn=lambda f: (
                    f"[{f.get('severity', '')}] {f.get('description', '')}"
                    + (f" ({f.get('file', '')}:{f.get('line', '')})"
                       if f.get('file') else "")
                    + (f"\n  Fix: {f.get('recommendation', '')}"
                       if f.get('recommendation') else "")
                ),
            ),
        ]

        return self.compile(traversals, max_tokens=max_tokens)
