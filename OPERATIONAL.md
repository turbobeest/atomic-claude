# Operational Guide: Atomic Claude Development & Testing

## Dual-Repository Setup

### Development Instance (This Repo)
- **Location**: `/Users/jamesterbeest/dev/atomic-claude`
- **Branch**: `python`
- **Purpose**: Primary development, debugging, and feature implementation
- **Upstream**: https://github.com/turbobeest/atomic-claude

### Operational Instance
- **Location**: `/Users/jamesterbeest/dev/CUI-ENGAGEMENT-MANAGER/atomic-claude`
- **Purpose**: Live operational testing against real projects
- **Sync**: Bug fixes and features should be applied to BOTH repos
- **Status**: ✅ Configured (2026-02-18)
- **Setup**: Cloned from python branch, embedded in host project
- **Dashboard**: Correctly detects host project context (verified)

## 🚨 Safety Rules

### Destructive Operations Require Human Approval

**CRITICAL RULE** (Established 2026-02-18):

**The `rm` command must NEVER be used without explicit human approval.**

This includes:
- ❌ `rm -rf` (recursive force delete)
- ❌ `rm -r` (recursive delete)
- ❌ `rm file.txt` (single file delete)
- ❌ Any variant of rm with wildcards

**Required Process**:
1. AI identifies files/directories for deletion
2. AI presents detailed analysis and recommendations
3. **Human explicitly approves** the specific rm command
4. Only then execute deletion

**Why**: Prevents accidental deletion of critical files, especially when working across dual repositories or analyzing deprecated content.

**Alternative Safe Commands** (AI can use without approval):
- ✅ `mv file.txt archive/` (move to archive)
- ✅ `git status` (check changes)
- ✅ `ls`, `find`, `grep` (read-only operations)
- ✅ File reads, analysis, recommendations

**Example Safe Workflow**:
```bash
# AI: "I recommend deleting these files: [list]"
# Human: "Approved, execute rm command"
# AI: [executes rm]
```

## Operational Instance Setup

### Initial Setup (Completed 2026-02-18)

**Location**: `/Users/jamesterbeest/dev/CUI-ENGAGEMENT-MANAGER/`

**Steps Performed**:
```bash
# 1. Initialize host project as git repo
cd /Users/jamesterbeest/dev/CUI-ENGAGEMENT-MANAGER
git init

# 2. Clone atomic-claude
git clone -b python https://github.com/turbobeest/atomic-claude.git

# 3. Create project structure
mkdir -p {.state,.outputs,.logs,src,docs,config,initialization}

# 4. Configure .gitignore (runtime directories)
echo ".state/
.outputs/
.logs/" > .gitignore

# 5. Create initialization/setup.md (project overview)

# 6. Commit setup
git add -A && git commit -m "Initial project setup with atomic-claude"
```

### Path Detection Verification
✅ **Dashboard correctly detects host project**:
- ATOMIC_ROOT: `/Users/jamesterbeest/dev/CUI-ENGAGEMENT-MANAGER/atomic-claude`
- PROJECT_ROOT: `/Users/jamesterbeest/dev/CUI-ENGAGEMENT-MANAGER`
- PID files: `/Users/jamesterbeest/dev/CUI-ENGAGEMENT-MANAGER/.state/dashboard/`

**Test commands**:
```bash
# Start dashboard from host project root
cd /Users/jamesterbeest/dev/CUI-ENGAGEMENT-MANAGER
bash atomic-claude/dashboard/start-dashboard.sh

# Verify path detection
curl http://127.0.0.1:5174/api/root
# Returns: {"root":"/Users/.../CUI-ENGAGEMENT-MANAGER/atomic-claude"}

# Check PID file location
ls .state/dashboard/
# Contains: main.pid, agents.pid, audits.pid, skills.pid
```

### Running Pipeline in Operational Instance
```bash
# From CUI-ENGAGEMENT-MANAGER root
cd /Users/jamesterbeest/dev/CUI-ENGAGEMENT-MANAGER

# Run phase
python atomic-claude/main.py run <phase>

# Check status
python atomic-claude/main.py status

# Backtrack if needed
python atomic-claude/main.py backtrack <phase> <task>
```

**All artifacts go to host project**:
- `.state/` - Pipeline state for CUI-ENGAGEMENT-MANAGER
- `.outputs/` - Working artifacts for CUI-ENGAGEMENT-MANAGER
- `.logs/` - Execution logs for CUI-ENGAGEMENT-MANAGER

## Workflow Best Practices

### 1. Making Changes

When fixing bugs or adding features:

1. **Develop in this repo first** (atomic-claude)
   - Make changes
   - Test locally
   - Commit to git

2. **Replicate to operational instance**
   - Apply same changes to `/Users/jamesterbeest/dev/CUI-ENGAGEMENT-MANAGER/atomic-claude`
   - Test in operational context
   - Verify against real project requirements

3. **Document learnings** (update this file)

### 2. Testing Strategy

- **Unit/Integration**: Run in dev repo (`pytest`)
- **E2E/UAT**: Run in operational repo against real workload
- **Compare outputs**: Ensure consistency across both instances

### 3. Git Workflow

```bash
# In dev repo
git add <files>
git commit -m "Fix: description"

# In operational repo (if needed)
cd /Users/jamesterbeest/dev/CUI-ENGAGEMENT-MANAGER/atomic-claude
# Apply same changes or copy files
```

### 4. Common Operations

#### Check Status Across Both Repos
```bash
# Dev repo
cd /Users/jamesterbeest/dev/atomic-claude
python main.py status

# Operational repo
cd /Users/jamesterbeest/dev/CUI-ENGAGEMENT-MANAGER/atomic-claude
python main.py status
```

#### Dashboard Usage

**IMPORTANT**: The dashboard should ONLY run from the operational repo, not from the dev repo!

**In DEV repo** (`/Users/jamesterbeest/dev/atomic-claude`):
- Dashboard should be **OFF** during normal operations
- Only start it temporarily when testing/debugging dashboard features
- This repo is for developing atomic-claude itself, not running it

**In OPERATIONAL repo** (`/Users/jamesterbeest/dev/CUI-ENGAGEMENT-MANAGER`):
- Dashboard should be **ON** and monitors the host project
- Start from host project root, NOT from inside atomic-claude/

```bash
# From CUI-ENGAGEMENT-MANAGER root:
cd /Users/jamesterbeest/dev/CUI-ENGAGEMENT-MANAGER
bash atomic-claude/dashboard/start-dashboard.sh

# Dashboard monitors CUI-ENGAGEMENT-MANAGER/.state/, .outputs/, .logs/
# NOT atomic-claude's internal state

# View dashboard
open http://127.0.0.1:5174

# Sub-apps:
# - Agent Manager: http://127.0.0.1:5175
# - Audit Browser: http://127.0.0.1:5176
# - Skills Browser: http://127.0.0.1:5177
```

#### Sync Critical Files
When core systems change (config, state, LLM routing, orchestration):
- Always sync to operational instance
- Test end-to-end before considering complete

## Known Issues & Resolutions

### Dashboard Sub-Apps Fail to Start on macOS
- **Date**: 2026-02-18
- **Symptom**: Agent Manager, Audit Browser, and Skills Browser fail to start with "command not found" error for `setsid`
- **Root Cause**: `setsid` is a Linux-specific command not available on macOS. The `start-dashboard.sh` script assumed Linux environment.
- **Fix**: Modified `start-dashboard.sh` line 104-108 to detect platform and use `setsid` on Linux, plain `nohup` on macOS
- **Additional Fix**: Skills Browser had corrupted node_modules, fixed by `rm -rf node_modules package-lock.json && npm install`
- **Files Modified**: `dashboard/start-dashboard.sh`
- **Testing**:
  ```bash
  bash dashboard/start-dashboard.sh
  # Verify all ports listening:
  lsof -i :5174,5175,5176,5177
  ```
- **Applied To**: [x] Dev [ ] Operational

### Dashboard Reading Wrong .state/ Directory
- **Date**: 2026-02-18
- **Symptom**: Dashboard reads from `atomic-claude/.state/` instead of host project's `.state/` when deployed in a nested directory
- **Root Cause**: Path detection logic was inconsistent - `.outputs/` checked parent directory but `.state/` did not
- **Impact**: Critical - dashboard would not monitor the correct project state when atomic-claude is deployed as a tool
- **Fix**:
  - Modified `server.js` to detect PROJECT_ROOT based on `.state/` OR `.outputs/` in parent
  - Modified `start-dashboard.sh` and `stop-dashboard.sh` to use same PROJECT_ROOT detection
  - All three files now consistently use PROJECT_ROOT for both `.state/` and `.outputs/`
- **Files Modified**:
  - `dashboard/server.js` (lines 12-30)
  - `dashboard/start-dashboard.sh` (lines 15-31)
  - `dashboard/stop-dashboard.sh` (lines 11-23)
- **Testing**:
  ```bash
  # In operational repo:
  cd /path/to/CUI-ENGAGEMENT-MANAGER
  bash atomic-claude/dashboard/start-dashboard.sh
  # Verify reads from CUI-ENGAGEMENT-MANAGER/.state/, not atomic-claude/.state/
  curl http://127.0.0.1:5174/api/root
  ```
- **Applied To**: [x] Dev [ ] Operational

### Documentation Cleanup - Historical Artifacts Removed
- **Date**: 2026-02-18
- **Symptom**: docs/ directory bloated with 2.5MB of historical development artifacts
- **Root Cause**: LLM training corpus and development progress docs accumulated during Python migration (Feb 2026)
- **Fix**:
  - Deleted `docs/corpus/` (1.6MB, 114 files) - LLM training corpus with split/duplicate files
  - Archived completion reports to `docs/archive/completion-reports/` (23 files, ~400KB)
  - Archived migration docs to `docs/archive/migration/` (9 files, ~140KB)
- **Files Removed**:
  - 114 corpus files (40 BUG-PATTERNS splits, 19 setup splits, 4 PRD splits, ~50 duplicates)
  - 23 completion status reports (*-COMPLETE.md)
  - 9 migration planning documents
- **Result**: docs/ reduced from 2.5MB to 2.1MB, streamlined to operational documentation
- **Testing**: Verified zero operational references to removed files
- **Applied To**: [x] Dev [ ] Operational
- **Safety**: Established rm command approval requirement (see Safety Rules section)

### Forcing Function False Positive - OPERATIONAL.md Blocked
- **Date**: 2026-02-18
- **Symptom**: Phase 0 blocked at startup with "OPERATIONAL.md → Should be in: ../docs/"
- **Root Cause**: `orchestration/pre_task_validation.py` whitelist missing OPERATIONAL.md
- **Impact**: Pipeline cannot start - forcing function blocks execution
- **Fix**: Added OPERATIONAL.md and .env to `allowed_root_files` whitelist (line 219-224)
- **Files Modified**: `orchestration/pre_task_validation.py`
- **Testing**:
  ```bash
  # Verify fix
  python orchestration/pre_task_validation.py
  # Should output: ✅ Directory pristine
  ```
- **Applied To**: [x] Dev [x] Operational (pulled d5d196c)
- **Note**: OPERATIONAL.md is tool documentation (dual-repo workflow), not project docs

### Dependabot Security Vulnerabilities - All Fixed
- **Date**: 2026-02-18
- **Symptom**: Enterprise GitHub reported 23 vulnerabilities (16 moderate, 7 low)
- **Root Cause**: Outdated Svelte/SvelteKit dependencies with known XSS and DoS vulnerabilities
- **Affected Apps**: All three Svelte sub-apps (agent-manager, audit-browser, skills-browser)
- **Impact**: LOW risk (apps run on 127.0.0.1 only, not exposed to internet)
- **Fix**:
  1. Ran `npm update` on each sub-app → fixed moderate vulnerabilities
  2. Added `"overrides": {"cookie": "^1.1.1"}` to package.json → fixed low vulnerabilities
- **Vulnerabilities Resolved**:
  - @sveltejs/kit: CPU/memory exhaustion (MODERATE) ✅
  - svelte: Multiple SSR XSS issues (MODERATE) ✅
  - cookie: Out of bounds characters (LOW) ✅
  - devalue: CPU amplification & prototype pollution (LOW) ✅
- **Python**: Scanned with pip-audit → 0 vulnerabilities ✅
- **Files Modified**:
  - `agents/agent-manager/package.json` + package-lock.json
  - `audits/audit-browser/package.json` + package-lock.json
  - `skills/skills-browser/package.json` + package-lock.json
- **Testing**:
  ```bash
  cd agents/agent-manager && npm audit  # 0 vulnerabilities
  cd audits/audit-browser && npm audit  # 0 vulnerabilities
  cd skills/skills-browser && npm audit  # 0 vulnerabilities
  pip-audit -r requirements*.txt         # No known vulnerabilities
  ```
- **Applied To**: [x] Dev [x] Operational (commit 76b5ca0)
- **Note**: Enterprise Dependabot may take time to rescan and clear alerts

### Issue Template
```
## [Issue Title]
- **Date**: YYYY-MM-DD
- **Symptom**: Description of the problem
- **Root Cause**: What was wrong
- **Fix**: What was changed
- **Files Modified**: List of files
- **Testing**: How to verify fix
- **Applied To**: [ ] Dev [ ] Operational
```

## Operational Observations

### What Works Well
- (To be documented as we learn)

### What Needs Improvement
- (To be documented as we encounter issues)

### Performance Notes
- (To be documented during operational testing)

## Emergency Procedures

### If Operational Instance Breaks
1. Check `.state/` and `.logs/` in operational repo
2. Compare with dev repo state
3. Use `python main.py backtrack` if needed
4. Copy working files from dev repo if necessary

### If Dev and Operational Diverge
1. Document differences
2. Determine which version is correct
3. Sync files
4. Run full test suite on both

## Notes

- This file tracks **operational workflow** and learnings
- See `CLAUDE.md` for technical architecture and conventions
- Update this file as patterns emerge and best practices solidify

---

**Last Updated**: 2026-02-18
**Current Focus**: Initial setup and dual-repo coordination
