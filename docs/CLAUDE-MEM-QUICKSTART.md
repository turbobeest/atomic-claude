# Quick Start: Claude-Mem Installation

## TL;DR

Claude-mem is **NOT installed** but atomic-claude works fine without it. To add persistent memory with semantic search:

### 5-Minute Install

1. **Install Plugin**
   ```
   Cmd+Shift+P → Marketplace → Search "claude-mem" → Install
   ```

2. **Restart Claude Code**

3. **Verify**
   ```bash
   ./verify-claude-mem.sh
   ```

4. **Enable in Atomic-Claude**
   ```bash
   ./main.sh run 0
   # Select "Enable memory" when prompted
   ```

5. **Check It Works**
   ```bash
   # Open web UI
   open http://localhost:37777

   # Should see memories captured
   ```

## What You Get

### Without Claude-Mem (Current)
✅ Local file-based memory
- Stores task outputs in `.state/memory/`
- Manual context passing between tasks
- Human-readable markdown files
- Works offline

### With Claude-Mem (After Install)
✅ All of the above PLUS:
- 🔍 Semantic search across all sessions
- 🌐 Web UI for browsing (port 37777)
- 🤖 Automatic context capture (no manual saves)
- 📊 Timeline view of all activities
- 🔗 Cross-session context recall

## Installation Commands

```bash
# Via Claude Code Marketplace (Recommended)
Cmd+Shift+P → "Marketplace" → Search "claude-mem" → Install → Restart

# Or via CLI
claude-code marketplace install claude-mem && claude-code restart

# Or via NPX (manual)
npx -y @anthropics/claude-mem
```

## Verification

```bash
# Quick check
type mem-search && curl http://localhost:37777 && echo "✓ Installed"

# Detailed check
./verify-claude-mem.sh

# Expected output:
# ✓ mem-search skill available
# ✓ Web UI accessible at http://localhost:37777
# ✓ Database found
```

## Enable Memory

### Option 1: Environment Variable
```bash
export ATOMIC_MEMORY_ENABLED=true
./main.sh run 0
```

### Option 2: During Setup
```bash
./main.sh run 0
# When prompted for providers, select option 5 (Local Memory)
```

### Option 3: Edit setup.md
```markdown
## Memory System
true
```

## Test It

```bash
# Run Phase 0
./main.sh run 0

# Check local storage
ls -la .state/memory/

# Check web UI
open http://localhost:37777

# Run Phase 1 (should recall Phase 0 context)
./main.sh run 1
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `mem-search: command not found` | Install plugin, restart Claude Code |
| Port 37777 not accessible | Check firewall, verify plugin running |
| No memories showing | Run Phase 0 to trigger first save |
| Database not found | Normal - created on first memory save |

## More Info

- **Full Guide:** `CLAUDE-MEM-INSTALLATION.md`
- **Status Check:** `CLAUDE-MEM-STATUS.md`
- **Technical Details:** `docs/CLAUDE-MEM-MIGRATION.md`

## Current Status

```
Claude-Mem Plugin:     ❌ NOT INSTALLED
Local Memory System:   ✅ WORKING
Integration Ready:     ✅ YES
Next Step:             Install plugin from Marketplace
```

---

**Install time:** ~5 minutes
**Benefit:** Semantic memory search + automatic context capture
**Required:** No (local files work fine)
**Recommended:** Yes (for better cross-session context)
