"""
ATOMIC CLAUDE - FalkorDB Connection Management

Singleton connection to FalkorDB with health check, auto-reconnect,
and graceful degradation.
"""

import os
import logging
import threading
from typing import Optional, Any, Dict

from .exceptions import GraphUnavailableError, QueryError

logger = logging.getLogger(__name__)

# Guard import — falkordb is required
try:
    from falkordb import FalkorDB
    HAS_FALKORDB = True
except ImportError:
    HAS_FALKORDB = False
    FalkorDB = None


class GraphConnection:
    """
    Singleton FalkorDB connection with health check and auto-reconnect.

    Usage:
        conn = GraphConnection.get()
        result = conn.query("MATCH (n) RETURN n LIMIT 1")
    """

    _instance: Optional['GraphConnection'] = None
    _lock = threading.Lock()

    def __init__(self, host: str = "localhost", port: int = 6379,
                 graph_name: str = "atomic-claude"):
        self._host = host
        self._port = port
        self._graph_name = graph_name
        self._client: Any = None  # FalkorDB instance
        self._graph: Any = None   # Graph handle
        self._connected = False

    @classmethod
    def get(cls, host: str = None, port: int = None,
            graph_name: str = None) -> 'GraphConnection':
        """
        Get or create singleton connection.

        Reads from environment if args not provided:
        - ATOMIC_GRAPH_HOST (default: localhost)
        - ATOMIC_GRAPH_PORT (default: 6380)
        - ATOMIC_GRAPH_NAME (default: atomic-claude)

        Raises:
            GraphUnavailableError: If falkordb not installed or connection fails
        """
        if not HAS_FALKORDB:
            raise GraphUnavailableError(
                "falkordb package not installed. pip install falkordb"
            )

        with cls._lock:
            if cls._instance is not None and cls._instance._connected:
                return cls._instance

            _host = host or os.environ.get("ATOMIC_GRAPH_HOST", "localhost")
            _port = port or int(os.environ.get("ATOMIC_GRAPH_PORT", "6380"))
            _name = graph_name or os.environ.get("ATOMIC_GRAPH_NAME", "atomic-claude")

            instance = cls(_host, _port, _name)
            try:
                instance._connect()
                cls._instance = instance
                return instance
            except Exception as e:
                raise GraphUnavailableError(
                    f"FalkorDB unavailable at {_host}:{_port}: {e}"
                )

    @classmethod
    def reset(cls):
        """Reset singleton (for testing)."""
        with cls._lock:
            if cls._instance is not None:
                try:
                    cls._instance.close()
                except Exception as e:
                    logger.debug("Error closing graph connection during reset: %s", e)
                cls._instance = None

    def _connect(self):
        """Establish connection to FalkorDB."""
        self._client = FalkorDB(host=self._host, port=self._port)
        self._graph = self._client.select_graph(self._graph_name)
        # Verify connection with ping
        if not self.health_check():
            raise GraphUnavailableError(
                f"FalkorDB at {self._host}:{self._port} not responding"
            )
        self._connected = True
        logger.info("Connected to FalkorDB graph '%s' at %s:%s",
                     self._graph_name, self._host, self._port)

    def health_check(self) -> bool:
        """
        Check if FalkorDB is reachable.

        Returns:
            True if connected and responding, False otherwise
        """
        if self._client is None:
            return False
        try:
            # FalkorDB uses Redis protocol; ping tests connectivity
            self._client.connection.ping()
            return True
        except Exception as e:
            logger.debug("FalkorDB health check ping failed: %s", e)
            self._connected = False
            return False

    def query(self, cypher: str, params: Dict[str, Any] = None) -> Any:
        """
        Execute a Cypher query with error handling.

        Args:
            cypher: Cypher query string
            params: Query parameters

        Returns:
            FalkorDB QueryResult

        Raises:
            GraphUnavailableError: If not connected
            QueryError: If query execution fails
        """
        if not self._connected or self._graph is None:
            # Try reconnect once
            try:
                self._connect()
            except Exception as e:
                logger.debug("FalkorDB reconnect failed: %s", e)
                raise GraphUnavailableError()

        try:
            if params:
                return self._graph.query(cypher, params)
            return self._graph.query(cypher)
        except Exception as e:
            error_msg = str(e)
            # Check if connection lost
            if "connection" in error_msg.lower() or "refused" in error_msg.lower():
                self._connected = False
                raise GraphUnavailableError(f"Lost connection to FalkorDB: {error_msg}")
            raise QueryError(error_msg, query=cypher)

    def select_graph(self, name: str) -> 'GraphConnection':
        """
        Switch to a different named graph (multi-tenancy).

        Args:
            name: Graph name

        Returns:
            self (for chaining)
        """
        if self._client is None:
            raise GraphUnavailableError()
        self._graph_name = name
        self._graph = self._client.select_graph(name)
        return self

    def delete_graph(self):
        """Delete the current graph entirely. Use with caution."""
        if self._graph is not None:
            try:
                self._graph.delete()
            except Exception as e:
                logger.warning("Failed to delete graph '%s': %s", self._graph_name, e)

    def close(self):
        """Close the connection and release the underlying Redis client."""
        self._connected = False
        self._graph = None
        if self._client is not None:
            try:
                self._client.connection.close()
            except Exception as e:
                logger.debug("Error closing FalkorDB client connection: %s", e)
        self._client = None

    @property
    def graph_name(self) -> str:
        """Current graph name."""
        return self._graph_name

    @property
    def connected(self) -> bool:
        """Whether currently connected."""
        return self._connected

    def __repr__(self):
        status = "connected" if self._connected else "disconnected"
        return f"GraphConnection({self._host}:{self._port}/{self._graph_name} [{status}])"
