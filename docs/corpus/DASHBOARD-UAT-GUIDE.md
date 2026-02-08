# Dashboard UAT Monitoring Guide

## Overview

The Tasks Dashboard provides real-time visibility into UAT execution, showing:
- LLM invocations (provider, model, task details)
- Task completion status
- Memory operations per task
- File artifacts (read/written)

**No code changes needed** - the dashboard already supports UAT monitoring.

---

## Setup

### 1. Start Dashboard

```bash
cd /Users/jamesterbeest/dev/atomic-claude2

# Dashboard auto-starts during Phase 0, or manually:
cd dashboard && node server.js
```

**URL**: http://localhost:5174

### 2. Run UAT Test

```bash
# In a separate terminal
cd /Users/jamesterbeest/dev/atomic-claude2
python test/uat_runner.py
```

---

## What You'll See

### Active LLM Invocation Box (Top)

When an LLM is actively processing:

```
⚡ ACTIVE LLM INVOCATION

Current Phase: Setup
Current Task: ⚡ 002 - Extracting config from setup.md

Provider: bedrock
Model: us-gov.anthropic.claude-sonnet-4-5
Context Window: 200K
Cost Tier: High
```

**Updates in real-time** via Server-Sent Events (1-2 second delay).

Between LLM calls, shows:
```
🟠 No Active Session
No pipeline activity detected. Run a phase to begin.
```

---

### Phase Progress

Each phase shows:
- **Status badge**: 📋 Planned | ⏳ In Progress | ✓ Complete
- **Task count**: "3/9 tasks"
- **Expand/collapse** to see individual tasks

Example (Phase 2 - PRD in progress):

```
▼ PRD
   (2-prd)                                     3/9 tasks    ⏳ In Progress

   ✅ 201  Entry validation                    🧠🏷️🗄️      ~ 1  + 2
   ⏳ 202  PRD setup                           🏃          ~ 3  + 0
   ○  203  PRD interview                       ➖           ~ 0  + 0
   ...
```

---

### Memory Flow Icons (Per Task)

Each task shows memory operations as icons:

| Icon | Meaning | Details |
|------|---------|---------|
| 🧠 | **Recalled** | Task successfully recalled context from memory |
| 🏷️ | **Saved** | Task successfully saved outputs to memory |
| 📦 | **Pending Save** | Save operation queued but not yet executed |
| ⬜ | **Pending Recall** | Recall operation queued but not yet executed |
| 🏃 | **In Progress** | Memory operation currently executing |
| 🗄️ | **Local** | Memory file exists locally (`.state/memory/`) |
| ☁️ | **Remote** | Memory synced to remote storage (if enabled) |
| 💉 | **Injected** | Context injected into LLM prompt |
| 📝 | **Written** | Memory written to disk |
| ⚠️ | **Failed** | Memory operation failed (check logs) |
| ➖ | **None** | No memory operations for this task |

**Example Patterns:**

- **Typical task**: `🧠🏷️🗄️` (recalled, saved, local file exists)
- **First task**: `🏷️🗄️` (no recall, just save)
- **No memory**: `➖` (deterministic task, no LLM)
- **Failed**: `⚠️` (check `.logs/atomic.log` for details)

---

### File Artifacts (Per Task)

Shows files read and written by each task:

- **~ (tilde)** - Files **read** by task (inputs)
- **+ (plus)** - Files **written** by task (outputs)

Example:
```
✅ 205  PRD authoring    🧠🏷️🗄️    ~ 3  + 5

Expand to see files:
  ~ project-config.json
  ~ discovery-summary.md
  ~ prd-interview.json
  + PRD.md
  + prd-metadata.json
  + prd-context.json
  + prd-session.json
  + prd-output.md
```

**Click any file name** to view its contents in a modal.

---

### Memory System Stats (Bottom)

Global memory system statistics:

```
Memory System Stats

Recall Definitions    Save Definitions    Debug Entries    Local Memory Files
       75                    75                 24               18
```

**What these mean:**
- **Recall Definitions**: Memory keys defined for recall (75 entries from `lib/task-memory-defs.sh`)
- **Save Definitions**: Memory keys defined for save (75 entries)
- **Debug Entries**: Debug logs in `.state/memory-debug/` (created during UAT)
- **Local Memory Files**: Actual memory files in `.state/memory/` (created during UAT)

**Expected progression during UAT:**
- Start: `Debug Entries: 0, Local Files: 0`
- After Phase 0: `Debug Entries: ~10, Local Files: ~5`
- After Phase 2: `Debug Entries: ~30, Local Files: ~15`
- After Phase 5: `Debug Entries: ~60, Local Files: ~30`

---

## UAT-Specific Observations

### UAT Mode Bypasses

Tasks running in UAT mode (with `ATOMIC_UAT_MODE=true`) will:
- **Complete quickly** (no actual LLM invocations for bypassed tasks)
- **Show minimal memory icons** (usually just `➖` or `🏷️`)
- **Create minimal files** (stub outputs)

Example UAT task:
```
✅ 203  PRD interview (UAT mode)    🏷️    ~ 0  + 1
```

This is **expected behavior** - UAT bypasses skip LLM calls to speed up testing.

### Real LLM Invocations

Some tasks **do invoke LLMs** even in UAT mode:
- Task 002 (Config extraction) - Parses `setup.md`
- Task 104 (Agent selection) - Selects agents from inventory
- Task 204 (Agent selection) - Selects PRD agents

These will show:
- Active LLM box with provider/model details
- Full memory flow icons (`🧠🏷️💉🗄️`)
- Multiple file artifacts

---

## Troubleshooting

### Dashboard shows "No Active Session" during UAT

**Cause**: Dashboard only shows LLM invocations **while they're running**. Between tasks, it shows idle.

**Solution**: This is normal. Watch for:
- Phase task counts incrementing (e.g., "3/9 tasks" → "4/9 tasks")
- Task status icons changing (○ → ⏳ → ✅)

### Memory icons not appearing

**Cause**: UAT bypasses skip memory operations for speed.

**Check**:
1. Look at "Memory System Stats" at bottom - should increment
2. Check `.state/memory/` directory: `ls -la .state/memory/phase-*/`
3. For non-bypassed tasks, memory icons will appear

### Files not showing

**Cause**: Task hasn't written outputs yet, or outputs are in different directory.

**Check**:
1. Click the task row to expand file list
2. Check `.outputs/<phase>/` directory manually
3. UAT bypassed tasks write minimal files

### Dashboard not updating

**Cause**: Server-Sent Events connection dropped.

**Solution**:
1. Check browser console for errors (F12)
2. Refresh page (dashboard auto-reconnects)
3. Verify server running: `lsof -Pi :5174`

---

## Expected UAT Timeline

When running full UAT (phases 0-5):

| Phase | Duration | LLM Invocations | Memory Ops | Files Written |
|-------|----------|-----------------|------------|---------------|
| 0 - Setup | ~2 min | 2-3 | 5-8 | 8-10 |
| 1 - Discovery | ~3 min | 3-4 | 10-15 | 15-20 |
| 2 - PRD | ~3 min | 2-3 | 8-12 | 20-25 |
| 3 - Tasking | ~2 min | 1-2 | 5-8 | 8-12 |
| 4 - Specification | ~2 min | 1-2 | 3-5 | 5-8 |
| 5 - Implementation | ~2 min | 1-2 | 3-5 | 5-8 |
| **Total** | **~14 min** | **10-16** | **34-53** | **61-83** |

**Watch for**:
- Task counts incrementing steadily
- Memory icons appearing on completed tasks
- "Active LLM Invocation" box showing provider/model during actual LLM calls

---

## Success Criteria

By end of UAT, dashboard should show:

✅ **All 6 phases**: Status = "✓ Complete"
✅ **All 47 tasks**: Status icon = "✅"
✅ **Memory stats**:
   - Debug Entries: 40-60
   - Local Memory Files: 25-35
✅ **File artifacts**: Each task shows ~ and + counts
✅ **No errors**: No "❌" or "⚠️" icons

---

## Advanced: Monitoring Memory Flow

### Identify Memory-Heavy Tasks

Look for tasks with many memory icons:

```
✅ 205  PRD authoring    🧠🏷️💉🗄️📝    ~ 8  + 12
```

This indicates:
- **🧠** Recalled prior context (discovery, config, etc.)
- **🏷️** Saved PRD sections to memory
- **💉** Injected context into LLM prompt
- **🗄️** Local memory file created
- **📝** Memory written to disk

**High memory usage = good** for complex tasks like PRD authoring.

### Identify Deterministic Tasks

Tasks with `➖` (no memory):

```
✅ 001  Mode selection    ➖    ~ 0  + 1
```

This is expected for:
- Configuration tasks (001-004)
- Validation tasks (101, 201, 301, etc.)
- Closeout tasks (110, 209, 306, etc.)

These are **deterministic** (no LLM, no memory needed).

---

## Conclusion

The dashboard provides **complete observability** of UAT execution without any code changes:
- Real-time LLM tracking
- Task completion status
- Memory flow per task
- File artifacts

Simply open http://localhost:5174 and watch the UAT run.
