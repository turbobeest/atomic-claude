# Atomic Claude Migration Guide: v1 (Bash) to v2 (Python)

**Version:** 2.0
**Last Updated:** February 7, 2026
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Why Migrate to v2](#why-migrate-to-v2)
3. [Key Differences](#key-differences)
4. [Pre-Migration Checklist](#pre-migration-checklist)
5. [Migration Steps](#migration-steps)
6. [State Format Changes](#state-format-changes)
7. [Breaking Changes](#breaking-changes)
8. [Configuration Changes](#configuration-changes)
9. [Post-Migration Validation](#post-migration-validation)
10. [Troubleshooting](#troubleshooting)
11. [Rollback Procedure](#rollback-procedure)
12. [FAQ](#faq)

---

## Overview

Atomic Claude v2.0 is a **clean Python refactoring** of the original bash-heavy v1 system. It maintains the same core principles and task scripts while providing better structure, testability, and maintainability through a Python orchestration layer.

**Core Philosophy:** The code works - we just organized it better.

**What Changed:**
- Bash orchestration → Python orchestration
- Scattered files → Grouped phase structure
- Manual process → Automated organization
- Basic state → Transactional state management
- Ad-hoc configuration → Multi-source config system

**What Stayed the Same:**
- Task scripts (bash)
- LLM invocation patterns
- Phase workflow
- Output structure
- Agent/audit repositories

---

## Why Migrate to v2

### Benefits of Python Version

**1. Better Organization**
- Grouped phase structure (orchestrator + tasks together)
- Enforced directory purity via forcing function
- Automatic file organization with organization agent
- Clear separation of concerns

**2. Improved State Management**
- Atomic transactions with rollback
- State snapshots and restore
- Concurrent access safety (file locking)
- Version migration support
- Better error recovery

**3. Enhanced Configuration**
- Multi-source loading (env, .env, JSON, CLI)
- Validation with Pydantic
- Override hierarchy (CLI > env > file > defaults)
- Hot-reload capability
- Type-safe access

**4. Developer Experience**
- Python debugging tools
- Unit testing framework (pytest)
- Integration testing
- Better error messages
- IDE support

**5. Production Ready**
- Comprehensive test suite (60+ tests per phase)
- Performance audits
- Security audits
- Regression testing
- UAT validation

**6. Maintainability**
- Cleaner code structure
- Self-documenting Python
- Easier to extend
- Better dependency management
- Version control friendly

---

## Key Differences

### Architecture

**v1 (Bash):**
```
atomic-claude/
├── atomic.sh              # Everything in bash
├── phases/
│   ├── 0-setup/
│   │   └── tasks/*.sh
│   ├── 2-prd/
│   │   └── tasks/*.sh
├── lib/*.sh               # Bash libraries
└── dashboard/             # Separate dashboard
```

**v2 (Python):**
```
atomic-claude/
├── main.py                # Python entry point
├── core/                  # Python utilities
│   ├── state.py
│   ├── config.py
│   ├── llm.py
│   └── providers.py
├── phases/                # Grouped structure
│   ├── phase00/
│   │   ├── orchestrator00.py    # Python orchestrator
│   │   ├── task001.sh           # Bash task scripts
│   │   └── task002.sh
│   ├── phase02/
│   │   ├── orchestrator02.py
│   │   ├── task201.sh
│   │   └── task205.sh
├── orchestration/         # End-of-task processes
│   ├── organization.py    # File organization
│   ├── git_manager.py     # Git prompts
│   └── backtrack.py       # Phase rollback
└── lib/                   # Bash libraries (unchanged)
```

### Execution

**v1:**
```bash
# Run phase
cd phases/2-prd
bash orchestrator.sh

# Manual state tracking
# Manual file organization
# Manual git commits
```

**v2:**
```bash
# Run phase
python main.py run 2

# Automatic state management
# Automatic file organization (forcing function)
# Prompted git commits
# Backtracking support
```

### State Management

**v1:** Simple JSON files
**v2:** Transactional state with snapshots, rollback, locking

### Configuration

**v1:** Environment variables only
**v2:** Multi-source (env, .env, JSON, CLI) with validation

---

## Pre-Migration Checklist

### 1. Backup Current State

**Critical:** Always backup before migration!

```bash
# Backup entire v1 directory
cd /path/to/atomic-claude
cp -r .state .state.backup.$(date +%Y%m%d_%H%M%S)
cp -r .outputs .outputs.backup.$(date +%Y%m%d_%H%M%S)

# Or use tar
tar -czf atomic-claude-backup-$(date +%Y%m%d_%H%M%S).tar.gz .state .outputs .logs
```

### 2. Check Current Status

```bash
# Check which phase/tasks are complete
cat .state/task-state.json | jq .

# Check outputs
ls -la .outputs/*/

# Check for uncommitted work
git status
```

### 3. Review Dependencies

**Python Requirements:**
- Python 3.9+
- pip packages: `pydantic`, `click`, `requests`

**Check Python version:**
```bash
python3 --version
# Must be 3.9 or higher
```

**Install dependencies:**
```bash
cd atomic-claude
pip install -r requirements.txt
```

### 4. Review Configuration

**v1 configuration locations:**
- `.env` - Environment variables
- `.outputs/0-setup/project-config.json` - Project config
- `.outputs/0-setup/secrets.json` - API keys

**Inventory your configuration:**
```bash
# Check environment
env | grep -E "ATOMIC_|CLAUDE_|AWS_"

# Check Phase 00 outputs
cat .outputs/0-setup/project-config.json
cat .outputs/0-setup/secrets.json
```

### 5. Document Current State

Create a snapshot document:

```bash
cat > migration-snapshot.txt << EOF
Migration Date: $(date)
Current Phase: $(cat .state/task-state.json | jq -r '.current_phase')
Completed Tasks: $(cat .state/task-state.json | jq '.phases | length')
Git Status: $(git rev-parse HEAD)
EOF
```

### 6. Clean Working Directory

```bash
# Commit any uncommitted changes
git add -A
git commit -m "Pre-migration snapshot"

# Or stash them
git stash save "Pre-migration stash"
```

---

## Migration Steps

### Step 1: Clone v2 Repository

```bash
# Clone alongside v1 (recommended)
cd /path/to/projects
git clone https://github.com/yourusername/atomic-claude.git

# Or clone as subdirectory
cd /path/to/atomic-claude
git clone https://github.com/yourusername/atomic-claude.git ACP
```

### Step 2: Install Dependencies

```bash
cd atomic-claude

# Install Python dependencies
pip install -r requirements.txt

# Optional: Install dev dependencies
pip install -r requirements-dev.txt
```

### Step 3: Copy Configuration

**Option A: Manual Copy**

```bash
# Copy .env file
cp ../atomic-claude/.env .env

# Verify contents
cat .env
```

**Option B: Recreate Configuration**

Create `.env` from template:

```bash
cp .env.example .env
nano .env
```

Example `.env`:
```bash
# LLM Provider
ANTHROPIC_API_KEY=your-api-key-here
# OR for Bedrock:
AWS_PROFILE=your-aws-profile
AWS_REGION=us-gov-west-1
CLAUDE_CODE_USE_BEDROCK=1

# Network Mode
ATOMIC_NETWORK_MODE=open

# Tool Development (set to false for production use)
ATOMIC_TOOL_DEVELOPMENT=false
```

### Step 4: Run Migration Script

```bash
# Run migration tool
python scripts/migrate.py \
  --old-state ../atomic-claude/.state \
  --new-state .state

# Expected output:
# ============================================================
# ATOMIC-CLAUDE STATE MIGRATION (v1 → v2)
# ============================================================
#
# Backing up old state to: .state.backup.20260207_150000
# ✓ Backup created: .state.backup.20260207_150000
#
# Migrating task state...
# ✓ State migrated: .state/task-state.json
#
# Migrating memory...
# ✓ Memory migrated
#
# ============================================================
# MIGRATION COMPLETE
# ============================================================
# Phases migrated: 3
# Backup location: .state.backup.20260207_150000
# New state location: .state
```

### Step 5: Copy Outputs (Optional)

If you want to preserve outputs from v1:

```bash
# Copy outputs
cp -r ../atomic-claude/.outputs .outputs

# Or symlink
ln -s ../atomic-claude/.outputs .outputs
```

**Note:** Most users don't need to copy outputs - v2 will regenerate them if needed.

### Step 6: Copy Agent/Audit Repositories

**Option A: Copy**
```bash
cp -r ../atomic-claude/agents agents
cp -r ../atomic-claude/audits audits
```

**Option B: Symlink** (recommended)
```bash
ln -s ../atomic-claude/agents agents
ln -s ../atomic-claude/audits audits
```

### Step 7: Validate Migration

```bash
# Check state loaded correctly
python main.py status

# Expected output:
# ================================================================================
#   ATOMIC CLAUDE 2.0 - PIPELINE STATUS
# ================================================================================
#
# 📦 0-setup
#    ✓ Task 001: Mode Selection
#    ✓ Task 002: Config Collection
#    ✓ Task 003: Config Review
#    ...
```

### Step 8: Test Run

```bash
# Try running next incomplete task
python main.py run 0

# Or resume from specific task
python main.py run 1 --resume-at=105
```

### Step 9: Verify Outputs

```bash
# Check outputs directory
ls -la .outputs/

# Verify state file
cat .state/task-state.json | jq .

# Check logs
tail -f .logs/atomic.log
```

---

## State Format Changes

### V1 State Structure

```json
{
  "phases": {
    "0-setup": {
      "started": "2026-02-01T10:00:00",
      "completed": "2026-02-01T11:00:00",
      "tasks": {
        "001": {
          "name": "Mode Selection",
          "status": "complete",
          "completed_at": "2026-02-01T10:15:00"
        }
      }
    }
  },
  "current_phase": "0-setup"
}
```

### V2 State Structure

```json
{
  "version": "2.0",
  "current_phase": "0-setup",
  "current_task": null,
  "phases": {
    "0-setup": {
      "started_at": "2026-02-01T10:00:00",
      "completed_at": "2026-02-01T11:00:00",
      "status": "completed",
      "tasks": {
        "001": {
          "name": "Mode Selection",
          "status": "completed",
          "completed_at": "2026-02-01T10:15:00",
          "artifacts": [
            ".outputs/0-setup/mode.json"
          ]
        }
      }
    }
  },
  "metadata": {
    "created_at": "2026-02-01T10:00:00",
    "last_updated": "2026-02-01T11:00:00"
  }
}
```

### Key Changes

1. **Version field:** Added for migration tracking
2. **Status normalization:** "complete" → "completed"
3. **Artifact tracking:** Tasks now record output files
4. **Metadata section:** Creation and update timestamps
5. **Phase status:** Explicit phase-level status tracking

### Migration Handles

- Converts "complete" to "completed"
- Adds missing metadata
- Preserves all task completion data
- Maintains phase timing information
- Creates artifacts list (empty for migrated tasks)

---

## Breaking Changes

### 1. Command Line Interface

**v1:**
```bash
cd phases/2-prd
bash orchestrator.sh
```

**v2:**
```bash
python main.py run 2
```

**Migration:** Update any automation scripts.

### 2. Directory Structure

**v1:** Tasks scattered across `phases/N-name/tasks/`
**v2:** Tasks grouped with orchestrators in `phases/phaseNN/`

**Migration:** Path references need updating if you have custom scripts.

### 3. State File Location

**v1:** `.state/task-state.json` (simple format)
**v2:** `.state/task-state.json` (enhanced format)

**Migration:** Automatic via migration script.

### 4. Environment Variables

**New variables:**
- `ATOMIC_ROOT` - Root directory (replaces manual paths)
- `ATOMIC_OUTPUT_DIR` - Outputs directory
- `ATOMIC_STATE_DIR` - State directory
- `ATOMIC_LOG_DIR` - Logs directory

**Deprecated variables:**
- `ROOT_DIR` (still works as alias)

**Migration:** No action needed - v2 sets these automatically.

### 5. Configuration Priority

**v1:** Environment variables only
**v2:** CLI > env vars > .env file > JSON config > defaults

**Migration:** Be aware of priority when setting configs.

### 6. Task Script Sourcing

**v1:**
```bash
source ../../lib/atomic.sh
```

**v2:**
```bash
set -euo pipefail
LIB_DIR="${ATOMIC_LIB_DIR:-$(dirname "$0")/../../lib}"
source "$LIB_DIR/atomic.sh"
```

**Migration:** Custom task scripts need updated sourcing.

### 7. Arithmetic Operations

**v1:**
```bash
((counter++))
```

**v2:**
```bash
((counter++)) || true  # Required with set -e
```

**Migration:** Update custom task scripts.

---

## Configuration Changes

### Environment Variables

**v1 Configuration:**
```bash
# In .env or environment
export CLAUDE_PROVIDER=max
export CLAUDE_MODEL=sonnet
export ATOMIC_PROJECT_NAME=my-project
```

**v2 Configuration:**

Multiple sources with priority:

1. **CLI Arguments** (highest priority)
```bash
python main.py run 2 --resume-at=205
```

2. **Environment Variables**
```bash
export CLAUDE_PROVIDER=bedrock
export CLAUDE_MODEL=sonnet
```

3. **.env File**
```bash
# .env
CLAUDE_PROVIDER=bedrock
CLAUDE_MODEL=sonnet
ATOMIC_NETWORK_MODE=open
```

4. **JSON Config Files** (Phase 00 outputs)
```json
// .outputs/0-setup/project-config.json
{
  "extracted": {
    "project": {
      "name": "my-project",
      "type": "web-app"
    },
    "llm": {
      "primary_provider": "bedrock",
      "primary_model": "sonnet"
    }
  }
}
```

5. **Defaults** (lowest priority)

### Configuration Access

**v1:**
```bash
# Direct environment access
echo $CLAUDE_PROVIDER
```

**v2:**
```python
from core.config import Config

config = Config()
provider = config.get_provider()  # Returns "bedrock"
model = config.get_model("primary")  # Returns "sonnet"
project = config.get("project.name")  # Dot notation
```

### New Configuration Options

**Dashboard Ports:**
```bash
ATOMIC_TASKS_PORT=5173     # Tasks dashboard
ATOMIC_AGENTS_PORT=5174    # Agents dashboard
ATOMIC_AUDITS_PORT=5175    # Audits dashboard
```

**Memory System:**
```bash
ATOMIC_MEMORY_ENABLED=true
ATOMIC_MEMORY_CHECKPOINT_FREQ=5
ATOMIC_MEMORY_MAX_SIZE_MB=100
```

**Tool Development Mode:**
```bash
ATOMIC_TOOL_DEVELOPMENT=true  # Disables forcing function
```

---

## Post-Migration Validation

### Checklist

- [ ] State migration completed successfully
- [ ] All completed tasks shown in status
- [ ] Configuration loaded correctly
- [ ] Can run next phase/task
- [ ] Outputs directory accessible
- [ ] Dashboard loads (if enabled)
- [ ] Git repository working
- [ ] Tests pass (if running dev mode)

### Validation Commands

**1. Check Status**
```bash
python main.py status
```

Expected: All migrated phases and tasks shown with completion status.

**2. Verify Configuration**
```bash
python -c "from core.config import Config; c = Config(); print(c.to_dict())"
```

Expected: Configuration dict with project, llm, secrets sections.

**3. Test State Access**
```bash
python -c "from core.state import StateManager; s = StateManager(); s.display_status()"
```

Expected: Same output as `main.py status`.

**4. Check Environment**
```bash
python -c "from core.subprocess_runner import get_task_environment; import json; print(json.dumps(get_task_environment('0-setup', '001'), indent=2))"
```

Expected: Complete environment with ATOMIC_*, CLAUDE_*, AWS_* variables.

**5. Dry Run Next Task**
```bash
# This will attempt to run but skip completed tasks
python main.py run 0
```

Expected: Should skip completed tasks and stop at first incomplete task (or succeed if phase complete).

**6. Test Backtracking** (optional)
```bash
# Check backtrack capability
python main.py backtrack 0 001
```

Expected: State rolled back to Task 001 of Phase 0.

### Comparison Test

Run same task in both versions and compare outputs:

**v1:**
```bash
cd atomic-claude/phases/0-setup
bash tasks/task001.sh > /tmp/v1-output.txt 2>&1
```

**v2:**
```bash
cd atomic-claude
python main.py run 0 --resume-at=001 > /tmp/v2-output.txt 2>&1
```

**Compare:**
```bash
diff /tmp/v1-output.txt /tmp/v2-output.txt
```

Expected: Minimal differences (timestamps, paths).

---

## Troubleshooting

### Common Issues

#### Issue 1: Migration Script Fails

**Symptoms:**
```
Error: Failed to load state file
```

**Causes:**
- Corrupt state JSON
- Missing .state directory
- Permission issues

**Solutions:**
```bash
# Validate JSON
cat .state/task-state.json | jq . > /dev/null

# Check permissions
ls -la .state/

# Restore from backup
cp .state.backup.20260207_150000/task-state.json .state/

# Or start fresh
python main.py reset
```

#### Issue 2: State Shows No Tasks

**Symptoms:**
```bash
python main.py status
# Output: No phases started yet.
```

**Causes:**
- Migration didn't copy state
- Wrong state directory
- Empty source state

**Solutions:**
```bash
# Check state file exists
cat .state/task-state.json

# Re-run migration
python scripts/migrate.py --old-state ../atomic-claude/.state --new-state .state

# Check source state had data
cat ../atomic-claude/.state/task-state.json
```

#### Issue 3: Configuration Not Loaded

**Symptoms:**
- Default values used instead of config
- "unknown" project name

**Causes:**
- .env file not present
- Phase 00 outputs missing
- Wrong working directory

**Solutions:**
```bash
# Check .env exists
cat .env

# Check Phase 00 outputs
cat .outputs/0-setup/project-config.json

# Load config explicitly
python -c "from core.config import Config; c = Config(); print(c.to_dict())"
```

#### Issue 4: Task Scripts Not Found

**Symptoms:**
```
FileNotFoundError: Task script not found: phases/phase00/task001.sh
```

**Causes:**
- Tasks not copied from v1
- Wrong directory structure

**Solutions:**
```bash
# Copy tasks from v1
cp -r ../atomic-claude/phases/0-setup/tasks/* phases/phase00/

# Or fix paths in orchestrator
```

#### Issue 5: Environment Variables Not Set

**Symptoms:**
- LLM calls fail
- "Provider not configured"

**Causes:**
- .env not loaded
- Missing API keys
- subprocess_runner not setting env

**Solutions:**
```bash
# Check .env loaded
python -c "from core.config import Config; c = Config(); print(c.get_provider())"

# Check environment
python -c "from core.subprocess_runner import get_task_environment; env = get_task_environment('0-setup', '001'); print(env.get('CLAUDE_PROVIDER'))"

# Set manually
export CLAUDE_PROVIDER=max
export ANTHROPIC_API_KEY=your-key
```

#### Issue 6: Forcing Function Blocks Tasks

**Symptoms:**
```
❌ Pre-task validation failed: Tool development files detected
```

**Causes:**
- Test files in project directory
- Wrong tool development mode

**Solutions:**
```bash
# Enable tool development mode
export ATOMIC_TOOL_DEVELOPMENT=true

# Or clean directory
mv test/ ../test-backup/
```

#### Issue 7: Dashboard Won't Start

**Symptoms:**
- Port already in use
- Dashboard 404

**Causes:**
- Port conflict
- Dashboard not built
- Wrong working directory

**Solutions:**
```bash
# Check port
lsof -i :5173

# Use different port
export ATOMIC_TASKS_PORT=5174

# Build dashboard
cd dashboard
npm install
npm run build
```

#### Issue 8: Git Repository Issues

**Symptoms:**
- "Not a git repository"
- Git commands fail

**Causes:**
- Working directory not a git repo
- .git directory missing

**Solutions:**
```bash
# Initialize git
git init

# Or clone as git repo
git clone /path/to/atomic-claude
```

### Debug Mode

Enable verbose logging:

```bash
# Set log level
export LOG_LEVEL=DEBUG

# Run with verbose output
python main.py run 0 --verbose

# Check logs
tail -f .logs/atomic.log
```

### Getting Help

1. **Check logs:** `.logs/atomic.log`
2. **Check state:** `.state/task-state.json`
3. **Check config:** `.env` and `.outputs/0-setup/`
4. **Run tests:** `pytest tests/`
5. **Open issue:** GitHub repository

---

## Rollback Procedure

If migration fails or you need to revert:

### Quick Rollback

```bash
# Stop v2
cd atomic-claude
# Ctrl+C or kill process

# Return to v1
cd ../atomic-claude

# Restore state (if needed)
cp .state.backup.20260207_150000/task-state.json .state/

# Continue with v1
cd phases/2-prd
bash orchestrator.sh
```

### Complete Rollback

```bash
# 1. Stop v2
cd atomic-claude
# Ctrl+C

# 2. Restore v1 state from backup
cd ../atomic-claude
rm -rf .state
cp -r .state.backup.20260207_150000 .state

# 3. Restore v1 outputs (if needed)
rm -rf .outputs
cp -r .outputs.backup.20260207_150000 .outputs

# 4. Verify v1 state
cat .state/task-state.json | jq .

# 5. Test v1 still works
cd phases/0-setup
bash orchestrator.sh
```

### Partial Rollback (Keep Progress)

If you made progress in v2 but need to go back to v1:

```bash
# 1. Export v2 state
cd atomic-claude
cp .state/task-state.json /tmp/v2-state.json

# 2. Manually merge state into v1
cd ../atomic-claude
# Edit .state/task-state.json to add v2 progress

# 3. Continue with v1
```

---

## FAQ

### General Questions

**Q: Do I have to migrate?**
A: No. V1 will continue to work. Migrate when you want better organization, testing, or are starting a new project.

**Q: Can I run both versions?**
A: Yes, but not on the same project simultaneously. Keep them in separate directories.

**Q: Will migration change my project?**
A: No. Migration only affects atomic-claude itself, not the project you're building.

**Q: How long does migration take?**
A: 5-15 minutes for most projects.

### Technical Questions

**Q: What happens to my bash task scripts?**
A: They're preserved and used as-is. V2 adds Python orchestration layer around them.

**Q: Are outputs preserved?**
A: Yes, if you copy them. But v2 can regenerate outputs if needed.

**Q: What about memory state?**
A: Memory is migrated automatically if it exists.

**Q: Can I customize task scripts?**
A: Yes, same as v1. Just drop new .sh scripts into phase directories.

**Q: Do I need to learn Python?**
A: Not for basic use. Python is only for orchestration. Task scripts remain bash.

### Migration Questions

**Q: Can I migrate mid-project?**
A: Yes. The migration script preserves all progress.

**Q: What if migration fails?**
A: Use rollback procedure to return to v1. State backup is automatic.

**Q: Can I test v2 before fully migrating?**
A: Yes. Clone v2 separately, copy state, test, then delete if not satisfied.

**Q: Do I need to reconfigure everything?**
A: No. Copy your .env file and you're mostly done.

### State Questions

**Q: Why is my state empty after migration?**
A: Check source state had data. Verify migration script source path.

**Q: Can I edit state manually?**
A: Yes, but use Python API for safety. Manual edits risk corruption.

**Q: How do I reset state?**
A: `python main.py reset` (nuclear option) or backtrack to specific point.

### Configuration Questions

**Q: Where do I put API keys?**
A: In `.env` file or environment variables, same as v1.

**Q: Can I use Bedrock?**
A: Yes, same configuration as v1. Just copy .env settings.

**Q: How do I change models?**
A: Set `CLAUDE_MODEL` in .env or Phase 00 config.

### Performance Questions

**Q: Is v2 slower than v1?**
A: No. Python overhead is negligible. Task scripts run at same speed.

**Q: Does v2 use more memory?**
A: Slightly (50-100MB more), but not significantly.

**Q: Can I run v2 on constrained systems?**
A: Yes, if Python 3.9+ is available.

---

## Next Steps

After successful migration:

1. **Run Tests** (if in dev mode)
   ```bash
   pytest tests/
   ```

2. **Update Documentation**
   - Update any project-specific docs
   - Update automation scripts
   - Update CI/CD pipelines

3. **Familiarize with New Features**
   - Organization agent (automatic file cleanup)
   - Backtracking (reset to any point)
   - State transactions (atomic changes)
   - Configuration validation

4. **Configure Git**
   - Set up commit prompts
   - Configure auto-push settings
   - Set up hooks

5. **Explore Dashboard**
   - Start dashboard: `npm run dev` in dashboard/
   - Access at http://localhost:5173
   - Real-time task monitoring

6. **Customize Phases**
   - Add custom task scripts
   - Modify orchestrators
   - Create custom agents

---

## Additional Resources

- [README.md](../README.md) - Getting started guide
- [CLAUDE.md](../CLAUDE.md) - Claude Code guidance
- [PROJECT-STRUCTURE.md](PROJECT-STRUCTURE.md) - Directory structure
- [REFACTORING-PLAN-V2.md](REFACTORING-PLAN-V2.md) - Design decisions
- [tests/README.md](../tests/README.md) - Testing documentation

---

## Version History

- **2.0** (2026-02-07) - Initial v2 migration guide
- **1.0** (2026-02-01) - V1 documentation

---

## Support

If you encounter issues during migration:

1. Check [Troubleshooting](#troubleshooting) section
2. Review logs in `.logs/atomic.log`
3. Check state in `.state/task-state.json`
4. Open GitHub issue with:
   - Migration command used
   - Error message
   - State backup info
   - Environment details

---

**Happy Migrating!**

The atomic-claude v2 team
