# Re-Audit: Phase 04 Specification
**Date:** 2026-02-28
**Auditor:** Claude Opus 4.6 (automated)
**Scope:** 7 files in Phase 04 (Specification) pipeline
**Criteria:** CRITICAL / HIGH / MEDIUM only. Each finding requires a specific, reproducible trigger scenario.

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

### [phases/phase04/orchestrator04.py] -- Audit

No actionable findings. The orchestrator correctly delegates to `run_phase_tasks`, wrapper functions have compatible signatures with the phase runner's calling convention (positional `mem`, keyword `graph`), and module-level path resolution is sound.

---

### [phases/phase_04_specification/tasks/task_401_entry_initialization.py] -- Audit

No actionable findings. Phase 3 verification logic is correct. UAT bypass path writes valid initialization JSON. Interactive path validates tasks.json before proceeding and re-reads it for the summary display.

---

### [phases/phase_04_specification/tasks/task_402_agent_selection.py] -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| D (Data flow) | MEDIUM | `task_count` in roster metadata is 0 when `analyze_project_characteristics()` fails | 96, 231, 337 | `tasks.json` exists but has a JSON decode error (e.g., trailing comma from manual edit). `analyze_project_characteristics` catches the exception and returns `{}`. `task_count = characteristics.get('task_count', 0)` yields 0. The saved `agent-roster.json` records `"task_count": 0` despite tasks existing on disk. Downstream consumers of the roster that rely on `task_count` would see incorrect data. | Either re-read `tasks_file` directly in `execute()` for the count, or propagate the error from `analyze_project_characteristics` instead of swallowing it and returning `{}`. |

---

### [phases/phase_04_specification/tasks/task_403_openspec_generation.py] -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| J (Concurrency) | HIGH | Missing LLM router warmup before parallel spec generation causes race condition | 467-472 | In normal (non-UAT) mode, `execute()` imports `invoke_llm` then immediately calls `_run_parallel_specs()` which spawns up to 5 threads, each calling `invoke_llm`. The `_get_default_router()` singleton has a documented race condition (acknowledged in task_404 lines 559-562): it sets the global `_default_router` before registering providers, so concurrent threads may see an empty router. This causes `RuntimeError("No LLM provider available")` in some threads, which fall back to stub specs. The fix already exists in task_404 (a main-thread warmup call) but was not applied here. | Add an LLM warmup call before `_run_parallel_specs`, identical to task_404 lines 563-566: `invoke_llm(prompt="Reply with OK", model="haiku", timeout=30)`. |
| D (Data flow) | HIGH | Generation report counts invalid specs as successfully generated | 374-376 | LLM returns malformed JSON for a spec (common with frontier models). `_spec_worker` detects the invalid JSON, deletes the spec file, and returns status `"invalid"`. In `_run_parallel_specs`, line 374 counts all non-None results as `generated`, and line 375 only counts `"stub"` as `failed`. So `"invalid"` results are counted as generated but have no file on disk. The report says e.g. "10/10 specs created, 0 failed" when 2 specs were deleted. Downstream task_404 finds missing specs and falls back to generic subtasks without explanation. | Change line 374 to: `generated = sum(1 for r in results if r and r[1] == "ok")`. Add a separate `invalid` counter: `invalid = sum(1 for r in results if r and r[1] == "invalid")`. Include `invalid` in the returned tuple and the generation report. |

---

### [phases/phase_04_specification/tasks/task_404_tdd_subtask_injection.py] -- Audit

No actionable findings. The LLM router race condition is properly mitigated with a main-thread warmup (lines 559-566). JSON parsing has multiple fallback strategies. Atomic file writes using `tempfile.mkstemp` + `os.replace` are correct. The `_validate_subtasks` mutation concern is handled via `copy.deepcopy` at all call sites.

---

### [phases/phase_04_specification/tasks/task_405_phase_audit.py] -- Audit

No actionable findings. The audit is non-blocking by design (always returns True). Phase number extraction from `output_dir.name` handles the expected format correctly. Import failures for the audit graph are caught and skipped gracefully.

---

### [phases/phase_04_specification/tasks/task_406_closeout.py] -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| D (Data flow) | MEDIUM | `check_closeout_items()` re-reads `tasks_file` from disk, ignoring the `tasks_data` already loaded at line 339 | 339, 351, 41 | In the non-UAT path, `execute()` loads `tasks_data` at line 339, then calls `check_closeout_items(tasks_file, ...)` at line 351, which independently calls `read_file(tasks_file)` again at line 41. If another process modifies `tasks.json` between the two reads (e.g., a concurrent phase runner or manual edit), `check_closeout_items` and `generate_closeout_documents` operate on different snapshots of the data. The checklist could report metrics that disagree with the closeout document. | Pass `tasks_data` to `check_closeout_items()` instead of having it re-read from disk, consistent with how `generate_closeout_documents()` already accepts a `tasks_data` parameter. |

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH     | 2 |
| MEDIUM   | 2 |

**Total actionable findings: 4**

### HIGH findings (2):
1. **task_403**: Missing LLM router warmup before parallel execution causes intermittent thread failures and silent fallback to stub specs. Fix exists in task_404 but was not ported.
2. **task_403**: Invalid spec results miscounted as successful in generation report, producing misleading output and masking spec generation failures.

### MEDIUM findings (2):
1. **task_402**: Roster metadata records `task_count: 0` when task analysis fails, producing incorrect agent-roster.json.
2. **task_406**: Double-read of `tasks_file` creates a TOCTOU window where checklist and closeout document can disagree on task state.
