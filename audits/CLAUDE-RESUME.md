# Audit Generation - Resume Guide for Claude Code

## Quick Start

You are continuing work on the Software Stack Audit Taxonomy project. This document helps you resume audit generation immediately.

## Current Progress

**Total Audits Generated:** 393 / ~2,200 (~18%)

| Category | Name | Audits | Status |
|----------|------|--------|--------|
| 01 | Security & Trust | 82 | COMPLETE |
| 02 | Performance & Efficiency | 95 | COMPLETE |
| 03 | Reliability & Resilience | 68 | COMPLETE |
| 04 | Scalability & Capacity | 48 | COMPLETE |
| 05 | Observability & Instrumentation | 60 | COMPLETE |
| 06 | Code Quality & Craftsmanship | 40 | PARTIAL (needs Static Analysis, Testing) |
| 07 | Architecture & Design | 0 | NOT STARTED |
| 08-43 | Remaining Categories | 0 | NOT STARTED |

## What's Left for Category 6

Need to complete in `audits/06-code-quality/`:
- **static-analysis/** (12 audits): linting-coverage, code-complexity, dead-code-detection, duplicate-code, dependency-vulnerability, type-safety, null-safety, security-scanning, code-style-consistency, static-analysis-ci, false-positive-rate, custom-rule-coverage
- **testing/** (14 audits): unit-test-coverage, integration-test-coverage, e2e-test-coverage, mutation-testing, test-execution-time, flaky-test, test-isolation, test-data-management, mock-vs-real-dependency, contract-testing, property-based-testing, visual-regression, accessibility-testing, test-maintenance

## What's Left for Category 7

Need to complete in `audits/07-architecture-design/`:
- **api-design/** (12 audits)
- **modularity/** (10 audits)
- **data-architecture/** (10 audits)
- **integration-patterns/** (10 audits)
- **architecture-evolution/** (8 audits)

## Repository Structure

```
~/walnut-drive/dev/audits/           # Main repo (push to main)
~/walnut-drive/dev/audit-worktrees/  # Git worktrees for parallel work
  ├── worker-1/                      # Branch: worker-1
  ├── worker-2/                      # Branch: worker-2
  ├── worker-3/                      # Branch: worker-3
  ├── worker-4/                      # Branch: worker-4
  ├── worker-5/                      # Branch: worker-5
  ├── orchestration.yaml             # Work assignments
  ├── progress.md                    # Progress tracking
  └── AGENT-PROMPT.md                # Worker instructions
```

## How to Generate Audits

### 1. Reset Worktrees to Latest Main
```bash
for i in 1 2 3 4 5; do
  cd ~/walnut-drive/dev/audit-worktrees/worker-$i
  git fetch origin main && git reset --hard origin/main
done
```

### 2. Create Category Directories
```bash
mkdir -p ~/walnut-drive/dev/audit-worktrees/worker-{1..5}/audits/{CATEGORY}/{subcategories}
```

### 3. Launch Parallel Workers
Use the Task tool with subagent_type="general-purpose" to launch workers. Each worker:
- Works in their own worktree (worker-1 through worker-5)
- Creates YAML audit files following the template
- Commits each audit individually
- Pushes with `git push origin worker-N --force`

### 4. Merge to Main
```bash
cd ~/walnut-drive/dev/audits
git fetch --all
git merge worker-1 -m "Merge message"
git merge worker-2 -m "Merge message"
# ... etc
git push origin main
```

## Audit YAML Template

Template location: `schema/AUDIT-TEMPLATE-BLANK.yaml`

Key fields:
- **id**: `{category}.{subcategory}.{slug}` (e.g., `security-trust.authentication.oauth2-implementation`)
- **category_number**: 1-43
- **signals**: Must have 2+ critical, 2+ high severity
- **closeout_checklist**: Must have working bash verification commands

## Category Reference

Full taxonomy in `AUDIT-MENU.md`. Categories 1-7:
1. Security & Trust (82 audits)
2. Performance & Efficiency (95 audits)
3. Reliability & Resilience (68 audits)
4. Scalability & Capacity (48 audits)
5. Observability & Instrumentation (60 audits)
6. Code Quality & Craftsmanship (~75 audits)
7. Architecture & Design (~50 audits)

## GitHub Repository

https://github.com/turbobeest/audits

## Next Steps to Resume

1. Read this file and `AUDIT-MENU.md`
2. Check current audit count: `find audits -name "*.yaml" | wc -l`
3. Complete Category 6 (static-analysis, testing)
4. Complete Category 7 (all subcategories)
5. Continue with Categories 8-43 as needed

## User Preferences

- Weekly budget: ~500 audits
- Generate specific audits on-demand for projects
- Parallel workers: 5 maximum
- Git worktrees for isolation
