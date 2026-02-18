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
