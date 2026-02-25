"""
ATOMIC CLAUDE - Graph Writer

Low-level write operations for the FalkorDB knowledge graph.
Handles node creation, edge creation, updates, and bulk operations.
"""

import logging
from typing import Any, Dict, List, Optional

from .exceptions import SchemaValidationError
from .schema import (
    PROPERTY_DEFAULTS,
    validate_node_properties, validate_relationship,
)

logger = logging.getLogger(__name__)

# Mapping of node labels to their primary ID property name.
# Most node types use "id"; Spec nodes use "task_id".
_NODE_ID_PROPERTY = {
    "Spec": "task_id",
}


def _id_prop(label: str) -> str:
    """Return the ID property name for a given node label."""
    return _NODE_ID_PROPERTY.get(label, "id")


class GraphWriter:
    """
    Low-level graph write operations.

    All writes go through validation before execution.
    """

    def __init__(self, connection):
        """
        Args:
            connection: GraphConnection instance
        """
        self.conn = connection

    def add_node(self, label: str, properties: Dict[str, Any]) -> None:
        """
        Create a node with the given label and properties.

        Applies defaults for missing optional properties, validates
        against the ontology schema, then executes the CREATE.

        Args:
            label: Node label (e.g., "Source", "Finding")
            properties: Property dict

        Raises:
            SchemaValidationError: If properties fail validation
            QueryError: If Cypher execution fails
        """
        label_str = label if isinstance(label, str) else label.value

        # Apply defaults
        defaults = PROPERTY_DEFAULTS.get(label_str, {})
        merged = {**defaults, **properties}

        # Validate
        error = validate_node_properties(label_str, merged)
        if error:
            raise SchemaValidationError(error, label=label_str)

        # Build parameterized CREATE
        param_pairs = []
        params = {}
        for i, (key, value) in enumerate(merged.items()):
            param_name = f"p{i}"
            param_pairs.append(f"{key}: ${param_name}")
            params[param_name] = value

        props_str = ", ".join(param_pairs)
        cypher = f"CREATE (:{label_str} {{{props_str}}})"

        self.conn.query(cypher, params)
        logger.debug("Created %s node: id=%s", label_str, merged.get('id'))

    def update_node(self, label: str, node_id: Any,
                    updates: Dict[str, Any]) -> bool:
        """
        Update properties on an existing node.

        Args:
            label: Node label
            node_id: Value of the 'id' property
            updates: Properties to update

        Returns:
            True if node was found and updated

        Raises:
            QueryError: If Cypher execution fails
        """
        label_str = label if isinstance(label, str) else label.value

        if not updates:
            return False

        set_clauses = []
        params = {"node_id": node_id}
        for i, (key, value) in enumerate(updates.items()):
            param_name = f"u{i}"
            set_clauses.append(f"n.{key} = ${param_name}")
            params[param_name] = value

        set_str = ", ".join(set_clauses)
        cypher = f"MATCH (n:{label_str} {{id: $node_id}}) SET {set_str} RETURN n"

        result = self.conn.query(cypher, params)
        updated = len(result.result_set) > 0
        if updated:
            logger.debug("Updated %s node: id=%s", label_str, node_id)
        return updated

    def delete_node(self, label: str, node_id: Any) -> bool:
        """
        Delete a node and all its relationships.

        Args:
            label: Node label
            node_id: Value of the 'id' property

        Returns:
            True if node was found and deleted
        """
        label_str = label if isinstance(label, str) else label.value
        cypher = f"MATCH (n:{label_str} {{id: $node_id}}) DETACH DELETE n RETURN count(n) AS c"
        result = self.conn.query(cypher, {"node_id": node_id})
        deleted = result.result_set[0][0] > 0 if result.result_set else False
        if deleted:
            logger.debug("Deleted %s node: id=%s", label_str, node_id)
        return deleted

    def add_edge(self, rel_type: str, from_label: str, from_id: Any,
                 to_label: str, to_id: Any,
                 properties: Dict[str, Any] = None) -> None:
        """
        Create a relationship between two nodes.

        Args:
            rel_type: Relationship type (e.g., "DERIVED_FROM")
            from_label: Source node label
            from_id: Source node id
            to_label: Target node label
            to_id: Target node id
            properties: Optional relationship properties

        Raises:
            SchemaValidationError: If relationship type is invalid
            QueryError: If Cypher execution fails
        """
        rel_str = rel_type if isinstance(rel_type, str) else rel_type.value
        from_str = from_label if isinstance(from_label, str) else from_label.value
        to_str = to_label if isinstance(to_label, str) else to_label.value

        # Validate relationship
        error = validate_relationship(rel_str, from_str, to_str)
        if error:
            raise SchemaValidationError(error)

        params = {"from_id": from_id, "to_id": to_id}

        if properties:
            prop_pairs = []
            for i, (key, value) in enumerate(properties.items()):
                param_name = f"rp{i}"
                prop_pairs.append(f"{key}: ${param_name}")
                params[param_name] = value
            props_str = " {" + ", ".join(prop_pairs) + "}"
        else:
            props_str = ""

        # Look up the ID property for each node label from the mapping
        from_id_prop = _id_prop(from_str)
        to_id_prop = _id_prop(to_str)

        cypher = (
            f"MATCH (a:{from_str} {{{from_id_prop}: $from_id}}), "
            f"(b:{to_str} {{{to_id_prop}: $to_id}}) "
            f"CREATE (a)-[:{rel_str}{props_str}]->(b)"
        )

        self.conn.query(cypher, params)
        logger.debug("Created %s: %s(%s) -> %s(%s)", rel_str, from_str, from_id, to_str, to_id)

    def delete_edge(self, rel_type: str, from_label: str, from_id: Any,
                    to_label: str, to_id: Any) -> bool:
        """
        Delete a specific relationship.

        Returns:
            True if the edge was found and deleted
        """
        rel_str = rel_type if isinstance(rel_type, str) else rel_type.value
        from_str = from_label if isinstance(from_label, str) else from_label.value
        to_str = to_label if isinstance(to_label, str) else to_label.value

        from_id_prop = _id_prop(from_str)
        to_id_prop = _id_prop(to_str)

        cypher = (
            f"MATCH (a:{from_str} {{{from_id_prop}: $from_id}})"
            f"-[r:{rel_str}]->"
            f"(b:{to_str} {{{to_id_prop}: $to_id}}) "
            f"DELETE r RETURN count(r) AS c"
        )
        result = self.conn.query(cypher, {"from_id": from_id, "to_id": to_id})
        return result.result_set[0][0] > 0 if result.result_set else False

    def bulk_write(self, operations: List[Dict[str, Any]]) -> int:
        """
        Execute multiple write operations in sequence.

        Each operation dict:
            {"op": "add_node", "label": "Finding", "properties": {...}}
            {"op": "add_edge", "rel_type": "DERIVED_FROM", "from_label": ..., ...}
            {"op": "update_node", "label": "Task", "node_id": 1, "updates": {...}}

        Args:
            operations: List of operation dicts

        Returns:
            Number of operations successfully executed
        """
        count = 0
        for op in operations:
            op_type = op.get("op")
            try:
                if op_type == "add_node":
                    self.add_node(op["label"], op["properties"])
                elif op_type == "add_edge":
                    self.add_edge(
                        op["rel_type"], op["from_label"], op["from_id"],
                        op["to_label"], op["to_id"],
                        op.get("properties"),
                    )
                elif op_type == "update_node":
                    self.update_node(op["label"], op["node_id"], op["updates"])
                elif op_type == "delete_node":
                    self.delete_node(op["label"], op["node_id"])
                else:
                    logger.warning("Unknown bulk operation: %s", op_type)
                    continue
                count += 1
            except Exception as e:
                logger.error("Bulk op failed (%s): %s", op_type, e)
                # Continue with remaining operations
        return count

    def delete_by_phase(self, phase: str) -> int:
        """
        Delete all nodes (and their edges) that belong to a specific phase.

        Args:
            phase: Phase identifier (e.g., "1-discovery", "2-prd")

        Returns:
            Number of nodes deleted
        """
        # Delete nodes with phase property matching
        cypher = (
            "MATCH (n) WHERE n.phase = $phase "
            "WITH n, count(n) AS c "
            "DETACH DELETE n "
            "RETURN sum(c) AS deleted"
        )
        result = self.conn.query(cypher, {"phase": phase})
        deleted = result.result_set[0][0] if result.result_set else 0
        logger.info("Deleted %d nodes for phase '%s'", deleted, phase)
        return deleted

    def ensure_indexes(self) -> None:
        """Create all indexes defined in the schema."""
        from .schema import INDEX_DEFINITIONS, FULLTEXT_INDEX_DEFINITIONS

        for label, prop in INDEX_DEFINITIONS:
            try:
                cypher = f"CREATE INDEX FOR (n:{label}) ON (n.{prop})"
                self.conn.query(cypher)
            except Exception as e:
                # Index may already exist
                if "already indexed" not in str(e).lower():
                    logger.debug("Index creation note for %s.%s: %s", label, prop, e)

        for label, fields in FULLTEXT_INDEX_DEFINITIONS:
            try:
                fields_str = ", ".join(f"'{f}'" for f in fields)
                cypher = f"CALL db.idx.fulltext.createNodeIndex('{label}', {fields_str})"
                self.conn.query(cypher)
            except Exception as e:
                if "already indexed" not in str(e).lower():
                    logger.debug("Fulltext index note for %s: %s", label, e)
