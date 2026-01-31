# ATOMIC CLAUDE

Script-controlled LLM invocations for deterministic software development pipelines.

## Session Context

If persistent memory is enabled, check `.outputs/session-context.md` for recalled project context from previous sessions.

## Key Directories

- `lib/` - Core library functions (atomic.sh, phase.sh, provider.sh, memory.sh)
- `phases/` - Pipeline phases 0-9 with task scripts
- `config/` - Provider and model configuration
- `.claude/` - Runtime state (closeouts, checkpoints, artifacts)
- `.outputs/` - Phase outputs and session context

## Pipeline Flow

```
Phase 0: Setup       - Configuration, API keys, environment
Phase 1: Discovery   - Requirements gathering, agent selection
Phase 2: PRD         - Product requirements document
Phase 3: Tasking     - Task decomposition
Phase 4: Specification - OpenSpec generation
Phase 5: Implementation - TDD cycles
Phase 6: Code Review - Review and refinement
Phase 7: Integration - Integration testing
Phase 8: Deployment Prep - Release preparation
Phase 9: Release     - Deployment
```

## Running

```bash
./main.sh run <phase>   # Run a phase
./main.sh status        # Check pipeline status
./main.sh list          # List all phases
```

## LLM Invocation

All LLM calls go through `atomic_invoke()` with bounded prompts:

```bash
atomic_invoke <prompt_file> <output_file> <description> [--model=opus|sonnet|haiku]
```
