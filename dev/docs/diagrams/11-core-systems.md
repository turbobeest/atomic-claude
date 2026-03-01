# Core Systems

Shared infrastructure used by all phases: state management, memory, LLM routing, audit, and dashboard sync.

```mermaid
flowchart TB
    subgraph state["StateManager (core/state.py)"]
        s1["Immutable transitions"]
        s2["Atomic file writes<br/>.state/task-state.json"]
        s3["File locking<br/>(fcntl/msvcrt)"]
        s4["Snapshots for rollback"]
        s1 --> s2
        s3 --> s2
        s4 --> s2
    end

    subgraph memory["Memory System (core/memory/)"]
        m1["MemoryStore<br/>Append-only .state/memory.json"]
        m2["CheckpointManager<br/>.state/memory-checkpoints/"]
        m3["MemoryRecall<br/>Hybrid search + scoring"]
        m4["MemoryCompactor<br/>Age + similarity pruning"]
        m1 --> m2
        m3 --> m1
        m4 --> m1
    end

    subgraph llm["LLM Router (core/llm/)"]
        l1["Role-based routing<br/>PRIMARY / FAST / HEAVY"]
        l2["Circuit breaker<br/>(3 failures → 5min cooldown)"]
        l3["Response cache<br/>(15min TTL)"]
        l4["Token tracking<br/>session-tokens.json"]
        l1 --> l2 --> l3
        l1 --> l4
    end

    subgraph providers["Provider Chain"]
        p1["Claude Code CLI"]
        p2["Anthropic API"]
        p3["AWS Bedrock"]
        p4["Ollama (local)"]
        p1 -->|"fallback"| p2 -->|"fallback"| p3 -->|"fallback"| p4
    end

    subgraph audit["Audit Framework (core/audit.py)"]
        a1["43 categories from CSV"]
        a2["Phase-specific selection"]
        a3["Parallel evaluation<br/>(5 concurrent)"]
        a4["Remediation loop<br/>(max 3 rounds)"]
        a1 --> a2 --> a3 --> a4
    end

    subgraph dashboard["Dashboard Sync"]
        d1["current-task.json"]
        d2["session-tokens.json"]
        d3["errors.json"]
        d4["POST localhost:5174"]
    end

    subgraph graph["Knowledge Graph (optional)"]
        g1["FalkorDB"]
        g2["Features, Tasks, Specs,<br/>Agents, Sources"]
        g1 --> g2
    end

    llm --> providers
    memory -.-> graph
    state --> dashboard

    phase["Any Phase Task"] --> state
    phase --> memory
    phase --> llm
    phase --> audit
    phase -.-> graph
```

## Memory Recall Scoring

```
Score = 50% keyword match
      + 30% recency (7-day half-life)
      + 20% phase relevance
      + signal boost
```

## State Lifecycle

```
NOT_STARTED → INITIALIZING → READY → RUNNING → COMPLETED
                                        ↓
                                      FAILED → ROLLED_BACK
```

## LLM Model Tiers

| Tier | Models | Typical Use |
|------|--------|-------------|
| opus | claude-opus-4 | PRD authoring, decomposition, implementation, deliberation |
| sonnet | claude-sonnet-4 | Validation, code review, artifact generation |
| haiku | claude-haiku-4.5 | Corpus analysis, agent suggestions, announcements |
