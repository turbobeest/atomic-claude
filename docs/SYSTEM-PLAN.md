# ATOMIC-CLAUDE System Plan

> **Version:** 1.0.0
> **Updated:** 2025-01-22
> **Repository:** github.com/turbobeest/atomic-claude

---

## Overview

ATOMIC-CLAUDE is a script-controlled LLM development pipeline that orchestrates software projects through 10 structured phases. Each phase contains bounded tasks with human gates, persistent state, and audit trails.

---

## Architecture

```
atomic-claude/
├── main.sh                 # Entry point - run, list, status, reset
├── lib/                    # Core libraries
│   ├── atomic.sh           # Invocation, state, context management
│   ├── phase.sh            # Phase lifecycle, task orchestration
│   ├── task-state.sh       # Persistence, resume, navigation
│   ├── audit.sh            # Audit integration
│   ├── provider.sh         # LLM provider abstraction
│   └── intro.sh            # UI animations
├── phases/                 # 10 phases (0-9)
│   └── X-name/
│       ├── run.sh          # Phase entry point
│       └── tasks/*.sh      # Individual task implementations
├── tests/                  # BATS test harness
│   ├── unit/               # Unit tests for lib files
│   ├── integration/        # State persistence tests
│   ├── fixtures/           # Mock responses, snapshots
│   └── run-tests.sh        # Test runner
├── .github/workflows/      # CI configuration
├── .claude/                # Runtime artifacts (gitignored)
├── .state/                 # Session state
├── .outputs/               # Phase outputs
└── .logs/                  # Invocation logs
```

---

## Phase Structure

| Phase | Name | Tasks | Purpose |
|-------|------|-------|---------|
| **0** | Setup | 001-008 | Project initialization, API keys, environment |
| **1** | Discovery | 101-110 | Corpus analysis, stakeholder dialogue, approach selection |
| **2** | PRD | 201-209 | Product requirements document authoring |
| **3** | Tasking | 301-306 | Task decomposition, dependency analysis |
| **4** | Specification | 401-406 | OpenSpec generation, TDD subtask injection |
| **5** | Implementation | 501-507 | TDD cycles (RED/GREEN/REFACTOR/VERIFY) |
| **6** | Code Review | 601-606 | Comprehensive review, refinement |
| **7** | Integration | 701-707 | E2E testing, acceptance validation |
| **8** | Deployment Prep | 801-806 | Release artifacts, documentation |
| **9** | Release | 901-906 | Production deployment, distribution |

**Total: 71 tasks across 10 phases**

---

## Task Execution Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     TASK LIFECYCLE                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Check Skip (task_state_should_skip)                     │
│     └── Already complete? → SKIP                            │
│     └── Resume target? → Wait until reached                 │
│     └── Force redo? → Continue                              │
│                                                             │
│  2. Display Task Header                                     │
│     └── Task ID, Name, Status banner                        │
│                                                             │
│  3. Mark In Progress (task_state_start)                     │
│     └── Update .claude/task-state.json                      │
│                                                             │
│  4. Execute Task Function                                   │
│     └── Deterministic or LLM-backed                         │
│     └── Context injection from previous outputs             │
│                                                             │
│  5. Mark Complete (task_state_complete)                     │
│     └── Record artifacts                                    │
│     └── Update completion timestamp                         │
│                                                             │
│  6. Post-Task Navigation                                    │
│     └── [c] Continue  [r] Redo  [b] Back  [j] Jump  [q] Quit│
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## State Management

### Session State (`.state/session.json`)
```json
{
  "session_id": "20250122-120000-12345",
  "started_at": "2025-01-22T12:00:00Z",
  "tasks_completed": 15,
  "tasks_failed": 0,
  "current_phase": "1-discovery",
  "current_task": "104"
}
```

### Task State (`.claude/task-state.json`)
```json
{
  "version": "1.0",
  "current_phase": "1-discovery",
  "phases": {
    "0-setup": {
      "completed": true,
      "tasks": {
        "001": { "status": "complete", "artifacts": [...] }
      }
    }
  }
}
```

---

## Human Gates

Each phase includes human approval gates:

| Phase | Gate Task | Purpose |
|-------|-----------|---------|
| 2 | 207 | PRD approval before tasking |
| 5 | 505 | Implementation validation |
| 7 | 705 | Integration approval |
| 8 | 805 | Deployment approval |
| 9 | 905 | Release confirmation |

---

## CLI Reference

```bash
# Main commands
./main.sh run <phase>     # Run a phase (e.g., run 0, run 1-discovery)
./main.sh list            # List all phases with status
./main.sh status          # Show current session status
./main.sh reset           # Reset all state (requires confirmation)

# Phase-level commands (from phases/X-name/run.sh)
./run.sh                  # Normal run (resumes from last complete)
./run.sh --resume-at 103  # Start from specific task
./run.sh --reset-from 105 # Reset from task 105 onward
./run.sh --redo           # Force re-run all tasks
./run.sh --clear          # Clear all task state
./run.sh --status         # Show task completion status

# Cross-phase commands
./run.sh --pipeline-status      # Full pipeline status
./run.sh --pipeline-reset=204   # Reset from task 204 across phases

# Testing
./tests/run-tests.sh            # Run all tests
./tests/run-tests.sh --unit     # Unit tests only
./tests/run-tests.sh --verbose  # Verbose output
```

---

## Context Management

Each phase maintains context for LLM tasks:

```
.outputs/<phase>/context/
├── summary.md          # Rolling context summary (auto-refreshed)
├── decisions.json      # Decision log
└── artifacts.json      # Artifact index
```

### Context Flow
1. **atomic_context_init** - Initialize context directory
2. **atomic_build_context** - Assemble from files
3. **atomic_context_decision** - Record decisions
4. **atomic_context_artifact** - Index outputs
5. **atomic_context_refresh** - LLM-driven summary update

---

## LLM Invocation

```bash
# Basic invocation
atomic_invoke "prompt.md" "output.json" "Task description"

# With options
atomic_invoke "prompt" "output" "desc" \
  --model=opus \
  --format=json \
  --timeout=600

# Contextual invocation (includes preflight check)
atomic_invoke_contextual "prompt" "output" "desc"
```

### Models
- **haiku** - Fast/cheap (preflight checks, summaries)
- **sonnet** - Default (most tasks)
- **opus** - Complex reasoning (architecture, design)

---

## Testing

### Test Structure
```
tests/
├── setup/
│   ├── helpers.bash    # Assertions, fixtures, setup/teardown
│   └── mocks.bash      # Claude mock, spies, date mock
├── unit/
│   ├── lib_atomic.bats     # 25+ tests
│   ├── lib_phase.bats      # 20+ tests
│   └── lib_taskstate.bats  # 25+ tests
├── integration/
│   └── state-persistence.bats
└── fixtures/
    ├── claude-responses/   # Mock LLM outputs
    └── state-snapshots/    # Pre-built state files
```

### Running Tests
```bash
# Install BATS (if needed)
sudo apt install bats

# Run all tests
./tests/run-tests.sh

# Run with options
./tests/run-tests.sh --unit         # Unit only
./tests/run-tests.sh --integration  # Integration only
./tests/run-tests.sh --verbose      # Verbose output
./tests/run-tests.sh 'state'        # Filter by pattern
```

---

## First Run Checklist

1. **Environment**
   ```bash
   cd /mnt/walnut-drive/dev/ATOMIC-CLAUDE
   ```

2. **Verify Installation**
   ```bash
   ./main.sh list
   ./tests/run-tests.sh --unit
   ```

3. **Start Pipeline**
   ```bash
   ./main.sh run 0
   ```

4. **Monitor Progress**
   ```bash
   ./main.sh status
   ```

---

## Configuration

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `ATOMIC_ROOT` | Script directory | Project root |
| `ATOMIC_STATE_DIR` | `.state` | Session state |
| `ATOMIC_OUTPUT_DIR` | `.outputs` | Phase outputs |
| `ATOMIC_LOG_DIR` | `.logs` | Invocation logs |
| `CLAUDE_MODEL` | `sonnet` | Default LLM model |
| `CLAUDE_TIMEOUT` | `300` | Invocation timeout (seconds) |

### Project Config (`.outputs/0-setup/project-config.json`)
```json
{
  "project": {
    "name": "my-project",
    "type": "cli-tool",
    "description": "..."
  },
  "settings": {
    "mode": "guided",
    "audit_enabled": true
  }
}
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "Previous phase not completed" | Run `./main.sh run <prev-phase>` first |
| Task stuck in_progress | Run `./run.sh --reset-from <task>` |
| LLM timeout | Increase `CLAUDE_TIMEOUT` or use `--timeout=N` |
| State corruption | Run `./main.sh reset` (loses all progress) |

### Debug Commands
```bash
# View task state
cat .claude/task-state.json | jq .

# View session state
cat .state/session.json | jq .

# View logs
tail -f .logs/*.log

# Test specific file
bats tests/unit/lib_atomic.bats
```

---

## Extending ATOMIC-CLAUDE

### Adding a New Task

1. Create task file: `phases/X-name/tasks/X0Y-task-name.sh`
2. Define function: `task_X0Y_task_name()`
3. Add to `run.sh`: `phase_task_interactive "X0Y" "Task Name" task_X0Y_task_name`

### Adding a New Phase

1. Create directory: `phases/N-name/`
2. Create `run.sh` following existing pattern
3. Create task files in `tasks/`
4. Update previous phase to chain: `phase_chain "N-1" "phases/N-name/run.sh" "Name"`

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-01-22 | Initial release with all 10 phases, test harness, CI |

---

## License

MIT - See LICENSE file

---

*Generated for ATOMIC-CLAUDE system readiness*
