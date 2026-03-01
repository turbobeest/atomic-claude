# Phase 2: PRD

15-section PRD authored in 12 LLM generations with guardian validation, followed by two-pass validation and human approval.

```mermaid
flowchart TB
    subgraph t201["Task 201: Entry Validation"]
        t201a["Load Phase 1 context:<br/>closeout, approach, corpus, dialogue"]
    end

    subgraph t202["Task 202: PRD Setup"]
        t202a["Confirm scope:<br/>full / mvp / component"]
        t202b["Select focus areas:<br/>architecture, api, data,<br/>security, performance, etc."]
        t202a --> t202b
    end

    subgraph t203["Task 203: Interview (optional)"]
        t203a["Gather stakeholders,<br/>success criteria, non-goals,<br/>MVP scope"]
    end

    t204["Task 204: Agent Selection<br/>requirements-engineer,<br/>prd-writer, prd-validator"]

    subgraph t205["Task 205: PRD Authoring"]
        g01["Gen 1: Vision + Executive Summary"]
        g02["Gen 2: Technical Architecture"]
        g03["Gen 3: Feature Requirements"]
        g04["Gen 4: Non-Functional Requirements"]
        g05["Gen 5: Dependency Chain"]
        g06["Gen 6: Development Phases"]
        g07["Gen 7: Code Structure"]
        g08["Gen 8: TDD Strategy"]
        g09["Gen 9: Integration Testing"]
        g10["Gen 10: Documentation Reqs"]
        g11["Gen 11: Operational Reqs"]
        g12["Gen 12: Risks + Metrics + Approval"]

        g01 -->|"prior content"| g02 --> g03 --> g04 --> g05 --> g06
        g06 --> g07 --> g08 --> g09 --> g10 --> g11 --> g12
    end

    subgraph t206["Task 206: PRD Validation"]
        v1["Pass 1: Structural<br/>(15 sections, 100+ lines)"]
        v2["Pass 2: Content<br/>(completeness, testability,<br/>consistency, compatibility)"]
        v1 --> v2
        v2 -->|"FAIL/WARNING"| t206b["Task 206b: Revision<br/>(max 3 iterations)"]
        t206b -->|"re-validate"| v1
    end

    t207["Task 207: PRD Approval"]
    t208["Task 208: Phase Audit"]
    t209["Task 209: Closeout"]

    t201 --> t202 --> t203 --> t204 --> t205 --> t206 --> t207 --> t208 --> t209

    t205 -->|"docs/prd/PRD.md"| prd[("PRD.md<br/>15 sections")]
    t206 -->|"prd-validation.json"| out1[(".outputs/2-prd/")]
    t207 -->|"prd-approved.json"| out1

    out1 -->|"closeout.json"| next["Phase 3: Tasking"]

    llm1["LLM: opus<br/>(12 generations)"] -.-> t205
    llm2["LLM: sonnet<br/>(validation)"] -.-> t206
    graph1[("Knowledge Graph<br/>Features F-1..F-12")] -.-> t205

    human1(["Human Gate:<br/>PRD Approval"]) -.-> t207
    human2(["Human: scope + focus"]) -.-> t202
    human3(["Human: stakeholder input"]) -.-> t203

    style human1 fill:#FFD700
    style human2 fill:#FFD700
    style human3 fill:#FFD700
    style llm1 fill:#98FB98
    style llm2 fill:#98FB98
    style graph1 fill:#DDA0DD
```

## Generation Detail

Each generation receives: project config + PRD setup + interview data + prior sections (capped at 12K chars). Guardian validation between each generation checks structure and content length.

| Gen | Sections | Model |
|-----|----------|-------|
| 1 | Vision, Executive Summary | opus |
| 2 | Technical Architecture | opus |
| 3 | Feature Requirements (FRs) | opus |
| 4 | Non-Functional Requirements (NFRs) | opus |
| 5 | Logical Dependency Chain | opus |
| 6 | Development Phases | opus |
| 7 | Code Structure & Organization | opus |
| 8 | TDD Requirements & Test Strategy | opus |
| 9 | Integration Testing Strategy | opus |
| 10 | Documentation Requirements | opus |
| 11 | Operational Requirements | opus |
| 12 | Risks, Success Metrics, Approval | opus |

## Validation Dimensions

| Dimension | What it checks |
|-----------|---------------|
| Completeness | All sections present, sufficient detail |
| Testability | RFC 2119 usage, measurable requirements |
| Consistency | No contradictions, consistent terminology |
| TaskMaster compatibility | Extractable dependency chains, explicit tech stack |
| OpenSpec compatibility | Can generate Gherkin scenarios |
