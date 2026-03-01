# Phase 01 Discovery -- Code Audit (Re-Audit 2)

**Date:** 2026-02-28
**Auditor:** Claude Opus 4.6
**Scope:** Phase 01 orchestrator + 9 task files (101-109)
**Severity criteria:** CRITICAL / HIGH / MEDIUM only (strict)
**Prior audits:** phase-01-discovery.md, reaudit-phase-01-discovery.md

---

## Prior Findings Disposition

All 7 findings from the first re-audit were reviewed against the current code.

| Prior # | Severity | File | Status | Detail |
|---------|----------|------|--------|--------|
| 1 | HIGH | task_102 lines 173-177 | FIXED | `relative_to(atomic_root)` now wrapped in try/except with `relative_to(project_root)` fallback |
| 2 | MEDIUM | task_103 lines 478-484 | FIXED | `return default_experts` now correctly placed on line 483 after hallucination detection |
| 3 | MEDIUM | task_103 line 297 | FIXED | Now uses `f"Phases mapped:    {len(roster.get('phases', {}))}"` |
| 4 | MEDIUM | task_104 lines 601-611 | FIXED | Fence-stripping now only includes lines when `in_fence` is True |
| 5 | MEDIUM | task_105 lines 766-777 | FIXED | Fence-stripping now uses `'```' in raw` check with proper toggle |
| 6 | MEDIUM | task_105 lines 299-314 | PARTIALLY FIXED | Negation patterns and sentence anchoring added; residual false positives remain (see Finding 2 below) |
| 7 | MEDIUM | task_107 lines 432-443 | FIXED | DOT extraction now only captures lines when `in_code` is True |

---

## Files Audited

1. `phases/phase01/orchestrator01.py`
2. `phases/phase_01_discovery/tasks/task_101_entry_validation.py`
3. `phases/phase_01_discovery/tasks/task_102_import_requirements.py`
4. `phases/phase_01_discovery/tasks/task_103_agent_selection.py`
5. `phases/phase_01_discovery/tasks/task_104_opening_dialogue.py`
6. `phases/phase_01_discovery/tasks/task_105_discovery_work.py`
7. `phases/phase_01_discovery/tasks/task_106_approach_selection.py`
8. `phases/phase_01_discovery/tasks/task_107_discovery_diagrams.py`
9. `phases/phase_01_discovery/tasks/task_108_phase_audit.py`
10. `phases/phase_01_discovery/tasks/task_109_closeout.py`

---

### [phases/phase01/orchestrator01.py]

No actionable findings.

The orchestrator correctly wires task modules via `__init__.py`, passes `ATOMIC_ROOT`, `OUTPUT_DIR`, `UAT_MODE`, `mem`, and `graph` through wrapper functions, and delegates to `run_phase_tasks()`. Module imports, task-artifact mapping, and return-type contracts are all correct.

---

### [phases/phase_01_discovery/tasks/task_101_entry_validation.py]

No actionable findings.

All prior concerns have been verified as non-issues or already addressed. The `content_hash=str(hash(...))[:16]` produces non-deterministic values across Python invocations, but `content_hash` on Source nodes is metadata-only and unused for identity or dedup.

---

### [phases/phase_01_discovery/tasks/task_102_import_requirements.py]

| # | Category | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|---|----------|----------|---------|---------|------------------|----------------|
| 1 | L (Operational) | HIGH | `execute()` accepts `uat_mode` parameter but never checks it; `input()` calls on lines 76, 82, and 141 block the pipeline in UAT mode | 32, 76, 82, 141 | When `ATOMIC_UAT_MODE=true` and the project has no RST files (the common case), the pipeline reaches line 76 (`input("  Does your project use Sphinx-Needs? [y/N]: ")`). In UAT mode, all other tasks (101, 103-109) have an early `if uat_mode:` guard that bypasses interactive prompts and returns True. Task 102 lacks this guard. The pipeline hangs waiting for stdin, blocking the automated UAT run. If stdin is closed (piped mode), `EOFError` is raised and the task crashes. | Add an early UAT guard matching the pattern in all other tasks: `if uat_mode: info("Requirements import: skipped (UAT mode)"); return True` |

---

### [phases/phase_01_discovery/tasks/task_103_agent_selection.py]

No actionable findings.

All three prior findings (hallucinated agent fallback, "Phases mapped" count, agent suggestion validation) have been fixed. The hallucination guard on lines 478-483 now correctly returns `default_experts` when all LLM suggestions fail validation. The phases count on line 297 now derives dynamically from `roster.get('phases', {})`.

---

### [phases/phase_01_discovery/tasks/task_104_opening_dialogue.py]

No actionable findings.

The fence-stripping logic in `_synthesize_dialogue()` (lines 601-611) has been corrected to only include lines when `in_fence` is True. The synthesis fallback provides sensible defaults. All conversation-loop paths handle empty input, exit commands, and canvas commands correctly.

---

### [phases/phase_01_discovery/tasks/task_105_discovery_work.py]

| # | Category | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|---|----------|----------|---------|---------|------------------|----------------|
| 2 | B (Logic) | MEDIUM | Closure-intent regex triggers false positives on sentence-initial closure words used in non-closure context | 304-314 | User types `"Sounds good. Let's finish discussing the API design."` -- the regex `(?:^|\.\s+|\!\s+|\?\s+)(?:let'?s?\s+)?(?:done|proceed|move on|wrap up|finish|ready)\b` matches because `\.\s+` anchors at the period, `let's\s+` matches, and `finish\b` matches. The deliberation terminates immediately with "Detected closure intent" even though the user intended to continue discussing a specific topic. The negation pattern list on lines 300-302 does not cover this case because the user is not negating closure -- they are using a closure word in a different syntactic context (transitive verb: "finish discussing"). Other triggering inputs: `"Great point. Ready the deployment plan next?"`, `"OK. Wrap up the authentication discussion first."` | Add a confirmation prompt when closure intent is detected: `"End deliberation? [Y/n]: "`. This is the most robust fix because heuristic regex cannot reliably distinguish transitive from intransitive uses of these verbs. Alternatively, require the closure word to be the LAST word in the input or the entire input. |

---

### [phases/phase_01_discovery/tasks/task_106_approach_selection.py]

No actionable findings.

The multi-section human review gate handles all user input paths correctly. The `reopen` action correctly returns `False` to signal the phase runner for backtracking. Canvas integration is wrapped in try/except. JSON and markdown outputs are generated with consistent data.

---

### [phases/phase_01_discovery/tasks/task_107_discovery_diagrams.py]

No actionable findings.

The DOT extraction logic (lines 432-443) has been corrected to only capture lines within code fences. The subprocess calls for graphviz include proper timeout handling. The retry/approval loop handles all user choices.

---

### [phases/phase_01_discovery/tasks/task_108_phase_audit.py]

No actionable findings.

The `print(print_green(...))` pattern on lines 63 and 65 is functionally correct -- `print_green` returns an ANSI-colored string which `print()` outputs. Phase number extraction handles the no-hyphen edge case via early return on line 45. The task correctly delegates to `run_phase_audit()` and is designed to be non-blocking (always returns True).

---

### [phases/phase_01_discovery/tasks/task_109_closeout.py]

| # | Category | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|---|----------|----------|---------|---------|------------------|----------------|
| 3 | R (Correctness) | MEDIUM | Session-end banner uses wrong Unicode box-drawing character on closing border line | 232 | Every non-UAT execution of task 109 displays the session-end banner. Line 232 prints `"╔═══...═══╝"` which uses the top-left corner character `╔` (U+2554) for what should be the bottom-left position. The correct character is `╚` (U+255A). This produces a visually malformed box where the bottom border appears to have two top-left corners. | Change line 232 from `"╔═══════════════════════════════════════════════════════════════╝"` to `"╚═══════════════════════════════════════════════════════════════╝"` |
| 4 | Q (Data Accuracy) | MEDIUM | Closeout markdown artifact table lists two non-existent files | 353, 355 | Every non-UAT execution generates `phase-01-closeout.md` which contains an "Artifacts Produced" table. Line 353 lists `first-principles.json` -- no Phase 1 task produces this file (there is a `first-principles-analyst` agent name in task_105, but no corresponding output file). Line 355 lists `deliberation-log.json` -- task_105 actually produces `deliberation-log.md` (defined on line 59 of task_105). Anyone reviewing the closeout document or using it to verify phase completion will find two phantom artifacts. | Remove the `first-principles.json` row entirely. Change `deliberation-log.json` to `deliberation-log.md` on line 355. Also consider adding `consensus.json` and `ingested-context.md` which ARE produced by task_105 but are missing from the table. |
| 5 | Q (Data Consistency) | MEDIUM | Normal vs UAT closeout JSON uses different types for `phase` field | 398, 428 | Normal closeout on line 398: `"phase": 1` (integer). UAT closeout on line 428: `"phase": "1-discovery"` (string). Any downstream code that reads `closeout.json` and checks `data["phase"] == 1` will fail for UAT closeouts, and code checking `data["phase"] == "1-discovery"` will fail for normal closeouts. The phase_runner's `create_phase_closeout()` (in `orchestration/phase_runner.py` line 481) uses `"phase": phase_id` (string like `"1-discovery"`), creating a third variant. This inconsistency means closeout verification logic must handle all three formats. | Standardize on string format `"1-discovery"` to match the `phase_id` used throughout the codebase. Change line 398 to `"phase": "1-discovery"`. |

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 4 |

### Finding Index

| # | Severity | File | Line(s) | Summary |
|---|----------|------|---------|---------|
| 1 | HIGH | task_102_import_requirements.py | 32, 76, 82, 141 | `uat_mode` parameter accepted but never checked; `input()` calls block or crash the pipeline in UAT mode |
| 2 | MEDIUM | task_105_discovery_work.py | 304-314 | Closure-intent regex triggers false positives on sentence-initial closure words used transitively (e.g., "Let's finish discussing...") |
| 3 | MEDIUM | task_109_closeout.py | 232 | Wrong Unicode box character `╔` instead of `╚` on session-end banner closing border |
| 4 | MEDIUM | task_109_closeout.py | 353, 355 | Closeout artifact table lists non-existent `first-principles.json` and incorrect `deliberation-log.json` (should be `.md`) |
| 5 | MEDIUM | task_109_closeout.py | 398, 428 | Normal closeout uses `"phase": 1` (int) but UAT closeout uses `"phase": "1-discovery"` (str) -- type inconsistency |

**Total: 0 critical, 1 high, 4 medium.**
