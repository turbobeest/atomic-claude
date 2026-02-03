# ATOMIC CLAUDE - Python Implementation

This directory contains the Python rewrite of ATOMIC CLAUDE's core orchestration system.

## Why Python?

The bash implementation has hit fundamental limitations:
- Associative array scope issues (can't export to subshells)
- Complex JSON parsing requiring `jq` dependency
- Heredoc quoting hell for multi-line strings
- Difficult error handling with exit codes
- No native data structures beyond strings and arrays

Python solves these immediately:
- Native dicts/lists with proper scoping
- Built-in JSON support
- F-strings for templating
- Try/except error handling
- Type hints for self-documenting code
- Proper testing with pytest

## Architecture

The Python implementation maintains the **same architecture** as bash:

```
main.py              # CLI entry point (replaces main.sh)
lib/
  ├── atomic.py      # Core LLM invocation (replaces lib/atomic.sh)
  ├── phase.py       # Phase orchestration (replaces lib/phase.sh)
  ├── provider.py    # Multi-provider routing (replaces lib/provider.sh)
  ├── memory.py      # Persistent memory layer (replaces lib/memory.sh)
  └── task_state.py  # Task state machine (replaces lib/task-state.sh)

phases/
  ├── phase_0/       # Setup phase
  ├── phase_1/       # Discovery
  └── ...            # Remaining phases

config/              # Shared with bash (same JSON files)
```

## Development Strategy

**Incremental conversion** to minimize risk:

1. ✓ Create parallel directory structure
2. **Phase 1**: Convert core lib/ (this is happening now via parallel agents)
3. **Phase 2**: Convert main.py orchestrator
4. **Phase 3**: Convert Phase 0 as proof-of-concept
5. **Phase 4**: Roll through remaining phases

During transition:
- Both versions coexist in the repo
- Bash version remains functional
- Python version proven in test runs before cutover

## Parallel Agent Conversion

Core lib/ files are being converted **in parallel** by specialized agents:

| Agent | Task | Output File |
|-------|------|-------------|
| python-pro | Convert lib/atomic.sh | lib/atomic.py |
| python-pro | Convert lib/phase.sh | lib/phase.py |
| python-pro | Convert lib/provider.sh | lib/provider.py |
| python-pro | Convert lib/memory.sh | lib/memory.py |
| python-pro | Convert lib/task-state.sh | lib/task_state.py |
| backend-architect | Design main.py | main.py |
| test-automator | Create pytest suite | tests/ |

## Dependencies

```bash
# Core Python 3.9+ (no special libraries needed initially)
pip install -r requirements.txt  # When created
```

## Status

🚧 **IN PROGRESS** - Parallel conversion underway
