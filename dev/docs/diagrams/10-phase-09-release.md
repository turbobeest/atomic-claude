# Phase 9: Release

Final release execution, announcement generation, and project completion.

```mermaid
flowchart TB
    subgraph t901["Task 901: Entry & Initialization"]
        t901a["Validate Phase 8 closeout"]
        t901b["Check CHANGELOG.md"]
        t901c["Check dist/ artifacts"]
        t901a --> t901b --> t901c
    end

    subgraph t902["Task 902: Release Setup"]
        t902a["Review release notes"]
        t902b["Confirm / review-again / abort"]
        t902a --> t902b
    end

    t903["Task 903: Agent Selection<br/>announcement writer (haiku/sonnet)"]

    subgraph t904["Task 904: Release Execution"]
        t904a["Gather context:<br/>PRD, CHANGELOG,<br/>Phase 5-8 closeouts"]
        t904b["Generate announcement"]
        t904a -->|"haiku"| t904b
    end

    subgraph t905["Task 905: Release Confirmation"]
        t905a["Review execution status"]
        t905b["Confirm / investigate / rollback"]
        t905a --> t905b
    end

    subgraph t906["Task 906: Final Closeout"]
        t906a["Generate final closeout"]
        t906b["PROJECT COMPLETE"]
        t906a --> t906b
    end

    t901 --> t902 --> t903 --> t904 --> t905 --> t906

    t904 -->|"announcement.md<br/>execution.json"| release[(".claude/release/")]
    t905 -->|"confirmation.json"| release

    release --> complete["Phase 9 closeout.json<br/>final_phase: true"]

    llm1["LLM: haiku<br/>(announcement)"] -.-> t904

    human1(["Human: confirm release"]) -.-> t902
    human2(["Human Gate:<br/>Release Sign-off"]) -.-> t905
    human3(["Human: final approval"]) -.-> t906

    style human1 fill:#FFD700
    style human2 fill:#FFD700
    style human3 fill:#FFD700
    style llm1 fill:#98FB98
    style complete fill:#90EE90
```

## Release Flow

```
Phase 8 artifacts (changelog, docs, install guide)
    → Task 902: Human confirms release notes
        → Task 904: LLM generates announcement
            → Task 905: Human confirms execution
                → Task 906: PROJECT COMPLETE
```
