# Claude Context: atomic-claude2 Refactor

**Quick Start Document for Any Claude Session**

---

## What Is This?

**atomic-claude2** is a complete Python refactor of **atomic-claude** (a Bash-based LLM orchestration system for software development pipelines).

**Goal:** Exact behavioral parity with improved performance, modularity, and maintainability.

**Reference:** `/Users/jamesterbeest/dev/atomic-claude` (READ-ONLY - do not modify)

**Working Directory:** `/Users/jamesterbeest/dev/atomic-claude2` (active development)

---

## Quick Facts

- **Timeline:** 10-15 working days (10 hours/day, max parallelism)
- **Lines of Code:** ~35,000 lines Python (from ~45,000 lines Bash)
- **Tests:** 1,310+ tests, 95%+ coverage target
- **Strategy:** Clean rewrite using atomic-claude as reference
- **Architecture:** Modular, provider-agnostic, heavily tested

---

## What atomic-claude Does

A **10-phase SDLC pipeline** orchestrated by Bash scripts that invoke LLMs for non-deterministic tasks:

1. **Phase 0:** Setup - Project configuration
2. **Phase 1:** Discovery - Requirements gathering, agent selection
3. **Phase 2:** PRD - 15-section Product Requirements Document
4. **Phase 3:** Tasking - Task decomposition
5. **Phase 4:** Specification - OpenSpec generation
6. **Phase 5:** Implementation - TDD cycles, code generation
7. **Phase 6:** Code Review - Review and refinement
8. **Phase 7:** Integration - Integration testing
9. **Phase 8:** Deployment Prep - Release preparation
10. **Phase 9:** Release - Deployment

**Key Features:**
- Multi-provider LLM routing (Anthropic, AWS Bedrock, Ollama)
- Persistent memory across sessions
- Task state tracking with resume capability
- Real-time web dashboard
- 221 Grade-A agents (Git submodule)
- 2,186 audits across 43 categories (Git submodule)
- Role-based provider routing (primary, fast, gardener, heavyweight)

---

## Current State

### What Exists in atomic-claude2
Check the directory to see what's already implemented. May include:
- Early Python code from previous experiments
- Some core modules partially complete
- Test infrastructure

### What Needs to Be Built
See `REFACTOR-PLAN.md` for complete implementation plan.

**Core priorities:**
1. Core systems (config, state, LLM, memory, task)
2. Orchestration (pipeline, scheduler, chaining)
3. Phase implementations (0-9)
4. Integration (agents, audits, skills, dashboard)
5. Testing (unit, integration, E2E, regression)
6. Documentation

---

## Architecture (Target)

```
atomic-claude2/
├── core/                     # Core systems
│   ├── config.py            # Configuration
│   ├── state.py             # State management
│   ├── llm/                 # LLM abstraction (providers, router, cache)
│   ├── memory/              # Memory system
│   ├── task/                # Task engine
│   └── utils/               # Utilities
├── orchestration/           # High-level coordination
│   ├── pipeline.py         # Phase pipeline
│   ├── phase_runner.py     # Phase execution
│   ├── task_scheduler.py   # Task scheduling
│   ├── backtrack.py        # Backtrack detection
│   └── chaining.py         # Phase chaining
├── phases/                  # Phase implementations (0-9)
│   ├── base.py
│   ├── phase_00_setup/
│   │   ├── phase.py
│   │   └── tasks/          # Tasks 001-010
│   └── ... (phases 1-9)
├── agents/                  # Agent integration
├── audits/                  # Audit integration
├── dashboard/               # Real-time dashboard
├── tests/                   # Test suite
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   ├── regression/
│   └── performance/
├── scripts/                 # Utilities
├── main.py                  # CLI entry
└── [docs, configs, etc.]
```

---

## How to Work on This

### 1. Understand the Current Phase
Check `REFACTOR-PLAN.md` to see what phase you're in.

### 2. Reference atomic-claude
All bash code is at `/Users/jamesterbeest/dev/atomic-claude/`

**Key reference files:**
- `lib/atomic.sh` - Core LLM invocation (~4,300 lines)
- `lib/provider.sh` - Provider routing (~2,000 lines)
- `lib/memory.sh` - Memory system (~1,500 lines)
- `lib/phase.sh` - Phase lifecycle (~1,200 lines)
- `lib/task-state.sh` - Task state machine (~1,000 lines)
- `phases/N-name/run.sh` - Phase runner
- `phases/N-name/tasks/*.sh` - Task scripts
- `CLAUDE.md` - Complete system documentation

### 3. Follow Design Principles
- **Modularity:** Single responsibility per module
- **Provider abstraction:** Pluggable LLM providers
- **Testability:** Mock external dependencies
- **Immutability:** Atomic state transitions
- **Observability:** Full logging and instrumentation
- **Error recovery:** Rollback capability

### 4. Test as You Go
- Write unit tests immediately
- Run tests frequently
- Add integration tests for workflows
- Regression test against atomic-claude outputs

### 5. Document
- Docstrings for all functions/classes
- Type hints throughout
- Inline comments for complex logic
- Update user/dev docs as needed

---

## Common Tasks

### Starting a New Module
1. Check bash reference implementation
2. Design Python class/function structure
3. Implement with type hints and docstrings
4. Write unit tests (aim for 95%+ coverage)
5. Add integration tests if multi-module
6. Validate against bash behavior

### Converting a Phase
1. Study `phases/N-name/run.sh` and all task scripts
2. Map bash logic to Python modules
3. Create `phases/phase_NN_name/phase.py` coordinator
4. Create task modules in `phases/phase_NN_name/tasks/`
5. Write tests: unit (6 per task), integration, regression, E2E
6. Validate outputs match bash version exactly

### Running Regression Tests
```bash
# Run both systems with identical input
cd /Users/jamesterbeest/dev/atomic-claude
./main.sh run 0 --mode=document  # Bash version

cd /Users/jamesterbeest/dev/atomic-claude2
python main.py run 0 --mode=document  # Python version

# Compare outputs
diff -r atomic-claude/.outputs/0-setup atomic-claude2/.outputs/0-setup
diff atomic-claude/.state/session.json atomic-claude2/.state/session.json
```

### Using Parallel Agents
When converting phases or building modules in parallel:
```
# In your response, use multiple Task tool calls in a single message
Task: Agent 1 - Implement core/config.py + tests
Task: Agent 2 - Implement core/state.py + tests
Task: Agent 3 - Implement core/llm/base.py + tests
Task: Agent 4 - Implement core/llm/router.py + tests
```

---

## Critical Constraints

### DO NOT Modify atomic-claude
- `/Users/jamesterbeest/dev/atomic-claude` is READ-ONLY
- Use only as reference
- Do not run destructive operations there
- Copy logic, don't move files

### Exact Behavioral Parity Required
- Outputs must match bash version exactly
- State files must be compatible
- Configuration files must be compatible
- CLI interface must match (or improve)

### Testing is Mandatory
- Every function needs tests
- 95%+ coverage target
- Regression validation against bash
- CI/CD must pass

### Performance Matters
- Must be within 10% of bash performance
- Profile hot paths
- Optimize where needed
- Benchmark against bash

---

## Useful Commands

```bash
# Run tests
pytest tests/ -v
pytest tests/unit/test_config.py -v
pytest tests/ --cov=core --cov-report=html

# Run specific test
pytest tests/unit/test_llm.py::test_anthropic_invoke -v

# Format code
black core/ orchestration/ phases/

# Lint code
pylint core/ orchestration/ phases/

# Type check
mypy core/ orchestration/ phases/

# Run performance benchmark
python scripts/benchmark.py

# Validate against atomic-claude
python scripts/validate.py --regression
```

---

## Key Files to Reference

### atomic-claude Bash Implementation
- `/Users/jamesterbeest/dev/atomic-claude/lib/atomic.sh` - Core
- `/Users/jamesterbeest/dev/atomic-claude/lib/provider.sh` - Providers
- `/Users/jamesterbeest/dev/atomic-claude/lib/memory.sh` - Memory
- `/Users/jamesterbeest/dev/atomic-claude/lib/phase.sh` - Phases
- `/Users/jamesterbeest/dev/atomic-claude/lib/task-state.sh` - Tasks
- `/Users/jamesterbeest/dev/atomic-claude/CLAUDE.md` - Documentation
- `/Users/jamesterbeest/dev/atomic-claude/phases/*/` - Phase implementations

### atomic-claude2 Documentation
- `REFACTOR-PLAN.md` - Complete implementation plan (this is essential)
- `CLAUDE-CONTEXT.md` - This file (quick reference)
- `README.md` - User-facing documentation
- `docs/` - Additional documentation

---

## Development Status

Check these to understand current progress:
1. `REFACTOR-PLAN.md` - See which phase you should work on
2. Git log - Recent commits and progress
3. Test results - `pytest tests/ -v`
4. Coverage - `pytest --cov=. --cov-report=term`

---

## When You Start a Session

1. **Read `REFACTOR-PLAN.md`** - Understand the current phase
2. **Check git status** - See what's been done
3. **Run tests** - Validate current state
4. **Ask user** - "Where should I start?" or "Continue from Phase X?"
5. **Use parallel agents** - Maximize throughput with Task tool

---

## Testing Strategy

### Test Pyramid (1,310 total tests)
- **800 Unit tests** - Every function, < 30s
- **250 Integration tests** - Multi-module, < 2min
- **80 E2E tests** - Full phases, < 15min
- **100 Regression tests** - vs atomic-claude, < 20min
- **50 Performance tests** - Benchmarks, < 5min
- **30 Stress tests** - Edge cases, < 10min

### Coverage Goals
- Line coverage: 95%+
- Branch coverage: 90%+
- Function coverage: 100%
- Mutation coverage: 90%+

### Regression Testing
- Run identical inputs through both systems
- Compare all outputs (JSON, markdown, state files)
- Allow formatting differences, not content differences
- Validate on every phase completion

---

## Timeline (Estimated)

**Day 1-2:** Core systems (config, state, LLM, memory, task)
**Day 3:** Orchestration (pipeline, scheduler, chaining)
**Day 4:** Phase 0
**Day 5:** Phase 1
**Day 6:** Phase 2
**Day 7-8:** Phases 3-6
**Day 9:** Phases 7-9 + Integration
**Day 10-12:** Testing, validation, performance
**Day 13-15:** Documentation, polish, release

**Total: 10-15 working days**

---

## Success Criteria

- ✅ All 10 phases produce identical outputs
- ✅ 1,310+ tests passing
- ✅ 95%+ code coverage
- ✅ Within 10% of bash performance
- ✅ Complete documentation
- ✅ Migration tooling works
- ✅ CI/CD pipeline running

---

## Questions to Ask User

When starting a session:
1. "What phase are we on?" (Check `REFACTOR-PLAN.md`)
2. "Should I continue from where we left off?"
3. "Any specific module or phase to prioritize?"
4. "Should I use parallel agents for this work?"

---

## Remember

- **Reference atomic-claude** for all behavior
- **Test continuously** - don't wait until the end
- **Use parallel agents** - maximize throughput
- **Regression validate** - catch divergence early
- **Document as you go** - docstrings immediately
- **Performance matters** - profile hot paths
- **Exact parity required** - outputs must match

---

**You have everything you need to build atomic-claude2. Start with Phase 1 (Foundation) unless the user directs otherwise.**

**Read `REFACTOR-PLAN.md` for complete details.**
