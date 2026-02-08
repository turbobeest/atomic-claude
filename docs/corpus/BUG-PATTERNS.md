# Bug Patterns - Bash Script Migration

This document tracks common bug patterns when migrating bash task scripts from atomic-claude to atomic-claude2, to prevent repetition when adding more phases.

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
- [ ] List all task scripts in phase (e.g., task201.sh, task202.sh, ...)
- [ ] Note which tasks are interactive (need UAT inputs)
- [ ] Check for any GNU-specific commands (grep with -z, head -z, etc.)

### After Copying
- [ ] Add library sourcing to ALL task scripts (`source "$LIB_DIR/atomic.sh"`)
- [ ] Add execution blocks to ALL task scripts (`if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then`)
- [ ] Fix ALL arithmetic operations: `((var++))` → `((var++)) || true`
- [ ] Run `bash -n` on ALL scripts to check syntax
- [ ] Search for corrupted syntax patterns: `grep -n "default:" phases/phaseNN/*.sh`
- [ ] Create orchestratorNN.py following the pattern
- [ ] Add `create_closeout()` function to orchestrator
- [ ] Update uat_runner.py with prescribed inputs for new phase
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

## Lessons Learned

1. **Always validate syntax after copying**: `bash -n script.sh`
2. **Set -e is aggressive**: Add `|| true` liberally to non-critical operations
3. **Closeout is critical**: Next phase won't start without it
4. **UAT needs exact input sequences**: Count prompts carefully
5. **macOS compatibility matters**: Test on both Linux and macOS if possible
6. **Pattern search prevents repetition**: Use grep to find issues across all scripts

---

## Future Improvements

- [ ] Create pre-migration validation script
- [ ] Automate arithmetic `|| true` insertion
- [ ] Build orchestrator generator from phase metadata
- [ ] Auto-generate UAT input sequences from task prompts
- [ ] Add bash linting to CI/CD

---

Last Updated: 2026-02-04
