# Code Audit: Phase 03 Tasking (Re-audit)

**Date:** 2026-02-28
**Auditor:** Claude Opus 4.6
**Scope:** 7 files in Phase 03 Tasking pipeline
**Criteria:** CRITICAL / HIGH / MEDIUM only (strict severity gate)

---

## File Audits

---

### phases/phase03/orchestrator03.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|

**No actionable findings.** The orchestrator delegates all work to `run_phase_tasks` and the individual task wrapper functions. The wrapper signatures `(mem=None, graph=None)` are compatible with both `task_func(mem)` and `task_func(mem, graph=graph)` call patterns in `phase_runner.py`. Module-level `Path.cwd()` default for `ATOMIC_ROOT` is consistent with other orchestrators.

---

### phases/phase_03_tasking/tasks/task_301_entry_initialization.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|

**No actionable findings.** The entry validation, TaskMaster initialization, and env-var writing logic is sound. The `_append_env_vars` function correctly guards against appending duplicate keys and the comment-only early return (line 487) prevents orphan comments. The `_ensure_env_gitignored` function correctly checks for `.env` in `.gitignore` before writing secrets. Provider configuration cascades (Bedrock -> Anthropic -> Ollama) are correct.

---

### phases/phase_03_tasking/tasks/task_302_agent_selection.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|

**No actionable findings.** The PRD analysis uses safe regex patterns with proper flags. Agent selection handles all interactive paths (approve/core/custom) correctly. The custom selection with index validation (line 349-350) is bounds-checked. Analysis and selection data are saved atomically.

---

### phases/phase_03_tasking/tasks/task_303_task_decomposition.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| O (data handling) | HIGH | `_repair_json` fails to extract valid JSON when LLM output has trailing text after the JSON object. The second repair path (line 768-769) takes `content[start:]` from first `{` to end-of-string. If the LLM emits `{...valid json...}\nSome trailing explanation`, `json.loads()` fails on the trailing text and repair returns `False`, causing unnecessary fallback to template tasks with only 3 generic tasks. | 766-778 | LLM returns valid JSON followed by any trailing text (common LLM behavior: explanation, notes, or whitespace with non-JSON characters). Per-feature decomposition produces valid task JSON but with trailing commentary -- all feature results for that feature are lost and template fallback may trigger. | Change line 769 to find the last matching `}`: `end = content.rindex("}") + 1; json_content = content[start:end]`. This handles the common case of trailing text after the JSON object. |
| O (data handling) | MEDIUM | `_merge_feature_tasks` dependency remapping silently drops cross-feature dependencies with no tracking or warning. When a task in feature A depends on a task in feature B, the dependency is silently removed (line 462 comment says "leave for task 304 dependency mapper"). However, task 304 does not re-discover cross-feature dependencies -- it only validates what is present. The task ends up with fewer dependencies than intended. | 454-463 | PRD has features with cross-feature dependencies (e.g., F2's authentication tasks depend on F1's database setup). Per-feature LLM calls may emit dependencies referencing IDs from another feature's numbering scheme. These are silently dropped, producing a DAG with missing edges. | Log dropped cross-feature dependencies as warnings. Alternatively, preserve them as metadata (e.g., `"unresolved_dependencies"`) so task 304 or the user can address them. |

---

### phases/phase_03_tasking/tasks/task_304_dependency_analysis.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| O (data handling) | MEDIUM | UAT mode writes `dependency-analysis.json` with schema `{"validation": "pass", ...}` where `"validation"` is a string. Task 306 `_run_checklist` reads it with `analysis.get("validation", {}).get("passed", False)`, calling `.get()` on a string, which raises `AttributeError`. The try/except catches this and reports "Dependency analysis invalid" -- a false negative in the closeout checklist. | 61-67 (task_304), 205-206 (task_306) | Run task 304 in UAT mode, then run task 306 in non-UAT mode (e.g., resume with `ATOMIC_UAT_MODE` toggled off, or a partial re-run). The closeout checklist will incorrectly report dependency analysis as invalid even though it passed. | Change UAT mode analysis data to match the expected schema: `{"validation": {"passed": True, "cycles": False, "invalid_refs": 0}, "mode": "uat"}`. |

---

### phases/phase_03_tasking/tasks/task_305_phase_audit.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|

**No actionable findings.** The audit task is a thin wrapper around `core.audit.run_phase_audit`. It correctly extracts the phase number from the output directory name and handles errors gracefully. The task is intentionally non-blocking (always returns True), which is documented behavior.

---

### phases/phase_03_tasking/tasks/task_306_closeout.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|

**No actionable findings.** The closeout logic is sound. The cross-file schema mismatch with task_304 UAT data is documented above under the task_304 finding. Within task_306 itself, all checklist checks are properly guarded with try/except, metrics gathering handles missing files gracefully, and the markdown/JSON closeout generation is correct.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH     | 1 |
| MEDIUM   | 2 |
| **Total** | **3** |

### Finding Index

1. **HIGH** -- `task_303_task_decomposition.py` `_repair_json`: Fails to extract valid JSON when LLM output has trailing text, causing unnecessary fallback to 3-task template. (Lines 766-778)
2. **MEDIUM** -- `task_303_task_decomposition.py` `_merge_feature_tasks`: Cross-feature dependencies silently dropped with no warning or tracking. (Lines 454-463)
3. **MEDIUM** -- `task_304_dependency_analysis.py` UAT mode writes `dependency-analysis.json` with incompatible schema vs. what `task_306_closeout.py` `_run_checklist` expects, causing false-negative "invalid" report on mixed-mode resume. (Lines 61-67 in task_304, Lines 205-206 in task_306)
