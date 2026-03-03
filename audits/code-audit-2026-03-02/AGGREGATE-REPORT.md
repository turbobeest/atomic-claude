# Atomic Claude 2.0 — Full Codebase Audit Report

**Date**: 2026-03-02
**Auditor**: Claude Opus 4.6 (12 parallel agents)
**Checklist**: TASK-CODE-AUDIT-CHECKLIST.md (categories A-R, 130+ checks)
**Scope**: ~100 files across 10 phases + orchestration + core modules
**Severity threshold**: CRITICAL / HIGH / MEDIUM only (strict criteria with concrete trigger scenarios)

---

## Aggregate Summary

| Phase | Files | Critical | High | Medium | Total |
|-------|-------|----------|------|--------|-------|
| 00 Setup | 6 | 0 | 0 | 3 | 3 |
| 01 Discovery | 10 | 0 | 0 | 6 | 6 |
| 02 PRD | 11 | 0 | 1 | 5 | 6 |
| 03 Tasking | 7 | 0 | 1 | 6 | 7 |
| 04 Specification | 7 | 0 | 0 | 5 | 5 |
| 05 Implementation | 8 | 0 | 0 | 7 | 7 |
| 06 Code Review | 7 | 0 | 0 | 5 | 5 |
| 07 Integration | 8 | 0 | 0 | 4 | 4 |
| 08 Deployment Prep | 8 | 0 | 0 | 4 | 4 |
| 09 Release | 7 | 0 | 0 | 3 | 3 |
| Orchestration | 10 | 0 | 1 | 7 | 8 |
| Core | 17 | 0 | 2 | 8 | 10 |
| **TOTAL** | **106** | **0** | **5** | **63** | **68** |

---

## Comparison with Previous Audit (2026-02-28)

| Metric | 2026-02-28 | 2026-03-02 | Change |
|--------|-----------|-----------|--------|
| Critical | 19 | 0 | -19 |
| High | 59 | 5 | -54 |
| Medium | 294 | 63 | -231 |
| Total reported | 1,777 | 68 | -1,709 |

Note: The 2026-02-28 audit reported LOW and INFO severity; this audit applies strict criteria (CRITICAL/HIGH/MEDIUM only, concrete trigger scenarios required). The reduction reflects both codebase improvements and stricter reporting standards.

---

## HIGH Findings (5)

### H1. `core/graph/reader.py` lines 82, 101 — Cypher injection via filter keys
**Check**: G2 | **Report**: core-modules.md
`get_nodes()` and `count_nodes()` interpolate filter dict keys directly into Cypher WHERE clauses without validation. The writer module has `_validate_property_key()` but the reader does not use it.
**Trigger**: Any caller passing user-derived data as a filter key (e.g., from LLM output or task metadata).
**Fix**: Apply `_validate_property_key()` to all filter keys in reader methods, or share the writer's validation.

### H2. `core/graph/reader.py` lines 129, 160-161 — Cypher injection via relationship types
**Check**: G2 | **Report**: core-modules.md
`get_neighbors()` and `get_path()` interpolate `rel_type` and `rel_types` strings directly into Cypher patterns without allowlist validation.
**Trigger**: Any caller passing unvalidated relationship type strings.
**Fix**: Add allowlist validation matching the writer module's pattern.

### H3. `orchestration/phase_runner.py` lines 141-298 — UnboundLocalError on non-LLM non-infrastructure tasks
**Check**: A1 | **Report**: orchestration-modules.md
The `roster` variable is only assigned inside an `else` branch when `is_infrastructure_task()` is False AND `task_uses_llm` is True. If a task has `uses_llm=False` but is not an infrastructure task, `roster` is never assigned, yet lines 230, 258, and 298 reference it.
**Trigger**: Any task registered with `uses_llm=False` that is not in the infrastructure task list.
**Fix**: Initialize `roster = None` before the conditional block, or restructure the branching.

### H4. `phases/phase_02_prd/tasks/task_207_prd_approval.py` lines 137-155 — Failed refinements count toward auto-approval budget
**Check**: R3 | **Report**: phase-02-prd.md (see also orchestrator02.py H1)
`refinement_count` increments even when refinement fails (LLM error, no changes made), prematurely exhausting the 3-attempt budget and leading to unintended auto-approval without explicit user confirmation.
**Trigger**: LLM returns errors on 3 consecutive refinement attempts; PRD auto-approves with no actual refinement.
**Fix**: Only increment `refinement_count` when refinement succeeds (changes were actually applied).

### H5. `phases/phase_03_tasking/tasks/task_301_entry_initialization.py` lines 296-363 — API key written to .env without verified gitignore
**Check**: G3 | **Report**: phase-03-tasking.md
The Anthropic API key from `secrets.json` is written in plaintext to the target project's `.env` file. `_ensure_env_gitignored()` is called beforehand but there is no verification that `.gitignore` was actually updated.
**Trigger**: If the gitignore write fails silently or the file is concurrently modified, the API key could end up committed to version control.
**Fix**: Verify gitignore contains the `.env` entry after writing, or write `.env` to a non-tracked location.

---

## MEDIUM Findings by Category

### Systemic: OUTPUT_DIR default path (7 occurrences)
Orchestrators 01-09 compute `OUTPUT_DIR` from `ATOMIC_ROOT.parent` or `Path.cwd()` at module import time, which can place outputs outside the project tree if `ATOMIC_ROOT` is unset.
**Files**: orchestrator01-09.py (lines 40-41 in each)

### Security & Injection
- **core/graph/reader.py** — Inconsistent label validation (labels interpolated without `_VALID_LABELS` check)
- **core/subprocess_runner.py** — `run_bash_command()` defaults `reject_shell_meta=False`
- **core/llm/ollama.py** — SSRF TOCTOU in DNS validation (DNS rebinding gap)
- **task_804 artifact_generation** — PRD content interpolated into LLM prompts without delimiters

### State & Data Integrity
- **phase_runner.py** — Retry loop exception handling leaves `success = None` on non-final attempts
- **phase_runner.py** — Stale `roster` from previous loop iteration leaks into current iteration
- **pipeline.py** — `memory_handle_backtrack` called twice during `rollback_to_phase()`
- **backtrack.py** — Inconsistent return values (`False`/`None`/implicit `None`)
- **backtrack.py** — Non-atomic `write_text()` for clearing `errors.json`
- **dashboard_sync.py** — Windows file locking uses hardcoded 1MB byte range
- **core/state.py** — Windows msvcrt.locking on empty file may fail
- **core/llm/invoke.py** — Windows msvcrt.locking byte range mismatch

### LLM Response Handling
- **task_104/105** — Silent fallback to fabricated data on JSON parse failures
- **task_303** — LLM output used without schema validation; missing keys cause KeyError in graph writes
- **task_303** — Unguarded `json.loads` after `_repair_json` returns True
- **task_504** — `extract_code_from_response` falls back to entire raw LLM response as source code
- **task_603** — Failed agent load silently defaults to "haiku" instead of "sonnet"
- **task_604** — Curly braces in LLM-generated findings corrupt f-string JSON template
- **task_604** — Valid non-dict JSON written to disk then crashes on `.get()`

### Cross-Task Contract Mismatches
- **task_504** — Multi-file GREEN output skips REFACTOR and VERIFY phases (file path mismatch)
- **task_804/806/807** — `"cached"` artifact status treated as failure by downstream tasks
- **task_109** — Closeout marks legitimately absent files as CRIT failures on greenfield projects

### Miscellaneous
- **task_002** — `_create_secrets_file()` returns `False` on failure but caller never checks
- **task_002** — Claude Code subscription writes `null` API key to secrets.json
- **task_001** — `import grp` on Windows raises before platform guard executes
- **task_101** — Auto-flatten overwrites project-config.json without backup
- **task_205** — Failed file write silently discards successfully generated LLM content
- **task_206** — Dead code: `isinstance(content, dict)` on always-str return value
- **task_206b** — Fuzzy edit fallback strips markdown trailing-space line breaks
- **task_207** — Auto-approval after max_refinements without explicit confirmation
- **task_301** — Repeated runs accumulate duplicate comment headers in .env file
- **task_303** — TOCTOU pattern in _repair_json (write-then-read vs return parsed dict)
- **task_304** — Bare `input()` blocks indefinitely in non-interactive environments
- **task_403** — Greedy JSON regex may grab invalid content
- **task_404** — `BaseException` catch doesn't protect `os.unlink` cleanup
- **task_406** — `Path.relative_to()` raises on Windows cross-drive paths
- **task_504** — Unbounded `rglob` in every parallel worker thread
- **task_604** — `subprocess.TimeoutExpired` reported as "No test runner detected"
- **task_606** — Triple `.parent` traversal for path computation
- **task_701** — Non-dict JSON from closeout file raises AttributeError
- **task_701** — `null` JSON literal passes prerequisite check silently
- **task_704** — Missing `OSError` in exception handler
- **task_902** — "Review again" path skips re-confirmation
- **task_904** — Greedy frontmatter stripping on `---` in agent markdown body
- **task_906** — Missing `uses_llm = False` triggers unnecessary agent roster display
- **core/config.py** — Parent directory config loading
- **core/llm/resolver.py** — Same parent directory traversal pattern
- **phase_runner.py** — File descriptor leak if `os.fdopen()` fails after `mkstemp()`

---

## Detailed Reports

| Report | Path |
|--------|------|
| Phase 00 | `audits/code-audit-2026-03-02/phase-00-setup.md` |
| Phase 01 | `audits/code-audit-2026-03-02/phase-01-discovery.md` |
| Phase 02 | `audits/code-audit-2026-03-02/phase-02-prd.md` |
| Phase 03 | `audits/code-audit-2026-03-02/phase-03-tasking.md` |
| Phase 04 | `audits/code-audit-2026-03-02/phase-04-specification.md` |
| Phase 05 | `audits/code-audit-2026-03-02/phase-05-implementation.md` |
| Phase 06 | `audits/code-audit-2026-03-02/phase-06-code-review.md` |
| Phase 07 | `audits/code-audit-2026-03-02/phase-07-integration.md` |
| Phase 08 | `audits/code-audit-2026-03-02/phase-08-deployment.md` |
| Phase 09 | `audits/code-audit-2026-03-02/phase-09-release.md` |
| Orchestration | `audits/code-audit-2026-03-02/orchestration-modules.md` |
| Core | `audits/code-audit-2026-03-02/core-modules.md` |
