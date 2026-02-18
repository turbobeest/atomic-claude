# Cleanup Inventory - Non-Operational Files

**Date**: 2026-02-18
**Purpose**: Identify deprecated/unused files for potential removal

## ⚠️ CRITICAL: Review Before Deletion

This inventory categorizes files by risk level:
- **HIGH RISK**: May break operational code if removed
- **MEDIUM RISK**: Likely safe but needs verification
- **LOW RISK**: Safe to remove (backups, duplicates, obvious deprecated)

---

## 1. Legacy Phase Directories (❌ NOT DEPRECATED - KEEP!)

### Phase Orchestrators (phase00-09) - OPERATIONAL
**Location**: `phases/phase00/` through `phases/phase09/`
**Status**: **ACTIVELY USED** - Contains orchestrators imported by pipeline.py

**CRITICAL FINDING** (verified 2026-02-18):
```python
# orchestration/pipeline.py PHASE_REGISTRY explicitly imports:
module_path="phases.phase00.orchestrator00"  # Line 137
module_path="phases.phase01.orchestrator01"  # Line 146
# ... through orchestrator09
```

**Verified References**:
- `orchestration/pipeline.py` - All 10 orchestrators registered in PHASE_REGISTRY
- `tests/integration/test_phase_orchestrators.py` - Integration tests import these

**Architecture Clarification**:
- `phases/phase00/orchestrator00.py` - Phase orchestrator (ACTIVE)
- `phases/phase_00_setup/tasks/*.py` - Python task modules called by orchestrator

**Both directory structures are required**:
- `phase00-09/` - Contains orchestrators (phase control logic)
- `phase_NN_name/` - Contains task implementations (actual work)

**Recommendation**: **KEEP** - Required for pipeline operation

**Documentation Issue**: CLAUDE.md line misleading - "Legacy directories...superseded" is incorrect. Both are needed and serve different purposes.

---

## 2. Dashboard HTML Backups (LOW RISK - SAFE TO DELETE)

### Multiple Dashboard Versions
**Location**: `dashboard/public/`
**Files**:
- `index-before-fix.html`
- `index-enhanced.html`
- `index-no-files.html`
- `index-original.html`
- `index-with-files.html`
- `index.html.bak`

**Current Version**: `index.html` (142KB)

**Analysis**:
- Clear backups/iterations of dashboard development
- Not referenced by server.js (serves `index.html` only)
- Safe to remove

**Recommendation**: DELETE

---

## 3. Test Infrastructure (HIGH RISK - KEEP)

### Pytest Suite (tests/)
**Location**: `tests/` (1.1MB)
**Status**: OPERATIONAL - configured in pytest.ini
**Contents**:
- unit/ - 35+ unit test files
- integration/ - Phase orchestrator tests
- e2e/ - End-to-end pipeline tests
- performance/ - Performance benchmarks
- conftest.py - Pytest fixtures

**Recommendation**: KEEP

### Legacy Shell Tests (test/)
**Location**: `test/` (56KB)
**Status**: DOCUMENTED - Referenced in test/README.md and test/fixtures/README.md
**Contents**:
- `continuity-test-scenario1.sh`
- `run-comprehensive-tests.sh`
- `run-uxui-evaluation.sh`
- `validate_phase_a_skills.sh`
- fixtures/phase00/ test data

**Verification Results** (2026-02-18):
- Referenced in `test/README.md` with usage instructions
- Referenced in `test/fixtures/README.md` for test data setup
- No CI configuration found (.yml files)
- Sets `ATOMIC_TOOL_DEVELOPMENT` env var for tool development mode

**Analysis**:
- Documented and intentional (not orphaned)
- Complements pytest suite with shell-level integration tests
- Provides test fixtures for pytest suite
- May be useful for end-to-end validation

**Recommendation**: **KEEP** - Documented test infrastructure, not deprecated

---

## 4. Documentation Files (MIXED RISK)

### Project Root Docs
**Files**:
- `README.md` - KEEP (main project readme)
- `CLAUDE.md` - KEEP (technical architecture)
- `OPERATIONAL.md` - KEEP (new dual-repo workflow)
- `claude-skills-categorized.md` - UNCLEAR (867 lines)

**Recommendation**: Review `claude-skills-categorized.md` for relevance

### Subdirectory Docs
**Locations**:
- `agents/README.md`, `agents/CLAUDE.md` - KEEP
- `audits/docs/archive/legacy-json-structure/` - DELETE (archived)
- `docs/` directory - REVIEW (may contain outdated docs)

---

## 5. Reports Directory (LOW RISK)

**Location**: `reports/`
**Status**: Empty except for README and .gitignore
**CLAUDE.md Note**: "`reports/` is scratch work only"

**Recommendation**: KEEP (used as working directory)

---

## 6. Examples Directory (LOW RISK)

**Location**: `examples/`
**Contents**: `llm_router_demo.py` only

**Analysis**:
- Single demo file for LLM router
- Useful for reference/documentation

**Recommendation**: KEEP

---

## 7. Node Modules Artifacts (LOW RISK)

**Status**: Multiple node_modules in sub-apps generate artifacts
**Locations**:
- `agents/agent-manager/node_modules/`
- `audits/audit-browser/node_modules/`
- `skills/skills-browser/node_modules/`

**Git Status**: Shows many .vite cache changes
**Analysis**: These are build artifacts, ignored by .gitignore

**Recommendation**: No action needed (git-ignored)

---

## Summary by Risk Level

### ✅ SAFE TO DELETE (Low Risk - ~200KB)
1. **Dashboard HTML backups** (6 files) - `dashboard/public/index-*.html`, `index.html.bak`
2. **Audits legacy archive** - `audits/docs/archive/legacy-json-structure/`

### ⚠️ NEEDS REVIEW (Medium Risk)
1. **claude-skills-categorized.md** (867 lines) - Verify if still relevant or superseded by skills browser
2. **docs/** directory - Check for outdated documentation

### ❌ DO NOT DELETE (Required for Operation)
1. **phase00-09 directories** - Active orchestrators (verified in use by pipeline.py)
2. **test/ directory** - Documented shell test infrastructure
3. **tests/ directory** - Operational pytest suite
4. **All README.md files** - Documentation
5. **CLAUDE.md, OPERATIONAL.md** - Architecture docs
6. **reports/ directory** - Working scratch space
7. **examples/ directory** - Reference implementations

---

## Recommended Actions

### Immediate (Safe to Execute Now)
1. **Delete dashboard HTML backups**:
   ```bash
   cd dashboard/public
   rm index-before-fix.html index-enhanced.html index-no-files.html \
      index-original.html index-with-files.html index.html.bak
   ```

2. **Delete audits legacy archive**:
   ```bash
   rm -rf audits/docs/archive/legacy-json-structure
   ```

### Requires Review (User Decision)
1. **claude-skills-categorized.md**: Check if superseded by skills browser
2. **docs/ directory**: Review for outdated content

### Documentation Fixes
1. **Update CLAUDE.md**: Clarify that phase00-09 directories are NOT deprecated
   - Current text: "Legacy `phases/phase00-09/` directories exist but are superseded"
   - Should say: "Both `phase00/` (orchestrators) and `phase_NN_name/` (tasks) are required"

### No Action Needed
- All other identified files are operational or documented

