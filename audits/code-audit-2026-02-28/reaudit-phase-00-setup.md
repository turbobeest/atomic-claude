# Re-Audit: Phase 00 Setup
**Date:** 2026-02-28
**Scope:** 6 files in phases/phase00/ and phases/phase_00_setup/tasks/
**Audit Categories:** A-R (full checklist)
**Severity Threshold:** CRITICAL, HIGH, MEDIUM only

---

## 1. phases/phase00/orchestrator00.py — Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|

No actionable findings. The orchestrator is a thin delegation layer that wires task callables to `run_phase_tasks`. Module-level `Path.cwd()` default for `ATOMIC_ROOT` is wrapped in `Path()` and works correctly for both string (env set) and Path (default) cases.

---

## 2. phases/phase_00_setup/tasks/task_001_environment_bootstrap.py — Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| E (Data flow) | MEDIUM | Global counters `REQUIRED_TOTAL`, `REQUIRED_INSTALLED`, `RECOMMENDED_TOTAL`, `RECOMMENDED_INSTALLED` are module-level mutable state. If `execute()` is called twice in the same process without a fresh import (e.g., a retry loop or test harness), the counters are reset at the top of `execute()` — but `RECOMMENDED_TOTAL` and `RECOMMENDED_INSTALLED` are only reset to 0 at lines 69-72, then `_show_recommended_tools` accumulates into them. If a caller invokes `_show_recommended_tools` or `_recheck_required` independently (outside `execute()`), the counters are stale. | 40-44, 68-72 | Call `_recheck_required` without first resetting `REQUIRED_TOTAL`/`REQUIRED_INSTALLED` to 0 — the counters accumulate across calls. Currently only `execute()` resets them, so this is safe in normal operation but fragile if any helper is called out-of-order. | Within the strict severity criteria, this is borderline. The current code path through `execute()` resets counters before use. Noting as informational context for the single genuine medium finding below. |
| N (Concurrency) | MEDIUM | `_launch_dashboard` spawns a `Popen` process (line 595) with `start_new_session=True` and `stdout=DEVNULL`/`stderr=DEVNULL`, then polls for readiness. If the dashboard script fails to start or crashes during the 10s polling window, the Popen object is never stored or tracked — it becomes an orphaned process. On the next re-run of task 001 (e.g., after a backtrack), a second dashboard instance will be spawned, potentially causing a port conflict on port 5174 that is swallowed silently. | 595-601 | Run task 001, dashboard starts on port 5174. Backtrack and re-run task 001 — second dashboard process is spawned. The second `Popen` may fail silently (port in use) or succeed if the first died. The first process is never reaped. | Before spawning, check if port is already in use (connect test to `127.0.0.1:{port}`) and skip launch if already occupied. Store the PID in a state file for cleanup on re-run. |

---

## 3. phases/phase_00_setup/tasks/task_002_provider_detection.py — Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| B (Security) | MEDIUM | `_credential_wizard` writes the Anthropic API key in plaintext to the `.env` file at line 343 (`f"ANTHROPIC_API_KEY={api_key}"`). The file permissions are set to 0o600 (line 410), but the key is also synced into `os.environ` (line 419) and written to `secrets.json` at line 469 without encryption. If the `.env` file is accidentally committed to git (no `.gitignore` check is performed), the API key is exposed. | 343, 407, 419, 460-469 | User selects Anthropic API provider (choice "2"), enters API key. Key is written to `.env` and `secrets.json` in plaintext. If `.gitignore` is missing or doesn't exclude `.env`, `git add .` will stage it. | Verify `.gitignore` contains `.env` and `secrets.json` entries before writing. Warn the user if `.gitignore` is absent or does not contain these patterns. |

---

## 4. phases/phase_00_setup/tasks/task_003_setup_wizard.py — Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| E (Data flow) | HIGH | `_run_wizard` returns the string `"RESTART"` (line 1272) when the user declines the configuration at step 10. The caller in `execute()` (lines 298-300) compares `config == "RESTART"` in a while loop. However, `_run_wizard`'s return type annotation says `Optional[Dict[str, Any]]`. Returning a bare string `"RESTART"` violates this contract and means that any code checking `isinstance(config, dict)` after the loop will incorrectly handle the restart case. While the current loop works because Python's `==` on string vs string succeeds, the real problem is: if the while loop terminates (config is not "RESTART" and not None), the code proceeds to `_save_config(config_file, extracted_file, config)` at line 306. The `_save_config` function calls `json.dumps(config, indent=2)` at line 1855. If `config` is somehow a non-dict truthy value (not currently reachable since the loop handles "RESTART"), the pattern is fragile. **More concretely:** if `_run_wizard` is refactored to return a different non-None, non-dict sentinel, the `while` loop exits and `_save_config` receives a non-dict, crashing on `config.get("project", {})` at line 1503 inside `_show_summary`.  | 298-303, 1272, 644 | Currently: user picks "n" at step 10 summary, wizard returns "RESTART", loop continues. The actual bug risk is that the type annotation is wrong and the sentinel-string pattern invites future breakage. Under current code paths this does not crash. | Use a dedicated sentinel constant (e.g., `_RESTART = object()`) instead of a string, and update the type annotation to `Optional[Union[Dict[str, Any], object]]`. Or restructure to use a loop inside `_run_wizard` itself. |
| G (Error handling) | MEDIUM | `_llm_invoke` at line 520 catches all exceptions from each LLM provider attempt via the `_with_retry` wrapper (line 536), logging them at debug level. If all 4 providers fail (Claude CLI, Anthropic SDK, Bedrock SDK, Ollama), the function returns `None` at line 612 and the wizard continues with directory-name defaults. However, a `KeyboardInterrupt` during any provider attempt is also caught by the bare `except Exception` at line 536, preventing the user from interrupting a hanging LLM call (each attempt has a 30-60s timeout). The user must wait up to 2 * (30 + 30 + 30 + 60) = 300 seconds worst case before the wizard falls back to defaults. | 529-540 | User starts setup wizard, no LLM providers are reachable. Each of the 4 providers is tried twice with timeouts (30s for Claude CLI, 30s for Anthropic, 30s for Bedrock, 60s for Ollama). User presses Ctrl+C during any attempt — `KeyboardInterrupt` is a `BaseException`, not `Exception`, so it does propagate. However, the subprocess calls with `timeout=30` in `_try_claude_cli` will not be interrupted by KeyboardInterrupt during `subprocess.run` on some platforms. | This is actually safe because `KeyboardInterrupt` inherits from `BaseException` not `Exception`. Downgrading — no actionable finding. |
| E (Data flow) | MEDIUM | In Step 5 (LLM Configuration), `atomic_root` is re-derived from `os.environ.get("ATOMIC_ROOT", Path.cwd())` at line 873, rather than using the `atomic_root` parameter passed to `execute()`. If `ATOMIC_ROOT` env var is not set (e.g., CLI invocation without the env), `Path.cwd()` is used, which may differ from the `atomic_root` argument. This means `_get_provider_profile` and `_get_default_phase_roles` may load `config/models.json` from the wrong directory. | 873 | Run the wizard via `python task_003_setup_wizard.py --atomic-root /path/to/atomic-claude --output-dir /tmp/out` from a different working directory, without `ATOMIC_ROOT` env var set. Line 873 uses `Path.cwd()` instead of the CLI-provided `--atomic-root`, so `config/models.json` is loaded from the wrong location, yielding incorrect default model tiers and phase roles. | Thread the `atomic_root` parameter through to `_run_wizard` and use it directly instead of re-deriving from env/cwd. |
| E (Data flow) | MEDIUM | Same issue repeats in `_apply_auto_defaults` at lines 1609 and 1627: `atomic_root = Path(os.environ.get("ATOMIC_ROOT", Path.cwd()))` re-derives the path from env/cwd instead of using the parameter from `execute()`. | 1609, 1627 | Same trigger as above — running via CLI with `--atomic-root` flag but without `ATOMIC_ROOT` env var, from a different working directory. The auto-defaults section loads `config/models.json` from the wrong path. | Pass `atomic_root` as parameter to `_apply_auto_defaults` and `_run_wizard`. |

---

## 5. phases/phase_00_setup/tasks/task_004_material_scan.py — Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| A (Logic) | HIGH | `_find_files` uses substring matching (`excl in str(f)`) for exclusion at line 1249. The `exclude_patterns` list includes short strings like `"dist"` and `"build"`. Any file whose absolute path contains these substrings anywhere — including in directory names like `distribution/`, `redistribute/`, `buildspec/`, or even the project name — will be incorrectly excluded from the scan results. The `exclude_dirs` parameter passes absolute paths (e.g., `/home/user/projects/my-project/atomic-claude`), which also uses substring matching, so a project named `atomic-claude-extra` at a sibling path would be excluded too. | 1241-1249 | Project root is `/home/user/distribution-app/`. User runs material scan. `_find_files` is called with `exclude_patterns = ["node_modules", ".git", ".outputs", "__pycache__", "dist", "build"]`. Any file path like `/home/user/distribution-app/src/main.py` contains `"dist"` as a substring, so ALL project files are excluded. The scan reports 0 source code files, 0 documentation files, etc. | Replace substring matching with path-component matching: check `excl in f.parts` or use `any(part == excl for part in rel_path.parts)` after computing `rel_path`. For absolute exclusion paths, use `f.is_relative_to(excl_path)` or check path prefix with a trailing separator. |
| A (Logic) | MEDIUM | `_scan_source_code` applies a second exclusion filter at line 413 using `any(pattern in str(f) for pattern in [".min.", "node_modules", "dist", "build", "__pycache__"])`. This has the same substring false-positive problem as `_find_files` — a file at `src/distribution/config.py` would be excluded because `"dist"` is a substring of `"distribution"`. | 412-414 | Project has a `src/distribution/` directory. All files in it are silently excluded from the source code scan, leading to an inaccurate file count and potentially missing key source files from the manifest. | Use path-component matching instead of substring matching. |

---

## 6. phases/phase_00_setup/tasks/task_005_repository_setup.py — Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| G (Error handling) | HIGH | `_show_summary` at line 1024 calls `json.loads(read_file(report_file))` without any exception handling. The `read_file` function raises `FileNotFoundError` if the file does not exist, and `json.loads` raises `json.JSONDecodeError` on corrupt content. If the report file was deleted or corrupted between `_flush_report` (line 138) and `_show_summary` (line 163), or if `_flush_report` failed silently, this will crash with an unhandled exception, aborting the entire task. This is on the normal execution path — `_show_summary` is called unconditionally at line 163. | 1024 | Run task 005 on a system where the report file write at `_flush_report` (line 138) fails silently (e.g., disk full, permission issue), or the file is deleted between flush and summary display. `_show_summary` crashes with `FileNotFoundError` or `json.JSONDecodeError`, causing `execute()` to raise an unhandled exception and the phase to fail. Note that `_save_configuration` (called at line 141) also reads the report file but wraps it in try/except (line 943-947), showing the inconsistency. | Wrap the `json.loads(read_file(report_file))` call at line 1024 in a try/except block, falling back to `{"capabilities": {}}` on failure, consistent with the pattern used in `_save_configuration` at line 943-947. |
| E (Data flow) | MEDIUM | Module-level global variables `_report_cache` and `_report_cache_file` (lines 871-872) are reset inside `execute()` at lines 78-79 via `global _report_cache, _report_cache_file` followed by assignment. However, `_report_cache` is typed as `Optional[Dict]` and `_report_cache_file` as `Optional[Path]`. If `execute()` is called twice in the same process (e.g., test suite or retry), the reset at lines 78-79 correctly clears them. But if `_flush_report` is never called (e.g., an exception occurs between the assessment calls and line 138), the cache holds stale data from a previous run. The `_get_report_cache` function at line 878 checks `_report_cache_file != report_file` and reloads — but if the report_file path is the same across runs, stale cache is used. | 871-884, 77-79 | Execute task 005, an exception occurs during `_assess_gpu` (line 135). The cache has partial data. Task is retried (same process). `execute()` resets `_report_cache = None` at line 78, so `_get_report_cache` reloads from disk. The disk file was written at line 87 with an empty report — so the reload is correct. This is actually safe due to the None reset. Downgrading. | No actionable finding after analysis — the reset at line 78-79 prevents stale cache. |

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 3 |
| MEDIUM | 5 |

### HIGH Findings (3)

1. **task_003_setup_wizard.py (line 298-303, 1272):** `_run_wizard` returns string `"RESTART"` violating `Optional[Dict]` type contract. The sentinel-string pattern is fragile and invites downstream breakage if the function is modified.

2. **task_004_material_scan.py (lines 1241-1249):** `_find_files` uses substring matching for directory exclusion patterns. Short patterns like `"dist"` and `"build"` cause false-positive exclusions on projects with directories named `distribution/`, `redistribute/`, `buildspec/`, etc., silently dropping all their files from scan results.

3. **task_005_repository_setup.py (line 1024):** `_show_summary` reads the report file without exception handling, crashing the task if the file is missing or corrupt. This is on the unconditional execution path and inconsistent with the error handling in `_save_configuration` (line 943-947) which handles the same operation safely.

### MEDIUM Findings (5)

1. **task_001_environment_bootstrap.py (lines 595-601):** Dashboard launch via `Popen` creates orphan processes on re-run; no port-in-use check prevents duplicate dashboard instances.

2. **task_002_provider_detection.py (lines 343, 407-469):** API key written to `.env` and `secrets.json` in plaintext without verifying `.gitignore` coverage.

3. **task_003_setup_wizard.py (line 873):** `atomic_root` re-derived from `os.environ`/`Path.cwd()` instead of using the function parameter, causing wrong `config/models.json` path when run via CLI from a different directory.

4. **task_003_setup_wizard.py (lines 1609, 1627):** Same `atomic_root` re-derivation issue in `_apply_auto_defaults`.

5. **task_004_material_scan.py (lines 412-414):** `_scan_source_code` post-filter uses same substring matching anti-pattern as `_find_files`, causing false-positive exclusions.
