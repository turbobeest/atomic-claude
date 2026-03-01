# Phase 7: Integration

Integration testing, acceptance validation, and human approval.

```mermaid
flowchart TB
    subgraph t701["Task 701: Entry & Initialization"]
        t701a["Validate Phase 6 closeout"]
        t701b["Check review artifacts"]
        t701a --> t701b
    end

    subgraph t702["Task 702: Integration Setup"]
        t702a["Configure test environment"]
        t702b["Define acceptance criteria"]
        t702a --> t702b
    end

    t703["Task 703: Agent Selection<br/>E2E test runner (sonnet)<br/>acceptance validator (sonnet)<br/>perf tester (haiku)<br/>integration reporter (haiku)"]

    subgraph t704["Task 704: Testing Execution"]
        t704a["E2E test suite"]
        t704b["Acceptance tests"]
        t704c["Performance tests"]
        t704a & t704b & t704c --> t704d["Aggregate results"]
    end

    subgraph t705["Task 705: Integration Approval"]
        t705a["Review test results"]
        t705b["Approve / investigate /<br/>fix-and-rerun"]
        t705a --> t705b
    end

    t706["Task 706: Phase Audit"]
    t707["Task 707: Closeout"]

    t701 --> t702 --> t703 --> t704 --> t705 --> t706 --> t707

    t702 -->|"integration-setup.json"| out1[(".outputs/7-integration/")]
    t704 -->|"integration-test-results.json"| out1
    t705 -->|"approval.json"| approval[(".claude/integration/")]

    out1 -->|"closeout.json"| next["Phase 8: Deployment Prep"]

    human1(["Human: acceptance criteria"]) -.-> t702
    human2(["Human: approve / investigate"]) -.-> t705
    human3(["Human: approve closeout"]) -.-> t707

    style human1 fill:#FFD700
    style human2 fill:#FFD700
    style human3 fill:#FFD700
```

## Test Suites

| Suite | Scope | Metric |
|-------|-------|--------|
| E2E | Full user flows | tests passed / total |
| Acceptance | Business requirements | criteria met / total |
| Performance | Load and response time | within thresholds |
