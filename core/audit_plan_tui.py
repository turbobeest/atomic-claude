"""
Textual TUI for interactive audit plan configuration.

Launches a full-screen terminal app where users can review, toggle,
and configure each audit before evaluation begins.

Keybindings:
  Up/k      Move cursor up
  Down/j    Move cursor down
  Space     Toggle audit on/off
  Enter     Open edit panel for highlighted audit
  A         Toggle all on/off
  R         Confirm and run enabled audits
  S         Skip (cancel all audits)
  Q         Quit (same as skip)
  Escape    Close edit panel (when open)
"""

from __future__ import annotations

import json
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Label,
    RadioButton,
    RadioSet,
    Static,
)


# ---------------------------------------------------------------------------
# Model catalog — loaded from config/models.json
# ---------------------------------------------------------------------------

def _load_model_catalog() -> dict:
    """Load config/models.json and return the full config dict.

    Returns empty dict on any error so the TUI can still function
    with hardcoded fallbacks.
    """
    candidates = [
        Path(__file__).resolve().parent.parent / "config" / "models.json",
        Path.cwd() / "config" / "models.json",
    ]
    for p in candidates:
        if p.is_file():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
    return {}


_catalog: dict | None = None


def _get_catalog() -> dict:
    global _catalog
    if _catalog is None:
        _catalog = _load_model_catalog()
    return _catalog


def _get_providers() -> list[str]:
    """Return ordered list of provider names from config."""
    cat = _get_catalog()
    model_ids = cat.get("model_ids", {})
    if model_ids:
        return list(model_ids.keys())
    return ["anthropic", "aws-bedrock", "claude-code", "ollama"]


def _get_models_for_provider(provider: str) -> list[tuple[str, str]]:
    """Return list of (model_key, display_label) for a provider.

    For Ollama: shows actual model names from ollama_models config,
    grouped by large/small. The model_key is the Ollama model ID.

    For other providers: shows tier-based entries (opus/sonnet/haiku)
    with real model IDs. The model_key is the tier name.
    """
    cat = _get_catalog()

    # Ollama: show actual model names from ollama_models config
    if provider == "ollama":
        ollama_models = cat.get("ollama_models", {})
        result = []
        for group in ("large", "small"):
            models = ollama_models.get(group, [])
            for m in models:
                mid = m.get("id", "unknown")
                name = m.get("name", mid)
                params = m.get("params", "")
                label = f"{name} ({mid})" if name != mid else mid
                result.append((mid, label))
        if result:
            return result
        # Fall through to tier-based if no ollama_models configured

    model_ids = cat.get("model_ids", {})
    provider_models = model_ids.get(provider, {})
    tier_defs = cat.get("tier_definitions", {})

    # Ordered by capability: opus > sonnet > haiku
    tier_order = ["opus", "sonnet", "haiku"]
    result = []

    for tier in tier_order:
        if tier not in tier_defs and tier not in provider_models:
            continue
        model_id = provider_models.get(tier)
        if model_id:
            result.append((tier, f"{tier}: {model_id}"))
        else:
            result.append((tier, f"{tier}: (not available)"))

    if not result:
        # Fallback if config is empty
        for tier in tier_order:
            result.append((tier, tier))

    return result


def _get_context_options(provider: str) -> list[int]:
    """Return available context window sizes for a provider."""
    cat = _get_catalog()
    tier_defs = cat.get("tier_definitions", {})
    prov_overrides = cat.get("provider_overrides", {}).get(provider, {})

    sizes = set()
    for tier, tdef in tier_defs.items():
        ctx = tdef.get("context_window", 200_000)
        sizes.add(ctx)
    # Provider might cap context
    prov_ctx = prov_overrides.get("context_window")
    if prov_ctx:
        sizes.add(prov_ctx)

    return sorted(sizes, reverse=True)


EFFORT_OPTIONS = ["max", "high", "medium"]


# ---------------------------------------------------------------------------
# Edit panel (modal screen)
# ---------------------------------------------------------------------------

class AuditEditScreen(ModalScreen):
    """Modal screen for editing a single audit's configuration."""

    BINDINGS = [
        Binding("escape", "dismiss_edit", "Close"),
    ]

    CSS = """
    AuditEditScreen {
        align: right middle;
    }
    #edit-panel {
        width: 50;
        height: 100%;
        background: $surface;
        border-left: thick $accent;
        padding: 1 2;
        overflow-y: auto;
    }
    #edit-panel Label {
        margin-top: 1;
        text-style: bold;
    }
    RadioSet {
        margin-left: 1;
        height: auto;
    }
    """

    def __init__(self, audit_config, config_index: int):
        super().__init__()
        self.audit_config = audit_config
        self.config_index = config_index

    def compose(self) -> ComposeResult:
        a = self.audit_config.audit
        cur_provider = self.audit_config.provider
        cur_model = self.audit_config.model
        cur_ctx = self.audit_config.context_window
        cur_effort = self.audit_config.effort

        providers = _get_providers()
        models = _get_models_for_provider(cur_provider)
        ctx_options = _get_context_options(cur_provider)

        with Vertical(id="edit-panel"):
            yield Label(f"Edit: Audit #{self.config_index + 1}")
            yield Static(a.get("audit_name", "Unnamed")[:45])
            yield Static("")

            yield Label("Provider")
            provider_set = RadioSet(id="provider-select")
            with provider_set:
                for p in providers:
                    yield RadioButton(
                        p,
                        value=(p == cur_provider),
                        name=p,
                    )

            yield Label("Model")
            model_set = RadioSet(id="model-select")
            with model_set:
                for tier, display in models:
                    yield RadioButton(
                        display,
                        value=(tier == cur_model),
                        name=tier,
                    )

            yield Label("Context Window")
            ctx_set = RadioSet(id="context-select")
            with ctx_set:
                for c in ctx_options:
                    label = f"{c:,}"
                    yield RadioButton(
                        label,
                        value=(c == cur_ctx),
                        name=str(c),
                    )

            yield Label("Effort")
            effort_set = RadioSet(id="effort-select")
            with effort_set:
                for e in EFFORT_OPTIONS:
                    yield RadioButton(
                        e,
                        value=(e == cur_effort),
                        name=e,
                    )

    def _rebuild_model_set(self, provider: str) -> None:
        """Rebuild model RadioSet when provider changes."""
        models = _get_models_for_provider(provider)
        cur_tier = self.audit_config.model

        model_set = self.query_one("#model-select", RadioSet)
        model_set.remove_children()

        for tier, display in models:
            btn = RadioButton(
                display,
                value=(tier == cur_tier),
                name=tier,
            )
            model_set.mount(btn)

        # If current tier isn't available for new provider, pick first
        available_tiers = [t for t, _ in models]
        if cur_tier not in available_tiers and available_tiers:
            self.audit_config.model = available_tiers[0]

    def _rebuild_context_set(self, provider: str) -> None:
        """Rebuild context window RadioSet when provider changes."""
        ctx_options = _get_context_options(provider)
        cur_ctx = self.audit_config.context_window

        ctx_set = self.query_one("#context-select", RadioSet)
        ctx_set.remove_children()

        for c in ctx_options:
            label = f"{c:,}"
            btn = RadioButton(
                label,
                value=(c == cur_ctx),
                name=str(c),
            )
            ctx_set.mount(btn)

    @on(RadioSet.Changed, "#provider-select")
    def on_provider_changed(self, event: RadioSet.Changed) -> None:
        if event.pressed and event.pressed.name:
            new_provider = event.pressed.name
            self.audit_config.provider = new_provider
            self._rebuild_model_set(new_provider)
            self._rebuild_context_set(new_provider)

    @on(RadioSet.Changed, "#model-select")
    def on_model_changed(self, event: RadioSet.Changed) -> None:
        if event.pressed and event.pressed.name:
            self.audit_config.model = event.pressed.name

    @on(RadioSet.Changed, "#context-select")
    def on_context_changed(self, event: RadioSet.Changed) -> None:
        if event.pressed and event.pressed.name:
            try:
                self.audit_config.context_window = int(event.pressed.name)
            except ValueError:
                pass

    @on(RadioSet.Changed, "#effort-select")
    def on_effort_changed(self, event: RadioSet.Changed) -> None:
        if event.pressed and event.pressed.name:
            self.audit_config.effort = event.pressed.name

    def action_dismiss_edit(self) -> None:
        self.dismiss()


# ---------------------------------------------------------------------------
# Main TUI app
# ---------------------------------------------------------------------------

def _format_model_display(tier: str, provider: str) -> str:
    """Short model display for the table column — show real model ID."""
    cat = _get_catalog()
    model_ids = cat.get("model_ids", {})
    provider_models = model_ids.get(provider, {})
    model_id = provider_models.get(tier)
    if model_id:
        # Shorten long IDs for table display
        # "claude-opus-4-6" → "opus-4-6"
        # "anthropic.claude-sonnet-4-5-20250929-v1:0" → "sonnet-4-5-v1:0"
        short = model_id
        short = short.replace("anthropic.", "")
        short = short.replace("claude-", "")
        # Collapse date suffixes: -20250929- → -
        import re
        short = re.sub(r"-\d{8}-", "-", short)
        short = re.sub(r"-\d{8}$", "", short)
        return short
    return f"{tier} (n/a)"


class AuditPlanApp(App):
    """Textual TUI for audit plan configuration."""

    CSS = """
    Screen {
        layout: vertical;
    }
    #status-bar {
        height: 1;
        dock: bottom;
        background: $accent;
        color: $text;
        padding: 0 2;
    }
    DataTable {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("k", "cursor_up", "Up", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("space", "toggle_audit", "Toggle"),
        Binding("a", "toggle_all", "Toggle All"),
        Binding("r", "run_audits", "Run"),
        Binding("s", "skip_audits", "Skip"),
        Binding("q", "quit_app", "Quit"),
    ]

    user_skipped: bool = False

    def __init__(self, audit_configs: list, phase_num: int = 0):
        super().__init__()
        self.audit_configs = audit_configs
        self.phase_num = phase_num
        self.user_skipped = False

    def compose(self) -> ComposeResult:
        from collections import Counter
        cats = Counter(c.audit.get("category", "?") for c in self.audit_configs)
        enabled = sum(1 for c in self.audit_configs if c.enabled)
        disabled = len(self.audit_configs) - enabled

        yield Header()
        yield DataTable(id="audit-table")
        yield Static(
            f"  {len(self.audit_configs)} audits across {len(cats)} domains   "
            f"  {enabled} enabled / {disabled} disabled   "
            f"  ↑↓/jk Navigate  Space Toggle  Enter Edit  A All  R Run  S Skip",
            id="status-bar",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.title = f"Phase {self.phase_num} Audit Plan"

        table = self.query_one("#audit-table", DataTable)
        table.cursor_type = "row"

        table.add_columns(
            "#", "En", "Sev", "Agent", "Model", "Provider",
            "Ctx", "Effort", "Category", "Audit Name"
        )

        for i, cfg in enumerate(self.audit_configs):
            table.add_row(*self._row_values(i, cfg), key=str(i))

    def _row_values(self, idx: int, cfg) -> tuple:
        """Build display values for a single table row."""
        a = cfg.audit
        check = "✓" if cfg.enabled else "·"
        sev = a.get("severity", "?")
        agent = cfg.agent[:22]
        model = _format_model_display(cfg.model, cfg.provider)
        provider = cfg.provider[:12]
        ctx = f"{cfg.context_window:,}"
        effort = cfg.effort
        cat = a.get("category", "?")
        if len(cat) > 14:
            cat = cat[:12] + "…"
        name = a.get("audit_name", "Unnamed")
        if len(name) > 35:
            name = name[:33] + "…"

        return (str(idx + 1), check, sev, agent, model,
                provider, ctx, effort, cat, name)

    def _update_row(self, idx: int) -> None:
        """Update a single row in the table."""
        table = self.query_one("#audit-table", DataTable)
        cfg = self.audit_configs[idx]
        row_key = str(idx)
        row_data = self._row_values(idx, cfg)

        for col_idx, value in enumerate(row_data):
            col_key = table.ordered_columns[col_idx].key
            table.update_cell(row_key, col_key, value)

    def _update_status_bar(self) -> None:
        """Update the status bar with enabled/disabled counts."""
        from collections import Counter
        cats = Counter(c.audit.get("category", "?") for c in self.audit_configs)
        enabled = sum(1 for c in self.audit_configs if c.enabled)
        disabled = len(self.audit_configs) - enabled
        status = self.query_one("#status-bar", Static)
        status.update(
            f"  {len(self.audit_configs)} audits across {len(cats)} domains   "
            f"  {enabled} enabled / {disabled} disabled   "
            f"  ↑↓/jk Navigate  Space Toggle  Enter Edit  A All  R Run  S Skip"
        )

    def _get_cursor_index(self) -> int | None:
        """Get the index of the currently highlighted row."""
        table = self.query_one("#audit-table", DataTable)
        if table.cursor_row is not None and 0 <= table.cursor_row < len(self.audit_configs):
            return table.cursor_row
        return None

    def action_cursor_up(self) -> None:
        table = self.query_one("#audit-table", DataTable)
        table.action_cursor_up()

    def action_cursor_down(self) -> None:
        table = self.query_one("#audit-table", DataTable)
        table.action_cursor_down()

    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        """Enter pressed on a row — open the edit panel."""
        self.action_edit_audit()

    def action_toggle_audit(self) -> None:
        idx = self._get_cursor_index()
        if idx is not None:
            self.audit_configs[idx].enabled = not self.audit_configs[idx].enabled
            self._update_row(idx)
            self._update_status_bar()

    def action_edit_audit(self) -> None:
        idx = self._get_cursor_index()
        if idx is not None:
            cfg = self.audit_configs[idx]

            def on_dismiss(_result=None) -> None:
                self._update_row(idx)
                self._update_status_bar()

            self.push_screen(AuditEditScreen(cfg, idx), callback=on_dismiss)

    def action_toggle_all(self) -> None:
        any_enabled = any(c.enabled for c in self.audit_configs)
        new_state = not any_enabled
        for c in self.audit_configs:
            c.enabled = new_state
        for i in range(len(self.audit_configs)):
            self._update_row(i)
        self._update_status_bar()

    def action_run_audits(self) -> None:
        self.user_skipped = False
        self.exit()

    def action_skip_audits(self) -> None:
        self.user_skipped = True
        self.exit()

    def action_quit_app(self) -> None:
        self.user_skipped = True
        self.exit()
