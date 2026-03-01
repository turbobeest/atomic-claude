# Phase 4: Specification

OpenSpec generation for each task and TDD subtask injection (RED/GREEN/REFACTOR/VERIFY).

```mermaid
flowchart TB
    subgraph t401["Task 401: Entry & Initialization"]
        t401a["Validate Phase 3 closeout"]
        t401b["Initialize .openspec/ directory"]
        t401a --> t401b
    end

    t402["Task 402: Agent Selection<br/>specification-agent,<br/>tdd-implementation-agent"]

    subgraph t403["Task 403: OpenSpec Generation"]
        t403a["Load tasks + project context"]
        t403b["Parallel LLM generation<br/>(5 concurrent workers)"]
        t403c["Write .openspec/spec-t*.json"]
        t403a -->|"opus"| t403b --> t403c
    end

    subgraph t404["Task 404: TDD Subtask Injection"]
        t404a["Backup tasks.json"]
        t404b["Per-task LLM enrichment<br/>(5 concurrent workers)"]
        t404c["Inject RED/GREEN/<br/>REFACTOR/VERIFY subtasks"]
        t404a -->|"opus"| t404b --> t404c
    end

    t405["Task 405: Phase Audit"]
    t406["Task 406: Closeout"]

    t401 --> t402 --> t403 --> t404 --> t405 --> t406

    tasks[(".taskmaster/tasks/tasks.json")] -->|"input"| t403
    tasks -->|"input"| t404
    t403 -->|"spec-t*.json"| specs[(".openspec/")]
    specs -->|"context"| t404
    t404 -->|"updated tasks.json<br/>(with subtasks)"| tasks2[(".taskmaster/tasks/")]

    tasks2 --> next["Phase 5: Implementation"]
    specs --> next

    llm1["LLM: opus<br/>(5 concurrent)"] -.-> t403
    llm2["LLM: opus<br/>(5 concurrent)"] -.-> t404
    graph1[("Knowledge Graph<br/>spec nodes")] -.-> t403

    style llm1 fill:#98FB98
    style llm2 fill:#98FB98
    style graph1 fill:#DDA0DD
```

## OpenSpec Format

```json
{
  "spec_id": "SPEC-T1",
  "task_id": 1,
  "test_strategy": {
    "unit_tests": [{"name": "test_...", "description": "..."}],
    "integration_tests": [...],
    "scenarios": [{"given": "...", "when": "...", "then": "..."}]
  },
  "interfaces": {
    "inputs": [{"name": "...", "type": "...", "required": true}],
    "outputs": [{"name": "...", "type": "..."}],
    "errors": [{"code": "ERR_001", "condition": "..."}]
  },
  "edge_cases": [{"scenario": "...", "expected_behavior": "..."}],
  "security_requirements": [{"requirement": "...", "validation": "..."}]
}
```

## TDD Subtask Chain

Each task receives 4 ordered subtasks:

```
RED: Write failing tests     (deps: [])
  → GREEN: Minimal impl       (deps: [RED])
    → REFACTOR: Clean up       (deps: [GREEN])
      → VERIFY: Security scan  (deps: [REFACTOR])
```
