# Dashboard Review & Innovation Opportunities

**Date:** February 10, 2026
**Dashboard URL:** http://localhost:5174
**Status:** Running (PID: 28067)

---

## Current Dashboard Architecture

### Technology Stack
- **Backend:** Node.js + Express (dashboard/server.js)
- **Frontend:** Vanilla HTML/CSS/JS (dashboard/public/index.html)
- **Protocol:** Server-Sent Events (SSE) for real-time updates
- **Port:** 5174 (configurable via ATOMIC_TASKS_PORT)
- **State Files:** `.state/current-task.json`, `.state/task-state.json`

### Launch Mechanism
- **Start Script:** `./dashboard/start-dashboard.sh`
- **Auto-launch:** Via `atomic_start_dashboard()` in lib/atomic.sh
- **Browser:** Opens as Chrome app window (1250x900px)
- **Background:** Runs detached from terminal

### Current Features

**Real-Time Monitoring:**
- Current task status (active LLM invocations)
- Provider/model tracking (Max, API, Ollama)
- Staleness detection (60s timeout)
- Server-Sent Events for live updates

**Phase/Task Organization:**
- Collapsible phase sections
- Task completion status (✓ ⏳ ○)
- Progress tracking (N/M tasks complete)
- Phase badges (complete, in-progress, pending, planned)

**Memory Flow Visualization:**
- Task memory operations (recalled, saved)
- Local/remote memory tracking
- Pending operations indicator
- Debug log integration

**File Artifacts:**
- Input files (prompts, context, corpus)
- Output files (responses, extracted data)
- File viewer with 1MB limit
- Recursive directory scanning

**Session Status:**
- Active/idle/stale detection
- Last update timestamp
- Provider/model display
- Warning banners

**Project Context:**
- Project name (from setup.md)
- Configuration display
- Intelligent fallbacks for naming

---

## Strengths (What Works Well)

### 1. **Real-Time Updates**
✅ SSE provides instant feedback without polling overhead
✅ Staleness detection prevents confusion about idle sessions
✅ File watching for automatic refresh

### 2. **Clean, Dark UI**
✅ Professional dark theme (#1a1a2e background)
✅ Good contrast and readability
✅ Consistent color scheme (blue, green, yellow, red status colors)

### 3. **Memory Flow Tracking**
✅ Unique feature - shows task-to-task context flow
✅ Helps debug memory issues
✅ Visualizes the "cognitive trail"

### 4. **Collapsible Phases**
✅ Reduces clutter for completed phases
✅ Focus on current work
✅ Good for 10-phase pipeline

### 5. **File Artifacts**
✅ Shows inputs/outputs per task
✅ Inline file viewer
✅ Useful for debugging

---

## Current Gaps & Optimization Opportunities

### 1. **Dashboard Doesn't Launch Early Enough**

**Issue:**
- Dashboard not explicitly launched in Phase 0 early tasks
- Users may not know it exists until later
- Manual launch required: `./dashboard/start-dashboard.sh`

**Impact:** Low visibility, reduced utility during critical setup phase

**Solution Options:**

**A. Launch in Task 001 (Mode Selection)** ✅ RECOMMENDED
```bash
# In phases/phase00/task001.sh, after showing setup guide:

# Auto-launch dashboard for pipeline visibility
if [[ "${ATOMIC_AUTO_DASHBOARD:-true}" == "true" ]]; then
    atomic_substep "Starting pipeline dashboard..."
    bash "$ATOMIC_ROOT/dashboard/start-dashboard.sh" &>/dev/null || true
    sleep 1
    atomic_ref_tasks "Monitor pipeline progress"
fi
```

**B. Launch in orchestrator00.py (before Phase 0)**
```python
# In phases/phase00/orchestrator00.py, in run_phase():

def run_phase(resume_at: str = None) -> bool:
    phase_header("Phase 0: Setup")

    # Launch dashboard before any tasks
    if os.getenv("ATOMIC_AUTO_DASHBOARD", "true") == "true":
        launch_dashboard()

    state = StateManager()
    # ... rest of orchestration
```

**C. Launch in main.py (universal)**
```python
# In main.py run command:

def run_command(args):
    # Launch dashboard for all phase runs
    if args.command == "run" and not args.no_dashboard:
        launch_dashboard()

    # Run the phase
    success = run_phase(args.phase, args.resume_at)
```

**Recommendation:** **Option A** (Task 001) - Most predictable, user sees it immediately

---

### 2. **No Token/Cost Tracking**

**Issue:**
- Dashboard shows provider/model but not token usage
- No running cost estimate
- Important for budget-conscious users

**Impact:** Users can't track API costs in real-time

**Solution:**

**Add Token Tracking API:**
```javascript
// dashboard/server.js - new endpoint:
app.get('/api/tokens', (req, res) => {
  const sessionFile = path.join(STATE_DIR, 'session-tokens.json');
  if (fs.existsSync(sessionFile)) {
    const data = JSON.parse(fs.readFileSync(sessionFile, 'utf8'));
    res.json(data);
  } else {
    res.json({
      total_input_tokens: 0,
      total_output_tokens: 0,
      estimated_cost_usd: 0,
      by_provider: {}
    });
  }
});
```

**Update State Writer (lib/atomic.sh):**
```bash
# In atomic_invoke, after successful completion:
_atomic_log_tokens() {
    local provider="$1"
    local model="$2"
    local input_tokens="$3"
    local output_tokens="$4"

    local token_file="$ATOMIC_STATE_DIR/session-tokens.json"

    # Calculate cost (model-specific rates)
    local cost_usd
    cost_usd=$(_atomic_calculate_cost "$provider" "$model" "$input_tokens" "$output_tokens")

    # Append to token log
    jq --arg provider "$provider" \
       --arg model "$model" \
       --argjson input "$input_tokens" \
       --argjson output "$output_tokens" \
       --argjson cost "$cost_usd" \
       '.total_input_tokens += $input |
        .total_output_tokens += $output |
        .estimated_cost_usd += $cost |
        .by_provider[$provider].tokens += ($input + $output) |
        .by_provider[$provider].cost_usd += $cost' \
       "$token_file" > "$token_file.tmp" && mv "$token_file.tmp" "$token_file"
}
```

**Dashboard UI Addition:**
```html
<div class="token-tracker-box">
  <div class="token-title">Session Tokens & Cost</div>
  <div class="token-grid">
    <div class="token-item">
      <div class="token-label">Input Tokens</div>
      <div class="token-value" id="input-tokens">0</div>
    </div>
    <div class="token-item">
      <div class="token-label">Output Tokens</div>
      <div class="token-value" id="output-tokens">0</div>
    </div>
    <div class="token-item">
      <div class="token-label">Estimated Cost</div>
      <div class="token-value cost" id="estimated-cost">$0.00</div>
    </div>
  </div>
</div>
```

---

### 3. **No Timeline View**

**Issue:**
- Can't see task duration or performance trends
- No way to identify slow tasks
- Can't estimate remaining time

**Impact:** Users don't know if pipeline is performing well

**Solution:**

**Add Timeline Visualization:**
```javascript
// New component: Task Timeline
{
  task_id: "001",
  start_time: "2026-02-10T10:30:00Z",
  end_time: "2026-02-10T10:32:15Z",
  duration_seconds: 135,
  status: "complete"
}
```

**UI: Horizontal Timeline:**
```
Phase 0: Setup
├─ 001: Setup Validation          [██████] 15s  ✓
├─ 002: Config Collection          [████████████] 45s  ✓
├─ 003: Config Review              [██] 8s  ✓
├─ 004: API Keys                   [████] 12s  ✓
└─ 005: Material Scan              [██████████████████] ⏳ 67s (in progress)
```

**Benefits:**
- Visual performance tracking
- Identify bottlenecks
- Estimate completion time
- Historical comparison

---

### 4. **No Agent Visibility**

**Issue:**
- Dashboard doesn't show which agents are being used
- No link to agent repository
- Missing agent selection tracking

**Impact:** Users don't see the "AI workforce" at work

**Solution:**

**Add Agent Tracking Panel:**
```html
<div class="agents-panel">
  <div class="panel-title">🤖 Active Agents</div>
  <div class="agent-list">
    <div class="agent-item">
      <div class="agent-role">Discovery Lead</div>
      <div class="agent-name">corpus-collector</div>
      <div class="agent-status">✓ Completed Task 102</div>
    </div>
    <div class="agent-item active">
      <div class="agent-role">Analysis</div>
      <div class="agent-name">dialogue-architect</div>
      <div class="agent-status">⏳ Working on Task 105</div>
    </div>
  </div>
  <div class="agent-footer">
    <a href="http://localhost:5175/agents" target="_blank">
      Browse 221 available agents →
    </a>
  </div>
</div>
```

**Benefits:**
- Shows AI collaboration in action
- Links to agent dashboards (5175, 5176)
- Makes system more transparent

---

### 5. **No Audit Integration**

**Issue:**
- 2,186 audits available but not surfaced in dashboard
- No proactive audit suggestions
- Users may not know audits exist

**Impact:** Powerful quality tool goes unused

**Solution:**

**Add Audit Suggestions:**
```javascript
// Based on current task, suggest relevant audits
const auditSuggestions = {
  "0-setup": [
    "Configuration Validation",
    "Environment Security Check",
    "API Key Security Audit"
  ],
  "1-discovery": [
    "Corpus Quality Analysis",
    "Feature Extraction Audit",
    "Requirements Completeness Check"
  ],
  "5-implementation": [
    "Code Quality Audit",
    "Security Vulnerability Scan",
    "Test Coverage Analysis"
  ]
};
```

**UI: Audit Sidebar:**
```html
<div class="audit-suggestions">
  <div class="audit-title">📋 Recommended Audits</div>
  <div class="audit-list">
    <div class="audit-item">
      <div class="audit-name">Configuration Validation</div>
      <button class="audit-run-btn">Run Audit</button>
    </div>
  </div>
  <a href="http://localhost:5176/audits">Browse all 2,186 audits →</a>
</div>
```

**Benefits:**
- Proactive quality checks
- Educates users about audit library
- Reduces defects

---

### 6. **No Skill Visibility**

**Issue:**
- 85 skills available but not shown in dashboard
- No indication when skills are used
- Users don't see skill invocations

**Impact:** Skills are invisible, underutilized

**Solution:**

**Add Skill Tracking:**
```javascript
// Track skill invocations in current-task.json
{
  "description": "PRD Gen 3: Feature Requirements",
  "provider": "max",
  "model": "sonnet",
  "skills_used": [
    "/writing-plans",
    "/executing-plans"
  ],
  "skill_invocations": 2
}
```

**UI: Skills Panel:**
```html
<div class="skills-panel">
  <div class="panel-title">⚡ Skills Used This Session</div>
  <div class="skill-badges">
    <span class="skill-badge">/writing-plans (3)</span>
    <span class="skill-badge">/test-driven-development (1)</span>
    <span class="skill-badge">/audit-context-building (2)</span>
  </div>
  <div class="skill-footer">
    85 skills available · <a href="#">Browse skills →</a>
  </div>
</div>
```

**Benefits:**
- Shows when LLM uses skills
- Validates skill integration
- Educates users about available skills

---

### 7. **No Error Highlighting**

**Issue:**
- Failed tasks don't stand out enough
- No error details in dashboard
- Users must check logs manually

**Impact:** Errors go unnoticed, debugging is slow

**Solution:**

**Add Error Panel:**
```html
<div class="error-panel" id="error-panel" style="display: none;">
  <div class="error-header">
    <span class="error-icon">⚠️</span>
    <span class="error-title">Task 305 Failed</span>
    <button class="error-dismiss">✕</button>
  </div>
  <div class="error-details">
    <div class="error-message">
      Dependency validation failed: circular dependency detected between FR-012 and FR-034
    </div>
    <div class="error-actions">
      <button class="error-retry">Retry Task</button>
      <button class="error-logs">View Full Logs</button>
      <button class="error-skip">Skip & Continue</button>
    </div>
  </div>
</div>
```

**Error Log API:**
```javascript
// dashboard/server.js
app.get('/api/errors', (req, res) => {
  const errorLog = path.join(ATOMIC_ROOT, '.logs', 'errors.json');
  if (fs.existsSync(errorLog)) {
    res.json(JSON.parse(fs.readFileSync(errorLog, 'utf8')));
  } else {
    res.json({ errors: [] });
  }
});
```

**Benefits:**
- Immediate error visibility
- Quick access to error details
- Actionable recovery options

---

## Innovative Features (Blue-Sky Ideas)

### 1. **AI Progress Narrator** 🎯

**Concept:** Real-time natural language updates

**UI:**
```
┌─────────────────────────────────────────┐
│ 🤖 What's happening right now:          │
│                                          │
│ Claude is analyzing your codebase to    │
│ identify common patterns and extract    │
│ feature requirements. The corpus-       │
│ collector agent found 47 source files   │
│ and is now categorizing them by         │
│ functionality.                           │
│                                          │
│ ⏱️  This typically takes 2-3 minutes    │
└─────────────────────────────────────────┘
```

**Benefits:**
- Less technical, more accessible
- Keeps users engaged during long tasks
- Explains what's actually happening

---

### 2. **Confidence Meter** 🎯

**Concept:** Show LLM confidence in current output

**UI:**
```
┌─────────────────────────────────────────┐
│ 📊 Output Confidence                    │
│                                          │
│ Feature Requirements (Section 3)        │
│ ████████████████████░░ 85%              │
│                                          │
│ High confidence in FR-001 through       │
│ FR-028. FR-029 to FR-035 may need      │
│ human review due to ambiguous           │
│ requirements in discovery phase.        │
└─────────────────────────────────────────┘
```

**Implementation:**
- Parse LLM output for uncertainty markers
- Track revision cycles (more revisions = lower confidence)
- Guardian agent feedback integration

**Benefits:**
- Identifies sections needing human review
- Improves PRD quality
- Reduces downstream rework

---

### 3. **3D Phase Flow Visualization** 🎯

**Concept:** Animated 3D pipeline view

**Tech:** Three.js or D3.js

**Visualization:**
```
     [0]─────[1]─────[2]─────[3]─────[4]
      │       │       │       │       │
    Setup Discovery PRD  Tasking Spec
      ✓       ✓       ⏳      ○       ○
                      ↑
                   Current
```

**Interactions:**
- Click phase to zoom in
- Hover for tooltips
- Rotate/pan for exploration
- Color-coded by status

**Benefits:**
- Visually stunning
- Intuitive pipeline understanding
- Great for demos/presentations

---

### 4. **Dependency Graph Viewer** 🎯

**Concept:** Interactive task dependency DAG

**UI:**
```
          ┌──────┐
          │ F0   │ Foundation
          └──┬───┘
             │
       ┌─────┴─────┐
       │           │
    ┌──▼──┐     ┌─▼───┐
    │ F1  │     │ F2  │
    │Auth │     │Tasks│
    └──┬──┘     └──┬──┘
       │           │
       └─────┬─────┘
             │
          ┌──▼──┐
          │ F3  │
          │Tests│
          └─────┘
```

**Benefits:**
- Visualize task relationships
- Identify critical path
- Detect circular dependencies
- Show parallel opportunities

---

### 5. **Embedded Chat Assistant** 🎯

**Concept:** AI helper in dashboard

**UI:**
```
┌─────────────────────────────────────────┐
│ 💬 Ask Claude about your pipeline      │
│                                          │
│ You: Why did task 305 fail?             │
│                                          │
│ Claude: Task 305 (Dependency Mapping)   │
│ failed because FR-034 references        │
│ FR-012 as a dependency, but FR-012      │
│ also references FR-034, creating a      │
│ circular dependency. To fix this,       │
│ review Section 5 of your PRD and        │
│ break the cycle by introducing an       │
│ intermediary feature.                   │
│                                          │
│ [View PRD Section 5] [Retry Task]      │
└─────────────────────────────────────────┘
```

**Features:**
- Context-aware (knows current task)
- Suggests fixes
- Links to relevant docs
- Powered by Haiku (fast, cheap)

**Benefits:**
- Self-serve debugging
- Reduces context switching
- Improves learning curve

---

### 6. **Performance Benchmarks** 🎯

**Concept:** Compare against typical runs

**UI:**
```
┌─────────────────────────────────────────┐
│ ⚡ Performance vs Average               │
│                                          │
│ Phase 1: Discovery                       │
│   Your time:    8m 34s                  │
│   Typical:      6m 15s (25% slower)     │
│   Best:         4m 52s                  │
│                                          │
│ Slowest task: 102 (Corpus Collection)  │
│   Your time:    5m 12s                  │
│   Typical:      2m 45s                  │
│   Reason:       Large codebase (500+    │
│                 files) - expected       │
└─────────────────────────────────────────┘
```

**Benefits:**
- Identifies performance outliers
- Sets expectations
- Helps optimize slow tasks

---

### 7. **Export Pipeline Report** 🎯

**Concept:** Generate shareable pipeline summary

**Features:**
- PDF/HTML export
- Timeline visualization
- Key metrics (tokens, cost, duration)
- Task summaries
- Agent assignments
- Memory flow diagram
- Error log
- Output artifacts

**Use Cases:**
- Share with team
- Document process
- Compliance/audit trail
- Process improvement analysis

**UI:**
```
┌─────────────────────────────────────────┐
│ 📄 Export Pipeline Report              │
│                                          │
│ Format: [●] PDF  [ ] HTML  [ ] JSON    │
│                                          │
│ Include:                                 │
│ [✓] Timeline & Metrics                  │
│ [✓] Agent Assignments                   │
│ [✓] Task Summaries                      │
│ [✓] Memory Flow                         │
│ [ ] File Artifacts (large)              │
│ [✓] Error Log                           │
│                                          │
│ [Generate Report]                       │
└─────────────────────────────────────────┘
```

---

## Implementation Priority Matrix

| Feature | Impact | Effort | Priority |
|---------|--------|--------|----------|
| **Launch Dashboard Earlier** | 🔴 High | 🟢 Low | **P0 - Critical** |
| **Error Highlighting** | 🔴 High | 🟡 Medium | **P0 - Critical** |
| **Token/Cost Tracking** | 🟡 Medium | 🟡 Medium | **P1 - High** |
| **Timeline View** | 🟡 Medium | 🟡 Medium | **P1 - High** |
| **Agent Visibility** | 🟡 Medium | 🟢 Low | **P1 - High** |
| **Audit Integration** | 🟡 Medium | 🟡 Medium | **P2 - Medium** |
| **Skill Tracking** | 🟢 Low | 🟢 Low | **P2 - Medium** |
| **AI Progress Narrator** | 🟢 Low | 🔴 High | **P3 - Nice-to-have** |
| **Confidence Meter** | 🟡 Medium | 🔴 High | **P3 - Nice-to-have** |
| **3D Visualization** | 🟢 Low | 🔴 High | **P4 - Future** |
| **Dependency Graph** | 🟡 Medium | 🔴 High | **P3 - Nice-to-have** |
| **Chat Assistant** | 🟡 Medium | 🔴 High | **P4 - Future** |
| **Performance Benchmarks** | 🟢 Low | 🔴 High | **P4 - Future** |
| **Export Report** | 🟡 Medium | 🟡 Medium | **P2 - Medium** |

---

## Recommended Immediate Actions

### 1. **Launch Dashboard in Task 001** (30 minutes)
- Add auto-launch code to phases/phase00/task001.sh
- Add ATOMIC_AUTO_DASHBOARD env var
- Test with fresh Phase 0 run

### 2. **Add Error Panel** (2 hours)
- Create error-panel HTML component
- Add /api/errors endpoint
- Highlight failed tasks in UI
- Add error.json logging to atomic.sh

### 3. **Add Token Tracker** (3 hours)
- Implement session-tokens.json logging
- Add /api/tokens endpoint
- Create token-tracker UI component
- Calculate costs by provider/model

### 4. **Add Agent Panel** (1 hour)
- Parse selected-agents.json from .outputs/
- Create agents-panel component
- Link to agent dashboards (5175, 5176)
- Show active agent for current task

### 5. **Improve Session Status** (30 minutes)
- Make stale detection more prominent
- Add estimated remaining time
- Show last N completed tasks
- Add "Resume Pipeline" button for stale sessions

**Total Effort:** ~7 hours for high-impact improvements

---

## Questions for Discussion

1. **Dashboard Launch:** Should it auto-launch in Task 001, orchestrator, or main.py?
2. **Token Tracking:** Is cost tracking a priority? Which providers need rate data?
3. **Error Handling:** Should dashboard offer retry/skip actions, or just display errors?
4. **Agent Visibility:** How deep should agent integration go? (just names vs full agent details)
5. **Audit Integration:** Should audits be passive suggestions or active "run this now" buttons?
6. **UI Framework:** Consider React/Vue/Svelte for future? Or keep vanilla JS?
7. **3D Visualization:** Worth the effort, or stick with 2D?

---

## Conclusion

The dashboard is **well-architected** with solid real-time capabilities and good UX foundations. The main gaps are:

1. **Visibility** - Launch earlier, make it more prominent
2. **Actionability** - Error handling, suggested actions
3. **Transparency** - Show tokens, agents, skills, audits
4. **Performance** - Timeline view, benchmarks

**Top Priority:** Launch dashboard in Task 001 so users see it immediately and understand pipeline progress from the start.

**Quick Wins:** Error panel, token tracker, agent visibility (< 1 day of work, high impact)

**Future Vision:** AI narrator, 3D flow, chat assistant (months of work, impressive but not critical)

---

*Ready to discuss specific features and start implementation!* 🚀
