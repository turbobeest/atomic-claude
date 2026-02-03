# ATOMIC CLAUDE - Tasks Dashboard

Real-time web dashboard for monitoring ATOMIC CLAUDE task execution.

## Features

- **Real-time Status Box**: Shows current LLM task with all diagnostic information
  - Provider (Max/API/Bedrock/Ollama)
  - Model being used
  - Service status (online/offline)
  - Network mode (CUI/Internet)
  - Context window size
  - Cost tier
  - Role (primary/fast/heavyweight/gardener)
  - Timeout settings
  - Current phase and task ID

- **Task History**: Lists all tasks across all phases with completion status

- **Commands Cheatsheet**: Click the info button (top right) for quick reference to:
  - Main CLI commands
  - Phase flags and options
  - Pipeline phases overview
  - Configuration files
  - Task navigation shortcuts
  - Quick examples

- **Server-Sent Events**: Real-time updates without polling

## Quick Start

```bash
# From atomic-claude root
./scripts/start-dashboard.sh
```

The dashboard will be available at: **http://localhost:5173**

## Architecture

```
┌─────────────────┐       ┌──────────────────┐       ┌────────────────┐
│   atomic.sh     │──────▶│ current-task.json│◀──────│   Dashboard    │
│                 │       │  (status file)   │       │  (localhost)   │
│ atomic_invoke() │       └──────────────────┘       └────────────────┘
│ writes status   │              ▲                           │
└─────────────────┘              │                           │
                                 │                           │
                          SSE stream (real-time)             │
                                 └───────────────────────────┘
```

### Status Flow

1. **Task Start**: `atomic_task_header()` writes status to `.state/current-task.json`
2. **Dashboard Monitors**: Server watches status file via `fs.watch()`
3. **Real-time Updates**: Changes pushed to browser via Server-Sent Events
4. **Task Complete**: `atomic_task_clear()` marks task as inactive

## API Endpoints

- `GET /api/status` - Current task status
- `GET /api/tasks` - All tasks from `.claude/task-state.json`
- `GET /api/config` - Project configuration
- `GET /api/stream` - Server-Sent Events stream for real-time updates

## CLI Changes

The verbose task headers have been removed from CLI output. Instead of:

```
  ╶─── Generate PRD section ─────────────────────────────────
    provider  max            model     opus            ● online
    context   200K           cost      high            role  heavyweight
    host      CLAUDECODE     timeout   300s
    prompt    .outputs/.../prompt.md
    output    .outputs/.../response.txt
  ╶──────────────────────────────────────────────────────────
```

You now see:

```
  ▶ Generate PRD section (max/opus)
```

All diagnostic information is available in the web dashboard.

## Development

```bash
cd tasks-dashboard

# Install dependencies
npm install

# Start server
npm start

# Server runs on port 5173 (configurable via ATOMIC_TASKS_PORT)
```

## Environment Variables

- `ATOMIC_ROOT` - Path to atomic-claude installation (auto-detected)
- `ATOMIC_TASKS_PORT` - Dashboard port (default: 5173)

## Status File Schema

`.state/current-task.json`:

```json
{
  "active": true,
  "description": "Extract configuration from setup",
  "provider": "max",
  "model": "sonnet",
  "role": "primary",
  "timeout": 300,
  "online": true,
  "network_mode": "cui",
  "context_window": "200K",
  "cost_tier": "medium",
  "host_type": "CLAUDECODE",
  "phase": "0-setup",
  "task_id": "002",
  "timestamp": "2026-02-02T10:30:00Z"
}
```

## Styling

The dashboard uses a dark terminal-inspired theme with:
- **Monospace fonts** (SF Mono, Monaco, Fira Code)
- **Color-coded status indicators**
  - Green: Online/Completed
  - Blue: Active/Running
  - Red: Offline/Failed
  - Gray: Idle/Pending
- **Responsive grid layout**
- **Real-time pulsing indicators**

## Browser Compatibility

- Chrome/Edge: ✅ Full support
- Firefox: ✅ Full support
- Safari: ✅ Full support
- Mobile: ✅ Responsive design

## Performance

- **Minimal overhead**: Status file is ~500 bytes
- **Efficient streaming**: SSE only sends updates on file change
- **No database required**: Everything in JSON files
- **Fast startup**: < 1 second

## Troubleshooting

**Dashboard not loading?**
- Ensure Node.js is installed: `node --version`
- Check if port 5173 is available: `lsof -i :5173`
- Verify `npm install` completed successfully

**Status not updating?**
- Check `.state/current-task.json` exists and is being written
- Ensure browser console shows no errors
- Try hard refresh: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows/Linux)

**Tasks not showing?**
- Ensure Phase 0 has been run at least once
- Check `.claude/task-state.json` exists
- Verify tasks are being tracked via task_state_* functions
