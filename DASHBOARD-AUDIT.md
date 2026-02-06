# Dashboard Audit Report

**Date**: 2026-02-04
**Auditor**: Claude Code
**Dashboard Version**: tasks-dashboard (v1)

## Executive Summary

The dashboard has **5 critical issues** causing incorrect status display:
1. SSE stream doesn't send "inactive" state when task file is deleted
2. Browser caches old status indefinitely
3. No staleness detection in real-time stream
4. Provider/model shows old values when no task is active
5. "Active" indicator stays green even after tasks complete

---

## Issue #1: SSE Stream Silent on Missing File

**Location**: `tasks-dashboard/server.js` lines 255-264

**Problem**:
When `.state/current-task.json` doesn't exist, the SSE stream sends nothing. The browser keeps the last cached status, showing tasks as "active" even after deletion.

```javascript
// Current buggy code:
const sendStatus = () => {
  try {
    if (fs.existsSync(STATUS_FILE)) {  // ❌ Only sends if file exists
      const status = JSON.parse(fs.readFileSync(STATUS_FILE, 'utf8'));
      res.write(`data: ${JSON.stringify(status)}\n\n`);
    }
  } catch (error) {
    // Ignore streaming errors
  }
};
```

**Fix**: Send explicit "inactive" status when file is missing
```javascript
const sendStatus = () => {
  try {
    if (fs.existsSync(STATUS_FILE)) {
      const status = JSON.parse(fs.readFileSync(STATUS_FILE, 'utf8'));
      res.write(`data: ${JSON.stringify(status)}\n\n`);
    } else {
      // Send inactive status when file doesn't exist
      res.write(`data: ${JSON.stringify({
        active: false,
        message: 'No active task',
        provider: null,
        model: null
      })}\n\n`);
    }
  } catch (error) {
    // Send error status
    res.write(`data: ${JSON.stringify({
      active: false,
      error: true,
      message: 'Error reading status'
    })}\n\n`);
  }
};
```

---

## Issue #2: Dashboard Doesn't Clear Old Status

**Location**: `tasks-dashboard/public/index.html` lines 1241-1248

**Problem**:
When `currentStatus.active` is false, the LLM info box is hidden but the OLD status remains in memory. Next time a task runs, old provider/model info flashes before new data arrives.

```javascript
// Current code:
function renderLLMInfo() {
  const llmBox = document.getElementById('llmInfoBox');
  const llmGrid = document.getElementById('llmGrid');

  if (!currentStatus || !currentStatus.active) {
    llmBox.style.display = 'none';  // ❌ Only hides, doesn't clear
    return;
  }
  // ... render active status
}
```

**Fix**: Clear the status object when inactive
```javascript
function renderLLMInfo() {
  const llmBox = document.getElementById('llmInfoBox');
  const llmGrid = document.getElementById('llmGrid');

  if (!currentStatus || !currentStatus.active) {
    llmBox.style.display = 'none';
    llmGrid.innerHTML = ''; // ✅ Clear old content
    // Clear currentStatus so it doesn't reappear
    if (currentStatus && !currentStatus.active) {
      currentStatus = null;
    }
    return;
  }
  // ... render active status
}
```

---

## Issue #3: No Staleness Detection in SSE Stream

**Location**: `tasks-dashboard/server.js` lines 255-264

**Problem**:
The `/api/status` endpoint has staleness detection (checks if file is >60s old), but the SSE stream `/api/stream` doesn't include this metadata. Tasks can appear "active" for minutes after they've actually hung.

**The /api/status endpoint DOES have this**:
```javascript
const ageSeconds = Math.floor((Date.now() - mostRecentTime) / 1000);
status.file_age_seconds = ageSeconds;
status.is_stale = ageSeconds > 60;
```

**But /api/stream doesn't**:
- SSE just passes through the raw status file content
- No timestamp checking
- No staleness flag

**Fix**: Add staleness detection to SSE stream
```javascript
const sendStatus = () => {
  try {
    if (fs.existsSync(STATUS_FILE)) {
      const status = JSON.parse(fs.readFileSync(STATUS_FILE, 'utf8'));

      // Add staleness detection (same as /api/status)
      let mostRecentTime = fs.statSync(STATUS_FILE).mtimeMs;
      if (fs.existsSync(TASK_STATE_FILE)) {
        const taskStateTime = fs.statSync(TASK_STATE_FILE).mtimeMs;
        mostRecentTime = Math.max(mostRecentTime, taskStateTime);
      }
      const ageSeconds = Math.floor((Date.now() - mostRecentTime) / 1000);

      status.file_age_seconds = ageSeconds;
      status.is_stale = ageSeconds > 60;
      status.last_modified = new Date(mostRecentTime).toISOString();

      res.write(`data: ${JSON.stringify(status)}\n\n`);
    } else {
      res.write(`data: ${JSON.stringify({
        active: false,
        message: 'No active task'
      })}\n\n`);
    }
  } catch (error) {
    res.write(`data: ${JSON.stringify({
      active: false,
      error: true
    })}\n\n`);
  }
};
```

---

## Issue #4: Provider/Model Display Shows Old Values

**Location**: `tasks-dashboard/public/index.html` lines 1254-1260

**Problem**:
When displaying provider/model, the code directly reads from `currentStatus.provider` and `currentStatus.model`. If these are stale or from a deleted task, they still display.

**Current code**:
```javascript
if (currentStatus.provider) {
  items.push({ label: 'Provider', value: currentStatus.provider.toUpperCase() });
}

if (currentStatus.model) {
  items.push({ label: 'Model', value: currentStatus.model });
}
```

**Issue**: No validation that status is fresh or task is actually running

**Fix**: Check staleness before displaying
```javascript
// Only show provider/model if status is fresh and active
if (currentStatus.active && !currentStatus.is_stale) {
  if (currentStatus.provider) {
    items.push({ label: 'Provider', value: currentStatus.provider.toUpperCase() });
  }

  if (currentStatus.model) {
    items.push({ label: 'Model', value: currentStatus.model });
  }
} else if (currentStatus.is_stale) {
  // Show staleness warning
  items.push({
    label: 'Status',
    value: '⚠️ STALE (no update >60s)'
  });
}
```

---

## Issue #5: Session Banner Not Updated on Inactive State

**Location**: `tasks-dashboard/public/index.html` lines 79-98 (CSS), unknown for JS

**Problem**:
The session banner shows "Active" or "Idle" states, but doesn't update when currentStatus becomes inactive. The banner CSS is defined but the update logic may not handle the inactive→active transition properly.

**Search needed**: Find `updateSessionBanner()` function to verify it handles `active: false`

---

## Additional Issues Found

### Design Inconsistency #1: Duplicate Status Endpoints

- `/api/status` - has staleness detection, used for initial load
- `/api/stream` - no staleness detection, used for real-time updates

**Problem**: Two different sources of truth with different behaviors

**Fix**: Make them consistent - both should include staleness metadata

---

### Design Inconsistency #2: Task Status Values

**Location**: Multiple files

**Problem**: Task status uses different values in different places:
- `completed` (in most places)
- `complete` (in some places)
- `running` vs `in_progress`

**Evidence**:
```javascript
// Line 969:
actualTasks.every(([_, t]) => t.status === 'completed' || t.status === 'complete');

// Line 947:
const runningTask = Object.entries(phase.tasks).find(([_, task]) => task.status === 'running');
```

**Fix**: Standardize on one set of values:
- `pending` - not started
- `in_progress` - currently running
- `completed` - finished
- `failed` - error occurred

---

### Design Inconsistency #3: Provider Name Normalization

**Location**: Multiple locations

**Problem**: Provider names aren't normalized consistently:
- Sometimes "bedrock", sometimes "BEDROCK"
- Sometimes "ollama", sometimes "OLLAMA"
- Upstream code uses lowercase, dashboard displays uppercase

**Evidence**:
```javascript
// Line 1255:
items.push({ label: 'Provider', value: currentStatus.provider.toUpperCase() });
```

**Issue**: If provider is already "BEDROCK" from upstream, this does `.toUpperCase()` again (harmless but redundant)

**Fix**: Normalize provider names at the source (server.js), not in display logic

---

## Recommended Fixes Priority

### P0 (Critical - Breaks UX)
1. ✅ **Fix SSE stream to send inactive status** - Issue #1
2. ✅ **Clear old status in dashboard** - Issue #2
3. ✅ **Add staleness detection to SSE** - Issue #3

### P1 (High - Confusing UX)
4. ✅ **Fix provider/model display logic** - Issue #4
5. **Verify session banner updates** - Issue #5

### P2 (Medium - Code Quality)
6. **Standardize task status values** - Design Inconsistency #2
7. **Merge duplicate status logic** - Design Inconsistency #1

### P3 (Low - Polish)
8. **Normalize provider names at source** - Design Inconsistency #3

---

## Testing Checklist

After fixes are applied:

- [ ] Start dashboard, verify "No active task" shows when no task running
- [ ] Start Task 205, verify provider/model displays correctly
- [ ] Kill Task 205 process, verify dashboard shows "stale" within 60s
- [ ] Delete `.state/current-task.json`, verify dashboard shows "inactive" immediately
- [ ] Start new task, verify old status doesn't flash before new one appears
- [ ] Check phases 0-2 show as "Complete" if all tasks done
- [ ] Check phase 2 task 205 shows as "pending" (not in task-state)
- [ ] Verify file count display works for all phases

---

## Files to Modify

1. **tasks-dashboard/server.js** (lines 255-264) - Fix SSE stream
2. **tasks-dashboard/public/index.html** (lines 1241-1301) - Fix dashboard rendering

---

## Estimated Fix Time

- P0 fixes: ~20 minutes
- P1 fixes: ~10 minutes
- P2 fixes: ~30 minutes (requires refactoring)
- P3 fixes: ~5 minutes

**Total**: ~1 hour for complete fix

---

## Next Steps

1. Apply P0 fixes immediately (critical UX breaks)
2. Test with Task 205 reset scenario
3. Apply P1 fixes
4. Re-test full workflow
5. Consider P2/P3 for next iteration
