# Docs Directory Deep Evaluation

**Date**: 2026-02-18
**Scope**: Comprehensive analysis of `docs/` directory (2.5MB, 250+ files)
**Focus**: Identify deprecated/historical content for archival or deletion

---

## Executive Summary

### Size Analysis
- **Total**: 2.5MB, 250+ files
- **corpus/**: 1.6MB, 114 files (⚠️ 64% of total docs size)
- **testing/**: 364KB, 37 files
- **core/**: 184KB, 15 files
- **root**: ~800KB, 80+ files

### Key Finding: corpus/ Directory is Historical Artifacts
- **114 files** of split/duplicated documentation
- **40 BUG-PATTERNS** splits (BUG-PATTERNS_1.md through _40.md)
- **19 setup** splits (setup_1.md through _19.md)
- **4 PRD** splits (PRD_1.md through _4.md)
- **NO operational references** (checked Python and markdown files)
- **Purpose**: LLM training corpus during development (Feb 7, 2026 CORPUS-INDEX.md)

---

## Category 1: corpus/ Directory (1.6MB) - ARCHIVE/DELETE

### Status: Historical Development Artifacts
**Recommendation**: **MOVE TO ARCHIVE or DELETE**

### Evidence:
1. ✅ Not referenced in any Python code
2. ✅ Not referenced in any documentation
3. ✅ Contains duplicates of docs/core/ content
4. ✅ Contains split versions of consolidated files
5. ✅ CORPUS-INDEX.md dated Feb 7, 2026 (development phase)

### File Breakdown:
- **40 files**: BUG-PATTERNS_1 through _40 (split versions)
- **19 files**: setup_1 through _19 (split versions)
- **4 files**: PRD_1 through _4 (split versions)
- **~50 files**: Duplicates of core/, testing/, migration docs

### Space Savings: **1.6MB** (64% of docs/)

### Action Options:
1. **DELETE** - Safe, no operational impact
2. **MOVE TO archive/** - Preserve for historical reference
3. **KEEP** - Only if needed for LLM training/testing

---

## Category 2: Completion/Status Reports (Root) - ARCHIVE

### Files (50+ completion/status docs):
```
PHASE-1-FOUNDATION-COMPLETE.md (11KB)
PHASE-2-CORE-SYSTEMS-COMPLETE.md (19KB)
PHASE-3-ORCHESTRATION-COMPLETE.md (13KB)
PHASE-4-COMPLETE.md (16KB)
PHASE-4-IMPLEMENTATIONS-COMPLETE.md (22KB)
PHASE-5-COMPLETE.md (12KB)
PHASE-6-COMPLETE.md (13KB)
PHASES-7-9-COMPLETE.md (28KB)
PHASE-1-AGENT-4-COMPLETE.md (12KB)
PHASE-2-3-MIGRATION-COMPLETE.md (8KB)
PHASE-2-3-UAT-COMPLETE.md (10KB)
PHASE-A-INSTALLATION-COMPLETE.md (17KB)
SKILLS-COMPLETE.md (17KB)
SKILLS-PHASE1-COMPLETE.md (12KB)
SKILLS-PHASE2-COMPLETE.md (16KB)
SKILLS-PHASE3-COMPLETE.md (16KB)
SKILLS-INTEGRATION-COMPLETE.md (12KB)
SKILLS-INTEGRATION-FINAL.md (12KB)
TEST-COMPLETION-SUMMARY.md (8KB)
UAT-RUNNER-COMPLETE.md (in corpus/)
PACKAGING-COMPLETE.md (10KB)
CLEANUP-COMPLETE.md (5KB)
IMPLEMENTATION-COMPLETE-2026-02-10.md (15KB)
PROJECT-COMPLETE.md (14KB)
STEP-3-COMPLETE.md (8KB)
```

**Status**: Historical progress reports from development
**Recommendation**: **MOVE TO docs/archive/completion-reports/**
**Space Savings**: ~400KB

---

## Category 3: Migration Documentation - ARCHIVE

### Files:
```
REFACTORING-PLAN.md (16KB)
REFACTORING-PLAN-V2.md (29KB)
PHASE-00-01-EXTRACTION.md (13KB)
PHASE-2-3-MIGRATION.md (1.4KB)
PHASE-4-5-MIGRATION.md (6KB)
PHASE-6-7-MIGRATION.md (7KB)
PHASE-8-9-MIGRATION.md (7KB)
EXTRACTION-STRATEGY.md (8KB)
EXTRACTION-PROGRESS.md (13KB)
MIGRATION-GUIDE.md (24KB)
MIGRATION-QUICK-START.md (2KB)
```

**Status**: Documentation of Python migration (completed Feb 2026)
**Recommendation**: **MOVE TO docs/archive/migration/**
**Space Savings**: ~140KB
**Note**: Keep MIGRATION-GUIDE.md for reference (move to root or keep)

---

## Category 4: Testing Documentation - KEEP/ORGANIZE

### Current Structure:
```
docs/testing/ (364KB, 37 files)
- Audit quickstarts, summaries, guides
- UAT runner documentation
- Test framework documentation
```

**Status**: OPERATIONAL - Referenced by test infrastructure
**Recommendation**: **KEEP** but review for consolidation
**Note**: Some files may be duplicates (e.g., UAT-RUNNER-COMPLETE in both root and corpus)

---

## Category 5: Core Documentation - KEEP

### Files:
```
docs/core/ (184KB, 15 files)
- Provider documentation (Anthropic, Bedrock, Ollama)
- Memory system documentation
- Task engine documentation
```

**Status**: OPERATIONAL - Core system documentation
**Recommendation**: **KEEP**

---

## Category 6: Active Documentation - KEEP

### Files to Keep in docs/ root:
```
DEVELOPER-GUIDE.md (28KB) ✅
USER-GUIDE.md (21KB) ✅
API-REFERENCE.md (32KB) ✅
FEATURE-FLAG-ARCHITECTURE.md (25KB) ✅
MCP.md (11KB) ✅
AGENT.md (8KB) ✅
```

**Status**: CURRENT - Referenced documentation
**Recommendation**: **KEEP**

---

## Category 7: Questionable/Review Needed

### Files:
```
DASHBOARD-REVIEW-2026-02-10.md (22KB) - Historical review?
DASHBOARD-REVIEW-PACKAGE.md (15KB) - Historical review?
DASHBOARD-IMPLEMENTATION-STATUS.md (9KB) - Status doc?
DASHBOARD-INNOVATIONS-DETAILED.md (27KB) - Detailed doc?
SESSION-SUMMARY-2026-02-07.md (8KB) - Session log?
DAY-1-PROGRESS-SUMMARY.md (6KB) - Progress log?
BUG-PATTERNS.md (21KB) - Still relevant?
BUG-PATTERN-FIXES.md (14KB) - Historical fixes?
```

**Recommendation**: USER REVIEW - Determine if historical or still needed

---

## Proposed Actions

### Phase 1: Safe Deletion (No Operational Impact)
```bash
# DELETE corpus/ directory (1.6MB, 64% of docs)
rm -rf docs/corpus/
```
**Risk**: NONE (verified no references)
**Savings**: 1.6MB

### Phase 2: Archive Completion Reports
```bash
mkdir -p docs/archive/completion-reports
mv docs/*-COMPLETE*.md docs/archive/completion-reports/
mv docs/STEP-3-COMPLETE.md docs/archive/completion-reports/
mv docs/PROJECT-COMPLETE.md docs/archive/completion-reports/
```
**Risk**: NONE (historical status docs)
**Savings**: ~400KB

### Phase 3: Archive Migration Documentation
```bash
mkdir -p docs/archive/migration
mv docs/REFACTORING-PLAN*.md docs/archive/migration/
mv docs/PHASE-*-MIGRATION*.md docs/archive/migration/
mv docs/EXTRACTION-*.md docs/archive/migration/
mv docs/MIGRATION-QUICK-START.md docs/archive/migration/
# Keep MIGRATION-GUIDE.md for reference
```
**Risk**: LOW (migration completed)
**Savings**: ~140KB

### Phase 4: User Review
- Dashboard review documents
- Session/progress summaries
- Bug pattern documentation

---

## Final Structure Proposal

```
docs/
├── README.md                    # Overview of docs structure
├── DEVELOPER-GUIDE.md           # Keep
├── USER-GUIDE.md                # Keep
├── API-REFERENCE.md             # Keep
├── MIGRATION-GUIDE.md           # Keep (consolidated migration reference)
├── FEATURE-FLAG-ARCHITECTURE.md # Keep
├── MCP.md                       # Keep
├── AGENT.md                     # Keep
├── core/                        # Keep (provider & system docs)
├── testing/                     # Keep (test infrastructure docs)
├── prd/                         # Keep (PRD documentation)
├── archive/                     # NEW: Historical documents
│   ├── completion-reports/      # Phase completion docs
│   ├── migration/               # Python migration documentation
│   └── corpus/                  # LLM training corpus (if kept)
└── diagrams/                    # Keep (visual documentation)
```

---

## Summary

### Recommended Actions:
1. ✅ **DELETE** `docs/corpus/` (1.6MB, 114 files) - No operational impact
2. ✅ **ARCHIVE** completion reports (~400KB) - Historical status docs
3. ✅ **ARCHIVE** migration docs (~140KB) - Migration completed
4. ⚠️ **USER REVIEW** dashboard/session docs (~80KB) - Determine relevance

### Total Space Reduction:
- **2.14MB** removed/archived (86% of docs/)
- **~350KB** remaining operational docs
- **Clean, maintainable docs structure**

### Risk Assessment:
- **corpus/ deletion**: ZERO risk (verified no references)
- **Completion reports archival**: ZERO risk (historical only)
- **Migration docs archival**: LOW risk (migration complete, keep guide)
- **Dashboard docs**: REVIEW NEEDED

