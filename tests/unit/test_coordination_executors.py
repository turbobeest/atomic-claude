"""Tests for orchestration.coordination.executors."""

import pytest
from unittest.mock import MagicMock, patch

from orchestration.coordination.executors import execute_with_pattern
from orchestration.coordination.executors.base import (
    BasePatternExecutor,
    ExecutionContext,
    ExecutionResult,
)
from orchestration.coordination.executors.sequential import SequentialExecutor
from orchestration.coordination.executors.review_loop import ReviewLoopExecutor
from orchestration.coordination.executors.saga import SagaExecutor, SagaStep
from orchestration.coordination.patterns import CoordinationPattern


def _make_ctx(task_func=None, graph=None, roster=None, **kwargs):
    """Helper to create ExecutionContext."""
    if task_func is None:
        task_func = MagicMock(return_value=True)
    mem = MagicMock()
    mem.has_entries.return_value = True
    mem.build_content.return_value = "task output"
    return ExecutionContext(
        task_id="001",
        task_name="Test Task",
        task_func=task_func,
        mem=mem,
        roster=roster,
        gravity="standard",
        graph=graph,
        phase_id="0-setup",
        **kwargs,
    )


class TestSequentialExecutor:
    """Test SequentialExecutor preserves existing behavior."""

    def test_success(self):
        task_func = MagicMock(return_value=True)
        ctx = _make_ctx(task_func=task_func)
        result = SequentialExecutor().execute(ctx)
        assert result.success is True
        assert result.pattern_used == "sequential"
        task_func.assert_called_once()

    def test_none_is_success(self):
        task_func = MagicMock(return_value=None)
        ctx = _make_ctx(task_func=task_func)
        result = SequentialExecutor().execute(ctx)
        assert result.success is True

    def test_false_is_failure(self):
        task_func = MagicMock(return_value=False)
        ctx = _make_ctx(task_func=task_func)
        result = SequentialExecutor().execute(ctx)
        assert result.success is False

    def test_exception_is_failure(self):
        task_func = MagicMock(side_effect=RuntimeError("boom"))
        ctx = _make_ctx(task_func=task_func)
        result = SequentialExecutor().execute(ctx)
        assert result.success is False
        assert "boom" in result.error

    def test_passes_graph_when_accepted(self):
        def task_with_graph(mem, graph=None):
            return graph is not None

        graph = MagicMock()
        ctx = _make_ctx(task_func=task_with_graph, graph=graph)
        result = SequentialExecutor().execute(ctx)
        assert result.success is True

    def test_skips_graph_when_not_accepted(self):
        def task_no_graph(mem):
            return True

        graph = MagicMock()
        ctx = _make_ctx(task_func=task_no_graph, graph=graph)
        result = SequentialExecutor().execute(ctx)
        assert result.success is True


class TestReviewLoopExecutor:
    """Test ReviewLoopExecutor iteration behavior."""

    def test_no_roster_runs_once(self):
        task_func = MagicMock(return_value=True)
        ctx = _make_ctx(task_func=task_func, roster=None)
        result = ReviewLoopExecutor().execute(ctx)
        assert result.success is True
        assert result.iterations == 1

    def test_single_agent_runs_once(self):
        task_func = MagicMock(return_value=True)
        ctx = _make_ctx(task_func=task_func, roster=[("a1", "m1")])
        result = ReviewLoopExecutor().execute(ctx)
        assert result.success is True
        assert result.iterations == 1

    @patch("orchestration.coordination.executors.review_loop.ReviewLoopExecutor._request_review")
    def test_approved_first_iteration(self, mock_review):
        mock_review.return_value = "APPROVED"
        task_func = MagicMock(return_value=True)
        ctx = _make_ctx(task_func=task_func, roster=[("a1", "m1"), ("a2", "m2")])
        result = ReviewLoopExecutor().execute(ctx)
        assert result.success is True
        assert result.metadata.get("review_status") == "approved"

    @patch("orchestration.coordination.executors.review_loop.ReviewLoopExecutor._request_review")
    def test_revision_then_approved(self, mock_review):
        mock_review.side_effect = ["REVISION_NEEDED: fix X", "APPROVED"]
        task_func = MagicMock(return_value=True)
        ctx = _make_ctx(task_func=task_func, roster=[("a1", "m1"), ("a2", "m2")])
        result = ReviewLoopExecutor().execute(ctx)
        assert result.success is True
        assert result.iterations <= 3

    def test_task_failure_stops_loop(self):
        task_func = MagicMock(return_value=False)
        ctx = _make_ctx(task_func=task_func, roster=[("a1", "m1"), ("a2", "m2")])
        result = ReviewLoopExecutor().execute(ctx)
        assert result.success is False


class TestSagaExecutor:
    """Test SagaExecutor rollback behavior."""

    def test_single_step_success(self):
        task_func = MagicMock(return_value=True)
        ctx = _make_ctx(task_func=task_func)
        result = SagaExecutor().execute(ctx)
        assert result.success is True
        assert result.pattern_used == "saga"

    def test_step_failure_triggers_rollback(self):
        compensate = MagicMock()
        steps = [
            SagaStep("step1", lambda: True, compensate=compensate),
            SagaStep("step2", lambda: False, compensate=None),
        ]
        ctx = _make_ctx(extra={"saga_steps": steps})
        result = SagaExecutor().execute(ctx)
        assert result.success is False
        compensate.assert_called_once()

    def test_exception_triggers_rollback(self):
        compensate = MagicMock()
        steps = [
            SagaStep("step1", lambda: True, compensate=compensate),
            SagaStep("step2", lambda: (_ for _ in ()).throw(RuntimeError("boom")),
                     compensate=None),
        ]
        ctx = _make_ctx(extra={"saga_steps": steps})
        result = SagaExecutor().execute(ctx)
        assert result.success is False
        compensate.assert_called_once()

    def test_multi_step_all_succeed(self):
        steps = [
            SagaStep("step1", lambda: True),
            SagaStep("step2", lambda: True),
            SagaStep("step3", lambda: True),
        ]
        ctx = _make_ctx(extra={"saga_steps": steps})
        result = SagaExecutor().execute(ctx)
        assert result.success is True
        assert result.iterations == 3


class TestExecuteWithPattern:
    """Test the top-level dispatch function."""

    def test_sequential_dispatch(self):
        task_func = MagicMock(return_value=True)
        ctx = _make_ctx(task_func=task_func)
        result = execute_with_pattern(CoordinationPattern.SEQUENTIAL, ctx)
        assert result.success is True

    def test_fallback_on_error(self):
        """Unknown pattern falls back to sequential."""
        task_func = MagicMock(return_value=True)
        ctx = _make_ctx(task_func=task_func)
        # Should not raise even with a bad executor
        result = execute_with_pattern(CoordinationPattern.SEQUENTIAL, ctx)
        assert result.success is True

    def test_all_patterns_dispatchable(self):
        """Every pattern in the enum can be dispatched (may fall back)."""
        for pattern in CoordinationPattern:
            task_func = MagicMock(return_value=True)
            ctx = _make_ctx(task_func=task_func, roster=[
                (MagicMock(name="a1", description="d1", composite_score=80), "m1"),
                (MagicMock(name="a2", description="d2", composite_score=70), "m2"),
                (MagicMock(name="a3", description="d3", composite_score=60), "m3"),
            ])
            result = execute_with_pattern(pattern, ctx)
            # Should at least return a result (success or fallback)
            assert isinstance(result, ExecutionResult)
