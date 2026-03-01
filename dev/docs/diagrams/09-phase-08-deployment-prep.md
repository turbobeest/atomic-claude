# Phase 8: Deployment Prep

Release artifact generation via LLM and deployment approval.

```mermaid
flowchart TB
    subgraph t801["Task 801: Entry & Initialization"]
        t801a["Validate Phase 7 closeout"]
    end

    subgraph t802["Task 802: Deployment Setup"]
        t802a["Select release type:<br/>major / minor / patch"]
        t802b["Set version (SemVer)"]
        t802a --> t802b
    end

    t803["Task 803: Agent Selection<br/>release packager (sonnet/haiku)<br/>changelog writer (sonnet/haiku)<br/>doc generator (opus/sonnet)<br/>install guide writer (sonnet/haiku)"]

    subgraph t804["Task 804: Artifact Generation"]
        a1["Release packaging analysis"]
        a2["CHANGELOG.md generation"]
        a3["Documentation generation<br/>(README, USAGE, API,<br/>CONFIG, TROUBLESHOOTING)"]
        a4["INSTALL.md generation"]
        a1 & a2 & a3 & a4 -->|"sonnet<br/>(2-attempt retry)"| artifacts["artifacts.json"]
    end

    t805["Task 805: Phase Audit"]

    subgraph t806["Task 806: Deployment Approval"]
        t806a["Review artifacts"]
        t806b["Approve / revise / discuss"]
        t806a --> t806b
    end

    t807["Task 807: Closeout"]

    t801 --> t802 --> t803 --> t804 --> t805 --> t806 --> t807

    t802 -->|"setup.json"| deploy[(".claude/deployment/")]
    t804 -->|"artifacts.json"| deploy
    t806 -->|"approval.json"| deploy

    deploy -->|"closeout.json"| next["Phase 9: Release"]

    llm1["LLM: sonnet<br/>(4 artifacts, 2 retries each)"] -.-> t804

    human1(["Human: version + type"]) -.-> t802
    human2(["Human: approve artifacts"]) -.-> t806
    human3(["Human: approve closeout"]) -.-> t807

    style human1 fill:#FFD700
    style human2 fill:#FFD700
    style human3 fill:#FFD700
    style llm1 fill:#98FB98
```

## Generated Artifacts

| Artifact | Format | Content |
|----------|--------|---------|
| Release package | tar.gz, wheel | Packaging analysis |
| Changelog | CHANGELOG.md | Keep a Changelog format |
| Documentation | 5 markdown files | User-facing docs |
| Install guide | INSTALL.md | Platform-specific instructions |
