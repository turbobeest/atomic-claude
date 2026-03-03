# Phase 00 — Setup Audit

**Date**: 2026-03-02
**Auditor**: Claude Opus 4.6
**Checklist**: TASK-CODE-AUDIT-CHECKLIST.md (categories A-R)
**Files audited**: 6

## Findings

| # | File | Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|---|------|-------|----------|---------|---------|------------------|----------------|
| 1 | `phases/phase_00_setup/tasks/task_001_environment_bootstrap.py` | A1 | MEDIUM | `_ensure_docker_group()` imports `grp` (Unix-only) at line 660 before the `platform.system() != "Linux"` early-return guard at line 662. On Windows this raises `ModuleNotFoundError` immediately. Similarly, `_run_docker_compose()` imports `grp` unconditionally at line 727. Both are called from `_start_falkordb()` during every task_001 run. The outer `except Exception` (line 817) prevents a pipeline crash but produces a misleading error message and skips FalkorDB startup entirely on Windows, even when Docker Desktop is installed and functional. | 660, 727 | Run task_001 on Windows with Docker Desktop installed and `docker-compose.yml` present. `_ensure_docker_group()` fails at `import grp` before the platform check. FalkorDB startup is skipped with "FalkorDB startup error: No module named 'grp'" instead of attempting `docker compose up`. | Move `import grp` below the `platform.system() != "Linux"` guard in `_ensure_docker_group`. In `_run_docker_compose`, move `import grp` inside the `if "permission denied"` block. The `grp`/`sg docker` fallback is Linux-only and should not affect other platforms. |
| 2 | `phases/phase_00_setup/tasks/task_002_provider_detection.py` | A2 | MEDIUM | `_create_secrets_file()` declares return type `-> None` but returns `False` on line 486 when `write_file` raises `OSError`. The caller at line 231 does not check the return value, so a secrets file write failure is silently swallowed — `execute()` continues and reports success. Downstream tasks (003, 005) that read `secrets.json` will operate on stale or missing data. | 450, 486, 231 | Run task_002 when the output directory is on a read-only filesystem or disk is full. `_create_secrets_file` fails silently, `execute()` returns `True`, and task_003 reads a missing/stale `secrets.json`. | Either change return type to `-> bool` and check the return in `execute()`, or raise the `OSError` and let `execute()` handle it at the top level. |
| 3 | `phases/phase_00_setup/tasks/task_002_provider_detection.py` | F1 | MEDIUM | `_create_secrets_file` writes `"anthropic_api_key": null` to `secrets.json` when provider is `claude-code`. At line 260, `has_anthropic` is set `True` for Claude Code subscriptions (no API key exists). At line 472-473, the code writes `secrets["anthropic_api_key"] = env_vars.get('ANTHROPIC_API_KEY')` which evaluates to `None`. Downstream consumers that use `"anthropic_api_key" in secrets` (key-presence check) will incorrectly believe a key is configured, while `secrets.get("anthropic_api_key")` truthiness checks work correctly. | 260, 472-473 | Select Claude Code subscription in the credential wizard. `secrets.json` contains `"anthropic_api_key": null`. Any downstream code that checks key presence rather than truthiness will be misled. | Guard with `if has_anthropic and env_vars.get('ANTHROPIC_API_KEY'):` to avoid writing a null key to `secrets.json`. |

## Summary

- CRITICAL: 0
- HIGH: 0
- MEDIUM: 3

**Files with no findings at MEDIUM or above**: `phases/phase00/orchestrator00.py`, `phases/phase_00_setup/tasks/task_003_setup_wizard.py`, `phases/phase_00_setup/tasks/task_004_material_scan.py`, `phases/phase_00_setup/tasks/task_005_repository_setup.py`
