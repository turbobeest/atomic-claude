# Code Audit: Phase 02 + Phase 03 (Pass 4 / Re-audit 3)

**Date:** 2026-02-28
**Auditor:** Claude Opus 4.6
**Scope:** 18 files across Phase 02 (PRD) and Phase 03 (Tasking)
**Criteria:** CRITICAL / HIGH / MEDIUM only. Each finding has a specific, reproducible trigger scenario.

---

## Phase 02 Files

### 1. `phases/phase02/orchestrator02.py`

No actionable findings.

### 2. `phases/phase_02_prd/tasks/task_201_entry_validation.py`

No actionable findings.

### 3. `phases/phase_02_prd/tasks/task_202_prd_setup.py`

No actionable findings.

### 4. `phases/phase_02_prd/tasks/task_203_prd_interview.py`

No actionable findings.

### 5. `phases/phase_02_prd/tasks/task_204_agent_selection.py`

No actionable findings.

### 6. `phases/phase_02_prd/tasks/task_205_prd_authoring.py`

**Finding 205-A [MEDIUM]: `_strip_llm_preamble` regex misses `##` headings; LLM preamble leaks into PRD**

- **Category:** I (Data Processing)
- **File:** `/mnt/walnut-drive/dev/atomic-claude/phases/phase_02_prd/tasks/task_205_prd_authoring.py`
- **Lines:** 602-605
- **Defect:** `_strip_llm_preamble` searches for `^# \d+\.` (single `#`, numbered). When the LLM generates sections with `##` headings (e.g., `## 0. Vision & Executive Summary`) or unnumbered headings (e.g., `# Vision`), the regex does not match. Any preamble text the LLM emits before the section header is retained in the PRD content.
- **Trigger:** LLM returns `I have sufficient context to write this section.\n\n## 0. Vision & Executive Summary\n...`. The preamble "I have sufficient context..." is included verbatim in the PRD because the regex requires `# \d+\.` (single `#`, numbered).
- **Impact:** LLM thinking/reflection text contaminates the PRD document. Downstream validation (task 206) may flag spurious content issues.
- **Suggested fix:** Broaden the regex to `r'^(#{1,2}\s+(?:\d+\.)?\s*\w)'` to match both `#` and `##` headings, numbered or unnumbered.

**Finding 205-B [MEDIUM]: `_is_valid_section_output` 500-char threshold rejects valid short sections during resume**

- **Category:** I (Data Processing)
- **File:** `/mnt/walnut-drive/dev/atomic-claude/phases/phase_02_prd/tasks/task_205_prd_authoring.py`
- **Lines:** 608-614
- **Defect:** `_is_valid_section_output` requires content to be at least 500 characters AND contain `##` or `###` subheadings. This function is only used by `_detect_completed_sections` (line 627) for resume detection. Sections like "Vision & Executive Summary" (gen 1) or "Risks & Success Metrics & Approval" (gen 12) can legitimately be under 500 characters for small projects.
- **Trigger:** Run Phase 2 on a small project. LLM generates a concise Vision section (~300 chars). User interrupts mid-authoring. On resume, `_detect_completed_sections` marks the Vision section as invalid (under 500 chars). The user sees "Invalid sections (1): 1-Vision" in the resume dialog, and if they choose "Resume", gen 1 is regenerated unnecessarily. The previously written PRD file still contains the original content, so the regeneration creates a duplicate.
- **Impact:** Valid sections incorrectly classified as invalid during resume detection. Unnecessary LLM calls and potential content duplication.

### 7. `phases/phase_02_prd/tasks/task_206_prd_validation.py`

No actionable findings.

### 8. `phases/phase_02_prd/tasks/task_206b_prd_revision.py`

No actionable findings.

### 9. `phases/phase_02_prd/tasks/task_207_prd_approval.py`

**Finding 207-A [MEDIUM]: View actions consume iteration budget, causing unintended auto-approval**

- **Category:** E (Control Flow)
- **File:** `/mnt/walnut-drive/dev/atomic-claude/phases/phase_02_prd/tasks/task_207_prd_approval.py`
- **Lines:** 84-85, 124-138, 168-169
- **Defect:** The review loop condition is `refinement_count < max_refinements and total_iterations < max_total_iterations` (line 84). `total_iterations` is incremented unconditionally at line 85. The `view` branch (lines 124-138) does not increment `refinement_count` but does consume a `total_iterations` tick. After 50 view operations, the loop exits and executes auto-approval at lines 168-169: `approve_prd(approval_file, prd_file, "auto-approved")`.
- **Trigger:** User selects "view" repeatedly (50 times) to inspect the PRD during the approval step. The `total_iterations` counter reaches 50. The while loop exits, and the PRD is auto-approved with approver set to `"auto-approved"` without explicit user consent.
- **Impact:** PRD auto-approved without the user ever choosing "approve". The `total_iterations` guard conflates read-only navigation with mutation actions.
- **Suggested fix:** Only increment `total_iterations` for actions that modify state (refine, custom). Alternatively, exclude non-mutating actions from the counter.

### 10. `phases/phase_02_prd/tasks/task_208_phase_audit.py`

No actionable findings.

### 11. `phases/phase_02_prd/tasks/task_209_closeout.py`

No actionable findings.

---

## Phase 03 Files

### 12. `phases/phase03/orchestrator03.py`

No actionable findings.

### 13. `phases/phase_03_tasking/tasks/task_301_entry_initialization.py`

No actionable findings.

### 14. `phases/phase_03_tasking/tasks/task_302_agent_selection.py`

**Finding 302-A [MEDIUM]: Feature/NFR count regexes never match pipeline-generated PRDs**

- **Category:** I (Data Processing)
- **File:** `/mnt/walnut-drive/dev/atomic-claude/phases/phase_03_tasking/tasks/task_302_agent_selection.py`
- **Lines:** 228-229 (`_analyze_prd`)
- **Defect:** The regex `r'^## feature f\d+'` (case-insensitive) expects headings like `## Feature F1`. The PRD template (task 205) generates headings like `## 3. Feature Requirements (FRs)` with individual features under `### F1: Title` or `#### FR-001:`. Similarly, `r'^## nfr-\d+'` expects `## NFR-001` but PRDs use NFR IDs inside tables (`| NFR-001 | ...`), not as headings. Neither regex matches any PRD generated by the pipeline.
- **Trigger:** Run Phase 3 after Phase 2. `analysis['feature_count']` and `analysis['nfr_count']` are always 0, regardless of the actual number of features and NFRs in the PRD.
- **Impact:** The `test-strategy-planner` agent recommendation (triggered when `feature_count > 5`, line 297) never activates based on feature count. Projects with many features but no explicit testing keywords in the PRD will miss this recommendation.
- **Suggested fix:** Match actual PRD patterns:
  - Features: `r'#{2,4}\s+F\d+[:\s]'` or count `FR-\d+` occurrences in body text
  - NFRs: `r'NFR-\d+'` (body text search, not heading-anchored)

### 15. `phases/phase_03_tasking/tasks/task_303_task_decomposition.py`

**Finding 303-A [MEDIUM]: Per-feature merge drops cross-feature dependencies silently**

- **Category:** I (Data Processing)
- **File:** `/mnt/walnut-drive/dev/atomic-claude/phases/phase_03_tasking/tasks/task_303_task_decomposition.py`
- **Lines:** 452-476 (`_merge_feature_tasks`)
- **Defect:** When decomposing features individually (per-feature mode, triggered for PRDs with 2+ features), each feature's tasks have local IDs starting from 1. During merge, `_merge_feature_tasks` remaps IDs and dependencies within each feature's namespace. Cross-feature dependencies (where feature F2's task depends on a task from feature F1) cannot be resolved because the lookup at line 460 only searches the current feature's namespace: `old_id_to_idx.get((feat_idx, dep_id))`. Unresolvable cross-feature deps are dropped with only a logger warning (line 472-476).
- **Trigger:** PRD with 2+ features where the LLM generates cross-feature dependencies. Example: F1 generates tasks with IDs 1-5 (database schema). F2 generates tasks with IDs 1-5 (API endpoints). F2's task 2 (endpoint implementation) depends on ID 3 (from F1's namespace: schema migration). The merge remaps F1's task 3 to global ID 3, F2's task 2 to global ID 8, but the dependency from ID 8 to "old ID 3 in F2's namespace" finds nothing (F2 has no task 3 that maps to a schema migration). The dependency is dropped.
- **Impact:** Task 304's DAG will show tasks as independent when they actually depend on each other. Work packages may schedule dependent tasks in the same parallel wave.
- **Suggested fix:** After intra-feature lookup fails, attempt cross-feature resolution by searching `old_id_to_idx` across all `(feat_idx, dep_id)` combinations.

### 16. `phases/phase_03_tasking/tasks/task_304_dependency_analysis.py`

**Finding 304-A [MEDIUM]: `_compute_levels` defaults unresolved tasks to level 0 (root level)**

- **Category:** I (Data Processing)
- **File:** `/mnt/walnut-drive/dev/atomic-claude/phases/phase_03_tasking/tasks/task_304_dependency_analysis.py`
- **Lines:** 307-362, specifically 342-344
- **Defect:** After the iterative level computation loop, any task that was not assigned a level is defaulted to level 0 (line 343: `level = 0`). This can occur when the graph-based dependency fix (lines 159-181) modifies the `tasks` list AFTER the DAG validation has passed. The graph fix at line 174 reassigns the local `tasks` variable with potentially different dependency structures that have not been re-validated. If the graph fix introduces a dependency cycle or references that the iterative solver cannot resolve, those tasks silently default to level 0.
- **Trigger:** Knowledge graph is available and `graph.validate_dependencies()` returns invalid. `graph.fix_dependencies()` runs and `graph.get_tasks()` returns a modified task list with new dependency edges. The modified tasks are used for level computation at line 184 without re-validation. If the fix introduces a subtle cycle or a dependency on a task that hasn't been leveled yet in the current pass, that task defaults to level 0.
- **Impact:** Tasks that should execute AFTER their prerequisites are placed at the root level (level 0), scheduled for the first parallel wave alongside tasks they depend on. This violates dependency ordering.
- **Suggested fix:** After the iterative loop, default unresolved tasks to `max(levels_map.values()) + 1` instead of 0, ensuring they execute last rather than first.

### 17. `phases/phase_03_tasking/tasks/task_305_phase_audit.py`

No actionable findings.

### 18. `phases/phase_03_tasking/tasks/task_306_closeout.py`

No actionable findings.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0     |
| HIGH     | 0     |
| MEDIUM   | 6     |

### Findings Index

| ID    | Severity | File                           | Description |
|-------|----------|--------------------------------|-------------|
| 205-A | MEDIUM   | task_205_prd_authoring.py      | `_strip_llm_preamble` regex misses `##` headings; LLM preamble leaks into PRD |
| 205-B | MEDIUM   | task_205_prd_authoring.py      | 500-char threshold in `_is_valid_section_output` rejects valid short sections on resume |
| 207-A | MEDIUM   | task_207_prd_approval.py       | View actions consume `total_iterations` budget, causing unintended auto-approval after 50 views |
| 302-A | MEDIUM   | task_302_agent_selection.py    | Feature/NFR count regexes never match pipeline-generated PRDs; counts always 0 |
| 303-A | MEDIUM   | task_303_task_decomposition.py | Per-feature merge drops cross-feature dependencies silently |
| 304-A | MEDIUM   | task_304_dependency_analysis.py | Unresolved tasks default to level 0 (root), violating dependency ordering |

**Total: 0 critical, 0 high, 6 medium.**
