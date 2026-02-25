"""ATOMIC CLAUDE - Graph Manager

High-level graph operations for pipeline tasks.
This is the primary interface used by phase orchestrators."""

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GraphManager:
    """
    High-level graph operations for pipeline phases.

    Provides a unified API over GraphWriter, GraphReader, GraphExporter,
    and GraphOperations. Phase orchestrators and tasks interact with
    the knowledge graph exclusively through this class.
    """

    def __init__(self, connection, phase_id: str):
        from .writer import GraphWriter
        from .reader import GraphReader
        from .export import GraphExporter
        from .operations import GraphOperations

        self.conn = connection
        self.phase_id = phase_id
        self.writer = GraphWriter(connection)
        self.reader = GraphReader(connection)
        self.exporter = GraphExporter(self.reader)
        self.operations = GraphOperations(self.reader, self.writer)

    # ========================================================================
    # WRITE OPERATIONS
    # ========================================================================

    def add_source(self, id: Any, type: str, title: str, **kwargs) -> None:
        """Add a Source node to the graph."""
        self.writer.add_node("Source", {
            "id": id,
            "type": type,
            "title": title,
            "phase": self.phase_id,
            **kwargs,
        })

    def add_finding(self, id: Any, category: str, title: str, content: str,
                    source_id: Any = None, **kwargs) -> None:
        """Add a Finding node, optionally linked to a Source."""
        self.writer.add_node("Finding", {
            "id": id,
            "category": category,
            "title": title,
            "content": content,
            "phase": self.phase_id,
            **kwargs,
        })
        if source_id:
            self.writer.add_edge(
                "DERIVED_FROM", "Finding", id, "Source", source_id,
            )

    def add_decision(self, id: Any, title: str, rationale: str,
                     status: str = "proposed", **kwargs) -> None:
        """Add a Decision node."""
        self.writer.add_node("Decision", {
            "id": id,
            "title": title,
            "rationale": rationale,
            "status": status,
            "phase": self.phase_id,
            **kwargs,
        })

    def add_requirement(self, id: Any, type: str, title: str, content: str,
                        feature_id: Any = None, **kwargs) -> None:
        """Add a Requirement node, optionally contained by a Feature."""
        self.writer.add_node("Requirement", {
            "id": id,
            "type": type,
            "title": title,
            "content": content,
            **kwargs,
        })
        if feature_id:
            self.writer.add_edge(
                "CONTAINS", "Feature", feature_id, "Requirement", id,
            )

    def add_feature(self, id: Any, title: str, description: Optional[str] = None,
                    **kwargs) -> None:
        """Add a Feature node."""
        self.writer.add_node("Feature", {
            "id": id,
            "title": title,
            "description": description or "",
            **kwargs,
        })

    def add_task(self, id: Any, title: str, description: str,
                 requirements: Optional[List[Any]] = None,
                 depends_on: Optional[List[Any]] = None,
                 **kwargs) -> None:
        """Add a Task node with optional requirement and dependency edges."""
        self.writer.add_node("Task", {
            "id": id,
            "title": title,
            "description": description,
            **kwargs,
        })
        for req_id in (requirements or []):
            self.writer.add_edge(
                "IMPLEMENTS", "Task", id, "Requirement", req_id,
            )
        for dep_id in (depends_on or []):
            self.writer.add_edge(
                "TASK_DEPENDS_ON", "Task", id, "Task", dep_id,
            )

    def update_task_status(self, task_id: Any, status: str) -> bool:
        """Update a Task node's status field.

        Args:
            task_id: The task identifier
            status: One of "pending", "in_progress", "done", "blocked"

        Returns:
            True if the node was found and updated

        Raises:
            ValueError: If status is not a valid value
        """
        valid_statuses = {"pending", "in_progress", "done", "blocked"}
        if status not in valid_statuses:
            raise ValueError(f"Invalid task status '{status}'; must be one of {valid_statuses}")
        return self.writer.update_node("Task", task_id, {"status": status})

    def add_spec(self, task_id: Any, spec_data: dict) -> None:
        """Add a Spec node linked to its Task via HAS_SPEC."""
        spec_id = f"spec-{task_id}"
        self.writer.add_node("Spec", {
            "id": spec_id,
            "task_id": task_id,
            **spec_data,
        })
        self.writer.add_edge(
            "HAS_SPEC", "Task", task_id, "Spec", task_id,
        )

    def add_interface(self, from_task_id: Any, to_task_id: Any,
                      name: str, direction: str, **kwargs) -> None:
        """Add a SPEC_INTERFACE edge between two Spec nodes."""
        self.writer.add_edge(
            "SPEC_INTERFACE", "Spec", from_task_id, "Spec", to_task_id,
            {"name": name, "direction": direction, **kwargs},
        )

    def link(self, rel_type: str, from_label: str, from_id: Any,
             to_label: str, to_id: Any, **properties) -> None:
        """Create an arbitrary relationship between two nodes."""
        self.writer.add_edge(
            rel_type, from_label, from_id, to_label, to_id,
            properties if properties else None,
        )

    # ========================================================================
    # AGENT OPERATIONS
    # ========================================================================

    def add_agent(self, name: str, tier: str, category: str, role: str,
                  **kwargs) -> None:
        """Add an Agent node to the graph."""
        self.writer.add_node("Agent", {
            "id": name,
            "name": name,
            "tier": tier,
            "category": category,
            "role": role,
            "phase": self.phase_id,
            **kwargs,
        })

    def load_agents_from_manifest(self, manifest_path: Path) -> int:
        """Load agents from agent-manifest.json into graph.

        Skips loading if all agents are already present (idempotent).
        Returns count of agents loaded (0 if already loaded).
        """
        manifest_path = Path(manifest_path)
        if not manifest_path.exists():
            logger.warning(f"Agent manifest not found: {manifest_path}")
            return 0

        with open(manifest_path) as f:
            manifest = json.load(f)

        agents = manifest.get("agents", [])
        if not agents:
            return 0

        # Check if already loaded
        existing = self.reader.count_nodes("Agent")
        if existing >= len(agents):
            logger.debug(f"Agent catalog already loaded ({existing} agents)")
            return 0

        # Bulk load all agents
        ops = []
        for agent in agents:
            props = {
                "id": agent["name"],
                "name": agent["name"],
                "tier": agent.get("tier", "expert"),
                "category": agent.get("category", ""),
                "role": agent.get("role", "executor"),
                "phase": self.phase_id,
                "description": agent.get("description", ""),
                "subcategory": agent.get("subcategory", ""),
                "composite_score": agent.get("composite_score", 0.0),
                "grade": agent.get("grade", ""),
            }
            ops.append({"op": "add_node", "label": "Agent", "properties": props})

        loaded = self.writer.bulk_write(ops)
        logger.info(f"Loaded {loaded} agents from manifest into graph")
        return loaded

    def query_agent_catalog(self, tier: str = None,
                            categories: List[str] = None) -> str:
        """Return a formatted agent catalog string for LLM consumption.

        Groups agents by category with name + short description.
        Optional filters by tier and/or categories.
        """
        filters = {}
        if tier:
            filters["tier"] = tier

        agents = self.reader.get_nodes("Agent", filters=filters if filters else None,
                                       order_by="category")

        # Apply category filter if specified
        if categories:
            cat_set = set(categories)
            agents = [a for a in agents if a.get("category") in cat_set]

        if not agents:
            return ""

        # Group by category
        by_category = defaultdict(list)
        for a in agents:
            by_category[a.get("category", "uncategorized")].append(a)

        parts = []
        for cat in sorted(by_category.keys()):
            cat_agents = by_category[cat]
            parts.append(f"### {cat} ({len(cat_agents)} agents)")
            for a in sorted(cat_agents, key=lambda x: x.get("name", "")):
                desc = a.get("description", "")
                # Truncate long descriptions for prompt efficiency
                if len(desc) > 120:
                    desc = desc[:117] + "..."
                parts.append(f"- {a['name']}: {desc}")
            parts.append("")  # blank line between categories

        return "\n".join(parts)

    # ========================================================================
    # MEMORY OPERATIONS
    # ========================================================================

    def save_memory(self, entry_id: str, phase: str, content: str,
                    entry_type: str = "task_end", task_id: str = None,
                    tags: List[str] = None, relevance_score: float = 0.8,
                    metadata: dict = None) -> None:
        """Save a memory entry as a Memory node in the graph."""
        self.writer.add_node("Memory", {
            "id": entry_id,
            "phase": phase,
            "task_id": task_id or "",
            "entry_type": entry_type,
            "content": content,
            "tags_csv": ",".join(tags) if tags else "",
            "relevance_score": relevance_score,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    def recall_memory(self, query: str, phase: str = None,
                      task_id: str = None, limit: int = 20) -> List[Dict]:
        """Recall memory entries using fulltext search + filters.

        Returns list of Memory node dicts sorted by relevance.
        Falls back to property-based query if fulltext search fails.
        """
        try:
            results = self.reader.fulltext_search("Memory", query, limit=limit)
        except Exception as e:
            logger.debug("Memory fulltext search failed: %s", e)
            results = []

        # Apply phase/task_id filters
        if phase:
            results = [r for r in results if r.get("phase") == phase]
        if task_id:
            results = [r for r in results if r.get("task_id") == task_id]

        # If fulltext returned nothing, try property-based query
        if not results:
            filters = {}
            if phase:
                filters["phase"] = phase
            if task_id:
                filters["task_id"] = task_id
            results = self.reader.get_nodes(
                "Memory", filters=filters if filters else None, limit=limit,
            )

        return results[:limit]

    def save_checkpoint(self, checkpoint_id: str, phase: int,
                        phase_name: str, summary: str,
                        key_decisions: List[str] = None,
                        artifacts: List[str] = None) -> None:
        """Save a phase checkpoint as a PhaseCheckpoint node."""
        self.writer.add_node("PhaseCheckpoint", {
            "id": checkpoint_id,
            "phase": phase,
            "phase_name": phase_name,
            "summary": summary,
            "key_decisions_csv": ",".join(key_decisions) if key_decisions else "",
            "artifacts_csv": ",".join(artifacts) if artifacts else "",
            "status": "valid",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    def invalidate_checkpoints_after(self, phase_num: int) -> int:
        """Mark all PhaseCheckpoint nodes after phase_num as invalidated."""
        cypher = (
            "MATCH (c:PhaseCheckpoint) WHERE c.phase > $phase_num "
            "SET c.status = 'invalidated' RETURN count(c)"
        )
        result = self.conn.query(cypher, {"phase_num": phase_num})
        count = result.result_set[0][0] if result.result_set else 0
        if count:
            logger.info(f"Invalidated {count} checkpoints after phase {phase_num}")
        return count

    def clear_memory_after_phase(self, phase_num: int) -> int:
        """Delete Memory nodes belonging to phases after phase_num.

        Parses phase string (e.g. '2-prd') to extract phase number.
        """
        # Memory nodes store phase as string like "2-prd"
        # We need to match all where the numeric prefix > phase_num
        # FalkorDB doesn't have great string parsing, so fetch and filter
        all_memory = self.reader.get_nodes("Memory")
        to_delete = []
        for m in all_memory:
            try:
                mem_phase = int(m.get("phase", "0").split("-")[0])
                if mem_phase > phase_num:
                    to_delete.append(m.get("id"))
            except (ValueError, AttributeError):
                continue

        for mid in to_delete:
            self.writer.delete_node("Memory", mid)

        if to_delete:
            logger.info(f"Cleared {len(to_delete)} memory nodes after phase {phase_num}")
        return len(to_delete)

    # ========================================================================
    # CONTEXT QUERIES
    # ========================================================================

    def query_prd_context(self, section: str, max_tokens: int = 8000) -> str:
        """Assemble focused context for a PRD section."""
        return self.reader.query_prd_context(section, max_tokens)

    def query_task_context(self, feature_id: Optional[str] = None) -> str:
        """Assemble context for task decomposition."""
        return self.reader.query_task_context(feature_id)

    def query_spec_context(self, task_id: int) -> str:
        """Assemble context for OpenSpec generation of a specific task."""
        return self.reader.query_spec_context(task_id)

    # ========================================================================
    # TASK MANAGEMENT OPERATIONS
    # ========================================================================

    def analyze_complexity(self, refine_with_llm: bool = False) -> dict:
        """Analyze task complexity across the graph."""
        return self.operations.analyze_complexity(refine_with_llm)

    def update_from(self, task_id: int, prompt: str) -> list:
        """Update a task from an LLM prompt response."""
        return self.operations.update_from(task_id, prompt)

    def research_save_to(self, task_id: int, research_content: str) -> str:
        """Save research content as a Finding linked to a Task."""
        return self.operations.research_save_to(task_id, research_content)

    def validate_dependencies(self) -> dict:
        """Validate the task dependency graph for cycles and orphans."""
        return self.operations.validate_dependencies()

    def fix_dependencies(self) -> dict:
        """Auto-fix dependency issues in the task graph."""
        return self.operations.fix_dependencies()

    def add_new_task(self, title: str, description: str,
                     depends_on: Optional[List[Any]] = None,
                     implements: Optional[List[Any]] = None) -> int:
        """Add a new task via the operations layer."""
        return self.operations.add_new_task(
            title, description, depends_on, implements,
        )

    # ========================================================================
    # EXPORT
    # ========================================================================

    def export_prd_md(self, output_path: Path) -> None:
        """Export the PRD as Markdown."""
        self.exporter.export_prd_md(output_path)

    def export_tasks_json(self, output_path: Path) -> None:
        """Export tasks as JSON."""
        self.exporter.export_tasks_json(output_path)

    def export_openspec(self, task_id: Any, output_path: Path) -> None:
        """Export an OpenSpec for a single task."""
        self.exporter.export_openspec(task_id, output_path)

    def export_needs_index(self, output_path: Path) -> None:
        """Export a needs-traceability index."""
        self.exporter.export_needs_index(output_path)

    # ========================================================================
    # LIFECYCLE
    # ========================================================================

    def delete_phase_data(self, phase_id: str) -> int:
        """Delete all nodes belonging to a specific phase."""
        return self.writer.delete_by_phase(phase_id)

    def ensure_schema(self) -> None:
        """Create all indexes defined in the ontology schema."""
        self.writer.ensure_indexes()
