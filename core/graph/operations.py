"""ATOMIC CLAUDE - Graph Operations

Task management operations replacing TaskMaster CLI.
Complexity analysis, impact analysis, research binding, dependency validation."""

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GraphOperations:
    """
    High-level task management operations on the knowledge graph.

    Provides complexity analysis, impact analysis, research binding,
    dependency validation and repair, and task creation.
    """

    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer

    # ========================================================================
    # COMPLEXITY ANALYSIS
    # ========================================================================

    def analyze_complexity(self, refine_with_llm: bool = False) -> dict:
        """
        Compute structural complexity scores for all tasks.

        Scores are based on requirement count, dependency count,
        transitive dependencies, and conflict count. Each task node
        is updated with its estimated complexity, rationale, and
        recommended subtask count.

        Args:
            refine_with_llm: Placeholder for future LLM-based refinement.
                Accepted but not yet implemented.

        Returns:
            Dict with 'tasks' list and 'avg_complexity' float.
        """
        if refine_with_llm:
            logger.warning(
                "refine_with_llm=True requested but LLM refinement is not "
                "yet implemented; using structural scoring only"
            )

        topology = self.reader.get_task_topology()
        results = []
        total_score = 0

        for task in topology:
            score = min(10, 1
                        + task["req_count"] * 0.8
                        + task["dep_count"] * 0.5
                        + task["transitive_deps"] * 0.3
                        + task["conflict_count"] * 1.5)
            score = round(score)

            rationale = (
                f"reqs={task['req_count']}, "
                f"deps={task['dep_count']}, "
                f"conflicts={task['conflict_count']}"
            )

            self.writer.update_node("Task", task["id"], {
                "estimated_complexity": round(score),
                "complexity_rationale": rationale,
                "recommended_subtask_count": max(4, round(score * 0.6)),
            })

            results.append({
                "id": task["id"],
                "title": task["title"],
                "score": score,
                "rationale": rationale,
            })
            total_score += score

        avg = total_score / len(results) if results else 0

        logger.info(
            "Complexity analysis complete: %d tasks, avg=%.1f",
            len(results), avg,
        )

        return {
            "tasks": results,
            "avg_complexity": round(avg, 2),
        }

    # ========================================================================
    # IMPACT ANALYSIS
    # ========================================================================

    def update_from(self, task_id: int, prompt: str) -> list:
        """
        Identify downstream tasks affected by a change to the given task.

        Traverses the TASK_DEPENDS_ON graph up to 10 hops to find all
        tasks that transitively depend on the changed task.

        Note:
            Actual LLM regeneration of affected tasks is the caller's
            responsibility. This method performs impact analysis only.

        Args:
            task_id: The task being changed.
            prompt: Description of the change (reserved for future use).

        Returns:
            List of downstream task IDs affected by the change.
        """
        cypher = (
            "MATCH (t:Task {id: $task_id}) "
            "OPTIONAL MATCH (t)<-[:TASK_DEPENDS_ON*1..10]-(downstream:Task) "
            "RETURN t.id, collect(DISTINCT downstream.id) AS affected_ids"
        )
        result = self.reader.conn.query(cypher, {"task_id": task_id})

        if not result.result_set:
            logger.warning("Task %d not found for impact analysis", task_id)
            return []

        affected_ids = result.result_set[0][1]
        # Filter out None values that may appear from OPTIONAL MATCH
        affected_ids = [aid for aid in affected_ids if aid is not None]

        logger.info(
            "Impact analysis for task %d: %d downstream tasks affected",
            task_id, len(affected_ids),
        )
        return affected_ids

    # ========================================================================
    # RESEARCH BINDING
    # ========================================================================

    def research_save_to(self, task_id: int, research_content: str) -> str:
        """
        Bind a research finding to a task.

        Creates a Finding node with the research content and links it
        to the specified task via an INFORMED_BY edge.

        Args:
            task_id: Task to attach the research to.
            research_content: The research text to store.

        Returns:
            The generated finding ID (e.g., "R-42-1700000000").
        """
        finding_id = f"R-{task_id}-{int(time.time())}"

        self.writer.add_node("Finding", {
            "id": finding_id,
            "category": "research",
            "title": f"Research for Task {task_id}",
            "content": research_content,
            "phase": "3-tasking",
            "task_id": str(task_id),
        })

        self.writer.add_edge(
            "INFORMED_BY", "Task", task_id, "Finding", finding_id,
        )

        logger.info(
            "Saved research finding %s for task %d", finding_id, task_id,
        )
        return finding_id

    # ========================================================================
    # DEPENDENCY VALIDATION
    # ========================================================================

    def validate_dependencies(self) -> dict:
        """
        Validate the task dependency graph.

        Checks for:
        - Cycles in TASK_DEPENDS_ON relationships
        - Orphan tasks (no incoming or outgoing dependencies)
        - Missing references (structurally impossible in a graph DB,
          so always returns an empty list)

        Returns:
            Dict with 'cycles', 'orphans', 'missing_refs', and 'valid' keys.
        """
        cycles = self.reader.detect_cycles()
        orphans = self.reader.find_orphan_tasks()

        # Missing refs: in a graph DB, edges can only exist between
        # existing nodes, so dangling references are structurally
        # impossible. Included for API compatibility.
        missing_refs = []

        valid = len(cycles) == 0

        logger.info(
            "Dependency validation: cycles=%d, orphans=%d, valid=%s",
            len(cycles), len(orphans), valid,
        )

        return {
            "cycles": cycles,
            "orphans": orphans,
            "missing_refs": missing_refs,
            "valid": valid,
        }

    def fix_dependencies(self) -> dict:
        """
        Attempt to repair dependency cycles.

        For each detected cycle, removes the last edge as a heuristic
        to break the cycle, then re-validates.

        Returns:
            Dict with 'fixed_cycles' count and 'validation_after' result.
        """
        validation = self.validate_dependencies()
        fixed_count = 0

        for cycle in validation["cycles"]:
            if len(cycle) >= 2:
                from_id = cycle[-2]
                to_id = cycle[-1]
                deleted = self.writer.delete_edge(
                    "TASK_DEPENDS_ON", "Task", from_id, "Task", to_id,
                )
                if deleted:
                    fixed_count += 1
                    logger.info(
                        "Broke cycle by removing edge: Task(%s) -> Task(%s)",
                        from_id, to_id,
                    )

        result = {
            "fixed_cycles": fixed_count,
            "validation_after": self.validate_dependencies(),
        }

        logger.info(
            "Dependency fix complete: %d cycles addressed, now valid=%s",
            fixed_count, result["validation_after"]["valid"],
        )
        return result

    # ========================================================================
    # TASK CREATION
    # ========================================================================

    def add_new_task(self, title: str, description: str,
                     depends_on: list = None,
                     implements: list = None) -> int:
        """
        Create a new task with optional dependencies and requirement links.

        Automatically assigns the next available task ID and sets
        sensible defaults for status, priority, and complexity.

        Args:
            title: Task title.
            description: Task description.
            depends_on: List of task IDs this task depends on.
            implements: List of requirement IDs this task implements.

        Returns:
            The new task's ID.
        """
        # Determine next task ID
        result = self.reader.conn.query(
            "MATCH (t:Task) RETURN max(t.id) AS max_id"
        )
        max_id = result.result_set[0][0] if result.result_set and result.result_set[0][0] is not None else 0
        new_id = max_id + 1

        # Create the task node
        self.writer.add_node("Task", {
            "id": new_id,
            "title": title,
            "description": description,
            "status": "pending",
            "priority": "medium",
            "category": "feature",
            "estimated_complexity": 5,
        })

        # Add dependency edges
        if depends_on:
            for dep_id in depends_on:
                self.writer.add_edge(
                    "TASK_DEPENDS_ON", "Task", new_id, "Task", dep_id,
                )

        # Add implements edges
        if implements:
            for req_id in implements:
                self.writer.add_edge(
                    "IMPLEMENTS", "Task", new_id, "Requirement", req_id,
                )

        logger.info(
            "Created task %d: '%s' (deps=%s, implements=%s)",
            new_id, title,
            depends_on or [],
            implements or [],
        )
        return new_id
