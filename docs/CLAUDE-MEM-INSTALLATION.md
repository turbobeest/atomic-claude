# Claude-Mem Installation Guide

## Overview

This guide will help you install and configure the claude-mem plugin to provide persistent memory across atomic-claude sessions.

## What is Claude-Mem?

Claude-mem is a Claude Code MCP (Model Context Protocol) server that:
- Automatically captures tool usage, commands, and context during sessions
- Stores memories in a local SQLite database
- Provides semantic search across your session history
- Offers a web UI for browsing memories (port 37777)
- Works entirely locally (no external APIs)

## Prerequisites

- Claude Code (latest version)
- This atomic-claude repository
- ~100MB disk space for memory database

## Installation Steps

### Step 1: Install Claude-Mem Plugin

**Option A: Via Claude Code CLI**
```bash
# If you have the claude-code CLI installed
claude-code marketplace install claude-mem
```

**Option B: Via Claude Code UI (Recommended)**
1. Open Claude Code
2. Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux)
3. Type "Marketplace" and select "Claude Code: Open Marketplace"
4. Search for "claude-mem"
5. Click "Install"
6. Restart Claude Code

**Option C: Manual Installation from GitHub**
```bash
# Clone the claude-mem repository
cd ~/.config/claude-code/plugins
git clone https://github.com/anthropics/claude-mem.git

# Install dependencies (if needed)
cd claude-mem
npm install

# Restart Claude Code
```

### Step 2: Verify Installation

Run the verification script:

```bash
./verify-claude-mem.sh
```

Or check manually:

```bash
# Check if mem-search skill is available
type mem-search

# Check if web UI is running
curl -s http://localhost:37777 | head -5

# Check for database
find ~ -name "claude-mem*.db" -type f
```

### Step 3: Configure for Atomic-Claude

#### A. Enable Memory in Atomic-Claude

Edit `initialization/setup.md` or run Phase 0 with memory enabled:

```markdown
## Memory System
# Enable persistent memory across sessions?
# Options: true | false | default [false]

true
```

Or set environment variable:
```bash
export ATOMIC_MEMORY_ENABLED=true
```

#### B. Configure Project Scope (Optional)

To isolate memories per project, you can tag them:

Create `.claude-mem-config.json` in your project root:
```json
{
  "project_name": "atomic-claude",
  "project_id": "atomic-claude-pipeline",
  "auto_tag": true,
  "retention_days": 90,
  "scope": "project"
}
```

### Step 4: Test Memory Flow

**Test 1: Basic Capture**
```bash
# Start a new Claude Code session in this repo
cd /path/to/atomic-claude

# Run some commands
echo "Testing claude-mem integration" > test-memory.txt
cat test-memory.txt

# Check if captured in web UI
open http://localhost:37777
```

**Test 2: Cross-Session Recall**
```bash
# In a NEW Claude Code session
cd /path/to/atomic-claude

# Search for previous context
# (This should work if claude-mem is installed)
# The /mem-search skill should be available
```

**Test 3: Atomic-Claude Pipeline**
```bash
# Run Phase 0 with memory enabled
./main.sh run 0

# Check that memories were saved
ls -la .state/memory/

# Check web UI for captured context
open http://localhost:37777
```

## Configuration Options

### Memory Storage Location

By default, claude-mem stores data in:
- **macOS:** `~/Library/Application Support/claude-code/claude-mem/`
- **Linux:** `~/.local/share/claude-code/claude-mem/`
- **Windows:** `%APPDATA%\claude-code\claude-mem\`

### Environment Variables

```bash
# Enable atomic-claude memory system
export ATOMIC_MEMORY_ENABLED=true

# Claude-mem database location (optional override)
export CLAUDE_MEM_DB_PATH="$HOME/.claude-mem/atomic-claude.db"

# Memory retention (days)
export CLAUDE_MEM_RETENTION_DAYS=90
```

### MCP Server Configuration

If you need to manually configure the MCP server, add to `~/.config/claude-code/mcp_servers.json`:

```json
{
  "claude-mem": {
    "command": "npx",
    "args": ["-y", "@anthropics/claude-mem"],
    "env": {
      "CLAUDE_MEM_DB_PATH": "${HOME}/.claude-mem/atomic-claude.db"
    }
  }
}
```

## Integration with Atomic-Claude

### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│ Task Execution in Atomic-Claude                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Task Start                                                 │
│    ↓                                                        │
│  memory_task_start()                                        │
│    ├─→ Recall from .state/memory/ (local files)           │
│    └─→ mem-search skill (claude-mem SQLite) ← NEW!        │
│    ↓                                                        │
│  Inject context into prompt                                 │
│    ↓                                                        │
│  Execute task with LLM                                      │
│    ↓                                                        │
│  Claude Code hooks capture:                                 │
│    ├─→ Tool usage (Read, Write, Edit, Bash)               │
│    ├─→ User prompts                                        │
│    ├─→ Agent outputs                                       │
│    └─→ Automatically saved to SQLite ← NEW!               │
│    ↓                                                        │
│  memory_task_end()                                          │
│    └─→ Save summary to .state/memory/ (redundant backup)  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Dual Storage Strategy

Atomic-claude uses **both** storage backends:

1. **Local Files** (`.state/memory/`)
   - Fast, reliable, works offline
   - Explicit control over what's saved
   - Used for phase closeouts and task summaries
   - Human-readable markdown files

2. **Claude-Mem SQLite** (automatic)
   - Captures everything via hooks
   - Semantic search across sessions
   - Web UI for browsing
   - Timeline-based retrieval

### Memory Recall Priority

When a task starts, atomic-claude recalls context in this order:

1. **Phase-specific memory** - Previous task outputs from current phase
2. **Recent phase closeouts** - Summaries from completed phases
3. **Claude-mem search** - Semantic search for relevant past context
4. **Task-specific artifacts** - Files created by previous tasks

## Web UI Features

Access at `http://localhost:37777`:

### Search Memories
- Semantic search across all sessions
- Filter by project, date, task
- View tool usage timeline

### Browse Timeline
- Chronological view of all activities
- See what commands were run
- Review file modifications

### Manage Memories
- Delete specific memories
- Clear project scope
- Export memory database

## Troubleshooting

### Claude-Mem Not Starting

```bash
# Check Claude Code logs
tail -f ~/.config/claude-code/logs/mcp-claude-mem.log

# Manually start claude-mem
npx -y @anthropics/claude-mem

# Check for port conflicts
lsof -i :37777
```

### Database Locked Errors

```bash
# Close all Claude Code sessions
pkill -f "claude-code"

# Check for stale locks
find ~ -name "claude-mem*.db-wal" -delete
find ~ -name "claude-mem*.db-shm" -delete

# Restart Claude Code
```

### Web UI Not Accessible

```bash
# Check if service is running
curl -v http://localhost:37777

# Check firewall
# macOS: System Preferences > Security > Firewall
# Linux: sudo ufw allow 37777

# Try different port (if configured)
echo $CLAUDE_MEM_PORT
```

### Memory Not Persisting

```bash
# Verify memory is enabled
cat .outputs/0-setup/secrets.json | jq '.memory_enabled'

# Check local storage
ls -la .state/memory/

# Check claude-mem database
sqlite3 ~/.claude-mem/atomic-claude.db "SELECT count(*) FROM memories;"
```

## Verification Checklist

After installation, verify these items:

- [ ] `mem-search` skill is available
- [ ] Web UI accessible at http://localhost:37777
- [ ] Database file exists (find ~ -name "claude-mem*.db")
- [ ] `ATOMIC_MEMORY_ENABLED=true` set
- [ ] Phase 0 runs without errors
- [ ] Memories visible in web UI after running tasks
- [ ] `.state/memory/` contains local backups
- [ ] Cross-session recall works (run Phase 1 after Phase 0)

## Performance Considerations

### Database Size

Claude-mem databases grow over time:
- ~1MB per 10 task executions
- ~10MB per complete pipeline run
- Configure retention to auto-prune old memories

### Query Performance

- Semantic search is O(n) but optimized
- Index on project_id for faster scoping
- Consider pruning memories older than 90 days

### Disk Space

Monitor database growth:
```bash
# Check database size
du -h ~/.claude-mem/*.db

# Compact database (reclaim space)
sqlite3 ~/.claude-mem/atomic-claude.db "VACUUM;"
```

## Advanced Usage

### Project-Specific Databases

Use separate databases per project:
```bash
# Set per-project database
export CLAUDE_MEM_DB_PATH="./.claude-mem/project.db"
```

### Custom Search Queries

```bash
# Search for specific task outputs
mem-search "Phase 2 PRD section"

# Search by date range
mem-search --after="2026-02-01" "implementation"

# Search within project scope
mem-search-project "atomic-claude" "agent selection"
```

### Memory Export

```bash
# Export all memories to JSON
sqlite3 ~/.claude-mem/atomic-claude.db \
  "SELECT json_group_array(json_object(
    'timestamp', timestamp,
    'content', content,
    'tags', tags
  )) FROM memories;" > memories-export.json

# Import to another instance
sqlite3 ~/.claude-mem/backup.db < memories-export.json
```

## Security & Privacy

### Data Storage

- All data stored locally (no cloud)
- SQLite database is unencrypted
- Consider encrypting the database file if needed

### Sensitive Data

Configure filtering to exclude:
```json
{
  "exclude_patterns": [
    "**/secrets.json",
    "**/.env*",
    "**/credentials/*",
    "**/*.key",
    "**/*.pem"
  ]
}
```

### GDPR Compliance

Claude-mem supports:
- Right to erasure (delete specific memories)
- Data portability (export to JSON)
- Retention limits (auto-delete after N days)

## Support

### Documentation
- Claude-mem GitHub: https://github.com/anthropics/claude-mem
- Claude Code Docs: https://docs.anthropic.com/claude-code
- MCP Protocol: https://modelcontextprotocol.io

### Community
- Claude Code Discord
- GitHub Issues: https://github.com/anthropics/claude-mem/issues

### Atomic-Claude Specific
- See: `docs/CLAUDE-MEM-MIGRATION.md`
- See: `lib/memory.sh` for integration details
- See: `lib/task-memory-defs.sh` for memory definitions

## Next Steps

Once claude-mem is installed and verified:

1. Run Phase 0 to initialize memory system
2. Complete a full pipeline run (Phases 0-2)
3. Check web UI to verify memories captured
4. Test cross-session recall by restarting Claude Code
5. Configure retention and project scoping as needed

Happy memory-enabled development! 🧠✨
