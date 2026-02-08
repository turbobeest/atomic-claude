# Bug Patterns - Bash Script Migration

This document tracks common bug patterns when migrating bash task scripts from atomic-claude to atomic-claude2, to prevent repetition when adding more phases.

## Important Notes

### UAT Mode Limitations

**Critical Understanding**: The UAT mode bypasses in Tasks 105 and 106 create **fake minimal outputs** to prevent the pipeline from hanging. This means:

- ✅ UAT validates that tasks CAN execute without errors
- ✅ UAT validates phase transitions and state tracking
- ❌ UAT does NOT validate actual agent selection or discovery work
- ❌ UAT does NOT validate LLM interactions

**For Real Testing**: You need:
1. Actual agents repository with `agent-manifest.json`
2. Actual audits repository with `AUDIT-INVENTORY.csv`
3. LLM provider configured (not just mock mode)

**When UAT Mode is Sufficient**:
- Testing refactoring changes to orchestrators
- Testing state persistence and phase transitions
- Testing task script execution flow
- Testing error handling and validation

**When Real Mode is Required**:
- Testing agent selection logic
- Testing LLM prompt construction
- Testing discovery dialogue quality
- Testing audit recommendations

---

## Recent Fixes (2026-02-04)

### Task 109 & 110 (Phase Audit & Closeout)
- **Issue**: Both tasks have interactive prompts waiting for stdin during UAT
- **Fix**: Added `ATOMIC_UAT_MODE` bypass to both tasks
  - Task 109: Skips audit mode selection, creates minimal audit output
  - Task 110: Auto-approves closeout, creates minimal closeout files
- **Arithmetic Fix**: Task 109 lines 218, 236 - added `|| true`
- **Pattern**: #1 (Arithmetic) + #8 (Interactive Conversation Loops)

### Task 104 (Agent Selection)
- **Issue**: Interactive conversation loop waiting for stdin during UAT run
- **Fix**: Added `ATOMIC_UAT_MODE` bypass to create default agent selection
- **Pattern**: #8 (Interactive Conversation Loops)
- **Output**: Creates minimal `selected-agents.json` and `agent-roster.json` with default agents

### Dashboard Project Alignment
- **Issue**: Dashboard runs for one project (test-project2) but doesn't switch when UAT runs for atomic-claude2
- **Fix**: Modified `dashboard/start-dashboard.sh` to:
  1. Set `ATOMIC_ROOT` from environment or script location
  2. Check if running dashboard serves different project
  3. Kill and restart dashboard if project changed
- **Pattern**: #9 (Dashboard Port Configuration) - extended
- **Detection**: Dashboard shows wrong project name or data
- **Prevention**: Always export ATOMIC_ROOT before starting dashboard

### Agents & Audits Repositories Added
- **Issue**: Tasks 104+ failed because agent-manifest.json and AUDIT-INVENTORY.csv were missing
- **Fix**: Copied entire agents/ and audits/ directories from atomic-claude
- **Files**: `agents/agent-manifest.json` (221 agents), `audits/AUDIT-INVENTORY.csv` (2,186 audits)
- **Updated**: `.gitignore` to allow agents/**/*.{json,csv,md} and audits/**/*.{csv,md}
- **Location**: `/Users/jamesterbeest/dev/atomic-claude2/agents/` and `/audits/`

### Task 106 (Discovery Work)
- **Issue**: Arithmetic operation `((files_ingested++))` on line 301 failed with `set -e` when starting at 0
- **Fix**: Added `|| true` to line 301 and all other arithmetic operations (lines 107, 143, 439)
- **Pattern**: #1 (Arithmetic with set -e)
- **Prevention**: Always search for `((` after copying and bulk-fix with sed

### Task 105 & 106 UAT Mode
- **Issue**: Interactive conversation loops waiting for stdin during UAT runs
- **Fix**: Added `ATOMIC_UAT_MODE` bypass at start of both tasks to skip conversations and create minimal outputs
- **Pattern**: #8 (Interactive Conversation Loops)
- **Prevention**: Add UAT mode to ALL tasks with `read -e` in loops

### Dashboard Port Mismatch
- **Issue**: Hardcoded port 5173 but actual dashboard runs on 5174
- **Fix**: Changed default port to 5174 in all dashboard scripts and task002.sh
- **Pattern**: #9 (Dashboard Port Configuration)
- **Files Changed**: `dashboard/start-dashboard.sh`, `dashboard/open-dashboard.sh`, `phases/phase00/task002.sh`

---

## Critical Patterns

### 1. Arithmetic with `set -e` ⚠️

**Pattern**: Arithmetic operations return the old value, causing `set -e` to exit when starting from 0.

**Symptoms**:
```bash
_COUNTER=0
((_COUNTER++))  # Returns 0, triggers set -e exit!
```

**Fix**: Add `|| true` to all arithmetic operations:
```bash
((_COUNTER++)) || true
((_CHECKS_PASS++)) || true
((count--)) || true
```

**Affected**: Every task that uses counter variables

**Detection**: Look for `((` in bash scripts, especially in loops or validation sections

---

### 2. Corrupted Bash Syntax 🐛

**Pattern**: Copy-paste or autocomplete corrupts conditional syntax.

**Symptoms**:
```bash
# WRONG
if (default: [ -n "${VAR[$key):-}" ]]; then

# CORRECT
if [ -n "${VAR[$key]:-}" ]; then
```

**Fix**: Manual syntax correction

**Affected**: task103importrequirements.sh (line 94)

**Detection**:
- Bash reports "syntax error near unexpected token `then'"
- Look for stray characters like `(default:` or mismatched brackets

**Prevention**: Always run `bash -n script.sh` after copying scripts

---

### 3. Missing Closeout Files 📄

**Pattern**: Phase orchestrators don't create closeout.json after completion.

**Symptoms**:
- Phase completes successfully
- Next phase Task 001 fails with "closeout not found"
- `atomic_find_closeout()` returns empty string

**Fix**: Add closeout creation to orchestrator:
```python
def create_closeout(phase_id: str, tasks: list):
    """Create phase closeout file."""
    import os
    from pathlib import Path
    from datetime import datetime
    import json

    atomic_root = Path(os.environ.get("ATOMIC_ROOT", Path.cwd()))
    output_dir = atomic_root / ".outputs" / phase_id
    output_dir.mkdir(parents=True, exist_ok=True)

    closeout_file = output_dir / "closeout.json"
    phase_num = int(phase_id.split("-")[0])
    completed_tasks = [task_id for task_id, _, _ in tasks]

    closeout_data = {
        "phase": phase_id,
        "phase_num": phase_num,
        "completed_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "tasks_completed": completed_tasks,
        "summary": f"Phase {phase_num} (...) completed successfully."
    }

    with open(closeout_file, "w") as f:
        json.dump(closeout_data, f, indent=2)

# Call after phase_complete()
create_closeout(phase_id, tasks)
```

**Affected**: All phase orchestrators

**Detection**: Check for closeout.json in `.outputs/{phase}/` after phase completion

---

### 4. Missing Library Sourcing 📚

**Pattern**: Task scripts don't source atomic.sh library.

**Symptoms**:
- Script defines functions but doesn't execute them
- Functions like `atomic_invoke()`, `atomic_step()` are undefined
- Script exits without doing anything

**Fix**: Add at top of every task script:
```bash
#!/usr/bin/env bash
# Task NNN: Description

# Source required libraries
set -euo pipefail
LIB_DIR="${ATOMIC_LIB_DIR:-$(dirname "$0")/../../lib}"
source "$LIB_DIR/atomic.sh"
```

**Affected**: All task scripts (task001.sh through task110.sh)

**Detection**: Script runs but produces no output or errors

---

### 5. Missing Execution Blocks 🎯

**Pattern**: Task scripts don't have execution blocks to run when called directly.

**Symptoms**:
- Script can be sourced but doesn't run standalone
- `bash taskNNN.sh` does nothing

**Fix**: Add at bottom of every task script:
```bash
# Execute if run directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    task_NNN_function_name
fi
```

**Affected**: All task scripts

**Detection**: Run `bash phases/phaseNN/taskNNN.sh` - should execute, not exit silently

---

### 6. UAT Input Handling 🤖

**Pattern**: Interactive tasks wait for user input during UAT runs.

**Symptoms**:
- UAT hangs waiting for stdin
- Task doesn't receive prescribed inputs from uat_runner.py
- Task shows output but then fails (exit code 1)
- Expected outputs not created

**Root Causes**:
1. **Missing inputs** - Task expects more inputs than provided
2. **Wrong input values** - Task expects "3" but gets "a"
3. **Multi-turn conversations** - Task has dialogue loop requiring "done" to exit

**Fix**: Count ALL prompts carefully and provide correct input for each:

```python
auto_input = "\n".join([
    "",        # Task 101: Entry validation (press Enter)
    "",        # Task 102: No materials (1st prompt)
    "",        # Task 102: Continue (2nd prompt)
    "",        # Task 103: Press Enter (no RST auto-detected)
    "3",       # Task 104: Use built-in defaults
    "This is a UAT test.",  # Task 105: Vision text (single line!)
    "done",    # Task 105: Exit dialogue loop (CRITICAL!)
    "1",       # Task 107: Select first approach
    # ... rest of inputs
])
```

**Special Case - Task 105 (Opening Dialogue)**:
- Expects vision text on first prompt
- Expects "done" (or "skip") on second prompt to exit conversation loop
- Will fail if only one input provided

**Affected**: All interactive tasks (102, 103, 104, 105, 107, 108, 109, 110)

**Detection**:
- Task shows partial output then exits with code 1
- UAT log shows "❌ Task NNN failed"
- Manual test: Run task standalone and count all `read` prompts

**Prevention**: For each new phase, manually run tasks and count prompts before writing UAT inputs

---

### 7. macOS vs. Linux Command Differences 🍎

**Pattern**: GNU/Linux commands have different syntax on macOS.

**Symptoms**:
```
head: invalid option -- z
usage: head [-n lines | -c bytes] [file ...]
```

**Fix**: Use portable syntax:
```bash
# WRONG (GNU head)
head -z file.txt

# CORRECT (portable)
head -n 20 file.txt
```

**Affected**: Task 102 (corpus collection) uses `head -z`

**Detection**: macOS shows "invalid option" errors

---

## Checklist for New Phase Migration

When copying a new phase from atomic-claude to atomic-claude2:

### Before Copying
- [ ] **Verify agents/ and audits/ repositories exist** in atomic-claude2
  - [ ] Check `agents/agent-manifest.json` exists
  - [ ] Check `audits/AUDIT-INVENTORY.csv` exists
  - [ ] If missing, copy from atomic-claude: `cp -r ../atomic-claude/agents/ ./` and `cp -r ../atomic-claude/audits/ ./`
- [ ] List all task scripts in phase (e.g., task201.sh, task202.sh, ...)
- [ ] Note which tasks are interactive (need UAT inputs)
- [ ] Check for any GNU-specific commands (grep with -z, head -z, etc.)

### After Copying
- [ ] Add library sourcing to ALL task scripts (`source "$LIB_DIR/atomic.sh"`)
- [ ] Add execution blocks to ALL task scripts (`if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then`)
- [ ] Fix ALL arithmetic operations: `((var++))` → `((var++)) || true`
  - [ ] Use sed for bulk fix: `sed -i.bak 's/((i++))/((i++)) || true/g' phases/phaseNN/*.sh`
  - [ ] Check for remaining: `grep -n '((' phases/phaseNN/*.sh | grep -v '|| true'`
- [ ] Run `bash -n` on ALL scripts to check syntax
- [ ] Search for corrupted syntax patterns: `grep -n "default:" phases/phaseNN/*.sh`
- [ ] Add UAT mode bypass to interactive tasks:
  - [ ] Identify conversation loops (tasks with `while` + `read -e`)
  - [ ] Add `if [[ "${ATOMIC_UAT_MODE:-false}" == "true" ]]; then` bypass
  - [ ] Create minimal required outputs in UAT bypass
- [ ] Verify dashboard port references (should be 5174, not 5173)
- [ ] Create orchestratorNN.py following the pattern
- [ ] Add `create_closeout()` function to orchestrator
- [ ] Update uat_runner.py with prescribed inputs OR add UAT mode to tasks
- [ ] Test phase standalone: `python phases/phaseNN/orchestratorNN.py`
- [ ] Test via main.py: `python main.py run N`
- [ ] Test via UAT: `./test/run_uat.sh --phase N`

### Validation
- [ ] All tasks complete without errors
- [ ] closeout.json created in `.outputs/N-phase/`
- [ ] State tracking updated in `.state/task-state.json`
- [ ] Next phase can read closeout.json

---

## Quick Fixes Reference

```bash
# Find arithmetic operations needing || true
grep -rn '((' phases/phaseNN/*.sh | grep -v '|| true'

# Find corrupted syntax
grep -n "default:" phases/phaseNN/*.sh
grep -n "(.*:[" phases/phaseNN/*.sh

# Check bash syntax
for f in phases/phaseNN/*.sh; do bash -n "$f" || echo "FAIL: $f"; done

# Find missing library sourcing
for f in phases/phaseNN/*.sh; do
    grep -q "source.*atomic.sh" "$f" || echo "MISSING: $f"
done

# Find missing execution blocks
for f in phases/phaseNN/*.sh; do
    grep -q 'BASH_SOURCE.*BASH_SOURCE' "$f" || echo "MISSING: $f"
done
```

---

### 8. Interactive Conversation Loops 💬

**Pattern**: Tasks with multi-turn conversations (like Task 105) can't easily be automated via stdin piping.

**Symptoms**:
- Agent prints opening message
- Task hangs waiting for user input
- Prescribed inputs don't reach the script
- Exit code 1 after timeout

**Fix**: Add UAT mode bypass for complex interactive tasks:

```bash
# At top of task function
if [[ "${ATOMIC_UAT_MODE:-false}" == "true" ]]; then
    echo ""
    echo -e "  ${YELLOW}⚡${NC} UAT Mode: Skipping interactive dialogue"
    echo ""

    # Create minimal output that satisfies next tasks
    cat > "$output_file" << 'EOF'
{
  "conversation": [
    {"role": "agent", "content": "UAT mode: Skipped"},
    {"role": "human", "content": "UAT test validation"}
  ],
  "synthesis": { /* minimal required data */ }
}
EOF

    atomic_success "Task complete (UAT mode)"
    return 0
fi
```

**Affected**:
- Task 104 (Agent Selection)
- Task 105 (Opening Dialogue)
- Task 106 (Discovery Work)
- Task 109 (Phase Audit)
- Task 110 (Closeout)
- Any multi-turn conversation tasks or interactive approval prompts

**Detection**: Task shows agent message but then hangs/fails

**Environment Variable**: Set `ATOMIC_UAT_MODE=true` in test environment

**When to Add UAT Mode:**
- Interactive conversation loops with `read -e`
- Multi-turn agent deliberations
- Tasks that require back-and-forth dialogue
- Any task that takes user input more than twice

---

### 9. Dashboard Port Configuration 🌐

**Pattern**: Dashboard port hardcoded incorrectly or inconsistently.

**Symptoms**:
- Documentation says port 5173 but actual port is 5174
- Browser opens to wrong port
- Dashboard appears offline when it's actually running

**Fix**: Use consistent port variable throughout:

```bash
# In dashboard scripts and task002.sh
PORT="${ATOMIC_TASKS_PORT:-5174}"

# Check if already running (correct port)
if ! lsof -Pi :5174 -sTCP:LISTEN -t >/dev/null 2>&1; then
    # Start dashboard
fi
```

**Affected Files**:
- `dashboard/start-dashboard.sh` - Server startup
- `dashboard/open-dashboard.sh` - Browser launch
- `phases/phase00/task002.sh` - Auto-launch check
- `phases/phase01/task104agentselection.sh` - Dashboard references

**Detection**:
- `lsof -Pi :5173 -sTCP:LISTEN` returns nothing
- `lsof -Pi :5174 -sTCP:LISTEN` shows node process

**Standard Ports**:
- **5174** - Tasks dashboard (default)
- **5173** - Alternative/legacy port

---

## Lessons Learned

1. **Always validate syntax after copying**: `bash -n script.sh`
2. **Set -e is aggressive**: Add `|| true` liberally to non-critical operations
3. **Closeout is critical**: Next phase won't start without it
4. **UAT needs exact input sequences**: Count prompts carefully OR add UAT mode bypass
5. **macOS compatibility matters**: Test on both Linux and macOS if possible
6. **Pattern search prevents repetition**: Use grep to find issues across all scripts
7. **Interactive tasks need UAT mode**: Complex conversations should detect ATOMIC_UAT_MODE and skip
8. **Dashboard auto-launch**: Copy dashboard files and update task002.sh path

---

## Future Improvements

- [ ] Create pre-migration validation script
- [ ] Automate arithmetic `|| true` insertion
- [ ] Build orchestrator generator from phase metadata
- [ ] Auto-generate UAT input sequences from task prompts
- [ ] Add bash linting to CI/CD

---

Last Updated: 2026-02-04
