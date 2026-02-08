# Phase 00 & 01 Extraction Plan

**Goal:** Extract and test Phase 00 (Setup) and Phase 01 (Discovery) to prove the architecture works before scaling to all phases.

---

## Why Start with Phase 00 & 01?

1. **Phase 00 is simple** - 6 tasks, mostly configuration collection
2. **Phase 01 is moderate** - More complex with agent selection, proves orchestration
3. **Together they prove the pattern** - If these work, all phases will work
4. **Fast validation** - Can test end-to-end in minutes, not hours
5. **Early feedback** - Catch architecture issues before extracting all phases

---

## Phase 00: Setup

### Tasks to Extract

| Task ID | Name | Source File | Target File | Complexity |
|---------|------|-------------|-------------|------------|
| 001 | Mode selection | `phases/0-setup/tasks/001-mode-selection.sh` | `phases/phase00/task001.sh` | Low |
| 002 | Config collection | `phases/0-setup/tasks/002-config-collection.sh` | `phases/phase00/task002.sh` | Low |
| 003 | Config review | `phases/0-setup/tasks/003-config-review.sh` | `phases/phase00/task003.sh` | Low |
| 004 | API keys | `phases/0-setup/tasks/004-api-keys.sh` | `phases/phase00/task004.sh` | Low |
| 006 | Reference materials | `phases/0-setup/tasks/006-reference-materials.sh` | `phases/phase00/task006.sh` | Low |
| 009 | Environment check | `phases/0-setup/tasks/009-environment-check.sh` | `phases/phase00/task009.sh` | Low |

### Extraction Commands

```bash
cd /Users/jamesterbeest/dev/atomic-claude2

# Copy Phase 0 tasks
cp ../atomic-claude/phases/0-setup/tasks/001-mode-selection.sh phases/phase00/task001.sh
cp ../atomic-claude/phases/0-setup/tasks/002-config-collection.sh phases/phase00/task002.sh
cp ../atomic-claude/phases/0-setup/tasks/003-config-review.sh phases/phase00/task003.sh
cp ../atomic-claude/phases/0-setup/tasks/004-api-keys.sh phases/phase00/task004.sh
cp ../atomic-claude/phases/0-setup/tasks/006-reference-materials.sh phases/phase00/task006.sh
cp ../atomic-claude/phases/0-setup/tasks/009-environment-check.sh phases/phase00/task009.sh
```

### Orchestrator Updates

**File:** `phases/phase00/orchestrator00.py`

Currently has stub implementations. Need to:
1. Import and call the actual bash scripts
2. Use `subprocess` to execute .sh files
3. Pass correct environment variables
4. Capture and validate output

**Pattern:**
```python
def task_001_mode_selection() -> bool:
    """Task 001: Mode selection"""
    result = subprocess.run(
        ["bash", "phases/phase00/task001.sh"],
        cwd=Path(__file__).parent.parent.parent,
        env=get_task_environment("0-setup", "001"),
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(result.stdout)
        return True
    else:
        print(result.stderr)
        return False
```

---

## Phase 01: Discovery

### Tasks to Extract

| Task ID | Name | Source File | Target File | Complexity |
|---------|------|-------------|-------------|------------|
| 101 | Entry initialization | `phases/1-discovery/tasks/101-entry-initialization.sh` | `phases/phase01/task101.sh` | Low |
| 103 | Import requirements | `phases/1-discovery/tasks/103-import-requirements.sh` | `phases/phase01/task103.sh` | Medium |
| 104 | Agent selection | `phases/1-discovery/tasks/104-agent-selection.sh` | `phases/phase01/task104.sh` | High |
| 106 | Discovery work | `phases/1-discovery/tasks/106-discovery-work.sh` | `phases/phase01/task106.sh` | High |
| 108 | Discovery diagrams | `phases/1-discovery/tasks/108-discovery-diagrams.sh` | `phases/phase01/task108.sh` | Medium |
| 109 | Phase audit | `phases/1-discovery/tasks/109-phase-audit.sh` | `phases/phase01/task109.sh` | Medium |
| 110 | Closeout | `phases/1-discovery/tasks/110-closeout.sh` | `phases/phase01/task110.sh` | Low |

### Extraction Commands

```bash
cd /Users/jamesterbeest/dev/atomic-claude2

# Copy Phase 1 tasks
cp ../atomic-claude/phases/1-discovery/tasks/101-entry-initialization.sh phases/phase01/task101.sh
cp ../atomic-claude/phases/1-discovery/tasks/103-import-requirements.sh phases/phase01/task103.sh
cp ../atomic-claude/phases/1-discovery/tasks/104-agent-selection.sh phases/phase01/task104.sh
cp ../atomic-claude/phases/1-discovery/tasks/106-discovery-work.sh phases/phase01/task106.sh
cp ../atomic-claude/phases/1-discovery/tasks/108-discovery-diagrams.sh phases/phase01/task108.sh
cp ../atomic-claude/phases/1-discovery/tasks/109-phase-audit.sh phases/phase01/task109.sh
cp ../atomic-claude/phases/1-discovery/tasks/110-closeout.sh phases/phase01/task110.sh
```

### Orchestrator Creation

**File:** `phases/phase01/orchestrator01.py`

Create new orchestrator following Phase 00 pattern:
```python
#!/usr/bin/env python3
"""
Phase 1 Orchestrator (orchestrator01.py)

Orchestrator for Phase 1: Discovery - Requirements gathering and agent selection.

Tasks:
  101 - Entry initialization
  103 - Import requirements
  104 - Agent selection
  106 - Discovery work
  108 - Discovery diagrams
  109 - Phase audit
  110 - Closeout
"""

# ... similar structure to orchestrator00.py
```

---

## Core Dependencies Required

Before Phase 00/01 can run, need these core modules:

### 1. Core Modules (Extract First)

#### core/providers.py
```bash
# Copy AS-IS (works perfectly)
cp ../atomic-claude-python/lib/provider.py core/providers.py
```

#### core/memory.py
```bash
# Copy AS-IS (claude-mem working)
cp ../atomic-claude-python/lib/memory.py core/memory.py
```

#### core/state.py
```bash
# Copy and clean
cp ../atomic-claude-python/lib/task_state.py core/state.py
# Then: Update imports, clean up
```

#### core/llm.py
```bash
# Copy and clean
cp ../atomic-claude-python/lib/atomic.py core/llm.py
# Then: Remove TODOs, update imports
```

#### core/config.py
```bash
# Extract from lib/atomic.sh
# Parse environment variables, config files
```

#### core/ui.py (already stubbed)
```bash
# Extract UI functions from lib/atomic.sh
# Functions: atomic_step, atomic_success, atomic_error, etc.
```

### 2. Environment Setup

**Create:** `core/environment.py`

```python
def get_task_environment(phase_id: str, task_id: str) -> dict:
    """
    Build environment variables for task execution.

    Returns dict with:
    - ATOMIC_ROOT
    - ATOMIC_OUTPUT_DIR
    - CURRENT_PHASE
    - CURRENT_TASK
    - All provider configs
    - All model configs
    """
    pass
```

### 3. Subprocess Runner

**Create:** `core/subprocess_runner.py`

```python
def run_task_script(
    script_path: Path,
    phase_id: str,
    task_id: str,
    timeout: int = 600
) -> bool:
    """
    Execute bash task script with proper environment.

    Handles:
    - Environment setup
    - Working directory
    - Output capture
    - Error handling
    - Timeout
    """
    pass
```

---

## Extraction Order

### Day 1: Core Infrastructure

**Morning:**
1. ✅ Copy `core/providers.py` (AS-IS)
2. ✅ Copy `core/memory.py` (AS-IS)
3. ⚠️ Copy `core/state.py` (clean imports)
4. ⚠️ Copy `core/llm.py` (clean TODOs)
5. 🆕 Create `core/config.py` (extract from atomic.sh)
6. 🆕 Create `core/environment.py` (new)
7. 🆕 Create `core/subprocess_runner.py` (new)

**Afternoon:**
8. Test core module imports
9. Fix any import errors
10. Validate with simple script

### Day 2: Phase 00 Extraction

**Morning:**
1. Copy all 6 Phase 00 task scripts
2. Update `orchestrator00.py` to call bash scripts
3. Update imports and environment setup

**Afternoon:**
4. Test Phase 00 end-to-end (quick mode)
5. Fix any issues
6. Validate state tracking works

### Day 3: Phase 01 Extraction

**Morning:**
1. Copy all 7 Phase 01 task scripts
2. Create `orchestrator01.py`
3. Update imports and environment setup

**Afternoon:**
4. Test Phase 01 end-to-end
5. Fix any issues
6. Validate agent selection works

### Day 4: Integration Testing

**Full Day:**
1. Test Phase 00 → Phase 01 flow
2. Test resume functionality
3. Test backtrack functionality
4. Validate directory purity (no violations)
5. Fix any integration issues
6. Document issues for remaining phases

---

## Testing Plan

### Phase 00 Tests

**Test 1: Quick Mode (Minimal)**
```bash
cd /Users/jamesterbeest/dev/atomic-claude2

# Create minimal setup.md
mkdir -p initialization
cat > initialization/setup.md << 'EOF'
name: test-project
type: webapp
tech_stack: react, nodejs
llm.primary_model: sonnet
EOF

# Run Phase 0
python main.py run 0
```

**Expected output:**
- ✅ All 6 tasks complete
- ✅ State saved to `.state/task-state.json`
- ✅ Config saved to `.outputs/0-setup/project-config.json`
- ✅ No directory violations
- ✅ Dashboard shows Phase 0 complete (if running)

**Test 2: Resume Mid-Phase**
```bash
# Run up to task 004
python main.py run 0 --resume-at=004

# Should skip 001-003, run 004-009
```

**Test 3: Backtrack**
```bash
# Complete Phase 0
python main.py run 0

# Backtrack to task 002
python main.py backtrack 0 002

# Re-run from 002
python main.py run 0 --resume-at=002
```

### Phase 01 Tests

**Test 1: Full Discovery**
```bash
cd /Users/jamesterbeest/dev/atomic-claude2

# Run Phase 1 (requires Phase 0 complete)
python main.py run 1
```

**Expected output:**
- ✅ All 7 tasks complete
- ✅ Agents selected and saved
- ✅ Discovery artifacts in `.outputs/1-discovery/`
- ✅ State updated
- ✅ No directory violations

**Test 2: Agent Selection Validation**
```bash
# Check agents selected
cat .outputs/1-discovery/selected-agents.json
# Should have 2-5 agents from agent-manifest.json
```

### Integration Tests

**Test 1: Phase 00 → 01 Flow**
```bash
# Fresh start
python main.py reset

# Run both phases
python main.py run 0
python main.py run 1

# Validate
python main.py status
# Should show both phases complete
```

**Test 2: Directory Purity Throughout**
```bash
# After each phase
python main.py validate
# Should always show: ✅ Directory pristine
```

**Test 3: Memory System**
```bash
# Check memory saved
ls .state/memory/phase-0/
ls .state/memory/phase-1/
# Should have task memory files
```

---

## Success Criteria

### Phase 00 Success
- [ ] All 6 tasks execute without errors
- [ ] Configuration collected and saved
- [ ] State tracking works (can resume)
- [ ] Directory remains pristine (no violations)
- [ ] Can backtrack and re-run

### Phase 01 Success
- [ ] All 7 tasks execute without errors
- [ ] Agents selected from manifest (2-5 agents)
- [ ] Discovery artifacts created
- [ ] State tracking works
- [ ] Directory remains pristine
- [ ] Can backtrack and re-run

### Integration Success
- [ ] Phase 00 → 01 flow works seamlessly
- [ ] Resume works across phase boundary
- [ ] Backtrack works to any task in either phase
- [ ] Memory persists correctly
- [ ] Dashboard shows accurate status (if running)
- [ ] No project artifacts leak into atomic-claude2/

---

## Known Challenges

### Challenge 1: Environment Variables

**Issue:** Bash scripts expect many environment variables

**Solution:** `core/environment.py` builds complete env dict

**Variables needed:**
- `ATOMIC_ROOT`
- `ATOMIC_OUTPUT_DIR`
- `ATOMIC_STATE_DIR`
- `ATOMIC_AGENT_REPO`
- `ATOMIC_AUDIT_REPO`
- `CLAUDE_PROVIDER`
- `ANTHROPIC_API_KEY` (if using API)
- Plus model configs

### Challenge 2: Working Directory

**Issue:** Bash scripts assume specific working directory

**Solution:** Always run from atomic-claude2 root, pass correct cwd to subprocess

### Challenge 3: Script Dependencies

**Issue:** Tasks source lib/atomic.sh, lib/phase.sh

**Solution:** Copy lib/ directory temporarily, or extract functions to Python

### Challenge 4: Provider Configuration

**Issue:** Bash scripts call atomic_invoke which needs provider routing

**Solution:** Ensure core/providers.py is working before running tasks

### Challenge 5: Agent Manifest

**Issue:** Phase 01 needs agents/agent-manifest.json

**Solution:** Symlink or copy agents/ directory:
```bash
cd /Users/jamesterbeest/dev/atomic-claude2
ln -s ../atomic-claude/agents agents
```

---

## Fallback Plan

If bash script integration is too complex:

### Option A: Convert to Python Immediately

Instead of calling bash scripts, convert tasks to Python:
- Extract logic from .sh files
- Rewrite in Python using core modules
- More work upfront, but cleaner

### Option B: Hybrid Approach

- Simple tasks (001-004, 009): Convert to Python
- Complex tasks (104, 106): Keep bash, call via subprocess
- Gradual conversion over time

### Option C: Bash Wrapper

Keep bash scripts, but:
- Create thin Python wrapper
- Wrapper sets up environment
- Wrapper validates output
- Wrapper updates state

---

## Next Steps

1. **Review this plan** - Any adjustments needed?
2. **Start Day 1** - Extract core modules
3. **Test incrementally** - Validate each module as extracted
4. **Day 2-3** - Extract Phase 00 & 01
5. **Day 4** - Test, fix, validate
6. **Then decide** - If successful, extract remaining phases

---

**Ready to begin! This focused approach proves the architecture before scaling.**
