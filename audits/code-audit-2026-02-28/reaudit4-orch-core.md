# Re-Audit 4: Orchestration + Core Modules (2026-02-28)

Fourth-pass audit of 21 files (7 orchestration, 14 core) against categories A-R. Verifies fixes from the third re-audit (pass 4), then identifies any remaining or newly introduced CRITICAL, HIGH, and MEDIUM findings. Every finding includes a specific, reproducible trigger scenario.

**Previous audit (reaudit3)** reported:
- 0 CRITICAL, 1 HIGH (R3-1), 2 MEDIUM (R3-2, R3-3)
- B-1 carried forward as PARTIALLY FIXED

---

## Verification of Previously Reported Fixes

### Fixes Applied Since Pass 4

| # | Previous Finding | Status | Evidence |
|---|------------------|--------|----------|
| R3-1 | backtrack.py line 286: `memory_init()` called without arguments, defaulting to `CWD/.state/` instead of `atomic_root/.state/` | **FIXED** | Line 286 now reads `memory_init(atomic_root / ".state")`. The correct project root directory is passed explicitly, matching the pattern in `pipeline.py` line 645. |
| R3-2 | state.py line 435: `shutil.move()` used instead of `os.replace()` for atomic rename | **FIXED** | Line 435 now reads `os.replace(temp_path, self.state_file)`. Comment on line 434 updated to: `"Atomic rename (os.replace is atomic on POSIX same-filesystem)"`. This matches the atomic write pattern used in `backtrack.py` line 496, `pipeline.py` line 711, and `dashboard_sync.py` line 163. |
| R3-3 | memory/__init__.py: `_initialized` singleton guard silently ignores subsequent `memory_init()` calls with different `state_dir` | **FIXED** | Line 37 adds `_initialized_state_dir: Optional[Path] = None`. Lines 51-59: when `_initialized` is True and a different `state_dir` is provided, the resolved paths are compared and a `logger.warning()` is emitted with both the new and old paths. Line 65 stores the resolved `state_dir` for future comparison. The warning makes the silent-ignore behavior diagnosable. |

### Previously Reported Findings — Cumulative Status

| # | Origin | Status | Summary |
|---|--------|--------|---------|
| P-1 | Pass 2 | **FIXED** (verified pass 4) | pipeline.py TOCTOU gap in `_finalize_phase` — lock now covers full sequence |
| P-2 | Pass 2 | **FIXED** (verified pass 4) | pipeline.py double `save_state()` — `auto_save=False` eliminates double write |
| O-1 | Pass 2 | **FIXED** (verified pass 4) | pre_task_validation.py garbage directories — `FORBIDDEN_TYPES` uses clean paths |
| B-1 | Pass 1 | **PARTIALLY FIXED** (unchanged since pass 4) | backtrack.py marker checked within `backtrack_to()` but not at pipeline startup (see below) |
| F1 | Pass 3 | **FIXED** (verified pass 4) | audit.py empty filename — fallback values added |
| F2 | Pass 3 | **FIXED** (verified pass 4) | state.py `StateTransaction.__exit__()` — rollback on commit failure |
| F3 | Pass 3 | **FIXED** (verified pass 4) | router.py circuit breaker race — `_stats_lock` now covers the reset |
| F4 | Pass 3 | **FIXED** (verified pass 4) | invoke.py corrupted tokens file — self-healing with `_empty_data` reset |
| F5 | Pass 3 | **NO CHANGE** (documented limitation) | ollama.py DNS rebinding — documented limitation, defense-in-depth |
| F7 | Pass 3 | **FIXED** (verified pass 4) | manager.py count-based idempotency — SHA-256 hash comparison added |
| R3-1 | Pass 4 | **FIXED** (verified this pass) | backtrack.py `memory_init()` now passes `atomic_root / ".state"` |
| R3-2 | Pass 4 | **FIXED** (verified this pass) | state.py `os.replace()` replaces `shutil.move()` |
| R3-3 | Pass 4 | **FIXED** (verified this pass) | memory/__init__.py logs warning on conflicting `state_dir` |

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

All three fixes from pass 4 are correctly implemented and introduce no regressions. The remaining open item (B-1) is unchanged from the previous assessment and is carried forward below.

---

## Carried-Forward Finding

### B-1 — orchestration/backtrack.py: Backtrack-in-progress marker not checked at startup

| Field | Detail |
|-------|--------|
| **Category** | F (State) |
| **Severity** | MEDIUM |
| **Origin** | Pass 1 (orchestration-modules.md, finding L2) |
| **Status** | PARTIALLY FIXED since pass 3 |
| **File** | `orchestration/backtrack.py` |
| **Lines** | 388-399 (within-function check), 468-475 (marker write), 507-510 (marker cleanup) |

**Description**: The `backtrack-in-progress` marker file (`<atomic_root>/.state/backtrack-in-progress`) is written at line 469 before cleanup begins and removed in the `finally` block at line 509. Within `backtrack_to()` itself, lines 388-399 check for a stale marker from a previous interrupted run and print a warning before proceeding.

However, no check exists at pipeline startup. Neither `main.py`'s `main()` function nor `PhasePipeline.__init__()` (pipeline.py line 474) inspects the marker. If the user runs `python main.py run N` after an interrupted backtrack (without running another backtrack first), the inconsistent state goes undetected. The comment on line 491 claims the marker is "checked at startup" -- this remains inaccurate.

**Trigger scenario**: (1) Run `python main.py backtrack 3`. (2) Send SIGKILL during step 2 (artifact deletion) after some files are deleted but before the state file is atomically written in step 4 (line 496). (3) The `finally` block does not execute (SIGKILL is untrappable). The `backtrack-in-progress` marker remains on disk. (4) Run `python main.py run 4`. Pipeline starts with no warning. The state file still reflects the pre-backtrack state (e.g., phases 4-9 marked as completed) but some artifacts for those phases have been deleted. Tasks that depend on those artifacts will fail with confusing `FileNotFoundError`s rather than a clear "interrupted backtrack" diagnostic.

**Recommendation**: Add a startup check in `PhasePipeline.__init__()` or `PhasePipeline.run_phase()` that reads `<atomic_root>/.state/backtrack-in-progress`. If the marker exists, print a prominent warning with the marker contents (target phase, start time) and either (a) refuse to proceed until the user runs another backtrack to complete the interrupted operation, or (b) offer to auto-resume the backtrack. The check should run before any phase execution logic.

**Risk assessment**: The severity remains MEDIUM because it requires an untrappable signal (SIGKILL or power loss) during a narrow window (between artifact deletion and state write), and the consequences (confusing errors rather than data loss) are limited. The marker infrastructure is already in place; the fix is a single check at startup.

---

## Per-File Analysis

### 1. orchestration/pipeline.py

No new actionable findings. All previous findings (P-1, P-2) remain fixed. The `_finalize_phase` method correctly wraps `reload()`, `mark_phase_complete(auto_save=False)`, and `set_current_phase(None)` under a single `StateLock` scope (lines 659-672). The recursive `_handle_phase_transition` (line 588) is bounded by the 10-phase limit (phases 0-9).

### 2. orchestration/backtrack.py

No new actionable findings beyond the carried-forward B-1. The R3-1 fix (`memory_init(atomic_root / ".state")` on line 286) is correctly implemented. The atomic state write pattern (lines 492-502) uses `tempfile.mkstemp` + `os.replace` correctly.

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

No new actionable findings. The R3-2 fix (`os.replace` on line 435) is correctly implemented. The `StateTransaction.__exit__` rollback-on-commit-failure (F2 fix) remains correct.

### 9. core/audit.py

No new actionable findings. The F1 fix (fallback values for empty filenames) remains correct.

### 10. core/memory/__init__.py

No new actionable findings. The R3-3 fix (warning log on conflicting `state_dir`, lines 51-59) is correctly implemented. The `_initialized_state_dir` tracking variable (line 37) is properly set (line 65) after resolution.

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

No new actionable findings. The DNS rebinding limitation (F5) is unchanged and documented in the docstring (lines 120-126).

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

1. **B-1 (MEDIUM) -- orchestration/backtrack.py**: Backtrack-in-progress marker is checked within `backtrack_to()` itself (lines 388-399) but not at pipeline startup (`main.py` or `PhasePipeline.__init__`). If the process is killed during a backtrack, the marker persists on disk but is not detected when the user next runs a phase. The inaccurate comment on line 491 ("checked at startup") remains unchanged.

### All Previous Findings — Final Status

All 3 findings from pass 4 (R3-1 HIGH, R3-2 MEDIUM, R3-3 MEDIUM) are confirmed **FIXED** in this pass. The only remaining open item across all 5 passes is B-1 (MEDIUM), which has been partially fixed since pass 3 and requires a startup check to fully resolve.

### Audit Convergence

This audit identifies **zero new findings** across 21 files. All fixes applied between passes have been verified as correct and regression-free. The codebase's orchestration and core modules have converged to a state where only one MEDIUM-severity item (B-1) remains open. This suggests the audit cycle for these 21 files is nearing completion.
