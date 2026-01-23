# Phase 1: Ideation - Complete UX Walkthrough

## Reversibility Architecture

The pipeline now supports **task-level state persistence**, meaning:

1. **Resume from any task**: `./run.sh --resume-at 105`
2. **Reset and redo**: `./run.sh --reset-from 106`
3. **Force full redo**: `./run.sh --redo`
4. **Check status**: `./run.sh --status`
5. **Mid-session jump**: Press `[j]` after any task to jump to another

### State File: `.claude/task-state.json`

```json
{
  "version": "1.0",
  "current_phase": "1-ideation",
  "current_task": null,
  "phases": {
    "1-ideation": {
      "started_at": "2024-01-15T10:30:00Z",
      "tasks": {
        "101": { "status": "complete", "completed_at": "..." },
        "102": { "status": "complete", "completed_at": "..." },
        "103": { "status": "complete", "completed_at": "..." },
        "104": { "status": "in_progress", "started_at": "..." }
      },
      "completed": false
    }
  }
}
```

---

## Phase 1 Flow Diagram

```
                    ┌─────────────────────────────────────┐
                    │         PHASE 1: IDEATION           │
                    │   Corpus → Dialogue → Agents →      │
                    │   Ideation → Roster → Closeout      │
                    └─────────────────────────────────────┘
                                     │
     ┌───────────────────────────────┼───────────────────────────────┐
     │                               │                               │
     ▼                               ▼                               ▼
┌─────────┐                    ┌─────────┐                    ┌─────────┐
│  CONV 1 │                    │  CONV 2 │                    │  CONV 3 │
│ Corpus  │───────────────────▶│Dialogue │───────────────────▶│ Agents  │
└─────────┘                    └─────────┘                    └─────────┘
     │                               │                               │
   101-103                         104                             105
     │                               │                               │
     └───────────────────────────────┼───────────────────────────────┘
                                     │
                                     ▼
                              ┌─────────────┐
                              │  IDEATION   │
                              │    WORK     │
                              │     106     │
                              └──────┬──────┘
                                     │
                    ╔════════════════╧════════════════╗
                    ║      HUMAN GATE: APPROACH       ║
                    ║           SELECTION             ║
                    ║             107                 ║
                    ╚════════════════╤════════════════╝
                                     │
                              ┌──────┴──────┐
                              │   ROSTER    │
                              │  PLANNING   │
                              │     108     │
                              └──────┬──────┘
                                     │
                    ╔════════════════╧════════════════╗
                    ║      HUMAN GATE: ROSTER         ║
                    ║          APPROVAL               ║
                    ║             109                 ║
                    ╚════════════════╤════════════════╝
                                     │
                    ┌────────────────┴────────────────┐
                    │                                 │
                    ▼                                 ▼
             ┌─────────────┐                  ┌─────────────┐
             │   CUSTOM    │                  │   PHASE     │
             │   AGENTS    │─────────────────▶│   AUDIT     │
             │  110 (opt)  │                  │    111      │
             └─────────────┘                  └──────┬──────┘
                                                     │
                                              ┌──────┴──────┐
                                              │  CLOSEOUT   │
                                              │     112     │
                                              └──────┬──────┘
                                                     │
                                                     ▼
                                            [ PHASE 2: DISCOVERY ]
```

---

## Step-by-Step Walkthrough

### Launch

```bash
cd /path/to/ATOMIC-CLAUDE
./phases/1-ideation/run.sh
```

**First-time run:**
```
╔════════════════════════════════════════════════════════════╗
║  PHASE 1: IDEATION                    [ProjectName]        ║
╚════════════════════════════════════════════════════════════╝
  Phase ID: 1-ideation
  Started: Mon Jan 15 10:30:00 UTC 2024
```

**Resume run (tasks 101-103 complete):**
```
╔════════════════════════════════════════════════════════════╗
║  PHASE 1: IDEATION                    [ProjectName]        ║
╚════════════════════════════════════════════════════════════╝
  Phase ID: 1-ideation
  Started: Mon Jan 15 10:35:00 UTC 2024
  Last completed: Task 103
```

---

### Task 101: Entry Validation

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ TASK 101: Entry Validation                                  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

  ┌─────────────────────────────────────────────────────────┐
  │ PHASE ENTRY VALIDATION                                  │
  │                                                         │
  │ Checking prerequisites before starting Ideation phase. │
  └─────────────────────────────────────────────────────────┘

  Checking prerequisites...
  ✓ Phase 0 closeout found
  ✓ Project configuration valid
  ✓ Pipeline state initialized

  WELCOME TO PHASE 1: IDEATION

  ╔═══════════════════════════════════════════════════════════╗
  ║ In this phase we will:                                    ║
  ║                                                           ║
  ║  1. Collect and organize project materials (Corpus)       ║
  ║  2. Understand your vision and constraints (Dialogue)     ║
  ║  3. Select agents for the pipeline (Agent Selection)      ║
  ║  4. Generate solution approaches (Ideation Work)          ║
  ║  5. Get your approval on direction (Approach Gate)        ║
  ║  6. Plan agent roster for phases 2-12 (Roster Planning)   ║
  ║  7. Get your approval on roster (Roster Gate)             ║
  ║  8. Conduct phase audit (Audit)                           ║
  ║  9. Close out and prepare for Discovery (Closeout)        ║
  ╚═══════════════════════════════════════════════════════════╝

  Press Enter to begin...

✓ Task completed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [c] Continue    [r] Redo    [b] Go back    [j] Jump to    [q] Quit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Choice [c]: _
```

**Navigation Options:**
- `c` (default): Continue to Task 102
- `r`: Redo Task 101
- `b`: Go back (at first task, shows "Already at first task")
- `j`: Jump to any task (e.g., type `105` to skip ahead)
- `q`: Quit phase (can resume later)

---

### Task 102: Corpus Collection

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CONVERSATION 1: CORPUS COLLECTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ TASK 102: Corpus Collection                                 ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

  ┌─────────────────────────────────────────────────────────┐
  │ CORPUS COLLECTION                                       │
  │                                                         │
  │ We'll gather all project materials: docs, specs, PRDs, │
  │ links, and any relevant context for ideation.          │
  └─────────────────────────────────────────────────────────┘

╔═══════════════════════════════════════════════════════════╗
║ STEP 1: SCAN FOR EXISTING MATERIALS                        ║
╚═══════════════════════════════════════════════════════════╝

  Scanning project for existing materials...

  Found in docs/:
    README.md
    architecture/overview.md
    requirements/initial-brief.md

  Found in project root:
    PRD.md
    SPEC.md

  Total materials found: 5

╔═══════════════════════════════════════════════════════════╗
║ STEP 2: REQUEST ADDITIONAL MATERIALS                        ║
╚═══════════════════════════════════════════════════════════╝

  Do you have additional materials to add?

  You can provide:
    • File paths (e.g., /path/to/design-doc.pdf)
    • URLs (e.g., https://notion.so/project-brief)
    • Descriptions (e.g., "Competitor analysis we discussed")

  Enter material (or 'done'): https://notion.so/project-requirements
  ✓ Added: https://notion.so/project-requirements

  Enter material (or 'done'): done

╔═══════════════════════════════════════════════════════════╗
║ STEP 3: ANALYZE MATERIALS                                   ║
╚═══════════════════════════════════════════════════════════╝

  Analyzing corpus for key themes and patterns...
  [ideation-facilitator working...]

  Key themes identified:
    • Authentication system modernization
    • Multi-tenant architecture
    • API-first design
    • Performance requirements (sub-100ms)

╔═══════════════════════════════════════════════════════════╗
║ STEP 4: REFLECT ON CORPUS                                   ║
╚═══════════════════════════════════════════════════════════╝

  Corpus Summary:
  ─────────────────────────────────────────────────────────
  Materials collected:     6
  Key themes:              4
  Potential approaches:    3 (preliminary)
  ─────────────────────────────────────────────────────────

  Does this corpus feel complete, or is something missing?

    [complete] The corpus is sufficient
    [add]      I have more to add
    [discuss]  Let's discuss what's missing

  Choice [complete]: _

╔═══════════════════════════════════════════════════════════╗
║ STEP 5: ORGANIZE CORPUS                                     ║
╚═══════════════════════════════════════════════════════════╝

  ✓ Generated: docs/corpus/CORPUS-INDEX.md
  ✓ Generated: output/1-ideation/corpus.json

✓ Task completed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [c] Continue    [r] Redo    [b] Go back    [j] Jump to    [q] Quit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Choice [c]: _
```

---

### Task 103: Sphinx-Needs (Optional)

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ TASK 103: Sphinx-Needs                                      ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

  ┌─────────────────────────────────────────────────────────┐
  │ SPHINX-NEEDS PARSING (Optional)                         │
  │                                                         │
  │ If your project uses Sphinx with needs directives,     │
  │ we can extract requirements, specs, and tests.         │
  └─────────────────────────────────────────────────────────┘

  Does your project use Sphinx-Needs? [y/N]: n

  ℹ Skipping Sphinx-Needs parsing

✓ Task completed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [c] Continue    [r] Redo    [b] Go back    [j] Jump to    [q] Quit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Choice [c]: _
```

---

### Task 104: Opening Dialogue

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CONVERSATION 2: OPENING DIALOGUE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ TASK 104: Opening Dialogue                                  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

  ┌─────────────────────────────────────────────────────────┐
  │ OPENING DIALOGUE                                        │
  │                                                         │
  │ Let's understand your vision, constraints, and what    │
  │ success looks like for this project.                   │
  └─────────────────────────────────────────────────────────┘

╔═══════════════════════════════════════════════════════════╗
║ STEP 1: OPENING REMARKS                                     ║
╚═══════════════════════════════════════════════════════════╝

  [ideation-facilitator reviewing corpus...]

  Based on the materials collected, here's what I understand:

  ─────────────────────────────────────────────────────────
  You're building a modern authentication system that needs to:
  - Support multi-tenant SaaS architecture
  - Provide sub-100ms response times
  - Integrate with existing OAuth2/OIDC providers
  ─────────────────────────────────────────────────────────

  Does this summary capture the essence? [Y/n]: Y

╔═══════════════════════════════════════════════════════════╗
║ STEP 2: BUILD CONSENSUS                                     ║
╚═══════════════════════════════════════════════════════════╝

  Let me understand the core vision better.

  What is the PRIMARY impact you want this project to have?
  > Replace legacy auth system, reduce login friction by 50%

  Who is the TARGET AUDIENCE?
  > Enterprise customers with 1000+ users

  What does SUCCESS look like in 6 months?
  > Zero legacy auth dependencies, all tenants migrated

  What is absolutely NON-NEGOTIABLE?
  > Security - no regression in security posture

╔═══════════════════════════════════════════════════════════╗
║ STEP 3: GATHER CONSTRAINTS                                  ║
╚═══════════════════════════════════════════════════════════╝

  Now let's capture the constraints we're working with.

  Tech Stack (comma-separated):
  > Python, FastAPI, PostgreSQL, Redis

  Budget Tier:
    [1] Bootstrap (minimal resources)
    [2] Startup (moderate)
    [3] Enterprise (well-resourced)
  > 2

  Timeline:
    [1] Weeks (prototype/MVP)
    [2] Months (full product)
    [3] Quarters (major platform)
  > 2

  Team Size:
  > 4 developers

  Compliance Requirements (comma-separated, or 'none'):
  > SOC2, GDPR

  ✓ Constraints captured

╔═══════════════════════════════════════════════════════════╗
║ STEP 4: DIALOGUE SUMMARY                                    ║
╚═══════════════════════════════════════════════════════════╝

  ✓ Generated: output/1-ideation/dialogue.json

  Summary:
  ─────────────────────────────────────────────────────────
  Vision:     Modern auth system for enterprise SaaS
  Impact:     50% reduction in login friction
  Timeline:   Months
  Team:       4 developers
  Compliance: SOC2, GDPR
  ─────────────────────────────────────────────────────────

✓ Task completed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [c] Continue    [r] Redo    [b] Go back    [j] Jump to    [q] Quit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Choice [c]: _
```

---

### Task 105: Agent Selection

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CONVERSATION 3: AGENT SELECTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ TASK 105: Agent Selection                                   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

  ┌─────────────────────────────────────────────────────────┐
  │ AGENT SELECTION                                         │
  │                                                         │
  │ Choose which specialized agents will work on this      │
  │ project throughout the pipeline.                       │
  └─────────────────────────────────────────────────────────┘

╔═══════════════════════════════════════════════════════════╗
║ CORE AGENTS (Always Active)                                 ║
╚═══════════════════════════════════════════════════════════╝

  These agents are always part of the pipeline:

    ✓ ideation-facilitator    Guides brainstorming and approach generation
    ✓ first-principles-analyst Challenges assumptions, validates reasoning
    ✓ decision-synthesizer     Consolidates options into recommendations

╔═══════════════════════════════════════════════════════════╗
║ SUGGESTED AGENTS                                            ║
╚═══════════════════════════════════════════════════════════╝

  Based on your tech stack (Python, FastAPI) and compliance (SOC2, GDPR):

    [1] python-architect      Deep Python ecosystem knowledge
    [2] api-designer          REST/GraphQL API design patterns
    [3] security-reviewer     Security analysis, compliance checks
    [4] database-specialist   PostgreSQL optimization, schema design

  How would you like to proceed?

    [accept]  Accept all suggested agents
    [select]  Select specific agents by number
    [manual]  Enter agent names manually
    [skip]    Use only core agents

  Choice [accept]: accept

  ✓ Selected 7 agents for pipeline

╔═══════════════════════════════════════════════════════════╗
║ SELECTED AGENTS                                             ║
╚═══════════════════════════════════════════════════════════╝

  Core:
    • ideation-facilitator
    • first-principles-analyst
    • decision-synthesizer

  Specialized:
    • python-architect
    • api-designer
    • security-reviewer
    • database-specialist

  ✓ Generated: output/1-ideation/selected-agents.json

✓ Task completed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [c] Continue    [r] Redo    [b] Go back    [j] Jump to    [q] Quit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Choice [c]: _
```

---

### Task 106: Ideation Work

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  IDEATION WORK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ TASK 106: Ideation Work                                     ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

  ┌─────────────────────────────────────────────────────────┐
  │ IDEATION WORK                                           │
  │                                                         │
  │ Generate and analyze solution approaches based on      │
  │ corpus, dialogue, and selected agents.                 │
  └─────────────────────────────────────────────────────────┘

╔═══════════════════════════════════════════════════════════╗
║ CONTEXT SUMMARY                                             ║
╚═══════════════════════════════════════════════════════════╝

  Project:     Modern Auth System
  Vision:      50% reduction in login friction
  Tech Stack:  Python, FastAPI, PostgreSQL, Redis
  Constraints: SOC2, GDPR, 4 developers, months timeline
  Agents:      7 selected (3 core + 4 specialized)

╔═══════════════════════════════════════════════════════════╗
║ APPROACH GENERATION                                         ║
╚═══════════════════════════════════════════════════════════╝

  How many approaches should we generate?
    [3] Quick exploration (recommended)
    [5] Thorough exploration
    [7] Exhaustive exploration

  Choice [3]: 3

  [ideation-facilitator generating approaches...]
  [first-principles-analyst validating assumptions...]

╔═══════════════════════════════════════════════════════════╗
║ GENERATED APPROACHES                                        ║
╚═══════════════════════════════════════════════════════════╝

  APPROACH 1: OAuth2/OIDC Native
  ─────────────────────────────────────────────────────────
  Build directly on OAuth2/OIDC standards using existing
  libraries (authlib, python-jose).

  Pros:  Standard compliance, proven patterns
  Cons:  Limited customization, vendor lock-in risk
  Risk:  Medium
  Effort: 2-3 months

  APPROACH 2: Custom Token Service
  ─────────────────────────────────────────────────────────
  Build custom JWT/session management with flexible
  multi-tenant isolation.

  Pros:  Full control, optimized for use case
  Cons:  Security expertise required, more testing
  Risk:  High
  Effort: 4-5 months

  APPROACH 3: Hybrid Gateway
  ─────────────────────────────────────────────────────────
  API gateway handling auth with tenant-aware routing
  and session management.

  Pros:  Separation of concerns, scalable
  Cons:  Additional infrastructure, latency
  Risk:  Medium
  Effort: 3-4 months

  ✓ Generated: output/1-ideation/approaches.json

╔═══════════════════════════════════════════════════════════╗
║ FIRST PRINCIPLES ANALYSIS                                   ║
╚═══════════════════════════════════════════════════════════╝

  [first-principles-analyst challenging assumptions...]

  Core Questions:
  ─────────────────────────────────────────────────────────
  1. Is a custom solution necessary, or can managed auth
     (Auth0, Cognito) meet requirements?

  2. Is sub-100ms achievable with external IdP calls?

  3. Are all tenants similar enough for shared auth logic?

  Recommendation:
  ─────────────────────────────────────────────────────────
  Approach 1 (OAuth2/OIDC Native) best balances:
  - Security compliance (SOC2/GDPR)
  - Team expertise
  - Timeline constraints

  Suggest: Prototype managed auth before building custom.

  ✓ Generated: output/1-ideation/first-principles.json

✓ Task completed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [c] Continue    [r] Redo    [b] Go back    [j] Jump to    [q] Quit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Choice [c]: _
```

---

### Task 107: Approach Selection (HUMAN GATE)

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ TASK 107: Approach Selection                                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║  🛑 HUMAN GATE: APPROACH SELECTION                        ║
║                                                           ║
║  You must select which approach to pursue.                ║
║  This decision shapes the entire project.                 ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

╔═══════════════════════════════════════════════════════════╗
║ APPROACH SUMMARY                                            ║
╚═══════════════════════════════════════════════════════════╝

  ID   Approach              Risk    Effort
  ─────────────────────────────────────────────────
  1    OAuth2/OIDC Native    Medium  2-3 months  ★ Recommended
  2    Custom Token Service  High    4-5 months
  3    Hybrid Gateway        Medium  3-4 months

  First Principles Recommendation: Approach 1

╔═══════════════════════════════════════════════════════════╗
║ YOUR SELECTION                                              ║
╚═══════════════════════════════════════════════════════════╝

  How would you like to proceed?

    [1-3]     Select approach by ID
    [refine]  Request refinement of an approach
    [combine] Combine elements of multiple approaches
    [other]   Describe a different approach

  Selection: 1

  You selected: Approach 1 - OAuth2/OIDC Native

  Confirm selection? [Y/n]: Y

  ✓ Approach selected: OAuth2/OIDC Native
  ✓ Generated: output/1-ideation/selected-approach.json

✓ Task completed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [c] Continue    [r] Redo    [b] Go back    [j] Jump to    [q] Quit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Choice [c]: _
```

---

### Task 108: Roster Planning

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  AGENT ROSTER PLANNING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ TASK 108: Roster Planning                                   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

  ┌─────────────────────────────────────────────────────────┐
  │ ROSTER PLANNING                                         │
  │                                                         │
  │ Assign agents to each phase (2-12) based on the       │
  │ selected approach and project needs.                   │
  └─────────────────────────────────────────────────────────┘

╔═══════════════════════════════════════════════════════════╗
║ SELECTED APPROACH DOCUMENTATION                             ║
╚═══════════════════════════════════════════════════════════╝

  [decision-synthesizer documenting approach...]

  ✓ Generated: output/1-ideation/selected-approach.md

╔═══════════════════════════════════════════════════════════╗
║ PROPOSED AGENT ROSTER                                       ║
╚═══════════════════════════════════════════════════════════╝

  Phase   Name                    Proposed Agent
  ─────────────────────────────────────────────────────────
  2       Discovery               discovery-researcher
  3       PRD Validation          prd-validator
  4       Architecture Design     python-architect
  5       Detailed Design         api-designer
  6       Test Planning           security-reviewer
  7       Implementation          python-architect
  8       Integration Testing     integration-tester
  9       Security Audit          security-reviewer
  10      Documentation           documentation-writer
  11      Deployment Prep         devops-engineer
  12      Retrospective           retrospective-facilitator

╔═══════════════════════════════════════════════════════════╗
║ ROSTER CUSTOMIZATION                                        ║
╚═══════════════════════════════════════════════════════════╝

  Would you like to customize any phase assignments?

    [accept]     Accept proposed roster
    [customize]  Modify specific phases
    [explain]    Explain agent selection rationale

  Choice [accept]: accept

  ✓ Generated: output/1-ideation/agent-roster.json

✓ Task completed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [c] Continue    [r] Redo    [b] Go back    [j] Jump to    [q] Quit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Choice [c]: _
```

---

### Task 109: Roster Approval (HUMAN GATE)

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ TASK 109: Roster Approval                                   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║  🛑 HUMAN GATE: ROSTER APPROVAL                           ║
║                                                           ║
║  Review the agent assignments for each phase.             ║
║                                                           ║
║  REMINDER: The roster is flexible and can be             ║
║  modified throughout the project journey.                 ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

╔═══════════════════════════════════════════════════════════╗
║ AGENT ROSTER FOR PHASES 2-12                                ║
╚═══════════════════════════════════════════════════════════╝

  Phase    Name                     Agent
  ──────── ─────────────────────── ─────────────────────────
  2        Discovery               discovery-researcher
  3        PRD Validation          prd-validator
  4        Architecture Design     python-architect
  5        Detailed Design         api-designer
  6        Test Planning           security-reviewer
  7        Implementation          python-architect
  8        Integration Testing     integration-tester
  9        Security Audit          security-reviewer
  10       Documentation           documentation-writer
  11       Deployment Prep         devops-engineer
  12       Retrospective           retrospective-facilitator

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  [approve]  Approve roster as-is
  [modify]   Modify specific phase assignments
  [discuss]  Add notes for future consideration

  Choice: approve

  ✓ Roster approved

✓ Task completed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [c] Continue    [r] Redo    [b] Go back    [j] Jump to    [q] Quit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Choice [c]: _
```

---

### Task 110: Custom Agents (Optional)

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ TASK 110: Custom Agents                                     ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

  ┌─────────────────────────────────────────────────────────┐
  │ CUSTOM AGENTS (Optional)                                │
  │                                                         │
  │ If the built-in agents don't fit your needs, you can  │
  │ create custom agent definitions for specific roles.    │
  └─────────────────────────────────────────────────────────┘

  Would you like to create custom agents?

  Create custom agents? [y/N]: N

  ℹ Skipping custom agent creation

✓ Task completed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [c] Continue    [r] Redo    [b] Go back    [j] Jump to    [q] Quit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Choice [c]: _
```

---

### Task 111: Phase Audit

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PHASE AUDIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ TASK 111: Phase Audit                                       ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

  ┌─────────────────────────────────────────────────────────┐
  │ PHASE AUDIT (Light - 10 Dimensions)                     │
  │                                                         │
  │ An independent review of Phase 1 outputs to ensure     │
  │ quality and completeness before proceeding.            │
  └─────────────────────────────────────────────────────────┘

╔═══════════════════════════════════════════════════════════╗
║ AUDIT DIMENSION SELECTION                                   ║
╚═══════════════════════════════════════════════════════════╝

  Available Dimensions:

    ID-01: Corpus Completeness
           Are all relevant materials collected?
    ID-02: Vision Clarity
           Is the project vision clear and actionable?
    ID-03: Constraint Definition
           Are constraints well-defined and realistic?
    ID-04: Approach Viability
           Is the selected approach feasible?
    ID-05: First Principles Validity
           Have assumptions been properly challenged?
    ID-06: Stakeholder Coverage
           Are all stakeholders identified?
    ID-07: Risk Awareness
           Are key risks identified and considered?
    ID-08: Agent Alignment
           Are agents appropriate for each phase?
    ID-09: Scope Boundaries
           Are scope boundaries clear?
    ID-10: Success Criteria
           Are success criteria measurable?

  Audit Mode:
    [quick]  Top 5 dimensions (fast)
    [custom] Select specific dimensions
    [all]    All 10 dimensions (thorough)

  Mode [quick]: quick

  ✓ Selected 5 dimensions for audit

╔═══════════════════════════════════════════════════════════╗
║ EXECUTING AUDIT                                             ║
╚═══════════════════════════════════════════════════════════╝

  [ideation-auditor analyzing...]

╔═══════════════════════════════════════════════════════════╗
║ AUDIT FINDINGS                                              ║
╚═══════════════════════════════════════════════════════════╝

  Overall Status: PASS

  PASSED:   4
  WARNINGS: 1
  CRITICAL: 0

  ✓ ID-01: PASS - Corpus complete (6 materials, key themes identified)
  ✓ ID-02: PASS - Vision clear (50% friction reduction, enterprise focus)
  ✓ ID-04: PASS - Approach viable (OAuth2/OIDC fits constraints)
  ! ID-07: WARNING - Risk awareness could be deeper (no explicit risk register)
  ✓ ID-10: PASS - Success criteria measurable (migration metrics defined)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  How would you like to proceed?

    [accept]    Accept findings and continue
    [address]   Address issues before continuing
    [defer]     Defer issues to later phases
    [challenge] Challenge audit findings

  Choice [accept]: defer

  ✓ Issues deferred

✓ Task completed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [c] Continue    [r] Redo    [b] Go back    [j] Jump to    [q] Quit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Choice [c]: _
```

---

### Task 112: Closeout

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PHASE CLOSEOUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ TASK 112: Closeout                                          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

  ┌─────────────────────────────────────────────────────────┐
  │ PHASE CLOSEOUT                                          │
  │                                                         │
  │ Final review before moving to Phase 2 (Discovery).     │
  └─────────────────────────────────────────────────────────┘

╔═══════════════════════════════════════════════════════════╗
║ CLOSEOUT CHECKLIST                                          ║
╚═══════════════════════════════════════════════════════════╝

  [CRIT] ✓ Corpus collected
  [CRIT] ✓ Dialogue completed
  [BLCK] ✓ Agents selected
  [CRIT] ✓ Approaches generated
  [CRIT] ✓ Approach selected
  [CRIT] ✓ Agent roster approved
  [BLCK] ! Audit has warnings
  [PASS] ✓ Ready for Discovery

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Closeout options:

    [approve] Approve closeout and proceed
    [review]  Review specific artifacts
    [hold]    Hold closeout for now

  Choice [approve]: approve

╔═══════════════════════════════════════════════════════════╗
║ GENERATING CLOSEOUT                                         ║
╚═══════════════════════════════════════════════════════════╝

  ✓ Generated phase-01-closeout.md
  ✓ Generated phase-01-closeout.json

╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║  SESSION END                                              ║
║                                                           ║
║  Closeout saved to:                                       ║
║  .claude/closeout/phase-01-closeout.md                    ║
║                                                           ║
║  Next: PHASE 2 - DISCOVERY                                ║
║                                                           ║
║  To continue:                                             ║
║  ./orchestrator/pipeline resume                           ║
║                                                           ║
║  ─────────────────────────────────────────────────────── ║
║                                                           ║
║      Phase 1 Complete!                                    ║
║      Great work. See you in Discovery.                    ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

✓ Phase 1 closeout complete

✓ Task completed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [c] Continue    [r] Redo    [b] Go back    [j] Jump to    [q] Quit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Choice [c]: _
```

---

## Error Recovery Scenarios

### Scenario 1: Session Crashes at Task 106

```bash
# What happened: Power failure during ideation work

# State was saved - tasks 101-105 are complete
cat .claude/task-state.json
# Shows: 101-105 complete, 106 in_progress

# Resume normally - will start at 106
./phases/1-ideation/run.sh

# Output shows:
# Last completed: Task 105
# [COMPLETE - SKIPPED] Task 101, 102, 103, 104, 105
# [RUNNING] Task 106
```

### Scenario 2: Want to Redo Agent Selection

```bash
# Realized wrong agents were selected in task 105
# Need to redo from there

./phases/1-ideation/run.sh --reset-from 105

# Output:
# Reset to task 105 - all subsequent tasks marked pending
# [COMPLETE - SKIPPED] Task 101, 102, 103, 104
# [RUNNING] Task 105
```

### Scenario 3: Jump During Session

```
# Currently at Task 108, but want to go back to 106

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [c] Continue    [r] Redo    [b] Go back    [j] Jump to    [q] Quit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Choice [c]: j

  Enter task ID to jump to (e.g., 101, 105):
  Jump to: 106

  Reset to task 106 - all subsequent tasks marked pending
  ℹ Jumping to task 106...
```

### Scenario 4: Check Status Without Running

```bash
./phases/1-ideation/run.sh --status

# Output:
Task State: Phase 1-ideation
─────────────────────────────────────────────────
  ✓ 101: complete - Entry Validation
  ✓ 102: complete - Corpus Collection
  ✓ 103: complete - Sphinx-Needs
  ✓ 104: complete - Opening Dialogue
  ✓ 105: complete - Agent Selection
  → 106: in_progress - Ideation Work
  ○ 107: pending - Approach Selection
  ○ 108: pending - Roster Planning
  ○ 109: pending - Roster Approval
  ○ 110: pending - Custom Agents
  ○ 111: pending - Phase Audit
  ○ 112: pending - Closeout
```

---

## CLI Reference

### Phase-Level Commands

```bash
# Normal run (resumes from last completed task in this phase)
./phases/1-ideation/run.sh

# Start from specific task within phase
./phases/1-ideation/run.sh --resume-at 106

# Reset tasks from point and run (within phase)
./phases/1-ideation/run.sh --reset-from 105

# Force re-run everything in this phase
./phases/1-ideation/run.sh --redo

# Clear all state for this phase
./phases/1-ideation/run.sh --clear

# Show phase status
./phases/1-ideation/run.sh --status

# Help
./phases/1-ideation/run.sh --help
```

### Pipeline-Level Commands (Cross-Phase)

```bash
# Show full pipeline state across all phases
./pipeline status

# Reset from any task - clears that task + all subsequent phases
./pipeline reset 204    # Reset from Phase 2, Task 04 - clears Phases 3, 4, etc.
./pipeline reset 107    # Reset from Phase 1, Task 07 - clears Phases 2, 3, etc.

# Resume from wherever you left off
./pipeline resume

# Run specific phase
./pipeline run 2        # Run Phase 2
./pipeline run 4        # Run Phase 4
```

### Cross-Phase Reset Example

```
Scenario: You're at Task 405 and realize Task 204 was wrong.

$ ./pipeline reset 204

╔═══════════════════════════════════════════════════════════╗
║ PIPELINE RESET                                            ║
╠═══════════════════════════════════════════════════════════╣
║ Resetting from: Task 204 (Phase 2)                        ║
║                                                           ║
║ This will:                                                ║
║   • Reset Phase 2 from task 204                           ║
║   • Clear ALL phases after Phase 2                        ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

This will reset the pipeline from task 204 forward.
All subsequent tasks and phases will be cleared.

Continue? [y/N]: y

  ✓ Phase 0: Preserved
  ✓ Phase 1: Preserved
  → Phase 2: Resetting from task 204
  ✗ Phase 3: Clearing all tasks
  ✗ Phase 4: Clearing all tasks

  Summary:
    Tasks reset in Phase 2: 5
    Phases cleared: 2

  To continue from task 204:
    ./phases/2-*/run.sh
```

---

## Artifacts Produced

| Task | Artifact | Description |
|------|----------|-------------|
| 102 | `corpus.json` | Collected materials |
| 102 | `docs/corpus/CORPUS-INDEX.md` | Organized corpus index |
| 104 | `dialogue.json` | Opening dialogue capture |
| 105 | `selected-agents.json` | Agents for pipeline |
| 106 | `approaches.json` | Generated approaches |
| 106 | `first-principles.json` | First principles analysis |
| 107 | `selected-approach.json` | Human-selected approach |
| 108 | `selected-approach.md` | Approach documentation |
| 108 | `agent-roster.json` | Agent assignments |
| 110 | `custom-agents.json` | Custom agent definitions (if any) |
| 111 | `phase-01-audit.json` | Audit results |
| 112 | `phase-01-closeout.md` | Phase closeout |
| 112 | `phase-01-closeout.json` | Closeout data |
