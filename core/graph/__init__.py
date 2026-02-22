"""ATOMIC CLAUDE - Knowledge Graph

FalkorDB-backed knowledge graph for SDLC pipeline phases."""

from typing import Optional

from .connection import GraphConnection
from .manager import GraphManager
from .schema import NodeLabel, RelType
from .exceptions import (
    GraphException,
    GraphUnavailableError,
    SchemaValidationError,
    CycleDetectedError,
    QueryError,
    NodeNotFoundError,
)


def get_graph(phase_id: str = "unknown", host: str = None,
              port: int = None, graph_name: str = None) -> Optional[GraphManager]:
    """
    Get a GraphManager instance, or None if graph is disabled/unavailable.

    This is the primary entry point for tasks and orchestrators.

    Usage:
        graph = get_graph(phase_id="2-prd")
        if graph:
            graph.add_finding(...)
    """
    conn = GraphConnection.get(host=host, port=port, graph_name=graph_name)
    if conn is None:
        return None
    return GraphManager(conn, phase_id)


__all__ = [
    "get_graph",
    "GraphConnection",
    "GraphManager",
    "NodeLabel",
    "RelType",
    "GraphException",
    "GraphUnavailableError",
    "SchemaValidationError",
    "CycleDetectedError",
    "QueryError",
    "NodeNotFoundError",
]
