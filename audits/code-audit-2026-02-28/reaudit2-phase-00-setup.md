# Re-Audit 2: Phase 00 Setup
**Date:** 2026-02-28
**Scope:** 6 files in phases/phase00/ and phases/phase_00_setup/tasks/
**Audit Categories:** A-R (full checklist)
**Severity Threshold:** CRITICAL, HIGH, MEDIUM only
**Previous Audit:** reaudit-phase-00-setup.md (same date)

---

## Previously Reported Findings -- Disposition

All 8 findings from the previous audit were reviewed. Six have been fixed:

| # | File | Previous Finding | Status |
|---|------|-----------------|--------|
| 1 | task_001 (lines 591-601) | Dashboard port-in-use check missing | **FIXED** -- port check added before spawn |
| 2 | task_002 (lines 343, 407-469) | `.gitignore` not verified before writing API key | **FIXED** -- `_ensure_env_gitignored()` added, called before `.env` write |
| 3 | task_003 (line 298-303, 1272) | `_run_wizard` returns `"RESTART"` string, violating type contract | **STILL PRESENT** -- re-assessed below |
| 4 | task_003 (line 873) | `atomic_root` re-derived from env/cwd instead of parameter | **FIXED** -- `atomic_root` now threaded through as parameter |
| 5 | task_003 (lines 1609, 1627) | Same `atomic_root` re-derivation in `_apply_auto_defaults` | **FIXED** -- `atomic_root` now accepted as parameter with fallback |
| 6 | task_004 (lines 1241-1249) | `_find_files` substring matching for exclusion patterns | **PARTIALLY FIXED** -- short patterns now use `f.parts` matching (correct), but absolute-path exclusions are broken (see new finding) |
| 7 | task_004 (lines 412-414) | `_scan_source_code` substring matching post-filter | **FIXED** -- now uses `part in (...) for part in f.parts` |
| 8 | task_005 (line 1024) | `_show_summary` reads report file without error handling | **FIXED** -- now wrapped in try/except with fallback |

---

## 1. phases/phase00/orchestrator00.py

No actionable findings.

---

## 2. phases/phase_00_setup/tasks/task_001_environment_bootstrap.py

No actionable findings. The previous dashboard orphan-process finding has been fixed with a port-in-use check (lines 591-601). Global counter state is reset at the top of `execute()` and only used within that call chain.

---

## 3. phases/phase_00_setup/tasks/task_002_provider_detection.py

No actionable findings. The previous `.gitignore` finding has been fixed with `_ensure_env_gitignored()` (lines 285-293).

---

## 4. phases/phase_00_setup/tasks/task_003_setup_wizard.py

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| E (Data flow) | MEDIUM | `_run_wizard` returns the literal string `"RESTART"` (line 1275) as a sentinel value, but its return type annotation is `Optional[Dict[str, Any]]`. The caller at lines 298-300 compares `config == "RESTART"` in a while loop. After the loop, if `config` is not None and not `"RESTART"`, it is passed to `_save_config()` which calls `json.dumps(config, indent=2)`. The type violation means static analysis tools and IDE autocomplete are unreliable for this function. While the current runtime behavior is correct (the while loop only exits when config is a dict or None), any future refactoring that introduces a new non-dict truthy return value would silently pass through to `_save_config` and crash. | 298-300, 644, 1275 | User declines configuration at step 10 (enters "n"), `_run_wizard` returns `"RESTART"`, loop restarts. After approval, returns a dict, loop exits, `_save_config` receives the dict. The type annotation mismatch means mypy/pyright would flag the `config.get("project")` call at line 306 as a potential error on `str`. If someone adds a new sentinel return like `"SKIP"`, the while loop exits and `_save_config` crashes on `json.dumps("SKIP")`. | Use a dedicated sentinel constant (`_RESTART = object()`) or restructure the loop inside `_run_wizard`. |

Previously reported as HIGH, downgraded to MEDIUM because: the current code path works correctly at runtime, the string sentinel is documented in a comment (line 297), and the failure mode requires a code change (adding a new non-dict return) rather than a user action. The risk is a maintenance trap, not a runtime bug in current code.

---

## 5. phases/phase_00_setup/tasks/task_004_material_scan.py

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| A (Logic) | HIGH | `_find_files` exclusion of absolute directory paths is silently broken. At line 106, `exclude_dirs` is set to `[str(atomic_root)]` -- a full absolute path like `"/home/user/project/atomic-claude"`. This is passed to `_find_files` and appended to `exclude_patterns` at line 1245. The check at line 1250 uses `any(excl in f.parts for excl in exclude_patterns)`. However, `f.parts` contains individual path components (e.g., `('/', 'home', 'user', 'project', 'atomic-claude', 'core', 'main.py')`), and the full absolute path string `"/home/user/project/atomic-claude"` will never match any single component. This means the atomic-claude directory is NOT excluded from project scans, and all files inside atomic-claude are included in scan results for documentation, configuration, source code, and tests. | 106, 1244-1250 | Run material scan on a project where `atomic_root` is a subdirectory of `project_root` (the standard layout). `_find_files` is called with `exclude_dirs=["/home/user/project/atomic-claude"]`. Files like `atomic-claude/core/main.py` are NOT excluded because `"/home/user/project/atomic-claude" in ('/','home','user','project','atomic-claude','core','main.py')` is False. The scan reports hundreds of atomic-claude internal files as project source code, inflating file counts and polluting the material manifest. | Change the exclusion check for absolute paths to use path prefix matching. For example: `if any(str(f).startswith(excl + os.sep) or str(f) == excl for excl in exclude_dirs_abs): continue` where `exclude_dirs_abs` is separated from the short-name `exclude_patterns`. Or use `try: f.relative_to(excl_path)` with `ValueError` catch. |

**Note:** The previous audit's finding about short patterns like `"dist"` causing false positives in `_find_files` has been correctly fixed by switching to `f.parts` matching. However, this fix inadvertently broke the absolute-path exclusion that was previously working via substring matching (when `excl in str(f)` would match the full path prefix). The fix was correct for one class of exclusion but broke another.

---

## 6. phases/phase_00_setup/tasks/task_005_repository_setup.py

No actionable findings. The previous `_show_summary` error handling finding has been fixed (lines 1024-1027 now use try/except with fallback). The report cache mechanism correctly resets on each `execute()` call.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 1 |

### HIGH Findings (1)

1. **task_004_material_scan.py (lines 106, 1244-1250):** Absolute directory path exclusion in `_find_files` is silently broken after the partial fix from the previous audit. The `excl in f.parts` check works for short directory name patterns but fails for full absolute paths like `str(atomic_root)`, because the complete path string never matches any single path component. The atomic-claude tool directory is not excluded from project scans, causing all its internal files to appear in scan results.

### MEDIUM Findings (1)

1. **task_003_setup_wizard.py (lines 298-300, 644, 1275):** `_run_wizard` returns string `"RESTART"` as a sentinel, violating its `Optional[Dict[str, Any]]` return type. Runtime-safe in current code but a maintenance trap that could cause crashes if new non-dict return values are added.
