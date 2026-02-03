# ATOMIC CLAUDE - Python Implementation

## Overview

This is the Python rewrite of ATOMIC CLAUDE's main orchestrator (`main.sh` → `main.py`). The implementation maintains **100% compatibility** with the bash version while providing improved maintainability, error handling, and extensibility.

## Architecture

### Core Design Principles

1. **Drop-in replacement**: Same CLI interface, same file structure, same state files
2. **Gradual migration**: Python and bash versions coexist during transition
3. **Type safety**: Type hints throughout for self-documenting code
4. **Error handling**: Try/except with proper exit codes instead of bash's `set -e`
5. **Testability**: Structured for pytest unit/integration tests

### File Structure

```
atomic-claude-python/
├── main.py              # CLI orchestrator (replaces main.sh)
├── lib/
│   ├── __init__.py
│   ├── atomic.py        # Core LLM invocation (replaces atomic.sh)
│   ├── phase.py         # Phase lifecycle (replaces phase.sh)
│   ├── provider.py      # Multi-provider routing (replaces provider.sh)
│   ├── memory.py        # Persistent memory (replaces memory.sh)
│   └── task_state.py    # Task state machine (replaces task-state.sh)
├── phases/
│   ├── __init__.py
│   ├── phase_0/         # Setup phase (Python)
│   ├── phase_1/         # Discovery phase (Python)
│   └── ...
├── tests/
│   ├── test_main.py
│   ├── test_lib/
│   └── test_phases/
└── requirements.txt     # Python dependencies
```

## main.py Design

### Command Structure

The CLI uses `argparse` with subcommands matching the bash version:

```python
main.py <command> [options]

Commands:
  run <phase>       Run a specific phase (e.g., run 0)
  status            Show current pipeline status
  list              List available phases
  providers         Check provider availability
  reset             Reset pipeline state
```

### Key Functions

#### `cmd_run(phase_input: str, extra_args: List[str]) -> int`

Executes a phase with the following workflow:

1. **Initialize memory layer** - Loads context from previous sessions
2. **Find phase directory** - Supports both "0" and "0-setup" formats
3. **Check prerequisites** - Ensures previous phase completed
4. **Execute phase script** - Shells out to bash `run.sh` (for now)
5. **Return exit code** - 0 for success, non-zero for errors

**Future improvement**: Replace bash execution with Python phase runners when `phases/phase_N/run.py` is available.

```python
# Current (transitional)
subprocess.run(["bash", str(phase_script)] + extra_args)

# Future (pure Python)
from phases.phase_0 import run_phase
run_phase(extra_args)
```

#### `cmd_status() -> int`

Shows pipeline status by:

1. Loading session data from `.state/session.json`
2. Displaying session metadata (ID, start time, current phase)
3. Listing all phases with completion status (checks for `closeout.json`)

#### `cmd_list() -> int`

Lists all phases by:

1. Scanning `phases/` directory for subdirectories with `run.sh`
2. Checking completion status (presence of `closeout.json` in `.outputs/`)
3. Formatting output with color-coded status

#### `cmd_providers() -> int`

Checks provider availability by:

1. Testing for AWS credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. Testing for Anthropic API key (`ANTHROPIC_API_KEY`)
3. Testing for Ollama installation (`which ollama`)
4. Displaying status with color-coded indicators

**Future improvement**: Import from `lib/provider.py` instead of inline checks.

#### `cmd_reset() -> int`

Resets pipeline state with:

1. User confirmation prompt (must type "reset")
2. Removal of `.state/`, `.outputs/`, `.logs/` directories
3. Success/cancellation message

### State Management

The Python implementation uses the **same state files** as bash:

| File | Purpose | Format |
|------|---------|--------|
| `.state/session.json` | Current session metadata | JSON |
| `.outputs/<phase>/closeout.json` | Phase completion record | JSON |
| `.claude/task-state.json` | Task completion tracking | JSON |
| `.state/memory/` | Persistent context | Files |

This ensures **zero migration cost** - you can switch between bash and Python versions seamlessly.

### Color Output

Terminal colors are defined in the `Colors` class:

```python
class Colors:
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    NC = "\033[0m"  # No Color
```

Helper functions provide consistent formatting:

- `atomic_header(text)` - Centered header with border
- `atomic_info(text)` - Info message with ℹ icon
- `atomic_success(text)` - Success message with ✓ icon
- `atomic_error(text)` - Error message with ✗ icon (stderr)
- `atomic_warn(text)` - Warning message with ⚠ icon

### Error Handling

Exit codes match bash conventions:

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 130 | Interrupted (Ctrl+C) |

Python exceptions are caught at the top level:

```python
try:
    return cmd_run(args.phase, extra_args)
except KeyboardInterrupt:
    atomic_warn("Interrupted by user")
    return 130
except Exception as e:
    atomic_error(f"Unexpected error: {e}")
    traceback.print_exc()
    return 1
```

## Usage Examples

### Run a phase

```bash
./main.py run 0                  # Run Phase 0 (Setup)
./main.py run 1                  # Run Phase 1 (Discovery)
./main.py run 0-setup            # Same as run 0
```

### Resume from a task

```bash
./main.py run 1 --resume-at=107  # Resume Phase 1 from Task 107
./main.py run 0 --task=005       # Resume Phase 0 from Task 005
```

### Redo tasks

```bash
./main.py run 1 --redo           # Force redo all tasks in Phase 1
./main.py run 1 --reset-from=107 # Reset from task 107 onward
```

### Check status

```bash
./main.py status                 # Show session and phase status
./main.py list                   # List all phases
./main.py providers              # Check provider availability
```

### Reset state

```bash
./main.py reset                  # Reset all pipeline state
```

## Implementation Status

### Completed

- ✅ CLI argument parsing with `argparse`
- ✅ All 5 commands (run, status, list, providers, reset)
- ✅ Phase discovery and validation
- ✅ Prerequisite checking (previous phase completed)
- ✅ Color-coded terminal output
- ✅ Pass-through of extra args to phase scripts
- ✅ Error handling with proper exit codes
- ✅ Session data loading and display
- ✅ Provider availability checking
- ✅ State reset with confirmation

### In Progress

- 🚧 `lib/atomic.py` - Core LLM invocation (being converted in parallel)
- 🚧 `lib/phase.py` - Phase lifecycle management (being converted in parallel)
- 🚧 `lib/provider.py` - Multi-provider routing (being converted in parallel)
- 🚧 `lib/memory.py` - Persistent memory layer (being converted in parallel)
- 🚧 `lib/task_state.py` - Task state machine (being converted in parallel)

### TODO

- ⏳ `phases/phase_0/run.py` - Python version of Phase 0
- ⏳ `phases/phase_1/run.py` - Python version of Phase 1
- ⏳ `tests/` - Pytest test suite
- ⏳ `requirements.txt` - Python dependencies

## Testing

### Manual Testing

Test all commands:

```bash
cd atomic-claude-python

# Test help
./main.py --help

# Test list
./main.py list

# Test status
./main.py status

# Test providers
./main.py providers

# Test run (dry run - will execute bash phase script)
./main.py run 0 --help
```

### Automated Testing (Future)

```bash
pytest tests/                    # Run all tests
pytest tests/test_main.py        # Test main.py
pytest tests/test_lib/           # Test lib/ modules
pytest --cov=. --cov-report=html # Generate coverage report
```

## Migration Path

### Phase 1: Core Libraries (Current)

Convert `lib/*.sh` to `lib/*.py` in parallel:

- `atomic.sh` → `atomic.py` (LLM invocation)
- `phase.sh` → `phase.py` (Phase lifecycle)
- `provider.sh` → `provider.py` (Provider routing)
- `memory.sh` → `memory.py` (Memory layer)
- `task-state.sh` → `task_state.py` (Task state)

### Phase 2: Phase Runners

Convert phase scripts from bash to Python:

1. Create `phases/phase_0/run.py` (proof of concept)
2. Test Phase 0 end-to-end in Python
3. Roll through remaining phases (1-9)

### Phase 3: Integration

Update `main.py` to import Python phase runners:

```python
# Instead of:
subprocess.run(["bash", str(phase_script)])

# Use:
from phases.phase_0 import run_phase
run_phase(extra_args)
```

### Phase 4: Cutover

1. Run full pipeline with Python implementation
2. Compare outputs with bash version
3. Document differences (if any)
4. Switch default in repo from `main.sh` to `main.py`
5. Keep bash version as `main-legacy.sh` for fallback

## Design Decisions

### Why subprocess for phase execution?

**Short-term**: During transition, `main.py` shells out to bash phase scripts (`run.sh`) to avoid a big-bang rewrite.

**Long-term**: Once phase runners are converted to Python, `main.py` will import them as modules.

### Why keep the same state files?

**Compatibility**: Allows seamless switching between bash and Python versions during transition.

**Zero migration**: Users don't need to convert state when moving to Python.

**Debugging**: Can use bash tools to inspect Python-generated state and vice versa.

### Why argparse instead of click/typer?

**Minimal dependencies**: argparse is in the standard library.

**Sufficient features**: argparse handles our use case (subcommands, pass-through args).

**Future upgrade**: Easy to swap for click/typer if needed.

## Contributing

### Code Style

- **Type hints**: All function signatures must have type hints
- **Docstrings**: Google-style docstrings for all public functions
- **Line length**: 100 characters (following PEP 8 flexibility)
- **Naming**: Snake_case for functions/variables, PascalCase for classes

### Adding a New Command

1. Add subparser in `main()`
2. Create `cmd_<name>()` function
3. Add dispatch case in `main()`
4. Update help text and IMPLEMENTATION.md

Example:

```python
# In main()
subparsers.add_parser("validate", help="Validate pipeline state")

# New function
def cmd_validate() -> int:
    """Validate pipeline state integrity"""
    atomic_header("Pipeline Validation")
    # ... implementation ...
    return 0

# In dispatch
elif args.command == "validate":
    return cmd_validate()
```

## Future Enhancements

### 1. Rich Terminal UI

Replace ANSI colors with `rich` library:

```python
from rich.console import Console
from rich.table import Table

console = Console()
table = Table(title="Available Phases")
table.add_column("Phase ID", style="cyan")
table.add_column("Status", style="green")
# ...
console.print(table)
```

### 2. Interactive Mode

Add interactive phase selection:

```python
from InquirerPy import inquirer

phase = inquirer.select(
    message="Select phase to run:",
    choices=[(f"{id} - {status}", id) for id, status in phases]
).execute()
```

### 3. Progress Bars

Show task progress within phases:

```python
from tqdm import tqdm

for task in tqdm(tasks, desc="Running Phase 1"):
    run_task(task)
```

### 4. Async Execution

Run independent tasks in parallel:

```python
import asyncio

async def run_tasks_async(tasks):
    await asyncio.gather(*[run_task(t) for t in tasks])
```

### 5. Configuration File

Support `atomic.toml` for settings:

```toml
[pipeline]
default_phase = "0-setup"
auto_advance = true

[llm]
primary_model = "sonnet"
fast_model = "haiku"
```

## Troubleshooting

### main.py not executable

```bash
chmod +x atomic-claude-python/main.py
```

### Python version error

Requires Python 3.9+:

```bash
python3 --version  # Should be >= 3.9
```

### Import errors

Ensure you're running from the correct directory:

```bash
cd atomic-claude-python
./main.py run 0
```

### State file not found

If `.state/session.json` is missing, start from Phase 0:

```bash
./main.py run 0
```

## References

- **Original bash implementation**: `/main.sh`
- **Phase management**: `/lib/phase.sh`
- **Task state**: `/lib/task-state.sh`
- **Memory system**: `/lib/memory.sh`
- **Provider routing**: `/lib/provider.sh`
