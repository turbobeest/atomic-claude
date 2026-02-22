"""
ATOMIC CLAUDE - Graph Reader

Read and query operations for the FalkorDB knowledge graph.
Provides context assembly for LLM prompts and graph traversal.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class GraphReader:
    """
    Graph read operations optimized for LLM context assembly.
    """

    def __init__(self, connection):
        """
        Args:
            connection: GraphConnection instance
        """
        self.conn = connection

    # ========================================================================
    # NODE RETRIEVAL
    # ========================================================================

    def get_node(self, label: str, node_id: Any) -> Optional[Dict[str, Any]]:
        """
        Get a single node by label and id.

        Returns:
            Property dict or None if not found
        """
        id_prop = "task_id" if label == "Spec" else "id"
        cypher = f"MATCH (n:{label} {{{id_prop}: $nid}}) RETURN n"
        result = self.conn.query(cypher, {"nid": node_id})
        if result.result_set:
            return self._node_to_dict(result.result_set[0][0])
        return None

    def get_nodes(self, label: str, filters: Dict[str, Any] = None,
                  order_by: str = None, limit: int = None) -> List[Dict[str, Any]]:
        """
        Get nodes by label with optional filters.

        Args:
            label: Node label
            filters: Property filters (exact match)
            order_by: Property to sort by
            limit: Max results

        Returns:
            List of property dicts
        """
        params = {}
        where_clauses = []

        if filters:
            for i, (key, value) in enumerate(filters.items()):
                param_name = f"f{i}"
                where_clauses.append(f"n.{key} = ${param_name}")
                params[param_name] = value

        where_str = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        order_str = f" ORDER BY n.{order_by}" if order_by else ""
        limit_str = f" LIMIT {limit}" if limit else ""

        cypher = f"MATCH (n:{label}){where_str} RETURN n{order_str}{limit_str}"
        result = self.conn.query(cypher, params)
        return [self._node_to_dict(row[0]) for row in result.result_set]

    def count_nodes(self, label: str, filters: Dict[str, Any] = None) -> int:
        """Count nodes matching label and optional filters."""
        params = {}
        where_clauses = []

        if filters:
            for i, (key, value) in enumerate(filters.items()):
                param_name = f"f{i}"
                where_clauses.append(f"n.{key} = ${param_name}")
                params[param_name] = value

        where_str = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        cypher = f"MATCH (n:{label}){where_str} RETURN count(n)"
        result = self.conn.query(cypher, params)
        return result.result_set[0][0] if result.result_set else 0

    # ========================================================================
    # RELATIONSHIP QUERIES
    # ========================================================================

    def get_neighbors(self, label: str, node_id: Any,
                      rel_type: str = None,
                      direction: str = "out") -> List[Dict[str, Any]]:
        """
        Get nodes connected to a given node.

        Args:
            label: Source node label
            node_id: Source node id
            rel_type: Filter by relationship type (optional)
            direction: "out", "in", or "both"

        Returns:
            List of connected node property dicts
        """
        id_prop = "task_id" if label == "Spec" else "id"
        rel_pattern = f":{rel_type}" if rel_type else ""

        if direction == "out":
            cypher = (f"MATCH (n:{label} {{{id_prop}: $nid}})"
                      f"-[{rel_pattern}]->(m) RETURN m")
        elif direction == "in":
            cypher = (f"MATCH (n:{label} {{{id_prop}: $nid}})"
                      f"<-[{rel_pattern}]-(m) RETURN m")
        else:
            cypher = (f"MATCH (n:{label} {{{id_prop}: $nid}})"
                      f"-[{rel_pattern}]-(m) RETURN DISTINCT m")

        result = self.conn.query(cypher, {"nid": node_id})
        return [self._node_to_dict(row[0]) for row in result.result_set]

    def get_path(self, from_label: str, from_id: Any,
                 to_label: str, to_id: Any,
                 rel_types: List[str] = None,
                 max_depth: int = 10) -> List[Dict[str, Any]]:
        """
        Find shortest path between two nodes.

        Returns:
            List of node dicts along the path, or empty list if no path
        """
        from_id_prop = "task_id" if from_label == "Spec" else "id"
        to_id_prop = "task_id" if to_label == "Spec" else "id"

        if rel_types:
            rel_filter = "|".join(rel_types)
            rel_pattern = f":{rel_filter}"
        else:
            rel_pattern = ""

        cypher = (
            f"MATCH path = shortestPath("
            f"(a:{from_label} {{{from_id_prop}: $from_id}})"
            f"-[{rel_pattern}*1..{max_depth}]-"
            f"(b:{to_label} {{{to_id_prop}: $to_id}}))"
            f" RETURN nodes(path) AS nodes"
        )
        result = self.conn.query(cypher, {"from_id": from_id, "to_id": to_id})
        if result.result_set:
            return [self._node_to_dict(n) for n in result.result_set[0][0]]
        return []

    # ========================================================================
    # CONTEXT QUERIES (for LLM prompt assembly)
    # ========================================================================

    def query_prd_context(self, section: str, max_tokens: int = 8000) -> str:
        """
        Assemble focused context for a PRD section.

        Retrieves findings, decisions, and requirements relevant to the
        given section, formatted as text within the token budget.

        Args:
            section: PRD section name (e.g., "features", "nfr", "architecture")
            max_tokens: Approximate max output tokens (chars / 4 heuristic)

        Returns:
            Formatted context string
        """
        max_chars = max_tokens * 4
        parts = []

        # Get findings relevant to this section
        findings = self._query_section_findings(section)
        if findings:
            parts.append("## Relevant Findings\n")
            for f in findings:
                parts.append(f"- [{f.get('category', 'general')}] {f.get('title', '')}: "
                             f"{f.get('content', '')}\n")

        # Get decisions
        decisions = self._query_section_decisions(section)
        if decisions:
            parts.append("\n## Relevant Decisions\n")
            for d in decisions:
                status = d.get('status', 'proposed')
                parts.append(f"- [{status}] {d.get('title', '')}: "
                             f"{d.get('rationale', '')}\n")

        # Get existing requirements for cross-referencing
        requirements = self._query_section_requirements(section)
        if requirements:
            parts.append("\n## Existing Requirements\n")
            for r in requirements:
                parts.append(f"- [{r.get('type', '')}] {r.get('title', '')}: "
                             f"{r.get('content', '')}\n")

        # Get source summaries for provenance
        sources = self.get_nodes("Source", limit=20)
        if sources:
            parts.append("\n## Source Materials\n")
            for s in sources:
                parts.append(f"- [{s.get('type', '')}] {s.get('title', '')}\n")

        text = "".join(parts)
        if len(text) > max_chars:
            text = text[:max_chars] + "\n... [context truncated]"
        return text

    def query_task_context(self, feature_id: str = None) -> str:
        """
        Assemble context for task decomposition.

        Returns requirements grouped by feature, with decisions
        and dependencies.
        """
        parts = []

        if feature_id:
            # Specific feature
            cypher = (
                "MATCH (f:Feature {id: $fid})-[:CONTAINS]->(r:Requirement) "
                "OPTIONAL MATCH (r)-[:DEPENDS_ON]->(dep:Requirement) "
                "RETURN f, r, collect(dep) AS deps "
                "ORDER BY r.id"
            )
            result = self.conn.query(cypher, {"fid": feature_id})
        else:
            # All features
            cypher = (
                "MATCH (f:Feature)-[:CONTAINS]->(r:Requirement) "
                "OPTIONAL MATCH (r)-[:DEPENDS_ON]->(dep:Requirement) "
                "RETURN f, r, collect(dep) AS deps "
                "ORDER BY f.id, r.id"
            )
            result = self.conn.query(cypher)

        current_feature = None
        for row in result.result_set:
            feature = self._node_to_dict(row[0])
            req = self._node_to_dict(row[1])
            deps = [self._node_to_dict(d) for d in row[2]] if row[2] else []

            if feature.get('id') != current_feature:
                current_feature = feature.get('id')
                parts.append(f"\n## Feature: {feature.get('title', '')}\n")
                if feature.get('description'):
                    parts.append(f"{feature['description']}\n")

            priority = req.get('priority', 'medium')
            rfc = req.get('rfc2119_keyword', '')
            parts.append(f"- [{priority}] {rfc} {req.get('title', '')}: "
                         f"{req.get('content', '')}\n")
            if deps:
                dep_ids = [d.get('id', '?') for d in deps]
                parts.append(f"  Depends on: {', '.join(str(d) for d in dep_ids)}\n")

        # Include relevant decisions
        decisions = self.get_nodes("Decision", filters={"status": "accepted"})
        if decisions:
            parts.append("\n## Accepted Decisions\n")
            for d in decisions:
                parts.append(f"- {d.get('title', '')}: {d.get('rationale', '')}\n")

        return "".join(parts)

    def query_spec_context(self, task_id: int) -> str:
        """
        Assemble context for OpenSpec generation of a specific task.

        Returns: task details, implemented requirements, upstream
        interfaces, and relevant decisions.
        """
        parts = []

        # Task details
        task = self.get_node("Task", task_id)
        if task:
            parts.append(f"## Task {task_id}: {task.get('title', '')}\n")
            parts.append(f"{task.get('description', '')}\n")
            if task.get('acceptance_criteria'):
                parts.append(f"\nAcceptance Criteria: {task['acceptance_criteria']}\n")

        # Requirements this task implements
        cypher = (
            "MATCH (t:Task {id: $tid})-[:IMPLEMENTS]->(r:Requirement) "
            "RETURN r ORDER BY r.id"
        )
        result = self.conn.query(cypher, {"tid": task_id})
        if result.result_set:
            parts.append("\n## Requirements\n")
            for row in result.result_set:
                r = self._node_to_dict(row[0])
                parts.append(f"- [{r.get('type', '')}] {r.get('title', '')}: "
                             f"{r.get('content', '')}\n")
                if r.get('acceptance_criteria'):
                    parts.append(f"  AC: {r['acceptance_criteria']}\n")

        # Upstream task interfaces (specs already generated)
        cypher = (
            "MATCH (t:Task {id: $tid})-[:TASK_DEPENDS_ON]->(upstream:Task)"
            "-[:HAS_SPEC]->(s:Spec) "
            "RETURN upstream.id, upstream.title, s.interfaces_json"
        )
        result = self.conn.query(cypher, {"tid": task_id})
        if result.result_set:
            parts.append("\n## Upstream Interfaces\n")
            for row in result.result_set:
                up_id, up_title, ifaces = row[0], row[1], row[2]
                parts.append(f"### Task {up_id}: {up_title}\n")
                if ifaces:
                    try:
                        parsed = json.loads(ifaces) if isinstance(ifaces, str) else ifaces
                        parts.append(f"```json\n{json.dumps(parsed, indent=2)}\n```\n")
                    except (json.JSONDecodeError, TypeError):
                        parts.append(f"{ifaces}\n")

        # Research findings bound to this task
        cypher = (
            "MATCH (t:Task {id: $tid})-[:INFORMED_BY]->(f:Finding) "
            "RETURN f ORDER BY f.id"
        )
        result = self.conn.query(cypher, {"tid": task_id})
        if result.result_set:
            parts.append("\n## Research Findings\n")
            for row in result.result_set:
                f = self._node_to_dict(row[0])
                parts.append(f"- {f.get('title', '')}: {f.get('content', '')}\n")

        return "".join(parts)

    # ========================================================================
    # GRAPH ANALYSIS
    # ========================================================================

    def get_task_topology(self) -> List[Dict[str, Any]]:
        """
        Get tasks with dependency and requirement counts for complexity analysis.
        """
        cypher = """
            MATCH (t:Task)
            OPTIONAL MATCH (t)-[:IMPLEMENTS]->(r:Requirement)
            OPTIONAL MATCH (t)-[:TASK_DEPENDS_ON]->(dep:Task)
            OPTIONAL MATCH (r)-[:DEPENDS_ON]->(rdep:Requirement)
            OPTIONAL MATCH (r)-[:CONFLICTS_WITH]->(conflict:Requirement)
            RETURN t.id AS id, t.title AS title, t.category AS category,
                   count(DISTINCT r) AS req_count,
                   count(DISTINCT dep) AS dep_count,
                   count(DISTINCT rdep) AS transitive_deps,
                   count(DISTINCT conflict) AS conflict_count
            ORDER BY t.id
        """
        result = self.conn.query(cypher)
        return [
            {
                "id": row[0], "title": row[1], "category": row[2],
                "req_count": row[3], "dep_count": row[4],
                "transitive_deps": row[5], "conflict_count": row[6],
            }
            for row in result.result_set
        ]

    def get_topological_order(self) -> List[int]:
        """
        Return task IDs in topological order (respecting TASK_DEPENDS_ON).

        Tasks with no dependencies come first.
        """
        # Get all tasks and their dependencies
        cypher = """
            MATCH (t:Task)
            OPTIONAL MATCH (t)-[:TASK_DEPENDS_ON]->(dep:Task)
            RETURN t.id AS id, collect(dep.id) AS deps
            ORDER BY t.id
        """
        result = self.conn.query(cypher)

        # Build adjacency and perform Kahn's algorithm
        in_degree = {}
        graph = {}
        all_ids = []

        for row in result.result_set:
            tid = row[0]
            deps = [d for d in row[1] if d is not None]
            all_ids.append(tid)
            in_degree[tid] = len(deps)
            graph[tid] = deps

        # Reverse graph for topological sort
        reverse_graph = {tid: [] for tid in all_ids}
        for tid, deps in graph.items():
            for dep in deps:
                if dep in reverse_graph:
                    reverse_graph[dep].append(tid)

        # Kahn's algorithm
        queue = [tid for tid in all_ids if in_degree[tid] == 0]
        order = []
        while queue:
            queue.sort()  # Stable ordering by ID
            node = queue.pop(0)
            order.append(node)
            for neighbor in reverse_graph.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return order

    def detect_cycles(self) -> List[List[Any]]:
        """Detect cycles in the task dependency graph."""
        cypher = """
            MATCH path = (t:Task)-[:TASK_DEPENDS_ON*2..20]->(t)
            RETURN [node IN nodes(path) | node.id] AS cycle
            LIMIT 10
        """
        result = self.conn.query(cypher)
        return [row[0] for row in result.result_set]

    def find_orphan_tasks(self) -> List[int]:
        """Find tasks with no incoming or outgoing TASK_DEPENDS_ON edges."""
        cypher = """
            MATCH (t:Task)
            WHERE NOT EXISTS { MATCH (t)-[:TASK_DEPENDS_ON]->() }
              AND NOT EXISTS { MATCH ()-[:TASK_DEPENDS_ON]->(t) }
            RETURN t.id
            ORDER BY t.id
        """
        result = self.conn.query(cypher)
        return [row[0] for row in result.result_set]

    def fulltext_search(self, label: str, query_text: str,
                        limit: int = 10) -> List[Dict[str, Any]]:
        """
        Full-text search across node properties.

        Args:
            label: Node label to search
            query_text: Search text
            limit: Max results
        """
        cypher = (
            f"CALL db.idx.fulltext.queryNodes('{label}', $query) "
            f"YIELD node RETURN node LIMIT {limit}"
        )
        result = self.conn.query(cypher, {"query": query_text})
        return [self._node_to_dict(row[0]) for row in result.result_set]

    # ========================================================================
    # HELPERS
    # ========================================================================

    def _query_section_findings(self, section: str) -> List[Dict[str, Any]]:
        """Get findings relevant to a PRD section."""
        # Map section names to finding categories
        section_category_map = {
            "vision": ["vision", "impact"],
            "audience": ["audience"],
            "features": ["technical", "non_negotiable"],
            "nfr": ["constraint", "non_negotiable"],
            "architecture": ["technical"],
            "constraints": ["constraint"],
            "open_questions": ["open_question"],
        }
        categories = section_category_map.get(section.lower(), [])
        if not categories:
            # Return all findings if section not mapped
            return self.get_nodes("Finding", limit=30)

        results = []
        for cat in categories:
            results.extend(self.get_nodes("Finding", filters={"category": cat}))
        return results

    def _query_section_decisions(self, section: str) -> List[Dict[str, Any]]:
        """Get accepted decisions."""
        return self.get_nodes("Decision", filters={"status": "accepted"})

    def _query_section_requirements(self, section: str) -> List[Dict[str, Any]]:
        """Get requirements for a given section."""
        return self.get_nodes("Requirement", filters={"section": section}, limit=50)

    @staticmethod
    def _node_to_dict(node) -> Dict[str, Any]:
        """Convert a FalkorDB node to a plain dict."""
        if node is None:
            return {}
        if isinstance(node, dict):
            return node
        # FalkorDB Node object has .properties
        if hasattr(node, 'properties'):
            return dict(node.properties)
        return {}
