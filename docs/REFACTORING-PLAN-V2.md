# Atomic Claude Python (ACP) - Refactoring Plan v2

**Date:** February 4, 2026
**Status:** Ready to Execute
**Approach:** Extract & Organize (Not Rewrite)

---

## 🎯 Core Philosophy

**THE CODE WORKS - WE JUST NEED TO ORGANIZE IT**

This is NOT a rewrite. This is an extraction and organization effort:
1. Extract working code from the messy codebase
2. Organize into clean, strict structure
3. Add orchestration for end-of-task processes
4. Fix dashboard bugs (it's 95% perfect)
5. Add organization agent and backtrack capability

### Key Architectural Decision: Grouped Phase Structure

**Phase orchestrators and their tasks live together in the same directory:**
- `phases/phase00/` contains `orchestrator00.py` + all Phase 0 task scripts
- `phases/phase02/` contains `orchestrator02.py` + all Phase 2 task scripts

**Why?** Clear boundaries, easy customization, self-contained packages. Users adding custom tasks just drop new scripts into the phase directory. Everything for a phase is in one place.

---

## 📁 Target Architecture

```
my-project/                    # The project being built
├── ACP/                       # 🎯 Cloned atomic-claude tool
│   │
│   ├── main.py               # Central orchestrator & state machine
│   │
│   ├── core/                 # Extracted utilities (from current lib/)
│   │   ├── __init__.py
│   │   ├── llm.py           # LLM invocation (from atomic.py)
│   │   ├── state.py         # State management (from task_state.py)
│   │   ├── config.py        # Config loading (from atomic.sh)
│   │   ├── memory.py        # Memory system (from memory.py)
│   │   ├── providers.py     # Provider routing (from provider.py)
│   │   └── ui.py            # Console UI (extracted)
│   │
│   ├── phases/              # 🎯 Phase modules (orchestrator + tasks together)
│   │   ├── __init__.py
│   │   ├── phase00/
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator00.py   # Phase 0 orchestrator
│   │   │   ├── task001.sh          # Mode selection
│   │   │   ├── task002.sh          # Config collection
│   │   │   ├── task003.sh          # Config review
│   │   │   ├── task004.sh          # API keys
│   │   │   ├── task006.sh          # Reference materials
│   │   │   └── task009.sh          # Environment check
│   │   ├── phase01/
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator01.py   # Phase 1 orchestrator
│   │   │   ├── task101.sh
│   │   │   ├── task103.sh
│   │   │   └── task110.sh
│   │   ├── phase02/
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator02.py   # Phase 2 orchestrator
│   │   │   ├── task201.sh
│   │   │   ├── task205.sh          # PRD authoring (8-gen workflow)
│   │   │   └── task209.sh
│   │   └── ... (phase03-09)
│   │
│   ├── orchestration/       # 🆕 End-of-task processes
│   │   ├── __init__.py
│   │   ├── organization_agent.py    # Check for misplaced files
│   │   ├── git_manager.py           # Commit/push prompts
│   │   ├── backtrack.py             # Reset to any phase/task
│   │   └── dashboard_sync.py        # Keep dashboard accurate
│   │
│   ├── dashboard/           # Dashboard (mostly extracted as-is)
│   │   ├── server.js        # Express server (fix bugs)
│   │   ├── public/
│   │   │   └── index.html   # UI (fix bugs)
│   │   └── package.json
│   │
│   ├── reports/             # 🆕 Scratch/analysis folder
│   │   ├── README.md        # "Analysis and scratch work only"
│   │   └── .gitignore       # Ignore all except README
│   │
│   ├── .outputs/            # Working artifacts per phase
│   │   ├── 0-setup/
│   │   ├── 2-prd/
│   │   └── ...
│   │
│   ├── .state/              # State tracking
│   │   ├── current-task.json
│   │   ├── task-state.json
│   │   └── memory/
│   │
│   ├── .logs/               # Execution logs
│   │
│   ├── config/              # Configuration
│   │   ├── models.yaml      # LLM provider config
│   │   └── defaults.yaml    # Default settings
│   │
│   └── docs/                # Documentation
│       ├── architecture.md
│       └── user-guide.md
│
├── src/                     # Generated project code
├── tests/                   # Generated project tests
└── docs/                    # Generated project docs
```

### Why Grouped Structure?

**Phase orchestrator + tasks together in same directory:**

**Advantages:**
1. **Clear boundaries** - Everything for Phase 0 lives in `phases/phase00/`
2. **Easy customization** - Users adding custom tasks just drop new scripts in the phase directory
3. **Self-contained** - Each phase is a complete package with its orchestrator and tasks
4. **Natural discovery** - `ls phases/phase02/` shows both orchestrator and all its tasks
5. **Better encapsulation** - Phase can have internal helpers without polluting global namespace
6. **Matches hierarchy principle** - Tasks are "organized under" their phase orchestrator

**Why `orchestrator00.py`, `orchestrator01.py`, etc?**
- **Unique names** - No confusion when multiple orchestrators open in editor
- **Self-documenting** - File name immediately tells you which phase
- **IDE-friendly** - Tab completion and file browsers show distinct names
- **Grep-friendly** - Easy to search for specific orchestrator (grep "orchestrator02")
- **Better stack traces** - Errors show "orchestrator02.py:45" not generic "orchestrator.py:45"

---

## 🔧 What Gets Extracted (Not Rewritten)

### From Current Codebase

| Current File | Extract To | Changes |
|--------------|-----------|---------|
| `atomic-claude-python/lib/atomic.py` | `core/llm.py` | Clean up, remove TODOs |
| `atomic-claude-python/lib/provider.py` | `core/providers.py` | As-is, works perfectly |
| `atomic-claude-python/lib/task_state.py` | `core/state.py` | Clean up |
| `atomic-claude-python/lib/memory.py` | `core/memory.py` | Fix dict issues |
| `lib/atomic.sh` functions | `core/ui.py` | Extract UI functions |
| `phases/2-prd/tasks/205-*.sh` | `phases/phase02/task205.py` | Already works! Just organize |
| `tasks-dashboard/*` | `dashboard/*` | Fix 5 known bugs, keep rest |
| Phase run scripts | `phases/phase0X/orchestrator0X.py` | Convert to Python orchestrators |

**Key Point:** Most Python code already exists and works. We're just organizing it cleanly.

---

## 📋 Execution Plan

### Phase 1: Setup Clean Structure (Day 1)

**Goal:** Create directory tree, move what works

#### Tasks:
1. **Create Directory Structure**
   ```bash
   mkdir -p ACP/{core,orchestration,dashboard,reports,.outputs,.state,.logs,config,docs}
   mkdir -p ACP/phases/{phase00,phase01,phase02,phase03,phase04,phase05,phase06,phase07,phase08,phase09}

   # Create __init__.py files for Python packages
   touch ACP/core/__init__.py
   touch ACP/orchestration/__init__.py
   touch ACP/phases/__init__.py
   touch ACP/phases/phase{00..09}/__init__.py
   ```

2. **Copy Working Dashboard**
   ```bash
   cp -r atomic-claude/tasks-dashboard/* ACP/dashboard/
   ```

3. **Extract Core Modules** (these already work!)
   - Copy `atomic-claude-python/lib/*.py` → `ACP/core/`
   - Rename appropriately (atomic.py → llm.py, etc.)
   - Clean up TODOs (not critical functionality)

4. **Create Configuration**
   - Extract from `config/models.json` → `config/models.yaml`
   - Create `config/defaults.yaml`

**Deliverable:** Clean directory structure with working core modules

**Time:** 4 hours

---

### Phase 2: Main Orchestrator (Day 2)

**Goal:** Central state machine that manages everything

#### Create `main.py`:

```python
#!/usr/bin/env python3
"""
Atomic Claude Python - Central Orchestrator

Usage:
    python main.py run <phase> [--resume-at=<task>]
    python main.py status
    python main.py backtrack <phase> [<task>]
    python main.py reset
"""

import sys
from pathlib import Path
from core.state import StateManager
from orchestration.backtrack import backtrack_to

def run_phase(phase_num: int, resume_at: str = None):
    """Run a phase, optionally resuming from a task."""
    # Import phase orchestrator dynamically
    phase_module = __import__(f"phases.phase{phase_num:02d}.orchestrator", fromlist=["run_phase"])

    # Execute
    success = phase_module.run_phase(resume_at=resume_at)

    if not success:
        print(f"\n⚠️  Phase {phase_num} stopped. To resume:")
        print(f"   python main.py run {phase_num} --resume-at=<task>")
        sys.exit(1)

def show_status():
    """Show current pipeline status."""
    state = StateManager()
    state.display_status()

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Atomic Claude Pipeline")
    subparsers = parser.add_subparsers(dest="command")

    # Run command
    run = subparsers.add_parser("run", help="Run a phase")
    run.add_argument("phase", type=int, help="Phase number (0-9)")
    run.add_argument("--resume-at", help="Resume from task (e.g., task205)")

    # Status command
    subparsers.add_parser("status", help="Show pipeline status")

    # Backtrack command
    back = subparsers.add_parser("backtrack", help="Reset to earlier point")
    back.add_argument("phase", type=int, help="Phase number")
    back.add_argument("task", nargs="?", help="Task to reset to")

    # Reset command
    subparsers.add_parser("reset", help="Reset entire pipeline")

    args = parser.parse_args()

    if args.command == "run":
        run_phase(args.phase, resume_at=args.resume_at)
    elif args.command == "status":
        show_status()
    elif args.command == "backtrack":
        backtrack_to(args.phase, args.task)
    elif args.command == "reset":
        confirm = input("⚠️  Reset entire pipeline? (yes/no): ")
        if confirm.lower() == "yes":
            StateManager().reset_all()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
```

**Deliverable:** Working main.py that can run phases

**Time:** 6 hours

---

### Phase 3: Extract Tasks (Days 3-5)

**Goal:** Convert task scripts to standalone executables

#### Pattern for Each Task:

```python
#!/usr/bin/env python3
"""
Task 205: PRD Authoring
8-stage generation workflow with guardian validation

Location: phases/phase02/task205.py
"""

import sys
from pathlib import Path

# Ensure ACP root is in path (go up 3 levels: task -> phase02 -> phases -> ACP)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.llm import invoke_llm
from core.state import get_task_state, save_task_state, task_running
from core.config import get_config
from orchestration.organization_agent import check_organization
from orchestration.git_manager import prompt_git_actions
from orchestration.dashboard_sync import sync_dashboard

def main():
    """Execute PRD authoring task."""

    # Check prerequisites
    if not get_task_state("2-prd", "204").completed:
        print("❌ Task 204 must complete first")
        return False

    # Mark task as running
    with task_running("2-prd", "205", "PRD Authoring"):

        # Main task logic (extracted from 205-prd-authoring.sh)
        for gen_num in range(1, 9):
            print(f"\n⚡ Generation {gen_num}/8...")

            # Generate section
            content = generate_section(gen_num)

            # Guardian validation
            if not validate_with_guardian(gen_num, content):
                print(f"❌ Guardian rejected generation {gen_num}")
                return False

        # Assemble final PRD
        assemble_prd()

    # End-of-task orchestration
    return end_of_task_orchestration("2-prd", "205")

def end_of_task_orchestration(phase_id: str, task_id: str) -> bool:
    """Standard end-of-task processes."""

    print("\n" + "="*80)
    print("  END-OF-TASK ORCHESTRATION")
    print("="*80 + "\n")

    # 1. Organization check
    print("📁 Checking file organization...")
    misplaced = check_organization(phase_id, task_id)
    if misplaced:
        print(f"\n⚠️  BLOCKER: {len(misplaced)} misplaced files detected:")
        for file in misplaced:
            print(f"   - {file['path']} (expected: {file['correct_location']})")

        action = input("\nAction? [fix/ignore/abort]: ").lower()
        if action == "abort":
            return False
        elif action == "fix":
            fix_organization(misplaced)

    # 2. Git actions
    print("\n📦 Git actions...")
    git_action = prompt_git_actions(phase_id, task_id)
    if git_action == "commit":
        commit_changes(phase_id, task_id)
    elif git_action == "commit_push":
        commit_changes(phase_id, task_id)
        push_changes()
    # else: skip

    # 3. Navigation prompt
    print("\n🧭 Navigation...")
    print("   [c] Continue to next task")
    print("   [b] Backtrack to earlier task")
    print("   [q] Quit")

    choice = input("\nChoice (default: c): ").lower() or "c"

    if choice == "b":
        target = input("Backtrack to (phase/task): ")
        backtrack_to(target)
        return False  # Don't continue forward
    elif choice == "q":
        sys.exit(0)

    # 4. Sync dashboard
    print("\n📊 Syncing dashboard...")
    sync_dashboard()

    # Mark complete
    save_task_state(phase_id, task_id, completed=True)
    print("\n✅ Task 205 complete\n")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```

**Priority Order for Extraction:**
1. Phase 0 tasks (001-009) - Simple, prove pattern
2. Phase 2 task 205 - Complex, already works
3. Phase 3 tasks - Fast-path tested
4. Remaining phases

**Deliverable:** All tasks as standalone Python scripts

**Time:** 3 days (8 tasks/day × 60 tasks = ~3 days)

---

### Phase 4: Orchestration Systems (Days 6-7)

**Goal:** End-of-task automation that maintains order

#### 4A. Organization Agent

```python
# orchestration/organization_agent.py

"""
Organization Agent - Enforces strict file placement

Runs after each task to ensure no artifacts are misplaced.
Creates BLOCKERS if files are out of order.
"""

from pathlib import Path
from typing import List, Dict
import json

ALLOWED_LOCATIONS = {
    "prompts": ".outputs/{phase}/prompts/",
    "outputs": ".outputs/{phase}/outputs/",
    "specs": ".claude/specs/",
    "state": ".state/",
    "logs": ".logs/",
    "reports": "reports/",  # Scratch work only
    "generated_code": "../src/",
    "generated_tests": "../tests/",
    "generated_docs": "../docs/",
}

def check_organization(phase_id: str, task_id: str) -> List[Dict]:
    """
    Check for misplaced files after task completion.

    Returns list of misplaced files with suggested locations.
    """
    misplaced = []
    acp_root = Path(__file__).parent.parent

    # Scan for files in unexpected locations
    for item in acp_root.rglob("*"):
        if item.is_file() and not is_allowed_location(item, phase_id):
            misplaced.append({
                "path": str(item.relative_to(acp_root)),
                "correct_location": suggest_location(item, phase_id),
                "reason": classify_file(item)
            })

    return misplaced

def is_allowed_location(file_path: Path, phase_id: str) -> bool:
    """Check if file is in an allowed location."""
    # Check against allowed patterns
    for location_type, pattern in ALLOWED_LOCATIONS.items():
        pattern = pattern.format(phase=phase_id)
        if str(file_path).startswith(pattern):
            return True

    # Core modules, configs, etc. are allowed
    allowed_dirs = {"core", "phases", "tasks", "orchestration", "dashboard", "config", "docs"}
    if any(part in allowed_dirs for part in file_path.parts):
        return True

    return False

def suggest_location(file_path: Path, phase_id: str) -> str:
    """Suggest correct location for misplaced file."""
    # Logic to determine correct location based on file type
    if file_path.suffix == ".md" and "prompt" in file_path.name:
        return f".outputs/{phase_id}/prompts/"
    elif file_path.suffix == ".json":
        return f".outputs/{phase_id}/outputs/"
    elif file_path.suffix in [".py", ".js", ".ts"]:
        return "../src/"
    else:
        return "reports/"  # When in doubt, scratch folder

def classify_file(file_path: Path) -> str:
    """Classify what type of file this is."""
    if "prompt" in file_path.name:
        return "LLM prompt"
    elif "output" in file_path.name:
        return "LLM response"
    elif file_path.suffix in [".py", ".js"]:
        return "Generated code"
    else:
        return "Unknown artifact"
```

#### 4B. Git Manager

```python
# orchestration/git_manager.py

"""
Git Manager - Handles commit/push prompts

Prompts user after each task for git actions.
Generates contextual commit messages.
"""

import subprocess
from pathlib import Path

def prompt_git_actions(phase_id: str, task_id: str) -> str:
    """
    Prompt user for git actions after task completion.

    Returns: "commit", "commit_push", or "skip"
    """
    print("\n📦 Git Actions")
    print("   [1] Commit changes")
    print("   [2] Commit & push")
    print("   [3] Skip")

    choice = input("\nChoice (default: skip): ").strip()

    if choice == "1":
        return "commit"
    elif choice == "2":
        return "commit_push"
    else:
        return "skip"

def commit_changes(phase_id: str, task_id: str):
    """Commit changes with auto-generated message."""

    # Generate commit message
    message = generate_commit_message(phase_id, task_id)

    print(f"\n💬 Commit message:\n{message}\n")
    confirm = input("Commit with this message? (y/n): ")

    if confirm.lower() == "y":
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", message], check=True)
        print("✅ Changes committed")
    else:
        custom = input("Enter custom message: ")
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", custom], check=True)
        print("✅ Changes committed")

def push_changes():
    """Push changes to remote."""
    try:
        subprocess.run(["git", "push"], check=True)
        print("✅ Changes pushed to remote")
    except subprocess.CalledProcessError:
        print("⚠️  Push failed. Check git status.")

def generate_commit_message(phase_id: str, task_id: str) -> str:
    """Generate contextual commit message."""
    # Map tasks to commit messages
    messages = {
        "2-prd": {
            "205": "feat(prd): Complete PRD with 8-section generation\n\nGenerated comprehensive PRD covering:\n- Vision & executive summary\n- Technical architecture\n- Feature requirements\n- Logical dependencies",
        },
        # ... more mappings
    }

    return messages.get(phase_id, {}).get(task_id, f"feat({phase_id}): Complete {task_id}")
```

#### 4C. Backtrack Script

```python
# orchestration/backtrack.py

"""
Backtrack - Reset to any phase/task with clean slate

Allows user to go back to any point and start fresh.
Clears all state and artifacts after the target point.
"""

from pathlib import Path
import shutil
import json

def backtrack_to(phase: int, task: str = None):
    """
    Reset pipeline to a specific phase/task.

    Args:
        phase: Phase number (0-9)
        task: Optional task ID to reset to (e.g., "task205")

    This will:
    1. Reset state to target point
    2. Clear all artifacts after target
    3. Clear all phases after target
    """

    print(f"\n🔄 Backtracking to Phase {phase}" + (f", {task}" if task else ""))
    print("\n⚠️  WARNING: This will DELETE all work after this point!")
    confirm = input("\nType 'yes' to confirm: ")

    if confirm.lower() != "yes":
        print("❌ Backtrack cancelled")
        return

    # Load state
    state_file = Path(".state/task-state.json")
    with open(state_file) as f:
        state = json.load(f)

    # Determine what to clear
    phases_to_clear = list(range(phase + 1, 10))

    # Clear state for future phases
    for p in phases_to_clear:
        phase_id = f"{p}-{get_phase_name(p)}"
        if phase_id in state["phases"]:
            del state["phases"][phase_id]

    # If task specified, clear subsequent tasks in target phase
    if task:
        phase_id = f"{phase}-{get_phase_name(phase)}"
        tasks = state["phases"].get(phase_id, {}).get("tasks", {})

        # Parse task number
        task_num = int(task.replace("task", ""))

        # Clear tasks after target
        for task_id in list(tasks.keys()):
            if int(task_id) > task_num:
                del tasks[task_id]

    # Clear artifacts
    print("\n📁 Clearing artifacts...")
    outputs_dir = Path(".outputs")
    for p in phases_to_clear:
        phase_dir = outputs_dir / f"{p}-{get_phase_name(p)}"
        if phase_dir.exists():
            shutil.rmtree(phase_dir)
            print(f"   ✓ Cleared {phase_dir}")

    # Clear generated code (optional prompt)
    clear_code = input("\nClear generated code in ../src/? (y/n): ")
    if clear_code.lower() == "y":
        src_dir = Path("../src")
        if src_dir.exists():
            shutil.rmtree(src_dir)
            src_dir.mkdir()
            print("   ✓ Cleared ../src/")

    # Save updated state
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)

    print(f"\n✅ Reset complete. Resume with:")
    print(f"   python main.py run {phase}" + (f" --resume-at={task}" if task else ""))

def get_phase_name(phase_num: int) -> str:
    """Map phase number to name."""
    names = {
        0: "setup", 1: "discovery", 2: "prd", 3: "tasking",
        4: "specification", 5: "implementation", 6: "code-review",
        7: "integration", 8: "deployment-prep", 9: "release"
    }
    return names[phase_num]
```

#### 4D. Dashboard Sync

```python
# orchestration/dashboard_sync.py

"""
Dashboard Sync - Keep dashboard accurate

Validates state files, fixes inconsistencies, triggers dashboard refresh.
"""

import json
from pathlib import Path
import requests

def sync_dashboard():
    """Ensure dashboard shows accurate state."""

    # Validate state files
    validate_state_files()

    # Trigger dashboard refresh (if server running)
    try:
        requests.post("http://localhost:5173/api/refresh", timeout=1)
    except:
        pass  # Dashboard not running, that's ok

def validate_state_files():
    """Check state files for consistency."""

    state_file = Path(".state/task-state.json")
    current_task_file = Path(".state/current-task.json")

    # Ensure files exist
    if not state_file.exists():
        initialize_state_file(state_file)

    # Load and validate
    with open(state_file) as f:
        state = json.load(f)

    # Check for inconsistencies
    # ... validation logic

    print("✅ Dashboard state validated")
```

**Deliverable:** Complete orchestration system

**Time:** 2 days

---

### Phase 5: Fix Dashboard Bugs (Day 8)

**Goal:** Fix 5 known bugs, keep everything else

#### Known Issues to Fix:

1. **Current-task.json staleness** (FIXED in test, port over)
   - Location: `dashboard/server.js` lines 255-304

2. **Provider/model mislabeling** (FIXED in test, port over)
   - Location: `dashboard/public/index.html` lines 920-956

3. **Phase status calculation** (FIXED in test, port over)
   - Logic for "Complete" vs "In Progress"

4. **File organization display**
   - Show files per task properly

5. **Session staleness detection** (FIXED in test, port over)
   - 60s no-update warning

#### Dashboard Fixes:

```bash
# Copy fixed dashboard from test
cp /Users/jamesterbeest/dev/atomic-claude/tasks-dashboard/server.js ACP/dashboard/
cp /Users/jamesterbeest/dev/atomic-claude/tasks-dashboard/public/index.html ACP/dashboard/public/

# Update paths to work with ACP structure
# Fix ATOMIC_ROOT detection
```

**Deliverable:** Bug-free dashboard

**Time:** 1 day

---

### Phase 6: Testing & Documentation (Days 9-10)

**Goal:** Validate everything works, document usage

#### Testing:
1. **Smoke Test**
   - Run Phase 0 end-to-end
   - Verify organization agent works
   - Verify git prompts work
   - Verify backtrack works

2. **Full Pipeline Test**
   - Run fast-path test (Phases 3-9)
   - Verify all orchestration points work
   - Verify dashboard stays accurate

3. **Backtrack Test**
   - Complete Phase 3
   - Backtrack to Phase 2, Task 205
   - Verify clean slate
   - Re-run Phase 2-3

#### Documentation:
1. **User Guide** (`docs/user-guide.md`)
   - How to run pipeline
   - How to backtrack
   - How to customize tasks

2. **Architecture Doc** (`docs/architecture.md`)
   - Directory structure
   - Orchestration flow
   - Adding new tasks

3. **Developer Guide** (`docs/developer-guide.md`)
   - How to add new phases
   - How to modify tasks
   - Testing guidelines

**Deliverable:** Tested, documented system

**Time:** 2 days

---

## 📊 Timeline Summary

| Phase | Days | Focus |
|-------|------|-------|
| 1. Clean Structure | 0.5 | Directory tree, copy dashboard |
| 2. Main Orchestrator | 0.75 | Central state machine |
| 3. Extract Tasks | 3 | Convert to Python scripts |
| 4. Orchestration | 2 | Org agent, git, backtrack, sync |
| 5. Fix Dashboard | 1 | Port test fixes |
| 6. Test & Docs | 2 | Validate, document |
| **Total** | **9.25 days** | **~2 weeks with buffer** |

---

## 🎯 End-of-Task Flow (Repeatable Process)

```
Task Execution
      ↓
Check Organization (blocker if misplaced)
      ↓
Fix or Abort?
      ↓
Git Actions (commit/push/skip)
      ↓
Navigation (continue/backtrack/quit)
      ↓
Sync Dashboard
      ↓
Next Task or Exit
```

**Every single task ends with this flow - no exceptions.**

This ensures:
- ✅ Clean file organization always
- ✅ Git history tracks progress
- ✅ Easy backtracking anytime
- ✅ Dashboard always accurate

---

## 🐛 Dashboard Bug Fixes

### Already Fixed in Test Session:

1. **SSE Stream Inactive Status**
   - Send explicit inactive when no task running
   - Fixed: server.js lines 255-304

2. **Dashboard Not Clearing Old Status**
   - Clear llmGrid innerHTML when inactive
   - Fixed: index.html lines 1241-1301

3. **Staleness Detection**
   - Check >60s since last update
   - Fixed: server.js age calculation

4. **Provider Display Incorrect**
   - Read from status file correctly
   - Fixed: index.html renderLLMInfo

5. **Phase Status Wrong**
   - Check completed flag properly
   - Fixed: Dashboard phase calculation

**Action:** Copy these fixes to ACP dashboard (already done in test)

---

## 🎁 What We Get

### Immediate Benefits:
✅ **Crystal clear organization** - Every file has its place
✅ **Easy to extend** - Drop new task script in, done
✅ **Bulletproof state** - Organization agent prevents chaos
✅ **Git tracking** - Commit prompts keep history clean
✅ **Easy backtracking** - Reset to any point cleanly
✅ **Accurate dashboard** - Always shows truth

### Long-term Benefits:
✅ **Maintainable** - Strict structure prevents mess
✅ **Debuggable** - Run any task independently
✅ **Testable** - Each task is a unit
✅ **Extensible** - Add phases/tasks easily
✅ **Professional** - Clean codebase anyone can understand

---

## 🚀 Execution Strategy

### Week 1: Core Extraction
- Days 1-3: Setup, Main, Extract Phase 0-2 tasks
- Days 4-5: Extract remaining tasks

### Week 2: Orchestration & Polish
- Days 6-7: Build orchestration systems
- Day 8: Fix dashboard bugs
- Days 9-10: Test and document

### Week 3: Buffer & Refinement
- Polish rough edges
- Additional testing
- User feedback integration

---

## 📝 Key Principles to Maintain

1. **NOTHING goes in wrong place** - Organization agent enforces
2. **ACP lives IN the project** - Not separate
3. **Tasks are standalone** - Run independently
4. **Every task ends same way** - Orchestration flow
5. **Dashboard shows truth** - Sync after every task
6. **Backtrack anytime** - Clean reset capability
7. **reports/ for scratch** - Nothing else

---

## 🔍 Success Criteria

- [ ] All 60+ tasks as standalone Python scripts
- [ ] main.py orchestrates everything
- [ ] Organization agent blocks misplaced files
- [ ] Git prompts after every task
- [ ] Backtrack works to any phase/task
- [ ] Dashboard bug-free and accurate
- [ ] Fast-path test completes cleanly
- [ ] Documentation complete
- [ ] Zero files in wrong locations

---

## 💡 Next Steps

1. **Review this plan** - Any adjustments?
2. **Make key decisions:**
   - Async or sync for LLM calls?
   - YAML or TOML for config?
   - Additional dependencies (rich, pydantic)?
3. **Start Phase 1** - Create clean structure
4. **Execute methodically** - One phase at a time

---

**This is extraction, not rewriting. The hard work is done - we just need to organize it properly.**

**Ready to begin?**
