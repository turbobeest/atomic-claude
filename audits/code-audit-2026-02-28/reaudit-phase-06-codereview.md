# Re-Audit: Phase 06 Code Review
**Date:** 2026-02-28
**Auditor:** Claude Opus 4.6 (automated)
**Scope:** 7 files in phases/phase06/ and phases/phase_06_code_review/tasks/
**Criteria:** CRITICAL / HIGH / MEDIUM only. Each finding has a concrete trigger scenario.

---

## Audit Categories Applied
A-Data Integrity, B-Error Handling, C-Control Flow, D-Concurrency, E-Resource Management,
F-API Contract, G-Security, H-Configuration, I-Observability, J-Performance,
K-State Management, L-Input Validation, M-Boundary Conditions, N-Type Safety,
O-Compatibility, P-Idempotency, Q-Ordering/Timing, R-Business Logic

---

### [phases/phase06/orchestrator06.py] -- Audit

No actionable findings meeting CRITICAL/HIGH/MEDIUM criteria.

The orchestrator delegates to `run_phase_tasks` and task wrappers. The module-level `Path(os.getenv(...))` calls and `get_graph()` invocation follow established patterns across all orchestrators. The `graph` parameter is passed to tasks 604 and 605 correctly; tasks 601-603 and 606 do not need it.

---

### [phases/phase_06_code_review/tasks/task_601_entry_initialization.py] -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| F, N | MEDIUM | `_verify_phase_5` assumes `tasks_completed` is an integer and `total_tasks` / `tests` / `coverage` keys exist, but the actual closeout.json produced by `create_phase_closeout` in phase_runner.py stores `tasks_completed` as a **list of task ID strings** and omits `total_tasks`, `tests`, and `coverage` entirely. | 166-183 | Run Phase 5 to completion, then start Phase 6. `_find_closeout` resolves `.outputs/5-implementation/closeout.json` (the generic one from phase_runner). Line 181 prints `TDD cycles completed: ['501', '502', ...] / 0`. Lines 182-183 show `Tests passing: 0 / 0` and `Unit coverage: 0%` because those keys are absent. The Phase 5 gate at line 174 still passes (status is "complete"), so Phase 6 proceeds but with misleading verification output. | Read both closeout files (generic + Phase 5's own `phase-05-closeout.json`). Use `len(tasks_completed)` when the value is a list, and source test/coverage data from Phase 5's detailed closeout. |
| F, N | MEDIUM | Same `tasks_completed` list-vs-int issue in the `phase5_summary` written to `entry-context.json`. | 88-89 | Same trigger as above. `entry-context.json` stores `"tasks_completed": ["501", ...]` and `"total_tasks": 0`. Downstream consumers expecting an integer count get a list. | Normalize to integer count: `len(tasks_completed) if isinstance(tasks_completed, list) else tasks_completed`. |

---

### [phases/phase_06_code_review/tasks/task_602_agent_selection.py] -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| R | HIGH | Agent model tier selections are written to `review-agents.json` but **never consumed by task_603**. In the sequential path, `_deep_code_review` hardcodes `"sonnet"` (line 476) instead of opus, and `_performance_review` hardcodes `"haiku"` (line 498) instead of sonnet. In the TeamSession path, the model tier is not passed to the `claude --print` command at all (line 433). The user's model tier choices from task_602 are silently ignored. | 93-97 (task_602), 476, 487, 498, 509, 433 (task_603) | User selects agents interactively. Task 602 records `deep_code.model = "opus"` and `performance.model = "sonnet"`. Task 603 runs: deep code review uses sonnet instead of opus; performance review uses haiku instead of sonnet. User pays for cheaper models than selected, and critical deep-code review runs at lower capability than intended. | In task_603, load the model tier from `review-agents.json` and pass it to `_execute_review()` instead of hardcoding. For TeamSession path, include `--model` flag or equivalent in the `claude` command. |

---

### [phases/phase_06_code_review/tasks/task_603_comprehensive_review.py] -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| R | HIGH | (Cross-file: see task_602 finding above.) Sequential review functions hardcode model tiers that contradict the user's selection in task_602. `_deep_code_review` uses `"sonnet"` instead of the configured `"opus"`; `_performance_review` uses `"haiku"` instead of `"sonnet"`. | 476, 498 | User completes task_602 selecting opus for deep code review, then task_603 executes sequentially (TeamSession unavailable). Deep code review runs on sonnet, producing lower-quality analysis than the user configured. | Load agent config from `review-agents.json` and pass `model` to `_execute_review`. |
| M | MEDIUM | `_strip_json_fences` fails to extract JSON when ```` ```json ``` ```` appears as a **substring** mid-text (not at the start). The function uses `"```json" in stripped` (finds it anywhere) to locate the start, but then searches for the closing ```` ``` ```` from position `start` -- which may match a nested or early fence rather than the true closing fence. | 49-53 | LLM returns: `"Here is the review:\n```json\n{...}\n```\nAdditional notes: use ``` for code blocks"`. The closing fence search at line 52 finds the correct one, but if the LLM returns `"```json\n{...}\n```\nSee ```example```"`, the function works. However, if LLM returns `"Some preamble with ``` and then\n```json\n{...}\n```"`, the `"```json" in stripped` check finds it mid-text and correctly extracts. Actually problematic case: LLM returns `"```json\n{\"key\": \"value with ``` backticks\"}\n```"` -- line 52 finds the backticks inside the JSON string before the real closing fence, truncating the JSON and causing a `json.JSONDecodeError`. The fallback in `_execute_review` catches this and returns an empty result. | Use a more robust fence-stripping approach: find the last ```` ``` ```` for the closing fence, or use regex `r'```json\s*\n(.*?)\n```'` with `re.DOTALL`. |
| K | MEDIUM | UAT mode for task_603 does not create the prompt artifact files (`prompts/code-sample.txt`, `prompts/test-sample.txt`, `prompts/review-code.json`, etc.) that the orchestrator declares in `task_artifacts["603"]`. While the phase_runner artifact check is non-blocking, the `compute_task_score` function uses the mismatch between expected and actual artifacts to penalize the task's score, and `summarize_task_artifacts` returns empty content. | 93-124 (task_603), 108-110 (orchestrator06) | Run full pipeline in UAT mode. Task 603 succeeds but produces only 2 of 7 expected artifacts. Task score is penalized. Memory enrichment for this task has no artifacts to summarize. | In UAT mode, create stub prompt files (empty or minimal) to satisfy the artifact contract. |

---

### [phases/phase_06_code_review/tasks/task_604_refinement.py] -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| G | MEDIUM | `_resolve_source_path` accepts arbitrary `finding_file` strings from LLM-generated findings (via `finding.get('file')`) and constructs filesystem paths including `Path(finding_file)` as an absolute path candidate (line 348). If the LLM-generated finding contains a path like `/etc/passwd` or `../../../etc/shadow`, this path is used directly in `source_path.read_text()` (line 450) to extract context sent to another LLM call. While the read is not destructive, it enables the LLM-in-the-loop to exfiltrate arbitrary file contents into the fix prompt. | 341-353, 448-458 | LLM returns a finding with `"file": "/etc/passwd"`. `_resolve_source_path` returns `Path("/etc/passwd")`, which exists. `_apply_fix` reads its contents and embeds them in a prompt sent to the LLM. | Validate that resolved paths are within `project_root`. Add: `if not resolved.resolve().is_relative_to(project_root.resolve()): return None`. |
| B | MEDIUM | `_run_test_verification` silently reports "all tests passing" when no test runner is detected. When none of the test runner config files exist (no `Cargo.toml`, `package.json`, `go.mod`, `pytest.ini`, `pyproject.toml`), `result` stays `None`, `tests_passing` stays `True`, and the function displays "All tests passing after refinements" with 0 tests. | 517-591 | Project uses a test runner not detected by the heuristics (e.g., `Makefile`-based test suite, Ruby `Gemfile`, or C++ project). Task_604 reports "All tests passing" with zero tests verified, giving false confidence that refinements are safe. The refinement report records `"all_passing": True`. | When `result is None` and no test command ran, set `tests_passing` to a distinct "unknown" state and display a warning instead of a green checkmark. |

---

### [phases/phase_06_code_review/tasks/task_605_phase_audit.py] -- Audit

No actionable findings meeting CRITICAL/HIGH/MEDIUM criteria.

This is a thin wrapper around `run_phase_audit` with correct non-blocking behavior. The phase number extraction from `output_dir.name` handles the expected `6-code-review` format correctly.

---

### [phases/phase_06_code_review/tasks/task_606_closeout.py] -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| K | MEDIUM | `_check_review_items` at line 146 checks `metrics["critical_fixed"] >= metrics["critical_found"]` to determine if all critical issues are resolved. If both values are 0 (no findings file, or no critical issues found), this passes as "all critical issues resolved" -- which is correct. However, if the refinement step was **skipped** (user chose "skip" scope in task_604), `refinement-report.json` does not exist, so `metrics["critical_fixed"]` defaults to 0 while `metrics["critical_found"]` may be > 0. The closeout correctly flags this as FAIL. **The actual issue:** if refinement was skipped and there ARE critical findings, the user is blocked from closeout even though they chose to skip refinement. The only escape is the "approve" override. | 146-152, 253-265 | Task 603 finds 2 critical issues. User skips refinement in task 604. Task 606 runs closeout checklist: `critical_fixed=0, critical_found=2` -- FAIL. User must explicitly type "approve" to override. This is arguably correct gating behavior, not a bug, but the UX doesn't explain why closeout is blocked after the user themselves chose to skip. | Add a message explaining that critical issues from the review are unresolved because refinement was skipped, and suggest re-running task 604. |

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 2 |
| MEDIUM | 7 |

**HIGH findings (2):**
1. **Agent model tier ignored (task_602 + task_603):** User-selected model tiers from task_602 are never passed to task_603's review execution. Deep code review runs on sonnet instead of opus; performance review runs on haiku instead of sonnet. Both sequential and TeamSession paths are affected.

**MEDIUM findings (7):**
1. **task_601:** `_verify_phase_5` assumes `tasks_completed` is an int but gets a list from phase_runner's generic closeout.json, causing garbled display output.
2. **task_601:** Same list-vs-int issue propagated into `entry-context.json`.
3. **task_603:** `_strip_json_fences` can mis-parse when JSON content contains triple-backtick sequences, though fallback handling prevents crashes.
4. **task_603:** UAT mode missing 5 of 7 expected prompt artifacts, penalizing task score and memory enrichment.
5. **task_604:** `_resolve_source_path` allows LLM-controlled arbitrary file reads outside project boundary.
6. **task_604:** `_run_test_verification` reports "all tests passing" when no test runner is detected (0 tests run).
7. **task_606:** Closeout blocks on unresolved critical issues after user explicitly skipped refinement, without explaining the connection.

Note: The 2 HIGH findings are the same root cause (model tier not propagated from task_602 to task_603) manifesting in two files.
