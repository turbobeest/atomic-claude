"""
Dynamic Model Registry

Syncs model metadata from models.dev upstream and provider availability probes.
Replaces static MODEL_CONTEXT_WINDOWS, MODEL_MAX_OUTPUT, PROVIDER_CAPABILITIES dicts
as the primary source of model information.
"""

import json
import logging
import os
import re
import shutil
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Upstream catalog URL
UPSTREAM_URL = "https://models.dev/api.json"

# Providers we care about from the upstream catalog
RELEVANT_PROVIDERS = {"anthropic", "amazon-bedrock", "aws-bedrock", "bedrock", "ollama"}

# Cache staleness threshold (seconds)
CACHE_MAX_AGE = 86400  # 24 hours

# Probe timeout (seconds)
PROBE_TIMEOUT = 5


@dataclass
class ModelRecord:
    """Single model's complete metadata."""
    model_id: str
    provider_id: str
    display_name: str = ""
    context_window: int = 200_000
    max_output: int = 4_096
    input_cost_per_mtok: Optional[float] = None
    output_cost_per_mtok: Optional[float] = None
    supports_extended_thinking: bool = False
    supports_tool_use: bool = False
    supports_vision: bool = False
    supports_streaming: bool = True
    supports_structured_output: bool = False
    tier: Optional[str] = None
    available: bool = False
    source: str = "upstream"  # "upstream" | "probed" | "manual"
    last_verified: Optional[str] = None

    def registry_key(self) -> str:
        return f"{self.provider_id}:{self.model_id}"


@dataclass
class RegistrySnapshot:
    """Complete registry state — serializable to .state/model-registry.json."""
    models: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    last_upstream_sync: Optional[str] = None
    last_probe: Optional[str] = None
    upstream_url: str = UPSTREAM_URL
    version: str = "1.0"


class ModelRegistry:
    """
    Dynamic model registry with upstream sync and provider probing.

    Usage:
        registry = ModelRegistry(atomic_root)
        registry.sync_upstream()
        registry.probe_providers()
        available = registry.get_available_models(provider="aws-bedrock")
    """

    def __init__(self, atomic_root: Path = None):
        self._atomic_root = atomic_root or Path(
            os.environ.get("ATOMIC_ROOT", Path.cwd())
        )
        self._state_dir = self._atomic_root / ".state"
        self._cache_path = self._state_dir / "model-registry.json"
        self._models: Dict[str, ModelRecord] = {}
        self._last_upstream_sync: Optional[str] = None
        self._last_probe: Optional[str] = None
        self.load()

    # ==================================================================
    # UPSTREAM SYNC
    # ==================================================================

    def sync_upstream(self, force: bool = False) -> int:
        """Fetch models.dev/api.json, parse, cache. Skip if cache <24h unless force.

        Returns:
            Number of models imported (0 if skipped or failed).
        """
        if not force and self._is_cache_fresh():
            logger.debug("Registry cache is fresh (age < 24h), skipping sync")
            return 0

        try:
            data = self._fetch_upstream()
        except Exception as e:
            logger.warning("Failed to fetch upstream registry: %s", e)
            # If we have cached data, keep using it
            if self._models:
                logger.info("Using cached registry data")
            return 0

        count = self._parse_upstream(data)
        self._last_upstream_sync = datetime.now(timezone.utc).isoformat()
        self.save()
        logger.info("Synced %d models from models.dev", count)
        return count

    def _is_cache_fresh(self) -> bool:
        """Check if cache is less than 24h old."""
        if not self._last_upstream_sync:
            return False
        try:
            sync_time = datetime.fromisoformat(self._last_upstream_sync)
            age = (datetime.now(timezone.utc) - sync_time).total_seconds()
            return age < CACHE_MAX_AGE
        except (ValueError, TypeError):
            return False

    def _fetch_upstream(self) -> Any:
        """Fetch models.dev/api.json."""
        req = urllib.request.Request(
            UPSTREAM_URL,
            headers={"User-Agent": "atomic-claude/2.0"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _parse_upstream(self, data: Any) -> int:
        """Parse models.dev response, filter to relevant providers.

        The models.dev API returns a flat list of model objects, each with
        provider, id, name, context_length, max_output_tokens, pricing, etc.
        We only import models from providers we care about.
        """
        count = 0
        # models.dev returns a dict keyed by model ID or a list — handle both
        models_list = data if isinstance(data, list) else data.get("data", [])
        if isinstance(data, dict) and not models_list:
            # Try flat dict format: {model_id: {provider, ...}}
            models_list = []
            for mid, info in data.items():
                if isinstance(info, dict):
                    info["id"] = mid
                    models_list.append(info)

        for entry in models_list:
            if not isinstance(entry, dict):
                continue

            provider = (entry.get("provider", {}).get("id", "")
                        if isinstance(entry.get("provider"), dict)
                        else str(entry.get("provider", "")))

            # Normalize provider names
            provider_lower = provider.lower()
            if not any(p in provider_lower for p in ("anthropic", "bedrock", "ollama")):
                continue

            model_id = entry.get("id", "") or entry.get("model", "")
            if not model_id:
                continue

            # Normalize provider to our naming convention
            if "bedrock" in provider_lower:
                norm_provider = "aws-bedrock"
            elif "ollama" in provider_lower:
                norm_provider = "ollama"
            else:
                norm_provider = "anthropic"

            # Extract capabilities
            caps = entry.get("capabilities", {})
            if isinstance(caps, list):
                caps = {c: True for c in caps}

            # Extract pricing
            pricing = entry.get("pricing", {})
            input_price = None
            output_price = None
            if isinstance(pricing, dict):
                raw_in = pricing.get("prompt") or pricing.get("input")
                raw_out = pricing.get("completion") or pricing.get("output")
                try:
                    if raw_in is not None:
                        input_price = float(raw_in) * 1_000_000  # per-token → per-Mtok
                    if raw_out is not None:
                        output_price = float(raw_out) * 1_000_000
                except (ValueError, TypeError):
                    pass
            elif entry.get("input_cost_per_token"):
                try:
                    input_price = float(entry["input_cost_per_token"]) * 1_000_000
                    output_price = float(entry.get("output_cost_per_token", 0)) * 1_000_000
                except (ValueError, TypeError):
                    pass

            record = ModelRecord(
                model_id=model_id,
                provider_id=norm_provider,
                display_name=entry.get("name", "") or entry.get("display_name", model_id),
                context_window=int(entry.get("context_length", 0)
                                   or entry.get("context_window", 0)
                                   or entry.get("max_input_tokens", 200_000)),
                max_output=int(entry.get("max_output_tokens", 0)
                               or entry.get("max_tokens", 4_096)),
                input_cost_per_mtok=input_price,
                output_cost_per_mtok=output_price,
                supports_extended_thinking=bool(
                    caps.get("reasoning") or caps.get("extended_thinking")
                    or entry.get("supports_extended_thinking")
                ),
                supports_tool_use=bool(
                    caps.get("tool_calling") or caps.get("tool_use") or caps.get("function_calling")
                ),
                supports_vision=bool(
                    caps.get("vision")
                    or "image" in str(entry.get("input_modalities", []))
                ),
                supports_streaming=bool(caps.get("streaming", True)),
                supports_structured_output=bool(
                    caps.get("structured_output") or caps.get("json_mode")
                ),
                tier=self.classify_tier(model_id),
                source="upstream",
            )

            key = record.registry_key()
            self._models[key] = record
            count += 1

        return count

    # ==================================================================
    # PROVIDER PROBING
    # ==================================================================

    def probe_providers(self, providers: List[str] = None) -> Dict[str, int]:
        """Run availability probes for configured providers.

        Args:
            providers: List of provider names to probe. Default: all.

        Returns:
            Dict mapping provider name to count of available models discovered.
        """
        all_providers = providers or ["claude-code", "anthropic", "aws-bedrock", "ollama"]
        results = {}

        for p in all_providers:
            try:
                if p == "claude-code":
                    results[p] = self._probe_claude_code()
                elif p == "anthropic":
                    results[p] = self._probe_anthropic_api()
                elif p == "aws-bedrock":
                    results[p] = self._probe_bedrock()
                elif p == "ollama":
                    results[p] = self._probe_ollama()
                else:
                    logger.debug("Unknown provider for probing: %s", p)
                    results[p] = 0
            except Exception as e:
                logger.warning("Probe failed for %s: %s", p, e)
                results[p] = 0

        self._last_probe = datetime.now(timezone.utc).isoformat()
        self.save()
        return results

    def _probe_claude_code(self) -> int:
        """Check if claude CLI is on PATH. If so, mark all Claude models available."""
        if not shutil.which("claude"):
            return 0

        # Claude Code subscription gives access to all Claude tiers
        count = 0
        for key, record in self._models.items():
            if record.provider_id == "anthropic":
                # Create a claude-code variant
                cc_key = f"claude-code:{record.model_id}"
                if cc_key not in self._models:
                    from dataclasses import replace
                    cc_record = replace(
                        record,
                        provider_id="claude-code",
                        available=True,
                        source="probed",
                        last_verified=datetime.now(timezone.utc).isoformat(),
                        input_cost_per_mtok=None,  # subscription = no per-token cost
                        output_cost_per_mtok=None,
                    )
                    self._models[cc_key] = cc_record
                else:
                    self._models[cc_key].available = True
                    self._models[cc_key].last_verified = datetime.now(timezone.utc).isoformat()
                count += 1

        # If no upstream models were loaded, add known Claude models manually
        if count == 0:
            for tier, model_id in [
                ("opus", "claude-opus-4-6"),
                ("sonnet", "claude-sonnet-4-5-20250929"),
                ("haiku", "claude-haiku-4-5-20251001"),
            ]:
                key = f"claude-code:{model_id}"
                self._models[key] = ModelRecord(
                    model_id=model_id,
                    provider_id="claude-code",
                    display_name=f"Claude {tier.title()}",
                    context_window=1_000_000 if tier == "opus" else 200_000,
                    max_output=32_000 if tier == "opus" else (16_000 if tier == "sonnet" else 8_192),
                    supports_extended_thinking=tier in ("opus", "sonnet"),
                    supports_tool_use=True,
                    supports_vision=True,
                    supports_streaming=True,
                    supports_structured_output=True,
                    tier=tier,
                    available=True,
                    source="probed",
                    last_verified=datetime.now(timezone.utc).isoformat(),
                )
                count += 1

        return count

    def _probe_anthropic_api(self) -> int:
        """Check for ANTHROPIC_API_KEY. Mark standard Claude models available."""
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return 0

        count = 0
        for key, record in list(self._models.items()):
            if record.provider_id == "anthropic":
                record.available = True
                record.last_verified = datetime.now(timezone.utc).isoformat()
                record.source = "probed"
                count += 1

        # If no upstream models loaded, add known models manually
        if count == 0:
            for tier, model_id in [
                ("opus", "claude-opus-4-6"),
                ("sonnet", "claude-sonnet-4-5-20250929"),
                ("haiku", "claude-haiku-4-5-20251001"),
            ]:
                key = f"anthropic:{model_id}"
                self._models[key] = ModelRecord(
                    model_id=model_id,
                    provider_id="anthropic",
                    display_name=f"Claude {tier.title()}",
                    context_window=1_000_000 if tier == "opus" else 200_000,
                    max_output=32_000 if tier == "opus" else (16_000 if tier == "sonnet" else 8_192),
                    input_cost_per_mtok=15.0 if tier == "opus" else (3.0 if tier == "sonnet" else 0.25),
                    output_cost_per_mtok=75.0 if tier == "opus" else (15.0 if tier == "sonnet" else 1.25),
                    supports_extended_thinking=tier in ("opus", "sonnet"),
                    supports_tool_use=True,
                    supports_vision=True,
                    supports_streaming=True,
                    supports_structured_output=True,
                    tier=tier,
                    available=True,
                    source="probed",
                    last_verified=datetime.now(timezone.utc).isoformat(),
                )
                count += 1

        return count

    def _probe_bedrock(self) -> int:
        """Use boto3 to list available Bedrock Anthropic models."""
        try:
            import boto3
        except ImportError:
            logger.debug("boto3 not available, skipping Bedrock probe")
            return 0

        try:
            region = os.environ.get("AWS_REGION", "us-east-1")
            client = boto3.client("bedrock", region_name=region)
            response = client.list_foundation_models(byProvider="Anthropic")
        except Exception as e:
            logger.debug("Bedrock probe failed: %s", e)
            return 0

        count = 0
        now = datetime.now(timezone.utc).isoformat()
        for summary in response.get("modelSummaries", []):
            model_id = summary.get("modelId", "")
            if not model_id:
                continue

            key = f"aws-bedrock:{model_id}"
            if key in self._models:
                self._models[key].available = True
                self._models[key].last_verified = now
                self._models[key].source = "probed"
            else:
                # Model not in upstream catalog — add from probe data
                self._models[key] = ModelRecord(
                    model_id=model_id,
                    provider_id="aws-bedrock",
                    display_name=summary.get("modelName", model_id),
                    context_window=200_000,
                    max_output=4_096,
                    tier=self.classify_tier(model_id),
                    available=True,
                    source="probed",
                    last_verified=now,
                )
            count += 1

        return count

    def _probe_ollama(self) -> int:
        """Query Ollama /api/tags for locally pulled models.

        Checks hosts in this order:
        1. OLLAMA_HOST env var (defaults to localhost:11434)
        2. ollama_hosts from .outputs/0-setup/secrets.json

        Aggregates model counts across all reachable hosts, deduplicating
        models that appear on multiple hosts.
        """
        # Build list of unique hosts to probe
        hosts_to_probe: list[str] = []
        env_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        hosts_to_probe.append(env_host)

        # Also check configured hosts from secrets.json
        # .outputs/ may be in atomic_root or its parent (project root)
        candidates = [
            self._atomic_root / ".outputs" / "0-setup" / "secrets.json",
            self._atomic_root.parent / ".outputs" / "0-setup" / "secrets.json",
        ]
        for secrets_path in candidates:
            try:
                if secrets_path.exists():
                    secrets_data = json.loads(secrets_path.read_text())
                    configured_hosts = secrets_data.get("ollama_hosts", [])
                    for h in configured_hosts:
                        normalized = h.rstrip("/")
                        if normalized not in hosts_to_probe:
                            hosts_to_probe.append(normalized)
                    break  # Found secrets, stop looking
            except Exception as e:
                logger.debug("Failed to read ollama_hosts from %s: %s", secrets_path, e)

        count = 0
        now = datetime.now(timezone.utc).isoformat()

        for host in hosts_to_probe:
            url = f"{host}/api/tags"
            try:
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=PROBE_TIMEOUT) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                logger.debug("Ollama probe failed for %s: %s", host, e)
                continue

            for model in data.get("models", []):
                name = model.get("name", "")
                if not name:
                    continue

                # Extract parameter size from details
                details = model.get("details", {})
                param_size = details.get("parameter_size", "")

                key = f"ollama:{name}"
                if key in self._models:
                    self._models[key].available = True
                    self._models[key].last_verified = now
                    self._models[key].source = "probed"
                else:
                    # Determine context window from parameter size heuristic
                    param_billions = self._parse_param_size(param_size)
                    ctx = 131_072 if param_billions >= 30 else 32_768

                    self._models[key] = ModelRecord(
                        model_id=name,
                        provider_id="ollama",
                        display_name=name,
                        context_window=ctx,
                        max_output=ctx // 4,
                        tier=self.classify_tier(name, param_size=param_size),
                        available=True,
                        source="probed",
                        last_verified=now,
                    )
                count += 1

        return count

    # ==================================================================
    # QUERIES
    # ==================================================================

    def get_available_models(
        self,
        provider: str = None,
        min_context: int = 0,
        needs_thinking: bool = False,
        needs_vision: bool = False,
        needs_tools: bool = False,
    ) -> List[ModelRecord]:
        """Filter registry by availability + requirements.

        Returns list sorted by context_window desc, then cost asc.
        """
        results = []
        for record in self._models.values():
            if not record.available:
                continue
            if provider and record.provider_id != provider:
                continue
            if min_context and record.context_window < min_context:
                continue
            if needs_thinking and not record.supports_extended_thinking:
                continue
            if needs_vision and not record.supports_vision:
                continue
            if needs_tools and not record.supports_tool_use:
                continue
            results.append(record)

        # Sort: context_window desc, then cost asc (None costs sort first = free)
        results.sort(key=lambda m: (
            -m.context_window,
            m.input_cost_per_mtok if m.input_cost_per_mtok is not None else -1,
        ))
        return results

    def get_model(self, provider: str, model_id: str) -> Optional[ModelRecord]:
        """Exact lookup by provider + model_id."""
        key = f"{provider}:{model_id}"
        return self._models.get(key)

    def find_by_model_id(self, model_id: str) -> Optional[ModelRecord]:
        """Find any record matching model_id (any provider). Prefers available."""
        matches = [r for r in self._models.values() if r.model_id == model_id]
        if not matches:
            return None
        available = [r for r in matches if r.available]
        return available[0] if available else matches[0]

    def get_best_for_tier(self, provider: str, tier: str) -> Optional[ModelRecord]:
        """Given a tier, return the best available model for that provider."""
        candidates = [
            r for r in self._models.values()
            if r.provider_id == provider and r.tier == tier and r.available
        ]
        if not candidates:
            return None
        # Prefer largest context window
        candidates.sort(key=lambda m: -m.context_window)
        return candidates[0]

    def get_best_available(self, provider: str) -> Optional[ModelRecord]:
        """Return the most capable available model for a provider."""
        candidates = [
            r for r in self._models.values()
            if r.provider_id == provider and r.available
        ]
        if not candidates:
            return None
        tier_rank = {"opus": 3, "sonnet": 2, "haiku": 1}
        candidates.sort(key=lambda m: (
            -tier_rank.get(m.tier, 0),
            -m.context_window,
        ))
        return candidates[0]

    def summarize_available(self) -> str:
        """Return a human-readable summary of available models."""
        by_provider: Dict[str, List[str]] = {}
        for record in self._models.values():
            if not record.available:
                continue
            prov = record.provider_id
            if prov not in by_provider:
                by_provider[prov] = []
            label = record.tier or record.model_id
            if label not in by_provider[prov]:
                by_provider[prov].append(label)

        parts = []
        for prov in sorted(by_provider.keys()):
            models = ", ".join(sorted(by_provider[prov]))
            parts.append(f"{prov} ({models})")
        return "Available: " + "; ".join(parts) if parts else "No models available"

    # ==================================================================
    # TIER CLASSIFICATION
    # ==================================================================

    @staticmethod
    def classify_tier(model_id: str, param_size: str = None) -> Optional[str]:
        """Derive tier from model ID or parameter count.

        Rules:
            - "opus" in ID → opus
            - "sonnet" in ID → sonnet
            - "haiku" in ID → haiku
            - Ollama: ≥65B → opus, 14B-64B → sonnet, <14B → haiku
        """
        mid = model_id.lower()
        if "opus" in mid:
            return "opus"
        if "sonnet" in mid:
            return "sonnet"
        if "haiku" in mid:
            return "haiku"

        # Ollama param-size heuristic
        if param_size:
            billions = ModelRegistry._parse_param_size(param_size)
            if billions >= 65:
                return "opus"
            elif billions >= 14:
                return "sonnet"
            elif billions > 0:
                return "haiku"

        return None

    @staticmethod
    def _parse_param_size(param_size: str) -> float:
        """Parse a parameter size string like '14B', '70B', '235B' to a float."""
        if not param_size:
            return 0.0
        match = re.search(r"([\d.]+)\s*[bB]", param_size)
        if match:
            return float(match.group(1))
        return 0.0

    # ==================================================================
    # PERSISTENCE
    # ==================================================================

    def save(self) -> None:
        """Write registry to .state/model-registry.json."""
        self._state_dir.mkdir(parents=True, exist_ok=True)
        snapshot = RegistrySnapshot(
            models={k: asdict(v) for k, v in self._models.items()},
            last_upstream_sync=self._last_upstream_sync,
            last_probe=self._last_probe,
        )
        try:
            self._cache_path.write_text(json.dumps(asdict(snapshot), indent=2))
        except OSError as e:
            logger.warning("Failed to save registry: %s", e)

    def load(self) -> None:
        """Load registry from .state/model-registry.json."""
        if not self._cache_path.exists():
            return
        try:
            data = json.loads(self._cache_path.read_text())
            self._last_upstream_sync = data.get("last_upstream_sync")
            self._last_probe = data.get("last_probe")
            for key, model_data in data.get("models", {}).items():
                self._models[key] = ModelRecord(**{
                    k: v for k, v in model_data.items()
                    if k in ModelRecord.__dataclass_fields__
                })
        except (OSError, json.JSONDecodeError, TypeError) as e:
            logger.debug("Failed to load registry cache: %s", e)


# ==================================================================
# Module-level singleton
# ==================================================================

_registry: Optional[ModelRegistry] = None


def get_registry(atomic_root: Path = None) -> Optional[ModelRegistry]:
    """Return the singleton ModelRegistry, creating if needed."""
    global _registry
    if _registry is None:
        try:
            _registry = ModelRegistry(atomic_root)
        except Exception as e:
            logger.debug("Failed to initialize model registry: %s", e)
            return None
    return _registry


def reset_registry() -> None:
    """Reset the singleton. For tests."""
    global _registry
    _registry = None
