# Atomic Claude Skills

**Tactical operations for high-frequency, focused tasks.**

Skills are **not agents**. They are fast, focused, frequent operations that complement agent expertise.

---

## Three Pillars

| Pillar | Purpose | Count | When to Use |
|--------|---------|-------|-------------|
| **Agents** | Domain expertise | 221 | Strategic work, deep analysis |
| **Audits** | Quality verification | 2,186 | Comprehensive validation |
| **Skills** | Tactical operations | 20 | Quick checks, formatting, extraction |

---

## What are Skills?

Skills are:
- ✅ **Fast** (< 30 seconds)
- ✅ **Focused** (single operation)
- ✅ **Frequent** (used 5-20x/day)
- ✅ **Forked** (disposable context via `context: fork`)
- ✅ **Tool-based** (often no LLM needed, pure tooling)

Skills are NOT:
- ❌ Domain experts (use agents)
- ❌ Comprehensive audits (use audits)
- ❌ Strategic decisions (use agents)
- ❌ Complex analysis (use agents)

---

## When to Use What?

### Use Agent When:
- Need domain expertise (python-pro, security-auditor, kubernetes-expert)
- Strategic decision required
- Multi-step reasoning
- Explanation required
- Complex analysis
- Architecture design

### Use Audit When:
- Comprehensive quality check (OWASP Top 10, API design audit)
- Pass/fail gate
- Checklist-driven validation
- Evidence-based scoring

### Use Skill When:
- Quick formatting/linting
- Status check
- Simple extraction (TODOs, imports)
- File validation
- Repetitive operation
- Want to avoid context pollution

---

## Example Comparison

### Scenario: Format Python Files

**Using Agent (python-pro):**
```bash
atomic_invoke "agents/expert-agents/.../python-pro.md" "output.txt" \
  "Format this Python file according to PEP 8"

# Result:
# - Explains PEP 8 principles
# - Discusses formatting choices
# - Explains why patterns are Pythonic
# - Provides formatted code
# Time: 2-3 minutes
# Context pollution: High (explanation fills context)
```

**Using Skill (format-code):**
```bash
/format-code "src/api.py"

# Result:
# - Runs black
# - Returns: "✓ Formatted 1 file"
# Time: 10 seconds
# Context pollution: Zero (forked context, auto-disposed)
```

**When to use which:**
- Need to understand WHY → Agent
- Just need formatted code → Skill

---

## Available Skills

### Phase 1 (Implemented) ✅

#### Formatting
- **`/format-code`** - Auto-format code (black, prettier, gofmt, rustfmt)
  - Usage: `/format-code "src/**/*.py"`
  - Time saved: 30s/use, 10x/day = 5 min/day

#### Git Operations
- **`/quick-status`** - Git status + recent commits + branch info
  - Usage: `/quick-status`
  - Time saved: 20s/use, 20x/day = 6.7 min/day

#### Extraction
- **`/extract-todos`** - Find TODO/FIXME/HACK/NOTE comments
  - Usage: `/extract-todos "src/"`
  - Time saved: 1 min/use, 5x/day = 5 min/day

#### Validation
- **`/validate-json`** - Parse & validate JSON files
  - Usage: `/validate-json "config/database.json"`
  - Time saved: 20s/use, 8x/day = 2.7 min/day

#### Phase Checks
- **`/check-phase-outputs`** - Verify phase outputs exist and are valid
  - Usage: `/check-phase-outputs 0`
  - Time saved: 1 min/use, 3x/day = 3 min/day

**Phase 1 Total:** 22.4 min/day saved

---

### Phase 2 (Implemented) ✅

#### Formatting
- **`/lint-check`** - Run linters without explanation
  - Usage: `/lint-check "src/"`
  - Time saved: 45s/use, 8x/day = 6 min/day

- **`/type-check`** - Run type checkers (mypy, tsc)
  - Usage: `/type-check "src/"`
  - Time saved: 1 min/use, 6x/day = 6 min/day

#### Validation
- **`/validate-yaml`** - Parse & validate YAML files
  - Usage: `/validate-yaml "config/app.yaml"`
  - Time saved: 20s/use, 5x/day = 1.7 min/day

- **`/validate-openapi`** - Validate OpenAPI specs
  - Usage: `/validate-openapi "api/openapi.yaml"`
  - Time saved: 30s/use, 4x/day = 2 min/day

#### Extraction
- **`/extract-functions`** - List function signatures
  - Usage: `/extract-functions "src/"`
  - Time saved: 45s/use, 4x/day = 3 min/day

- **`/extract-imports`** - List dependencies
  - Usage: `/extract-imports "src/"`
  - Time saved: 30s/use, 3x/day = 1.5 min/day

#### Git Operations
- **`/quick-diff`** - Git diff summary
  - Usage: `/quick-diff` or `/quick-diff "HEAD~3"`
  - Time saved: 30s/use, 10x/day = 5 min/day

#### Phase Checks
- **`/validate-prd`** - Quick PRD completeness check
  - Usage: `/validate-prd`
  - Time saved: 1 min/use, 2x/day = 2 min/day

- **`/check-test-coverage`** - Coverage percentage
  - Usage: `/check-test-coverage "src/"`
  - Time saved: 1 min/use, 5x/day = 5 min/day

**Phase 2 Total:** 32.2 min/day saved

---

### Phase 3 (Implemented) ✅

#### File Operations
- **`/count-lines`** - Lines of code by language
  - Usage: `/count-lines "src/"`
  - Time saved: 30s/use, 4x/day = 2 min/day

- **`/find-duplicates`** - Duplicate code detection
  - Usage: `/find-duplicates "src/"`
  - Time saved: 1 min/use, 3x/day = 3 min/day

- **`/check-imports-unused`** - Find unused imports
  - Usage: `/check-imports-unused "src/"`
  - Time saved: 45s/use, 4x/day = 3 min/day

#### Documentation
- **`/generate-changelog`** - Auto-generate from git commits
  - Usage: `/generate-changelog "v1.0.0..HEAD"`
  - Time saved: 2 min/use, 1x/day = 2 min/day

- **`/generate-api-summary`** - API endpoint summary
  - Usage: `/generate-api-summary "api/openapi.yaml"`
  - Time saved: 1 min/use, 2x/day = 2 min/day

**Phase 3 Total:** 12 min/day saved

---

### Phase 4 (Implemented) ✅

#### Atomic-Specific
- **`/phase-summary`** - Phase progress status
  - Usage: `/phase-summary` or `/phase-summary all` or `/phase-summary 0`
  - Time saved: 30s/use, 10x/day = 5 min/day

**Phase 4 Total:** 5 min/day saved

---

## Usage

### Option 1: Slash Commands (Recommended)

```bash
# Start Claude Code
cd /Users/jamesterbeest/dev/atomic-claude2
claude

# Use slash command
> /format-code "src/**/*.py"
> /quick-status
> /extract-todos "src/"
```

### Option 2: Auto-Discovery

```bash
# Claude Code auto-discovers based on description
> "Format all Python files in src/"
# Claude sees "format" + "Python", invokes /format-code

> "Show me git status"
# Claude sees "git status", invokes /quick-status
```

### Option 3: Bash Wrapper (Future)

```bash
# Direct invocation from bash scripts
atomic_skill "format-code" "src/**/*.py"
atomic_skill "quick-status"
```

---

## Integration with Phases

### Phase 0: Setup
- `/quick-status` - Check git state
- `/validate-json` - Verify setup.json

### Phase 1: Discovery
- `/extract-todos` - Find existing TODOs
- `/count-lines` - Codebase size
- `/extract-imports` - Dependency inventory

### Phase 2: PRD
- `/validate-prd` - Quick completeness check
- `/validate-json` - Verify PRD JSON structure

### Phase 3: Tasking
- `/check-phase-outputs` - Verify Phase 2 complete

### Phase 4: Specification
- `/validate-openapi` - Spec validation
- `/generate-api-summary` - Quick overview

### Phase 5: Implementation
- `/format-code` - Auto-format generated code
- `/lint-check` - Quick lint validation
- `/type-check` - Type validation

### Phase 6: Code Review
- `/check-imports-unused` - Cleanup check
- `/find-duplicates` - Code quality

### Phase 7: Integration
- `/check-test-coverage` - Coverage validation
- `/quick-status` - Git state before PR

### Phase 8: Deployment Prep
- `/check-phase-outputs` - Verify all outputs

### Phase 9: Release
- `/generate-changelog` - Auto-generate changelog
- `/quick-diff` - Review changes

---

## Expected Impact

### Time Savings

| Phase | Skills per Phase | Time Saved/Day |
|-------|------------------|----------------|
| Phase 1 (Implemented) | 5 skills | 22.4 min |
| Phase 2 (Implemented) | 9 skills | 32.2 min |
| Phase 3 (Implemented) | 5 skills | 12.0 min |
| Phase 4 (Implemented) | 1 skill | 5.0 min |
| **Total (All phases)** | **20 skills** | **71.6 min/day** |

**Annual:** 71.6 min/day × 250 days = **298.3 hours/year**

**ROI:** 298.3 hours × $150/hr = **$44,745/year**

### Cost Savings

**All skills use Sonnet with forked context:**
- Premium model quality (consistent with atomic-claude philosophy)
- Forked context = minimal token usage (typically < 1000 tokens)
- Fast operations = low API costs per invocation

**Cost analysis:**
- Sonnet: ~$0.003 per skill invocation (< 1000 tokens)
- 50 invocations/day = $0.15/day = $38/year
- **Negligible cost compared to $34,125/year time savings (ROI: 898x)**

**Skills vs Agent comparison:**
- Agent: 2-3 minutes, 5,000+ tokens, full context
- Skill: 10-30 seconds, < 1,000 tokens, forked context
- **Savings: 80% less time, 80% less tokens, 100% less context pollution**

**Estimated total savings:** Time savings ($34k/yr) >> API costs ($38/yr)

### Context Savings

Skills use `context: fork` → disposable context

**Without skills:**
- Main session fills with formatting output, lint results
- Need `/clear` frequently (lose context)
- Need `/catchup` after clear (time cost)

**With skills:**
- Main session stays clean (only strategic work)
- Tactical work in forked context (auto-disposed)
- Rarely need `/clear`

**Estimated:** 3-5 fewer `/clear + /catchup` cycles/day = 15-25 min saved

---

## Directory Structure

```
.claude/skills/
├── README.md                    # This file
│
├── formatting/
│   ├── format-code/
│   │   └── SKILL.md
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

## Contributing

To add a new skill:

1. **Determine category** (formatting, validation, extraction, etc.)

2. **Create skill directory:**
   ```bash
   mkdir -p .claude/skills/{category}/{skill-name}
   ```

3. **Create SKILL.md** with frontmatter:
   ```yaml
   ---
   name: skill-name
   description: Brief description for auto-discovery
   model: haiku
   tools:
     - Read
     - Write
     - Bash
   context: fork
   disable-model-invocation: false
   ---
   ```

4. **Keep it tactical:**
   - Fast (< 30 seconds)
   - Focused (single operation)
   - No explanation unless required
   - Tool-based when possible

5. **Test:**
   ```bash
   claude
   > /skill-name "arguments"
   ```

6. **Document usage** in this README

---

## FAQs

**Q: When should I use a skill vs an agent?**
A: If you need expertise or explanation, use an agent. If you just need a quick operation done, use a skill.

**Q: Can skills call agents?**
A: No. Skills are independent. If you need agent expertise, use the agent directly.

**Q: Why do skills use Haiku?**
A: Most skills are simple operations that don't need Opus/Sonnet reasoning. Haiku is 10x cheaper and fast enough.

**Q: What if a skill needs a more powerful model?**
A: Change `model: haiku` to `model: sonnet` in frontmatter. Only do this if truly needed (cost implications).

**Q: Can I use skills from bash scripts?**
A: Not yet, but we plan to add `atomic_skill()` function to lib/atomic.sh for bash integration.

**Q: Why `context: fork`?**
A: Keeps main session clean. Skill work is disposable, shouldn't pollute strategic conversation.

---

*Skills catalog for atomic-claude2*
*Phase 1 implemented: February 10, 2026*
