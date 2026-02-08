# Forcing Function: Directory Purity Enforcement

**Philosophy:** atomic-claude is a TOOL, not a project. ALL project artifacts must live in the parent directory.

---

## The Problem

Without enforcement, LLMs and scripts can accidentally (or intentionally) create project files inside the tool directory:
- Generated code ends up in `atomic-claude/src/`
- Test files get created in `atomic-claude/tests/`
- Project docs land in `atomic-claude/docs/`
- Data files, configs, and other artifacts leak into the tool

This creates **chaos**:
- Tool and project code mixed together
- Unclear what to commit to atomic-claude repo
- Difficult to archive/rename directories
- Impossible to reuse tool in other projects

## The Solution: Multi-Layer Forcing Function

### Layer 1: .gitignore (Prevention)

**File:** `.gitignore`

Prevents Git from tracking project artifacts in atomic-claude directory:
```gitignore
# Block generated code (unless it's tool code)
*.js
*.ts
!core/**/*.py
!phases/**/*.py
!dashboard/server.js

# Block project docs (unless it's tool docs)
*.md
!README.md
!PROJECT-STRUCTURE.md
```

**Effect:**
- Project files won't be accidentally committed to atomic-claude repo
- Visual indicator (untracked files) that something is wrong
- Safe default - if unsure, file is ignored

### Layer 2: Pre-Task Validation (Hard Blocker)

**File:** `orchestration/pre_task_validation.py`

**Runs BEFORE each task execution:**
```python
# In orchestrator00.py, orchestrator01.py, etc.
if not validate_directory_pristine(phase_id, task_id):
    print("🛑 Cannot proceed - fix violations first")
    return False
```

**What it does:**
1. Scans atomic-claude directory for project artifacts
2. Classifies each violation (what it is, where it should go)
3. **BLOCKS task execution** if violations found
4. Prints detailed instructions for fixing

**Effect:**
- **NO TASK CAN RUN** if project files are in wrong place
- Forces immediate cleanup before proceeding
- Prevents violations from accumulating

**Example output:**
```
================================================================================
  🚨 PRE-TASK VALIDATION FAILED 🚨
================================================================================

Found 3 project artifact(s) in atomic-claude directory!

⚠️  atomic-claude is a TOOL, not a project.
   ALL project code must live in the parent directory.

❌ src/components/Button.tsx
   → Should be in: ../src/
   → Reason: Generated project code

❌ tests/button.test.ts
   → Should be in: ../tests/
   → Reason: Project test file

❌ README.project.md
   → Should be in: ../docs/ or reports/ (if scratch work)
   → Reason: Project documentation

================================================================================
  TASK BLOCKED - FIX VIOLATIONS FIRST
================================================================================

Options:
  1. Move files to correct locations manually
  2. Run: python main.py cleanup (auto-fix)
  3. Delete files if they're mistakes
```

### Layer 3: Auto-Cleanup (Easy Fix)

**Command:** `python main.py cleanup`

Automatically moves violations to correct locations:
- Generated code → `../src/`
- Tests → `../tests/`
- Docs → `../docs/` or `reports/` (scratch)
- Unknown files → `reports/` (safe default)

**Effect:**
- One command fixes all violations
- Files moved to correct locations automatically
- Pipeline can resume immediately

### Layer 4: Validation Command (Manual Check)

**Command:** `python main.py validate`

Check for violations without auto-fixing:
```bash
$ python main.py validate

🔍 Checking directory organization...

❌ Found 2 violation(s):
   - src/Button.tsx → ../src/
   - tests/button.test.ts → ../tests/

Run 'python main.py cleanup' to auto-fix
```

**Effect:**
- See what's wrong without making changes
- Useful before committing to atomic-claude repo
- Can be run in CI/CD to enforce purity

---

## What's Allowed vs Forbidden

### ✅ ALLOWED in atomic-claude/

| Type | Location | Purpose |
|------|----------|---------|
| Tool code | `core/*.py`, `phases/**/*.py`, `orchestration/*.py` | Pipeline implementation |
| Task scripts | `phases/phase*/task*.sh` | Task implementations |
| Tool docs | `README.md`, `PROJECT-STRUCTURE.md`, `docs/*.md` | Tool documentation |
| Tool config | `config/*.yaml` | Pipeline configuration |
| Dashboard | `dashboard/*.js`, `dashboard/*.html` | Web UI |
| Runtime artifacts | `.outputs/**`, `.state/**`, `.logs/**` | Pipeline state |
| Scratch work | `reports/**` | Temporary analysis |
| Python package | `**/__init__.py`, `main.py` | Package structure |

### ❌ FORBIDDEN in atomic-claude/

| Type | Forbidden | Correct Location |
|------|-----------|------------------|
| Project code | `*.js`, `*.ts`, `*.tsx` (except dashboard) | `../src/` |
| Project tests | `*test.py`, `*spec.js` | `../tests/` |
| Project docs | `*.md` (project-specific) | `../docs/` |
| Data files | `*.csv`, `*.db`, `*.json` (except config) | `../data/` or parent |
| Notebooks | `*.ipynb` | `../notebooks/` or parent |
| Binaries | `*.exe`, `*.dll` | Should never exist |
| Archives | `*.zip`, `*.tar` | Should never exist |

---

## Usage

### During Development

**Before starting task:**
```bash
# Pipeline automatically validates before each task
python main.py run 2 --resume-at=205
# If violations exist, task is BLOCKED
```

**After LLM creates files:**
```bash
# Check what went wrong
python main.py validate

# Auto-fix violations
python main.py cleanup

# Resume pipeline
python main.py run 2 --resume-at=205
```

### Before Committing

**Always validate before committing to atomic-claude repo:**
```bash
# Check for violations
python main.py validate

# If clean, commit
git status
git add .
git commit -m "feat: Add Phase 3 orchestrator"

# If violations, fix first
python main.py cleanup
git status  # Verify only tool files staged
```

### In CI/CD

**Add to GitHub Actions / CI:**
```yaml
- name: Validate directory purity
  run: |
    cd atomic-claude
    python main.py validate
    # Fails CI if violations found
```

---

## How It Works: Technical Details

### Detection Algorithm

1. **Scan all files** in atomic-claude directory
2. **Check each file** against allowed patterns
3. **Classify violations** by type and suggest location
4. **Report or fix** depending on mode

### Classification Logic

```python
# Example: classify a .tsx file
if suffix == ".tsx":
    if "dashboard" in str(rel_path):
        return "ALLOWED"  # Dashboard tool code
    else:
        return "FORBIDDEN: ../src/"  # Project code

# Example: classify a .md file
if suffix == ".md":
    if name in ["README", "PROJECT-STRUCTURE", "REFACTORING-PLAN"]:
        return "ALLOWED"  # Tool documentation
    elif "docs/" in str(rel_path):
        return "ALLOWED"  # Tool documentation directory
    else:
        return "FORBIDDEN: ../docs/ or reports/"  # Project docs
```

### Auto-Fix Strategy

**Safe defaults when location is ambiguous:**
- Unknown files → `reports/` (temporary scratch work)
- Can always be moved later if wrong
- Prevents data loss

**Parent directory precedence:**
- Project code → `../src/`
- Project tests → `../tests/`
- Project docs → `../docs/`

---

## Benefits

### For Solo Developers

✅ **Clean separation** - Tool and project never mixed
✅ **Easy archiving** - Can archive/rename project without touching tool
✅ **Reusable tool** - Can use atomic-claude in multiple projects

### For Teams

✅ **Clear boundaries** - Everyone knows where files go
✅ **Easy reviews** - PRs to atomic-claude only contain tool changes
✅ **Onboarding** - New developers see violations immediately

### For Tool Maintenance

✅ **Clean repo** - atomic-claude repo only has tool code
✅ **Easy upgrades** - Pull tool updates without merge conflicts
✅ **Portable** - Tool can be extracted to separate repo easily

---

## Troubleshooting

### Task blocked, don't know why

```bash
# See detailed violation report
python main.py validate

# Auto-fix all violations
python main.py cleanup
```

### LLM keeps creating files in wrong place

**Update your task prompts:**
```markdown
IMPORTANT: You are working in the PROJECT directory, not atomic-claude.

File locations:
- Generated code: ./src/ (current directory)
- Tests: ./tests/
- Docs: ./docs/

DO NOT write files into atomic-claude/ directory.
```

### Validation incorrectly flagging tool files

**Update allowed patterns** in `orchestration/pre_task_validation.py`:
```python
ALLOWED_PATTERNS = {
    "your_new_tool_dir/**/*.py",  # Add new pattern
}
```

### Need to temporarily bypass validation (NOT RECOMMENDED)

**Only for emergencies:**
```python
# In orchestrator, comment out validation:
# if not validate_directory_pristine(phase_id, task_id):
#     return False
```

**Better approach:** Fix the violation properly!

---

## Future Enhancements

### Continuous Monitoring (Future)

Watch filesystem for violations in real-time:
```bash
python main.py monitor
# Watches atomic-claude/ and alerts on violations
```

### IDE Integration (Future)

VS Code extension that:
- Highlights files in wrong locations
- Offers quick-fix to move to correct location
- Prevents saving files in wrong places

### Git Hooks (Future)

Pre-commit hook that runs validation:
```bash
#!/bin/bash
cd atomic-claude
python main.py validate || exit 1
```

---

## Summary

**The forcing function ensures atomic-claude remains a pure tool:**

1. **Prevention** - .gitignore prevents tracking project files
2. **Detection** - Pre-task validation catches violations
3. **Blocking** - Tasks cannot run with violations present
4. **Auto-fix** - One command fixes everything
5. **Validation** - Manual check anytime

**Result:** atomic-claude directory ONLY contains tool code, ALWAYS.

**When you eventually rename this to atomic-claude (main branch), the forcing function ensures you'll never have this problem again!**
