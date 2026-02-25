"""Tests for ContextCompiler - Stage 3 graph integration."""

import pytest
from unittest.mock import MagicMock, patch, call
from core.graph.context_compiler import (
    ContextCompiler, Traversal, _estimate_tokens, _default_format,
)


@pytest.fixture
def mock_reader():
    """Create a mock GraphReader."""
    reader = MagicMock()
    reader.get_nodes.return_value = []
    reader.get_neighbors.return_value = []
    return reader


@pytest.fixture
def compiler(mock_reader):
    return ContextCompiler(mock_reader)


class TestEstimateTokens:

    @pytest.mark.unit
    def test_basic_estimation(self):
        assert _estimate_tokens("abcd") == 1
        assert _estimate_tokens("a" * 400) == 100

    @pytest.mark.unit
    def test_empty_string(self):
        assert _estimate_tokens("") == 0


class TestDefaultFormat:

    @pytest.mark.unit
    def test_full_node(self):
        result = _default_format({"category": "security", "title": "SQL Injection", "content": "Found vulnerability"})
        assert "security" in result
        assert "SQL Injection" in result
        assert "Found vulnerability" in result

    @pytest.mark.unit
    def test_minimal_node(self):
        result = _default_format({"id": "42"})
        assert "42" in result

    @pytest.mark.unit
    def test_description_fallback(self):
        result = _default_format({"title": "Test", "description": "A desc"})
        assert "A desc" in result


class TestTraversal:

    @pytest.mark.unit
    def test_defaults(self):
        t = Traversal(label="Task")
        assert t.label == "Task"
        assert t.heading == ""
        assert t.filters is None
        assert t.rel_from is None
        assert t.direction == "out"
        assert t.token_budget == 0
        assert t.include_empty is False

    @pytest.mark.unit
    def test_all_fields(self):
        fn = lambda n: n.get("title", "")
        t = Traversal(
            label="Finding", heading="## Findings",
            filters={"category": "vision"}, rel_from=("Source", "s1"),
            rel_type="DERIVED_FROM", direction="in",
            order_by="id", limit=10, format_fn=fn,
            token_budget=2000, include_empty=True,
        )
        assert t.rel_from == ("Source", "s1")
        assert t.token_budget == 2000


class TestCompile:

    @pytest.mark.unit
    def test_basic_compile(self, compiler, mock_reader):
        mock_reader.get_nodes.return_value = [
            {"category": "tech", "title": "Finding A", "content": "Details A"},
            {"category": "tech", "title": "Finding B", "content": "Details B"},
        ]
        result = compiler.compile([
            Traversal(label="Finding", heading="## Findings"),
        ], max_tokens=4000)
        assert "## Findings" in result
        assert "Finding A" in result
        assert "Finding B" in result
        mock_reader.get_nodes.assert_called_once()

    @pytest.mark.unit
    def test_compile_multiple_traversals(self, compiler, mock_reader):
        def side_effect(label, **kwargs):
            if label == "Finding":
                return [{"title": "F1", "content": "c1"}]
            elif label == "Decision":
                return [{"title": "D1", "rationale": "r1"}]
            return []
        mock_reader.get_nodes.side_effect = side_effect

        result = compiler.compile([
            Traversal(label="Finding", heading="## Findings"),
            Traversal(label="Decision", heading="## Decisions"),
        ], max_tokens=8000)
        assert "## Findings" in result
        assert "## Decisions" in result
        assert "F1" in result
        assert "D1" in result

    @pytest.mark.unit
    def test_compile_empty_skips_section(self, compiler, mock_reader):
        mock_reader.get_nodes.return_value = []
        result = compiler.compile([
            Traversal(label="Finding", heading="## Findings"),
        ], max_tokens=4000)
        assert result == ""

    @pytest.mark.unit
    def test_compile_include_empty(self, compiler, mock_reader):
        mock_reader.get_nodes.return_value = []
        result = compiler.compile([
            Traversal(label="Finding", heading="## Findings", include_empty=True),
        ], max_tokens=4000)
        assert "## Findings" in result
        assert "(none)" in result

    @pytest.mark.unit
    def test_compile_with_rel_from(self, compiler, mock_reader):
        mock_reader.get_neighbors.return_value = [
            {"title": "Dep 1", "status": "done"},
        ]
        result = compiler.compile([
            Traversal(
                label="Task", heading="## Dependencies",
                rel_from=("Task", 5), rel_type="TASK_DEPENDS_ON",
            ),
        ], max_tokens=4000)
        assert "Dep 1" in result
        mock_reader.get_neighbors.assert_called_once_with(
            "Task", 5, rel_type="TASK_DEPENDS_ON", direction="out",
        )

    @pytest.mark.unit
    def test_compile_respects_token_budget(self, compiler, mock_reader):
        # Generate many large nodes that exceed budget
        big_nodes = [
            {"title": f"Node {i}", "content": "x" * 500}
            for i in range(50)
        ]
        mock_reader.get_nodes.return_value = big_nodes
        result = compiler.compile([
            Traversal(label="Finding", heading="## Findings"),
        ], max_tokens=200)  # Very small budget
        # Should truncate well before including all 50 nodes
        assert len(result) < 200 * 4 + 100  # some slack for truncation marker

    @pytest.mark.unit
    def test_compile_custom_format_fn(self, compiler, mock_reader):
        mock_reader.get_nodes.return_value = [
            {"severity": "critical", "file": "main.py", "line": 42},
        ]
        result = compiler.compile([
            Traversal(
                label="ReviewFinding", heading="## Issues",
                format_fn=lambda f: f"[{f['severity']}] {f['file']}:{f['line']}",
            ),
        ], max_tokens=4000)
        assert "[critical] main.py:42" in result

    @pytest.mark.unit
    def test_compile_traversal_error_handled(self, compiler, mock_reader):
        mock_reader.get_nodes.side_effect = Exception("DB down")
        result = compiler.compile([
            Traversal(label="Finding", heading="## Findings"),
        ], max_tokens=4000)
        assert result == ""  # Gracefully returns empty on error


class TestPresets:

    @pytest.mark.unit
    def test_prd_context_calls_compile(self, compiler, mock_reader):
        mock_reader.get_nodes.return_value = []
        result = compiler.prd_context("features", max_tokens=4000)
        # Should have called get_nodes for Finding categories + Decision + Requirement + Source
        assert mock_reader.get_nodes.call_count >= 1

    @pytest.mark.unit
    def test_task_context_specific_task(self, compiler, mock_reader):
        mock_reader.get_nodes.return_value = [
            {"id": 5, "title": "Build API", "description": "REST API"}
        ]
        mock_reader.get_neighbors.return_value = []
        result = compiler.task_context(task_id=5, max_tokens=4000)
        mock_reader.get_nodes.assert_any_call("Task", filters={"id": 5}, order_by=None, limit=1)

    @pytest.mark.unit
    def test_task_context_all_tasks(self, compiler, mock_reader):
        mock_reader.get_nodes.return_value = [
            {"id": 1, "title": "Task 1", "status": "done"},
        ]
        result = compiler.task_context(max_tokens=4000)
        # Should call get_nodes with label="Task" and order_by="id"
        mock_reader.get_nodes.assert_any_call("Task", filters=None, order_by="id", limit=None)

    @pytest.mark.unit
    def test_review_context(self, compiler, mock_reader):
        mock_reader.get_nodes.return_value = [
            {"severity": "critical", "description": "SQL injection", "file": "app.py", "line": 10},
        ]
        result = compiler.review_context(severity="critical", max_tokens=4000)
        assert "critical" in result
        assert "SQL injection" in result

    @pytest.mark.unit
    def test_review_context_heading_includes_filters(self, compiler, mock_reader):
        mock_reader.get_nodes.return_value = [{"severity": "major", "description": "test"}]
        result = compiler.review_context(
            severity="major", review_dimension="deep_code", max_tokens=4000,
        )
        assert "(major)" in result
        assert "[deep_code]" in result
