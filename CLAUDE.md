# Atomic Claude 2.0

Python SDLC pipeline with phased orchestration, LLM routing, memory, and agent-driven tasks.

## Dual-Repo Workflow (CRITICAL)

Atomic Claude is developed and operationally tested across two locations:

| Repo | Path | Purpose |
|------|------|---------|
| **Source** | `/mnt/walnut-drive/dev/atomic-claude` | Canonical source. All commits and pushes happen here. |
| **Operational** | `/mnt/walnut-drive/dev/eloreum/atomic-claude` | Live deployment inside the eloreum project. Pipeline runs here against a real codebase. |

### Bug Fix Workflow

When the user reports a bug encountered during eloreum operational testing:

1. **Fix in source** — Edit files in `/mnt/walnut-drive/dev/atomic-claude/`
2. **Push to eloreum** — Copy the fixed file(s) to `/mnt/walnut-drive/dev/eloreum/atomic-claude/` so the live run can continue immediately
3. **Commit in source** — Stage, commit, and push from the source repo
4. **Never edit eloreum's copy directly** — All changes flow source → eloreum, never the reverse

Quick copy pattern:
```bash
cp /mnt/walnut-drive/dev/atomic-claude/<path> /mnt/walnut-drive/dev/eloreum/atomic-claude/<path>
```

## Strict Organization Rules

These rules are non-negotiable. Every file and directory must have a clear, justified reason to exist.

### File Placement

- **No files in the wrong directory.** Every file lives where its type dictates. No Python source in `config/`, no configs in `core/`, no tests outside `dev/tests/`.
- **No orphan files.** Every file must be imported, referenced, or documented. If nothing uses it, delete it.
- **No duplicate functionality.** One canonical location for each concern. If two files do the same thing, consolidate.
- **No ad-hoc directories.** New directories require a clear purpose that existing directories cannot serve. Document the purpose in a docstring or README.

### Naming Conventions

- **Directories**: lowercase with hyphens for multi-word (`expert-agents/`, `code-review/`), underscores for Python packages (`phase_00_setup/`)
- **Python files**: `snake_case.py` — descriptive, no abbreviations
- **Task files**: `task_NNN_descriptive_name.py` (three-digit ID, matches orchestrator registration)
- **Orchestrators**: `orchestratorNN.py` (two-digit phase number)
- **Config files**: lowercase with hyphens (`models.json`, `runtime-manifest.json`)

### What Goes Where

| Content | Location | Notes |
|---------|----------|-------|
| Pipeline entry point | `main.py` | Single entry point, no alternatives |
| Core systems | `core/` | Config, state, memory, LLM, graph, audit, UI |
| Phase orchestrators | `phases/phaseNN/` | One per phase, imports task modules |
| Task implementations | `phases/phase_NN_name/tasks/` | One file per task, called by orchestrator |
| Pipeline coordination | `orchestration/` | Pipeline, phase_runner, backtrack, dashboard |
| Agent definitions | `agents/` | Manifest + expert + pipeline subdirs |
| Audit framework | `audits/` | Categories, data, schema, scripts |
| Dashboard | `dashboard/` | Node.js/Express web UI |
| Configuration | `config/` | JSON configs, models, manifests |
| Tests | `dev/tests/` | pytest suite — NOT in source directories |
| Dev scripts | `dev/scripts/` | Utility scripts, runners, audit tools |
| Documentation | `dev/docs/` | Developer docs, diagrams, guides |
| Runtime state | `.state/` | Gitignored. Created at runtime. |
| Runtime outputs | `.outputs/` | Gitignored. Per-phase working artifacts. |
| Runtime logs | `.logs/` | Gitignored. Execution logs. |

### Prohibited Patterns

- No `utils.py` or `helpers.py` grab-bags — use descriptive module names
- No `test_*.py` files outside `dev/tests/`
- No hardcoded absolute paths — use `ATOMIC_ROOT` or `Path(__file__)`
- No `print()` for user-facing output in core/orchestration — use `core.utils.cli_ui` wrappers
- No bare `except:` or `except Exception: pass` — log at minimum
- No files created during development left in `.outputs/`, `.state/`, or `.logs/`

## Installation Modes

- **Runtime** (`curl | bash`): Sparse checkout ~23MB. Core pipeline, agents, audits, config. Excludes `dev/`.
- **Full** (`--full` flag or `git clone`): Everything ~160MB. Includes `dev/` (tests, docs, scripts, examples).

See `install.sh` at repo root for the installer. Runtime manifest: `config/runtime-manifest.json`.

## Project Structure

```
main.py                # Entry point: run <phase>, status, backtrack, reset
core/                  # Core systems
  config.py            # Configuration management (multi-source: env, .env, JSON, CLI)
  state.py             # Immutable state with atomic transactions, snapshots, rollback
  memory.py            # Memory system wrapper
  audit.py             # Audit framework integration
  ui.py                # Terminal UI (Rich)
  subprocess_runner.py # Subprocess execution with logging
  utils/               # Shared utilities (cli_ui, file_ops)
  llm/                 # LLM provider routing
    router.py          # Provider routing and model selection
    resolver.py        # Claude Code integration, intelligent model resolution
    invoke.py          # LLM invocation interface
    anthropic.py       # Anthropic API provider
    bedrock.py         # AWS Bedrock provider
    ollama.py          # Ollama local provider
    cache.py           # Response caching
    capabilities.py    # Model capability matrix
  memory/              # Memory subsystem
    store.py           # Memory persistence
    checkpoint.py      # Checkpoint creation/management
    compaction.py      # Context compaction
    recall.py          # Memory recall
  graph/               # FalkorDB knowledge graph (optional)
  features/            # Feature flags and profiles
  discovery/           # Project discovery utilities
  skills/              # Skill definitions and execution
phases/                # Dual structure: orchestrators + task implementations
  phaseNN/             # Orchestrator directory (e.g., phase00, phase05)
    orchestratorNN.py  # Phase orchestrator imported by pipeline.py
  phase_NN_name/       # Task implementation directory
    tasks/             # Python task modules called by orchestrator
      task_NNN_name.py # Individual task
orchestration/         # Pipeline coordination
  pipeline.py          # PhasePipeline orchestrator, phase registry, state machine
  phase_runner.py      # Task execution loop, memory, graph context
  task_display.py      # Task roster display and agent resolution
  pre_task_validation.py # Directory purity validation
  dashboard_sync.py    # Real-time dashboard synchronization
  backtrack.py         # Backtracking and rollback
  consensus/           # Multi-agent consensus protocols
  coordination/        # Cross-phase coordination
agents/                # 221 agent definitions (186 expert + 35 pipeline)
  agent-manifest.json  # Central agent registry (v3.0.0)
  expert-agents/       # 19 category directories
  pipeline-agents/     # 13 pipeline stage directories
audits/                # 43-category audit framework
  categories/          # Audit category definitions
  data/                # Pre-built audit catalog (JSON)
  schema/              # Audit data schemas
  scripts/             # Audit runner scripts
dashboard/             # Real-time web dashboard (Node.js/Express, port 5174)
config/                # Configuration files
  models.json          # LLM provider and model configuration
initialization/        # Setup procedures
dev/                   # Development-only (NOT deployed via sparse-checkout)
  tests/               # pytest suite (unit, integration, e2e, performance)
  scripts/             # Utility scripts and audit runners
  docs/                # Developer documentation, diagrams, guides
  examples/            # Example usage
  reports/             # Generated reports (gitignored)
```

### Runtime Directories (gitignored)

```
.state/                # Pipeline state tracking (current-task.json, task-state.json, memory/)
.outputs/              # Working artifacts per phase
.logs/                 # Execution logs
```

## Key Commands

```bash
python main.py run <phase>              # Run a phase (0-9)
python main.py status                   # Check pipeline status
python main.py backtrack <phase> [task] # Reset to earlier point
python main.py reset                    # Full reset
pytest                                  # Run tests (with coverage)
pytest -m unit                          # Unit tests only
pytest -m integration                   # Integration tests only
```

## Tech Stack

- **Python 3.9+** with type hints (Pydantic models)
- **LLM**: Anthropic SDK, Boto3 (Bedrock), Ollama (local), Claude Code CLI
- **CLI**: Click + Rich
- **Dashboard**: Node.js/Express (port 5174) with real-time status, memory explorer, skills browser
- **Testing**: pytest with markers (unit, integration, e2e, llm, slow, fileio)

## LLM Provider Chain

Fallback order: Claude Code CLI → Anthropic API → AWS Bedrock (GovCloud-compatible) → Ollama (offline)

Configured via `.env` (`ATOMIC_LLM_PROVIDER`, `ATOMIC_NETWORK_MODE`). See `.env.example` for all options.

## Conventions

- Phase orchestrators: `phases/phaseNN/orchestratorNN.py` (imported by pipeline.py)
- Phase tasks: `phases/phase_NN_name/tasks/task_NNN_name.py` (called by orchestrators)
- Both `phaseNN/` and `phase_NN_name/` directories are required (orchestrators + tasks)
- State persisted in `.state/`, logs in `.logs/`, outputs in `.outputs/`
- Agent definitions follow templates in `agents/templates/`
- Phase outputs go to `.outputs/N-phase_name/`

## Testing

- Config: `pytest.ini` at project root
- Fixtures: `dev/tests/conftest.py` and `dev/tests/fixtures/`
- Coverage targets: `core/`, `phases/`, `orchestration/` (95%+ with branch coverage)
- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`, `@pytest.mark.llm`, `@pytest.mark.slow`, `@pytest.mark.fileio`
