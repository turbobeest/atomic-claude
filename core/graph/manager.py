"""ATOMIC CLAUDE - Graph Manager

High-level graph operations for pipeline tasks.
This is the primary interface used by phase orchestrators."""

import logging
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
