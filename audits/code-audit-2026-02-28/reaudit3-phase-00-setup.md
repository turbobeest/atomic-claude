# Re-Audit 3: Phase 00 Setup
**Date:** 2026-02-28
**Scope:** 6 files in phases/phase00/ and phases/phase_00_setup/tasks/
**Audit Categories:** A-R (full checklist)
**Severity Threshold:** CRITICAL, HIGH, MEDIUM only
**Previous Audit:** reaudit2-phase-00-setup.md (same date)

---

## Previously Reported Findings -- Disposition

Both findings from the previous audit (reaudit2) were reviewed against the current code:

| # | File | Previous Finding | Status |
|---|------|-----------------|--------|
| 1 | task_004 (lines 106, 1244-1250) | Absolute directory path exclusion in `_find_files` broken because full path string never matches any single path component in `f.parts` | **FIXED** -- `_find_files` now uses `Path.resolve()` and `Path.is_relative_to()` at lines 1244-1257 to properly check absolute directory exclusions |
| 2 | task_003 (lines 298-300, 644, 1275) | `_run_wizard` returns string `"RESTART"` sentinel violating return type | **FIXED** -- Module-level `_RESTART = object()` sentinel at line 54, used via `is` comparison at lines 301-302 and returned at line 1278 |

---

## 1. phases/phase00/orchestrator00.py

No actionable findings.

---

## 2. phases/phase_00_setup/tasks/task_001_environment_bootstrap.py

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| A (Logic) | MEDIUM | Node version parsing in `_show_required_tools` is unprotected against non-numeric version strings. At line 379, `int(version.split('.')[0])` is called without a try/except. The `_check_tool("node")` function returns `"installed"` (line 285) when `node` is found on PATH but `node --version` returns a non-zero exit code (e.g., broken Node installation, or a shim that exits with error). In this case, `int("installed".split('.')[0])` raises `ValueError`, crashing the entire task. The same parsing in `_recheck_required` (lines 419-424) IS properly wrapped in try/except, showing awareness of this failure mode. | 379, 285 | Install a broken node shim or wrapper script on PATH that exits with a non-zero return code. `_check_tool("node")` returns `"installed"` because shutil.which() finds it but `node --version` fails. `_show_required_tools` then calls `int("installed".split('.')[0])` which raises an unhandled `ValueError`. The task crashes instead of showing the node version check result. | Wrap lines 378-385 in try/except ValueError, matching the pattern used in `_recheck_required` at lines 419-424. On ValueError, treat node as not meeting the minimum version requirement. |

---

## 3. phases/phase_00_setup/tasks/task_002_provider_detection.py

No actionable findings.

---

## 4. phases/phase_00_setup/tasks/task_003_setup_wizard.py

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| E (Data flow) | MEDIUM | `_save_config` overwrites the entire `project-config.json` without reading existing content, discarding data written by task 001. Task 001 (`_record_environment` at line 762 of task_001) writes an `environment` key to project-config.json containing OS type, tool counts, cargo availability, and a timestamp. Task 003's `_save_config` (lines 1879-1891) creates a new `project_config` dict from scratch and writes it, discarding whatever was already in the file. The `environment` key is silently lost. While no downstream phase currently reads this key from project-config.json (it is only asserted in unit tests), the data loss means the environment bootstrap record is not preserved in the canonical configuration file as intended, and unit tests that check for this key after a full pipeline run would fail. | 1879-1891 (task_003), 762-774 (task_001) | Run the full Phase 0 pipeline (tasks 001-005). After task 001 completes, project-config.json contains `{"environment": {"os_type": "linux", ...}}`. After task 003 completes, project-config.json contains the wizard output but the `environment` key is gone. Any code or test that expects `project-config.json` to contain the `environment` key after Phase 0 will fail or get missing data. | In `_save_config`, read the existing project-config.json before writing, and merge the new config into it (similar to the read-merge-write pattern used by task_004's `_record_reference_info` and task_005's `_save_configuration`). Alternatively, add `'environment'` to the flatten list at line 1887 and ensure it is preserved from the existing file. |

---

## 5. phases/phase_00_setup/tasks/task_004_material_scan.py

No actionable findings. The previously reported `_find_files` absolute-path exclusion bug has been properly fixed using `Path.resolve()` and `is_relative_to()` at lines 1244-1257.

---

## 6. phases/phase_00_setup/tasks/task_005_repository_setup.py

No actionable findings. The read-merge-write pattern for project-config.json is correctly implemented at lines 959-971. The report cache mechanism properly resets on each `execute()` call (lines 77-79).

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 2 |

### MEDIUM Findings (2)

1. **task_001_environment_bootstrap.py (line 379):** Node version parsing in `_show_required_tools` calls `int(version.split('.')[0])` without try/except. If `_check_tool("node")` returns the fallback string `"installed"` (when node is on PATH but `node --version` returns non-zero), this raises an unhandled `ValueError` that crashes the task. The identical parsing in `_recheck_required` (lines 419-424) already handles this with try/except.

2. **task_003_setup_wizard.py (lines 1879-1891):** `_save_config` creates a new dict and overwrites project-config.json without reading existing content. This discards the `environment` key written by task 001. No downstream phase currently reads this key, but the data loss means the environment bootstrap record is not preserved as intended, and unit tests asserting its presence after full pipeline runs would fail.

**Total: 0 critical, 0 high, 2 medium.**
