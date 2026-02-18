# Atomic Claude Python (ACP) - Refactoring Plan

**Date:** February 4, 2026
**Target Directory:** `/Users/jamesterbeest/dev/ACP`
**Goal:** Create a clean, modular, production-ready Python implementation

---

## 🎯 Core Principles

1. **Modularity** - Each phase/task is a separate, testable module
2. **Clarity** - No monolithic 900-line files; clear single responsibilities
3. **Testability** - Every module has corresponding tests
4. **Type Safety** - Full type hints, validated with mypy
5. **Documentation** - Self-documenting code with comprehensive docstrings
6. **No Bash** - Pure Python, no subprocess calls to bash scripts

---

## 📁 Proposed Architecture

```
ACP/
├── acp/                          # Main package
│   ├── __init__.py
│   ├── cli.py                    # CLI entry point (replaces main.py)
│   │
│   ├── core/                     # Core utilities (extracted from monolithic lib/)
│   │   ├── __init__.py
│   │   ├── llm.py                # LLM invocation (bedrock, ollama, api)
│   │   ├── providers.py          # Provider detection and routing
│   │   ├── state.py              # Task state management
│   │   ├── memory.py             # Persistent memory system
│   │   ├── config.py             # Configuration loading
│   │   └── logging.py            # Structured logging
│   │
│   ├── phases/                   # Phase modules (one per phase)
│   │   ├── __init__.py
│   │   ├── base.py               # Base phase class
│   │   ├── phase_00_setup.py
│   │   ├── phase_01_discovery.py
│   │   ├── phase_02_prd.py
│   │   ├── phase_03_tasking.py
│   │   ├── phase_04_specification.py
│   │   ├── phase_05_implementation.py
│   │   ├── phase_06_code_review.py
│   │   ├── phase_07_integration.py
│   │   ├── phase_08_deployment.py
│   │   └── phase_09_release.py
│   │
│   ├── tasks/                    # Task modules (organized by phase)
│   │   ├── __init__.py
│   │   ├── phase_00/             # Setup tasks
│   │   │   ├── __init__.py
│   │   │   ├── task_001_mode_selection.py
│   │   │   ├── task_002_config_collection.py
│   │   │   └── ...
│   │   ├── phase_02/             # PRD tasks
│   │   │   ├── __init__.py
│   │   │   ├── task_201_entry.py
│   │   │   ├── task_205_prd_authoring.py
│   │   │   └── ...
│   │   └── ...                   # Other phases
│   │
│   ├── agents/                   # Agent management
│   │   ├── __init__.py
│   │   ├── loader.py             # Load agents from CSV/manifest
│   │   ├── selector.py           # Agent selection logic
│   │   └── registry.py           # Agent registry
│   │
│   ├── audits/                   # Audit system
│   │   ├── __init__.py
│   │   ├── loader.py             # Load audits from inventory
│   │   ├── executor.py           # Execute audits
│   │   └── reporter.py           # Generate audit reports
│   │
│   └── utils/                    # Shared utilities
│       ├── __init__.py
│       ├── files.py              # File operations
│       ├── json_utils.py         # JSON parsing/validation
│       ├── markdown.py           # Markdown processing
│       └── ui.py                 # Console UI helpers
│
├── tests/                        # Comprehensive test suite
│   ├── __init__.py
│   ├── conftest.py               # Pytest fixtures
│   ├── unit/                     # Unit tests (one per module)
│   │   ├── core/
│   │   ├── phases/
│   │   ├── tasks/
│   │   └── ...
│   ├── integration/              # Integration tests
│   │   ├── test_phase_flow.py
│   │   ├── test_end_to_end.py
│   │   └── ...
│   └── fixtures/                 # Test data/mocks
│
├── docs/                         # Documentation
│   ├── architecture.md           # Architecture overview
│   ├── api.md                    # API reference
│   ├── contributing.md           # Contribution guide
│   └── migration.md              # Migration from bash
│
├── scripts/                      # Utility scripts
│   ├── dev.sh                    # Development helpers
│   └── build.sh                  # Build/package scripts
│
├── config/                       # Configuration files
│   ├── models.yaml               # Model configurations
│   └── defaults.yaml             # Default settings
│
├── pyproject.toml                # Modern Python packaging
├── setup.cfg                     # Setup configuration
├── requirements.txt              # Runtime dependencies
├── requirements-dev.txt          # Development dependencies
├── .mypy.ini                     # Type checking config
├── .pytest.ini                   # Test configuration
└── README.md                     # Project readme
```

---

## 🔧 Key Issues to Fix

### From Current Codebase

1. **Monolithic Files**
   - Current: 900-1000 line files that do everything
   - Target: Max 300 lines per file, single responsibility

2. **Bash-Python Hybrid**
   - Current: Python CLI calling bash phase runners
   - Target: Pure Python, no subprocess calls

3. **Unbound Variables**
   - Current: `ATOMIC_AGENT_REPO` errors across 10+ files
   - Target: Proper config management with defaults

4. **Memory System Errors**
   - Current: "TASK_MEMORY_SAVE: bad array subscript"
   - Target: Clean Python dict-based memory

5. **No Task Modularity**
   - Current: All phase logic in single run.sh files
   - Target: Each task is importable, testable module

6. **Mixed Responsibilities**
   - Current: atomic.py does LLM + state + logging + UI
   - Target: Separate modules for each concern

7. **No Type Safety**
   - Current: Inconsistent typing, runtime errors
   - Target: Full mypy compliance

8. **Poor Error Handling**
   - Current: Silent failures, vague errors
   - Target: Explicit exceptions with context

9. **Dashboard Coupling**
   - Current: Dashboard reads state files directly
   - Target: API layer for state access

10. **Configuration Chaos**
    - Current: Env vars + JSON + bash variables
    - Target: Single config system (YAML/TOML)

---

## 📋 Refactoring Phases

### Phase 1: Core Infrastructure (Week 1)

**Goal:** Clean, testable core modules

#### Tasks:
1. **Setup Project Structure**
   - Create directory tree
   - Setup pyproject.toml with modern packaging
   - Configure mypy, pytest, black, isort
   - CI/CD pipeline (GitHub Actions)

2. **Core Modules**
   - `core/config.py` - Load from YAML, env vars, defaults
   - `core/llm.py` - LLM invocation (bedrock, ollama, api)
   - `core/providers.py` - Provider detection
   - `core/state.py` - Task state management
   - `core/logging.py` - Structured logging

3. **Tests**
   - Unit tests for each core module
   - 100% coverage target

4. **Documentation**
   - Architecture doc
   - API reference (auto-generated from docstrings)

### Phase 2: Phase & Task Framework (Week 2)

**Goal:** Reusable phase/task base classes

#### Tasks:
1. **Base Classes**
   - `phases/base.py` - Abstract Phase class
   - `tasks/base.py` - Abstract Task class
   - Lifecycle hooks (setup, execute, teardown, validate)

2. **Phase Registry**
   - Dynamic phase loading
   - Phase dependency graph
   - Phase state transitions

3. **Task Registry**
   - Dynamic task discovery
   - Task dependencies
   - Task validation

4. **Tests**
   - Test base classes
   - Test phase/task registration
   - Test lifecycle hooks

### Phase 3: Phase 0 Conversion (Week 3)

**Goal:** Prove the pattern with Phase 0

#### Tasks:
1. **Convert Tasks**
   - task_001_mode_selection.py
   - task_002_config_collection.py
   - task_003_config_review.py
   - task_004_api_keys.py
   - task_006_reference_materials.py
   - task_009_environment_check.py

2. **Phase 0 Module**
   - phase_00_setup.py orchestrates tasks
   - Clean error handling
   - Progress reporting

3. **Tests**
   - Unit tests for each task
   - Integration test for full phase

4. **Validation**
   - Run Phase 0 end-to-end
   - Compare output with bash version

### Phase 4: Phase 2 Conversion (Week 4)

**Goal:** Convert complex PRD generation phase

#### Tasks:
1. **Convert PRD Tasks**
   - task_205_prd_authoring.py (8-generation workflow)
   - Guardian validation module
   - Context injection module

2. **Memory Integration**
   - Clean Python memory system
   - No associative array issues

3. **Tests**
   - Unit tests for each task
   - Integration test with stub mode

### Phase 5: Remaining Phases (Weeks 5-7)

**Goal:** Complete all 10 phases

#### Tasks:
1. **Phase 1: Discovery**
2. **Phase 3: Tasking**
3. **Phase 4: Specification**
4. **Phase 5: Implementation**
5. **Phase 6: Code Review**
6. **Phase 7: Integration**
7. **Phase 8: Deployment**
8. **Phase 9: Release**

### Phase 6: Agent & Audit Systems (Week 8)

**Goal:** Clean agent and audit management

#### Tasks:
1. **Agent System**
   - CSV/manifest loader
   - Agent selection algorithms
   - Agent registry

2. **Audit System**
   - Audit inventory loader
   - Audit executor
   - Report generator

3. **Tests**
   - Mock agents for testing
   - Mock audits for testing

### Phase 7: Dashboard API (Week 9)

**Goal:** Decouple dashboard from state files

#### Tasks:
1. **State API**
   - REST API for state access
   - WebSocket for real-time updates
   - Clean separation of concerns

2. **Dashboard Update**
   - Use API instead of file reads
   - Better error handling

3. **Tests**
   - API unit tests
   - Integration tests with dashboard

### Phase 8: CLI & Documentation (Week 10)

**Goal:** Polish and production-ready

#### Tasks:
1. **Enhanced CLI**
   - Better help text
   - Progress bars
   - Interactive prompts

2. **Documentation**
   - User guide
   - Developer guide
   - Migration guide

3. **Packaging**
   - PyPI package
   - Docker image
   - Installation scripts

---

## ✅ Success Criteria

### Code Quality
- [ ] 100% type coverage (mypy --strict passes)
- [ ] 90%+ test coverage
- [ ] All tests passing
- [ ] No linting errors (black, isort, flake8)
- [ ] No security issues (bandit scan)

### Functionality
- [ ] All 10 phases working
- [ ] Fast-path mode working
- [ ] Dashboard working with API
- [ ] Memory system working
- [ ] Agent selection working
- [ ] Audit system working

### Performance
- [ ] Phase 0-9 complete in <60 minutes (full mode)
- [ ] Phase 3-9 complete in <15 minutes (fast-path mode)
- [ ] Startup time <1 second

### Documentation
- [ ] Architecture documented
- [ ] API reference complete
- [ ] User guide complete
- [ ] Migration guide complete
- [ ] All modules have docstrings

---

## 🚧 Migration Strategy

### Parallel Development
1. Keep `/Users/jamesterbeest/dev/atomic-claude` unchanged (bash version)
2. Keep `/Users/jamesterbeest/dev/atomic-claude-python` unchanged (hybrid version)
3. Build clean version in `/Users/jamesterbeest/dev/ACP`

### Testing Parity
- Run same test suite on bash, hybrid, and ACP versions
- Ensure output compatibility
- Validate state file compatibility

### Cutover Plan
1. Complete ACP implementation
2. Run parallel testing (bash vs ACP)
3. Document differences
4. User acceptance testing
5. Switch default to ACP
6. Deprecate bash version

---

## 🎯 Key Design Decisions

### 1. Task as Module Pattern
```python
# tasks/phase_02/task_205_prd_authoring.py

from acp.tasks.base import Task
from acp.core.llm import invoke_llm
from acp.core.state import save_task_state

class PRDAuthoringTask(Task):
    """Generate PRD using 8-stage workflow with guardian validation."""

    task_id = "205"
    phase_id = "2-prd"
    dependencies = ["204"]

    async def execute(self) -> bool:
        """Execute PRD authoring with 8 generations."""
        for gen_num in range(1, 9):
            content = await self._generate_section(gen_num)
            if not await self._validate_with_guardian(gen_num, content):
                return False
        return True

    async def _generate_section(self, gen_num: int) -> str:
        """Generate a single PRD section."""
        # Implementation
        pass

    async def _validate_with_guardian(self, gen_num: int, content: str) -> bool:
        """Validate section with document guardian."""
        # Implementation
        pass
```

### 2. Phase as Orchestrator Pattern
```python
# phases/phase_02_prd.py

from acp.phases.base import Phase
from acp.tasks.phase_02 import *

class PRDPhase(Phase):
    """Phase 2: Product Requirements Document generation."""

    phase_id = "2-prd"
    phase_name = "PRD"

    tasks = [
        Task201EntryValidation,
        Task202PRDSetup,
        Task203PRDInterview,
        Task204AgentSelection,
        Task205PRDAuthoring,
        Task206PRDValidation,
        Task207PRDApproval,
        Task208PhaseAudit,
        Task209Closeout,
    ]

    async def run(self) -> bool:
        """Execute all PRD tasks in order."""
        for task_class in self.tasks:
            task = task_class(phase=self)
            if not await task.run():
                return False
        return True
```

### 3. Config Management
```python
# core/config.py

from dataclasses import dataclass
from pathlib import Path
import yaml

@dataclass
class ACPConfig:
    """Atomic Claude Python configuration."""

    # Paths
    atomic_root: Path
    agent_repo: Path
    audit_repo: Path

    # Providers
    primary_provider: str
    primary_model: str

    # Features
    memory_enabled: bool
    guardian_enabled: bool
    fast_path_mode: bool

    @classmethod
    def load(cls, config_path: Path = None) -> 'ACPConfig':
        """Load config from YAML, env vars, and defaults."""
        # Priority: CLI args > env vars > config file > defaults
        pass
```

---

## 📊 Estimated Effort

| Phase | Tasks | Complexity | Estimate |
|-------|-------|------------|----------|
| 1. Core Infrastructure | 10 | Medium | 1 week |
| 2. Phase/Task Framework | 8 | High | 1 week |
| 3. Phase 0 Conversion | 6 | Medium | 1 week |
| 4. Phase 2 Conversion | 9 | High | 1 week |
| 5. Remaining Phases | 50+ | Medium | 3 weeks |
| 6. Agent/Audit Systems | 10 | Medium | 1 week |
| 7. Dashboard API | 8 | Medium | 1 week |
| 8. CLI & Docs | 10 | Low | 1 week |
| **Total** | **111+** | | **10 weeks** |

---

## 🔍 Open Questions

1. **Async vs Sync?**
   - Should we use async/await for LLM calls?
   - Pro: Better concurrency for parallel agents
   - Con: More complexity

2. **ORM for State?**
   - Should we use SQLAlchemy for state management?
   - Pro: Better queries, migrations
   - Con: Adds dependency

3. **Pydantic for Validation?**
   - Should we use Pydantic for data validation?
   - Pro: Great validation, serialization
   - Con: Adds dependency

4. **Rich for UI?**
   - Should we use Rich for console UI?
   - Pro: Beautiful, feature-rich
   - Con: Adds dependency

5. **FastAPI for Dashboard?**
   - Should dashboard be FastAPI app?
   - Pro: Modern, async, auto-docs
   - Con: More complex setup

---

## 📝 Notes

- This is a **draft plan** - open to discussion and iteration
- Estimates are rough - adjust based on complexity discovered
- Can parallelize some phases (e.g., core + phase framework)
- Consider bringing in additional developers for phases 5-8

---

**Next Steps:**
1. Review and iterate on this plan
2. Make key design decisions (async, deps, etc.)
3. Setup ACP project structure
4. Begin Phase 1: Core Infrastructure

