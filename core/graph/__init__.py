"""ATOMIC CLAUDE - Knowledge Graph

FalkorDB-backed knowledge graph for SDLC pipeline phases."""

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
              port: int = None, graph_name: str = None) -> GraphManager:
    """
    Get a GraphManager instance. Raises GraphUnavailableError if FalkorDB is not running.

    This is the primary entry point for tasks and orchestrators.

    Usage:
        graph = get_graph(phase_id="2-prd")
        graph.add_finding(...)
    """
    conn = GraphConnection.get(host=host, port=port, graph_name=graph_name)
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
