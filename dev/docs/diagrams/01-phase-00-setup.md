# Phase 0: Setup

Environment detection, provider configuration, project setup wizard, and system validation.

```mermaid
flowchart TB
    subgraph t001["Task 001: Environment Bootstrap"]
        t001a["Detect OS, verify tools<br/>(8 required + 5 recommended)"]
        t001b["Launch dashboard + FalkorDB"]
        t001a --> t001b
    end

    subgraph t002["Task 002: Provider Detection"]
        t002a["Load credentials from .env"]
        t002b["Health-check providers<br/>(Anthropic, Bedrock, Ollama)"]
        t002c["Build provider inventory"]
        t002a --> t002b --> t002c
    end

    subgraph t003["Task 003: Setup Wizard"]
        t003a["10-step interactive config:<br/>name, type, mode, repo, LLM,<br/>agents, audit, sandbox"]
        t003b["Optional: AI suggestions<br/>from reference materials"]
        t003b -.->|"haiku"| t003a
    end

    subgraph t004["Task 004: Material Scan"]
        t004a["Scan project for 40+ file types"]
        t004b["Collect external references"]
        t004c["Organize into docs/reference/"]
        t004a --> t004b --> t004c
    end

    subgraph t005["Task 005: Repository & System Setup"]
        t005a["Verify agents/audits/skills"]
        t005b["Configure task routing"]
        t005c["Assess CPU/GPU/memory/network"]
        t005a --> t005b --> t005c
    end

    t001 --> t002 --> t003 --> t004 --> t005

    t001 -->|"project-config.json<br/>(environment)"| out1[(".outputs/0-setup/")]
    t002 -->|"provider-inventory.json<br/>secrets.json"| out1
    t003 -->|"project-config.json<br/>(full config)"| out1
    t004 -->|"material-manifest.json"| out1
    t005 -->|"env-validation.json"| out1

    out1 -->|"closeout.json"| next["Phase 1: Discovery"]

    human1(["Human: install missing tools"]) -.-> t001
    human2(["Human: credential wizard"]) -.-> t002
    human3(["Human: 10-step wizard"]) -.-> t003
    human4(["Human: organize materials?"]) -.-> t004

    style human1 fill:#FFD700
    style human2 fill:#FFD700
    style human3 fill:#FFD700
    style human4 fill:#FFD700
```

## Key Outputs

| File | Purpose | Consumers |
|------|---------|-----------|
| `project-config.json` | Project identity, type, LLM config, agent defaults | All phases |
| `provider-inventory.json` | Available LLM providers and health status | LLM Router |
| `secrets.json` | Credential flags (no secrets stored) | Task 003 |
| `material-manifest.json` | Scanned files and external references | Phase 1 Task 101 |
| `env-validation.json` | System capabilities, agent/audit counts | Closeout |
