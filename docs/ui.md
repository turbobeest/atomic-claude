# ATOMIC CLAUDE - Current UI Rendering Per Task

This file shows what each task's UI currently looks like based on task-inventory.csv.
Every element marked "yes" in the CSV is rendered here.

=========================================
## PHASE 0: SETUP
=========================================

### Task 001: Mode Selection
**CSV says:** h1=yes, h2=yes, menu=yes, profile=yes, json=yes, setup_task=yes

```
∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙
  ⬢ PHASE 0: SETUP
∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙

─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Mode Selection

  1. DOCUMENT  - Parse initialization files
  2. GUIDED    - Interactive Q&A
  3. QUICK     - Sensible defaults

  Profile: [standard / minimal / thorough]

  Select [1-3]:
```

=========================================

### Task 002: Config Collection
**CSV says:** h1=yes, h2=yes, menu=yes, profile=yes, json=yes, md=yes, setup_task=yes

```
∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙
  ⬢ CONFIG COLLECTION
∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙

─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Configuration Collection

  1. Parse setup.md
  2. Guided Q&A
  3. Use defaults

  Profile: [standard / minimal / thorough]

  Select [1-3]:
```

=========================================

### Task 003: Config Review (HUMAN GATE)
**CSV says:** h1=yes, h2=yes, menu=yes, custom=yes, gate=yes, approv=yes, json=yes, md=yes

```
∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙
  ⬢ CONFIG REVIEW
∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙

─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Configuration Review

  Approval Checklist:
  ✓ Project name configured
  ✓ Pipeline mode selected
  ✓ API keys validated

  1. Approve configuration
  2. Edit configuration
  3. Start over
  c. [Custom input]

  ╔═══════════════════════════════════════════════════════════╗
  ║ HUMAN GATE                                                ║
  ╠═══════════════════════════════════════════════════════════╣
  ║ Approve this configuration to proceed?                    ║
  ╚═══════════════════════════════════════════════════════════╝

  Proceed? [y/N]:
```

=========================================

### Task 004: API Keys
**CSV says:** h2=yes, json=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  API Keys

  Enter your Anthropic API key:
  > ********

  ✓ API key validated
```

=========================================

### Task 005: Material Scan
**CSV says:** h2=yes, json=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Material Scan

  Scanning project directory...
  ✓ Material scan complete
```

=========================================

### Task 006: Environment Setup
**CSV says:** h2=yes, json=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Environment Setup

  Required dependencies listed...
```

=========================================

### Task 007: Repository Setup
**CSV says:** h2=yes, flow=yes, wkflw=yes, agent_sel=yes, agent_ex=yes, agents_repo=yes, audits_repo=yes, menu=yes, custom=yes, json=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Repository Setup

  ┌──────────────────────────────────────────────────────────────────┐
  │  FLOW DIAGRAM                                                    │
  │                                                                  │
  │  EXTERNAL REPOSITORIES                                           │
  │                                                                  │
  │  Agents:  github.com/turbobeest/agents                           │
  │           162+ specialized agents for pipeline phases            │
  │                                                                  │
  │  Audits:  github.com/turbobeest/audits                           │
  │           Audit checklists and validation profiles               │
  └──────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────┐
  │  WORKFLOW DIAGRAM                                                │
  │                                                                  │
  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐           │
  │  │Clone Agents │───►│Clone Audits │───►│  Validate   │           │
  │  └─────────────┘    └─────────────┘    └─────────────┘           │
  └──────────────────────────────────────────────────────────────────┘

  1. Clone both repositories (recommended)
  2. Specify existing paths
  3. Skip - use built-in defaults only
  c. [Custom repository URLs]

  ⏳ Cloning repositories... (agent_execution)

  Select [1-3, c]:
```

=========================================

### Task 008: Environment Check
**CSV says:** h2=yes, menu=yes, json=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Environment Check

  1. Continue to Phase 1
  2. Re-run environment check
  3. Exit setup

  ✓ All tools validated
  ✓ System capabilities assessed

  Select [1-3]:
```

=========================================

### Task 009: Closeout
**CSV says:** close=yes, approv=yes, json=yes, md=yes, closeout_task=yes

```
  Approval Checklist:
  ✓ Configuration complete
  ✓ API keys validated
  ✓ Agent repository configured
  ✓ Environment verified

  ✓ Phase 0 complete

                                                    ▪▪▪ CLOSEOUT ▪▪▪
```

=========================================
## PHASE 1: DISCOVERY
=========================================

### Task 101: Entry Validation
**CSV says:** h1=yes, entry=yes, flow=yes, approv=yes, entry_task=yes

```
══════════════════════════════════════════════════════════════════════
  ▶▶ PHASE 1: DISCOVERY ─────────────────────────────────────── [101]
══════════════════════════════════════════════════════════════════════

∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙
  ⬢ ENTRY VALIDATION
∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙

  ┌──────────────────────────────────────────────────────────────────┐
  │  FLOW DIAGRAM                                                    │
  │                                                                  │
  │  Phase 0 ──────────────────► Phase 1                             │
  │  [Setup]                     [Discovery]                         │
  │     ✓                           ◉                                │
  └──────────────────────────────────────────────────────────────────┘

  Approval Checklist:
  ✓ Phase 0 closeout complete
  ✓ Project config loaded
  ✓ Agent repository accessible
```

=========================================

### Task 102: Corpus Collection
**CSV says:** h2=yes, json=yes, md=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Corpus Collection

  Scanning for project materials...
```

=========================================

### Task 103: Import Requirements
**CSV says:** h2=yes, menu=yes, json=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Import Requirements

  1. requirements.md (local)
  2. JIRA export (external)
  3. Skip import

  Select [1-3]:
```

=========================================

### Task 104: Opening Dialogue
**CSV says:** h2=yes, json=yes, md=yes, execution=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Opening Dialogue

  ⏳ Agent executing discovery dialogue...
```

=========================================

### Task 105: Agent Selection
**CSV says:** h2=yes, flow=yes, wkflw=yes, agent_sel=yes, agent_ex=yes, agents_repo=yes, menu=yes, custom=yes, json=yes, md=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Agent Selection

  ┌──────────────────────────────────────────────────────────────────┐
  │  FLOW DIAGRAM                                                    │
  │                                                                  │
  │  AGENT ROSTER FOR ALL PHASES                                     │
  │                                                                  │
  │  Phase 1: discovery-agent     Phase 6: code-reviewer             │
  │  Phase 2: prd-writer          Phase 7: integration-agent         │
  │  Phase 3: task-decomposer     Phase 8: deployment-agent          │
  │  Phase 4: spec-author         Phase 9: release-agent             │
  │  Phase 5: tdd-implementer                                        │
  └──────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────┐
  │  WORKFLOW DIAGRAM                                                │
  │                                                                  │
  │  ┌─────────┐    ┌─────────┐    ┌─────────┐                       │
  │  │ Select  │───►│ Validate│───►│ Activate│                       │
  │  └─────────┘    └─────────┘    └─────────┘                       │
  └──────────────────────────────────────────────────────────────────┘

  1. discovery-agent (recommended)
  2. research-agent
  3. analyst-agent
  c. [Custom agent definition]

  Select [1-3, c]:

  ⏳ Activating agent... (agent_execution)
```

=========================================

### Task 106: Approach Deliberation
**CSV says:** h2=yes, flow=yes, wkflw=yes, agent_sel=yes, agent_ex=yes, menu=yes, custom=yes, json=yes, md=yes, execution=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Approach Deliberation

  ┌──────────────────────────────────────────────────────────────────┐
  │  FLOW DIAGRAM                                                    │
  │                                                                  │
  │  ┌──────────┐      ┌──────────┐      ┌──────────┐                │
  │  │ Propose  │ ───► │  Debate  │ ───► │ Consensus│                │
  │  └──────────┘      └──────────┘      └──────────┘                │
  └──────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────┐
  │  WORKFLOW DIAGRAM                                                │
  │                                                                  │
  │  Agent 1 proposes → Agent 2 critiques → Consensus reached        │
  └──────────────────────────────────────────────────────────────────┘

  1. Continue deliberation
  2. Switch participating agents
  3. Pause deliberation
  c. [Custom input]

  Select [1-3, c]:

  ⏳ Multi-agent deliberation in progress...
```

=========================================

### Task 107: Direction Confirmation
**CSV says:** h2=yes, menu=yes, profile=yes, json=yes, execution=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Direction Confirmation

  Consensus from deliberation:
  ┌──────────────────────────────────────────────────────────────────┐
  │  Recommended: Greenfield approach                                │
  │  Risk Level: Medium                                              │
  │  Agent Agreement: 4/5 in favor                                   │
  └──────────────────────────────────────────────────────────────────┘

  1. Accept consensus recommendation
  2. Override with alternative approach
  3. Request additional deliberation

  Profile: [conservative / balanced / aggressive]

  Select [1-3]:
```

=========================================

### Task 108: Discovery Diagrams
**CSV says:** h2=yes, flow=yes, wkflw=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Discovery Diagrams

  ┌──────────────────────────────────────────────────────────────────┐
  │  FLOW DIAGRAM                                                    │
  │                                                                  │
  │  ┌──────────┐      ┌──────────┐      ┌──────────┐                │
  │  │  Client  │ ───► │   API    │ ───► │ Database │                │
  │  └──────────┘      └──────────┘      └──────────┘                │
  └──────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────┐
  │  WORKFLOW DIAGRAM                                                │
  │                                                                  │
  │  Request ──► Validate ──► Process ──► Store ──► Response         │
  └──────────────────────────────────────────────────────────────────┘
```

=========================================

### Task 109: Phase Audit
**CSV says:** h2=yes, audit=yes, approv=yes, audits_repo=yes, profile=yes, json=yes, md=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Phase Audit

  Profile: [quick / standard / thorough]

  ┌──────────────────────────────────────────────────────────────────┐
  │  AUDIT RESULTS (from audits repo)                                │
  │                                                                  │
  │  ✓ REQ-001: Requirements documented                              │
  │  ✓ REQ-002: Success criteria defined                             │
  │  ⚠ REQ-003: Edge cases identified (partial)                      │
  └──────────────────────────────────────────────────────────────────┘

  Approval Checklist:
  ✓ All critical items passed
  ✓ High-priority items passed
  ⚠ 1 medium-priority warning
```

=========================================

### Task 110: Closeout
**CSV says:** close=yes, approv=yes, json=yes, md=yes, closeout_task=yes

```
  Approval Checklist:
  ✓ Discovery complete
  ✓ Artifacts generated
  ✓ Agent output reviewed

  ✓ Phase 1 complete

                                                    ▪▪▪ CLOSEOUT ▪▪▪
```

=========================================
## PHASE 2: PRD
=========================================

### Task 201: Entry Validation
**CSV says:** h1=yes, entry=yes, flow=yes, approv=yes, entry_task=yes

```
══════════════════════════════════════════════════════════════════════
  ▶▶ PHASE 2: PRD ───────────────────────────────────────────── [201]
══════════════════════════════════════════════════════════════════════

∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙
  ⬢ ENTRY VALIDATION
∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙

  ┌──────────────────────────────────────────────────────────────────┐
  │  FLOW DIAGRAM                                                    │
  │                                                                  │
  │  Phase 1 ──────────────────► Phase 2                             │
  │  [Discovery]                 [PRD]                               │
  │     ✓                           ◉                                │
  └──────────────────────────────────────────────────────────────────┘

  Approval Checklist:
  ✓ Phase 1 closeout complete
  ✓ Discovery artifacts loaded
```

=========================================

### Task 202: PRD Setup
**CSV says:** h2=yes, json=yes, setup_task=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  PRD Setup

  Initializing PRD structure...
```

=========================================

### Task 203: PRD Interview
**CSV says:** h2=yes, json=yes, md=yes, execution=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  PRD Interview

  ⏳ Conducting interview...
```

=========================================

### Task 204: Agent Selection
**CSV says:** h2=yes, flow=yes, wkflw=yes, agent_sel=yes, agent_ex=yes, agents_repo=yes, menu=yes, custom=yes, json=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Agent Selection

  ┌──────────────────────────────────────────────────────────────────┐
  │  FLOW DIAGRAM                                                    │
  │                                                                  │
  │  Current Phase: PRD                                              │
  │  Roster Assignment: prd-writer                                   │
  └──────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────┐
  │  WORKFLOW DIAGRAM                                                │
  │                                                                  │
  │  ┌─────────┐    ┌─────────┐    ┌─────────┐                       │
  │  │ Select  │───►│ Validate│───►│ Activate│                       │
  │  └─────────┘    └─────────┘    └─────────┘                       │
  └──────────────────────────────────────────────────────────────────┘

  1. prd-writer (roster assignment)
  2. requirements-analyst
  3. product-manager-agent
  c. [Custom agent definition]

  Select [1-3, c]:

  ⏳ Activating agent... (agent_execution)
```

=========================================

### Task 205: PRD Authoring
**CSV says:** h2=yes, agent_ex=yes, json=yes, md=yes, execution=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  PRD Authoring

  ⏳ Agent authoring PRD...
```

=========================================

### Task 206: PRD Validation
**CSV says:** h2=yes, approv=yes, json=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  PRD Validation

  Approval Checklist:
  ✓ All required sections present
  ✓ User stories have acceptance criteria
```

=========================================

### Task 207: Phase Audit
**CSV says:** h2=yes, audit=yes, approv=yes, audits_repo=yes, profile=yes, json=yes, md=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Phase Audit

  Profile: [quick / standard / thorough]

  ┌──────────────────────────────────────────────────────────────────┐
  │  AUDIT RESULTS                                                   │
  │  ✓ REQ-001: Requirements complete                                │
  │  ✓ REQ-002: Testability verified                                 │
  └──────────────────────────────────────────────────────────────────┘

  Approval Checklist:
  ✓ All items passed
```

=========================================

### Task 208: PRD Approval (HUMAN GATE)
**CSV says:** h1=yes, h2=yes, approv=yes, gate=yes, json=yes

```
∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙
  ⬢ PRD APPROVAL
∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙

─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  PRD Approval

  Approval Checklist:
  ✓ Stakeholder review complete
  ✓ Technical feasibility confirmed
  ✓ Phase audit passed (see Task 207)

  ╔═══════════════════════════════════════════════════════════╗
  ║ HUMAN GATE                                                ║
  ╠═══════════════════════════════════════════════════════════╣
  ║ Approve PRD to proceed?                                   ║
  ╚═══════════════════════════════════════════════════════════╝

  Proceed? [y/N]:
```

=========================================

### Task 209: Closeout
**CSV says:** close=yes, approv=yes, json=yes, md=yes, closeout_task=yes

```
  Approval Checklist:
  ✓ PRD finalized
  ✓ Stakeholder approval
  ✓ Artifacts archived

  ✓ Phase 2 complete

                                                    ▪▪▪ CLOSEOUT ▪▪▪
```

=========================================
## PHASE 3: TASK DECOMPOSITION
=========================================

### Task 301: Entry Initialization
**CSV says:** h1=yes, entry=yes, flow=yes, approv=yes, entry_task=yes

```
══════════════════════════════════════════════════════════════════════
  ▶▶ PHASE 3: TASK DECOMPOSITION ────────────────────────────── [301]
══════════════════════════════════════════════════════════════════════

∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙
  ⬢ ENTRY INITIALIZATION
∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙

  ┌──────────────────────────────────────────────────────────────────┐
  │  FLOW DIAGRAM                                                    │
  │                                                                  │
  │  Phase 2 ──────────────────► Phase 3                             │
  │  [PRD]                       [Task Decomposition]                │
  │     ✓                           ◉                                │
  └──────────────────────────────────────────────────────────────────┘

  Approval Checklist:
  ✓ Phase 2 closeout complete
  ✓ PRD loaded
```

=========================================

### Task 302: Agent Selection
**CSV says:** h2=yes, flow=yes, wkflw=yes, agent_sel=yes, agent_ex=yes, agents_repo=yes, menu=yes, custom=yes, json=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Agent Selection

  ┌──────────────────────────────────────────────────────────────────┐
  │  FLOW DIAGRAM                                                    │
  │                                                                  │
  │  Current Phase: Task Decomposition                               │
  │  Roster Assignment: task-decomposer                              │
  └──────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────┐
  │  WORKFLOW DIAGRAM                                                │
  │                                                                  │
  │  ┌─────────┐    ┌─────────┐    ┌─────────┐                       │
  │  │ Select  │───►│ Validate│───►│ Activate│                       │
  │  └─────────┘    └─────────┘    └─────────┘                       │
  └──────────────────────────────────────────────────────────────────┘

  1. task-decomposer (roster assignment)
  2. project-planner
  3. work-breakdown-agent
  c. [Custom agent definition]

  Select [1-3, c]:

  ⏳ Activating agent... (agent_execution)
```

=========================================

### Task 303: Task Decomposition
**CSV says:** h2=yes, wkflw=yes, agent_ex=yes, json=yes, md=yes, execution=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Task Decomposition

  ┌──────────────────────────────────────────────────────────────────┐
  │  WORKFLOW DIAGRAM                                                │
  │                                                                  │
  │  PRD → Epic → Story → Task                                       │
  │                                                                  │
  │  Epic 1: User Authentication                                     │
  │    ├── Story 1.1: Login flow                                     │
  │    │     ├── Task: Create login form                             │
  │    │     └── Task: Implement auth API                            │
  │    └── Story 1.2: Registration                                   │
  └──────────────────────────────────────────────────────────────────┘

  ⏳ Decomposing requirements...
```

=========================================

### Task 304: Dependency Analysis
**CSV says:** h2=yes, flow=yes, wkflw=yes, json=yes, md=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Dependency Analysis

  ┌──────────────────────────────────────────────────────────────────┐
  │  FLOW DIAGRAM                                                    │
  │                                                                  │
  │  ┌──────────┐                                                    │
  │  │ Task 1.1 │──────┐                                             │
  │  └──────────┘      │      ┌──────────┐                           │
  │                    ├─────►│ Task 1.3 │                           │
  │  ┌──────────┐      │      └──────────┘                           │
  │  │ Task 1.2 │──────┘                                             │
  │  └──────────┘                                                    │
  └──────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────┐
  │  WORKFLOW DIAGRAM                                                │
  │                                                                  │
  │  Critical Path: Task 1.1 → Task 1.3 → Task 2.1                   │
  └──────────────────────────────────────────────────────────────────┘
```

=========================================

### Task 305: Phase Audit
**CSV says:** h2=yes, audit=yes, approv=yes, audits_repo=yes, profile=yes, json=yes, md=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Phase Audit

  Profile: [quick / standard / thorough]

  ┌──────────────────────────────────────────────────────────────────┐
  │  AUDIT RESULTS                                                   │
  │  ✓ All PRD items mapped to tasks                                 │
  │  ✓ Dependencies are acyclic                                      │
  │  ✓ Estimates provided                                            │
  └──────────────────────────────────────────────────────────────────┘

  Approval Checklist:
  ✓ All items passed
```

=========================================

### Task 306: Closeout
**CSV says:** close=yes, approv=yes, json=yes, md=yes, closeout_task=yes

```
  Approval Checklist:
  ✓ Tasks decomposed
  ✓ Dependencies mapped
  ✓ Critical path identified

  ✓ Phase 3 complete

                                                    ▪▪▪ CLOSEOUT ▪▪▪
```

=========================================
## PHASE 4: SPECIFICATION
=========================================

### Task 401: Entry Initialization
**CSV says:** h1=yes, entry=yes, flow=yes, approv=yes, entry_task=yes

```
══════════════════════════════════════════════════════════════════════
  ▶▶ PHASE 4: SPECIFICATION ─────────────────────────────────── [401]
══════════════════════════════════════════════════════════════════════

∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙
  ⬢ ENTRY INITIALIZATION
∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙

  ┌──────────────────────────────────────────────────────────────────┐
  │  FLOW DIAGRAM                                                    │
  │                                                                  │
  │  Phase 3 ──────────────────► Phase 4                             │
  │  [Task Decomposition]        [Specification]                     │
  │     ✓                           ◉                                │
  └──────────────────────────────────────────────────────────────────┘

  Approval Checklist:
  ✓ Phase 3 closeout complete
  ✓ Task breakdown loaded
```

=========================================

### Task 402: Agent Selection
**CSV says:** h2=yes, flow=yes, wkflw=yes, agent_sel=yes, agent_ex=yes, agents_repo=yes, menu=yes, custom=yes, json=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Agent Selection

  ┌──────────────────────────────────────────────────────────────────┐
  │  FLOW DIAGRAM                                                    │
  │                                                                  │
  │  Current Phase: Specification                                    │
  │  Roster Assignment: spec-author                                  │
  └──────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────┐
  │  WORKFLOW DIAGRAM                                                │
  │                                                                  │
  │  ┌─────────┐    ┌─────────┐    ┌─────────┐                       │
  │  │ Select  │───►│ Validate│───►│ Activate│                       │
  │  └─────────┘    └─────────┘    └─────────┘                       │
  └──────────────────────────────────────────────────────────────────┘

  1. spec-author (roster assignment)
  2. api-designer
  3. architect-agent
  c. [Custom agent definition]

  Select [1-3, c]:

  ⏳ Activating agent... (agent_execution)
```

=========================================

### Task 403: OpenSpec Generation
**CSV says:** h2=yes, agent_ex=yes, json=yes, md=yes, execution=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  OpenSpec Generation

  ⏳ Generating OpenAPI spec...
```

=========================================

### Task 404: TDD Subtask Injection
**CSV says:** h2=yes, json=yes, md=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  TDD Subtask Injection

  Injecting test-first subtasks...
```

=========================================

### Task 405: Phase Audit
**CSV says:** h2=yes, audit=yes, approv=yes, audits_repo=yes, profile=yes, json=yes, md=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Phase Audit

  Profile: [quick / standard / thorough]

  ┌──────────────────────────────────────────────────────────────────┐
  │  AUDIT RESULTS                                                   │
  │  ✓ All endpoints specified                                       │
  │  ✓ Data models complete                                          │
  │  ✓ TDD tasks injected                                            │
  └──────────────────────────────────────────────────────────────────┘

  Approval Checklist:
  ✓ All items passed
```

=========================================

### Task 406: Closeout
**CSV says:** close=yes, approv=yes, json=yes, md=yes, closeout_task=yes

```
  Approval Checklist:
  ✓ Specifications complete
  ✓ TDD subtasks injected
  ✓ Artifacts validated

  ✓ Phase 4 complete

                                                    ▪▪▪ CLOSEOUT ▪▪▪
```

=========================================
## PHASE 5: TDD IMPLEMENTATION
=========================================

### Task 501: Entry Initialization
**CSV says:** h1=yes, entry=yes, flow=yes, approv=yes, entry_task=yes

```
══════════════════════════════════════════════════════════════════════
  ▶▶ PHASE 5: TDD IMPLEMENTATION ────────────────────────────── [501]
══════════════════════════════════════════════════════════════════════

∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙
  ⬢ ENTRY INITIALIZATION
∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙

  ┌──────────────────────────────────────────────────────────────────┐
  │  FLOW DIAGRAM                                                    │
  │                                                                  │
  │  Phase 4 ──────────────────► Phase 5                             │
  │  [Specification]             [TDD Implementation]                │
  │     ✓                           ◉                                │
  └──────────────────────────────────────────────────────────────────┘

  Approval Checklist:
  ✓ Phase 4 closeout complete
  ✓ Specifications loaded
```

=========================================

### Task 502: TDD Setup
**CSV says:** h2=yes, json=yes, setup_task=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  TDD Setup

  Setting up test environment...
```

=========================================

### Task 503: Agent Selection
**CSV says:** h2=yes, flow=yes, wkflw=yes, agent_sel=yes, agent_ex=yes, agents_repo=yes, menu=yes, custom=yes, json=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Agent Selection

  ┌──────────────────────────────────────────────────────────────────┐
  │  FLOW DIAGRAM                                                    │
  │                                                                  │
  │  Current Phase: TDD Implementation                               │
  │  Roster Assignment: tdd-implementer                              │
  └──────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────┐
  │  WORKFLOW DIAGRAM                                                │
  │                                                                  │
  │  ┌─────────┐    ┌─────────┐    ┌─────────┐                       │
  │  │ Select  │───►│ Validate│───►│ Activate│                       │
  │  └─────────┘    └─────────┘    └─────────┘                       │
  └──────────────────────────────────────────────────────────────────┘

  1. tdd-implementer (roster assignment)
  2. test-driven-dev
  3. fullstack-agent
  c. [Custom agent definition]

  Select [1-3, c]:

  ⏳ Activating agent... (agent_execution)
```

=========================================

### Task 504: TDD Execution
**CSV says:** h2=yes, agent_ex=yes, json=yes, md=yes, execution=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  TDD Execution

  ⏳ Running TDD cycle...
```

=========================================

### Task 505: Validation
**CSV says:** h2=yes, approv=yes, json=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Validation

  Approval Checklist:
  ✓ All tests passing
  ✓ Coverage target met
  ✓ API matches spec
```

=========================================

### Task 506: Phase Audit
**CSV says:** h2=yes, audit=yes, approv=yes, audits_repo=yes, profile=yes, json=yes, md=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Phase Audit

  Profile: [quick / standard / thorough]

  ┌──────────────────────────────────────────────────────────────────┐
  │  AUDIT RESULTS                                                   │
  │  ✓ MAINT-003: Test coverage adequate                             │
  │  ✓ SEC-001: No vulnerabilities found                             │
  │  ✓ PERF-001: Performance acceptable                              │
  └──────────────────────────────────────────────────────────────────┘

  Approval Checklist:
  ✓ All items passed
```

=========================================

### Task 507: Closeout
**CSV says:** close=yes, approv=yes, json=yes, md=yes, closeout_task=yes

```
  Approval Checklist:
  ✓ Implementation complete
  ✓ All tests passing
  ✓ Code coverage met

  ✓ Phase 5 complete

                                                    ▪▪▪ CLOSEOUT ▪▪▪
```

=========================================
## PHASE 6: CODE REVIEW
=========================================

### Task 601: Entry Initialization
**CSV says:** h1=yes, entry=yes, flow=yes, approv=yes, entry_task=yes

```
══════════════════════════════════════════════════════════════════════
  ▶▶ PHASE 6: CODE REVIEW ───────────────────────────────────── [601]
══════════════════════════════════════════════════════════════════════

∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙
  ⬢ ENTRY INITIALIZATION
∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙

  ┌──────────────────────────────────────────────────────────────────┐
  │  FLOW DIAGRAM                                                    │
  │                                                                  │
  │  Phase 5 ──────────────────► Phase 6                             │
  │  [TDD Implementation]        [Code Review]                       │
  │     ✓                           ◉                                │
  └──────────────────────────────────────────────────────────────────┘

  Approval Checklist:
  ✓ Phase 5 closeout complete
  ✓ Implementation ready for review
```

=========================================

### Task 602: Agent Selection
**CSV says:** h2=yes, flow=yes, wkflw=yes, agent_sel=yes, agent_ex=yes, agents_repo=yes, menu=yes, custom=yes, json=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Agent Selection

  ┌──────────────────────────────────────────────────────────────────┐
  │  FLOW DIAGRAM                                                    │
  │                                                                  │
  │  Current Phase: Code Review                                      │
  │  Roster Assignment: code-reviewer                                │
  └──────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────┐
  │  WORKFLOW DIAGRAM                                                │
  │                                                                  │
  │  ┌─────────┐    ┌─────────┐    ┌─────────┐                       │
  │  │ Select  │───►│ Validate│───►│ Activate│                       │
  │  └─────────┘    └─────────┘    └─────────┘                       │
  └──────────────────────────────────────────────────────────────────┘

  1. code-reviewer (roster assignment)
  2. security-reviewer
  3. senior-engineer-agent
  c. [Custom agent definition]

  Select [1-3, c]:

  ⏳ Activating agent... (agent_execution)
```

=========================================

### Task 603: Comprehensive Review
**CSV says:** h2=yes, agent_ex=yes, json=yes, md=yes, execution=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Comprehensive Review

  ⏳ Running comprehensive review...
```

=========================================

### Task 604: Refinement
**CSV says:** h2=yes, agent_ex=yes, json=yes, md=yes, execution=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Refinement

  ⏳ Refining code based on review...
```

=========================================

### Task 605: Phase Audit
**CSV says:** h2=yes, audit=yes, approv=yes, audits_repo=yes, profile=yes, json=yes, md=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Phase Audit

  Profile: [quick / standard / thorough]

  ┌──────────────────────────────────────────────────────────────────┐
  │  AUDIT RESULTS                                                   │
  │  ✓ All review findings addressed                                 │
  │  ✓ Code quality improved                                         │
  │  ✓ No regressions introduced                                     │
  └──────────────────────────────────────────────────────────────────┘

  Approval Checklist:
  ✓ All items passed
```

=========================================

### Task 606: Closeout
**CSV says:** close=yes, approv=yes, json=yes, md=yes, closeout_task=yes

```
  Approval Checklist:
  ✓ Review complete
  ✓ All findings addressed
  ✓ Code quality verified

  ✓ Phase 6 complete

                                                    ▪▪▪ CLOSEOUT ▪▪▪
```

=========================================
## PHASE 7: INTEGRATION
=========================================

### Task 701: Entry Initialization
**CSV says:** h1=yes, entry=yes, flow=yes, approv=yes, entry_task=yes

```
══════════════════════════════════════════════════════════════════════
  ▶▶ PHASE 7: INTEGRATION ───────────────────────────────────── [701]
══════════════════════════════════════════════════════════════════════

∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙
  ⬢ ENTRY INITIALIZATION
∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙

  ┌──────────────────────────────────────────────────────────────────┐
  │  FLOW DIAGRAM                                                    │
  │                                                                  │
  │  Phase 6 ──────────────────► Phase 7                             │
  │  [Code Review]               [Integration]                       │
  │     ✓                           ◉                                │
  └──────────────────────────────────────────────────────────────────┘

  Approval Checklist:
  ✓ Phase 6 closeout complete
  ✓ Reviewed code ready
```

=========================================

### Task 702: Integration Setup
**CSV says:** h2=yes, json=yes, setup_task=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Integration Setup

  Setting up integration environment...
```

=========================================

### Task 703: Agent Selection
**CSV says:** h2=yes, flow=yes, wkflw=yes, agent_sel=yes, agent_ex=yes, agents_repo=yes, menu=yes, custom=yes, json=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Agent Selection

  ┌──────────────────────────────────────────────────────────────────┐
  │  FLOW DIAGRAM                                                    │
  │                                                                  │
  │  Current Phase: Integration                                      │
  │  Roster Assignment: integration-agent                            │
  └──────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────┐
  │  WORKFLOW DIAGRAM                                                │
  │                                                                  │
  │  ┌─────────┐    ┌─────────┐    ┌─────────┐                       │
  │  │  Unit   │───►│  Integ  │───►│   E2E   │                       │
  │  │  Tests  │    │  Tests  │    │  Tests  │                       │
  │  └─────────┘    └─────────┘    └─────────┘                       │
  └──────────────────────────────────────────────────────────────────┘

  1. integration-agent (roster assignment)
  2. qa-engineer-agent
  3. e2e-test-agent
  c. [Custom agent definition]

  Select [1-3, c]:

  ⏳ Activating agent... (agent_execution)
```

=========================================

### Task 704: Testing Execution
**CSV says:** h2=yes, agent_ex=yes, json=yes, md=yes, execution=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Testing Execution

  ⏳ Running integration tests...
```

=========================================

### Task 705: Phase Audit
**CSV says:** h2=yes, audit=yes, approv=yes, audits_repo=yes, profile=yes, json=yes, md=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Phase Audit

  Profile: [quick / standard / thorough]

  ┌──────────────────────────────────────────────────────────────────┐
  │  AUDIT RESULTS                                                   │
  │  ✓ INT-001: E2E flows validated                                  │
  │  ✓ INT-002: API contracts verified                               │
  │  ✓ PERF-002: Load test passed                                    │
  └──────────────────────────────────────────────────────────────────┘

  Approval Checklist:
  ✓ All items passed
```

=========================================

### Task 706: Integration Approval (HUMAN GATE)
**CSV says:** h1=yes, h2=yes, approv=yes, gate=yes, json=yes

```
∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙
  ⬢ INTEGRATION APPROVAL
∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙

─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Integration Approval

  Approval Checklist:
  ✓ All integration tests pass
  ✓ Performance acceptable
  ✓ No data integrity issues
  ✓ Phase audit passed (see Task 705)

  ╔═══════════════════════════════════════════════════════════╗
  ║ HUMAN GATE                                                ║
  ╠═══════════════════════════════════════════════════════════╣
  ║ Approve integration to proceed to Deployment?             ║
  ╚═══════════════════════════════════════════════════════════╝

  Proceed? [y/N]:
```

=========================================

### Task 707: Closeout
**CSV says:** close=yes, approv=yes, json=yes, md=yes, closeout_task=yes

```
  Approval Checklist:
  ✓ Integration complete
  ✓ All tests passing
  ✓ Performance validated

  ✓ Phase 7 complete

                                                    ▪▪▪ CLOSEOUT ▪▪▪
```

=========================================
## PHASE 8: DEPLOYMENT PREP
=========================================

### Task 801: Entry Initialization
**CSV says:** h1=yes, entry=yes, flow=yes, approv=yes, entry_task=yes

```
══════════════════════════════════════════════════════════════════════
  ▶▶ PHASE 8: DEPLOYMENT PREP ───────────────────────────────── [801]
══════════════════════════════════════════════════════════════════════

∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙
  ⬢ ENTRY INITIALIZATION
∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙

  ┌──────────────────────────────────────────────────────────────────┐
  │  FLOW DIAGRAM                                                    │
  │                                                                  │
  │  Phase 7 ──────────────────► Phase 8                             │
  │  [Integration]               [Deployment Prep]                   │
  │     ✓                           ◉                                │
  └──────────────────────────────────────────────────────────────────┘

  Approval Checklist:
  ✓ Phase 7 closeout complete
  ✓ Integration validated
```

=========================================

### Task 802: Deployment Setup
**CSV says:** h2=yes, menu=yes, json=yes, setup_task=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Deployment Setup

  1. Internal release (team only)
  2. Beta release (limited users)
  3. Full release (all users)

  Select [1-3]:
```

=========================================

### Task 803: Agent Selection
**CSV says:** h2=yes, flow=yes, wkflw=yes, agent_sel=yes, agent_ex=yes, agents_repo=yes, menu=yes, custom=yes, json=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Agent Selection

  ┌──────────────────────────────────────────────────────────────────┐
  │  FLOW DIAGRAM                                                    │
  │                                                                  │
  │  Current Phase: Deployment Prep                                  │
  │  Roster Assignment: deployment-agent                             │
  └──────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────┐
  │  WORKFLOW DIAGRAM                                                │
  │                                                                  │
  │  ┌─────────┐    ┌─────────┐    ┌─────────┐                       │
  │  │  Build  │───►│ Package │───►│ Publish │                       │
  │  └─────────┘    └─────────┘    └─────────┘                       │
  └──────────────────────────────────────────────────────────────────┘

  1. deployment-agent (roster assignment)
  2. devops-agent
  3. release-engineer-agent
  c. [Custom agent definition]

  Select [1-3, c]:

  ⏳ Activating agent... (agent_execution)
```

=========================================

### Task 804: Artifact Generation
**CSV says:** h2=yes, agent_ex=yes, json=yes, md=yes, execution=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Artifact Generation

  ⏳ Generating deployment artifacts...
```

=========================================

### Task 805: Deployment Approval (HUMAN GATE)
**CSV says:** h1=yes, h2=yes, approv=yes, gate=yes, json=yes

```
∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙
  ⬢ DEPLOYMENT APPROVAL
∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙

─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Deployment Approval

  Approval Checklist:
  ✓ All artifacts generated
  ✓ Version numbers correct
  ✓ Release notes reviewed

  ╔═══════════════════════════════════════════════════════════╗
  ║ HUMAN GATE                                                ║
  ╠═══════════════════════════════════════════════════════════╣
  ║ Approve deployment readiness to proceed to Release?       ║
  ╚═══════════════════════════════════════════════════════════╝

  Proceed? [y/N]:
```

=========================================

### Task 806: Closeout
**CSV says:** close=yes, approv=yes, json=yes, md=yes, closeout_task=yes

```
  Approval Checklist:
  ✓ Artifacts generated
  ✓ Deployment approved
  ✓ Ready for release

  ✓ Phase 8 complete

                                                    ▪▪▪ CLOSEOUT ▪▪▪
```

=========================================
## PHASE 9: RELEASE
=========================================

### Task 901: Entry Initialization
**CSV says:** h1=yes, entry=yes, flow=yes, approv=yes, entry_task=yes

```
══════════════════════════════════════════════════════════════════════
  ▶▶ PHASE 9: RELEASE ───────────────────────────────────────── [901]
══════════════════════════════════════════════════════════════════════

∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙
  ⬢ ENTRY INITIALIZATION
∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙

  ┌──────────────────────────────────────────────────────────────────┐
  │  FLOW DIAGRAM                                                    │
  │                                                                  │
  │  Phase 8 ──────────────────► Phase 9                             │
  │  [Deployment Prep]           [Release]                           │
  │     ✓                           ◉                                │
  └──────────────────────────────────────────────────────────────────┘

  Approval Checklist:
  ✓ Phase 8 closeout complete
  ✓ Deployment artifacts ready
```

=========================================

### Task 902: Release Setup
**CSV says:** h2=yes, menu=yes, json=yes, setup_task=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Release Setup

  1. Preview release notes
  2. Edit release notes
  3. Proceed with release

  Select [1-3]:
```

=========================================

### Task 903: Agent Selection
**CSV says:** h2=yes, flow=yes, wkflw=yes, agent_sel=yes, agent_ex=yes, agents_repo=yes, menu=yes, custom=yes, json=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Agent Selection

  ┌──────────────────────────────────────────────────────────────────┐
  │  FLOW DIAGRAM                                                    │
  │                                                                  │
  │  Current Phase: Release                                          │
  │  Roster Assignment: release-agent                                │
  └──────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────┐
  │  WORKFLOW DIAGRAM                                                │
  │                                                                  │
  │  ┌─────────┐    ┌─────────┐    ┌─────────┐                       │
  │  │  Tag    │───►│ Publish │───►│ Notify  │                       │
  │  └─────────┘    └─────────┘    └─────────┘                       │
  └──────────────────────────────────────────────────────────────────┘

  1. release-agent (roster assignment)
  2. publisher-agent
  3. distribution-agent
  c. [Custom agent definition]

  Select [1-3, c]:

  ⏳ Activating agent... (agent_execution)
```

=========================================

### Task 904: Release Execution
**CSV says:** h2=yes, agent_ex=yes, json=yes, md=yes, execution=yes

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Release Execution

  ⏳ Executing internal release...
```

=========================================

### Task 905: Release Confirmation (HUMAN GATE)
**CSV says:** h1=yes, h2=yes, approv=yes, gate=yes, json=yes

```
∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙
  ⬢ RELEASE CONFIRMATION
∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙

─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Release Confirmation

  Approval Checklist:
  ✓ All channels published
  ✓ Team notified
  ✓ Rollback plan documented

  ╔═══════════════════════════════════════════════════════════╗
  ║ HUMAN GATE                                                ║
  ╠═══════════════════════════════════════════════════════════╣
  ║ Confirm release success?                                  ║
  ╚═══════════════════════════════════════════════════════════╝

  Proceed? [y/N]:
```

=========================================

### Task 906: Closeout
**CSV says:** close=yes, approv=yes, json=yes, md=yes, closeout_task=yes

```
  Approval Checklist:
  ✓ All phases completed
  ✓ Release successful
  ✓ Documentation updated

  ✓ PROJECT COMPLETE

                                                    ▪▪▪ CLOSEOUT ▪▪▪
```

=========================================
## CONSISTENCY SUMMARY
=========================================

All inconsistencies have been resolved:

### Task Type Patterns (Now Consistent)

| Task Type | h1 | h2 | entry | close | flow | wkflw | agent_sel | agent_ex | audit | approv | gate | menu | custom |
|-----------|----|----|-------|-------|------|-------|-----------|----------|-------|--------|------|------|--------|
| Entry (x01) | yes | no | yes | no | yes | no | no | no | no | yes | no | no | no |
| Agent Selection | no | yes | no | no | yes | yes | yes | yes | no | no | no | yes | yes |
| Phase Audit | no | yes | no | no | no | no | no | no | yes | yes | no | yes | no |
| Human Gate | yes | yes | no | no | no | no | no | no | no | yes | yes | no | no |
| Closeout | no | no | no | yes | no | no | no | no | no | yes | no | no | no |
| Execution | no | yes | no | no | * | * | * | yes | no | no | no | * | * |

### Key Fixes Applied

1. **Task 007**: Renamed "Agent Repository" → "Repository Setup" (clones both agents and audits repos)
2. **Task 008**: Removed closeout_banner (now just environment check)
3. **Task 009**: Added as Phase 0 Closeout
4. **Task 106**: Renamed "Discovery Work" → "Approach Deliberation" (multi-agent deliberation)
5. **Task 107**: Renamed "Approach Selection" → "Direction Confirmation" (human gate)
6. **Phase 2 reordered**: 207 is now Phase Audit, 208 is now PRD Approval (audit before approval)
7. **Phase 7 reordered**: 705 is now Phase Audit, 706 is now Integration Approval (audit before approval)
8. **All Agent Selection tasks**: Now have agent_execution=yes, workflow_diagrams=yes
9. **All Human Gate tasks** (003, 208, 706, 805, 905): Now have h1_header=yes
10. **All Closeout tasks**: Now have approval_checklist=yes
11. **All Execution tasks**: Now have md_output=yes

### Total Tasks: 67

- Phase 0: 9 tasks (001-009)
- Phase 1: 10 tasks (101-110)
- Phase 2: 9 tasks (201-209)
- Phase 3: 6 tasks (301-306)
- Phase 4: 6 tasks (401-406)
- Phase 5: 7 tasks (501-507)
- Phase 6: 6 tasks (601-606)
- Phase 7: 7 tasks (701-707)
- Phase 8: 6 tasks (801-806)
- Phase 9: 6 tasks (901-906)
