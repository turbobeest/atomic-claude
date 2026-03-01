# Orchestration Modules Re-Audit #2

**Date**: 2026-02-28
**Scope**: 7 orchestration files, categories A-R
**Severity Criteria**: CRITICAL / HIGH / MEDIUM only (strict)
**Context**: This audit follows a prior re-audit that found 4 issues (1 CRITICAL, 1 HIGH, 2 MEDIUM). Fixes have been applied for: atomic writes, StateLock usage, garbage path cleanup (partial), and non-numeric key safety. This audit verifies those fixes and searches for any remaining or newly exposed issues.

---

## Verified Fixes

The following fixes from the prior re-audit were verified as correctly applied:

1. **CRITICAL (pipeline.py line 658)**: `StateLock` was given a directory path. **FIXED** -- now uses `self.state.lock_file` (`.state/state.lock`), matching the pattern in `StateManager.save_state()`.

2. **MEDIUM (pipeline.py lines 685-717)**: `_ensure_closeout_exists` used non-atomic `write_json`. **FIXED** -- now uses `tempfile.mkstemp()` + `os.fdopen()` + `os.replace()` with proper cleanup in a `try/except BaseException` block.

3. **MEDIUM (backtrack.py lines 108-111)**: `int(task_id)` on state dict keys could raise `ValueError`. **FIXED** -- wrapped in `try/except (ValueError, TypeError): continue`, correctly skipping non-numeric keys.

4. **HIGH (pre_task_validation.py lines 295-303)**: `auto_cleanup` created garbage directories for `"should never exist"` entries. **PARTIALLY FIXED** -- the `"should never exist"` case now correctly deletes files. However, other ambiguous location strings still create garbage directories (see finding O-1 below).

5. **HIGH (pipeline.py line 670)**: Stale `current_phase` after phase completion (from filtered findings H4). **FIXED** -- `self.state.set_current_phase(None)` added in `_finalize_phase`.

6. **CRITICAL (dashboard_sync.py lines 153-165)**: `write_current_task` used non-atomic write. **FIXED** -- now uses `tempfile.mkstemp()` + `os.fdopen()` + `os.replace()` with proper cleanup.

7. **CRITICAL (backtrack.py lines 479-489)**: `backtrack_to` state write used non-atomic `write_json`. **FIXED** -- now uses `tempfile.mkstemp()` + `os.fdopen()` + `os.replace()` with proper cleanup.

8. **MEDIUM (dashboard_sync.py line 540)**: `fix_state_inconsistencies` deleted `current-task.json` for tasks older than 5 minutes. **FIXED** -- now checks `current.get("active", False)` before deleting; active tasks are preserved.

9. **MEDIUM (backtrack.py lines 427-430)**: Invalid task ID parsing raised unhandled `ValueError`. **FIXED** -- wrapped in `try/except ValueError` with user-friendly error message.

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

## orchestration/pipeline.py

| # | Severity | Category | Line(s) | Finding | Trigger Scenario | Recommendation |
|---|----------|----------|---------|---------|------------------|----------------|
| P-1 | MEDIUM | E (Concurrency) | 658-670 | TOCTOU gap between `reload()` and `save_state()`. The `StateLock` at line 658 covers only the `reload()` call. After the lock is released (line 660), `mark_phase_complete` (line 667) and `set_current_phase` (line 670) each call `save_state()` which acquires a separate lock internally. Between the reload-unlock and the next lock acquisition in `save_state()`, another process (e.g., dashboard sync calling `update_current_task_provider`) could write state to disk. That write is then overwritten by `save_state()` which writes the stale-read-then-modified in-memory state. | Pipeline runs Phase 3 to completion. `_finalize_phase` reloads state (lock, read, unlock). In the microsecond gap before `mark_phase_complete` calls `save_state`, the dashboard sync process calls `update_current_task_provider`, which reads+modifies+writes state under its own lock. Then `mark_phase_complete.save_state()` overwrites the dashboard's provider update with its own copy that does not include it. Provider info is silently lost from state. | Expand the lock scope to cover reload through `mark_phase_complete` + `set_current_phase`, or refactor to do a single lock-read-modify-write cycle. Alternatively, add `reload()` calls within `save_state()` to merge changes. |
| P-2 | MEDIUM | F (State) | 667, 670 | Double `save_state()` in `_finalize_phase`. `mark_phase_complete` (line 667) calls `save_state()`, then `set_current_phase(None)` (line 670) calls `save_state()` again. Each acquires the lock, writes the full state dict, and releases. If a crash occurs between the two saves, the phase is marked complete but `current_phase` still points to the finished phase. `get_pipeline_status` would report `pipeline_state: "running"` for a completed phase until the next `run_phase` call. | Phase 5 completes. `mark_phase_complete` writes state with `phases["5-implementation"].status = "completed"` and `current_phase = "5-implementation"`. Process is killed (SIGKILL) before `set_current_phase(None)` executes. On next startup, `get_pipeline_status` reads `current_phase = "5-implementation"` and reports `pipeline_state: "running"`, even though the phase is fully complete. Dashboard shows incorrect "running" status. | Combine both mutations into a single save: set `current_phase = None` in memory first, then call `mark_phase_complete` (which saves both changes atomically). Or create a `finalize_phase_state(phase_id)` method on `StateManager` that does both in one save. |

---

## orchestration/task_display.py

No actionable findings.

The file handles display and interactive prompts. Private attribute access (`resolver._defaults`, `resolver._config`) is documented with inline comments. The `_handle_override` function is long but functionally correct. All user input is properly validated with strip/lower/try-except patterns. The `_fmt_context` function returns "0K" for values below 1000, but the resolver guarantees `context_window` is always at least 128,000, so the edge case is unreachable during normal operation.

---

## orchestration/task_memory.py

No actionable findings.

The module is a clean in-memory accumulator. The `checkpoint` method's exception handling is appropriate. The `_format_entries` static method correctly groups by category and skips empty categories. The `build_metadata` method safely accesses `self._skill_selection.skills` only when `_skill_selection` is truthy. No file I/O, no concurrency concerns.

---

## orchestration/pre_task_validation.py

| # | Severity | Category | Line(s) | Finding | Trigger Scenario | Recommendation |
|---|----------|----------|---------|---------|------------------|----------------|
| O-1 | HIGH | C (Data Flow) | 304-314, 47-52 | `auto_cleanup()` still creates garbage directories for `FORBIDDEN_TYPES` entries whose `correct_location` strings contain spaces, "or" alternatives, or other non-path content. The fix for `"should never exist"` (lines 295-303) was correct, but remaining location strings are still used as filesystem paths. Specifically: `.csv` maps to `"parent directory or ../data/"`, `.db` maps to `"parent directory or ../data/"`, `.sqlite` maps to `"parent directory or ../data/"`, `.sql` maps to `"parent directory or ../migrations/"`, `.ipynb` maps to `"../notebooks/ or parent directory"`. For these, `split("(")[0].strip()` does NOT remove the `"or"` clauses because they don't use parentheses. The resulting `dst_dir` resolves to paths like `acp_root.parent / "parent directory or ../data/"`, creating a literal directory named `"parent directory or ../data/"` on the filesystem. | User has a stray `.csv` file in the atomic-claude root. They run `python orchestration/pre_task_validation.py cleanup`. The violation has `correct_location = "parent directory or ../data/"`. Line 307 check fails (string starts with `"parent"`, not `"../"`) . Line 311 computes `raw_loc = "parent directory or ../data/"`. Line 314 creates `dst_dir = acp_root.parent / "parent directory or ../data/"`. Line 317 calls `mkdir(parents=True)`, creating a directory literally named `"parent directory or ../data/"` under the project root. The `.csv` file is moved into this garbage directory. Affected types: `.csv`, `.db`, `.sqlite`, `.sql`, `.ipynb`. | Separate display messages from cleanup destinations in `FORBIDDEN_TYPES`. Use a structure like `(display_message, cleanup_path_or_None)`. For entries without a clear single destination, default to `reports/` and log a message. Alternatively, add a routing table that maps each `correct_location` pattern to an actual path. |

---

## orchestration/dashboard_sync.py

No actionable findings.

The atomic write pattern in `write_current_task` (lines 153-165, tempfile + `os.replace`) is correct. The `_locked_file` context manager properly handles both Unix and Windows locking. The `update_current_task_provider` read-modify-write with locking is appropriate. The `fix_state_inconsistencies` stale-task cleanup now correctly checks the `active` flag (line 540) before deleting old files. The `log_error` function uses `_locked_file` for `errors.json` writes.

Note: `backtrack.py` line 239 writes `errors.json` via `write_text` without locking, which could conflict with `log_error`'s locked writes. However, backtrack runs as a user-initiated single-process operation (not concurrent with pipeline execution), so the practical risk is negligible under normal operation.

---

## orchestration/backtrack.py

| # | Severity | Category | Line(s) | Finding | Trigger Scenario | Recommendation |
|---|----------|----------|---------|---------|------------------|----------------|
| B-1 | MEDIUM | F (State) | 456-462, 494-497 | Backtrack-in-progress marker has no recovery consumer. The marker file (`.state/backtrack-in-progress`) is written before cleanup begins (line 458) and removed in the `finally` block (line 496). If the process is killed with SIGKILL during cleanup (between artifact deletion and state write), the marker persists on disk. However, no code in `pipeline.py`, `main.py`, or any startup path checks for a stale marker. The marker's stated purpose (making "interrupted backtracks detectable") is never fulfilled because nothing detects it. This means an interrupted backtrack leaves the system in an inconsistent state (artifacts deleted, state unmodified) with no automated recovery path and no warning to the user. | User runs `backtrack_to(3)`. `_clear_artifacts` deletes outputs for phases 4-9. Process is killed by OOM killer before the atomic state write on line 479. The marker file `.state/backtrack-in-progress` exists. User restarts and runs `python main.py run 4`. Pipeline sees state showing phases 4-9 as completed but their artifacts are gone. Closeout validation fails for missing files, and the user gets confusing error messages. The marker file is never checked, so there is no "interrupted backtrack detected -- please re-run" message. | Add a startup check (in `PhasePipeline.__init__` or `main.py`) that detects the stale marker and either resumes the backtrack or warns the user to re-run it. |

---

## orchestration/memory_enrichment.py

No actionable findings.

The temp file cleanup in `enrich_memory_with_llm` is properly handled in a `finally` block with `Path.unlink(missing_ok=True)`. HTML/script tag stripping and length truncation on LLM output provide adequate defense-in-depth. `scan_output_files` correctly handles `OSError` at both directory and file levels. The `secrets.json` exclusion is properly implemented. The scan result caching (avoiding double `scan_output_files` calls) is correctly implemented.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH     | 1 |
| MEDIUM   | 3 |
| **Total** | **4** |

### Finding Index

| # | Severity | File | Line(s) | Short Description |
|---|----------|------|---------|-------------------|
| P-1 | MEDIUM | orchestration/pipeline.py | 658-670 | TOCTOU gap: `StateLock` covers only `reload()`, not the subsequent `mark_phase_complete` + `set_current_phase` saves |
| P-2 | MEDIUM | orchestration/pipeline.py | 667, 670 | Double `save_state()` in `_finalize_phase` -- crash between the two saves leaves `current_phase` stale |
| O-1 | HIGH | orchestration/pre_task_validation.py | 304-314, 47-52 | `auto_cleanup()` still creates garbage directories for `.csv`, `.db`, `.sqlite`, `.sql`, `.ipynb` -- only `"should never exist"` case was fixed |
| B-1 | MEDIUM | orchestration/backtrack.py | 456-462, 494-497 | Backtrack-in-progress marker is written but never checked on startup -- interrupted backtracks leave inconsistent state with no recovery path |

### Files with No Actionable Findings

- `orchestration/task_display.py` -- No actionable findings
- `orchestration/task_memory.py` -- No actionable findings
- `orchestration/dashboard_sync.py` -- No actionable findings
- `orchestration/memory_enrichment.py` -- No actionable findings
