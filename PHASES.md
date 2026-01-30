# ATOMIC CLAUDE - Phase Structure

## Overview

ATOMIC CLAUDE uses a 10-phase pipeline (0-9), each with tasks numbered X01-X99.

```
0-Setup → 1-Discovery → 2-PRD → 3-Tasking → 4-Specification → 5-Implementation → 6-Code-Review → 7-Integration → 8-Deployment-Prep → 9-Release
```

## Common Task Patterns

Most phases follow a consistent structure with these recurring task types:

| Pattern | Purpose |
|---------|---------|
| **Entry & Initialization** | Validate prerequisites, load context from previous phase |
| **Agent Selection** | Choose specialized LLM agents for phase-specific work |
| **Phase Audit** | Automated validation that phase objectives were met |
| **Closeout** | Save artifacts, prepare context for next phase |

---

## Phase Definitions

### Phase 0: Setup (001-009)
**Purpose:** Project configuration, environment validation, and material collection

| Task | Name | Type | Description |
|------|------|------|-------------|
| 001 | Mode Selection | Menu | Choose new project or resume existing |
| 002 | Config Collection | Input | Gather project name, description, type |
| 003 | Config Review | Gate | Review and confirm configuration |
| 004 | API Keys | Secure Input | Configure LLM provider credentials |
| 005 | Material Scan | Deterministic | Scan for reference materials (docs, repos) |
| 006 | Reference Materials | LLM | Summarize and index reference materials |
| 007 | Environment Setup | Deterministic | Create output directories and state files |
| 008 | Repository Setup | Deterministic | Initialize or clone git repository |
| 009 | Environment Check | Deterministic | Validate all dependencies are available |

---

### Phase 1: Discovery (101-110)
**Purpose:** Understand the project idea, explore existing codebase, establish context

| Task | Name | Type | Description |
|------|------|------|-------------|
| 101 | Entry Validation | Deterministic | Verify Phase 0 completed successfully |
| 102 | Corpus Collection | Deterministic | Gather codebase files for analysis |
| 103 | Import Requirements | Input (Optional) | Import existing requirements documents |
| 104 | Opening Dialogue | LLM + Input | Initial conversation about project goals |
| 105 | Agent Selection | Menu | Choose discovery agents (e.g., systems-architect) |
| 106 | Discovery Work | LLM | Deep exploration of idea and codebase |
| 107 | Approach Selection | Gate | Human confirms direction before proceeding |
| 108 | Discovery Diagrams | LLM | Generate architecture and flow diagrams |
| 109 | Phase Audit | LLM | Validate discovery objectives met |
| 110 | Closeout | Deterministic | Save context for PRD phase |

---

### Phase 2: PRD (201-209)
**Purpose:** Draft, validate, and approve Product Requirements Document

| Task | Name | Type | Description |
|------|------|------|-------------|
| 201 | Entry Validation | Deterministic | Verify Phase 1 completed successfully |
| 202 | PRD Setup | Deterministic | Initialize PRD structure and templates |
| 203 | PRD Interview | LLM + Input (Optional) | Confirmatory questions about requirements |
| 204 | Agent Selection | Menu | Choose PRD agents (e.g., prd-author) |
| 205 | PRD Authoring | LLM | Generate comprehensive PRD document |
| 206 | PRD Validation | LLM | Validate PRD completeness and consistency |
| 206b | PRD Revision | LLM + Input | Address validation findings via Q&A |
| 207 | PRD Approval | Gate | Human review, refinement, and sign-off |
| 208 | Phase Audit | LLM | Validate PRD meets quality standards |
| 209 | Closeout | Deterministic | Save approved PRD for tasking phase |

---

### Phase 3: Tasking (301-306)
**Purpose:** Decompose PRD into implementable tasks with dependencies

| Task | Name | Type | Description |
|------|------|------|-------------|
| 301 | Entry & Initialization | Deterministic | Verify Phase 2 completed, load PRD |
| 302 | Agent Selection | Menu | Choose tasking agents (e.g., task-decomposer) |
| 303 | Task Decomposition | LLM | Break PRD into atomic tasks |
| 304 | Dependency Analysis | LLM | Identify task dependencies, create DAG |
| 305 | Phase Audit | LLM | Validate task coverage and dependencies |
| 306 | Closeout | Deterministic | Save tasks.json for specification phase |

---

### Phase 4: Specification (401-406)
**Purpose:** Generate detailed OpenSpec for each task

| Task | Name | Type | Description |
|------|------|------|-------------|
| 401 | Entry & Initialization | Deterministic | Verify Phase 3 completed, load tasks |
| 402 | Agent Selection | Menu | Choose spec agents (e.g., openspec-author) |
| 403 | OpenSpec Generation | LLM | Generate specs for all tasks (parallel capable) |
| 404 | TDD Subtask Injection | Deterministic | Add RED/GREEN/REFACTOR/VERIFY subtasks |
| 405 | Phase Audit | LLM | Validate spec completeness |
| 406 | Closeout | Deterministic | Save specs for implementation phase |

---

### Phase 5: Implementation (501-507)
**Purpose:** TDD execution - Red/Green/Refactor/Verify cycles

| Task | Name | Type | Description |
|------|------|------|-------------|
| 501 | Entry & Initialization | Deterministic | Verify Phase 4 completed, load specs |
| 502 | TDD Setup | Deterministic | Configure test framework and directories |
| 503 | Agent Selection | Menu | Choose TDD agents (test-writer, implementer, etc.) |
| 504 | TDD Execution | LLM | Execute TDD cycles (parallel/sequential/guided) |
| 505 | Final Validation | Deterministic | Run full test suite, coverage check |
| 506 | Phase Audit | LLM | Validate implementation completeness |
| 507 | Closeout | Deterministic | Save implementation for review phase |

**TDD Cycle (per task in 504):**
1. **RED** - Write failing tests based on OpenSpec
2. **GREEN** - Implement minimal code to pass tests
3. **REFACTOR** - Improve code quality while maintaining tests
4. **VERIFY** - Security scan and spec conformance check

---

### Phase 6: Code Review (601-606)
**Purpose:** Comprehensive code review and quality assurance

| Task | Name | Type | Description |
|------|------|------|-------------|
| 601 | Entry & Initialization | Deterministic | Verify Phase 5 completed, collect changes |
| 602 | Agent Selection | Menu | Choose review agents (e.g., code-review-gate) |
| 603 | Comprehensive Review | LLM | Static analysis, security review, best practices |
| 604 | Refinement | LLM + Input | Address review findings |
| 605 | Phase Audit | LLM | Validate review coverage |
| 606 | Closeout | Deterministic | Save reviewed code for integration |

---

### Phase 7: Integration (701-707)
**Purpose:** Integration testing and component verification

| Task | Name | Type | Description |
|------|------|------|-------------|
| 701 | Entry & Initialization | Deterministic | Verify Phase 6 completed |
| 702 | Integration Setup | Deterministic | Configure integration test environment |
| 703 | Agent Selection | Menu | Choose integration agents |
| 704 | Testing Execution | LLM + Deterministic | Run integration and E2E tests |
| 705 | Integration Approval | Gate | Human approval of integration results |
| 706 | Phase Audit | LLM | Validate integration completeness |
| 707 | Closeout | Deterministic | Save integration results |

---

### Phase 8: Deployment Prep (801-807)
**Purpose:** Prepare deployment artifacts and documentation

| Task | Name | Type | Description |
|------|------|------|-------------|
| 801 | Entry & Initialization | Deterministic | Verify Phase 7 completed |
| 802 | Deployment Setup | Deterministic | Configure deployment targets |
| 803 | Agent Selection | Menu | Choose deployment agents |
| 804 | Artifact Generation | LLM + Deterministic | Generate deployment artifacts, docs |
| 805 | Phase Audit | LLM | Validate deployment readiness |
| 806 | Deployment Approval | Gate | Human approval for deployment |
| 807 | Closeout | Deterministic | Save deployment artifacts |

---

### Phase 9: Release (901-906)
**Purpose:** Execute release and confirm deployment

| Task | Name | Type | Description |
|------|------|------|-------------|
| 901 | Entry & Initialization | Deterministic | Verify Phase 8 completed |
| 902 | Release Setup | Deterministic | Configure release environment |
| 903 | Agent Selection | Menu | Choose release agents |
| 904 | Release Execution | Deterministic + LLM | Execute deployment, run smoke tests |
| 905 | Release Confirmation | Gate | Verify deployment success |
| 906 | Closeout (Final) | Deterministic | Archive project, generate summary |

---

## Task Numbering Convention

```
XYY
│││
│└┴─ Task number within phase (01-99)
└─── Phase number (0-9)
```

**Examples:**
- `001` → Phase 0 (Setup), Task 1 (Mode Selection)
- `105` → Phase 1 (Discovery), Task 5 (Agent Selection)
- `504` → Phase 5 (Implementation), Task 4 (TDD Execution)
- `906` → Phase 9 (Release), Task 6 (Final Closeout)

**Gaps are intentional** - allows inserting tasks without renumbering:
- `206b` was inserted between validation and approval
- Future tasks can use numbers like `307`, `408`, etc.

---

## Task Types

| Type | Description |
|------|-------------|
| **Deterministic** | No LLM needed - file operations, validation, setup |
| **Input** | Requires human input (text, selection) |
| **Menu** | Selection from predefined options |
| **LLM** | Requires LLM agent invocation |
| **LLM + Input** | LLM generates, human refines |
| **Gate** | Human approval required to proceed |
| **Secure Input** | Sensitive data entry (API keys, credentials) |

---

## Execution Modes

Phases support different execution modes where applicable:

| Mode | Description |
|------|-------------|
| **Sequential** | Process tasks one at a time (default) |
| **Guided** | Pause between tasks for human review |
| **Parallel** | Process independent tasks concurrently (DAG-aware) |

Parallel mode respects task dependencies - a task won't start until all its dependencies are complete.
