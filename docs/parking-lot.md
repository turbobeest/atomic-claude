# Parking Lot: Textual TUI Migration

> **Status**: Planned — execute after first successful operational test
> **Priority**: High — directly impacts operator experience for every pipeline run
> **Dependency**: `pip install textual textual-dev`

## Motivation

The current CLI renders output as sequential scrolling text across 4 inconsistent UI systems (ANSI box-drawing, Rich, Textual audit TUI, curses). This wastes screen real estate, provides no mid-task progress visibility, and makes long-running phases feel stalled. Textual consolidates all of this into a single framework with persistent split-pane layouts, real-time widget updates, and keyboard navigation.

## Current State

| Component | Tech | File | Pain Point |
|-----------|------|------|------------|
| Phase/task headers | ANSI box-drawing + emoji | `core/ui.py` | Scrolls off screen |
| Color helpers, prompts | ANSI + readline | `core/utils/cli_ui.py` | No layout control |
| Agent roster table | Manual ANSI box-drawing | `orchestration/task_display.py` | Hard to maintain, no color |
| Audit progress | Rich Live + Progress | `core/audit.py` | Only audit subsystem has this |
| Audit plan config | Textual DataTable | `core/audit_plan_tui.py` | Falls back to plain text |
| File exclusion picker | Curses | `core/utils/multi_select.py` | Fragile, no tree view |
| Pipeline status | Plain print + emoji | `core/state.py` | Too minimal |
| LLM output display | Custom wrap_text() | `core/ui.py` | No syntax highlighting |

## Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Header: Phase 2 — PRD Generation           [3/7 tasks]  ▶  │
├──────────────────────┬──────────────────────────────────────┤
│  Task Roster         │  Task Output                         │
│                      │                                      │
│  ✅ 201 Entry Valid  │  ⚡ Task 204: PRD Generation          │
│  ✅ 202 Corpus Scan  │                                      │
│  ▶  203 Agent Select │  Analyzing 47 source files...        │
│  ⬚ 204 PRD Gen      │  ████████████████░░░░  78%           │
│  ⬚ 205 PRD Review   │                                      │
│  ⬚ 206 Approval     │  ## Generated Sections               │
│  ⬚ 207 Checkpoint   │  1. Overview ✓                       │
│                      │  2. Requirements ✓                   │
│  Agent: prd-expert   │  3. Architecture (generating...)     │
│  Model: opus-4       │                                      │
│  Provider: anthropic │  ```python                           │
│  Context: 200K       │  class PRDGenerator:                 │
│                      │      def generate(self):             │
│                      │          ...                         │
├──────────────────────┴──────────────────────────────────────┤
│  Memory: 12 entries | Checkpoint: phase1-20260223 | ⏱ 4m32s │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: PipelineApp Shell (foundation)

**Goal**: Wrap existing orchestrators in a Textual App without changing task logic.

**New file**: `core/tui/app.py`

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
from textual.containers import Horizontal, Vertical

class PipelineApp(App):
    CSS = """
    #task-sidebar { width: 28; }
    #task-output { width: 1fr; }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            yield Vertical(id="task-sidebar")
            yield Vertical(id="task-output")
        yield Footer()
```

**Tasks**:
- [ ] Create `core/tui/` package with `__init__.py`, `app.py`
- [ ] `PipelineApp` with Header (phase name + progress), Footer (memory/checkpoint/timer)
- [ ] Left sidebar: task list with status icons (pending/running/done/failed)
- [ ] Right panel: scrolling output log
- [ ] Wire `main.py run <phase>` to launch `PipelineApp` when TTY detected
- [ ] Fallback to current ANSI output when `--no-tui` flag or non-TTY
- [ ] Pass-through: orchestrator print() captured and routed to output panel

**Textual widgets used**: `Header`, `Footer`, `Static`, `Horizontal`, `Vertical`, `RichLog`

### Phase 2: Agent Roster Screen

**Goal**: Replace ANSI box-drawing roster table with interactive DataTable.

**New file**: `core/tui/roster.py`

**Tasks**:
- [ ] `AgentRosterTable(DataTable)` widget showing agent name, provider, model, context, effort
- [ ] Row selection to override agent/model/provider (replaces numbered menu)
- [ ] Tier quick-switch keybindings (1=Opus, 2=Sonnet, 3=Haiku)
- [ ] Provider quick-switch (p=cycle provider)
- [ ] "Run" button / Enter to proceed, Esc to abort
- [ ] Retire `orchestration/task_display.py` ANSI table (keep override logic as data layer)
- [ ] Scope selector: apply override to all tasks or current only

**Textual widgets used**: `DataTable`, `Button`, `Select`, `RadioSet`

### Phase 3: Live Task Progress

**Goal**: Show real-time progress during LLM calls and long operations.

**New file**: `core/tui/progress.py`

**Tasks**:
- [ ] `TaskProgress` widget: progress bar + step label + elapsed time
- [ ] Hook into `core/llm/invoke.py` to emit progress events (streaming tokens counted)
- [ ] Hook into task functions to emit sub-step updates (e.g., "Scanning file 23/47")
- [ ] Integrate with `orchestration/dashboard_sync.py` so TUI and web dashboard share events
- [ ] Replace audit Rich.Live progress with Textual ProgressBar (unify)

**Textual widgets used**: `ProgressBar`, `Static`, `Label`

**Event protocol**:
```python
# Tasks emit progress via a simple protocol
class TaskProgress:
    def update(self, step: str, current: int = 0, total: int = 0): ...
    def log(self, message: str): ...
    def complete(self, summary: str): ...
```

### Phase 4: LLM Output Viewer

**Goal**: Syntax-highlighted, structured display of LLM responses.

**New file**: `core/tui/output.py`

**Tasks**:
- [ ] `LLMOutputPanel(RichLog)` widget with markdown rendering
- [ ] Syntax highlighting for code blocks (via Rich Syntax integration)
- [ ] Section headers bolded, bullet lists formatted
- [ ] Auto-scroll with "pin to bottom" toggle
- [ ] Copy-to-clipboard for code blocks (keybinding)
- [ ] Replace `core/ui.py` `wrap_text()` and `print_llm_output()` for TUI mode
- [ ] Keep `core/ui.py` functions for non-TUI fallback

**Textual widgets used**: `RichLog`, `Markdown` (if textual-markdown available)

### Phase 5: Interactive Screens

**Goal**: Full-screen interactive workflows for complex operations.

**New files**: `core/tui/screens/` package

**Tasks**:
- [ ] `StatusScreen` — phase overview with task tree, timing, artifact counts (replaces `core/state.py` display)
- [ ] `AuditPlanScreen` — migrate `core/audit_plan_tui.py` into the app (currently standalone)
- [ ] `FilePickerScreen` — replace curses `multi_select.py` with Textual `Tree` widget for file exclusion
- [ ] `BacktrackScreen` — visual phase/task selector for `main.py backtrack` with preview of what gets rolled back
- [ ] Command palette (Ctrl+P) wired to common actions: skip task, override agent, view memory, open dashboard

**Textual widgets used**: `Tree`, `DataTable`, `OptionList`, `Tabs`, `TabbedContent`

### Phase 6: Dashboard Bridge

**Goal**: Unify TUI and web dashboard event streams.

**Tasks**:
- [ ] Shared event bus: TUI widgets and dashboard SSE read from same source
- [ ] `textual serve` option to expose TUI as web interface (alternative to Express dashboard)
- [ ] Memory feed widget in TUI sidebar (mirrors dashboard memory explorer)
- [ ] Consider: does `textual serve` replace the Express dashboard long-term?

## File Structure

```
core/tui/
├── __init__.py           # TUI availability check, launch helper
├── app.py                # PipelineApp main application
├── roster.py             # AgentRosterTable widget
├── progress.py           # TaskProgress widget + event protocol
├── output.py             # LLMOutputPanel widget
├── styles.tcss           # Textual CSS (external stylesheet)
└── screens/
    ├── __init__.py
    ├── status.py          # Pipeline status overview
    ├── audit_plan.py      # Audit plan configuration
    ├── file_picker.py     # File exclusion tree
    └── backtrack.py       # Backtrack phase/task selector
```

## Migration Strategy

1. **Additive, not destructive** — all existing `core/ui.py` and `core/utils/cli_ui.py` functions stay intact as the non-TUI fallback path
2. **Detection at entry point** — `main.py` checks `sys.stdin.isatty()` and `--no-tui` flag; launches `PipelineApp` or falls back to current behavior
3. **Orchestrators emit events** — instead of calling `print()` directly, orchestrators call a thin abstraction that routes to either TUI widget updates or plain print
4. **One phase at a time** — each TUI phase can be developed and tested independently; partial migration is fine (e.g., Phase 1 shell works even if Phase 4 output viewer isn't done yet)
5. **Testing** — Textual's `pilot` framework for TUI interaction tests; existing pytest suite unchanged for non-UI logic

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Framework | Textual (not curses, not blessed) | Built on Rich (already in project), CSS layout, async-native, web-servable |
| Fallback | Keep all current ANSI output | Non-TTY, SSH pipes, CI/CD, `--no-tui` flag |
| Stylesheet | External `.tcss` file | Easier to iterate on layout without touching Python |
| Event routing | Thin abstraction over print() | Minimal change to orchestrators; TUI or plain print based on mode |
| Dashboard coexistence | Both run simultaneously | TUI for operator, web dashboard for observers/monitoring |

## Dependencies

```
textual>=3.0.0       # TUI framework
textual-dev>=1.0.0   # Dev tools (console, CSS live reload) — dev only
```

No other new dependencies. Textual pulls in Rich automatically (already present).

## Estimated Scope

| Phase | New Code | Modified Files | Complexity |
|-------|----------|----------------|------------|
| 1. App Shell | ~200 lines | main.py, orchestrators (thin wrapper) | Medium |
| 2. Agent Roster | ~150 lines | orchestration/task_display.py (data extraction) | Medium |
| 3. Live Progress | ~120 lines | core/llm/invoke.py, task functions (emit hooks) | High |
| 4. LLM Output | ~100 lines | core/ui.py (keep as fallback) | Low |
| 5. Screens | ~300 lines | core/audit_plan_tui.py, core/utils/multi_select.py | Medium |
| 6. Dashboard Bridge | ~100 lines | orchestration/dashboard_sync.py | Medium |
| **Total** | **~970 lines** | | |

## Success Criteria

After full migration, a pipeline run should:
- Show persistent split-pane layout with task list, output, and progress visible simultaneously
- Update progress bar in real-time during LLM calls
- Allow agent/model override via keyboard without leaving the app
- Syntax-highlight code blocks in LLM output
- Fall back cleanly to scrolling ANSI output with `--no-tui`
- Work over SSH with 80x24 minimum terminal
- Not break any existing pytest tests
