"""
LLM-driven phase audit system.

Loads audit criteria from AUDIT-INVENTORY.csv, gathers phase deliverables,
and uses an LLM to evaluate compliance. Reports are saved as structured JSON.

Pipeline: curation → interactive plan (Textual TUI) → per-audit parallel
evaluation with Rich live progress → detailed findings → remediation loop.

Always non-blocking: returns True even when audits find issues.
"""

import csv
import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# Phase number → CSV column name mapping
PHASE_CSV_COLUMN = {
    1: "discovery",
    2: "prd",
    3: "task_decomposition",
    4: "specification",
    5: "implementation",
    6: "testing",
    7: "integration",
    8: "deployment",
    9: "post_production",
}

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

# Cap audits sent to LLM to control prompt size
MAX_AUDITS = 20

# Parallel evaluation settings
MAX_CONCURRENT = 5
MAX_REMEDIATION_ROUNDS = 3


# Audit category → agent manifest category mapping
AUDIT_AGENT_MAP = {
    "security-trust": "security-compliance",
    "architecture-design": "development-architecture",
    "requirements-specification": "03-validation",
    "risk-management": "performance-reliability",
    "documentation-knowledge": "documentation-content",
    "compliance-legal": "security-compliance",
    "compliance-governance": "security-compliance",
    "human-organizational": "business-operations",
    "testing-quality-assurance": "00-quality-assurance",
    "code-quality": "00-quality-assurance",
    "performance-efficiency": "performance-reliability",
    "reliability-resilience": "performance-reliability",
    "scalability-capacity": "performance-reliability",
    "observability-instrumentation": "performance-reliability",
    "operational-excellence": "cloud-infrastructure",
    "cloud-infrastructure": "cloud-infrastructure",
    "infrastructure-as-code": "cloud-infrastructure",
    "devops-ci-cd": "development-tooling",
    "developer-experience": "development-tooling",
    "configuration-management": "development-tooling",
    "dependency-supply-chain": "development-tooling",
    "api-integration": "backend-ecosystems",
    "data-state-management": "data-intelligence",
    "machine-learning-ai": "data-intelligence",
    "business-logic-domain": "business-operations",
    "cost-economics": "business-operations",
    "usability-interaction": "documentation-content",
    "accessibility-inclusion": "documentation-content",
    "seo-discoverability": "documentation-content",
    "internationalization-localization": "documentation-content",
    "emotional-design-trust": "documentation-content",
    "gamification-behavioral": "documentation-content",
    "ethical-societal": "business-operations",
    "blockchain-distributed-ledger": "blockchain-web3",
    "real-time-embedded": "embedded-hardware",
    "sensors-physical-systems": "sensing-perception",
    "signal-processing-data-acquisition": "signal-processing",
    "metaverse-immersive": "immersive-spatial",
    "quantum-computing": "data-intelligence",
    "legacy-migration": "backend-ecosystems",
    "vendor-third-party": "business-operations",
    "networking-telecom": "networking-telecom",
}

# Default fallback agent when no match found
_FALLBACK_AGENT = "agent-quality-auditor"

# Project root (core/audit.py → parent.parent)
_ATOMIC_ROOT = Path(__file__).parent.parent

# Cached agent manifest
_agent_manifest_cache: Optional[dict] = None

# Cached model config (config/models.json)
_model_config_cache: Optional[dict] = None


@dataclass
class AuditConfig:
    """Per-audit configuration for evaluation."""
    audit: dict
    agent: str = ""
    model: str = "sonnet"
    provider: str = "anthropic"
    context_window: int = 200000
    effort: str = "max"
    enabled: bool = True


@dataclass
class AuditEvaluation:
    """Result of evaluating a single audit."""
    audit_id: str
    audit_name: str
    category: str
    severity: str
    tier: str
    status: str           # pass/warn/fail
    model_used: str
    agent_used: str
    provider_used: str
    analysis: str         # full markdown report
    evidence: str         # specific deliverable references
    gaps: str             # what's missing
    recommendations: str  # actionable steps
    confidence: str       # high/medium/low
    duration_seconds: float
    error: Optional[str] = None


def _load_audit_inventory() -> list[dict]:
    """Load all rows from AUDIT-INVENTORY.csv."""
    csv_path = _ATOMIC_ROOT / "audits" / "AUDIT-INVENTORY.csv"
    if not csv_path.exists():
        return []
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _select_audits_for_phase(rows: list[dict], phase_num: int) -> list[dict]:
    """Filter and rank audits applicable to a phase."""
    col = PHASE_CSV_COLUMN.get(phase_num)
    if not col:
        return []

    applicable = [
        r for r in rows
        if r.get(col, "").strip().lower() == "yes"
    ]

    # Sort by severity (critical first)
    applicable.sort(
        key=lambda r: SEVERITY_ORDER.get(r.get("severity", "").strip().lower(), 99)
    )

    return applicable


def _build_audit_roster(audits: list[dict]) -> str:
    """Build a condensed one-line-per-audit roster for the curation prompt."""
    lines = []
    for a in audits:
        aid = a.get("audit_id", "unknown")
        name = a.get("audit_name", "Unnamed")
        sev = a.get("severity", "medium")
        cat = a.get("category", "unknown")
        lines.append(f"  {aid} | {sev} | {cat} | {name}")
    return "\n".join(lines)


def _build_curation_prompt(
    roster: str,
    deliverables: str,
    phase_num: int,
    phase_id: str,
    total_count: int,
) -> str:
    """Build the LLM prompt for audit curation."""
    return f"""You are selecting audits for Phase {phase_num} ({phase_id}).

Your job: read the phase deliverables, understand what was produced, then
handpick the specific audits most relevant to evaluating this output.
Select audits that provide multi-domain coverage (security, quality,
compliance, architecture, etc.) without redundancy. Prefer fewer, sharper
audits over a broad sweep.

PHASE DELIVERABLES:
{deliverables[:8000]}

AVAILABLE AUDITS ({total_count} total):
{roster}

Select 10-25 audits by audit_id. Respond with ONLY JSON (no fencing):
{{"selected": ["audit-id-1", "audit-id-2", ...], "rationale": "One paragraph explaining your multi-domain coverage strategy."}}"""


def _parse_curation_response(response: str) -> tuple[list[str], str]:
    """Parse curation LLM response. Returns (audit_ids, rationale)."""
    cleaned = response.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            ids = parsed.get("selected", [])
            rationale = parsed.get("rationale", "")
            if isinstance(ids, list) and ids:
                return [str(i) for i in ids], str(rationale)
    except (json.JSONDecodeError, TypeError):
        pass

    return [], ""


def _display_curated_selection(
    selected: list[dict],
    rationale: str,
) -> None:
    """Display LLM-curated audit selection grouped by category."""
    from collections import defaultdict

    by_cat: dict[str, list[dict]] = defaultdict(list)
    for a in selected:
        by_cat[a.get("category", "unknown")].append(a)

    print()
    print(f"  LLM recommends {len(selected)} audits across {len(by_cat)} domains:")
    print()
    idx = 1
    for cat, cat_audits in sorted(by_cat.items()):
        sev_counts = {}
        for a in cat_audits:
            s = a.get("severity", "medium")
            sev_counts[s] = sev_counts.get(s, 0) + 1
        sev_summary = ", ".join(f"{c} {s}" for s, c in sev_counts.items())
        print(f"    {cat} ({len(cat_audits)} audits: {sev_summary})")
        for a in cat_audits:
            print(f"      {idx:>2}. [{a.get('severity', '?'):>8}] {a.get('audit_name', 'Unnamed')}")
            idx += 1
    print()
    if rationale:
        print(f"  Rationale: {rationale}")
        print()


def _fallback_category_selection(audits: list[dict]) -> list[dict]:
    """Manual category picker — used when LLM curation is unavailable."""
    from collections import Counter

    cats = Counter(a.get("category", "unknown") for a in audits)
    ordered = cats.most_common()

    if not ordered:
        return audits

    print()
    print("  Available audit categories (LLM curation unavailable):")
    print()
    for i, (cat, count) in enumerate(ordered, 1):
        print(f"    {i:>2}. {cat:<35} ({count} audits)")
    print()
    print(f"       Total: {len(audits)} audits across {len(ordered)} categories")
    print()

    from core.utils.cli_ui import prompt_user, clear_input_buffer

    clear_input_buffer()
    choice = prompt_user("  Categories [all/skip/1,3,5]: ").strip().lower()

    if choice == "skip":
        return []
    if not choice or choice == "all":
        return audits

    selected_cats = set()
    for part in choice.split(","):
        part = part.strip()
        try:
            idx = int(part) - 1
            if 0 <= idx < len(ordered):
                selected_cats.add(ordered[idx][0])
        except ValueError:
            pass

    if not selected_cats:
        print("  No valid selection, using all categories")
        return audits

    filtered = [a for a in audits if a.get("category", "unknown") in selected_cats]
    print(f"  Selected {len(filtered)} audits from {len(selected_cats)} categories")
    return filtered


# ---------------------------------------------------------------------------
# Model Config & Provider Detection
# ---------------------------------------------------------------------------

def _load_model_config() -> dict:
    """Load config/models.json with module-level caching."""
    global _model_config_cache
    if _model_config_cache is not None:
        return _model_config_cache
    config_path = _ATOMIC_ROOT / "config" / "models.json"
    if config_path.exists():
        try:
            _model_config_cache = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.debug("Failed to load model config from %s: %s", config_path, e)
            _model_config_cache = {}
    else:
        _model_config_cache = {}
    return _model_config_cache


def _detect_default_provider() -> str:
    """Detect the configured LLM provider for audit defaults."""
    try:
        from core.config import Config
        config = Config()
        name = config.get("llm.primary_provider", "api")
    except Exception as e:
        logger.debug("Failed to detect default provider: %s", e)
        name = "api"
    _MAP = {
        "api": "anthropic", "max": "anthropic", "anthropic": "anthropic",
        "claude-code": "claude-code", "bedrock": "aws-bedrock", "ollama": "ollama",
    }
    return _MAP.get(name, "anthropic")


def _resolve_model_display(tier: str, provider: str) -> str:
    """Resolve tier + provider to a display-friendly model name.

    Uses config/models.json to show real model IDs instead of bare tier names.
    E.g. 'opus' + 'anthropic' → 'opus-4-6'
         'sonnet' + 'aws-bedrock' → 'sonnet-4-5-v1:0'
         'opus' + 'ollama' → 'opus (n/a)'
    """
    cfg = _load_model_config()
    model_ids = cfg.get("model_ids", {})
    provider_models = model_ids.get(provider, {})
    model_id = provider_models.get(tier)
    if not model_id:
        return f"{tier} (n/a)"
    # Shorten for table display
    short = model_id
    short = short.replace("anthropic.", "")
    short = short.replace("claude-", "")
    short = re.sub(r"-\d{8}-", "-", short)
    short = re.sub(r"-\d{8}$", "", short)
    return short


# ---------------------------------------------------------------------------
# Agent Assignment
# ---------------------------------------------------------------------------

def _load_agent_manifest() -> dict:
    """Load agent-manifest.json, cache on module."""
    global _agent_manifest_cache
    if _agent_manifest_cache is not None:
        return _agent_manifest_cache

    manifest_path = _ATOMIC_ROOT / "agents" / "agent-manifest.json"
    if not manifest_path.exists():
        _agent_manifest_cache = {}
        return _agent_manifest_cache

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        _agent_manifest_cache = data
    except Exception as e:
        logger.debug("Failed to load agent manifest: %s", e)
        _agent_manifest_cache = {}

    return _agent_manifest_cache


def _assign_agent(audit: dict) -> str:
    """Map audit category → best-matching agent from manifest."""
    manifest = _load_agent_manifest()
    agents = manifest.get("agents", [])
    if not agents:
        return _FALLBACK_AGENT

    audit_cat = audit.get("category", "")
    audit_subcat = audit.get("subcategory", "")
    target_agent_cat = AUDIT_AGENT_MAP.get(audit_cat, "")

    if not target_agent_cat:
        return _FALLBACK_AGENT

    # Find agents matching the target category
    matches = [a for a in agents if a.get("category") == target_agent_cat]
    if not matches:
        return _FALLBACK_AGENT

    # Prefer agents whose subcategory or name relates to audit subcategory
    if audit_subcat:
        subcat_lower = audit_subcat.lower().replace("-", " ")
        scored = []
        for a in matches:
            agent_sub = (a.get("subcategory", "") or "").lower().replace("-", " ")
            agent_name = (a.get("name", "") or "").lower().replace("-", " ")
            score = 0
            if subcat_lower in agent_sub or agent_sub in subcat_lower:
                score += 2
            # Check for word overlap
            sub_words = set(subcat_lower.split())
            name_words = set(agent_name.split())
            score += len(sub_words & name_words)
            scored.append((score, a))
        scored.sort(key=lambda x: (-x[0], x[1].get("name", "")))
        return scored[0][1].get("name", _FALLBACK_AGENT)

    # No subcategory preference — pick highest-scored agent in category
    matches.sort(key=lambda a: a.get("composite_score", 0), reverse=True)
    return matches[0].get("name", _FALLBACK_AGENT)


def _get_provider_default_tier(provider: str) -> str:
    """Return the default model tier for a provider from config/models.json."""
    config = _load_model_config()
    defaults = config.get("provider_defaults", {})
    prov_default = defaults.get(provider, {})
    return prov_default.get("tier", "opus")


def _build_audit_configs(audits: list[dict]) -> list[AuditConfig]:
    """Build AuditConfig list with agent assignments and provider-default model.

    Uses the best model tier for the active provider (from config/models.json
    provider_defaults). Sorts by category to match Step 1 display order.
    """
    provider = _detect_default_provider()
    model = _get_provider_default_tier(provider)
    configs = []
    for audit in audits:
        agent = _assign_agent(audit)
        configs.append(AuditConfig(
            audit=audit,
            agent=agent,
            model=model,
            provider=provider,
        ))
    # Sort by category then audit name — matches Step 1 display order
    configs.sort(key=lambda c: (
        c.audit.get("category", ""),
        c.audit.get("audit_name", ""),
    ))
    return configs


# ---------------------------------------------------------------------------
# Audit Plan Display (Textual TUI)
# ---------------------------------------------------------------------------

def _display_audit_plan(audit_configs: list[AuditConfig], phase_num: int) -> list[AuditConfig]:
    """
    Launch Textual TUI for interactive audit plan configuration.

    Returns user-confirmed configs (enabled only). Returns empty list if
    user skips. Falls back to non-interactive display on import error
    or when terminal does not support full-screen TUI.
    """
    import sys
    import os

    # Textual requires a real terminal (not a pipe or non-interactive context)
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("  (non-interactive terminal detected, using simple audit plan)")
        return _display_audit_plan_fallback(audit_configs)

    # Check if /dev/tty is accessible (Textual opens it directly)
    try:
        fd = os.open("/dev/tty", os.O_RDWR)
        os.close(fd)
    except OSError:
        print("  (/dev/tty unavailable, using simple audit plan)")
        return _display_audit_plan_fallback(audit_configs)

    try:
        from core.audit_plan_tui import AuditPlanApp

        app = AuditPlanApp(audit_configs=audit_configs, phase_num=phase_num)
        app.run()

        if app.user_skipped:
            return []

        return [c for c in audit_configs if c.enabled]
    except ImportError:
        print("  (textual not installed, using simple audit plan)")
        return _display_audit_plan_fallback(audit_configs)
    except Exception as e:
        import traceback
        print(f"  TUI error: {type(e).__name__}: {e}")
        traceback.print_exc()
        print("  Falling back to simple audit plan display")
        return _display_audit_plan_fallback(audit_configs)


def _display_audit_plan_fallback(audit_configs: list[AuditConfig]) -> list[AuditConfig]:
    """Non-interactive fallback when Textual is unavailable."""
    from collections import defaultdict

    by_cat: dict[str, list[AuditConfig]] = defaultdict(list)
    for c in audit_configs:
        by_cat[c.audit.get("category", "unknown")].append(c)

    print()
    print(f"  Audit Plan: {len(audit_configs)} audits across {len(by_cat)} domains")
    print()
    idx = 1
    for cat, configs in sorted(by_cat.items()):
        print(f"    {cat}:")
        for c in configs:
            sev = c.audit.get("severity", "?")
            name = c.audit.get("audit_name", "Unnamed")
            print(f"      {idx:>2}. [{sev:>8}] {name}  ({c.agent} / {c.model})")
            idx += 1
    print()

    from core.utils.cli_ui import prompt_user, clear_input_buffer
    clear_input_buffer()
    choice = prompt_user("  [enter] run all / [s] skip: ").strip().lower()

    if choice == "s" or choice == "skip":
        return []
    return audit_configs


# ---------------------------------------------------------------------------
# Per-Audit Deep Evaluation (Stage 2)
# ---------------------------------------------------------------------------

def _build_single_audit_prompt(
    audit_config: AuditConfig,
    deliverables: str,
    phase_num: int,
    phase_id: str,
) -> str:
    """Build a focused evaluation prompt for ONE audit.

    Asks the LLM to produce free-form markdown — no JSON constraints.
    The audit agent writes whatever structure makes sense for this type
    of audit (code review, PRD review, architecture review, etc.).
    A separate haiku summarization pass extracts structured verdicts.
    """
    a = audit_config.audit
    return f"""You are a {audit_config.agent} evaluating Phase {phase_num} ({phase_id}) deliverables.

# Audit: {a.get('audit_name', 'Unnamed')}
- **ID**: {a.get('audit_id', 'unknown')}
- **Category**: {a.get('category', 'unknown')} / {a.get('subcategory', '')}
- **Severity**: {a.get('severity', 'medium')}
- **Tier**: {a.get('tier', 'expert')}

Evaluate this single audit criterion against the phase deliverables below.
Write your audit report as **markdown** — use whatever structure best fits
this type of audit (narrative analysis, checklist, code review, etc.).

Your report should cover:
- **Analysis**: Thorough evaluation (cite specific evidence from deliverables)
- **Findings**: What you found — both strengths and weaknesses
- **Gaps**: What is missing or inadequate
- **Recommendations**: Actionable steps, ordered by priority

End your report with a single verdict line in exactly this format:
`VERDICT: PASS|WARN|FAIL — <one-sentence rationale>`

## Phase Deliverables

{deliverables[:12000]}"""


def _extract_verdict(response: str) -> str:
    """Extract VERDICT line from markdown audit response.

    Looks for 'VERDICT: PASS|WARN|FAIL' anywhere in the response.
    Returns 'pass', 'warn', or 'fail'. Defaults to 'warn' if not found.
    """
    match = re.search(
        r"VERDICT:\s*(PASS|WARN|FAIL)",
        response,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).lower()
    # Heuristic fallback: look for strong signals in the text
    lower = response.lower()
    if "no issues" in lower or "fully compliant" in lower or "all requirements met" in lower:
        return "pass"
    if "critical" in lower and ("missing" in lower or "absent" in lower or "failure" in lower):
        return "fail"
    return "warn"


def _parse_single_audit_response(response: str, audit_config: AuditConfig) -> AuditEvaluation:
    """Convert a free-form markdown audit response into AuditEvaluation.

    The full markdown is stored in `analysis`. The verdict is extracted
    from the VERDICT line. No JSON parsing — the LLM writes freely.
    """
    a = audit_config.audit
    status = _extract_verdict(response)

    return AuditEvaluation(
        audit_id=a.get("audit_id", "unknown"),
        audit_name=a.get("audit_name", "Unnamed"),
        category=a.get("category", "unknown"),
        severity=a.get("severity", "medium"),
        tier=a.get("tier", "expert"),
        status=status,
        model_used=audit_config.model,
        agent_used=audit_config.agent,
        provider_used=audit_config.provider,
        analysis=response.strip(),
        evidence="",
        gaps="",
        recommendations="",
        confidence="medium",
        duration_seconds=0.0,
    )


def _evaluate_worker(
    audit_config: AuditConfig,
    deliverables: str,
    phase_num: int,
    phase_id: str,
) -> AuditEvaluation:
    """Evaluate a single audit (runs in thread pool). Never raises."""
    start = time.monotonic()
    try:
        from core.llm.invoke import invoke_llm

        prompt = _build_single_audit_prompt(
            audit_config, deliverables, phase_num, phase_id
        )
        response = invoke_llm(prompt=prompt, model=audit_config.model)
        evaluation = _parse_single_audit_response(response, audit_config)
        evaluation.duration_seconds = time.monotonic() - start
        return evaluation
    except Exception as e:
        a = audit_config.audit
        return AuditEvaluation(
            audit_id=a.get("audit_id", "unknown"),
            audit_name=a.get("audit_name", "Unnamed"),
            category=a.get("category", "unknown"),
            severity=a.get("severity", "medium"),
            tier=a.get("tier", "expert"),
            status="warn",
            model_used=audit_config.model,
            agent_used=audit_config.agent,
            provider_used=audit_config.provider,
            analysis="",
            evidence="",
            gaps="",
            recommendations="",
            confidence="low",
            duration_seconds=time.monotonic() - start,
            error=str(e),
        )


# ---------------------------------------------------------------------------
# Parallel Execution with Rich Live Progress (Stage 3)
# ---------------------------------------------------------------------------

def _run_parallel_evaluations(
    audit_configs: list[AuditConfig],
    deliverables: str,
    phase_num: int,
    phase_id: str,
    round_label: str = "",
) -> list[AuditEvaluation]:
    """Run audit evaluations in parallel with Rich live progress display."""
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
    from rich.table import Table
    from rich.text import Text

    console = Console()
    total = len(audit_configs)
    evaluations: list[Optional[AuditEvaluation]] = [None] * total

    # Status display constants
    STATUS_ICON = {"pass": "✅", "warn": "⚠️ ", "fail": "❌"}
    STATUS_LABEL = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}

    def _build_full_display() -> Panel:
        """Build complete display with summary + table."""
        completed = sum(1 for e in evaluations if e is not None)
        passed = sum(1 for e in evaluations if e and e.status == "pass")
        warned = sum(1 for e in evaluations if e and e.status == "warn")
        failed = sum(1 for e in evaluations if e and e.status == "fail")

        pct = int(completed / total * 100) if total else 100
        bar_filled = int(pct / 100 * 30)
        bar = "█" * bar_filled + "░" * (30 - bar_filled)

        lines = []
        lines.append("")
        if completed < total:
            lines.append(f"  {completed}/{total} complete   "
                         f"{passed} passed   {warned} warnings   {failed} failed")
            lines.append(f"  ⠸ Evaluating {bar} {pct}%")
        else:
            lines.append(f"  {completed}/{total} complete   "
                         f"{passed} passed   {warned} warnings   {failed} failed")
            lines.append(f"  ✓ Complete {bar} {pct}%")
        lines.append("")

        # Table header
        lines.append(
            f"  {'#':>3}  {'Status':<10} {'Sev':<8} {'Agent':<24} "
            f"{'Model':<18} {'Provider':<12} {'Category':<18} {'Audit':<30} {'Time':>8}"
        )

        for i, cfg in enumerate(audit_configs):
            a = cfg.audit
            ev = evaluations[i]
            num = f"{i+1:>3}"
            sev = a.get("severity", "?")[:8]
            agent = cfg.agent[:24]
            model = _resolve_model_display(cfg.model, cfg.provider)
            if len(model) > 17:
                model = model[:15] + "…"
            provider = cfg.provider[:12]
            cat = a.get("category", "?")
            if len(cat) > 17:
                cat = cat[:15] + "…"
            name = a.get("audit_name", "Unnamed")
            if len(name) > 29:
                name = name[:27] + "…"

            if ev is not None:
                icon = STATUS_ICON.get(ev.status, "?")
                label = STATUS_LABEL.get(ev.status, "?")
                status_text = f"{icon} {label}"
                time_text = f"{ev.duration_seconds:.1f}s"
            else:
                status_text = "...      "
                time_text = ""

            lines.append(
                f"  {num}  {status_text:<10} {sev:<8} {agent:<24} "
                f"{model:<18} {provider:<12} {cat:<18} {name:<30} {time_text:>8}"
            )

        lines.append("")
        title = f"Phase {phase_num} Audit Evaluation"
        if round_label:
            title += f" — {round_label}"
        return Panel("\n".join(lines), title=title)

    with Live(_build_full_display(), console=console, refresh_per_second=2) as live:
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as executor:
            future_to_idx = {}
            for i, cfg in enumerate(audit_configs):
                future = executor.submit(
                    _evaluate_worker, cfg, deliverables, phase_num, phase_id
                )
                future_to_idx[future] = i

            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                evaluations[idx] = future.result()
                live.update(_build_full_display())

    return [e for e in evaluations if e is not None]


# ---------------------------------------------------------------------------
# Results Display (Stage 4)
# ---------------------------------------------------------------------------

def _audit_report_filename(ev: AuditEvaluation) -> str:
    """Consistent filename for an audit's markdown report."""
    safe_name = re.sub(r"[^a-z0-9]+", "-", ev.audit_name.lower()).strip("-")
    return f"{ev.audit_id}-{safe_name}.md"


def _save_audit_markdowns(
    evaluations: list[AuditEvaluation],
    phase_num: int,
) -> Path:
    """Save each audit's full markdown report to disk.

    Returns the audit directory path for reference.
    """
    audit_dir = _ATOMIC_ROOT.parent / ".outputs" / "audits" / f"phase-{phase_num}"
    audit_dir.mkdir(parents=True, exist_ok=True)

    for e in evaluations:
        md_path = audit_dir / _audit_report_filename(e)
        model_display = _resolve_model_display(e.model_used, e.provider_used)
        header = (
            f"# {e.audit_name}\n\n"
            f"- **Status**: {e.status.upper()}\n"
            f"- **Category**: {e.category}\n"
            f"- **Severity**: {e.severity}\n"
            f"- **Agent**: {e.agent_used}\n"
            f"- **Model**: {model_display} ({e.provider_used})\n"
            f"- **Duration**: {e.duration_seconds:.1f}s\n\n---\n\n"
        )
        md_path.write_text(header + e.analysis, encoding="utf-8")

    return audit_dir


def _save_audit_report(
    evaluations: list[AuditEvaluation],
    phase_num: int,
    phase_id: str,
    audit_dir: Path,
) -> None:
    """Save JSON summary report and print final summary line."""
    passed = sum(1 for e in evaluations if e.status == "pass")
    warnings = sum(1 for e in evaluations if e.status == "warn")
    failed = sum(1 for e in evaluations if e.status == "fail")

    if failed > 0:
        overall = "FAIL"
    elif warnings > 0:
        overall = "WARNING"
    else:
        overall = "PASS"

    report = {
        "phase_num": phase_num,
        "phase_id": phase_id,
        "overall_status": overall,
        "summary": {"passed": passed, "warnings": warnings, "failed": failed},
        "evaluations": [
            {
                "audit_id": e.audit_id,
                "audit_name": e.audit_name,
                "category": e.category,
                "severity": e.severity,
                "status": e.status,
                "model_used": e.model_used,
                "provider_used": e.provider_used,
                "agent_used": e.agent_used,
                "confidence": e.confidence,
                "duration_seconds": e.duration_seconds,
                "report_file": _audit_report_filename(e),
            }
            for e in evaluations
        ],
        # Backward-compatible results array
        "results": [
            {
                "audit_id": e.audit_id,
                "status": e.status,
                "finding": (e.analysis[:200] + "...") if len(e.analysis) > 200 else e.analysis,
            }
            for e in evaluations
        ],
    }

    report_path = audit_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2))

    print(f"  ─── Summary ─────────────────────────────────────────────────")
    print(f"  Phase {phase_num} audit: {overall} "
          f"({passed} passed, {warnings} warnings, {failed} failed)")
    print(f"  Reports: {audit_dir}/")
    print()


def _display_rich_results(
    evaluations: list[AuditEvaluation],
    phase_num: int,
    audit_dir: Optional[Path] = None,
    round_label: str = "",
    prev_evaluations: list[AuditEvaluation] | None = None,
) -> None:
    """Display compact audit results — one line per audit with file references.

    Full analysis lives in the markdown files. Terminal shows just the
    verdict, category, and where to read the details.

    When prev_evaluations is provided, shows a delta column indicating
    what improved, regressed, or stayed the same since the previous round.
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()

    passed = sum(1 for e in evaluations if e.status == "pass")
    warned = sum(1 for e in evaluations if e.status == "warn")
    failed = sum(1 for e in evaluations if e.status == "fail")
    total_time = sum(e.duration_seconds for e in evaluations)

    STATUS_ICON = {"pass": "✅", "warn": "⚠️ ", "fail": "❌"}
    STATUS_RANK = {"pass": 2, "warn": 1, "fail": 0}

    # Build prev lookup for delta display
    prev_by_id = {}
    if prev_evaluations:
        prev_by_id = {e.audit_id: e for e in prev_evaluations}

    # Compact table — every audit in one table
    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("#", width=4, justify="right")
    table.add_column("Result", width=10)
    if prev_by_id:
        table.add_column("Delta", width=6)
    table.add_column("Sev", width=8)
    table.add_column("Category", width=20, no_wrap=True)
    table.add_column("Audit", no_wrap=True)
    table.add_column("Time", width=7, justify="right")

    improved = 0
    regressed = 0
    unchanged = 0

    for i, ev in enumerate(evaluations):
        icon = STATUS_ICON.get(ev.status, "?")
        label = ev.status.upper()
        cat = ev.category
        if len(cat) > 19:
            cat = cat[:17] + "…"

        row = [
            str(i + 1),
            f"{icon} {label}",
        ]

        if prev_by_id:
            prev = prev_by_id.get(ev.audit_id)
            if prev:
                cur_rank = STATUS_RANK.get(ev.status, 0)
                prev_rank = STATUS_RANK.get(prev.status, 0)
                if cur_rank > prev_rank:
                    row.append("  ↑")
                    improved += 1
                elif cur_rank < prev_rank:
                    row.append("  ↓")
                    regressed += 1
                else:
                    row.append("  ·")
                    unchanged += 1
            else:
                row.append("  ★")  # new audit (wasn't in previous)

        row.extend([
            ev.severity,
            cat,
            ev.audit_name,
            f"{ev.duration_seconds:.1f}s",
        ])
        table.add_row(*row)

    title = "Audit Results"
    if round_label:
        title += f" — {round_label}"

    summary = (
        f"  Passed: {passed}   Warnings: {warned}   Failed: {failed}   "
        f"Total time: {total_time:.1f}s"
    )
    if prev_by_id:
        summary += f"\n  Delta: {improved} improved ↑   {regressed} regressed ↓   {unchanged} unchanged ·"

    console.print()
    console.print(Panel(summary, title=title))
    console.print(table)

    if audit_dir:
        console.print(f"\n  Full reports: {audit_dir}/")
    console.print()


# ---------------------------------------------------------------------------
# Resume from Existing Results
# ---------------------------------------------------------------------------

def _load_existing_evaluations(
    phase_num: int,
) -> tuple[list[AuditEvaluation], list[AuditConfig]]:
    """Load audit evaluations from a previous run's report.json + markdown files.

    Returns (evaluations, audit_configs) or ([], []) if no prior results exist.
    Used to resume the remediation loop without re-running all LLM evaluations.
    """
    audit_dir = _ATOMIC_ROOT.parent / ".outputs" / "audits" / f"phase-{phase_num}"
    report_path = audit_dir / "report.json"

    if not report_path.exists():
        return [], []

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.debug("Failed to load audit report from %s: %s", report_path, e)
        return [], []

    eval_entries = report.get("evaluations", [])
    if not eval_entries:
        return [], []

    evaluations = []
    configs = []

    for entry in eval_entries:
        # Read full markdown analysis from saved report file
        report_file = entry.get("report_file", "")
        md_path = audit_dir / report_file
        analysis = ""
        if md_path.exists():
            try:
                raw = md_path.read_text(encoding="utf-8")
                # Strip the metadata header (everything before "---\n\n")
                marker = "---\n\n"
                idx = raw.find(marker)
                analysis = raw[idx + len(marker):] if idx >= 0 else raw
            except Exception as e:
                logger.debug("Failed to read audit analysis from %s: %s", md_path, e)

        ev = AuditEvaluation(
            audit_id=entry.get("audit_id", "unknown"),
            audit_name=entry.get("audit_name", "Unnamed"),
            category=entry.get("category", "unknown"),
            severity=entry.get("severity", "medium"),
            tier="expert",
            status=entry.get("status", "warn"),
            model_used=entry.get("model_used", ""),
            agent_used=entry.get("agent_used", ""),
            provider_used=entry.get("provider_used", ""),
            analysis=analysis,
            evidence="",
            gaps="",
            recommendations="",
            confidence=entry.get("confidence", "medium"),
            duration_seconds=entry.get("duration_seconds", 0.0),
        )
        evaluations.append(ev)

        # Rebuild minimal AuditConfig for re-audit in remediation loop
        audit_dict = {
            "audit_id": entry.get("audit_id", "unknown"),
            "audit_name": entry.get("audit_name", "Unnamed"),
            "category": entry.get("category", "unknown"),
            "severity": entry.get("severity", "medium"),
        }
        configs.append(AuditConfig(
            audit=audit_dict,
            agent=entry.get("agent_used", ""),
            model=entry.get("model_used", "sonnet"),
            provider=entry.get("provider_used", "anthropic"),
        ))

    return evaluations, configs


# ---------------------------------------------------------------------------
# AI-Automated Remediation (Stage 5a)
# ---------------------------------------------------------------------------

def _extract_remediation_guidance(
    evaluations: list[AuditEvaluation],
    failures_only: bool = False,
) -> str:
    """Extract Gaps and Recommendations sections from failed/warned audit reports.

    Handles both numbered (## 3. Gaps) and unnumbered (## Gaps) heading styles.
    Falls back to last 1000 chars of analysis if headings not found.
    Caps total output at 30K chars.

    Args:
        evaluations: List of audit evaluations
        failures_only: If True, only extract guidance from failures (skip warnings)
    """
    MAX_GUIDANCE_CHARS = 30_000
    heading_pattern = re.compile(
        r"^##\s*(?:\d+\.?\s*)?(Gaps|Recommendations)\b",
        re.MULTILINE | re.IGNORECASE,
    )
    # Next heading pattern to find section boundaries
    next_heading = re.compile(r"^##\s", re.MULTILINE)

    target_statuses = ("fail",) if failures_only else ("fail", "warn")

    parts: list[str] = []
    total = 0

    for ev in evaluations:
        if ev.status not in target_statuses:
            continue
        if not ev.analysis:
            continue

        sections: list[str] = []
        for match in heading_pattern.finditer(ev.analysis):
            start = match.start()
            # Find next heading after this one
            rest = ev.analysis[match.end():]
            end_match = next_heading.search(rest)
            if end_match:
                end = match.end() + end_match.start()
            else:
                end = len(ev.analysis)
            sections.append(ev.analysis[start:end].strip())

        if sections:
            excerpt = "\n\n".join(sections)
        else:
            # Fallback: last 1000 chars
            excerpt = ev.analysis[-1000:]

        chunk = (
            f"### [{ev.status.upper()}] {ev.audit_name} ({ev.category})\n"
            f"{excerpt}\n"
        )

        if total + len(chunk) > MAX_GUIDANCE_CHARS:
            break
        parts.append(chunk)
        total += len(chunk)

    return "\n".join(parts)


def _build_remediation_prompt(
    guidance: str,
    deliverables: str,
    output_dir: Path,
    atomic_root: Path | None = None,
    project_root: Path | None = None,
) -> str:
    """Build prompt for LLM to fix deliverables based on audit findings."""
    file_layout = ""
    if atomic_root or project_root:
        file_layout = "\n## File Layout\n\n"
        file_layout += f"- Phase output artifacts: {output_dir} (use paths relative to this dir)\n"
        if atomic_root:
            file_layout += (
                f"- Pipeline source code: {atomic_root}/phases/, {atomic_root}/core/\n"
                f"- Tests: {atomic_root}/tests/\n"
            )
        if project_root:
            file_layout += (
                f"- Project deliverables: {project_root}/.taskmaster/, {project_root}/docs/\n"
            )
        file_layout += (
            "\nUse paths relative to the appropriate root. For example:\n"
            "- To fix task decomposition code: phases/phase_03_tasking/tasks/task_303_task_decomposition.py\n"
            "- To fix the task list: .taskmaster/tasks/tasks.json\n"
            "- To fix a phase output artifact: raw-tasks.json (relative to output dir)\n"
        )

    return f"""You are a senior engineer fixing deliverables based on audit findings.

CRITICAL: You MUST output your fixes using the exact delimited format shown below.
Do NOT use markdown code blocks. Do NOT write prose without file blocks.

## Required Output Format

For EACH file you modify or create, output exactly:

=== FILE: relative/path/to/file ===
<complete file content here>
=== END FILE ===

After all file blocks, output:

=== SUMMARY ===
<brief description of what you changed and why>
=== END SUMMARY ===

Example (fixing a JSON deliverable):

=== FILE: openspec-generation.json ===
{{
  "status": "complete",
  "specs_generated": 118,
  "security_coverage": "threat-model included"
}}
=== END FILE ===

=== SUMMARY ===
Added security_coverage field to address missing threat model audit finding.
=== END SUMMARY ===

---

## Audit Findings (Gaps & Recommendations)

{guidance}

## Current Deliverables

{deliverables}
{file_layout}
## Instructions

Fix the deliverables to address the audit gaps and recommendations above.

Rules:
- Only modify files that need changes to address audit findings
- Preserve correct existing content (do NOT regress passing audits)
- You may create new files if recommendations call for missing deliverables
- Use placeholder `[TODO: description]` for information you cannot determine
- Be thorough but precise — fix what the audits flag, nothing more
- For pipeline source files, use paths starting with phases/, core/, tests/ etc.
- For project deliverables, use paths starting with .taskmaster/, docs/, src/ etc.
- For phase output artifacts, use bare filenames (relative to output dir)

REMINDER: You MUST use === FILE: path === and === END FILE === delimiters for every file you output."""


def _parse_remediation_response(response: str) -> tuple[dict[str, str], str]:
    """Parse LLM remediation response into file updates and summary.

    Primary: extracts === FILE: path === ... === END FILE === blocks.
    Fallback: extracts ```lang\n// path: ...\n or ```lang:path blocks.
    Returns ({path: content}, summary). Returns ({}, "") on parse failure.
    """
    file_pattern = re.compile(
        r"===\s*FILE:\s*(.+?)\s*===\s*\n(.*?)\n===\s*END FILE\s*===",
        re.DOTALL,
    )
    summary_pattern = re.compile(
        r"===\s*SUMMARY\s*===\s*\n(.*?)\n===\s*END SUMMARY\s*===",
        re.DOTALL,
    )

    files: dict[str, str] = {}
    for match in file_pattern.finditer(response):
        path = match.group(1).strip()
        content = match.group(2)
        if path:
            files[path] = content

    # Fallback: extract from markdown code blocks with file paths
    if not files:
        # Pattern 1: ```lang\n// FILE: path\n or // path: ...\n
        fb1 = re.compile(
            r"```\w*\s*\n"
            r"(?://|#)\s*(?:FILE|file|path):\s*(.+?)\s*\n"
            r"(.*?)"
            r"\n```",
            re.DOTALL,
        )
        for match in fb1.finditer(response):
            path = match.group(1).strip()
            content = match.group(2)
            if path:
                files[path] = content

    # Fallback 2: ```lang:filename\n...\n```
    if not files:
        fb2 = re.compile(
            r"```\w+:(\S+)\s*\n(.*?)\n```",
            re.DOTALL,
        )
        for match in fb2.finditer(response):
            path = match.group(1).strip()
            content = match.group(2)
            if path:
                files[path] = content

    summary = ""
    summary_match = summary_pattern.search(response)
    if summary_match:
        summary = summary_match.group(1).strip()

    return files, summary


def _classify_remediation_path(rel_path: str) -> str:
    """Classify a remediation file path to its target root.

    Returns: 'atomic' | 'project' | 'output'
    """
    parts = Path(rel_path).parts
    if not parts:
        return "output"
    first = parts[0]
    if first in ("phases", "core", "orchestration", "tests", "agents", "audits", "skills"):
        return "atomic"
    if first in (".taskmaster", "docs", "src", "lib", "config"):
        return "project"
    return "output"


def _safe_write(target: Path, resolved_base: Path, content: str) -> int:
    """Write content to target if it resolves within resolved_base.

    Returns new file size in bytes, or -1 if path traversal was rejected.
    """
    resolved_target = target.resolve()
    if not str(resolved_target).startswith(str(resolved_base)):
        return -1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return len(content.encode("utf-8"))


def _apply_remediation(
    file_updates: dict[str, str],
    output_dir: Path,
    project_root: Path | None = None,
    atomic_root: Path | None = None,
) -> list[tuple[str, int, int, str]]:
    """Write remediation file updates to disk.

    Files are ALWAYS written to output_dir (so re-audit sees them).
    Additionally, files are written to their canonical location based on
    path classification:
    - phases/, core/, tests/ etc. → atomic_root (pipeline source)
    - .taskmaster/, docs/, src/ etc. → project_root (project deliverables)
    - everything else → output_dir only

    Safety: each target root is validated independently (no traversal escape).
    Returns [(relative_path, old_size, new_size, target_label), ...].
    """
    changes: list[tuple[str, int, int, str]] = []
    resolved_output = output_dir.resolve()
    resolved_atomic = atomic_root.resolve() if atomic_root else None
    resolved_project = project_root.resolve() if project_root else None

    for rel_path, content in file_updates.items():
        # Always write to output_dir
        output_target = (output_dir / rel_path).resolve()
        if not str(output_target).startswith(str(resolved_output)):
            continue

        old_size = output_target.stat().st_size if output_target.exists() else 0
        output_target.parent.mkdir(parents=True, exist_ok=True)
        output_target.write_text(content, encoding="utf-8")
        new_size = len(content.encode("utf-8"))

        # Determine canonical target
        classification = _classify_remediation_path(rel_path)
        target_label = "output"

        if classification == "atomic" and resolved_atomic:
            canonical = (atomic_root / rel_path).resolve()
            if str(canonical).startswith(str(resolved_atomic)):
                canon_old = canonical.stat().st_size if canonical.exists() else 0
                result = _safe_write(canonical, resolved_atomic, content)
                if result >= 0:
                    target_label = "atomic"
                    old_size = canon_old  # report canonical file's old size
        elif classification == "project" and resolved_project:
            canonical = (project_root / rel_path).resolve()
            if str(canonical).startswith(str(resolved_project)):
                canon_old = canonical.stat().st_size if canonical.exists() else 0
                result = _safe_write(canonical, resolved_project, content)
                if result >= 0:
                    target_label = "project"
                    old_size = canon_old

        changes.append((rel_path, old_size, new_size, target_label))

    return changes


def _display_remediation_changes(
    changes: list[tuple[str, int, int, str]],
    summary: str,
    console,
) -> None:
    """Display remediation changes using Rich Panel.

    Each change is (rel_path, old_size, new_size, target_label).
    target_label is 'atomic', 'project', or 'output'.
    """
    from rich.panel import Panel
    from rich.table import Table

    if not changes:
        console.print("  No files were modified.")
        return

    TARGET_LABELS = {
        "atomic": "pipeline",
        "project": "project",
        "output": "output",
    }

    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("File", no_wrap=True)
    table.add_column("Target", width=10)
    table.add_column("Old", justify="right", width=8)
    table.add_column("New", justify="right", width=8)
    table.add_column("Delta", justify="right", width=10)

    for rel_path, old_size, new_size, target_label in changes:
        delta = new_size - old_size
        sign = "+" if delta >= 0 else ""
        table.add_row(
            rel_path,
            TARGET_LABELS.get(target_label, target_label),
            f"{old_size:,}",
            f"{new_size:,}",
            f"{sign}{delta:,}",
        )

    # Count files by target
    by_target = {}
    for _, _, _, t in changes:
        by_target[t] = by_target.get(t, 0) + 1
    target_summary = ", ".join(
        f"{c} {TARGET_LABELS.get(t, t)}" for t, c in sorted(by_target.items())
    )

    console.print()
    console.print(Panel(
        f"  AI remediation: {len(changes)} file(s) updated ({target_summary})",
        title="Remediation Applied",
    ))
    console.print(table)
    if summary:
        console.print(f"\n  Summary: {summary}")
    console.print()


def _auto_remediate(
    evaluations: list[AuditEvaluation],
    output_dir: Path,
    phase_num: int,
    phase_id: str,
    failures_only: bool = False,
) -> bool:
    """Orchestrate AI-automated remediation. Returns True if changes applied.

    Writes patched files to both output_dir (for re-audit) and their
    canonical locations (pipeline source or project deliverables).

    Args:
        failures_only: If True, only remediate failures (skip warnings)

    Non-blocking: returns False on any error without raising.
    """
    from rich.console import Console
    console = Console()

    # Determine project root and atomic root
    atomic_root = _ATOMIC_ROOT
    project_root = _ATOMIC_ROOT.parent  # project being worked on

    scope = "failures only" if failures_only else "failures + warnings"

    try:
        # 1. Extract guidance from failed/warned audits
        guidance = _extract_remediation_guidance(evaluations, failures_only=failures_only)
        if not guidance.strip():
            console.print(f"  No actionable guidance extracted from audit reports ({scope}).")
            return False

        # 2. Gather current deliverables (with source context for remediation)
        source_dirs = _get_remediation_source_dirs(phase_num, atomic_root, project_root)
        extra_dirs = _get_phase_deliverable_dirs(phase_num, project_root)
        deliverables = _gather_deliverables(
            output_dir, source_dirs=source_dirs, extra_dirs=extra_dirs,
        )

        # 3. Build prompt (with file layout context)
        prompt = _build_remediation_prompt(
            guidance, deliverables, output_dir,
            atomic_root=atomic_root,
            project_root=project_root,
        )

        # 4. Invoke LLM (opus for high-quality remediation, extended timeout)
        from core.llm.invoke import invoke_llm
        console.print(f"  Invoking AI remediation (opus, {scope})...")
        response = invoke_llm(prompt=prompt, model="opus", timeout=1800)

        # Handle response object
        if hasattr(response, 'content'):
            response_text = response.content
        else:
            response_text = str(response)

        # 5. Parse response
        file_updates, summary = _parse_remediation_response(response_text)
        if not file_updates:
            # Show what the LLM actually returned so it's not a black box
            preview = response_text[:500].strip()
            if len(response_text) > 500:
                preview += "..."
            console.print("  AI returned no file updates (no === FILE: ... === blocks found).")
            console.print(f"  Response preview ({len(response_text)} chars):")
            console.print(f"  [dim]{preview}[/dim]")
            return False

        # 6. Apply changes (to output_dir + canonical locations)
        changes = _apply_remediation(
            file_updates, output_dir,
            project_root=project_root,
            atomic_root=atomic_root,
        )
        if not changes:
            console.print("  No valid file changes applied (possible path issues).")
            return False

        # 7. Display what changed
        _display_remediation_changes(changes, summary, console)
        return True

    except Exception as e:
        console.print(f"  AI remediation error: {e}")
        return False


# ---------------------------------------------------------------------------
# Remediation Loop (Stage 5b)
# ---------------------------------------------------------------------------

def _remediation_loop(
    evaluations: list[AuditEvaluation],
    audit_configs: list[AuditConfig],
    phase_num: int,
    phase_id: str,
    output_dir: Path,
) -> list[AuditEvaluation]:
    """
    Iterative remediation loop: AI fixes → re-audit → repeat until pass.

    After each round of failures, the user can:
    - Accept the results as-is (enter)
    - AI-remediate and re-audit (r)
    - Skip (s)

    Saves updated markdown reports after each re-audit round.
    Capped at MAX_REMEDIATION_ROUNDS rounds to prevent infinite loops.
    """
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    round_num = 0

    while True:
        failures = [e for e in evaluations if e.status == "fail"]
        warnings = [e for e in evaluations if e.status == "warn"]

        if not failures and not warnings:
            console.print("  All audits passed!")
            return evaluations

        # Show what failed
        fail_count = len(failures)
        warn_count = len(warnings)
        remaining = MAX_REMEDIATION_ROUNDS - round_num
        console.print()
        if round_num > 0:
            console.print(f"  Round {round_num + 1}: {fail_count} failures, {warn_count} warnings remain")
        else:
            console.print(f"  {fail_count} failures, {warn_count} warnings detected")

        from core.utils.cli_ui import prompt_menu

        if remaining <= 0:
            console.print(f"  Max remediation rounds ({MAX_REMEDIATION_ROUNDS}) reached.")
            prompt_menu(
                [("accept", "Accept results and continue")],
                header="  Max rounds reached:",
                default=1,
            )
            return evaluations

        # Build menu options — only show failures-only when both types present
        menu_options = [
            ("accept", "Accept results and continue"),
            ("remediate", f"AI-remediate and re-audit ({remaining} rounds remaining)"),
        ]
        if fail_count > 0 and warn_count > 0:
            menu_options.append(
                ("failures", f"AI-remediate failures only, skip {warn_count} warnings ({remaining} rounds remaining)"),
            )
        menu_options.append(("skip", "Skip remediation"))

        choice = prompt_menu(
            menu_options,
            header="  Remediation options:",
            default=1,
        )

        if choice not in ("remediate", "failures"):
            return evaluations

        failures_only = (choice == "failures")

        # Snapshot current evaluations for delta comparison
        prev_evaluations = list(evaluations)

        # AI-automated remediation
        success = _auto_remediate(evaluations, output_dir, phase_num, phase_id,
                                  failures_only=failures_only)
        if not success:
            console.print("  AI remediation did not produce changes. You can accept or retry.")
            round_num += 1
            continue

        # Re-gather deliverables (AI may have changed them)
        project_root = _ATOMIC_ROOT.parent
        extra_dirs = _get_phase_deliverable_dirs(phase_num, project_root)
        fresh_deliverables = _gather_deliverables(output_dir, extra_dirs=extra_dirs)

        # Re-audit only the audits that were targeted for remediation
        reaudit_statuses = ("fail",) if failures_only else ("fail", "warn")
        reaudit_ids = {e.audit_id for e in evaluations if e.status in reaudit_statuses}
        re_configs = [c for c in audit_configs if c.audit.get("audit_id") in reaudit_ids]

        if not re_configs:
            console.print("  No audits to re-evaluate")
            return evaluations

        scope_label = "failed" if failures_only else "failed/warned"
        round_label = f"Re-Audit Round {round_num + 1} ({len(re_configs)} {scope_label})"
        console.print(f"  {round_label}...")

        new_evals = _run_parallel_evaluations(
            re_configs, fresh_deliverables, phase_num, phase_id,
            round_label=round_label,
        )

        # Merge: replace old evaluations with new ones
        new_by_id = {e.audit_id: e for e in new_evals}
        evaluations = [
            new_by_id.get(e.audit_id, e) for e in evaluations
        ]

        # Save updated markdowns and show compact results with delta
        audit_dir = _save_audit_markdowns(evaluations, phase_num)
        _display_rich_results(
            evaluations, phase_num, audit_dir,
            round_label=round_label,
            prev_evaluations=prev_evaluations,
        )

        round_num += 1

    return evaluations


def _synthesize_findings(
    evaluations: list[AuditEvaluation],
    phase_num: int,
    phase_id: str,
) -> str:
    """Use haiku to synthesize all findings into executive summary.

    Haiku reads the full markdown reports from each audit and produces
    a concise executive synthesis. This is fast and cheap — perfect for
    summarization work.
    """
    failures = [e for e in evaluations if e.status == "fail"]
    warnings = [e for e in evaluations if e.status == "warn"]
    passes = [e for e in evaluations if e.status == "pass"]

    if not failures and not warnings:
        return ""

    # Build digest of all audit reports for haiku
    report_sections = []
    for e in failures + warnings + passes:
        # Truncate very long reports for the summary prompt
        analysis_excerpt = e.analysis[:2000] if e.analysis else "(no analysis)"
        report_sections.append(
            f"### [{e.status.upper()}] {e.audit_name}\n"
            f"Category: {e.category} | Severity: {e.severity}\n\n"
            f"{analysis_excerpt}"
        )

    prompt = f"""You are synthesizing audit results for Phase {phase_num} ({phase_id}).

{len(failures)} failures, {len(warnings)} warnings, {len(passes)} passes.

# Audit Reports

{chr(10).join(report_sections)}

---

Write a concise executive synthesis in markdown covering:
1. **Executive Summary** — key themes across all audits (2-3 sentences)
2. **Most Critical Action Items** — top 3-5 actions, ordered by priority
3. **Quick Wins** — low-effort improvements that can be done immediately
4. **Overall Risk Assessment** — HIGH/MEDIUM/LOW with brief rationale"""

    try:
        from core.llm.invoke import invoke_llm
        return invoke_llm(prompt=prompt, model="haiku")
    except Exception as e:
        # Non-blocking: return empty on failure
        logger.debug("LLM executive synthesis failed: %s", e)
        return ""


def _curate_audit_selection(
    audits: list[dict],
    deliverables: str,
    phase_num: int,
    phase_id: str,
    uat_mode: bool = False,
) -> list[dict]:
    """
    LLM-curated audit selection.

    Sends the phase deliverables and full audit roster to the LLM, which
    handpicks individual audits for multi-domain coverage. User confirms
    or adjusts. Falls back to manual category pick on LLM failure.
    """
    if uat_mode:
        return audits

    if not audits:
        return audits

    # Build roster and call LLM
    roster = _build_audit_roster(audits)
    prompt = _build_curation_prompt(
        roster, deliverables, phase_num, phase_id, len(audits)
    )

    selected_ids: list[str] = []
    rationale = ""

    try:
        from core.llm.invoke import invoke_llm

        response = invoke_llm(prompt=prompt, model="haiku")
        selected_ids, rationale = _parse_curation_response(response)
    except Exception as e:
        print(f"  LLM curation unavailable ({e}), falling back to manual selection")

    if not selected_ids:
        return _fallback_category_selection(audits)

    # Map IDs back to audit dicts
    audit_by_id = {a.get("audit_id"): a for a in audits}
    selected = [audit_by_id[aid] for aid in selected_ids if aid in audit_by_id]

    if not selected:
        print("  LLM returned no matching audit IDs, falling back to manual selection")
        return _fallback_category_selection(audits)

    # Display and confirm
    _display_curated_selection(selected, rationale)

    from core.utils.cli_ui import prompt_user, clear_input_buffer

    clear_input_buffer()
    choice = prompt_user("  [enter] accept / [1,3,5] pick by number / [skip]: ").strip().lower()

    if choice == "skip":
        return []
    if not choice or choice == "all":
        return selected

    # Parse numbered picks from the displayed list
    picked_indices = set()
    for part in choice.split(","):
        part = part.strip()
        try:
            idx = int(part) - 1
            if 0 <= idx < len(selected):
                picked_indices.add(idx)
        except ValueError:
            pass

    if not picked_indices:
        print("  No valid selection, using LLM recommendation")
        return selected

    result = [selected[i] for i in sorted(picked_indices)]
    print(f"  Selected {len(result)} audits")
    return result


def _get_phase_deliverable_dirs(
    phase_num: int,
    project_root: Path,
) -> list[Path]:
    """Return additional deliverable directories for a given phase.

    These are phase-specific directories that contain actual deliverables
    (not just summaries) that the audit evaluator and remediation LLM
    need to see.  For example, Phase 4 generates OpenSpec files in
    project_root/.openspec/ rather than in .outputs/4-specification/.
    """
    dirs: list[Path] = []

    if phase_num == 4:
        openspec = project_root / ".openspec"
        if openspec.is_dir():
            dirs.append(openspec)

    return dirs


def _get_remediation_source_dirs(
    phase_num: int,
    atomic_root: Path,
    project_root: Path,
) -> list[Path]:
    """Return source directories relevant to remediation for a given phase.

    These directories contain actual source code and project deliverables
    that the remediation LLM may need to read and fix.
    """
    dirs: list[Path] = []

    # Phase task source files
    phase_pattern = f"phase_{phase_num:02d}_*"
    for d in atomic_root.glob(f"phases/{phase_pattern}/tasks"):
        if d.is_dir():
            dirs.append(d)

    # Project deliverables
    taskmaster = project_root / ".taskmaster" / "tasks"
    if taskmaster.is_dir():
        dirs.append(taskmaster)

    # Phase-specific deliverable directories (e.g., .openspec for phase 4)
    dirs.extend(_get_phase_deliverable_dirs(phase_num, project_root))

    return dirs


def _gather_deliverables(
    output_dir: Path,
    max_chars: int = 50_000,
    source_dirs: list[Path] | None = None,
    extra_dirs: list[Path] | None = None,
) -> str:
    """Read deliverable files from the phase output directory.

    Args:
        output_dir: Primary phase output directory (.outputs/N-phase/)
        max_chars: Total character budget for all deliverables
        source_dirs: Additional source code directories for remediation context
            (labeled [source] or [project], separate 30K budget)
        extra_dirs: Additional deliverable directories (e.g., .openspec/)
            that share the main deliverable budget with output_dir
    """
    extensions = {".json", ".md", ".txt", ".py"}
    parts: list[str] = []
    total = 0

    # Phase output artifacts
    if output_dir.exists():
        output_extensions = {".json", ".md", ".txt"}
        for fp in sorted(output_dir.rglob("*")):
            if not fp.is_file() or fp.suffix.lower() not in output_extensions:
                continue
            try:
                text = fp.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                logger.debug("Failed to read output artifact %s: %s", fp, e)
                continue

            header = f"--- {fp.relative_to(output_dir)} ---\n"
            chunk = header + text + "\n"
            if total + len(chunk) > max_chars:
                remaining = max_chars - total
                if remaining > len(header) + 100:
                    parts.append(chunk[:remaining] + "\n[...truncated]")
                    total = max_chars
                break
            parts.append(chunk)
            total += len(chunk)

    # Extra deliverable directories (same budget as output artifacts)
    if extra_dirs and total < max_chars:
        deliverable_extensions = {".json", ".md", ".txt"}
        for extra_dir in extra_dirs:
            if not extra_dir.is_dir() or total >= max_chars:
                break
            try:
                dir_name = extra_dir.relative_to(_ATOMIC_ROOT.parent)
            except ValueError:
                dir_name = extra_dir.name
            for fp in sorted(extra_dir.rglob("*")):
                if not fp.is_file() or fp.suffix.lower() not in deliverable_extensions:
                    continue
                try:
                    text = fp.read_text(encoding="utf-8", errors="replace")
                except Exception as e:
                    logger.debug("Failed to read deliverable file %s: %s", fp, e)
                    continue

                rel = fp.relative_to(extra_dir)
                header = f"--- [{dir_name}] {rel} ---\n"
                chunk = header + text + "\n"
                if total + len(chunk) > max_chars:
                    remaining = max_chars - total
                    if remaining > len(header) + 100:
                        parts.append(chunk[:remaining] + "\n[...truncated]")
                        total = max_chars
                    break
                parts.append(chunk)
                total += len(chunk)

    # Source context (for remediation)
    if source_dirs and total < max_chars:
        source_budget = min(30_000, max_chars - total)
        source_total = 0

        for src_dir in source_dirs:
            if not src_dir.exists():
                continue
            for fp in sorted(src_dir.rglob("*")):
                if not fp.is_file() or fp.suffix.lower() not in extensions:
                    continue
                try:
                    text = fp.read_text(encoding="utf-8", errors="replace")
                except Exception as e:
                    logger.debug("Failed to read source file %s: %s", fp, e)
                    continue

                # Use path relative to atomic/project root for identification
                try:
                    rel = fp.relative_to(_ATOMIC_ROOT)
                    header = f"--- [source] {rel} ---\n"
                except ValueError:
                    try:
                        rel = fp.relative_to(_ATOMIC_ROOT.parent)
                        header = f"--- [project] {rel} ---\n"
                    except ValueError:
                        header = f"--- [source] {fp} ---\n"

                chunk = header + text + "\n"
                if source_total + len(chunk) > source_budget:
                    break
                parts.append(chunk)
                source_total += len(chunk)

    if not parts:
        return "(No deliverables found)"
    return "".join(parts)


def _build_audit_prompt(
    audits: list[dict],
    deliverables: str,
    phase_num: int,
    phase_id: str,
) -> str:
    """Build the LLM evaluation prompt."""
    criteria_lines = []
    for i, a in enumerate(audits, 1):
        criteria_lines.append(
            f"{i}. [{a.get('audit_id', 'unknown')}] "
            f"({a.get('severity', 'medium')}) {a.get('audit_name', 'Unnamed')}"
        )
    criteria_block = "\n".join(criteria_lines)

    return f"""You are a software quality auditor evaluating Phase {phase_num} ({phase_id}) deliverables.

AUDIT CRITERIA (evaluate each):
{criteria_block}

DELIVERABLES:
{deliverables}

For each audit criterion, determine:
- "pass" if the deliverables satisfy the criterion or it is clearly addressed
- "warn" if partially addressed or cannot be fully determined from available deliverables
- "fail" if the deliverables clearly violate or miss the criterion

Respond with ONLY a JSON array (no markdown fencing). Each element:
{{"audit_id": "<id>", "status": "pass|warn|fail", "finding": "<one-sentence explanation>"}}
"""


def _parse_audit_response(response: str, audits: list[dict]) -> list[dict]:
    """Parse LLM JSON response. Falls back to all-warn on failure."""
    # Strip markdown code fences if present
    cleaned = response.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list) and len(parsed) > 0:
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass

    # Fallback: mark everything as warn
    return [
        {
            "audit_id": a.get("audit_id", "unknown"),
            "status": "warn",
            "finding": "Could not parse LLM audit response",
        }
        for a in audits
    ]


def _display_audit_results(results: list[dict], audits: list[dict]) -> None:
    """Display color-coded audit results inline."""
    # Build audit name lookup
    name_by_id = {a.get("audit_id"): a.get("audit_name", "Unnamed") for a in audits}

    _STATUS_ICON = {"pass": "✅", "warn": "⚠️ ", "fail": "❌"}
    _STATUS_LABEL = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}

    print()
    print("  ─── Audit Results ───────────────────────────────────────────")
    print()

    for i, r in enumerate(results, 1):
        aid = r.get("audit_id", "unknown")
        status = r.get("status", "warn")
        finding = r.get("finding", "")
        name = name_by_id.get(aid, aid)
        icon = _STATUS_ICON.get(status, "?")
        label = _STATUS_LABEL.get(status, "???")

        print(f"  {i:>2}. {icon} [{label:>4}] {name}")
        if finding:
            print(f"              {finding}")

    # Separate failures and warnings for quick scanning
    failures = [r for r in results if r.get("status") == "fail"]
    warns = [r for r in results if r.get("status") == "warn"]

    if failures:
        print()
        print(f"  ─── Failures ({len(failures)}) ──────────────────────────────────────────")
        for r in failures:
            aid = r.get("audit_id", "unknown")
            name = name_by_id.get(aid, aid)
            print(f"    ❌ {name}")
            if r.get("finding"):
                print(f"       {r['finding']}")

    if warns:
        print()
        print(f"  ─── Warnings ({len(warns)}) ─────────────────────────────────────────")
        for r in warns:
            aid = r.get("audit_id", "unknown")
            name = name_by_id.get(aid, aid)
            print(f"    ⚠️  {name}")
            if r.get("finding"):
                print(f"       {r['finding']}")

    print()


def run_phase_audit(
    phase_num: int,
    phase_id: str,
    output_dir: Path,
    uat_mode: bool = False,
) -> bool:
    """
    Run LLM-driven audit for a phase.

    Pipeline: load audits → gather deliverables → LLM curation →
    interactive plan (Textual TUI) → per-audit parallel evaluation →
    detailed results → remediation loop → save report.

    Always returns True (non-blocking).
    """
    if uat_mode:
        print(f"⚠️  UAT Mode: Skipping phase {phase_num} audit")
        return True

    # 0. Check for existing audit results — offer to resume remediation
    existing_evals, existing_configs = _load_existing_evaluations(phase_num)
    if existing_evals:
        failures = sum(1 for e in existing_evals if e.status == "fail")
        warnings = sum(1 for e in existing_evals if e.status == "warn")
        passed = sum(1 for e in existing_evals if e.status == "pass")

        if failures or warnings:
            print(f"\n  Previous audit results found: "
                  f"{passed} passed, {warnings} warnings, {failures} failures")

            from core.utils.cli_ui import prompt_user, clear_input_buffer
            clear_input_buffer()
            choice = prompt_user(
                "  [r] Resume remediation / [enter] Re-run full audit: "
            ).strip().lower()

            if choice == "r" or "resume" in choice or "remediat" in choice or "fix" in choice:
                audit_dir = _ATOMIC_ROOT.parent / ".outputs" / "audits" / f"phase-{phase_num}"
                _display_rich_results(existing_evals, phase_num, audit_dir)

                evaluations = _remediation_loop(
                    existing_evals, existing_configs,
                    phase_num, phase_id, output_dir,
                )

                audit_dir = _save_audit_markdowns(evaluations, phase_num)
                _save_audit_report(evaluations, phase_num, phase_id, audit_dir)
                return True

    # 1. Load and filter audits
    rows = _load_audit_inventory()
    if not rows:
        print("⚠️  Audit inventory not found or empty, skipping audit")
        return True

    audits = _select_audits_for_phase(rows, phase_num)
    if not audits:
        col = PHASE_CSV_COLUMN.get(phase_num)
        if col is None:
            print(f"⚠️  No audit column for phase {phase_num}, skipping audit")
        else:
            print(f"⚠️  No applicable audits for phase {phase_num}")
        return True

    # 2. Gather deliverables early — LLM curation needs them
    #    Include phase-specific dirs (e.g., .openspec for phase 4) so audits
    #    evaluate actual deliverables, not just summary reports.
    project_root = _ATOMIC_ROOT.parent
    extra_dirs = _get_phase_deliverable_dirs(phase_num, project_root)
    deliverables = _gather_deliverables(output_dir, extra_dirs=extra_dirs)

    # 3. LLM-curated audit selection
    audits = _curate_audit_selection(audits, deliverables, phase_num, phase_id, uat_mode)
    if not audits:
        print("⚠️  Audit skipped by user")
        return True

    # 4. Cap audits
    audits = audits[:MAX_AUDITS]

    # 5. Build audit configs with agent assignment
    audit_configs = _build_audit_configs(audits)

    # 6. Interactive audit plan (Textual TUI)
    audit_configs = _display_audit_plan(audit_configs, phase_num)
    if not audit_configs:
        print("⚠️  Audit skipped by user")
        return True

    # 7. Per-audit parallel evaluation with Rich live progress
    print(f"\n  Evaluating {len(audit_configs)} audits against phase deliverables...")
    try:
        evaluations = _run_parallel_evaluations(
            audit_configs, deliverables, phase_num, phase_id
        )
    except Exception as e:
        print(f"⚠️  LLM audit failed: {e} (non-blocking)")
        return True

    if not evaluations:
        print("⚠️  No evaluation results")
        return True

    # 8. Save markdown reports immediately (before display)
    audit_dir = _save_audit_markdowns(evaluations, phase_num)

    # 9. Display compact results with file references
    _display_rich_results(evaluations, phase_num, audit_dir)

    # 10. Remediation loop — iterates until user accepts or all pass
    evaluations = _remediation_loop(
        evaluations, audit_configs,
        phase_num, phase_id, output_dir,
    )

    # 11. Save final JSON summary (markdowns already saved by remediation loop)
    audit_dir = _save_audit_markdowns(evaluations, phase_num)
    _save_audit_report(evaluations, phase_num, phase_id, audit_dir)

    return True


def run_audit(
    audit_name: str,
    phase_id: str,
    output_dir: Path,
    uat_mode: bool = False,
) -> bool:
    """
    Run an audit (backward-compatible entry point).

    Delegates to run_phase_audit by extracting phase_num from phase_id.
    """
    if uat_mode:
        print(f"⚠️  UAT Mode: Skipping audit {audit_name}")
        return True

    # Extract phase number from phase_id (e.g., "1-discovery" → 1)
    try:
        phase_num = int(phase_id.split("-")[0])
    except (ValueError, IndexError):
        print(f"⚠️  Could not parse phase number from '{phase_id}', skipping audit")
        return True

    return run_phase_audit(phase_num, phase_id, output_dir, uat_mode)


def select_audit(
    phase_num: int,
    output_dir: Path,
    uat_mode: bool = False,
) -> Optional[str]:
    """
    Select audit for phase (backward-compatible).

    Returns a phase audit name string, or None if no audits apply.
    """
    if uat_mode:
        return f"phase-{phase_num}-audit"

    col = PHASE_CSV_COLUMN.get(phase_num)
    if col is None:
        return None

    return f"phase-{phase_num}-audit"


# ---------------------------------------------------------------------------
# On-demand audit API (CLI and programmatic use)
# ---------------------------------------------------------------------------

def list_audits(
    phase_num: int = None,
    category: str = None,
) -> list[dict]:
    """
    List available audits, optionally filtered by phase or category.

    Args:
        phase_num: If given, return only audits applicable to this phase.
        category: If given, return only audits matching this category (case-insensitive).

    Returns:
        List of audit row dicts from the inventory CSV.
    """
    rows = _load_audit_inventory()
    if phase_num is not None:
        rows = _select_audits_for_phase(rows, phase_num)
    if category:
        cat_lower = category.lower()
        rows = [r for r in rows if cat_lower in r.get("category", "").lower()]
    return rows


def search_audits(query: str) -> list[dict]:
    """
    Search audits by substring match on audit_id, audit_name, and category.

    Args:
        query: Search string (case-insensitive).

    Returns:
        Matching audit row dicts.
    """
    rows = _load_audit_inventory()
    q = query.lower()
    return [
        r for r in rows
        if q in r.get("audit_id", "").lower()
        or q in r.get("audit_name", "").lower()
        or q in r.get("category", "").lower()
        or q in r.get("subcategory", "").lower()
    ]


def load_audit_results(phase_num: int = None) -> Optional[dict]:
    """
    Load existing audit report.json for a phase (or latest available).

    Args:
        phase_num: Specific phase, or None to auto-detect latest.

    Returns:
        Parsed report dict, or None if no results found.
    """
    audits_dir = _ATOMIC_ROOT.parent / ".outputs" / "audits"

    if phase_num is not None:
        report_path = audits_dir / f"phase-{phase_num}" / "report.json"
        if report_path.exists():
            return json.loads(report_path.read_text(encoding="utf-8"))
        return None

    # Auto-detect: find latest phase with audit results
    if not audits_dir.exists():
        return None
    for pn in range(9, -1, -1):
        rp = audits_dir / f"phase-{pn}" / "report.json"
        if rp.exists():
            return json.loads(rp.read_text(encoding="utf-8"))
    return None


def run_targeted_audit(
    audit_ids: list = None,
    category: str = None,
    phase_num: int = None,
    output_dir: Path = None,
    interactive: bool = True,
) -> list:
    """
    Run specific audits on demand (outside the pipeline phase gate).

    Three filter modes:
    - audit_ids: run specific audits by ID
    - category: run all audits in a category
    - phase_num alone: run phase-appropriate audits (like pipeline)

    Auto-detects phase and output directory if not provided.

    Args:
        audit_ids: List of audit IDs to run.
        category: Category name to filter by.
        phase_num: Phase number for deliverable context.
        output_dir: Phase output directory (auto-resolved if None).
        interactive: If True, show audit plan TUI before running.

    Returns:
        List of AuditEvaluation results.
    """
    # Lazy imports to avoid circular deps
    from orchestration.pipeline import PHASE_REGISTRY

    # 1. Load inventory
    rows = _load_audit_inventory()
    if not rows:
        print("  No audit inventory found.")
        return []

    # 2. Filter audits
    if audit_ids:
        all_ids = {r.get("audit_id", "") for r in rows}
        missing = [aid for aid in audit_ids if aid not in all_ids]
        if missing:
            print(f"  Unknown audit ID(s): {', '.join(missing)}")
            return []
        audits = [r for r in rows if r.get("audit_id", "") in audit_ids]
    elif category:
        cat_lower = category.lower()
        audits = [r for r in rows if cat_lower in r.get("category", "").lower()]
        if not audits:
            print(f"  No audits found for category '{category}'")
            return []
    elif phase_num is not None:
        audits = _select_audits_for_phase(rows, phase_num)
        if not audits:
            print(f"  No applicable audits for phase {phase_num}")
            return []
    else:
        print("  Specify audit_ids, category, or phase_num")
        return []

    # 3. Auto-detect phase if not provided
    if phase_num is None:
        project_root = _ATOMIC_ROOT.parent
        for pn in range(9, -1, -1):
            meta = PHASE_REGISTRY.get(pn)
            if meta:
                closeout = project_root / ".outputs" / meta.phase_id / "closeout.json"
                if closeout.exists():
                    phase_num = pn
                    break
        if phase_num is None:
            # Fall back to latest output dir that exists
            for pn in range(9, -1, -1):
                meta = PHASE_REGISTRY.get(pn)
                if meta and (project_root / ".outputs" / meta.phase_id).exists():
                    phase_num = pn
                    break
        if phase_num is None:
            print("  No phase output found. Run a phase first or specify --phase.")
            return []

    # 4. Resolve output_dir and phase_id
    meta = PHASE_REGISTRY.get(phase_num)
    phase_id = meta.phase_id if meta else f"{phase_num}-unknown"
    if output_dir is None:
        output_dir = _ATOMIC_ROOT.parent / ".outputs" / phase_id

    # 5. Gather deliverables
    project_root = _ATOMIC_ROOT.parent
    extra_dirs = _get_phase_deliverable_dirs(phase_num, project_root)
    deliverables = _gather_deliverables(output_dir, extra_dirs=extra_dirs)

    # 6. Build configs
    audit_configs = _build_audit_configs(audits[:MAX_AUDITS])

    # 7. Optional interactive plan
    if interactive:
        audit_configs = _display_audit_plan(audit_configs, phase_num)
        if not audit_configs:
            print("  Audit skipped by user.")
            return []

    # 8. Run parallel evaluations
    print(f"\n  Evaluating {len(audit_configs)} audit(s) against phase {phase_num} deliverables...")
    try:
        evaluations = _run_parallel_evaluations(
            audit_configs, deliverables, phase_num, phase_id
        )
    except Exception as e:
        print(f"  Audit evaluation failed: {e}")
        return []

    if not evaluations:
        print("  No evaluation results.")
        return []

    # 9. Save and display
    audit_dir = _save_audit_markdowns(evaluations, phase_num)
    _save_audit_report(evaluations, phase_num, phase_id, audit_dir)
    _display_rich_results(evaluations, phase_num, audit_dir)

    return evaluations


class AuditManager:
    """Manages audit execution and reporting."""

    def __init__(self, atomic_root: Path, output_dir: Path):
        self.atomic_root = atomic_root
        self.output_dir = output_dir

    def run_phase_audit(
        self,
        phase_num: int,
        phase_id: str,
        uat_mode: bool = False,
    ) -> bool:
        return run_phase_audit(phase_num, phase_id, self.output_dir, uat_mode)
