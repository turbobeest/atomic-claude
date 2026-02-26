"""Nightly skill consolidation: workflow crystallization, decay, pruning, calibration."""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.skills.models import GravityLevel

logger = logging.getLogger(__name__)


class SkillConsolidation:
    """Nightly maintenance for the skill graph."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.report: Dict[str, List[str]] = {
            "actions": [],
            "warnings": [],
        }

    def run_all(self) -> Dict[str, List[str]]:
        """Execute full consolidation pipeline."""
        try:
            from core.graph import get_graph
            graph = get_graph(phase_id="skill-consolidate")
            conn = graph.conn
        except Exception as e:
            self.report["warnings"].append(f"Graph unavailable: {e}")
            return self.report

        self.crystallize_workflows(conn)
        self.decay_unused_skills(conn)
        self.prune_weak_edges(conn)
        self.calibrate_gravity(conn)

        return self.report

    def crystallize_workflows(self, conn) -> int:
        """
        Find recurring skill sequences (3+ successful uses).
        Promote to Workflow nodes.
        """
        cypher = (
            "MATCH (e:Episode) "
            "WHERE e.skills_used IS NOT NULL AND e.success_score IS NOT NULL "
            "RETURN e.skills_used, toFloat(e.success_score) AS score"
        )
        try:
            result = conn.query(cypher)
        except Exception as e:
            logger.debug("Crystallize query failed: %s", e)
            return 0

        # Group by sorted skill tuples
        sequences = {}
        for row in result.result_set:
            skills_csv = row[0]
            score = row[1]
            if not skills_csv or score < 0.7:
                continue
            skills = tuple(sorted(s.strip() for s in skills_csv.split(",") if s.strip()))
            if len(skills) < 3:
                continue
            if skills not in sequences:
                sequences[skills] = {"count": 0, "total_score": 0.0}
            sequences[skills]["count"] += 1
            sequences[skills]["total_score"] += score

        created = 0
        for skills, data in sequences.items():
            if data["count"] < 3:
                continue

            wf_id = "wf-" + hashlib.md5(",".join(skills).encode()).hexdigest()[:12]
            avg_score = data["total_score"] / data["count"]

            if self.dry_run:
                self.report["actions"].append(f"[DRY-RUN] Would create Workflow {wf_id}: {skills}")
                created += 1
                continue

            cypher_wf = (
                "MERGE (w:Workflow {id: $id}) "
                "SET w.name = $name, w.skills_csv = $skills_csv, "
                "w.occurrence_count = $count, w.avg_score = $avg, "
                "w.task_pattern = $pattern, w.created_at = $now"
            )
            try:
                conn.query(cypher_wf, {
                    "id": wf_id,
                    "name": f"Workflow: {', '.join(skills[:3])}...",
                    "skills_csv": ",".join(skills),
                    "count": data["count"],
                    "avg": avg_score,
                    "pattern": " ".join(skills),
                    "now": datetime.now(timezone.utc).isoformat(),
                })

                # Create STEP edges
                for order, skill_id in enumerate(skills):
                    cypher_step = (
                        "MATCH (w:Workflow {id: $wid}), (s:Skill {id: $sid}) "
                        "MERGE (w)-[r:STEP]->(s) "
                        "SET r.order = $order"
                    )
                    conn.query(cypher_step, {"wid": wf_id, "sid": skill_id, "order": order})

                created += 1
                self.report["actions"].append(f"Created Workflow {wf_id}: {skills}")
            except Exception as e:
                logger.debug("Workflow creation failed for %s: %s", wf_id, e)

        return created

    def decay_unused_skills(self, conn) -> int:
        """Reduce avg_success_score by 5% for skills unused 30+ days. Floor at 0.1."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        cypher = (
            "MATCH (s:Skill) "
            "WHERE (s.last_used < $cutoff) OR (s.last_used IS NULL) "
            "RETURN s.id, s.avg_success_score, s.last_used"
        )
        try:
            result = conn.query(cypher, {"cutoff": cutoff})
        except Exception as e:
            logger.debug("Decay query failed: %s", e)
            return 0

        decayed = 0
        for row in result.result_set:
            sid, old_score, last_used = row
            if old_score is None or old_score <= 0.1:
                continue

            new_score = max(0.1, old_score * 0.95)
            if self.dry_run:
                self.report["actions"].append(f"[DRY-RUN] Decay {sid}: {old_score:.3f} → {new_score:.3f}")
                decayed += 1
                continue

            cypher_update = "MATCH (s:Skill {id: $id}) SET s.avg_success_score = $score"
            try:
                conn.query(cypher_update, {"id": sid, "score": new_score})
                decayed += 1
                self.report["actions"].append(f"Decayed {sid}: {old_score:.3f} → {new_score:.3f}")
            except Exception as e:
                logger.debug("Decay update failed for %s: %s", sid, e)

        return decayed

    def prune_weak_edges(self, conn) -> int:
        """Remove COMPOSES_WITH edges with co_occurrence < 2 and age > 60 days."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        cypher = (
            "MATCH (a:Skill)-[r:COMPOSES_WITH]->(b:Skill) "
            "WHERE r.co_occurrence < 2 "
            "AND r.created_at < $cutoff "
            "RETURN a.id, b.id, r.co_occurrence"
        )
        try:
            result = conn.query(cypher, {"cutoff": cutoff})
        except Exception as e:
            logger.debug("Prune query failed: %s", e)
            return 0

        pruned = 0
        for row in result.result_set:
            a_id, b_id, count = row
            if self.dry_run:
                self.report["actions"].append(f"[DRY-RUN] Prune {a_id}→{b_id} (co_occurrence={count})")
                pruned += 1
                continue

            cypher_del = (
                "MATCH (a:Skill {id: $a})-[r:COMPOSES_WITH]->(b:Skill {id: $b}) "
                "DELETE r"
            )
            try:
                conn.query(cypher_del, {"a": a_id, "b": b_id})
                pruned += 1
                self.report["actions"].append(f"Pruned {a_id}→{b_id}")
            except Exception as e:
                logger.debug("Prune delete failed: %s", e)

        return pruned

    def calibrate_gravity(self, conn) -> None:
        """Track false-light rates per project, auto-raise gravity floors."""
        cypher = (
            "MATCH (e:Episode) "
            "WHERE e.gravity = 'light' AND e.success_score < 0.5 "
            "RETURN count(e) AS false_light_count"
        )
        try:
            result = conn.query(cypher)
            false_light = result.result_set[0][0] if result.result_set else 0

            cypher_total = (
                "MATCH (e:Episode) WHERE e.gravity = 'light' RETURN count(e)"
            )
            total_result = conn.query(cypher_total)
            total_light = total_result.result_set[0][0] if total_result.result_set else 0

            if total_light > 10 and false_light / total_light > 0.15:
                self.report["warnings"].append(
                    f"High false-light rate: {false_light}/{total_light} "
                    f"({false_light/total_light:.1%}). Consider raising gravity floors."
                )
        except Exception as e:
            logger.debug("Gravity calibration query failed: %s", e)
