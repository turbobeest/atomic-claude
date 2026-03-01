# Orchestration Modules Re-Audit

**Date**: 2026-02-28
**Scope**: 7 orchestration files, categories A-R
**Severity Criteria**: CRITICAL / HIGH / MEDIUM only (strict)

---

## Files Audited

1. `orchestration/pipeline.py`
2. `orchestration/task_display.py`
3. `orchestration/task_memory.py`
4. `orchestration/pre_task_validation.py`
5. `orchestration/dashboard_sync.py`
6. `orchestration/backtrack.py`
7. `orchestration/memory_enrichment.py`

---

### orchestration/pipeline.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| E (Concurrency / Locking) | CRITICAL | `StateLock` is instantiated with a **directory path** (`self.state.state_file.parent` resolves to `.state/`), but `StateLock.__init__` expects a **file path**. `StateLock.acquire()` calls `open(self.lock_file, 'w')` which raises `IsADirectoryError` on Linux when given a directory. This crashes `_finalize_phase`, preventing phase completion, closeout writing, and state updates after a successful phase run. | 658 | Run any phase to completion. When `_finalize_phase` is called, `StateLock(.state/)` raises `IsADirectoryError`, the `with lock:` block fails, and the phase is not finalized despite all tasks completing successfully. The orchestrator returns `False` (line 614 catch) and the user sees "Phase X failed" even though all work was done. | Change line 658 from `StateLock(self.state.state_file.parent)` to `StateLock(self.state.lock_file)` to use the proper lock file path (`.state/state.lock`), matching the pattern used internally by `StateManager.save_state()`. |
| F (State Management) | MEDIUM | `_ensure_closeout_exists` uses `write_json()` which performs a non-atomic write (`open` + `json.dump`). If the process crashes mid-write, a partially-written closeout file would exist on disk. Subsequent validation checks only test `closeout_file.exists()` (lines 345, 564), so a corrupt closeout would pass validation but cause `JSONDecodeError` when any code attempts to read and parse it. | 685-703 | System crash or kill -9 during `_ensure_closeout_exists`. On next run, `_validate_closeout_files` passes (file exists), but any code that reads the closeout JSON (e.g., downstream phase processing) fails with `JSONDecodeError`. | Use the same atomic write pattern used elsewhere in this file: `tempfile.mkstemp()` + `os.fdopen()` + `os.replace()`. Alternatively, import and use `StateManager.save_state()`'s atomic write helper. |

---

### orchestration/task_display.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|

No actionable findings. The file handles display and interactive prompts. The `_fmt_context` function produces "0K" for context_window values below 1000, but the resolver guarantees context_window is always at least 128,000 in practice, so this edge case is not reachable during normal operation. Private attribute access (`resolver._defaults`, `resolver._config`) is intentional and documented with inline comments.

---

### orchestration/task_memory.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|

No actionable findings. The module is a clean in-memory accumulator with no file I/O, no concurrency concerns, and correct data flow. The `checkpoint` method's exception handling is appropriate (logs and continues). The `_format_entries` static method correctly handles missing categories by skipping them.

---

### orchestration/pre_task_validation.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| C (Data Flow / Correctness) | HIGH | `auto_cleanup()` uses `correct_location` strings from `FORBIDDEN_TYPES` and `classify_violation()` as filesystem paths, but many of these are human-readable descriptions containing spaces, parentheses, and alternatives -- not valid path components. For example, `.js` maps to `"../src/ (unless it's dashboard/server.js)"`. At line 309, `replace("../", "")` yields `"src/ (unless it's dashboard/server.js)"`, which is then used as a directory path via `acp_root.parent / ...`, creating a directory with literal spaces and parentheses. Similarly, `.csv` maps to `"parent directory or ../data/"` (line 46), which at line 312 becomes `acp_root.parent / "parent directory or ../data/"`, another bogus path. | 295-316, 26-62 | User runs `python orchestration/pre_task_validation.py cleanup` with a stray `.js` or `.csv` file in the atomic-claude root. The auto_cleanup function creates garbage directories like `../src/ (unless it's dashboard/server.js)/` and moves files there. Affected file types: `.js`, `.csv`, `.db`, `.sqlite`, `.sql`, `.ipynb` (any FORBIDDEN_TYPES entry with parenthetical notes or the word "or"). | Separate the `FORBIDDEN_TYPES` dict into two concerns: (1) a display message for the violation report and (2) an actual destination path for auto_cleanup. For example, use a tuple `(display_msg, cleanup_path)` or add a `cleanup_destination` field. For types with ambiguous destinations, default to `reports/` and log a message asking the user to move manually. |

---

### orchestration/dashboard_sync.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|

No actionable findings. The atomic write pattern in `write_current_task` (tempfile + os.replace) is correct. The `_locked_file` context manager properly handles both Unix and Windows locking. The `update_current_task_provider` read-modify-write with locking is appropriate for its single-process sequential call pattern. The stale current-task.json cleanup in `fix_state_inconsistencies` correctly checks the `active` flag before deleting old files.

---

### orchestration/backtrack.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| C (Data Flow / Correctness) | MEDIUM | `_clear_state` at line 109 calls `int(task_id)` on task dictionary keys from the state file. If a state file contains a non-numeric task key (e.g., due to manual editing, a migration artifact, or a plugin adding metadata keys under `tasks`), this raises `ValueError`, aborting the entire backtrack operation. The state dict modifications up to that point would be lost (state is written atomically at the end, so no partial write), but the artifacts and memory cleared in steps 1-2 would already be deleted, leaving an inconsistent state. | 108-111 | State file `task-state.json` contains a non-numeric key under `phases.<phase_id>.tasks` (e.g., `"metadata"` or `"_schema_version"`). User runs `backtrack_to(phase, task="205")`. The `int(task_id)` call on the non-numeric key raises `ValueError`. Artifacts and memory have already been cleared (steps 1-2), but the state file is NOT updated (step 4 never runs), leaving the system in an inconsistent state where artifacts are gone but state still shows them as completed. | Wrap the `int(task_id)` conversion in a try/except and skip non-numeric keys: `try: tid = int(task_id) except ValueError: continue`. |

---

### orchestration/memory_enrichment.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|

No actionable findings. The temp file cleanup in `enrich_memory_with_llm` is properly handled in a `finally` block. The HTML/script tag stripping and length truncation on LLM output provide adequate defense-in-depth. The `scan_output_files` function correctly handles `OSError` at both the directory and file level. The `secrets.json` exclusion is properly implemented.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| HIGH     | 1 |
| MEDIUM   | 2 |
| **Total** | **4** |

### Finding Index

| # | Severity | File | Line(s) | Short Description |
|---|----------|------|---------|-------------------|
| 1 | CRITICAL | orchestration/pipeline.py | 658 | `StateLock` given directory path instead of file path -- crashes `_finalize_phase` with `IsADirectoryError` |
| 2 | MEDIUM | orchestration/pipeline.py | 685-703 | `_ensure_closeout_exists` uses non-atomic `write_json`, crash can leave corrupt closeout file |
| 3 | HIGH | orchestration/pre_task_validation.py | 295-316, 26-62 | `auto_cleanup()` uses human-readable location strings as filesystem paths, creating garbage directories |
| 4 | MEDIUM | orchestration/backtrack.py | 108-111 | `int(task_id)` on state dict keys can raise `ValueError` on non-numeric keys, leaving artifacts deleted but state unmodified |
