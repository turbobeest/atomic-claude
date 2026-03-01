# Re-Audit 5 (Final): Phase 00 Setup
**Date:** 2026-02-28
**Auditor:** Claude Opus 4.6
**Scope:** 6 files in phases/phase00/ and phases/phase_00_setup/tasks/
**Audit Categories:** A-R (full checklist)
**Severity Threshold:** CRITICAL, HIGH, MEDIUM only
**Previous Audit:** reaudit4-phase-00-setup.md (same date)

---

## Fix Verification

One fix was applied since pass 5:

| # | File | Previous Finding | Fix Applied | Verification |
|---|------|-----------------|-------------|--------------|
| 1 | task_003 `execute()` lines 279-297 | `uat_mode` parameter accepted but never used -- wizard always runs interactively, blocking pipeline in UAT mode | Lines 279-297: When `uat_mode=True`, the function now skips the interactive wizard entirely. It calls `_detect_environment()` + `_infer_project_defaults()` to gather environment info, constructs a stub config with project name/description/type, calls `_apply_auto_defaults()` to fill in standard sections (agents, providers, audits, gardener, mcp), and calls `_save_config()` to write both `project-config.json` and `extracted-config.json`. Returns `True` without ever entering `_run_wizard()`. | **CONFIRMED FIXED** -- The UAT guard at line 279 fully prevents the interactive wizard from running. The stub config includes all three required top-level sections (`project`, `llm`, `pipeline`) that downstream tasks expect. `_apply_auto_defaults` adds `agents`, `providers`, `audits`, `gardener`, and `mcp` sections. `_save_config` preserves existing keys via read-merge-write (lines 1901-1906), validates schema, resolves markers, and writes both output files. |

### Fix Quality Assessment

The fix is well-implemented:

1. **Non-interactive**: No `prompt_user()` calls in the UAT path.
2. **Config completeness**: The stub includes `project`, `llm`, and `pipeline` sections directly, plus `_apply_auto_defaults()` adds `agents`, `providers`, `audits`, `gardener`, and `mcp`. This matches the schema downstream tasks expect.
3. **Output files**: Both `project-config.json` and `extracted-config.json` are written via `_save_config()`.
4. **Memory recording**: The `if mem:` block at line 295-296 records the decision, matching the pattern used by other tasks.
5. **Preserves existing config**: `_save_config` uses read-merge-write at lines 1901-1906 to preserve keys written by task_001 (e.g., `environment`).

One minor observation: the stub config at line 288 uses `"application"` as the fallback project type, which is not in `VALID_PROJECT_TYPES`. This produces a schema validation warning but causes no functional breakage -- `_save_config` prints warnings but does not fail, and downstream code uses `project.type` purely as an informational string in LLM prompts. This does not meet MEDIUM severity (no incorrect behavior, just a cosmetic warning in UAT mode).

---

## 1. phases/phase00/orchestrator00.py

No actionable findings.

---

## 2. phases/phase_00_setup/tasks/task_001_environment_bootstrap.py

No actionable findings.

---

## 3. phases/phase_00_setup/tasks/task_002_provider_detection.py

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| R6 | MEDIUM | `_credential_wizard` enters interactive prompts without checking `uat_mode` | 89, 220-226, 316 | Set `ATOMIC_UAT_MODE=true` and run the pipeline with NO credentials configured: no `.env` file, no `ANTHROPIC_API_KEY` in env, no `AWS_PROFILE`/`AWS_ACCESS_KEY_ID` in env, no `~/.aws/credentials`, and no local Ollama running. `execute()` calls `_check_credentials()` at line 89. `_check_credentials()` calls `_detect_credentials()` which returns `(False, False, False)`. At line 220 the condition `not has_aws and not has_anthropic and not has_ollama` is True, so `_credential_wizard()` is called at line 223. The wizard immediately calls `prompt_user("  Provider [1]: ")` at line 316, which blocks on stdin input that never arrives in UAT mode. The `uat_mode` parameter is passed to `execute()` but never forwarded to `_check_credentials` or `_credential_wizard`. Note: the Ollama host configuration at line 590 already correctly guards with `if not uat_mode:`. | Forward `uat_mode` to `_check_credentials`. When `uat_mode=True` and no credentials are found, skip the wizard and return a default tuple (e.g., `(False, False, False, env_vars)`) so the pipeline continues with zero providers. Alternatively, return `None` to signal failure cleanly. |

---

## 4. phases/phase_00_setup/tasks/task_003_setup_wizard.py

No new actionable findings. Previous finding confirmed fixed (see fix verification above).

---

## 5. phases/phase_00_setup/tasks/task_004_material_scan.py

No actionable findings.

---

## 6. phases/phase_00_setup/tasks/task_005_repository_setup.py

No actionable findings.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 1 |

### MEDIUM Findings (1)

1. **task_002_provider_detection.py (lines 89, 220-226, 316):** `_credential_wizard` is called without checking `uat_mode` when no credentials are found. In UAT mode with zero credentials configured, the pipeline hangs on `prompt_user()`. Rated MEDIUM rather than HIGH because UAT mode without any LLM provider credentials is a misconfiguration edge case (the pipeline cannot do meaningful work without at least one provider), and the Ollama host prompt in the same file already correctly guards with `if not uat_mode:`.

### Previous Findings Disposition

| Pass | Finding | Current Status |
|------|---------|---------------|
| Pass 3 (reaudit2) | task_004 `_find_files` absolute-path exclusion broken | Fixed in pass 3, confirmed still fixed |
| Pass 3 (reaudit2) | task_003 `_run_wizard` returns string `"RESTART"` sentinel | Fixed in pass 3, confirmed still fixed |
| Pass 4 (reaudit3) | task_001 line 379 node version parsing unprotected | Fixed in pass 5, confirmed still fixed |
| Pass 4 (reaudit3) | task_003 `_save_config` overwrites project-config.json | Fixed in pass 5, confirmed still fixed |
| Pass 5 (reaudit4) | task_003 `uat_mode` accepted but never used | **Fixed in pass 6**, confirmed (see fix verification) |
| Pass 6 (this) | task_002 `_credential_wizard` ignores `uat_mode` | **NEW** -- MEDIUM, edge case in UAT with zero credentials |

**Total: 0 critical, 0 high, 1 medium.**
