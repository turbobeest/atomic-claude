# Claude-Mem Migration Plan

## Overview

Replace Supermemory (external API) with claude-mem (local Claude Code plugin) for ATOMIC-CLAUDE's persistent memory system.

## Why Claude-Mem?

| Aspect | Supermemory | Claude-Mem |
|--------|-------------|------------|
| Storage | External API | Local SQLite |
| Dependency | API key required | Self-contained |
| Integration | Custom bash wrappers | Native Claude Code hooks |
| Browsing | External dashboard | Local web UI (port 37777) |
| Cost | API usage fees | Free (local) |
| Privacy | Data sent externally | All data stays local |

## Architecture Changes

### Current (Supermemory)

```
Task Start → memory_task_start() → _sm_recall() → HTTP API → task-context.md
Task End   → memory_task_end()   → _sm_memory() → HTTP API → Supermemory cloud
```

### Target (Claude-Mem)

```
Task Start → memory_task_start() → mem-search skill → SQLite → task-context.md
Task End   → memory_task_end()   → Claude Code hooks → SQLite (automatic)
```

## Key Insight: Claude-Mem's Hook System

Claude-mem already captures context via Claude Code hooks:
- `SessionStart` - Session begins
- `UserPromptSubmit` - User input captured
- `PostToolUse` - Tool results captured
- `Stop` / `SessionEnd` - Session cleanup

**This means**: ATOMIC-CLAUDE may not need explicit `memory_task_end()` saves - claude-mem captures tool usage automatically.

## Migration Steps

### Phase 1: Install & Verify

1. Install claude-mem plugin in Claude Code
2. Verify hooks are firing during ATOMIC-CLAUDE runs
3. Check web UI at localhost:37777 shows captured context

**Status:** Pending (requires claude-mem plugin installation)

### Phase 2: Remove Supermemory Dependencies ✅ COMPLETE

**Removed:**
- `_sm_memory()` - Supermemory save function
- `_sm_recall()` - Supermemory recall function
- `_sm_delete()`, `_sm_forget()`, `_sm_forget_matching()` - Delete functions
- `_memory_forget_all_project()`, `_memory_forget_after_phase()` - Forget helpers
- `_memory_check_connection()` - Connection verification
- Supermemory API key checks throughout codebase
- HTTP curl calls to Supermemory API

**Kept:**
- `memory_task_start()` - Uses local file recall
- `memory_task_end()` - Saves to local files
- Local file storage in `.state/memory/`
- Task context injection into prompts
- Head tracking and backtrack detection
- User approval gates for phase closeouts

**Updated:**
- `phases/0-setup/tasks/004-api-keys.sh` - Replaced Supermemory option with local memory toggle
- `README.md` - Updated persistent memory documentation
- `agents/agent-manifest.json` - Renamed supermemory-expert to ai-memory-expert
- Deprecated `SUPERMEMORY-INTEGRATION.md`

### Phase 3: Update lib/task-memory-defs.sh

The recall/save definitions remain unchanged - they define WHAT to recall/save.
The implementation now uses local files exclusively.

**Status:** No changes needed - definitions are backend-agnostic

### Phase 4: Test Memory Flow

1. Run Phase 0 setup with memory enabled
2. Verify local files created in `.state/memory/`
3. Run Phase 1 and verify recall from local files works
4. Check task-context.md contains relevant history

**Status:** Ready for testing

## Open Questions

1. **Project Isolation**: How to scope queries to specific ATOMIC project?
   - Tag memories with project name?
   - Use directory path in queries?

2. **Structured vs Natural**: Supermemory used structured saves. Claude-mem uses natural observations.
   - Do we need structured task outputs?
   - Or rely on claude-mem's semantic compression?

3. **Token Budget**: Claude-mem has progressive disclosure.
   - How much context to inject per task?
   - Use timeline vs full fetch?

4. **Offline Support**: SQLite is local, so offline works.
   - Keep local `.state/memory/` as redundant backup?
   - Or simplify to claude-mem only?

## Files to Modify

```
lib/memory.sh              # Core changes - remove Supermemory, add claude-mem
lib/task-memory-defs.sh    # Keep as-is (defines what, not how)
lib/atomic.sh              # Update context injection
phases/*/tasks/*.sh        # Remove SUPERMEMORY_API_KEY checks
config/secrets.json        # Remove supermemory key requirement
```

## Success Criteria

- [x] ATOMIC-CLAUDE runs without Supermemory API key
- [x] Local memory storage in `.state/memory/` works
- [x] Phase closeouts capture meaningful summaries (local)
- [x] Recall at task start retrieves from local files
- [ ] Task context persists across sessions via claude-mem (requires plugin)
- [ ] Web UI at localhost:37777 shows ATOMIC project history (requires plugin)
- [ ] No degradation in cross-task context quality (needs testing)

## Timeline Estimate

- Phase 1 (Install): Quick verification
- Phase 2 (memory.sh): Main refactor work
- Phase 3 (task-defs): Minimal changes
- Phase 4 (Testing): Full pipeline run

## Rollback Plan

Keep Supermemory code commented/branched - can restore if claude-mem doesn't meet needs.
