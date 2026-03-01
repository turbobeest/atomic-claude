# Re-Audit 3: Phase 04 (Specification) + Phase 05 (Implementation)
**Date:** 2026-02-28
**Auditor:** Claude Opus 4.6 (automated)
**Scope:** 15 files across Phase 04 and Phase 05
**Criteria:** CRITICAL / HIGH / MEDIUM only. Every finding requires a specific, reproducible trigger scenario. Previously-fixed issues not re-reported. Style, missing tests, and hypothetical concerns excluded.

---

## Previous Findings Status (from reaudit2)

### Phase 04 (reaudit2-phase-04-specification.md, 2 findings):

| # | Severity | File | Finding | Status |
|---|----------|------|---------|--------|
| 1 | HIGH | task_403 lines 467-472 | Missing LLM router warmup before parallel spec generation | **FIXED** -- Warmup call now present at lines 470-475 with comment "Warmup: force router initialization on the main thread before spawning parallel workers (prevents TOCTOU race on singleton init)." The exception is silenced with `pass` rather than logged, but the warmup call is functionally equivalent to the one in task_404. |
| 2 | MEDIUM | task_403 line 226 | Unescaped `task_title` in JSON template | **FIXED** -- Line 222 now uses `json.dumps(task_title)` to properly escape the title in the JSON template. |

### Phase 05 (reaudit2-phase-05-implementation.md, 2 findings):

| # | Severity | File | Finding | Status |
|---|----------|------|---------|--------|
| 1 | MEDIUM | task_504 lines 1877-1880 | Pilot run cycle counts lost in final progress stats | **FIXED** -- Lines 2457-2462 now add pilot cycle counts (`pilot_red`, `pilot_green`, `pilot_refactor`, `pilot_verify`) back to `stats` after `_run_dag_parallel` returns. |
| 2 | MEDIUM | task_504 lines 928, 1229, 1361 | Test execution commands for Python/Node do not quote file paths | **FIXED** -- All three locations now use `shlex.quote(str(test_file))`: line 928 (RED), line 1229 (GREEN), line 1361 (REFACTOR). |

---

## Files Audited

### Phase 04:
1. `phases/phase04/orchestrator04.py`
2. `phases/phase_04_specification/tasks/task_401_entry_initialization.py`
3. `phases/phase_04_specification/tasks/task_402_agent_selection.py`
4. `phases/phase_04_specification/tasks/task_403_openspec_generation.py`
5. `phases/phase_04_specification/tasks/task_404_tdd_subtask_injection.py`
6. `phases/phase_04_specification/tasks/task_405_phase_audit.py`
7. `phases/phase_04_specification/tasks/task_406_closeout.py`

### Phase 05:
8. `phases/phase05/orchestrator05.py`
9. `phases/phase_05_implementation/tasks/task_501_entry_initialization.py`
10. `phases/phase_05_implementation/tasks/task_502_tdd_setup.py`
11. `phases/phase_05_implementation/tasks/task_503_agent_selection.py`
12. `phases/phase_05_implementation/tasks/task_504_tdd_execution.py`
13. `phases/phase_05_implementation/tasks/task_505_validation.py`
14. `phases/phase_05_implementation/tasks/task_506_phase_audit.py`
15. `phases/phase_05_implementation/tasks/task_507_closeout.py`

---

## Audit Categories Applied (A-R)

A. Error Handling | B. Input Validation | C. State Management | D. Concurrency/Threading
E. Resource Management | F. Data Integrity | G. Security | H. API Contract
I. Path/File Operations | J. Type Safety | K. Logic Errors | L. Configuration
M. Performance | N. Dependency Management | O. Serialization | P. Boundary Conditions
Q. Observability | R. Recovery/Resilience

---

## Phase 04 Findings

### orchestrator04.py

No actionable findings. Wrapper functions correctly forward `(mem, graph)` parameters to task `execute()` functions. Module-level constant paths are correctly derived. The `get_graph()` call with `ensure_schema()` at lines 59-60 properly initializes the knowledge graph before task execution.

---

### task_401_entry_initialization.py

No actionable findings. Phase 3 verification is structurally sound. The `task_count` variable from the initial read (line 107) is used on line 154 for display only; by that point, the file was re-read at line 147 and the fresh `tasks` list is used for priority breakdowns. The user prompt for existing specs (keep/replace/abort) handles all branches correctly.

---

### task_402_agent_selection.py

No actionable findings. The fallback block at lines 218-226 handles the case where `analyze_project_characteristics()` returns an empty dict. The `task_count` field in roster metadata is informational only. CSV parsing has appropriate error handling. The infinite input loop has proper break conditions on all branches.

---

### task_403_openspec_generation.py

No actionable findings. All previously-reported findings have been fixed:
- LLM router warmup is present at lines 470-475 (prevents TOCTOU race in ThreadPoolExecutor workers).
- `task_title` is now properly escaped with `json.dumps()` at line 222.
- Invalid specs are correctly excluded from the generated count at line 374.

---

### task_404_tdd_subtask_injection.py

No actionable findings. The LLM router warmup is properly implemented (lines 559-566). JSON parsing uses multiple fallback strategies with `copy.deepcopy` to handle `_validate_subtasks` mutation. Atomic file writes using `tempfile.mkstemp` + `os.replace` are correct. The `_parse_tdd_response` function handles raw JSON, fenced JSON, and embedded JSON arrays robustly.

---

### task_405_phase_audit.py

No actionable findings. Non-blocking by design (always returns `True`). Phase number extraction from `output_dir.name` handles the expected `N-name` format. Import failures for the audit graph are caught and skipped gracefully.

---

### task_406_closeout.py

No actionable findings. The previous TOCTOU fix is in place: `tasks_data` is loaded once (line 347) and passed as a kwarg to both `check_closeout_items` (line 359) and `generate_closeout_documents` (line 409). Spec files are cached (line 344). Closeout timestamp is captured once (line 341) for consistency.

---

## Phase 05 Findings

### orchestrator05.py

No actionable findings. The orchestrator does not initialize a knowledge graph (unlike orchestrator04), but this is by design: task_504 initializes its own graph internally at lines 2213-2217, and task_506's `graph` parameter is accepted for interface compatibility only (the audit task loads its own audit graph internally).

---

### task_501_entry_initialization.py

No actionable findings. Phase 4 verification logic correctly checks for the closeout file, TDD subtasks in tasks.json, and OpenSpec files in `.openspec/` with a fallback to `.claude/specs/`. The `read_json` helper is used consistently instead of raw `json.loads(read_file(...))`.

---

### task_502_tdd_setup.py

No actionable findings. The cascading tech stack detection (`detect_tech_stack_cascade`) is well-structured with 4 strategies and clear confidence thresholds. User input for coverage targets, pyramid profiles, and budget uses `try/except` for int/float parsing with appropriate defaults. `subprocess.run` calls use timeouts. The `detect_cpu_count` function handles cross-platform and container edge cases.

---

### task_503_agent_selection.py

No actionable findings. Agent selection is a UI task that writes well-structured JSON. CSV reading has exception handling. Pattern analysis is read-only against spec files. The `get_csv_model` function returns a static default which is appropriate given the agent-inventory.csv has no model column.

---

### task_504_tdd_execution.py

| # | Cat | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|---|-----|----------|---------|---------|------------------|----------------|
| 1 | I (Path/File Ops) | **MEDIUM** | VERIFY phase `verify_cmd` does not quote `impl_file` path | 1444 | `verify_cmd_template` is `"python -m py_compile {impl_file}"` (line 75). At line 1444, `verify_cmd = verify_cmd_template.format(impl_file=impl_file)` inserts the raw `Path` object without shell quoting. When the project root contains spaces (e.g., `/home/user/My Projects/myapp/`), `impl_file` resolves to a path with spaces. The resulting command `python -m py_compile /home/user/My Projects/myapp/.claude/testing/task-1/task_1_impl.py` splits at the space in the shell, causing a "No such file or directory" error. This affects Python, Node, and Go stack profiles (all use `{impl_file}` in their `verify_cmd` templates). The RED, GREEN, and REFACTOR phases were fixed in the previous audit, but the VERIFY phase was missed. The same issue exists for the gate commands in `STACK_PROFILES["python"]["gates"]["verify"]` (line 86: `"python -m py_compile {impl_file}"`), though `_run_gate` is only called for bootstrap tasks in the VERIFY phase (line 1420). | Change line 1444 to: `verify_cmd = verify_cmd_template.format(impl_file=shlex.quote(str(impl_file)))`. Also update the `gates` templates in `STACK_PROFILES` to use a quoted placeholder, or apply quoting at the call site. |

---

### task_505_validation.py

No actionable findings. Validation reads from artifacts with proper error handling. Test suite execution uses `shlex.quote` for `project_root`. All parsing failures return `None` with graceful fallback. The `_run_test_suite` function correctly aggregates multiple Rust workspace test results. The regex parsing for each stack is reasonable and handles partial matches.

---

### task_506_phase_audit.py

No actionable findings. Thin wrapper around `core.audit.run_phase_audit` with appropriate error handling. Always returns `True` (non-blocking by design). Phase number extraction handles the error case gracefully.

---

### task_507_closeout.py

No actionable findings. All previous findings remain fixed. `build_checklist` reads configured coverage targets from `tdd-setup.json` via the `output_dir` parameter. Metrics sourcing is well-documented with clear priority between `tdd-progress.json` (primary) and `validation-report.json` (fallback). The `_load_json` helper handles all failure modes.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 1 |
| **Total** | **1** |

### MEDIUM (1):
1. **task_504, line 1444**: The VERIFY phase's `verify_cmd` inserts `impl_file` into the shell command template via `str.format()` without `shlex.quote()`. This causes failures when the project path contains spaces. The same fix was applied to test commands (RED/GREEN/REFACTOR) in the previous audit but the VERIFY phase's `verify_cmd_template.format()` was overlooked.

### Previously reported findings now fixed (4 of 4):
- task_403 LLM router warmup: now present at lines 470-475
- task_403 `task_title` escaping: now uses `json.dumps()` at line 222
- task_504 pilot cycle counts: now added back to stats at lines 2457-2462
- task_504 test command quoting: now uses `shlex.quote()` at lines 928, 1229, 1361

**Summary: 0 critical, 0 high, 1 medium.**
