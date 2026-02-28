"""Decision Trail — structured decision tracking with graph persistence.

Records decisions made during task execution with confidence scores and
rejected alternatives. Writes Decision nodes to the knowledge graph and
links them to the current task via INFORMED_BY relationships.

Graceful degradation: works without a graph (stores in-memory only).
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TrailEntry:
    """A single recorded decision."""

    id: str
    title: str
    rationale: str
    confidence: float  # 0.0–1.0
    alternatives: List[Dict[str, str]]  # [{"title": ..., "reason_rejected": ...}]
    task_id: str
    phase_id: str
    status: str = "accepted"


class DecisionTrail:
    """Accumulates decisions during a task and optionally persists to graph."""

    def __init__(self, phase_id: str, task_id: str, graph=None):
        self._phase_id = phase_id
        self._task_id = task_id
        self._graph = graph
        self._entries: List[TrailEntry] = []

    def record(
        self,
        title: str,
        rationale: str,
        confidence: float = 0.7,
        alternatives: Optional[List[Dict[str, str]]] = None,
        status: str = "accepted",
    ) -> str:
        """Record a decision and persist to graph if available.

        Args:
            title: Short decision title.
            rationale: Why this was chosen.
            confidence: Confidence in range [0.0, 1.0] (clamped).
            alternatives: List of rejected alternatives with reasons.
            status: Decision status (proposed/accepted/rejected/superseded).

        Returns:
            Decision ID.
        """
        confidence = max(0.0, min(1.0, confidence))
        decision_id = f"decision-{uuid.uuid4().hex[:12]}"
        alts = alternatives or []

        entry = TrailEntry(
            id=decision_id,
            title=title,
            rationale=rationale,
            confidence=confidence,
            alternatives=alts,
            task_id=self._task_id,
            phase_id=self._phase_id,
            status=status,
        )
        self._entries.append(entry)

        # Persist to graph
        if self._graph is not None:
            try:
                self._graph.writer.create_node(
                    "Decision",
                    {
                        "id": decision_id,
                        "title": title,
                        "rationale": rationale,
                        "confidence": confidence,
                        "alternatives_json": json.dumps(alts) if alts else "",
                        "status": status,
                    },
                )
                # Link decision to current task
                self._graph.writer.create_relationship(
                    "Task", self._task_id,
                    "INFORMED_BY",
                    "Decision", decision_id,
                )
            except Exception as e:
                logger.debug("Decision graph write failed (non-blocking): %s", e)

        return decision_id

    def get_entries(self) -> List[TrailEntry]:
        """Return all recorded decisions."""
        return list(self._entries)

    def has_entries(self) -> bool:
        """Check if any decisions have been recorded."""
        return len(self._entries) > 0

    @staticmethod
    def get_trail(task_id: str, graph=None) -> List[Dict[str, Any]]:
        """Query graph for all decisions linked to a task.

        Args:
            task_id: Task to query decisions for.
            graph: GraphManager instance (returns empty list if None).

        Returns:
            List of decision property dicts.
        """
        if graph is None:
            return []
        try:
            nodes = graph.reader.get_nodes(
                "Decision",
                filters={},
                limit=50,
            )
            # Filter to decisions linked to this task via INFORMED_BY
            trail = []
            for node in nodes:
                # Check if this decision is linked to the task
                try:
                    rels = graph.reader.get_relationships(
                        from_label="Task",
                        from_id=task_id,
                        rel_type="INFORMED_BY",
                        to_label="Decision",
                        to_id=node.get("id"),
                    )
                    if rels:
                        trail.append(node)
                except Exception:
                    pass
            return trail
        except Exception as e:
            logger.debug("Decision trail query failed: %s", e)
            return []
