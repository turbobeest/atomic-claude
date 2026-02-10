# Dashboard Innovations - Detailed Specifications

**Date:** February 10, 2026
**Status:** Design & Planning Phase

---

## 1. 🌐 3D Phase Flow Visualization

### Concept

An **interactive 3D pipeline visualization** that shows all 10 phases as connected nodes in 3D space, with real-time status updates, smooth transitions, and cinematic camera movements.

### Technology Stack

**Option A: Three.js (Recommended)**
- Industry standard for 3D web graphics
- 100K+ GitHub stars, mature ecosystem
- Excellent performance, WebGL-based
- Rich examples and documentation

**Option B: D3.js with CSS3D**
- Leverages existing D3 knowledge
- Lightweight (no WebGL dependency)
- Good for simpler 3D layouts
- Easier learning curve

**Recommendation:** **Three.js** for rich, professional 3D effects

### Visual Design

```
           Phase 0 (Setup)
               ●━━━━┓
                    ┃
           Phase 1  ┃  Phase 2
           (Disc.) ●━━━● (PRD)
                 ╱    ┃ ╲
                ╱     ┃  ╲
        Phase 3●      ┃   ●Phase 4
        (Task)  ╲     ┃   ╱ (Spec)
                 ╲    ●  ╱
                  ╲ Phase 5 (Impl)
                   ╲  ┃  ╱
                 Phase 6 (Review)
                      ●
                      ┃
                  Phase 7-9
                   ●━●━●
                   ↑
               (Branch/merge/deploy)
```

### 3D Layout Strategies

**Strategy 1: Linear Pipeline (Horizontal)**
```
0 ──→ 1 ──→ 2 ──→ 3 ──→ 4 ──→ 5 ──→ 6 ──→ 7 ──→ 8 ──→ 9
```
- Simple, easy to understand
- Good for first-time users
- Shows clear progression
- Can rotate/zoom for depth

**Strategy 2: Circular Flow**
```
        0 (Setup)
           │
    9 ─────┼───── 1
   ╱       │       ╲
  8        │        2
  │        5        │
  7        │        3
   ╲       │       ╱
    6 ─────┼───── 4
           │
       (Center = Current)
```
- Emphasizes cyclical nature (can restart pipeline)
- Current phase at center (spotlight effect)
- Beautiful aesthetic
- Good for recurring builds

**Strategy 3: Helix/Spiral (🎯 RECOMMENDED)**
```
         0 (start)
        ╱
       1
      ╱
     2
    ╱
   3 ─── (ascending spiral)
  ╱
 4
╱
5 (implementation at peak)
╲
 6 (descending - review)
  ╲
   7
    ╲
     8
      ╲
       9 (deploy at bottom)
```

**Benefits:**
- Shows progression AND hierarchy
- Implementation (5) at peak = most critical
- Review/deploy descending = wind-down
- Visually stunning
- Natural camera path

### Node Styling

**Node Appearance:**
- **Sphere geometry** for phase nodes
- **Size based on status:**
  - Current: Large (2x)
  - Complete: Medium (1x)
  - Pending: Small (0.7x)
  - Planned: Tiny (0.4x), transparent

- **Color coding:**
  - Complete: Green (#22c55e) + glow
  - In-progress: Yellow (#eab308) + pulsing animation
  - Pending: Blue (#64748b)
  - Planned: Gray (#374151), semi-transparent
  - Failed: Red (#dc2626) + shake animation

- **Glow effects:**
  - Bloom post-processing for completed phases
  - Pulsing shader for current phase
  - Particle effects for active work

### Connections

**Edge Rendering:**
- Tube geometry for connections (not flat lines)
- Animated flow particles (data flowing forward)
- Color matches source node
- Thickness based on data transferred
- Dashed lines for not-yet-started phases

**Flow Animation:**
```javascript
// Particles flow from completed → current phase
class FlowParticle {
  position: Vector3
  speed: float
  color: Color
  trail: Vector3[]
}

// 10-20 particles per edge
// Speed: 0.5 units/second
// Trail length: 5 previous positions
// Fade out at end
```

### Camera Controls

**Auto-Camera Modes:**

**1. Orbit Mode (Default)**
- Slow rotation around entire pipeline
- Speed: 5 degrees/second
- Height: Slightly above center
- Good for ambient display

**2. Focus Mode**
- Zoom to current phase
- Rotate around that node
- Show task details in HUD
- Triggered automatically when phase starts

**3. Journey Mode**
- Camera follows completed path
- Smooth transitions between phases
- "Story" of the pipeline
- Great for demos/presentations

**Manual Controls:**
- Mouse drag: Rotate view
- Scroll: Zoom in/out
- Click node: Focus on that phase
- Double-click: Enter "detail view"

### Interactive Elements

**Node Interactions:**
- **Hover:** Show tooltip with phase info
  ```
  Phase 1: Discovery
  Status: Complete ✓
  Duration: 8m 34s
  Tasks: 10/10
  Cost: $2.47
  ```

- **Click:** Zoom to phase, show task list
- **Double-click:** Open 2D task view (current dashboard)
- **Right-click:** Phase actions menu
  - View outputs
  - Retry phase
  - Skip phase
  - Export report

**Task Subnodes:**
- When zoomed to phase, show task nodes as smaller spheres orbiting
- Task completion = orbit animation
- Failed task = red glow + stop orbiting

### HUD Overlay

**On-screen information:**
```
┌─────────────────────────────────────────────┐
│  Atomic Claude Pipeline - 3D View          │
│                                             │
│  Current: Phase 5 - Implementation ⏳      │
│  Progress: 5/10 phases (50%)               │
│  Time: 2h 15m                              │
│  Cost: $12.34                              │
│                                             │
│  [Controls]                                 │
│  Drag: Rotate  Scroll: Zoom               │
│  Click: Focus  Space: Pause               │
└─────────────────────────────────────────────┘
```

### Animations & Effects

**Phase Transition:**
```javascript
// When phase completes:
1. Node changes from yellow → green (0.5s ease)
2. Bloom pulse (expand/contract)
3. Particle burst (100 particles, radial)
4. Next node lights up (yellow glow fade-in)
5. Camera smooth transition to next node (2s ease-in-out)
6. Sound effect (optional: success chime)
```

**Active Task Indication:**
- Subtle rotation of current phase node
- Orbiting task indicator (small sphere)
- Shader pulse effect (breathing)
- Particle stream to/from node (input/output)

**Error State:**
- Node turns red
- Shake animation (0.5s)
- Warning particle effect (red sparks)
- Stop rotation
- Camera zooms to failed node

### Performance Optimization

**Level of Detail (LOD):**
- Close: High-poly spheres (32 segments)
- Medium: Mid-poly (16 segments)
- Far: Low-poly (8 segments)
- Very far: Billboards (flat sprites)

**Culling:**
- Frustum culling (only render visible objects)
- Occlusion culling (don't render hidden nodes)
- Distance culling (fade out distant particles)

**Target Performance:**
- 60 FPS on modern hardware
- 30 FPS on older machines
- Graceful degradation (disable particles if FPS < 30)

### Implementation Estimate

**Phase 1: Basic 3D Scene (Week 1)**
- Three.js setup
- 10 phase nodes in helix layout
- Camera controls (orbit, zoom, pan)
- Basic lighting

**Phase 2: Interactivity (Week 2)**
- Node click/hover handlers
- Tooltip system
- Phase info HUD
- Camera focus transitions

**Phase 3: Real-time Updates (Week 3)**
- SSE integration
- Status color updates
- Task subnodes
- Progress tracking

**Phase 4: Visual Polish (Week 4)**
- Particle systems
- Glow/bloom effects
- Flow animations
- Sound effects

**Total:** 4 weeks for full feature

**Quick MVP:** 1 week for basic interactive 3D view

### Fallback for Non-3D Browsers

**2D SVG Visualization:**
- Same helix layout, but flat
- CSS animations instead of WebGL
- Degrades gracefully
- Still interactive

---

## 2. 🧠 Claude-Mem Localhost Integration

### Discovery

**Found:** claude-mem running on **localhost:37777**

**Process Details:**
```bash
bun /Users/jamesterbeest/.claude/plugins/cache/thedotmack/claude-mem/9.0.12/scripts/worker-service.cjs --daemon
```

**Current Status:**
- ✅ Service running
- ❌ Viewer UI not found ("Viewer UI not found at any expected location")
- ❓ API endpoints unknown

### Investigation Needed

**Questions:**
1. What API endpoints does claude-mem expose?
2. Is there a separate viewer UI to install?
3. How to query memories programmatically?
4. What data format does it return?

### Proposed Integration

**Architecture:**
```
Dashboard (Port 5174)
    ↓ HTTP requests
claude-mem API (Port 37777)
    ↓ reads from
~/.claude-mem/vector-db (ChromaDB)
```

**New Dashboard Tab: "Memory Explorer"**

```html
<div class="tab-content" id="memory-tab">
  <div class="memory-explorer">
    <div class="memory-search">
      <input type="text" placeholder="Search memories...">
      <button>Search</button>
    </div>

    <div class="memory-timeline">
      <!-- Chronological list of saved memories -->
      <div class="memory-entry">
        <div class="memory-meta">
          <span class="memory-phase">Phase 1</span>
          <span class="memory-task">Task 102</span>
          <span class="memory-time">2h ago</span>
        </div>
        <div class="memory-content">
          Identified 47 source files in corpus...
        </div>
        <div class="memory-actions">
          <button>View Full</button>
          <button>Export</button>
        </div>
      </div>
      <!-- More entries... -->
    </div>
  </div>
</div>
```

### API Integration Plan

**Step 1: Reverse Engineer API**
```bash
# Test common endpoints
curl http://localhost:37777/memories
curl http://localhost:37777/api/list
curl http://localhost:37777/query
curl http://localhost:37777/search?q=test

# Check WebSocket support
wscat -c ws://localhost:37777
```

**Step 2: Create Proxy Endpoint**
```javascript
// dashboard/server.js
app.get('/api/claude-mem/memories', async (req, res) => {
  try {
    const response = await fetch('http://localhost:37777/memories');
    const data = await response.json();
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: 'claude-mem not available' });
  }
});

app.get('/api/claude-mem/search', async (req, res) => {
  const query = req.query.q;
  try {
    const response = await fetch(`http://localhost:37777/search?q=${query}`);
    const data = await response.json();
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: 'Search failed' });
  }
});
```

**Step 3: Build UI**
```javascript
// Fetch memories
async function loadMemories() {
  const response = await fetch('/api/claude-mem/memories');
  const memories = await response.json();

  // Render memory timeline
  renderMemoryTimeline(memories);
}

// Search memories
async function searchMemories(query) {
  const response = await fetch(`/api/claude-mem/search?q=${encodeURIComponent(query)}`);
  const results = await response.json();

  // Highlight search results
  renderSearchResults(results);
}
```

### Features

**1. Memory Timeline**
- Chronological view of all saved memories
- Filter by phase/task
- Search by content
- Export selected memories

**2. Memory Graph**
- Visual graph of memory relationships
- Nodes = memories
- Edges = references/dependencies
- Interactive exploration

**3. Memory Stats**
- Total memories saved
- Storage used
- Most-referenced memories
- Memory growth over time

**4. Memory Search**
- Full-text search across all memories
- Filter by date range, phase, task
- Semantic search (if supported by claude-mem)
- Export search results

### Benefits

- **Transparency:** See what Claude remembers
- **Debugging:** Track context flow issues
- **Audit Trail:** Complete memory history
- **Learning:** Understand how AI uses memory

**Replaces:** Current "Memory System Stats" card (local file counting)

---

## 3. 💬 Ask Claude Chatbot (Embedded Assistant)

### Concept

An **AI-powered chat assistant** embedded in the dashboard that can answer questions about:
- Why tasks failed
- How to fix errors
- What's happening now
- Pipeline best practices
- Interpret outputs

### Technology

**Model:** Claude 3.5 Haiku (fast, cheap, context-aware)

**Context Sources:**
1. Current task state
2. Recent task outputs
3. Error logs
4. Phase documentation
5. Task scripts (for technical questions)

### UI Design

**Chat Widget (Bottom-right corner):**
```
┌─────────────────────────────────────────┐
│ 💬 Ask Claude                     [─][×]│
├─────────────────────────────────────────┤
│                                          │
│ You: Why did task 305 fail?             │
│                                          │
│ Claude: Task 305 (Dependency Mapping)   │
│ failed because FR-034 references        │
│ FR-012 as a dependency, but FR-012      │
│ also references FR-034, creating a      │
│ circular dependency.                    │
│                                          │
│ To fix this:                            │
│ 1. Open docs/prd/PRD.md Section 5      │
│ 2. Review FR-012 and FR-034            │
│ 3. Break cycle with intermediary       │
│                                          │
│ [View PRD §5] [Retry Task 305]         │
│                                          │
├─────────────────────────────────────────┤
│ Ask a question...              [Send] │
└─────────────────────────────────────────┘
```

**Collapsed State:**
```
┌──────────────┐
│ 💬 Ask Claude│
└──────────────┘
```

### Example Conversations

**Q: "What's happening now?"**
```
Claude is currently running Task 205 (PRD Authoring -
Generation 3). It's analyzing the discovery artifacts
from Phase 1 to extract feature requirements for Section
3 of the PRD.

This typically takes 2-3 minutes. The model is using
Claude Opus 4.6 with 1M context window to ensure all
prior sections are considered.

Progress: 25% (3/12 generations complete)
```

**Q: "How much is this costing me?"**
```
So far this session:
• Input tokens: 245,328
• Output tokens: 18,492
• Estimated cost: $4.23

Based on current usage, the full pipeline will cost
approximately $15-20. Phase 2 (PRD) is the most expensive
due to multiple generations with large context.

[View detailed breakdown]
```

**Q: "Can I skip Phase 4?"**
```
Phase 4 (Specification) can be skipped if you have very
detailed feature requirements in your PRD. However,
skipping it means:

❌ No formal test specifications
❌ TDD may be less effective
❌ Implementation may deviate from intent

✅ Recommended: Run Phase 4 (adds ~30 minutes, $3-5)
⚠️  Caution: Only skip for prototypes/MVPs

[Skip anyway] [Continue with Phase 4]
```

**Q: "Show me the last 5 tasks"**
```
Recent tasks:
✓ 203 - PRD Structure (2m 14s)
✓ 204 - PRD Interview (8m 45s)
✓ 205 - PRD Authoring (24m 12s)
✓ 206 - PRD Validation (3m 08s)
⏳ 207 - PRD Approval (in progress)

[View full task history]
```

### Actionable Responses

**Smart Buttons:**
- `[View PRD §5]` → Opens file viewer to that section
- `[Retry Task 305]` → Triggers task retry
- `[View logs]` → Opens log viewer
- `[Export report]` → Generates task report
- `[Skip Phase 4]` → Updates pipeline config

### Implementation

**Backend:**
```javascript
// dashboard/server.js
app.post('/api/chat', async (req, res) => {
  const { message, context } = req.body;

  // Build context from current state
  const systemContext = buildChatContext();

  // Call Claude API (Haiku for speed/cost)
  const response = await callClaudeAPI({
    model: 'claude-3-5-haiku-20241022',
    system: systemContext,
    messages: [{ role: 'user', content: message }],
    max_tokens: 500
  });

  // Extract action buttons from response
  const actions = extractActions(response.content);

  res.json({
    message: response.content,
    actions: actions
  });
});

function buildChatContext() {
  const currentTask = readCurrentTask();
  const taskState = readTaskState();
  const recentErrors = readRecentErrors();

  return `You are an AI assistant helping users understand their Atomic Claude pipeline.

Current state:
- Phase: ${currentTask.phase}
- Task: ${currentTask.task_id}
- Status: ${currentTask.status}
- Recent errors: ${recentErrors.length}

Be concise, helpful, and actionable. Suggest specific fixes when tasks fail.`;
}
```

**Frontend:**
```javascript
// Chat widget
class ChatWidget {
  constructor() {
    this.messages = [];
    this.collapsed = true;
  }

  async sendMessage(text) {
    this.messages.push({ role: 'user', content: text });

    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        context: getCurrentContext()
      })
    });

    const data = await response.json();
    this.messages.push({ role: 'assistant', content: data.message });

    this.render();
  }
}
```

### Cost Control

**Rate Limiting:**
- Max 10 messages/minute
- Max 100 messages/session
- Warn when approaching limits

**Context Optimization:**
- Only send essential context
- Summarize long outputs
- Cache common responses

**Estimated Cost:**
- $0.01 per question (Haiku pricing)
- ~$1 per typical session (100 questions)
- Negligible compared to pipeline cost

---

## 4. 📊 Confidence Meter

### Concept

Show **LLM confidence** in generated outputs, helping users identify sections that need human review.

### Confidence Sources

**1. Uncertainty Markers in Output**
```
Low confidence phrases:
- "may", "might", "possibly", "perhaps"
- "unclear", "ambiguous", "uncertain"
- "could be", "seems like", "appears to"
- "I think", "I believe", "probably"

High confidence phrases:
- "will", "must", "shall", "definitely"
- "clearly", "obviously", "certainly"
- "confirmed", "verified", "established"
```

**2. Revision Cycles**
- First generation: 90% confidence (fresh)
- After 1 revision: 75% confidence
- After 2+ revisions: 50% confidence
- More revisions = more uncertainty

**3. Guardian Agent Feedback**
- If guardian approves: +10% confidence
- If guardian requests changes: -20% confidence
- Multiple guardian rejections: 30% confidence

**4. Token Ratios**
- High output/input ratio: High confidence (elaborative)
- Low output/input ratio: Low confidence (struggling)

**5. Response Time**
- Fast responses: Higher confidence
- Slow responses with low tokens: Lower confidence

### UI Design

**Section-Level Confidence:**
```html
<div class="confidence-card">
  <div class="confidence-header">
    <span class="confidence-label">PRD Section 3: Feature Requirements</span>
    <span class="confidence-score">85%</span>
  </div>

  <div class="confidence-bar">
    <div class="confidence-fill" style="width: 85%"></div>
  </div>

  <div class="confidence-details">
    <p>High confidence in FR-001 through FR-028.</p>
    <p class="confidence-warning">
      ⚠️  FR-029 to FR-035 may need human review due to
      ambiguous requirements in discovery phase.
    </p>
  </div>

  <div class="confidence-actions">
    <button>Review Low-Confidence Items</button>
    <button>Re-generate Section</button>
  </div>
</div>
```

**Color Coding:**
- 90-100%: Green (#22c55e) - Excellent
- 70-89%: Blue (#60a5fa) - Good
- 50-69%: Yellow (#eab308) - Review recommended
- 0-49%: Red (#dc2626) - Human review required

### Per-Task Confidence Tracking

```json
{
  "task_id": "205",
  "task_name": "PRD Authoring",
  "confidence": {
    "overall": 82,
    "by_section": {
      "section_1": { "score": 95, "issues": [] },
      "section_2": { "score": 88, "issues": [] },
      "section_3": { "score": 75, "issues": [
        "FR-029: Ambiguous priority",
        "FR-031: Unclear dependency"
      ]},
      "section_4": { "score": 91, "issues": [] }
    },
    "revision_count": 1,
    "guardian_approved": true
  }
}
```

---

## 5. 🕸️ Interactive Dependency Graph

### Concept

**Visual DAG (Directed Acyclic Graph)** showing task dependencies, critical path, and parallel opportunities.

### Technology

**D3.js Force-Directed Graph** (recommended)
- Natural clustering
- Interactive drag/zoom
- Edge routing
- Collision detection

### Visual Design

```
    F0 (Foundation)
      │
      ├─────────┐
      │         │
      F1        F2
    (Auth)    (Tasks)
      │         │
      ├─────────┤
      │         │
      F3        F4
   (Profile)  (Search)
      │         │
      └────┬────┘
           │
        F5 (Tests)
```

### Node Types

**Foundation (F0):**
- Large node, gray
- Always at top
- No dependencies

**Feature Nodes (F1-FN):**
- Medium nodes
- Color by status
- Size by complexity

**Test Nodes (T1-TN):**
- Small nodes, dashed border
- Always depend on features

### Edge Styling

**Dependency Types:**
- Solid line: Hard dependency (must complete first)
- Dashed line: Soft dependency (optional ordering)
- Dotted line: Data dependency (outputs used)

**Edge Colors:**
- Green: Completed dependency
- Yellow: In-progress dependency
- Gray: Not-yet-started
- Red: Blocked by failed task

### Critical Path Highlighting

**Algorithm:**
- Calculate longest path through DAG
- Highlight critical tasks (red border)
- Show estimated completion time
- Identify bottlenecks

```
Critical Path: F0 → F1 → F3 → F5 (8 hours)
Parallel Path: F0 → F2 → F4 (4 hours)

⚡ Opportunity: F2/F4 can run while F1/F3 runs
```

### Interaction

**Hover Node:**
```
F2: Task Management Core
Status: Complete ✓
Duration: 3h 24m
Dependencies: F0 (complete)
Blocks: F4, F5
Parallel with: F1
```

**Click Node:**
- Zoom to node
- Show full task details
- List all dependencies/dependents
- Highlight related paths

**Drag Node:**
- Rearrange layout (aesthetic only)
- Snap to grid option

**Filter Controls:**
- Show only incomplete tasks
- Show only critical path
- Show only blocked tasks
- Highlight parallel opportunities

---

## 6. 📄 Export Pipeline Report

### Concept

Generate **shareable reports** (PDF/HTML/JSON) documenting the entire pipeline run.

### Report Sections

**1. Executive Summary**
- Project name & type
- Pipeline completion: 8/10 phases (80%)
- Total duration: 4h 23m
- Total cost: $18.47
- Status: In Progress

**2. Timeline Visualization**
```
┌────────────────────────────────────────┐
│ Phase 0: Setup        [██] 15m $0.23  │
│ Phase 1: Discovery    [████] 45m $2.15│
│ Phase 2: PRD          [██████] 2h $8.34│
│ Phase 3: Tasking      [██] 24m $1.89  │
│ Phase 4: Spec         [███] 38m $2.47 │
│ Phase 5: Implementation ⏳ (in progress)│
└────────────────────────────────────────┘
```

**3. Phase Details**
- For each phase:
  - Tasks completed
  - Duration breakdown
  - Token usage
  - Key outputs
  - Issues/warnings

**4. Agent Assignments**
```
Discovery Lead: corpus-collector
Analysis: dialogue-architect
PRD Author: prd-guardian
Validator: contract-lawyer
```

**5. Memory Flow Diagram**
```
Phase 0 → (setup.json) → Phase 1
Phase 1 → (corpus, discoveries) → Phase 2
Phase 2 → (PRD) → Phase 3
Phase 3 → (tasks.json) → Phase 4
```

**6. Metrics Summary**
- Total input tokens: 1,245,892
- Total output tokens: 156,483
- Model distribution:
  - Sonnet: 80%
  - Opus: 15%
  - Haiku: 5%
- Error rate: 2.3% (3/130 tasks)

**7. File Artifacts**
- List of all generated files
- Sizes and timestamps
- Links (in HTML version)

**8. Error Log**
- All failed tasks
- Error messages
- Resolution attempts
- Final outcome

**9. Recommendations**
- Performance optimizations
- Cost reduction opportunities
- Quality improvements
- Next steps

### Export Formats

**PDF:**
- Professional formatting
- Charts and graphs
- Suitable for sharing with stakeholders
- Tool: jsPDF or puppeteer

**HTML:**
- Interactive charts (Chart.js)
- Collapsible sections
- Clickable links to artifacts
- Self-contained (embedded CSS/JS)

**JSON:**
- Complete structured data
- For programmatic analysis
- API integration
- Machine-readable

**Markdown:**
- Plain text format
- Version control friendly
- Easy to edit/customize

### Generation

```javascript
// dashboard/server.js
app.get('/api/export/report', async (req, res) => {
  const format = req.query.format || 'pdf';

  // Gather all data
  const report = {
    summary: generateSummary(),
    timeline: generateTimeline(),
    phases: generatePhaseDetails(),
    agents: getAgentAssignments(),
    memory: getMemoryFlow(),
    metrics: calculateMetrics(),
    files: listArtifacts(),
    errors: getErrorLog(),
    recommendations: generateRecommendations()
  };

  // Generate format-specific output
  switch (format) {
    case 'pdf':
      const pdf = await generatePDF(report);
      res.setHeader('Content-Type', 'application/pdf');
      res.setHeader('Content-Disposition', 'attachment; filename="pipeline-report.pdf"');
      res.send(pdf);
      break;

    case 'html':
      const html = generateHTML(report);
      res.setHeader('Content-Type', 'text/html');
      res.send(html);
      break;

    case 'json':
      res.json(report);
      break;

    case 'markdown':
      const md = generateMarkdown(report);
      res.setHeader('Content-Type', 'text/plain');
      res.setHeader('Content-Disposition', 'attachment; filename="pipeline-report.md"');
      res.send(md);
      break;
  }
});
```

---

## Implementation Roadmap

### Week 1: Foundation
- ✅ Dashboard auto-launch (DONE)
- ✅ Aesthetic improvements (DONE)
- 🔄 Error highlighting panel (IN PROGRESS)
- 🔄 Token/cost tracking (IN PROGRESS)

### Week 2: Quick Wins
- Agent visibility panel
- Timeline view
- Skill tracking
- Audit suggestions

### Week 3: claude-mem Integration
- Reverse engineer API
- Build proxy endpoints
- Create Memory Explorer UI
- Replace Memory Stats card

### Week 4: Advanced Features - Part 1
- AI Progress Narrator
- Confidence Meter
- Export Report (PDF/HTML)

### Weeks 5-6: Advanced Features - Part 2
- Dependency Graph (D3.js)
- Ask Claude Chatbot

### Weeks 7-8: 3D Visualization
- Three.js setup
- Helix layout
- Interactive controls
- Particle effects

---

## Questions & Decisions Needed

1. **3D Phase Flow:** Helix layout vs Circular vs Linear?
2. **claude-mem:** Need help reverse engineering API - can user provide plugin docs?
3. **Chatbot:** Should it have access to code? (security implications)
4. **Confidence Meter:** Should it block progression on low confidence?
5. **Export Report:** Which format is most important? (PDF? HTML?)
6. **Priority:** Which feature to implement first after quick wins?

---

*Ready to start implementing! What's your top priority?* 🚀
