# Tasks Dashboard - Quick Start

## TL;DR

The verbose CLI task headers are **gone**. All diagnostic info now lives in a **real-time web dashboard**.

## How to Use

### 1. Start Your Project

```bash
cd /Users/jamesterbeest/dev/test-project
./ATOMIC-CLAUDE/main.sh run 0
```

The dashboard **auto-starts** when Phase 0 begins.

### 2. Open the Dashboard

Open in your browser: **http://localhost:5173**

You'll see:
- 🟢 **Live status box** with current task details
- 📊 **Task history** showing all completed/pending tasks
- ⚡ **Real-time updates** as tasks execute
- ⓘ **Commands cheatsheet** (click the info button or press `?`)

### 3. Run Tasks

As ATOMIC CLAUDE executes tasks, the dashboard updates **automatically** showing:

- What provider is being used (Max/API/Bedrock/Ollama)
- Which model is running
- Service status (online/offline)
- Network mode (CUI/Internet)
- Context window, cost tier, timeout
- Current phase and task number

### Manual Start (If Needed)

```bash
cd /Users/jamesterbeest/dev/atomic-claude
./scripts/start-dashboard.sh
```

## What You'll See

### In the CLI (Simplified ✨)

**Before**:
```
  ╶─── Extract configuration from setup ───────────────────
    provider  max            model     sonnet        ● online
    context   200K           cost      medium        role  primary
    host      CLAUDECODE     timeout   300s
    prompt    .outputs/.../prompt.md
    output    .outputs/.../extracted-config.json
  ╶─────────────────────────────────────────────────────────
```

**After**:
```
  ▶ Extract configuration from setup (max/sonnet)
```

### In the Dashboard (Rich Details 🎨)

```
┌─────────────────────────────────────────────────────┐
│ ● Task Running                      10:30:45 AM     │
├─────────────────────────────────────────────────────┤
│ Extract configuration from setup                    │
├─────────────────────────────────────────────────────┤
│ PROVIDER       │ SERVICE STATUS │ NETWORK MODE     │
│ MAX            │ ● ONLINE       │ [CUI]            │
├────────────────┼────────────────┼──────────────────┤
│ MODEL          │ CONTEXT WINDOW │ COST TIER        │
│ sonnet         │ 200K           │ MEDIUM           │
├────────────────┼────────────────┼──────────────────┤
│ ROLE           │ TIMEOUT        │ HOST             │
│ primary        │ 300s           │ CLAUDECODE       │
├────────────────┼────────────────┼──────────────────┤
│ PHASE          │ TASK ID        │                  │
│ 0-setup        │ 002            │                  │
└─────────────────────────────────────────────────────┘
```

## Architecture

```
┌─────────────┐    writes      ┌──────────────────┐
│   Task      │───────────────▶│ current-task.json│
│  Execution  │                └────────┬─────────┘
└─────────────┘                         │
                                        │ watches
                                        │
                               ┌────────▼─────────┐
                               │   Dashboard      │
                               │   Server (SSE)   │
                               └────────┬─────────┘
                                        │ streams
                                        │
                               ┌────────▼─────────┐
                               │    Browser       │
                               │  (auto-updates)  │
                               └──────────────────┘
```

## Configuration

Everything comes from `setup.md` → flows to dashboard:

- **llm.primary_provider** → Provider field
- **llm.primary_model** → Model field
- **sandbox.network_mode** → Network badge
- Model config from `config/models.json` → Context/Cost

## Benefits

✅ **Clean CLI** - No visual clutter, focus on progress
✅ **Rich diagnostics** - All info available when you need it
✅ **Real-time** - See exactly what's happening live
✅ **History** - Track all tasks across the pipeline
✅ **Multi-screen** - CLI on one screen, dashboard on another
✅ **Shareable** - LAN access for team visibility

## Requirements

- Node.js 14+ (for dashboard server)
- Modern browser (Chrome/Firefox/Safari)
- Port 5173 available

## Next Steps

1. **Run your dry-run** in `/Users/jamesterbeest/dev/test-project`
2. **Keep dashboard open** in a browser tab
3. **Watch tasks execute** in real-time
4. **Verify setup.md settings** flow correctly

## Questions?

See `tasks-dashboard/README.md` for full documentation.
