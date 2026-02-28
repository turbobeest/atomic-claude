# Atomic Claude

Python-based SDLC pipeline with phased orchestration, LLM routing, memory, and agent-driven tasks.

## Project Status

⚠️ **Operational Testing** - Pipeline is functional and entering live operational testing.

**For Early Adopters:**
- Expect to encounter bugs in current tasks
- Be prepared to fix issues locally, backtrack, and retry
- **Please report bugs as issues**: https://github.com/turbobeest/atomic-claude/issues
- Workflow: Find bug → Fix task → `python main.py backtrack <phase> <task>` → Retry

## Quick Start

### Running the Pipeline
```bash
# Run a phase (0-9)
python main.py run <phase> [--resume-at=<task>]

# Check pipeline status
python main.py status

# Backtrack to earlier point
python main.py backtrack <phase> [<task>]

# Reset everything
python main.py reset
```

### Dashboard & Monitoring
```bash
# Start real-time dashboard (port 5174)
bash dashboard/start-dashboard.sh

# Stop dashboard
bash dashboard/stop-dashboard.sh

# View in browser
# macOS: open http://127.0.0.1:5174
# Windows: start http://127.0.0.1:5174
# Linux: xdg-open http://127.0.0.1:5174
```

### Testing
```bash
# Run test suite
pytest

# Run specific test categories
pytest -m unit           # Unit tests
pytest -m integration    # Integration tests
pytest -m e2e            # End-to-end tests

# With coverage
pytest --cov=core --cov=phases --cov=orchestration
```

## Key Features

### 🧠 LLM Provider Chain
Multi-provider fallback with intelligent routing:
1. **Claude Code CLI** (preferred) - Native integration
2. **Anthropic API** - Direct API access
3. **AWS Bedrock** (GovCloud-compatible) - Enterprise deployments
4. **Ollama** - Local/offline operation

Configure via `.env` - see `.env.example` for options.

### 🤖 Agent System
- **221 agents** (186 expert + 35 pipeline)
- **19 categories**: Backend, Frontend, DevOps, Data, Security, Business Ops, etc.
- Centralized registry: `agents/agent-manifest.json` (v3.0.0)
- Browse agents: http://127.0.0.1:5175 (when dashboard running)

### 🔍 Audit Framework
- **43 audit categories** with 2,186+ checks
- Security, performance, dependency, code quality audits
- Automated audit runners in `scripts/`
- Browse audits: http://127.0.0.1:5176 (when dashboard running)

### 🎯 Skills System
- **Tactical skills** - Project-specific capabilities
- **Community skills** - superpowers, trailofbits plugins, ralph monitoring
- Web browser UI: http://127.0.0.1:5177 (when dashboard running)

### 💾 Memory System
- **Checkpoint creation** - Capture task context
- **Compaction** - Intelligent context compression
- **Recall mechanisms** - Retrieve relevant prior work
- **Persistence** - State maintained in `.state/memory/`

### 📊 Real-Time Dashboard
- **Main dashboard** (port 5174): Pipeline status, task tracking, memory flow
- **Agent Manager** (port 5175): Browse and search agents
- **Audit Browser** (port 5176): Explore audit categories
- **Skills Browser** (port 5177): View available skills

### 🔄 Phase Management
- **10 phases** (0-9): Setup → Discovery → PRD → Tasking → Specification → Implementation → Code Review → Integration → Deployment Prep → Release
- **State machine** with dependencies and validation
- **Atomic operations** with rollback capability
- **Auto-chaining** between phases (optional)

## Architecture

```
atomic-claude/
├── main.py                 # Entry point: run, status, backtrack, reset
├── core/                   # Core systems
│   ├── config.py           # Multi-source configuration
│   ├── state.py            # Immutable state with transactions
│   ├── memory.py           # Memory system wrapper
│   ├── llm/                # LLM provider routing
│   │   ├── router.py       # Provider selection logic
│   │   ├── anthropic.py    # Anthropic API
│   │   ├── bedrock.py      # AWS Bedrock
│   │   ├── ollama.py       # Local Ollama
│   │   └── cache.py        # Response caching
│   └── memory/             # Memory subsystem
│       ├── checkpoint.py   # Checkpoint management
│       ├── compaction.py   # Context compaction
│       └── recall.py       # Memory recall
├── phases/                 # Dual structure
│   ├── phaseNN/            # Orchestrators (imported by pipeline.py)
│   │   └── orchestratorNN.py
│   └── phase_NN_name/      # Task implementations (called by orchestrators)
│       └── tasks/
│           └── task_NNN_name.py
├── orchestration/          # Pipeline coordination
│   ├── pipeline.py         # Phase registry, state machine
│   ├── task_display.py     # Task roster display
│   └── backtrack.py        # Rollback mechanisms
├── agents/                 # 221 agent definitions
│   ├── agent-manifest.json # Central registry (v3.0.0)
│   ├── expert-agents/      # 19 category directories
│   └── pipeline-agents/    # 13 pipeline stage directories
├── audits/                 # 43-category audit framework
│   ├── categories/         # Audit definitions
│   └── audit-browser/      # Web UI (port 5176)
├── skills/                 # Skills system
│   ├── tactical/           # Project-specific skills
│   ├── community/          # Community contributions
│   └── skills-browser/     # Web UI (port 5177)
├── dashboard/              # Real-time monitoring
│   ├── server.js           # Express server (port 5174)
│   ├── public/             # Web UI
│   └── start-dashboard.sh  # Startup script
├── tests/                  # Pytest suite (95%+ coverage)
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── e2e/                # End-to-end tests
├── config/                 # Configuration files
│   └── models.json         # LLM provider/model config
├── scripts/                # Utility scripts
└── docs/                   # Comprehensive documentation

Runtime Directories (gitignored):
├── .state/                 # Pipeline state tracking
├── .outputs/               # Working artifacts per phase
└── .logs/                  # Execution logs
```

## Documentation

### Getting Started
- **[CLAUDE.md](CLAUDE.md)** - Technical architecture and conventions
- **[User Guide](docs/USER-GUIDE.md)** - How to use the pipeline
- **[Developer Guide](docs/DEVELOPER-GUIDE.md)** - How to extend and modify

### Reference
- **[API Reference](docs/API-REFERENCE.md)** - Core APIs and interfaces
- **[Project Structure](docs/PROJECT-STRUCTURE.md)** - Directory layout and design decisions
- **[Feature Flags](docs/FEATURE-FLAG-ARCHITECTURE.md)** - Feature flag system
- **[MCP Integration](docs/MCP.md)** - Model Context Protocol support

### Operational
- **[OPERATIONAL.md](OPERATIONAL.md)** - Dual-repo workflow and safety rules

### Historical (Archived)
- Migration documentation: `docs/archive/migration/`
- Completion reports: `docs/archive/completion-reports/`

## Configuration

### Environment Variables
Configure via `.env` file (see `.env.example`):

```bash
# LLM Provider Selection
ATOMIC_LLM_PROVIDER=claude-code  # claude-code, anthropic, bedrock, ollama
ATOMIC_NETWORK_MODE=online        # online, offline, local

# API Keys (when not using Claude Code CLI)
ANTHROPIC_API_KEY=sk-ant-...
AWS_PROFILE=default               # For Bedrock

# Dashboard
ATOMIC_TASKS_PORT=5174           # Main dashboard port
```

### Multi-Source Configuration
Priority order: CLI args → Environment vars → `.env` file → `config/models.json` → Defaults

## Technology Stack

- **Python 3.9+** with type hints (Pydantic models)
- **LLM SDKs**: Anthropic SDK, Boto3 (Bedrock), Ollama client, Claude Code CLI
- **CLI**: Click + Rich for terminal UI
- **Dashboard**: Node.js/Express (port 5174) with real-time status
- **Testing**: pytest with markers (unit, integration, e2e, uat, llm, slow, fileio)

## Development

### Project Structure Conventions
- Phase orchestrators: `phases/phaseNN/orchestratorNN.py` (imported by pipeline.py)
- Phase tasks: `phases/phase_NN_name/tasks/task_NNN_name.py` (called by orchestrators)
- Both `phaseNN/` and `phase_NN_name/` directories are required
- State persisted in `.state/`, logs in `.logs/`, outputs in `.outputs/`
- Agent definitions follow templates in `agents/templates/`

### Testing Infrastructure
- Config: `pytest.ini` at project root
- Fixtures: `tests/conftest.py` and `tests/fixtures/`
- Coverage targets: `core/`, `phases/`, `orchestration/` (95%+ with branch coverage)
- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`, etc.

### Contributing
When you find bugs:
1. Fix the task locally in `phases/phase_NN_name/tasks/task_NNN_name.py`
2. Test the fix: `python main.py backtrack <phase> <task>` then `python main.py run <phase>`
3. Report the issue: https://github.com/turbobeest/atomic-claude/issues
4. Include: Task ID, error message, fix description, test results

## License

MIT

## Links

- **GitHub**: https://github.com/turbobeest/atomic-claude
- **Issues**: https://github.com/turbobeest/atomic-claude/issues
- **Branches**: `python` (active development), `main` (stable)
