"""Tests for Dynamic Model Registry."""

import json
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path
from datetime import datetime, timezone, timedelta
from core.llm.registry import ModelRegistry, ModelRecord, RegistrySnapshot, CACHE_MAX_AGE


@pytest.fixture
def tmp_registry(tmp_path):
    """Create a ModelRegistry with a temp state dir."""
    registry = ModelRegistry.__new__(ModelRegistry)
    registry._atomic_root = tmp_path
    registry._state_dir = tmp_path / ".state"
    registry._cache_path = registry._state_dir / "model-registry.json"
    registry._models = {}
    registry._last_upstream_sync = None
    registry._last_probe = None
    return registry


# --- Upstream parsing tests ---

class TestParseUpstream:

    @pytest.mark.unit
    def test_parse_upstream_anthropic_models(self, tmp_registry):
        """Parsing models.dev JSON extracts correct fields for Anthropic models."""
        data = [
            {
                "id": "claude-sonnet-4-5-20250929",
                "provider": {"id": "anthropic"},
                "name": "Claude Sonnet 4.5",
                "context_length": 200000,
                "max_output_tokens": 16000,
                "pricing": {"prompt": 0.000003, "completion": 0.000015},
                "capabilities": {"reasoning": True, "tool_calling": True, "vision": True},
            }
        ]
        count = tmp_registry._parse_upstream(data)
        assert count == 1
        record = tmp_registry.get_model("anthropic", "claude-sonnet-4-5-20250929")
        assert record is not None
        assert record.context_window == 200000
        assert record.max_output == 16000
        assert record.supports_extended_thinking is True
        assert record.supports_tool_use is True
        assert record.supports_vision is True
        assert record.tier == "sonnet"
        # Pricing: per-token * 1M = per Mtok
        assert record.input_cost_per_mtok == pytest.approx(3.0)
        assert record.output_cost_per_mtok == pytest.approx(15.0)

    @pytest.mark.unit
    def test_parse_upstream_filters_providers(self, tmp_registry):
        """Only configured providers are imported, not all 75+."""
        data = [
            {"id": "claude-opus-4-6", "provider": {"id": "anthropic"}, "name": "Opus"},
            {"id": "gpt-4o", "provider": {"id": "openai"}, "name": "GPT-4o"},
            {"id": "gemini-pro", "provider": {"id": "google"}, "name": "Gemini"},
        ]
        count = tmp_registry._parse_upstream(data)
        assert count == 1  # Only anthropic
        assert tmp_registry.get_model("anthropic", "claude-opus-4-6") is not None


# --- Cache freshness tests ---

class TestCacheFreshness:

    @pytest.mark.unit
    def test_cache_freshness_check(self, tmp_registry):
        """sync_upstream() skips fetch when cache is <24h old."""
        tmp_registry._last_upstream_sync = datetime.now(timezone.utc).isoformat()
        # Add a model to prove cache has data
        tmp_registry._models["anthropic:test"] = ModelRecord(
            model_id="test", provider_id="anthropic"
        )
        with patch.object(tmp_registry, '_fetch_upstream') as mock_fetch:
            count = tmp_registry.sync_upstream(force=False)
            mock_fetch.assert_not_called()
            assert count == 0

    @pytest.mark.unit
    def test_cache_force_refresh(self, tmp_registry):
        """sync_upstream(force=True) fetches even with fresh cache."""
        tmp_registry._last_upstream_sync = datetime.now(timezone.utc).isoformat()
        with patch.object(tmp_registry, '_fetch_upstream', return_value=[]):
            count = tmp_registry.sync_upstream(force=True)
            tmp_registry._fetch_upstream.assert_called_once()

    @pytest.mark.unit
    def test_upstream_unreachable_uses_cache(self, tmp_registry):
        """Network failure falls back to existing cached data."""
        tmp_registry._models["anthropic:old"] = ModelRecord(
            model_id="old", provider_id="anthropic"
        )
        with patch.object(tmp_registry, '_fetch_upstream', side_effect=Exception("Network down")):
            count = tmp_registry.sync_upstream(force=True)
            assert count == 0
            assert tmp_registry.get_model("anthropic", "old") is not None

    @pytest.mark.unit
    def test_upstream_unreachable_no_cache(self, tmp_registry):
        """Network failure + no cache = empty registry (no crash)."""
        with patch.object(tmp_registry, '_fetch_upstream', side_effect=Exception("Network down")):
            count = tmp_registry.sync_upstream(force=True)
            assert count == 0
            assert len(tmp_registry._models) == 0


# --- Provider probing tests ---

class TestProviderProbes:

    @pytest.mark.unit
    def test_probe_ollama_discovers_models(self, tmp_registry):
        """Mock /api/tags response creates ModelRecords with correct parameter sizes."""
        mock_response = json.dumps({
            "models": [
                {"name": "qwen3:235b-a22b", "details": {"parameter_size": "235B"}},
                {"name": "llama3.1:8b", "details": {"parameter_size": "8B"}},
            ]
        }).encode()

        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_response
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("core.llm.registry.urllib.request.urlopen", return_value=mock_resp):
            count = tmp_registry._probe_ollama()

        assert count == 2
        qwen = tmp_registry.get_model("ollama", "qwen3:235b-a22b")
        assert qwen is not None
        assert qwen.tier == "opus"  # 235B >= 65B
        assert qwen.available is True

        llama = tmp_registry.get_model("ollama", "llama3.1:8b")
        assert llama is not None
        assert llama.tier == "haiku"  # 8B < 14B

    @pytest.mark.unit
    def test_probe_ollama_offline(self, tmp_registry):
        """Ollama not running = 0 models, no crash."""
        with patch("core.llm.registry.urllib.request.urlopen", side_effect=Exception("Connection refused")):
            count = tmp_registry._probe_ollama()
        assert count == 0

    @pytest.mark.unit
    def test_probe_bedrock_list_models(self, tmp_registry):
        """Mock list_foundation_models returns region-specific models."""
        mock_client = MagicMock()
        mock_client.list_foundation_models.return_value = {
            "modelSummaries": [
                {"modelId": "anthropic.claude-sonnet-4-5-20250929-v1:0", "modelName": "Claude Sonnet 4.5"},
                {"modelId": "anthropic.claude-haiku-4-5-20251001-v1:0", "modelName": "Claude Haiku 4.5"},
            ]
        }
        mock_boto3 = MagicMock()
        mock_boto3.client.return_value = mock_client

        with patch.dict("sys.modules", {"boto3": mock_boto3}):
            with patch("core.llm.registry.boto3", mock_boto3, create=True):
                count = tmp_registry._probe_bedrock()

        assert count == 2
        sonnet = tmp_registry.get_model("aws-bedrock", "anthropic.claude-sonnet-4-5-20250929-v1:0")
        assert sonnet is not None
        assert sonnet.available is True
        assert sonnet.tier == "sonnet"

    @pytest.mark.unit
    def test_probe_bedrock_no_boto3(self, tmp_registry):
        """boto3 not installed = skip gracefully."""
        with patch.dict("sys.modules", {"boto3": None}):
            # Force import to fail
            import importlib
            with patch("builtins.__import__", side_effect=ImportError("No module")):
                count = tmp_registry._probe_bedrock()
        assert count == 0


# --- Tier classification tests ---

class TestClassifyTier:

    @pytest.mark.unit
    def test_classify_tier_claude_models(self):
        """Tier classification for all Claude model ID patterns."""
        assert ModelRegistry.classify_tier("claude-opus-4-6") == "opus"
        assert ModelRegistry.classify_tier("anthropic.claude-opus-4-6-20250219-v1:0") == "opus"
        assert ModelRegistry.classify_tier("claude-sonnet-4-5-20250929") == "sonnet"
        assert ModelRegistry.classify_tier("claude-haiku-4-5-20251001") == "haiku"

    @pytest.mark.unit
    def test_classify_tier_ollama_by_params(self):
        """Tier classification by parameter count."""
        assert ModelRegistry.classify_tier("qwen3:235b", param_size="235B") == "opus"
        assert ModelRegistry.classify_tier("llama3.1:70b", param_size="70B") == "opus"
        assert ModelRegistry.classify_tier("phi4:14b", param_size="14B") == "sonnet"
        assert ModelRegistry.classify_tier("qwen3:8b", param_size="8B") == "haiku"
        assert ModelRegistry.classify_tier("unknown-model") is None


# --- Filtering tests ---

class TestFiltering:

    @pytest.mark.unit
    def test_get_available_filtered(self, tmp_registry):
        """get_available_models(needs_thinking=True) excludes models without extended thinking."""
        tmp_registry._models["a:opus"] = ModelRecord(
            model_id="opus", provider_id="a", available=True,
            supports_extended_thinking=True, context_window=1_000_000,
        )
        tmp_registry._models["a:haiku"] = ModelRecord(
            model_id="haiku", provider_id="a", available=True,
            supports_extended_thinking=False, context_window=200_000,
        )
        results = tmp_registry.get_available_models(needs_thinking=True)
        assert len(results) == 1
        assert results[0].model_id == "opus"

    @pytest.mark.unit
    def test_get_best_for_tier(self, tmp_registry):
        """get_best_for_tier returns highest-context model matching provider+tier."""
        tmp_registry._models["anthropic:sonnet-old"] = ModelRecord(
            model_id="sonnet-old", provider_id="anthropic", available=True,
            tier="sonnet", context_window=100_000,
        )
        tmp_registry._models["anthropic:sonnet-new"] = ModelRecord(
            model_id="sonnet-new", provider_id="anthropic", available=True,
            tier="sonnet", context_window=200_000,
        )
        tmp_registry._models["anthropic:opus"] = ModelRecord(
            model_id="opus", provider_id="anthropic", available=True,
            tier="opus", context_window=1_000_000,
        )
        best = tmp_registry.get_best_for_tier("anthropic", "sonnet")
        assert best is not None
        assert best.model_id == "sonnet-new"
        assert best.context_window == 200_000
        # Opus should not be returned for sonnet tier
        assert best.tier == "sonnet"
        # Non-existent tier returns None
        assert tmp_registry.get_best_for_tier("anthropic", "nano") is None


# --- Persistence tests ---

class TestPersistence:

    @pytest.mark.unit
    def test_save_load_roundtrip(self, tmp_registry):
        """RegistrySnapshot serializes to JSON and deserializes identically."""
        tmp_registry._models["anthropic:test"] = ModelRecord(
            model_id="test", provider_id="anthropic",
            display_name="Test Model", context_window=200000,
            max_output=8192, tier="sonnet", available=True,
        )
        tmp_registry._last_upstream_sync = "2025-01-01T00:00:00+00:00"
        tmp_registry._last_probe = "2025-01-01T01:00:00+00:00"

        tmp_registry.save()
        assert tmp_registry._cache_path.exists()

        # Create a new registry and load
        new_registry = ModelRegistry.__new__(ModelRegistry)
        new_registry._atomic_root = tmp_registry._atomic_root
        new_registry._state_dir = tmp_registry._state_dir
        new_registry._cache_path = tmp_registry._cache_path
        new_registry._models = {}
        new_registry._last_upstream_sync = None
        new_registry._last_probe = None
        new_registry.load()

        assert "anthropic:test" in new_registry._models
        loaded = new_registry._models["anthropic:test"]
        assert loaded.model_id == "test"
        assert loaded.provider_id == "anthropic"
        assert loaded.context_window == 200000
        assert loaded.tier == "sonnet"
        assert loaded.available is True
        assert new_registry._last_upstream_sync == "2025-01-01T00:00:00+00:00"
