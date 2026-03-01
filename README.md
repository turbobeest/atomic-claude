# Atomic Claude

An AI-powered SDLC pipeline that takes a software project from idea to deployment-ready code. Ten phases — setup, discovery, PRD, tasking, specification, implementation, code review, integration, deployment prep, and release — each orchestrated by specialized agents with full state management, rollback, and memory.

## Install

```bash
# Runtime install (~23MB, pipeline essentials only)
curl -fsSL https://raw.githubusercontent.com/turbobeest/atomic-claude/python/install.sh | bash

# Full install (includes tests, docs, dev tooling)
curl -fsSL .../install.sh | bash -s -- --full
```

## Quick Start

```bash
cd atomic-claude
python main.py run 0        # Start with Phase 0 (Setup)
python main.py status       # Check progress
python main.py run 1        # Continue to Phase 1
```

## How It Works

You point it at a project idea. It walks you through requirements gathering, generates a PRD, breaks it into tasks, writes specifications, implements code, reviews it, integrates components, and prepares deployment artifacts. Each phase produces outputs that feed the next.

**LLM providers** fall back automatically: Claude Code CLI → Anthropic API → AWS Bedrock → Ollama (local).

**221 agents** across 19 categories handle specialized work — backend, frontend, security, DevOps, data, and more.

**State is atomic.** Every task checkpoints. Backtrack to any point with `python main.py backtrack <phase> [task]`.

## Configuration

Copy `.env.example` to `.env` and set your provider credentials. See the [User Guide](dev/docs/USER-GUIDE.md) for details.

## Documentation

- [User Guide](dev/docs/USER-GUIDE.md) — Using the pipeline
- [Developer Guide](dev/docs/DEVELOPER-GUIDE.md) — Extending and contributing
- [API Reference](dev/docs/API-REFERENCE.md) — Core interfaces
- [CLAUDE.md](CLAUDE.md) — Project conventions and structure

## License

MIT
