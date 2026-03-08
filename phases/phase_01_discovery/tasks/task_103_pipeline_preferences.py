"""
Task 103: Pipeline Preferences

Interactive wizard for configuring task-to-task autonomy and model
recommendation strategy. Non-LLM task — purely interactive user input.

These preferences apply to all phases from here forward and are consumed
by the model resolver (core/llm/resolver.py) and phase runner
(orchestration/phase_runner.py).

Outputs:
  - pipeline-preferences.json    - Structured preference data
  - Updates project-config.json  - Adds extracted.autonomy and extracted.model_strategy
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.ui import success, step

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS
# ============================================================================

PHASE_NAMES = {
    0: "Setup",
    1: "Discovery",
    2: "PRD",
    3: "Task Decomposition",
    4: "Specification",
    5: "Implementation",
    6: "Code Review",
    7: "Integration Testing",
    8: "Deployment Prep",
    9: "Release",
}

AUTONOMY_MODES = [
    ("fully_autonomous", "Run all tasks without pausing for approval"),
    ("per_task_approval", "Pause between every task for your approval"),
    ("selective", "Pause only for specific tasks or criteria"),
]

SELECTIVE_CRITERIA = [
    ("llm_tasks_only", "Pause before tasks that use an LLM"),
    ("risk_above_medium", "Pause when task risk exceeds medium"),
    ("custom", "Specify individual task IDs"),
]

ERROR_HANDLING_MODES = [
    ("auto_retry", "Retry failed tasks automatically"),
    ("pause_on_error", "Pause and ask for guidance"),
    ("fail_fast", "Stop the pipeline immediately"),
]

STRATEGY_PRESETS = [
    ("cost_focused", "Minimize API costs (haiku default, no thinking)"),
    ("performance_focused", "Maximum quality (sonnet minimum, full thinking)"),
    ("balanced", "Standard phase-role mapping (recommended)"),
    ("custom", "Configure every option manually"),
]

TIER_OPTIONS = ["haiku", "sonnet", "opus"]

EFFORT_LEVELS = [
    ("low", "Minimal effort (faster, less thorough)"),
    ("medium", "Standard effort"),
    ("high", "Maximum effort (slower, more thorough)"),
]

FALLBACK_STRATEGIES = [
    ("downgrade_tier", "Try a lower tier (opus -> sonnet -> haiku)"),
    ("switch_provider", "Try a different provider"),
    ("fail", "Fail the task if preferred model unavailable"),
]

# Preset definitions
_PRESETS = {
    "cost_focused": {
        "tier_constraints": {"minimum_tier": None, "maximum_tier": "sonnet", "phase_overrides": {}},
        "thinking": {"extended_thinking": False, "thinking_budget": None, "phase_thinking_config": {}},
        "effort": {"default_level": "medium", "phase_effort": {}},
        "cost_guardrails": {"token_tracking": True, "alert_threshold_usd": None, "per_phase_budget_usd": None},
        "fallback_behavior": {"strategy": "downgrade_tier", "allow_cross_provider_fallback": True, "fail_if_no_fallback": False},
    },
    "performance_focused": {
        "tier_constraints": {"minimum_tier": "sonnet", "maximum_tier": None, "phase_overrides": {}},
        "thinking": {"extended_thinking": True, "thinking_budget": 20000, "phase_thinking_config": {}},
        "effort": {"default_level": "high", "phase_effort": {}},
        "cost_guardrails": {"token_tracking": False, "alert_threshold_usd": None, "per_phase_budget_usd": None},
        "fallback_behavior": {"strategy": "downgrade_tier", "allow_cross_provider_fallback": True, "fail_if_no_fallback": False},
    },
    "balanced": {
        "tier_constraints": {"minimum_tier": None, "maximum_tier": None, "phase_overrides": {}},
        "thinking": {"extended_thinking": True, "thinking_budget": None, "phase_thinking_config": {}},
        "effort": {"default_level": "high", "phase_effort": {}},
        "cost_guardrails": {"token_tracking": False, "alert_threshold_usd": None, "per_phase_budget_usd": None},
        "fallback_behavior": {"strategy": "downgrade_tier", "allow_cross_provider_fallback": True, "fail_if_no_fallback": False},
    },
}


# ============================================================================
# MAIN EXECUTE
# ============================================================================

def execute(atomic_root: Path, output_dir: Path, mem=None, graph=None) -> bool:
    """
    Execute Task 103: Pipeline Preferences.

    Presents an interactive wizard for configuring task autonomy and model
    selection strategy. Supports quick-accept (one keypress) or detailed
    configuration.

    Returns:
        True always (preferences are optional, not blocking)
    """
    project_root = atomic_root.parent
    config_file = project_root / ".outputs" / "0-setup" / "project-config.json"
    output_file = output_dir / "pipeline-preferences.json"
    existing_prefs = output_dir / "pipeline-preferences.json"

    step("Pipeline Preferences")

    # Load existing config for smart defaults
    project_config = _load_config(config_file)
    primary_provider = _get_primary_provider(project_config)
    autonomy_defaults, strategy_defaults = _compute_defaults(project_config, existing_prefs)

    # Header
    print()
    print("  ┌───────────────────────────────────────────────────────────┐")
    print("  │ PIPELINE PREFERENCES                                      │")
    print("  │                                                           │")
    print("  │ Configure task autonomy and model selection strategy.     │")
    print("  │ These preferences apply to all phases from here forward.  │")
    print("  │                                                           │")
    print(f"  │ Detected: {primary_provider:<12} / {_pipeline_mode(project_config):<16} │")
    print("  └───────────────────────────────────────────────────────────┘")
    print()
    print(f"  Defaults: {autonomy_defaults['task_mode']}, "
          f"{strategy_defaults['preset']} model strategy")
    print()
    print("  [enter] Accept defaults    [c] Configure")

    choice = input("  > ").strip().lower()

    if choice in ("c", "configure"):
        autonomy = _section_autonomy(autonomy_defaults)
        model_strategy = _section_model_strategy(strategy_defaults, primary_provider)
    else:
        autonomy = autonomy_defaults
        model_strategy = strategy_defaults

    # Confirmation
    print()
    _show_summary(autonomy, model_strategy, primary_provider)
    print()
    print("  [enter] Save    [r] Restart")

    confirm = input("  > ").strip().lower()
    if confirm in ("r", "restart"):
        # Recurse once
        return execute(atomic_root, output_dir, mem=mem, graph=graph)

    # Save
    _save_preferences(autonomy, model_strategy, config_file, output_file, graph, mem)

    print()
    success("Pipeline preferences saved")
    return True


# ============================================================================
# SECTION 1: TASK AUTONOMY
# ============================================================================

def _section_autonomy(defaults: dict) -> dict:
    """Run the autonomy configuration section."""
    result = dict(defaults)

    print()
    print("  ╔═══════════════════════════════════════════════════════════╗")
    print("  ║ 1. TASK AUTONOMY                                          ║")
    print("  ╚═══════════════════════════════════════════════════════════╝")
    print()
    print("  How should the pipeline handle transitions between tasks?")
    print()

    # Task mode
    default_idx = next(
        (i for i, (k, _) in enumerate(AUTONOMY_MODES) if k == defaults["task_mode"]),
        0,
    )
    mode_idx = _prompt_numbered(AUTONOMY_MODES, default_idx)
    result["task_mode"] = AUTONOMY_MODES[mode_idx][0]

    # Selective mode details
    if result["task_mode"] == "selective":
        print()
        print("  Select criteria for approval pauses:")
        print()
        crit_default = next(
            (i for i, (k, _) in enumerate(SELECTIVE_CRITERIA)
             if k == defaults.get("selective_criteria")),
            0,
        )
        crit_idx = _prompt_numbered(SELECTIVE_CRITERIA, crit_default)
        result["selective_criteria"] = SELECTIVE_CRITERIA[crit_idx][0]

        if result["selective_criteria"] == "custom":
            print()
            print("  Enter task IDs requiring approval (comma-separated):")
            ids_raw = input("  > ").strip()
            result["selective_tasks"] = [
                t.strip() for t in ids_raw.split(",") if t.strip()
            ]
        else:
            result["selective_tasks"] = []
    else:
        result["selective_criteria"] = None
        result["selective_tasks"] = []

    # Error handling
    print()
    print("  What should happen when a task fails?")
    print()
    err_default = next(
        (i for i, (k, _) in enumerate(ERROR_HANDLING_MODES)
         if k == defaults["error_handling"]),
        1,
    )
    err_idx = _prompt_numbered(ERROR_HANDLING_MODES, err_default)
    result["error_handling"] = ERROR_HANDLING_MODES[err_idx][0]

    # Phase gates
    print()
    gates = result["phase_gates"]
    gate_names = ", ".join(
        f"{g}-{PHASE_NAMES.get(g, '?')}" for g in sorted(gates)
    )
    print(f"  Phase gates: {gate_names}")
    print()
    print("  [enter] Keep    [e] Edit")
    if input("  > ").strip().lower() in ("e", "edit"):
        gates = _prompt_phase_gates(gates)
        result["phase_gates"] = gates

    return result


# ============================================================================
# SECTION 2: MODEL STRATEGY
# ============================================================================

def _section_model_strategy(defaults: dict, primary_provider: str) -> dict:
    """Run the model strategy configuration section."""
    result = dict(defaults)

    print()
    print("  ╔═══════════════════════════════════════════════════════════╗")
    print("  ║ 2. MODEL STRATEGY                                         ║")
    print("  ╚═══════════════════════════════════════════════════════════╝")
    print()
    print("  Choose a strategy preset:")
    print()

    if primary_provider == "claude-code":
        print("  Note: Your provider is claude-code (fixed-cost subscription).")
        print("        Cost-focused settings won't save money. Balanced recommended.")
        print()

    preset_default = next(
        (i for i, (k, _) in enumerate(STRATEGY_PRESETS) if k == defaults["preset"]),
        2,  # balanced
    )
    preset_idx = _prompt_numbered(STRATEGY_PRESETS, preset_default)
    preset_name = STRATEGY_PRESETS[preset_idx][0]
    result["preset"] = preset_name

    # Apply preset values
    if preset_name in _PRESETS:
        for key, val in _PRESETS[preset_name].items():
            result[key] = dict(val) if isinstance(val, dict) else val

    # Show preset summary and offer customization
    if preset_name != "custom":
        print()
        _show_strategy_summary(result)
        print()
        print("  [enter] Accept preset    [c] Customize individual settings")
        if input("  > ").strip().lower() not in ("c", "customize"):
            return result

    # Drill into subsections
    result = _customize_provider_constraints(result, primary_provider)
    result = _customize_tier_constraints(result)
    result = _customize_context_window(result)
    result = _customize_thinking(result)
    result = _customize_effort(result)
    result = _customize_cost_guardrails(result)
    result = _customize_fallback(result)

    return result


def _customize_provider_constraints(strategy: dict, primary_provider: str) -> dict:
    """Customize provider constraints subsection."""
    pc = strategy.get("provider_constraints", {
        "mandatory_provider": None, "forbidden_providers": [], "local_only": False,
    })

    print()
    print("  PROVIDER CONSTRAINTS")
    print(f"    Mandatory:  {pc.get('mandatory_provider') or 'none'}")
    print(f"    Forbidden:  {', '.join(pc.get('forbidden_providers', [])) or 'none'}")
    print(f"    Local only: {'yes' if pc.get('local_only') else 'no'}")
    print()
    print("  [enter] Accept    [e] Edit")

    if input("  > ").strip().lower() in ("e", "edit"):
        print()
        print("  Mandatory provider (enter for none):")
        mp = input("  > ").strip() or None
        pc["mandatory_provider"] = mp

        print("  Forbidden providers (comma-separated, enter for none):")
        fp = input("  > ").strip()
        pc["forbidden_providers"] = [p.strip() for p in fp.split(",") if p.strip()] if fp else []

        print("  Local-only mode (ollama only)? [y/N]:")
        pc["local_only"] = input("  > ").strip().lower() in ("y", "yes")

    strategy["provider_constraints"] = pc
    return strategy


def _customize_tier_constraints(strategy: dict) -> dict:
    """Customize tier constraints subsection."""
    tc = strategy.get("tier_constraints", {
        "minimum_tier": None, "maximum_tier": None, "phase_overrides": {},
    })

    print()
    print("  TIER CONSTRAINTS")
    print(f"    Minimum tier: {tc.get('minimum_tier') or 'none'}")
    print(f"    Maximum tier: {tc.get('maximum_tier') or 'none'}")
    overrides = tc.get("phase_overrides", {})
    if overrides:
        print(f"    Phase overrides: {overrides}")
    print()
    print("  [enter] Accept    [e] Edit")

    if input("  > ").strip().lower() in ("e", "edit"):
        print()
        print(f"  Minimum tier ({'/'.join(TIER_OPTIONS)}, enter for none):")
        mint = input("  > ").strip().lower()
        tc["minimum_tier"] = mint if mint in TIER_OPTIONS else None

        print(f"  Maximum tier ({'/'.join(TIER_OPTIONS)}, enter for none):")
        maxt = input("  > ").strip().lower()
        tc["maximum_tier"] = maxt if maxt in TIER_OPTIONS else None

        print("  Per-phase tier overrides? [y/N]:")
        if input("  > ").strip().lower() in ("y", "yes"):
            print("  Format: phase_num=tier (e.g., 2=opus,5=sonnet). Enter for none:")
            raw = input("  > ").strip()
            overrides = {}
            if raw:
                for pair in raw.split(","):
                    parts = pair.strip().split("=")
                    if len(parts) == 2:
                        phase_key = f"{parts[0].strip()}-{PHASE_NAMES.get(int(parts[0].strip()), 'unknown').lower().replace(' ', '-')}"
                        if parts[1].strip() in TIER_OPTIONS:
                            overrides[phase_key] = parts[1].strip()
            tc["phase_overrides"] = overrides

    strategy["tier_constraints"] = tc
    return strategy


def _customize_context_window(strategy: dict) -> dict:
    """Customize context window subsection."""
    cw = strategy.get("context_window", {
        "preferred_max": None, "allow_1m_window": True,
    })

    print()
    print("  CONTEXT WINDOW")
    pmax = cw.get("preferred_max")
    print(f"    Preferred max:   {f'{pmax:,}' if pmax else 'provider default'}")
    print(f"    Allow 1M window: {'yes' if cw.get('allow_1m_window', True) else 'no'}")
    print()
    print("  [enter] Accept    [e] Edit")

    if input("  > ").strip().lower() in ("e", "edit"):
        print()
        print("  Preferred max context window (e.g., 200000, enter for provider default):")
        raw = input("  > ").strip()
        cw["preferred_max"] = int(raw) if raw.isdigit() else None

        print("  Allow 1M context window? [Y/n]:")
        ans = input("  > ").strip().lower()
        cw["allow_1m_window"] = ans not in ("n", "no")

    strategy["context_window"] = cw
    return strategy


def _customize_thinking(strategy: dict) -> dict:
    """Customize extended thinking subsection."""
    th = strategy.get("thinking", {
        "extended_thinking": True, "thinking_budget": None, "phase_thinking_config": {},
    })

    print()
    print("  EXTENDED THINKING")
    print(f"    Enabled: {'yes' if th.get('extended_thinking', True) else 'no'}")
    budget = th.get("thinking_budget")
    print(f"    Budget:  {f'{budget:,} tokens' if budget else 'provider default'}")
    ptc = th.get("phase_thinking_config", {})
    if ptc:
        print(f"    Phase overrides: {ptc}")
    print()
    print("  [enter] Accept    [e] Edit")

    if input("  > ").strip().lower() in ("e", "edit"):
        print()
        print("  Enable extended thinking? [Y/n]:")
        ans = input("  > ").strip().lower()
        th["extended_thinking"] = ans not in ("n", "no")

        if th["extended_thinking"]:
            print("  Thinking budget in tokens (enter for provider default):")
            raw = input("  > ").strip()
            th["thinking_budget"] = int(raw) if raw.isdigit() else None

            print("  Per-phase thinking budget? (e.g., 2=20000,5=10000 or enter for none):")
            raw = input("  > ").strip()
            ptc = {}
            if raw:
                for pair in raw.split(","):
                    parts = pair.strip().split("=")
                    if len(parts) == 2 and parts[1].strip().isdigit():
                        pnum = parts[0].strip()
                        phase_key = f"{pnum}-{PHASE_NAMES.get(int(pnum), 'unknown').lower().replace(' ', '-')}"
                        ptc[phase_key] = int(parts[1].strip())
            th["phase_thinking_config"] = ptc

    strategy["thinking"] = th
    return strategy


def _customize_effort(strategy: dict) -> dict:
    """Customize effort level subsection."""
    eff = strategy.get("effort", {"default_level": "high", "phase_effort": {}})

    print()
    print("  EFFORT LEVEL")
    print(f"    Default: {eff.get('default_level', 'high')}")
    pe = eff.get("phase_effort", {})
    if pe:
        print(f"    Phase overrides: {pe}")
    print()
    print("  [enter] Accept    [e] Edit")

    if input("  > ").strip().lower() in ("e", "edit"):
        print()
        print("  Default effort level:")
        eff_default = next(
            (i for i, (k, _) in enumerate(EFFORT_LEVELS)
             if k == eff.get("default_level", "high")),
            2,
        )
        idx = _prompt_numbered(EFFORT_LEVELS, eff_default)
        eff["default_level"] = EFFORT_LEVELS[idx][0]

        print("  Per-phase effort? (e.g., 7=medium,8=low or enter for none):")
        raw = input("  > ").strip()
        pe = {}
        if raw:
            valid_efforts = {e[0] for e in EFFORT_LEVELS}
            for pair in raw.split(","):
                parts = pair.strip().split("=")
                if len(parts) == 2 and parts[1].strip() in valid_efforts:
                    pnum = parts[0].strip()
                    phase_key = f"{pnum}-{PHASE_NAMES.get(int(pnum), 'unknown').lower().replace(' ', '-')}"
                    pe[phase_key] = parts[1].strip()
        eff["phase_effort"] = pe

    strategy["effort"] = eff
    return strategy


def _customize_cost_guardrails(strategy: dict) -> dict:
    """Customize cost guardrails subsection."""
    cg = strategy.get("cost_guardrails", {
        "token_tracking": False, "alert_threshold_usd": None, "per_phase_budget_usd": None,
    })

    print()
    print("  COST GUARDRAILS")
    print(f"    Token tracking:    {'on' if cg.get('token_tracking') else 'off'}")
    alert = cg.get("alert_threshold_usd")
    print(f"    Alert threshold:   {f'${alert:.2f}' if alert else 'none'}")
    ppb = cg.get("per_phase_budget_usd")
    print(f"    Per-phase budget:  {f'${ppb:.2f}' if ppb else 'none'}")
    print()
    print("  [enter] Accept    [e] Edit")

    if input("  > ").strip().lower() in ("e", "edit"):
        print()
        print("  Enable token tracking? [y/N]:")
        cg["token_tracking"] = input("  > ").strip().lower() in ("y", "yes")

        print("  Alert threshold in USD (enter for none):")
        raw = input("  > ").strip()
        try:
            cg["alert_threshold_usd"] = float(raw) if raw else None
        except ValueError:
            cg["alert_threshold_usd"] = None

        print("  Per-phase budget in USD (enter for none):")
        raw = input("  > ").strip()
        try:
            cg["per_phase_budget_usd"] = float(raw) if raw else None
        except ValueError:
            cg["per_phase_budget_usd"] = None

    strategy["cost_guardrails"] = cg
    return strategy


def _customize_fallback(strategy: dict) -> dict:
    """Customize fallback behavior subsection."""
    fb = strategy.get("fallback_behavior", {
        "strategy": "downgrade_tier", "allow_cross_provider_fallback": True,
        "fail_if_no_fallback": False,
    })

    print()
    print("  FALLBACK BEHAVIOR")
    print(f"    Strategy:       {fb.get('strategy', 'downgrade_tier')}")
    print(f"    Cross-provider: {'yes' if fb.get('allow_cross_provider_fallback', True) else 'no'}")
    print(f"    Fail if none:   {'yes' if fb.get('fail_if_no_fallback', False) else 'no'}")
    print()
    print("  [enter] Accept    [e] Edit")

    if input("  > ").strip().lower() in ("e", "edit"):
        print()
        print("  Fallback strategy:")
        fb_default = next(
            (i for i, (k, _) in enumerate(FALLBACK_STRATEGIES)
             if k == fb.get("strategy", "downgrade_tier")),
            0,
        )
        idx = _prompt_numbered(FALLBACK_STRATEGIES, fb_default)
        fb["strategy"] = FALLBACK_STRATEGIES[idx][0]

        print("  Allow cross-provider fallback? [Y/n]:")
        ans = input("  > ").strip().lower()
        fb["allow_cross_provider_fallback"] = ans not in ("n", "no")

        print("  Fail hard if no fallback available? [y/N]:")
        fb["fail_if_no_fallback"] = input("  > ").strip().lower() in ("y", "yes")

    strategy["fallback_behavior"] = fb
    return strategy


# ============================================================================
# UI HELPERS
# ============================================================================

def _prompt_numbered(options: list, default_idx: int = 0) -> int:
    """Display numbered options and return selected index."""
    for i, (key, desc) in enumerate(options):
        marker = " *" if i == default_idx else ""
        print(f"    {i + 1}. {key:<24} {desc}{marker}")
    print()
    raw = input(f"  Choice [{default_idx + 1}]: ").strip()
    if not raw:
        return default_idx
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(options):
            return idx
    except ValueError:
        pass
    return default_idx


def _prompt_phase_gates(current: list) -> list:
    """Toggle phase gates on/off."""
    selected = set(current)
    print()
    print("  Toggle phases (enter number to toggle, 'done' to finish):")
    while True:
        for num, name in sorted(PHASE_NAMES.items()):
            marker = "[x]" if num in selected else "[ ]"
            print(f"    {num}. {marker} {name}")
        print()
        raw = input("  Toggle [done]: ").strip().lower()
        if not raw or raw == "done":
            break
        try:
            num = int(raw)
            if num in PHASE_NAMES:
                if num in selected:
                    selected.discard(num)
                else:
                    selected.add(num)
        except ValueError:
            pass
    return sorted(selected)


def _show_strategy_summary(strategy: dict) -> None:
    """Display a compact strategy summary."""
    tc = strategy.get("tier_constraints", {})
    th = strategy.get("thinking", {})
    eff = strategy.get("effort", {})
    cg = strategy.get("cost_guardrails", {})
    fb = strategy.get("fallback_behavior", {})

    print(f"    Min tier:       {tc.get('minimum_tier') or 'none'}")
    print(f"    Max tier:       {tc.get('maximum_tier') or 'none'}")
    thinking_str = "enabled" if th.get("extended_thinking") else "disabled"
    budget = th.get("thinking_budget")
    if budget:
        thinking_str += f" ({budget:,} tokens)"
    print(f"    Thinking:       {thinking_str}")
    print(f"    Effort:         {eff.get('default_level', 'high')}")
    print(f"    Cost tracking:  {'on' if cg.get('token_tracking') else 'off'}")
    print(f"    Fallback:       {fb.get('strategy', 'downgrade_tier')}")


def _show_summary(autonomy: dict, strategy: dict, provider: str) -> None:
    """Display the final confirmation summary."""
    print("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  SUMMARY")
    print()
    gates = ", ".join(str(g) for g in autonomy.get("phase_gates", []))
    print(f"    Autonomy:  {autonomy['task_mode']} / {autonomy['error_handling']}")
    print(f"    Gates:     {gates}")
    if autonomy["task_mode"] == "selective":
        crit = autonomy.get("selective_criteria", "")
        if crit == "custom":
            tasks = ", ".join(autonomy.get("selective_tasks", []))
            print(f"    Selective: tasks {tasks}")
        elif crit:
            print(f"    Selective: {crit}")
    print()
    th = strategy.get("thinking", {})
    thinking_str = "on" if th.get("extended_thinking") else "off"
    eff = strategy.get("effort", {}).get("default_level", "high")
    print(f"    Strategy:  {strategy['preset']} / {provider}")
    print(f"    Effort:    {eff} / thinking: {thinking_str}")
    tc = strategy.get("tier_constraints", {})
    if tc.get("minimum_tier") or tc.get("maximum_tier"):
        print(f"    Tiers:     min={tc.get('minimum_tier') or 'any'}, "
              f"max={tc.get('maximum_tier') or 'any'}")
    print("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


# ============================================================================
# DEFAULTS & CONFIG
# ============================================================================

def _load_config(config_file: Path) -> dict:
    """Load project-config.json, returning empty dict on failure."""
    try:
        with open(config_file) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _get_primary_provider(config: dict) -> str:
    """Extract primary provider from config."""
    extracted = config.get("extracted", config)
    providers = extracted.get("providers", {})
    chain = providers.get("chain_priority", [])
    if chain:
        return chain[0]
    llm = extracted.get("llm", {})
    return llm.get("primary_provider", "unknown")


def _pipeline_mode(config: dict) -> str:
    """Extract pipeline mode for display."""
    extracted = config.get("extracted", config)
    pipeline = extracted.get("pipeline", {})
    return pipeline.get("mode", "full") + " pipeline"


def _compute_defaults(config: dict, existing_prefs: Path) -> Tuple[dict, dict]:
    """Compute smart defaults from project config and any previous preferences."""
    extracted = config.get("extracted", config)
    pipeline = extracted.get("pipeline", {})
    providers = extracted.get("providers", {})

    # If previous preferences exist, use those as defaults
    if existing_prefs.exists():
        try:
            with open(existing_prefs) as f:
                prev = json.load(f)
            return prev.get("autonomy", {}), prev.get("model_strategy", {})
        except (json.JSONDecodeError, KeyError):
            pass

    autonomy = {
        "task_mode": "fully_autonomous",
        "selective_tasks": [],
        "selective_criteria": None,
        "phase_gates": pipeline.get("human_gates", [0, 2, 5, 9]),
        "error_handling": "pause_on_error",
        "approval_timeout_minutes": None,
        "notify_on_task_complete": False,
    }

    model_strategy = {
        "preset": "balanced",
        "provider_constraints": {
            "mandatory_provider": None,
            "forbidden_providers": [],
            "local_only": False,
        },
        "tier_constraints": {
            "minimum_tier": None,
            "maximum_tier": None,
            "phase_overrides": {},
        },
        "context_window": {
            "preferred_max": None,
            "allow_1m_window": True,
        },
        "thinking": {
            "extended_thinking": True,
            "thinking_budget": providers.get("thinking_budget"),
            "phase_thinking_config": {},
        },
        "effort": {
            "default_level": providers.get("effort_level", "high"),
            "phase_effort": {},
        },
        "cost_guardrails": {
            "token_tracking": False,
            "alert_threshold_usd": None,
            "per_phase_budget_usd": None,
        },
        "fallback_behavior": {
            "strategy": "downgrade_tier",
            "allow_cross_provider_fallback": True,
            "fail_if_no_fallback": False,
        },
    }

    return autonomy, model_strategy


# ============================================================================
# PERSISTENCE
# ============================================================================

def _save_preferences(
    autonomy: dict,
    model_strategy: dict,
    config_file: Path,
    output_file: Path,
    graph,
    mem,
) -> None:
    """Save preferences to config file, output file, graph, and memory."""
    prefs = {
        "autonomy": autonomy,
        "model_strategy": model_strategy,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }

    # 1. Save to output file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(prefs, f, indent=2)
    logger.info("Saved pipeline preferences to %s", output_file)

    # 2. Merge into project-config.json
    try:
        project_config = _load_config(config_file)
        extracted = project_config.get("extracted", {})
        extracted["autonomy"] = autonomy
        extracted["model_strategy"] = model_strategy
        project_config["extracted"] = extracted
        # Flatten for direct access
        project_config["autonomy"] = autonomy
        project_config["model_strategy"] = model_strategy

        with open(config_file, "w") as f:
            json.dump(project_config, f, indent=2)
        logger.info("Updated project config with preferences")
    except Exception as e:
        logger.warning("Failed to update project-config.json: %s", e)

    # 3. Write to knowledge graph
    if graph:
        try:
            # Source node for user-provided pipeline preferences
            graph.add_source(
                id="S-103-pipeline-preferences",
                type="dialogue",
                title="Pipeline Preferences (user input)",
            )
            graph.add_decision(
                id="DEC-103-autonomy",
                title=f"Task autonomy: {autonomy['task_mode']}",
                rationale=(
                    f"User preference — task mode: {autonomy['task_mode']}, "
                    f"error handling: {autonomy['error_handling']}, "
                    f"phase gates: {autonomy['phase_gates']}"
                ),
                status="accepted",
            )
            graph.link("DERIVED_FROM", "Decision", "DEC-103-autonomy",
                       "Source", "S-103-pipeline-preferences")
            graph.add_decision(
                id="DEC-103-model-strategy",
                title=f"Model strategy: {model_strategy['preset']}",
                rationale=(
                    f"User preference — preset: {model_strategy['preset']}, "
                    f"effort: {model_strategy['effort']['default_level']}, "
                    f"thinking: {'enabled' if model_strategy['thinking']['extended_thinking'] else 'disabled'}"
                ),
                status="accepted",
            )
            graph.link("DERIVED_FROM", "Decision", "DEC-103-model-strategy",
                       "Source", "S-103-pipeline-preferences")
        except Exception as e:
            logger.warning("Failed to write decisions to graph: %s", e)

    # 4. Record in memory
    if mem:
        try:
            mem.finding(f"Pipeline preferences: {autonomy['task_mode']}, "
                        f"{model_strategy['preset']} strategy")
        except Exception:
            pass
