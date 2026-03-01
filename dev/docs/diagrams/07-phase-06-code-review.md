# Phase 6: Code Review

Four-dimensional code review (code, architecture, performance, documentation) with LLM-driven fix generation.

```mermaid
flowchart TB
    subgraph t601["Task 601: Entry & Initialization"]
        t601a["Validate Phase 5 closeout"]
    end

    subgraph t602["Task 602: Agent Selection"]
        t602a["Select review agents:<br/>deep reviewer (opus/sonnet)<br/>arch compliance (sonnet)<br/>perf analyzer (sonnet/haiku)<br/>doc reviewer (haiku)<br/>code refiner (opus)"]
    end

    subgraph t603["Task 603: Comprehensive Review"]
        r1["Deep Code Review"]
        r2["Architecture Review"]
        r3["Performance Review"]
        r4["Documentation Review"]
        r1 & r2 & r3 & r4 -->|"parallel via<br/>TeamSession"| findings["findings.json"]
    end

    subgraph t604["Task 604: Refinement"]
        t604a["Human selects scope:<br/>critical / major / minor / all"]
        t604b["Per-finding LLM fix generation"]
        t604c["Run project tests"]
        t604a -->|"sonnet"| t604b --> t604c
    end

    t605["Task 605: Phase Audit"]

    subgraph t606["Task 606: Closeout"]
        t606a["Memory save:<br/>critical/major counts,<br/>test status"]
    end

    t601 --> t602 --> t603 --> t604 --> t605 --> t606

    src["Host project source<br/>(up to 50 files)"] -->|"input"| t603
    specs[(".openspec/spec-t*.json")] -->|"constraints"| t603
    t603 -->|"findings.json<br/>review-report.md"| out1[(".claude/reviews/")]
    t604 -->|"refinement-report.json"| out1

    out1 -->|"closeout.json"| next["Phase 7: Integration"]

    llm1["LLM: sonnet + haiku<br/>(4 parallel reviews)"] -.-> t603
    llm2["LLM: sonnet<br/>(per-finding fixes)"] -.-> t604

    human1(["Human: refinement scope"]) -.-> t604
    human2(["Human: approve closeout"]) -.-> t606

    style human1 fill:#FFD700
    style human2 fill:#FFD700
    style llm1 fill:#98FB98
    style llm2 fill:#98FB98
```

## Review Dimensions

| Dimension | Model | Focus |
|-----------|-------|-------|
| Deep Code | sonnet | Logic, correctness, patterns, error handling |
| Architecture | sonnet | Consistency with design, coupling, separation |
| Performance | haiku | Bottlenecks, memory, algorithmic complexity |
| Documentation | haiku | Coverage, accuracy, API docs |

## Finding Severity

Findings are categorized: **critical** > **major** > **minor** > **suggestions**.
Human chooses which severity levels to fix in Task 604.
