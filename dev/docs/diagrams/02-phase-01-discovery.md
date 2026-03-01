# Phase 1: Discovery

Requirements elicitation through corpus analysis, conversational dialogue, multi-agent deliberation, and approach selection.

```mermaid
flowchart TB
    subgraph t101["Task 101: Entry & Corpus Analysis"]
        t101a["Validate Phase 0 closeout"]
        t101b["Analyze reference materials"]
        t101a --> t101b
    end

    subgraph t102["Task 102: Import Requirements"]
        t102a["Parse RST/JSON/YAML/CSV<br/>requirement files (optional)"]
    end

    subgraph t103["Task 103: Agent Selection"]
        t103a["Select expert agents<br/>from 221 available"]
        t103b["AI suggests SMEs<br/>based on corpus"]
        t103b -.->|"haiku"| t103a
    end

    subgraph t104["Task 104: Opening Dialogue"]
        t104a["Multi-turn conversation:<br/>vision, impact, constraints"]
        t104b["Canvas tracks PRD<br/>section coverage"]
        t104a ---|"opus"| t104b
    end

    subgraph t105["Task 105: Discovery Conversation"]
        t105a["Conference table:<br/>orchestrator + facilitator<br/>+ analyst + 3 experts"]
        t105b["Generate approaches"]
        t105c["Reach consensus"]
        t105a -->|"opus"| t105b --> t105c
    end

    subgraph t106["Task 106: Approach Selection"]
        direction LR
        t106a["Review consensus"]
        t106b["Edit decisions inline"]
        t106c["Approve approach"]
        t106a --> t106b --> t106c
    end

    t107["Task 107: Discovery Diagrams<br/>(C4, data flow, sequence, etc.)"]
    t108["Task 108: Phase Audit"]
    t109["Task 109: Closeout"]

    t101 --> t102 --> t103 --> t104 --> t105 --> t106 --> t107 --> t108 --> t109

    t101 -->|"corpus.json<br/>corpus-analysis.md"| out1[(".outputs/1-discovery/")]
    t102 -->|"needs-index.json"| out1
    t103 -->|"selected-agents.json"| out1
    t104 -->|"dialogue.json"| out1
    t105 -->|"approaches.json<br/>consensus.json"| out1
    t106 -->|"selected-approach.json"| out1
    t107 -->|"docs/diagrams/*.dot + *.svg"| out1

    out1 -->|"closeout.json"| next["Phase 2: PRD"]

    human1(["Human Gate:<br/>Approach approval"]) -.-> t106
    llm1["LLM: haiku"] -.-> t101
    llm2["LLM: opus (multi-turn)"] -.-> t104
    llm3["LLM: opus (heavy)"] -.-> t105
    llm4["LLM: opus"] -.-> t107

    graph1[("Knowledge Graph")] -.-> t101
    graph1 -.-> t102
    graph1 -.-> t103
    graph1 -.-> t105

    style human1 fill:#FFD700
    style llm1 fill:#98FB98
    style llm2 fill:#98FB98
    style llm3 fill:#98FB98
    style llm4 fill:#98FB98
    style graph1 fill:#DDA0DD
```

## Data Flow Detail

```
Phase 0 project-config.json
    + docs/reference/ materials
        → Task 101: corpus-analysis.md
            → Task 104: dialogue context
                → Task 105: panel deliberation
                    → Task 106: selected-approach.json
                        → Phase 2 PRD authoring context
```

## LLM Usage

| Task | Model | Purpose |
|------|-------|---------|
| 101 | haiku | Corpus material analysis |
| 103 | haiku | Agent recommendations |
| 104 | opus | Multi-turn vision dialogue (min 3 turns) |
| 105 | opus | Multi-agent deliberation (heavy) |
| 107 | opus | Architecture diagram generation (DOT format) |
