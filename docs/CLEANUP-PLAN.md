# Directory Cleanup Plan

## Issues Found

### 1. Duplicate Test Directories
- `/test` - Old hybrid prototype test infrastructure (UAT, audits, lots of docs)
- `/tests` - Proper pytest structure for Python rewrite (unit/, integration/, e2e/)

### 2. Root-Level Files That Need Moving
- `demo_uat_report.html` → `reports/`
- `AGENT.md` → `docs/`
- `CLAUDE-CONTEXT.md` → `docs/`
- `STATUS.md` → `docs/`
- `REFACTOR-PLAN.md` (old) → Archive or delete (we have V2)

### 3. Files That Are OK in Root
✅ Standard Python packaging:
- `pyproject.toml`, `setup.py`, `MANIFEST.in`
- `requirements*.txt`

✅ Standard configuration:
- `.gitignore`, `.env`, `.env.example`
- `.pre-commit-config.yaml`

✅ Documentation:
- `CLAUDE.md`, `README.md`
- `REFACTOR-PLAN-V2.md`, `REFACTOR-PROGRESS.json`
- `.PRE-WORK-CHECKLIST.md`

✅ Entry point:
- `main.py`

---

## Cleanup Actions

### Action 1: Consolidate Test Directories

**Decision:** Keep `/tests` (proper pytest structure for Python rewrite), archive `/test`

```bash
# Move useful content from /test to proper locations
mkdir -p tests/uat
mv test/run_uat.sh tests/uat/
mv test/fixtures tests/uat/fixtures_old  # Merge with tests/fixtures later
mv test/preflight_check.sh scripts/

# Move audit runners to scripts (if needed for Python rewrite)
mkdir -p scripts/audit_runners
mv test/*_audit_runner.py scripts/audit_runners/
mv test/run_all_audits.py scripts/audit_runners/

# Move test documentation to docs/testing/
mkdir -p docs/testing
mv test/*.md docs/testing/
mv test/README*.md docs/testing/

# Archive the rest
mkdir -p archive/test_prototype
mv test/* archive/test_prototype/ 2>/dev/null || true
rmdir test
```

### Action 2: Move Root-Level Files

```bash
# Move reports
mv demo_uat_report.html reports/

# Move documentation
mv AGENT.md docs/
mv CLAUDE-CONTEXT.md docs/
mv STATUS.md docs/

# Archive old refactor plan
mkdir -p archive/planning
mv REFACTOR-PLAN.md archive/planning/
```

### Action 3: Verify Clean Structure

After cleanup, root should contain:
```
atomic-claude2/
├── .env, .env.example, .gitignore           # Config
├── .pre-commit-config.yaml                   # Pre-commit
├── .PRE-WORK-CHECKLIST.md                   # Plan adherence
├── CLAUDE.md                                 # Development docs
├── README.md                                 # User docs
├── REFACTOR-PLAN-V2.md                      # Current plan
├── REFACTOR-PROGRESS.json                   # Progress tracking
├── pyproject.toml, setup.py, MANIFEST.in    # Packaging
├── requirements*.txt                         # Dependencies
├── main.py                                   # Entry point
│
├── agents/                                   # Agent definitions
├── audits/                                   # Audit definitions
├── config/                                   # Config files
├── core/                                     # Core Python modules
├── dashboard/                                # Dashboard
├── docs/                                     # All documentation
├── examples/                                 # Example projects
├── lib/                                      # Bash libraries (reference)
├── orchestration/                            # Orchestration Python
├── phases/                                   # Phase implementations
├── reports/                                  # Generated reports
├── scripts/                                  # Utility scripts
├── tests/                                    # Test suite (proper pytest structure)
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   ├── runners/
│   ├── fixtures/
│   └── conftest.py
│
└── archive/                                  # Archived old code
    ├── test_prototype/                       # Old /test directory
    └── planning/                             # Old plans
```

---

## Validation

After cleanup:
```bash
# Check root is clean
ls -1 | grep -E "^[^.]" | wc -l  # Should be ~15 items

# Check no markdown in root except CLAUDE.md, README.md, REFACTOR-PLAN-V2.md
ls -1 *.md | wc -l  # Should be 3

# Check test structure
ls -1 tests/  # Should see: unit/, integration/, e2e/, runners/, conftest.py

# Check reports directory
ls -1 reports/  # Should include demo_uat_report.html

# Check docs directory
ls -1 docs/ | grep -E "(AGENT|STATUS|CLAUDE-CONTEXT)"  # Should see all 3
```

---

## Execute Cleanup?

Run the cleanup actions above, then verify the structure.
