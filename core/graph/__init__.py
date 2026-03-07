"""ATOMIC CLAUDE - Knowledge Graph

FalkorDB-backed knowledge graph for SDLC pipeline phases.

Two graphs:
  - 'atomic-claude': Pipeline state (sources, findings, requirements, tasks, etc.)
  - 'atomic-audits': Audit catalog (2,186 audit definitions for phase audit tasks)
"""

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
from .audit_loader import (
    get_audit_graph,
    load_audit_catalog,
    query_audits,
    query_audits_for_task,
    get_audit_stats,
)
from .context_injector import (
    build_graph_context,
    set_active_graph_context,
    get_active_graph_context,
)
from .validator import validate_graph_for_phase


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
    "get_audit_graph",
    "load_audit_catalog",
    "query_audits",
    "query_audits_for_task",
    "get_audit_stats",
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
    # Context injector
    "build_graph_context",
    "set_active_graph_context",
    "get_active_graph_context",
    # Validator
    "validate_graph_for_phase",
]
