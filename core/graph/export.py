"""
ATOMIC CLAUDE - Graph Export

Exports knowledge graph data to file formats for downstream consumption.
Supports PRD markdown, task JSON, OpenSpec JSON, and needs index JSON.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GraphExporter:
    """
    Export graph data to structured file formats.

    Reads from the knowledge graph via GraphReader and produces
    markdown and JSON files suitable for pipeline consumption.
    """

    def __init__(self, reader):
        """
        Args:
            reader: GraphReader instance for querying the graph
        """
        self.reader = reader

    # ========================================================================
    # PRD MARKDOWN EXPORT
    # ========================================================================

    def export_prd_md(self, output_path: Path) -> None:
        """
        Export a PRD markdown document assembled from graph data.

        Sections:
        - Vision (findings with category "vision")
        - Target Audience (findings with category "audience")
        - Features (Feature nodes with their Requirements)
        - Non-Functional Requirements
        - Constraints
        - Decisions (accepted)

        Args:
            output_path: Destination file path (.md)
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        parts: List[str] = []
        parts.append("# Product Requirements Document\n\n")

        # --- Vision ---
        vision_findings = self.reader.get_nodes(
            "Finding", filters={"category": "vision"}
        )
        parts.append("## Vision\n\n")
        if vision_findings:
            for f in vision_findings:
                title = f.get("title", "")
                content = f.get("content", "")
                if title:
                    parts.append(f"### {title}\n\n")
                if content:
                    parts.append(f"{content}\n\n")
        else:
            parts.append("_No vision findings recorded._\n\n")

        # --- Target Audience ---
        audience_findings = self.reader.get_nodes(
            "Finding", filters={"category": "audience"}
        )
        parts.append("## Target Audience\n\n")
        if audience_findings:
            for f in audience_findings:
                title = f.get("title", "")
                content = f.get("content", "")
                if title:
                    parts.append(f"### {title}\n\n")
                if content:
                    parts.append(f"{content}\n\n")
        else:
            parts.append("_No audience findings recorded._\n\n")

        # --- Features with Requirements ---
        parts.append("## Features\n\n")
        features = self.reader.get_nodes("Feature", order_by="id")
        if features:
            for feature in features:
                fid = feature.get("id", "")
                ftitle = feature.get("title", "")
                fdesc = feature.get("description", "")
                parts.append(f"### {ftitle}\n\n")
                if fdesc:
                    parts.append(f"{fdesc}\n\n")

                # Get requirements contained in this feature
                requirements = self.reader.get_neighbors(
                    "Feature", fid, rel_type="CONTAINS", direction="out"
                )
                if requirements:
                    parts.append("**Requirements:**\n\n")
                    for req in requirements:
                        priority = req.get("priority", "medium")
                        rfc = req.get("rfc2119_keyword", "")
                        rtitle = req.get("title", "")
                        rcontent = req.get("content", "")
                        prefix = f"[{priority}]"
                        if rfc:
                            prefix += f" {rfc}"
                        parts.append(f"- {prefix} **{rtitle}**: {rcontent}\n")
                    parts.append("\n")
        else:
            parts.append("_No features defined._\n\n")

        # --- Non-Functional Requirements ---
        parts.append("## Non-Functional Requirements\n\n")
        nfr_list = self.reader.get_nodes(
            "Requirement", filters={"type": "non_functional"}
        )
        if nfr_list:
            for req in nfr_list:
                priority = req.get("priority", "medium")
                rtitle = req.get("title", "")
                rcontent = req.get("content", "")
                parts.append(f"- [{priority}] **{rtitle}**: {rcontent}\n")
            parts.append("\n")
        else:
            parts.append("_No non-functional requirements defined._\n\n")

        # --- Constraints ---
        parts.append("## Constraints\n\n")
        constraints = self.reader.get_nodes(
            "Requirement", filters={"type": "constraint"}
        )
        if constraints:
            for req in constraints:
                rtitle = req.get("title", "")
                rcontent = req.get("content", "")
                parts.append(f"- **{rtitle}**: {rcontent}\n")
            parts.append("\n")
        else:
            parts.append("_No constraints defined._\n\n")

        # --- Decisions ---
        parts.append("## Decisions\n\n")
        decisions = self.reader.get_nodes(
            "Decision", filters={"status": "accepted"}
        )
        if decisions:
            for d in decisions:
                dtitle = d.get("title", "")
                rationale = d.get("rationale", "")
                parts.append(f"### {dtitle}\n\n")
                if rationale:
                    parts.append(f"**Rationale:** {rationale}\n\n")
        else:
            parts.append("_No accepted decisions recorded._\n\n")

        content = "".join(parts)
        output_path.write_text(content, encoding="utf-8")
        logger.info(f"Exported PRD markdown to {output_path}")

    # ========================================================================
    # TASKS JSON EXPORT
    # ========================================================================

    def export_tasks_json(self, output_path: Path) -> None:
        """
        Export all Task nodes as a JSON file with dependencies.

        Output schema:
        {
            "tasks": [
                {
                    "id": 1,
                    "title": "...",
                    "description": "...",
                    "dependencies": [2, 3],
                    "subtasks": [...],
                    ...
                }
            ],
            "metadata": {
                "generated_from": "graph",
                "timestamp": "..."
            }
        }

        Args:
            output_path: Destination file path (.json)
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        tasks = self.reader.get_nodes("Task", order_by="id")
        task_list: List[Dict[str, Any]] = []

        for task in tasks:
            task_id = task.get("id")

            # Query dependencies via TASK_DEPENDS_ON edges
            dep_neighbors = self.reader.get_neighbors(
                "Task", task_id, rel_type="TASK_DEPENDS_ON", direction="out"
            )
            dependency_ids = [
                dep.get("id") for dep in dep_neighbors if dep.get("id") is not None
            ]

            # Query subtasks (tasks that depend on this one, incoming edges)
            subtask_neighbors = self.reader.get_neighbors(
                "Task", task_id, rel_type="TASK_DEPENDS_ON", direction="in"
            )
            subtask_ids = [
                st.get("id") for st in subtask_neighbors if st.get("id") is not None
            ]

            task_entry = dict(task)
            task_entry["dependencies"] = sorted(dependency_ids)
            task_entry["subtasks"] = sorted(subtask_ids)
            task_list.append(task_entry)

        output_data = {
            "tasks": task_list,
            "metadata": {
                "generated_from": "graph",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "task_count": len(task_list),
            },
        }

        output_path.write_text(
            json.dumps(output_data, indent=2, default=str),
            encoding="utf-8",
        )
        logger.info(f"Exported {len(task_list)} tasks to {output_path}")

    # ========================================================================
    # OPENSPEC EXPORT
    # ========================================================================

    def export_openspec(self, task_id: int, output_path: Path) -> None:
        """
        Export the OpenSpec for a specific task.

        Retrieves the Spec node, parses JSON string properties back to
        objects, and includes linked task details and requirements.

        Args:
            task_id: Task ID to export the spec for
            output_path: Destination file path (.json)
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        spec = self.reader.get_node("Spec", task_id)
        if spec is None:
            logger.warning(f"No Spec found for task_id={task_id}")
            output_path.write_text(
                json.dumps({"error": f"No spec found for task {task_id}"}),
                encoding="utf-8",
            )
            return

        # Parse JSON string fields back to objects
        json_fields = [
            "test_strategy_json",
            "interfaces_json",
            "error_handling_json",
            "dependencies_json",
            "file_structure_json",
        ]
        for field in json_fields:
            raw_value = spec.get(field)
            if raw_value and isinstance(raw_value, str):
                try:
                    spec[field] = json.loads(raw_value)
                except (json.JSONDecodeError, TypeError):
                    logger.debug(
                        f"Could not parse {field} as JSON for task {task_id}"
                    )

        # Include task details
        task = self.reader.get_node("Task", task_id)
        if task:
            spec["task"] = task

        # Include requirements this task implements
        cypher = (
            "MATCH (t:Task {id: $tid})-[:IMPLEMENTS]->(r:Requirement) "
            "RETURN r ORDER BY r.id"
        )
        result = self.reader.conn.query(cypher, {"tid": task_id})
        if result.result_set:
            spec["requirements"] = [
                self.reader._node_to_dict(row[0]) for row in result.result_set
            ]

        output_data = {
            "spec": spec,
            "metadata": {
                "generated_from": "graph",
                "task_id": task_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

        output_path.write_text(
            json.dumps(output_data, indent=2, default=str),
            encoding="utf-8",
        )
        logger.info(f"Exported OpenSpec for task {task_id} to {output_path}")

    # ========================================================================
    # NEEDS INDEX EXPORT
    # ========================================================================

    def export_needs_index(self, output_path: Path) -> None:
        """
        Export all Source nodes of type "need" with linked Findings.

        Output schema:
        {
            "needs": [
                {
                    "id": "...",
                    "title": "...",
                    "type": "need",
                    "findings": [...]
                }
            ],
            "metadata": {
                "generated_from": "graph",
                "timestamp": "..."
            }
        }

        Args:
            output_path: Destination file path (.json)
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        need_sources = self.reader.get_nodes(
            "Source", filters={"type": "need"}
        )

        needs_list: List[Dict[str, Any]] = []
        for source in need_sources:
            source_id = source.get("id")

            # Findings derived from this source (DERIVED_FROM points Source <- Finding)
            cypher = (
                "MATCH (f:Finding)-[:DERIVED_FROM]->(s:Source {id: $sid}) "
                "RETURN f ORDER BY f.id"
            )
            result = self.reader.conn.query(cypher, {"sid": source_id})
            findings = [
                self.reader._node_to_dict(row[0]) for row in result.result_set
            ] if result.result_set else []

            need_entry = dict(source)
            need_entry["findings"] = findings
            needs_list.append(need_entry)

        output_data = {
            "needs": needs_list,
            "metadata": {
                "generated_from": "graph",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "need_count": len(needs_list),
            },
        }

        output_path.write_text(
            json.dumps(output_data, indent=2, default=str),
            encoding="utf-8",
        )
        logger.info(f"Exported {len(needs_list)} needs to {output_path}")
