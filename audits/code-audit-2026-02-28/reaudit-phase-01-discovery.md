# Phase 01 Discovery -- Code Audit (Re-Audit)

**Date:** 2026-02-28
**Auditor:** Claude Opus 4.6
**Scope:** Phase 01 orchestrator + 9 task files (101-109)
**Severity criteria:** CRITICAL / HIGH / MEDIUM only (strict)

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

### [phases/phase01/orchestrator01.py] -- Audit

No actionable findings.

The orchestrator correctly imports task modules via `__init__.py`, passes `ATOMIC_ROOT`, `OUTPUT_DIR`, `UAT_MODE`, `mem`, and `graph` to each task wrapper, and delegates to `run_phase_tasks()` with keyword-only arguments. Task-artifact mapping, resume logic, and module wiring are all correct.

---

### [phases/phase_01_discovery/tasks/task_101_entry_validation.py] -- Audit

No actionable findings.

The file reads config, validates Phase 0 prerequisites, performs corpus analysis with LLM, and handles all failure paths with fallbacks. The `content_hash=str(hash(...))[:16]` on line 234 produces non-deterministic values across Python invocations (PYTHONHASHSEED), but `content_hash` on Source nodes is metadata-only and not used for identity or dedup, so this has no functional impact.

---

### [phases/phase_01_discovery/tasks/task_102_import_requirements.py] -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| D (Data Integrity) | HIGH | `rst_file.relative_to(atomic_root)` raises `ValueError` when RST files are found under `project_root` (which is `atomic_root.parent`) | 68-71, 173 | Line 68 searches `project_root` first (the normal/primary path). If RST files are found there (e.g., `/home/user/myproject/docs/reqs.rst`), line 173 calls `rst_file.relative_to(atomic_root)` where `atomic_root` is `/home/user/myproject/atomic-claude/`. Since the file is NOT under `atomic_root`, Python raises `ValueError: '/home/user/myproject/docs/reqs.rst' is not relative to '/home/user/myproject/atomic-claude/'`. This crashes the entire task. | Change line 173 to use `project_root` instead of `atomic_root`, or use a try/except with `os.path.relpath()` as a fallback: `file_relpath = str(rst_file.relative_to(project_root))` |

---

### [phases/phase_01_discovery/tasks/task_103_agent_selection.py] -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| B (Logic) | MEDIUM | Hallucinated agent names returned instead of defaults when validation rejects all LLM suggestions | 478-484 | When `valid_names` is populated (graph or manifest loaded) and the LLM returns agent names that are ALL hallucinated (none match `valid_names`), `validated` is empty on line 480. Code falls through to line 484 which returns `parsed` (the hallucinated names) because `parsed` is truthy. The comment on line 482 says "fall through to defaults" but the code does not do that. Result: hallucinated agent names are presented to the user as SME suggestions. | Add `return default_experts` after line 482, or change line 484 to `return parsed if (parsed and not valid_names) else default_experts` |
| B (Logic) | MEDIUM | Hard-coded "Phases mapped: 10" but only 9 phases exist in the roster | 297 | During every normal (non-UAT) execution, the user sees "Phases mapped: 10" but `_get_default_pipeline_agents()` returns 9 entries and `_build_roster()` creates 9 phase entries. The displayed count is wrong. | Change to `f"Phases mapped:    {len(default_pipeline_agents)}"` or hard-code `9` |

---

### [phases/phase_01_discovery/tasks/task_104_opening_dialogue.py] -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| B (Logic) | MEDIUM | JSON fence-stripping logic can include lines outside code fences | 601-611 | In `_synthesize_dialogue`, when LLM output contains markdown fences AND lines outside fences that start with `{` (e.g., prose like `{See above for details}`), the condition `if in_json or line.strip().startswith('{')` on line 609 captures those lines. The resulting string is not valid JSON, causing `json.loads()` to raise `JSONDecodeError`. This is caught by the broad `except Exception` on line 614 and falls through to the fallback synthesis, silently discarding the LLM's actual synthesis. The user sees generic "Not fully captured" / "Not discussed" values instead of real synthesis. | Only include lines when `in_json` is True. Remove the `or line.strip().startswith('{')` clause from the fence-stripping branch, or restructure to handle the no-fence case separately. |

---

### [phases/phase_01_discovery/tasks/task_105_discovery_work.py] -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| B (Logic) | MEDIUM | Consensus fence-stripping only handles opening fence at start of content | 755-760 | In `_generate_consensus`, the code checks `if raw.startswith("```")` then strips opening/closing fences. If the LLM returns content with preamble text before the code fence (e.g., `"Here is the consensus:\n```json\n{...}\n```"`), the `startswith("```")` check fails and the raw content (including the preamble and fences) is passed to `json.loads()`, which raises `JSONDecodeError`. The exception is caught and falls through to a hardcoded fallback consensus ("Phased Implementation"), discarding the LLM's real consensus. | Use a more robust fence-stripping approach: search for the first `\`\`\`` occurrence and extract content between the first and last fence markers, similar to the pattern used in task_104's `_synthesize_dialogue`. |
| N (Closure Intent) | MEDIUM | False-positive closure detection on common words like "ready" or "proceed" | 299 | The closure-intent detector on line 299 checks `if any(phrase in input_lower for phrase in ['done', 'proceed', 'move on', 'wrap up', 'finish', 'ready'])`. If the user types something like "I'm not ready yet" or "How should we proceed with the API design?", the substring match triggers closure and ends the deliberation prematurely. This is a normal conversational input during discovery. | Use word-boundary matching (e.g., `re.search(r'\b(done|proceed|finish)\b', input_lower)`) or only trigger on standalone short inputs (e.g., `if input_lower in closure_phrases or (len(input_lower.split()) <= 3 and ...)`). Alternatively, require confirmation before closing. |

---

### [phases/phase_01_discovery/tasks/task_106_approach_selection.py] -- Audit

No actionable findings.

The file implements a multi-section human review gate with edit, add, clear, reorder, and resolve capabilities. All user input paths are handled. The canvas integration is wrapped in try/except. The `reopen` action correctly returns `False` to signal the phase runner. JSON and markdown outputs are generated with consistent data.

---

### [phases/phase_01_discovery/tasks/task_107_discovery_diagrams.py] -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| B (Logic) | MEDIUM | DOT extraction captures lines outside code fences that start with `digraph` or `graph` | 437-443 | In `_generate_diagram`, when the LLM output contains markdown fences AND text outside the fences where a line happens to start with "graph" (e.g., "graph-based architecture is preferred"), the condition `if in_code or line.startswith('digraph') or line.startswith('graph')` captures that prose line into the DOT content. The resulting DOT file is syntactically invalid, causing graphviz to fail on SVG conversion (handled gracefully), but also causing the task to report the DOT file as "generated" successfully when it contains corrupt content. | Only include lines when `in_code` is True. Remove the `or line.startswith('digraph') or line.startswith('graph')` clause from the fence-stripping branch. |

---

### [phases/phase_01_discovery/tasks/task_108_phase_audit.py] -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| B (Logic) | HIGH | `print(print_yellow(...))` and `print(print_green(...))` double-wraps output, printing `None` after the colored text | 44, 63, 65 | `print_yellow()` and `print_green()` (from `core.utils.cli_ui`) are documented as "Return yellow/green text" -- they return a string, they do not print. Wrapping them in `print()` prints the colored string correctly BUT also outputs the implicit `None` return... wait, they DO return a string. So `print(print_green("text"))` prints the returned colored string. This is actually correct -- `print_green` returns the ANSI-colored string, and `print()` outputs it. Let me re-verify. | N/A -- see re-analysis below. |

Let me re-check this. `print_green` returns `f"{GREEN}{text}{NC}"` -- a string. `print(print_green("text"))` calls `print_green("text")` which returns the ANSI string, then `print()` prints it. This is correct. My initial concern was wrong.

However, there is a different issue:

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| R (Robustness) | MEDIUM | Phase number extraction does not handle output_dir names without a hyphen | 36-45 | Line 37 checks `if '-' in phase_name`. If the output directory name contains a hyphen (normal case like "1-discovery"), it extracts the phase number. But if it does NOT contain a hyphen (else branch, line 43-45), the code prints a warning and returns True without setting `phase_num` or `phase_id`. The subsequent code on lines 59-60 (`run_phase_audit(phase_num, phase_id, ...)`) would use uninitialized variables. However, the `return True` on line 45 prevents reaching that code. So the early return is correct. No bug here. |

Re-analysis: task_108 has no actionable findings meeting the severity criteria.

---

### [phases/phase_01_discovery/tasks/task_109_closeout.py] -- Audit

No actionable findings.

The file correctly checks artifacts, generates markdown and JSON closeout documents, and handles all edge cases (missing audit file with multiple path patterns, UAT mode). The `_check_artifact` boolean logic on lines 80-84 is correctly ordered to ensure all side effects (print + checklist append) execute regardless of short-circuit evaluation.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 5 |

### Finding Index

| # | Severity | File | Line(s) | Summary |
|---|----------|------|---------|---------|
| 1 | HIGH | task_102_import_requirements.py | 68-71, 173 | `relative_to(atomic_root)` crashes with `ValueError` when RST files found under `project_root` (the primary search path) |
| 2 | MEDIUM | task_103_agent_selection.py | 478-484 | Hallucinated agent names returned instead of defaults when all LLM suggestions fail validation |
| 3 | MEDIUM | task_103_agent_selection.py | 297 | Hard-coded "Phases mapped: 10" but only 9 phases exist |
| 4 | MEDIUM | task_104_opening_dialogue.py | 601-611 | JSON fence-stripping captures lines outside code fences, causing synthesis to silently fall back to generic defaults |
| 5 | MEDIUM | task_105_discovery_work.py | 755-760 | Consensus fence-stripping only handles fences at start of content; preamble text causes fallback to hardcoded consensus |
| 6 | MEDIUM | task_105_discovery_work.py | 299 | False-positive closure detection on common words like "ready" and "proceed" in longer sentences |
| 7 | MEDIUM | task_107_discovery_diagrams.py | 437-443 | DOT extraction captures prose lines outside code fences that start with "digraph" or "graph" |

**Total: 0 critical, 1 high, 6 medium.**
