# Re-Audit 3: Orchestration + Core Modules (2026-02-28)

Third-pass audit of 21 files (7 orchestration, 14 core) against categories A-R. Verifies fixes from the second re-audit, then identifies any remaining or newly introduced CRITICAL, HIGH, and MEDIUM findings. Every finding includes a specific, reproducible trigger scenario.

**Previous audit (reaudit2)** reported:
- Orchestration: 0 CRITICAL, 1 HIGH (O-1), 3 MEDIUM (P-1, P-2, B-1)
- Core: 0 CRITICAL, 1 HIGH (F2), 5 MEDIUM (F1, F3, F4, F5, F7)

---

## Verification of Previously Reported Fixes

### Orchestration Fixes

| # | Previous Finding | Status | Evidence |
|---|------------------|--------|----------|
| P-1 | pipeline.py: TOCTOU gap between `reload()` and `save_state()` in `_finalize_phase` — `StateLock` covered only `reload()` | **FIXED** | Lines 659-672: `with lock:` now wraps the full sequence: `reload()`, `_ensure_closeout_exists()`, `mark_phase_complete(auto_save=False)`, and `set_current_phase(None)`. |
| P-2 | pipeline.py: Double `save_state()` in `_finalize_phase` — crash between two saves leaves `current_phase` stale | **FIXED** | Line 669: `mark_phase_complete` called with `auto_save=False`. Line 672: `set_current_phase(None)` saves both mutations atomically in a single `save_state()` call. |
| O-1 | pre_task_validation.py: `auto_cleanup()` creates garbage directories for `.csv`, `.db`, `.sqlite`, `.sql`, `.ipynb` | **FIXED** | Lines 46-52: `FORBIDDEN_TYPES` now uses clean relative path strings (`"../data/"`, `"../migrations/"`, `"../notebooks/"`) instead of prose descriptions with "or" alternatives. The `split("(")[0].strip()` on line 309 works correctly with these paths. |
| B-1 | backtrack.py: Backtrack-in-progress marker written but never checked on startup | **PARTIALLY FIXED** | Lines 388-399: The marker IS checked within `backtrack_to()` itself — a subsequent backtrack warns about the stale marker. However, no check exists at pipeline startup (`main.py` or `PhasePipeline.__init__`). If the user runs `main.py run N` after an interrupted backtrack (without running another backtrack first), the inconsistent state goes undetected. The comment on line 491 claims "checked at startup" but this is inaccurate. |

### Core Fixes

| # | Previous Finding | Status | Evidence |
|---|------------------|--------|----------|
| F1 | audit.py: `_audit_report_filename()` produces empty/colliding filenames for all-special-char `audit_id` | **FIXED** | Lines 803-807: Fallback added — `safe_id` defaults to `"audit-unknown"` and `safe_name` defaults to `"unnamed"` when sanitization produces empty strings. |
| F2 | state.py: `StateTransaction.__exit__()` does not handle `commit()` failures — half-committed state | **FIXED** | Lines 284-289: Success path now wraps `self.commit()` in `try/except Exception`, calls `self.rollback()` on failure, then re-raises. |
| F3 | router.py: Circuit breaker cooldown-expiry reset in `_is_provider_available()` races with `_record_failure()` | **FIXED** | Lines 526-540: `_is_provider_available()` now holds `self._stats_lock` via `with self._stats_lock:` during the cooldown check and reset. |
| F4 | invoke.py: Corrupted `session-tokens.json` causes permanent token tracking failure | **FIXED** | Lines 270-276: `json.loads` failure is caught with `except (json.JSONDecodeError, ValueError)`, resets `data` to `dict(_empty_data)`, and logs a warning. The write-back at lines 323-325 overwrites the corrupt file with clean data (self-healing). |
| F5 | ollama.py: SSRF hostname validation bypassed via DNS rebinding | **NO CHANGE** | The DNS rebinding limitation remains documented in the docstring (lines 120-126). The `_PRIVATE_IP_RE` (lines 101-111) catches IP-literal URLs pointing at private ranges. Since the host config comes from admin-controlled config/env vars, this is a known, documented defense-in-depth limitation. Not re-reported (no change in risk profile). |
| F7 | graph/manager.py: `load_agents_from_manifest()` count-based idempotency check fails on manifest changes | **FIXED** | Lines 207-222: SHA-256 content hash (`hashlib.sha256` of JSON-serialized agents) stored in `.agent-manifest.hash` file. When count matches but hash differs, agents are reloaded. |

---

## Files Audited

### Orchestration (7 files)
1. `orchestration/pipeline.py`
2. `orchestration/backtrack.py`
3. `orchestration/task_display.py`
4. `orchestration/task_memory.py`
5. `orchestration/pre_task_validation.py`
6. `orchestration/dashboard_sync.py`
7. `orchestration/memory_enrichment.py`

### Core (14 files)
8. `core/state.py`
9. `core/audit.py`
10. `core/memory/__init__.py`
11. `core/config.py`
12. `core/ui.py`
13. `core/subprocess_runner.py`
14. `core/llm/router.py`
15. `core/llm/invoke.py`
16. `core/llm/anthropic.py`
17. `core/llm/bedrock.py`
18. `core/llm/ollama.py`
19. `core/graph/connection.py`
20. `core/graph/manager.py`
21. `core/graph/writer.py`

---

## New Findings

### 1. orchestration/backtrack.py

| # | Cat | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|---|-----|----------|---------|---------|------------------|----------------|
| R3-1 | F (State) | HIGH | `_clear_memory()` calls `memory_init()` without arguments (line 286). When memory has not been previously initialized (fresh process), `memory_init()` defaults `state_dir` to `Path.cwd() / ".state"` (core/memory/__init__.py line 50). If the user's CWD is not the atomic-claude root, the memory system initializes with the wrong state directory. `memory_handle_backtrack(phase)` then operates on the wrong memory store — either a non-existent directory (silent no-op) or a different project's memory (data corruption). The module already has `atomic_root = Path(__file__).resolve().parent.parent` at line 27 and uses it for artifact and file operations (lines 292, 300), but does not pass it to `memory_init()`. When called from `pipeline.py` (line 782), memory is initialized correctly before `backtrack_to()` is invoked, so the `_initialized` guard makes the no-args call a no-op. But when called directly from `main.py` (line 92), no prior initialization occurs. | User runs `cd ~ && python /path/to/atomic-claude/main.py backtrack 3` from their home directory. Process starts fresh (no prior `memory_init` call). `_clear_memory()` calls `memory_init()` without args. `state_dir` defaults to `/home/user/.state/` (CWD). `MemoryStore` initializes pointing at `/home/user/.state/memory/`. `memory_handle_backtrack(3)` silently operates on this directory (likely empty), skipping cleanup of the actual memory at `/path/to/atomic-claude/.state/memory/`. The file-based cleanup on lines 292-303 works correctly (uses `atomic_root`), but the in-memory `MemoryStore` singleton is now permanently initialized with the wrong path for the rest of the process. | Change line 286 to: `memory_init(atomic_root / ".state")`. This matches the pattern used in `pipeline.py` line 645 and line 782. |

---

### 2. orchestration/pipeline.py

No new actionable findings.

Previous findings P-1 and P-2 are verified fixed. The `_finalize_phase` method now correctly wraps reload + mark_phase_complete + set_current_phase under a single `StateLock` scope (lines 659-672). The recursive `_handle_phase_transition` (line 588) is bounded by the 10-phase limit (phases 0-9), well within Python's default recursion limit of 1000.

---

### 3. orchestration/task_display.py

No actionable findings.

---

### 4. orchestration/task_memory.py

No actionable findings.

---

### 5. orchestration/pre_task_validation.py

No new actionable findings. Previous finding O-1 is verified fixed.

---

### 6. orchestration/dashboard_sync.py

No actionable findings.

---

### 7. orchestration/memory_enrichment.py

No actionable findings.

---

### 8. core/state.py

| # | Cat | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|---|-----|----------|---------|---------|------------------|----------------|
| R3-2 | P (Data Integrity) | MEDIUM | `save_state()` uses `shutil.move(temp_path, self.state_file)` (line 435) instead of `os.replace()`. While `tempfile.mkstemp(dir=self.state_dir)` (line 423-424) creates the temp file in the same directory as the state file — making `shutil.move` use `os.rename` (atomic) on the same filesystem — this is an implicit invariant. If `self.state_dir` is a symlink to a different filesystem, or if a future refactor changes the temp directory, `shutil.move` silently falls back to `shutil.copy2` + `os.unlink` (non-atomic). This is a correctness risk: a crash during the copy phase would leave a partially-written state file, corrupting the pipeline state. Other atomic write sites in the codebase (`pipeline.py` line 711, `backtrack.py` line 496, `dashboard_sync.py` line 163) correctly use `os.replace()`. | Mount `.state/` as a symlink to a directory on a different filesystem (e.g., NFS or a USB drive for backups). `tempfile.mkstemp(dir=self.state_dir)` creates the temp file on the remote filesystem (correct directory, same mount). `shutil.move(temp_path, self.state_file)` detects same-filesystem and uses `os.rename` — this works. But if `state_dir` is a regular directory while `state_file` is a symlink to a different filesystem, `shutil.move` falls back to copy+delete. A SIGKILL during the copy leaves a truncated `task-state.json`. On next startup, `load_state()` (line 392) catches `json.JSONDecodeError` and returns empty state, losing all progress. | Replace `shutil.move(temp_path, self.state_file)` with `os.replace(temp_path, self.state_file)` on line 435 to match the atomic write pattern used elsewhere in the codebase. `os.replace` is atomic on POSIX (same filesystem) and raises `OSError` on cross-device rather than silently falling back to copy+delete. |

---

### 9. core/audit.py

No new actionable findings. Previous finding F1 is verified fixed.

---

### 10. core/memory/__init__.py

| # | Cat | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|---|-----|----------|---------|---------|------------------|----------------|
| R3-3 | F (State) | MEDIUM | The `_initialized` singleton guard (line 46) silently ignores subsequent `memory_init()` calls with different `state_dir` parameters. Once `memory_init(path_A)` succeeds, `memory_init(path_B)` returns immediately without warning, and all subsequent memory operations use `path_A`. This interacts with the backtrack bug (R3-1): if the pipeline initializes memory with the correct path, the backtrack's no-args call is harmlessly ignored. But if backtrack runs first in a fresh process with the wrong default path, the subsequent pipeline call to `memory_init(correct_path)` is also silently ignored, and the pipeline's memory operations use the wrong path for the entire session. | 1) Start a fresh process. 2) Call `backtrack_to(3)` from `main.py`. `_clear_memory` calls `memory_init()` with no args — initializes with `CWD/.state/`. 3) Later in the same process, pipeline calls `memory_init(atomic_root / ".state")`. The `_initialized` guard returns immediately. 4) `memory_checkpoint()`, `memory_add()`, and `memory_recall()` all operate on `CWD/.state/` instead of `atomic_root/.state/`. Memory data is written to the wrong location for the rest of the session. | Add a warning log when `memory_init()` is called with a different `state_dir` than the already-initialized path. Alternatively, store the initialized `state_dir` and raise `ValueError` if a subsequent call provides a conflicting path. This makes the silent-ignore behavior explicit and diagnosable. |

---

### 11. core/config.py

No actionable findings.

---

### 12. core/ui.py

No actionable findings.

---

### 13. core/subprocess_runner.py

No actionable findings.

---

### 14. core/llm/router.py

No new actionable findings. Previous finding F3 is verified fixed.

---

### 15. core/llm/invoke.py

No new actionable findings. Previous finding F4 is verified fixed.

---

### 16. core/llm/anthropic.py

No actionable findings.

---

### 17. core/llm/bedrock.py

No actionable findings.

---

### 18. core/llm/ollama.py

No new actionable findings. The DNS rebinding limitation (F5) is unchanged and documented. The `_PRIVATE_IP_RE` provides defense-in-depth for IP-literal URLs.

---

### 19. core/graph/connection.py

No actionable findings.

---

### 20. core/graph/manager.py

No new actionable findings. Previous finding F7 is verified fixed.

---

### 21. core/graph/writer.py

No actionable findings.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 2 |
| **Total** | **3** |

### HIGH Findings (1)

1. **R3-1 -- orchestration/backtrack.py line 286**: `_clear_memory()` calls `memory_init()` without arguments, defaulting to `Path.cwd() / ".state"` instead of `atomic_root / ".state"`. When invoked directly from `main.py` (not via pipeline), and CWD differs from the atomic-claude root, the memory system initializes with the wrong state directory. Memory cleanup during backtrack silently targets the wrong location, and the `_initialized` singleton guard prevents correction for the rest of the process. Fix: pass `atomic_root / ".state"` as the argument.

### MEDIUM Findings (2)

1. **R3-2 -- core/state.py line 435**: `save_state()` uses `shutil.move()` instead of `os.replace()` for the atomic rename step. While same-filesystem operation is guaranteed by the current `tempfile.mkstemp(dir=self.state_dir)` call, `shutil.move` silently falls back to non-atomic copy+delete on cross-device scenarios, unlike `os.replace` which raises an explicit error. Other atomic write sites in the codebase correctly use `os.replace()`.

2. **R3-3 -- core/memory/__init__.py line 46**: The `_initialized` singleton guard silently ignores subsequent `memory_init()` calls with different `state_dir` parameters. Combined with R3-1, if backtrack initializes memory with the wrong default path first, the pipeline's subsequent correct initialization is silently discarded. No warning or error is logged.

### Previously Reported Findings — Status

| # | Status | Summary |
|---|--------|---------|
| P-1 | **FIXED** | pipeline.py TOCTOU gap in `_finalize_phase` — lock now covers full sequence |
| P-2 | **FIXED** | pipeline.py double `save_state()` — `auto_save=False` eliminates double write |
| O-1 | **FIXED** | pre_task_validation.py garbage directories — `FORBIDDEN_TYPES` uses clean paths |
| B-1 | **PARTIALLY FIXED** | backtrack.py marker checked within `backtrack_to()` but not at pipeline startup |
| F1 | **FIXED** | audit.py empty filename — fallback values added |
| F2 | **FIXED** | state.py `StateTransaction.__exit__()` — rollback on commit failure |
| F3 | **FIXED** | router.py circuit breaker race — `_stats_lock` now covers the reset |
| F4 | **FIXED** | invoke.py corrupted tokens file — self-healing with `_empty_data` reset |
| F5 | **NO CHANGE** | ollama.py DNS rebinding — documented limitation, defense-in-depth |
| F7 | **FIXED** | manager.py count-based idempotency — SHA-256 hash comparison added |

### Files With No Actionable Findings

- `orchestration/pipeline.py` — All previous findings fixed. No new issues.
- `orchestration/task_display.py` — No actionable findings.
- `orchestration/task_memory.py` — No actionable findings.
- `orchestration/pre_task_validation.py` — Previous finding fixed. No new issues.
- `orchestration/dashboard_sync.py` — No actionable findings.
- `orchestration/memory_enrichment.py` — No actionable findings.
- `core/audit.py` — Previous finding fixed. No new issues.
- `core/config.py` — No actionable findings.
- `core/ui.py` — No actionable findings.
- `core/subprocess_runner.py` — No actionable findings.
- `core/llm/router.py` — Previous finding fixed. No new issues.
- `core/llm/invoke.py` — Previous finding fixed. No new issues.
- `core/llm/anthropic.py` — No actionable findings.
- `core/llm/bedrock.py` — No actionable findings.
- `core/llm/ollama.py` — No new findings. Known DNS rebinding limitation documented.
- `core/graph/connection.py` — No actionable findings.
- `core/graph/manager.py` — Previous finding fixed. No new issues.
- `core/graph/writer.py` — No actionable findings.
