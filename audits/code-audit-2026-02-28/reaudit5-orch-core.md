# Re-Audit 5: Orchestration + Core Modules (2026-02-28)

Fifth-pass audit of 21 files (7 orchestration, 14 core) against categories A-R. Verifies fixes from the fourth re-audit (pass 5), then identifies any remaining or newly introduced CRITICAL, HIGH, and MEDIUM findings. Every finding includes a specific, reproducible trigger scenario.

**Previous audit (reaudit4)** reported:
- 0 CRITICAL, 0 HIGH, 1 MEDIUM (B-1 carried forward)
- All 3 fixes from pass 4 (R3-1, R3-2, R3-3) confirmed FIXED
- Zero new findings across 21 files

**Fix claimed since pass 5**: pipeline.py `run_phase()` backtrack-in-progress marker check at startup.

---

## Verification of Fix Claimed Since Pass 5

### B-1 -- Backtrack-in-progress marker not checked at startup

| Field | Detail |
|-------|--------|
| **Claimed fix** | `pipeline.py` `run_phase()` now checks for `backtrack-in-progress` marker before phase validation |
| **Verification result** | **NOT FIXED** |
| **Evidence** | `pipeline.py` `run_phase()` (lines 491-554) contains no reference to `backtrack-in-progress`. A `grep` for `backtrack-in-progress` and `backtrack_marker` in `pipeline.py` returns zero matches. The method proceeds directly from the docstring to `self.validator.validate_phase(phase_num)` at line 511. The marker is still only checked within `backtrack_to()` in `backtrack.py` (lines 388-399). |

The fix was not applied. B-1 remains in its previously reported PARTIALLY FIXED state.

### Previously Reported Findings -- Cumulative Status

| # | Origin | Status | Summary |
|---|--------|--------|---------|
| P-1 | Pass 2 | **FIXED** (verified pass 4) | pipeline.py TOCTOU gap in `_finalize_phase` -- lock now covers full sequence |
| P-2 | Pass 2 | **FIXED** (verified pass 4) | pipeline.py double `save_state()` -- `auto_save=False` eliminates double write |
| O-1 | Pass 2 | **FIXED** (verified pass 4) | pre_task_validation.py garbage directories -- `FORBIDDEN_TYPES` uses clean paths |
| B-1 | Pass 1 | **PARTIALLY FIXED** (unchanged since pass 3) | backtrack.py marker checked within `backtrack_to()` but not at pipeline startup (see below) |
| F1 | Pass 3 | **FIXED** (verified pass 4) | audit.py empty filename -- fallback values added |
| F2 | Pass 3 | **FIXED** (verified pass 4) | state.py `StateTransaction.__exit__()` -- rollback on commit failure |
| F3 | Pass 3 | **FIXED** (verified pass 4) | router.py circuit breaker race -- `_stats_lock` now covers the reset |
| F4 | Pass 3 | **FIXED** (verified pass 4) | invoke.py corrupted tokens file -- self-healing with `_empty_data` reset |
| F5 | Pass 3 | **NO CHANGE** (documented limitation) | ollama.py DNS rebinding -- documented limitation, defense-in-depth |
| F7 | Pass 3 | **FIXED** (verified pass 4) | manager.py count-based idempotency -- SHA-256 hash comparison added |
| R3-1 | Pass 4 | **FIXED** (verified pass 5) | backtrack.py `memory_init()` now passes `atomic_root / ".state"` |
| R3-2 | Pass 4 | **FIXED** (verified pass 5) | state.py `os.replace()` replaces `shutil.move()` |
| R3-3 | Pass 4 | **FIXED** (verified pass 5) | memory/__init__.py logs warning on conflicting `state_dir` |

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

No new CRITICAL, HIGH, or MEDIUM findings were identified in this pass.

All previously verified fixes remain correctly implemented with no regressions. The only open item is B-1, which was claimed fixed but the fix was not applied to the source file.

---

## Carried-Forward Finding

### B-1 -- orchestration/backtrack.py + orchestration/pipeline.py: Backtrack-in-progress marker not checked at startup

| Field | Detail |
|-------|--------|
| **Category** | F (State) |
| **Severity** | MEDIUM |
| **Origin** | Pass 1 (orchestration-modules.md, finding L2) |
| **Status** | PARTIALLY FIXED since pass 3 (unchanged through pass 6) |
| **Files** | `orchestration/backtrack.py` lines 388-399, 468-475, 507-510; `orchestration/pipeline.py` lines 491-554 |

**Description**: The `backtrack-in-progress` marker file (`<atomic_root>/.state/backtrack-in-progress`) is written at backtrack.py line 469 before cleanup begins and removed in the `finally` block at line 509. Within `backtrack_to()` itself, lines 388-399 check for a stale marker from a previous interrupted run and print a warning before proceeding.

However, no check exists at pipeline startup. The `PhasePipeline.run_phase()` method (pipeline.py line 491) proceeds directly to phase validation without inspecting the marker. If the user runs `python main.py run N` after an interrupted backtrack (without running another backtrack first), the inconsistent state goes undetected. The comment on backtrack.py line 491 reads "checked on the next backtrack_to() call" -- this is accurate for the current implementation but does not address the startup gap.

**Trigger scenario**: (1) Run `python main.py backtrack 3`. (2) Send SIGKILL during step 2 (artifact deletion) after some files are deleted but before the state file is atomically written in step 4 (line 496). (3) The `finally` block does not execute (SIGKILL is untrappable). The `backtrack-in-progress` marker remains on disk. (4) Run `python main.py run 4`. Pipeline starts with no warning. The state file still reflects the pre-backtrack state (e.g., phases 4-9 marked as completed) but some artifacts for those phases have been deleted. Tasks that depend on those artifacts will fail with confusing `FileNotFoundError`s rather than a clear "interrupted backtrack" diagnostic.

**Recommendation**: Add a check at the top of `PhasePipeline.run_phase()` (before the `validate_phase()` call on line 511) that reads `self.atomic_root / ".state" / "backtrack-in-progress"`. If the marker exists, print a prominent warning with the marker contents (target phase, start time) and either (a) refuse to proceed until the user runs another backtrack to complete the interrupted operation, or (b) print instructions for how to resolve the inconsistency. The marker infrastructure is already fully in place in `backtrack.py`; the fix is a single check at startup.

**Risk assessment**: The severity remains MEDIUM because it requires an untrappable signal (SIGKILL or power loss) during a narrow window (between artifact deletion and state write), and the consequences (confusing errors rather than data loss) are limited.

---

## Per-File Analysis

### 1. orchestration/pipeline.py

No new actionable findings. All previous findings (P-1, P-2) remain fixed. The `_finalize_phase` method correctly wraps `reload()`, `mark_phase_complete(auto_save=False)`, and `set_current_phase(None)` under a single `StateLock` scope. The recursive `_handle_phase_transition` is bounded by the 10-phase limit (phases 0-9). B-1 remains open: `run_phase()` (line 491) does not check for the `backtrack-in-progress` marker.

### 2. orchestration/backtrack.py

No new actionable findings beyond the carried-forward B-1. The R3-1 fix (`memory_init(atomic_root / ".state")` on line 286) remains correctly implemented. The atomic state write pattern (lines 492-502) uses `tempfile.mkstemp` + `os.replace` correctly. The within-function marker check (lines 388-399) is functional. The comment on line 491 accurately describes the current behavior.

### 3. orchestration/task_display.py

No actionable findings.

### 4. orchestration/task_memory.py

No actionable findings.

### 5. orchestration/pre_task_validation.py

No new actionable findings. Previous finding O-1 remains fixed.

### 6. orchestration/dashboard_sync.py

No actionable findings.

### 7. orchestration/memory_enrichment.py

No actionable findings.

### 8. core/state.py

No new actionable findings. The R3-2 fix (`os.replace` on line 435) remains correctly implemented. The `StateTransaction.__exit__` rollback-on-commit-failure (F2 fix) remains correct.

### 9. core/audit.py

No new actionable findings. The F1 fix (fallback values for empty filenames, lines 800-808) remains correct. Path traversal protection in `_safe_write` (lines 1322-1325) and `_apply_remediation` (line 1358) correctly validates that resolved paths stay within their respective root directories using `is_relative_to()`. The `_audit_report_filename` function (lines 798-808) properly sanitizes both `audit_id` and `audit_name` with regex substitution and provides non-empty fallback values.

### 10. core/memory/__init__.py

No new actionable findings. The R3-3 fix (warning log on conflicting `state_dir`, lines 51-59) remains correctly implemented. The `_initialized_state_dir` tracking variable (line 37) is properly set (line 65) after path resolution.

### 11. core/config.py

No actionable findings.

### 12. core/ui.py

No actionable findings.

### 13. core/subprocess_runner.py

No actionable findings.

### 14. core/llm/router.py

No new actionable findings. The F3 fix (`_stats_lock` covering cooldown check and reset) remains correct.

### 15. core/llm/invoke.py

No new actionable findings. The F4 fix (corrupted tokens file self-healing) remains correct.

### 16. core/llm/anthropic.py

No actionable findings.

### 17. core/llm/bedrock.py

No actionable findings.

### 18. core/llm/ollama.py

No new actionable findings. The DNS rebinding limitation (F5) is unchanged and documented.

### 19. core/graph/connection.py

No actionable findings.

### 20. core/graph/manager.py

No new actionable findings. The F7 fix (SHA-256 hash-based idempotency for agent manifest loading) remains correct.

### 21. core/graph/writer.py

No actionable findings.

---

## Summary

| Severity | New | Carried Forward | Total |
|----------|-----|-----------------|-------|
| CRITICAL | 0 | 0 | 0 |
| HIGH | 0 | 0 | 0 |
| MEDIUM | 0 | 1 | 1 |
| **Total** | **0** | **1** | **1** |

### Carried-Forward Findings (1)

1. **B-1 (MEDIUM) -- orchestration/pipeline.py**: Backtrack-in-progress marker is checked within `backtrack_to()` itself (backtrack.py lines 388-399) but not at pipeline startup (`PhasePipeline.run_phase()`). If the process is killed during a backtrack, the marker persists on disk but is not detected when the user next runs a phase. The fix claimed for this pass was not applied to the source file.

### All Previous Findings -- Final Status

All 10 fixes from passes 1-5 (P-1, P-2, O-1, F1, F2, F3, F4, F7, R3-1, R3-2, R3-3) remain correctly implemented with no regressions. F5 (ollama.py DNS rebinding) remains a documented limitation. The only remaining open item across all 6 passes is B-1 (MEDIUM), which has been partially fixed since pass 3 and requires a startup check in `pipeline.py` to fully resolve.

### Audit Convergence

This audit identifies **zero new findings** across 21 files for the second consecutive pass. All previously applied fixes have been verified as correct and regression-free. The codebase's orchestration and core modules have converged to a stable state where only one MEDIUM-severity item (B-1) remains open. The fix for B-1 was not applied despite being claimed; the implementation gap is precisely defined (add a marker file check at the top of `PhasePipeline.run_phase()`) and can be completed in a single code change.
