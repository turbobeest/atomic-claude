# Atomic Claude 2.0

Python SDLC pipeline with phased orchestration, LLM routing, memory, and agent-driven tasks.

## Installation Modes

- **Runtime** (`curl | bash`): Sparse checkout ~23MB. Core pipeline, agents, audits, config. No tests/docs/scripts.
- **Full** (`--full` flag or `git clone`): Everything ~160MB. Includes tests, docs, scripts, dev tooling.

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
  llm/                 # LLM provider routing
    router.py          # Provider routing and model selection
    resolver.py        # Claude Code integration, intelligent model resolution
    invoke.py          # LLM invocation interface
    anthropic.py       # Anthropic API provider
    bedrock.py         # AWS Bedrock provider
    ollama.py          # Ollama local provider
    cache.py           # Response caching
    capabilities.py    # Model capability matrix
    types.py           # Type definitions
    exceptions.py      # Error handling
  memory/              # Memory subsystem
    checkpoint.py      # Checkpoint creation/management
    compaction.py      # Context compaction algorithms
    recall.py          # Memory recall mechanisms
    store.py           # Memory persistence
  features/            # Feature flags and profiles
phases/                # Dual structure: orchestrators + task implementations
  phaseNN/             # Orchestrator directory (e.g., phase00, phase05)
    orchestratorNN.py  # Phase orchestrator imported by pipeline.py
  phase_NN_name/       # Task implementation directory (e.g., phase_00_setup, phase_05_implementation)
    tasks/             # Python task modules called by orchestrator
      task_NNN_name.py # Individual task (e.g., task_001_mode_selection.py)
orchestration/         # Pipeline coordination
  pipeline.py          # PhasePipeline orchestrator, phase registry, state machine
  task_display.py      # Task roster display and agent resolution
  pre_task_validation.py # Directory purity validation
  dashboard_sync.py    # Real-time dashboard synchronization
  backtrack.py         # Backtracking and rollback
agents/                # 221 agent definitions (186 expert + 35 pipeline)
  agent-manifest.json  # Central agent registry (v3.0.0)
  expert-agents/       # 19 category directories
  pipeline-agents/     # 13 pipeline stage directories
audits/                # 43-category audit framework
  categories/          # Audit category definitions
  data/                # Pre-built audit catalog (JSON)
tests/                 # pytest suite (unit, integration, e2e, uat, performance)
dashboard/             # Real-time web dashboard (Node.js/Express, port 5174)
config/                # Configuration files
  models.json          # LLM provider and model configuration
scripts/               # Utility scripts and audit runners
docs/                  # User-facing documentation
examples/              # Example usage
initialization/        # Setup procedures
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
- **Dashboard**: Node.js/Express (port 3000) with real-time status, memory explorer, skills browser
- **Testing**: pytest with markers (unit, integration, e2e, uat, llm, slow, fileio)

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
- Fixtures: `tests/conftest.py` and `tests/fixtures/`
- Coverage targets: `core/`, `phases/`, `orchestration/` (95%+ with branch coverage)
- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`, `@pytest.mark.uat`, `@pytest.mark.llm`, `@pytest.mark.slow`, `@pytest.mark.fileio`

## Deployments

- **Main dev**: `W:\dev\atomic-claude` (this repo)
- **Operational test**: `W:\dev\eloreum\atomic-claude`
  - Bug fixes should be applied to both repos
  - eloreum is a live MVP build running against the pipeline
