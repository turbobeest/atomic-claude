# Atomic Claude 2.0

Clean, organized Python implementation of the Atomic Claude SDLC pipeline.

## Quick Start

```bash
# Run pipeline
python main.py run <phase> [--resume-at=<task>]

# Check status
python main.py status

# Backtrack to earlier point
python main.py backtrack <phase> [<task>]

# Reset everything
python main.py reset
```

## Architecture

```
atomic-claude2/
├── main.py              # Central orchestrator
├── core/                # Core utilities (LLM, state, config, memory, providers)
├── phases/              # Phase modules (orchestrator + tasks per phase)
│   ├── phase00/        # Setup
│   ├── phase01/        # Discovery
│   ├── phase02/        # PRD
│   └── ...
├── orchestration/       # End-of-task processes (organization, git, backtrack)
├── dashboard/           # Real-time web dashboard
├── reports/             # Scratch work only
├── .outputs/            # Working artifacts per phase
├── .state/              # State tracking
├── .logs/               # Execution logs
├── config/              # Configuration
└── docs/                # Documentation
```

## Key Features

✅ **Clean Organization** - Every file has its place, enforced by organization agent
✅ **Easy to Extend** - Drop new task scripts into phase directories
✅ **Bulletproof State** - Organization agent prevents chaos
✅ **Git Tracking** - Commit prompts keep history clean
✅ **Easy Backtracking** - Reset to any point cleanly
✅ **Accurate Dashboard** - Real-time status monitoring

## Documentation

- [Project Structure](docs/PROJECT-STRUCTURE.md) - Complete directory layout and design decisions
- [Refactoring Plan](docs/REFACTORING-PLAN-V2.md) - Detailed extraction and implementation plan
- [Forcing Function](docs/FORCING-FUNCTION.md) - Directory purity enforcement system
- [Architecture Overview](docs/architecture.md) - Architecture details (coming soon)
- [User Guide](docs/user-guide.md) - How to use the pipeline (coming soon)
- [Developer Guide](docs/developer-guide.md) - How to extend and modify (coming soon)

## Project Status

🚧 **Under Active Development** - Extraction and organization in progress

See [docs/REFACTORING-PLAN-V2.md](docs/REFACTORING-PLAN-V2.md) for full refactoring plan.
