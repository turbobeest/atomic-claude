"""Integration tests for core/graph/ with real FalkorDB.

Requires: docker compose up -d falkordb
Run with: pytest tests/integration/test_graph_falkordb.py -m integration
"""
import json
import os
import tempfile
import uuid

import pytest

# Set ATOMIC_GRAPH_ENABLED before imports
os.environ["ATOMIC_GRAPH_ENABLED"] = "true"

from core.graph import get_graph, GraphConnection, NodeLabel, RelType
from core.graph.connection import HAS_FALKORDB
from core.graph.schema import validate_node_properties


# Skip entire module if FalkorDB not available
pytestmark = pytest.mark.integration


def _falkordb_available():
    """Check if FalkorDB is reachable."""
    if not HAS_FALKORDB:
        return False
    try:
        from falkordb import FalkorDB
        client = FalkorDB(host="localhost", port=6379)
        client.connection.ping()
        return True
    except Exception:
        return False


if not _falkordb_available():
    pytest.skip("FalkorDB not available", allow_module_level=True)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def graph_name():
    return f"test-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="module")
def graph(graph_name):
    """Create a GraphManager connected to a test graph."""
    GraphConnection.reset()
    conn = GraphConnection.get(graph_name=graph_name)
    assert conn is not None, "Could not connect to FalkorDB"

    from core.graph.manager import GraphManager
    gm = GraphManager(conn, phase_id="test")
    gm.ensure_schema()
    yield gm

    # Cleanup
    conn.delete_graph()
    GraphConnection.reset()


# ---------------------------------------------------------------------------
# TestNodeCRUD
# ---------------------------------------------------------------------------

class TestNodeCRUD:
    """Basic node create / read / update / delete operations."""

    def test_create_source(self, graph):
        """Add a Source node, read it back, verify properties."""
        graph.add_source(id="src-crud-1", type="corpus", title="Test Corpus")

        node = graph.reader.get_node("Source", "src-crud-1")
        assert node is not None
        assert node["id"] == "src-crud-1"
        assert node["type"] == "corpus"
        assert node["title"] == "Test Corpus"

    def test_create_finding_with_defaults(self, graph):
        """Add Finding with minimal props, verify defaults (confidence, phase)."""
        graph.add_finding(
            id="find-crud-1",
            category="vision",
            title="Vision Finding",
            content="We need a dashboard",
        )

        node = graph.reader.get_node("Finding", "find-crud-1")
        assert node is not None
        assert node["category"] == "vision"
        assert node["title"] == "Vision Finding"
        # Schema defaults
        assert node.get("confidence") == 0.8
        # Phase comes from GraphManager phase_id
        assert node.get("phase") == "test"

    def test_update_task(self, graph):
        """Create Task, update status to 'done', read back."""
        graph.add_task(id=9000, title="CRUD Task", description="To be updated")

        graph.writer.update_node("Task", 9000, {"status": "done"})

        node = graph.reader.get_node("Task", 9000)
        assert node is not None
        assert node["status"] == "done"

    def test_delete_node(self, graph):
        """Create a Task, delete it, verify get_node returns None."""
        graph.add_task(id=9001, title="Ephemeral Task", description="Will be deleted")

        # Confirm it exists first
        assert graph.reader.get_node("Task", 9001) is not None

        deleted = graph.writer.delete_node("Task", 9001)
        assert deleted is True

        assert graph.reader.get_node("Task", 9001) is None


# ---------------------------------------------------------------------------
# TestEdges
# ---------------------------------------------------------------------------

class TestEdges:
    """Relationship creation and traversal."""

    def test_create_implements_edge(self, graph):
        """Create Task and Requirement, add IMPLEMENTS edge, verify neighbors."""
        graph.add_task(id=9100, title="Edge Task", description="Implements a req")
        graph.add_requirement(
            id="req-edge-1", type="functional",
            title="Edge Req", content="Must implement edges",
        )
        graph.link(
            "IMPLEMENTS", "Task", 9100, "Requirement", "req-edge-1",
        )

        neighbors = graph.reader.get_neighbors(
            "Task", 9100, rel_type="IMPLEMENTS", direction="out",
        )
        assert any(n.get("id") == "req-edge-1" for n in neighbors)

    def test_derived_from_with_properties(self, graph):
        """Create Finding and Source, link with confidence property."""
        graph.add_source(id="src-edge-1", type="interview", title="Edge Source")
        graph.add_finding(
            id="find-edge-1", category="technical",
            title="Edge Finding", content="Technical insight",
        )
        graph.link(
            "DERIVED_FROM", "Finding", "find-edge-1",
            "Source", "src-edge-1",
            confidence=0.95,
        )

        neighbors = graph.reader.get_neighbors(
            "Finding", "find-edge-1", rel_type="DERIVED_FROM", direction="out",
        )
        assert any(n.get("id") == "src-edge-1" for n in neighbors)

    def test_contains_edge(self, graph):
        """Create Feature and Requirement, add CONTAINS edge, verify direction."""
        graph.add_feature(id="feat-edge-1", title="Edge Feature")
        graph.add_requirement(
            id="req-edge-2", type="functional",
            title="Contained Req", content="Inside a feature",
        )
        graph.link(
            "CONTAINS", "Feature", "feat-edge-1",
            "Requirement", "req-edge-2",
        )

        # Outbound from Feature should include the Requirement
        out_neighbors = graph.reader.get_neighbors(
            "Feature", "feat-edge-1", rel_type="CONTAINS", direction="out",
        )
        assert any(n.get("id") == "req-edge-2" for n in out_neighbors)

        # Inbound to Requirement should include the Feature
        in_neighbors = graph.reader.get_neighbors(
            "Requirement", "req-edge-2", rel_type="CONTAINS", direction="in",
        )
        assert any(n.get("id") == "feat-edge-1" for n in in_neighbors)


# ---------------------------------------------------------------------------
# TestContextQueries
# ---------------------------------------------------------------------------

class TestContextQueries:
    """Context assembly methods used by LLM prompts."""

    def test_prd_context(self, graph):
        """Add Findings, Decisions, Requirements; call query_prd_context."""
        graph.add_finding(
            id="find-ctx-1", category="vision",
            title="Product Vision", content="Build an awesome tool",
        )
        graph.add_finding(
            id="find-ctx-2", category="technical",
            title="Tech Stack", content="Python + FalkorDB",
        )
        graph.add_decision(
            id="dec-ctx-1", title="Use FalkorDB",
            rationale="Graph model fits", status="accepted",
        )
        graph.add_requirement(
            id="req-ctx-1", type="functional",
            title="Graph Storage", content="Store nodes in graph",
            section="features",
        )

        context = graph.query_prd_context("features")
        assert isinstance(context, str)
        # The features section maps to categories technical + non_negotiable
        assert "Tech Stack" in context or "Python" in context

    def test_task_context(self, graph):
        """Add Feature, Requirements, CONTAINS edges; call query_task_context."""
        graph.add_feature(id="feat-ctx-1", title="Context Feature", description="For task ctx")
        graph.add_requirement(
            id="req-ctx-2", type="functional",
            title="Context Req", content="Must have context",
            feature_id="feat-ctx-1",
        )

        context = graph.query_task_context()
        assert isinstance(context, str)
        assert "Context Feature" in context
        assert "Context Req" in context

    def test_spec_context(self, graph):
        """Add Task, Requirement, IMPLEMENTS edge; call query_spec_context."""
        graph.add_task(
            id=9200, title="Spec Context Task", description="Task for spec ctx",
        )
        graph.add_requirement(
            id="req-ctx-3", type="functional",
            title="Spec Req", content="Required for spec",
        )
        graph.link(
            "IMPLEMENTS", "Task", 9200, "Requirement", "req-ctx-3",
        )

        context = graph.query_spec_context(9200)
        assert isinstance(context, str)
        assert "Spec Context Task" in context
        assert "Spec Req" in context


# ---------------------------------------------------------------------------
# TestTaskOperations
# ---------------------------------------------------------------------------

class TestTaskOperations:
    """Operations layer: complexity, dependencies, research binding."""

    def test_complexity_analysis(self, graph):
        """Add Tasks with varying requirements/dependencies, verify scores."""
        # Simple task - no requirements, no dependencies
        graph.add_task(id=9300, title="Simple Task", description="Nothing extra")

        # Medium task - has requirements
        graph.add_requirement(
            id="req-cplx-1", type="functional",
            title="Req A", content="Requirement A",
        )
        graph.add_requirement(
            id="req-cplx-2", type="functional",
            title="Req B", content="Requirement B",
        )
        graph.add_task(
            id=9301, title="Medium Task", description="Has reqs",
            requirements=["req-cplx-1", "req-cplx-2"],
        )

        # Complex task - has requirements + depends on medium task
        graph.add_requirement(
            id="req-cplx-3", type="functional",
            title="Req C", content="Requirement C",
        )
        graph.add_task(
            id=9302, title="Complex Task", description="Has reqs and deps",
            requirements=["req-cplx-3"],
            depends_on=[9301],
        )

        result = graph.analyze_complexity()
        assert "tasks" in result
        assert "avg_complexity" in result

        scores = {t["id"]: t["score"] for t in result["tasks"]}

        # Filter to our test tasks
        assert 9300 in scores
        assert 9301 in scores
        assert 9302 in scores

        # All scores within range 1-10
        for tid in [9300, 9301, 9302]:
            assert 1 <= scores[tid] <= 10, f"Task {tid} score out of range: {scores[tid]}"

        # Complex task should score higher than simple task
        assert scores[9302] > scores[9300]

    def test_dependency_validation_clean(self, graph):
        """Add Tasks with clean DAG (1->2->3); validate_dependencies returns valid."""
        graph.add_task(id=9310, title="DAG Root", description="No deps")
        graph.add_task(id=9311, title="DAG Mid", description="Depends on root",
                       depends_on=[9310])
        graph.add_task(id=9312, title="DAG Leaf", description="Depends on mid",
                       depends_on=[9311])

        # The graph may contain other tasks; cycles among 9310-9312 do not exist
        result = graph.validate_dependencies()
        assert isinstance(result, dict)
        assert "valid" in result
        assert "cycles" in result
        assert "orphans" in result

        # These specific tasks form no cycle; overall validity depends on entire graph
        # but at minimum, the cycle list should not include any of our three IDs
        for cycle in result["cycles"]:
            cycle_set = set(cycle)
            assert not {9310, 9311, 9312}.issubset(cycle_set), \
                "Our clean DAG tasks should not form a cycle"

    def test_cycle_detection(self, graph):
        """Add Tasks with a cycle (1->2->3->1); validate_dependencies should detect it."""
        graph.add_task(id=9320, title="Cycle A", description="Cyclic")
        graph.add_task(id=9321, title="Cycle B", description="Cyclic",
                       depends_on=[9320])
        graph.add_task(id=9322, title="Cycle C", description="Cyclic",
                       depends_on=[9321])
        # Close the cycle: 9320 depends on 9322
        graph.link(
            "TASK_DEPENDS_ON", "Task", 9320, "Task", 9322,
        )

        result = graph.validate_dependencies()
        assert result["valid"] is False
        assert len(result["cycles"]) > 0

    def test_add_new_task(self, graph):
        """Call add_new_task with a dependency, verify task and edge exist."""
        # Create a dependency target first
        graph.add_task(id=9330, title="Dep Target", description="Exists for dep")

        new_id = graph.add_new_task(
            "Dynamically Added", "Created via add_new_task",
            depends_on=[9330],
        )
        assert isinstance(new_id, int)
        assert new_id > 0

        # Verify the node was created
        node = graph.reader.get_node("Task", new_id)
        assert node is not None
        assert node["title"] == "Dynamically Added"
        assert node["status"] == "pending"

        # Verify dependency edge
        deps = graph.reader.get_neighbors(
            "Task", new_id, rel_type="TASK_DEPENDS_ON", direction="out",
        )
        assert any(d.get("id") == 9330 for d in deps)

    def test_research_save_to(self, graph):
        """Call research_save_to, verify Finding created and linked to Task."""
        graph.add_task(id=9340, title="Research Host", description="Gets research")

        finding_id = graph.research_save_to(9340, "Research findings about caching")

        assert isinstance(finding_id, str)
        assert finding_id.startswith("R-9340-")

        # Verify Finding node
        finding = graph.reader.get_node("Finding", finding_id)
        assert finding is not None
        assert finding["category"] == "research"
        assert "caching" in finding["content"]

        # Verify INFORMED_BY edge from Task to Finding
        neighbors = graph.reader.get_neighbors(
            "Task", 9340, rel_type="INFORMED_BY", direction="out",
        )
        assert any(n.get("id") == finding_id for n in neighbors)


# ---------------------------------------------------------------------------
# TestExport
# ---------------------------------------------------------------------------

class TestExport:
    """Export to JSON and Markdown formats."""

    def test_export_tasks_json(self, graph):
        """Add Tasks with dependencies, export to JSON, verify structure."""
        graph.add_task(id=9400, title="Export Root", description="Root for export")
        graph.add_task(id=9401, title="Export Child", description="Child for export",
                       depends_on=[9400])
        graph.add_task(id=9402, title="Export Grandchild", description="Grandchild",
                       depends_on=[9401])

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name

        try:
            graph.export_tasks_json(tmp_path)

            with open(tmp_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)

            assert "tasks" in data
            assert "metadata" in data
            assert data["metadata"]["generated_from"] == "graph"
            assert isinstance(data["tasks"], list)
            assert len(data["tasks"]) >= 3  # at least our three tasks

            # Find our export child task
            child = next(
                (t for t in data["tasks"] if t.get("id") == 9401), None,
            )
            assert child is not None
            assert 9400 in child["dependencies"]
        finally:
            os.unlink(tmp_path)

    def test_export_prd_md(self, graph):
        """Add Features and Requirements, export PRD markdown, verify structure."""
        graph.add_feature(id="feat-exp-1", title="Export Feature Alpha")
        graph.add_requirement(
            id="req-exp-1", type="functional",
            title="Export Req One", content="First export requirement",
            feature_id="feat-exp-1",
        )
        graph.add_requirement(
            id="req-exp-2", type="non_functional",
            title="Export NFR", content="Performance export requirement",
        )

        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            tmp_path = f.name

        try:
            graph.export_prd_md(tmp_path)

            with open(tmp_path, "r", encoding="utf-8") as fh:
                content = fh.read()

            assert isinstance(content, str)
            assert len(content) > 0

            # Verify expected markdown section headings
            assert "# Product Requirements Document" in content
            assert "## Features" in content
            assert "## Non-Functional Requirements" in content

            # Verify our data appears
            assert "Export Feature Alpha" in content
        finally:
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# TestTopologicalOrder
# ---------------------------------------------------------------------------

class TestTopologicalOrder:
    """Topological sorting of task dependency graph."""

    def test_topo_order(self, graph):
        """Add Tasks 1->2->3 and verify topological order."""
        graph.add_task(id=9500, title="Topo First", description="No deps")
        graph.add_task(id=9501, title="Topo Second", description="Depends on first",
                       depends_on=[9500])
        graph.add_task(id=9502, title="Topo Third", description="Depends on second",
                       depends_on=[9501])

        order = graph.reader.get_topological_order()
        assert isinstance(order, list)

        # Our three tasks should appear in the correct relative order
        # (other tasks may be interspersed from other test classes)
        positions = {}
        for idx, tid in enumerate(order):
            if tid in (9500, 9501, 9502):
                positions[tid] = idx

        # All three should be present in the topological order
        assert 9500 in positions
        assert 9501 in positions
        assert 9502 in positions

        # Verify ordering: 9500 before 9501 before 9502
        assert positions[9500] < positions[9501]
        assert positions[9501] < positions[9502]


# ---------------------------------------------------------------------------
# TestBulkOperations
# ---------------------------------------------------------------------------

class TestBulkOperations:
    """Bulk write operations."""

    def test_bulk_write(self, graph):
        """Execute bulk_write with multiple add_node operations, verify all created."""
        ops = [
            {
                "op": "add_node",
                "label": "Task",
                "properties": {
                    "id": 9600,
                    "title": "Bulk Task A",
                    "description": "First bulk task",
                },
            },
            {
                "op": "add_node",
                "label": "Task",
                "properties": {
                    "id": 9601,
                    "title": "Bulk Task B",
                    "description": "Second bulk task",
                },
            },
            {
                "op": "add_node",
                "label": "Task",
                "properties": {
                    "id": 9602,
                    "title": "Bulk Task C",
                    "description": "Third bulk task",
                },
            },
        ]

        count = graph.writer.bulk_write(ops)
        assert count == 3

        # Verify all nodes were created
        for tid in (9600, 9601, 9602):
            node = graph.reader.get_node("Task", tid)
            assert node is not None, f"Task {tid} not found after bulk_write"

        assert graph.reader.get_node("Task", 9600)["title"] == "Bulk Task A"
        assert graph.reader.get_node("Task", 9601)["title"] == "Bulk Task B"
        assert graph.reader.get_node("Task", 9602)["title"] == "Bulk Task C"
