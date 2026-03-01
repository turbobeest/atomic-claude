# Phase 3: Tasking

PRD decomposition into atomic tasks with dependency analysis and work package generation.

```mermaid
flowchart TB
    subgraph t301["Task 301: Entry & Initialization"]
        t301a["Validate PRD + Phase 2 closeout"]
        t301b["Initialize .taskmaster/ directory"]
        t301a --> t301b
    end

    subgraph t302["Task 302: Agent Selection"]
        t302a["Analyze PRD for patterns:<br/>API, auth, database, UI"]
        t302b["Select decomposition agents"]
        t302a --> t302b
    end

    subgraph t303["Task 303: Task Decomposition"]
        t303a["Extract PRD sections:<br/>features, NFRs, deps, phases"]
        t303b["Per-feature LLM decomposition<br/>(large PRDs split by feature)"]
        t303c["Merge + renumber tasks"]
        t303a -->|"opus"| t303b --> t303c
    end

    subgraph t304["Task 304: Dependency Analysis"]
        t304a["Validate DAG:<br/>cycles, self-refs, orphans"]
        t304b["Compute execution levels<br/>(topological sort)"]
        t304c["Generate work packages<br/>(parallel waves)"]
        t304a --> t304b --> t304c
    end

    t305["Task 305: Phase Audit"]
    t306["Task 306: Closeout"]

    t301 --> t302 --> t303 --> t304 --> t305 --> t306

    prd[("docs/prd/PRD.md")] -->|"input"| t303
    t303 -->|"tasks.json"| tm[(".taskmaster/tasks/")]
    t304 -->|"dependency-graph.json<br/>work-packages.json"| tmr[(".taskmaster/reports/")]

    tm --> next["Phase 4: Specification"]
    tmr --> next

    llm1["LLM: opus<br/>(decomposition)"] -.-> t303
    graph1[("Knowledge Graph<br/>task nodes")] -.-> t303
    graph1 -.-> t304

    style llm1 fill:#98FB98
    style graph1 fill:#DDA0DD
```

## Task Output Format

```json
{
  "id": 1,
  "title": "F0: Foundation Setup",
  "description": "...",
  "status": "pending",
  "priority": "high|medium|low",
  "category": "infrastructure|feature|testing|documentation|security",
  "dependencies": [2, 3],
  "acceptance_criteria": "...",
  "estimated_complexity": "simple|moderate|complex",
  "prd_section": "Section 3",
  "subtasks": []
}
```

## Work Package Structure

Tasks grouped into parallel execution waves based on dependency levels:

```
Wave 1 (Level 0): [T1, T2, T3]     ← root tasks, no dependencies
Wave 2 (Level 1): [T4, T5, T6, T7] ← depend on Wave 1
Wave 3 (Level 2): [T8, T9]          ← depend on Wave 2
```
