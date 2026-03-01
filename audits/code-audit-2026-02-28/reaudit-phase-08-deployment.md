# Phase 08 Deployment Prep -- Code Audit (Re-Audit)

**Date:** 2026-02-28
**Auditor:** Claude Opus 4.6 (automated)
**Scope:** 8 files in Phase 08 Deployment Prep
**Categories:** A-R (full checklist)
**Severity threshold:** CRITICAL, HIGH, MEDIUM only

---

### phases/phase08/orchestrator08.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| E - Logic / Control Flow | HIGH | `task_805_wrapper` declares `**kwargs` to receive `graph`, but `phase_runner.py` uses `inspect.signature()` to check for a named `graph` parameter. Since `**kwargs` does not expose `graph` as a named parameter, `accepts_graph` evaluates to `False`, and the wrapper is called as `task_func(mem)` without `graph`. The `kwargs.get("graph")` in the wrapper always returns `None`. | 74-76 | Run phase 8 with a FalkorDB graph active and pattern_selection=None (direct/legacy call path). Task 805's `execute()` receives `graph=None`, so the audit graph parameter from the orchestrator is silently dropped. | Change the wrapper signature to use an explicit `graph=None` parameter: `def task_805_wrapper(mem=None, graph=None, **kwargs) -> bool:` so that `inspect.signature()` can detect it. |

---

### phases/phase_08_deployment_prep/tasks/task_801_entry_initialization.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| E - Logic / Control Flow | MEDIUM | `_find_closeout` primary path checks `project_root / ".outputs" / "7-integration" / "closeout.json"`, where `project_root = atomic_root.parent`. However, `phase_runner.create_phase_closeout()` writes to `ATOMIC_ROOT / ".outputs" / "7-integration" / "closeout.json"` (i.e., inside atomic-claude, not in its parent). The primary path can never find the phase_runner-generated closeout because the directories differ by one level. | 134-148 | Phase 7 completes. The `phase_runner` writes `closeout.json` to `ATOMIC_ROOT/.outputs/7-integration/`. Task 801 checks `project_root/.outputs/7-integration/` (one directory up) and does not find it. The primary check always fails; the fallback (`.claude/closeout/phase-07-closeout.json` from task_707) saves it. If task_707's closeout was not written (e.g., task_707 failed but phase_runner still ran `create_phase_closeout`), prerequisite validation fails incorrectly. | Either fix `_find_closeout` to also check `atomic_root / ".outputs"`, or fix `phase_runner.create_phase_closeout` to accept and use the actual `output_dir` from `run_phase_tasks`. |

---

### phases/phase_08_deployment_prep/tasks/task_802_deployment_setup.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| E - Logic / Control Flow | MEDIUM | Distribution channel selection only handles input `"1"`. Any other explicit input (e.g., `"2"`, a typo like `"q"`) results in `channels = []` (empty list). The configuration summary displays `Channels:` with an empty string, and the setup is persisted with `"channels": []` if the user confirms. | 115-117 | User is prompted for channel selection, types `"2"` or any non-`"1"` value. `channels` stays `[]`. The summary shows blank channels. If confirmed, `setup.json` is saved with empty channels list. Downstream code relying on at least one channel being present may malfunction. | Add an `else` clause that defaults to `["internal"]` or re-prompts the user for a valid selection. |

---

### phases/phase_08_deployment_prep/tasks/task_803_agent_selection.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| E - Logic / Data Contract | MEDIUM | UAT mode writes `{"agents": [...], "count": 4}` (no `"phase"` or `"selected_at"` keys). Non-UAT mode writes `{"phase": 8, "agents": [...], "selected_at": "..."}` (no `"count"` key). The two code paths produce structurally different JSON schemas for the same output file. | 42-53 vs 150-157 | Run UAT mode, then switch to non-UAT mode (or vice versa) and use a consumer that expects `"count"` or `"phase"` fields. Consumer code that checks `agents_data.get("count")` or `agents_data.get("phase")` gets `None` depending on which mode produced the file. | Normalize both code paths to emit the same schema. Add `"phase": 8` and `"selected_at"` to UAT output; add `"count": len(selected_agents)` to non-UAT output. |

---

### phases/phase_08_deployment_prep/tasks/task_804_artifact_generation.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| F - Error Handling | HIGH | `read_json(setup_file)` on line 86 is unprotected. If `setup_file` exists but contains invalid JSON (e.g., partially written, corrupted, or empty), `json.JSONDecodeError` propagates as an uncaught exception, crashing `execute()` and causing the entire phase to fail. Other tasks (806 line 77-81, 807 line 79-83) protect equivalent `read_json` calls with try/except. | 85-88 | `setup.json` exists but is empty or contains malformed JSON (e.g., disk-full write, race condition with task_802, manual edit error). Task 804 crashes with `json.JSONDecodeError` instead of falling back to defaults. | Wrap `read_json(setup_file)` in a try/except block, log the error, and fall through to the default values (`version = "0.1.0"`, `release_type = "minor"`), matching the defensive pattern used in tasks 806 and 807. |

---

### phases/phase_08_deployment_prep/tasks/task_805_phase_audit.py -- Audit

No actionable findings meeting CRITICAL/HIGH/MEDIUM criteria. The task is simple, delegates to `run_phase_audit`, and handles import failures gracefully. The `graph` parameter received as `None` due to the orchestrator wrapper bug (see orchestrator08.py finding) does not cause a crash here since `task_805.execute()` does not use `graph` directly.

---

### phases/phase_08_deployment_prep/tasks/task_806_deployment_approval.py -- Audit

No actionable findings meeting CRITICAL/HIGH/MEDIUM criteria. Error handling for JSON parsing is present (line 77-81). The interactive flow handles edge cases (discuss loop, revise, approve paths). The `deployment_dir.mkdir` call is guarded.

---

### phases/phase_08_deployment_prep/tasks/task_807_closeout.py -- Audit

No actionable findings meeting CRITICAL/HIGH/MEDIUM criteria. JSON reads are protected with try/except. The closeout data correctly records checklist state. The `_format_checklist_markdown` splitting logic handles the colon-delimited format safely.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH     | 2 |
| MEDIUM   | 3 |

**HIGH findings (2):**

1. **orchestrator08.py line 74-76** -- `task_805_wrapper` uses `**kwargs` which hides `graph` from `inspect.signature()`, so the graph parameter is never forwarded to task 805 via the legacy direct-call path in `phase_runner.py`.
2. **task_804_artifact_generation.py line 85-88** -- `read_json(setup_file)` is unprotected against `JSONDecodeError`, causing an unhandled crash if the file is malformed, unlike equivalent calls in tasks 806 and 807.

**MEDIUM findings (3):**

1. **task_801_entry_initialization.py line 134-148** -- `_find_closeout` primary path uses `project_root / ".outputs"` which does not match where `phase_runner.create_phase_closeout` writes (`ATOMIC_ROOT / ".outputs"`), making the primary check always fail; the fallback path masks this.
2. **task_802_deployment_setup.py line 115-117** -- Any non-`"1"` channel input produces an empty channels list with no warning or re-prompt, persisting an invalid configuration.
3. **task_803_agent_selection.py line 42-53 vs 150-157** -- UAT and non-UAT code paths produce structurally different JSON schemas for the same output file (`deployment-agents.json`).
