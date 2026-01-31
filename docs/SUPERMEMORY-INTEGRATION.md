# Supermemory Integration Design

## Problem Statement

Every ATOMIC-CLAUDE session starts fresh. Claude Code has no memory of:
- What project we're working on
- What phase we're in
- Decisions made in previous sessions
- User preferences and patterns
- Multi-agent conversation context

This creates a **token tax** - thousands of tokens spent re-explaining context that should be persistent.

## Additional Concern: Memory Coherence

When users backtrack (redo Phase 2 after completing Phase 4) or fix bugs in atomic-claude itself, we need to ensure memory reflects the **agreed-upon progression**, not orphaned/invalid states.

## Solution: Three-Tier Memory Architecture

### Tier 1: Session Bootstrap

On session start, inject essential context from memory:

```
┌─────────────────────────────────────────────┐
│ SESSION START                               │
├─────────────────────────────────────────────┤
│ 1. Query supermemory for project context    │
│ 2. Retrieve: identity, phase, decisions     │
│ 3. Write to .claude/session-context.md      │
│ 4. CLAUDE.md references session-context.md  │
└─────────────────────────────────────────────┘
```

**Before**: CLAUDE.md is 2000+ tokens explaining everything
**After**: CLAUDE.md is ~200 tokens saying "see session-context.md"

### Tier 2: Gardener Persistence

The haiku gardener maintains running summaries during multi-agent work. Currently ephemeral.

```
┌─────────────────────────────────────────────┐
│ MULTI-AGENT SESSION                         │
├─────────────────────────────────────────────┤
│ Every N turns:                              │
│   → Gardener writes checkpoint to memory    │
│                                             │
│ On session end:                             │
│   → Final summary persisted                 │
│                                             │
│ Next session:                               │
│   → Can resume from checkpoint              │
└─────────────────────────────────────────────┘
```

### Tier 3: Phase Closeout Capture

Each phase produces a closeout document. This gets persisted to memory.

```
┌─────────────────────────────────────────────┐
│ PHASE CLOSEOUT                              │
├─────────────────────────────────────────────┤
│ Write to memory:                            │
│   → Phase summary                           │
│   → Key decisions with rationale            │
│   → Artifacts produced                      │
│   → Issues encountered                      │
│                                             │
│ Queryable later:                            │
│   "Why did we choose that architecture?"    │
│   "What was decided in Phase 2?"            │
└─────────────────────────────────────────────┘
```

## Memory Coherence: Checkpoint + Head Model

### The Problem

```
Timeline A (happy path):
  Phase 0 ──→ Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4
     ↓           ↓           ↓           ↓           ↓
  memory      memory      memory      memory      memory

Timeline B (backtrack):
  Phase 0 ──→ Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4
     ↓           ↓           ↓           ↓           ↓
  memory      memory      memory      memory      memory
                             │
                             └──→ Phase 2 (redo)
                                       ↓
                                  What happens to Phase 3-4 memories?
```

### The Solution: Head Tracking

Like git, we track a "head" pointer:

```json
// .state/memory-head.json
{
  "project": "atomic-my-project",
  "head_phase": 2,
  "head_checkpoint": "phase2-20260131-143022",
  "checkpoints": [
    {"id": "phase0-...", "phase": 0, "status": "valid"},
    {"id": "phase1-...", "phase": 1, "status": "valid"},
    {"id": "phase2-...", "phase": 2, "status": "valid"},
    {"id": "phase3-...", "phase": 3, "status": "invalidated"},
    {"id": "phase4-...", "phase": 4, "status": "invalidated"}
  ]
}
```

### Backtrack Handling

When user starts Phase 2 after completing Phase 4:

1. **Detect**: `memory_check_backtrack(2)` returns true
2. **Prompt**: Ask user what to do with Phase 3-4 memories
3. **Options**:
   - `continue`: Mark as invalidated locally (ignored on recall)
   - `forget`: Also remove from Supermemory
   - `abort`: Cancel the backtrack
4. **Update**: Set head_phase = 2

### Scope Separation

Pipeline work vs. meta/debug work:

- **Pipeline mode**: `$ATOMIC_PHASE` is set → memories persist
- **Meta mode**: No phase context → skip memory operations

This prevents bug-fixing sessions from polluting project memory.

### User Approval Gate

Nothing persists without explicit consent:

```
MEMORY CHECKPOINT

Summary to persist:
  Phase 2 PRD complete. Mobile-first e-commerce platform.
  JWT auth, React frontend, Python/FastAPI backend.

Options:
  [save] Save to long-term memory
  [edit] Edit summary before saving
  [skip] Don't save (local only)

Choice [save]: _
```

## Memory Schema

### Project Scope
```
project:{id}:identity      → Project description, tech stack, mode
project:{id}:phase         → Current phase and status
project:{id}:decision:{ts} → Individual decisions with rationale
project:{id}:preferences   → User preferences for this project
```

### Phase Scope
```
phase:{id}:{n}:closeout    → Phase closeout summary
phase:{id}:{n}:artifacts   → List of artifacts produced
phase:{id}:{n}:agents      → Agents used and their outputs
phase:{id}:{n}:issues      → Problems encountered
```

### Gardener Scope
```
gardener:{id}:{session}:checkpoint → Running summary checkpoint
gardener:{id}:{session}:insights   → Key insights extracted
gardener:{id}:{session}:final      → Final session summary
```

### User Scope (Cross-Project)
```
user:preferences:model     → Preferred model (sonnet, opus, etc.)
user:preferences:style     → Code style preferences
user:patterns:{name}       → Patterns that work well
user:conventions:{name}    → Naming, structure conventions
```

## Implementation

### lib/memory.sh

Core memory functions:
- `memory_write(key, content, metadata)` - Write to memory
- `memory_read(key)` - Read from memory
- `memory_search(query, namespace)` - Search memories

High-level functions:
- `memory_write_project_identity()` - Project setup
- `memory_write_phase_state()` - Phase transitions
- `memory_write_decision()` - Decision capture
- `memory_write_phase_closeout()` - Phase completion
- `memory_write_gardener_checkpoint()` - Multi-agent checkpoints

Lifecycle:
- `memory_session_start()` - Load context on start
- `memory_session_end()` - Persist context on end

### Integration Points

1. **Phase 0 (Setup)**: Write project identity
2. **Phase transitions**: Write phase state
3. **Decision points**: Write decisions with rationale
4. **Phase closeouts**: Write closeout summaries
5. **Gardener**: Checkpoint during multi-agent work
6. **Session hooks**: Start/end lifecycle

### Providers

1. **Supermemory (Primary)**: Via MCP server
2. **Local (Fallback)**: JSON files in `.claude/memory/`

## Token Reduction Estimate

| Context | Before | After |
|---------|--------|-------|
| CLAUDE.md baseline | 2000 tokens | 200 tokens |
| Phase context | 500 tokens | Retrieved |
| PRD reference | 1000 tokens | Summarized in memory |
| Decision history | Scattered | Queryable |
| **Total bootstrap** | **3500+ tokens** | **~500 tokens** |

**Reduction: ~85%**

## Configuration

```bash
# Enable memory
export ATOMIC_MEMORY_ENABLED=true

# Provider (supermemory or local)
export ATOMIC_MEMORY_PROVIDER=supermemory

# API key
export SUPERMEMORY_API_KEY=your_key_here

# Gardener checkpoint interval
export ATOMIC_MEMORY_CHECKPOINT_INTERVAL=10
```

## Graceful Degradation

Memory is an enhancement, not a requirement:
- If supermemory unavailable → fall back to local
- If local unavailable → continue without memory
- All memory operations are non-blocking
- System works identically, just with higher token usage

## Future Enhancements

1. **Cross-project learning**: "How did we handle auth in project X?"
2. **Pattern extraction**: Automatically identify reusable patterns
3. **Smart retrieval**: Only inject relevant memories based on current task
4. **Memory pruning**: Archive old memories, keep recent relevant
5. **Team memories**: Shared organizational knowledge
