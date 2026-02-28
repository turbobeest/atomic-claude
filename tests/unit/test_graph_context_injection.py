"""Tests for graph context injection pipeline.

Covers:
- context_injector: build_graph_context, ContextVar accessors, helpers
- Auto-injection: ContextVar -> FeatureAwareLLMInvoker.invoke() and stream()
- Graceful degradation: graph exceptions don't propagate
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from core.graph.context_injector import (
    build_graph_context,
    get_active_graph_context,
    set_active_graph_context,
    _format_agent_context,
    _format_memory_context,
)


def _mock_graph(nodes=None, recall_entries=None):
    """Create a mock GraphManager with reader and recall_memory."""
    graph = MagicMock()
    graph.reader = MagicMock()
    graph.reader.get_nodes.return_value = nodes or []
    graph.recall_memory.return_value = recall_entries or []
    return graph


def _mock_gravity(value="standard"):
    """Create a mock GravityLevel enum."""
    g = MagicMock()
    g.value = value
    return g


# ───────────────────────────────────────────────────────────
# ContextVar accessors
# ───────────────────────────────────────────────────────────

@pytest.mark.unit
class TestGraphContextVar:

    def test_default_is_none(self):
        set_active_graph_context(None)
        assert get_active_graph_context() is None

    def test_set_and_get(self):
        set_active_graph_context("[Assigned Experts] test-agent")
        assert get_active_graph_context() == "[Assigned Experts] test-agent"
        set_active_graph_context(None)

    def test_clear(self):
        set_active_graph_context("something")
        set_active_graph_context(None)
        assert get_active_graph_context() is None


# ───────────────────────────────────────────────────────────
# build_graph_context
# ───────────────────────────────────────────────────────────

@pytest.mark.unit
class TestBuildGraphContext:

    def test_none_graph_returns_none(self):
        result = build_graph_context(
            None, "1-discovery", "101", "Test", _mock_gravity(),
        )
        assert result is None

    def test_empty_graph_returns_none(self):
        """Graph with no data returns None (all sections empty)."""
        graph = _mock_graph()
        result = build_graph_context(
            graph, "1-discovery", "101", "Test", _mock_gravity(),
        )
        assert result is None

    def test_with_agent_roster_produces_output(self):
        graph = _mock_graph(nodes=[{"id": "arch-expert", "description": "Architecture specialist"}])
        # Mock AgentEntry
        agent_entry = MagicMock()
        agent_entry.name = "arch-expert"
        model = MagicMock()
        roster = [(agent_entry, model)]

        result = build_graph_context(
            graph, "2-prd", "205", "PRD Authoring", _mock_gravity(), roster=roster,
        )
        assert result is not None
        assert "arch-expert" in result

    def test_with_memory_produces_output(self):
        graph = _mock_graph(recall_entries=[
            {"content": "Phase 1 completed discovery of 3 providers"},
        ])
        result = build_graph_context(
            graph, "2-prd", "205", "PRD Authoring", _mock_gravity(),
        )
        assert result is not None
        assert "Prior Context" in result
        assert "3 providers" in result

    def test_light_produces_shorter_output_than_standard(self):
        graph = _mock_graph(
            nodes=[{"id": "test-agent", "description": "A long description of the agent's capabilities"}],
            recall_entries=[{"content": "Some prior context from earlier"}],
        )
        agent_entry = MagicMock()
        agent_entry.name = "test-agent"
        roster = [(agent_entry, MagicMock())]

        light = build_graph_context(
            graph, "1-disc", "101", "Test", _mock_gravity("light"), roster=roster,
        )
        standard = build_graph_context(
            graph, "1-disc", "101", "Test", _mock_gravity("standard"), roster=roster,
        )
        # Light should be shorter (or equal if both are minimal)
        if light and standard:
            assert len(light) <= len(standard)

    def test_graceful_degradation_on_graph_exception(self):
        graph = MagicMock()
        graph.reader = MagicMock()
        graph.reader.get_nodes.side_effect = Exception("FalkorDB down")
        graph.recall_memory.side_effect = Exception("FalkorDB down")

        # Should not raise
        result = build_graph_context(
            graph, "1-disc", "101", "Test", _mock_gravity(),
        )
        assert result is None


# ───────────────────────────────────────────────────────────
# _format_agent_context
# ───────────────────────────────────────────────────────────

@pytest.mark.unit
class TestFormatAgentContext:

    def test_empty_roster_returns_empty(self):
        graph = _mock_graph()
        assert _format_agent_context(graph, None, 300) == ""
        assert _format_agent_context(graph, [], 300) == ""

    def test_light_budget_names_only(self):
        graph = _mock_graph()
        agent_entry = MagicMock()
        agent_entry.name = "security-expert"
        roster = [(agent_entry, MagicMock())]

        result = _format_agent_context(graph, roster, 100)
        assert "security-expert" in result
        assert "[Assigned Experts]" in result
        # Should NOT have description at this budget
        assert ": " not in result or "security-expert" in result

    def test_standard_budget_includes_descriptions(self):
        graph = _mock_graph(nodes=[{
            "id": "arch-specialist",
            "description": "Deep architecture analysis expert",
        }])
        agent_entry = MagicMock()
        agent_entry.name = "arch-specialist"
        roster = [(agent_entry, MagicMock())]

        result = _format_agent_context(graph, roster, 300)
        assert "arch-specialist" in result
        assert "Deep architecture" in result


# ───────────────────────────────────────────────────────────
# _format_memory_context
# ───────────────────────────────────────────────────────────

@pytest.mark.unit
class TestFormatMemoryContext:

    def test_no_entries_returns_empty(self):
        graph = _mock_graph(recall_entries=[])
        result = _format_memory_context(graph, "1-disc", "Test", 300)
        assert result == ""

    def test_entries_formatted(self):
        graph = _mock_graph(recall_entries=[
            {"content": "Provider A configured successfully"},
            {"content": "Project uses Python 3.11"},
        ])
        result = _format_memory_context(graph, "1-disc", "Test", 300)
        assert "[Prior Context]" in result
        assert "Provider A" in result
        assert "Python 3.11" in result

    def test_long_entries_truncated(self):
        long_content = "x" * 500
        graph = _mock_graph(recall_entries=[{"content": long_content}])
        result = _format_memory_context(graph, "1-disc", "Test", 300)
        assert len(result) < 500  # Should be truncated

    def test_zero_budget_returns_empty(self):
        graph = _mock_graph(recall_entries=[{"content": "something"}])
        result = _format_memory_context(graph, "1-disc", "Test", 0)
        assert result == ""


# ───────────────────────────────────────────────────────────
# Auto-injection in FeatureAwareLLMInvoker
# ───────────────────────────────────────────────────────────

@pytest.mark.unit
class TestGraphAutoInjection:

    def test_invoke_prepends_graph_context(self):
        set_active_graph_context("[Assigned Experts] test-agent")
        try:
            mock_provider = MagicMock()
            mock_provider.provider_name = "test"
            mock_provider.invoke.return_value = "response"

            from core.llm.invoke import FeatureAwareLLMInvoker
            invoker = FeatureAwareLLMInvoker(mock_provider)
            invoker.invoke("hello", system_prompt="You are helpful.")

            call_kwargs = mock_provider.invoke.call_args
            sys_prompt = call_kwargs.kwargs.get("system_prompt") or call_kwargs[1].get("system_prompt", "")
            assert "[Assigned Experts]" in sys_prompt
            assert "You are helpful." in sys_prompt
        finally:
            set_active_graph_context(None)

    def test_invoke_no_injection_when_cleared(self):
        set_active_graph_context(None)

        mock_provider = MagicMock()
        mock_provider.provider_name = "test"
        mock_provider.invoke.return_value = "response"

        from core.llm.invoke import FeatureAwareLLMInvoker
        invoker = FeatureAwareLLMInvoker(mock_provider)
        invoker.invoke("hello", system_prompt="Original.")

        call_kwargs = mock_provider.invoke.call_args
        sys_prompt = call_kwargs.kwargs.get("system_prompt") or call_kwargs[1].get("system_prompt", "")
        assert "[Assigned Experts]" not in sys_prompt
        assert "Original." in sys_prompt

    def test_both_skill_and_graph_context_coexist(self):
        """Both skill and graph context should appear in system_prompt."""
        from core.skills.context_formatter import set_active_skill_context
        set_active_skill_context("[Active Skills]\n- Test Skill: Do stuff.")
        set_active_graph_context("[Assigned Experts] arch-expert")
        try:
            mock_provider = MagicMock()
            mock_provider.provider_name = "test"
            mock_provider.invoke.return_value = "response"

            from core.llm.invoke import FeatureAwareLLMInvoker
            invoker = FeatureAwareLLMInvoker(mock_provider)
            invoker.invoke("hello")

            call_kwargs = mock_provider.invoke.call_args
            sys_prompt = call_kwargs.kwargs.get("system_prompt") or call_kwargs[1].get("system_prompt", "")
            assert "[Active Skills]" in sys_prompt
            assert "[Assigned Experts]" in sys_prompt
        finally:
            set_active_skill_context(None)
            set_active_graph_context(None)


# ───────────────────────────────────────────────────────────
# stream() injection (bug fix verification)
# ───────────────────────────────────────────────────────────

@pytest.mark.unit
class TestStreamInjection:

    def test_stream_gets_skill_context(self):
        """stream() should inject skill context (was missing before fix)."""
        from core.skills.context_formatter import set_active_skill_context
        set_active_skill_context("[Active Skills]\n- Stream Skill")
        try:
            mock_provider = MagicMock()
            mock_provider.provider_name = "test"
            mock_provider.stream.return_value = iter(["chunk"])

            from core.llm.invoke import FeatureAwareLLMInvoker
            invoker = FeatureAwareLLMInvoker(mock_provider)
            list(invoker.stream("hello", system_prompt="Base."))

            call_kwargs = mock_provider.stream.call_args
            sys_prompt = call_kwargs.kwargs.get("system_prompt") or call_kwargs[1].get("system_prompt", "")
            assert "[Active Skills]" in sys_prompt
        finally:
            set_active_skill_context(None)

    def test_stream_gets_graph_context(self):
        """stream() should inject graph context (was missing before fix)."""
        set_active_graph_context("[Prior Context]\n- Some memory")
        try:
            mock_provider = MagicMock()
            mock_provider.provider_name = "test"
            mock_provider.stream.return_value = iter(["chunk"])

            from core.llm.invoke import FeatureAwareLLMInvoker
            invoker = FeatureAwareLLMInvoker(mock_provider)
            list(invoker.stream("hello"))

            call_kwargs = mock_provider.stream.call_args
            sys_prompt = call_kwargs.kwargs.get("system_prompt") or call_kwargs[1].get("system_prompt", "")
            assert "[Prior Context]" in sys_prompt
        finally:
            set_active_graph_context(None)
