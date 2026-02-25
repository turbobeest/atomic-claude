"""
Graph-Derived Risk Budget

Computes how safe it is to use a less capable (cheaper) model for a given task,
based on structural analysis of the knowledge graph.

The risk_budget is 0.0–1.0:
  - 0.0 = never downgrade (high blast radius, no validation, deep lineage)
  - 1.0 = safe to use cheapest capable model (leaf node, validated, shallow)

When the graph is unavailable, risk_budget defaults to 0.0 (always use best model).
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def compute_blast_radius(task_id: Any, graph) -> float:
    """Score 0.0–1.0: how many downstream tasks are affected by failure.

    Uses TASK_DEPENDS_ON edges (inbound = tasks that depend on this one)
    and CONFLICTS_WITH edges on implemented requirements (amplify risk).

    Args:
        task_id: The task node ID
        graph: GraphManager instance

    Returns:
        Float 0.0–1.0 (capped)
    """
    try:
        # Tasks that directly depend on this task's output
        direct_dependents = graph.reader.get_neighbors(
            "Task", task_id, rel_type="TASK_DEPENDS_ON", direction="in",
        )

        # Transitive downstream: tasks depending on our direct dependents
        transitive_count = 0
        seen = {task_id}
        frontier = [d.get("id") for d in direct_dependents if d.get("id")]
        while frontier and transitive_count < 20:
            next_id = frontier.pop(0)
            if next_id in seen:
                continue
            seen.add(next_id)
            transitive_count += 1
            further = graph.reader.get_neighbors(
                "Task", next_id, rel_type="TASK_DEPENDS_ON", direction="in",
            )
            frontier.extend(f.get("id") for f in further if f.get("id") and f.get("id") not in seen)

        # Check for conflicting requirements (amplifies fragility)
        has_conflicts = False
        requirements = graph.reader.get_neighbors(
            "Task", task_id, rel_type="IMPLEMENTS", direction="out",
        )
        for req in requirements:
            req_id = req.get("id")
            if req_id:
                conflicts = graph.reader.get_neighbors(
                    "Requirement", req_id, rel_type="CONFLICTS_WITH", direction="both",
                )
                if conflicts:
                    has_conflicts = True
                    break

        score = (
            len(direct_dependents) * 0.3
            + transitive_count * 0.1
            + (1.0 if has_conflicts else 0.0)
        )
        return min(score, 1.0)

    except Exception as e:
        logger.debug("compute_blast_radius failed for task %s: %s", task_id, e)
        # Default to maximum blast radius on error (conservative) — forces
        # the caller to use the most capable model when risk is unknown.
        return 1.0


def has_downstream_validation(task_id: Any, graph) -> bool:
    """Check whether a later task validates/reviews this task's output.

    Checks for:
    1. REVIEW_OF edges pointing at this task (from ReviewFinding nodes)
    2. Phase heuristic: Phase 5 tasks are reviewed by Phase 6

    Args:
        task_id: The task node ID
        graph: GraphManager instance

    Returns:
        True if downstream validation exists
    """
    try:
        # Direct: ReviewFinding nodes linked via REVIEW_OF
        review_findings = graph.reader.get_neighbors(
            "Task", task_id, rel_type="REVIEW_OF", direction="in",
        )
        if review_findings:
            return True

        # Heuristic: Phase 5 implementation tasks are covered by Phase 6 code review
        task_node = graph.reader.get_node("Task", task_id)
        if task_node:
            phase = str(task_node.get("phase", ""))
            if phase.startswith("5"):
                return True

        return False

    except Exception as e:
        logger.debug("has_downstream_validation failed for task %s: %s", task_id, e)
        return False  # Conservative: assume no validation on error


def get_traceability_depth(task_id: Any, graph) -> int:
    """Count upstream lineage steps from this task back toward Source nodes.

    Traverses: Task -[IMPLEMENTS]-> Requirement -[DERIVED_FROM]-> Source
    and counts the number of hops. Deeper lineage = more accumulated
    decisions = higher risk of drift.

    Args:
        task_id: The task node ID
        graph: GraphManager instance

    Returns:
        Number of hops (0 if task has no traceable lineage)
    """
    try:
        depth = 0

        # Task -> Requirements (IMPLEMENTS)
        requirements = graph.reader.get_neighbors(
            "Task", task_id, rel_type="IMPLEMENTS", direction="out",
        )
        if requirements:
            depth += 1

        # Requirements -> Sources/Decisions/Findings (DERIVED_FROM, SUPPORTS, etc.)
        for req in requirements:
            req_id = req.get("id")
            if not req_id:
                continue
            upstream = graph.reader.get_neighbors(
                "Requirement", req_id, rel_type="DERIVED_FROM", direction="out",
            )
            if upstream:
                depth += len(upstream)
                break  # Use first requirement's depth as representative

        return depth

    except Exception as e:
        logger.debug("get_traceability_depth failed for task %s: %s", task_id, e)
        return 5  # Conservative: assume deep lineage on error


def compute_risk_budget(task_id: Any, graph=None) -> float:
    """Compute how safe it is to use a less capable model for this task.

    Combines three signals:
    1. Blast radius (inverted: low blast = high budget)
    2. Validation coverage (30% bonus if validated)
    3. Traceability depth (deeper = reduced budget)

    Args:
        task_id: The task node ID
        graph: GraphManager instance (or None)

    Returns:
        Float 0.0–1.0. Returns 0.0 if graph is unavailable (conservative).
    """
    if graph is None:
        return 0.0

    try:
        blast = compute_blast_radius(task_id, graph)
        validated = has_downstream_validation(task_id, graph)
        lineage_depth = get_traceability_depth(task_id, graph)

        # Start from blast radius (inverted: low blast = high budget)
        budget = 1.0 - blast

        # Validation catch net gives a 30% bonus (capped at 1.0)
        if validated:
            budget = min(budget * 1.3, 1.0)

        # Deep lineage reduces budget (more accumulated risk)
        # Each lineage step beyond 2 reduces budget by 10%
        if lineage_depth > 2:
            budget *= max(0.3, 1.0 - (lineage_depth - 2) * 0.1)

        return max(0.0, min(1.0, budget))

    except Exception as e:
        logger.debug("compute_risk_budget failed for task %s: %s", task_id, e)
        return 0.0  # Conservative: always use best model on error
