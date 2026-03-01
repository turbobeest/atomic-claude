# Phase 04 - Specification: Code Audit Report

**Auditor:** Claude Opus 4.6 (automated)
**Date:** 2026-02-28
**Scope:** 7 files in Phase 04 (Specification)
**Method:** Full read of every file, all audit categories A-R applied

---

## File 1: `phases/phase04/orchestrator04.py`

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| C1 | LOW | `os` imported but only used for `os.getenv`; could use a narrower import or keep as-is. Minimal impact. | 18, 40-43 | Acceptable; no action needed. |
| I1 | MEDIUM | `ATOMIC_ROOT` falls back to `Path.cwd()` which may be wrong if the script is imported rather than run directly. Other orchestrators share this pattern, so this is a cross-cutting issue. | 40 | Consider raising an error when `ATOMIC_ROOT` is not set instead of silently using cwd. |
| I1 | LOW | `OUTPUT_DIR` default uses `Path` concatenation with a `str`-typed env var fallback. `os.getenv` returns `str`, which is passed to `Path()` correctly, but the fallback expression `PROJECT_ROOT / '.outputs' / '4-specification'` is evaluated regardless and wrapped by `Path()`. Works correctly. | 42 | No change needed. |
| N1 | INFO | `sys.path.insert(0, ...)` at module level modifies the Python path globally at import time. This is a project-wide pattern shared by all orchestrators. | 22 | Consider a project-wide solution (e.g., `setup.py` / `pyproject.toml` editable install) to avoid sys.path manipulation. |
| F1 | INFO | Task wrapper functions accept `(mem=None, graph=None)` and forward to task `execute()` with positional args `(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem, graph=graph)`. The phase_runner calls `task_func(mem, graph=graph)`, so `mem` is received as the first positional parameter. This works correctly. | 98-125 | No change needed; correct interface. |
| J6 | INFO | Task wrappers all follow the identical pattern. Consistent. | 98-125 | No change needed. |
| K1 | INFO | Import of `get_graph` and `run_phase_tasks` matches project conventions. | 27-28 | No change needed. |

**File verdict:** Clean. No critical or high issues.

---

## File 2: `phases/phase_04_specification/tasks/task_401_entry_initialization.py`

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| C1 | LOW | `Dict` and `Any` imported from `typing` but never used in any type annotation in this file. | 12 | Remove `Dict, Any` from the import. |
| A3 | MEDIUM | `task_count` is set on line 107 inside a `try` block under `if tasks_file.exists()`. If `tasks_file` does not exist, `verification_passed` is set False and the function returns False on line 139. However, if it does exist but the `tasks` list is present with `task_count > 0`, `task_count` is set. Later on line 154, `task_count` is used again (via re-read of tasks_file). The variable `task_count` from line 107 is only used on line 154, but by that point the file has been re-read (line 147) and `tasks` re-derived. So the `task_count` on line 154 references the original scope variable. This works but is fragile -- if the file changed between reads, `task_count` and `tasks` could be inconsistent. | 107, 147, 154 | Use `len(tasks)` directly on line 154 instead of the stale `task_count` variable, or compute it from the fresh re-read. |
| A1 | LOW | The `tasks_file` is read twice: once at line 106 for verification and again at line 147 for display. This is redundant I/O. | 106, 147 | Cache the parsed data from the first read. |
| E4 | LOW | Double read of `tasks_file` -- see A1 above. | 106, 147 | Same as above. |
| R1 | INFO | Banner is 109 characters wide, which may wrap on narrow terminals. Consistent with other phases. | 26-40 | Acceptable; project convention. |
| R6 | MEDIUM | In non-UAT mode, the function calls `prompt_user()` (lines 193, 230) which blocks on stdin. Running in non-interactive/CI mode will hang. | 193, 230 | Add guard: skip prompts if stdin is not a TTY. |
| B3 | LOW | Exception on line 98 catches broadly and prints a warning but continues. This is acceptable for a non-critical closeout check. | 98-99 | No change needed. |
| G1 | INFO | No path traversal risk; all paths derived from `atomic_root` and `project_root`. | -- | No change needed. |
| L1 | MEDIUM | Deleting existing spec files (line 196-197) is not idempotent -- if interrupted mid-delete, some specs are gone. No rollback. | 195-197 | Consider atomic replace: move to temp dir, then delete. Or confirm this is acceptable UX. |
| H1 | INFO | Uses `print()` for all output rather than `logger`. Consistent with project pattern for user-facing output. | -- | Acceptable project convention. |

**File verdict:** No critical issues. Medium issues around stale variable reference and interactive-only prompts.

---

## File 3: `phases/phase_04_specification/tasks/task_402_agent_selection.py`

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| C1 | LOW | `Optional` imported from `typing` but never used. | 13 | Remove `Optional` from the import. |
| A5 | LOW | `task_count` on line 337 references the variable from `analyze_project_characteristics()` return (line 231). If `characteristics` is empty dict (error path on line 96), `task_count` will be `0`. This is safe but `task_count` is stored in `roster_data` even when it may be `0` due to an analysis failure, which could be misleading. | 231, 337 | Consider falling back to actual task count from tasks_file if analysis fails. |
| E7 | LOW | `load_agents_from_csv` truncates descriptions to 70 characters (`[:70]`). This is a magic number. | 47 | Extract as a named constant, e.g., `AGENT_DESC_MAX_LEN = 70`. |
| E6 | LOW | Magic number `category_filter="06-09-implementation"` in function default. | 27 | Extract as a named constant. |
| R6 | MEDIUM | Multiple `prompt_user()` calls (lines 268, 288) block on stdin in non-interactive mode. | 268, 288 | Add TTY guard for non-interactive environments. |
| E1 | LOW | ANSI escape sequences manually constructed (lines 186-189, 195-196, 202-206, 225, 260) instead of using the `print_*` helpers from `cli_ui`. Inconsistent with the rest of the file which uses `print_bold`, `print_cyan`, etc. | 186-196, 202-206, 225, 260 | Use `cli_ui` helper functions consistently. |
| B2 | LOW | Broad `except Exception` on line 49 catches all CSV parsing errors. Acceptable for a best-effort load. | 49 | Consider logging the specific exception type. |
| A8 | INFO | `recommend_agents` returns `reasons` list but it is only checked for emptiness on line 235; the individual reasons are never displayed. | 103-127, 235 | Either display reasons or remove the reasons list. |
| J1 | INFO | Imports are consistent with other phase 04 tasks. | 7-24 | No change needed. |
| L1 | LOW | Agent selection writes to both `roster_file` and `output_dir / "selected-agents.json"`. If one write fails after the other succeeds, state is inconsistent. | 342, 346-349 | Low risk; acceptable for interactive flow. |

**File verdict:** No critical issues. Minor style inconsistency with ANSI escapes.

---

## File 4: `phases/phase_04_specification/tasks/task_403_openspec_generation.py`

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| B2 | LOW | `except (json.JSONDecodeError, Exception)` on line 44 -- `Exception` subsumes `JSONDecodeError`, making the multi-catch redundant. | 44 | Simplify to `except Exception:`. |
| E1 | MEDIUM | Markdown code fence stripping logic is duplicated between `_spec_worker` (lines 268-275), `execute` graph-write block (lines 483-487), and also in task_404's `_load_openspec` and task_406's `check_closeout_items`. Same pattern repeated 4+ times. | 268-275, 483-487 | Extract a shared `strip_markdown_fences(text) -> str` utility into `core/utils/file_ops.py` or a spec helper module. |
| M1 | MEDIUM | The LLM prompt in `_build_spec_prompt` includes `task_title` directly in a JSON template string on line 226. If `task_title` contains double quotes or backslashes, the JSON template will be malformed, potentially confusing the LLM. | 226 | Escape `task_title` for JSON embedding (e.g., use `json.dumps(task_title)` to get a properly escaped string). |
| M2 | MEDIUM | `_spec_worker` validates the output file is valid JSON (line 277), but if validation fails, the invalid file is left on disk. Subsequent runs or task_404 may pick up this invalid file. | 268-282 | Delete or rename the invalid file, or write a `.invalid` marker. |
| A6 | LOW | `_spec_worker` accesses `invoke_llm` via closure parameter. Thread-safety depends on invoke_llm being thread-safe. The code comments in task_404 (line 549) mention a race condition in the LLM router. Task 403 does NOT perform the same warm-up. | 257-262 | Add the same LLM warm-up call that task_404 performs (line 552) before spawning the thread pool. |
| I1 | LOW | `MAX_CONCURRENT = 5` is hardcoded. | 32 | Consider making configurable via env var, e.g., `int(os.getenv('ATOMIC_SPEC_WORKERS', 5))`. |
| M7 | INFO | Model is hardcoded as `"opus"` in both the prompt and the `invoke_llm` call. | 260, 504 | Consider making the model configurable. |
| L1 | LOW | If interrupted mid-generation, partial spec files may exist on disk without any marker indicating they are incomplete. | 253-289 | Consider writing a `.generating` marker file that is removed on completion. |
| M4 | MEDIUM | On LLM failure, falls back to stub spec silently (line 286-289). The stub spec has `"stub_mode": True` but there is no downstream check that warns the user that LLM-generated specs failed. | 286-289 | Log a warning or surface to the user that a fallback stub was used. |
| E1 | LOW | The entire ImportError fallback block (lines 514-531) duplicates the UAT mode stub generation logic (lines 419-449). | 514-531 | Factor out shared stub-generation logic. |
| H1 | INFO | Print output mixes `print()` and `print(print_green(...))`. Pattern calls like `print(print_dim(...))` pass the return value of `print_dim` to `print`. This works because `print_dim` returns a string. | -- | Correct; consistent with project convention. |
| A1 | LOW | `_load_project_context` reads tasks_file (line 134-148) which is also read in `load_tasks` (line 37-45). Duplicate I/O for the same file. | 37-45, 134-148 | Pass the already-loaded tasks list to `_load_project_context`. |

**File verdict:** No critical issues. Medium issues around duplicate fence-stripping logic, LLM prompt injection risk, and silent fallback to stubs.

---

## File 5: `phases/phase_04_specification/tasks/task_404_tdd_subtask_injection.py`

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| C1 | LOW | `re` is imported (line 15) and used in `_load_openspec` and `_extract_json_block`. However, `copy` (line 12) is used in `_parse_tdd_response` for `deepcopy`. Both are used. No unused imports. | 12, 15 | No change needed. |
| A4 | MEDIUM | `_validate_subtasks` mutates its input by adding `spec_references` key (line 244-245). The docstring warns about this (line 228-229), and callers pass `copy.deepcopy(parsed)` (lines 196, 207). However, if a future caller forgets `deepcopy`, the original LLM response dict gets mutated. | 244-245 | Have `_validate_subtasks` return a new list with the added keys instead of mutating in-place, or always deepcopy inside the function. |
| M1 | LOW | `_build_tdd_prompt` embeds `task_title`, `task_desc`, and `acceptance` directly into the prompt without escaping. Less risky than task_403 since this is not inside a JSON template, but adversarial task titles could still influence LLM behavior. | 130-138 | Consider sanitizing or at minimum noting the trust boundary. |
| A6 | INFO | Thread-safety: task_404 explicitly performs an LLM warm-up on line 552 to avoid a race condition in the router singleton. This is well-documented. Good practice. | 548-553 | No change needed; good defensive programming. |
| E1 | MEDIUM | `_run_parallel_tdd` (lines 296-377) is structurally near-identical to `_run_parallel_specs` in task_403 (lines 292-375). ~80 lines of Rich Live progress display logic are duplicated. | 296-377 | Extract a generic `_run_parallel_with_progress(tasks, worker_fn, title)` utility. |
| R6 | MEDIUM | `prompt_user` called on line 540 blocks in non-interactive mode. Also `clear_input_buffer` + `prompt_user` on line 488-489 blocks. | 488-489, 540 | Add TTY guard. |
| Q1 | LOW | Graph `get_node` access on line 519 uses a fallback pattern: `getattr(graph, 'get_node', None) or graph.reader.get_node`. This couples the task to internal graph implementation details. | 519 | Use a single stable API method on the graph manager. |
| L5 | MEDIUM | `shutil.copy(tasks_file, backup_file)` (line 447) creates a backup, then the modified `tasks_data` is written back to `tasks_file` (line 578). If the write fails mid-way, `tasks_file` could be corrupted. The backup exists but there's no automatic restore mechanism. | 447, 578 | Write to a temp file first, then atomically rename to `tasks_file`. |
| B2 | LOW | Multiple `except Exception` blocks (lines 291, 524). Acceptable for worker threads and graph queries. | 291, 524 | No change needed. |
| E6 | LOW | Magic numbers: `SPEC_TRUNCATE_CHARS = 50_000` and `MAX_CONCURRENT = 5`, `timeout=600`, `timeout=30` (warm-up). | 36-37, 262, 274, 552 | Consider centralizing timeout/concurrency config. |
| M6 | INFO | LLM warm-up uses `model="haiku"` (line 552) but actual generation uses `model="opus"` (line 272). The warm-up is documented as router initialization, not model-specific, so this is fine. | 552, 272 | No change needed; documented behavior. |
| A1 | LOW | `tasks_data` is read from disk twice: once on line 452 for processing and again on line 607 for verification. The second read is intentional (to verify the write succeeded). | 452, 607 | Acceptable; verification read is deliberate. |

**File verdict:** No critical issues. Medium issues around duplicated parallel runner code, non-atomic file writes, and interactive-only prompts.

---

## File 6: `phases/phase_04_specification/tasks/task_405_phase_audit.py`

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| A1 | LOW | `phase_name` is derived from `output_dir.name` (line 36). For Phase 4, `output_dir` is `.outputs/4-specification` so `phase_name = "4-specification"`, `phase_num = 4`, `phase_id = "4-specification"`. This works correctly for the expected path structure. | 36-43 | No change needed. |
| F4 | MEDIUM | `run_phase_audit` is called with `audit_context` kwarg (line 59-60), which matches the function signature at `core/audit.py:2076`. However, the function may not exist as a module-level import -- `from core.audit import run_phase_audit` (line 16). The module is `core/audit.py` (a single file, not a package), so this import path is correct. | 16 | No change needed. |
| B2 | LOW | Broad `except Exception` on line 55 catches all graph/audit errors. Acceptable since audit is non-blocking. | 55-56 | No change needed. |
| D3 | INFO | Comment "Non-blocking" appears in return statement (line 67), docstring (line 33), and error message (line 65). Adequately documented. | 33, 58, 65, 67 | No change needed. |
| A1 | LOW | If `output_dir.name` does not contain `-`, the function returns True on line 45 without writing any artifact. The orchestrator expects no artifact from task 405 (artifact list is empty). Consistent. | 43-45 | No change needed. |
| J7 | INFO | This file is notably shorter and simpler than the other tasks. It delegates to `core.audit.run_phase_audit` and the audit graph loader. Clean separation of concerns. | -- | Good design. |

**File verdict:** Clean. No critical or high issues. Well-delegated.

---

## File 7: `phases/phase_04_specification/tasks/task_406_closeout.py`

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| C1 | LOW | `List` imported from `typing` but used only in type hints. `Tuple` also imported and used. `Dict` imported and used. All imports are used. | 11 | No change needed. |
| A3 | MEDIUM | `tasks_data` is loaded from `tasks_file` on line 339, but `check_closeout_items` on line 351 also reads `tasks_file` internally (line 41). The file is read twice. | 339, 351 (delegates to `check_closeout_items` line 41) | Pass `tasks_data` to `check_closeout_items` to avoid redundant I/O. |
| E1 | MEDIUM | Markdown code fence stripping in `check_closeout_items` (lines 117-121) duplicates the same pattern from task_403 and task_404. | 117-121 | Use shared utility (see task_403 finding). |
| R6 | MEDIUM | `prompt_user` calls on lines 371 and 387 block in non-interactive mode. | 371, 387 | Add TTY guard. |
| A8 | LOW | `spec_count` is computed from `spec_files` on line 418, but `spec_files` was already computed on line 336. However, `generate_closeout_documents` also accepts `spec_files` as a parameter and uses it. The value computed on line 418 is used for the memory checkpoint print, and is derived from the same list. Consistent but could use `len(spec_files)` directly from the outer scope. | 336, 418 | Minor; use `len(spec_files)` from the outer scope variable. |
| D3 | LOW | "Memory Checkpoint (placeholder for future memory.py integration)" comment on line 416, and "Memory checkpoint would save here..." print on line 422. This is a documented stub/placeholder. | 416, 422 | Implement or remove the placeholder when memory integration is done. |
| E5 | INFO | `generate_closeout_documents` accepts many optional parameters with None defaults, adding complexity. The function signature has 7 parameters. | 162-170 | Acceptable; kwargs are for performance optimization (avoiding re-reads). |
| L1 | LOW | `generate_closeout_documents` writes both `.md` and `.json` files. If the second write fails, the first file exists without its counterpart. Low risk since both are informational. | 262, 283 | Acceptable for closeout artifacts. |
| H1 | INFO | User-facing messages use `print()` with `cli_ui` formatters. Consistent with project pattern. | -- | No change needed. |
| Q6 | INFO | Closeout data includes `next_phase: 5` which ties the closeout to the pipeline ordering. If phases are renumbered, this would need updating. | 280 | Accept as-is; phase numbering is stable. |

**File verdict:** No critical issues. Medium issues around redundant file I/O and non-interactive blocking.

---

## Cross-File Findings

| Check | Severity | Finding | Files | Recommendation |
|-------|----------|---------|-------|----------------|
| E1 | MEDIUM | Markdown code fence stripping logic (````json...````) duplicated 4+ times across task_403 (2x), task_404, and task_406. | task_403, task_404, task_406 | Extract `strip_code_fences(text: str) -> str` into `core/utils/file_ops.py` or a new `core/utils/json_helpers.py`. |
| E1 | MEDIUM | Rich Live parallel progress display duplicated between task_403 `_run_parallel_specs` and task_404 `_run_parallel_tdd` (~80 lines each, nearly identical structure). | task_403, task_404 | Extract a reusable `run_parallel_with_live_progress()` function. |
| R6 | MEDIUM | Five files use `prompt_user()` / `clear_input_buffer()` without checking if stdin is a TTY. Running the pipeline in CI or non-interactive mode will hang. | task_401, task_402, task_404, task_406 | Add `sys.stdin.isatty()` guard, or add a `--non-interactive` flag that auto-accepts defaults. |
| N1 | LOW | All 6 task files insert `sys.path.insert(0, ...)` at module level. This is a project-wide pattern but pollutes the Python path. | All task files | Project-wide: adopt editable install (`pip install -e .`) so sys.path manipulation is unnecessary. |
| J1 | INFO | Import pattern is consistent across all files: stdlib, sys.path hack, then project imports. All files follow the same structure. | All files | Consistent; good. |
| J6 | INFO | All task `execute()` functions follow the same signature: `(atomic_root, output_dir, uat_mode, mem, graph) -> bool`. Consistent interface contract. | All task files | Good consistency. |
| A6 | LOW | task_404 has an LLM warm-up call (line 552) to avoid a documented race condition in the router singleton, but task_403 does NOT have this warm-up despite using the same `ThreadPoolExecutor` pattern with `invoke_llm`. | task_403, task_404 | Add the same warm-up call to task_403 before launching the thread pool. |

---

## Aggregate Counts

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 14 |
| LOW | 22 |
| INFO | 16 |
| **Total** | **52** |

### Medium Findings Summary

1. **E1 - Duplicated code fence stripping** (task_403, task_404, task_406) -- extract shared utility
2. **E1 - Duplicated parallel runner** (task_403, task_404) -- extract shared utility
3. **R6 - Non-interactive blocking** (task_401, task_402, task_404, task_406) -- 4 files, add TTY guard
4. **M1 - LLM prompt injection via task_title** (task_403) -- escape for JSON embedding
5. **M2 - Invalid spec files left on disk** (task_403) -- clean up or mark invalid
6. **M4 - Silent fallback to stubs** (task_403) -- surface to user
7. **L5 - Non-atomic tasks.json write** (task_404) -- use temp file + rename
8. **A4 - Mutation in validator** (task_404) -- return new list instead of mutating
9. **I1 - Silent cwd fallback for ATOMIC_ROOT** (orchestrator04) -- consider error
10. **A3 - Stale `task_count` variable** (task_401) -- use fresh computation
11. **A3 - Redundant file I/O** (task_406) -- pass cached data
12. **L1 - Non-idempotent spec deletion** (task_401) -- consider atomic replace

### Overall Assessment

Phase 04 is well-structured with consistent patterns across all files. The code is functional and handles error cases reasonably. The main areas for improvement are:

1. **Code duplication** -- fence stripping and parallel runner patterns should be extracted
2. **Non-interactive safety** -- all interactive prompts need TTY guards for CI usage
3. **LLM robustness** -- the warm-up race condition fix in task_404 should be applied to task_403 as well
4. **File atomicity** -- tasks.json modifications should use atomic write patterns

No critical or high-severity issues were found. The codebase is production-viable with the medium findings representing improvement opportunities rather than blockers.
