"""Skill usage logging, composition discovery, and gravity accuracy tracking."""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from core.skills.models import GravityLevel

logger = logging.getLogger(__name__)


class SkillLearning:
    """Post-task learning: episode logging, composition discovery, gravity calibration."""

    def log_usage(
        self,
        task_id: str,
        skill_ids: List[str],
        success_score: float,
        gravity: str = "standard",
        tokens: int = 0,
        duration_ms: int = 0,
    ) -> Optional[str]:
        """
        Create Episode node, USED_IN edges, update Skill running averages.
        Returns episode_id or None if graph unavailable.
        """
        try:
            from core.graph import get_graph
            graph = get_graph(phase_id="skill-learning")
            conn = graph.conn
        except Exception as e:
            logger.debug("Graph unavailable for skill learning: %s", e)
            return None

        # Determine outcome category
        if success_score >= 0.8:
            outcome = "success"
        elif success_score >= 0.4:
            outcome = "partial"
        else:
            outcome = "failure"

        episode_id = f"ep-{task_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        # Create Episode node (idempotent via MERGE)
        # Ported from falkordb_bridge.py action_log_outcome
        cypher_episode = (
            "MERGE (e:Episode {id: $id}) "
            "SET e.task_id = $task_id, "
            "e.outcome = $outcome, "
            "e.success_score = $success_score, "
            "e.tokens_consumed = $tokens, "
            "e.duration_ms = $duration_ms, "
            "e.gravity = $gravity, "
            "e.skills_used = $skills_csv, "
            "e.created_at = $created_at"
        )
        conn.query(cypher_episode, {
            "id": episode_id,
            "task_id": task_id,
            "outcome": outcome,
            "success_score": success_score,
            "tokens": tokens,
            "duration_ms": duration_ms,
            "gravity": gravity,
            "skills_csv": ",".join(skill_ids),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

        # Create USED_IN edges and update skill running averages
        for skill_id in skill_ids:
            # USED_IN edge
            cypher_used = (
                "MATCH (s:Skill {id: $skill_id}), (e:Episode {id: $episode_id}) "
                "MERGE (s)-[r:USED_IN]->(e) "
                "SET r.success_score = $score"
            )
            conn.query(cypher_used, {
                "skill_id": skill_id,
                "episode_id": episode_id,
                "score": success_score,
            })

            # Running average update on Skill node
            # Ported from falkordb_bridge.py action_log_outcome
            cypher_avg = (
                "MATCH (s:Skill {id: $skill_id}) "
                "SET s.times_used = s.times_used + 1, "
                "s.avg_success_score = "
                "CASE WHEN s.times_used = 0 THEN $score "
                "ELSE ((s.avg_success_score * s.times_used) + $score) / (s.times_used + 1) "
                "END, "
                "s.last_used = $now"
            )
            conn.query(cypher_avg, {
                "skill_id": skill_id,
                "score": success_score,
                "now": datetime.now(timezone.utc).isoformat(),
            })

        logger.info("Logged episode %s: %d skills, outcome=%s", episode_id, len(skill_ids), outcome)
        return episode_id

    def discover_compositions(self, task_id: str) -> int:
        """
        Find co-used skill pairs from recent episodes, strengthen COMPOSES_WITH edges.

        Ported from consolidate_skills.py crystallize_workflows — the co-occurrence
        detection part. Skills used together in successful episodes (score >= 0.7)
        get a COMPOSES_WITH edge when co-occurrence count >= 2.
        """
        try:
            from core.graph import get_graph
            graph = get_graph(phase_id="skill-compose")
            conn = graph.conn
        except Exception:
            return 0

        # Find skills used together in successful episodes
        cypher = (
            "MATCH (s1:Skill)-[:USED_IN]->(e:Episode)<-[:USED_IN]-(s2:Skill) "
            "WHERE s1.id < s2.id AND e.success_score >= 0.7 "
            "RETURN s1.id, s2.id, count(e) AS co_count, avg(e.success_score) AS avg_score"
        )
        try:
            result = conn.query(cypher)
        except Exception as e:
            logger.debug("Composition discovery failed: %s", e)
            return 0

        updated = 0
        for row in result.result_set:
            s1_id, s2_id, co_count, avg_score = row
            if co_count >= 2:
                cypher_comp = (
                    "MATCH (a:Skill {id: $a_id}), (b:Skill {id: $b_id}) "
                    "MERGE (a)-[r:COMPOSES_WITH]->(b) "
                    "SET r.co_occurrence = $count, r.avg_combined_success = $avg"
                )
                conn.query(cypher_comp, {
                    "a_id": s1_id,
                    "b_id": s2_id,
                    "count": co_count,
                    "avg": avg_score,
                })
                updated += 1

        if updated:
            logger.info("Discovered %d skill compositions for task %s", updated, task_id)
        return updated

    def log_gravity_accuracy(
        self,
        task_id: str,
        assessed_gravity: GravityLevel,
        success_score: float,
        tokens: int = 0,
        duration_ms: int = 0,
    ) -> None:
        """
        Compare outcome against gravity medians, flag misclassifications.

        A light-classified task that fails is a "false-light" -- the gravity was
        under-estimated and the task needed more resources. An intensive-classified
        task that succeeds trivially is over-classified.
        """
        if assessed_gravity == GravityLevel.LIGHT and success_score < 0.5:
            logger.warning(
                "GRAVITY MISCLASSIFICATION: task %s classified as LIGHT but scored %.2f "
                "(possible false-light)",
                task_id, success_score,
            )
        elif assessed_gravity == GravityLevel.INTENSIVE and success_score >= 0.95 and tokens < 500:
            logger.info(
                "Gravity over-classification: task %s classified as INTENSIVE but was trivial "
                "(score=%.2f, tokens=%d)",
                task_id, success_score, tokens,
            )
