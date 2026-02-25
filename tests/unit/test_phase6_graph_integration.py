"""Tests for Phase 6 graph integration -- ReviewFinding nodes and code review."""

import pytest
from unittest.mock import MagicMock, patch, call

from core.graph.schema import (
    NodeLabel, RelType, REQUIRED_PROPERTIES, VALID_VALUES, VALID_RELATIONSHIPS,
)
from core.graph.manager import GraphManager


# Reuse the mock pattern from test_graph_memory.py / test_phase5_graph_integration.py
class MockQueryResult:
    def __init__(self, rows=None):
        self.result_set = rows or []


@pytest.fixture
def mock_conn():
    conn = MagicMock()
    conn.query.return_value = MockQueryResult()
    return conn


@pytest.fixture
def manager(mock_conn):
    return GraphManager(mock_conn, phase_id="6-code-review")


def _make_node(props):
    """Create a mock FalkorDB node with .properties dict."""
    node = MagicMock()
    node.properties = props
    return node


# ============================================================================
# TestReviewFindingSchema
# ============================================================================

@pytest.mark.unit
class TestReviewFindingSchema:
    """Tests for the ReviewFinding schema definition in core/graph/schema.py."""

    def test_review_finding_in_node_labels(self):
        """REVIEW_FINDING exists as a NodeLabel enum member."""
        assert hasattr(NodeLabel, "REVIEW_FINDING")
        assert NodeLabel.REVIEW_FINDING.value == "ReviewFinding"

    def test_review_finding_required_properties(self):
        """ReviewFinding requires id, severity, category, description."""
        required = REQUIRED_PROPERTIES.get(NodeLabel.REVIEW_FINDING)
        assert required is not None, "ReviewFinding missing from REQUIRED_PROPERTIES"
        assert "id" in required
        assert "severity" in required
        assert "category" in required
        assert "description" in required

    def test_review_finding_valid_values(self):
        """ReviewFinding has valid values for severity, category, status, review_dimension."""
        valid = VALID_VALUES.get(NodeLabel.REVIEW_FINDING)
        assert valid is not None, "ReviewFinding missing from VALID_VALUES"

        # Severity values
        assert "severity" in valid
        assert valid["severity"] == {"critical", "major", "minor", "suggestion"}

        # Category values
        assert "category" in valid
        expected_categories = {
            "logic", "error_handling", "security", "code_quality",
            "layer_separation", "dependency", "pattern", "module_boundary", "coupling",
            "algorithm", "memory", "io", "caching", "concurrency",
            "api_docs", "comments", "types", "examples", "accuracy",
        }
        assert valid["category"] == expected_categories

        # Status values
        assert "status" in valid
        assert valid["status"] == {"open", "resolved", "wont_fix", "deferred"}

        # Review dimension values
        assert "review_dimension" in valid
        assert valid["review_dimension"] == {
            "deep_code", "architecture", "performance", "documentation",
        }

    def test_review_of_and_violates_relationships(self):
        """REVIEW_OF and VIOLATES are in RelType and VALID_RELATIONSHIPS."""
        # RelType enum members
        assert hasattr(RelType, "REVIEW_OF")
        assert RelType.REVIEW_OF.value == "REVIEW_OF"
        assert hasattr(RelType, "VIOLATES")
        assert RelType.VIOLATES.value == "VIOLATES"

        # VALID_RELATIONSHIPS entries
        assert RelType.REVIEW_OF in VALID_RELATIONSHIPS
        review_of_from, review_of_to = VALID_RELATIONSHIPS[RelType.REVIEW_OF]
        assert NodeLabel.REVIEW_FINDING in review_of_from
        assert NodeLabel.TASK in review_of_to

        assert RelType.VIOLATES in VALID_RELATIONSHIPS
        violates_from, violates_to = VALID_RELATIONSHIPS[RelType.VIOLATES]
        assert NodeLabel.REVIEW_FINDING in violates_from
        assert NodeLabel.REQUIREMENT in violates_to


# ============================================================================
# TestAddReviewFinding
# ============================================================================

@pytest.mark.unit
class TestAddReviewFinding:
    """Tests for GraphManager.add_review_finding()."""

    def test_add_basic_finding(self, manager):
        """add_review_finding creates a ReviewFinding node with correct properties."""
        manager.writer.add_node = MagicMock()
        manager.writer.add_edge = MagicMock()

        manager.add_review_finding(
            id="rf-001",
            severity="major",
            category="logic",
            description="Off-by-one in loop boundary",
            review_dimension="deep_code",
        )

        manager.writer.add_node.assert_called_once()
        call_args = manager.writer.add_node.call_args
        label = call_args[0][0]
        props = call_args[0][1]

        assert label == "ReviewFinding"
        assert props["id"] == "rf-001"
        assert props["severity"] == "major"
        assert props["category"] == "logic"
        assert props["description"] == "Off-by-one in loop boundary"
        assert props["review_dimension"] == "deep_code"
        assert props["phase"] == "6-code-review"

        # No edges should be created without task_id or requirement_id
        manager.writer.add_edge.assert_not_called()

    def test_add_finding_with_file_and_line(self, manager):
        """File and line number appear in node properties when provided."""
        manager.writer.add_node = MagicMock()
        manager.writer.add_edge = MagicMock()

        manager.add_review_finding(
            id="rf-002",
            severity="minor",
            category="code_quality",
            description="Unclear variable name",
            review_dimension="deep_code",
            file="src/parser.py",
            line=42,
        )

        props = manager.writer.add_node.call_args[0][1]
        assert props["file"] == "src/parser.py"
        assert props["line"] == 42

    def test_add_finding_with_task_link(self, manager):
        """Providing task_id creates a REVIEW_OF edge to the Task."""
        manager.writer.add_node = MagicMock()
        manager.writer.add_edge = MagicMock()

        manager.add_review_finding(
            id="rf-003",
            severity="critical",
            category="security",
            description="SQL injection via unsanitized input",
            review_dimension="deep_code",
            task_id=7,
        )

        manager.writer.add_edge.assert_called_once_with(
            "REVIEW_OF", "ReviewFinding", "rf-003", "Task", 7,
        )

    def test_add_finding_with_requirement_link(self, manager):
        """Providing requirement_id creates a VIOLATES edge to the Requirement."""
        manager.writer.add_node = MagicMock()
        manager.writer.add_edge = MagicMock()

        manager.add_review_finding(
            id="rf-004",
            severity="major",
            category="error_handling",
            description="Missing error handling violates REQ-12",
            review_dimension="deep_code",
            requirement_id="REQ-12",
        )

        # Should create VIOLATES edge (no REVIEW_OF since no task_id)
        manager.writer.add_edge.assert_called_once_with(
            "VIOLATES", "ReviewFinding", "rf-004", "Requirement", "REQ-12",
        )


# ============================================================================
# TestGetReviewSummary
# ============================================================================

@pytest.mark.unit
class TestGetReviewSummary:
    """Tests for GraphManager.get_review_summary()."""

    def test_summary_with_findings(self, manager, mock_conn):
        """Returns severity-to-count dict from Cypher aggregation rows."""
        mock_conn.query.return_value = MockQueryResult([
            ["critical", 2],
            ["major", 5],
            ["minor", 8],
            ["suggestion", 3],
        ])

        summary = manager.get_review_summary()

        assert summary == {
            "critical": 2,
            "major": 5,
            "minor": 8,
            "suggestion": 3,
        }
        # Verify the Cypher query was issued
        cypher = mock_conn.query.call_args[0][0]
        assert "ReviewFinding" in cypher
        assert "severity" in cypher
        assert "count" in cypher

    def test_summary_empty(self, manager, mock_conn):
        """Returns all zeros when no ReviewFinding nodes exist."""
        mock_conn.query.return_value = MockQueryResult([])

        summary = manager.get_review_summary()

        assert summary == {
            "critical": 0,
            "major": 0,
            "minor": 0,
            "suggestion": 0,
        }


# ============================================================================
# TestGetUnresolvedFindings
# ============================================================================

@pytest.mark.unit
class TestGetUnresolvedFindings:
    """Tests for GraphManager.get_unresolved_findings()."""

    def test_unresolved_default(self, manager):
        """Default call passes status='open' filter to reader.get_nodes."""
        mock_findings = [
            {"id": "rf-001", "severity": "major", "status": "open"},
            {"id": "rf-002", "severity": "minor", "status": "open"},
        ]
        manager.reader.get_nodes = MagicMock(return_value=mock_findings)

        results = manager.get_unresolved_findings()

        manager.reader.get_nodes.assert_called_once_with(
            "ReviewFinding", filters={"status": "open"},
        )
        assert len(results) == 2
        assert results[0]["id"] == "rf-001"

    def test_unresolved_with_filters(self, manager):
        """Severity and review_dimension filters are passed through."""
        mock_findings = [
            {"id": "rf-010", "severity": "critical", "status": "open",
             "review_dimension": "architecture"},
        ]
        manager.reader.get_nodes = MagicMock(return_value=mock_findings)

        results = manager.get_unresolved_findings(
            severity="critical",
            review_dimension="architecture",
        )

        manager.reader.get_nodes.assert_called_once_with(
            "ReviewFinding",
            filters={
                "status": "open",
                "severity": "critical",
                "review_dimension": "architecture",
            },
        )
        assert len(results) == 1
        assert results[0]["severity"] == "critical"


# ============================================================================
# TestWriteFindingsToGraph
# ============================================================================

@pytest.mark.unit
class TestWriteFindingsToGraph:
    """Tests for _write_findings_to_graph() in task_603_comprehensive_review."""

    def test_write_findings_basic(self, manager):
        """Findings from multiple dimensions are written to graph via add_review_finding."""
        from phases.phase_06_code_review.tasks.task_603_comprehensive_review import (
            _write_findings_to_graph,
        )

        manager.add_review_finding = MagicMock()

        findings_data = {
            "deep_code": {
                "findings": [
                    {
                        "severity": "critical",
                        "category": "security",
                        "description": "SQL injection risk",
                        "file": "src/db.py",
                        "line": 55,
                        "recommendation": "Use parameterized queries",
                    },
                    {
                        "severity": "minor",
                        "category": "code_quality",
                        "description": "Unused import",
                        "file": "src/utils.py",
                        "line": 3,
                    },
                ],
            },
            "architecture": {
                "findings": [
                    {
                        "severity": "major",
                        "category": "coupling",
                        "description": "Direct DB access from handler",
                        "file": "src/handler.py",
                    },
                ],
            },
            "performance": {
                "findings": [],
            },
            "documentation": {
                "findings": [
                    {
                        "severity": "suggestion",
                        "category": "api_docs",
                        "description": "Missing docstring on public function",
                        "file": "src/api.py",
                    },
                ],
            },
        }

        _write_findings_to_graph(manager, findings_data)

        # Should be called once per finding across all dimensions
        assert manager.add_review_finding.call_count == 4

        # Verify the first call has the expected arguments
        first_call_kwargs = manager.add_review_finding.call_args_list[0]
        # Check that review_dimension is passed (mapped from the dict key)
        kwargs = first_call_kwargs[1] if first_call_kwargs[1] else {}
        args = first_call_kwargs[0] if first_call_kwargs[0] else ()
        # The function should pass review_dimension matching the dict key
        all_call_kwargs = [c[1] for c in manager.add_review_finding.call_args_list]
        dimensions_used = {kw.get("review_dimension") for kw in all_call_kwargs}
        assert "deep_code" in dimensions_used
        assert "architecture" in dimensions_used
        assert "documentation" in dimensions_used

    def test_write_findings_handles_errors(self, manager):
        """If one add_review_finding call raises, others are still written."""
        from phases.phase_06_code_review.tasks.task_603_comprehensive_review import (
            _write_findings_to_graph,
        )

        call_count = {"value": 0}

        def side_effect(*args, **kwargs):
            call_count["value"] += 1
            if call_count["value"] == 1:
                raise Exception("Graph write failed")

        manager.add_review_finding = MagicMock(side_effect=side_effect)

        findings_data = {
            "deep_code": {
                "findings": [
                    {
                        "severity": "critical",
                        "category": "security",
                        "description": "Finding 1 - will fail",
                    },
                    {
                        "severity": "minor",
                        "category": "logic",
                        "description": "Finding 2 - should succeed",
                    },
                ],
            },
            "architecture": {
                "findings": [
                    {
                        "severity": "major",
                        "category": "coupling",
                        "description": "Finding 3 - should succeed",
                    },
                ],
            },
        }

        # Should not raise
        _write_findings_to_graph(manager, findings_data)

        # All 3 findings attempted despite first one failing
        assert manager.add_review_finding.call_count == 3
