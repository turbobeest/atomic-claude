# Extraction Strategy

**Goal:** Build atomic-claude2 by extracting and organizing code from the working bash/Python hybrid system.

---

## Core Principle: COPY, Don't Move

**IMPORTANT:** We are NOT refactoring atomic-claude in place. We are building a new, clean version.

```
SOURCE: /Users/jamesterbeest/dev/atomic-claude (DO NOT MODIFY)
TARGET: /Users/jamesterbeest/dev/atomic-claude2 (BUILD HERE)
```

### Why Copy, Not Move?

1. **Preserve working system** - atomic-claude still works, don't break it
2. **Safe experimentation** - Can try approaches without risk
3. **Easy comparison** - Can diff between old and new
4. **Rollback option** - If atomic-claude2 fails, atomic-claude still works
5. **Archive strategy** - Once atomic-claude2 is proven, archive atomic-claude

### Extraction Process

```bash
# ✅ CORRECT - Copy from source
cp /Users/jamesterbeest/dev/atomic-claude/lib/provider.py \
   /Users/jamesterbeest/dev/atomic-claude2/core/providers.py

# ❌ WRONG - Don't move from source
mv /Users/jamesterbeest/dev/atomic-claude/lib/provider.py \
   /Users/jamesterbeest/dev/atomic-claude2/core/providers.py
```

---

## Extraction Phases

### Phase 1: Core Modules (Copy AS-IS)

**Source:** `atomic-claude-python/lib/`
**Target:** `atomic-claude2/core/`

| Source File | Target File | Strategy |
|-------------|-------------|----------|
| `provider.py` (1,022 lines) | `core/providers.py` | COPY AS-IS - works perfectly |
| `memory.py` (~900 lines) | `core/memory.py` | COPY AS-IS - claude-mem working |
| `atomic.py` | `core/llm.py` | COPY + clean up TODOs |
| `task_state.py` | `core/state.py` | COPY + clean up |

**Commands:**
```bash
cd /Users/jamesterbeest/dev/atomic-claude2

# Provider (AS-IS)
cp ../atomic-claude-python/lib/provider.py core/providers.py

# Memory (AS-IS)
cp ../atomic-claude-python/lib/memory.py core/memory.py

# LLM (copy then clean)
cp ../atomic-claude-python/lib/atomic.py core/llm.py
# Then: Remove TODO stubs, update imports

# State (copy then clean)
cp ../atomic-claude-python/lib/task_state.py core/state.py
# Then: Clean up, update imports
```

### Phase 2: Dashboard (Copy + Fix Bugs)

**Source:** `atomic-claude/tasks-dashboard/`
**Target:** `atomic-claude2/dashboard/`

```bash
cd /Users/jamesterbeest/dev/atomic-claude2

# Copy entire dashboard
cp -r ../atomic-claude/tasks-dashboard/* dashboard/

# Then: Fix 5 known bugs
# 1. SSE stream inactive status (server.js:255-304)
# 2. Dashboard not clearing old status (index.html:1241-1301)
# 3. Staleness detection (server.js age calculation)
# 4. Provider display incorrect (index.html renderLLMInfo)
# 5. Phase status wrong (dashboard phase calculation)
```

### Phase 3: Task Scripts (Copy + Organize)

**Source:** `atomic-claude/phases/*/tasks/`
**Target:** `atomic-claude2/phases/phase*/`

**Example: Phase 0 tasks**
```bash
cd /Users/jamesterbeest/dev/atomic-claude2

# Copy Phase 0 tasks
cp ../atomic-claude/phases/0-setup/tasks/001-mode-selection.sh \
   phases/phase00/task001.sh

cp ../atomic-claude/phases/0-setup/tasks/002-config-collection.sh \
   phases/phase00/task002.sh

# Continue for all Phase 0 tasks (001, 002, 003, 004, 006, 009)
```

**Example: Phase 2 tasks**
```bash
# Copy Phase 2 tasks
cp ../atomic-claude/phases/2-prd/tasks/201-entry-validation.sh \
   phases/phase02/task201.sh

cp ../atomic-claude/phases/2-prd/tasks/205-prd-authoring.sh \
   phases/phase02/task205.sh

# Continue for all Phase 2 tasks (201-209)
```

### Phase 4: Configuration

**Source:** `atomic-claude/config/`
**Target:** `atomic-claude2/config/`

```bash
cd /Users/jamesterbeest/dev/atomic-claude2

# Copy models config (then convert JSON → YAML)
cp ../atomic-claude/config/models.json config/models.json
# Then: Convert to models.yaml

# Create defaults.yaml (new file based on atomic.sh defaults)
```

### Phase 5: Agent & Audit Integration

**Source:** `atomic-claude/agents/` and `atomic-claude/audits/`
**Target:** Git submodules or symlinks

```bash
cd /Users/jamesterbeest/dev/atomic-claude2

# Option A: Git submodules (if agents/audits are separate repos)
git submodule add <agents-repo-url> agents
git submodule add <audits-repo-url> audits

# Option B: Symlinks (if staying in same parent directory)
ln -s ../atomic-claude/agents agents
ln -s ../atomic-claude/audits audits
```

---

## File Naming Conventions

### Task Scripts

**Old naming:** `NNN-task-name.sh`
**New naming:** `taskNNN.sh`

| Source | Target |
|--------|--------|
| `001-mode-selection.sh` | `task001.sh` |
| `205-prd-authoring.sh` | `task205.sh` |
| `604-refinement.sh` | `task604.sh` |

**Rationale:**
- Shorter, cleaner
- Consistent with orchestrator naming (orchestrator00.py)
- Easier to type and reference

### Orchestrators

**Old naming:** Phase run scripts mixed with tasks
**New naming:** `orchestratorNN.py` in phase directory

| Source | Target |
|--------|--------|
| `phases/0-setup/run.sh` | `phases/phase00/orchestrator00.py` |
| `phases/2-prd/run.sh` | `phases/phase02/orchestrator02.py` |

---

## What NOT to Copy

### Runtime Artifacts (Generate Fresh)
- `.outputs/` - Will be generated during runs
- `.state/` - Fresh state for atomic-claude2
- `.logs/` - Fresh logs

### Temporary/Scratch Files
- `reports/` - Scratch work, don't copy
- `.claude/` - Session-specific, don't copy
- `*.backup*` - Backup files, don't copy

### Git/IDE Files
- `.git/` - Fresh git repo for atomic-claude2
- `.vscode/` - User-specific IDE settings
- `.DS_Store` - OS files

---

## Verification After Extraction

### Core Module Check
```bash
cd /Users/jamesterbeest/dev/atomic-claude2

# Verify imports work
python -c "from core.providers import ProviderRouter; print('✓ Providers loaded')"
python -c "from core.memory import MemoryManager; print('✓ Memory loaded')"
python -c "from core.state import StateManager; print('✓ State loaded')"
```

### Directory Purity Check
```bash
cd /Users/jamesterbeest/dev/atomic-claude2

# Ensure no project artifacts leaked in
python main.py validate
# Should show: ✅ Directory pristine
```

### Task Script Check
```bash
cd /Users/jamesterbeest/dev/atomic-claude2

# Verify Phase 0 has all tasks
ls phases/phase00/task*.sh
# Should show: task001.sh, task002.sh, task003.sh, task004.sh, task006.sh, task009.sh

# Verify Phase 2 has all tasks
ls phases/phase02/task*.sh
# Should show: task201.sh through task209.sh
```

---

## Timeline

### Week 1: Core Extraction
- Day 1: Core modules (providers, memory, llm, state, config, ui)
- Day 2: Dashboard (copy + fix 5 bugs)
- Day 3-5: Phase 0-2 task scripts

### Week 2: Remaining Phases + Polish
- Day 6-7: Phase 3-9 task scripts
- Day 8: Configuration, agents, audits
- Day 9-10: Testing, documentation, validation

---

## Archive Strategy (After Atomic-Claude2 Proven)

Once atomic-claude2 passes all tests:

```bash
# In /Users/jamesterbeest/dev/

# 1. Archive old versions
mv atomic-claude atomic-claude-bash-archived
mv atomic-claude-python atomic-claude-python-archived

# 2. Graduate atomic-claude2 to main
mv atomic-claude2 atomic-claude

# 3. Update git
cd atomic-claude
git checkout main
# Merge or replace main branch with atomic-claude2 content

# 4. Archive old branches
git branch -m main main-bash-archived
git branch -m atomic-claude2 main
```

---

## Key Reminders

✅ **Always COPY from source**, never move
✅ **Verify imports** after extracting each module
✅ **Run validation** after extraction to ensure purity
✅ **Keep atomic-claude untouched** until atomic-claude2 is proven
✅ **Test incrementally** - don't wait until everything is extracted

❌ **Don't modify atomic-claude** during extraction
❌ **Don't move files** from atomic-claude to atomic-claude2
❌ **Don't copy runtime artifacts** (.outputs, .state, .logs)
❌ **Don't copy scratch/temporary files**

---

**Ready to start extraction! Follow this guide to build atomic-claude2 safely.**
