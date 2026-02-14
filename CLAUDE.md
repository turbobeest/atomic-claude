# Atomic Claude 2.0

Python SDLC pipeline with phased orchestration, LLM routing, memory, and agent-driven tasks.

## Project Structure

```
main.py              # Entry point: run <phase>, status, backtrack, reset
core/                # Core systems
  llm/               # LLM provider routing (Anthropic, Bedrock, Ollama)
  memory/            # Checkpoint, compaction, recall, store
  task/              # Task execution, dependencies, validation
  config.py          # Configuration management
  state.py           # Pipeline state tracking
  ui.py              # Terminal UI (Rich)
  features/          # Feature flags and profiles
phases/              # Phase 00-09 orchestrators + shell task scripts
orchestration/       # Pipeline, scheduling, git, backtracking, dashboard sync
agents/              # 221 agent definitions (186 expert + 35 pipeline)
audits/              # 43-category audit framework
tests/               # pytest suite (unit, integration, e2e, uat)
dashboard/           # Real-time web dashboard (Node/Express)
```

## Key Commands

```bash
python main.py run <phase>              # Run a phase
python main.py status                   # Check pipeline status
python main.py backtrack <phase> [task] # Reset to earlier point
python main.py reset                    # Full reset
pytest                                  # Run tests (with coverage)
pytest -m unit                          # Unit tests only
pytest -m integration                   # Integration tests only
```

## Tech Stack

- **Python 3.9+** with type hints (Pydantic models)
- **LLM**: Anthropic SDK, Boto3 (Bedrock), Ollama (local)
- **CLI**: Click + Rich
- **Web**: FastAPI + Uvicorn (dashboard)
- **Testing**: pytest with markers (unit, integration, e2e, uat, llm, slow)
- **Shell**: Bash task scripts in phases/ executed by Python orchestrators

## Conventions

- Phase orchestrators are Python (`phases/phaseNN/orchestratorNN.py`)
- Tasks within phases are shell scripts (`phases/phaseNN/tasks/*.sh`)
- State persisted in `.state/`, logs in `.logs/`, outputs in `.outputs/`
- `reports/` is scratch work only
- Agent definitions follow templates in `agents/templates/`

## Testing

- Config: `pytest.ini` at project root
- Fixtures: `tests/conftest.py` and `tests/fixtures/`
- Coverage targets: `core/`, `phases/`, `orchestration/`
- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`, `@pytest.mark.uat`, `@pytest.mark.llm`, `@pytest.mark.slow`
