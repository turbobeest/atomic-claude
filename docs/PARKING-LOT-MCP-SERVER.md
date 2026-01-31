# Parking Lot: ATOMIC-CLAUDE as MCP Server

> **Status**: Concept / Future Development
> **Created**: 2025-01-31

## The Idea

ATOMIC-CLAUDE could expose its pipeline, agents, and audits as an MCP (Model Context Protocol) server. Any Claude Code session could then invoke ATOMIC capabilities without running the full pipeline.

## Potential MCP Tools

### Pipeline Tools
```
atomic/start_phase      → Start a specific phase
atomic/resume           → Resume from last checkpoint
atomic/phase_status     → Get current phase state
atomic/skip_phase       → Skip to a phase (with guardrails)
```

### Agent Tools
```
atomic/list_agents      → List available agents by category
atomic/invoke_agent     → Run a specific agent with prompt
atomic/agent_info       → Get agent details and capabilities
```

### Audit Tools
```
atomic/run_audit        → Run a specific audit
atomic/audit_report     → Get audit results
atomic/list_audits      → List available audits by dimension
```

### Memory Tools (with Supermemory)
```
atomic/remember         → Store context for later
atomic/recall           → Retrieve relevant memories
atomic/decisions        → Get project decisions
```

## Potential MCP Resources

### Static Resources
```
atomic://agents/inventory.csv     → Agent inventory
atomic://audits/inventory.csv     → Audit inventory
atomic://pipeline/phases          → Phase definitions
```

### Dynamic Resources
```
atomic://project/prd              → Current PRD
atomic://project/decisions        → Decision log
atomic://project/phase/{n}        → Phase artifacts
```

## Use Cases

### 1. Ad-hoc Agent Invocation
```
User: "Run the security-auditor agent on this file"
Claude: [Uses atomic/invoke_agent tool]
```

### 2. Quick Audit
```
User: "Check this code for accessibility issues"
Claude: [Uses atomic/run_audit with a11y dimension]
```

### 3. Pipeline Snippet
```
User: "Generate a spec for this feature"
Claude: [Uses atomic/start_phase with phase=4]
```

### 4. Cross-Project Context
```
User: "How did we handle auth in the other project?"
Claude: [Uses atomic/recall to search memories]
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Claude Code Session                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  User: "Run the specification agent on this feature"        │
│                                                              │
│  Claude: [Invokes MCP tool]                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    ATOMIC-CLAUDE MCP Server                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Tools:                      Resources:                      │
│  ├── atomic/invoke_agent     ├── atomic://agents/*          │
│  ├── atomic/run_audit        ├── atomic://audits/*          │
│  ├── atomic/start_phase      ├── atomic://project/*         │
│  └── atomic/recall           └── atomic://pipeline/*        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    ATOMIC-CLAUDE Core                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  agents/          audits/          lib/          phases/    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Considerations

### Language Choice
- **TypeScript**: Native MCP SDK support, async-friendly
- **Python**: Also has MCP SDK, familiar to many
- **Bash wrapper**: Could wrap existing bash scripts

### Server Mode
- **Stdio**: Local development, single user
- **SSE**: Could support remote/team use

### State Management
- MCP servers are typically stateless
- Would need to manage project state externally
- Supermemory integration helps here

### Security
- Agent invocation needs guardrails
- Audit execution is read-only (safe)
- Pipeline phases need approval flows

## Relationship to Supermemory

Supermemory + MCP Server = Powerful combination:

1. **Memory as MCP resource**: Expose memories as queryable resources
2. **Contextual tool invocation**: Use memories to inform tool behavior
3. **Persistent project state**: MCP server reads state from memory

## Questions to Resolve

1. Should the MCP server be a separate repo or part of atomic-claude?
2. How to handle long-running operations (some phases take time)?
3. How to surface approval requirements through MCP?
4. Should agents be invokable individually or only through phases?

## Next Steps (When Ready)

1. [ ] Define tool schemas (JSON Schema for each tool)
2. [ ] Define resource URIs and schemas
3. [ ] Choose implementation language
4. [ ] Build minimal viable server (1-2 tools)
5. [ ] Test with Claude Code
6. [ ] Expand tool coverage

---

*This document is a parking lot for future development. The focus now is on Supermemory integration.*
