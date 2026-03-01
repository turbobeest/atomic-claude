# Re-Audit 4: Phase 00 Setup
**Date:** 2026-02-28
**Auditor:** Claude Opus 4.6
**Scope:** 6 files in phases/phase00/ and phases/phase_00_setup/tasks/
**Audit Categories:** A-R (full checklist)
**Severity Threshold:** CRITICAL, HIGH, MEDIUM only
**Previous Audit:** reaudit3-phase-00-setup.md (same date)

---

## Fix Verification

Both fixes from the previous audit (reaudit3) were verified against the current code:

| # | File | Previous Finding | Fix Applied | Verification |
|---|------|-----------------|-------------|--------------|
| 1 | task_001 line 379 | `int(version.split('.')[0])` in `_show_required_tools` unprotected against non-numeric version strings | Lines 379-390: `try/except ValueError` now wraps the `int()` call; on failure, logs at DEBUG and prints "version could not be verified" with install hint | **CONFIRMED FIXED** -- The try/except at line 387 catches `ValueError` from `int("installed".split('.')[0])` and degrades gracefully. Matches the pattern already used in `_recheck_required` at lines 424-429. |
| 2 | task_003 `_save_config` lines 1879-1891 | Overwrites entire project-config.json without reading existing content, discarding `environment` key written by task_001 | Lines 1879-1885: Now reads existing project-config.json via `read_json(config_file)`, catches `FileNotFoundError` and `json.JSONDecodeError`, starts with empty dict on failure. Then uses `project_config.update(...)` at line 1887 to merge new keys into existing config. | **CONFIRMED FIXED** -- The read-merge-write pattern at lines 1880-1899 correctly preserves keys written by earlier tasks (e.g., the `environment` key from task_001). The `read_json` function (from `core.utils.file_ops`) raises `FileNotFoundError`/`json.JSONDecodeError` which are both caught. The `isinstance(project_config, dict)` guard at line 1882 handles the edge case where the JSON file contains a non-dict value. |

---

## 1. phases/phase00/orchestrator00.py

No actionable findings.

---

## 2. phases/phase_00_setup/tasks/task_001_environment_bootstrap.py

No new actionable findings. Previous finding confirmed fixed (see fix verification above).

---

## 3. phases/phase_00_setup/tasks/task_002_provider_detection.py

No actionable findings.

---

## 4. phases/phase_00_setup/tasks/task_003_setup_wizard.py

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| R6 | HIGH | `uat_mode` parameter accepted but never used -- wizard always runs interactively | 256 (signature), 300-303 (wizard call) | Set `ATOMIC_UAT_MODE=true` and run the full Phase 0 pipeline. Tasks 001, 002, 004, and 005 all check `uat_mode` and skip interactive prompts accordingly. Task 003's `execute()` accepts `uat_mode` (line 256) but never references it in the function body. Execution reaches `_run_wizard()` at line 303, which calls `prompt_user()` at many points (lines 692, 700, 706, 742, 806, 957, 971, 1011, 1018, 1111, 1128, 1160, 1272, etc.). The pipeline blocks indefinitely on the first prompt, waiting for stdin input that will never arrive in an automated UAT run. No unit test exercises `task_003.execute()` in UAT mode -- all task_003 tests target internal helpers (`_validate_project_name`, `_slugify`, `_validate_config_schema`, etc.). Every other Phase 0 task has a `test_execute_uat_mode_returns_true` test; task_003 does not. | Add UAT mode handling to `execute()`: when `uat_mode` is True, generate a stub config from `_apply_auto_defaults()` and `_infer_project_defaults()` results without entering `_run_wizard()`, matching the pattern used by the other 4 tasks. |

---

## 5. phases/phase_00_setup/tasks/task_004_material_scan.py

No actionable findings. The previously reported `_find_files` absolute-path exclusion bug remains properly fixed using `Path.resolve()` and `is_relative_to()` at lines 1244-1257.

---

## 6. phases/phase_00_setup/tasks/task_005_repository_setup.py

No actionable findings. The read-merge-write pattern for project-config.json is correctly implemented at lines 959-971. The report cache mechanism properly resets on each `execute()` call (lines 77-79).

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 0 |

### HIGH Findings (1)

1. **task_003_setup_wizard.py (line 256, 300-303):** `uat_mode` is accepted in `execute()` but never used. The wizard always runs interactively, blocking indefinitely on `prompt_user()` calls when `ATOMIC_UAT_MODE=true`. All other Phase 0 tasks properly bypass interactive prompts in UAT mode. No test exercises `task_003.execute(uat_mode=True)`.

### Previous Findings Disposition

| Pass | Finding | Current Status |
|------|---------|---------------|
| Pass 3 (reaudit2) | task_004 `_find_files` absolute-path exclusion broken | Fixed in pass 3, confirmed still fixed |
| Pass 3 (reaudit2) | task_003 `_run_wizard` returns string `"RESTART"` sentinel | Fixed in pass 3, confirmed still fixed |
| Pass 4 (reaudit3) | task_001 line 379 node version parsing unprotected | **Fixed in pass 5**, confirmed (see fix verification) |
| Pass 4 (reaudit3) | task_003 `_save_config` overwrites project-config.json | **Fixed in pass 5**, confirmed (see fix verification) |
| Pass 5 (this) | task_003 `uat_mode` accepted but never used | **NEW** -- pipeline hangs in UAT mode |

**Total: 0 critical, 1 high, 0 medium.**
