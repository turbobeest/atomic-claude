# Pipeline Overview

10-phase SDLC pipeline with sequential dependency gates and human checkpoints.

```mermaid
flowchart TB
    entry["main.py<br/>(CLI Entry)"] --> pipeline["PhasePipeline<br/>orchestration/pipeline.py"]

    pipeline --> p0

    subgraph phases["Phases (sequential, closeout-gated)"]
        p0["Phase 0: Setup<br/>5 tasks"]
        p1["Phase 1: Discovery<br/>9 tasks"]
        p2["Phase 2: PRD<br/>10 tasks"]
        p3["Phase 3: Tasking<br/>6 tasks"]
        p4["Phase 4: Specification<br/>6 tasks"]
        p5["Phase 5: Implementation<br/>7 tasks"]
        p6["Phase 6: Code Review<br/>6 tasks"]
        p7["Phase 7: Integration<br/>7 tasks"]
        p8["Phase 8: Deployment Prep<br/>7 tasks"]
        p9["Phase 9: Release<br/>6 tasks"]

        p0 -->|"closeout.json"| p1
        p1 -->|"closeout.json"| p2
        p2 -->|"closeout.json"| p3
        p3 -->|"closeout.json"| p4
        p4 -->|"closeout.json"| p5
        p5 -->|"closeout.json"| p6
        p6 -->|"closeout.json"| p7
        p7 -->|"closeout.json"| p8
        p8 -->|"closeout.json"| p9
    end

    subgraph gates["Human Gates"]
        g0{{"Gate: Setup Review"}}
        g2{{"Gate: PRD Approval"}}
        g5{{"Gate: Impl Review"}}
        g9{{"Gate: Release Sign-off"}}
    end

    p0 -.-> g0 -.-> p1
    p2 -.-> g2 -.-> p3
    p5 -.-> g5 -.-> p6
    p9 -.-> g9

    subgraph core["Core Systems (shared)"]
        state[("StateManager<br/>.state/task-state.json")]
        memory[("Memory System<br/>.state/memory/")]
        llm["LLM Router<br/>claude-code → anthropic<br/>→ bedrock → ollama"]
        audit["Audit Framework<br/>43 categories"]
        dashboard["Dashboard<br/>localhost:5174"]
    end

    p0 -.-> state
    p0 -.-> memory
    p0 -.-> llm
    p0 -.-> audit
    p0 -.-> dashboard
```

## Phase Transition Rules

- Each phase produces a `closeout.json` that the next phase validates on entry
- Human gates force interactive approval before proceeding
- `python main.py backtrack <phase> [task]` restores state snapshots
- Transition modes: AUTO (chain), PROMPT (ask), MANUAL (explicit)

## Artifact Flow Across Phases

```
Phase 0  →  project-config.json, provider-inventory.json, material-manifest.json
Phase 1  →  corpus-analysis.md, selected-approach.json, diagrams/
Phase 2  →  docs/prd/PRD.md (15 sections), prd-validation.json
Phase 3  →  .taskmaster/tasks/tasks.json, work-packages.json, dependency-graph.json
Phase 4  →  .openspec/spec-t*.json, tasks.json (with TDD subtasks)
Phase 5  →  test files, implementation files, tdd-progress.json, validation-report.json
Phase 6  →  findings.json, refinement-report.json, review-report.md
Phase 7  →  integration-test-results.json, approval.json
Phase 8  →  artifacts.json (changelog, docs, install guide), approval.json
Phase 9  →  announcement.md, execution.json, confirmation.json → PROJECT COMPLETE
```
