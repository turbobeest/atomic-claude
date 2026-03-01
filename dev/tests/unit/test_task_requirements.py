"""Tests for TaskRequirements and intelligent model downgrade."""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from core.llm.resolver import TaskRequirements, ModelResolver


@pytest.fixture
def resolver(tmp_path):
    """Create a resolver with minimal config."""
    # Write a minimal models.json
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    models_json = {
        "phase_roles": {"0-setup": "primary", "2-prd": "heavyweight"},
        "role_to_tier": {"primary": "sonnet", "heavyweight": "opus", "fast": "haiku", "gardener": "haiku"},
        "tier_definitions": {
            "opus": {"context_window": 1000000, "max_output": 32000, "extended_thinking": True},
            "sonnet": {"context_window": 200000, "max_output": 16000, "extended_thinking": True},
            "haiku": {"context_window": 200000, "max_output": 8192, "extended_thinking": False},
        },
        "model_ids": {
            "anthropic": {"opus": "claude-opus-4-6", "sonnet": "claude-sonnet-4-5", "haiku": "claude-haiku-4-5"},
        },
        "fallback_chains": {"opus": ["sonnet", "haiku"], "sonnet": ["haiku"]},
    }
    import json
    (config_dir / "models.json").write_text(json.dumps(models_json))

    return ModelResolver(atomic_root=tmp_path)


@pytest.mark.unit
class TestTaskRequirements:

    def test_default_requirements(self):
        """Default TaskRequirements has risk_budget=0.0."""
        req = TaskRequirements()
        assert req.risk_budget == 0.0
        assert req.needs_extended_thinking is False

    def test_for_phase_role_no_graph(self):
        """Without graph, factory returns budget=0.0."""
        req = TaskRequirements.for_phase_role("5-impl", "task-501")
        assert req.risk_budget == 0.0

    def test_for_phase_role_with_graph(self):
        """With graph, factory calls compute_risk_budget."""
        mock_graph = MagicMock()
        with patch("core.llm.risk.compute_risk_budget", return_value=0.6):
            req = TaskRequirements.for_phase_role("5-impl", "task-501", graph=mock_graph)
        assert req.risk_budget == pytest.approx(0.6)

    def test_frozen(self):
        """TaskRequirements is immutable."""
        req = TaskRequirements()
        with pytest.raises(AttributeError):
            req.risk_budget = 0.5


@pytest.mark.unit
class TestZeroMarginalCost:

    def test_claude_code_is_zero_cost(self, resolver):
        """Claude Code subscription = zero marginal cost."""
        assert resolver._is_zero_marginal_cost("claude-code") is True

    def test_ollama_is_zero_cost(self, resolver):
        """Ollama = zero marginal cost."""
        assert resolver._is_zero_marginal_cost("ollama") is True

    def test_anthropic_is_not_zero_cost(self, resolver):
        """Anthropic API = per-token cost."""
        assert resolver._is_zero_marginal_cost("anthropic") is False

    def test_bedrock_is_not_zero_cost(self, resolver):
        """AWS Bedrock = per-token cost."""
        assert resolver._is_zero_marginal_cost("aws-bedrock") is False


@pytest.mark.unit
class TestMaybeDowngrade:

    def test_no_downgrade_low_budget(self, resolver):
        """risk_budget < 0.3 = never downgrade."""
        req = TaskRequirements(risk_budget=0.2)
        result = resolver._maybe_downgrade("opus", "anthropic", req)
        assert result is None

    def test_no_downgrade_zero_cost_provider(self, resolver):
        """Claude Code never downgrades regardless of budget."""
        req = TaskRequirements(risk_budget=0.9)
        result = resolver._maybe_downgrade("opus", "claude-code", req)
        assert result is None

    def test_downgrade_opus_to_sonnet_medium_budget(self, resolver):
        """0.3-0.7 budget: opus -> sonnet."""
        req = TaskRequirements(risk_budget=0.5)
        result = resolver._maybe_downgrade("opus", "anthropic", req)
        assert result == "sonnet"

    def test_downgrade_opus_to_haiku_high_budget(self, resolver):
        """>0.7 budget: opus -> haiku (no thinking needed)."""
        req = TaskRequirements(risk_budget=0.85)
        result = resolver._maybe_downgrade("opus", "anthropic", req)
        assert result == "haiku"

    def test_downgrade_opus_to_sonnet_when_thinking_needed(self, resolver):
        """>0.7 budget but needs thinking: opus -> sonnet (not haiku)."""
        req = TaskRequirements(risk_budget=0.85, needs_extended_thinking=True)
        result = resolver._maybe_downgrade("opus", "anthropic", req)
        assert result == "sonnet"

    def test_haiku_never_downgrades(self, resolver):
        """Haiku is already cheapest."""
        req = TaskRequirements(risk_budget=0.9)
        result = resolver._maybe_downgrade("haiku", "anthropic", req)
        assert result is None


@pytest.mark.unit
class TestResolveWithRequirements:

    def test_resolve_without_requirements_unchanged(self, resolver):
        """resolve() without requirements works exactly as before."""
        with patch.dict("os.environ", {"ATOMIC_LLM_PROVIDER": "anthropic"}, clear=False):
            rm = resolver.resolve("5-impl", "task-501")
        # Should use default "primary" -> "sonnet"
        assert rm.tier == "sonnet"

    def test_resolve_with_high_budget_downgrades(self, resolver):
        """resolve() with high risk_budget can downgrade."""
        req = TaskRequirements(risk_budget=0.85)
        with patch.dict("os.environ", {"ATOMIC_LLM_PROVIDER": "anthropic"}, clear=False):
            rm = resolver.resolve("5-impl", "task-501", requirements=req)
        # "sonnet" (from primary) can downgrade to "haiku" at budget > 0.7
        assert rm.tier == "haiku"
