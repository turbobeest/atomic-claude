# Atomic Claude 2.0 - Project Structure

**Created:** February 4, 2026
**Status:** Ready for extraction and implementation

---

## Directory Tree

```
atomic-claude/
├── main.py                           # Central orchestrator & CLI entry point
├── README.md                         # Project overview and quick start
├── PROJECT-STRUCTURE.md              # This file
├── REFACTORING-PLAN-V2.md            # Detailed refactoring plan
│
├── core/                             # Core utilities (extracted from lib/)
│   ├── __init__.py
│   ├── llm.py                       # LLM invocation (from atomic.py)
│   ├── providers.py                 # Provider routing (from provider.py) - 1,022 lines AS-IS
│   ├── state.py                     # State management (from task_state.py)
│   ├── config.py                    # Configuration loading
│   ├── memory.py                    # Memory system with claude-mem
│   └── ui.py                        # Console UI utilities
│
├── phases/                           # 🎯 Phase modules (orchestrator + tasks grouped)
│   ├── __init__.py
│   ├── phase00/                     # Setup phase
│   │   ├── __init__.py
│   │   ├── orchestrator00.py        # Phase 0 orchestrator
│   │   ├── task001.sh               # Mode selection
│   │   ├── task002.sh               # Config collection
│   │   ├── task003.sh               # Config review
│   │   ├── task004.sh               # API keys
│   │   ├── task006.sh               # Reference materials
│   │   └── task009.sh               # Environment check
│   ├── phase01/                     # Discovery phase
│   │   ├── __init__.py
│   │   ├── orchestrator01.py        # Phase 1 orchestrator
│   │   └── task*.sh                # Discovery tasks
│   ├── phase02/                     # PRD phase
│   │   ├── __init__.py
│   │   ├── orchestrator02.py        # Phase 2 orchestrator
│   │   ├── task201.sh               # Entry validation
│   │   ├── task205.sh               # PRD authoring (8-generation workflow)
│   │   └── task209.sh               # Closeout
│   ├── phase03/                     # Tasking phase
│   │   ├── __init__.py
│   │   ├── orchestrator03.py        # Phase 3 orchestrator
│   │   └── task*.sh
│   ├── phase04/                     # Specification phase
│   │   ├── __init__.py
│   │   ├── orchestrator04.py        # Phase 4 orchestrator
│   │   └── task*.sh
│   ├── phase05/                     # Implementation phase
│   │   ├── __init__.py
│   │   ├── orchestrator05.py        # Phase 5 orchestrator
│   │   └── task*.sh
│   ├── phase06/                     # Code review phase
│   │   ├── __init__.py
│   │   ├── orchestrator06.py        # Phase 6 orchestrator
│   │   └── task*.sh
│   ├── phase07/                     # Integration phase
│   │   ├── __init__.py
│   │   ├── orchestrator07.py        # Phase 7 orchestrator
│   │   └── task*.sh
│   ├── phase08/                     # Deployment prep phase
│   │   ├── __init__.py
│   │   ├── orchestrator08.py        # Phase 8 orchestrator
│   │   └── task*.sh
│   └── phase09/                     # Release phase
│       ├── __init__.py
│       ├── orchestrator09.py        # Phase 9 orchestrator
│       └── task*.sh
│
├── orchestration/                   # 🆕 End-of-task processes
│   ├── __init__.py
│   ├── organization_agent.py        # Enforces file placement rules
│   ├── git_manager.py               # Commit/push prompts with contextual messages
│   ├── backtrack.py                 # Reset to any phase/task
│   └── dashboard_sync.py            # Keep dashboard accurate
│
├── dashboard/                       # Real-time web dashboard (port 5173)
│   ├── server.js                    # Express server
│   ├── public/
│   │   └── index.html               # Dashboard UI
│   └── package.json                 # Node.js dependencies
│
├── reports/                         # 🆕 Scratch work ONLY
│   ├── README.md                    # Usage rules
│   └── .gitignore                   # Ignore all except README
│
├── .outputs/                        # Working artifacts per phase
│   ├── 0-setup/
│   ├── 1-discovery/
│   ├── 2-prd/
│   └── ...
│
├── .state/                          # State tracking
│   ├── task-state.json              # Task completion state
│   ├── current-task.json            # Active task
│   └── memory/                      # claude-mem storage
│       ├── phase-0/
│       ├── phase-2/
│       └── ...
│
├── .logs/                           # Execution logs
│   └── atomic.log
│
├── config/                          # Configuration
│   ├── models.yaml                  # LLM provider/model config
│   └── defaults.yaml                # Default settings
│
└── docs/                            # Documentation
    ├── architecture.md              # Architecture overview
    ├── user-guide.md                # User guide
    └── developer-guide.md           # Developer guide
```

---

## Key Architectural Decisions

### 1. Grouped Phase Structure

**Phase orchestrators and tasks live together:**
- `phases/phase00/` contains `orchestrator.py` + all Phase 0 task scripts
- `phases/phase02/` contains `orchestrator.py` + all Phase 2 task scripts

**Why?**
- Clear boundaries - everything for a phase in one place
- Easy customization - drop new task scripts directly into phase directory
- Self-contained - each phase is a complete Python package
- Natural discovery - `ls phases/phase02/` shows orchestrator and all tasks

### 2. End-of-Task Orchestration

**Every task ends with the same flow:**

```
Task Execution
    ↓
Organization Check (BLOCKER if misplaced files)
    ↓
Fix or Abort?
    ↓
Git Actions (commit/push/skip)
    ↓
Navigation (continue/backtrack/quit)
    ↓
Sync Dashboard
    ↓
Next Task or Exit
```

This ensures:
- ✅ Clean file organization always
- ✅ Git history tracks progress
- ✅ Easy backtracking anytime
- ✅ Dashboard always accurate

### 3. Extraction, Not Rewrite

**Core principle:** The code works - just organize it.

- Extract working code from messy codebase
- Organize into clean structure
- Add orchestration for end-of-task processes
- Fix known dashboard bugs
- Keep bash task scripts initially, convert to Python gradually

**Timeline:** 9-10 days (not 10 weeks!)

---

## File Placement Rules

**Enforced by Organization Agent:**

| Type | Location | Example |
|------|----------|---------|
| LLM prompts | `.outputs/{phase}/prompts/` | `gen-3-prompt.md` |
| LLM responses | `.outputs/{phase}/outputs/` | `gen-3-sections.md` |
| Specifications | `.claude/specs/` | `phase-2-spec.json` |
| State files | `.state/` | `task-state.json` |
| Logs | `.logs/` | `atomic.log` |
| **Scratch work** | `reports/` | Analysis, diagnostics |
| Generated code | `../src/` | Project source code |
| Generated tests | `../tests/` | Project tests |
| Generated docs | `../docs/` | Project documentation |
| Tool code | `core/`, `phases/`, `orchestration/` | Tool implementation |

**⚠️ NOTHING goes in `reports/` except temporary analysis/scratch work!**

---

## Core Systems (Preserved from Original)

### 1. claude-mem
- Semantic memory system
- Context persistence across sessions
- Stored in `.state/memory/phase-N/`

### 2. Multi-Provider Support
- **max** (Claude subscription) - Primary workhorse
- **api** (Claude API) - Pay-per-token
- **bedrock** (AWS Bedrock) - Government/enterprise
- **ollama** (Local models) - Airgapped/offline

Fallback chains:
- `max → bedrock → api → ollama`
- `api → ollama`
- `bedrock → api → ollama`

### 3. Agent System
- **221 Grade-A agents** (186 expert + 35 pipeline)
- CSV manifest in `agents/` (git submodule)
- 20 categories: backend, frontend, cloud, security, etc.

### 4. Audit System
- **2,186 audits** across 43 categories
- SDLC phase filtering (discovery, prd, tasking, etc.)
- CSV inventory in `audits/` (git submodule)

### 5. Skills System
- Domain-specific knowledge modules
- Auto-loaded based on project type
- Example: `webapp-testing` for React/Vue/Angular

### 6. Hooks System
- User-configurable shell commands on events
- Preserved via environment variables

### 7. MCP (Model Context Protocol)
- Integration with MCP servers
- Preserved for future extensibility

---

## Usage

### Run Pipeline

```bash
# Run a phase
python main.py run <phase>

# Resume from specific task
python main.py run 2 --resume-at=205

# Check status
python main.py status
```

### Backtrack

```bash
# Reset to Phase 2, Task 205
python main.py backtrack 2 205

# Reset to start of Phase 2
python main.py backtrack 2
```

### Reset Everything

```bash
python main.py reset
```

---

## Development Status

### ✅ Completed
- [x] Directory structure created
- [x] Core module stubs
- [x] Orchestration module stubs
- [x] Phase orchestrators (Phase 0, Phase 2 examples)
- [x] main.py CLI
- [x] Documentation structure

### 🚧 In Progress
- [ ] Extract core modules from working codebase
- [ ] Copy working dashboard and fix 5 known bugs
- [ ] Extract task scripts from bash to Python
- [ ] Implement organization agent enforcement
- [ ] Implement git manager commit prompts
- [ ] Implement backtrack functionality
- [ ] Test end-to-end Phase 0
- [ ] Test end-to-end fast-path (Phases 3-9)

### 📅 Planned
- [ ] Extract all 60+ task scripts
- [ ] Full integration testing
- [ ] Documentation completion
- [ ] Migration from atomic-claude to atomic-claude

---

## Next Steps

1. **Review structure** - Validate this architecture meets requirements
2. **Begin extraction** - Start with core modules (providers.py AS-IS)
3. **Phase 0 conversion** - Prove the pattern works
4. **Iterate** - Extract remaining phases methodically

See [REFACTORING-PLAN-V2.md](REFACTORING-PLAN-V2.md) for detailed implementation plan.

---

**Ready to extract and organize!**
