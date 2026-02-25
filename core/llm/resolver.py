"""
Model Resolution Engine

Encapsulates all model selection logic into a single component.
The setup wizard configures it, orchestrators call it at task start,
and the dashboard reads its output.

Resolution hierarchy (first match wins):
  1. Explicit override   — caller passes tier directly
  2. Agent preference    — agent-manifest.json says model="opus"
  3. Phase role          — config says phase 2 uses "heavyweight" -> opus
  4. Task-type routing   — project config says "critical" -> cloud/primary
  5. Global default      — providers.models.primary -> "sonnet"
"""

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Claude Code fast mode (--fast / /fast) is STRICTLY FORBIDDEN.
# Subscription is fixed-cost — fast mode gives degraded output for the same
# price.  This flag is checked by any code that builds CLI invocations.
CLAUDE_CODE_FAST_MODE_FORBIDDEN = True


@dataclass(frozen=True)
class TaskRequirements:
    """What a task needs from its model — used for intelligent selection."""
    needs_extended_thinking: bool = False
    needs_vision: bool = False
    needs_tool_use: bool = False
    min_context_window: int = 0
    risk_budget: float = 0.0  # 0.0 = never downgrade, 1.0 = freely downgrade
    preferred_tier: Optional[str] = None  # From phase role resolution

    @staticmethod
    def for_phase_role(phase_id: str, task_id: str = None, graph=None) -> "TaskRequirements":
        """Factory: build requirements from phase role + graph risk budget.

        Uses the risk module to compute a risk budget from the knowledge graph.
        """
        risk_budget = 0.0
        if graph and task_id:
            try:
                from core.llm.risk import compute_risk_budget
                risk_budget = compute_risk_budget(task_id, graph)
            except Exception:
                pass
        return TaskRequirements(risk_budget=risk_budget)


@dataclass(frozen=True)
class ResolvedModel:
    """Result of model resolution — everything needed to invoke a model."""

    tier: str                                  # "opus", "sonnet", "haiku"
    model_id: str                              # Full model ID: "claude-opus-4-6", "anthropic.claude-sonnet-4-5-20250929-v1:0"
    role: str                                  # "primary", "fast", "heavyweight", "gardener"
    provider: Optional[str]                    # "claude-code", "anthropic", etc.
    context_window: int                        # 1_000_000, 200_000
    max_output: int                            # 32_000, 16_000, 8_192
    extended_thinking: bool                    # Whether model supports it
    thinking_budget: Optional[int]             # Token budget (None = not applicable)
    effort_level: Optional[str]                # "medium"/"high" (Claude Code); "low"/"medium"/"high" (API)
    fallback_tiers: List[str] = field(default_factory=list)
    source: str = "default"                    # "override" | "agent" | "phase_role" | "default"
    agent_name: Optional[str] = None           # Agent that influenced resolution
    phase_id: Optional[str] = None
    task_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ModelResolver:
    """Resolves the correct model for a given phase/task/agent combination.

    Loads three data sources:
      - config/models.json    — shipped tool defaults
      - .outputs/0-setup/project-config.json — user-configured project config
      - agents/agent-manifest.json — agent model preferences

    User overrides (set via the per-task roster display) are checked between
    explicit overrides and agent manifest preferences (Level 1.5).
    """

    def __init__(self, atomic_root: Path = None):
        self._atomic_root = atomic_root or Path(
            os.environ.get("ATOMIC_ROOT", Path.cwd())
        )
        self._defaults = self._load_tool_defaults()
        self._config = self._load_project_config()
        self._agents = self._load_agent_manifest()
        self._config_mtime: float = self._get_config_mtime()
        self._overrides: Dict[str, Dict[str, Optional[str]]] = {}      # Session-wide (persisted)
        self._task_overrides: Dict[str, Dict[str, Optional[str]]] = {}  # Task-scoped (in-memory)
        self._load_persisted_overrides()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_override(
        self,
        agent_name: str,
        tier: str = None,
        provider: str = None,
        model_id: str = None,
        context_window: int = None,
        effort_level: str = None,
        task_only: bool = False,
    ) -> None:
        """Set an override for an agent's model assignment.

        task_only=False: persists to .state/model-overrides.json (session-wide)
        task_only=True: in-memory only, cleared by clear_task_overrides()
        """
        entry = {
            "tier": tier, "provider": provider, "model_id": model_id,
            "context_window": context_window, "effort_level": effort_level,
        }
        if task_only:
            self._task_overrides[agent_name] = entry
        else:
            self._overrides[agent_name] = entry
            self._persist_overrides()

    def clear_task_overrides(self) -> None:
        """Clear all task-scoped overrides. Called by orchestrator after task."""
        self._task_overrides.clear()

    def clear_override(self, agent_name: str) -> None:
        """Remove a session-wide agent override."""
        self._overrides.pop(agent_name, None)
        self._persist_overrides()

    def _persist_overrides(self) -> None:
        """Write overrides to .state/model-overrides.json."""
        path = self._atomic_root / ".state" / "model-overrides.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._overrides, indent=2))

    def _load_persisted_overrides(self) -> None:
        """Load overrides from .state/model-overrides.json."""
        path = self._atomic_root / ".state" / "model-overrides.json"
        try:
            self._overrides = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as e:
            logger.debug("Could not load model overrides from %s: %s", path, e)
            self._overrides = {}

    def resolve(
        self,
        phase_id: str,
        task_id: str = None,
        agent_name: str = None,
        override_tier: str = None,
        override_role: str = None,
        requirements: TaskRequirements = None,
    ) -> ResolvedModel:
        """Main entry point.  Walks the 5-level hierarchy."""
        self._maybe_reload_config()

        # Level 1: Explicit override (caller passes tier directly)
        if override_tier:
            role = override_role or "primary"
            return self._build(
                override_tier, role=role, source="override",
                phase_id=phase_id, task_id=task_id,
            )

        # Level 1.5: User override (task-scoped first, then session-wide)
        if agent_name:
            ov = self._task_overrides.get(agent_name) or self._overrides.get(agent_name)
            if ov:
                tier = ov.get("tier") or (
                    self._agents.get(agent_name, {}).get("model", "sonnet")
                )
                return self._build(
                    tier, source="user_override",
                    agent_name=agent_name,
                    phase_id=phase_id, task_id=task_id,
                    override_provider=ov.get("provider"),
                    override_model_id=ov.get("model_id"),
                    override_context_window=ov.get("context_window"),
                    override_effort_level=ov.get("effort_level"),
                )

        # Level 2: Agent preference
        if agent_name and agent_name in self._agents:
            agent = self._agents[agent_name]
            if agent.get("model"):
                return self._build(
                    agent["model"], source="agent",
                    agent_name=agent_name,
                    phase_id=phase_id, task_id=task_id,
                )

        # Level 3: Phase role from project config (user-configured)
        #           falls back to config/models.json defaults
        phase_roles = self._get_phase_roles()
        role = phase_roles.get(phase_id)
        if role:
            tier = self._role_to_tier(role)
            return self._build(
                tier, role=role, source="phase_role",
                phase_id=phase_id, task_id=task_id,
            )

        # Level 4 / Level 5: Global default
        tier = self._role_to_tier("primary")

        # Intelligent downgrade: if risk_budget permits, try a cheaper tier
        if requirements and requirements.risk_budget > 0.0:
            provider_hint = (
                self._config.get("llm", {}).get("primary_provider")
                or os.environ.get("ATOMIC_LLM_PROVIDER")
                or self._detect_bootstrap_provider()
            )
            downgraded = self._maybe_downgrade(tier, provider_hint, requirements)
            if downgraded:
                tier = downgraded

        return self._build(
            tier, role="primary", source="default",
            phase_id=phase_id, task_id=task_id,
        )

    # ------------------------------------------------------------------
    # Intelligent downgrade helpers
    # ------------------------------------------------------------------

    def _is_zero_marginal_cost(self, provider: Optional[str] = None) -> bool:
        """Check if the active provider has zero marginal cost per token.

        Claude Code (subscription) and Ollama (local) never pay per-token,
        so downgrading gives worse output for the same price.
        """
        prov = (
            provider
            or self._config.get("llm", {}).get("primary_provider")
            or os.environ.get("ATOMIC_LLM_PROVIDER")
            or self._detect_bootstrap_provider()
        )
        return prov in ("claude-code", "ollama")

    def _maybe_downgrade(
        self,
        tier: str,
        provider: Optional[str],
        requirements: TaskRequirements,
    ) -> Optional[str]:
        """Attempt to downgrade tier based on risk budget.

        Returns a lower tier if safe, or None to keep current tier.

        Rules:
        - Zero-marginal-cost providers never downgrade
        - risk_budget < 0.3: no downgrade
        - risk_budget 0.3-0.7: opus -> sonnet
        - risk_budget > 0.7: opus -> haiku, sonnet -> haiku
        """
        if self._is_zero_marginal_cost(provider):
            return None

        budget = requirements.risk_budget

        if budget < 0.3:
            return None

        if budget <= 0.7:
            if tier == "opus":
                return "sonnet"
            return None

        # budget > 0.7
        if tier == "opus":
            return "haiku" if not requirements.needs_extended_thinking else "sonnet"
        if tier == "sonnet":
            return "haiku" if not requirements.needs_extended_thinking else None

        return None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_phase_roles(self) -> Dict[str, str]:
        """Phase roles from project config, falling back to config/models.json."""
        cfg_roles = (
            self._config
            .get("providers", {})
            .get("phase_roles", {})
        )
        if cfg_roles:
            return cfg_roles
        return self._defaults.get("phase_roles", {})

    def _role_to_tier(self, role: str) -> str:
        """Resolve role name to model tier, respecting provider overrides."""
        # Check project config first
        models = self._config.get("providers", {}).get("models", {})
        if role in models:
            return models[role]

        # Check provider-specific overrides in config/models.json
        provider = (
            self._config.get("llm", {}).get("primary_provider")
            or os.environ.get("ATOMIC_LLM_PROVIDER")
            or self._detect_bootstrap_provider()
        )
        if provider:
            overrides = (
                self._defaults
                .get("provider_overrides", {})
                .get(provider, {})
            )
            r2t = overrides.get("role_to_tier", {})
            if role in r2t:
                return r2t[role]

        # Base default from config/models.json
        return self._defaults.get("role_to_tier", {}).get(role, "sonnet")

    def _build(
        self,
        tier: str,
        role: str = "primary",
        source: str = "default",
        agent_name: str = None,
        phase_id: str = None,
        task_id: str = None,
        override_provider: str = None,
        override_model_id: str = None,
        override_context_window: int = None,
        override_effort_level: str = None,
    ) -> ResolvedModel:
        """Construct a ResolvedModel from a resolved tier."""
        provider = (
            override_provider
            or self._config.get("llm", {}).get("primary_provider")
            or os.environ.get("ATOMIC_LLM_PROVIDER")
            or self._detect_bootstrap_provider()
        )
        tier_def = self._defaults.get("tier_definitions", {}).get(tier, {})
        prov_overrides = (
            self._defaults
            .get("provider_overrides", {})
            .get(provider or "", {})
        )

        # Resolve full model ID from provider + tier (or use explicit override)
        model_id = override_model_id or self._resolve_model_id(tier, provider)

        context_window = tier_def.get("context_window", 200_000)
        # Provider can cap default context window (e.g. aws-bedrock 200K)
        # Heavyweight role (Phase 2) gets the full tier context window
        prov_ctx = prov_overrides.get("context_window")
        if prov_ctx and role != "heavyweight":
            context_window = prov_ctx
        # User override for context window
        if override_context_window:
            context_window = override_context_window
        max_output = tier_def.get("max_output", 8_192)
        ext_thinking = tier_def.get("extended_thinking", False)

        # Provider can disable extended thinking (e.g. Ollama)
        if prov_overrides.get("extended_thinking") is False:
            ext_thinking = False

        # Thinking budget: project config > provider override
        thinking_budget = (
            self._config.get("providers", {}).get("thinking_budget")
            or prov_overrides.get("thinking_budget")
        )

        # Effort level: project config > provider override > user override
        effort_level = (
            self._config.get("providers", {}).get("effort_level")
            or prov_overrides.get("effort_level")
        )
        if override_effort_level:
            effort_level = override_effort_level

        # GUARD: Enforce minimum effort level per provider.
        # Claude Code "low" effort is strictly forbidden — subscription is
        # fixed-cost, so "low" gives worse output for the same price.
        min_effort = prov_overrides.get("min_effort")
        if min_effort and effort_level:
            effort_rank = {"low": 0, "medium": 1, "high": 2}
            if effort_rank.get(effort_level, 0) < effort_rank.get(min_effort, 0):
                effort_level = min_effort

        # Fallback chain from config/models.json
        fallbacks = list(
            self._defaults.get("fallback_chains", {}).get(tier, [])
        )

        return ResolvedModel(
            tier=tier,
            model_id=model_id,
            role=role,
            provider=provider,
            context_window=context_window,
            max_output=max_output,
            extended_thinking=ext_thinking,
            thinking_budget=thinking_budget,
            effort_level=effort_level,
            fallback_tiers=fallbacks,
            source=source,
            agent_name=agent_name,
            phase_id=phase_id,
            task_id=task_id,
        )

    def _resolve_model_id(self, tier: str, provider: Optional[str]) -> str:
        """Look up the full model ID for a tier + provider combination.

        Checks: project config model_ids > config/models.json model_ids > tier shorthand.
        """
        # Check project config for custom model IDs
        cfg_model_ids = (
            self._config
            .get("providers", {})
            .get("model_ids", {})
        )
        if provider and provider in cfg_model_ids:
            mid = cfg_model_ids[provider].get(tier)
            if mid:
                return mid

        # Check config/models.json model_ids
        default_model_ids = self._defaults.get("model_ids", {})
        if provider and provider in default_model_ids:
            mid = default_model_ids[provider].get(tier)
            if mid:
                return mid

        # Fallback: use tier shorthand (e.g. "opus")
        return tier

    # ------------------------------------------------------------------
    # Config loading
    # ------------------------------------------------------------------

    def _maybe_reload_config(self) -> None:
        """Reload project config if file changed (handles Phase 0 bootstrap)."""
        current_mtime = self._get_config_mtime()
        if current_mtime != self._config_mtime:
            self._config = self._load_project_config()
            self._config_mtime = current_mtime

    def _get_config_mtime(self) -> float:
        """Get mtime of project config file, 0 if missing."""
        config_path = self._atomic_root.parent / ".outputs" / "0-setup" / "project-config.json"
        try:
            return config_path.stat().st_mtime
        except OSError:
            return 0

    def _load_tool_defaults(self) -> Dict[str, Any]:
        """Load config/models.json — shipped tool defaults."""
        config_path = self._atomic_root / "config" / "models.json"
        try:
            return json.loads(config_path.read_text())
        except (OSError, json.JSONDecodeError) as e:
            logger.debug("Could not load tool defaults from %s: %s", config_path, e)
            return {}

    def _load_project_config(self) -> Dict[str, Any]:
        """Load .outputs/0-setup/project-config.json -> extracted section."""
        config_path = self._atomic_root.parent / ".outputs" / "0-setup" / "project-config.json"
        try:
            data = json.loads(config_path.read_text())
            return data.get("extracted", {})
        except (OSError, json.JSONDecodeError) as e:
            logger.debug("Could not load project config from %s: %s", config_path, e)
            return {}

    def _load_agent_manifest(self) -> Dict[str, Dict[str, Any]]:
        """Load agents/agent-manifest.json, keyed by agent name."""
        manifest_path = self._atomic_root / "agents" / "agent-manifest.json"
        try:
            data = json.loads(manifest_path.read_text())
            agents = data.get("agents", [])
            return {a["name"]: a for a in agents if "name" in a}
        except (OSError, json.JSONDecodeError) as e:
            logger.debug("Could not load agent manifest from %s: %s", manifest_path, e)
            return {}

    def _detect_bootstrap_provider(self) -> Optional[str]:
        """Detect provider from environment before project config exists.

        Checked once and cached.  Used during Phase 0 bootstrap when no
        project-config.json has been written yet.
        """
        if hasattr(self, "_bootstrap_provider"):
            return self._bootstrap_provider

        import shutil

        # 1. claude CLI on PATH → subscription
        if shutil.which("claude"):
            self._bootstrap_provider = "claude-code"
            return self._bootstrap_provider

        # 2. Anthropic API key
        if os.environ.get("ANTHROPIC_API_KEY"):
            self._bootstrap_provider = "anthropic"
            return self._bootstrap_provider

        # 3. AWS credentials
        if os.environ.get("AWS_PROFILE") or os.environ.get("AWS_ACCESS_KEY_ID"):
            self._bootstrap_provider = "aws-bedrock"
            return self._bootstrap_provider

        # 4. .env file in project root
        env_file = self._atomic_root / ".env"
        if env_file.exists():
            try:
                text = env_file.read_text()
                if "ATOMIC_LLM_PROVIDER=claude-code" in text:
                    self._bootstrap_provider = "claude-code"
                    return self._bootstrap_provider
                if "ANTHROPIC_API_KEY=" in text:
                    self._bootstrap_provider = "anthropic"
                    return self._bootstrap_provider
                if "AWS_PROFILE=" in text or "CLAUDE_CODE_USE_BEDROCK=" in text:
                    self._bootstrap_provider = "aws-bedrock"
                    return self._bootstrap_provider
            except OSError as e:
                logger.debug("Could not read .env for bootstrap provider detection: %s", e)

        self._bootstrap_provider = None
        return None


# ------------------------------------------------------------------
# Module-level convenience (singleton)
# ------------------------------------------------------------------

_resolver: Optional[ModelResolver] = None


def get_resolver(atomic_root: Path = None) -> ModelResolver:
    """Return the singleton ModelResolver, creating it if needed."""
    global _resolver
    if _resolver is None:
        _resolver = ModelResolver(atomic_root)
    return _resolver


def resolve_model(
    phase_id: str,
    task_id: str = None,
    agent_name: str = None,
    requirements: "TaskRequirements" = None,
    **kwargs,
) -> ResolvedModel:
    """Convenience: resolve a model using the singleton resolver."""
    return get_resolver().resolve(phase_id, task_id, agent_name, requirements=requirements, **kwargs)


def reset_resolver() -> None:
    """Reset the singleton.  For tests and Phase 0 config reload."""
    global _resolver
    _resolver = None
