# Skills Strategy - Third Pillar Architecture

**Date:** February 10, 2026
**Decision:** Skills as complementary capability, NOT replacement for agents
**Structure:** Agents + Audits + Skills (three distinct pillars)

---

## Core Principle

**Agents ≠ Skills. They serve different purposes.**

```
agents/          # 221 PhD-level domain experts (deep, sophisticated)
audits/          # 2,186 quality verification frameworks (comprehensive)
skills/          # NEW - Tactical operations (fast, focused, frequent)
```

---

## Three Pillars - What Each Does

### Agents (Existing - Keep As-Is)

**Purpose:** Deep domain expertise with PhD-level sophistication

**Characteristics:**
- Complex (100+ lines of frontmatter)
- Multi-provider model fallbacks
- Cognitive modes (generative, critical, evaluative, informative)
- Ensemble roles (solo, panel_member, auditor, decision_maker)
- Tool modes (audit, solution, research)
- Escalation logic
- Audit metadata (10-dimension quality tracking)

**When to use:**
- Complex domain work requiring depth
- Multi-step reasoning
- Architectural decisions
- Security analysis
- Code review requiring expertise

**Example agents:**
- python-pro (backend implementation)
- security-auditor (vulnerability analysis)
- kubernetes-expert (orchestration design)
- database-optimizer (query optimization)

**Invocation:**
```bash
# Bash orchestration
atomic_invoke "agents/expert-agents/.../python-pro.md" "$output" "Implement async API"
```

---

### Audits (Existing - Keep As-Is)

**Purpose:** Quality verification frameworks and checklists

**Characteristics:**
- Comprehensive checklist-driven
- 10-dimension evaluation
- Pass/fail criteria
- Evidence-based scoring
- Rubric-driven assessment

**When to use:**
- Code quality verification
- Security audits
- Compliance checking
- Architecture review
- Documentation validation

**Example audits:**
- OWASP Top 10 security audit
- API design audit
- Test coverage audit
- Performance audit

**Invocation:**
```bash
# Phase 6 - Code Review
atomic_invoke "audits/audits/security/owasp-top-10.md" "$output" "Security Audit"
```

---

### Skills (NEW - Strategic Addition)

**Purpose:** Tactical, high-frequency operations where Claude Code native features add value

**Characteristics:**
- Simple (10 lines of frontmatter)
- Single model
- Tool restriction for safety
- Context forking (keeps main session clean)
- Slash command invocation
- Auto-discovery

**When to use:**
- Repetitive operations (formatting, linting, validation)
- High-frequency tasks (quick checks, status queries)
- Operations needing tool restriction (read-only operations)
- Tasks that pollute context (disposable work)
- Quick tactical work (not strategic depth)

**Example skills:**
- format-code (run prettier, black, gofmt)
- lint-check (run linters without explaining)
- validate-json (parse and validate JSON files)
- extract-todos (find TODO comments)
- quick-status (check git status, recent commits)

**Invocation:**
```bash
# Slash command
/format-code "src/**/*.py"

# Or via Claude Code auto-discovery
"Format all Python files in src/"
# Claude sees "format" + "Python", auto-invokes format-code skill
```

---

## Decision Matrix: When to Use What?

| Scenario | Use |
|----------|-----|
| **Implement async FastAPI endpoint with security** | Agent (python-pro) |
| **Design RESTful API architecture** | Agent (openapi-expert) |
| **Audit code for OWASP Top 10 vulnerabilities** | Audit (owasp-top-10) |
| **Review test coverage completeness** | Audit (test-coverage-audit) |
| **Format all Python files with black** | Skill (format-code) |
| **Check git status and recent commits** | Skill (quick-status) |
| **Validate JSON schema** | Skill (validate-json) |
| **Extract all TODO comments** | Skill (extract-todos) |
| **Explain Python async patterns** | Agent (python-pro) |
| **Quick lint check (no explanation)** | Skill (lint-check) |

**Rule of thumb:**
- **Depth & expertise** → Agent
- **Quality verification** → Audit
- **Quick & tactical** → Skill

---

## Skills Catalog - What to Build

### Category 1: Code Formatting & Linting (High Frequency)

**Value:** Time savings, consistency, avoid polluting main session

#### 1. `format-code`
**Purpose:** Auto-format code files (prettier, black, gofmt, rustfmt)
**Why skill:** High frequency, deterministic, no explanation needed
**Time saved:** 30s per invocation
**Context:** `fork` (keeps main session clean)
**Tools:** `Read, Write, Bash`

**Usage:**
```bash
/format-code "src/**/*.py"
/format-code "*.js *.ts"
```

---

#### 2. `lint-check`
**Purpose:** Run linters without explanation (eslint, pylint, ruff, clippy)
**Why skill:** Quick check, no analysis needed
**Time saved:** 45s per invocation
**Context:** `fork`
**Tools:** `Read, Bash` (read-only - no fixes)

**Usage:**
```bash
/lint-check "src/api.py"
/lint-check "*.ts"
```

---

#### 3. `type-check`
**Purpose:** Run type checkers (mypy, tsc, flow)
**Why skill:** Quick validation, deterministic
**Time saved:** 30s per invocation
**Context:** `fork`
**Tools:** `Read, Bash`

**Usage:**
```bash
/type-check "src/**/*.py"
```

---

### Category 2: Validation & Verification (Safety)

**Value:** Tool restriction (read-only), quick checks

#### 4. `validate-json`
**Purpose:** Parse and validate JSON files, check schema
**Why skill:** Tool restriction (can't modify files accidentally)
**Context:** `fork`
**Tools:** `Read` (read-only - safe)

**Usage:**
```bash
/validate-json "config/database.json"
/validate-json ".outputs/2-prd/prd.json" --schema="schemas/prd-schema.json"
```

---

#### 5. `validate-yaml`
**Purpose:** Parse and validate YAML files
**Why skill:** Tool restriction (read-only)
**Context:** `fork`
**Tools:** `Read`

**Usage:**
```bash
/validate-yaml ".github/workflows/ci.yml"
```

---

#### 6. `validate-openapi`
**Purpose:** Validate OpenAPI spec compliance
**Why skill:** Specialized validation, read-only
**Context:** `fork`
**Tools:** `Read, Bash`

**Usage:**
```bash
/validate-openapi "api-spec.yaml"
```

---

### Category 3: Quick Extraction (High Frequency)

**Value:** Fast queries, no analysis needed, disposable context

#### 7. `extract-todos`
**Purpose:** Find all TODO/FIXME/HACK comments
**Why skill:** High frequency, simple extraction
**Time saved:** 1 min per invocation
**Context:** `fork` (disposable)
**Tools:** `Read, Grep`

**Usage:**
```bash
/extract-todos "src/"
/extract-todos "." --format=checklist
```

---

#### 8. `extract-functions`
**Purpose:** List all function signatures
**Why skill:** Quick inventory, no explanation
**Context:** `fork`
**Tools:** `Read, Grep`

**Usage:**
```bash
/extract-functions "src/api.py"
/extract-functions "*.go"
```

---

#### 9. `extract-imports`
**Purpose:** List all imports/dependencies
**Why skill:** Quick check, inventory
**Context:** `fork`
**Tools:** `Read, Grep`

**Usage:**
```bash
/extract-imports "src/**/*.py"
```

---

### Category 4: Git Operations (High Frequency)

**Value:** Quick status checks, no deep analysis

#### 10. `quick-status`
**Purpose:** Git status + recent commits + branch info
**Why skill:** High frequency, quick context
**Time saved:** 30s per invocation
**Context:** `fork`
**Tools:** `Bash`

**Usage:**
```bash
/quick-status
```

**Output:**
```
Branch: main
Status: 3 modified, 1 untracked
Recent commits:
  aee7d57 Remove .env from tracking
  10d3bb0 Complete Python migration
```

---

#### 11. `quick-diff`
**Purpose:** Show git diff summary
**Why skill:** Quick check, no analysis
**Context:** `fork`
**Tools:** `Bash`

**Usage:**
```bash
/quick-diff
/quick-diff "main..feature-branch"
```

---

### Category 5: File Operations (Tactical)

**Value:** Quick file operations without explanation

#### 12. `count-lines`
**Purpose:** Count lines of code by language
**Why skill:** Quick metric, no analysis
**Context:** `fork`
**Tools:** `Read, Bash`

**Usage:**
```bash
/count-lines "src/"
```

**Output:**
```
Python: 15,234 lines
TypeScript: 8,456 lines
Shell: 1,234 lines
Total: 24,924 lines
```

---

#### 13. `find-duplicates`
**Purpose:** Find duplicate code blocks
**Why skill:** Quick check, automated
**Context:** `fork`
**Tools:** `Read, Bash`

**Usage:**
```bash
/find-duplicates "src/" --threshold=10
```

---

#### 14. `check-imports-unused`
**Purpose:** Find unused imports
**Why skill:** Quick check, tooling-based
**Context:** `fork`
**Tools:** `Read, Bash`

**Usage:**
```bash
/check-imports-unused "src/**/*.py"
```

---

### Category 6: Phase-Specific Quick Checks

**Value:** Phase validation without full audit

#### 15. `check-phase-outputs`
**Purpose:** Verify phase output files exist and are valid
**Why skill:** Quick validation before next phase
**Time saved:** 1 min per phase transition
**Context:** `fork`
**Tools:** `Read, Bash`

**Usage:**
```bash
/check-phase-outputs 0  # Check Phase 0 outputs
/check-phase-outputs 2  # Check Phase 2 outputs
```

**Output:**
```
✓ .outputs/0-setup/setup.json exists (valid JSON)
✓ .outputs/0-setup/closeout.json exists (valid JSON)
✓ All required outputs present
```

---

#### 16. `validate-prd`
**Purpose:** Quick PRD completeness check (not full audit)
**Why skill:** Fast pre-flight before Phase 3
**Context:** `fork`
**Tools:** `Read`

**Usage:**
```bash
/validate-prd ".outputs/2-prd/prd.md"
```

**Output:**
```
✓ Executive Summary present
✓ Requirements section present
✗ Missing: Acceptance Criteria
⚠  Recommendation: Add acceptance criteria before Phase 3
```

---

#### 17. `check-test-coverage`
**Purpose:** Quick coverage percentage (not full audit)
**Why skill:** Fast check, tooling-based
**Context:** `fork`
**Tools:** `Read, Bash`

**Usage:**
```bash
/check-test-coverage
```

**Output:**
```
Coverage: 87.5%
Files < 80%: api.py (45%), utils.py (67%)
```

---

### Category 7: Documentation Quick Gen

**Value:** Repetitive doc generation without strategic thinking

#### 18. `generate-changelog`
**Purpose:** Generate changelog from git commits
**Why skill:** Automated, follows pattern
**Context:** `fork`
**Tools:** `Read, Bash, Write`

**Usage:**
```bash
/generate-changelog "v1.0.0..v1.1.0"
```

---

#### 19. `generate-api-summary`
**Purpose:** Quick endpoint summary (not full API docs)
**Why skill:** Extraction, no design analysis
**Context:** `fork`
**Tools:** `Read`

**Usage:**
```bash
/generate-api-summary "api-spec.yaml"
```

**Output:**
```
Endpoints: 15
  GET: 8
  POST: 4
  PUT: 2
  DELETE: 1
Authentication: Bearer token
```

---

### Category 8: Atomic-Claude Specific

**Value:** Pipeline-specific operations

#### 20. `phase-summary`
**Purpose:** Quick summary of phase progress
**Why skill:** High frequency check
**Context:** `fork`
**Tools:** `Read`

**Usage:**
```bash
/phase-summary 1
```

**Output:**
```
Phase 1: Discovery
Status: In Progress
Completed: 7/10 tasks
Last: Task 107 (Approach Selection)
Next: Task 108 (Discovery Diagrams)
```

---

## Skills Directory Structure

```
.claude/skills/
├── README.md                    # Skills catalog
│
├── formatting/
│   ├── format-code/
│   │   ├── SKILL.md
│   │   └── templates/
│   │       ├── prettier.json
│   │       ├── black.toml
│   │       └── rustfmt.toml
│   ├── lint-check/
│   │   └── SKILL.md
│   └── type-check/
│       └── SKILL.md
│
├── validation/
│   ├── validate-json/
│   │   └── SKILL.md
│   ├── validate-yaml/
│   │   └── SKILL.md
│   └── validate-openapi/
│       └── SKILL.md
│
├── extraction/
│   ├── extract-todos/
│   │   └── SKILL.md
│   ├── extract-functions/
│   │   └── SKILL.md
│   └── extract-imports/
│       └── SKILL.md
│
├── git-ops/
│   ├── quick-status/
│   │   └── SKILL.md
│   └── quick-diff/
│       └── SKILL.md
│
├── file-ops/
│   ├── count-lines/
│   │   └── SKILL.md
│   ├── find-duplicates/
│   │   └── SKILL.md
│   └── check-imports-unused/
│       └── SKILL.md
│
├── phase-checks/
│   ├── check-phase-outputs/
│   │   └── SKILL.md
│   ├── validate-prd/
│   │   └── SKILL.md
│   └── check-test-coverage/
│       └── SKILL.md
│
├── doc-gen/
│   ├── generate-changelog/
│   │   └── SKILL.md
│   └── generate-api-summary/
│       └── SKILL.md
│
└── atomic/
    └── phase-summary/
        └── SKILL.md
```

---

## Implementation Priority

### Phase 1: High-Value Quick Wins (Week 1)

1. **format-code** - High frequency, clear value
2. **quick-status** - Used constantly
3. **extract-todos** - Very common operation
4. **validate-json** - Safety + frequent use
5. **check-phase-outputs** - Phase transition validation

**Expected impact:** 10-15 min/day saved

---

### Phase 2: Phase-Specific (Week 2)

6. **validate-prd** - Phase 2 → 3 gate
7. **check-test-coverage** - Phase 7 validation
8. **phase-summary** - Status checking
9. **quick-diff** - Git operations
10. **lint-check** - Pre-commit checks

**Expected impact:** 5-10 min/day saved

---

### Phase 3: Documentation & Advanced (Week 3)

11. **generate-changelog** - Release automation
12. **generate-api-summary** - API documentation
13. **validate-openapi** - API validation
14. **count-lines** - Metrics
15. **find-duplicates** - Code quality

**Expected impact:** 5-10 min/day saved

---

### Phase 4: Specialized (Week 4)

16-20. Remaining skills based on usage patterns

**Total expected impact:** 20-35 min/day saved

---

## Comparison: Agent vs Skill

### Example: Code Formatting

**Using Agent (python-pro):**
```bash
atomic_invoke "agents/expert-agents/.../python-pro.md" "output.txt" \
  "Format this Python file according to PEP 8"

# Result:
# - Explains PEP 8 principles
# - Discusses formatting choices
# - Explains why certain patterns are Pythonic
# - Provides formatted code
# Time: 2-3 minutes
# Context pollution: High (long explanation)
```

**Using Skill (format-code):**
```bash
/format-code "src/api.py"

# Result:
# - Runs black
# - Returns formatted file
# - No explanation
# Time: 10 seconds
# Context pollution: Zero (forked)
```

**When to use which:**
- Need to understand WHY → Agent (python-pro)
- Just need formatted code → Skill (format-code)

---

## Integration with Existing Pipeline

### Phase 0: Setup
- **/quick-status** - Check git state
- **/validate-json** - Verify setup.json

### Phase 1: Discovery
- **/extract-todos** - Find existing TODOs
- **/count-lines** - Codebase size
- **/extract-imports** - Dependency inventory

### Phase 2: PRD
- **/validate-prd** - Quick completeness check
- **/validate-json** - Verify PRD JSON structure

### Phase 3: Tasking
- **/check-phase-outputs** - Verify Phase 2 complete

### Phase 4: Specification
- **/validate-openapi** - Spec validation
- **/generate-api-summary** - Quick overview

### Phase 5: Implementation
- **/format-code** - Auto-format generated code
- **/lint-check** - Quick lint validation
- **/type-check** - Type validation

### Phase 6: Code Review
- **/check-imports-unused** - Cleanup check
- **/find-duplicates** - Code quality check

### Phase 7: Integration
- **/check-test-coverage** - Coverage validation
- **/quick-status** - Git state before PR

### Phase 8: Deployment Prep
- **/check-phase-outputs** - Verify all outputs

### Phase 9: Release
- **/generate-changelog** - Auto-generate changelog
- **/quick-diff** - Review changes

---

## Cost-Benefit Analysis

### Time Savings

| Skill | Frequency | Time Saved/Use | Daily Savings |
|-------|-----------|----------------|---------------|
| format-code | 10x/day | 30s | 5 min |
| quick-status | 20x/day | 20s | 6.7 min |
| extract-todos | 5x/day | 1 min | 5 min |
| validate-json | 8x/day | 20s | 2.7 min |
| check-phase-outputs | 3x/day | 1 min | 3 min |
| lint-check | 15x/day | 30s | 7.5 min |
| **Total** | | | **30 min/day** |

**Annual:** 30 min/day × 250 days = **125 hours**

**ROI:** 125 hours × $150/hr = **$18,750/year**

---

### Context Savings

Skills use `context: fork` → disposable context

**Without skills:**
- Main session fills with formatting output, lint results, status checks
- Need `/clear` frequently (lose context)
- Need `/catchup` after clear (time cost)

**With skills:**
- Main session stays clean (only strategic work)
- Tactical work in forked context (auto-disposed)
- Rarely need `/clear`

**Estimated:** 3-5 fewer `/clear + /catchup` cycles per day = 15-25 min saved

---

### Cost Savings

Skills use fast operations (no LLM needed for many):

- `format-code` - Runs black/prettier (no LLM)
- `lint-check` - Runs linters (no LLM)
- `validate-json` - JSON parser (no LLM)
- `quick-status` - Git commands (no LLM)

**Many skills = pure tooling, no API cost.**

Skills that DO use LLM use Haiku (10x cheaper than Opus):
- `extract-todos` - Simple extraction (Haiku sufficient)
- `phase-summary` - Simple summary (Haiku sufficient)

**Estimated cost savings:** 20-30% reduction in LLM API costs for tactical operations

---

## Skills vs Agents: Clear Boundaries

### Use Agent When:
- Need domain expertise
- Strategic decision required
- Multi-step reasoning
- Explanation required
- Complex analysis
- Security review
- Architecture design

### Use Skill When:
- Repetitive operation
- Quick check/validation
- Formatting/linting
- Simple extraction
- Status query
- Tool-based operation (no reasoning)
- Want to avoid context pollution

---

## Documentation

Create `skills/README.md`:

```markdown
# Atomic Claude Skills

Tactical operations for high-frequency, focused tasks.

## What are Skills?

Skills are **not agents**. They are:
- Fast (< 30 seconds)
- Focused (single operation)
- Frequent (used 5-20x/day)
- Forked (disposable context)
- Tool-based (often no LLM needed)

## When to Use Skills

Use skills for:
✓ Code formatting
✓ Linting/type checking
✓ Quick validation
✓ Status checks
✓ Simple extraction
✓ Repetitive operations

Use agents for:
✗ Domain expertise
✗ Strategic decisions
✗ Complex analysis
✗ Explanations
✗ Multi-step reasoning

## Available Skills

### Formatting (3)
- `/format-code` - Auto-format code files
- `/lint-check` - Run linters
- `/type-check` - Run type checkers

### Validation (3)
- `/validate-json` - Validate JSON files
- `/validate-yaml` - Validate YAML files
- `/validate-openapi` - Validate OpenAPI specs

### Extraction (3)
- `/extract-todos` - Find TODO comments
- `/extract-functions` - List function signatures
- `/extract-imports` - List imports/dependencies

### Git (2)
- `/quick-status` - Git status + recent commits
- `/quick-diff` - Git diff summary

### Files (3)
- `/count-lines` - Count lines of code
- `/find-duplicates` - Find duplicate code
- `/check-imports-unused` - Find unused imports

### Phase Checks (3)
- `/check-phase-outputs` - Verify phase outputs
- `/validate-prd` - Quick PRD completeness
- `/check-test-coverage` - Quick coverage check

### Documentation (2)
- `/generate-changelog` - Generate changelog
- `/generate-api-summary` - API endpoint summary

### Atomic (1)
- `/phase-summary` - Phase progress summary

## Usage

```bash
# Start Claude Code
claude

# Use slash command
/format-code "src/**/*.py"

# Or let Claude auto-discover
"Format all Python files"
```
```

---

## Next Steps

1. **Create skills directory structure:**
   ```bash
   mkdir -p .claude/skills/{formatting,validation,extraction,git-ops,file-ops,phase-checks,doc-gen,atomic}
   ```

2. **Implement Phase 1 skills** (5 high-value):
   - format-code
   - quick-status
   - extract-todos
   - validate-json
   - check-phase-outputs

3. **Test in real workflow:**
   - Use during Phase 0 setup
   - Measure time savings
   - Validate context forking works

4. **Roll out Phase 2-4 skills** based on usage patterns

5. **Document in skills/README.md**

---

## Summary

**Three Pillars:**

| Pillar | Purpose | Count | Sophistication | Frequency |
|--------|---------|-------|----------------|-----------|
| **Agents** | Domain expertise | 221 | PhD-level | Low (strategic) |
| **Audits** | Quality verification | 2,186 | Comprehensive | Medium (gates) |
| **Skills** | Tactical operations | 20 | Simple | High (tactical) |

**Skills fill a gap:** Fast, focused, frequent operations that don't need agent sophistication.

**Expected Impact:**
- **Time:** 125 hours/year saved
- **Cost:** 20-30% reduction in tactical LLM costs
- **Quality:** Cleaner main context, less pollution
- **UX:** Faster feedback, slash commands, auto-discovery

**No conflict with agents.** Skills complement agents, not replace them.

---

*Strategy document created February 10, 2026*
*Recommendation: Proceed with Phase 1 implementation (5 skills)*
