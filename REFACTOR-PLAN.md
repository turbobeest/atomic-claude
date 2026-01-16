# ATOMIC CLAUDE: The Refactor Plan

## Executive Summary

**Current State (dev-sys):** Claude runs as the orchestrator, trying to follow instructions while a bash script constrains it.

**Proposed State (ATOMIC-CLAUDE):** Bash scripts control all flow. Claude is invoked as a tool for specific, bounded, non-deterministic tasks only.

```
CURRENT (dev-sys):
┌─────────────────────────────────────────────────────────────┐
│  Claude Code Session                                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Orchestrator tries to guide Claude                   │  │
│  │  ↓                                                    │  │
│  │  Claude decides what to do next                       │  │
│  │  ↓                                                    │  │
│  │  Hooks try to block bad behavior                      │  │
│  │  ↓                                                    │  │
│  │  Claude may or may not follow instructions            │  │
│  └───────────────────────────────────────────────────────┘  │
│  Problems: Context rot, skipped steps, inconsistent output  │
└─────────────────────────────────────────────────────────────┘

PROPOSED (ATOMIC-CLAUDE):
┌─────────────────────────────────────────────────────────────┐
│  Bash Script (Sovereign)                                    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  1. Read state                                        │  │
│  │  2. Perform deterministic task                        │  │
│  │  3. IF LLM needed: atomic_invoke(prompt, output)      │  │
│  │     └─→ Claude starts, does ONE thing, exits          │  │
│  │  4. Validate output                                   │  │
│  │  5. Update state                                      │  │
│  │  6. Next step (or human gate)                         │  │
│  └───────────────────────────────────────────────────────┘  │
│  Benefits: Deterministic flow, no context rot, guaranteed   │
│            steps, bounded prompts, validated outputs        │
└─────────────────────────────────────────────────────────────┘
```

## Core Principles

### 1. Script is Sovereign
- Bash/Python controls ALL flow, state, and decisions
- Claude never decides "what to do next"
- Script reads state, constructs prompts, validates outputs

### 2. Claude is Stateless
- Each invocation knows ONLY what the prompt tells it
- No memory between invocations
- Context is explicitly passed via prompt construction

### 3. Bounded Prompts
- Every Claude call has a markdown file defining:
  - Exactly what task to perform
  - Expected output format
  - Constraints and boundaries
- No open-ended "help me with X" prompts

### 4. Structured Output
- Claude returns parseable results (JSON, specific formats)
- Script validates output before proceeding
- Invalid output = task failure, not "try again"

### 5. No Context Bleed
- Session terminates after each task
- Fresh start every invocation
- State lives in files, not LLM memory

### 6. Human Gates are Script Logic
- Not "Claude please ask the user"
- Script literally waits for input
- Approval is logged and verifiable

---

## Task Classification

From analyzing the dev-sys storyboards, every task falls into one of these categories:

### Deterministic Tasks (No LLM Needed) ≈85%

| Category | Examples | Implementation |
|----------|----------|----------------|
| File Operations | Create dirs, copy files, chmod | Pure bash |
| Git Operations | commit, tag, push, branch | Pure bash |
| State Management | Read/write JSON state | jq + bash |
| Validation | Check file exists, validate JSON schema | bash + jq |
| User Input | Collect name, choose from menu | read + select |
| Environment Checks | Tool versions, dependency check | which/command -v |
| Template Expansion | Variable substitution | sed/envsubst |
| Report Generation | Aggregate data into report | jq |

### Non-Deterministic Tasks (LLM Needed) ≈15%

| Category | Examples | Prompt Strategy |
|----------|----------|-----------------|
| **Analysis** | Summarize docs, analyze architecture | Read → Summarize |
| **Synthesis** | Generate PRD from notes, write specs | Structured input → Output format |
| **Code Generation** | Write tests, implement features | Spec + examples → Code |
| **Review** | Code review, security audit | Code + checklist → Findings |
| **Decision Support** | Recommend approach, identify risks | Context → Structured recommendation |

---

## Phase Breakdown

Based on the storyboards in `dev-sys/docs/architecture/storyboards/`:

### Phase 00: Setup (95% Deterministic)

```
LLM Tasks:
- Summarize existing documentation (optional, ~50 lines context)
- Categorize materials (only if >10 files found)

Everything Else (Deterministic):
- Collect project name (user input)
- Collect description (user input)
- Select project type (menu)
- Detect/collect GitHub URL (git command)
- Collect API keys (secure input)
- Validate environment (tool checks)
- Create configuration files (templates)
```

### Phase 01: Ideation (70% Deterministic)

```
LLM Tasks:
- Extract key concepts from user's idea description
- Identify potential challenges/risks
- Generate initial user stories

Everything Else:
- Collect idea description (user input)
- Store/organize user stories (file ops)
- Manage iteration (script loop)
- Human review gates
```

### Phase 02: Discovery (60% Deterministic)

```
LLM Tasks:
- Analyze codebase architecture
- Identify patterns and conventions
- Generate technical summary

Everything Else:
- Scan codebase (find, grep)
- Count files by type (wc, file)
- Detect frameworks (pattern matching)
- Create structure report (jq)
```

### Phase 03-04: PRD & Validation (50% Deterministic)

```
LLM Tasks:
- Draft PRD sections
- Validate PRD completeness
- Generate acceptance criteria
- Cross-reference requirements

Everything Else:
- Structure PRD document (templates)
- Version control PRD
- Track review iterations
- Human approval gates
```

### Phase 05-06: Task Decomposition & Specification (40% Deterministic)

```
LLM Tasks:
- Break down features into tasks
- Generate task specifications
- Identify dependencies
- Estimate complexity

Everything Else:
- Task tracking (JSON state)
- Dependency graph (mermaid gen)
- Assignment management
```

### Phase 07: TDD Implementation (30% Deterministic)

```
LLM Tasks:
- Write failing tests (RED)
- Implement code to pass tests (GREEN)
- Refactor for quality (REFACTOR)
- Security analysis (VERIFY)

Everything Else:
- Run test suite (pytest, jest)
- Coverage reporting (coverage tools)
- Git operations per task
- Worktree management (git worktree)
```

### Phase 08-12: Review, Integration, Deployment (50% Deterministic)

```
LLM Tasks:
- Code review analysis
- Integration verification
- Deployment planning

Everything Else:
- CI/CD execution (scripts)
- Environment management
- Rollback procedures
- Telemetry collection
```

---

## Directory Structure

```
ATOMIC-CLAUDE/
├── lib/
│   ├── atomic.sh          # Core invocation library
│   ├── phase.sh           # Phase lifecycle management
│   ├── state.sh           # State management utilities
│   └── output.sh          # Formatting and display
│
├── phases/
│   ├── 00-setup/
│   │   ├── run.sh         # Main phase script
│   │   ├── tasks/         # Individual task scripts (if complex)
│   │   ├── prompts/       # Bounded prompt templates
│   │   └── verify.sh      # Phase verification
│   │
│   ├── 01-ideation/
│   │   ├── run.sh
│   │   ├── prompts/
│   │   │   ├── extract-concepts.md
│   │   │   ├── identify-risks.md
│   │   │   └── generate-stories.md
│   │   └── verify.sh
│   │
│   ├── 02-discovery/
│   ├── 03-prd-draft/
│   ├── 04-prd-validation/
│   ├── 05-task-decomposition/
│   ├── 06-specification/
│   ├── 07-tdd-implementation/
│   ├── 08-code-review/
│   ├── 09-integration/
│   ├── 10-validation/
│   ├── 11-deployment/
│   └── 12-rollback/
│
├── .state/                # Runtime state (gitignored)
│   └── session.json
│
├── .outputs/              # Phase outputs
│   ├── 00-setup/
│   │   ├── project-config.json
│   │   ├── doc-summary.md
│   │   └── closeout.json
│   └── ...
│
├── .logs/                 # Invocation logs
│   └── 20241215.log
│
└── main.sh               # Entry point / orchestrator
```

---

## Migration Strategy

### Step 1: Validate Core (DONE)
- [x] Create `lib/atomic.sh` with `atomic_invoke`
- [x] Create `lib/phase.sh` with phase lifecycle
- [x] Test with prototype

### Step 2: Extract Phase 00
- [ ] Map storyboard to task list
- [ ] Identify LLM vs deterministic tasks
- [ ] Create prompts for LLM tasks
- [ ] Implement `phases/00-setup/run.sh`
- [ ] Test end-to-end

### Step 3: Extract Remaining Phases
- [ ] Phase 01: Ideation
- [ ] Phase 02: Discovery
- [ ] Phase 03: PRD Draft
- [ ] Phase 04: PRD Validation
- [ ] Phase 05: Task Decomposition
- [ ] Phase 06: Specification
- [ ] Phase 07: TDD Implementation
- [ ] Phase 08: Code Review
- [ ] Phase 09: Integration
- [ ] Phase 10: Validation
- [ ] Phase 11: Deployment
- [ ] Phase 12: Rollback

### Step 4: Testing Framework
- [ ] Create test harness for phases
- [ ] Mock Claude responses for CI
- [ ] Integration tests

### Step 5: Documentation
- [ ] Usage guide
- [ ] Prompt writing guide
- [ ] Customization guide

---

## Prompt Design Guidelines

### Structure Every Prompt

```markdown
# Task: [Clear Task Name]

[1-2 sentence description of what Claude should do]

## Context

[Relevant background provided by the script]

## Instructions

1. [Step 1]
2. [Step 2]
3. [Step 3]

## Output Format

[Exact format expected - JSON schema, template, etc.]

## Constraints

- [What NOT to do]
- [Boundaries]
- [Assumptions NOT to make]

## Input

[Data provided via stdin or inline]
```

### Model Selection Guidelines

| Model | Use For | Cost/Speed |
|-------|---------|------------|
| haiku | Simple analysis, categorization, extraction | Fast/Cheap |
| sonnet | Code generation, reviews, complex synthesis | Balanced |
| opus | Critical decisions, complex architecture | Slow/Expensive |

### Output Validation

Always validate:
```bash
# For JSON output
if jq . "$output_file" > /dev/null 2>&1; then
    # Valid JSON
else
    # Failed - don't proceed
fi

# For required fields
if jq -e '.required_field' "$output_file" > /dev/null; then
    # Field exists
fi
```

---

## Benefits Over dev-sys

| Issue | dev-sys | ATOMIC-CLAUDE |
|-------|---------|---------------|
| Context rot | Session grows, Claude forgets | Fresh context every task |
| Skipped steps | Claude decides to skip | Script enforces every step |
| Inconsistent output | Varies by session | Bounded prompts = consistent |
| Human gates bypassed | Claude might not wait | Script literally blocks |
| State confusion | LLM "remembers" wrong state | State in files, not memory |
| Debugging | Read Claude's reasoning | Read script + logs |
| Testing | Can't mock Claude decisions | Can mock individual prompts |
| Cost control | Long sessions = many tokens | Short bursts, measurable |

---

## Next Steps

1. **Finish Phase 00 implementation** - Complete and test
2. **Run real project through Phase 00** - Validate in practice
3. **Extract Phase 01-02** - Build momentum
4. **Parallel development** - Multiple phases can be built independently
5. **Integration testing** - Full pipeline test
6. **Deprecate dev-sys** - Once ATOMIC-CLAUDE is proven

---

## Notes

- The storyboards in `dev-sys/docs/architecture/storyboards/` are excellent specifications
- Most of the "agent" complexity in dev-sys can be eliminated
- Agents become just: model selection + prompt template
- Human gates become: script waits for input, logs the response
- Verification becomes: bash checks, not LLM self-evaluation
