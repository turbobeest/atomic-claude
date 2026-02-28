"""Graph-aware skill selection engine with gravity-based filtering."""

import logging
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.skills.models import (
    GravityLevel, SkillMetadata, SkillSelection,
    PROFILE_SKILL_RULES,
)

logger = logging.getLogger(__name__)


class SkillSelector:
    """3-stage skill selection: workflow match -> structural traversal -> fulltext search."""

    def select(
        self,
        task_prompt: str,
        profile_name: str = "cloud_full",
        gravity: GravityLevel = GravityLevel.STANDARD,
        project_id: str = "default",
    ) -> SkillSelection:
        """Select skills for a task based on gravity + profile."""
        params = self._gravity_params(gravity)

        # Try graph-based selection
        try:
            return self._graph_select(task_prompt, profile_name, gravity, params)
        except Exception as e:
            logger.debug("Graph selection failed, falling back to filesystem: %s", e)
            return self._filesystem_fallback(task_prompt, profile_name, gravity, params)

    def _gravity_params(self, gravity: GravityLevel) -> Dict:
        """Return query parameters adjusted for gravity level."""
        if gravity == GravityLevel.LIGHT:
            return {
                "max_skills": 2,
                "limit": 3,
                "skip_workflow": True,
                "skip_semantic": True,
                "mandatory_categories": [],
            }
        elif gravity == GravityLevel.INTENSIVE:
            return {
                "max_skills": 15,
                "limit": 15,
                "skip_workflow": False,
                "skip_semantic": False,
                "mandatory_categories": ["testing", "security"],
                "composition_threshold": 0.4,
            }
        else:  # STANDARD
            return {
                "max_skills": 8,
                "limit": 10,
                "skip_workflow": False,
                "skip_semantic": False,
                "mandatory_categories": [],
            }

    def _graph_select(self, task_prompt, profile_name, gravity, params) -> SkillSelection:
        """3-stage graph-based selection."""
        from core.graph import get_graph
        graph = get_graph(phase_id="skill-select")
        conn = graph.conn

        result_skills = []
        method = "none"
        workflow_name = None

        # Stage 1: Workflow match (skip for light gravity)
        if not params.get("skip_workflow"):
            # Ported from falkordb_bridge.py action_select Stage 1
            cypher = (
                "MATCH (w:Workflow) "
                "WHERE toLower(w.task_pattern) CONTAINS toLower($task) "
                "RETURN w.id AS wid, w.name AS wname "
                "LIMIT 1"
            )
            try:
                wf_result = conn.query(cypher, {"task": task_prompt})
                if wf_result.result_set:
                    wid = wf_result.result_set[0][0]
                    workflow_name = wf_result.result_set[0][1]

                    # Get skills in this workflow, ordered by STEP.order
                    cypher_skills = (
                        "MATCH (w:Workflow {id: $wid})-[step:STEP]->(s:Skill) "
                        "WHERE s.installed = true "
                        "RETURN s "
                        "ORDER BY step.order"
                    )
                    wf_skills = conn.query(cypher_skills, {"wid": wid})
                    for row in wf_skills.result_set:
                        node = row[0]
                        props = dict(node.properties) if hasattr(node, "properties") else node
                        result_skills.append(props)
                    if result_skills:
                        method = "workflow"
            except Exception as e:
                logger.debug("Workflow match failed: %s", e)

        # Stage 2: Structural traversal (phase-based, quality-weighted)
        if not result_skills:
            # Quality-weighted ordering: avg_success_score * log(times_used + 1)
            # High quality + moderate use beats low quality + heavy use
            cypher = (
                "MATCH (s:Skill)-[:BELONGS_TO]->(p:SDLCPhase) "
                "WHERE s.installed = true "
                "WITH DISTINCT s, "
                "CASE WHEN s.times_used > 0 "
                "THEN s.avg_success_score * log(toFloat(s.times_used) + 1.0) "
                "ELSE 0.0 END AS quality_score "
                "RETURN s "
                "ORDER BY quality_score DESC "
                "LIMIT $limit"
            )
            try:
                struct_result = conn.query(cypher, {"limit": params["limit"]})
                for row in struct_result.result_set:
                    node = row[0]
                    props = dict(node.properties) if hasattr(node, "properties") else node
                    result_skills.append(props)
                if result_skills:
                    method = "structural"
            except Exception as e:
                logger.debug("Structural traversal failed: %s", e)

        # Stage 3: Fulltext search (skip for light gravity)
        if not result_skills and not params.get("skip_semantic"):
            # Ported from falkordb_bridge.py action_select Stage 3
            cypher = (
                "CALL db.idx.fulltext.queryNodes('Skill', $query) "
                "YIELD node AS s "
                "WHERE s.installed = true "
                "RETURN s "
                "LIMIT $limit"
            )
            try:
                ft_result = conn.query(cypher, {"query": task_prompt, "limit": params["limit"]})
                for row in ft_result.result_set:
                    node = row[0]
                    props = dict(node.properties) if hasattr(node, "properties") else node
                    result_skills.append(props)
                if result_skills:
                    method = "semantic"
            except Exception as e:
                logger.debug("Fulltext search failed: %s", e)

        # Profile filter: only keep skills allowed in this profile
        filtered = []
        for props in result_skills:
            csv = props.get("installable_in_profiles_csv", "")
            installable = [p.strip() for p in csv.split(",") if p.strip()] if csv else ["development"]
            if profile_name in installable:
                filtered.append(props)
        result_skills = filtered

        # Inject mandatory categories for intensive gravity
        if gravity == GravityLevel.INTENSIVE and params.get("mandatory_categories"):
            existing_cats = {s.get("category") for s in result_skills}
            for cat in params["mandatory_categories"]:
                if cat not in existing_cats:
                    cypher = (
                        "MATCH (s:Skill) "
                        "WHERE s.category = $cat AND s.installed = true "
                        "RETURN s LIMIT 1"
                    )
                    try:
                        cat_result = conn.query(cypher, {"cat": cat})
                        if cat_result.result_set:
                            node = cat_result.result_set[0][0]
                            props = dict(node.properties) if hasattr(node, "properties") else node
                            result_skills.append(props)
                    except Exception:
                        pass

        # Limit to max_skills
        result_skills = result_skills[:params["max_skills"]]

        # Convert to SkillMetadata objects
        skills = []
        for props in result_skills:
            try:
                skills.append(SkillMetadata(
                    **{k: v for k, v in props.items() if k != "installable_in_profiles_csv"}
                ))
            except Exception:
                logger.debug("Skipping skill with invalid props: %s", props.get("id", "?"))

        return SkillSelection(
            skills=skills,
            workflow=workflow_name,
            method=method,
            gravity=gravity,
            profile=profile_name,
        )

    def _filesystem_fallback(self, task_prompt, profile_name, gravity, params) -> SkillSelection:
        """Fallback when FalkorDB is unavailable -- scan local skill directories."""
        from core.skills.catalog import SKILL_CATALOG

        prompt_lower = task_prompt.lower()
        scored = []
        for skill in SKILL_CATALOG:
            if profile_name not in skill.installable_in_profiles():
                continue
            # Keyword relevance score
            relevance = 0
            name_lower = skill.name.lower()
            desc_lower = skill.description.lower()
            for word in prompt_lower.split():
                if len(word) < 3:
                    continue
                if word in name_lower:
                    relevance += 2
                if word in desc_lower:
                    relevance += 1
            if relevance > 0:
                # Quality multiplier: avg_success_score * log(times_used + 1)
                if skill.times_used > 0:
                    quality = skill.avg_success_score * math.log(skill.times_used + 1)
                else:
                    quality = 0.5  # Neutral prior for unused skills
                combined = relevance * max(quality, 0.1)
                scored.append((combined, skill))

        scored.sort(key=lambda x: x[0], reverse=True)
        skills = [s for _, s in scored[:params["max_skills"]]]

        return SkillSelection(
            skills=skills,
            method="filesystem_fallback",
            gravity=gravity,
            profile=profile_name,
        )
