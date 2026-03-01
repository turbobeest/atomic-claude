# Code Audit: Phase 03 Tasking (Re-audit 2)

**Date:** 2026-02-28
**Auditor:** Claude Opus 4.6
**Scope:** 7 files in Phase 03 Tasking pipeline
**Criteria:** CRITICAL / HIGH / MEDIUM only (strict severity gate)
**Categories:** A through R (full checklist)

---

## Previously Reported Findings -- Status

The following findings from the prior two audits have been verified as **fixed**:

1. **FIXED** -- task_302 UAT schema mismatch: UAT mode now writes `decomposition_agents` / `validation_agents` keys, matching the non-UAT schema consumed by task_303. (Lines 66-70)
2. **FIXED** -- task_304 UAT `dependency-analysis.json` schema: Now writes `{"validation": {"passed": True, ...}}` matching what task_306 `_run_checklist` expects via `.get("validation", {}).get("passed", False)`. (Lines 61-70)
3. **FIXED** -- task_303 `_repair_json` trailing-text handling: Now uses `content.rindex("}") + 1` to find the last closing brace, correctly extracting JSON from LLM output with trailing commentary. (Line 769)
4. **FIXED** -- task_306 `_run_checklist` audit parse error: Now correctly appends `("Audit", "WARN")` and prints "Audit file could not be parsed" instead of marking a corrupted audit file as PASS. (Lines 244-247)

---

## File 1: phases/phase03/orchestrator03.py

No actionable findings.

The orchestrator is a thin delegation layer. Wrapper function signatures `(mem=None, graph=None)` are compatible with both call patterns in `phase_runner.py`: `task_func(mem, graph=graph)` (line 314) and `task_func(mem)` (lines 316/318). Module-level globals (`ATOMIC_ROOT`, `OUTPUT_DIR`, `UAT_MODE`) are consistent with the pattern used by all other orchestrators in the project.

---

## File 2: phases/phase_03_tasking/tasks/task_301_entry_initialization.py

No actionable findings.

Entry validation logic, TaskMaster initialization, provider configuration cascade (Bedrock -> Anthropic -> Ollama), `.env` writing with `.gitignore` protection, and `_append_env_vars` idempotency are all sound. The `_ensure_env_gitignored` call at line 321 correctly runs BEFORE `_append_env_vars` at line 322, ensuring `.gitignore` protects the `.env` file before any secrets are written.

---

## File 3: phases/phase_03_tasking/tasks/task_302_agent_selection.py

No actionable findings.

The UAT schema mismatch (previously HIGH) has been fixed. The PRD analysis regex patterns, agent recommendation logic, and interactive selection paths (approve/core/custom) are functionally correct. Index validation in `_custom_selection` (line 349-350) is properly bounds-checked.

---

## File 4: phases/phase_03_tasking/tasks/task_303_task_decomposition.py

| # | Category | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|---|----------|----------|---------|---------|------------------|----------------|
| 1 | O (data handling) | MEDIUM | `graph_context` is queried from the knowledge graph via `graph.query_task_context()` but the result is assigned to a local variable and never referenced again. The graph query executes (consuming resources and potentially failing with a logged warning), but its result is discarded. The task decomposition prompt is built without any graph context, even when graph data is available. | 94-100 | Run Phase 3 with a configured FalkorDB graph. Task 303 queries the graph, the query succeeds, but the returned context (prior phase decisions, existing task patterns, etc.) is not injected into the LLM decomposition prompt. The LLM decomposes the PRD without the benefit of graph context that was explicitly loaded. | Either pass `graph_context` into `_build_decomposition_prompt` as an additional context section (e.g., alongside `corpus_analysis`), or remove the dead query to avoid wasted graph I/O and misleading log messages. |
| 2 | O (data handling) | MEDIUM | `_merge_feature_tasks` silently drops cross-feature dependencies with no warning or tracking. When per-feature LLM calls produce tasks with dependency IDs referencing tasks from another feature's numbering scheme, those dependencies are removed (line 462 comment: "leave for task 304 dependency mapper"). However, task 304 only validates existing dependencies -- it does not rediscover dropped ones. The resulting DAG has missing edges. | 454-463 | PRD has cross-feature dependencies (e.g., F2 authentication tasks depend on F1 database setup tasks). Each feature is decomposed independently. The LLM for F2 emits `"dependencies": [3]` referencing F1's task 3. This dependency is not in `old_id_to_idx` for F2's `feat_idx`, so it is silently dropped. Task 304 validates the remaining deps and finds no issues. The work packages will schedule F2 tasks to run in parallel with F1 tasks they actually depend on. | Log dropped cross-feature deps as warnings. Optionally preserve them in an `"unresolved_dependencies"` field on the task so they can be surfaced during task 304 analysis or manual review. |

---

## File 5: phases/phase_03_tasking/tasks/task_304_dependency_analysis.py

| # | Category | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|---|----------|----------|---------|---------|------------------|----------------|
| 3 | O (data handling) | MEDIUM | `_compute_levels` does not filter task dependencies to valid IDs before computing levels. While `_validate_dependencies` runs first and catches invalid refs, the validation loop (lines 83-156) allows the user to choose "fix" and re-validate. Between validation passes, if the user fixes invalid refs but introduces a dependency on a valid task ID that itself has unresolvable deps (e.g., a long chain), the iterative level computation could default those tasks to level 0. The default-to-0 fallback at line 332-333 places unresolvable tasks at the same execution level as root tasks, potentially causing them to execute before their actual dependencies. | 306-333 | Tasks file has a deep chain where one intermediate task depends on a non-existent ID (detected and fixed by user), but the fix introduces a valid-but-deep chain that doesn't fully resolve within `len(tasks)+1` iterations (impossible in practice for acyclic graphs) OR: validation passes but a task's dependency list contains an ID that exists in `valid_ids` but whose own level was defaulted to 0 due to an earlier resolution failure. In that case, the dependent task resolves to level 1 instead of a deeper level, causing premature scheduling. | Filter `deps` to only IDs present in `task_map` within `_compute_levels` (line 308), consistent with how `_validate_dependencies` filters its adjacency list. Log when defaulting to level 0 at WARNING level rather than DEBUG. |
| 4 | F (contracts) | MEDIUM | `graph.validate_dependencies()` and `graph.fix_dependencies()` are called (lines 159-165), but fixes applied in the graph are never propagated back to `tasks.json`. After this code runs, the file-based task data and graph-based task data can have divergent dependency structures. Downstream consumers (task 306 closeout, Phase 4+ execution) read from `tasks.json`, not the graph, so graph fixes are effectively lost. | 159-169 | Graph validation detects and fixes a cycle or invalid reference in the knowledge graph. The fix is applied in FalkorDB but the on-disk `tasks.json` retains the original broken dependencies. Phase 4 reads `tasks.json` and encounters the unfixed dependency issue. | After `graph.fix_dependencies()`, export the corrected graph state back to `tasks.json`, or at minimum log a WARNING that graph and file state have diverged and instruct the user to reconcile. |

---

## File 6: phases/phase_03_tasking/tasks/task_305_phase_audit.py

No actionable findings.

The audit task is a thin wrapper around `core.audit.run_phase_audit`. Phase number extraction from `output_dir.name` is correct for the established naming convention (`3-tasking`). The task is intentionally non-blocking (always returns `True`), which is documented behavior and consistent with audit tasks in other phases.

---

## File 7: phases/phase_03_tasking/tasks/task_306_closeout.py

No actionable findings.

The previous finding about audit parse error handling (marking unparseable audit as PASS) has been fixed -- it now correctly reports WARN. The checklist logic, metrics gathering, markdown/JSON closeout generation, and memory checkpoint are all functionally sound. The `_memory_checkpoint` function only prints a summary (no actual persistence), but this is by design -- the actual memory save is handled by `phase_runner.py`'s memory infrastructure after task completion.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH     | 0 |
| MEDIUM   | 4 |
| **Total** | **4** |

### Finding Index

1. **MEDIUM** -- `task_303_task_decomposition.py`: `graph_context` queried from knowledge graph but result is never used in prompt building. Dead variable wastes graph I/O and omits available context from LLM input. (Lines 94-100)
2. **MEDIUM** -- `task_303_task_decomposition.py`: `_merge_feature_tasks` silently drops cross-feature dependencies with no warning or tracking, producing a DAG with missing edges that task 304 cannot recover. (Lines 454-463)
3. **MEDIUM** -- `task_304_dependency_analysis.py`: `_compute_levels` defaults unresolvable tasks to level 0 (root level) which could cause premature parallel scheduling if dependency resolution fails for any reason. (Lines 306-333)
4. **MEDIUM** -- `task_304_dependency_analysis.py`: Graph dependency fixes via `graph.fix_dependencies()` are not propagated back to `tasks.json`, causing file/graph state divergence. (Lines 159-169)

### Previously Fixed (4 items verified)

- task_302 UAT schema mismatch (was HIGH)
- task_304 UAT dependency-analysis.json schema (was MEDIUM)
- task_303 `_repair_json` trailing-text handling (was HIGH)
- task_306 `_run_checklist` audit parse error handling (was MEDIUM)
