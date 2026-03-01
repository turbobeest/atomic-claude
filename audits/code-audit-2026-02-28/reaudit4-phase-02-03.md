# Code Audit: Phase 02 + Phase 03 (Pass 5 / Re-audit 4)

**Date:** 2026-02-28
**Auditor:** Claude Opus 4.6
**Scope:** 18 files across Phase 02 (PRD) and Phase 03 (Tasking)
**Criteria:** CRITICAL / HIGH / MEDIUM only. Each finding must have a specific, reproducible trigger scenario.

---

## Fix Verification (6 fixes from Pass 4)

### Fix 1: task_205 `_strip_llm_preamble` regex broadened

**File:** `phases/phase_02_prd/tasks/task_205_prd_authoring.py`, line 603
**Expected:** Regex changed to `r'^(#{1,2}\s+(?:\d+\.)?\s*\w)'` to match `##` and unnumbered headings.
**Verified:** CONFIRMED. Line 603 reads `re.search(r'^(#{1,2}\s+(?:\d+\.)?\s*\w)', content, re.MULTILINE)`. The regex now matches:
  - `# 1. Vision` (single `#`, numbered)
  - `## Vision` (double `##`, unnumbered)
  - `## 0. Vision & Executive Summary` (double `##`, numbered)
  - Any combination of `#`/`##` with optional `\d+.` prefix.

### Fix 2: task_205 `_is_valid_section_output` threshold and logic

**File:** `phases/phase_02_prd/tasks/task_205_prd_authoring.py`, lines 609-619
**Expected:** Threshold lowered to 200 chars, AND logic changed to OR logic.
**Verified:** CONFIRMED. `has_sufficient_length = len(content) >= 200` (line 617), `has_subheadings = bool(re.search(...))` (line 618), `return has_sufficient_length or has_subheadings` (line 619). A section is now valid if it has >= 200 characters OR contains `##`/`###` subheadings. Short but structured sections pass validation.

### Fix 3: task_207 `total_iterations` only incremented for mutating actions

**File:** `phases/phase_02_prd/tasks/task_207_prd_approval.py`, lines 122-166
**Expected:** View actions do not increment `total_iterations`.
**Verified:** CONFIRMED. The `view` branch (lines 122-136) contains no counter increment. Only `custom` (line 140: `total_iterations += 1`) and `refine` (line 156: `total_iterations += 1`) increment the counter. The `approve` branch (lines 113-120) exits the loop via `return True`. The `else` (invalid choice, line 165-166) prints an error and continues without incrementing.

### Fix 4: task_302 feature/NFR count regexes updated

**File:** `phases/phase_03_tasking/tasks/task_302_agent_selection.py`, lines 228-233
**Expected:** Feature regex changed to `r'#{2,4}\s+F\d+[:\s]'` + body `FR-\d+`; NFR regex changed to body text `NFR-\d+`.
**Verified:** CONFIRMED. Line 228: `re.findall(r'#{2,4}\s+F\d+[:\s]', content, re.MULTILINE | re.IGNORECASE)` matches headings like `### F1:`, `#### FR-001:`. Line 229: `re.findall(r'FR-\d+', content, re.IGNORECASE)` finds inline `FR-001` occurrences. Line 230: `max(len(heading_features), len(set(inline_features)))` takes the better count. Line 233: `len(set(re.findall(r'NFR-\d+', content, re.IGNORECASE)))` searches body text for `NFR-001` patterns. Note: content is `.lower()`'d on line 225, and all regexes use `re.IGNORECASE`, which is redundant but not harmful.

### Fix 5: task_303 cross-feature dependency resolution added

**File:** `phases/phase_03_tasking/tasks/task_303_task_decomposition.py`, lines 467-482
**Expected:** After intra-feature lookup fails, search across all feature indices.
**Verified:** CONFIRMED. Lines 467-482 implement cross-feature resolution: when `old_id_to_idx.get((feat_idx, dep_id))` returns None (intra-feature miss), a loop iterates `other_feat_idx` across all features (lines 469-480). If a match is found via `old_id_to_idx.get((other_feat_idx, dep_id))`, the dependency is resolved to the remapped ID and logged. The `break` at line 480 prevents ambiguous multiple matches. Unresolved dependencies are logged and dropped (lines 481-482, 494-499).

### Fix 6: task_304 unresolved tasks default to `max(levels) + 1`

**File:** `phases/phase_03_tasking/tasks/task_304_dependency_analysis.py`, lines 341-351
**Expected:** Unresolved tasks default to `max(levels) + 1` instead of 0.
**Verified:** CONFIRMED. Line 341: `fallback_level = max(levels_map.values(), default=0) + 1 if levels_map else 0`. When `levels_map` has entries, the fallback is one level beyond the deepest resolved task. When `levels_map` is empty (impossible after successful validation), fallback is 0. Lines 346-351: tasks not in `levels_map` get `fallback_level` with a warning log message indicating they'll execute in the "last wave".

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

Previous findings 205-A and 205-B are resolved. No new actionable findings.

Notes reviewed and dismissed:
- `_strip_llm_preamble` regex does not match `###` headings. Assessed as acceptable: PRD section generators produce `#` or `##` top-level headings per the prompt instructions. A `###` start would require LLM deviation from the explicit "Start with the section header(s)" instruction.
- `_rebuild_prd_content` has no try/except around `read_file` / `extract_markdown` / `_strip_llm_preamble` calls. Assessed as acceptable: the caller `_detect_completed_sections` wraps these same operations in try/except, and `_rebuild_prd_content` is only called with gen numbers that already passed validation in `_detect_completed_sections`.

### 7. `phases/phase_02_prd/tasks/task_206_prd_validation.py`

No actionable findings.

### 8. `phases/phase_02_prd/tasks/task_206b_prd_revision.py`

No actionable findings.

Notes reviewed and dismissed:
- `apply_edit_blocks` fuzzy fallback permanently normalizes trailing whitespace in content after the first fuzzy match (line 263 assigns from `norm_content`). Assessed as acceptable: trailing whitespace is insignificant in Markdown. The fuzzy fallback is a degraded-but-functional path for when LLM search text has whitespace differences.

### 9. `phases/phase_02_prd/tasks/task_207_prd_approval.py`

Previous finding 207-A is resolved. No new actionable findings.

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

Previous finding 302-A is resolved. No new actionable findings.

### 15. `phases/phase_03_tasking/tasks/task_303_task_decomposition.py`

Previous finding 303-A is resolved. No new actionable findings.

Notes reviewed and dismissed:
- Cross-feature dependency resolution uses `break` on first match (line 480), which is ambiguous when multiple features have tasks with the same old ID. Assessed as acceptable: the alternative (matching all) would create duplicate dependencies; first-match is a pragmatic choice with appropriate logging.

### 16. `phases/phase_03_tasking/tasks/task_304_dependency_analysis.py`

Previous finding 304-A is resolved. No new actionable findings.

Notes reviewed and dismissed:
- Graph-fixed tasks (lines 158-181) bypass `_validate_dependencies` re-validation. If `graph.fix_dependencies()` introduces cycles or invalid refs, `_compute_levels` will fail to resolve those tasks. However, the fallback-to-last-level fix ensures these tasks execute last (safe degradation) rather than first (previous broken behavior). The DFS cycle detection at lines 260-296 was verified as algorithmically correct for the reverse-adjacency representation used.

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
| MEDIUM   | 0     |

All 6 findings from Pass 4 have been verified as correctly fixed. No new findings at CRITICAL, HIGH, or MEDIUM severity were identified.

### Fix Verification Summary

| Fix | Finding | Status |
|-----|---------|--------|
| 1   | 205-A: `_strip_llm_preamble` regex misses `##` headings | FIXED and VERIFIED |
| 2   | 205-B: 500-char threshold rejects valid short sections | FIXED and VERIFIED |
| 3   | 207-A: View actions consume iteration budget | FIXED and VERIFIED |
| 4   | 302-A: Feature/NFR count regexes never match PRDs | FIXED and VERIFIED |
| 5   | 303-A: Per-feature merge drops cross-feature dependencies | FIXED and VERIFIED |
| 6   | 304-A: Unresolved tasks default to level 0 | FIXED and VERIFIED |

**Phase 02 + Phase 03: CLEAN at MEDIUM+ threshold.**

**Total: 0 critical, 0 high, 0 medium.**
