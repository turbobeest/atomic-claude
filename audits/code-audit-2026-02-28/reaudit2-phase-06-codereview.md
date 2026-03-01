# Re-Audit #2: Phase 06 Code Review
**Date:** 2026-02-28
**Auditor:** Claude Opus 4.6 (automated)
**Scope:** 7 files in phases/phase06/ and phases/phase_06_code_review/tasks/
**Criteria:** CRITICAL / HIGH / MEDIUM only. Each finding has a concrete trigger scenario.
**Prior audit:** reaudit-phase-06-codereview.md (same date)

---

## Audit Categories Applied
A-Data Integrity, B-Error Handling, C-Control Flow, D-Concurrency, E-Resource Management,
F-API Contract, G-Security, H-Configuration, I-Observability, J-Performance,
K-State Management, L-Input Validation, M-Boundary Conditions, N-Type Safety,
O-Compatibility, P-Idempotency, Q-Ordering/Timing, R-Business Logic

---

## Fixes Verified Since Prior Audit

The following prior-audit findings have been confirmed **FIXED** and are excluded from this report:

1. **HIGH (task_602 + task_603, sequential path):** Agent model tier selections from task_602 are now passed to review functions in the sequential code path. Lines 161-164 of task_603 now use `model=agents.get("deep_model", "sonnet")` etc., and `_load_agents` (lines 189-193) reads model tiers from `review-agents.json`.

2. **MEDIUM (task_601, line 181):** `_verify_phase_5` display now handles list-vs-int for `tasks_completed` via `len(tasks_completed) if isinstance(tasks_completed, list) else tasks_completed`.

3. **MEDIUM (task_604, lines 350-352):** `_resolve_source_path` now validates that resolved paths are within `project_root` using `resolved.is_relative_to(project_root.resolve())`, preventing LLM-controlled arbitrary file reads.

---

### [phases/phase06/orchestrator06.py] -- Audit

No actionable findings meeting CRITICAL/HIGH/MEDIUM criteria.

---

### [phases/phase_06_code_review/tasks/task_601_entry_initialization.py] -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| F, N | MEDIUM | `entry-context.json` still stores raw `tasks_completed` value from Phase 5 closeout without normalizing. While the display (line 181) was fixed to handle list-vs-int, the data written to `entry-context.json` at line 88 still passes through the raw value: `"tasks_completed": phase5_data.get("tasks_completed", 0)`. When Phase 5's closeout.json stores `tasks_completed` as a list (e.g., `["501", "502", "503"]`), this list is written directly to entry-context.json. | 88 | Run Phase 5 to completion (phase_runner creates closeout.json with `tasks_completed` as a list of task IDs). Start Phase 6. The `entry-context.json` written at line 94 contains `"tasks_completed": ["501", "502", ...]` and `"total_tasks": 0`. Any downstream consumer parsing entry-context.json expecting an integer count gets a list. | Normalize: `"tasks_completed": len(tc) if isinstance(tc, list) else tc` where `tc = phase5_data.get("tasks_completed", 0)`. |

---

### [phases/phase_06_code_review/tasks/task_602_agent_selection.py] -- Audit

No actionable findings meeting CRITICAL/HIGH/MEDIUM criteria.

---

### [phases/phase_06_code_review/tasks/task_603_comprehensive_review.py] -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| R | HIGH | **TeamSession path ignores user-selected model tiers.** The sequential path was fixed to pass model tiers (lines 161-164), but `_run_team_session_review` at line 438 still launches `cat {prompt} \| claude --print` without any `--model` flag. All four review dimensions run on `claude`'s default model regardless of the tier selections made in task_602 (e.g., opus for deep code review, sonnet for architecture). The `agents` dict containing model tiers is passed into the function but never consumed for model selection. | 438 | TeamSession is available (tmux installed). User selects opus for deep code review in task_602. Task_603 takes the TeamSession path (line 155). The `claude --print` command uses whatever the default model is rather than opus. Deep code review runs at a different capability level than the user configured. | Add model flag to the command: `f"cat {shlex.quote(str(prompt_file))} \| claude --print --model {agents.get(dim_key + '_model', 'sonnet')}"`. Alternatively, map dim_key to the correct model key in the dimensions dict and include it in the command construction loop. |
| M | MEDIUM | `_discover_review_scope` at line 234 uses substring matching `"test" in f.stem.lower()` to exclude test files from the source file list. This false-positives on any source file whose stem contains "test" as a substring, such as `contest.py`, `attest.py`, `latest_data.rs`, `testimony.js`, or `context_helper.py`. These legitimate source files are silently excluded from code review. | 234 | Host project has a source file named `contest.py` or `context_manager.py` in `src/`. The substring check `"test" in "contest"` evaluates to True, so the file is skipped from source review. It is also not picked up by test discovery (patterns `*.test.*`, `*_test.*`, `test_*` don't match `contest.py`), so the file is reviewed by neither path. | Use a more precise check: `f.stem.lower().startswith("test_") or f.stem.lower().endswith("_test") or ".test." in f.name.lower()` to match conventional test file naming patterns without false-positiving on substring matches. |
| K | MEDIUM | **UAT mode missing prompt artifact files** (not fixed from prior audit). UAT mode creates only `review-report.md` and `findings.json` but does not create the 6 prompt files declared in `task_artifacts["603"]`: `prompts/code-sample.txt`, `prompts/test-sample.txt`, `prompts/review-code.json`, `prompts/review-arch.json`, `prompts/review-perf.json`, `prompts/review-doc.json`. | 93-124 (task_603), 108-110 (orchestrator06) | Run full pipeline in UAT mode (`ATOMIC_UAT_MODE=true`). Task 603 succeeds but produces only 1 of 7 expected artifacts (review-report.md; findings.json is written outside output_dir). `compute_task_score` computes artifact ratio as 1/7 = 0.14, yielding a bonus of only 0.036 instead of the full 0.25. Memory enrichment via `summarize_task_artifacts` has only 1 artifact to summarize. | In UAT mode, create minimal stub files for each expected artifact (e.g., empty JSON `{}` for review files, empty text for sample files). |

---

### [phases/phase_06_code_review/tasks/task_604_refinement.py] -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| B, K | MEDIUM | **`_run_test_verification` returns `tests_passing=True` when no test runner is detected** (not fixed from prior audit). When none of the test runner config files exist (`Cargo.toml`, `package.json`, `go.mod`, `pytest.ini`, `pyproject.toml`), `result` stays `None` and `tests_passing` stays `True` (initialized at line 520). The terminal displays a yellow warning (lines 585-586), but the returned tuple `(True, 0, 0)` records `tests_passing=True` in the refinement report JSON. Task_606 then reads this and reports "All tests passing after refinements" in the closeout. | 520, 584-597 | Host project uses a Makefile-based test suite, Ruby Gemfile, or C++ CMake project. No config file matches any detector. Task_604 reports `"all_passing": True` with 0 tests verified. Task_606 closeout shows tests passing. The closeout JSON and markdown both record a false positive. | When `result is None`, set `tests_passing = True` only if `tests_total == 0` is acceptable, or better: return a tri-state (True/False/None) and have task_606 treat None as "unverified" rather than "passed". |

---

### [phases/phase_06_code_review/tasks/task_605_phase_audit.py] -- Audit

No actionable findings meeting CRITICAL/HIGH/MEDIUM criteria.

---

### [phases/phase_06_code_review/tasks/task_606_closeout.py] -- Audit

No new actionable findings meeting CRITICAL/HIGH/MEDIUM criteria.

The prior-audit finding about closeout blocking after refinement skip without explanation (MEDIUM) remains unfixed but is not re-reported here as it was characterized as borderline gating behavior in the prior audit.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 4 |

**0 critical, 1 high, 4 medium.**

**HIGH finding (1):**
1. **TeamSession path ignores model tiers (task_603, line 438):** When TeamSession is available, `claude --print` is invoked without a `--model` flag, so all four review dimensions run on the default model instead of the user-selected tiers from task_602. The sequential path was fixed but the parallel path was not.

**MEDIUM findings (4):**
1. **task_601, line 88:** `entry-context.json` still writes raw `tasks_completed` value (could be a list) without normalizing to integer count. Display was fixed but persisted data was not.
2. **task_603, line 234:** Substring check `"test" in f.stem.lower()` false-positives on source files containing "test" as a substring (e.g., `contest.py`, `context_helper.py`), silently excluding them from code review.
3. **task_603, lines 93-124:** UAT mode still does not create the 6 prompt artifact files expected by the orchestrator, degrading task scoring and memory enrichment.
4. **task_604, lines 520/597:** `_run_test_verification` returns `tests_passing=True` when no test runner is detected, causing false positive test verification in refinement and closeout reports.

**Previously reported findings now fixed (3):**
- HIGH: Sequential model tier passthrough (task_602 -> task_603) -- FIXED
- MEDIUM: `_verify_phase_5` list-vs-int display -- FIXED
- MEDIUM: `_resolve_source_path` arbitrary file read outside project boundary -- FIXED
