# Re-Audit 2: Phase 04 Specification
**Date:** 2026-02-28
**Auditor:** Claude Opus 4.6 (automated)
**Scope:** 7 files in Phase 04 (Specification) pipeline
**Criteria:** CRITICAL / HIGH / MEDIUM only. Each finding requires a specific, reproducible trigger scenario. Previously-fixed issues are not re-reported.

---

## Previous Findings Status

From reaudit-phase-04-specification.md (4 findings):

| # | Severity | File | Finding | Status |
|---|----------|------|---------|--------|
| 1 | HIGH | task_403 | Missing LLM router warmup before parallel spec generation | **STILL OPEN** |
| 2 | HIGH | task_403 | Invalid specs miscounted as generated | **FIXED** -- line 374 now excludes `"invalid"` from generated count |
| 3 | MEDIUM | task_402 | Roster metadata records `task_count: 0` when analysis fails | **FIXED** -- fallback block at lines 218-226 re-reads tasks.json; additionally `task_count` is purely informational metadata not consumed by any downstream logic |
| 4 | MEDIUM | task_406 | Double-read TOCTOU on tasks_file | **FIXED** -- `tasks_data` is now passed as kwarg to `check_closeout_items` (line 359) |

---

## Files Audited

1. `phases/phase04/orchestrator04.py`
2. `phases/phase_04_specification/tasks/task_401_entry_initialization.py`
3. `phases/phase_04_specification/tasks/task_402_agent_selection.py`
4. `phases/phase_04_specification/tasks/task_403_openspec_generation.py`
5. `phases/phase_04_specification/tasks/task_404_tdd_subtask_injection.py`
6. `phases/phase_04_specification/tasks/task_405_phase_audit.py`
7. `phases/phase_04_specification/tasks/task_406_closeout.py`

---

### orchestrator04.py

No actionable findings. Wrapper functions correctly forward `(mem, graph)` to task `execute()` with the `(atomic_root, output_dir, uat_mode, mem, graph)` signature. Module-level constants resolve paths correctly.

---

### task_401_entry_initialization.py

No actionable findings. Phase 3 verification logic is correct. The `task_count` variable from the first read (line 107) is used on line 154 but by that point the same file was re-read (line 147) and the fresh `tasks` list is the source of priority counts. While `task_count` could theoretically be stale, the guard on lines 134-139 returns False if verification failed, and in the success path the same file was just verified as parseable. No runtime impact.

---

### task_402_agent_selection.py

No actionable findings. The previous finding about `task_count: 0` in roster metadata has been addressed by the fallback block (lines 218-226), and the `task_count` field in `agent-roster.json` is purely informational metadata with no downstream behavioral consumers.

---

### task_403_openspec_generation.py

| # | Cat | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|---|-----|----------|---------|---------|------------------|----------------|
| 1 | J (Concurrency) | **HIGH** | Missing LLM router warmup before parallel spec generation causes race condition | 467-472 | In normal (non-UAT) mode, `execute()` imports `invoke_llm` then immediately calls `_run_parallel_specs()` which spawns up to 5 threads via `ThreadPoolExecutor`, each calling `invoke_llm`. The `_get_default_router()` singleton has a documented race condition (acknowledged in task_404 lines 559-562): it sets the global `_default_router` variable before registering providers, so concurrent threads that call `invoke_llm` during that window see a router with no providers. This raises `RuntimeError("No LLM provider available")` in affected threads. Because `_spec_worker` catches all exceptions (line 286) and falls back to a stub spec, the failure is silent -- the user sees specs marked "ok" but some are actually generic stubs. The identical fix already exists in task_404 (main-thread warmup call, lines 563-566) but was never ported to task_403. | Add an LLM warmup call before `_run_parallel_specs`, identical to task_404 lines 563-566: `print(print_dim("  Warming up LLM provider...")); invoke_llm(prompt="Reply with OK", model="haiku", timeout=30); print(print_green("  ✓ LLM provider ready"))`. |
| 2 | M (LLM Integration) | **MEDIUM** | Unescaped `task_title` in JSON template within LLM prompt produces malformed example JSON | 226 | A task created in Phase 3 has a title containing double quotes, e.g. `Configure "primary" database connection`. The `_build_spec_prompt` function interpolates `task_title` directly into a JSON template string: `"task_title": "{task_title}"`. This produces `"task_title": "Configure "primary" database connection"` in the prompt -- syntactically invalid JSON in the example. The LLM may then produce structurally malformed JSON output, which fails validation in `_spec_worker` (line 277), causing the spec file to be deleted (line 282) and the task to have no spec. Downstream, task_404 falls back to generic TDD subtasks for that task. | Use `json.dumps(task_title)` to produce a properly escaped string: `"task_title": {json.dumps(task_title)},`. Apply the same treatment to `task_desc` and `acceptance` which are also interpolated into the template region. |

---

### task_404_tdd_subtask_injection.py

No actionable findings. The LLM router race condition is properly mitigated with a main-thread warmup (lines 559-566). JSON parsing uses multiple fallback strategies with `copy.deepcopy` at all call sites to handle the `_validate_subtasks` mutation. Atomic file writes using `tempfile.mkstemp` + `os.replace` are correct. The `_parse_tdd_response` function handles raw JSON, fenced JSON, and embedded JSON arrays.

---

### task_405_phase_audit.py

No actionable findings. The audit is non-blocking by design (always returns True). Phase number extraction from `output_dir.name` handles the expected `N-name` format correctly. Import failures for the audit graph are caught and skipped gracefully.

---

### task_406_closeout.py

No actionable findings. The previous TOCTOU finding has been fixed -- `tasks_data` is now loaded once (line 347) and passed to both `check_closeout_items` (line 359, via `tasks_data=tasks_data`) and `generate_closeout_documents` (line 409, via `tasks_data=tasks_data`). Spec file list is cached (line 344) and reused. Closeout timestamp is captured once (line 341) for consistency.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH     | 1 |
| MEDIUM   | 1 |

**Total actionable findings: 2**

### HIGH (1):
1. **task_403, lines 467-472**: Missing LLM router warmup before parallel `ThreadPoolExecutor` execution causes a race condition in `_get_default_router()`. Threads may see an uninitialized router and silently fall back to stub specs. The fix exists in task_404 but was never applied to task_403. *This is a carry-forward from the previous reaudit and remains unfixed.*

### MEDIUM (1):
1. **task_403, line 226**: Unescaped `task_title` (and other task fields) interpolated directly into a JSON template within the LLM prompt. Task titles containing double quotes produce malformed JSON in the prompt example, which can cause the LLM to generate unparseable output, resulting in deleted spec files and missing specifications.

### Previously reported findings now fixed (3 of 4):
- task_403 invalid spec counting (line 374 now correctly excludes "invalid")
- task_402 roster task_count (fallback block added; field is informational only)
- task_406 TOCTOU double-read (tasks_data now passed as parameter)
