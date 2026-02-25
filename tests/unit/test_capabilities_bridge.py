"""Tests for capabilities.py registry bridge.

Verifies that get_model_context_window, get_model_max_output, and
model_supports check the dynamic ModelRegistry first and fall back
to the static dicts when the registry is unavailable or has no match.
"""

import pytest
from unittest.mock import MagicMock, patch

from core.llm.capabilities import (
    get_model_context_window,
    get_model_max_output,
    model_supports,
    ModelCapability,
)


@pytest.fixture
def mock_registry():
    """Mock registry with a test model record."""
    from core.llm.registry import ModelRecord

    record = ModelRecord(
        model_id="test-model-v2",
        provider_id="anthropic",
        context_window=500_000,
        max_output=32_000,
        supports_extended_thinking=True,
        supports_tool_use=True,
        supports_vision=True,
        tier="opus",
        available=True,
    )
    registry = MagicMock()
    registry.find_by_model_id.return_value = record
    return registry


@pytest.fixture
def mock_registry_no_thinking():
    """Mock registry with a model that does NOT support extended thinking."""
    from core.llm.registry import ModelRecord

    record = ModelRecord(
        model_id="cheap-haiku-v1",
        provider_id="anthropic",
        context_window=200_000,
        max_output=8_192,
        supports_extended_thinking=False,
        supports_tool_use=True,
        supports_vision=False,
        tier="haiku",
        available=True,
    )
    registry = MagicMock()
    registry.find_by_model_id.return_value = record
    return registry


@pytest.fixture
def empty_registry():
    """Mock registry that returns None for every lookup."""
    registry = MagicMock()
    registry.find_by_model_id.return_value = None
    return registry


# -----------------------------------------------------------------------
# get_model_context_window
# -----------------------------------------------------------------------

@pytest.mark.unit
class TestContextWindowBridge:

    def test_context_window_from_registry(self, mock_registry):
        """Registry model returns its context_window."""
        with patch("core.llm.capabilities._get_registry", return_value=mock_registry):
            result = get_model_context_window("test-model-v2")
        assert result == 500_000
        mock_registry.find_by_model_id.assert_called_once_with("test-model-v2")

    def test_context_window_fallback_to_static(self, empty_registry):
        """Known static model still works when registry has no match."""
        with patch("core.llm.capabilities._get_registry", return_value=empty_registry):
            result = get_model_context_window("claude-opus-4-6")
        assert result == 1_000_000

    def test_context_window_registry_unavailable(self):
        """Registry returning None falls back to static."""
        with patch("core.llm.capabilities._get_registry", return_value=None):
            result = get_model_context_window("opus")
        assert result == 1_000_000

    def test_context_window_registry_raises(self):
        """Registry import/call failure falls back to static."""
        with patch("core.llm.capabilities._get_registry", side_effect=Exception("boom")):
            result = get_model_context_window("opus")
        assert result == 1_000_000

    def test_context_window_unknown_model_default(self, empty_registry):
        """Completely unknown model returns 200_000 default."""
        with patch("core.llm.capabilities._get_registry", return_value=empty_registry):
            result = get_model_context_window("no-such-model")
        assert result == 200_000

    def test_context_window_zero_in_registry_falls_through(self):
        """Registry record with context_window=0 falls back to static."""
        from core.llm.registry import ModelRecord

        record = ModelRecord(
            model_id="opus",
            provider_id="anthropic",
            context_window=0,  # zero — should be ignored
            max_output=32_000,
        )
        registry = MagicMock()
        registry.find_by_model_id.return_value = record
        with patch("core.llm.capabilities._get_registry", return_value=registry):
            result = get_model_context_window("opus")
        assert result == 1_000_000


# -----------------------------------------------------------------------
# get_model_max_output
# -----------------------------------------------------------------------

@pytest.mark.unit
class TestMaxOutputBridge:

    def test_max_output_from_registry(self, mock_registry):
        """Registry model returns its max_output."""
        with patch("core.llm.capabilities._get_registry", return_value=mock_registry):
            result = get_model_max_output("test-model-v2")
        assert result == 32_000
        mock_registry.find_by_model_id.assert_called_once_with("test-model-v2")

    def test_max_output_fallback_to_static(self, empty_registry):
        """Known static model still works when registry returns None."""
        with patch("core.llm.capabilities._get_registry", return_value=empty_registry):
            result = get_model_max_output("claude-sonnet-4-5")
        assert result == 16_000

    def test_max_output_registry_unavailable(self):
        """Registry returning None falls back to static."""
        with patch("core.llm.capabilities._get_registry", return_value=None):
            result = get_model_max_output("haiku")
        assert result == 8_192

    def test_max_output_registry_raises(self):
        """Exception in registry falls back to static."""
        with patch("core.llm.capabilities._get_registry", side_effect=RuntimeError("fail")):
            result = get_model_max_output("sonnet")
        assert result == 16_000

    def test_max_output_unknown_model_default(self, empty_registry):
        """Unknown model returns 4_096 default."""
        with patch("core.llm.capabilities._get_registry", return_value=empty_registry):
            result = get_model_max_output("no-such-model")
        assert result == 4_096

    def test_max_output_zero_in_registry_falls_through(self):
        """Registry record with max_output=0 falls back to static."""
        from core.llm.registry import ModelRecord

        record = ModelRecord(
            model_id="sonnet",
            provider_id="anthropic",
            context_window=200_000,
            max_output=0,  # zero — should be ignored
        )
        registry = MagicMock()
        registry.find_by_model_id.return_value = record
        with patch("core.llm.capabilities._get_registry", return_value=registry):
            result = get_model_max_output("sonnet")
        assert result == 16_000


# -----------------------------------------------------------------------
# model_supports (extended thinking)
# -----------------------------------------------------------------------

@pytest.mark.unit
class TestModelSupportsBridge:

    def test_extended_thinking_true_from_registry(self, mock_registry):
        """Registry says model supports thinking + provider supports it."""
        with patch("core.llm.capabilities._get_registry", return_value=mock_registry):
            result = model_supports("anthropic", "test-model-v2", ModelCapability.EXTENDED_THINKING)
        assert result is True

    def test_extended_thinking_false_from_registry(self, mock_registry_no_thinking):
        """Registry says model does NOT support thinking."""
        with patch("core.llm.capabilities._get_registry", return_value=mock_registry_no_thinking):
            result = model_supports("anthropic", "cheap-haiku-v1", ModelCapability.EXTENDED_THINKING)
        assert result is False

    def test_extended_thinking_registry_miss_falls_to_static(self, empty_registry):
        """No registry record: falls back to EXTENDED_THINKING_MODELS set."""
        with patch("core.llm.capabilities._get_registry", return_value=empty_registry):
            # "opus" is in the static EXTENDED_THINKING_MODELS set
            result = model_supports("anthropic", "opus", ModelCapability.EXTENDED_THINKING)
        assert result is True

    def test_extended_thinking_static_unknown_model(self, empty_registry):
        """Unknown model not in static set returns False."""
        with patch("core.llm.capabilities._get_registry", return_value=empty_registry):
            result = model_supports("anthropic", "totally-unknown", ModelCapability.EXTENDED_THINKING)
        assert result is False

    def test_extended_thinking_provider_lacks_capability(self, mock_registry):
        """Registry says model supports thinking but provider doesn't."""
        with patch("core.llm.capabilities._get_registry", return_value=mock_registry):
            # Ollama doesn't have EXTENDED_THINKING in its capabilities
            result = model_supports("ollama", "test-model-v2", ModelCapability.EXTENDED_THINKING)
        assert result is False

    def test_extended_thinking_registry_raises(self):
        """Exception in registry falls back to static set."""
        with patch("core.llm.capabilities._get_registry", side_effect=Exception("crash")):
            result = model_supports("anthropic", "claude-sonnet-4-5", ModelCapability.EXTENDED_THINKING)
        # claude-sonnet-4-5 IS in EXTENDED_THINKING_MODELS, and anthropic supports it
        assert result is True

    def test_non_thinking_capability_ignores_registry(self, mock_registry):
        """Non-EXTENDED_THINKING capabilities go straight to provider check."""
        with patch("core.llm.capabilities._get_registry", return_value=mock_registry):
            result = model_supports("anthropic", "test-model-v2", ModelCapability.VISION)
        assert result is True
        # Registry should NOT have been consulted for a non-thinking capability
        mock_registry.find_by_model_id.assert_not_called()

    def test_registry_none_getter(self):
        """_get_registry is None (ImportError at module load) — still works."""
        with patch("core.llm.capabilities._get_registry", None):
            # "opus" is in EXTENDED_THINKING_MODELS and anthropic supports it
            result = model_supports("anthropic", "opus", ModelCapability.EXTENDED_THINKING)
        assert result is True
