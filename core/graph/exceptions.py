"""
ATOMIC CLAUDE - Graph Exception Hierarchy

Exception types for FalkorDB knowledge graph operations.
"""


class GraphException(Exception):
    """
    Base exception for all graph-related errors.

    All graph exceptions inherit from this base class.
    """

    def __init__(self, message: str, error_code: str = None, retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.retryable = retryable

    def to_dict(self):
        """Convert to dictionary representation."""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "retryable": self.retryable,
        }


class GraphUnavailableError(GraphException):
    """
    FalkorDB is not reachable or not configured.

    Examples:
    - Docker container not running
    - Connection refused
    - ATOMIC_GRAPH_ENABLED=false
    """

    def __init__(self, message: str = "FalkorDB unavailable"):
        super().__init__(message, "graph_unavailable", retryable=True)


class SchemaValidationError(GraphException):
    """
    Node or edge data fails ontology validation.

    Examples:
    - Unknown node label
    - Missing required property
    - Invalid property value
    """

    def __init__(self, message: str, label: str = None, field: str = None):
        super().__init__(message, "schema_validation", retryable=False)
        self.label = label
        self.field = field


class CycleDetectedError(GraphException):
    """
    Cycle detected in task dependency graph.

    Adding an edge would create a cycle in the DAG.
    """

    def __init__(self, message: str, cycle_path: list = None):
        super().__init__(message, "cycle_detected", retryable=False)
        self.cycle_path = cycle_path or []


class QueryError(GraphException):
    """
    Cypher query execution failed.

    Examples:
    - Syntax error in query
    - Constraint violation
    - Query timeout
    """

    def __init__(self, message: str, query: str = None, retryable: bool = False):
        super().__init__(message, "query_error", retryable=retryable)
        self.query = query


class NodeNotFoundError(GraphException):
    """
    Referenced node does not exist in the graph.
    """

    def __init__(self, label: str, node_id: str):
        super().__init__(
            f"{label} node with id '{node_id}' not found",
            "node_not_found",
            retryable=False,
        )
        self.label = label
        self.node_id = node_id
