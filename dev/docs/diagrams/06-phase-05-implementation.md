# Phase 5: Implementation

Stack-aware parallel TDD execution engine with DAG-ordered waves, pilot batches, and token budget tracking.

```mermaid
flowchart TB
    subgraph t501["Task 501: Entry & Initialization"]
        t501a["Validate Phase 4 closeout"]
        t501b["Verify TDD subtasks exist"]
        t501c["Initialize .claude/testing/"]
        t501a --> t501b --> t501c
    end

    subgraph t502["Task 502: TDD Setup"]
        t502a["Detect tech stack<br/>(filesystem → PRD → spec → user)"]
        t502b["Configure coverage targets"]
        t502c["Set test pyramid ratios"]
        t502a --> t502b --> t502c
    end

    t503["Task 503: Agent Selection<br/>RED: test-strategist<br/>GREEN: tdd-implementation<br/>REFACTOR: code-review-gate<br/>VERIFY: plan-guardian"]

    subgraph t504["Task 504: TDD Execution"]
        pilot["Pilot batch (2-3 root tasks)"]
        pilot -->|"pass"| dag["DAG-ordered wave execution"]

        subgraph cycle["Per-Task TDD Cycle"]
            red["RED: Write failing tests"]
            green["GREEN: Minimal implementation"]
            refactor["REFACTOR: Lint + clean"]
            verify["VERIFY: Security scan"]
            red -->|"gate: compile"| green
            green -->|"gate: tests pass"| refactor
            refactor -->|"gate: lint clean"| verify
        end

        dag --> cycle
    end

    subgraph t505["Task 505: Validation"]
        t505a["Aggregate TDD records"]
        t505b["Run test suite"]
        t505c["Measure coverage"]
        t505d["Security summary"]
        t505a --> t505b --> t505c --> t505d
    end

    t506["Task 506: Phase Audit"]
    t507["Task 507: Closeout"]

    t501 --> t502 --> t503 --> t504 --> t505 --> t506 --> t507

    specs[(".openspec/spec-t*.json")] -->|"test strategy"| t504
    tasks[(".taskmaster/tasks/tasks.json")] -->|"task DAG"| t504
    t504 -->|"tdd-t*.json<br/>test + impl files"| testing[(".claude/testing/")]
    t505 -->|"validation-report.json"| out1[(".outputs/5-implementation/")]

    out1 -->|"closeout.json"| next["Phase 6: Code Review"]

    llm1["LLM: opus<br/>(RED, GREEN,<br/>REFACTOR, VERIFY)"] -.-> t504
    budget["Token Budget<br/>tracking"] -.-> t504
    registry["ProjectSourceRegistry<br/>(dependency code)"] -.-> t504

    human1(["Human Gate:<br/>Impl Review"]) -.-> t507
    human2(["Human: pilot approval"]) -.-> t504
    human3(["Human: budget confirm"]) -.-> t504

    style human1 fill:#FFD700
    style human2 fill:#FFD700
    style human3 fill:#FFD700
    style llm1 fill:#98FB98
```

## Execution Strategy

1. **Pilot batch**: Run 2-3 root tasks first. If >50% fail, pause for review.
2. **DAG waves**: Tasks grouped by dependency level, parallel within each wave.
3. **Token budget**: Tracks cumulative spend, pauses before exceeding configured limit.
4. **Failure handling**: Per-task retry (max 3), cascading failure tracking.

## Stack Profiles

| Stack | Test Framework | Lint | Security | File Pattern |
|-------|---------------|------|----------|-------------|
| Python | pytest | py_compile | py_compile | `test_task_{id}.py` |
| Rust | cargo test | cargo clippy | cargo audit | `test_task_{id}.rs` |
| Node | jest | eslint | npm audit | `test_task_{id}.test.js` |
| Go | go test | go vet | go vet | `task_{id}_test.go` |

## Task Classification

- **bootstrap**: Project scaffold, CI setup (no deps, run first)
- **library**: Foundational types/traits (other tasks import these)
- **feature**: Application logic (typical tasks)
